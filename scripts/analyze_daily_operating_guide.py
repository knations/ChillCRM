#!/usr/bin/env python3
"""Generate a printable daily operating guide for the local CRM."""

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


def metric_summary(row: dict[str, Any]) -> str:
    metrics = []
    for index in range(1, 8):
        label = row.get(f"metric_{index}_label")
        value = row.get(f"metric_{index}_value")
        if label:
            metrics.append(f"{label}: {value}")
    return "; ".join(metrics)


def status_count(rows: list[dict[str, Any]], key: str) -> int:
    for row in rows:
        if row.get("value") == key:
            try:
                return int(row.get("count") or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def first_week_rows(status: dict[str, Any]) -> list[dict[str, Any]]:
    project_decisions = status.get("project_decisions") or {}
    data_quality = (status.get("data_quality") or {}).get("totals") or {}
    archive_review = ((status.get("operational_work_queue") or {}).get("archive_review") or {})
    archive_unreviewed = status_count(archive_review.get("review_status_counts") or [], "unreviewed")
    cleanup = (status.get("cleanup") or {}).get("summary") or {}
    reports = status.get("reports") or []
    reports_ready = sum(1 for report in reports if report.get("exists"))
    reports_total = len(reports)
    return [
        {
            "day": "Day 1",
            "focus": "Orient and protect the database",
            "work": "Open Status, read Migration Completion Audit, confirm exports/backups, and avoid cleanup execution.",
            "proof": f"{reports_ready:,} of {reports_total:,} reports ready; 2 export packages ready; backups visible.",
        },
        {
            "day": "Day 2",
            "focus": "Follow-up triage",
            "work": "Review imported open tasks, copy only still-relevant reminders into local follow-ups, and leave stale imported reminders historical.",
            "proof": "Follow Up shows imported/local source labels and Activity captures local copies.",
        },
        {
            "day": "Day 3",
            "focus": "Pipeline and New leads",
            "work": "Review active deals and New leads from Status shortcuts; save only known local edits.",
            "proof": "Active deal and New lead queues are visible from Status.",
        },
        {
            "day": "Day 4",
            "focus": "Ordinary Data Quality",
            "work": f"Work known contact/value gaps from the Data Quality work order; {int(data_quality.get('attention_records') or 0):,} rows currently need attention.",
            "proof": "/reports/local_crm_data_quality.md",
        },
        {
            "day": "Day 5",
            "focus": "Archive review",
            "work": f"Review unlinked calls/texts only when identity evidence is clear; {archive_unreviewed:,} are currently unreviewed.",
            "proof": "/reports/archive_review_worklist.md",
        },
        {
            "day": "Before cleanup",
            "focus": "Project decisions",
            "work": f"Save explicit A/B/C choices for pending cleanup policies before group-level cleanup; {int(project_decisions.get('pending') or 0):,} pending and {int(project_decisions.get('deferred') or 0):,} deferred decisions remain.",
            "proof": "/reports/project_decision_option_matrix.md",
        },
        {
            "day": "Before merging",
            "focus": "Cleanup review",
            "work": f"Use Cleanup Starter and group detail panels after policies are saved; {int(cleanup.get('open_groups') or 0):,} open groups remain.",
            "proof": "/reports/cleanup_review_starter_packet.md",
        },
    ]


def pre_change_rows() -> list[dict[str, Any]]:
    return [
        {
            "situation": "Saving a Project Decision",
            "do_first": "Read the evidence report and choose one explicit A/B/C path.",
            "safety": "Save Decision creates a backup first and records Activity/audit; it does not merge or rewrite CRM records.",
        },
        {
            "situation": "Editing a record",
            "do_first": "Confirm the value is known and belongs on the opened person/company/lead/deal.",
            "safety": "Local edit forms create a backup first and refresh quality-focused queues after saving.",
        },
        {
            "situation": "Reviewing archive calls/texts",
            "do_first": "Confirm identity from reliable context before saving review status or linking.",
            "safety": "Review status and manual linking are explicit Archive inspector actions with backup/audit entries.",
        },
        {
            "situation": "Cleanup group review",
            "do_first": "Save the related project policy and inspect the group comparison/history signals.",
            "safety": "Group decisions do not merge records; future merge execution remains separately gated.",
        },
        {
            "situation": "Any future cleanup execution",
            "do_first": "Create a fresh manual backup, review dry-run counts, and require explicit final confirmation.",
            "safety": "People/leads/overlaps should not auto-merge without reviewed group decisions.",
        },
    ]


def recovery_rows(status: dict[str, Any]) -> list[dict[str, Any]]:
    backups = status.get("backups") or {}
    export_packages = status.get("export_packages") or {}
    return [
        {
            "need": "Portable handoff",
            "where": "Exports",
            "action": "Download Complete Local CRM Package for the database, CSVs, reports, and docs.",
            "current_state": f"{int(export_packages.get('ready_count') or 0):,} of {int(export_packages.get('total_count') or 0):,} packages ready.",
        },
        {
            "need": "Recovered files",
            "where": "Exports",
            "action": "Download Document Files package when recovered Zendesk document attachments are needed separately.",
            "current_state": "203 recovered document files are packaged separately.",
        },
        {
            "need": "Rollback",
            "where": "Cleanup > Backups",
            "action": "Use Restore beside the desired backup; the app creates a pre-restore backup first.",
            "current_state": f"{int(backups.get('count') or 0):,} backups available.",
        },
        {
            "need": "Command-line backup",
            "where": "Terminal",
            "action": "Run python3 scripts/local_crm_maintenance.py backup --reason manual.",
            "current_state": "Use before saving several decisions or enabling cleanup execution.",
        },
        {
            "need": "Completion proof",
            "where": "Reports",
            "action": "Open Migration Completion Audit for operational status, remaining gates, and evidence links.",
            "current_state": "/reports/migration_completion_audit.md",
        },
    ]


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    status = app.migration_status()
    guide = status.get("daily_guide") or {}
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    guide_rows = rows if rows and rows[0].get("key") else []
    for row in guide_rows:
        row["metrics"] = metric_summary(row)
    lines = [
        "# Daily Operating Guide",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a live runbook for using the local CRM after the Zendesk Sell data pull. It does not save project decisions, merge records, delete records, resolve cleanup flags, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Guide status: {guide.get('status') or 'unknown'}.",
        f"- Steps: {len(guide.get('steps') or []):,}.",
        f"- Status report: `{guide.get('report') or '/reports/daily_operating_guide.md'}`.",
        f"- CSV export: `{guide.get('csv') or '/reports/daily_operating_guide.csv'}`.",
        "",
    ]
    if guide_rows:
        lines.extend(
            [
                "## Daily Runbook",
                "",
                *table(
                    guide_rows,
                    [
                        ("order", "Step"),
                        ("title", "Work Area"),
                        ("status", "Status"),
                        ("description", "Purpose"),
                        ("action", "Primary Action"),
                        ("view", "View"),
                        ("preset", "Preset"),
                    ],
                ),
                "",
                "## Metrics And Evidence",
                "",
                *table(
                    guide_rows,
                    [
                        ("order", "Step"),
                        ("title", "Work Area"),
                        ("metrics", "Live Metrics"),
                        ("secondary_action", "Secondary Action"),
                        ("report", "Report"),
                        ("export_url", "Export"),
                    ],
                ),
                "",
                "## Safety Boundaries",
                "",
                *table(
                    guide_rows,
                    [
                        ("order", "Step"),
                        ("title", "Work Area"),
                        ("safety", "Boundary"),
                    ],
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## First Week Handoff",
            "",
            *table(
                first_week_rows(status),
                [
                    ("day", "When"),
                    ("focus", "Focus"),
                    ("work", "What To Do"),
                    ("proof", "Evidence"),
                ],
            ),
            "",
            "## Before You Change Anything",
            "",
            *table(
                pre_change_rows(),
                [
                    ("situation", "Situation"),
                    ("do_first", "Do First"),
                    ("safety", "Safety Boundary"),
                ],
            ),
            "",
            "## Recovery And Portability",
            "",
            *table(
                recovery_rows(status),
                [
                    ("need", "Need"),
                    ("where", "Where"),
                    ("action", "Action"),
                    ("current_state", "Current State"),
                ],
            ),
            "",
        ]
    )
    lines.extend(
        [
            "## How To Use",
            "",
            "1. Open Status in the local CRM.",
            "2. Start with the Next Action card if a major decision needs attention.",
            "3. Use the Daily Operating Guide for normal CRM work: follow-ups, active deals, new leads, data quality, archive review, recent local changes, decision review, cleanup starter review, and export checks.",
            "4. Save local record edits only from the normal record forms. The guide itself is navigation and reporting only.",
            "5. Use the related reports when you want a printable or exportable checklist.",
            "",
            "## Related Files",
            "",
            "- `reports/daily_operating_guide.csv`",
            "- `reports/decision_prep_packet.md`",
            "- `reports/project_decision_ballot.md`",
            "- `reports/cleanup_review_starter_packet.md`",
            "- `reports/local_crm_data_quality.md`",
            "- `reports/backup_safety_ledger.md`",
            "- `reports/archive_review_worklist.md`",
            "- `reports/archive_association_audit.md`",
            "- `reports/project_decision_sequence.md`",
            "- `docs/operating_notes.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_daily_operating_guide_rows()
    write_csv(REPORTS_DIR / "daily_operating_guide.csv", rows)
    (REPORTS_DIR / "daily_operating_guide.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} daily operating guide rows to reports/daily_operating_guide.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
