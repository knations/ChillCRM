#!/usr/bin/env python3
"""Generate a read-only remote production cutover checklist."""

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
    phases = rows_of_type(rows, "cutover_phase")
    checklist = rows_of_type(rows, "checklist_item")
    rollback_triggers = rows_of_type(rows, "rollback_trigger")
    monitoring_checks = rows_of_type(rows, "monitoring_check")
    communications = rows_of_type(rows, "communication")
    signoff_gates = rows_of_type(rows, "signoff_gate")
    next_steps = rows_of_type(rows, "next_step")

    lines = [
        "# Remote Production Cutover Checklist",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only production cutover checklist for moving from the local CRM to the hosted private-company CRM after staging validation, Supabase backup/restore proof, hosted write-audit rehearsal, and owner shakedown are complete. It defines the freeze, final package, production load, validation, owner/internal handoff, rollback, monitoring, communication, and signoff gates. It does not unlock hosted writes, create accounts, invite internal users, migrate data, upload files, save decisions, expose localhost, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Stage: {summary.get('stage')}.",
        f"- Cutover entry gate: {summary.get('cutover_entry_gate')}.",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Source of truth after cutover: {summary.get('source_of_truth_after_cutover')}.",
        f"- Local database size: {float(summary.get('local_database_mib') or 0):,.2f} MiB.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files totaling {float(summary.get('document_file_gib') or 0):,.3f} GiB.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Cutover Phases",
        "",
        *table(
            phases,
            [
                ("order", "Order"),
                ("phase", "Phase"),
                ("detail", "Detail"),
            ],
            170,
        ),
        "",
        "## Checklist",
        "",
        *table(
            checklist,
            [
                ("order", "Order"),
                ("item", "Item"),
                ("proof", "Proof"),
                ("phase_key", "Phase"),
                ("owner_role", "Owner Role"),
                ("status", "Status"),
            ],
            175,
        ),
        "",
        "## Rollback Triggers",
        "",
        *table(
            rollback_triggers,
            [
                ("order", "Order"),
                ("trigger", "Trigger"),
                ("response", "Response"),
                ("severity", "Severity"),
            ],
            175,
        ),
        "",
        "## First-Week Monitoring",
        "",
        *table(
            monitoring_checks,
            [
                ("order", "Order"),
                ("check", "Check"),
                ("proof", "Proof"),
                ("cadence", "Cadence"),
                ("status", "Status"),
            ],
            175,
        ),
        "",
        "## Communication Plan",
        "",
        *table(
            communications,
            [
                ("order", "Order"),
                ("message", "Message"),
                ("detail", "Detail"),
                ("timing", "Timing"),
                ("owner_role", "Owner Role"),
            ],
            175,
        ),
        "",
        "## Signoff Gates",
        "",
        *table(
            signoff_gates,
            [
                ("order", "Order"),
                ("gate", "Gate"),
                ("criteria", "Criteria"),
                ("owner_role", "Owner Role"),
            ],
            175,
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
        "This checklist is tracking only. It does not unlock hosted writes, create users, invite internal users, save decisions, expose this machine, switch source of truth, or change local CRM records. The production cutover happens only after explicit owner approval, final package creation, repeated validation, provider backup/restore proof, and rollback readiness.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_production_cutover_checklist.csv`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_staging_setup_runbook.md`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_migration_readiness.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `reports/migration_completion_audit.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_production_cutover_checklist_rows()
    write_csv(REPORTS_DIR / "remote_production_cutover_checklist.csv", rows)
    (REPORTS_DIR / "remote_production_cutover_checklist.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote production cutover rows to reports/remote_production_cutover_checklist.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
