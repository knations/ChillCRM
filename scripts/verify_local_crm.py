#!/usr/bin/env python3
"""Verify the final local CRM database against the staging database."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Any


EXPECTED_COUNTS = [
    ("users", "users"),
    ("companies", "contacts", "kind = 'company'"),
    ("people", "contacts", "kind = 'person'"),
    ("leads", "leads"),
    ("deals", "deals"),
    ("notes", "notes"),
    ("tasks", "tasks"),
    ("tag_assignments", "tag_assignments"),
    ("custom_field_values", "custom_field_values"),
]


def count(conn: sqlite3.Connection, table: str, where: str | None = None) -> int:
    sql = f"SELECT count(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return conn.execute(sql).fetchone()[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["result"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local CRM migration.")
    parser.add_argument("--staging-db", default="staging_database/zendesk_sell_staging.sqlite")
    parser.add_argument("--crm-db", default="crm_database/local_crm.sqlite")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()

    staging = sqlite3.connect(args.staging_db)
    crm = sqlite3.connect(args.crm_db)
    staging.row_factory = sqlite3.Row
    crm.row_factory = sqlite3.Row
    reports_dir = Path(args.reports_dir)

    count_rows: list[dict[str, Any]] = []
    failures = 0
    for crm_table, staging_table, *where_parts in EXPECTED_COUNTS:
        where = where_parts[0] if where_parts else None
        staging_count = count(staging, staging_table, where)
        crm_count = count(crm, crm_table)
        status = "ok" if staging_count == crm_count else "mismatch"
        if status != "ok":
            failures += 1
        count_rows.append(
            {
                "object": crm_table,
                "staging_count": staging_count,
                "local_crm_count": crm_count,
                "status": status,
            }
        )

    review_rows = [
        dict(row)
        for row in crm.execute(
            """
            SELECT flag_type, severity, status, count(*) AS count
            FROM review_flags
            GROUP BY flag_type, severity, status
            ORDER BY flag_type, severity, status
            """
        ).fetchall()
    ]

    source_rows = [
        dict(row)
        for row in crm.execute(
            """
            SELECT local_table, zendesk_collection, count(*) AS mapped_records
            FROM source_map
            GROUP BY local_table, zendesk_collection
            ORDER BY local_table, zendesk_collection
            """
        ).fetchall()
    ]

    write_csv(reports_dir / "local_crm_count_verification.csv", count_rows)
    write_csv(reports_dir / "local_crm_review_flags.csv", review_rows)
    write_csv(reports_dir / "local_crm_source_map_summary.csv", source_rows)

    lines = [
        "# Local CRM Verification",
        "",
        "## Count Verification",
        "",
        "| Object | Staging Count | Local CRM Count | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in count_rows:
        lines.append(f"| {row['object']} | {row['staging_count']} | {row['local_crm_count']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Review Flags",
            "",
            "| Flag Type | Severity | Status | Count |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for row in review_rows:
        lines.append(f"| {row['flag_type']} | {row['severity']} | {row['status']} | {row['count']} |")
    lines.extend(
        [
            "",
            "## Result",
            "",
            "All required counts match." if failures == 0 else f"{failures} count checks failed.",
            "",
        ]
    )
    (reports_dir / "local_crm_verification.md").write_text("\n".join(lines), encoding="utf-8")

    staging.close()
    crm.close()
    print(f"Wrote {reports_dir / 'local_crm_verification.md'}")
    print(f"Wrote {reports_dir / 'local_crm_count_verification.csv'}")
    print(f"Wrote {reports_dir / 'local_crm_review_flags.csv'}")
    print(f"Wrote {reports_dir / 'local_crm_source_map_summary.csv'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
