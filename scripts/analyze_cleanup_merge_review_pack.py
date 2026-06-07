#!/usr/bin/env python3
"""Generate a non-destructive merge review pack for cleanup decisions."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"
GROUP_TYPES = [
    ("lead_person_overlap", "Lead/Person Overlap"),
    ("duplicate_people", "Duplicate People"),
    ("duplicate_leads", "Duplicate Leads"),
]
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
LANE_ORDER = {
    "policy_review_overlap": 0,
    "priority_review": 1,
    "conflict_heavy_review": 2,
    "multi_record_review": 3,
    "short_guided_review": 4,
}


def handler() -> server.CRMRequestHandler:
    server.ensure_runtime_schema(DB_PATH)
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DB_PATH
    return instance


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def clip(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def join_unique(values: list[Any], limit: int | None = None) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = " ".join(str(value if value is not None else "").split())
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
        if limit and len(output) >= limit:
            break
    return " | ".join(output)


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
    fieldnames = [
        "group_type",
        "queue_label",
        "group_key",
        "group_label",
        "priority",
        "review_score",
        "policy_lane",
        "policy_lane_label",
        "policy_action",
        "record_count",
        "people_count",
        "lead_count",
        "flag_count",
        "decision",
        "decision_label",
        "decision_note",
        "keeper_record_key",
        "keeper_type",
        "keeper_id",
        "keeper_name",
        "keeper_email",
        "keeper_score",
        "keeper_reason",
        "blank_field_suggestions",
        "manual_review_fields",
        "history_records_to_preserve",
        "history_signals_to_preserve",
        "record_summary",
        "profile_summary",
        "conflict_summary",
        "fill_summary",
        "history_summary",
        "warnings",
        "guidance_reasons",
        "recommended_review_action",
        "first_seen",
        "last_seen",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def record_label(record: dict[str, Any]) -> str:
    label = f"{str(record.get('record_type') or 'record').title()} #{record.get('source_id')}: {record.get('name') or '(blank name)'}"
    if record.get("email"):
        label += f" <{record['email']}>"
    phone = record.get("phone") or record.get("mobile")
    if phone:
        label += f" {phone}"
    badges = record.get("badges") or []
    if badges:
        label += f" [{', '.join(str(badge) for badge in badges)}]"
    return label


def record_profile_label(record: dict[str, Any]) -> str:
    profile = record.get("profile_summary") or []
    if not profile:
        return ""
    fields = "; ".join(f"{item.get('field_name')}: {clip(item.get('field_value'), 60)}" for item in profile)
    return f"{str(record.get('record_type') or 'record').title()} #{record.get('source_id')}: {fields}"


def conflict_label(conflict: dict[str, Any]) -> str:
    alternatives = conflict.get("alternatives") or []
    alternative_text = "; ".join(
        f"{alt.get('record_name') or alt.get('record_key')}: {clip(alt.get('value'), 48)}"
        for alt in alternatives
    )
    return f"{conflict.get('field_name')}: keeper '{clip(conflict.get('keeper_value'), 48)}' vs {alternative_text}"


def fill_label(suggestion: dict[str, Any]) -> str:
    return f"{suggestion.get('field_name')}: fill from {suggestion.get('from_record_name') or suggestion.get('from_record_key')} with '{clip(suggestion.get('value'), 48)}'"


def history_label(item: dict[str, Any]) -> str:
    signals = item.get("signals") or []
    signal_text = ", ".join(f"{signal.get('count')} {signal.get('label')}" for signal in signals)
    return f"{item.get('record_name') or item.get('record_key')}: {signal_text}"


def recommended_review_action(group_type: str, row: dict[str, Any]) -> str:
    if group_type == "lead_person_overlap":
        return "Open first; decide whether the person should be keeper and lead history preserved."
    if row.get("policy_lane") == "priority_review":
        return "Review early; verify keeper, conflicts, and history before marking Merge Later."
    if row.get("policy_lane") == "conflict_heavy_review":
        return "Inspect field conflicts before trusting the draft keeper."
    return "Use the draft keeper as a starting point, then spot-check fields and history."


def cleanup_merge_rows(app: server.CRMRequestHandler) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_type, queue_label in GROUP_TYPES:
        export = app.export_cleanup_group_rows({"type": [group_type], "status": ["open"], "sort": ["policy"]})
        for group in export["rows"]:
            detail = app.cleanup_groups({"type": [group_type], "status": ["open"], "key": [str(group.get("group_key"))]})
            draft = detail.get("merge_draft") or {}
            keeper = draft.get("keeper") or {}
            summary = app.cleanup_merge_draft_summary(draft) or {}
            counts = detail.get("counts") or {}
            guidance = detail.get("guidance") or {}
            decision = detail.get("decision") or {}
            records = detail.get("records") or []
            policy_lane = group.get("policy_lane") or ""
            row = {
                "group_type": group_type,
                "queue_label": queue_label,
                "group_key": group.get("group_key"),
                "group_label": group.get("group_label") or group.get("group_key"),
                "priority": guidance.get("priority") or group.get("priority"),
                "review_score": guidance.get("score") or group.get("review_score"),
                "policy_lane": policy_lane,
                "policy_lane_label": group.get("policy_lane_label"),
                "policy_action": group.get("policy_action"),
                "record_count": counts.get("record_count") or group.get("record_count"),
                "people_count": counts.get("people_count") or group.get("people_count"),
                "lead_count": counts.get("lead_count") or group.get("lead_count"),
                "flag_count": len(detail.get("flags") or []),
                "decision": decision.get("decision"),
                "decision_label": server.CLEANUP_GROUP_DECISIONS.get(decision.get("decision"), ""),
                "decision_note": decision.get("note"),
                "keeper_record_key": keeper.get("record_key"),
                "keeper_type": keeper.get("record_type"),
                "keeper_id": keeper.get("record_id"),
                "keeper_name": keeper.get("record_name"),
                "keeper_email": keeper.get("email"),
                "keeper_score": keeper.get("completeness_score"),
                "keeper_reason": keeper.get("reason"),
                "blank_field_suggestions": summary.get("fill_suggestion_count"),
                "manual_review_fields": summary.get("conflict_count"),
                "history_records_to_preserve": summary.get("preserve_record_count"),
                "history_signals_to_preserve": summary.get("preserve_signal_count"),
                "record_summary": join_unique([record_label(record) for record in records]),
                "profile_summary": join_unique([record_profile_label(record) for record in records if record_profile_label(record)], limit=5),
                "conflict_summary": join_unique([conflict_label(conflict) for conflict in draft.get("conflicts") or []], limit=8),
                "fill_summary": join_unique([fill_label(suggestion) for suggestion in draft.get("fill_suggestions") or []], limit=8),
                "history_summary": join_unique([history_label(item) for item in draft.get("preserve_signals") or []], limit=8),
                "warnings": join_unique(draft.get("warnings") or []),
                "guidance_reasons": join_unique(guidance.get("reasons") or []),
                "recommended_review_action": recommended_review_action(group_type, {**group, "policy_lane": policy_lane}),
                "first_seen": group.get("first_seen"),
                "last_seen": group.get("last_seen"),
            }
            rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            LANE_ORDER.get(str(row.get("policy_lane")), 99),
            PRIORITY_ORDER.get(str(row.get("priority") or "Low"), 3),
            -as_int(row.get("review_score")),
            -as_int(row.get("record_count")),
            str(row.get("group_label") or row.get("group_key") or "").casefold(),
        ),
    )


def summary_by_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for group_type, queue_label in GROUP_TYPES:
        queue_rows = [row for row in rows if row.get("group_type") == group_type]
        output.append(
            {
                "queue": queue_label,
                "groups": len(queue_rows),
                "high": sum(1 for row in queue_rows if row.get("priority") == "High"),
                "medium": sum(1 for row in queue_rows if row.get("priority") == "Medium"),
                "low": sum(1 for row in queue_rows if row.get("priority") == "Low"),
                "manual_fields": sum(as_int(row.get("manual_review_fields")) for row in queue_rows),
                "history_signals": sum(as_int(row.get("history_signals_to_preserve")) for row in queue_rows),
            }
        )
    return output


def summary_by_lane(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(row.get("policy_lane")) for row in rows)
    output = []
    for lane in sorted(counts, key=lambda value: LANE_ORDER.get(value, 99)):
        lane_rows = [row for row in rows if row.get("policy_lane") == lane]
        output.append(
            {
                "lane": lane_rows[0].get("policy_lane_label") or server.CLEANUP_POLICY_LANES.get(lane, {}).get("label") or lane,
                "groups": len(lane_rows),
                "high": sum(1 for row in lane_rows if row.get("priority") == "High"),
                "medium": sum(1 for row in lane_rows if row.get("priority") == "Medium"),
                "low": sum(1 for row in lane_rows if row.get("priority") == "Low"),
            }
        )
    return output


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    priority_counts = Counter(str(row.get("priority") or "Low") for row in rows)
    total_manual_fields = sum(as_int(row.get("manual_review_fields")) for row in rows)
    total_blank_fills = sum(as_int(row.get("blank_field_suggestions")) for row in rows)
    total_history_signals = sum(as_int(row.get("history_signals_to_preserve")) for row in rows)
    lead_person_rows = [row for row in rows if row.get("group_type") == "lead_person_overlap"]
    people_rows = [row for row in rows if row.get("group_type") == "duplicate_people"]
    lead_rows = [row for row in rows if row.get("group_type") == "duplicate_leads"]
    priority_examples = sorted(
        rows,
        key=lambda row: (
            PRIORITY_ORDER.get(str(row.get("priority") or "Low"), 3),
            -as_int(row.get("review_score")),
            -as_int(row.get("record_count")),
        ),
    )

    lines = [
        "# Cleanup Merge Review Pack",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Use this pack to decide the person, lead, and lead/person overlap merge policies. Start with lead/person overlaps, then high-priority duplicate people, then conflict-heavy duplicate leads. The draft keeper is a decision aid only; a future merge still needs saved project decisions, group approvals, a backup, and a separate execution confirmation.",
        "",
        f"- Open person/lead cleanup groups: {len(rows):,}.",
        f"- Priority split: {priority_counts.get('High', 0):,} high, {priority_counts.get('Medium', 0):,} medium, {priority_counts.get('Low', 0):,} low.",
        f"- Draft blank-field suggestions: {total_blank_fills:,}.",
        f"- Manual review fields: {total_manual_fields:,}.",
        f"- History signals to preserve: {total_history_signals:,}.",
        "",
        "## Queue Summary",
        "",
        *table(
            summary_by_queue(rows),
            [
                ("queue", "Queue"),
                ("groups", "Groups"),
                ("high", "High"),
                ("medium", "Medium"),
                ("low", "Low"),
                ("manual_fields", "Manual Fields"),
                ("history_signals", "History Signals"),
            ],
        ),
        "",
        "## Guided Work Lanes",
        "",
        *table(
            summary_by_lane(rows),
            [
                ("lane", "Lane"),
                ("groups", "Groups"),
                ("high", "High"),
                ("medium", "Medium"),
                ("low", "Low"),
            ],
        ),
        "",
        "## First Groups To Review",
        "",
        *table(
            rows,
            [
                ("queue_label", "Queue"),
                ("group_label", "Group"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("keeper_name", "Draft Keeper"),
                ("manual_review_fields", "Manual Fields"),
                ("history_signals_to_preserve", "History Signals"),
                ("recommended_review_action", "Action"),
            ],
            limit=18,
        ),
        "",
        "## Lead/Person Overlaps",
        "",
        *table(
            lead_person_rows,
            [
                ("group_label", "Email"),
                ("record_count", "Records"),
                ("keeper_name", "Draft Keeper"),
                ("blank_field_suggestions", "Blank Fills"),
                ("manual_review_fields", "Manual Fields"),
                ("history_summary", "History To Preserve"),
            ],
        ),
        "",
        "## Duplicate People Starting Set",
        "",
        *table(
            people_rows,
            [
                ("group_label", "Email"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("keeper_name", "Draft Keeper"),
                ("blank_field_suggestions", "Blank Fills"),
                ("manual_review_fields", "Manual Fields"),
                ("history_signals_to_preserve", "History Signals"),
            ],
            limit=16,
        ),
        "",
        "## Duplicate Leads Starting Set",
        "",
        *table(
            lead_rows,
            [
                ("group_label", "Email"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("keeper_name", "Draft Keeper"),
                ("blank_field_suggestions", "Blank Fills"),
                ("manual_review_fields", "Manual Fields"),
                ("history_signals_to_preserve", "History Signals"),
            ],
            limit=16,
        ),
        "",
        "## Detail Examples",
        "",
        *table(
            priority_examples,
            [
                ("queue_label", "Queue"),
                ("group_label", "Group"),
                ("record_summary", "Records"),
                ("conflict_summary", "Conflicts"),
                ("fill_summary", "Blank Fills"),
            ],
            limit=10,
        ),
        "",
        "## Safety Notes",
        "",
        "- The report is non-destructive and reads from the current local CRM only.",
        "- Draft keepers do not become merge rules until the related Project Decisions are saved.",
        "- Group-level decisions such as Merge Later still do not merge records; they only make groups eligible for a future preview.",
        "- Future merge execution should require a fresh backup, preview counts, undo documentation, and an explicit final confirmation.",
        "",
        "## Related Files",
        "",
        "- `reports/cleanup_review_starter_packet.md`",
        "- `reports/cleanup_review_starter_packet.csv`",
        "- `reports/cleanup_merge_review_pack.csv`",
        "- `reports/merge_policy_options.md`",
        "- `reports/project_decision_brief.md`",
        "- `reports/cleanup_decision_readiness.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = cleanup_merge_rows(app)
    write_csv(REPORTS_DIR / "cleanup_merge_review_pack.csv", rows)
    (REPORTS_DIR / "cleanup_merge_review_pack.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} person/lead cleanup groups to reports/cleanup_merge_review_pack.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
