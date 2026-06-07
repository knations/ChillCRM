#!/usr/bin/env python3
"""Generate a read-only plan for moving from imported Zendesk tasks to local follow-ups."""

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


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    plan = app.followup_transition_plan()
    counts = plan.get("counts") or {}
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    step_rows = [row for row in rows if row.get("row_type") == "transition_step"]
    task_rows = [row for row in rows if row.get("row_type") == "imported_open_task"]
    lines = [
        "# Follow Up Transition Plan",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a review plan only. Running it does not complete tasks, create local follow-ups, delete reminders, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Plan status: {plan.get('status') or 'unknown'}.",
        f"- Open imported Zendesk tasks: {int(counts.get('open_imported') or 0):,}.",
        f"- Open local CRM follow-ups: {int(counts.get('open_local') or 0):,}.",
        f"- Overdue imported tasks: {int(counts.get('overdue_imported') or 0):,}.",
        f"- Imported tasks without due date: {int(counts.get('imported_without_due') or 0):,}.",
        f"- Linked imported tasks: {int(counts.get('linked_imported') or 0):,}.",
        f"- Unlinked imported tasks: {int(counts.get('unlinked_imported') or 0):,}.",
        "",
        "## Transition Steps",
        "",
        *table(
            step_rows,
            [
                ("title", "Step"),
                ("status", "Status"),
                ("count", "Items"),
                ("action", "App Action"),
                ("description", "Purpose"),
            ],
        ),
        "",
    ]
    if task_rows:
        lines.extend(
            [
                "## Imported Open Tasks To Review",
                "",
                *table(
                    task_rows,
                    [
                        ("task_id", "Local Task ID"),
                        ("zendesk_task_id", "Zendesk ID"),
                        ("record_type", "Record Type"),
                        ("record_id", "Record ID"),
                        ("record_name", "Record"),
                        ("content", "Task"),
                        ("due_date", "Due"),
                    ],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## How To Use",
            "",
            "1. Open Follow Up in the local CRM.",
            "2. Use Show Imported Open to review all open reminders that came from Zendesk.",
            "3. Use Show Overdue Imported for the highest-friction items first.",
            "4. For reminders that still matter, use Copy Local in Follow Up and choose a fresh local due date, or leave the due date blank.",
            "5. Treat old imported reminders as historical until you explicitly complete or edit them locally.",
            "",
            "## Safety Notes",
            "",
            f"- {plan.get('safety')}",
            "- Copy Local creates a separate local follow-up after an explicit click; it does not complete or delete the imported Zendesk task.",
            "- Imported Zendesk task rows remain preserved in the local database unless you explicitly edit or complete them locally.",
            "- New local follow-ups have no Zendesk task ID and stay separate from imported reminder history.",
            "",
            "## Related Files",
            "",
            "- `reports/followup_transition_plan.csv`",
            "- `reports/daily_operating_guide.md`",
            "- `docs/operating_notes.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_followup_transition_rows()
    write_csv(REPORTS_DIR / "followup_transition_plan.csv", rows)
    (REPORTS_DIR / "followup_transition_plan.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} follow-up transition rows to reports/followup_transition_plan.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
