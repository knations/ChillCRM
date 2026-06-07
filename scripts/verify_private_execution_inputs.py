#!/usr/bin/env python3
"""Map private execution inputs for remaining production gates without storing secrets."""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def env_present(name: str) -> str:
    return "yes" if os.environ.get(name, "").strip() else "no"


def has_any_env(names: list[str]) -> bool:
    return any(os.environ.get(name, "").strip() for name in names)


def env_group_present(names: list[str]) -> str:
    return "yes" if names and all(env_present(name) == "yes" for name in names) else "no"


def add_row(
    rows: list[dict[str, Any]],
    *,
    order: int,
    key: str,
    gate: str,
    status: str,
    secret_inputs: list[str],
    non_secret_inputs: list[str],
    evidence: str,
    safe_command: str,
    proof_report: str,
    secret_inputs_present: str | None = None,
    prompt_available: str = "yes",
    owner_input_required: str = "no",
) -> None:
    secret_presence = secret_inputs_present
    if secret_presence is None:
        secret_presence = env_group_present(secret_inputs) if secret_inputs else "not_required"
    rows.append(
        {
            "row_type": "input",
            "order": order,
            "key": key,
            "gate": gate,
            "status": status,
            "secret_inputs": ", ".join(secret_inputs) or "none",
            "secret_inputs_present": secret_presence,
            "prompt_available": prompt_available,
            "owner_input_required": owner_input_required,
            "non_secret_inputs": ", ".join(non_secret_inputs) or "none",
            "evidence": " ".join(str(evidence).split()),
            "safe_command": safe_command,
            "proof_report": proof_report,
            "secret_values_stored": "no",
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
    inputs = [row for row in rows if row["row_type"] == "input"]
    env_rows = [row for row in rows if row["row_type"] == "env_presence"]
    lines = [
        "# Private Execution Inputs",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report maps which private inputs are needed for the remaining CHILLCRM Supabase/Vercel production actions. It records only whether inputs are present or still needed. It never stores Vercel tokens, owner passwords, database URLs, Supabase tokens, bypass secrets, service-role keys, or credential fragments.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Private execution groups ready now: {summary.get('ready_groups')}.",
        f"- Private execution groups waiting: {summary.get('waiting_groups')}.",
        f"- Env-ready secret groups: {summary.get('env_ready')}.",
        f"- Hidden-prompt-capable groups: {summary.get('prompt_available')}.",
        f"- Owner-input-required groups: {summary.get('owner_input_required_groups')}.",
        f"- Owner confirmation required: {summary.get('owner_confirmation_required')}.",
        f"- Secret env values present: {summary.get('secret_env_values_present')}.",
        "- Provider calls: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Input Map",
        "",
        "| Order | Gate | Status | Secret Inputs | Present | Prompt | Owner Input | Non-Secret Inputs | Evidence | Proof Report |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in inputs:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("order")),
                    str(row.get("gate", "")).replace("|", "/"),
                    str(row.get("status")),
                    str(row.get("secret_inputs")),
                    str(row.get("secret_inputs_present")),
                    str(row.get("prompt_available")),
                    str(row.get("owner_input_required")),
                    str(row.get("non_secret_inputs")),
                    str(row.get("evidence", "")).replace("|", "/"),
                    str(row.get("proof_report")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Secret Environment Presence",
            "",
            "| Name | Present | Used By |",
            "| --- | --- | --- |",
        ]
    )
    for row in env_rows:
        lines.append(f"| `{row.get('name')}` | {row.get('present')} | {row.get('used_by')} |")
    lines.extend(
        [
            "",
            "## Safe Use",
            "",
            "- Use hidden prompts where possible instead of shell environment variables.",
            "- If a one-shot environment variable is used, set it only for that command invocation and do not save it to files.",
            "- Owner approvals and Dashboard facts are non-secret, but they still must be recorded by their guarded scripts before a gate can pass.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    owner_disable = read_text("reports/owner_recovery_disable_run.md")
    owner_confirmed = plain_value(owner_disable, "Owner confirmed access") == "yes"

    vercel_token_present = env_present("VERCEL_TOKEN")
    owner_password_present = env_present("AUTH_BOOTSTRAP_ADMIN_PASSWORD")
    hosted_smoke_owner_password_present = "yes" if has_any_env(["AUTH_BOOTSTRAP_ADMIN_PASSWORD", "CHILLCRM_OWNER_RECOVERY_PASSWORD"]) else "no"
    vercel_database_url_present = env_present("CHILLCRM_VERCEL_DATABASE_URL")
    supabase_database_url_present = env_present("CHILLCRM_DATABASE_URL")
    supabase_access_token_present = env_present("SUPABASE_ACCESS_TOKEN")
    vercel_bypass_secret_present = env_present("VERCEL_PROTECTION_BYPASS_SECRET")

    rows: list[dict[str, Any]] = []
    env_defs = [
        ("VERCEL_TOKEN", vercel_token_present, "Vercel deploys, protection bypass lookup, hosted smoke, write-audit execution"),
        ("AUTH_BOOTSTRAP_ADMIN_PASSWORD", env_present("AUTH_BOOTSTRAP_ADMIN_PASSWORD"), "Owner login for hosted smoke and recovery-disable verification"),
        ("CHILLCRM_OWNER_RECOVERY_PASSWORD", env_present("CHILLCRM_OWNER_RECOVERY_PASSWORD"), "Owner recovery smoke path when explicitly enabled"),
        ("CHILLCRM_VERCEL_DATABASE_URL", vercel_database_url_present, "Deploy-time Vercel DATABASE_URL env upsert when full provider env refresh is needed"),
        ("VERCEL_PROTECTION_BYPASS_SECRET", vercel_bypass_secret_present, "Optional hosted smoke bypass; VERCEL_TOKEN can read it in memory when absent"),
        ("CHILLCRM_DATABASE_URL", supabase_database_url_present, "Supabase staging refresh execution"),
        ("SUPABASE_ACCESS_TOKEN", supabase_access_token_present, "Supabase backup/PITR Management API visibility"),
    ]
    for name, present, used_by in env_defs:
        rows.append(
            {
                "row_type": "env_presence",
                "name": name,
                "present": present,
                "used_by": used_by,
                "secret_values_stored": "no",
            }
        )

    owner_recovery_ready = owner_confirmed and vercel_token_present == "yes" and owner_password_present == "yes"
    redeploy_ready = vercel_token_present == "yes" and hosted_smoke_owner_password_present == "yes"
    staging_refresh_ready = supabase_database_url_present == "yes"
    backup_api_ready = supabase_access_token_present == "yes"
    write_audit_secret_ready = vercel_token_present == "yes" and owner_password_present == "yes"

    add_row(
        rows,
        order=1,
        key="owner_recovery_disable",
        gate="Owner recovery switch disabled",
        status="ready" if owner_recovery_ready else "input_required",
        secret_inputs=["VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD"],
        non_secret_inputs=["Owner confirms access restored"],
        evidence=f"owner_confirmed={'yes' if owner_confirmed else 'no'}, vercel_token={vercel_token_present}, owner_password={owner_password_present}",
        safe_command="scripts/disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets",
        proof_report="reports/owner_recovery_disable_run.md; reports/owner_recovery_closure.md",
        secret_inputs_present=env_group_present(["VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD"]),
        owner_input_required="no" if owner_confirmed else "yes",
    )
    add_row(
        rows,
        order=2,
        key="hosted_redeploy_and_smoke",
        gate="Hosted deployment matches local runtime",
        status="ready" if redeploy_ready else "input_required",
        secret_inputs=["VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD or CHILLCRM_OWNER_RECOVERY_PASSWORD", "optional VERCEL_PROTECTION_BYPASS_SECRET", "optional CHILLCRM_VERCEL_DATABASE_URL for full env upsert"],
        non_secret_inputs=["Owner confirmation if recovery-disable wave is also being run"],
        evidence=f"vercel_token={vercel_token_present}, owner_password_or_recovery={hosted_smoke_owner_password_present}, vercel_database_url={vercel_database_url_present}; Vercel protection bypass can be read in memory with VERCEL_TOKEN.",
        safe_command="scripts/deploy_chillcrm_to_vercel.py; scripts/run_newest_hosted_smoke_with_vercel_bypass.py",
        proof_report="reports/hosted_redeploy_preflight.md; reports/hosted_deployment_freshness.md; reports/vercel_hosted_app_smoke.md",
        secret_inputs_present="yes" if redeploy_ready else "no",
    )
    add_row(
        rows,
        order=3,
        key="supabase_staging_refresh",
        gate="Supabase staging data parity",
        status="ready" if staging_refresh_ready else "input_required",
        secret_inputs=["CHILLCRM_DATABASE_URL"],
        non_secret_inputs=["Supabase staging refresh approval"],
        evidence=f"database_url={supabase_database_url_present}",
        safe_command="scripts/run_supabase_staging_refresh.py --execute --prompt-secrets",
        proof_report="reports/supabase_staging_refresh_run.md; reports/supabase_staging_data_parity.md",
        secret_inputs_present=supabase_database_url_present,
    )
    add_row(
        rows,
        order=4,
        key="supabase_backup_visibility",
        gate="Supabase provider backup/PITR visibility",
        status="ready" if backup_api_ready else "dashboard_or_token_input_required",
        secret_inputs=["SUPABASE_ACCESS_TOKEN"],
        non_secret_inputs=["Alternative: owner-confirmed Supabase Dashboard backup/PITR facts plus rollback proof approval"],
        evidence=f"supabase_access_token={supabase_access_token_present}; dashboard evidence path remains available without token.",
        safe_command="scripts/verify_supabase_backup_readiness.py",
        proof_report="reports/supabase_backup_readiness.md; reports/supabase_backup_evidence_packet.md",
        secret_inputs_present=supabase_access_token_present,
        owner_input_required="yes",
    )
    add_row(
        rows,
        order=5,
        key="hosted_write_audit_execution",
        gate="Hosted write-unlock actor-audit rehearsal",
        status="ready_after_owner_approval" if write_audit_secret_ready else "input_required",
        secret_inputs=["VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD"],
        non_secret_inputs=["Explicit owner approval for one staging write-audit rehearsal"],
        evidence=f"vercel_token={vercel_token_present}, owner_password={owner_password_present}; owner approval is still required before any write-lock change.",
        safe_command="scripts/execute_hosted_write_audit_rehearsal.py --owner-approved --execute --prompt-secrets",
        proof_report="reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
        secret_inputs_present=env_group_present(["VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD"]),
        owner_input_required="yes",
    )
    add_row(
        rows,
        order=6,
        key="monitoring_signoff",
        gate="Remote monitoring readiness",
        status="owner_input_required",
        secret_inputs=[],
        non_secret_inputs=["Monitoring owner/cadence approval"],
        evidence="No secret input is required; record owner, cadence, backup, audit, file, export, and feedback monitoring signoff.",
        safe_command="scripts/record_remote_monitoring_signoff.py --approve-owner --approve-cadence --approve-feedback",
        proof_report="reports/remote_monitoring_signoff.md; reports/remote_monitoring_readiness.md",
        prompt_available="not_required",
        owner_input_required="yes",
    )
    add_row(
        rows,
        order=7,
        key="owner_shakedown_signoff",
        gate="Owner-only staging shakedown signoff",
        status="owner_input_required_after_prerequisites",
        secret_inputs=[],
        non_secret_inputs=["Owner shakedown signoff after backup, smoke, write-audit, and monitoring gates pass"],
        evidence="No secret input is required; this gate should be recorded after prerequisite gates pass.",
        safe_command="scripts/record_owner_shakedown_signoff.py --approve",
        proof_report="reports/owner_shakedown_signoff.md",
        prompt_available="not_required",
        owner_input_required="yes",
    )
    add_row(
        rows,
        order=8,
        key="source_of_truth_cutover_approval",
        gate="Owner source-of-truth cutover approval",
        status="owner_input_required_last",
        secret_inputs=[],
        non_secret_inputs=["Final owner approval, support window, rollback posture"],
        evidence="No secret input is required; this remains the final gate after all other production blockers pass.",
        safe_command="scripts/record_source_of_truth_cutover_approval.py --approve-cutover",
        proof_report="reports/source_of_truth_cutover_approval.md",
        prompt_available="not_required",
        owner_input_required="yes",
    )

    input_rows = [row for row in rows if row["row_type"] == "input"]
    ready_groups = sum(1 for row in input_rows if str(row.get("status", "")).startswith("ready"))
    waiting_groups = len(input_rows) - ready_groups
    env_ready = sum(1 for row in input_rows if row.get("secret_inputs_present") in {"yes", "not_required"})
    prompt_available = sum(1 for row in input_rows if row.get("prompt_available") == "yes")
    owner_input_required_groups = sum(1 for row in input_rows if row.get("owner_input_required") == "yes")
    secret_env_values_present = sum(1 for _, present, _ in env_defs if present == "yes")
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "private_execution_inputs_mapped",
        "production_gate": "pass",
        "ready_groups": ready_groups,
        "waiting_groups": waiting_groups,
        "env_ready": env_ready,
        "prompt_available": prompt_available,
        "owner_input_required_groups": owner_input_required_groups,
        "owner_confirmation_required": "no" if owner_confirmed else "yes",
        "secret_env_values_present": secret_env_values_present,
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    rows_with_summary = [summary, *rows]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "private_execution_inputs.csv", rows_with_summary)
    write_report(REPORTS_DIR / "private_execution_inputs.md", rows_with_summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
