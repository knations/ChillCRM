#!/usr/bin/env python3
"""Generate a non-destructive project decision brief for the local CRM."""

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


def clip(value: Any, limit: int = 96) -> str:
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


def fact_text(decision: dict[str, Any]) -> str:
    facts = (decision.get("impact") or {}).get("facts") or []
    return "; ".join(f"{fact.get('label')}: {fact.get('value')}" for fact in facts)


def generate_report(app: server.CRMRequestHandler) -> str:
    decisions = app.project_decisions()
    preview = app.cleanup_execution_preview(decisions)
    recommended_preview = app.recommended_cleanup_execution_preview()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decision_rows = []
    for decision in decisions.get("decisions", []):
        impact = decision.get("impact") or {}
        decision_rows.append(
            {
                "title": decision.get("title"),
                "status": decision.get("status_label"),
                "choice": decision.get("choice_label") or "No saved path",
                "recommended": (decision.get("recommended_option") or {}).get("label"),
                "impact": impact.get("summary"),
                "facts": fact_text(decision),
                "next_step": impact.get("next_step"),
                "evidence_report": decision.get("report") or "",
                "worksheet_report": decision.get("worksheet_report") or "",
                "after_save": (decision.get("sequence") or {}).get("after_save"),
                "save_safety": server.PROJECT_DECISION_SAVE_SAFETY,
            }
        )

    lines = [
        "# Project Decision Brief",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not merge, delete, resolve, ignore, or rewrite any CRM record.",
        "Saving a Project Decision through Status creates a local backup first, then records the selected path in Project Decisions, Activity, and the audit log.",
        "",
        "## Current Decision State",
        "",
        f"- Decisions tracked: {decisions.get('total', 0):,}.",
        f"- Pending: {decisions.get('pending', 0):,}.",
        f"- Decided: {decisions.get('decided', 0):,}.",
        f"- Deferred: {decisions.get('deferred', 0):,}.",
        f"- Cleanup execution preview: {preview.get('status', 'unknown').replace('_', ' ').title()}.",
        f"- Locked gates: {preview.get('totals', {}).get('blocked_gates', 0):,}.",
        f"- Eligible actions: {preview.get('totals', {}).get('eligible_actions', 0):,}.",
        f"- Recommended-path simulated eligible actions: {recommended_preview.get('totals', {}).get('eligible_actions', 0):,}.",
        f"- Recommended-path simulated eligible groups: {recommended_preview.get('totals', {}).get('eligible_groups', 0):,}.",
        "",
        "## Decisions",
        "",
        *table(
            decision_rows,
            [
                ("title", "Decision"),
                ("status", "Status"),
                ("choice", "Saved Path"),
                ("recommended", "Recommended"),
                ("impact", "Impact"),
                ("facts", "Key Facts"),
                ("next_step", "Next Step"),
            ],
        ),
        "",
        "## Evidence And Worksheets",
        "",
        *table(
            decision_rows,
            [
                ("title", "Decision"),
                ("evidence_report", "Evidence Report"),
                ("worksheet_report", "Worksheet"),
            ],
        ),
        "",
        "## Decision Save Effects",
        "",
        *table(
            decision_rows,
            [
                ("title", "Decision"),
                ("after_save", "After Save"),
                ("save_safety", "Save Safety"),
            ],
        ),
        "",
        "## Execution Gates",
        "",
        *table(
            preview.get("gates") or [],
            [
                ("label", "Gate"),
                ("status", "Status"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Preview Actions",
        "",
        *table(
            preview.get("actions") or [],
            [
                ("label", "Action"),
                ("status", "Status"),
                ("open_groups", "Open Groups"),
                ("approved_groups", "Approved Groups"),
                ("eligible_groups", "Eligible Groups"),
                ("eligible_records", "Eligible Records"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Recommended Path Simulation",
        "",
        "This simulation assumes every Project Decision uses its recommended path. It is not saved and does not change records.",
        "",
        f"- Simulated status: {recommended_preview.get('status', 'unknown').replace('_', ' ').title()}.",
        f"- Simulated locked gates: {recommended_preview.get('totals', {}).get('blocked_gates', 0):,}.",
        f"- Simulated eligible actions: {recommended_preview.get('totals', {}).get('eligible_actions', 0):,}.",
        f"- Simulated eligible groups: {recommended_preview.get('totals', {}).get('eligible_groups', 0):,}.",
        "",
        "### Simulated Gates",
        "",
        *table(
            recommended_preview.get("gates") or [],
            [
                ("label", "Gate"),
                ("status", "Status"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "### Simulated Actions",
        "",
        *table(
            recommended_preview.get("actions") or [],
            [
                ("label", "Action"),
                ("status", "Status"),
                ("open_groups", "Open Groups"),
                ("approved_groups", "Approved Groups"),
                ("eligible_groups", "Eligible Groups"),
                ("eligible_records", "Eligible Records"),
                ("detail", "Detail"),
            ],
        ),
        "",
        "## Safety Notes",
        "",
        "- Saving a Project Decision through Status creates a local backup before the database write.",
        "- A saved Project Decision records intent in Project Decisions, Activity, and the audit log only.",
        "- Use Backups restore if a saved decision needs to be rolled back.",
    ]
    for warning in preview.get("warnings") or []:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Related Files",
            "",
            "- `reports/decision_prep_packet.md`",
            "- `reports/project_decision_sequence.md`",
            "- `reports/project_decision_brief.csv`",
            "- `reports/cleanup_execution_safety_plan.md`",
            "- `reports/merge_policy_options.md`",
            "- `reports/cleanup_merge_review_pack.md`",
            "- `reports/duplicate_people_review_worksheet.md`",
            "- `reports/duplicate_leads_review_worksheet.md`",
            "- `reports/duplicate_tag_spot_check.md`",
            "- `reports/unlinked_archive_matching_candidates.md`",
            "- `reports/application_profile_editability_review.md`",
            "- `reports/cleanup_decision_readiness.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_project_decision_rows()
    write_csv(REPORTS_DIR / "project_decision_brief.csv", rows)
    (REPORTS_DIR / "project_decision_brief.md").write_text(generate_report(app), encoding="utf-8")
    print(f"Wrote {len(rows):,} project decisions to reports/project_decision_brief.md and .csv")


if __name__ == "__main__":
    main()
