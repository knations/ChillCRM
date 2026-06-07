#!/usr/bin/env python3
"""Generate a compact A/B/C option matrix for remaining project decisions."""

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


def clip(value: Any, limit: int = 130) -> str:
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


def grouped_options(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    options = [row for row in rows if row.get("row_type") == "option"]
    grouped: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for row in options:
        key = str(row.get("decision_key") or "")
        if key not in grouped:
            grouped[key] = (row, [])
        grouped[key][1].append(row)
    return list(grouped.values())


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    groups = grouped_options(rows)
    lines = [
        "# Project Decision Option Matrix",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a comparison matrix only. It does not save choices, prefill forms, merge records, delete records, resolve cleanup flags, link archive items, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Remaining decisions: {summary.get('remaining_decisions', 0):,}.",
        f"- Pending: {summary.get('pending', 0):,}.",
        f"- Deferred: {summary.get('deferred', 0):,}.",
        f"- Decided: {summary.get('decided', 0):,}.",
        f"- CSV export: `{summary.get('export_url') or '/api/export?type=project_decision_option_matrix'}`.",
        "",
        "## Recommended Choices At A Glance",
        "",
        *table(
            [option for _, options in groups for option in options if option.get("recommended") == "yes"],
            [
                ("step", "Step"),
                ("decision_title", "Decision"),
                ("option_display", "Recommended"),
                ("recommended_timing", "Timing"),
                ("why_recommended", "Why"),
                ("evidence_report", "Evidence"),
                ("worksheet_report", "Worksheet"),
            ],
        ),
        "",
    ]
    for lead, options in groups:
        lines.extend(
            [
                f"## Step {lead.get('step')}: {lead.get('decision_title')}",
                "",
                f"- Status: {lead.get('status_label') or lead.get('status')}.",
                f"- Phase: {lead.get('phase')}.",
                f"- Question: {lead.get('question')}",
                f"- Impact: {lead.get('impact_summary')}",
                f"- Facts: {lead.get('fact_summary')}",
                f"- Evidence: `{lead.get('evidence_report') or ''}`",
                f"- Worksheet: `{lead.get('worksheet_report') or ''}`" if lead.get("worksheet_report") else "",
                "",
                *table(
                    options,
                    [
                        ("option_display", "Choice"),
                        ("choice_position", "Role"),
                        ("tradeoff", "Tradeoff"),
                        ("after_save", "After Save"),
                    ],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## How To Use",
            "",
            "1. Review the first active pending decision unless you intentionally want to skip it.",
            "2. Reply with A, B, or C only when you are ready to save that exact decision.",
            "3. Saving still happens from Status and creates a local backup first.",
            "",
            "## Related Files",
            "",
            "- `reports/project_decision_option_matrix.csv`",
            "- `reports/project_decision_ballot.md`",
            "- `reports/decision_prep_packet.md`",
            "- `reports/project_decision_sequence.md`",
            "- `reports/duplicate_people_review_worksheet.md`",
            "- `reports/duplicate_leads_review_worksheet.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    app = handler()
    rows = app.export_project_decision_option_matrix_rows()
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "project_decision_option_matrix.csv", rows)
    (REPORTS_DIR / "project_decision_option_matrix.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} option matrix rows to reports/project_decision_option_matrix.md and .csv")


if __name__ == "__main__":
    main()
