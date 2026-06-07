#!/usr/bin/env python3
"""Prepare a non-secret owner intake packet for the remaining production gates."""

from __future__ import annotations

import csv
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


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


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


def build_rows() -> list[dict[str, Any]]:
    production = read_text("reports/remote_production_readiness.md")
    monitoring = read_text("reports/remote_monitoring_readiness.md")
    deployment_freshness = read_text("reports/hosted_deployment_freshness.md")
    write_audit = read_text("reports/hosted_write_unlock_audit_rehearsal.md")
    write_audit_execution = read_text("reports/hosted_write_audit_execution.md")
    backup = read_text("reports/supabase_backup_readiness.md")
    rollback = read_text("reports/cutover_rollback_package_readiness.md")
    owner_recovery = read_text("reports/owner_recovery_closure.md")
    source_cutover = read_text("reports/source_of_truth_cutover_approval.md")
    latest_url = backtick_value(production, "Latest URL")
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "generated_at": now_utc(),
            "status": "owner_gate_intake_packet_ready",
            "latest_url": latest_url,
            "production_status": plain_value(production, "Status") or "missing",
            "production_gate": plain_value(production, "Production gate") or "missing",
            "production_passed": plain_value(production, "Passing gates") or "0",
            "production_failed": plain_value(production, "Failed gates") or "0",
            "production_input_required": plain_value(production, "Input-required gates") or "0",
            "deployment_freshness_status": plain_value(deployment_freshness, "Status") or "missing",
            "monitoring_status": plain_value(monitoring, "Status") or "missing",
            "write_audit_preflight": plain_value(write_audit, "Preflight status") or "missing",
            "write_audit_execution": plain_value(write_audit_execution, "Status") or "missing",
            "backup_status": plain_value(backup, "Status") or "missing",
            "rollback_status": plain_value(rollback, "Status") or "missing",
            "owner_recovery_status": plain_value(owner_recovery, "Status") or "missing",
            "source_cutover_status": plain_value(source_cutover, "Status") or "missing",
            "secret_values_required": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
        }
    ]
    questions = [
        (
            1,
            "supabase_backup_path",
            "Supabase backup/PITR evidence",
            "In Supabase Dashboard > Database > Backups, provide the latest backup timestamp or completed backup count, plus PITR enabled/disabled/unknown and recovery window if enabled.",
            "Non-secret Dashboard facts only. Do not share service-role keys, database passwords, JWTs, connection strings, or access tokens in chat.",
            "reports/supabase_backup_readiness.md",
            "scripts/verify_supabase_backup_readiness.py",
        ),
        (
            2,
            "rollback_proof_approval",
            "Rollback proof approval",
            "Confirm whether you approve using the current passing local rollback package plus the 203-file Supabase storage manifest as rollback proof, and confirm no live Supabase restore was run.",
            "Approval facts only; no secrets. The current rollback package is already verified separately.",
            "reports/cutover_rollback_package_readiness.md",
            "scripts/verify_supabase_backup_readiness.py --use-current-local-rollback-package",
        ),
        (
            3,
            "owner_recovery_disable",
            "Owner recovery closure",
            "After you confirm you can sign in with your own password, approve disabling the temporary hosted owner-recovery switch.",
            "Approval only. Do not paste the password; just confirm access is restored and recovery can be disabled.",
            "reports/owner_recovery_closure.md",
            "scripts/disable_owner_recovery_after_access.py",
        ),
        (
            4,
            "write_audit_rehearsal_approval",
            "Hosted write-audit rehearsal approval",
            "Confirm whether you approve temporarily lifting REMOTE_WRITE_LOCK on the safe staging target for one controlled actor-aware write rehearsal, then restoring the lock.",
            "Approval only. This is the one step that can lead to a staging write after explicit approval.",
            "reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
            "scripts/prepare_hosted_write_audit_rehearsal.py; scripts/execute_hosted_write_audit_rehearsal.py",
        ),
        (
            5,
            "monitoring_owner_cadence",
            "Monitoring owner and cadence approval",
            "Confirm the responsible owner and cadence for health/protection, Vercel/Supabase logs, backup status, audit/file/export checks, and owner feedback during shakedown and week one.",
            "Approval only. No secrets or provider changes.",
            "reports/remote_monitoring_signoff.md",
            "scripts/record_remote_monitoring_signoff.py",
        ),
        (
            6,
            "owner_shakedown_signoff",
            "Owner shakedown signoff",
            "After the backup, write-audit, and monitoring gates pass, confirm whether owner-only staging shakedown is accepted for cutover review.",
            "Final approval only after prerequisite gates are green.",
            "reports/owner_shakedown_signoff.md",
            "scripts/record_owner_shakedown_signoff.py",
        ),
        (
            7,
            "source_of_truth_cutover_approval",
            "Final source-of-truth cutover approval",
            "After every other production gate passes, confirm whether you approve the hosted Supabase/Vercel CRM as the company source of truth, plus the support window and rollback posture.",
            "Approval facts only. No secrets. This is separate from owner shakedown signoff and should happen last.",
            "reports/source_of_truth_cutover_approval.md",
            "scripts/record_source_of_truth_cutover_approval.py",
        ),
    ]
    for order, key, gate, question, safe_handling, proof_report, consumed_by in questions:
        rows.append(
            {
                "row_type": "owner_question",
                "order": order,
                "key": key,
                "gate": gate,
                "question": question,
                "safe_handling": safe_handling,
                "proof_report": proof_report,
                "consumed_by": consumed_by,
            }
        )
    reply_lines = [
        ("backup_latest", "Latest backup timestamp or completed backup count: <value from Supabase Dashboard>"),
        ("pitr_status", "PITR status: <enabled / disabled / unknown>; recovery window: <window or none shown>"),
        ("rollback_approval", "Rollback proof approval: <yes/no>; use current local rollback package + storage manifest: <yes/no>; no live Supabase restore was run: <yes/no>"),
        ("owner_recovery_disable", "Owner access restored and temporary recovery can be disabled: <yes/no>"),
        ("write_audit_approval", "Write-audit rehearsal approval: <yes/no>"),
        ("monitoring_approval", "Monitoring owner/cadence approval: <yes/no>; monitoring owner: <name>; cadence changes, if any: <text>"),
        ("shakedown", "Owner shakedown signoff: <not yet / yes after prerequisites are green>"),
        ("source_cutover", "Source-of-truth cutover approval: <not yet / yes after every gate is green>; support window: <text>; rollback posture: <text>"),
    ]
    for order, (key, template) in enumerate(reply_lines, start=1):
        rows.append(
            {
                "row_type": "reply_template",
                "order": order,
                "key": key,
                "template": template,
            }
        )
    return rows


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    questions = [row for row in rows if row["row_type"] == "owner_question"]
    templates = [row for row in rows if row["row_type"] == "reply_template"]
    lines = [
        "# Owner Production Gate Intake Packet",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This packet gathers the exact owner inputs still needed before CHILLCRM can become the Supabase/Vercel source of truth. It does not store secrets, call providers, unlock writes, restore backups, change CRM records, or switch source of truth.",
        "",
        "## Current Gate State",
        "",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Production status: {summary.get('production_status')} / gate {summary.get('production_gate')}.",
        f"- Production pass/fail/input: {summary.get('production_passed')} passed, {summary.get('production_failed')} failed, {summary.get('production_input_required')} input-required.",
        f"- Hosted deployment freshness: {summary.get('deployment_freshness_status')}.",
        f"- Supabase backup status: {summary.get('backup_status')}.",
        f"- Write-audit preflight: {summary.get('write_audit_preflight')}.",
        f"- Write-audit execution: {summary.get('write_audit_execution')}.",
        f"- Monitoring status: {summary.get('monitoring_status')}.",
        f"- Rollback package status: {summary.get('rollback_status')}.",
        f"- Owner recovery closure: {summary.get('owner_recovery_status')}.",
        f"- Source-of-truth cutover approval: {summary.get('source_cutover_status')}.",
        "- Secret values required for this packet: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "",
        "## Owner Access Restoration",
        "",
        "Open the latest hosted URL above. If you cannot sign in, use the login page's **Set Owner Password** button while the temporary recovery switch is still enabled, choose a private owner password with at least 12 characters, and sign in with that password.",
        "",
        "After sign-in succeeds, do not share the password. Confirm only whether owner access is restored and whether the temporary recovery switch can be disabled.",
        "",
        "## Questions For Owner",
        "",
        "| Order | Gate | Question | Safe Handling | Proof Report |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in questions:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("order")),
                    str(row.get("gate")),
                    str(row.get("question")).replace("|", "/"),
                    str(row.get("safe_handling")).replace("|", "/"),
                    str(row.get("proof_report")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safe Reply Template",
            "",
            "Paste answers in this shape. Leave anything unknown as `unknown`; do not paste secrets.",
            "",
            "```text",
        ]
    )
    for row in templates:
        lines.append(str(row.get("template")))
    lines.extend(
        [
            "```",
            "",
            "## Boundary",
            "",
            "Owner answers are not automatically approvals until they are recorded by the corresponding gate script. A hosted write-audit rehearsal still requires explicit approval before any temporary write-lock change.",
            "",
            "## Related Reports",
            "",
            "- `reports/remote_production_readiness.md`",
            "- `reports/remaining_production_gates_packet.md`",
            "- `reports/owner_gate_reply_validation.md`",
            "- `reports/hosted_deployment_freshness.md`",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/owner_recovery_closure.md`",
            "- `reports/owner_recovery_disable_run.md`",
            "- `reports/hosted_write_unlock_audit_rehearsal.md`",
            "- `reports/hosted_write_audit_execution.md`",
            "- `reports/remote_monitoring_signoff.md`",
            "- `reports/owner_shakedown_signoff.md`",
            "- `reports/source_of_truth_cutover_approval.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "owner_gate_intake_packet.csv", rows)
    write_report(REPORTS_DIR / "owner_gate_intake_packet.md", rows)
    print(f"Wrote {len(rows):,} rows to reports/owner_gate_intake_packet.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
