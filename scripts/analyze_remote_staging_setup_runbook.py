#!/usr/bin/env python3
"""Generate a read-only remote staging setup runbook."""

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
    provider_paths = rows_of_type(rows, "provider_path")
    phases = rows_of_type(rows, "staging_phase")
    setup_tasks = rows_of_type(rows, "setup_task")
    env_vars = rows_of_type(rows, "environment_variable")
    verification_gates = rows_of_type(rows, "verification_gate")
    approval_gates = rows_of_type(rows, "approval_gate")
    sources = rows_of_type(rows, "official_source")
    next_steps = rows_of_type(rows, "next_step")

    lines = [
        "# Remote Staging Setup Runbook",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only setup runbook for the first hosted staging CRM. It defines the DigitalOcean and Railway staging paths, phases, setup tasks, environment variables, validation gates, and approval gates. It does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Decision needed: {summary.get('decision_needed')}.",
        f"- Recommended first path: {summary.get('recommended_first_path')}.",
        f"- Alternate path: {summary.get('alternate_path')}.",
        f"- Source basis: {summary.get('source_basis')}",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Local database size: {float(summary.get('local_database_mib') or 0):,.2f} MiB.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files totaling {float(summary.get('document_file_gib') or 0):,.3f} GiB.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Provider Paths",
        "",
        *table(
            provider_paths,
            [
                ("provider", "Provider"),
                ("stack", "Stack"),
                ("recommendation", "Recommendation"),
                ("setup_shape", "Setup Shape"),
                ("owner_gate", "Owner Gate"),
                ("watch_item", "Watch Item"),
            ],
            170,
        ),
        "",
        "## Staging Phases",
        "",
        *table(
            phases,
            [
                ("order", "Order"),
                ("phase", "Phase"),
                ("detail", "Detail"),
                ("gate", "Gate"),
            ],
            170,
        ),
        "",
        "## Setup Tasks",
        "",
        *table(
            setup_tasks,
            [
                ("order", "Order"),
                ("provider", "Provider"),
                ("task", "Task"),
                ("owner_role", "Owner Role"),
                ("detail", "Detail"),
                ("phase_key", "Phase"),
            ],
            170,
        ),
        "",
        "## Environment Variables",
        "",
        *table(
            env_vars,
            [
                ("key", "Key"),
                ("scope", "Scope"),
                ("secret", "Secret"),
                ("required_for_staging", "Required"),
                ("value_source", "Value Source"),
                ("purpose", "Purpose"),
            ],
            170,
        ),
        "",
        "## Verification Gates",
        "",
        *table(
            verification_gates,
            [
                ("order", "Order"),
                ("gate", "Gate"),
                ("proof", "Proof"),
            ],
            170,
        ),
        "",
        "## Approval Gates",
        "",
        *table(
            approval_gates,
            [
                ("order", "Order"),
                ("gate", "Gate"),
                ("proof", "Proof"),
            ],
            170,
        ),
        "",
        "## Official Sources",
        "",
        *table(
            sources,
            [
                ("source_name", "Source"),
                ("supports", "Supports"),
                ("source_url", "URL"),
            ],
            220,
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
            170,
        ),
        "",
        "## Safety Boundary",
        "",
        "This runbook is planning only. It does not choose a provider, provision hosting, create accounts, enter payment details, create a remote database, upload files, create users, invite admins, save decisions, expose this machine, or change local CRM records. Actual secret values belong only in the selected provider's secret/variable manager.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_staging_setup_runbook.csv`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/remote_staging_pricing_preflight.md`",
        "- `reports/remote_managed_cloud_provider_shortlist.md`",
        "- `reports/remote_hosting_decision_packet.md`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/remote_admin_rollout_board.md`",
        "- `reports/hosted_database_migration_readiness.md`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_staging_setup_runbook_rows()
    write_csv(REPORTS_DIR / "remote_staging_setup_runbook.csv", rows)
    (REPORTS_DIR / "remote_staging_setup_runbook.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote staging setup rows to reports/remote_staging_setup_runbook.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
