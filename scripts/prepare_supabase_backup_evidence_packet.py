#!/usr/bin/env python3
"""Prepare the owner-facing Supabase backup evidence capture packet."""

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


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            values.append(str(row.get(key, "")).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def build_rows() -> list[dict[str, Any]]:
    production = read_text("reports/remote_production_readiness.md")
    backup = read_text("reports/supabase_backup_readiness.md")
    storage = read_text("reports/chillcrm_supabase_storage_migration.md")
    latest_url = backtick_value(production, "Latest URL")
    project_ref = backtick_value(backup, "Project ref") or "ckjbnummsxqcyeahzynz"
    backup_status = plain_value(backup, "Status") or "missing"
    production_gate = plain_value(backup, "Production gate") or "missing"
    storage_manifest_clean = (
        "Document files inventoried: 203." in storage
        and "Missing local files: 0." in storage
        and "Size mismatches: 0." in storage
        and "Remote file object rows: 203." in storage
        and "Linked remote document rows: 203." in storage
    )
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "generated_at": now_utc(),
            "status": "supabase_backup_evidence_packet_ready",
            "project_ref": project_ref,
            "latest_url": latest_url,
            "backup_status": backup_status,
            "production_gate": production_gate,
            "storage_manifest_present": "yes" if storage_manifest_clean else "unknown",
            "secret_values_required": "no",
            "crm_record_writes": "no",
            "source_of_truth_changed": "no",
        }
    ]
    checklist = [
        (
            "open_dashboard",
            "Open Supabase project",
            "Supabase Dashboard > CHILLCRM project > Database > Backups.",
            "Do not copy service-role keys, database passwords, JWTs, or connection strings.",
        ),
        (
            "record_backup_path",
            "Record provider backup path",
            "Note whether backups are visible, the latest backup timestamp, completed backup count if shown, and restore controls.",
            "Safe to share: timestamps, yes/no status, count, and non-secret screenshots.",
        ),
        (
            "record_pitr",
            "Record PITR status",
            "If PITR is enabled, note the recovery window shown by the Dashboard. If it is disabled, record disabled.",
            "Safe to share: enabled/disabled and earliest/latest recovery window.",
        ),
        (
            "record_storage_scope",
            "Confirm storage rollback scope",
            "Confirm database backups do not restore Storage object bytes, so CHILLCRM keeps the 203-file document package and Supabase storage manifest separately.",
            "Safe to share: confirmation only; no bucket keys or signed URLs.",
        ),
        (
            "record_restore_path",
            "Choose restore/rollback proof",
            "Pick a proof type: Supabase disposable restore, Supabase clone restore, or owner-approved local rollback package plus storage manifest.",
            "No restore should be run on the live project from this packet.",
        ),
    ]
    for order, (key, task, detail, safe_share) in enumerate(checklist, start=1):
        rows.append(
            {
                "row_type": "checklist",
                "order": order,
                "key": key,
                "task": task,
                "detail": detail,
                "safe_to_share": safe_share,
            }
        )
    commands = [
        (
            "api_token_path",
            "Use Management API token",
            "Supabase token is supplied through a hidden prompt or one-shot env var; the report stores no token value.",
            "SUPABASE_ACCESS_TOKEN=<supabase-management-token> .venv/bin/python scripts/verify_supabase_backup_readiness.py",
        ),
        (
            "dashboard_path",
            "Use Dashboard evidence",
            "Use when the owner can see the backup/PITR facts in Supabase Dashboard and wants to avoid sharing a Management API token.",
            '.venv/bin/python scripts/verify_supabase_backup_readiness.py --dashboard-backup-visible --dashboard-latest-backup-at "<dashboard timestamp>" --dashboard-pitr-enabled <yes|no|unknown> --dashboard-evidence-owner "Kevin Nations"',
        ),
        (
            "restore_proof_path",
            "Add restore/rollback proof",
            "Use only after restore/rollback evidence is genuinely completed and owner-approved.",
            '.venv/bin/python scripts/verify_supabase_backup_readiness.py --dashboard-backup-visible --dashboard-latest-backup-at "<dashboard timestamp>" --dashboard-pitr-enabled <yes|no|unknown> --dashboard-evidence-owner "Kevin Nations" --restore-proof --use-current-local-rollback-package --restore-proof-owner "Kevin Nations"',
        ),
    ]
    for order, (key, path, detail, command) in enumerate(commands, start=1):
        rows.append(
            {
                "row_type": "command_option",
                "order": order,
                "key": key,
                "path": path,
                "detail": detail,
                "command": command,
            }
        )
    return rows


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    checklist = [row for row in rows if row["row_type"] == "checklist"]
    commands = [row for row in rows if row["row_type"] == "command_option"]
    lines = [
        "# Supabase Backup Evidence Packet",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This packet tells the owner/operator exactly how to capture Supabase backup/PITR evidence for CHILLCRM without exposing secrets or changing data. It does not call Supabase, restore backups, unlock hosted writes, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Project ref: `{summary.get('project_ref')}`.",
        f"- Latest hosted URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Current backup report status: {summary.get('backup_status')}.",
        f"- Current production gate: {summary.get('production_gate')}.",
        f"- Storage manifest present: {summary.get('storage_manifest_present')}.",
        f"- Secret values required for this packet: {summary.get('secret_values_required')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        "",
        "## Dashboard Checklist",
        "",
        *table(
            checklist,
            [
                ("order", "Order"),
                ("task", "Task"),
                ("detail", "Detail"),
                ("safe_to_share", "Safe To Share"),
            ],
        ),
        "",
        "## Command Options",
        "",
    ]
    for row in commands:
        lines.extend(
            [
                f"### {row.get('order')}. {row.get('path')}",
                "",
                str(row.get("detail")),
                "",
                "```bash",
                str(row.get("command")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Evidence Needed From Owner",
            "",
            "- Latest backup timestamp or PITR recovery window from Supabase Dashboard.",
            "- PITR status: enabled, disabled, or unknown.",
            "- Restore/rollback proof choice: disposable Supabase restore, clone restore, or owner-approved local rollback package plus storage manifest.",
            "- If using the local rollback package path, the verifier can pull the current passing rollback-package detail from `reports/cutover_rollback_package_readiness.md` with `--use-current-local-rollback-package`.",
            "- Explicit confirmation that no live Supabase restore has been run from this packet.",
            "",
            "## Related Reports",
            "",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/remaining_production_gates_packet.md`",
            "- `reports/remote_production_readiness.md`",
            "- `reports/cutover_rollback_package_readiness.md`",
            "- `reports/chillcrm_supabase_storage_migration.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "supabase_backup_evidence_packet.csv", rows)
    write_report(REPORTS_DIR / "supabase_backup_evidence_packet.md", rows)
    print(f"Wrote {len(rows):,} rows to reports/supabase_backup_evidence_packet.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
