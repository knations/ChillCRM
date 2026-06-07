#!/usr/bin/env python3
"""Run the guarded Supabase staging refresh with private credential handling."""

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
DEFAULT_SSLROOTCERT = PROJECT_ROOT / "config" / "supabase-prod-ca-2021.crt"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def latest_backup_name() -> str:
    return backtick_value(read_text("reports/cutover_rollback_package_readiness.md"), "Latest backup")


def prompt_secret(env_name: str, label: str, *, prompt: bool) -> tuple[str, str]:
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
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=1800)


def compact_result(result: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(chunk for chunk in [result.stdout or "", result.stderr or ""] if chunk).strip()
    if not output:
        return f"exit_code={result.returncode}"
    try:
        payload = json.loads(output)
        clean = {key: payload.get(key) for key in payload if key not in {"password", "token", "secret", "database_url"}}
        return f"exit_code={result.returncode}; output={json.dumps(clean, sort_keys=True)}"
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        detail = lines[-1] if lines else ""
        detail = re.sub(r"\b(vcp_|vck_)[A-Za-z0-9._-]+", r"\1[redacted]", detail)
        detail = re.sub(r"(Bearer\s+)[A-Za-z0-9._-]+", r"\1[redacted]", detail, flags=re.IGNORECASE)
        db_url_pattern = r"postgres" + r"ql://\S+"
        detail = re.sub(db_url_pattern, "database-url-[redacted]", detail)
        detail = re.sub(r"eyJ[A-Za-z0-9._-]{40,}", "[redacted_jwt]", detail)
        return f"exit_code={result.returncode}; output={detail[:500]}"


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
        "# Supabase Staging Refresh Run",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the guarded Supabase staging refresh runner. It does not store database URLs, passwords, service-role keys, or tokens. It refreshes only Supabase staging when explicitly run with `--execute`.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Execution requested: {summary.get('execution_requested')}.",
        f"- Database URL source: {summary.get('database_url_source')}.",
        f"- SSL root cert: `{summary.get('ssl_root_cert') or 'missing'}`.",
        f"- Source backup/package note: `{summary.get('source_backup_name') or 'missing'}`.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
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
            "## Safe Execution",
            "",
            "```bash",
            ".venv/bin/python scripts/run_supabase_staging_refresh.py --execute --prompt-secrets",
            "```",
            "",
            "## Boundary",
            "",
            "- This runner resets only the Supabase `crm` schema through `scripts/migrate_chillcrm_to_supabase.py --reset-crm-schema`.",
            "- It does not unlock hosted writes or make hosted Supabase the source of truth.",
            "- Supply `CHILLCRM_DATABASE_URL` only through a private prompt or one-shot environment variable.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(
    rows: list[dict[str, Any]],
    *,
    execution_requested: bool,
    database_url_source: str,
    source_backup_name: str,
    ssl_root_cert: str,
    provider_calls: str,
    refresh_current: bool = False,
) -> dict[str, Any]:
    steps = [row for row in rows if row["row_type"] == "step"]
    failed = [row for row in steps if row["status"] == "failed"]
    input_required = [row for row in steps if row["status"] == "input_required"]
    passed = [row for row in steps if row["status"] == "passed"]
    if failed:
        status = "supabase_staging_refresh_failed"
        production_gate = "blocked_until_current_local_data_reloaded_to_supabase"
    elif input_required:
        status = "input_required_supabase_staging_refresh_execution"
        production_gate = "blocked_until_current_local_data_reloaded_to_supabase"
    elif refresh_current:
        status = "supabase_staging_refresh_current"
        production_gate = "pass"
    elif execution_requested:
        status = "supabase_staging_refresh_completed"
        production_gate = "pass"
    else:
        status = "supabase_staging_refresh_ready_for_execution"
        production_gate = "blocked_until_current_local_data_reloaded_to_supabase"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": production_gate,
        "execution_requested": "yes" if execution_requested else "no",
        "database_url_source": database_url_source,
        "source_backup_name": source_backup_name,
        "ssl_root_cert": ssl_root_cert,
        "passed": len(passed),
        "failed": len(failed),
        "input_required": len(input_required),
        "provider_calls": provider_calls,
        "crm_record_writes": "remote_staging_reload_only" if execution_requested and not failed and not input_required else "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    rows_with_summary = [summary, *steps]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "supabase_staging_refresh_run.csv", rows_with_summary)
    write_report(REPORTS_DIR / "supabase_staging_refresh_run.md", rows_with_summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Supabase staging from the current local CHILLCRM source.")
    parser.add_argument("--execute", action="store_true", help="Required to reload Supabase staging.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt privately for CHILLCRM_DATABASE_URL if missing.")
    parser.add_argument("--source-backup-name", default=latest_backup_name())
    parser.add_argument("--ssl-root-cert", default=str(DEFAULT_SSLROOTCERT))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    preflight = run_child("verify_supabase_staging_refresh_preflight.py", [])
    add_step(rows, "refresh_preflight", "passed" if preflight.returncode == 0 else "failed", compact_result(preflight))
    try:
        preflight_payload = json.loads((preflight.stdout or "{}").strip())
    except json.JSONDecodeError:
        preflight_payload = {}
    refresh_required = str(preflight_payload.get("refresh_required") or "").strip().lower()
    if preflight.returncode != 0:
        summary = persist(
            rows,
            execution_requested=args.execute,
            database_url_source="not_requested",
            source_backup_name=args.source_backup_name,
            ssl_root_cert=args.ssl_root_cert,
            provider_calls="no",
        )
        print(json.dumps(summary, indent=2))
        return 1

    if not args.execute:
        if refresh_required == "no":
            add_step(rows, "execution_request", "passed", "No staging reload required; Supabase staging parity is current.")
            summary = persist(
                rows,
                execution_requested=False,
                database_url_source="not_requested",
                source_backup_name=args.source_backup_name,
                ssl_root_cert=args.ssl_root_cert,
                provider_calls="no",
                refresh_current=True,
            )
            print(json.dumps(summary, indent=2))
            return 0
        add_step(rows, "execution_request", "input_required", "Run with --execute --prompt-secrets when ready to reload Supabase staging.")
        summary = persist(
            rows,
            execution_requested=False,
            database_url_source="not_requested",
            source_backup_name=args.source_backup_name,
            ssl_root_cert=args.ssl_root_cert,
            provider_calls="no",
        )
        print(json.dumps(summary, indent=2))
        return 0

    database_url, database_url_source = prompt_secret("CHILLCRM_DATABASE_URL", "Supabase database URL", prompt=args.prompt_secrets)
    if not database_url:
        add_step(rows, "database_url", "input_required", "Missing CHILLCRM_DATABASE_URL. Use --prompt-secrets or a one-shot environment variable.")
        summary = persist(
            rows,
            execution_requested=True,
            database_url_source="missing",
            source_backup_name=args.source_backup_name,
            ssl_root_cert=args.ssl_root_cert,
            provider_calls="no",
        )
        print(json.dumps(summary, indent=2))
        return 1

    add_step(rows, "database_url", "passed", f"Database URL source={database_url_source}; value not stored.")
    migration = run_child(
        "migrate_chillcrm_to_supabase.py",
        ["--reset-crm-schema", "--source-backup-name", args.source_backup_name],
        {"CHILLCRM_DATABASE_URL": database_url, "CHILLCRM_SSLROOTCERT": args.ssl_root_cert},
    )
    add_step(rows, "staging_reload", "passed" if migration.returncode == 0 else "failed", compact_result(migration))
    if migration.returncode == 0:
        parity = run_child("verify_supabase_staging_data_parity.py", [])
        add_step(rows, "staging_parity", "passed" if parity.returncode == 0 else "failed", compact_result(parity))
        readiness = run_child("verify_remote_production_readiness.py", [])
        add_step(rows, "production_readiness_refresh", "passed" if readiness.returncode == 0 else "failed", compact_result(readiness))
        owner_wave = run_child("prepare_owner_approved_wave_packet.py", [])
        add_step(rows, "owner_wave_refresh", "passed" if owner_wave.returncode == 0 else "failed", compact_result(owner_wave))
        remaining = run_child("prepare_remaining_production_gate_packet.py", [])
        add_step(rows, "remaining_packet_refresh", "passed" if remaining.returncode == 0 else "failed", compact_result(remaining))

    summary = persist(
        rows,
        execution_requested=True,
        database_url_source=database_url_source,
        source_backup_name=args.source_backup_name,
        ssl_root_cert=args.ssl_root_cert,
        provider_calls="yes_staging_database_reload",
    )
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] or summary["input_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
