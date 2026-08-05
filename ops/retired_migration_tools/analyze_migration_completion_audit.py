#!/usr/bin/env python3
"""Generate an end-to-end migration completion audit."""

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


def clip(value: Any, limit: int = 140) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


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
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    requirements = [row for row in rows if row.get("row_type") == "requirement"]
    readiness = [row for row in rows if row.get("row_type") == "readiness_check"]
    gates = [row for row in rows if row.get("row_type") == "remaining_gate"]
    lines = [
        "# Migration Completion Audit",
        "",
        f"Generated: {generated_at}",
        "",
        "This is an audit/report only. It does not save decisions, merge records, delete records, link archive items, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Overall status: {summary.get('overall_status') or 'unknown'}.",
        f"- Core records: {summary.get('core_records', 0):,}.",
        f"- Deals: {summary.get('deals', 0):,}.",
        f"- Archive items: {summary.get('archive_items', 0):,}.",
        f"- Linked resources: {summary.get('linked_resources', 0):,}.",
        f"- Reports ready: {summary.get('reports_ready', 0):,} of {summary.get('reports_total', 0):,}.",
        f"- Export packages ready: {summary.get('export_packages_ready', 0):,} of {summary.get('export_packages_total', 0):,}.",
        f"- Backups available: {summary.get('backups_available', 0):,}.",
        f"- Pending project decisions: {summary.get('pending_project_decisions', 0):,}.",
        f"- Deferred project decisions: {summary.get('deferred_project_decisions', 0):,}.",
        f"- Open cleanup groups: {summary.get('open_cleanup_groups', 0):,}.",
        f"- Next action: {summary.get('next_action') or 'n/a'}.",
        "",
        "## Requirement Audit",
        "",
        *table(
            requirements,
            [
                ("order", "Order"),
                ("title", "Requirement"),
                ("status", "Status"),
                ("evidence", "Evidence"),
                ("proof", "Proof"),
                ("next_step", "Next Step"),
            ],
        ),
        "",
        "## Readiness Checklist",
        "",
        *table(
            readiness,
            [
                ("order", "Order"),
                ("title", "Check"),
                ("status", "Status"),
                ("detail", "Detail"),
                ("action", "Action"),
            ],
        ),
        "",
        "## Remaining Gates",
        "",
        *table(
            gates,
            [
                ("order", "Order"),
                ("title", "Gate"),
                ("status", "Status"),
                ("detail", "Detail"),
                ("report", "Evidence"),
            ],
        ),
        "",
        "## Recommendation",
        "",
        "Treat the local CRM as operational for ordinary local work, exports, archive search, follow-up, and data review. Do not call the migration fully complete until the remaining major Project Decisions are saved, cleanup review policies are settled, and the open cleanup/data-quality gates are either resolved or intentionally deferred.",
        "",
        "## Related Files",
        "",
        "- `reports/local_crm_verification.md`",
        "- `reports/project_decision_option_matrix.md`",
        "- `reports/cleanup_execution_safety_plan.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `reports/daily_operating_guide.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    app = handler()
    rows = app.export_migration_completion_audit_rows()
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "migration_completion_audit.csv", rows)
    (REPORTS_DIR / "migration_completion_audit.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} completion audit rows to reports/migration_completion_audit.md and .csv")


if __name__ == "__main__":
    main()
