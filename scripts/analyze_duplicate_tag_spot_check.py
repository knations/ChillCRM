#!/usr/bin/env python3
"""Generate a non-destructive duplicate tag spot-check report."""

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
    return "; ".join(output)


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
        "tag_id",
        "local_tag",
        "normalized_name",
        "priority",
        "review_score",
        "definition_count",
        "assignment_count",
        "people_count",
        "company_count",
        "lead_count",
        "deal_count",
        "resource_types",
        "alias_count",
        "distinct_alias_names",
        "alias_resource_types",
        "aliases",
        "sample_records",
        "sample_names",
        "decision",
        "decision_label",
        "decision_note",
        "policy_lane",
        "policy_action",
        "spot_check_note",
        "recommended_action",
        "first_seen",
        "last_seen",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def alias_label(alias: dict[str, Any]) -> str:
    parts = [str(alias.get("source_name") or "(blank tag)")]
    if alias.get("resource_type"):
        parts.append(f"[{alias['resource_type']}]")
    if alias.get("zendesk_tag_id"):
        parts.append(f"Zendesk #{alias['zendesk_tag_id']}")
    return " ".join(parts)


def sample_record_label(record: dict[str, Any]) -> str:
    name = record.get("name") or "(blank name)"
    label = f"{record.get('record_type', 'record')} #{record.get('source_id')}: {name}"
    if record.get("email"):
        label += f" <{record['email']}>"
    if record.get("source_name"):
        label += f" [{record['source_name']}]"
    return label


def spot_check_note(alias_names: list[str], resource_types: list[str]) -> str:
    if len(alias_names) <= 1 and len(resource_types) <= 1:
        return "Aliases match exactly in one resource type."
    if len(alias_names) <= 1:
        return "Same alias text appears across multiple Zendesk resource types."
    return "Alias text varies; spot-check spelling before saving the tag policy."


def duplicate_tag_rows(app: server.CRMRequestHandler) -> list[dict[str, Any]]:
    export = app.export_cleanup_group_rows({"type": ["duplicate_tags"], "status": ["open"], "sort": ["policy"]})
    rows: list[dict[str, Any]] = []
    for group in export["rows"]:
        detail = app.cleanup_groups({"type": ["duplicate_tags"], "status": ["open"], "key": [str(group.get("group_key"))]})
        counts = detail.get("counts") or {}
        aliases = detail.get("aliases") or []
        records = detail.get("records") or []
        alias_names = sorted({str(alias.get("source_name") or "").strip() for alias in aliases if alias.get("source_name")})
        alias_resource_types = sorted({str(alias.get("resource_type") or "").strip() for alias in aliases if alias.get("resource_type")})
        decision = detail.get("decision") or {}
        guidance = detail.get("guidance") or {}
        policy_lane = group.get("policy_lane") or ""
        row = {
            "tag_id": group.get("group_key"),
            "local_tag": counts.get("display_name") or group.get("group_label"),
            "normalized_name": counts.get("normalized_name"),
            "priority": guidance.get("priority") or group.get("priority"),
            "review_score": guidance.get("score") or group.get("review_score"),
            "definition_count": counts.get("definition_count") or group.get("definition_count"),
            "assignment_count": counts.get("record_count") or group.get("record_count"),
            "people_count": counts.get("people_count") or group.get("people_count"),
            "company_count": counts.get("company_count") or group.get("company_count"),
            "lead_count": counts.get("lead_count") or group.get("lead_count"),
            "deal_count": counts.get("deal_count") or group.get("deal_count"),
            "resource_types": counts.get("resource_types") or group.get("resource_types"),
            "alias_count": len(aliases),
            "distinct_alias_names": join_unique(alias_names),
            "alias_resource_types": join_unique(alias_resource_types),
            "aliases": join_unique([alias_label(alias) for alias in aliases]),
            "sample_records": join_unique([sample_record_label(record) for record in records], limit=8),
            "sample_names": group.get("sample_names"),
            "decision": decision.get("decision"),
            "decision_label": server.CLEANUP_GROUP_DECISIONS.get(decision.get("decision"), ""),
            "decision_note": decision.get("note"),
            "policy_lane": policy_lane,
            "policy_action": group.get("policy_action") or "Candidate for one batch tag decision after a spot check.",
            "spot_check_note": spot_check_note(alias_names, alias_resource_types),
            "recommended_action": "Spot check aliases, then save the duplicate-tag project policy if the aliases look correct.",
            "first_seen": group.get("first_seen"),
            "last_seen": group.get("last_seen"),
        }
        rows.append(row)
    return rows


def project_decision_summary(app: server.CRMRequestHandler) -> dict[str, Any]:
    decisions = app.project_decisions()
    duplicate_tag = next(
        (decision for decision in decisions.get("decisions", []) if decision.get("key") == "duplicate_tag_policy"),
        {},
    )
    preview_action = next(
        (
            action
            for action in app.cleanup_execution_preview(decisions).get("actions", [])
            if action.get("group_type") == "duplicate_tags"
        ),
        {},
    )
    recommended_action = next(
        (
            action
            for action in app.recommended_cleanup_execution_preview().get("actions", [])
            if action.get("group_type") == "duplicate_tags"
        ),
        {},
    )
    return {
        "status": duplicate_tag.get("status_label") or "Pending",
        "saved_path": duplicate_tag.get("choice_label") or "No saved path",
        "recommended_value": duplicate_tag.get("recommendation") or "mark_normalized_tags_handled",
        "recommended_path": (duplicate_tag.get("recommended_option") or {}).get("label") or "Mark normalized tags handled",
        "impact": (duplicate_tag.get("impact") or {}).get("summary") or "",
        "next_step": (duplicate_tag.get("impact") or {}).get("next_step") or "",
        "current_action_status": preview_action.get("status") or "",
        "recommended_action_status": recommended_action.get("status") or "",
        "recommended_eligible_groups": recommended_action.get("eligible_groups") or 0,
        "recommended_eligible_records": recommended_action.get("eligible_records") or 0,
    }


def decision_option_rows() -> list[dict[str, Any]]:
    definition = next(item for item in server.PROJECT_DECISIONS if item["key"] == "duplicate_tag_policy")
    recommended_value = definition.get("recommendation")
    option_effects = {
        "mark_normalized_tags_handled": {
            "choose_when": "The aliases in this report look like the same tag concepts.",
            "effect": "Records the policy; Cleanup Preview can show 32 tag groups as eligible candidates.",
        },
        "manual_review_each_tag": {
            "choose_when": "You want to inspect each duplicate tag group before accepting the normalized structure.",
            "effect": "Keeps the tag cleanup lane gated behind manual group review.",
        },
        "keep_aliases_visible": {
            "choose_when": "You want duplicate Zendesk definitions visible for audit/history despite normalized local assignments.",
            "effect": "Leaves the duplicate tag groups open as visible historical definitions.",
        },
    }
    rows = []
    for index, option in enumerate(definition["options"]):
        value = option["value"]
        rows.append(
            {
                "code": chr(ord("A") + index),
                "path": option["label"],
                "recommended": "Yes" if value == recommended_value else "",
                "choose_when": option_effects[value]["choose_when"],
                "effect": option_effects[value]["effect"],
                "value": value,
            }
        )
    return rows


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    priority_counts = Counter(str(row.get("priority") or "Low") for row in rows)
    total_assignments = sum(as_int(row.get("assignment_count")) for row in rows)
    total_definitions = sum(as_int(row.get("definition_count")) for row in rows)
    decision = project_decision_summary(app)
    options = decision_option_rows()

    exact_aliases = sum(1 for row in rows if str(row.get("spot_check_note") or "").startswith("Aliases match exactly"))
    cross_resource = sum(1 for row in rows if str(row.get("spot_check_note") or "").startswith("Same alias text"))
    varied_aliases = len(rows) - exact_aliases - cross_resource

    lines = [
        "# Duplicate Tag Spot Check",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Use this report as the final spot check before saving the Duplicate Tag policy. The local CRM has already normalized duplicate Zendesk tag definitions into single local tags while preserving assignments; this report shows the aliases and sample records behind that recommendation.",
        "",
        f"- Open duplicate tag groups: {len(rows):,}.",
        f"- Affected tag assignments: {total_assignments:,}.",
        f"- Zendesk tag definitions represented by those groups: {total_definitions:,}.",
        f"- Priority split: {priority_counts.get('High', 0):,} high, {priority_counts.get('Medium', 0):,} medium, {priority_counts.get('Low', 0):,} low.",
        f"- Current project decision: {decision['status']} / {decision['saved_path']}.",
        f"- Recommended project path: {decision['recommended_path']}.",
        f"- Recommended-path simulation: {decision['recommended_action_status'].replace('_', ' ') or 'unknown'} for {as_int(decision['recommended_eligible_groups']):,} groups and {as_int(decision['recommended_eligible_records']):,} assignments.",
        "",
        "## Decision Prompt",
        "",
        "Answer A, B, or C in Status when you are ready. This report does not save the decision.",
        "",
        *table(
            options,
            [
                ("code", "Choice"),
                ("path", "Path"),
                ("recommended", "Recommended"),
                ("choose_when", "Choose When"),
                ("effect", "After Save"),
            ],
        ),
        "",
        "## Save Boundary",
        "",
        "- Saving a Duplicate Tag project decision creates a local backup first.",
        "- Saving records the selected policy in Project Decisions, Activity, and the audit log.",
        "- Saving does not merge records, delete tags, resolve cleanup flags, rewrite tag assignments, or update Zendesk Sell.",
        "- Even with A saved, any future cleanup execution still needs its own preview, backup, and explicit confirmation.",
        "",
        "## What To Spot Check",
        "",
        "- Confirm alias names are the same tag concept, not two different meanings that happen to share a normalized name.",
        "- Confirm the assigned record types make sense for the tag.",
        "- Confirm the sample records look like expected users of the tag.",
        "- If the rows look right, choose A in Status before any future cleanup execution is enabled.",
        "",
        "## Alias Shape",
        "",
        f"- Exact same alias text in one resource type: {exact_aliases:,} groups.",
        f"- Same alias text across multiple resource types: {cross_resource:,} groups.",
        f"- Alias text varies by spelling or formatting: {varied_aliases:,} groups.",
        "",
        "## Duplicate Tag Groups",
        "",
        *table(
            rows,
            [
                ("tag_id", "Tag ID"),
                ("local_tag", "Local Tag"),
                ("priority", "Priority"),
                ("definition_count", "Definitions"),
                ("assignment_count", "Assignments"),
                ("resource_types", "Assigned To"),
                ("distinct_alias_names", "Alias Names"),
                ("spot_check_note", "Spot Check"),
            ],
        ),
        "",
        "## Sample Records",
        "",
        *table(
            rows,
            [
                ("local_tag", "Local Tag"),
                ("aliases", "Aliases"),
                ("sample_records", "Sample Assigned Records"),
            ],
        ),
        "",
        "## Related Files",
        "",
        "- `reports/duplicate_tag_spot_check.csv`",
        "- `reports/project_decision_option_matrix.md`",
        "- `reports/merge_policy_options.md`",
        "- `reports/project_decision_brief.md`",
        "- `reports/cleanup_decision_readiness.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = duplicate_tag_rows(app)
    write_csv(REPORTS_DIR / "duplicate_tag_spot_check.csv", rows)
    (REPORTS_DIR / "duplicate_tag_spot_check.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} duplicate tag groups to reports/duplicate_tag_spot_check.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
