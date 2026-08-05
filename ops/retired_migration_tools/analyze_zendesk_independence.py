#!/usr/bin/env python3
"""Generate a read-only Zendesk independence checklist."""

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


def filter_rows(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = filter_rows(rows, "summary")[0]
    requirements = filter_rows(rows, "requirement")
    preserve_items = filter_rows(rows, "preserve_item")
    boundaries = filter_rows(rows, "boundary")
    lines = [
        "# Zendesk Independence Checklist",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only checklist for operating locally without relying on Zendesk Sell. It does not contact Zendesk, save decisions, merge records, delete records, link archive items, resolve cleanup flags, or update CRM data.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Latest snapshot: `{summary.get('snapshot_name')}`.",
        f"- Optional sweep: {summary.get('optional_sweep_status')}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive items: {int(summary.get('archive_items') or 0):,}.",
        f"- Linked resources: {int(summary.get('linked_resources') or 0):,}.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}.",
        f"- Export packages ready: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,}.",
        f"- Backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending decisions, {int(summary.get('deferred_project_decisions') or 0):,} deferred decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Independence Requirements",
        "",
        *table(
            requirements,
            [
                ("order", "Order"),
                ("title", "Requirement"),
                ("status", "Status"),
                ("evidence", "Evidence"),
                ("next_step", "Next Step"),
                ("proof", "Proof"),
            ],
        ),
        "",
        "## Preserve Before Decommission",
        "",
        *table(
            preserve_items,
            [
                ("order", "Order"),
                ("path", "Path"),
                ("title", "Artifact"),
                ("handling", "Handling"),
            ],
        ),
        "",
        "## Zendesk Access Boundary",
        "",
        *table(
            boundaries,
            [
                ("order", "Order"),
                ("title", "Boundary"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Recommendation",
        "",
        "Use the local CRM as the working system. Keep Zendesk exports, document files, backups, reports, and project docs preserved. Do not cancel or delete Zendesk-side access until you have downloaded the Complete Local CRM Package and Downloaded Document Files package and decided whether you want one final deliberate API re-check.",
        "",
        "## Related Files",
        "",
        "- `reports/zendesk_independence_checklist.csv`",
        "- `reports/migration_completion_audit.md`",
        "- `reports/local_crm_database_map.md`",
        "- `reports/backup_safety_ledger.md`",
        "- `reports/daily_operating_guide.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_zendesk_independence_rows()
    write_csv(REPORTS_DIR / "zendesk_independence_checklist.csv", rows)
    (REPORTS_DIR / "zendesk_independence_checklist.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} independence checklist rows to reports/zendesk_independence_checklist.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
