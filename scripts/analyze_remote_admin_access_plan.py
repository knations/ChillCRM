#!/usr/bin/env python3
"""Generate a read-only remote admin access migration plan."""

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


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
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
    hosting_options = rows_of_type(rows, "hosting_option")
    phases = rows_of_type(rows, "phase")
    security_controls = rows_of_type(rows, "security_control")
    roles = rows_of_type(rows, "role")
    data_checks = rows_of_type(rows, "data_migration_check")
    file_steps = rows_of_type(rows, "file_storage_step")
    cutover_steps = rows_of_type(rows, "cutover_step")
    open_decisions = rows_of_type(rows, "open_decision")

    lines = [
        "# Remote Admin Access Plan",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only plan for moving the local CRM prototype into a secure shared system for remote admins. It does not provision hosting, expose localhost, save project decisions, migrate data, invite users, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Recommended path: {summary.get('recommended_path')}.",
        f"- Decision needed: {summary.get('decision_needed')}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Tasks/notes: {int(summary.get('tasks') or 0):,} tasks, {int(summary.get('notes') or 0):,} notes.",
        f"- Archive items: {int(summary.get('archive_items') or 0):,}; document file coverage: {summary.get('document_file_coverage_percent')}%.",
        f"- Open local gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('deferred_project_decisions') or 0):,} deferred decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}.",
        f"- Backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Hosting Posture",
        "",
        *table(
            hosting_options,
            [
                ("choice_code", "Choice"),
                ("label", "Option"),
                ("recommendation", "Recommendation"),
                ("description", "Description"),
                ("upside", "Upside"),
                ("tradeoff", "Tradeoff"),
            ],
        ),
        "",
        "## Deployment Phases",
        "",
        *table(
            phases,
            [
                ("order", "Order"),
                ("title", "Phase"),
                ("work", "Work"),
                ("proof", "Proof"),
                ("gate", "Gate"),
            ],
        ),
        "",
        "## Security Controls",
        "",
        *table(
            security_controls,
            [
                ("order", "Order"),
                ("title", "Control"),
                ("requirement", "Requirement"),
            ],
        ),
        "",
        "## Admin Roles",
        "",
        *table(
            roles,
            [
                ("order", "Order"),
                ("label", "Role"),
                ("permissions", "Permissions"),
            ],
        ),
        "",
        "## Data Migration Checks",
        "",
        *table(
            data_checks,
            [
                ("order", "Order"),
                ("title", "Check"),
                ("scope", "Scope"),
            ],
        ),
        "",
        "## File Storage",
        "",
        *table(
            file_steps,
            [
                ("order", "Order"),
                ("title", "Step"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Cutover Steps",
        "",
        *table(
            cutover_steps,
            [
                ("order", "Order"),
                ("title", "Step"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Open Decisions",
        "",
        *table(
            open_decisions,
            [
                ("order", "Order"),
                ("question", "Decision"),
                ("recommended_path", "Recommended Path"),
                ("save_boundary", "Save Boundary"),
            ],
        ),
        "",
        "## Recommendation",
        "",
        "Choose the hosting posture first. The recommended posture is a managed cloud app with managed Postgres and private file storage. After that choice, build a staging migration, verify counts and permissions, then cut over only after a final local backup and export package.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_admin_access_plan.csv`",
        "- `reports/remote_admin_permissions_matrix.md`",
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
        "- `reports/hosted_database_migration_readiness.md`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_schema_draft.sql`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/local_crm_database_map.md`",
        "- `reports/zendesk_independence_checklist.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `reports/migration_completion_audit.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_admin_access_plan_rows()
    write_csv(REPORTS_DIR / "remote_admin_access_plan.csv", rows)
    (REPORTS_DIR / "remote_admin_access_plan.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote admin access rows to reports/remote_admin_access_plan.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
