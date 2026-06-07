#!/usr/bin/env python3
"""Generate a non-destructive sequence guide for the remaining project decisions."""

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


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> list[str]:
    visible_rows = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), 120).replace("|", "/"))
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
    return "; ".join(
        f"{fact.get('label')}: {fact.get('value')}"
        for fact in (decision.get("impact") or {}).get("facts") or []
    )


def sequence_rows(app: server.CRMRequestHandler) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    decisions = app.project_decisions()
    recommended_preview = app.recommended_cleanup_execution_preview()
    current_preview = app.cleanup_execution_preview(decisions)
    action_by_group_type = {
        action.get("group_type"): action for action in recommended_preview.get("actions") or []
    }
    group_type_by_decision = {
        "duplicate_people_merge_policy": "duplicate_people",
        "duplicate_leads_merge_policy": "duplicate_leads",
        "lead_person_overlap_policy": "lead_person_overlap",
        "duplicate_tag_policy": "duplicate_tags",
    }
    decisions_by_key = {decision["key"]: decision for decision in decisions.get("decisions") or []}
    output = []
    for index, item in enumerate(server.PROJECT_DECISION_SEQUENCE, start=1):
        decision = decisions_by_key.get(item["key"]) or {}
        recommended = decision.get("recommended_option") or {}
        group_type = group_type_by_decision.get(item["key"])
        simulated_action = action_by_group_type.get(group_type) or {}
        output.append(
            {
                "step": index,
                "phase": item["phase"],
                "decision_key": item["key"],
                "decision": decision.get("title"),
                "status": decision.get("status_label"),
                "saved_path": decision.get("choice_label") or "No saved path",
                "recommended_path": recommended.get("label"),
                "recommended_timing": item["recommended_timing"],
                "readiness": (decision.get("impact") or {}).get("readiness"),
                "why": item["why"],
                "after_save": item["after_save"],
                "save_creates_backup": "yes",
                "save_safety": server.PROJECT_DECISION_SAVE_SAFETY,
                "restore_path": server.PROJECT_DECISION_RESTORE_PATH,
                "impact_facts": fact_text(decision),
                "evidence_report": decision.get("report") or "",
                "worksheet_report": decision.get("worksheet_report") or "",
                "worksheet_export_url": decision.get("worksheet_export_url") or "",
                "open_view": decision.get("view") or "",
                "simulated_action_status": simulated_action.get("status") or "",
                "simulated_eligible_groups": simulated_action.get("eligible_groups") or "",
                "simulated_eligible_records": simulated_action.get("eligible_records") or "",
            }
        )
    return output, current_preview, recommended_preview


def generate_report(rows: list[dict[str, Any]], current_preview: dict[str, Any], recommended_preview: dict[str, Any]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decided = sum(1 for row in rows if row.get("status") == "Decided")
    deferred = sum(1 for row in rows if row.get("status") == "Deferred")
    pending = sum(1 for row in rows if row.get("status") == "Pending")
    tag_row = next((row for row in rows if row.get("decision_key") == "duplicate_tag_policy"), {})
    lines = [
        "# Project Decision Sequence",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not save decisions, merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Use the recommended paths, but save them in a sequence that protects the data model: archive/profile/design decisions first, tag policy after its spot check, then the person/lead cleanup policies before group-level review. Saving project decisions still does not merge records; it only unlocks clearer preview and review states.",
        "Each saved Project Decision creates a local backup first, records intent in Project Decisions, Activity, and the audit log, and can be rolled back through Backups restore.",
        "",
        f"- Decisions tracked: {len(rows):,}.",
        f"- Pending decisions: {pending:,}.",
        f"- Deferred decisions: {deferred:,}.",
        f"- Decided decisions: {decided:,}.",
        f"- Current cleanup execution status: {str(current_preview.get('status') or 'unknown').replace('_', ' ').title()}.",
        f"- Current locked gates: {int((current_preview.get('totals') or {}).get('blocked_gates') or 0):,}.",
        f"- Recommended-path simulated status: {str(recommended_preview.get('status') or 'unknown').replace('_', ' ').title()}.",
        f"- Recommended-path simulated eligible actions: {int((recommended_preview.get('totals') or {}).get('eligible_actions') or 0):,}.",
        f"- Duplicate tag simulated eligible groups: {tag_row.get('simulated_eligible_groups') or 0}.",
        "",
        "## Decision Save Order",
        "",
        *table(
            rows,
            [
                ("step", "Step"),
                ("phase", "Phase"),
                ("decision", "Decision"),
                ("status", "Status"),
                ("recommended_path", "Recommended Path"),
                ("recommended_timing", "Timing"),
                ("why", "Why This Order"),
                ("after_save", "After Save"),
            ],
        ),
        "",
        "## Evidence Links",
        "",
        *table(
            rows,
            [
                ("step", "Step"),
                ("decision", "Decision"),
                ("impact_facts", "Impact Facts"),
                ("evidence_report", "Evidence Report"),
                ("worksheet_report", "Worksheet"),
                ("open_view", "App View"),
            ],
        ),
        "",
        "## What Changes After Saving",
        "",
        "- Archive/Profile/Design decisions document operating intent; they do not enable mutating cleanup.",
        "- Duplicate tag policy can make the tag batch action preview-ready after the final spot check.",
        "- People, lead, and overlap policies still require group-level review. Groups must be marked Merge Later before any future merge preview can include them.",
        "- Saving any Project Decision creates a local backup before the database write.",
        "- Saved Project Decisions record intent only; they do not merge, delete, resolve, ignore, or rewrite CRM records.",
        "- Use Backups restore if a saved decision needs to be rolled back.",
        "- Mutating cleanup should still require a fresh backup, preview counts, undo documentation, and explicit final confirmation.",
        "",
        "## Related Files",
        "",
        "- `reports/decision_prep_packet.md`",
        "- `reports/project_decision_sequence.csv`",
        "- `reports/project_decision_brief.md`",
        "- `reports/cleanup_merge_review_pack.md`",
        "- `reports/duplicate_people_review_worksheet.md`",
        "- `reports/duplicate_leads_review_worksheet.md`",
        "- `reports/duplicate_tag_spot_check.md`",
        "- `reports/unlinked_archive_matching_candidates.md`",
        "- `reports/application_profile_editability_review.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows, current_preview, recommended_preview = sequence_rows(app)
    write_csv(REPORTS_DIR / "project_decision_sequence.csv", rows)
    (REPORTS_DIR / "project_decision_sequence.md").write_text(
        generate_report(rows, current_preview, recommended_preview),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows):,} decision sequence steps to reports/project_decision_sequence.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
