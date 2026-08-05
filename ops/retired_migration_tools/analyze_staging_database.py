#!/usr/bin/env python3
"""Analyze the Zendesk Sell staging database for migration planning."""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path
from typing import Any


def rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return conn.execute(sql, params).fetchall()


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def write_csv(path: Path, result_rows: list[sqlite3.Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        if not result_rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=result_rows[0].keys())
        writer.writeheader()
        for row in result_rows:
            writer.writerow(dict(row))


def md_table(headers: list[str], data: list[list[Any]]) -> str:
    if not data:
        return "_None found._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in data:
        lines.append("| " + " | ".join("" if value is None else str(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Zendesk Sell staging database.")
    parser.add_argument("--db-path", default="staging_database/zendesk_sell_staging.sqlite")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()

    db_path = Path(args.db_path).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    counts = {
        "contacts": scalar(conn, "SELECT count(*) FROM contacts"),
        "people": scalar(conn, "SELECT count(*) FROM contacts WHERE kind = 'person'"),
        "companies": scalar(conn, "SELECT count(*) FROM contacts WHERE kind = 'company'"),
        "leads": scalar(conn, "SELECT count(*) FROM leads"),
        "deals": scalar(conn, "SELECT count(*) FROM deals"),
        "notes": scalar(conn, "SELECT count(*) FROM notes"),
        "tasks": scalar(conn, "SELECT count(*) FROM tasks"),
        "tags": scalar(conn, "SELECT count(*) FROM tags"),
        "custom_field_values": scalar(conn, "SELECT count(*) FROM custom_field_values"),
        "tag_assignments": scalar(conn, "SELECT count(*) FROM tag_assignments"),
    }

    report_queries = {
        "duplicate_contact_emails.csv": """
            SELECT normalized_email AS email, count(*) AS record_count
            FROM contacts
            WHERE normalized_email IS NOT NULL
            GROUP BY normalized_email
            HAVING count(*) > 1
            ORDER BY record_count DESC, email
        """,
        "duplicate_lead_emails.csv": """
            SELECT normalized_email AS email, count(*) AS record_count
            FROM leads
            WHERE normalized_email IS NOT NULL
            GROUP BY normalized_email
            HAVING count(*) > 1
            ORDER BY record_count DESC, email
        """,
        "contact_lead_email_overlap.csv": """
            SELECT c.normalized_email AS email,
                   count(DISTINCT c.source_id) AS contact_count,
                   count(DISTINCT l.source_id) AS lead_count
            FROM contacts c
            JOIN leads l ON l.normalized_email = c.normalized_email
            WHERE c.normalized_email IS NOT NULL
            GROUP BY c.normalized_email
            ORDER BY contact_count DESC, lead_count DESC, email
        """,
        "duplicate_company_names.csv": """
            SELECT lower(trim(name)) AS company_name, count(*) AS record_count
            FROM contacts
            WHERE kind = 'company' AND name IS NOT NULL AND trim(name) != ''
            GROUP BY lower(trim(name))
            HAVING count(*) > 1
            ORDER BY record_count DESC, company_name
        """,
        "duplicate_tag_names.csv": """
            SELECT lower(trim(name)) AS tag_name, count(*) AS definition_count,
                   group_concat(DISTINCT resource_type) AS resource_types
            FROM tags
            WHERE name IS NOT NULL AND trim(name) != ''
            GROUP BY lower(trim(name))
            HAVING count(*) > 1
            ORDER BY definition_count DESC, tag_name
        """,
        "stage_breakdown.csv": """
            SELECT s.position, s.name AS stage_name, s.category,
                   count(d.source_id) AS deal_count,
                   coalesce(round(sum(d.value), 2), 0) AS total_value
            FROM stages s
            LEFT JOIN deals d ON d.stage_id = s.source_id
            GROUP BY s.source_id
            ORDER BY s.position
        """,
        "lead_status_breakdown.csv": """
            SELECT coalesce(status, '(blank)') AS status, count(*) AS lead_count
            FROM leads
            GROUP BY coalesce(status, '(blank)')
            ORDER BY lead_count DESC
        """,
        "custom_field_usage.csv": """
            SELECT record_type, field_name,
                   count(*) AS records_with_field,
                   sum(CASE WHEN field_value IS NOT NULL AND trim(field_value) != '' THEN 1 ELSE 0 END)
                       AS records_with_value
            FROM custom_field_values
            GROUP BY record_type, field_name
            ORDER BY record_type, field_name
        """,
        "tag_usage.csv": """
            SELECT tag, count(*) AS assignment_count,
                   group_concat(DISTINCT record_type) AS record_types
            FROM tag_assignments
            GROUP BY tag
            ORDER BY assignment_count DESC, tag
        """,
        "owner_breakdown.csv": """
            SELECT u.name AS owner_name, u.email AS owner_email,
                   (SELECT count(*) FROM contacts c WHERE c.owner_id = u.source_id) AS contacts,
                   (SELECT count(*) FROM leads l WHERE l.owner_id = u.source_id) AS leads,
                   (SELECT count(*) FROM deals d WHERE d.owner_id = u.source_id) AS deals,
                   (SELECT count(*) FROM tasks t WHERE t.owner_id = u.source_id) AS tasks
            FROM users u
            ORDER BY contacts DESC, leads DESC, deals DESC
        """,
        "relationship_issues.csv": """
            SELECT 'deal_missing_contact' AS issue_type, source_id AS record_id, contact_id AS linked_id
            FROM deals
            WHERE contact_id IS NOT NULL
              AND contact_id NOT IN (SELECT source_id FROM contacts)
            UNION ALL
            SELECT 'deal_missing_organization' AS issue_type, source_id AS record_id, organization_id AS linked_id
            FROM deals
            WHERE organization_id IS NOT NULL
              AND organization_id NOT IN (SELECT source_id FROM contacts)
            UNION ALL
            SELECT 'note_missing_resource' AS issue_type, source_id AS record_id, resource_id AS linked_id
            FROM notes
            WHERE resource_type = 'contact'
              AND resource_id NOT IN (SELECT source_id FROM contacts)
            UNION ALL
            SELECT 'note_missing_deal' AS issue_type, source_id AS record_id, resource_id AS linked_id
            FROM notes
            WHERE resource_type = 'deal'
              AND resource_id NOT IN (SELECT source_id FROM deals)
            UNION ALL
            SELECT 'task_missing_contact' AS issue_type, source_id AS record_id, resource_id AS linked_id
            FROM tasks
            WHERE resource_type = 'contact'
              AND resource_id NOT IN (SELECT source_id FROM contacts)
            UNION ALL
            SELECT 'task_missing_deal' AS issue_type, source_id AS record_id, resource_id AS linked_id
            FROM tasks
            WHERE resource_type = 'deal'
              AND resource_id NOT IN (SELECT source_id FROM deals)
            ORDER BY issue_type, record_id
        """,
    }

    query_results: dict[str, list[sqlite3.Row]] = {}
    for filename, sql in report_queries.items():
        result_rows = rows(conn, sql)
        query_results[filename] = result_rows
        write_csv(reports_dir / filename, result_rows)

    db_size = os.path.getsize(db_path)
    relationship_issue_count = len(query_results["relationship_issues.csv"])

    stage_rows = query_results["stage_breakdown.csv"]
    lead_status_rows = query_results["lead_status_breakdown.csv"]
    duplicate_tag_rows = query_results["duplicate_tag_names.csv"]
    custom_field_rows = query_results["custom_field_usage.csv"]

    lines: list[str] = []
    lines.append("# Zendesk Sell Staging Analysis")
    lines.append("")
    lines.append(f"Database: `{db_path}`")
    lines.append(f"Database size: `{db_size:,}` bytes")
    lines.append("")
    lines.append("## Summary Counts")
    lines.append("")
    lines.append(md_table(["Object", "Count"], [[key.replace("_", " ").title(), value] for key, value in counts.items()]))
    lines.append("## Deal Pipeline")
    lines.append("")
    lines.append(md_table(["Position", "Stage", "Category", "Deals", "Total Value"], [
        [row["position"], row["stage_name"], row["category"], row["deal_count"], row["total_value"]]
        for row in stage_rows
    ]))
    lines.append("## Lead Statuses")
    lines.append("")
    lines.append(md_table(["Status", "Leads"], [[row["status"], row["lead_count"]] for row in lead_status_rows]))
    lines.append("## Cleanup Signals")
    lines.append("")
    lines.append(md_table(
        ["Signal", "Count"],
        [
            ["Duplicate contact email groups", len(query_results["duplicate_contact_emails.csv"])],
            ["Duplicate lead email groups", len(query_results["duplicate_lead_emails.csv"])],
            ["Contact/lead email overlaps", len(query_results["contact_lead_email_overlap.csv"])],
            ["Duplicate company name groups", len(query_results["duplicate_company_names.csv"])],
            ["Duplicate tag name groups", len(duplicate_tag_rows)],
            ["Relationship issues", relationship_issue_count],
        ],
    ))
    lines.append("## Top Duplicate Tags")
    lines.append("")
    lines.append(md_table(["Tag", "Definitions", "Resource Types"], [
        [row["tag_name"], row["definition_count"], row["resource_types"]]
        for row in duplicate_tag_rows[:15]
    ]))
    lines.append("## Custom Field Usage")
    lines.append("")
    lines.append(md_table(["Record Type", "Field", "Has Field", "Has Value"], [
        [row["record_type"], row["field_name"], row["records_with_field"], row["records_with_value"]]
        for row in custom_field_rows
    ]))
    lines.append("## Detailed Local CSVs")
    lines.append("")
    for filename in report_queries:
        lines.append(f"- `{filename}`")
    lines.append("")
    lines.append("## Recommended Next Move")
    lines.append("")
    lines.append(
        "Design the local CRM schema around people, companies, leads, deals, notes, tasks, tags, "
        "and custom application fields, then decide how aggressively to merge leads into existing contacts."
    )
    lines.append("")

    report_path = reports_dir / "staging_analysis.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {report_path}")
    for filename in report_queries:
        print(f"Wrote {reports_dir / filename}")
    print()
    print("Cleanup signals:")
    print(f"- duplicate contact email groups: {len(query_results['duplicate_contact_emails.csv'])}")
    print(f"- duplicate lead email groups: {len(query_results['duplicate_lead_emails.csv'])}")
    print(f"- contact/lead email overlaps: {len(query_results['contact_lead_email_overlap.csv'])}")
    print(f"- duplicate company name groups: {len(query_results['duplicate_company_names.csv'])}")
    print(f"- duplicate tag name groups: {len(duplicate_tag_rows)}")
    print(f"- relationship issues: {relationship_issue_count}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
