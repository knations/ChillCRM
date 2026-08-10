#!/usr/bin/env python3
"""Delete explicitly approved duplicate automation task rows."""

from __future__ import annotations

import argparse
import json
import os
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
REPORTS_DIR = PROJECT_ROOT / "reports"
CONFIRM_PHRASE = "DELETE DUPLICATE TASKS 29 30"
TARGET_IDS = (29, 30)


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


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def fetch_targets(conn: Any) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in TARGET_IDS)
    return rows_to_dicts(
        conn.execute(
            f"""
            SELECT id, record_type, record_id, content, completed, due_date, source_json, created_at, updated_at
            FROM tasks
            WHERE id IN ({placeholders})
            ORDER BY id
            """,
            TARGET_IDS,
        ).fetchall()
    )


def validate_targets(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    found_ids = {int(row.get("id")) for row in rows}
    missing = sorted(set(TARGET_IDS) - found_ids)
    if missing:
        errors.append(f"Missing approved task IDs: {missing}")
    for row in rows:
        if str(row.get("record_type") or "") != "person":
            errors.append(f"Task {row.get('id')} is not a person task.")
        if int(row.get("record_id") or 0) not in {738, 808}:
            errors.append(f"Task {row.get('id')} is not attached to Aaron/Liana keeper IDs.")
        source = str(row.get("source_json") or "")
        if "automation_transcript_task" not in source and "docs.google.com" not in source:
            errors.append(f"Task {row.get('id')} does not look like an automation transcript task.")
    return errors


def execute_delete(conn: Any) -> None:
    placeholders = ",".join("?" for _ in TARGET_IDS)
    conn.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", TARGET_IDS)
    conn.commit()


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete approved duplicate automation task rows.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB))
    parser.add_argument("--database-url", default="")
    parser.add_argument("--ssl-root-cert", default="")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    stamp = utc_stamp()
    hosted = is_hosted(args)
    report_path = REPORTS_DIR / f"duplicate_automation_task_cleanup_{stamp}.json"
    with connect(args) as conn:
        targets = fetch_targets(conn)
        errors = validate_targets(targets)
        if args.execute:
            if args.confirm != CONFIRM_PHRASE:
                raise SystemExit(f'To execute, pass --confirm "{CONFIRM_PHRASE}"')
            if errors:
                raise SystemExit("; ".join(errors))
            execute_delete(conn)
            remaining = fetch_targets(conn)
        else:
            remaining = targets

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "executed" if args.execute else "dry_run",
        "database_target": "hosted_postgres" if hosted else "local_sqlite",
        "approved_task_ids": list(TARGET_IDS),
        "target_count": len(targets),
        "validation_errors": errors,
        "deleted_count": len(targets) - len(remaining) if args.execute else 0,
        "remaining_target_count": len(remaining),
        "secret_values_stored": "no",
        "targets": targets,
    }
    write_report(report_path, report)
    print(json.dumps({key: report[key] for key in ["mode", "database_target", "target_count", "deleted_count", "remaining_target_count", "validation_errors"]}, indent=2))
    print(f"Report: {report_path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
