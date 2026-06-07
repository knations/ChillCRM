#!/usr/bin/env python3
"""Generate a read-only duplicate leads review worksheet."""

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


def first_row(rows: list[dict[str, Any]], row_type: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("row_type") == row_type), {})


def filter_rows(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = first_row(rows, "summary")
    lane_rows = filter_rows(rows, "lane_summary")
    decision_rows = filter_rows(rows, "decision_summary")
    instruction_rows = filter_rows(rows, "instruction")
    group_rows = filter_rows(rows, "group")
    high_groups = [row for row in group_rows if str(row.get("priority") or "").lower() == "high"]

    lines = [
        "# Duplicate Leads Review Worksheet",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only working packet for duplicate-lead cleanup review. It does not save the project policy, save group decisions, merge records, delete records, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Current project decision: {str(summary.get('decision_status') or 'pending').title()} / {summary.get('current_choice_label') or 'No saved path'}.",
        f"- Recommendation: {summary.get('recommendation') or 'Guided review, then merge'}.",
        f"- Open duplicate-lead groups: {int(summary.get('open_groups') or 0):,}.",
        f"- Review remaining: {int(summary.get('review_remaining') or 0):,}.",
        f"- High-priority groups: {int(summary.get('high_priority_groups') or 0):,}.",
        f"- Lead records involved: {int(summary.get('records_involved') or 0):,}.",
        f"- Blank-field suggestions: {int(summary.get('blank_field_suggestions') or 0):,}.",
        f"- Manual review fields: {int(summary.get('manual_review_fields') or 0):,}.",
        f"- History signals to preserve: {int(summary.get('history_signals') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
        f"- Deep merge-draft export: `{summary.get('deep_draft_export_url')}`.",
        "",
        "## How To Use",
        "",
        *table(instruction_rows, [("order", "Order"), ("title", "Step"), ("detail", "Why")]),
        "",
        "## Queue Summary",
        "",
        *table(lane_rows, [("lane", "Lane"), ("group_count", "Groups")]),
        "",
        "## Decision Progress",
        "",
        *table(decision_rows, [("decision_label", "Decision"), ("group_count", "Groups")]),
        "",
        "## First High-Priority Groups",
        "",
        *table(
            high_groups,
            [
                ("review_order", "Order"),
                ("group_label", "Email"),
                ("record_count", "Records"),
                ("draft_keeper", "Draft Keeper"),
                ("manual_review_fields", "Manual Fields"),
                ("history_signals", "History Signals"),
                ("policy_lane_label", "Lane"),
                ("current_group_decision_label", "Current Decision"),
            ],
            limit=18,
        ),
        "",
        "## Worksheet Columns",
        "",
        *table(
            group_rows,
            [
                ("review_order", "Order"),
                ("group_label", "Email"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("draft_keeper", "Draft Keeper"),
                ("profile_summary", "Application Profile"),
                ("conflict_summary", "Review Fields"),
                ("history_summary", "History To Preserve"),
                ("reviewer_choice", "Reviewer Choice"),
                ("reviewer_notes", "Reviewer Notes"),
            ],
            limit=30,
        ),
        "",
        "## Safety Boundary",
        "",
        "- The worksheet is evidence only; it does not save the duplicate leads policy.",
        "- Group-level decisions still require opening the Cleanup group and saving an explicit local decision.",
        "- Group-level decisions create a backup and audit entry, but still do not merge records.",
        "- Future lead merge execution should remain disabled until a fresh backup, exact affected counts, undo path, and final confirmation exist.",
        "",
        "## Related Files",
        "",
        "- `reports/duplicate_leads_review_worksheet.csv`",
        "- `reports/duplicate_leads_spot_check.md`",
        "- `reports/cleanup_merge_review_pack.md`",
        "- `reports/cleanup_review_starter_packet.md`",
        "- `reports/cleanup_execution_safety_plan.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_duplicate_leads_review_worksheet_rows()
    write_csv(REPORTS_DIR / "duplicate_leads_review_worksheet.csv", rows)
    (REPORTS_DIR / "duplicate_leads_review_worksheet.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} duplicate leads worksheet rows to reports/duplicate_leads_review_worksheet.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
