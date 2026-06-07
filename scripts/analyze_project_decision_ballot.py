#!/usr/bin/env python3
"""Generate a printable project decision ballot for the local CRM."""

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


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decisions = [row for row in rows if row.get("row_type") == "decision"]
    options_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("row_type") == "option":
            options_by_key.setdefault(str(row.get("key") or ""), []).append(row)
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    lines = [
        "# Project Decision Ballot",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a review worksheet only. It does not save choices, prefill forms, merge records, delete records, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Total decisions: {int(summary.get('total_decisions') or 0):,}.",
        f"- Pending: {int(summary.get('pending') or 0):,}.",
        f"- Decided: {int(summary.get('decided') or 0):,}.",
        f"- Deferred: {int(summary.get('deferred') or 0):,}.",
        f"- Safety: {summary.get('safety')}",
        f"- Restore path: {summary.get('restore_path')}",
        "",
        "## Ballot Overview",
        "",
        *table(
            decisions,
            [
                ("step", "Step"),
                ("title", "Decision"),
                ("current_status_label", "Current"),
                ("recommended_display", "Recommended"),
                ("recommended_timing", "Timing"),
                ("impact_summary", "Impact"),
                ("your_choice", "Your Choice"),
                ("your_note", "Your Note"),
            ],
        ),
        "",
    ]
    for decision in decisions:
        key = str(decision.get("key") or "")
        lines.extend(
            [
                f"## Step {decision.get('step')}: {decision.get('title')}",
                "",
                f"- Phase: {decision.get('phase') or ''}.",
                f"- Question: {decision.get('question') or ''}",
                f"- Recommended path: {decision.get('recommended_display') or decision.get('recommended_label') or ''}.",
                f"- Why now: {decision.get('why_now') or ''}",
                f"- After save: {decision.get('after_save') or ''}",
                f"- Evidence: `{decision.get('evidence_report') or ''}`",
                f"- Worksheet: `{decision.get('worksheet_report') or ''}`" if decision.get("worksheet_report") else "",
                f"- Impact facts: {decision.get('fact_summary') or ''}",
                "",
                "Options:",
                "",
            ]
        )
        for option in options_by_key.get(key, []):
            marker = "[recommended] " if option.get("recommended") == "yes" else ""
            lines.append(f"- [ ] {option.get('option_code')}. {marker}{option.get('option_label')}: {option.get('option_description')}")
        lines.extend(
            [
                "",
                "Your choice:",
                "",
                "```text",
                "Status: ",
                "Choice (A/B/C): ",
                "Note: ",
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## How To Save After Review",
            "",
            "1. Create a fresh manual backup if you are about to save several decisions in one sitting.",
            "2. Open Status in the local CRM.",
            "3. Use Open Ballot or Open Sequence as reference, then save one Project Decision card at a time.",
            "4. Each save creates a local backup first and records only the selected decision path.",
            "",
            "## Related Files",
            "",
            "- `reports/project_decision_ballot.csv`",
            "- `reports/project_decision_sequence.md`",
            "- `reports/decision_prep_packet.md`",
            "- `reports/project_decision_brief.md`",
            "- `reports/duplicate_people_review_worksheet.md`",
            "- `reports/duplicate_leads_review_worksheet.md`",
            "- `reports/backup_safety_ledger.md`",
            "- `docs/operating_notes.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_project_decision_ballot_rows()
    write_csv(REPORTS_DIR / "project_decision_ballot.csv", rows)
    (REPORTS_DIR / "project_decision_ballot.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} project decision ballot rows to reports/project_decision_ballot.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
