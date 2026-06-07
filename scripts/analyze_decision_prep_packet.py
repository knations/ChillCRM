#!/usr/bin/env python3
"""Generate a printable decision prep packet for the local CRM."""

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
    packet = app.project_decision_prep_packet()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decision_rows = rows if rows and rows[0].get("key") else []
    lines = [
        "# Decision Prep Packet",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning packet only. Running it does not save choices, merge, delete, resolve, ignore, or rewrite CRM records.",
        "Use it to review the remaining major decisions before saving any paths in Status.",
        "",
        "## Summary",
        "",
        f"- Remaining decisions: {int(packet.get('remaining_count') or 0):,}.",
        f"- Pending decisions: {int(packet.get('pending_count') or 0):,}.",
        f"- Decided decisions: {int(packet.get('decided_count') or 0):,}.",
        f"- Deferred decisions: {int(packet.get('deferred_count') or 0):,}.",
        f"- Next decision: {packet.get('next_decision_title') or 'None'}.",
        "",
    ]
    if decision_rows:
        lines.extend(
            [
                "## Remaining Decision Review",
                "",
                *table(
                    decision_rows,
                    [
                        ("step", "Step"),
                        ("phase", "Phase"),
                        ("title", "Decision"),
                        ("status_label", "Status"),
                        ("recommended_label", "Recommended Path"),
                        ("recommended_timing", "Timing"),
                        ("impact_summary", "Impact"),
                        ("next_step", "Next Step"),
                    ],
                ),
                "",
                "## Evidence And Effects",
                "",
                *table(
                    decision_rows,
                    [
                        ("step", "Step"),
                        ("title", "Decision"),
                        ("fact_1_label", "Fact 1"),
                        ("fact_1_value", "Value"),
                        ("fact_2_label", "Fact 2"),
                        ("fact_2_value", "Value"),
                        ("after_save", "After Save"),
                        ("report", "Evidence Report"),
                        ("worksheet_report", "Worksheet"),
                    ],
                ),
                "",
            ]
        )
    else:
        lines.extend(["## Remaining Decision Review", "", "All major project decisions have saved paths.", ""])
    lines.extend(
        [
            "## How To Use",
            "",
            "1. Open Status in the local CRM.",
            "2. Review the Decision Prep Packet and evidence links.",
            "3. Use Open Next Decision to focus the next active pending decision; deferred decisions stay parked until pending decisions are cleared.",
            "4. Use Fill Recommended only to stage the suggested path; nothing is saved until Save Decision is clicked.",
            "5. Save one decision at a time. Each save creates a local backup first.",
            "",
            "## Safety Notes",
            "",
            f"- {server.PROJECT_DECISION_SAVE_SAFETY}",
            f"- Saved Project Decisions record intent in {server.PROJECT_DECISION_SAVE_RECORDS}.",
            f"- Saved Project Decisions do not {server.PROJECT_DECISION_SAVE_DOES_NOT}.",
            f"- Restore path: {server.PROJECT_DECISION_RESTORE_PATH}",
            "",
            "## Related Files",
            "",
            "- `reports/decision_prep_packet.csv`",
            "- `reports/project_decision_sequence.md`",
            "- `reports/project_decision_brief.md`",
            "- `reports/cleanup_execution_safety_plan.md`",
            "- `reports/cleanup_merge_review_pack.md`",
            "- `reports/duplicate_tag_spot_check.md`",
            "- `reports/duplicate_people_review_worksheet.md`",
            "- `reports/duplicate_leads_review_worksheet.md`",
            "- `reports/unlinked_archive_matching_candidates.md`",
            "- `reports/application_profile_editability_review.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_decision_prep_packet_rows()
    write_csv(REPORTS_DIR / "decision_prep_packet.csv", rows)
    (REPORTS_DIR / "decision_prep_packet.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} decision prep rows to reports/decision_prep_packet.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
