#!/usr/bin/env python3
"""Prepare the remaining CHILLCRM production-gate input packet."""

from __future__ import annotations

import csv
import json
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


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


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


def read_csv(relative_path: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_command_lines(command: str) -> list[str]:
    return [line for line in command.split("\n") if line.strip()]


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    inputs = [row for row in rows if row["row_type"] == "input"]
    completed_inputs = [row for row in rows if row["row_type"] == "completed_input"]
    phases = [row for row in rows if row["row_type"] == "phase"]
    lines = [
        "# Remaining Production Gates Packet",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This packet consolidates the remaining CHILLCRM Supabase/Vercel production gates into a safe operator checklist. This packet generator does not store secrets, run hosted smoke, call Supabase, unlock writes, create users, switch source of truth, or change CRM records.",
        "",
        "## Current Gate State",
        "",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Public URL: `{summary.get('public_url') or 'missing'}`.",
        f"- Production readiness: {summary.get('production_status')} / gate {summary.get('production_gate')}.",
        f"- Production pass/fail/input: {summary.get('production_passed')} passed, {summary.get('production_failed')} failed, {summary.get('production_input_required')} input-required.",
        f"- Monitoring readiness: {summary.get('monitoring_status')} / gate {summary.get('monitoring_gate')}.",
        f"- Monitoring pass/fail/input: {summary.get('monitoring_passed')} passed, {summary.get('monitoring_failed')} failed, {summary.get('monitoring_input_required')} input-required.",
        f"- Newest hosted smoke current: {summary.get('newest_hosted_smoke_current')}.",
        "",
        "## Needed Inputs",
        "",
        "| Order | Input | Status | Secret Handling | Consumed By | Proof Report |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    if inputs:
        for row in inputs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("order")),
                        str(row.get("input")),
                        str(row.get("status")),
                        str(row.get("secret_handling")),
                        str(row.get("consumed_by")),
                        str(row.get("proof_report")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | None right now | pass | No remaining external input recorded. | - | - |")
    if completed_inputs:
        lines.extend(
            [
                "",
                "## Already Cleared Inputs",
                "",
                "| Input | Cleared By | Proof Report |",
                "| --- | --- | --- |",
            ]
        )
        for row in completed_inputs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("input")),
                        str(row.get("cleared_by")),
                        str(row.get("proof_report")),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Guided Safe Runner",
            "",
            "Use `scripts/run_safe_production_gate_checks.py` when you want one guided command to run safe checks and refresh the gate reports without storing secrets. With `--all-safe --prompt-secrets`, it can rerun hosted smoke when fresh deployment evidence is needed and run Supabase backup visibility checks using hidden prompts, then refresh monitoring/readiness evidence.",
            "",
            "The runner does not write CRM records, unlock hosted writes, approve write-audit rehearsal, sign monitoring cadence, sign owner shakedown, restore backups, switch source of truth, or store secret values. The hosted smoke may create and deactivate temporary app users only to prove role behavior.",
            "",
            "```bash",
            ".venv/bin/python scripts/run_safe_production_gate_checks.py --all-safe --prompt-secrets",
            "```",
            "",
            "For a no-secret evidence refresh only:",
            "",
            "```bash",
            ".venv/bin/python scripts/run_safe_production_gate_checks.py --refresh-only",
            "```",
            "",
            "Proof report: `reports/safe_production_gate_runner.md`",
            "",
            "Execution-readiness proof: `reports/remaining_gate_execution_readiness.md`",
            "",
            "Secret-boundary proof: `reports/secret_handling_boundaries.md`",
            "Private-input map: `reports/private_execution_inputs.md`",
            "Owner-confirmed wave runner: `reports/owner_confirmed_production_wave.md`",
            "",
            "## Owner-Approved Wave Packet",
            "",
            "Use `reports/owner_approved_wave_packet.md` after owner access is restored and before disabling the temporary recovery switch. It gives the exact owner reply, the recovery-disable command, the redeploy/freshness fallback sequence, secret handling, proof reports, and the remaining separate owner approvals. It does not store secrets, call providers, deploy code, unlock writes, switch source of truth, or change CRM records.",
            "",
            "Proof report: `reports/owner_approved_wave_packet.md`",
            "",
            "Owner reply validator: `reports/owner_gate_reply_validation.md`",
            "",
            "One-command owner-confirmed wave after access is restored:",
            "",
            "```bash",
            ".venv/bin/python scripts/run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets",
            "```",
            "",
            "## Execution Order",
            "",
        ]
    )
    for row in phases:
        lines.extend(
            [
                f"### {row.get('order')}. {row.get('phase')}",
                "",
                f"- Purpose: {row.get('purpose')}",
                f"- Gate affected: {row.get('gate')}",
                f"- Proof report: `{row.get('proof_report')}`",
                "- Safe command:",
                "",
                "```bash",
                *safe_command_lines(str(row.get("safe_command") or "")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Rules",
            "",
            "- Never write secret values into reports, docs, source files, shell history, or chat logs when avoidable.",
            "- Supply tokens/passwords through hidden prompts or one-shot environment variables only.",
            "- Keep `REMOTE_WRITE_LOCK=true` until the hosted write-audit rehearsal is explicitly approved and performed on a safe staging target.",
            "- Do not declare hosted Supabase as source of truth until every blocking gate in `reports/remote_production_readiness.md` passes and owner cutover approval is explicit.",
            "",
            "## Related Reports",
            "",
            "- `reports/remote_production_readiness.md`",
            "- `reports/owner_gate_intake_packet.md`",
            "- `reports/owner_gate_reply_validation.md`",
            "- `reports/owner_approved_wave_packet.md`",
            "- `reports/remote_monitoring_readiness.md`",
            "- `reports/safe_production_gate_runner.md`",
            "- `reports/remaining_gate_execution_readiness.md`",
            "- `reports/private_execution_inputs.md`",
            "- `reports/owner_confirmed_production_wave.md`",
            "- `reports/secret_handling_boundaries.md`",
            "- `reports/remaining_gate_guardrails.md`",
            "- `reports/vercel_hosted_app_smoke.md`",
            "- `reports/hosted_redeploy_preflight.md`",
            "- `reports/hosted_deployment_freshness.md`",
            "- `reports/supabase_staging_refresh_preflight.md`",
            "- `reports/supabase_staging_refresh_run.md`",
            "- `reports/supabase_staging_data_parity.md`",
            "- `reports/local_write_freeze_readiness.md`",
            "- `reports/owner_recovery_closure.md`",
            "- `reports/owner_recovery_disable_run.md`",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/hosted_write_unlock_audit_rehearsal.md`",
            "- `reports/hosted_write_audit_execution.md`",
            "- `reports/remote_monitoring_signoff.md`",
            "- `reports/owner_shakedown_signoff.md`",
            "- `reports/source_of_truth_cutover_preflight.md`",
            "- `reports/source_of_truth_cutover_approval.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows() -> list[dict[str, Any]]:
    production = read_text("reports/remote_production_readiness.md")
    monitoring = read_text("reports/remote_monitoring_readiness.md")
    readiness_rows = read_csv("reports/remote_production_readiness.csv")
    gate_status = {
        row.get("key") or "": row.get("status") or ""
        for row in readiness_rows
        if row.get("row_type") == "gate"
    }
    latest_url = backtick_value(production, "Latest URL")
    public_url = backtick_value(production, "Public URL")
    latest_smoke_url = backtick_value(production, "Latest smoke-tested URL")
    latest_deployment_id = backtick_value(production, "Latest deployment")
    expected_smoke_url = public_url or latest_url
    newest_hosted_smoke_current = bool(
        expected_smoke_url
        and latest_smoke_url == expected_smoke_url
        and "| Newest hosted smoke | pass |" in production
    )
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "latest_deployment_id": latest_deployment_id,
        "latest_url": latest_url,
        "public_url": public_url,
        "latest_smoke_url": latest_smoke_url,
        "newest_hosted_smoke_current": "yes" if newest_hosted_smoke_current else "no",
        "production_status": plain_value(production, "Status"),
        "production_gate": plain_value(production, "Production gate"),
        "production_passed": plain_value(production, "Passing gates"),
        "production_failed": plain_value(production, "Failed gates"),
        "production_input_required": plain_value(production, "Input-required gates"),
        "monitoring_status": plain_value(monitoring, "Status"),
        "monitoring_gate": plain_value(monitoring, "Production gate"),
        "monitoring_passed": plain_value(monitoring, "Passed checks"),
        "monitoring_failed": plain_value(monitoring, "Failed checks"),
        "monitoring_input_required": plain_value(monitoring, "Input required"),
    }
    rows: list[dict[str, Any]] = [summary]
    input_specs = [
        (
            "newest_hosted_smoke",
            "Owner email and owner password",
            "input_required",
            "Password is secret. Use hidden prompt or one-shot env var; do not write to reports. Vercel bypass is not required for https://chillcrm.app.",
            "scripts/verify_vercel_hosted_app.py",
            "reports/vercel_hosted_app_smoke.md",
        )
    ]
    input_specs.extend(
        [
        (
            "owner_recovery_closure",
            "Owner access restored and recovery disable approval",
            "input_required",
            "Approval only. Do not share the password; confirm the owner can sign in and the temporary recovery switch can be disabled.",
            "scripts/prepare_owner_approved_wave_packet.py; scripts/disable_owner_recovery_after_access.py",
            "reports/owner_approved_wave_packet.md; reports/owner_recovery_disable_run.md",
        ),
        (
            "hosted_deployment_freshness",
            "Redeploy current local runtime to Vercel and rerun hosted smoke",
            "input_required",
            "Vercel token and owner password are secret. Use hidden prompts or one-shot environment variables only.",
            "scripts/prepare_owner_approved_wave_packet.py; scripts/verify_hosted_redeploy_preflight.py; scripts/deploy_chillcrm_to_vercel.py; scripts/run_newest_hosted_smoke_with_vercel_bypass.py; scripts/verify_hosted_deployment_freshness.py",
            "reports/owner_approved_wave_packet.md; reports/hosted_redeploy_preflight.md; reports/hosted_deployment_freshness.md; reports/vercel_hosted_app_smoke.md",
        ),
        (
            "supabase_staging_data_parity",
            "Reload current local audit/data changes to Supabase staging",
            "input_required",
            "Supabase database connection string is secret. Use hidden prompt or one-shot environment variable only.",
            "scripts/run_supabase_staging_refresh.py; scripts/verify_supabase_staging_refresh_preflight.py; scripts/migrate_chillcrm_to_supabase.py; scripts/verify_supabase_staging_data_parity.py; scripts/verify_remote_production_readiness.py",
            "reports/supabase_staging_refresh_run.md; reports/supabase_staging_refresh_preflight.md; reports/chillcrm_supabase_staging_validation.md; reports/supabase_staging_data_parity.md; reports/remote_production_readiness.md",
        ),
        (
            "supabase_provider_backup",
            "Supabase Management API access token or Dashboard backup evidence",
            "input_required",
            "Token is secret; Dashboard backup facts are non-secret. Do not write token values to reports.",
            "scripts/verify_supabase_backup_readiness.py",
            "reports/supabase_backup_readiness.md",
        ),
        (
            "hosted_write_unlock_audit_rehearsal",
            "Owner approval for hosted write-audit rehearsal",
            "input_required",
            "Approval only. No secret value; must be explicit before any write lock change.",
            "scripts/prepare_hosted_write_audit_rehearsal.py; scripts/execute_hosted_write_audit_rehearsal.py",
            "reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
        ),
        (
            "remote_monitoring_readiness",
            "Monitoring owner/cadence approval",
            "input_required",
            "Approval only. No secret value.",
            "scripts/record_remote_monitoring_signoff.py",
            "reports/remote_monitoring_signoff.md",
        ),
        (
            "owner_shakedown_signoff",
            "Owner shakedown signoff",
            "input_required",
            "Approval only. No secret value; should happen after smoke, backup, audit, and monitoring are green.",
            "scripts/record_owner_shakedown_signoff.py",
            "reports/owner_shakedown_signoff.md",
        ),
        (
            "source_of_truth_cutover_approval",
            "Owner source-of-truth cutover approval",
            "input_required",
            "Approval only. No secret value; should happen only after every other blocking production gate is green.",
            "scripts/record_source_of_truth_cutover_approval.py",
            "reports/source_of_truth_cutover_approval.md",
        ),
        ]
    )
    active_input_specs = [spec for spec in input_specs if gate_status.get(spec[0], "input_required") != "pass"]
    completed_input_specs = [spec for spec in input_specs if gate_status.get(spec[0], "input_required") == "pass"]
    for order, (_, input_name, status, secret_handling, consumed_by, proof_report) in enumerate(active_input_specs, start=1):
        rows.append(
            {
                "row_type": "input",
                "order": order,
                "input": input_name,
                "status": status,
                "secret_handling": secret_handling,
                "consumed_by": consumed_by,
                "proof_report": proof_report,
            }
        )
    for _, input_name, _, _, _, proof_report in completed_input_specs:
        rows.append(
            {
                "row_type": "completed_input",
                "input": input_name,
                "cleared_by": "Current production readiness gate is pass.",
                "proof_report": proof_report,
            }
        )
    phase_specs = []
    if not newest_hosted_smoke_current:
        phase_specs.append(
            {
            "phase": "Run newest hosted smoke",
            "purpose": "Prove the current Vercel deployment works with CRM auth, role checks, locks, and signed document access.",
            "gate": "Newest hosted smoke",
            "proof_report": "reports/vercel_hosted_app_smoke.md",
            "safe_command": (
                f"CHILLCRM_VERCEL_URL={expected_smoke_url or '<owner-facing-url>'} \\\n"
                "AUTH_BOOTSTRAP_ADMIN_EMAIL=<owner-email> \\\n"
                "AUTH_BOOTSTRAP_ADMIN_PASSWORD=<owner-password> \\\n"
                "EXPECT_DOCUMENT_FILE_ACCESS=true \\\n"
                ".venv/bin/python scripts/verify_vercel_hosted_app.py"
            ),
            }
        )
    phase_specs.extend(
        [
        {
            "phase": "Disable temporary owner recovery",
            "purpose": "Close the temporary hosted owner-recovery switch after the owner confirms they can sign in with their own password.",
            "gate": "Owner recovery switch disabled",
            "proof_report": "reports/owner_recovery_disable_run.md",
            "safe_command": ".venv/bin/python scripts/disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets",
        },
        {
            "phase": "Redeploy current local runtime",
            "purpose": "Deploy the current local hosted runtime package so Vercel matches the verified local app before cutover review.",
            "gate": "Hosted deployment matches local runtime",
            "proof_report": "reports/hosted_redeploy_preflight.md; reports/hosted_deployment_freshness.md",
            "safe_command": (
                ".venv/bin/python scripts/verify_hosted_redeploy_preflight.py\n"
                "CHILLCRM_SKIP_ENV_UPSERT=1 CHILLCRM_VERCEL_INLINE_FILES=1 .venv/bin/python scripts/deploy_chillcrm_to_vercel.py\n"
                ".venv/bin/python scripts/run_newest_hosted_smoke_with_vercel_bypass.py\n"
                ".venv/bin/python scripts/verify_hosted_deployment_freshness.py\n"
                ".venv/bin/python scripts/run_safe_production_gate_checks.py --refresh-only"
            ),
        },
        {
            "phase": "Refresh Supabase staging data parity",
            "purpose": "Reload current local audit/data changes into Supabase staging so the remote staging copy matches the current local source before cutover review.",
            "gate": "Supabase staging data parity",
            "proof_report": "reports/supabase_staging_refresh_run.md; reports/supabase_staging_refresh_preflight.md; reports/chillcrm_supabase_staging_validation.md; reports/supabase_staging_data_parity.md",
            "safe_command": (
                ".venv/bin/python scripts/verify_supabase_staging_refresh_preflight.py\n"
                ".venv/bin/python scripts/run_supabase_staging_refresh.py --execute --prompt-secrets"
            ),
        },
        {
            "phase": "Verify Supabase provider backup visibility",
            "purpose": "Prove provider backup/PITR status is visible through the Supabase Management API or owner-confirmed Dashboard evidence before production cutover.",
            "gate": "Supabase provider backup/PITR visibility",
            "proof_report": "reports/supabase_backup_readiness.md",
            "safe_command": (
                "SUPABASE_ACCESS_TOKEN=<supabase-management-token> .venv/bin/python scripts/verify_supabase_backup_readiness.py\n"
                "# or record owner-confirmed Dashboard evidence without a token:\n"
                ".venv/bin/python scripts/verify_supabase_backup_readiness.py --dashboard-backup-visible --dashboard-latest-backup-at <dashboard-timestamp> --dashboard-pitr-enabled <yes|no|unknown> --dashboard-evidence-owner \"Kevin Nations\"\n"
                "# after owner approval, tie rollback proof to the current passing rollback package:\n"
                ".venv/bin/python scripts/verify_supabase_backup_readiness.py --dashboard-backup-visible --dashboard-latest-backup-at <dashboard-timestamp> --dashboard-pitr-enabled <yes|no|unknown> --dashboard-evidence-owner \"Kevin Nations\" --restore-proof --use-current-local-rollback-package --restore-proof-owner \"Kevin Nations\""
            ),
        },
        {
            "phase": "Record monitoring owner/cadence approval",
            "purpose": "Confirm who watches health, logs/errors, backups, audit evidence, files, exports, and owner feedback.",
            "gate": "Remote monitoring readiness",
            "proof_report": "reports/remote_monitoring_signoff.md",
            "safe_command": '.venv/bin/python scripts/record_remote_monitoring_signoff.py --signoff-owner "Kevin Nations" --approve-owner --approve-cadence --approve-feedback',
        },
        {
            "phase": "Approve hosted write-audit rehearsal",
            "purpose": "Record approval before temporarily lifting write lock on a safe staging target.",
            "gate": "Hosted write-unlock actor-audit rehearsal",
            "proof_report": "reports/hosted_write_unlock_audit_rehearsal.md",
            "safe_command": f'.venv/bin/python scripts/prepare_hosted_write_audit_rehearsal.py --target-url {latest_url or "<latest-url>"} --owner-approved --notes "Owner approved rehearsal preparation; no writes performed by this command."',
        },
        {
            "phase": "Execute hosted write-audit rehearsal",
            "purpose": "After explicit approval, temporarily lift the staging write lock, create one actor-audited probe record, restore the lock, and refresh proof reports.",
            "gate": "Hosted write-unlock actor-audit rehearsal",
            "proof_report": "reports/hosted_write_audit_execution.md",
            "safe_command": f".venv/bin/python scripts/execute_hosted_write_audit_rehearsal.py --url {latest_url or '<latest-url>'} --owner-approved --execute --prompt-secrets",
        },
        {
            "phase": "Refresh monitoring and production readiness",
            "purpose": "Recalculate the consolidated gates after smoke, backup, monitoring signoff, or rehearsal evidence changes.",
            "gate": "Remote monitoring readiness and Remote production readiness",
            "proof_report": "reports/remote_production_readiness.md",
            "safe_command": ".venv/bin/python scripts/verify_remote_monitoring_readiness.py\n.venv/bin/python scripts/verify_remote_production_readiness.py",
        },
        {
            "phase": "Record owner-only shakedown signoff",
            "purpose": "Record owner shakedown approval only after the newest hosted smoke, backup, write-audit, and monitoring gates are green.",
            "gate": "Owner-only staging shakedown signoff",
            "proof_report": "reports/owner_shakedown_signoff.md",
            "safe_command": '.venv/bin/python scripts/record_owner_shakedown_signoff.py --signoff-owner "Kevin Nations" --approve --notes "Owner shakedown passed after all prerequisite production gates were verified."',
        },
        {
            "phase": "Record final source-of-truth cutover approval",
            "purpose": "Record the separate owner decision that the hosted Supabase/Vercel CRM can become the company source of truth.",
            "gate": "Owner source-of-truth cutover approval",
            "proof_report": "reports/source_of_truth_cutover_preflight.md; reports/source_of_truth_cutover_approval.md",
            "safe_command": (
                ".venv/bin/python scripts/verify_source_of_truth_cutover_preflight.py\n"
                f'.venv/bin/python scripts/record_source_of_truth_cutover_approval.py --approve-cutover --signoff-owner "Kevin Nations" --production-url {public_url or latest_url or "<verified-production-url>"} '
                '--support-window "<cutover support window>" --rollback-posture "<final local package retained; rollback trigger rules accepted>" '
                '--notes "Owner approved hosted CHILLCRM as source of truth after all production gates passed."'
            ),
        },
        ]
    )
    for order, spec in enumerate(phase_specs, start=1):
        rows.append({"row_type": "phase", "order": order, **spec})
    return rows


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "remaining_production_gates_packet.csv", rows)
    write_report(REPORTS_DIR / "remaining_production_gates_packet.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
