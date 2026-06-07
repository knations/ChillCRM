#!/usr/bin/env python3
"""Generate non-destructive merge policy options for cleanup groups."""

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
    ("duplicate_people", "Duplicate People"),
    ("duplicate_leads", "Duplicate Leads"),
    ("lead_person_overlap", "Lead/Person Overlap"),
    ("duplicate_tags", "Duplicate Tags"),
]
GROUP_LABELS = dict(GROUP_TYPES)
LANE_LABELS = {
    "priority_review": "Priority manual review",
    "short_guided_review": "Short guided review",
    "conflict_heavy_review": "Conflict-heavy manual review",
    "multi_record_review": "Multi-record manual review",
    "policy_review_overlap": "Lead/person policy review",
    "tag_batch_candidate": "Tag batch candidate",
}
LANE_ORDER = {
    "policy_review_overlap": 0,
    "priority_review": 1,
    "conflict_heavy_review": 2,
    "multi_record_review": 3,
    "short_guided_review": 4,
    "tag_batch_candidate": 5,
}
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def handler() -> server.CRMRequestHandler:
    server.ensure_runtime_schema(DB_PATH)
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DB_PATH
    return instance


def as_int(row: dict[str, Any], key: str) -> int:
    try:
        return int(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def cleanup_group_rows(app: server.CRMRequestHandler) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_type, label in GROUP_TYPES:
        export = app.export_cleanup_group_rows({"type": [group_type], "status": ["open"], "sort": ["priority"]})
        for row in export["rows"]:
            row = dict(row)
            row["group_type"] = group_type
            row["queue_label"] = label
            rows.append(row)
    return rows


def classify_lane(row: dict[str, Any]) -> tuple[str, str, str]:
    group_type = str(row.get("group_type") or "")
    priority = str(row.get("priority") or "Low")
    record_count = as_int(row, "record_count")
    manual_fields = as_int(row, "draft_manual_review_fields")

    if group_type == "duplicate_tags":
        return (
            "tag_batch_candidate",
            "Candidate for one batch tag decision after a spot check.",
            "Duplicate tag definitions are already normalized locally; this can likely be handled as a tag-policy decision instead of record-by-record merging.",
        )
    if group_type == "lead_person_overlap":
        return (
            "policy_review_overlap",
            "Decide person-versus-lead policy before merging.",
            "A lead and a person share contact identity, so the keeper rule affects how future client history is represented.",
        )
    if priority == "High":
        return (
            "priority_review",
            "Open first; verify keeper, conflicts, and history before any merge.",
            "The group has high priority based on record count, review score, or cleanup guidance.",
        )
    if manual_fields >= 4:
        return (
            "conflict_heavy_review",
            "Do not batch; inspect field comparisons and history.",
            f"{manual_fields} fields need comparison before the draft keeper can be trusted.",
        )
    if record_count > 2:
        return (
            "multi_record_review",
            "Review manually before choosing the keeper.",
            f"{record_count} records are involved, which makes a silent batch rule too risky.",
        )
    return (
        "short_guided_review",
        "Use the draft keeper as a starting point, then compare the listed fields.",
        "The group is smaller and lower priority, but it still has field comparisons that deserve a quick human check.",
    )


def annotate_row(row: dict[str, Any]) -> dict[str, Any]:
    lane = str(row.get("policy_lane") or "")
    if lane in LANE_LABELS:
        action = str(row.get("policy_action") or server.CLEANUP_POLICY_LANES.get(lane, {}).get("action") or "")
        reason = str(row.get("policy_reason") or "")
    else:
        lane, action, reason = classify_lane(row)
    group_type = str(row.get("group_type") or "")
    annotated = dict(row)
    annotated["recommended_lane"] = lane
    annotated["recommended_lane_label"] = LANE_LABELS[lane]
    annotated["recommended_action"] = action
    annotated["policy_reason"] = reason
    annotated["batch_decision_candidate"] = "yes" if lane == "tag_batch_candidate" else "no"
    annotated["auto_merge_candidate"] = (
        "possible_but_not_recommended"
        if group_type in {"duplicate_people", "duplicate_leads"} and row.get("draft_keeper")
        else "no"
    )
    annotated["conservative_policy"] = "Manual review"
    if lane == "tag_batch_candidate":
        annotated["guided_policy"] = "Batch tag decision candidate"
    elif lane == "short_guided_review":
        annotated["guided_policy"] = "Short guided review"
    else:
        annotated["guided_policy"] = "Manual review first"
    if group_type in {"duplicate_people", "duplicate_leads"}:
        annotated["aggressive_policy"] = "Auto-merge to draft keeper; not recommended yet"
    elif group_type == "duplicate_tags":
        annotated["aggressive_policy"] = "Auto-mark normalized duplicate tags handled"
    else:
        annotated["aggressive_policy"] = "Hold for lead/person policy"
    return annotated


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "group_type",
        "queue_label",
        "group_key",
        "group_label",
        "status",
        "priority",
        "review_score",
        "record_count",
        "flag_count",
        "people_count",
        "lead_count",
        "definition_count",
        "sample_names",
        "draft_keeper",
        "draft_keeper_type",
        "draft_keeper_id",
        "draft_manual_review_fields",
        "draft_blank_field_suggestions",
        "draft_history_records",
        "draft_history_signals",
        "decision",
        "decision_label",
        "decision_note",
        "recommended_lane",
        "recommended_lane_label",
        "recommended_action",
        "policy_reason",
        "batch_decision_candidate",
        "auto_merge_candidate",
        "conservative_policy",
        "guided_policy",
        "aggressive_policy",
        "headline",
        "reasons",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clip(value: Any, limit: int = 80) -> str:
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
            text = clip(row.get(key), 96).replace("|", "/")
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return lines


def sort_for_review(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            LANE_ORDER.get(str(row.get("recommended_lane")), 99),
            PRIORITY_ORDER.get(str(row.get("priority") or "Low"), 3),
            -as_int(row, "review_score"),
            -as_int(row, "record_count"),
            str(row.get("group_label") or row.get("group_key") or "").lower(),
        ),
    )


def summary_by_lane(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(row.get("recommended_lane")) for row in rows)
    priority_counts: Counter[tuple[str, str]] = Counter(
        (str(row.get("recommended_lane")), str(row.get("priority") or "Low")) for row in rows
    )
    output = []
    for lane in sorted(counts, key=lambda value: LANE_ORDER.get(value, 99)):
        output.append(
            {
                "lane": LANE_LABELS.get(lane, lane),
                "groups": counts[lane],
                "high": priority_counts[(lane, "High")],
                "medium": priority_counts[(lane, "Medium")],
                "low": priority_counts[(lane, "Low")],
            }
        )
    return output


def summary_by_type(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for group_type, label in GROUP_TYPES:
        group_rows = [row for row in rows if row.get("group_type") == group_type]
        output.append(
            {
                "queue": label,
                "groups": len(group_rows),
                "high": sum(1 for row in group_rows if row.get("priority") == "High"),
                "medium": sum(1 for row in group_rows if row.get("priority") == "Medium"),
                "low": sum(1 for row in group_rows if row.get("priority") == "Low"),
            }
        )
    return output


def policy_comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(rows)
    short_guided = sum(1 for row in rows if row.get("recommended_lane") == "short_guided_review")
    tag_batch = sum(1 for row in rows if row.get("recommended_lane") == "tag_batch_candidate")
    guided_manual_first = total - short_guided - tag_batch
    aggressive_auto = sum(1 for row in rows if row.get("group_type") in {"duplicate_people", "duplicate_leads"})
    overlap_manual = sum(1 for row in rows if row.get("group_type") == "lead_person_overlap")
    return [
        {
            "policy": "Conservative",
            "manual_first": total,
            "short_guided_review": 0,
            "batch_decision_candidates": 0,
            "auto_merge_candidates": 0,
            "recommendation": "Safest, slowest.",
        },
        {
            "policy": "Guided",
            "manual_first": guided_manual_first,
            "short_guided_review": short_guided,
            "batch_decision_candidates": tag_batch,
            "auto_merge_candidates": 0,
            "recommendation": "Recommended next path.",
        },
        {
            "policy": "Aggressive",
            "manual_first": overlap_manual,
            "short_guided_review": 0,
            "batch_decision_candidates": tag_batch,
            "auto_merge_candidates": aggressive_auto,
            "recommendation": "Do not use until rules are proven.",
        },
    ]


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = len(rows)
    short_guided = sum(1 for row in rows if row.get("recommended_lane") == "short_guided_review")
    tag_batch = sum(1 for row in rows if row.get("recommended_lane") == "tag_batch_candidate")
    manual_first = total - short_guided - tag_batch
    sorted_rows = sort_for_review(rows)
    top_rows = sorted(
        rows,
        key=lambda row: (
            PRIORITY_ORDER.get(str(row.get("priority") or "Low"), 3),
            -as_int(row, "review_score"),
            -as_int(row, "record_count"),
        ),
    )[:14]

    lines = [
        "# Merge Policy Options",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Use the Guided policy next. It keeps every person, lead, and lead/person overlap merge under human review, but separates the work into faster lanes. Duplicate tag definitions are the only current batch-decision candidate because the local CRM has already normalized tag aliases while preserving assignments.",
        "",
        f"- Open cleanup groups: {total:,}.",
        f"- Manual review first: {manual_first:,}.",
        f"- Short guided reviews: {short_guided:,}.",
        f"- Batch tag decision candidates: {tag_batch:,}.",
        "- Auto-merge candidates recommended today: 0.",
        "",
        "## Policy Comparison",
        "",
        *table(
            policy_comparison(rows),
            [
                ("policy", "Policy"),
                ("manual_first", "Manual First"),
                ("short_guided_review", "Short Guided"),
                ("batch_decision_candidates", "Batch Candidates"),
                ("auto_merge_candidates", "Auto-Merge"),
                ("recommendation", "Recommendation"),
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
        "## Queue Summary",
        "",
        *table(
            summary_by_type(rows),
            [
                ("queue", "Queue"),
                ("groups", "Groups"),
                ("high", "High"),
                ("medium", "Medium"),
                ("low", "Low"),
            ],
        ),
        "",
        "## Highest-Impact Groups",
        "",
        *table(
            top_rows,
            [
                ("queue_label", "Queue"),
                ("group_label", "Group"),
                ("recommended_lane_label", "Lane"),
                ("priority", "Priority"),
                ("review_score", "Score"),
                ("record_count", "Records"),
                ("draft_manual_review_fields", "Manual Fields"),
                ("draft_keeper", "Draft Keeper"),
            ],
        ),
        "",
        "## Suggested Review Order",
        "",
        *table(
            sorted_rows,
            [
                ("queue_label", "Queue"),
                ("group_label", "Group"),
                ("recommended_lane_label", "Lane"),
                ("priority", "Priority"),
                ("record_count", "Records"),
                ("draft_manual_review_fields", "Manual Fields"),
                ("draft_blank_field_suggestions", "Blank Fills"),
                ("recommended_action", "Action"),
            ],
            limit=24,
        ),
        "",
        "## Decision Gates",
        "",
        "1. Duplicate people: decide whether same-email people can merge after a guided review accepts a keeper and preserves history.",
        "2. Duplicate leads: decide whether same-email leads should merge, or stay separate when they represent different application histories.",
        "3. Lead/person overlap: decide whether the person record usually becomes the keeper and the lead becomes preserved history.",
        "4. Duplicate tags: decide whether normalized duplicate tag aliases can be marked already handled as one batch.",
        "5. Merge execution: require a fresh backup, preview counts, and an undo path before any future merge operation is enabled.",
        "",
        "## Related Files",
        "",
        "- `reports/merge_policy_options.csv`",
        "- `reports/cleanup_decision_readiness.md`",
        "- `reports/cleanup_decision_readiness.csv`",
        "- `reports/local_crm_cleanup_merge_drafts_open.csv` from the Exports view or API",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = [annotate_row(row) for row in cleanup_group_rows(app)]
    rows = sort_for_review(rows)
    write_csv(REPORTS_DIR / "merge_policy_options.csv", rows)
    (REPORTS_DIR / "merge_policy_options.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} cleanup groups to reports/merge_policy_options.md and .csv")


if __name__ == "__main__":
    main()
