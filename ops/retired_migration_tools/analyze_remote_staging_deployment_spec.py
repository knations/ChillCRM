#!/usr/bin/env python3
"""Generate a read-only remote staging deployment specification."""

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
    deployment_targets = rows_of_type(rows, "deployment_target")
    app_specs = rows_of_type(rows, "app_service_spec")
    config_vars = rows_of_type(rows, "configuration_variable")
    deployment_inputs = rows_of_type(rows, "deployment_input")
    hardening_gaps = rows_of_type(rows, "implementation_gap")
    smoke_tests = rows_of_type(rows, "staging_smoke_test")
    owner_decisions = rows_of_type(rows, "owner_decision")
    next_steps = rows_of_type(rows, "next_step")

    lines = [
        "# Remote Staging Deployment Spec",
        "",
        f"Generated: {generated_at}",
        "",
        "This is the active hosted-staging deployment specification for turning the local CRM into an owner-approved remote CRM. It now reflects the selected Supabase data layer, seeded staging database, private document storage upload, and deployed locked Vercel staging app with signed file access while keeping admin access, backup/restore, audit, role lifecycle, and cutover as explicit gates. It does not invite admins, save decisions, expose localhost, unlock writes, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Stage: {summary.get('stage')}.",
        f"- Recommended first path: {summary.get('recommended_first_path')}.",
        f"- Alternate path: {summary.get('alternate_path')}.",
        f"- Deployment boundary: {summary.get('deployment_boundary')}.",
        f"- Current app database mode: {summary.get('current_app_database_mode')}.",
        f"- Target staging database mode: {summary.get('target_staging_database_mode')}.",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Local database size: {float(summary.get('local_database_mib') or 0):,.2f} MiB.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files totaling {float(summary.get('document_file_gib') or 0):,.3f} GiB.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Deployment Targets",
        "",
        *table(
            deployment_targets,
            [
                ("provider", "Provider"),
                ("app_service", "App Service"),
                ("database", "Database"),
                ("storage", "Storage"),
                ("recommendation", "Recommendation"),
                ("owner_gate", "Owner Gate"),
                ("status", "Status"),
            ],
            170,
        ),
        "",
        "## App Service Spec",
        "",
        *table(
            app_specs,
            [
                ("order", "Order"),
                ("item", "Item"),
                ("value", "Value"),
                ("detail", "Detail"),
                ("gate", "Gate"),
            ],
            180,
        ),
        "",
        "## Configuration Variables",
        "",
        *table(
            config_vars,
            [
                ("key", "Key"),
                ("secret", "Secret"),
                ("value_source", "Value Source"),
                ("purpose", "Purpose"),
                ("implementation_state", "State"),
            ],
            170,
        ),
        "",
        "## Deployment Inputs",
        "",
        *table(
            deployment_inputs,
            [
                ("order", "Order"),
                ("artifact", "Artifact"),
                ("contents", "Contents"),
                ("gate", "Gate"),
            ],
            170,
        ),
        "",
        "## Implementation Gaps",
        "",
        *table(
            hardening_gaps,
            [
                ("order", "Order"),
                ("gap", "Gap"),
                ("detail", "Detail"),
                ("blocks", "Blocks"),
                ("status", "Status"),
            ],
            180,
        ),
        "",
        "## Staging Smoke Tests",
        "",
        *table(
            smoke_tests,
            [
                ("order", "Order"),
                ("test", "Test"),
                ("pass_criteria", "Pass Criteria"),
                ("severity", "Severity"),
                ("status", "Status"),
            ],
            175,
        ),
        "",
        "## Owner Decisions",
        "",
        *table(
            owner_decisions,
            [
                ("order", "Order"),
                ("decision", "Decision"),
                ("recommended", "Recommended"),
                ("gate", "Gate"),
                ("status", "Status"),
            ],
            170,
        ),
        "",
        "## Next Steps",
        "",
        *table(
            next_steps,
            [
                ("order", "Order"),
                ("step", "Step"),
                ("owner_role", "Owner Role"),
                ("gate", "Gate"),
            ],
            175,
        ),
        "",
        "## Safety Boundary",
        "",
        "This spec is planning and staging tracking only. Supabase staging database rows have been loaded and the locked Vercel staging app has passed smoke, but local SQLite remains the source of truth until cutover. It does not upload document files, invite admins, save decisions, expose this machine, unlock writes, or change local CRM records. It also does not claim the current hosted app is production-ready for remote admins; private file storage, backup/restore, actor-aware audit, role hardening, and monitoring remain explicit gates.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_staging_deployment_spec.csv`",
        "- `reports/remote_staging_setup_runbook.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/remote_staging_pricing_preflight.md`",
        "- `reports/remote_managed_cloud_provider_shortlist.md`",
        "- `reports/remote_hosting_decision_packet.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/hosted_postgres_adapter_smoke.md`",
        "- `reports/hosted_app_deployment_package_verification.md`",
        "- `reports/remote_file_access_verification.md`",
        "- `scripts/verify_remote_file_access.py`",
        "- `docs/vercel_staging_setup.md`",
        "- `config/chillcrm_vercel.env.example`",
        "- `api/index.py`",
        "- `vercel.json`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_staging_deployment_spec_rows()
    write_csv(REPORTS_DIR / "remote_staging_deployment_spec.csv", rows)
    (REPORTS_DIR / "remote_staging_deployment_spec.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote staging deployment spec rows to reports/remote_staging_deployment_spec.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
