#!/usr/bin/env python3
"""Generate cleanup decision-readiness reports for the local CRM."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"
GROUP_TYPES = [
    ("duplicate_people", "Duplicate People"),
    ("duplicate_leads", "Duplicate Leads"),
    ("lead_person_overlap", "Lead/Person Overlap"),
    ("duplicate_tags", "Duplicate Tags"),
]


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def count_rows(conn: sqlite3.Connection, sql: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return rows_to_dicts(conn.execute(sql, values).fetchall())


def handler() -> server.CRMRequestHandler:
    server.ensure_runtime_schema(DB_PATH)
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DB_PATH
    return instance


def cleanup_group_rows(app: server.CRMRequestHandler) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_type, label in GROUP_TYPES:
        export = app.export_cleanup_group_rows({"type": [group_type], "status": ["open"], "sort": ["priority"]})
        for row in export["rows"]:
            row = dict(row)
            row["group_type"] = group_type
            row["queue_label"] = label
            rows.append(row)
    return rows


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


def priority_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for row in rows:
        priority = str(row.get("priority") or "Low")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def top_groups(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            {"High": 0, "Medium": 1, "Low": 2}.get(str(row.get("priority")), 3),
            -int(row.get("review_score") or 0),
            -int(row.get("record_count") or 0),
            str(row.get("group_label") or row.get("group_key") or ""),
        ),
    )[:limit]


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = []
    lines.append("| " + " | ".join(label for _, label in columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        values = []
        for key, _ in columns:
            value = row.get(key)
            text = "" if value is None else str(value)
            values.append(text.replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        status_counts = count_rows(
            conn,
            """
            SELECT status, count(*) AS count
            FROM review_flags
            GROUP BY status
            ORDER BY status
            """,
        )
        flag_counts = count_rows(
            conn,
            """
            SELECT flag_type, status, count(*) AS count
            FROM review_flags
            GROUP BY flag_type, status
            ORDER BY flag_type, status
            """,
        )
        decision_counts = count_rows(
            conn,
            """
            SELECT group_type, decision, count(*) AS count
            FROM cleanup_group_decisions
            GROUP BY group_type, decision
            ORDER BY group_type, decision
            """,
        )
        archive_counts = count_rows(
            conn,
            """
            SELECT item_type, count(*) AS count, sum(record_id IS NOT NULL) AS linked
            FROM imported_archive_items
            GROUP BY item_type
            ORDER BY count DESC
            """,
        )

    by_type: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_type.setdefault(str(row.get("group_type")), []).append(row)

    lines = [
        "# Cleanup Decision Readiness",
        "",
        "This report summarizes the local cleanup queues after the final Zendesk optional archive import. It is a planning artifact only; no records are merged, deleted, or changed by this report.",
        "",
        "## Current State",
        "",
        "- Core CRM data is local.",
        "- Optional Zendesk archive data is local and searchable.",
        "- Cleanup is now the main human-decision area.",
        f"- Open cleanup groups: {len(rows):,}.",
        f"- Saved cleanup group decisions: {sum(int(row['count']) for row in decision_counts):,}.",
        "",
        "## Review Flag Status",
        "",
        *markdown_table(status_counts, [("status", "Status"), ("count", "Flags")]),
        "",
        "## Cleanup Workload",
        "",
        *markdown_table(flag_counts, [("flag_type", "Flag Type"), ("status", "Status"), ("count", "Flags")]),
        "",
        "## Open Group Priority",
        "",
    ]

    summary_rows = []
    for group_type, label in GROUP_TYPES:
        group_rows = by_type.get(group_type, [])
        counts = priority_counts(group_rows)
        summary_rows.append(
            {
                "group": label,
                "open_groups": len(group_rows),
                "high": counts.get("High", 0),
                "medium": counts.get("Medium", 0),
                "low": counts.get("Low", 0),
            }
        )
    lines.extend(markdown_table(summary_rows, [("group", "Queue"), ("open_groups", "Open Groups"), ("high", "High"), ("medium", "Medium"), ("low", "Low")]))

    lines.extend(
        [
            "",
            "## Top Groups To Review First",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            top_groups(rows),
            [
                ("queue_label", "Queue"),
                ("group_label", "Group"),
                ("priority", "Priority"),
                ("review_score", "Score"),
                ("record_count", "Records"),
                ("draft_keeper", "Draft Keeper"),
                ("draft_manual_review_fields", "Manual Fields"),
                ("draft_blank_field_suggestions", "Blank Fills"),
            ],
        )
    )

    lines.extend(
        [
            "",
            "## Archive Context",
            "",
            "The optional archive is imported and should be preserved during any future merge work.",
            "",
        ]
    )
    lines.extend(markdown_table(archive_counts, [("item_type", "Archive Type"), ("count", "Items"), ("linked", "Linked")]))

    lines.extend(
        [
            "",
            "## Major Decisions Needed",
            "",
            "1. Duplicate people: confirm whether same-email people should merge by default after review, and whether the draft keeper should be accepted unless manually overridden.",
            "2. Duplicate leads: confirm whether same-email leads should merge, or whether some should stay separate to preserve multiple application histories.",
            "3. Lead/person overlap: confirm whether the person should usually become the keeper and the lead should be archived/merged into history.",
            "4. Duplicate tags: confirm whether duplicate tag definitions should be consolidated into one normalized local tag without further review.",
            "5. Application Profile: decide whether promoted Application Profile fields should remain read-only views over custom fields or become editable first-class CRM fields.",
            "6. Unlinked calls/texts: decide whether to keep them searchable in Archive only, or later run a manual phone/name matching pass.",
            "",
            "## Recommended Next Action",
            "",
            "Start with high-priority Lead/Person Overlap groups, then high-priority Duplicate People groups. These have the highest chance of affecting the working client list and future merge rules.",
            "",
            "## Related Files",
            "",
            "- `reports/cleanup_review_starter_packet.md`",
            "- `reports/cleanup_review_starter_packet.csv`",
            "- `reports/cleanup_decision_readiness.csv`",
            "- `reports/local_crm_review_flags.csv`",
            "- `reports/local_crm_cleanup_merge_drafts_open.csv` from the Exports view or API",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = cleanup_group_rows(app)
    csv_path = REPORTS_DIR / "cleanup_decision_readiness.csv"
    report_path = REPORTS_DIR / "cleanup_decision_readiness.md"
    write_csv(csv_path, rows)
    report_path.write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
