#!/usr/bin/env python3
"""Generate a read-only hosted data load plan."""

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
    phases = rows_of_type(rows, "load_phase")
    table_loads = rows_of_type(rows, "table_load")
    remote_seeds = rows_of_type(rows, "remote_seed")
    file_steps = rows_of_type(rows, "file_migration_step")
    validation_checks = rows_of_type(rows, "validation_check")
    cutover_gates = rows_of_type(rows, "cutover_gate")

    lines = [
        "# Hosted Data Load Plan",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only staging data load plan for moving the local CRM into a hosted database after a hosting posture is chosen. It does not create a remote database, provision hosting, migrate data, create users, save decisions, invite admins, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Source database: `{summary.get('source_database')}`.",
        f"- Target database: {summary.get('target_database')}.",
        f"- Source tables: {int(summary.get('source_table_count') or 0):,}.",
        f"- Total source rows: {int(summary.get('total_source_rows') or 0):,}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Load Phases",
        "",
        *table(
            phases,
            [
                ("order", "Order"),
                ("phase", "Phase"),
                ("detail", "Detail"),
            ],
            180,
        ),
        "",
        "## Table Load Order",
        "",
        *table(
            table_loads,
            [
                ("phase_order", "Phase"),
                ("table_name", "Table"),
                ("row_count", "Rows"),
                ("primary_key_columns", "Primary Key"),
                ("preserve_local_ids", "Preserve IDs"),
                ("prerequisite_tables", "Prerequisites"),
                ("load_note", "Note"),
            ],
            180,
        ),
        "",
        "## Remote Seed Data",
        "",
        *table(
            remote_seeds,
            [
                ("order", "Order"),
                ("table_name", "Remote Table"),
                ("seed_action", "Seed Action"),
                ("gate", "Gate"),
            ],
            180,
        ),
        "",
        "## File Migration",
        "",
        *table(
            file_steps,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("action", "Action"),
                ("proof", "Proof"),
            ],
            180,
        ),
        "",
        "## Validation Checks",
        "",
        *table(
            validation_checks,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("check", "Check"),
                ("gate", "Gate"),
            ],
            180,
        ),
        "",
        "## Cutover Gates",
        "",
        *table(
            cutover_gates,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("gate", "Gate"),
            ],
            180,
        ),
        "",
        "## Recommendation",
        "",
        "Use this plan after the hosted schema draft is reviewed. Load a staging copy from the local SQLite database, preserve local IDs, upload private files, seed only staging users/roles, verify counts and permissions, and keep the local CRM as the source of truth until the production cutover gate is explicitly approved.",
        "",
        "## Safety Boundary",
        "",
        "This load plan is planning only. It does not connect to a remote host, create a database, upload files, create users, save decisions, or change local CRM records.",
        "",
        "## Related Files",
        "",
        "- `reports/hosted_database_data_load_plan.csv`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_schema_draft.sql`",
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
        "- `reports/archive_association_audit.md`",
        "- `reports/backup_safety_ledger.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_hosted_data_load_plan_rows()
    write_csv(REPORTS_DIR / "hosted_database_data_load_plan.csv", rows)
    (REPORTS_DIR / "hosted_database_data_load_plan.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} hosted data load plan rows to reports/hosted_database_data_load_plan.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
