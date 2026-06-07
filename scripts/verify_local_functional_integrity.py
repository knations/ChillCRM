#!/usr/bin/env python3
"""Verify local CRM functional data integrity before hosted staging."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CRM_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_STAGING_DB = PROJECT_ROOT / "staging_database" / "zendesk_sell_staging.sqlite"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"

CORE_COUNT_CHECKS = [
    ("users", "users", "users", None),
    ("companies", "companies", "contacts", "kind = 'company'"),
    ("people", "people", "contacts", "kind = 'person'"),
    ("leads", "leads", "leads", None),
    ("deals", "deals", "deals", None),
    ("notes", "notes", "notes", None),
    ("tasks", "tasks", "tasks", None),
    ("tag_assignments", "tag_assignments", "tag_assignments", None),
    ("custom_field_values", "custom_field_values", "custom_field_values", None),
]

RECORD_TARGETS = {
    "person": "people",
    "company": "companies",
    "lead": "leads",
    "deal": "deals",
    "tag": "tags",
}

AUDIT_RECORD_TARGETS = {
    **RECORD_TARGETS,
    "app_user": "app_users",
}

SOURCE_MAP_TARGETS = {
    "users": ("users", "zendesk_user_id"),
    "companies": ("companies", "zendesk_contact_id"),
    "people": ("people", "zendesk_contact_id"),
    "leads": ("leads", "zendesk_lead_id"),
    "deals": ("deals", "zendesk_deal_id"),
    "notes": ("notes", "zendesk_note_id"),
    "tasks": ("tasks", "zendesk_task_id"),
    "pipelines": ("pipelines", "zendesk_pipeline_id"),
    "stages": ("stages", "zendesk_stage_id"),
}

PROJECT_DECISION_KEYS = [
    "duplicate_people_merge_policy",
    "duplicate_leads_merge_policy",
    "lead_person_overlap_policy",
    "duplicate_tag_policy",
    "application_profile_editability",
    "unlinked_archive_matching",
    "apple_native_redesign_timing",
]

JSON_COLUMNS = [
    ("companies", "source_json"),
    ("people", "source_json"),
    ("leads", "source_json"),
    ("deals", "source_json"),
    ("notes", "source_json"),
    ("tasks", "source_json"),
    ("custom_field_definitions", "source_json"),
    ("imported_archive_items", "source_json"),
    ("local_list_views", "settings_json"),
]


@dataclass
class CheckResult:
    category: str
    check: str
    status: str
    count: int
    detail: str
    blocks_staging: str


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def count(conn: sqlite3.Connection, table: str, where: str | None = None) -> int:
    sql = f'SELECT count(*) FROM "{table}"'
    if where:
        sql += f" WHERE {where}"
    return int(conn.execute(sql).fetchone()[0])


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    value = conn.execute(sql, params).fetchone()[0]
    return int(value or 0)


def add(
    results: list[CheckResult],
    category: str,
    check: str,
    status: str,
    count_value: int,
    detail: str,
    blocks_staging: bool = True,
) -> None:
    results.append(
        CheckResult(
            category=category,
            check=check,
            status=status,
            count=count_value,
            detail=detail,
            blocks_staging="yes" if blocks_staging else "no",
        )
    )


def write_csv(path: Path, rows: list[CheckResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category", "check", "status", "count", "detail", "blocks_staging"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def empty_sql(column: str) -> str:
    return f"({column} IS NULL OR trim(CAST({column} AS TEXT)) = '')"


def check_count_parity(
    crm: sqlite3.Connection,
    staging_path: Path,
    results: list[CheckResult],
) -> None:
    if not staging_path.exists():
        add(results, "counts", "staging database present", "warn", 1, f"Missing {staging_path}", False)
        return
    staging = connect(staging_path)
    try:
        mismatches = 0
        details = []
        for label, crm_table, staging_table, staging_where in CORE_COUNT_CHECKS:
            crm_count = count(crm, crm_table)
            staging_count = count(staging, staging_table, staging_where)
            if crm_count != staging_count:
                mismatches += 1
                details.append(f"{label}: staging {staging_count}, local {crm_count}")
        status = "pass" if mismatches == 0 else "fail"
        detail = "All required source counts match staging." if not details else "; ".join(details)
        add(results, "counts", "staging to local CRM count parity", status, mismatches, detail)
    finally:
        staging.close()


def check_sqlite_foreign_keys(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    rows = crm.execute("PRAGMA foreign_key_check").fetchall()
    detail = "SQLite foreign key check returned no broken declared relationships."
    if rows:
        detail = "; ".join(str(dict(row)) for row in rows[:10])
    add(results, "relationships", "declared SQLite foreign keys", "pass" if not rows else "fail", len(rows), detail)


def check_owner_refs(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    checks = [
        (
            "people owner refs",
            "SELECT count(*) FROM people r LEFT JOIN users u ON u.zendesk_user_id = r.owner_user_id "
            "WHERE r.owner_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "companies owner refs",
            "SELECT count(*) FROM companies r LEFT JOIN users u ON u.zendesk_user_id = r.owner_user_id "
            "WHERE r.owner_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "leads owner refs",
            "SELECT count(*) FROM leads r LEFT JOIN users u ON u.zendesk_user_id = r.owner_user_id "
            "WHERE r.owner_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "tasks owner refs",
            "SELECT count(*) FROM tasks r LEFT JOIN users u ON u.zendesk_user_id = r.owner_user_id "
            "WHERE r.owner_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "tasks creator refs",
            "SELECT count(*) FROM tasks r LEFT JOIN users u ON u.zendesk_user_id = r.creator_user_id "
            "WHERE r.creator_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "notes creator refs",
            "SELECT count(*) FROM notes r LEFT JOIN users u ON u.zendesk_user_id = r.creator_user_id "
            "WHERE r.creator_user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
        (
            "archive user refs",
            "SELECT count(*) FROM imported_archive_items r LEFT JOIN users u ON u.zendesk_user_id = r.user_id "
            "WHERE r.user_id IS NOT NULL AND u.zendesk_user_id IS NULL",
        ),
    ]
    broken = 0
    details = []
    for label, sql in checks:
        bad = scalar(crm, sql)
        broken += bad
        if bad:
            details.append(f"{label}: {bad}")
    detail = "Owner/user references resolve through users.zendesk_user_id." if not details else "; ".join(details)
    add(results, "relationships", "owner and creator references", "pass" if broken == 0 else "fail", broken, detail)


def check_polymorphic_refs(
    crm: sqlite3.Connection,
    results: list[CheckResult],
    table: str,
    type_col: str,
    id_col: str,
    label: str,
    allow_unlinked: bool = False,
    unlinked_detail: str = "",
) -> None:
    type_empty = empty_sql(type_col)
    id_empty = empty_sql(id_col)
    partial = scalar(
        crm,
        f'SELECT count(*) FROM "{table}" WHERE ({type_empty} AND NOT {id_empty}) OR (NOT {type_empty} AND {id_empty})',
    )
    unknown = scalar(
        crm,
        f'SELECT count(*) FROM "{table}" WHERE NOT {type_empty} AND lower({type_col}) NOT IN ({",".join("?" for _ in RECORD_TARGETS)})',
        tuple(RECORD_TARGETS),
    )
    broken = partial + unknown
    details = []
    if partial:
        details.append(f"partial reference pairs: {partial}")
    if unknown:
        details.append(f"unknown record types: {unknown}")
    for record_type, target_table in AUDIT_RECORD_TARGETS.items():
        bad = scalar(
            crm,
            f"""
            SELECT count(*)
            FROM "{table}" r
            LEFT JOIN "{target_table}" t ON t.id = r.{id_col}
            WHERE lower(r.{type_col}) = ? AND r.{id_col} IS NOT NULL AND t.id IS NULL
            """,
            (record_type,),
        )
        broken += bad
        if bad:
            details.append(f"{record_type}: {bad}")
    unlinked = 0
    if allow_unlinked:
        unlinked = scalar(crm, f'SELECT count(*) FROM "{table}" WHERE {type_empty} AND {id_empty}')
    status = "pass" if broken == 0 else "fail"
    detail = "All saved polymorphic references point to existing local records."
    if details:
        detail = "; ".join(details)
    elif unlinked:
        detail = unlinked_detail or f"{unlinked} rows are intentionally unlinked."
    add(results, "relationships", label, status, broken, detail)
    if allow_unlinked and unlinked:
        add(results, "known queues", f"{label} intentionally unlinked rows", "warn", unlinked, detail, False)


def check_audit_refs(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    broken = 0
    details = []
    for record_type, target_table in RECORD_TARGETS.items():
        bad = scalar(
            crm,
            f"""
            SELECT count(*)
            FROM audit_log a
            LEFT JOIN "{target_table}" t ON t.id = a.record_id
            WHERE lower(a.record_type) = ? AND a.record_id IS NOT NULL AND t.id IS NULL
            """,
            (record_type,),
        )
        broken += bad
        if bad:
            details.append(f"{record_type}: {bad}")
    project_decision_bad = scalar(
        crm,
        """
        SELECT count(*)
        FROM audit_log a
        LEFT JOIN project_decisions p ON p.decision_key = a.field_name
        WHERE a.record_type = 'project_decision' AND p.decision_key IS NULL
        """,
    )
    broken += project_decision_bad
    if project_decision_bad:
        details.append(f"project_decision: {project_decision_bad}")
    unknown = scalar(
        crm,
        """
        SELECT count(*)
        FROM audit_log
        WHERE record_type NOT IN ('person', 'company', 'lead', 'deal', 'tag', 'project_decision', 'app_user')
        """,
    )
    broken += unknown
    if unknown:
        details.append(f"unknown audit record types: {unknown}")
    detail = "Audit entries point to saved records or saved project decisions." if not details else "; ".join(details)
    add(results, "relationships", "audit log references", "pass" if broken == 0 else "fail", broken, detail)


def check_source_map(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    unknown = scalar(
        crm,
        f'SELECT count(*) FROM source_map WHERE local_table NOT IN ({",".join("?" for _ in SOURCE_MAP_TARGETS)})',
        tuple(SOURCE_MAP_TARGETS),
    )
    broken = unknown
    details = []
    if unknown:
        details.append(f"unknown local_table values: {unknown}")
    for local_table, (target_table, source_column) in SOURCE_MAP_TARGETS.items():
        missing_target = scalar(
            crm,
            f"""
            SELECT count(*)
            FROM source_map sm
            LEFT JOIN "{target_table}" t ON t.id = sm.local_id
            WHERE sm.local_table = ? AND t.id IS NULL
            """,
            (local_table,),
        )
        source_mismatch = scalar(
            crm,
            f"""
            SELECT count(*)
            FROM source_map sm
            JOIN "{target_table}" t ON t.id = sm.local_id
            WHERE sm.local_table = ? AND t.{source_column} IS NOT NULL AND t.{source_column} != sm.zendesk_id
            """,
            (local_table,),
        )
        missing_map = scalar(
            crm,
            f"""
            SELECT count(*)
            FROM "{target_table}" t
            LEFT JOIN source_map sm
              ON sm.local_table = ?
             AND sm.local_id = t.id
             AND sm.zendesk_id = t.{source_column}
            WHERE t.{source_column} IS NOT NULL AND sm.local_id IS NULL
            """,
            (local_table,),
        )
        bad = missing_target + source_mismatch + missing_map
        broken += bad
        if bad:
            details.append(
                f"{local_table}: missing target {missing_target}, source mismatch {source_mismatch}, missing map {missing_map}"
            )
    detail = "Source map rows resolve to local records and imported source IDs." if not details else "; ".join(details)
    add(results, "source map", "source map coverage", "pass" if broken == 0 else "fail", broken, detail)


def check_custom_fields(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    missing_defs = scalar(
        crm,
        """
        SELECT count(*)
        FROM custom_field_values cfv
        LEFT JOIN custom_field_definitions d
          ON d.name = cfv.field_name
         AND d.resource_type = CASE
             WHEN cfv.record_type IN ('person', 'company') THEN 'contact'
             WHEN cfv.record_type = 'lead' THEN 'lead'
             ELSE cfv.record_type
         END
        WHERE d.id IS NULL
        """,
    )
    invalid_record_types = scalar(
        crm,
        "SELECT count(*) FROM custom_field_values WHERE record_type NOT IN ('person', 'company', 'lead')",
    )
    broken = missing_defs + invalid_record_types
    detail = "Custom field values have known definitions and valid target record types."
    if broken:
        detail = f"Missing definitions: {missing_defs}; invalid record types: {invalid_record_types}"
    add(results, "custom fields", "custom field definition coverage", "pass" if broken == 0 else "fail", broken, detail)


def check_json_columns(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    broken = 0
    details = []
    for table, column in JSON_COLUMNS:
        rows = crm.execute(f'SELECT id, "{column}" AS value FROM "{table}" WHERE "{column}" IS NOT NULL').fetchall()
        invalid = 0
        for row in rows:
            try:
                json.loads(row["value"])
            except (TypeError, json.JSONDecodeError):
                invalid += 1
        broken += invalid
        if invalid:
            details.append(f"{table}.{column}: {invalid}")
    detail = "JSON/source payload columns parse cleanly." if not details else "; ".join(details)
    add(results, "data shape", "JSON payload validity", "pass" if broken == 0 else "fail", broken, detail)


def check_files(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    document_rows = crm.execute(
        """
        SELECT id, local_file, size_bytes, record_type, record_id
        FROM imported_archive_items
        WHERE item_type = 'document'
        ORDER BY id
        """
    ).fetchall()
    missing_reference = 0
    missing_file = 0
    size_mismatch = 0
    total_bytes = 0
    for row in document_rows:
        if not row["local_file"]:
            missing_reference += 1
            continue
        path = PROJECT_ROOT / row["local_file"]
        if not path.exists():
            missing_file += 1
            continue
        actual_size = path.stat().st_size
        total_bytes += actual_size
        if row["size_bytes"] is not None and int(row["size_bytes"]) != actual_size:
            size_mismatch += 1
    linked_docs = scalar(
        crm,
        """
        SELECT count(*)
        FROM imported_archive_items
        WHERE item_type = 'document' AND record_type IS NOT NULL AND record_id IS NOT NULL
        """,
    )
    broken = missing_reference + missing_file + size_mismatch
    detail = (
        f"{len(document_rows)} document rows; {linked_docs} linked; "
        f"{total_bytes:,} bytes present; missing refs {missing_reference}; missing files {missing_file}; "
        f"size mismatches {size_mismatch}."
    )
    add(results, "files", "recovered document file coverage", "pass" if broken == 0 else "fail", broken, detail)


def check_local_queues(crm: sqlite3.Connection, results: list[CheckResult]) -> None:
    pending_decisions = 0
    saved_by_key = {
        row["decision_key"]: row["status"]
        for row in crm.execute("SELECT decision_key, status FROM project_decisions").fetchall()
    }
    for key in PROJECT_DECISION_KEYS:
        status = saved_by_key.get(key, "pending")
        if status == "pending":
            pending_decisions += 1
    deferred_decisions = sum(1 for status in saved_by_key.values() if status == "deferred")
    add(
        results,
        "known queues",
        "project policy decisions",
        "warn" if pending_decisions or deferred_decisions else "pass",
        pending_decisions + deferred_decisions,
        f"{pending_decisions} pending, {deferred_decisions} deferred; human policy gates do not block staging a read-only data copy.",
        False,
    )

    open_flags = scalar(crm, "SELECT count(*) FROM review_flags WHERE status = 'open'")
    duplicate_tag_groups = scalar(
        crm,
        "SELECT count(*) FROM review_flags WHERE status = 'open' AND flag_type = 'duplicate_tag_definition'",
    )
    keyed_groups = scalar(
        crm,
        """
        SELECT count(*)
        FROM (
            SELECT flag_type, flag_key
            FROM review_flags
            WHERE status = 'open'
              AND flag_type != 'duplicate_tag_definition'
              AND flag_key IS NOT NULL
            GROUP BY flag_type, flag_key
        )
        """,
    )
    open_groups = duplicate_tag_groups + keyed_groups
    add(
        results,
        "known queues",
        "cleanup review queues",
        "warn" if open_flags else "pass",
        open_groups,
        f"{open_flags} open cleanup flags across {open_groups} review groups; preserve as explicit human review work.",
        False,
    )

    data_quality_rows = (
        scalar(
            crm,
            """
            SELECT count(*) FROM people
            WHERE coalesce(trim(email), '') = ''
              AND coalesce(trim(phone), '') = ''
              AND coalesce(trim(mobile), '') = ''
            """,
        )
        + scalar(
            crm,
            """
            SELECT count(*) FROM companies
            WHERE coalesce(trim(email), '') = ''
              AND coalesce(trim(phone), '') = ''
            """,
        )
        + scalar(crm, "SELECT count(*) FROM leads WHERE coalesce(trim(email), '') = ''")
        + scalar(crm, "SELECT count(*) FROM deals WHERE value IS NULL OR value = 0")
    )
    add(
        results,
        "known queues",
        "ordinary data quality queue",
        "warn" if data_quality_rows else "pass",
        data_quality_rows,
        f"{data_quality_rows} ordinary CRM hygiene rows remain; do not invent missing contact details or deal values.",
        False,
    )


def check_backups_and_reports(reports_dir: Path, results: list[CheckResult]) -> None:
    backups = sorted((PROJECT_ROOT / "backups").glob("*.sqlite"))
    add(
        results,
        "safety",
        "local backups available",
        "pass" if backups else "fail",
        len(backups),
        f"{len(backups)} SQLite backup files are available.",
    )
    required_reports = [
        "local_crm_verification.md",
        "archive_association_audit.md",
        "local_crm_data_quality.md",
        "cleanup_decision_readiness.md",
        "hosted_database_migration_readiness.md",
        "hosted_database_data_load_plan.md",
    ]
    missing = [name for name in required_reports if not (reports_dir / name).exists()]
    detail = "Required migration/integrity reports are present." if not missing else f"Missing: {', '.join(missing)}"
    add(results, "safety", "required reports present", "pass" if not missing else "fail", len(missing), detail)


def write_markdown(path: Path, results: list[CheckResult]) -> None:
    blocking_failures = [row for row in results if row.status == "fail" and row.blocks_staging == "yes"]
    warnings = [row for row in results if row.status == "warn"]
    passes = [row for row in results if row.status == "pass"]
    status = "ready_for_hosted_staging" if not blocking_failures else "blocked"
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "# Local Functional Data Integrity Verification",
        "",
        f"Generated: {generated}",
        "",
        "This is a technical integrity report. It does not edit records, save merge decisions, link archive items, resolve cleanup flags, create backups, upload files, or contact Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Status: {status}.",
        f"- Passing checks: {len(passes)}.",
        f"- Warnings / known human queues: {len(warnings)}.",
        f"- Blocking failures: {len(blocking_failures)}.",
        "- Hosted staging gate: pass." if not blocking_failures else "- Hosted staging gate: blocked until failures are fixed.",
        "",
        "## Verification Results",
        "",
        "| Category | Check | Status | Count | Blocks Staging | Detail |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in results:
        detail = row.detail.replace("|", "\\|")
        lines.append(
            f"| {row.category} | {row.check} | {row.status} | {row.count} | {row.blocks_staging} | {detail} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `pass` means the local CRM foundation is technically consistent for that area.",
            "- `warn` means a known human work queue remains, but it is not a broken technical reference.",
            "- `fail` means the local copy should not be promoted into hosted staging until corrected.",
            "",
            "## Boundary",
            "",
            "The remaining duplicate, cleanup, archive-review, and ordinary data-quality queues are intentionally preserved as human review work. They should travel into hosted staging as explicit queues rather than being silently merged, invented, or auto-linked.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local CRM functional data integrity.")
    parser.add_argument("--crm-db", default=str(DEFAULT_CRM_DB))
    parser.add_argument("--staging-db", default=str(DEFAULT_STAGING_DB))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    args = parser.parse_args()

    crm_path = Path(args.crm_db)
    staging_path = Path(args.staging_db)
    reports_dir = Path(args.reports_dir)
    results: list[CheckResult] = []

    crm = connect(crm_path)
    try:
        check_count_parity(crm, staging_path, results)
        check_sqlite_foreign_keys(crm, results)
        check_owner_refs(crm, results)
        check_polymorphic_refs(crm, results, "notes", "record_type", "record_id", "notes record links")
        check_polymorphic_refs(
            crm,
            results,
            "tasks",
            "record_type",
            "record_id",
            "tasks record links",
            allow_unlinked=True,
            unlinked_detail="2 imported setup tasks are intentionally unlinked historical Zendesk reminders.",
        )
        check_polymorphic_refs(crm, results, "tag_assignments", "record_type", "record_id", "tag assignment links")
        check_polymorphic_refs(crm, results, "custom_field_values", "record_type", "record_id", "custom field value links")
        check_polymorphic_refs(crm, results, "local_addresses", "record_type", "record_id", "local address links")
        check_polymorphic_refs(crm, results, "review_flags", "record_type", "record_id", "review flag record links")
        check_polymorphic_refs(
            crm,
            results,
            "review_flags",
            "related_record_type",
            "related_record_id",
            "review flag related-record links",
            allow_unlinked=True,
            unlinked_detail="Review flags without related records are single-record cleanup flags.",
        )
        check_polymorphic_refs(
            crm,
            results,
            "imported_archive_items",
            "record_type",
            "record_id",
            "archive primary record links",
            allow_unlinked=True,
            unlinked_detail="Unlinked calls/texts remain archive-only until human review.",
        )
        check_polymorphic_refs(
            crm,
            results,
            "imported_archive_items",
            "related_record_type",
            "related_record_id",
            "archive related-record links",
            allow_unlinked=True,
            unlinked_detail="Most archive items have no secondary related record; saved secondary links resolve.",
        )
        check_audit_refs(crm, results)
        check_source_map(crm, results)
        check_custom_fields(crm, results)
        check_json_columns(crm, results)
        check_files(crm, results)
        check_local_queues(crm, results)
        check_backups_and_reports(reports_dir, results)
    finally:
        crm.close()

    csv_path = reports_dir / "local_functional_data_integrity.csv"
    md_path = reports_dir / "local_functional_data_integrity.md"
    write_csv(csv_path, results)
    write_markdown(md_path, results)

    blocking_failures = [row for row in results if row.status == "fail" and row.blocks_staging == "yes"]
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if blocking_failures:
        print(f"Blocking failures: {len(blocking_failures)}")
        return 1
    print("Local functional data integrity verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
