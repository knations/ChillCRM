#!/usr/bin/env python3
"""Move pasted task Source blocks into task metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
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
from crm_app.database import PostgresCompatConnection


DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
BACKUP_DIR = PROJECT_ROOT / "backups"
REPORTS_DIR = PROJECT_ROOT / "reports"
CONFIRM_PHRASE = "CLEAN TASK SOURCE BLOCKS"
SOURCE_BLOCK_RE = re.compile(r"\n\s*\nSource:\s*(.+)\s*$", re.IGNORECASE | re.DOTALL)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    return bool(args.database_url or os.environ.get("CHILLCRM_DATABASE_URL") or os.environ.get("DATABASE_URL"))


def backup_sqlite(db_path: Path, stamp: str) -> str:
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / f"before_clean_task_source_blocks_{stamp}.sqlite"
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


def row_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def decode_source_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def split_task_content(content: str) -> tuple[str, str] | None:
    match = SOURCE_BLOCK_RE.search(content or "")
    if not match:
        return None
    clean_content = SOURCE_BLOCK_RE.sub("", content).strip()
    source_notes = match.group(1).strip()
    if not clean_content or not source_notes:
        return None
    return clean_content, source_notes


def fetch_targets(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, record_type, record_id, content, source_json, due_date, created_at, updated_at
        FROM tasks
        WHERE content LIKE ?
        ORDER BY id
        """,
        ("%\n\nSource:%",),
    ).fetchall()
    targets = []
    for row in rows:
        item = row_dict(row)
        split = split_task_content(str(item.get("content") or ""))
        if not split:
            continue
        clean_content, source_notes = split
        source = decode_source_json(item.get("source_json"))
        source.setdefault("local_source", "automation_transcript_task")
        if source_notes:
            source["notes"] = source_notes
        item["clean_content"] = clean_content
        item["clean_source_json"] = json.dumps(source, ensure_ascii=False, sort_keys=True)
        targets.append(item)
    return targets


def execute_cleanup(conn: Any, targets: list[dict[str, Any]]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for item in targets:
        conn.execute(
            """
            UPDATE tasks
            SET content = ?, source_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (item["clean_content"], item["clean_source_json"], timestamp, item["id"]),
        )
    conn.commit()


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean visible task Source blocks.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB))
    parser.add_argument("--database-url", default="")
    parser.add_argument("--ssl-root-cert", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    stamp = utc_stamp()
    report_path = REPORTS_DIR / f"task_source_block_cleanup_{stamp}.json"
    hosted = is_hosted(args)
    backup_path = "hosted database; rely on provider backup plus report" if hosted else backup_sqlite(Path(args.db_path), stamp)

    with connect(args) as conn:
        targets = fetch_targets(conn)
        if args.execute:
            if args.confirm != CONFIRM_PHRASE:
                raise SystemExit(f'To execute, pass --confirm "{CONFIRM_PHRASE}"')
            execute_cleanup(conn, targets)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "executed" if args.execute else "dry_run",
        "database_target": "hosted_postgres" if hosted else "local_sqlite",
        "target_count": len(targets),
        "backup": backup_path,
        "secret_values_stored": "no",
        "targets": [
            {
                "id": item.get("id"),
                "record_type": item.get("record_type"),
                "record_id": item.get("record_id"),
                "old_content_preview": str(item.get("content") or "")[:160],
                "new_content": item.get("clean_content"),
            }
            for item in targets
        ],
    }
    write_report(report_path, report)
    print(json.dumps({key: report[key] for key in ["mode", "database_target", "target_count", "backup"]}, indent=2))
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
