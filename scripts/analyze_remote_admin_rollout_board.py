#!/usr/bin/env python3
"""Generate a read-only remote admin rollout task board."""

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
    lanes = rows_of_type(rows, "lane")
    tasks = rows_of_type(rows, "task")
    decision_prompts = rows_of_type(rows, "decision_prompt")
    verification_gates = rows_of_type(rows, "verification_gate")
    milestones = rows_of_type(rows, "milestone")

    lines = [
        "# Remote Admin Rollout Board",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only rollout board for moving the local CRM toward secure private-company remote access. Supabase/Vercel is the selected staging path; this board tracks remaining proof gates before CHILLCRM becomes the source of truth. It does not unlock writes, create users, invite internal users, save decisions, expose localhost, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Recommended path: {summary.get('recommended_path')}.",
        f"- Current blocker: {summary.get('current_blocker')}.",
        f"- Next action: {summary.get('next_action')}.",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- Tasks: {int(summary.get('task_count') or 0):,} total, {int(summary.get('ready_tasks') or 0):,} ready, {int(summary.get('waiting_tasks') or 0):,} waiting, {int(summary.get('blocked_tasks') or 0):,} blocked.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Rollout Lanes",
        "",
        *table(
            lanes,
            [
                ("order", "Order"),
                ("title", "Lane"),
                ("purpose", "Purpose"),
                ("task_count", "Tasks"),
                ("ready_count", "Ready"),
                ("blocked_count", "Blocked"),
            ],
            180,
        ),
        "",
        "## Rollout Tasks",
        "",
        *table(
            tasks,
            [
                ("order", "Order"),
                ("phase", "Phase"),
                ("title", "Task"),
                ("owner_role", "Owner Role"),
                ("priority", "Priority"),
                ("status", "Status"),
                ("dependency_keys", "Dependencies"),
                ("acceptance_criteria", "Proof"),
            ],
            180,
        ),
        "",
        "## Decision Prompts",
        "",
        *table(
            decision_prompts,
            [
                ("order", "Order"),
                ("question", "Question"),
                ("recommended_option", "Recommended"),
                ("option_a", "A"),
                ("option_b", "B"),
                ("option_c", "C"),
                ("save_boundary", "Boundary"),
            ],
            180,
        ),
        "",
        "## Verification Gates",
        "",
        *table(
            verification_gates,
            [
                ("order", "Order"),
                ("key", "Key"),
                ("gate", "Gate"),
                ("exit_criteria", "Exit Criteria"),
            ],
            180,
        ),
        "",
        "## Milestones",
        "",
        *table(
            milestones,
            [
                ("order", "Order"),
                ("title", "Milestone"),
                ("exit_criteria", "Exit Criteria"),
            ],
            180,
        ),
        "",
        "## Recommendation",
        "",
        "Use this as the active project board for the selected Supabase/Vercel path. Keep the local CRM as the source of truth until provider backup/restore evidence, hosted write-audit rehearsal, monitoring readiness, and owner-only staging shakedown pass; optional internal admin access can follow only after owner signoff.",
        "",
        "## Safety Boundary",
        "",
        "This board is tracking only. It does not unlock hosted writes, create users, invite internal users, save decisions, expose this machine, switch source of truth, or change local CRM records.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_admin_rollout_board.csv`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
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
        "- `reports/backup_safety_ledger.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_admin_rollout_board_rows()
    write_csv(REPORTS_DIR / "remote_admin_rollout_board.csv", rows)
    (REPORTS_DIR / "remote_admin_rollout_board.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} remote admin rollout rows to reports/remote_admin_rollout_board.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
