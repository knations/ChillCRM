#!/usr/bin/env python3
"""Generate a read-only lead/person overlap decision spot check."""

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


def first_row(rows: list[dict[str, Any]], row_type: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("row_type") == row_type), {})


def filter_rows(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = first_row(rows, "summary")
    option_rows = filter_rows(rows, "option")
    group_rows = filter_rows(rows, "group")
    current_status = summary.get("decision_status") or "pending"
    current_choice = summary.get("current_choice_label") or "No saved path"
    recommendation = summary.get("recommendation") or "Person keeper, preserve lead history"

    lines = [
        "# Lead/Person Overlap Spot Check",
        "",
        f"Generated: {generated_at}",
        "",
        "Use this report as the focused evidence page before saving the Lead/person overlap policy. It is read-only and does not save the project decision, merge records, delete records, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Current project decision: {str(current_status).title()} / {current_choice}.",
        f"- Recommendation: {recommendation}.",
        f"- Open overlap groups: {int(summary.get('open_groups') or 0):,}.",
        f"- High-priority groups: {int(summary.get('high_priority_groups') or 0):,}.",
        f"- Records involved: {int(summary.get('record_count') or 0):,} total, {int(summary.get('people_count') or 0):,} people, {int(summary.get('lead_count') or 0):,} leads.",
        f"- Person draft keepers: {int(summary.get('person_keeper_drafts') or 0):,}.",
        f"- Blank-field suggestions: {int(summary.get('blank_field_suggestions') or 0):,}.",
        f"- Manual review fields: {int(summary.get('manual_review_fields') or 0):,}.",
        f"- History signals to preserve: {int(summary.get('history_signals') or 0):,}.",
        f"- CSV export: `{summary.get('export_url') or '/api/export?type=lead_person_overlap_spot_check'}`.",
        "",
        "## Decision Prompt",
        "",
        "Answer A, B, or C in Status when you are ready. This report does not save the decision.",
        "",
        *table(
            option_rows,
            [
                ("option_display", "Choice"),
                ("recommended", "Recommended"),
                ("description", "Meaning"),
                ("tradeoff", "Tradeoff"),
                ("after_save", "After Save"),
            ],
        ),
        "",
        "## Why A Is Recommended",
        "",
        "- People are the natural ongoing client records in the local CRM.",
        "- Lead data can remain preserved as application and funnel history instead of being discarded.",
        "- Every overlap group still requires human group-level review before any future merge execution can include it.",
        "- Saving this policy only records intent and creates a backup; it does not merge the five groups.",
        "",
        "## Overlap Groups",
        "",
        *table(
            group_rows,
            [
                ("group_label", "Email"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("draft_keeper", "Draft Keeper"),
                ("blank_field_suggestions", "Blank Fills"),
                ("manual_review_fields", "Manual Fields"),
                ("history_signals", "History Signals"),
            ],
        ),
        "",
        "## Field Review Signals",
        "",
        *table(
            group_rows,
            [
                ("group_label", "Email"),
                ("record_summary", "Records"),
                ("conflict_summary", "Conflicts"),
                ("fill_summary", "Blank Fills"),
                ("history_summary", "History To Preserve"),
            ],
        ),
        "",
        "## Save Boundary",
        "",
        "- Saving this Project Decision creates a local backup first.",
        "- A saved Lead/person overlap policy records intent in Project Decisions, Activity, and the audit log.",
        "- Saving the policy does not merge people/leads, delete records, resolve cleanup flags, or rewrite CRM values.",
        "- Group-level decisions such as Merge Later are still separate review actions and also do not execute a merge by themselves.",
        "",
        "## Related Files",
        "",
        "- `reports/lead_person_overlap_spot_check.csv`",
        "- `reports/cleanup_merge_review_pack.md`",
        "- `reports/cleanup_review_starter_packet.md`",
        "- `reports/project_decision_option_matrix.md`",
        "- `reports/cleanup_execution_safety_plan.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_lead_person_overlap_spot_check_rows()
    write_csv(REPORTS_DIR / "lead_person_overlap_spot_check.csv", rows)
    (REPORTS_DIR / "lead_person_overlap_spot_check.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} lead/person overlap spot-check rows to reports/lead_person_overlap_spot_check.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
