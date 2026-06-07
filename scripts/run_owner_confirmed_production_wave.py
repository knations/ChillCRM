#!/usr/bin/env python3
"""Coordinate owner-confirmed production steps without storing secrets."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_OWNER_EMAIL = "kevinnations@gmail.com"
DEFAULT_PROJECT_REF = "ckjbnummsxqcyeahzynz"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def env_or_prompt(env_name: str, label: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def run_child(script_name: str, args: list[str], env_updates: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_updates:
        env.update(env_updates)
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache")
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=2400)


def compact_result(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        return f"exit_code={result.returncode}"
    try:
        payload = json.loads(text)
        clean = {
            key: payload.get(key)
            for key in payload
            if key not in {"password", "token", "secret", "database_url", "access_token"}
        }
        return f"exit_code={result.returncode}; output={json.dumps(clean, sort_keys=True)}"
    except json.JSONDecodeError:
        return f"exit_code={result.returncode}; output={text.splitlines()[0][:240]}"


def add_phase(
    rows: list[dict[str, Any]],
    *,
    order: int,
    phase: str,
    status: str,
    evidence: str,
    execution_requested: bool,
    provider_calls: str = "no",
    crm_record_writes: str = "no",
    proof_report: str = "",
    safe_command: str = "",
) -> None:
    rows.append(
        {
            "row_type": "phase",
            "order": order,
            "phase": phase,
            "status": status,
            "execution_requested": "yes" if execution_requested else "no",
            "provider_calls": provider_calls,
            "crm_record_writes": crm_record_writes,
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
            "evidence": " ".join(str(evidence).split()),
            "proof_report": proof_report,
            "safe_command": safe_command,
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


def summarize(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    phases = [row for row in rows if row["row_type"] == "phase"]
    failed = [row for row in phases if row.get("status") == "failed"]
    input_required = [row for row in phases if row.get("status") == "input_required"]
    executed = [row for row in phases if row.get("execution_requested") == "yes"]
    if failed:
        status = "owner_confirmed_wave_failed"
    elif input_required and executed:
        status = "input_required_owner_confirmed_wave"
    elif executed:
        status = "owner_confirmed_wave_completed_selected_steps"
    else:
        status = "owner_confirmed_wave_plan_ready"
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if not failed else "blocked_until_owner_confirmed_wave_fixed",
        "owner_confirmed_access": "yes" if args.owner_confirmed_access else "no",
        "owner_recovery_wave_requested": "yes" if args.execute_owner_recovery_wave else "no",
        "supabase_staging_refresh_requested": "yes" if args.execute_supabase_staging_refresh else "no",
        "supabase_backup_api_requested": "yes" if args.verify_supabase_backup_api else "no",
        "executed_phases": len(executed),
        "passed": sum(1 for row in phases if row.get("status") in {"passed", "ready", "skipped"}),
        "failed": len(failed),
        "input_required": len(input_required),
        "provider_calls": "yes_selected_provider_steps" if executed else "no",
        "crm_record_writes": "remote_staging_reload_only" if args.execute_supabase_staging_refresh and not failed else "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    phases = [row for row in rows if row["row_type"] == "phase"]
    lines = [
        "# Owner-Confirmed Production Wave Runner",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report coordinates the next owner-confirmed CHILLCRM production steps. Dry-run mode is report-only. Execution mode requires explicit flags and hidden prompts; it does not store passwords, tokens, database URLs, bypass secrets, service-role keys, or credential fragments.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Owner confirmed access: {summary.get('owner_confirmed_access')}.",
        f"- Owner recovery wave requested: {summary.get('owner_recovery_wave_requested')}.",
        f"- Supabase staging refresh requested: {summary.get('supabase_staging_refresh_requested')}.",
        f"- Supabase backup API requested: {summary.get('supabase_backup_api_requested')}.",
        f"- Executed phases: {summary.get('executed_phases')}.",
        f"- Passed/ready/skipped: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        "",
        "## Phases",
        "",
        "| Order | Phase | Status | Execution Requested | Evidence | Proof Report |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(phases, key=lambda item: int(item.get("order") or 0)):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("order")),
                    str(row.get("phase")),
                    str(row.get("status")),
                    str(row.get("execution_requested")),
                    str(row.get("evidence", "")).replace("|", "/"),
                    str(row.get("proof_report", "")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safe Commands",
            "",
            "Owner recovery disable, redeploy, hosted smoke, and safe refresh after owner access is confirmed:",
            "",
            "```bash",
            ".venv/bin/python scripts/run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets",
            "```",
            "",
            "Supabase staging refresh and backup visibility, still without write unlock or source-of-truth cutover:",
            "",
            "```bash",
            ".venv/bin/python scripts/run_owner_confirmed_production_wave.py --execute-supabase-staging-refresh --verify-supabase-backup-api --prompt-secrets",
            "```",
            "",
            "## Boundary",
            "",
            "- This runner does not approve or execute the hosted write-audit rehearsal.",
            "- This runner does not sign monitoring readiness, owner shakedown, or source-of-truth cutover.",
            "- This runner does not change `REMOTE_WRITE_LOCK` and cannot declare hosted Supabase/Vercel as source of truth.",
            "- If Supabase staging refresh is executed, it reloads only the staging `crm` schema through the existing guarded staging-refresh script.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_status(relative_path: str, label: str = "Status") -> str:
    return plain_value(read_text(relative_path), label)


def build_plan_rows(rows: list[dict[str, Any]]) -> None:
    owner_wave_status = report_status("reports/owner_approved_wave_packet.md")
    preflight_status = report_status("reports/hosted_redeploy_preflight.md")
    preflight_gate = report_status("reports/hosted_redeploy_preflight.md", "Preflight gate")
    staging_preflight_status = report_status("reports/supabase_staging_refresh_preflight.md")
    staging_preflight_gate = report_status("reports/supabase_staging_refresh_preflight.md", "Preflight gate")
    private_input_status = report_status("reports/private_execution_inputs.md")
    production_status = report_status("reports/remote_production_readiness.md")
    blocking_gates = plain_value(read_text("reports/remote_production_readiness.md"), "Blocking gates remaining")

    add_phase(
        rows,
        order=1,
        phase="current_private_input_map",
        status="ready" if private_input_status == "private_execution_inputs_mapped" else "input_required",
        execution_requested=False,
        evidence=f"private_input_status={private_input_status or 'missing'}",
        proof_report="reports/private_execution_inputs.md",
        safe_command="scripts/verify_private_execution_inputs.py",
    )
    add_phase(
        rows,
        order=2,
        phase="owner_recovery_disable_and_redeploy",
        status="ready" if owner_wave_status == "owner_approved_wave_ready_for_confirmation" else "input_required",
        execution_requested=False,
        evidence=f"owner_wave_status={owner_wave_status or 'missing'}",
        proof_report="reports/owner_approved_wave_packet.md; reports/owner_recovery_disable_run.md",
        safe_command="scripts/run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets",
    )
    add_phase(
        rows,
        order=3,
        phase="hosted_redeploy_preflight",
        status="ready" if preflight_status == "hosted_redeploy_preflight_ready" and preflight_gate == "pass" else "input_required",
        execution_requested=False,
        evidence=f"preflight_status={preflight_status or 'missing'}, preflight_gate={preflight_gate or 'missing'}",
        proof_report="reports/hosted_redeploy_preflight.md",
        safe_command="scripts/verify_hosted_redeploy_preflight.py",
    )
    add_phase(
        rows,
        order=4,
        phase="supabase_staging_refresh",
        status="ready" if staging_preflight_status == "supabase_staging_refresh_preflight_ready" and staging_preflight_gate == "pass" else "input_required",
        execution_requested=False,
        evidence=f"staging_preflight_status={staging_preflight_status or 'missing'}, staging_preflight_gate={staging_preflight_gate or 'missing'}",
        proof_report="reports/supabase_staging_refresh_preflight.md; reports/supabase_staging_refresh_run.md",
        safe_command="scripts/run_owner_confirmed_production_wave.py --execute-supabase-staging-refresh --prompt-secrets",
    )
    add_phase(
        rows,
        order=5,
        phase="supabase_backup_visibility",
        status="ready_with_token_or_dashboard_evidence",
        execution_requested=False,
        evidence="Use Supabase Management API token through hidden prompt, or owner-confirmed Dashboard evidence plus rollback proof.",
        proof_report="reports/supabase_backup_readiness.md; reports/supabase_backup_evidence_packet.md",
        safe_command="scripts/run_owner_confirmed_production_wave.py --verify-supabase-backup-api --prompt-secrets",
    )
    add_phase(
        rows,
        order=6,
        phase="production_readiness_snapshot",
        status="ready" if production_status == "blocked_until_production_gates_pass" else "input_required",
        execution_requested=False,
        evidence=f"production_status={production_status or 'missing'}, blocking_gates={blocking_gates or 'missing'}",
        proof_report="reports/remote_production_readiness.md",
        safe_command="scripts/run_safe_production_gate_checks.py --refresh-only",
    )


def execute_owner_recovery_wave(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    if not args.owner_confirmed_access:
        add_phase(
            rows,
            order=20,
            phase="execute_owner_recovery_wave",
            status="input_required",
            execution_requested=True,
            evidence="Missing --owner-confirmed-access; owner must confirm hosted sign-in before recovery is disabled.",
            proof_report="reports/owner_recovery_disable_run.md",
        )
        return
    vercel_token, token_source = env_or_prompt("VERCEL_TOKEN", "Vercel token", prompt=args.prompt_secrets)
    owner_password, password_source = env_or_prompt(
        "AUTH_BOOTSTRAP_ADMIN_PASSWORD", "Owner password", prompt=args.prompt_secrets
    )
    if not vercel_token or not owner_password:
        add_phase(
            rows,
            order=20,
            phase="execute_owner_recovery_wave",
            status="input_required",
            execution_requested=True,
            evidence=f"Missing {'VERCEL_TOKEN' if not vercel_token else ''} {'AUTH_BOOTSTRAP_ADMIN_PASSWORD' if not owner_password else ''}. Use --prompt-secrets or one-shot env values.",
            proof_report="reports/owner_recovery_disable_run.md",
        )
        return
    result = run_child(
        "disable_owner_recovery_after_access.py",
        ["--owner-confirmed-access", "--owner-email", args.owner_email],
        {
            "VERCEL_TOKEN": vercel_token,
            "AUTH_BOOTSTRAP_ADMIN_PASSWORD": owner_password,
            "CHILLCRM_VERCEL_INLINE_FILES": os.environ.get("CHILLCRM_VERCEL_INLINE_FILES", "1"),
        },
    )
    add_phase(
        rows,
        order=20,
        phase="execute_owner_recovery_wave",
        status="passed" if result.returncode == 0 else "failed",
        execution_requested=True,
        provider_calls="yes",
        evidence=f"{compact_result(result)}; token_source={token_source}; password_source={password_source}",
        proof_report="reports/owner_recovery_disable_run.md; reports/vercel_hosted_app_smoke.md; reports/remote_production_readiness.md",
    )


def execute_supabase_staging_refresh(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    database_url, database_source = env_or_prompt(
        "CHILLCRM_DATABASE_URL", "Supabase database URL", prompt=args.prompt_secrets
    )
    if not database_url:
        add_phase(
            rows,
            order=30,
            phase="execute_supabase_staging_refresh",
            status="input_required",
            execution_requested=True,
            evidence="Missing CHILLCRM_DATABASE_URL. Use --prompt-secrets or a one-shot environment variable.",
            proof_report="reports/supabase_staging_refresh_run.md",
        )
        return
    result = run_child(
        "run_supabase_staging_refresh.py",
        ["--execute"],
        {"CHILLCRM_DATABASE_URL": database_url},
    )
    add_phase(
        rows,
        order=30,
        phase="execute_supabase_staging_refresh",
        status="passed" if result.returncode == 0 else "failed",
        execution_requested=True,
        provider_calls="yes",
        crm_record_writes="remote_staging_reload_only",
        evidence=f"{compact_result(result)}; database_url_source={database_source}",
        proof_report="reports/supabase_staging_refresh_run.md; reports/supabase_staging_data_parity.md",
    )


def execute_supabase_backup_api(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    access_token, token_source = env_or_prompt(
        "SUPABASE_ACCESS_TOKEN", "Supabase Management API access token", prompt=args.prompt_secrets
    )
    if not access_token:
        add_phase(
            rows,
            order=40,
            phase="verify_supabase_backup_api",
            status="input_required",
            execution_requested=True,
            evidence="Missing SUPABASE_ACCESS_TOKEN. Use --prompt-secrets, one-shot env value, or Dashboard evidence path.",
            proof_report="reports/supabase_backup_readiness.md",
        )
        return
    result = run_child(
        "verify_supabase_backup_readiness.py",
        ["--project-ref", args.project_ref],
        {"SUPABASE_ACCESS_TOKEN": access_token},
    )
    add_phase(
        rows,
        order=40,
        phase="verify_supabase_backup_api",
        status="passed" if result.returncode == 0 else "failed",
        execution_requested=True,
        provider_calls="yes",
        evidence=f"{compact_result(result)}; token_source={token_source}",
        proof_report="reports/supabase_backup_readiness.md",
    )


def refresh_after_execution(rows: list[dict[str, Any]]) -> None:
    result = run_child("run_safe_production_gate_checks.py", ["--refresh-only"], {})
    add_phase(
        rows,
        order=90,
        phase="refresh_safe_production_reports",
        status="passed" if result.returncode == 0 else "failed",
        execution_requested=True,
        evidence=compact_result(result),
        proof_report="reports/safe_production_gate_runner.md; reports/remote_production_readiness.md",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Coordinate owner-confirmed CHILLCRM production steps with private credential handling."
    )
    parser.add_argument("--owner-confirmed-access", action="store_true", help="Owner confirms they can sign in before temporary recovery is disabled.")
    parser.add_argument("--execute-owner-recovery-wave", action="store_true", help="Disable temporary owner recovery, redeploy, smoke, and refresh reports.")
    parser.add_argument("--execute-supabase-staging-refresh", action="store_true", help="Reload current local data into Supabase staging through the guarded staging-refresh script.")
    parser.add_argument("--verify-supabase-backup-api", action="store_true", help="Verify Supabase backup visibility using a Management API token.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt for missing secrets without echoing them.")
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", DEFAULT_OWNER_EMAIL))
    parser.add_argument("--project-ref", default=os.environ.get("SUPABASE_PROJECT_REF", DEFAULT_PROJECT_REF))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    build_plan_rows(rows)

    executed_any = False
    if args.execute_owner_recovery_wave:
        executed_any = True
        execute_owner_recovery_wave(rows, args)
    if args.execute_supabase_staging_refresh:
        executed_any = True
        execute_supabase_staging_refresh(rows, args)
    if args.verify_supabase_backup_api:
        executed_any = True
        execute_supabase_backup_api(rows, args)
    if executed_any:
        refresh_after_execution(rows)

    REPORTS_DIR.mkdir(exist_ok=True)
    rows_with_summary = [summarize(rows, args), *rows]
    write_csv(REPORTS_DIR / "owner_confirmed_production_wave.csv", rows_with_summary)
    write_report(REPORTS_DIR / "owner_confirmed_production_wave.md", rows_with_summary)
    print(json.dumps(rows_with_summary[0], indent=2))
    return 1 if rows_with_summary[0]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
