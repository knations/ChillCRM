#!/usr/bin/env python3
"""Recommend which migrated custom fields should become first-class CRM fields."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "custom_field_promotion_recommendations.md"
DEFAULT_CSV = PROJECT_ROOT / "reports" / "custom_field_promotion_candidates.csv"

APPLICATION_FIELDS = {
    "APP Number": ("High", "Promote into application profile", "Unique application identifier."),
    "Date Created": ("High", "Promote into application profile", "Application intake date; keep separate from CRM record created date."),
    "Desired Growth": ("High", "Promote into application profile", "High-coverage qualification segment with few distinct choices."),
    "Time Frame": ("High", "Promote into application profile", "High-coverage urgency/timing segment with few distinct choices."),
    "Invest?": ("High", "Promote into application profile", "High-coverage buying-readiness signal with few distinct choices."),
    "Experience": ("High", "Promote into application profile", "High-coverage qualification answer."),
    "Skills": ("High", "Promote into application profile", "High-coverage long-form qualification answer."),
    "Success Is": ("High", "Promote into application profile", "High-coverage long-form goal statement."),
    "Why Waiting": ("High", "Promote into application profile", "High-coverage blocker statement."),
    "Why a Fit": ("High", "Promote into application profile", "High-coverage fit statement."),
}

CONTACT_FRAGMENT_FIELDS = {
    "Name#1",
    "Last name#1",
    "Phone#1",
    "Email#1",
    "Address#1",
    "City#1",
    "Address#2",
    "City#2",
    "Country#1",
}


@dataclass
class FieldRecommendation:
    field_name: str
    record_types: str
    priority: str
    recommendation: str
    rationale: str
    total_records_with_field: int
    total_records_with_value: int
    distinct_values: int
    coverage_summary: str
    sample_values: str


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def clean_sample(value: str) -> str:
    text = " ".join(str(value or "").split())
    return text[:120] + "..." if len(text) > 120 else text


def sample_min_length(field_name: str) -> int:
    if field_name in {"Skills", "Success Is", "Why Waiting", "Why a Fit"}:
        return 20
    if field_name == "Experience":
        return 5
    return 1


def sample_values(conn: sqlite3.Connection, field_name: str) -> list[str]:
    minimum = sample_min_length(field_name)
    samples = [
        clean_sample(row["field_value"])
        for row in conn.execute(
            """
            SELECT DISTINCT trim(field_value) AS field_value
            FROM custom_field_values
            WHERE field_name = ?
              AND coalesce(trim(field_value), '') <> ''
              AND length(trim(field_value)) >= ?
            ORDER BY length(trim(field_value)), trim(field_value)
            LIMIT 3
            """,
            (field_name, minimum),
        ).fetchall()
    ]
    if samples:
        return samples
    return [
        clean_sample(row["field_value"])
        for row in conn.execute(
            """
            SELECT DISTINCT trim(field_value) AS field_value
            FROM custom_field_values
            WHERE field_name = ?
              AND coalesce(trim(field_value), '') <> ''
            ORDER BY length(trim(field_value)), trim(field_value)
            LIMIT 3
            """,
            (field_name,),
        ).fetchall()
    ]


def classify_field(field_name: str, total_values: int, distinct_values: int) -> tuple[str, str, str]:
    if field_name in APPLICATION_FIELDS:
        return APPLICATION_FIELDS[field_name]
    if field_name in CONTACT_FRAGMENT_FIELDS:
        return (
            "Medium",
            "Review before merging into contact/address fields",
            "Looks like appended contact data from an import; verify record by record before merging.",
        )
    if field_name == "CALL RECORDINGS:":
        return (
            "Medium",
            "Keep as linked call-recording resource",
            "Useful but low-volume link field; better surfaced as a linked resource than merged into contact basics.",
        )
    if field_name == "Referred By":
        return (
            "Medium",
            "Consider promoting to referral source",
            "Useful relationship signal, but current volume is low; verify before adding a permanent field.",
        )
    if total_values <= 2:
        return (
            "Low",
            "Keep searchable until reviewed",
            "Low-volume field; preserve it in custom fields and exports unless it proves operationally important.",
        )
    if distinct_values <= 8:
        return (
            "Medium",
            "Consider list filter if used operationally",
            "Low-cardinality field could become a filter, but needs workflow confirmation.",
        )
    return (
        "Low",
        "Keep searchable as custom field",
        "Preserved and searchable; no immediate schema change recommended.",
    )


def record_type_totals(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "person": conn.execute("SELECT count(*) FROM people").fetchone()[0],
        "lead": conn.execute("SELECT count(*) FROM leads").fetchone()[0],
        "company": conn.execute("SELECT count(*) FROM companies").fetchone()[0],
    }


def field_recommendations(conn: sqlite3.Connection) -> list[FieldRecommendation]:
    totals = record_type_totals(conn)
    field_names = [
        row["field_name"]
        for row in conn.execute(
            """
            SELECT field_name
            FROM custom_field_values
            GROUP BY field_name
            ORDER BY lower(field_name)
            """
        ).fetchall()
    ]
    recommendations: list[FieldRecommendation] = []
    for field_name in field_names:
        stats = rows_to_dicts(
            conn.execute(
                """
                SELECT record_type,
                       count(*) AS records_with_field,
                       sum(CASE WHEN coalesce(trim(field_value), '') <> '' THEN 1 ELSE 0 END) AS records_with_value,
                       count(DISTINCT NULLIF(trim(coalesce(field_value, '')), '')) AS distinct_values
                FROM custom_field_values
                WHERE field_name = ?
                GROUP BY record_type
                ORDER BY record_type
                """,
                (field_name,),
            ).fetchall()
        )
        total_records_with_field = sum(row["records_with_field"] or 0 for row in stats)
        total_records_with_value = sum(row["records_with_value"] or 0 for row in stats)
        distinct_values = conn.execute(
            """
            SELECT count(DISTINCT NULLIF(trim(coalesce(field_value, '')), ''))
            FROM custom_field_values
            WHERE field_name = ?
            """,
            (field_name,),
        ).fetchone()[0]
        coverage_parts = []
        record_types = []
        for row in stats:
            record_type = row["record_type"]
            record_types.append(record_type)
            denominator = totals.get(record_type) or row["records_with_field"] or 1
            percent = round(((row["records_with_value"] or 0) / denominator) * 100, 1)
            coverage_parts.append(f"{record_type}: {row['records_with_value'] or 0}/{denominator} ({percent}%)")
        samples = sample_values(conn, field_name)
        priority, recommendation, rationale = classify_field(field_name, total_records_with_value, distinct_values)
        recommendations.append(
            FieldRecommendation(
                field_name=field_name,
                record_types=", ".join(record_types),
                priority=priority,
                recommendation=recommendation,
                rationale=rationale,
                total_records_with_field=total_records_with_field,
                total_records_with_value=total_records_with_value,
                distinct_values=distinct_values,
                coverage_summary="; ".join(coverage_parts),
                sample_values=" | ".join(samples),
            )
        )
    return sorted(recommendations, key=lambda row: ({"High": 0, "Medium": 1, "Low": 2}[row.priority], row.recommendation, row.field_name.lower()))


def write_csv(path: Path, recommendations: list[FieldRecommendation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FieldRecommendation.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in recommendations:
            writer.writerow(row.__dict__)


def markdown_table(rows: list[FieldRecommendation]) -> str:
    if not rows:
        return "No fields.\n"
    lines = [
        "| Field | Records With Value | Distinct Values | Coverage | Recommendation |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.field_name} | {row.total_records_with_value} | {row.distinct_values} | {row.coverage_summary} | {row.recommendation} |"
        )
    return "\n".join(lines) + "\n"


def write_report(path: Path, recommendations: list[FieldRecommendation], csv_path: Path) -> None:
    high = [row for row in recommendations if row.priority == "High"]
    medium = [row for row in recommendations if row.priority == "Medium"]
    low = [row for row in recommendations if row.priority == "Low"]
    total_values = sum(row.total_records_with_value for row in recommendations)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Custom Field Promotion Recommendations",
                "",
                "This report classifies migrated Zendesk Sell custom fields by how useful they are likely to be in the local CRM.",
                "",
                "No fields are changed by this report. It is decision support for future schema and UI work.",
                "",
                "## Summary",
                "",
                f"- Custom fields reviewed: {len(recommendations)}",
                f"- Nonblank custom field values reviewed: {total_values:,}",
                f"- High-priority promotion candidates: {len(high)}",
                f"- Medium-priority review candidates: {len(medium)}",
                f"- Low-priority keep-searchable fields: {len(low)}",
                f"- Candidate CSV: `{csv_path.relative_to(PROJECT_ROOT)}`",
                "",
                "## Recommended Next Move",
                "",
                "Promote the high-priority application fields into a shared Application Profile section for leads and people. Keep the original custom field values intact until the promoted view is verified.",
                "",
                "The import-style contact fragments should not be merged automatically. They need record-by-record review because they look like appended duplicate contact/address data.",
                "",
                "## Promote Into Application Profile",
                "",
                markdown_table(high),
                "## Review Before Promoting Or Merging",
                "",
                markdown_table(medium),
                "## Keep Searchable As Custom Fields",
                "",
                markdown_table(low),
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze custom fields for promotion candidates.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        recommendations = field_recommendations(conn)
    finally:
        conn.close()

    write_csv(args.csv, recommendations)
    write_report(args.report, recommendations, args.csv)
    print(f"Wrote {args.report}")
    print(f"Wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
