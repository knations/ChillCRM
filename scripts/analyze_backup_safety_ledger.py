#!/usr/bin/env python3
"""Generate a backup safety ledger for the local CRM."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"


def handler() -> server.CRMRequestHandler:
    server.ensure_runtime_schema(DB_PATH)
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DB_PATH
    return instance


def clip(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> list[str]:
    visible_rows = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), 140).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["result"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ledger = app.backup_safety_ledger()
    summary = ledger.get("summary") or {}
    backup_rows = [row for row in rows if row.get("row_type") == "backup"]
    action_rows = [row for row in rows if row.get("row_type") == "protected_action"]
    lines = [
        "# Backup Safety Ledger",
        "",
        f"Generated: {generated_at}",
        "",
        "This report documents local CRM backup inventory and restore posture. It does not create, restore, delete, or modify any backup or CRM record.",
        "",
        "## Summary",
        "",
        f"- Active database: `{summary.get('database_path')}`.",
        f"- Active database size: {int(summary.get('database_bytes') or 0):,} bytes.",
        f"- Backups available: {int(summary.get('backup_count') or 0):,}.",
        f"- Total backup size: {int(summary.get('total_backup_bytes') or 0):,} bytes.",
        f"- Latest backup: `{summary.get('latest_backup') or 'none'}`.",
        f"- Latest backup modified: {summary.get('latest_backup_modified_at') or 'n/a'}.",
        f"- Complete package ready: {summary.get('complete_package_ready')}.",
        f"- Document package ready: {summary.get('document_package_ready')}.",
        f"- Recommendation: {summary.get('recommendation')}",
        "",
        "## Backup Inventory",
        "",
        *table(
            backup_rows,
            [
                ("backup_name", "Backup"),
                ("reason", "Reason"),
                ("bytes", "Bytes"),
                ("modified_at", "Modified"),
                ("restore_method", "Restore Method"),
            ],
        ),
        "",
        "## Protected Local Actions",
        "",
        *table(
            action_rows,
            [
                ("category", "Category"),
                ("action", "Action"),
                ("trigger", "Trigger"),
                ("backup_timing", "Backup Timing"),
                ("audit", "Audit Trail"),
            ],
        ),
        "",
        "## Manual Safety Commands",
        "",
        "```sh",
        "python3 scripts/local_crm_maintenance.py backup --reason manual",
        "python3 scripts/local_crm_maintenance.py list-backups",
        "python3 scripts/local_crm_maintenance.py restore backups/local_crm_YYYYMMDDTHHMMSSffffffZ_manual.sqlite",
        "```",
        "",
        "## Related Files",
        "",
        "- `reports/backup_safety_ledger.csv`",
        "- `reports/cleanup_execution_safety_plan.md`",
        "- `reports/project_decision_brief.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_backup_safety_ledger_rows()
    write_csv(REPORTS_DIR / "backup_safety_ledger.csv", rows)
    (REPORTS_DIR / "backup_safety_ledger.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} backup safety ledger rows to reports/backup_safety_ledger.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
