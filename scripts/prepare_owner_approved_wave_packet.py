#!/usr/bin/env python3
"""Prepare the owner-approved CHILLCRM production wave packet."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
OWNER_REPLY = "I'm in, disable recovery"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def backtick_value(text: str, label: str) -> str:
    value = plain_value(text, label)
    if value.startswith("`") and "`" in value[1:]:
        return value.split("`", 2)[1].strip()
    return ""


def int_value(value: str) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


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


def add_phase(
    rows: list[dict[str, Any]],
    order: int,
    phase: str,
    status: str,
    purpose: str,
    owner_input: str,
    secret_handling: str,
    command: str,
    proof_report: str,
    *,
    wave_class: str,
    crm_record_writes: str = "no",
    remote_write_lock_changed: str = "no",
    source_of_truth_changed: str = "no",
) -> None:
    rows.append(
        {
            "row_type": "phase",
            "order": order,
            "phase": phase,
            "status": status,
            "wave_class": wave_class,
            "purpose": " ".join(purpose.split()),
            "owner_input": owner_input,
            "secret_handling": secret_handling,
            "command": command,
            "proof_report": proof_report,
            "provider_calls_by_packet": "no",
            "crm_record_writes": crm_record_writes,
            "remote_write_lock_changed": remote_write_lock_changed,
            "source_of_truth_changed": source_of_truth_changed,
            "secret_values_stored": "no",
        }
    )


def status_for_owner_confirmation(owner_recovery_status: str, owner_recovery_gate: str) -> str:
    if owner_recovery_status == "owner_recovery_closed" and owner_recovery_gate == "pass":
        return "pass"
    return "input_required_owner_confirmation"


def status_for_disable_run(owner_recovery_status: str, owner_recovery_gate: str, disable_status: str) -> str:
    if owner_recovery_status == "owner_recovery_closed" and owner_recovery_gate == "pass":
        return "pass"
    if disable_status and disable_status not in {
        "input_required",
        "input_required_owner_confirmation",
        "pending_owner_confirmation",
    }:
        return disable_status
    return "ready_after_owner_confirmation"


def status_for_redeploy(preflight_status: str, preflight_gate: str, freshness_status: str) -> str:
    if freshness_status == "hosted_deployment_fresh":
        return "pass"
    if preflight_status == "hosted_redeploy_preflight_ready" and preflight_gate == "pass":
        return "ready_after_owner_confirmation"
    return "preflight_attention_required"


def build_rows() -> list[dict[str, Any]]:
    production = read_text("reports/remote_production_readiness.md")
    owner_recovery = read_text("reports/owner_recovery_closure.md")
    owner_disable = read_text("reports/owner_recovery_disable_run.md")
    redeploy = read_text("reports/hosted_redeploy_preflight.md")
    freshness = read_text("reports/hosted_deployment_freshness.md")
    staging_parity = read_text("reports/supabase_staging_data_parity.md")
    staging_refresh_preflight = read_text("reports/supabase_staging_refresh_preflight.md")
    staging_refresh_run = read_text("reports/supabase_staging_refresh_run.md")
    remaining_packet = read_text("reports/remaining_production_gates_packet.md")
    deployment = read_text("reports/vercel_staging_deployment_status.md")

    latest_url = backtick_value(production, "Latest URL") or backtick_value(deployment, "URL")
    latest_deployment = backtick_value(production, "Latest deployment") or backtick_value(redeploy, "Latest deployment")
    owner_recovery_status = plain_value(owner_recovery, "Status")
    owner_recovery_gate = plain_value(owner_recovery, "Production gate")
    owner_recovery_switch = plain_value(owner_recovery, "Owner recovery switch")
    owner_disable_status = plain_value(owner_disable, "Status")
    preflight_status = plain_value(redeploy, "Status")
    preflight_gate = plain_value(redeploy, "Preflight gate")
    redeploy_required = plain_value(redeploy, "Redeploy required")
    freshness_status = plain_value(freshness, "Status")
    freshness_gate = plain_value(freshness, "Production gate")
    changed_runtime_files = int_value(plain_value(freshness, "Changed runtime files"))
    staging_parity_status = plain_value(staging_parity, "Status")
    staging_parity_gate = plain_value(staging_parity, "Production gate")
    staging_parity_table_failures = int_value(plain_value(staging_parity, "Table failures"))
    staging_refresh_preflight_status = plain_value(staging_refresh_preflight, "Status")
    staging_refresh_preflight_gate = plain_value(staging_refresh_preflight, "Preflight gate")
    staging_refresh_run_status = plain_value(staging_refresh_run, "Status")
    staging_refresh_run_gate = plain_value(staging_refresh_run, "Production gate")
    production_status = plain_value(production, "Status")
    production_gate = plain_value(production, "Production gate")
    production_passed = int_value(plain_value(production, "Passing gates"))
    production_failed = int_value(plain_value(production, "Failed gates"))
    production_input_required = int_value(plain_value(production, "Input-required gates"))
    production_blocking = int_value(plain_value(production, "Blocking gates remaining"))
    remaining_has_owner_disable = "disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets" in remaining_packet
    remaining_has_redeploy = "verify_hosted_redeploy_preflight.py" in remaining_packet and "run_newest_hosted_smoke_with_vercel_bypass.py" in remaining_packet

    owner_ready = owner_recovery_status in {
        "input_required_owner_recovery_disable",
        "owner_recovery_closed",
    }
    redeploy_ready = preflight_status == "hosted_redeploy_preflight_ready" and preflight_gate == "pass"
    if owner_ready and redeploy_ready and remaining_has_owner_disable and remaining_has_redeploy:
        packet_status = "owner_approved_wave_ready_for_confirmation"
    else:
        packet_status = "owner_approved_wave_attention_required"

    summary: dict[str, Any] = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": packet_status,
        "owner_reply_required": OWNER_REPLY,
        "latest_deployment_id": latest_deployment,
        "latest_url": latest_url,
        "production_status": production_status,
        "production_gate": production_gate,
        "production_passed": production_passed,
        "production_failed": production_failed,
        "production_input_required": production_input_required,
        "production_blocking": production_blocking,
        "owner_recovery_status": owner_recovery_status,
        "owner_recovery_gate": owner_recovery_gate,
        "owner_recovery_switch": owner_recovery_switch,
        "owner_recovery_disable_run_status": owner_disable_status,
        "hosted_redeploy_preflight_status": preflight_status,
        "hosted_redeploy_preflight_gate": preflight_gate,
        "redeploy_required": redeploy_required,
        "deployment_freshness_status": freshness_status,
        "deployment_freshness_gate": freshness_gate,
        "changed_runtime_files": changed_runtime_files,
        "supabase_staging_data_parity_status": staging_parity_status,
        "supabase_staging_data_parity_gate": staging_parity_gate,
        "supabase_staging_table_failures": staging_parity_table_failures,
        "supabase_staging_refresh_preflight_status": staging_refresh_preflight_status,
        "supabase_staging_refresh_preflight_gate": staging_refresh_preflight_gate,
        "supabase_staging_refresh_run_status": staging_refresh_run_status,
        "supabase_staging_refresh_run_gate": staging_refresh_run_gate,
        "provider_calls": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
        "secret_values_required_for_packet": "no",
        "secret_values_stored": "no",
    }
    rows: list[dict[str, Any]] = [summary]

    add_phase(
        rows,
        1,
        "Owner access confirmation",
        status_for_owner_confirmation(owner_recovery_status, owner_recovery_gate),
        "Owner confirms they can sign in with their own private password before the temporary recovery switch is disabled.",
        OWNER_REPLY,
        "No password or token should be shared in chat, reports, source files, or docs.",
        "Reply in Codex only after successful sign-in: I'm in, disable recovery",
        "reports/owner_recovery_disable_run.md; reports/owner_recovery_closure.md",
        wave_class="owner_confirmation_required",
    )
    add_phase(
        rows,
        2,
        "Disable temporary owner recovery",
        status_for_disable_run(owner_recovery_status, owner_recovery_gate, owner_disable_status),
        "Redeploy with owner password recovery disabled, then rerun hosted smoke, freshness, owner recovery closure, and safe readiness refreshes.",
        "Owner access must already be confirmed.",
        "Vercel token, owner password, and protection bypass secret must be supplied through hidden prompts or one-shot environment variables only.",
        ".venv/bin/python scripts/disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets",
        "reports/owner_recovery_disable_run.md; reports/owner_recovery_closure.md; reports/vercel_hosted_app_smoke.md; reports/hosted_deployment_freshness.md",
        wave_class="owner_approved_secret_prompted_execution",
    )
    add_phase(
        rows,
        3,
        "Redeploy current hosted runtime",
        status_for_redeploy(preflight_status, preflight_gate, freshness_status),
        "If the recovery-disable redeploy does not also clear freshness, deploy the current local hosted runtime and rerun hosted smoke plus freshness verification.",
        "No new owner approval beyond the recovery-disable confirmation, unless the deploy evidence changes unexpectedly.",
        "Vercel token, owner password, and protection bypass secret must be supplied through hidden prompts or one-shot environment variables only.",
        ".venv/bin/python scripts/verify_hosted_redeploy_preflight.py\nCHILLCRM_SKIP_ENV_UPSERT=1 CHILLCRM_VERCEL_INLINE_FILES=1 .venv/bin/python scripts/deploy_chillcrm_to_vercel.py\n.venv/bin/python scripts/run_newest_hosted_smoke_with_vercel_bypass.py\n.venv/bin/python scripts/verify_hosted_deployment_freshness.py\n.venv/bin/python scripts/run_safe_production_gate_checks.py --refresh-only",
        "reports/hosted_redeploy_preflight.md; reports/hosted_deployment_freshness.md; reports/vercel_hosted_app_smoke.md; reports/safe_production_gate_runner.md",
        wave_class="operator_secret_prompted_execution",
    )
    add_phase(
        rows,
        4,
        "Refresh Supabase staging data parity",
        "pass" if staging_parity_status == "supabase_staging_data_parity_passed" and staging_parity_gate == "pass" else "separate_input_required",
        "Reload current local audit/data changes into Supabase staging so the remote staging copy matches the current local source before cutover review.",
        "No owner approval beyond normal migration/cutover control; operator needs private Supabase database connection details.",
        "Supabase database connection string must be supplied through a hidden prompt or one-shot environment variable only.",
        ".venv/bin/python scripts/verify_supabase_staging_refresh_preflight.py\n.venv/bin/python scripts/run_supabase_staging_refresh.py --execute --prompt-secrets",
        "reports/supabase_staging_refresh_run.md; reports/supabase_staging_refresh_preflight.md; reports/chillcrm_supabase_staging_validation.md; reports/supabase_staging_data_parity.md",
        wave_class="operator_secret_prompted_execution",
    )
    add_phase(
        rows,
        5,
        "Verify Supabase backup/PITR evidence",
        "separate_input_required",
        "Prove Supabase provider backup visibility and restore/rollback evidence through the Management API or owner-confirmed Dashboard evidence.",
        "Owner may provide Dashboard facts or approve use of a Supabase Management API token.",
        "Supabase Management API token, if used, must be supplied through a hidden prompt or one-shot environment variable only.",
        "SUPABASE_ACCESS_TOKEN=<supabase-management-token> .venv/bin/python scripts/verify_supabase_backup_readiness.py\n# or use the dashboard-evidence flags listed in reports/remaining_production_gates_packet.md",
        "reports/supabase_backup_readiness.md; reports/supabase_backup_evidence_packet.md",
        wave_class="remaining_separate_production_gate",
    )
    add_phase(
        rows,
        6,
        "Record monitoring signoff",
        "separate_input_required",
        "Record who owns monitoring cadence for health, errors, backup visibility, files, exports, and owner feedback.",
        "Owner approval for monitoring owner, cadence, and feedback loop.",
        "No secret value.",
        ".venv/bin/python scripts/record_remote_monitoring_signoff.py --signoff-owner \"Kevin Nations\" --approve-owner --approve-cadence --approve-feedback",
        "reports/remote_monitoring_signoff.md; reports/remote_monitoring_readiness.md",
        wave_class="remaining_separate_owner_approval",
    )
    add_phase(
        rows,
        7,
        "Approve and execute hosted write-audit rehearsal",
        "separate_input_required",
        "After explicit approval, temporarily lift the staging write lock, create one actor-audited probe record, restore the lock, and verify evidence.",
        "Explicit owner approval is required before any hosted write rehearsal.",
        "Vercel token, owner password, and protection bypass secret must be supplied through hidden prompts or one-shot environment variables only.",
        ".venv/bin/python scripts/prepare_hosted_write_audit_rehearsal.py --owner-approved\n.venv/bin/python scripts/execute_hosted_write_audit_rehearsal.py --owner-approved --execute --prompt-secrets",
        "reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
        wave_class="remaining_separate_owner_approval",
        crm_record_writes="yes_when_later_explicitly_approved_for_probe_only",
        remote_write_lock_changed="yes_when_later_explicitly_approved_then_restored",
    )
    add_phase(
        rows,
        8,
        "Owner shakedown and final cutover",
        "separate_input_required",
        "Owner signs off only after smoke, backup, monitoring, write-audit, and readiness gates are green, then separately approves source-of-truth cutover.",
        "Owner shakedown and final source-of-truth approval remain separate explicit decisions.",
        "No secret value.",
        ".venv/bin/python scripts/record_owner_shakedown_signoff.py --signoff-owner \"Kevin Nations\" --approve\n.venv/bin/python scripts/verify_source_of_truth_cutover_preflight.py\n.venv/bin/python scripts/record_source_of_truth_cutover_approval.py --approve-cutover --signoff-owner \"Kevin Nations\" --production-url <verified-production-url>",
        "reports/owner_shakedown_signoff.md; reports/source_of_truth_cutover_preflight.md; reports/source_of_truth_cutover_approval.md; reports/remote_production_readiness.md",
        wave_class="final_owner_cutover_approval",
        source_of_truth_changed="no_until_final_approval_recorded",
    )
    return rows


def command_lines(command: str) -> list[str]:
    return [line for line in command.split("\n") if line.strip()]


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    phases = [row for row in rows if row["row_type"] == "phase"]
    lines = [
        "# Owner Approved Wave Packet",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This packet prepares the next owner-approved CHILLCRM production wave. It does not call Supabase or Vercel, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Owner reply required: `{summary.get('owner_reply_required')}`.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Production readiness: {summary.get('production_status') or 'missing'} / gate {summary.get('production_gate') or 'missing'}.",
        f"- Production pass/fail/input: {summary.get('production_passed')} passed, {summary.get('production_failed')} failed, {summary.get('production_input_required')} input-required.",
        f"- Blocking gates: {summary.get('production_blocking')}.",
        f"- Owner recovery closure: {summary.get('owner_recovery_status') or 'missing'} / gate {summary.get('owner_recovery_gate') or 'missing'} / switch {summary.get('owner_recovery_switch') or 'missing'}.",
        f"- Owner recovery disable run: {summary.get('owner_recovery_disable_run_status') or 'missing'}.",
        f"- Hosted redeploy preflight: {summary.get('hosted_redeploy_preflight_status') or 'missing'} / gate {summary.get('hosted_redeploy_preflight_gate') or 'missing'}.",
        f"- Deployment freshness: {summary.get('deployment_freshness_status') or 'missing'} / gate {summary.get('deployment_freshness_gate') or 'missing'} / changed runtime files {summary.get('changed_runtime_files')}.",
        f"- Supabase staging data parity: {summary.get('supabase_staging_data_parity_status') or 'missing'} / gate {summary.get('supabase_staging_data_parity_gate') or 'missing'} / table failures {summary.get('supabase_staging_table_failures')}.",
        f"- Supabase staging refresh preflight: {summary.get('supabase_staging_refresh_preflight_status') or 'missing'} / gate {summary.get('supabase_staging_refresh_preflight_gate') or 'missing'}.",
        f"- Supabase staging refresh run: {summary.get('supabase_staging_refresh_run_status') or 'missing'} / gate {summary.get('supabase_staging_refresh_run_gate') or 'missing'}.",
        f"- Redeploy required: {summary.get('redeploy_required') or 'missing'}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values required for this packet: {summary.get('secret_values_required_for_packet')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        "",
        "## Owner Confirmation",
        "",
        "Open the latest hosted URL above. If you cannot sign in, use the login page's **Set Owner Password** button while the temporary recovery switch is still enabled, choose a private owner password with at least 12 characters, and sign in with that password.",
        "",
        "After signing in successfully, reply exactly:",
        "",
        "```text",
        OWNER_REPLY,
        "```",
        "",
        "Do not share the password, Vercel token, Supabase token, or protection bypass secret in chat.",
        "",
        "## Wave Steps",
        "",
        "| Order | Step | Status | Class | Owner Input | Secret Handling | Proof Report |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in phases:
        cells = [
            str(row.get("order")),
            str(row.get("phase")),
            str(row.get("status")),
            str(row.get("wave_class")),
            str(row.get("owner_input")),
            str(row.get("secret_handling")),
            str(row.get("proof_report")),
        ]
        lines.append(
            "| "
            + " | ".join(cell.replace("|", "/") for cell in cells)
            + " |"
        )
    lines.extend(["", "## Command Detail", ""])
    for row in phases:
        lines.extend(
            [
                f"### {row.get('order')}. {row.get('phase')}",
                "",
                f"- Purpose: {row.get('purpose')}",
                f"- Packet provider calls: {row.get('provider_calls_by_packet')}",
                f"- Packet secret values stored: {row.get('secret_values_stored')}",
                f"- CRM record writes: {row.get('crm_record_writes')}",
                f"- Remote write lock changed: {row.get('remote_write_lock_changed')}",
                f"- Source of truth changed: {row.get('source_of_truth_changed')}",
                "- Command or action:",
                "",
                "```bash",
                *command_lines(str(row.get("command") or "")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Boundaries",
            "",
            "- This packet is a non-secret plan and evidence artifact only.",
            "- Owner recovery can be disabled only after owner sign-in is confirmed.",
            "- Secret values belong in hidden prompts or one-shot environment variables, not in reports, docs, source files, shell history, or chat.",
            "- Hosted write-audit rehearsal remains a separate explicit approval because it temporarily changes the write lock and creates a probe record.",
            "- Source-of-truth cutover remains a final separate owner approval after all production gates pass.",
            "",
            "## Related Reports",
            "",
            "- `reports/remote_production_readiness.md`",
            "- `reports/remaining_production_gates_packet.md`",
            "- `reports/owner_gate_intake_packet.md`",
            "- `reports/owner_recovery_closure.md`",
            "- `reports/owner_recovery_disable_run.md`",
            "- `reports/hosted_redeploy_preflight.md`",
            "- `reports/hosted_deployment_freshness.md`",
            "- `reports/vercel_hosted_app_smoke.md`",
            "- `reports/supabase_staging_refresh_run.md`",
            "- `reports/supabase_staging_refresh_preflight.md`",
            "- `reports/supabase_staging_data_parity.md`",
            "- `reports/local_write_freeze_readiness.md`",
            "- `reports/safe_production_gate_runner.md`",
            "- `reports/remaining_gate_execution_readiness.md`",
            "- `reports/private_execution_inputs.md`",
            "- `reports/owner_confirmed_production_wave.md`",
            "- `reports/secret_handling_boundaries.md`",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/remote_monitoring_signoff.md`",
            "- `reports/hosted_write_audit_execution.md`",
            "- `reports/owner_shakedown_signoff.md`",
            "- `reports/source_of_truth_cutover_preflight.md`",
            "- `reports/source_of_truth_cutover_approval.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "owner_approved_wave_packet.csv", rows)
    write_report(REPORTS_DIR / "owner_approved_wave_packet.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
