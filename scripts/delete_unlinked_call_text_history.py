#!/usr/bin/env python3
"""Delete unlinked call/text history items from CHILLCRM with evidence.

Default mode is dry-run. Execution requires:
  --execute --confirm "DELETE UNLINKED CALLS TEXTS"

The target is intentionally narrow:
  imported_archive_items where item_type is call/text_message
  and no linked CRM record is present.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crm_app import server
from crm_app.database import PostgresCompatConnection, hosted_postgres_adapter_enabled_from_env


DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
BACKUP_DIR = PROJECT_ROOT / "backups"
REPORTS_DIR = PROJECT_ROOT / "reports"
CONFIRM_PHRASE = "DELETE UNLINKED CALLS TEXTS"
TARGET_TYPES = ("call", "text_message")
TARGET_WHERE = """
item_type IN (?, ?)
AND (
  record_id IS NULL
  OR nullif(trim(coalesce(record_type, '')), '') IS NULL
)
"""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def connect(args: argparse.Namespace) -> Any:
    database_url = args.database_url or os.environ.get("CHILLCRM_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
    if database_url:
        os.environ["DATABASE_URL"] = database_url
        os.environ["CHILLCRM_DATABASE_ADAPTER"] = "supabase"
        return PostgresCompatConnection(database_url, args.ssl_root_cert or os.environ.get("CHILLCRM_POSTGRES_SSL_ROOT_CERT", ""))
    db_path = Path(args.db_path).resolve()
    server.ensure_runtime_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def is_hosted(args: argparse.Namespace) -> bool:
    return bool(args.database_url or os.environ.get("CHILLCRM_DATABASE_URL") or os.environ.get("DATABASE_URL") or hosted_postgres_adapter_enabled_from_env())


def backup_sqlite(db_path: Path, stamp: str) -> str:
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / f"before_delete_unlinked_call_text_history_{stamp}.sqlite"
    src = sqlite3.connect(db_path)
    try:
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return str(backup_path)


def fetch_targets(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT id, item_type, title, body, phone_number, occurred_at, created_at, updated_at,
               user_id, source_collection, zendesk_record_id, record_type, record_id,
               related_record_type, related_record_id, status, source_json
        FROM imported_archive_items
        WHERE {TARGET_WHERE}
        ORDER BY item_type, occurred_at DESC, id DESC
        """,
        TARGET_TYPES,
    ).fetchall()
    return rows_to_dicts(rows)


def count_by_type(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"call": 0, "text_message": 0}
    for row in rows:
        item_type = str(row.get("item_type") or "")
        if item_type in counts:
            counts[item_type] += 1
    return counts


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(exist_ok=True)
    fieldnames = [
        "id",
        "item_type",
        "title",
        "body",
        "phone_number",
        "occurred_at",
        "created_at",
        "updated_at",
        "user_id",
        "source_collection",
        "zendesk_record_id",
        "record_type",
        "record_id",
        "related_record_type",
        "related_record_id",
        "status",
        "source_json",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Unlinked Call/Text History Cleanup",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Mode: {summary['mode']}",
        f"- Database target: {summary['database_target']}",
        f"- Target rows: {summary['target_total']}",
        f"- Calls: {summary['call_count']}",
        f"- Text messages: {summary['text_message_count']}",
        f"- Expected calls/texts: {summary['expected_calls']} / {summary['expected_texts']}",
        f"- Count gate: {summary['count_gate']}",
        f"- Deleted rows: {summary['deleted_items']}",
        f"- Deleted review rows: {summary['deleted_review_rows']}",
        f"- Evidence CSV: `{summary['evidence_csv']}`",
        f"- SQLite backup: `{summary['sqlite_backup'] or 'not applicable'}`",
        "",
        "Target rule: only `imported_archive_items` with `item_type IN ('call', 'text_message')` and no linked CRM `record_type/record_id`.",
        "Linked files/documents and linked call/text history are excluded.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_counts(rows: list[dict[str, Any]], args: argparse.Namespace) -> tuple[bool, dict[str, int]]:
    counts = count_by_type(rows)
    expected_ok = counts["call"] == args.expected_calls and counts["text_message"] == args.expected_texts
    return expected_ok or args.allow_count_mismatch, counts


def execute_delete(conn: Any, rows: list[dict[str, Any]], actor: str, evidence_csv: str) -> tuple[int, int]:
    before_count = len(rows)
    before_review_count = conn.execute(
        f"""
        SELECT count(*)
        FROM archive_review_decisions
        WHERE archive_item_id IN (
          SELECT id FROM imported_archive_items WHERE {TARGET_WHERE}
        )
        """,
        TARGET_TYPES,
    ).fetchone()[0]
    conn.execute(
        f"""
        DELETE FROM archive_review_decisions
        WHERE archive_item_id IN (
          SELECT id FROM imported_archive_items WHERE {TARGET_WHERE}
        )
        """,
        TARGET_TYPES,
    )
    conn.execute(f"DELETE FROM imported_archive_items WHERE {TARGET_WHERE}", TARGET_TYPES)
    after_count = conn.execute(f"SELECT count(*) FROM imported_archive_items WHERE {TARGET_WHERE}", TARGET_TYPES).fetchone()[0]
    deleted_items = before_count - int(after_count or 0)
    audit_id = conn.execute("SELECT COALESCE(max(id), 0) + 1 AS next_id FROM audit_log").fetchone()[0]
    conn.execute(
        """
        INSERT INTO audit_log (id, action, record_type, record_id, field_name, old_value, new_value, note, actor_email, permission_action)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(audit_id or 1),
            "delete_unlinked_call_text_history",
            "files_history",
            None,
            "unlinked_call_text_history",
            json.dumps({"target_rows": before_count}, sort_keys=True),
            json.dumps({"remaining_target_rows": int(after_count or 0)}, sort_keys=True),
            f"Deleted unlinked call/text history only. Evidence CSV: {evidence_csv}",
            actor,
            "owner_approved_cleanup",
        ),
    )
    conn.commit()
    return deleted_items, int(before_review_count or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete unlinked CHILLCRM call/text history with evidence.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB), help="Local SQLite database path.")
    parser.add_argument("--database-url", default="", help="Hosted Postgres DATABASE_URL. Can also use CHILLCRM_DATABASE_URL or DATABASE_URL.")
    parser.add_argument("--ssl-root-cert", default="", help="Optional Postgres SSL root certificate path.")
    parser.add_argument("--execute", action="store_true", help="Actually delete rows. Omit for dry-run.")
    parser.add_argument("--confirm", default="", help=f'Required phrase for execute: "{CONFIRM_PHRASE}"')
    parser.add_argument("--expected-calls", type=int, default=373)
    parser.add_argument("--expected-texts", type=int, default=99)
    parser.add_argument("--allow-count-mismatch", action="store_true")
    parser.add_argument("--actor", default="Kevin Nations")
    args = parser.parse_args()

    if args.execute and args.confirm != CONFIRM_PHRASE:
        raise SystemExit(f'Execution blocked. Re-run with --confirm "{CONFIRM_PHRASE}".')

    stamp = utc_stamp()
    report_path = REPORTS_DIR / f"unlinked_call_text_history_cleanup_{stamp}.md"
    csv_path = REPORTS_DIR / f"unlinked_call_text_history_cleanup_{stamp}.csv"
    hosted = is_hosted(args)
    sqlite_backup = ""
    deleted_items = 0
    deleted_review_rows = 0

    with connect(args) as conn:
        targets = fetch_targets(conn)
        count_gate, counts = verify_counts(targets, args)
        write_csv(csv_path, targets)
        if not count_gate:
            mode = "blocked_count_mismatch"
        elif args.execute:
            if hosted:
                sqlite_backup = "hosted database; rely on provider backup plus evidence CSV"
            else:
                sqlite_backup = backup_sqlite(Path(args.db_path).resolve(), stamp)
            deleted_items, deleted_review_rows = execute_delete(conn, targets, args.actor, str(csv_path))
            mode = "executed"
        else:
            mode = "dry_run"

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "database_target": "hosted_postgres" if hosted else str(Path(args.db_path).resolve()),
        "target_total": len(targets),
        "call_count": counts["call"],
        "text_message_count": counts["text_message"],
        "expected_calls": args.expected_calls,
        "expected_texts": args.expected_texts,
        "count_gate": "pass" if count_gate else "blocked",
        "deleted_items": deleted_items,
        "deleted_review_rows": deleted_review_rows,
        "evidence_csv": str(csv_path),
        "sqlite_backup": sqlite_backup,
    }
    write_report(report_path, summary)
    print(json.dumps(summary, indent=2))
    return 0 if count_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
