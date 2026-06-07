#!/usr/bin/env python3
"""Generate a read-only remote admin permissions matrix."""

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


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int = 150) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), limit).replace("|", "/"))
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
    roles = rows_of_type(rows, "role")
    permissions = rows_of_type(rows, "permission")
    audit_requirements = rows_of_type(rows, "audit_requirement")
    implementation_gaps = rows_of_type(rows, "implementation_gap")
    rollout_gates = rows_of_type(rows, "rollout_gate")

    lines = [
        "# Remote Admin Permissions Matrix",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only permissions and rollout plan for moving the local CRM into a shared remote system for you and admins. It does not create users, expose localhost, provision hosting, migrate data, save decisions, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Recommended roles: {summary.get('recommended_roles')}.",
        f"- Current identity source: {summary.get('current_identity_source')}",
        f"- Remote identity needed: {summary.get('remote_identity_needed')}.",
        f"- Remote shared database needed: {summary.get('remote_shared_database_needed')}.",
        f"- Private file storage needed: {summary.get('private_file_storage_needed')}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, document coverage {summary.get('document_file_coverage_percent')}%.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Role Matrix",
        "",
        *table(
            roles,
            [
                ("order", "Order"),
                ("role", "Role"),
                ("lifespan", "Lifespan"),
                ("scope", "Scope"),
                ("example_user", "Example"),
                ("remote_gate", "Remote Gate"),
            ],
            180,
        ),
        "",
        "## Action Permissions",
        "",
        *table(
            permissions,
            [
                ("order", "Order"),
                ("area", "Area"),
                ("action", "Action"),
                ("owner", "Owner"),
                ("admin", "Admin"),
                ("staff", "Staff"),
                ("read_only", "Read-only"),
                ("backup_required", "Backup"),
                ("audit_required", "Audit"),
                ("remote_gate", "Remote Gate"),
            ],
            120,
        ),
        "",
        "## Endpoint Map",
        "",
        *table(
            permissions,
            [
                ("action_key", "Action Key"),
                ("current_endpoint", "Current Local Surface"),
                ("current_audit_action", "Current/Future Audit Action"),
            ],
            180,
        ),
        "",
        "## Audit Requirements",
        "",
        *table(
            audit_requirements,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("requirement", "Requirement"),
                ("implementation_note", "Implementation Note"),
            ],
            180,
        ),
        "",
        "## Implementation Gaps",
        "",
        *table(
            implementation_gaps,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("current_gap", "Current Gap"),
                ("required_fix", "Required Fix"),
            ],
            180,
        ),
        "",
        "## Rollout Gates",
        "",
        *table(
            rollout_gates,
            [
                ("order", "Order"),
                ("title", "Gate"),
                ("detail", "Detail"),
                ("exit_criteria", "Exit Criteria"),
            ],
            180,
        ),
        "",
        "## Recommendation",
        "",
        "Use the current local CRM as the source-of-truth working prototype while building a staged remote version. The safest path is: choose hosting posture, create a final local package, load a hosted staging database, move files into private storage, add app users/roles, upgrade audit attribution, run a one-admin pilot, then freeze local edits and cut over production.",
        "",
        "## Safety Boundary",
        "",
        "This matrix only describes the remote permission design. It does not create users, does not grant access to admins, does not expose the local machine, does not migrate the database, and does not alter CRM records.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_admin_permissions_matrix.csv`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/hosted_database_migration_readiness.md`",
        "- `reports/local_crm_database_map.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `reports/migration_completion_audit.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_admin_permissions_matrix_rows()
    write_csv(REPORTS_DIR / "remote_admin_permissions_matrix.csv", rows)
    (REPORTS_DIR / "remote_admin_permissions_matrix.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote admin permission rows to reports/remote_admin_permissions_matrix.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
