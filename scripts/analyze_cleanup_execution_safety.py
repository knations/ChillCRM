#!/usr/bin/env python3
"""Generate a non-destructive cleanup execution safety plan."""

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


def clip(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def label_status(value: Any) -> str:
    return str(value or "unknown").replace("_", " ").title()


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


def preview_summary_rows(current: dict[str, Any], recommended: dict[str, Any]) -> list[dict[str, Any]]:
    current_totals = current.get("totals") or {}
    recommended_totals = recommended.get("totals") or {}
    return [
        {
            "metric": "Preview status",
            "current": label_status(current.get("status")),
            "recommended_path_simulation": label_status(recommended.get("status")),
        },
        {
            "metric": "Locked gates",
            "current": f"{int(current_totals.get('blocked_gates') or 0):,}",
            "recommended_path_simulation": f"{int(recommended_totals.get('blocked_gates') or 0):,}",
        },
        {
            "metric": "Open cleanup groups",
            "current": f"{int(current_totals.get('open_groups') or 0):,}",
            "recommended_path_simulation": f"{int(recommended_totals.get('open_groups') or 0):,}",
        },
        {
            "metric": "Approved Merge Later groups",
            "current": f"{int(current_totals.get('approved_merge_later_groups') or 0):,}",
            "recommended_path_simulation": f"{int(recommended_totals.get('approved_merge_later_groups') or 0):,}",
        },
        {
            "metric": "Eligible actions",
            "current": f"{int(current_totals.get('eligible_actions') or 0):,}",
            "recommended_path_simulation": f"{int(recommended_totals.get('eligible_actions') or 0):,}",
        },
        {
            "metric": "Eligible groups",
            "current": f"{int(current_totals.get('eligible_groups') or 0):,}",
            "recommended_path_simulation": f"{int(recommended_totals.get('eligible_groups') or 0):,}",
        },
    ]


def action_detail(action: dict[str, Any]) -> str:
    return (
        f"{label_status(action.get('status'))}; "
        f"open groups {int(action.get('open_groups') or 0):,}; "
        f"approved groups {int(action.get('approved_groups') or 0):,}; "
        f"eligible groups {int(action.get('eligible_groups') or 0):,}; "
        f"eligible records {int(action.get('eligible_records') or 0):,}."
    )


def action_rows(current: dict[str, Any], recommended: dict[str, Any]) -> list[dict[str, Any]]:
    recommended_by_key = {action["action_type"]: action for action in recommended.get("actions") or []}
    rows = []
    for action in current.get("actions") or []:
        simulated = recommended_by_key.get(action["action_type"], {})
        rows.append(
            {
                "section": "action",
                "key": action.get("action_type"),
                "label": action.get("label"),
                "current_status": label_status(action.get("status")),
                "current_detail": action_detail(action),
                "recommended_status": label_status(simulated.get("status")),
                "recommended_detail": action_detail(simulated) if simulated else "",
                "next_step": action.get("detail") or "",
            }
        )
    return rows


def gate_rows(current: dict[str, Any], recommended: dict[str, Any], backups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommended_by_key = {gate["key"]: gate for gate in recommended.get("gates") or []}
    rows = []
    for gate in current.get("gates") or []:
        simulated = recommended_by_key.get(gate["key"], {})
        rows.append(
            {
                "section": "gate",
                "key": gate.get("key"),
                "label": gate.get("label"),
                "current_status": label_status(gate.get("status")),
                "current_detail": gate.get("detail") or "",
                "recommended_status": label_status(simulated.get("status")),
                "recommended_detail": simulated.get("detail") or "",
                "next_step": "Save the related Project Decision or create a backup if this gate is locked.",
            }
        )
    backup_detail = (
        f"{len(backups):,} backups available; latest is {backups[0].get('name')}."
        if backups
        else "No backup files are available yet."
    )
    rows.extend(
        [
            {
                "section": "gate",
                "key": "fresh_backup_at_execution",
                "label": "Fresh execution backup",
                "current_status": "Future Required",
                "current_detail": backup_detail,
                "recommended_status": "Future Required",
                "recommended_detail": "Create a new backup immediately before any mutating cleanup action.",
                "next_step": "Keep this as a hard gate in the future execution workflow.",
            },
            {
                "section": "gate",
                "key": "final_confirmation",
                "label": "Final confirmation",
                "current_status": "Not Enabled",
                "current_detail": "No mutating cleanup execution endpoint is currently enabled.",
                "recommended_status": "Required",
                "recommended_detail": "Show final affected counts, sample groups, backup name, and undo path before execution.",
                "next_step": "Build this only after the Project Decisions and group-level approvals are saved.",
            },
            {
                "section": "gate",
                "key": "restore_path",
                "label": "Undo / restore path",
                "current_status": "Ready",
                "current_detail": "The app and maintenance script can restore a backup, creating a pre-restore backup first.",
                "recommended_status": "Ready",
                "recommended_detail": "Use the same restore path after any future cleanup execution if rollback is needed.",
                "next_step": "Keep restore visible before any future cleanup execution is enabled.",
            },
        ]
    )
    return rows


def invariant_rows() -> list[dict[str, Any]]:
    invariants = [
        (
            "fresh_backup",
            "Fresh backup first",
            "Never mutate cleanup data without creating a new backup immediately before execution.",
        ),
        (
            "dry_run_counts",
            "Dry-run counts first",
            "Show exact affected groups, records, and action types before execution.",
        ),
        (
            "group_scope",
            "Approved group scope only",
            "Do not merge people, leads, or lead/person overlaps unless the group has an explicit Merge Later decision.",
        ),
        (
            "preserve_history",
            "Preserve history",
            "Keep notes, tasks, tags, archive links, linked resources, addresses, and custom fields attached or recoverable.",
        ),
        (
            "audit_log",
            "Audit every change",
            "Write an audit entry for each cleanup execution batch and each affected group.",
        ),
        (
            "tag_lowest_risk",
            "Duplicate tags first",
            "Duplicate tag handling is the lowest-risk batch candidate after the spot check and final preview.",
        ),
        (
            "no_auto_merge",
            "No automatic contact merge",
            "Do not auto-merge people, leads, or overlaps from draft keepers; draft keepers remain decision aids.",
        ),
    ]
    return [
        {
            "section": "invariant",
            "key": key,
            "label": label,
            "current_status": "Required",
            "current_detail": detail,
            "recommended_status": "Required",
            "recommended_detail": detail,
            "next_step": "Carry this rule into any future mutating cleanup workflow.",
        }
        for key, label, detail in invariants
    ]


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    decisions = app.project_decisions()
    current = app.cleanup_execution_preview(decisions)
    recommended = app.recommended_cleanup_execution_preview()
    backups = app.backups().get("backups", [])
    latest_backup = backups[0] if backups else None
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    current_totals = current.get("totals") or {}
    recommended_totals = recommended.get("totals") or {}
    gate_items = [row for row in rows if row["section"] == "gate"]
    action_items = [row for row in rows if row["section"] == "action"]
    invariant_items = [row for row in rows if row["section"] == "invariant"]

    lines = [
        "# Cleanup Execution Safety Plan",
        "",
        f"Generated: {generated_at}",
        "",
        "This report is non-destructive. It does not merge, delete, resolve, ignore, or rewrite CRM records.",
        "",
        "## Current Safety State",
        "",
        f"- Current preview status: {label_status(current.get('status'))}.",
        f"- Open cleanup groups: {int(current_totals.get('open_groups') or 0):,}.",
        f"- Approved Merge Later groups: {int(current_totals.get('approved_merge_later_groups') or 0):,}.",
        f"- Eligible actions today: {int(current_totals.get('eligible_actions') or 0):,}.",
        f"- Locked policy/backup gates: {int(current_totals.get('blocked_gates') or 0):,}.",
        f"- Backups available: {len(backups):,}.",
        f"- Latest backup: {latest_backup.get('name') if latest_backup else 'None found'}.",
        "",
        "## Recommended Path Simulation",
        "",
        "This simulation assumes the recommended Project Decision paths are saved. It is not saved and it does not change records.",
        "",
        f"- Simulated preview status: {label_status(recommended.get('status'))}.",
        f"- Simulated locked gates: {int(recommended_totals.get('blocked_gates') or 0):,}.",
        f"- Simulated eligible actions: {int(recommended_totals.get('eligible_actions') or 0):,}.",
        f"- Simulated eligible groups: {int(recommended_totals.get('eligible_groups') or 0):,}.",
        "",
        "## Preview Summary",
        "",
        *table(
            preview_summary_rows(current, recommended),
            [
                ("metric", "Metric"),
                ("current", "Current"),
                ("recommended_path_simulation", "Recommended Path Simulation"),
            ],
        ),
        "",
        "## Safety Gates",
        "",
        *table(
            gate_items,
            [
                ("label", "Gate"),
                ("current_status", "Current"),
                ("current_detail", "Current Detail"),
                ("recommended_status", "Recommended Path"),
                ("recommended_detail", "Recommended Detail"),
            ],
        ),
        "",
        "## Cleanup Actions",
        "",
        *table(
            action_items,
            [
                ("label", "Action"),
                ("current_status", "Current"),
                ("current_detail", "Current Detail"),
                ("recommended_status", "Recommended Path"),
                ("recommended_detail", "Recommended Detail"),
            ],
        ),
        "",
        "## Execution Rules",
        "",
        *table(
            invariant_items,
            [
                ("label", "Rule"),
                ("current_detail", "Requirement"),
            ],
        ),
        "",
        "## Practical Next Step",
        "",
        "Keep cleanup execution disabled while the remaining Project Decisions are pending. After those choices are saved, start with the duplicate-tag batch candidate because it is the lowest-risk eligible action in the recommended-path simulation. People, lead, and overlap merges should still require group-level Merge Later approval and a final confirmation preview.",
        "",
        "## Related Files",
        "",
        "- `reports/cleanup_execution_safety_plan.csv`",
        "- `reports/project_decision_sequence.md`",
        "- `reports/project_decision_brief.md`",
        "- `reports/cleanup_merge_review_pack.md`",
        "- `reports/duplicate_tag_spot_check.md`",
        "- `reports/cleanup_decision_readiness.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    decisions = app.project_decisions()
    current = app.cleanup_execution_preview(decisions)
    recommended = app.recommended_cleanup_execution_preview()
    backups = app.backups().get("backups", [])
    rows = [
        *gate_rows(current, recommended, backups),
        *action_rows(current, recommended),
        *invariant_rows(),
    ]
    write_csv(REPORTS_DIR / "cleanup_execution_safety_plan.csv", rows)
    (REPORTS_DIR / "cleanup_execution_safety_plan.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} safety rows to reports/cleanup_execution_safety_plan.md and .csv")


if __name__ == "__main__":
    main()
