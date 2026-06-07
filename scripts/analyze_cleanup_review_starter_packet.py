#!/usr/bin/env python3
"""Generate a read-only starter packet for cleanup group review."""

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
    packet = app.cleanup_review_starter_packet()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    group_rows = rows if rows and rows[0].get("group_key") else []
    lines = [
        "# Cleanup Review Starter Packet",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a review packet only. Running it does not save decisions, merge, delete, resolve, ignore, or rewrite CRM records.",
        "Use it after the related Project Decisions are saved to start group-level cleanup review in a controlled order.",
        "",
        "## Summary",
        "",
        f"- Starter groups: {int(packet.get('group_count') or 0):,}.",
        f"- Report limit: {int(packet.get('limit') or 0):,}.",
        f"- Merge review report: `{packet.get('merge_review_report')}`.",
        "",
        "## Queue Order",
        "",
        *table(
            packet.get("queue_summaries") or [],
            [
                ("queue_label", "Queue"),
                ("review_remaining", "Review Remaining"),
                ("high_priority", "High Priority"),
                ("phase", "Phase"),
                ("why", "Why"),
            ],
        ),
        "",
    ]
    if group_rows:
        lines.extend(
            [
                "## Starter Groups",
                "",
                *table(
                    group_rows,
                    [
                        ("review_order", "Order"),
                        ("queue_label", "Queue"),
                        ("group_label", "Group"),
                        ("priority", "Priority"),
                        ("review_score", "Score"),
                        ("record_count", "Records"),
                        ("draft_keeper", "Draft Keeper"),
                        ("manual_review_fields", "Manual Fields"),
                        ("history_signals", "History Signals"),
                    ],
                ),
                "",
                "## Review Notes",
                "",
                *table(
                    group_rows,
                    [
                        ("review_order", "Order"),
                        ("group_label", "Group"),
                        ("headline", "Guidance"),
                        ("sample_names", "Sample Names"),
                        ("why", "Queue Reason"),
                    ],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## How To Use",
            "",
            "1. Save the related Project Decisions in Status first.",
            "2. Open Cleanup and use the Cleanup Starter Packet.",
            "3. Review one group at a time; choose a group-level decision only after inspecting the records.",
            "4. Save & Next can move through Review Remaining groups, but it still does not merge records.",
            "5. Any future merge execution should require a fresh backup, final preview counts, and explicit confirmation.",
            "",
            "## Related Files",
            "",
            "- `reports/cleanup_review_starter_packet.csv`",
            "- `reports/cleanup_merge_review_pack.md`",
            "- `reports/cleanup_decision_readiness.md`",
            "- `reports/decision_prep_packet.md`",
            "- `reports/project_decision_sequence.md`",
            "- `reports/cleanup_execution_safety_plan.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_cleanup_starter_packet_rows()
    write_csv(REPORTS_DIR / "cleanup_review_starter_packet.csv", rows)
    (REPORTS_DIR / "cleanup_review_starter_packet.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} cleanup starter rows to reports/cleanup_review_starter_packet.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
