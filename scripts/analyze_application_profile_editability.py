#!/usr/bin/env python3
"""Generate a non-destructive Application Profile editability review."""

from __future__ import annotations

import csv
import sqlite3
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
EDITABLE_AFTER_CLEANUP = {"Desired Growth", "Time Frame", "Invest?"}
READ_ONLY_HISTORY = {
    "APP Number",
    "Date Created",
    "Experience",
    "Skills",
    "Success Is",
    "Why Waiting",
    "Why a Fit",
}
GROUP_TYPES = [
    ("lead_person_overlap", "Lead/Person Overlap"),
    ("duplicate_people", "Duplicate People"),
    ("duplicate_leads", "Duplicate Leads"),
]


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def clip(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def normalize_value(value: Any) -> str:
    return " ".join(str(value if value is not None else "").split()).casefold()


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


def role_for_field(field_name: str) -> tuple[str, str]:
    if field_name in EDITABLE_AFTER_CLEANUP:
        return (
            "Editable later",
            "Operational segment field; useful for list filters and day-to-day CRM updates after cleanup.",
        )
    if field_name == "APP Number":
        return (
            "Read-only identity",
            "Imported application identifier; changing it would make audit/history harder.",
        )
    if field_name == "Date Created":
        return (
            "Read-only timestamp",
            "Imported application intake date; keep separate from local CRM edit dates.",
        )
    return (
        "Read-only intake history",
        "Long-form application answer; better preserved as historical context than edited as a working CRM field.",
    )


def field_stats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for field_name in server.APPLICATION_PROFILE_FIELDS:
        record_type_counts = {
            row["record_type"]: row
            for row in rows_to_dicts(
                conn.execute(
                    """
                    SELECT record_type,
                           count(DISTINCT record_id) AS records,
                           count(*) AS value_rows,
                           count(DISTINCT NULLIF(trim(coalesce(field_value, '')), '')) AS distinct_values
                    FROM custom_field_values
                    WHERE field_name = ?
                    GROUP BY record_type
                    """,
                    (field_name,),
                ).fetchall()
            )
        }
        total_values = sum(int(row.get("value_rows") or 0) for row in record_type_counts.values())
        distinct_values = conn.execute(
            """
            SELECT count(DISTINCT NULLIF(trim(coalesce(field_value, '')), ''))
            FROM custom_field_values
            WHERE field_name = ?
            """,
            (field_name,),
        ).fetchone()[0]
        samples = [
            clip(row["field_value"], 60)
            for row in conn.execute(
                """
                SELECT trim(field_value) AS field_value, count(*) AS count
                FROM custom_field_values
                WHERE field_name = ?
                  AND coalesce(trim(field_value), '') <> ''
                GROUP BY trim(field_value)
                ORDER BY count DESC, length(trim(field_value)), trim(field_value)
                LIMIT 4
                """,
                (field_name,),
            ).fetchall()
        ]
        role, rationale = role_for_field(field_name)
        rows.append(
            {
                "field_name": field_name,
                "recommended_role": role,
                "lead_records": int(record_type_counts.get("lead", {}).get("records") or 0),
                "person_records": int(record_type_counts.get("person", {}).get("records") or 0),
                "value_rows": total_values,
                "distinct_values": int(distinct_values or 0),
                "sample_values": " | ".join(samples),
                "rationale": rationale,
            }
        )
    return rows


def cleanup_groups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    groups = []
    for group_type, label in GROUP_TYPES:
        flag_type = {
            "duplicate_people": "duplicate_person_email",
            "duplicate_leads": "duplicate_lead_email",
            "lead_person_overlap": "lead_person_email_overlap",
        }[group_type]
        keys = [
            row["flag_key"]
            for row in conn.execute(
                """
                SELECT DISTINCT flag_key
                FROM review_flags
                WHERE flag_type = ?
                  AND status = 'open'
                  AND flag_key IS NOT NULL
                ORDER BY flag_key
                """,
                (flag_type,),
            ).fetchall()
        ]
        for group_key in keys:
            records = group_records(conn, group_type, group_key)
            groups.append(
                {
                    "group_type": group_type,
                    "queue_label": label,
                    "group_key": group_key,
                    "records": records,
                }
            )
    return groups


def group_records(conn: sqlite3.Connection, group_type: str, group_key: str) -> list[dict[str, Any]]:
    if group_type == "duplicate_people":
        return rows_to_dicts(
            conn.execute(
                "SELECT 'person' AS record_type, id AS record_id, name, email FROM people WHERE normalized_email = ? ORDER BY updated_at DESC, id",
                (group_key,),
            ).fetchall()
        )
    if group_type == "duplicate_leads":
        return rows_to_dicts(
            conn.execute(
                "SELECT 'lead' AS record_type, id AS record_id, name, email FROM leads WHERE normalized_email = ? ORDER BY updated_at DESC, id",
                (group_key,),
            ).fetchall()
        )
    return rows_to_dicts(
        conn.execute(
            """
            SELECT 'lead' AS record_type, id AS record_id, name, email
            FROM leads
            WHERE normalized_email = ?
            UNION ALL
            SELECT 'person' AS record_type, id AS record_id, name, email
            FROM people
            WHERE normalized_email = ?
            ORDER BY record_type, record_id
            """,
            (group_key, group_key),
        ).fetchall()
    )


def profile_values_for_group(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    values_by_record = {f"{record['record_type']}:{record['record_id']}": {} for record in records}
    for record_type in {"person", "lead"}:
        ids = [int(record["record_id"]) for record in records if record["record_type"] == record_type]
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        field_placeholders = ",".join("?" for _ in server.APPLICATION_PROFILE_FIELDS)
        rows = rows_to_dicts(
            conn.execute(
                f"""
                SELECT record_id, field_name, field_value
                FROM custom_field_values
                WHERE record_type = ?
                  AND record_id IN ({placeholders})
                  AND field_name IN ({field_placeholders})
                  AND coalesce(trim(field_value), '') <> ''
                """,
                (record_type, *ids, *server.APPLICATION_PROFILE_FIELDS),
            ).fetchall()
        )
        for row in rows:
            values_by_record[f"{record_type}:{row['record_id']}"][row["field_name"]] = row["field_value"]
    return values_by_record


def cleanup_profile_conflicts(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    field_summary = {
        field_name: {
            "field_name": field_name,
            "conflict_groups": 0,
            "fill_gap_groups": 0,
            "duplicate_people_conflicts": 0,
            "duplicate_leads_conflicts": 0,
            "overlap_conflicts": 0,
        }
        for field_name in server.APPLICATION_PROFILE_FIELDS
    }
    examples = []
    for group in cleanup_groups(conn):
        records = group["records"]
        values_by_record = profile_values_for_group(conn, records)
        conflict_fields = []
        fill_gap_fields = []
        for field_name in server.APPLICATION_PROFILE_FIELDS:
            filled_values = [
                values.get(field_name)
                for values in values_by_record.values()
                if values.get(field_name) not in {None, ""}
            ]
            normalized = {normalize_value(value) for value in filled_values if normalize_value(value)}
            missing_count = len(records) - len(filled_values)
            if len(normalized) > 1:
                conflict_fields.append(field_name)
                field_summary[field_name]["conflict_groups"] += 1
                if group["group_type"] == "duplicate_people":
                    field_summary[field_name]["duplicate_people_conflicts"] += 1
                elif group["group_type"] == "duplicate_leads":
                    field_summary[field_name]["duplicate_leads_conflicts"] += 1
                else:
                    field_summary[field_name]["overlap_conflicts"] += 1
            if filled_values and missing_count > 0:
                fill_gap_fields.append(field_name)
                field_summary[field_name]["fill_gap_groups"] += 1
        if conflict_fields or fill_gap_fields:
            examples.append(
                {
                    "queue_label": group["queue_label"],
                    "group_key": group["group_key"],
                    "record_count": len(records),
                    "records": " | ".join(
                        f"{record['record_type'].title()} #{record['record_id']}: {record.get('name') or '(blank name)'}"
                        for record in records
                    ),
                    "conflict_fields": ", ".join(conflict_fields),
                    "fill_gap_fields": ", ".join(fill_gap_fields),
                }
            )
    return list(field_summary.values()), examples


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


def generate_report(field_rows: list[dict[str, Any]], conflict_rows: list[dict[str, Any]], examples: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total_profile_records = {
        "lead": max(int(row["lead_records"]) for row in field_rows),
        "person": max(int(row["person_records"]) for row in field_rows),
    }
    total_values = sum(int(row["value_rows"]) for row in field_rows)
    conflict_groups = sum(1 for row in examples if row.get("conflict_fields"))
    fill_gap_groups = sum(1 for row in examples if row.get("fill_gap_fields"))
    editable_rows = [row for row in field_rows if row["field_name"] in EDITABLE_AFTER_CLEANUP]
    read_only_rows = [row for row in field_rows if row["field_name"] not in EDITABLE_AFTER_CLEANUP]

    lines = [
        "# Application Profile Editability Review",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. Running it does not rename, edit, merge, delete, resolve, ignore, or rewrite any CRM record.",
        "",
        "## Recommendation",
        "",
        "Save the current recommended project path: Read-only until cleanup. The Application Profile is already useful as a promoted view and filter surface. Make fields editable only after duplicate/overlap cleanup rules are settled, because some open groups contain conflicting or partially missing profile answers.",
        "",
        "After cleanup, use a hybrid model: make the three operational segment fields editable, keep application identifiers/timestamps read-only, and preserve long-form application answers as intake history.",
        "",
        f"- Lead profile records: {total_profile_records['lead']:,}.",
        f"- Person profile records: {total_profile_records['person']:,}.",
        f"- Application Profile value rows: {total_values:,}.",
        f"- Editable-after-cleanup candidates: {len(editable_rows):,}.",
        f"- Read-only/history fields: {len(read_only_rows):,}.",
        f"- Cleanup groups with profile conflicts: {conflict_groups:,}.",
        f"- Cleanup groups with profile fill gaps: {fill_gap_groups:,}.",
        "",
        "## Proposed Field Roles",
        "",
        *table(
            field_rows,
            [
                ("field_name", "Field"),
                ("recommended_role", "Role"),
                ("lead_records", "Lead Records"),
                ("person_records", "Person Records"),
                ("distinct_values", "Distinct Values"),
                ("sample_values", "Common/Sample Values"),
                ("rationale", "Rationale"),
            ],
        ),
        "",
        "## Cleanup Dependency",
        "",
        "These counts show where duplicate people, duplicate leads, or lead/person overlaps already contain different Application Profile answers or one record has an answer another lacks.",
        "",
        *table(
            conflict_rows,
            [
                ("field_name", "Field"),
                ("conflict_groups", "Conflict Groups"),
                ("fill_gap_groups", "Fill Gaps"),
                ("duplicate_people_conflicts", "People Conflicts"),
                ("duplicate_leads_conflicts", "Lead Conflicts"),
                ("overlap_conflicts", "Overlap Conflicts"),
            ],
        ),
        "",
        "## Example Cleanup Groups",
        "",
        *table(
            sorted(examples, key=lambda row: (0 if row.get("conflict_fields") else 1, row.get("queue_label") or "", row.get("group_key") or "")),
            [
                ("queue_label", "Queue"),
                ("group_key", "Group"),
                ("record_count", "Records"),
                ("conflict_fields", "Conflicting Profile Fields"),
                ("fill_gap_fields", "Profile Fill Gaps"),
                ("records", "Record Examples"),
            ],
            limit=24,
        ),
        "",
        "## Decision Guidance",
        "",
        "- Choose Read-only until cleanup now.",
        "- Revisit Hybrid core editable after duplicate people/leads/overlaps have saved policies and reviewed group decisions.",
        "- Do not make APP Number or Date Created editable; they are audit/history fields.",
        "- Do not turn long-form fields into ordinary editable CRM properties unless a daily workflow needs that later.",
        "",
        "## Related Files",
        "",
        "- `reports/application_profile_editability_review.csv`",
        "- `reports/application_profile_cleanup_conflicts.csv`",
        "- `reports/application_profile_cleanup_examples.csv`",
        "- `reports/custom_field_promotion_recommendations.md`",
        "- `reports/project_decision_brief.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        fields = field_stats(conn)
        conflicts, examples = cleanup_profile_conflicts(conn)
    write_csv(REPORTS_DIR / "application_profile_editability_review.csv", fields)
    write_csv(REPORTS_DIR / "application_profile_cleanup_conflicts.csv", conflicts)
    write_csv(REPORTS_DIR / "application_profile_cleanup_examples.csv", examples)
    (REPORTS_DIR / "application_profile_editability_review.md").write_text(
        generate_report(fields, conflicts, examples),
        encoding="utf-8",
    )
    print(f"Wrote {len(fields):,} Application Profile fields to reports/application_profile_editability_review.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
