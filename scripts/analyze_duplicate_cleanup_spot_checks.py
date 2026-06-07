#!/usr/bin/env python3
"""Generate read-only duplicate people/leads policy spot checks."""

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


CONFIGS = [
    {
        "title": "Duplicate People Spot Check",
        "filename": "duplicate_people_spot_check",
        "export_method": "export_duplicate_people_spot_check_rows",
        "decision_label": "Duplicate people merge policy",
        "queue_label": "Duplicate People",
        "why_a": [
            "People are the working client/contact records, so duplicates should be reviewed with a clear keeper.",
            "The guided path uses the draft keeper only as a starting point; it does not merge anything automatically.",
            "Notes, tasks, tags, addresses, archive links, linked resources, and custom fields stay preservation requirements.",
            "Each duplicate people group still needs a group-level review decision before any future merge preview can include it.",
        ],
        "related": [
            "reports/duplicate_people_spot_check.csv",
            "reports/cleanup_merge_review_pack.md",
            "reports/cleanup_review_starter_packet.md",
            "reports/project_decision_option_matrix.md",
            "reports/cleanup_execution_safety_plan.md",
        ],
    },
    {
        "title": "Duplicate Leads Spot Check",
        "filename": "duplicate_leads_spot_check",
        "export_method": "export_duplicate_leads_spot_check_rows",
        "decision_label": "Duplicate leads merge policy",
        "queue_label": "Duplicate Leads",
        "why_a": [
            "Duplicate leads may be repeated applications, separate funnel history, or true duplicates, so they need guided review.",
            "The guided path allows reviewed groups to become eligible later without treating every same-email lead as automatically mergeable.",
            "Application Profile values and lead history stay visible as review signals before any future merge preview.",
            "Each duplicate lead group still needs a group-level review decision before any future merge preview can include it.",
        ],
        "related": [
            "reports/duplicate_leads_spot_check.csv",
            "reports/cleanup_merge_review_pack.md",
            "reports/cleanup_review_starter_packet.md",
            "reports/project_decision_option_matrix.md",
            "reports/cleanup_execution_safety_plan.md",
        ],
    },
]


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


def generate_report(rows: list[dict[str, Any]], config: dict[str, Any]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = first_row(rows, "summary")
    option_rows = filter_rows(rows, "option")
    group_rows = filter_rows(rows, "group")
    current_status = summary.get("decision_status") or "pending"
    current_choice = summary.get("current_choice_label") or "No saved path"
    recommendation = summary.get("recommendation") or "Guided review, then merge"

    lines = [
        f"# {config['title']}",
        "",
        f"Generated: {generated_at}",
        "",
        f"Use this report as the focused evidence page before saving the {config['decision_label']}. It is read-only and does not save the project decision, merge records, delete records, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Current project decision: {str(current_status).title()} / {current_choice}.",
        f"- Recommendation: {recommendation}.",
        f"- Open groups: {int(summary.get('open_groups') or 0):,}.",
        f"- High-priority groups: {int(summary.get('high_priority_groups') or 0):,}.",
        f"- Medium-priority groups: {int(summary.get('medium_priority_groups') or 0):,}.",
        f"- Records involved: {int(summary.get('record_count') or 0):,}.",
        f"- Blank-field suggestions: {int(summary.get('blank_field_suggestions') or 0):,}.",
        f"- Manual review fields: {int(summary.get('manual_review_fields') or 0):,}.",
        f"- History signals to preserve: {int(summary.get('history_signals') or 0):,}.",
        f"- CSV export: `{summary.get('export_url')}`.",
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
    ]
    lines.extend(f"- {item}" for item in config["why_a"])
    lines.extend(
        [
            "",
            "## Starting Groups",
            "",
            *table(
                group_rows,
                [
                    ("group_label", "Email"),
                    ("priority", "Priority"),
                    ("record_count", "Records"),
                    ("draft_keeper", "Draft Keeper"),
                    ("manual_review_fields", "Manual Fields"),
                    ("history_signals", "History Signals"),
                    ("policy_lane_label", "Lane"),
                ],
                limit=18,
            ),
            "",
            "## Review Signals",
            "",
            *table(
                group_rows,
                [
                    ("group_label", "Email"),
                    ("sample_names", "Sample Names"),
                    ("reasons", "Reasons"),
                    ("policy_action", "Suggested Review Action"),
                ],
                limit=18,
            ),
            "",
            "## Save Boundary",
            "",
            "- Saving this Project Decision creates a local backup first.",
            f"- A saved {config['decision_label']} records intent in Project Decisions, Activity, and the audit log.",
            "- Saving the policy does not merge records, delete records, resolve cleanup flags, or rewrite CRM values.",
            "- Group-level decisions such as Merge Later are still separate review actions and also do not execute a merge by themselves.",
            "",
            "## Related Files",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in config["related"])
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    for config in CONFIGS:
        rows = getattr(app, config["export_method"])()
        stem = str(config["filename"])
        write_csv(REPORTS_DIR / f"{stem}.csv", rows)
        (REPORTS_DIR / f"{stem}.md").write_text(generate_report(rows, config), encoding="utf-8")
        print(f"Wrote {len(rows):,} rows to reports/{stem}.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
