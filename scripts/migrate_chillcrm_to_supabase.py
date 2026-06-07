#!/usr/bin/env python3
"""Load the verified local CHILLCRM database into Supabase staging.

This script expects a Postgres connection string in CHILLCRM_DATABASE_URL.
Do not hard-code credentials into this file or into generated reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sqlite3
import sys
import urllib.parse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pg8000.dbapi as pg

try:
    import certifi
except ImportError:  # pragma: no cover - optional local certificate bundle.
    certifi = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_SCHEMA_SQL = PROJECT_ROOT / "reports" / "hosted_database_schema_draft.sql"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"

LOAD_TABLES = [
    "users",
    "companies",
    "people",
    "pipelines",
    "stages",
    "leads",
    "deals",
    "tags",
    "tag_aliases",
    "tag_assignments",
    "custom_field_definitions",
    "custom_field_values",
    "notes",
    "tasks",
    "imported_archive_items",
    "archive_review_decisions",
    "cleanup_group_decisions",
    "project_decisions",
    "review_flags",
    "audit_log",
    "local_addresses",
    "local_list_views",
    "local_settings",
    "migration_info",
    "source_map",
]

REMOTE_ONLY_TABLES = [
    "app_users",
    "app_roles",
    "app_user_roles",
    "app_permissions",
    "remote_audit_events",
    "remote_file_objects",
    "migration_runs",
    "migration_row_maps",
    "app_saved_views",
]

ROLE_SEEDS = [
    ("owner", "Owner", "Full CHILLCRM owner control."),
    ("admin", "Admin", "Trusted admin access for daily CRM management."),
    ("staff", "Staff", "Operational staff access once remote permissions are enabled."),
    ("read_only", "Read-only", "Read-only access for review and reporting."),
    ("migration_operator", "Migration Operator", "Temporary migration/setup operator role."),
]

PERMISSION_SEEDS = [
    ("records.read", "records", "Read CRM records.", True, True, True, True),
    ("records.write", "records", "Create and edit CRM records.", True, True, True, False),
    ("cleanup.review", "cleanup", "Review cleanup queues without executing merges.", True, True, True, False),
    ("cleanup.execute", "cleanup", "Execute future cleanup/merge actions after explicit approval.", True, False, False, False),
    ("archive.read", "archive", "Read imported archive items.", True, True, True, True),
    ("archive.link", "archive", "Manually link archive items after review.", True, True, False, False),
    ("files.read", "files", "Access private recovered document files.", True, True, True, False),
    ("exports.csv", "exports", "Download ordinary CSV exports.", True, True, True, False),
    ("exports.package", "exports", "Download complete CRM/database/document packages.", True, True, False, False),
    ("backups.manage", "backups", "Create, inspect, or restore backups.", True, True, False, False),
    ("users.manage", "users", "Invite or deactivate remote app users.", True, False, False, False),
]


@dataclass
class LoadResult:
    table_name: str
    local_count: int
    remote_count: int
    status: str
    detail: str


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def qualified(table_name: str) -> str:
    return f"crm.{quote_ident(table_name)}"


def sqlite_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def postgres_connect(database_url: str) -> pg.Connection:
    parsed = urllib.parse.urlparse(database_url)
    if not parsed.hostname:
        raise ValueError("Database URL is missing a host.")
    database = (parsed.path or "/postgres").lstrip("/") or "postgres"
    ssl_root_cert = os.environ.get("CHILLCRM_SSLROOTCERT")
    if ssl_root_cert:
        ssl_context = ssl.create_default_context(cafile=ssl_root_cert)
    else:
        ssl_context = ssl.create_default_context(cafile=certifi.where() if certifi else None)
    return pg.connect(
        user=urllib.parse.unquote(parsed.username or ""),
        password=urllib.parse.unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=database,
        ssl_context=ssl_context,
        timeout=30,
    )


def split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        char = sql[i]
        current.append(char)
        if char == "'" and not in_double:
            if i + 1 < len(sql) and sql[i + 1] == "'":
                current.append(sql[i + 1])
                i += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def table_columns_sqlite(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()
    return [str(row["name"]) for row in rows]


def target_column_types(pg_conn: pg.Connection, table_name: str) -> dict[str, str]:
    with closing(pg_conn.cursor()) as cur:
        cur.execute(
            """
            SELECT column_name, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'crm'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        return {str(row[0]): str(row[1]) for row in cur.fetchall()}


def count_sqlite(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT count(*) FROM {quote_ident(table_name)}").fetchone()[0])


def count_postgres(pg_conn: pg.Connection, table_name: str) -> int:
    with closing(pg_conn.cursor()) as cur:
        cur.execute(f"SELECT count(*) FROM {qualified(table_name)}")
        return int(cur.fetchone()[0])


def crm_schema_exists(pg_conn: pg.Connection) -> bool:
    with closing(pg_conn.cursor()) as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'crm')")
        return bool(cur.fetchone()[0])


def crm_table_counts(pg_conn: pg.Connection) -> dict[str, int]:
    if not crm_schema_exists(pg_conn):
        return {}
    with closing(pg_conn.cursor()) as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'crm'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        tables = [str(row[0]) for row in cur.fetchall()]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            counts[table] = count_postgres(pg_conn, table)
        except Exception:
            counts[table] = -1
    return counts


def execute_schema(pg_conn: pg.Connection, schema_sql_path: Path, reset_schema: bool) -> None:
    with closing(pg_conn.cursor()) as cur:
        if reset_schema:
            cur.execute("DROP SCHEMA IF EXISTS crm CASCADE")
            pg_conn.commit()
        schema_sql = schema_sql_path.read_text(encoding="utf-8")
        for statement in split_sql(schema_sql):
            cur.execute(statement)
    pg_conn.commit()


def seed_remote_roles(pg_conn: pg.Connection) -> None:
    with closing(pg_conn.cursor()) as cur:
        for role_key, label, description in ROLE_SEEDS:
            cur.execute(
                """
                INSERT INTO crm.app_roles (role_key, label, description, system_role)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (role_key)
                DO UPDATE SET label = EXCLUDED.label, description = EXCLUDED.description
                """,
                (role_key, label, description),
            )
        for action_key, area, description, owner, admin, staff, read_only in PERMISSION_SEEDS:
            cur.execute(
                """
                INSERT INTO crm.app_permissions
                    (action_key, area, description, owner_allowed, admin_allowed, staff_allowed, read_only_allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (action_key)
                DO UPDATE SET
                    area = EXCLUDED.area,
                    description = EXCLUDED.description,
                    owner_allowed = EXCLUDED.owner_allowed,
                    admin_allowed = EXCLUDED.admin_allowed,
                    staff_allowed = EXCLUDED.staff_allowed,
                    read_only_allowed = EXCLUDED.read_only_allowed
                """,
                (action_key, area, description, owner, admin, staff, read_only),
            )
    pg_conn.commit()


def json_compatible(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list, int, float, bool)):
        return json.dumps(value)
    text = str(value)
    if text == "":
        return None
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        return json.dumps(text)


def convert_value(value: Any, pg_type: str) -> Any:
    if value is None:
        return None
    if pg_type in {"json", "jsonb"}:
        return json_compatible(value)
    if pg_type in {"timestamptz", "timestamp", "date"} and str(value).strip() == "":
        return None
    return value


def insert_table(sqlite_conn: sqlite3.Connection, pg_conn: pg.Connection, table_name: str, batch_size: int = 500) -> None:
    columns = table_columns_sqlite(sqlite_conn, table_name)
    target_types = target_column_types(pg_conn, table_name)
    if not columns:
        return
    missing = [column for column in columns if column not in target_types]
    if missing:
        raise RuntimeError(f"Target table crm.{table_name} is missing columns: {', '.join(missing)}")
    column_sql = ", ".join(quote_ident(column) for column in columns)
    value_expressions = []
    for column in columns:
        if target_types.get(column) in {"json", "jsonb"}:
            value_expressions.append("CAST(%s AS jsonb)")
        else:
            value_expressions.append("%s")
    row_expression = f"({', '.join(value_expressions)})"
    rows = sqlite_conn.execute(f"SELECT {column_sql} FROM {quote_ident(table_name)} ORDER BY rowid").fetchall()
    if not rows:
        return
    with closing(pg_conn.cursor()) as cur:
        batch: list[tuple[Any, ...]] = []
        for row in rows:
            batch.append(tuple(convert_value(row[column], target_types[column]) for column in columns))
            if len(batch) >= batch_size:
                placeholders = ", ".join(row_expression for _ in batch)
                insert_sql = f"INSERT INTO {qualified(table_name)} ({column_sql}) VALUES {placeholders}"
                values = [value for batch_row in batch for value in batch_row]
                cur.execute(insert_sql, values)
                batch = []
        if batch:
            placeholders = ", ".join(row_expression for _ in batch)
            insert_sql = f"INSERT INTO {qualified(table_name)} ({column_sql}) VALUES {placeholders}"
            values = [value for batch_row in batch for value in batch_row]
            cur.execute(insert_sql, values)
    pg_conn.commit()


def load_data(sqlite_conn: sqlite3.Connection, pg_conn: pg.Connection, allow_existing_rows: bool) -> None:
    existing_counts = crm_table_counts(pg_conn)
    existing = {table: existing_counts.get(table, 0) for table in LOAD_TABLES if table in existing_counts}
    non_empty = {table: value for table, value in existing.items() if value > 0}
    if non_empty and not allow_existing_rows:
        detail = ", ".join(f"{table}={count}" for table, count in sorted(non_empty.items()))
        raise RuntimeError(f"Refusing to load over existing CRM rows without --allow-existing-rows: {detail}")
    for table_name in LOAD_TABLES:
        insert_table(sqlite_conn, pg_conn, table_name)


def insert_migration_run(pg_conn: pg.Connection, source_backup_name: str | None, notes: str) -> None:
    with closing(pg_conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO crm.migration_runs (run_type, source_backup_name, completed_at, status, notes)
            VALUES (%s, %s, now(), %s, %s)
            """,
            ("staging_initial_load", source_backup_name, "completed", notes),
        )
    pg_conn.commit()


def validate_counts(sqlite_conn: sqlite3.Connection, pg_conn: pg.Connection) -> list[LoadResult]:
    rows: list[LoadResult] = []
    for table_name in LOAD_TABLES:
        local_count = count_sqlite(sqlite_conn, table_name)
        remote_count = count_postgres(pg_conn, table_name)
        status = "pass" if local_count == remote_count else "fail"
        detail = "Counts match." if status == "pass" else f"Expected {local_count}, found {remote_count}."
        rows.append(LoadResult(table_name, local_count, remote_count, status, detail))
    return rows


def validate_remote_setup(pg_conn: pg.Connection) -> dict[str, int]:
    checks: dict[str, int] = {}
    with closing(pg_conn.cursor()) as cur:
        cur.execute("SELECT count(*) FROM crm.imported_archive_items WHERE item_type = 'document'")
        checks["document_archive_rows"] = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM crm.imported_archive_items WHERE item_type = 'document' AND local_file IS NOT NULL")
        checks["document_rows_with_local_file"] = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM crm.remote_file_objects")
        checks["remote_file_objects"] = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM crm.app_roles")
        checks["app_roles"] = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM crm.app_permissions")
        checks["app_permissions"] = int(cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM crm.migration_runs WHERE run_type = 'staging_initial_load' AND status = 'completed'")
        checks["completed_migration_runs"] = int(cur.fetchone()[0])
    return checks


def write_csv(path: Path, rows: list[LoadResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["table_name", "local_count", "remote_count", "status", "detail"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_markdown(path: Path, rows: list[LoadResult], setup_checks: dict[str, int], project_ref: str) -> None:
    failures = [row for row in rows if row.status != "pass"]
    status = "passed" if not failures else "failed"
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "# CHILLCRM Supabase Staging Validation",
        "",
        f"Generated: {generated}",
        "",
        "This report verifies the remote staging load only. It does not include database passwords, API secrets, production cutover approval, or storage upload credentials.",
        "",
        "## Summary",
        "",
        f"- Project ref: `{project_ref}`.",
        f"- Status: {status}.",
        f"- Loaded local CRM tables checked: {len(rows)}.",
        f"- Count failures: {len(failures)}.",
        f"- Document archive rows: {setup_checks.get('document_archive_rows', 0)}.",
        f"- Remote file objects: {setup_checks.get('remote_file_objects', 0)}.",
        f"- App roles seeded: {setup_checks.get('app_roles', 0)}.",
        f"- App permissions seeded: {setup_checks.get('app_permissions', 0)}.",
        f"- Completed staging migration runs: {setup_checks.get('completed_migration_runs', 0)}.",
        "",
        "## Table Counts",
        "",
        "| Table | Local Rows | Supabase Rows | Status | Detail |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row.table_name} | {row.local_count} | {row.remote_count} | {row.status} | {row.detail} |")
    lines.extend(
        [
            "",
            "## Storage Boundary",
            "",
            "The database stores recovered document metadata and local file paths. Actual private Supabase Storage upload requires storage credentials/service-role access and is validated in a later pass.",
            "",
            "## Production Boundary",
            "",
            "This is staging only. The local SQLite CRM remains the source of truth until staged auth, file storage, permissions, backup/restore, and user workflows are separately verified.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def project_ref_from_url(database_url: str) -> str:
    parsed = urllib.parse.urlparse(database_url)
    host = parsed.hostname or ""
    if "ckjbnummsxqcyeahzynz" in host:
        return "ckjbnummsxqcyeahzynz"
    username = urllib.parse.unquote(parsed.username or "")
    if "." in username:
        return username.split(".")[-1]
    return host


def main() -> int:
    parser = argparse.ArgumentParser(description="Load CHILLCRM local data into Supabase staging.")
    parser.add_argument("--sqlite-db", default=str(DEFAULT_SQLITE_DB))
    parser.add_argument("--schema-sql", default=str(DEFAULT_SCHEMA_SQL))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--reset-crm-schema", action="store_true", help="Drop only the crm schema before applying the schema.")
    parser.add_argument("--allow-existing-rows", action="store_true", help="Allow loading when crm tables already contain rows.")
    parser.add_argument("--schema-only", action="store_true", help="Apply schema and seed role metadata without loading CRM rows.")
    parser.add_argument("--validate-only", action="store_true", help="Validate an existing Supabase load without changing data.")
    parser.add_argument("--source-backup-name", default="", help="Optional source backup/package note for migration_runs.")
    args = parser.parse_args()

    database_url = os.environ.get("CHILLCRM_DATABASE_URL")
    if not database_url:
        print("CHILLCRM_DATABASE_URL is required.", file=sys.stderr)
        return 2

    sqlite_path = Path(args.sqlite_db)
    schema_sql_path = Path(args.schema_sql)
    reports_dir = Path(args.reports_dir)
    project_ref = project_ref_from_url(database_url)

    sqlite_conn = sqlite_connect(sqlite_path)
    pg_conn = postgres_connect(database_url)
    try:
        if not args.validate_only:
            existing_counts = crm_table_counts(pg_conn)
            existing_total = sum(count for count in existing_counts.values() if count > 0)
            if existing_total and not args.reset_crm_schema and not args.allow_existing_rows:
                print(
                    f"Remote crm schema already has {existing_total} rows. "
                    "Use --reset-crm-schema for staging reset or --allow-existing-rows if intentional.",
                    file=sys.stderr,
                )
                return 3
            execute_schema(pg_conn, schema_sql_path, args.reset_crm_schema)
            seed_remote_roles(pg_conn)
            if not args.schema_only:
                load_data(sqlite_conn, pg_conn, args.allow_existing_rows)
                insert_migration_run(
                    pg_conn,
                    args.source_backup_name or None,
                    "Loaded verified local CHILLCRM SQLite data into Supabase staging.",
                )
        rows = validate_counts(sqlite_conn, pg_conn)
        setup_checks = validate_remote_setup(pg_conn)
        csv_path = reports_dir / "chillcrm_supabase_staging_validation.csv"
        md_path = reports_dir / "chillcrm_supabase_staging_validation.md"
        write_csv(csv_path, rows)
        write_markdown(md_path, rows, setup_checks, project_ref)
        failures = [row for row in rows if row.status != "pass"]
        print(f"Wrote {md_path}")
        print(f"Wrote {csv_path}")
        if failures:
            print(f"Validation failures: {len(failures)}", file=sys.stderr)
            return 1
        print("CHILLCRM Supabase staging database validation passed.")
        return 0
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
