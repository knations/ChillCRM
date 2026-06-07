#!/usr/bin/env python3
"""Generate a read-only map of the local CRM database."""

from __future__ import annotations

import csv
import sys
from collections import Counter
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


def first_row(rows: list[dict[str, Any]], row_type: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("row_type") == row_type), {})


def filter_rows(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = first_row(rows, "summary")
    table_rows = filter_rows(rows, "table")
    column_rows = filter_rows(rows, "column")
    foreign_key_rows = filter_rows(rows, "foreign_key")
    export_rows = filter_rows(rows, "csv_export")
    report_rows = filter_rows(rows, "report")
    category_counts = Counter(str(row.get("category") or "Supporting data") for row in table_rows)
    category_summary = [
        {"category": category, "tables": count}
        for category, count in sorted(category_counts.items(), key=lambda item: (item[0], item[1]))
    ]
    relationship_rows = [
        row
        for row in foreign_key_rows
        if row.get("from_column") and row.get("target_table") and row.get("target_column")
    ]
    core_tables = [row for row in table_rows if row.get("category") == "Core CRM records"]
    operational_tables = [
        row
        for row in table_rows
        if row.get("category") in {"Local operations", "Cleanup and governance", "Recovered Zendesk archive"}
    ]

    lines = [
        "# Local CRM Database Map",
        "",
        f"Generated: {generated_at}",
        "",
        "Read-only database inventory. It does not edit records, save decisions, link archive items, resolve cleanup, restore backups, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Database: `{summary.get('database_path')}`.",
        f"- Database size: {int(summary.get('database_bytes') or 0):,} bytes.",
        f"- Tables: {int(summary.get('table_count') or 0):,}.",
        f"- Views: {int(summary.get('view_count') or 0):,}.",
        f"- Columns mapped: {len(column_rows):,}.",
        f"- Foreign-key links mapped: {len(relationship_rows):,}.",
        f"- CSV exports available: {int(summary.get('csv_export_count') or 0):,}.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('report_count') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Table Categories",
        "",
        *table(category_summary, [("category", "Category"), ("tables", "Tables")]),
        "",
        "## Core Table Map",
        "",
        *table(
            core_tables,
            [
                ("table_name", "Table"),
                ("row_count", "Rows"),
                ("column_count", "Columns"),
                ("primary_key_columns", "Primary Key"),
                ("purpose", "Purpose"),
            ],
        ),
        "",
        "## Operations And Governance Tables",
        "",
        *table(
            operational_tables,
            [
                ("table_name", "Table"),
                ("category", "Category"),
                ("row_count", "Rows"),
                ("column_count", "Columns"),
                ("purpose", "Purpose"),
            ],
        ),
        "",
        "## Table Map",
        "",
        *table(
            table_rows,
            [
                ("table_name", "Table"),
                ("category", "Category"),
                ("row_count", "Rows"),
                ("column_count", "Columns"),
                ("foreign_key_count", "FKs"),
                ("purpose", "Purpose"),
            ],
        ),
        "",
        "## Relationship Map",
        "",
        *table(
            relationship_rows,
            [
                ("table_name", "From Table"),
                ("from_column", "From Column"),
                ("target_table", "Target Table"),
                ("target_column", "Target Column"),
                ("on_delete", "On Delete"),
            ],
        ),
        "",
        "## Export Inventory",
        "",
        *table(
            export_rows,
            [
                ("export_type", "Export Type"),
                ("label", "Label"),
                ("url", "URL"),
            ],
            limit=40,
        ),
        "",
        "## Report Inventory",
        "",
        *table(
            report_rows,
            [
                ("report_name", "Report"),
                ("exists", "Ready"),
                ("bytes", "Bytes"),
                ("path", "Path"),
            ],
        ),
        "",
        "## Safety Boundary",
        "",
        "- Treat `crm_database/local_crm.sqlite` as the local source of truth after the Zendesk Sell pull.",
        "- Use the local CRM app and maintenance script for backups, restores, and edits; do not hand-edit SQLite tables.",
        "- Project Decisions, archive review/linking, cleanup review, and record edits create local audit entries when saved from the app.",
        "- The map is for understanding, export, and handoff only; it does not save decisions or run cleanup.",
        "",
        "## Related Files",
        "",
        "- `reports/local_crm_database_map.csv`",
        "- `reports/migration_completion_audit.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_database_map_rows()
    write_csv(REPORTS_DIR / "local_crm_database_map.csv", rows)
    (REPORTS_DIR / "local_crm_database_map.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} database map rows to reports/local_crm_database_map.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
