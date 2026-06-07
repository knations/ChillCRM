#!/usr/bin/env python3
"""Generate a read-only hosted database schema draft."""

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


def generate_sql(rows: list[dict[str, Any]]) -> str:
    sql_row_types = {"schema_sql", "table_ddl", "remote_table_ddl", "foreign_key_ddl", "index_ddl"}
    parts: list[str] = []
    for row in rows:
        if row.get("row_type") not in sql_row_types:
            continue
        title = row.get("title") or row.get("table_name") or row.get("index_name") or row.get("row_type")
        parts.append(f"-- {title}")
        parts.append(str(row.get("sql") or "").strip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = rows_of_type(rows, "summary")[0]
    table_rows = rows_of_type(rows, "table_ddl")
    remote_tables = rows_of_type(rows, "remote_table_ddl")
    foreign_keys = rows_of_type(rows, "foreign_key_ddl")
    indexes = rows_of_type(rows, "index_ddl")
    validation_queries = rows_of_type(rows, "validation_query")
    requirements = rows_of_type(rows, "schema_requirement")

    lines = [
        "# Hosted Database Schema Draft",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only hosted database schema draft for staging review. It translates the local SQLite CRM into a managed-Postgres-style schema and adds remote-only app user, role, audit, file, and migration tables. It does not create a remote database, provision hosting, migrate data, create users, save decisions, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Target database: {summary.get('target_database')}.",
        f"- Schema: {summary.get('schema_name')}.",
        f"- Source database: `{summary.get('source_database')}`.",
        f"- Source tables: {int(summary.get('source_table_count') or 0):,}.",
        f"- Source columns: {int(summary.get('source_column_count') or 0):,}.",
        f"- Remote-only tables: {int(summary.get('remote_only_table_count') or 0):,}.",
        f"- Foreign key statements: {int(summary.get('foreign_key_count') or 0):,}.",
        f"- Index statements: {int(summary.get('index_count') or 0):,}.",
        f"- SQL draft: `{summary.get('sql_report')}`.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## SQL Draft Location",
        "",
        "- `reports/hosted_database_schema_draft.sql`",
        "- Included in the Complete Local CRM Package.",
        "- Review and run only in a staging database after a hosting posture is chosen.",
        "",
        "## Source Table DDL",
        "",
        *table(
            table_rows,
            [
                ("table_name", "Table"),
                ("category", "Category"),
                ("purpose", "Purpose"),
                ("migration_note", "Note"),
            ],
        ),
        "",
        "## Remote-Only Tables",
        "",
        *table(
            remote_tables,
            [
                ("table_name", "Table"),
                ("category", "Category"),
                ("purpose", "Purpose"),
                ("migration_note", "Note"),
            ],
        ),
        "",
        "## Foreign Keys",
        "",
        *table(
            foreign_keys,
            [
                ("table_name", "From Table"),
                ("from_column", "From Column"),
                ("target_table", "Target Table"),
                ("target_column", "Target Column"),
                ("migration_note", "Note"),
            ],
            limit=60,
        ),
        "",
        "## Index Draft",
        "",
        *table(
            indexes,
            [
                ("table_name", "Table"),
                ("index_name", "Index"),
                ("columns", "Columns"),
                ("migration_note", "Note"),
            ],
            limit=80,
        ),
        "",
        "## Validation Queries",
        "",
        *table(
            validation_queries,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("sql", "SQL"),
                ("migration_note", "Note"),
            ],
        ),
        "",
        "## Requirements",
        "",
        *table(
            requirements,
            [
                ("order", "Order"),
                ("title", "Requirement"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Safety Boundary",
        "",
        "This schema draft is an artifact for staging review only. It does not connect to a remote host, does not create tables anywhere, does not migrate data, does not invite users, and does not alter the local CRM.",
        "",
        "## Related Files",
        "",
        "- `reports/hosted_database_schema_draft.csv`",
        "- `reports/hosted_database_schema_draft.sql`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/hosted_database_migration_readiness.md`",
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
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/local_crm_database_map.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_hosted_schema_draft_rows()
    write_csv(REPORTS_DIR / "hosted_database_schema_draft.csv", rows)
    (REPORTS_DIR / "hosted_database_schema_draft.md").write_text(generate_report(rows), encoding="utf-8")
    (REPORTS_DIR / "hosted_database_schema_draft.sql").write_text(generate_sql(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} hosted schema draft rows to reports/hosted_database_schema_draft.md, .csv, and .sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
