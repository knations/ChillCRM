#!/usr/bin/env python3
"""Enable CHILLCRM hosted production writes after explicit owner approval."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_OWNER_EMAIL = "kevinnations@gmail.com"
DEFAULT_PUBLIC_URL = "https://chillcrm.app"


class HttpResult:
    def __init__(self, status: int, headers: Any, body: bytes):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self) -> dict[str, Any]:
        return json.loads(self.body.decode("utf-8")) if self.body else {}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prompt_secret(label: str, env_name: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def app_request(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> HttpResult:
    data = None
    headers: dict[str, str] = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=90) as response:
            return HttpResult(response.status, response.headers, response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.headers, exc.read())


def run_child(script_name: str, args: list[str], env_updates: dict[str, str], *, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_updates)
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache")
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, timeout=timeout)


def compact_result(result: subprocess.CompletedProcess[str]) -> str:
    output = (result.stdout or result.stderr or "").strip()
    if not output:
        return f"exit_code={result.returncode}"
    try:
        payload = json.loads(output)
        clean = {key: payload.get(key) for key in payload if key not in {"password", "token", "secret"}}
        return f"exit_code={result.returncode}; output={json.dumps(clean, sort_keys=True)}"
    except json.JSONDecodeError:
        return f"exit_code={result.returncode}; output={output.splitlines()[0][:240]}"


def deploy_with_lock_state(token: str, *, locked: bool) -> tuple[subprocess.CompletedProcess[str], str]:
    result = run_child(
        "deploy_chillcrm_to_vercel.py",
        [],
        {
            "VERCEL_TOKEN": token,
            "CHILLCRM_SKIP_ENV_UPSERT": "1",
            "REMOTE_WRITE_LOCK": "1" if locked else "0",
            "CHILLCRM_VERCEL_INLINE_FILES": "1",
        },
    )
    url = ""
    try:
        payload = json.loads((result.stdout or "{}").strip())
        url = str(payload.get("url") or "").strip()
    except json.JSONDecodeError:
        url = ""
    return result, normalize_url(url)


def deploy_unlocked(token: str) -> tuple[subprocess.CompletedProcess[str], str]:
    return deploy_with_lock_state(token, locked=False)


def deploy_locked(token: str) -> tuple[subprocess.CompletedProcess[str], str]:
    return deploy_with_lock_state(token, locked=True)


def add_step(rows: list[dict[str, Any]], key: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "step",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
        }
    )


def has_failed(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("row_type") == "step" and row.get("status") == "failed" for row in rows)


def wait_for_runtime_lock_state(rows: list[dict[str, Any]], base_url: str, *, expected_locked: bool, key: str) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    last_evidence = ""
    for attempt in range(1, 37):
        health = app_request(opener, base_url, "GET", "/api/health")
        payload = health.json() if health.status == 200 else {}
        runtime = payload.get("runtime") or {}
        checks = payload.get("checks") or {}
        remote_lock = (runtime.get("remote_write_lock") or {}).get("enabled")
        database_mode = runtime.get("database_mode")
        database_ok = (checks.get("database") or {}).get("status") == "ok"
        exports_enabled = (runtime.get("bulk_package_exports") or {}).get("enabled")
        last_evidence = (
            f"attempt={attempt}; status={health.status}; ok={payload.get('ok')}; "
            f"database_mode={database_mode}; database_ok={database_ok}; remote_write_lock={remote_lock}; "
            f"export_package_enabled={exports_enabled}"
        )
        if (
            health.status == 200
            and payload.get("ok") is True
            and database_mode == "hosted_postgres_adapter_enabled"
            and database_ok
            and remote_lock is expected_locked
            and exports_enabled is False
        ):
            add_step(rows, key, "passed", last_evidence)
            return payload
        time.sleep(5)
    add_step(rows, key, "failed", last_evidence or "No health response.")
    return {}


def wait_for_unlocked_runtime(rows: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    return wait_for_runtime_lock_state(rows, base_url, expected_locked=False, key="verify_unlocked_runtime")


def wait_for_locked_runtime(rows: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    return wait_for_runtime_lock_state(rows, base_url, expected_locked=True, key="verify_relocked_runtime")


def verify_owner_credentials_before_unlock(rows: list[dict[str, Any]], base_url: str, owner_email: str, owner_password: str) -> bool:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    login = app_request(opener, base_url, "POST", "/api/auth/login", {"email": owner_email, "password": owner_password})
    login_payload = login.json()
    login_ok = login.status == 200 and login_payload.get("ok") is True
    add_step(rows, "preflight_owner_login", "passed" if login_ok else "failed", f"status={login.status}; ok={login_payload.get('ok')}; owner={owner_email}")
    if not login_ok:
        return False

    summary = app_request(opener, base_url, "GET", "/api/summary")
    summary_payload = summary.json()
    counts = summary_payload.get("counts") or {}
    counts_ok = summary.status == 200 and all(key in counts for key in ["people", "companies", "leads", "deals"])
    add_step(rows, "preflight_owner_summary_counts", "passed" if counts_ok else "failed", f"status={summary.status}; counts={counts}")
    return counts_ok


def verify_public_access(rows: list[dict[str, Any]], base_url: str) -> None:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    auth = app_request(opener, base_url, "GET", "/api/auth/status")
    auth_payload = auth.json()
    auth_ok = auth.status == 200 and auth_payload.get("auth_required") is True and auth_payload.get("authenticated") is False
    add_step(
        rows,
        "verify_public_auth_boundary",
        "passed" if auth_ok else "failed",
        f"auth_status={auth.status}; auth_required={auth_payload.get('auth_required')}; authenticated={auth_payload.get('authenticated')}",
    )
    summary = app_request(opener, base_url, "GET", "/api/summary")
    summary_payload = summary.json()
    summary_denied = summary.status == 401 and summary_payload.get("code") == "auth_required"
    add_step(rows, "verify_public_summary_denied", "passed" if summary_denied else "failed", f"status={summary.status}; code={summary_payload.get('code')}")
    write_attempt = app_request(
        opener,
        base_url,
        "POST",
        "/api/create_record",
        {"type": "person", "fields": {"name": "CHILLCRM Public Write Denial Probe"}},
    )
    write_payload = write_attempt.json()
    write_denied = write_attempt.status == 401 and write_payload.get("code") == "auth_required"
    add_step(rows, "verify_public_write_denied", "passed" if write_denied else "failed", f"status={write_attempt.status}; code={write_payload.get('code')}")


def owner_write_verification(rows: list[dict[str, Any]], base_url: str, owner_email: str, owner_password: str) -> str:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    login = app_request(opener, base_url, "POST", "/api/auth/login", {"email": owner_email, "password": owner_password})
    login_payload = login.json()
    login_ok = login.status == 200 and login_payload.get("ok") is True
    add_step(rows, "owner_login", "passed" if login_ok else "failed", f"status={login.status}; ok={login_payload.get('ok')}; owner={owner_email}")
    if not login_ok:
        return ""

    summary = app_request(opener, base_url, "GET", "/api/summary")
    summary_payload = summary.json()
    counts = summary_payload.get("counts") or {}
    counts_ok = summary.status == 200 and all(key in counts for key in ["people", "companies", "leads", "deals"])
    add_step(rows, "owner_summary_counts", "passed" if counts_ok else "failed", f"status={summary.status}; counts={counts}")
    if not counts_ok:
        return ""

    stamp = int(time.time())
    probe_name = f"CHILLCRM Production Write Verification {stamp} - RETAINED AS CUTOVER EVIDENCE"
    probe_email = f"chillcrm-production-write-{stamp}@example.test"
    created = app_request(
        opener,
        base_url,
        "POST",
        "/api/create_record",
        {"type": "person", "fields": {"name": probe_name, "email": probe_email}},
    )
    created_payload = created.json()
    detail = created_payload.get("detail") or {}
    record = detail.get("record") or {}
    record_id = int(record.get("id") or record.get("source_id") or 0)
    create_ok = created.status == 200 and created_payload.get("ok") is True and record_id > 0
    add_step(
        rows,
        "create_production_probe_record",
        "passed" if create_ok else "failed",
        f"status={created.status}; ok={created_payload.get('ok')}; record_id={record_id or 'missing'}; label=retained_cutover_evidence",
    )
    if not create_ok:
        return ""

    activity = app_request(opener, base_url, "GET", f"/api/activity?type=person&id={record_id}&limit=50")
    activity_payload = activity.json()
    events = activity_payload.get("activity") or []
    audit_events = [
        event
        for event in events
        if event.get("activity_type") == "audit"
        and event.get("summary") == "Created record"
        and str(event.get("actor_email") or "").lower() == owner_email.lower()
        and event.get("permission_action") == "create_edit_records"
    ]
    actor_roles = str((audit_events[0] if audit_events else {}).get("actor_roles") or "")
    audit_ok = activity.status == 200 and bool(audit_events) and ("owner" in actor_roles or "admin" in actor_roles)
    add_step(
        rows,
        "verify_actor_audit",
        "passed" if audit_ok else "failed",
        f"activity_status={activity.status}; actor={owner_email}; roles={actor_roles or 'missing'}; permission_action=create_edit_records",
    )
    add_step(
        rows,
        "cleanup_probe_record",
        "skipped",
        "The app has no clean delete/deactivate endpoint for CRM people; the clearly labeled production verification person was retained as cutover evidence.",
    )
    return f"person:{record_id} {probe_name}"


def refresh_reports(rows: list[dict[str, Any]], token: str, *, expected_unlocked: bool) -> None:
    lock_expected = "false" if expected_unlocked else "true"
    custom_domain_lock = "disabled" if expected_unlocked else "enabled"
    refresh_steps = [
        ("inspect_vercel_deployment.py", [], {"VERCEL_TOKEN": token}, "refresh_deployment_diagnostics"),
        ("verify_vercel_environment_readiness.py", [], {"VERCEL_TOKEN": token, "CHILLCRM_EXPECT_REMOTE_WRITE_LOCK": lock_expected}, "refresh_environment_readiness"),
        ("verify_custom_domain_readiness.py", ["--expected-remote-write-lock", custom_domain_lock], {}, "refresh_custom_domain_readiness"),
        ("verify_vercel_public_protection.py", [], {}, "refresh_public_protection"),
        ("verify_hosted_deployment_freshness.py", [], {}, "refresh_deployment_freshness"),
        ("verify_remote_production_readiness.py", [], {}, "refresh_remote_production_readiness"),
        ("prepare_remaining_production_gate_packet.py", [], {}, "refresh_remaining_gate_packet"),
        ("verify_secret_handling_boundaries.py", [], {}, "refresh_secret_boundaries"),
    ]
    for script_name, args, env, key in refresh_steps:
        result = run_child(script_name, args, env)
        add_step(rows, key, "passed" if result.returncode == 0 else "failed", compact_result(result))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["result"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    steps = [row for row in rows if row["row_type"] == "step"]
    lines = [
        "# Hosted Write Enablement",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the owner-approved production hosted-write enablement for CHILLCRM. It does not store Vercel tokens, owner passwords, database credentials, Supabase service-role keys, or bypass secrets.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Owner approved: {summary.get('owner_approved')}.",
        f"- Enable requested: {summary.get('enable_requested')}.",
        f"- Production URL: `{summary.get('production_url')}`.",
        f"- Deployment URL: `{summary.get('deployment_url') or 'missing'}`.",
        f"- Probe record: {summary.get('probe_record') or 'none'}.",
        f"- Remote write lock: {summary.get('remote_write_lock')}.",
        f"- Source of truth: {summary.get('source_of_truth')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        "- Secret values stored: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Hosted writes are enabled only when this report status is `hosted_writes_enabled`. If a failed status appears after a deployment attempt, re-enable `REMOTE_WRITE_LOCK=true` or stop hosted editing until the failure is understood.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(rows: list[dict[str, Any]], *, owner_approved: bool, enable_requested: bool, production_url: str, deployment_url: str, probe_record: str) -> dict[str, Any]:
    steps = [row for row in rows if row["row_type"] == "step"]
    failed = [row for row in steps if row["status"] == "failed"]
    input_required = [row for row in steps if row["status"] == "input_required"]
    passed = [row for row in steps if row["status"] == "passed"]
    remote_lock = "disabled" if not failed and not input_required and probe_record else "not_verified"
    status = "hosted_writes_enabled" if remote_lock == "disabled" else "hosted_write_enablement_failed" if failed else "input_required_hosted_write_enablement"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "hosted_writes_enabled" else "blocked_until_hosted_writes_verified",
        "owner_approved": "yes" if owner_approved else "no",
        "enable_requested": "yes" if enable_requested else "no",
        "production_url": production_url,
        "deployment_url": deployment_url,
        "probe_record": probe_record,
        "remote_write_lock": remote_lock,
        "source_of_truth": "hosted_remote_crm" if status == "hosted_writes_enabled" else "not_changed_by_failed_enablement",
        "passed": len(passed),
        "failed": len(failed),
        "input_required": len(input_required),
        "secret_values_stored": "no",
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    all_rows = [summary, *steps]
    write_csv(REPORTS_DIR / "hosted_write_enablement.csv", all_rows)
    write_report(REPORTS_DIR / "hosted_write_enablement.md", all_rows)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable owner-approved CHILLCRM hosted production writes.")
    parser.add_argument("--owner-approved", action="store_true", help="Required; confirms owner approved hosted production writes.")
    parser.add_argument("--enable-writes", action="store_true", help="Required to deploy REMOTE_WRITE_LOCK=false and verify a production write.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt for Vercel token and owner password without echoing them.")
    parser.add_argument("--url", default=DEFAULT_PUBLIC_URL, help="Owner-facing production URL.")
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", DEFAULT_OWNER_EMAIL))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    production_url = normalize_url(args.url or DEFAULT_PUBLIC_URL)
    deployment_url = ""
    probe_record = ""

    if not args.owner_approved:
        add_step(rows, "owner_approval", "input_required", "Run with --owner-approved only after explicit owner approval for hosted production writes.")
    if not args.enable_writes:
        add_step(rows, "enable_confirmation", "input_required", "Run with --enable-writes to deploy REMOTE_WRITE_LOCK=false and verify production writes.")
    if args.owner_approved and args.enable_writes:
        token, token_source = prompt_secret("Vercel token", "VERCEL_TOKEN", prompt=args.prompt_secrets)
        owner_password, password_source = prompt_secret("Owner password", "AUTH_BOOTSTRAP_ADMIN_PASSWORD", prompt=args.prompt_secrets)
        if not token:
            add_step(rows, "vercel_token", "input_required", "Missing Vercel token. Use --prompt-secrets or VERCEL_TOKEN.")
        if not owner_password:
            add_step(rows, "owner_password", "input_required", "Missing owner password. Use --prompt-secrets or AUTH_BOOTSTRAP_ADMIN_PASSWORD.")
    else:
        token, token_source = "", "not_requested"
        owner_password, password_source = "", "not_requested"

    if any(row["status"] == "input_required" for row in rows):
        summary = persist(
            rows,
            owner_approved=args.owner_approved,
            enable_requested=args.enable_writes,
            production_url=production_url,
            deployment_url=deployment_url,
            probe_record=probe_record,
        )
        print(json.dumps(summary, indent=2))
        return 1

    add_step(rows, "owner_approval", "passed", "Owner-approved hosted production write enablement flag supplied.")
    add_step(rows, "secrets", "passed", f"Vercel token source={token_source}; owner password source={password_source}; values not stored.")

    owner_email = args.owner_email.strip() or DEFAULT_OWNER_EMAIL
    credentials_ok = verify_owner_credentials_before_unlock(rows, production_url, owner_email, owner_password)
    if credentials_ok:
        deploy_result, deployment_url = deploy_unlocked(token)
        add_step(rows, "deploy_remote_write_lock_off", "passed" if deploy_result.returncode == 0 else "failed", compact_result(deploy_result))
        if deploy_result.returncode == 0:
            wait_for_unlocked_runtime(rows, production_url)
            verify_public_access(rows, production_url)
            if not has_failed(rows):
                probe_record = owner_write_verification(rows, production_url, owner_email, owner_password)
            if not has_failed(rows) and probe_record:
                persist(
                    rows,
                    owner_approved=args.owner_approved,
                    enable_requested=args.enable_writes,
                    production_url=production_url,
                    deployment_url=deployment_url,
                    probe_record=probe_record,
                )
                refresh_reports(rows, token, expected_unlocked=True)
            else:
                relock_result, relock_url = deploy_locked(token)
                if relock_url and not deployment_url:
                    deployment_url = relock_url
                add_step(rows, "safety_relock_remote_write_lock_on", "passed" if relock_result.returncode == 0 else "failed", compact_result(relock_result))
                if relock_result.returncode == 0:
                    wait_for_locked_runtime(rows, production_url)
                refresh_reports(rows, token, expected_unlocked=False)
    else:
        add_step(rows, "deploy_remote_write_lock_off", "skipped", "Owner credential preflight failed; production writes were not unlocked.")

    summary = persist(
        rows,
        owner_approved=args.owner_approved,
        enable_requested=args.enable_writes,
        production_url=production_url,
        deployment_url=deployment_url,
        probe_record=probe_record,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "hosted_writes_enabled" else 1


if __name__ == "__main__":
    raise SystemExit(main())
