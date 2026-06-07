#!/usr/bin/env python3
"""Generate a read-only Archive Review triage packet."""

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


def clip(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> list[str]:
    visible_rows = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), 150).replace("|", "/"))
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


def rows_of_type(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    lane_rows = rows_of_type(rows, "lane_summary")
    status_rows = rows_of_type(rows, "suggested_status_summary")
    group_rows = rows_of_type(rows, "top_group")
    item_rows = rows_of_type(rows, "archive_item")

    lines = [
        "# Archive Review Triage",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only triage packet for unlinked calls/texts. It does not save review status, link archive items, merge records, delete records, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Total unlinked calls/texts: {int(summary.get('total') or 0):,}.",
        f"- Unreviewed: {int(summary.get('unreviewed') or 0):,}.",
        f"- Report: `{summary.get('report') or '/reports/archive_review_triage.md'}`.",
        f"- CSV export: `{summary.get('export_url') or '/api/export?type=archive_review_triage'}`.",
        f"- Safety: {summary.get('safety') or 'Read-only triage.'}",
        "",
        "## Triage Lanes",
        "",
        *table(
            lane_rows,
            [
                ("triage_lane_label", "Lane"),
                ("count", "Items"),
                ("suggested_action", "Suggested Action"),
            ],
        ),
        "",
        "## Suggested Review Status",
        "",
        *table(
            status_rows,
            [
                ("suggested_status_label", "Suggested Status"),
                ("count", "Items"),
            ],
        ),
        "",
        "## Top Triage Groups",
        "",
        *table(
            group_rows,
            [
                ("rank", "Rank"),
                ("triage_lane_label", "Lane"),
                ("suggested_status_label", "Suggested Status"),
                ("item_type", "Type"),
                ("phone_number", "Phone"),
                ("item_count", "Items"),
                ("reason", "Reason"),
                ("signals", "Signals"),
            ],
            limit=30,
        ),
        "",
        "## First Triage Items",
        "",
        *table(
            item_rows,
            [
                ("archive_item_id", "Archive ID"),
                ("triage_lane_label", "Lane"),
                ("suggested_status_label", "Suggested Status"),
                ("phone_number", "Phone"),
                ("occurred_at", "Occurred"),
                ("title", "Title"),
                ("reason", "Reason"),
                ("body", "Body"),
            ],
            limit=40,
        ),
        "",
        "## How To Use",
        "",
        "1. Open Archive and start with the unreviewed calls/texts queue.",
        "2. Use the Archive triage lane filter to open a lane such as Likely archive-only or Needs lookup.",
        "3. Use the triage lane as a review suggestion only; it does not save anything.",
        "4. For likely archive-only groups, inspect enough examples before saving Archive-only reviewed from the sidebar.",
        "5. For needs-lookup groups, look for outside identity evidence before linking.",
        "6. Use Link Archive Item only after the local person, company, lead, or deal is confirmed.",
        "",
        "## Related Files",
        "",
        "- `reports/archive_review_triage.csv`",
        "- `reports/archive_review_worklist.md`",
        "- `reports/archive_association_audit.md`",
        "- `reports/unlinked_archive_matching_candidates.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_archive_review_triage_rows()
    write_csv(REPORTS_DIR / "archive_review_triage.csv", rows)
    (REPORTS_DIR / "archive_review_triage.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} archive triage rows to reports/archive_review_triage.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
