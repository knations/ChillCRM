#!/usr/bin/env python3
"""Generate a non-destructive unlinked archive matching report."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"


def normalize_phone(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 7:
        return None
    return digits[-10:] if len(digits) >= 10 else digits


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


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def phone_index(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources = [
        ("people", "person", ["phone", "mobile"], "name", "email"),
        ("companies", "company", ["phone"], "name", "email"),
        ("leads", "lead", ["phone", "mobile"], "name", "email"),
    ]
    for table_name, record_type, fields, name_field, email_field in sources:
        field_sql = ", ".join(["id", name_field, email_field, *fields])
        for row in conn.execute(f"SELECT {field_sql} FROM {table_name}"):
            for field in fields:
                key = normalize_phone(row[field])
                if not key:
                    continue
                candidate = {
                    "record_type": record_type,
                    "record_id": row["id"],
                    "record_name": row[name_field],
                    "email": row[email_field],
                    "phone_field": field,
                    "phone_value": row[field],
                }
                candidates[key].append(candidate)
    deduped: dict[str, list[dict[str, Any]]] = {}
    for key, matches in candidates.items():
        seen: set[tuple[str, int, str]] = set()
        unique_matches = []
        for match in matches:
            dedupe_key = (str(match["record_type"]), int(match["record_id"]), str(match["phone_field"]))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            unique_matches.append(match)
        deduped[key] = unique_matches
    return deduped


def candidate_label(match: dict[str, Any]) -> str:
    label = f"{str(match.get('record_type') or '').title()} #{match.get('record_id')}: {match.get('record_name') or '(blank name)'}"
    if match.get("email"):
        label += f" <{match['email']}>"
    label += f" [{match.get('phone_field')}: {match.get('phone_value')}]"
    return label


def classification(phone_key: str | None, matches: list[dict[str, Any]]) -> str:
    if phone_key is None:
        return "short_or_non_contact_number"
    unique_records = {(match["record_type"], match["record_id"]) for match in matches}
    if len(unique_records) == 1:
        return "exact_unique_candidate"
    if len(unique_records) > 1:
        return "ambiguous_exact_candidates"
    return "no_crm_phone_match"


def archive_rows(conn: sqlite3.Connection, index: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = rows_to_dicts(
        conn.execute(
            """
            SELECT id, item_type, source_collection, zendesk_record_id, title, body,
                   direction, occurred_at, created_at, updated_at, user_id,
                   duration_seconds, phone_number, status, source_json
            FROM imported_archive_items
            WHERE record_id IS NULL
              AND item_type IN ('call', 'text_message')
            ORDER BY occurred_at DESC, id DESC
            """
        ).fetchall()
    )
    output = []
    for row in rows:
        phone_key = normalize_phone(row.get("phone_number"))
        matches = index.get(phone_key or "", [])
        row_class = classification(phone_key, matches)
        source = json.loads(row.get("source_json") or "{}")
        output.append(
            {
                "archive_id": row.get("id"),
                "item_type": row.get("item_type"),
                "classification": row_class,
                "phone_number": row.get("phone_number"),
                "normalized_phone": phone_key,
                "candidate_count": len({(match["record_type"], match["record_id"]) for match in matches}),
                "candidate_records": " | ".join(candidate_label(match) for match in matches[:8]),
                "title": row.get("title"),
                "direction": row.get("direction"),
                "status": row.get("status"),
                "duration_seconds": row.get("duration_seconds"),
                "occurred_at": row.get("occurred_at"),
                "body": clip(row.get("body"), 180),
                "source_collection": row.get("source_collection"),
                "zendesk_record_id": row.get("zendesk_record_id"),
                "resource_type": source.get("resource_type"),
                "resource_id": source.get("resource_id"),
                "associated_deal_ids": ", ".join(str(value) for value in source.get("associated_deal_ids") or []),
                "recommended_action": recommended_action(row_class),
            }
        )
    return output


def recommended_action(row_class: str) -> str:
    if row_class == "exact_unique_candidate":
        return "Candidate for later manual confirmation before linking."
    if row_class == "ambiguous_exact_candidates":
        return "Manual review only; more than one CRM record shares the phone."
    if row_class == "short_or_non_contact_number":
        return "Keep archive-only; number looks like a shortcode or service number."
    return "Keep archive-only unless another external clue identifies the contact."


def grouped_phone_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("item_type")), str(row.get("classification")), str(row.get("phone_number") or ""))
        group = groups.setdefault(
            key,
            {
                "item_type": row.get("item_type"),
                "classification": row.get("classification"),
                "phone_number": row.get("phone_number"),
                "normalized_phone": row.get("normalized_phone"),
                "items": 0,
                "first_at": row.get("occurred_at"),
                "last_at": row.get("occurred_at"),
                "candidate_count": row.get("candidate_count"),
                "candidate_records": row.get("candidate_records"),
                "sample_titles": [],
                "recommended_action": row.get("recommended_action"),
            },
        )
        group["items"] += 1
        if row.get("occurred_at"):
            if not group.get("first_at") or row["occurred_at"] < group["first_at"]:
                group["first_at"] = row["occurred_at"]
            if not group.get("last_at") or row["occurred_at"] > group["last_at"]:
                group["last_at"] = row["occurred_at"]
        if row.get("title") and len(group["sample_titles"]) < 3 and row["title"] not in group["sample_titles"]:
            group["sample_titles"].append(row["title"])
    output = []
    for group in groups.values():
        group = dict(group)
        group["sample_titles"] = " | ".join(group["sample_titles"])
        output.append(group)
    return sorted(
        output,
        key=lambda row: (
            {
                "exact_unique_candidate": 0,
                "ambiguous_exact_candidates": 1,
                "no_crm_phone_match": 2,
                "short_or_non_contact_number": 3,
            }.get(str(row.get("classification")), 9),
            -int(row.get("items") or 0),
            str(row.get("phone_number") or ""),
        ),
    )


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


def generate_report(rows: list[dict[str, Any]], grouped_rows: list[dict[str, Any]], phone_key_count: int) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    item_counts = Counter(str(row.get("item_type")) for row in rows)
    class_counts = Counter(str(row.get("classification")) for row in rows)
    phone_class_counts = Counter(str(row.get("classification")) for row in grouped_rows)
    strong_candidates = class_counts.get("exact_unique_candidate", 0)
    ambiguous_candidates = class_counts.get("ambiguous_exact_candidates", 0)
    no_match = class_counts.get("no_crm_phone_match", 0)
    short_number = class_counts.get("short_or_non_contact_number", 0)
    grouped_top = sorted(grouped_rows, key=lambda row: -int(row.get("items") or 0))
    lines = [
        "# Unlinked Archive Matching Candidates",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not link, merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Keep unlinked calls and texts archive-only for now. The first import already linked calls/texts when an exact phone number had one clear CRM match. In the remaining unlinked archive items, no call has a CRM phone match, most unlinked texts have no CRM phone match, and the rest are short-code/service-number style texts.",
        "",
        f"- Unlinked calls/texts reviewed: {len(rows):,}.",
        f"- Calls: {item_counts.get('call', 0):,}.",
        f"- Text messages: {item_counts.get('text_message', 0):,}.",
        f"- CRM phone keys available for matching: {phone_key_count:,}.",
        f"- Exact unique CRM phone candidates: {strong_candidates:,} items.",
        f"- Ambiguous exact CRM phone candidates: {ambiguous_candidates:,} items.",
        f"- No CRM phone match: {no_match:,} items.",
        f"- Short-code or non-contact number: {short_number:,} items.",
        "",
        "## Matching Classification",
        "",
        *table(
            [
                {
                    "classification": "Exact unique candidate",
                    "items": class_counts.get("exact_unique_candidate", 0),
                    "phones": phone_class_counts.get("exact_unique_candidate", 0),
                    "meaning": "One CRM record shares the normalized phone.",
                },
                {
                    "classification": "Ambiguous exact candidates",
                    "items": class_counts.get("ambiguous_exact_candidates", 0),
                    "phones": phone_class_counts.get("ambiguous_exact_candidates", 0),
                    "meaning": "More than one CRM record shares the normalized phone.",
                },
                {
                    "classification": "No CRM phone match",
                    "items": class_counts.get("no_crm_phone_match", 0),
                    "phones": phone_class_counts.get("no_crm_phone_match", 0),
                    "meaning": "No local person/company/lead has that normalized phone.",
                },
                {
                    "classification": "Short-code/non-contact number",
                    "items": class_counts.get("short_or_non_contact_number", 0),
                    "phones": phone_class_counts.get("short_or_non_contact_number", 0),
                    "meaning": "Number is too short to be treated as a contact phone.",
                },
            ],
            [("classification", "Classification"), ("items", "Items"), ("phones", "Phones"), ("meaning", "Meaning")],
        ),
        "",
        "## Highest-Volume Unlinked Numbers",
        "",
        *table(
            grouped_top,
            [
                ("item_type", "Type"),
                ("phone_number", "Phone"),
                ("classification", "Classification"),
                ("items", "Items"),
                ("first_at", "First"),
                ("last_at", "Last"),
                ("recommended_action", "Recommended Action"),
            ],
            limit=30,
        ),
        "",
        "## Candidate Rows",
        "",
        *table(
            rows,
            [
                ("archive_id", "Archive ID"),
                ("item_type", "Type"),
                ("phone_number", "Phone"),
                ("classification", "Classification"),
                ("candidate_records", "Candidate Records"),
                ("occurred_at", "Occurred"),
                ("title", "Title"),
            ],
            limit=40,
        ),
        "",
        "## Decision Guidance",
        "",
        "- Recommended project decision: Archive-only for now.",
        "- Use the local CRM Archive Manual Review Queue to work the remaining items in small batches and mark review status before linking anything.",
        "- A manual matching pass should mostly confirm archive-only or needs-lookup status because these numbers have no CRM phone evidence.",
        "- If a specific item is identified by human review, use the Archive row inspector in the local CRM to link it manually; that action creates a backup and audit entry before changing the archive item.",
        "- If matching is revisited later, start with any future exact unique candidates first, then ambiguous exact candidates. Do not infer matches from area code alone.",
        "",
        "## Related Files",
        "",
        "- `reports/unlinked_archive_matching_candidates.csv`",
        "- `reports/zendesk_sell_optional_data_sweep.md`",
        "- `reports/project_decision_brief.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        index = phone_index(conn)
        rows = archive_rows(conn, index)
    grouped_rows = grouped_phone_rows(rows)
    write_csv(REPORTS_DIR / "unlinked_archive_matching_candidates.csv", rows)
    write_csv(REPORTS_DIR / "unlinked_archive_matching_phone_groups.csv", grouped_rows)
    (REPORTS_DIR / "unlinked_archive_matching_candidates.md").write_text(
        generate_report(rows, grouped_rows, len(index)),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows):,} unlinked archive items to reports/unlinked_archive_matching_candidates.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
