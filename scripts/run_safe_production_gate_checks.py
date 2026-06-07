#!/usr/bin/env python3
"""Run safe CHILLCRM production-gate checks without storing secrets."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_PROJECT_REF = "ckjbnummsxqcyeahzynz"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def latest_url() -> str:
    for relative_path in [
        "reports/remote_production_readiness.md",
        "reports/remaining_production_gates_packet.md",
        "reports/custom_domain_readiness.md",
    ]:
        value = backtick_value(read_text(relative_path), "Public URL")
        if value and value != "missing":
            return value
        value = backtick_value(read_text(relative_path), "Canonical URL")
        if value and value != "missing":
            return value
    for relative_path in [
        "reports/vercel_staging_deployment_status.md",
        "reports/remote_production_readiness.md",
        "reports/remaining_production_gates_packet.md",
    ]:
        value = backtick_value(read_text(relative_path), "Latest URL")
        if value and value != "missing":
            return value
        value = backtick_value(read_text(relative_path), "URL")
        if value and value != "missing":
            return value
    return ""


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def public_app_auth_domain(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    return host.lower() in {"chillcrm.app", "www.chillcrm.app"}


def env_or_prompt(env_name: str, label: str, *, prompt: bool, secret: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    if secret:
        value = getpass.getpass(f"{label}: ").strip()
    else:
        value = input(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def add_row(
    rows: list[dict[str, Any]],
    key: str,
    status: str,
    evidence: str,
    *,
    requested: bool,
    proof_report: str = "",
    exit_code: int | str = "",
    safe_class: str = "safe_no_crm_record_writes",
) -> None:
    rows.append(
        {
            "row_type": "phase",
            "key": key,
            "status": status,
            "requested": "yes" if requested else "no",
            "exit_code": exit_code,
            "safe_class": safe_class,
            "proof_report": proof_report,
            "evidence": " ".join(str(evidence).split()),
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secrets_stored": "no",
        }
    )


def run_child(script_name: str, args: list[str], env_updates: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_updates)
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache")
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=600)


def compact_child_result(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        return f"exit_code={result.returncode}"
    try:
        payload = json.loads(text)
        clean_payload = {key: payload.get(key) for key in payload if key not in {"password", "token", "secret"}}
        return f"exit_code={result.returncode}; output={json.dumps(clean_payload, sort_keys=True)}"
    except json.JSONDecodeError:
        first_line = text.splitlines()[0]
        return f"exit_code={result.returncode}; output={first_line[:220]}"


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
    phases = [row for row in rows if row["row_type"] == "phase"]
    lines = [
        "# Safe Production Gate Runner",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the safe CHILLCRM production-gate runner. The runner stores no secret values, does not write CRM records, does not unlock hosted writes, does not sign owner approvals, and does not switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Target URL: `{summary.get('target_url') or 'missing'}`.",
        f"- Requested checks: {summary.get('requested_checks')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Skipped: {summary.get('skipped')}.",
        f"- Failed: {summary.get('failed')}.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Phase Results",
        "",
        "| Phase | Status | Requested | Safe Class | Proof Report | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in phases:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("requested")),
                    str(row.get("safe_class")),
                    str(row.get("proof_report") or ""),
                    str(row.get("evidence") or "").replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safe Use",
            "",
            "- Use `--refresh-only` to regenerate non-secret readiness evidence.",
            "- Use `--all-safe --prompt-secrets` to run hosted smoke, Supabase backup visibility, and readiness refreshes with hidden prompts.",
            "- Public-domain hosted smoke on `https://chillcrm.app` uses CHILLCRM app auth and does not require a Vercel bypass secret.",
            "- Hosted smoke may create and deactivate temporary app users to prove role behavior; it should not create CRM people, companies, leads, deals, notes, tasks, or archive links while the remote write lock is enabled.",
            "- Write-audit rehearsal, monitoring signoff, owner shakedown signoff, write unlock, restore operations, and source-of-truth cutover remain separate owner-approved steps.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(rows: list[dict[str, Any]], target_url: str) -> dict[str, Any]:
    phases = [row for row in rows if row["row_type"] == "phase"]
    requested = [row for row in phases if row.get("requested") == "yes"]
    failed = [row for row in phases if row.get("status") == "failed"]
    input_required = [row for row in phases if row.get("status") == "input_required"]
    skipped = [row for row in phases if row.get("status") == "skipped"]
    passed = [row for row in phases if row.get("status") == "passed"]
    if failed:
        status = "safe_runner_failed"
    elif input_required:
        status = "input_required_safe_checks"
    elif requested and not skipped:
        status = "safe_checks_completed"
    elif passed:
        status = "safe_reports_refreshed"
    else:
        status = "no_safe_checks_requested"
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "target_url": target_url,
        "requested_checks": len(requested),
        "passed": len(passed),
        "input_required": len(input_required),
        "skipped": len(skipped),
        "failed": len(failed),
    }


def persist(rows: list[dict[str, Any]], target_url: str) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows_with_summary = [summarize(rows, target_url), *rows]
    write_csv(REPORTS_DIR / "safe_production_gate_runner.csv", rows_with_summary)
    write_report(REPORTS_DIR / "safe_production_gate_runner.md", rows_with_summary)


def run_refresh(rows: list[dict[str, Any]], *, requested: bool, target_url: str) -> None:
    refresh_scripts = [
        ("verify_hosted_deployment_freshness.py", "reports/hosted_deployment_freshness.md"),
        ("verify_hosted_redeploy_preflight.py", "reports/hosted_redeploy_preflight.md"),
        ("verify_custom_domain_readiness.py", "reports/custom_domain_readiness.md"),
        ("verify_remaining_gate_guardrails.py", "reports/remaining_gate_guardrails.md"),
        ("verify_private_execution_inputs.py", "reports/private_execution_inputs.md"),
        ("run_owner_confirmed_production_wave.py", "reports/owner_confirmed_production_wave.md"),
        ("verify_supabase_staging_data_parity.py", "reports/supabase_staging_data_parity.md"),
        ("verify_supabase_staging_refresh_preflight.py", "reports/supabase_staging_refresh_preflight.md"),
        ("run_supabase_staging_refresh.py", "reports/supabase_staging_refresh_run.md"),
        ("verify_remote_monitoring_readiness.py", "reports/remote_monitoring_readiness.md"),
        ("verify_local_write_freeze_readiness.py", "reports/local_write_freeze_readiness.md"),
        ("verify_cutover_rollback_package_readiness.py", "reports/cutover_rollback_package_readiness.md"),
        ("verify_source_of_truth_cutover_preflight.py", "reports/source_of_truth_cutover_preflight.md"),
        ("verify_owner_recovery_closure.py", "reports/owner_recovery_closure.md"),
        ("verify_remote_production_readiness.py", "reports/remote_production_readiness.md"),
        ("prepare_owner_gate_intake_packet.py", "reports/owner_gate_intake_packet.md"),
        ("validate_owner_gate_reply.py", "reports/owner_gate_reply_validation.md"),
        ("prepare_remaining_production_gate_packet.py", "reports/remaining_production_gates_packet.md"),
        ("verify_remaining_gate_execution_readiness.py", "reports/remaining_gate_execution_readiness.md"),
        ("verify_secret_handling_boundaries.py", "reports/secret_handling_boundaries.md"),
        ("verify_remote_production_readiness.py", "reports/remote_production_readiness.md"),
        ("prepare_owner_approved_wave_packet.py", "reports/owner_approved_wave_packet.md"),
    ]
    add_row(
        rows,
        "record_source_of_truth_cutover_approval.py",
        "skipped",
        "Refresh-only runner preserves final cutover approval state; use the dedicated owner approval command when every gate is green.",
        requested=False,
        proof_report="reports/source_of_truth_cutover_approval.md",
        safe_class="stateful_owner_approval_preserved",
    )
    persist(rows, target_url)
    for script_name, proof_report in refresh_scripts:
        result = run_child(script_name, [], {})
        add_row(
            rows,
            script_name,
            "passed" if result.returncode == 0 else "failed",
            compact_child_result(result),
            requested=requested,
            proof_report=proof_report,
            exit_code=result.returncode,
            safe_class="report_refresh_only",
        )
        persist(rows, target_url)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CHILLCRM safe production-gate checks without writing CRM records or storing secrets."
    )
    parser.add_argument("--url", default="", help="Vercel deployment URL. Defaults to the latest URL in reports.")
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", ""))
    parser.add_argument("--hosted-smoke", action="store_true", help="Run hosted app smoke against Vercel.")
    parser.add_argument("--supabase-backup", action="store_true", help="Run Supabase backup/PITR visibility check.")
    parser.add_argument("--all-safe", action="store_true", help="Run hosted smoke, Supabase backup visibility, and refresh reports.")
    parser.add_argument("--refresh-only", action="store_true", help="Only refresh non-secret monitoring/readiness reports.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt for missing secrets without echoing them.")
    parser.add_argument("--project-ref", default=os.environ.get("SUPABASE_PROJECT_REF", DEFAULT_PROJECT_REF))
    parser.add_argument("--expect-document-file-access", default=os.environ.get("EXPECT_DOCUMENT_FILE_ACCESS", "true"))
    args = parser.parse_args()

    target_url = normalize_url(args.url or latest_url())
    run_hosted_smoke = args.hosted_smoke or args.all_safe
    run_supabase_backup = args.supabase_backup or args.all_safe
    run_any_refresh = args.refresh_only or args.all_safe or run_hosted_smoke or run_supabase_backup
    rows: list[dict[str, Any]] = []

    if run_hosted_smoke:
        owner_email = args.owner_email.strip()
        email_source = "arg_or_env" if owner_email else "missing"
        if not owner_email and args.prompt_secrets:
            owner_email, email_source = env_or_prompt("AUTH_BOOTSTRAP_ADMIN_EMAIL", "Owner email", prompt=True, secret=False)
        owner_password, password_source = env_or_prompt(
            "AUTH_BOOTSTRAP_ADMIN_PASSWORD", "Owner password", prompt=args.prompt_secrets, secret=True
        )
        if public_app_auth_domain(target_url):
            bypass_secret, bypass_source = os.environ.get("VERCEL_PROTECTION_BYPASS_SECRET", "").strip(), "not_required_public_domain"
        else:
            bypass_secret, bypass_source = env_or_prompt(
                "VERCEL_PROTECTION_BYPASS_SECRET", "Vercel protection bypass secret", prompt=args.prompt_secrets, secret=True
            )
        missing = [
            label
            for label, value in [
                ("target URL", target_url),
                ("owner email", owner_email),
                ("owner password", owner_password),
                ("Vercel protection bypass secret", bypass_secret if not public_app_auth_domain(target_url) else "not_required"),
            ]
            if not value
        ]
        if missing:
            add_row(
                rows,
                "vercel_hosted_app_smoke",
                "input_required",
                f"Missing {', '.join(missing)}. Use --prompt-secrets or one-shot environment variables.",
                requested=True,
                proof_report="reports/vercel_hosted_app_smoke.md",
                safe_class="creates_and_deactivates_temp_app_users_no_crm_record_writes",
            )
        else:
            result = run_child(
                "verify_vercel_hosted_app.py",
                [],
                {
                    "CHILLCRM_VERCEL_URL": target_url,
                    "AUTH_BOOTSTRAP_ADMIN_EMAIL": owner_email,
                    "AUTH_BOOTSTRAP_ADMIN_PASSWORD": owner_password,
                    "VERCEL_PROTECTION_BYPASS_SECRET": bypass_secret,
                    "EXPECT_DOCUMENT_FILE_ACCESS": args.expect_document_file_access,
                },
            )
            add_row(
                rows,
                "vercel_hosted_app_smoke",
                "passed" if result.returncode == 0 else "failed",
                f"{compact_child_result(result)}; email_source={email_source}; password_source={password_source}; bypass_source={bypass_source}",
                requested=True,
                proof_report="reports/vercel_hosted_app_smoke.md",
                exit_code=result.returncode,
                safe_class="creates_and_deactivates_temp_app_users_no_crm_record_writes",
            )
        persist(rows, target_url)
    else:
        add_row(
            rows,
            "vercel_hosted_app_smoke",
            "skipped",
            "Not requested. Use --hosted-smoke or --all-safe.",
            requested=False,
            proof_report="reports/vercel_hosted_app_smoke.md",
            safe_class="creates_and_deactivates_temp_app_users_no_crm_record_writes",
        )

    if run_supabase_backup:
        token, token_source = env_or_prompt(
            "SUPABASE_ACCESS_TOKEN", "Supabase Management API access token", prompt=args.prompt_secrets, secret=True
        )
        if not token:
            add_row(
                rows,
                "supabase_backup_readiness",
                "input_required",
                "Missing Supabase Management API access token. Use --prompt-secrets or SUPABASE_ACCESS_TOKEN.",
                requested=True,
                proof_report="reports/supabase_backup_readiness.md",
                safe_class="management_api_read_no_data_changes",
            )
        else:
            result = run_child(
                "verify_supabase_backup_readiness.py",
                ["--project-ref", args.project_ref],
                {"SUPABASE_ACCESS_TOKEN": token},
            )
            add_row(
                rows,
                "supabase_backup_readiness",
                "passed" if result.returncode == 0 else "failed",
                f"{compact_child_result(result)}; token_source={token_source}",
                requested=True,
                proof_report="reports/supabase_backup_readiness.md",
                exit_code=result.returncode,
                safe_class="management_api_read_no_data_changes",
            )
        persist(rows, target_url)
    else:
        add_row(
            rows,
            "supabase_backup_readiness",
            "skipped",
            "Not requested. Use --supabase-backup or --all-safe.",
            requested=False,
            proof_report="reports/supabase_backup_readiness.md",
            safe_class="management_api_read_no_data_changes",
        )

    add_row(
        rows,
        "hosted_write_audit_rehearsal",
        "skipped",
        "This runner will not approve write-audit rehearsal, run execute_hosted_write_audit_rehearsal.py, lift REMOTE_WRITE_LOCK, or perform test writes.",
        requested=False,
        proof_report="reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
        safe_class="requires_separate_owner_approval",
    )
    add_row(
        rows,
        "owner_signoffs",
        "skipped",
        "This runner will not sign monitoring cadence, owner shakedown, or source-of-truth cutover.",
        requested=False,
        proof_report="reports/remote_monitoring_signoff.md; reports/owner_shakedown_signoff.md",
        safe_class="requires_separate_owner_approval",
    )
    persist(rows, target_url)

    if run_any_refresh:
        run_refresh(rows, requested=True, target_url=target_url)
    else:
        add_row(
            rows,
            "readiness_report_refresh",
            "skipped",
            "Not requested. Use --refresh-only or --all-safe.",
            requested=False,
            proof_report="reports/remote_production_readiness.md",
            safe_class="report_refresh_only",
        )

    persist(rows, target_url)
    summary = summarize(rows, target_url)
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
