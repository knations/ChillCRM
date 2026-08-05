#!/usr/bin/env python3
"""Generate a read-only hosted database migration readiness report."""

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


def clip(value: Any, limit: int = 150) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def rows_of_type(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> list[str]:
    visible_rows = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key)).replace("|", "/"))
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


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = rows_of_type(rows, "summary")[0]
    table_rows = rows_of_type(rows, "table_migration")
    column_rows = rows_of_type(rows, "column_migration")
    foreign_key_rows = rows_of_type(rows, "foreign_key")
    requirements = rows_of_type(rows, "migration_requirement")
    risks = rows_of_type(rows, "risk")
    core_tables = [row for row in table_rows if int(row.get("priority") or 99) <= 2]
    json_columns = [row for row in column_rows if row.get("postgres_type") == "jsonb"]
    timestamp_columns = [row for row in column_rows if row.get("postgres_type") == "timestamptz"]

    lines = [
        "# Hosted Database Migration Readiness",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only schema and data-shape analysis for promoting the local SQLite CRM into a hosted database for remote admin access. It does not create a remote database, provision hosting, migrate data, invite users, save decisions, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Source database: `{summary.get('source_database')}`.",
        f"- Target database: {summary.get('target_database')}.",
        f"- Tables: {int(summary.get('table_count') or 0):,}.",
        f"- Columns: {int(summary.get('column_count') or 0):,}.",
        f"- Total source rows: {int(summary.get('total_source_rows') or 0):,}.",
        f"- Foreign keys: {int(summary.get('foreign_key_count') or 0):,}.",
        f"- Largest table: {summary.get('largest_table')} ({int(summary.get('largest_table_rows') or 0):,} rows).",
        f"- JSON candidate columns: {int(summary.get('json_candidate_columns') or 0):,}.",
        f"- Timestamp/date text columns: {int(summary.get('timestamp_text_columns') or 0):,}.",
        f"- File path columns: {int(summary.get('file_path_columns') or 0):,}.",
        f"- Polymorphic reference tables: {int(summary.get('polymorphic_reference_tables') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Core Load Order",
        "",
        *table(
            core_tables,
            [
                ("priority", "Priority"),
                ("table_name", "Table"),
                ("category", "Category"),
                ("row_count", "Rows"),
                ("primary_key_columns", "Primary Key"),
                ("migration_note", "Migration Note"),
            ],
        ),
        "",
        "## Table Migration Inventory",
        "",
        *table(
            table_rows,
            [
                ("priority", "Priority"),
                ("table_name", "Table"),
                ("category", "Category"),
                ("row_count", "Rows"),
                ("column_count", "Columns"),
                ("foreign_key_count", "FKs"),
                ("has_polymorphic_reference", "Polymorphic"),
            ],
        ),
        "",
        "## Type Translation",
        "",
        *table(
            column_rows,
            [
                ("table_name", "Table"),
                ("column_name", "Column"),
                ("sqlite_type", "SQLite Type"),
                ("postgres_type", "Hosted Type"),
                ("migration_note", "Note"),
            ],
            limit=80,
        ),
        "",
        "## JSON Candidates",
        "",
        *table(
            json_columns,
            [
                ("table_name", "Table"),
                ("column_name", "Column"),
                ("migration_note", "Note"),
            ],
        ),
        "",
        "## Timestamp Normalization",
        "",
        *table(
            timestamp_columns,
            [
                ("table_name", "Table"),
                ("column_name", "Column"),
                ("migration_note", "Note"),
            ],
        ),
        "",
        "## Foreign Keys",
        "",
        *table(
            foreign_key_rows,
            [
                ("table_name", "From Table"),
                ("from_column", "From Column"),
                ("target_table", "Target Table"),
                ("target_column", "Target Column"),
                ("on_delete", "On Delete"),
            ],
        ),
        "",
        "## Migration Requirements",
        "",
        *table(
            requirements,
            [
                ("order", "Order"),
                ("title", "Requirement"),
                ("detail", "Detail"),
                ("gate", "Gate"),
            ],
        ),
        "",
        "## Risks And Mitigations",
        "",
        *table(
            risks,
            [
                ("order", "Order"),
                ("title", "Risk"),
                ("detail", "Detail"),
                ("mitigation", "Mitigation"),
            ],
        ),
        "",
        "## Recommendation",
        "",
        "Use this report as the technical preflight before choosing or provisioning the remote stack. The current data is small enough for a careful staged migration, but the hosted version should preserve local IDs, add remote app-user identity, move files into private storage, validate timestamp/JSON columns, and verify counts before any admin cutover.",
        "",
        "## Related Files",
        "",
        "- `reports/hosted_database_migration_readiness.csv`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_schema_draft.sql`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/local_crm_database_map.md`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/remote_admin_rollout_board.md`",
        "- `reports/remote_hosting_decision_packet.md`",
        "- `reports/remote_managed_cloud_provider_shortlist.md`",
        "- `reports/remote_staging_pricing_preflight.md`",
        "- `reports/remote_staging_setup_runbook.md`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_hosted_database_migration_readiness_rows()
    write_csv(REPORTS_DIR / "hosted_database_migration_readiness.csv", rows)
    (REPORTS_DIR / "hosted_database_migration_readiness.md").write_text(generate_report(rows), encoding="utf-8")
    print(
        f"Wrote {len(rows):,} hosted database migration readiness rows to "
        "reports/hosted_database_migration_readiness.md and .csv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
