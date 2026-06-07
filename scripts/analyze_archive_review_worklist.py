#!/usr/bin/env python3
"""Generate a printable Archive Review worklist for unlinked calls/texts."""

from __future__ import annotations

import csv
import sys
from collections import Counter
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
            values.append(clip(row.get(key), 140).replace("|", "/"))
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


def archive_linkage_rows(app: server.CRMRequestHandler) -> list[dict[str, Any]]:
    with app.db() as conn:
        return server.rows_to_dicts(
            conn.execute(
                """
                SELECT item_type,
                       COUNT(*) AS total,
                       SUM(CASE WHEN record_id IS NOT NULL THEN 1 ELSE 0 END) AS linked,
                       SUM(CASE WHEN record_id IS NULL THEN 1 ELSE 0 END) AS unlinked
                FROM imported_archive_items
                GROUP BY item_type
                ORDER BY total DESC
                """
            ).fetchall()
        )


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    top_numbers = [row for row in rows if row.get("row_type") == "top_number"]
    work_items = [row for row in rows if row.get("row_type") == "archive_item"]
    status_counts = Counter(str(row.get("review_status") or "unreviewed") for row in work_items)
    linkage_rows = archive_linkage_rows(app)
    item_counts = Counter(str(row.get("item_type") or "") for row in work_items)
    lines = [
        "# Archive Review Worklist",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning and review report only. It does not save review status, link archive items, merge records, delete records, or update Zendesk Sell.",
        "",
        "## Linkage Progress",
        "",
        *table(
            linkage_rows,
            [
                ("item_type", "Archive Type"),
                ("total", "Total"),
                ("linked", "Linked"),
                ("unlinked", "Unlinked"),
            ],
        ),
        "",
        "## Calls/Text Review Summary",
        "",
        f"- Unlinked calls/texts in this worklist: {summary.get('total', len(work_items)):,}.",
        f"- Calls: {item_counts.get('call', 0):,}.",
        f"- Text messages: {item_counts.get('text_message', 0):,}.",
        f"- Unreviewed: {summary.get('unreviewed', status_counts.get('unreviewed', 0)):,}.",
        f"- Needs lookup: {summary.get('needs_lookup', status_counts.get('needs_lookup', 0)):,}.",
        f"- Ready to link: {summary.get('ready_to_link', status_counts.get('ready_to_link', 0)):,}.",
        f"- Archive-only reviewed: {summary.get('archive_only', status_counts.get('archive_only', 0)):,}.",
        f"- Current recommendation: {summary.get('recommendation') or 'Review manually before linking.'}",
        f"- Reason: {summary.get('reason') or 'Calls/texts require stronger evidence than the remaining phone metadata provides.'}",
        "",
        "## Highest-Volume Unlinked Numbers",
        "",
        *table(
            top_numbers,
            [
                ("item_type", "Type"),
                ("phone_number", "Phone"),
                ("classification", "Classification"),
                ("item_count", "Items"),
                ("reviewed_count", "Reviewed"),
                ("first_at", "First"),
                ("last_at", "Last"),
            ],
            limit=30,
        ),
        "",
        "## First Review Items",
        "",
        *table(
            work_items,
            [
                ("archive_item_id", "Archive ID"),
                ("review_status_label", "Review"),
                ("item_type", "Type"),
                ("phone_number", "Phone"),
                ("occurred_at", "Occurred"),
                ("title", "Title"),
                ("body", "Body"),
                ("recommended_action", "Recommended Action"),
            ],
            limit=40,
        ),
        "",
        "## Working Guidance",
        "",
        "1. Start in Archive with the Unreviewed queue and use Save & Next.",
        "2. Mark each item Archive-only, Needs Lookup, or Ready to Link before attempting any link.",
        "3. Link only from the Archive inspector after the target person, company, lead, or deal is confirmed.",
        "4. Treat the 203 downloaded document files differently: they are already associated with local person records and have a separate document-file package.",
        "5. Keep the matching candidate report nearby for evidence, but do not infer matches from weak phone evidence alone.",
        "",
        "## Related Files",
        "",
        "- `reports/archive_review_worklist.csv`",
        "- `reports/archive_review_triage.md`",
        "- `reports/unlinked_archive_matching_candidates.md`",
        "- `reports/daily_operating_guide.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_archive_review_worklist_rows()
    write_csv(REPORTS_DIR / "archive_review_worklist.csv", rows)
    (REPORTS_DIR / "archive_review_worklist.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} archive review worklist rows to reports/archive_review_worklist.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
