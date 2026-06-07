#!/usr/bin/env python3
"""Execute the owner-approved hosted write-audit rehearsal with lock restore."""

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
VERCEL_API = "https://api.vercel.com"
DEFAULT_PROJECT_ID = "prj_BW7lf5NVtOGjZ8eA28pIVOBIACgh"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
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


def read_latest_url() -> str:
    report = REPORTS_DIR / "vercel_staging_deployment_status.md"
    if not report.exists():
        return ""
    for line in report.read_text(encoding="utf-8").splitlines():
        if line.startswith("- URL: `") and line.endswith("`."):
            return line.split("`", 2)[1].strip()
    return ""


def read_public_url() -> str:
    report = REPORTS_DIR / "custom_domain_readiness.md"
    if not report.exists():
        return DEFAULT_PUBLIC_URL
    for line in report.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Canonical URL: `") and line.endswith("`."):
            return line.split("`", 2)[1].strip()
    return DEFAULT_PUBLIC_URL


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def request_vercel_json(method: str, path: str, token: str, *, query: dict[str, str], body: Any | None = None) -> dict[str, Any]:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vercel request failed with {exc.code}: {raw[:500]}") from exc


def read_bypass_secret(token: str, project_id: str, team_slug: str) -> str:
    query = {"slug": team_slug} if team_slug else {}
    project = request_vercel_json("GET", f"/v9/projects/{project_id}", token, query=query)
    protection = project.get("protectionBypass") or {}
    if not protection:
        raise RuntimeError("No Vercel automation bypass secret is available for this project.")
    return str(next(iter(protection.keys())))


def app_request(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    bypass_secret: str = "",
) -> HttpResult:
    data = None
    headers: dict[str, str] = {"Accept": "application/json"}
    if bypass_secret:
        headers["x-vercel-protection-bypass"] = bypass_secret
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=90) as response:
            return HttpResult(response.status, response.headers, response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.headers, exc.read())


def run_child(script_name: str, args: list[str], env_updates: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_updates)
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache")
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, timeout=1800)


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


def deploy_write_lock(token: str, enabled: bool) -> tuple[subprocess.CompletedProcess[str], str]:
    result = run_child(
        "deploy_chillcrm_to_vercel.py",
        [],
        {
            "VERCEL_TOKEN": token,
            "CHILLCRM_SKIP_ENV_UPSERT": "1",
            "REMOTE_WRITE_LOCK": "1" if enabled else "0",
            "CHILLCRM_VERCEL_INLINE_FILES": "1",
        },
    )
    url = ""
    try:
        payload = json.loads((result.stdout or "{}").strip())
        url = str(payload.get("url") or "").strip()
    except json.JSONDecodeError:
        url = read_latest_url()
    return result, normalize_url(url)


def add_step(rows: list[dict[str, Any]], key: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "step",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
        }
    )


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
        "# Hosted Write-Audit Rehearsal Execution",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the guarded hosted write-audit rehearsal execution. It does not store passwords, Vercel tokens, bypass secrets, database credentials, or Supabase service-role keys. It only runs after explicit owner approval and restores REMOTE_WRITE_LOCK=true before marking the rehearsal passed.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Owner approved: {summary.get('owner_approved')}.",
        f"- Execution requested: {summary.get('execution_requested')}.",
        f"- Initial URL: `{summary.get('initial_url') or 'missing'}`.",
        f"- Unlocked URL: `{summary.get('unlocked_url') or 'missing'}`.",
        f"- Restored locked URL: `{summary.get('restored_url') or 'missing'}`.",
        f"- Probe record: {summary.get('probe_record') or 'none'}.",
        f"- Write lock restored: {summary.get('write_lock_restored')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        "- Secret values stored: no.",
        "- Source of truth changed: no.",
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
            "This rehearsal is staging-only. If any step fails, keep local SQLite as source of truth, inspect the failure, and verify REMOTE_WRITE_LOCK=true before trying again.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(
    rows: list[dict[str, Any]],
    *,
    owner_approved: bool,
    execution_requested: bool,
    initial_url: str,
    unlocked_url: str,
    restored_url: str,
    probe_record: str,
    write_lock_restored: bool,
) -> None:
    steps = [row for row in rows if row["row_type"] == "step"]
    failed = [row for row in steps if row["status"] == "failed"]
    input_required = [row for row in steps if row["status"] == "input_required"]
    passed = [row for row in steps if row["status"] == "passed"]
    status = "hosted_write_audit_execution_passed"
    production_gate = "pass"
    if failed:
        status = "hosted_write_audit_execution_failed"
        production_gate = "blocked_until_hosted_write_audit_rehearsal_passes"
    elif input_required:
        status = "input_required_hosted_write_audit_execution"
        production_gate = "blocked_until_hosted_write_audit_rehearsal_passes"
    elif not write_lock_restored:
        status = "write_lock_restore_unverified"
        production_gate = "blocked_until_write_lock_restored"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": production_gate,
        "owner_approved": "yes" if owner_approved else "no",
        "execution_requested": "yes" if execution_requested else "no",
        "initial_url": initial_url,
        "unlocked_url": unlocked_url,
        "restored_url": restored_url,
        "probe_record": probe_record,
        "write_lock_restored": "yes" if write_lock_restored else "no",
        "passed": len(passed),
        "failed": len(failed),
        "input_required": len(input_required),
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    all_rows = [summary, *steps]
    write_csv(REPORTS_DIR / "hosted_write_audit_execution.csv", all_rows)
    write_report(REPORTS_DIR / "hosted_write_audit_execution.md", all_rows)


def assert_status(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_rehearsal(args: argparse.Namespace, rows: list[dict[str, Any]], token: str, owner_password: str, initial_url: str) -> tuple[str, str, str, bool]:
    owner_email = args.owner_email.strip() or DEFAULT_OWNER_EMAIL
    project_id = args.project_id.strip() or DEFAULT_PROJECT_ID
    team_slug = args.team_slug.strip() or DEFAULT_TEAM_SLUG
    unlocked_url = ""
    restored_url = ""
    probe_record = ""
    write_lock_restored = False
    bypass_secret = read_bypass_secret(token, project_id, team_slug)
    add_step(rows, "vercel_bypass", "passed", "Read Vercel protection bypass in memory; secret not stored.")

    preflight = run_child(
        "prepare_hosted_write_audit_rehearsal.py",
        ["--target-url", initial_url, "--owner-approved", "--notes", "Owner approved execution runner preflight; no writes performed by preflight."],
        {},
    )
    add_step(rows, "preflight_owner_approval", "passed" if preflight.returncode == 0 else "failed", compact_result(preflight))
    if preflight.returncode != 0:
        return unlocked_url, restored_url, probe_record, write_lock_restored

    unlock_result, unlocked_url = deploy_write_lock(token, False)
    add_step(rows, "deploy_write_lock_off", "passed" if unlock_result.returncode == 0 else "failed", compact_result(unlock_result))
    if unlock_result.returncode != 0 or not unlocked_url:
        return unlocked_url, restored_url, probe_record, write_lock_restored

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    health = app_request(opener, unlocked_url, "GET", "/api/health", bypass_secret=bypass_secret)
    assert_status(health.status == 200, f"Unlocked health returned {health.status}.")
    runtime = health.json()["runtime"]
    assert_status(runtime["remote_write_lock"]["enabled"] is False, "Unlocked deployment still reports REMOTE_WRITE_LOCK enabled.")
    add_step(rows, "verify_unlocked_runtime", "passed", f"{unlocked_url} reports REMOTE_WRITE_LOCK=false.")

    login = app_request(opener, unlocked_url, "POST", "/api/auth/login", {"email": owner_email, "password": owner_password}, bypass_secret=bypass_secret)
    assert_status(login.status == 200 and login.json().get("ok") is True, f"Owner login returned {login.status}.")
    add_step(rows, "owner_login_unlocked", "passed", f"Signed in as {owner_email}.")

    stamp = int(time.time())
    probe_name = f"CHILLCRM Staging Write Audit Probe {stamp}"
    probe_email = f"chillcrm-write-audit-{stamp}@example.test"
    created = app_request(
        opener,
        unlocked_url,
        "POST",
        "/api/create_record",
        {"type": "person", "fields": {"name": probe_name, "email": probe_email}},
        bypass_secret=bypass_secret,
    )
    assert_status(created.status == 200 and created.json().get("ok") is True, f"Probe create returned {created.status}: {created.body[:160]!r}")
    detail = created.json().get("detail") or {}
    record_id = int(((detail.get("record") or {}).get("id") or (detail.get("record") or {}).get("source_id") or 0))
    assert_status(record_id > 0, "Probe create did not return a record id.")
    probe_record = f"person:{record_id} {probe_name}"
    add_step(rows, "create_probe_record", "passed", f"Created staging-only probe person id={record_id}; backup path omitted from report.")

    activity = app_request(opener, unlocked_url, "GET", f"/api/activity?type=person&id={record_id}&limit=50", bypass_secret=bypass_secret)
    assert_status(activity.status == 200, f"Probe activity returned {activity.status}.")
    events = activity.json().get("activity") or []
    audit_events = [
        event
        for event in events
        if event.get("activity_type") == "audit"
        and event.get("summary") == "Created record"
        and str(event.get("actor_email") or "").lower() == owner_email.lower()
        and event.get("permission_action") == "create_edit_records"
    ]
    assert_status(bool(audit_events), "Created probe record did not expose owner actor audit metadata through Activity.")
    actor_roles = str(audit_events[0].get("actor_roles") or "")
    assert_status("owner" in actor_roles or "admin" in actor_roles, f"Actor roles did not include owner/admin: {actor_roles!r}.")
    add_step(rows, "verify_actor_audit", "passed", f"Activity shows actor={owner_email}, roles={actor_roles}, permission_action=create_edit_records.")
    return unlocked_url, restored_url, probe_record, write_lock_restored


def restore_and_refresh(
    rows: list[dict[str, Any]],
    *,
    token: str,
    owner_password: str,
    owner_email: str,
    project_id: str,
    team_slug: str,
    restored_hint: str,
    probe_record: str,
) -> tuple[str, bool]:
    restored_url = restored_hint
    write_lock_restored = False
    locked_write_blocked = False
    restore_result, restored_url = deploy_write_lock(token, True)
    add_step(rows, "deploy_write_lock_on", "passed" if restore_result.returncode == 0 else "failed", compact_result(restore_result))
    if restore_result.returncode != 0 or not restored_url:
        return restored_url, write_lock_restored

    bypass_secret = read_bypass_secret(token, project_id, team_slug)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    health = app_request(opener, restored_url, "GET", "/api/health", bypass_secret=bypass_secret)
    if health.status == 200 and health.json().get("runtime", {}).get("remote_write_lock", {}).get("enabled") is True:
        write_lock_restored = True
        add_step(rows, "verify_relocked_runtime", "passed", f"{restored_url} reports REMOTE_WRITE_LOCK=true.")
    else:
        add_step(rows, "verify_relocked_runtime", "failed", f"Health returned {health.status}; lock evidence missing.")
        return restored_url, write_lock_restored

    login = app_request(opener, restored_url, "POST", "/api/auth/login", {"email": owner_email, "password": owner_password}, bypass_secret=bypass_secret)
    if login.status != 200 or login.json().get("ok") is not True:
        add_step(rows, "owner_login_relocked", "failed", f"Owner login returned {login.status}.")
        return restored_url, write_lock_restored
    locked_write = app_request(
        opener,
        restored_url,
        "POST",
        "/api/create_record",
        {"type": "person", "fields": {"name": "CHILLCRM Relock Verification Probe"}},
        bypass_secret=bypass_secret,
    )
    if locked_write.status == 423 and locked_write.json().get("code") == "remote_write_lock_enabled":
        locked_write_blocked = True
        add_step(rows, "verify_write_lock_blocks_again", "passed", "create_record is blocked after relock.")
    else:
        add_step(rows, "verify_write_lock_blocks_again", "failed", f"Locked write returned {locked_write.status}.")

    diagnostics = run_child("inspect_vercel_deployment.py", [], {"VERCEL_TOKEN": token})
    add_step(rows, "refresh_deployment_diagnostics", "passed" if diagnostics.returncode == 0 else "failed", compact_result(diagnostics))
    environment = run_child("verify_vercel_environment_readiness.py", [], {"VERCEL_TOKEN": token})
    add_step(rows, "refresh_environment_readiness", "passed" if environment.returncode == 0 else "failed", compact_result(environment))
    custom_domain = run_child("verify_custom_domain_readiness.py", [], {})
    add_step(rows, "refresh_custom_domain_readiness", "passed" if custom_domain.returncode == 0 else "failed", compact_result(custom_domain))
    smoke_url = read_public_url() or restored_url
    smoke = run_child(
        "run_newest_hosted_smoke_with_vercel_bypass.py",
        ["--url", smoke_url, "--owner-email", owner_email],
        {"VERCEL_TOKEN": token, "AUTH_BOOTSTRAP_ADMIN_PASSWORD": owner_password},
    )
    add_step(rows, "refresh_hosted_smoke", "passed" if smoke.returncode == 0 else "failed", compact_result(smoke))
    public = run_child("verify_vercel_public_protection.py", [], {})
    add_step(rows, "refresh_public_protection", "passed" if public.returncode == 0 else "failed", compact_result(public))
    can_mark_passed = True
    mark_skip_reason = ""
    if not probe_record:
        can_mark_passed = False
        mark_skip_reason = "Not marked passed because no staging probe record was created and verified."
    elif not write_lock_restored or not locked_write_blocked:
        can_mark_passed = False
        mark_skip_reason = "Not marked passed because relock and blocked-write proof are incomplete."
    elif any(row.get("status") == "failed" for row in rows):
        can_mark_passed = False
        mark_skip_reason = "Not marked passed because one or more execution or refresh steps failed."
    if can_mark_passed:
        evidence = f"{probe_record}; actor-aware activity verified; REMOTE_WRITE_LOCK restored on {restored_url}; hosted smoke refreshed."
        marked = run_child(
            "prepare_hosted_write_audit_rehearsal.py",
            ["--target-url", restored_url, "--owner-approved", "--mark-passed", "--write-lock-restored", "--execution-evidence", evidence],
            {},
        )
        add_step(rows, "mark_rehearsal_passed", "passed" if marked.returncode == 0 else "failed", compact_result(marked))
    else:
        add_step(rows, "mark_rehearsal_passed", "skipped", mark_skip_reason)
    for script_name, proof in [
        ("verify_remote_monitoring_readiness.py", "remote_monitoring_readiness"),
        ("verify_remote_production_readiness.py", "remote_production_readiness"),
        ("prepare_owner_gate_intake_packet.py", "owner_gate_intake_packet"),
        ("prepare_remaining_production_gate_packet.py", "remaining_production_gates_packet"),
    ]:
        result = run_child(script_name, [], {})
        add_step(rows, f"refresh_{proof}", "passed" if result.returncode == 0 else "failed", compact_result(result))
    return restored_url, write_lock_restored


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the owner-approved hosted write-audit rehearsal.")
    parser.add_argument("--execute", action="store_true", help="Required to perform the rehearsal and temporarily unlock hosted staging writes.")
    parser.add_argument("--owner-approved", action="store_true", help="Required; confirms owner approved the staging-only write-audit rehearsal.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt for Vercel token and owner password without echoing them.")
    parser.add_argument("--url", default="", help="Current locked hosted URL. Defaults to the latest deployment report.")
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", DEFAULT_OWNER_EMAIL))
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", DEFAULT_PROJECT_ID))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", DEFAULT_TEAM_SLUG))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    initial_url = normalize_url(args.url or read_latest_url())
    unlocked_url = ""
    restored_url = ""
    probe_record = ""
    write_lock_restored = False

    if not args.owner_approved:
        add_step(rows, "owner_approval", "input_required", "Run with --owner-approved only after explicit owner approval for the staging write-audit rehearsal.")
    if not args.execute:
        add_step(rows, "execution_confirmation", "input_required", "Run with --execute to temporarily unlock writes, run the probe, and restore the lock.")
    if not initial_url:
        add_step(rows, "target_url", "input_required", "Missing target URL. Refresh Vercel deployment status or pass --url.")
    should_execute = bool(args.execute and args.owner_approved and initial_url)
    if should_execute:
        token, token_source = prompt_secret("Vercel token", "VERCEL_TOKEN", prompt=args.prompt_secrets)
        owner_password, password_source = prompt_secret("Owner password", "AUTH_BOOTSTRAP_ADMIN_PASSWORD", prompt=args.prompt_secrets)
    else:
        token, token_source = "", "not_requested"
        owner_password, password_source = "", "not_requested"
    if args.execute and args.owner_approved:
        if not token:
            add_step(rows, "vercel_token", "input_required", "Missing Vercel token. Use --prompt-secrets or VERCEL_TOKEN.")
        if not owner_password:
            add_step(rows, "owner_password", "input_required", "Missing owner password. Use --prompt-secrets or AUTH_BOOTSTRAP_ADMIN_PASSWORD.")

    if any(row["status"] == "input_required" for row in rows):
        persist(
            rows,
            owner_approved=args.owner_approved,
            execution_requested=args.execute,
            initial_url=initial_url,
            unlocked_url=unlocked_url,
            restored_url=restored_url,
            probe_record=probe_record,
            write_lock_restored=write_lock_restored,
        )
        print(json.dumps({"status": "input_required_hosted_write_audit_execution", "report": str(REPORTS_DIR / "hosted_write_audit_execution.md")}, indent=2))
        return 1

    add_step(rows, "owner_approval", "passed", "Owner-approved execution flag supplied.")
    add_step(rows, "secrets", "passed", f"Vercel token source={token_source}; owner password source={password_source}; values not stored.")
    try:
        unlocked_url, restored_url, probe_record, write_lock_restored = run_rehearsal(args, rows, token, owner_password, initial_url)
    except Exception as exc:  # noqa: BLE001 - report must capture failure and still attempt relock.
        add_step(rows, "execute_rehearsal", "failed", str(exc))
    finally:
        if token:
            try:
                restored_url, write_lock_restored = restore_and_refresh(
                    rows,
                    token=token,
                    owner_password=owner_password,
                    owner_email=args.owner_email.strip() or DEFAULT_OWNER_EMAIL,
                    project_id=args.project_id.strip() or DEFAULT_PROJECT_ID,
                    team_slug=args.team_slug.strip() or DEFAULT_TEAM_SLUG,
                    restored_hint=restored_url,
                    probe_record=probe_record,
                )
            except Exception as exc:  # noqa: BLE001
                add_step(rows, "restore_and_refresh", "failed", str(exc))

    persist(
        rows,
        owner_approved=args.owner_approved,
        execution_requested=args.execute,
        initial_url=initial_url,
        unlocked_url=unlocked_url,
        restored_url=restored_url,
        probe_record=probe_record,
        write_lock_restored=write_lock_restored,
    )
    failed = [row for row in rows if row["status"] == "failed"]
    input_required = [row for row in rows if row["status"] == "input_required"]
    status = "failed" if failed else "input_required" if input_required else "hosted_write_audit_execution_passed"
    print(
        json.dumps(
            {
                "status": status,
                "unlocked_url": unlocked_url,
                "restored_url": restored_url,
                "probe_record": probe_record,
                "write_lock_restored": "yes" if write_lock_restored else "no",
                "failed": len(failed),
                "input_required": len(input_required),
                "report": str(REPORTS_DIR / "hosted_write_audit_execution.md"),
            },
            indent=2,
        )
    )
    return 1 if failed or input_required or not write_lock_restored else 0


if __name__ == "__main__":
    raise SystemExit(main())
