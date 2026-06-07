#!/usr/bin/env python3
"""Generate a read-only remote admin pilot onboarding plan."""

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
    roles = rows_of_type(rows, "pilot_role")
    prerequisites = rows_of_type(rows, "pilot_prerequisite")
    onboarding_steps = rows_of_type(rows, "onboarding_step")
    workflows = rows_of_type(rows, "pilot_workflow")
    permission_probes = rows_of_type(rows, "permission_probe")
    support_watch = rows_of_type(rows, "support_watch_item")
    blocker_rules = rows_of_type(rows, "pilot_blocker_rule")
    signoff_gates = rows_of_type(rows, "pilot_signoff_gate")
    next_steps = rows_of_type(rows, "next_step")

    lines = [
        "# Private CRM Owner Shakedown Plan",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only plan for the first owner-only CHILLCRM staging shakedown after hosted validation passes. It keeps the CRM private-company first, with optional internal users later only if the owner wants them. It defines roles, prerequisites, onboarding steps, workflows, permission probes, watch items, blocker rules, and signoff gates. It does not unlock writes, create accounts, invite internal users, migrate data, upload files, save decisions, expose localhost, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Stage: {summary.get('stage')}.",
        f"- Pilot size: {summary.get('pilot_size')}.",
        f"- Pilot entry gate: {summary.get('pilot_entry_gate')}.",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Local database size: {float(summary.get('local_database_mib') or 0):,.2f} MiB.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files totaling {float(summary.get('document_file_gib') or 0):,.3f} GiB.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Shakedown Roles",
        "",
        *table(
            roles,
            [
                ("role", "Role"),
                ("default_actor", "Default Actor"),
                ("responsibility", "Responsibility"),
            ],
            170,
        ),
        "",
        "## Prerequisites",
        "",
        *table(
            prerequisites,
            [
                ("order", "Order"),
                ("prerequisite", "Prerequisite"),
                ("proof", "Proof"),
                ("owner_role", "Owner Role"),
                ("blocks", "Blocks"),
                ("status", "Status"),
            ],
            170,
        ),
        "",
        "## Onboarding Steps",
        "",
        *table(
            onboarding_steps,
            [
                ("order", "Order"),
                ("step", "Step"),
                ("detail", "Detail"),
                ("owner_role", "Owner Role"),
                ("phase", "Phase"),
            ],
            170,
        ),
        "",
        "## Shakedown Workflows",
        "",
        *table(
            workflows,
            [
                ("order", "Order"),
                ("workflow", "Workflow"),
                ("detail", "Detail"),
                ("pass_criteria", "Pass Criteria"),
                ("category", "Category"),
                ("status", "Status"),
            ],
            170,
        ),
        "",
        "## Permission Probes",
        "",
        *table(
            permission_probes,
            [
                ("order", "Order"),
                ("probe", "Probe"),
                ("expected_behavior", "Expected Behavior"),
                ("proof", "Proof"),
                ("status", "Status"),
            ],
            170,
        ),
        "",
        "## Support Watch",
        "",
        *table(
            support_watch,
            [
                ("order", "Order"),
                ("watch_item", "Watch Item"),
                ("signal", "Signal"),
                ("response", "Response"),
            ],
            170,
        ),
        "",
        "## Blocker Rules",
        "",
        *table(
            blocker_rules,
            [
                ("order", "Order"),
                ("trigger", "Trigger"),
                ("response", "Response"),
                ("evidence_source", "Evidence Source"),
            ],
            170,
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
            170,
        ),
        "",
        "## Safety Boundary",
        "",
        "This plan is tracking only. It does not unlock hosted writes, create users, invite internal users, upload files, save decisions, expose this machine, switch source of truth, or change local CRM records. Optional internal-user access happens only after owner approval and passing staging validation gates.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_admin_pilot_onboarding_plan.csv`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_staging_setup_runbook.md`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/remote_staging_pricing_preflight.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/remote_admin_rollout_board.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_admin_pilot_onboarding_plan_rows()
    write_csv(REPORTS_DIR / "remote_admin_pilot_onboarding_plan.csv", rows)
    (REPORTS_DIR / "remote_admin_pilot_onboarding_plan.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote admin pilot onboarding rows to reports/remote_admin_pilot_onboarding_plan.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
