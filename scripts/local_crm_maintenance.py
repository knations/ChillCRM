#!/usr/bin/env python3
"""Maintenance utilities for the local CRM database."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def backup_database(db_path: Path = DEFAULT_DB, backup_dir: Path = DEFAULT_BACKUP_DIR, reason: str = "manual") -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"local_crm_{stamp()}_{reason}.sqlite"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup_path


def ensure_columns(conn: sqlite3.Connection, table: str, column_sql: str) -> None:
    column_name = column_sql.split()[0]
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def upgrade_schema(db_path: Path = DEFAULT_DB) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                record_type TEXT NOT NULL,
                record_id INTEGER,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS local_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        ensure_columns(conn, "review_flags", "resolved_at TEXT")
        ensure_columns(conn, "review_flags", "resolution_note TEXT")
        conn.commit()
    finally:
        conn.close()


def list_backups(backup_dir: Path = DEFAULT_BACKUP_DIR) -> list[Path]:
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("local_crm_*.sqlite"), reverse=True)


def restore_database(backup_path: Path, db_path: Path = DEFAULT_DB) -> None:
    if not backup_path.exists():
        raise FileNotFoundError(backup_path)
    pre_restore = backup_database(db_path, DEFAULT_BACKUP_DIR, "pre_restore")
    shutil.copy2(backup_path, db_path)
    upgrade_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO audit_log (action, record_type, record_id, field_name, old_value, new_value, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "restore_backup",
                "database",
                None,
                "backup",
                pre_restore.name,
                backup_path.name,
                "Database restored from local backup by maintenance script.",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain the local CRM database.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("upgrade", help="Apply safe local schema upgrades.")

    backup_parser = sub.add_parser("backup", help="Create a timestamped database backup.")
    backup_parser.add_argument("--reason", default="manual")

    sub.add_parser("list-backups", help="List local database backups.")

    restore_parser = sub.add_parser("restore", help="Restore a local database backup.")
    restore_parser.add_argument("backup_path")

    args = parser.parse_args()

    if args.command == "upgrade":
        upgrade_schema()
        print(f"Upgraded {DEFAULT_DB}")
    elif args.command == "backup":
        path = backup_database(reason=args.reason)
        print(path)
    elif args.command == "list-backups":
        for path in list_backups():
            print(path)
    elif args.command == "restore":
        restore_database(Path(args.backup_path))
        print(f"Restored {args.backup_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
