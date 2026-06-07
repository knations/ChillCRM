#!/usr/bin/env python3
"""Verify backup/restore mechanics against a disposable CRM database copy."""

from __future__ import annotations

import csv
import hashlib
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
BACKUP_DIR = PROJECT_ROOT / "backups"
REPORTS_DIR = PROJECT_ROOT / "reports"

KEY_TABLES = [
    "people",
    "companies",
    "leads",
    "deals",
    "activities",
    "tasks",
    "notes",
    "archive_items",
    "document_files",
    "remote_file_objects",
    "audit_log",
]


@dataclass
class Check:
    name: str
    status: str
    evidence: str
    gate: str


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sqlite_integrity(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        conn.close()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone() is not None


def key_counts(path: Path) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        counts: dict[str, int] = {}
        for table in KEY_TABLES:
            if table_exists(conn, table):
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return counts
    finally:
        conn.close()


def db_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_sqlite_backup(source: Path, target: Path) -> None:
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


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


def write_report(rows: list[dict[str, Any]]) -> None:
    checks = [row for row in rows if row.get("row_type") == "check"]
    counts = [row for row in rows if row.get("row_type") == "count"]
    summary = rows[0]
    passed = sum(1 for row in checks if row.get("status") == "pass")
    failed = sum(1 for row in checks if row.get("status") != "pass")
    lines = [
        "# Backup Restore Drill",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies backup and restore mechanics against a disposable copy of the local CRM database. It does not restore, replace, upload, or modify the live CRM database.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Passed: {passed}.",
        f"- Failed: {failed}.",
        f"- Live database: `{summary.get('live_database')}`.",
        f"- Live database bytes: {int(summary.get('live_database_bytes') or 0):,}.",
        f"- Existing project backups: {int(summary.get('project_backup_count') or 0):,}.",
        f"- Disposable restored counts matched: {summary.get('counts_matched')}.",
        f"- Production note: {summary.get('production_note')}",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Gate |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row.get('name')} | {row.get('status')} | {str(row.get('evidence')).replace('|', '/')} | {row.get('gate')} |"
        )
    lines.extend(
        [
            "",
            "## Key Counts",
            "",
            "| Table | Before | After Restore | Status |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in counts:
        lines.append(
            f"| {row.get('table')} | {row.get('before_count')} | {row.get('after_restore_count')} | {row.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Remaining Production Gate",
            "",
            "This clears the local/disposable restore-mechanics rehearsal only. Production readiness still requires Supabase provider backup/PITR confirmation or a staged restore into a disposable hosted target, plus the hosted write-unlock audit rehearsal before remote writes are enabled.",
            "",
            "## Related Files",
            "",
            "- `reports/backup_restore_drill.csv`",
            "- `reports/backup_safety_ledger.md`",
            "- `reports/remote_staging_validation_matrix.md`",
            "- `reports/remote_production_cutover_checklist.md`",
        ]
    )
    (REPORTS_DIR / "backup_restore_drill.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows: list[dict[str, Any]] = []
    checks: list[Check] = []
    generated_at = now_utc()
    project_backups = sorted(BACKUP_DIR.glob("local_crm_*.sqlite")) if BACKUP_DIR.exists() else []
    live_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0

    if not DB_PATH.exists():
        raise SystemExit(f"Missing local CRM database: {DB_PATH}")

    with tempfile.TemporaryDirectory(prefix="chillcrm_restore_drill_") as tmp:
        tmp_dir = Path(tmp)
        working_db = tmp_dir / "working_local_crm.sqlite"
        drill_backup = tmp_dir / "drill_backup.sqlite"
        restored_db = tmp_dir / "restored_local_crm.sqlite"
        shutil.copy2(DB_PATH, working_db)

        before_integrity = sqlite_integrity(working_db)
        before_counts = key_counts(working_db)
        before_digest = db_digest(working_db)
        checks.append(Check("source_copy_integrity", "pass" if before_integrity == "ok" else "fail", before_integrity, "local_restore_rehearsal"))
        checks.append(Check("source_key_counts", "pass" if before_counts else "fail", f"{len(before_counts)} key tables counted", "local_restore_rehearsal"))

        create_sqlite_backup(working_db, drill_backup)
        backup_integrity = sqlite_integrity(drill_backup)
        backup_digest = db_digest(drill_backup)
        checks.append(Check("drill_backup_created", "pass" if drill_backup.exists() and drill_backup.stat().st_size > 0 else "fail", f"{drill_backup.stat().st_size if drill_backup.exists() else 0} bytes", "local_restore_rehearsal"))
        checks.append(Check("drill_backup_integrity", "pass" if backup_integrity == "ok" else "fail", backup_integrity, "local_restore_rehearsal"))

        shutil.copy2(drill_backup, restored_db)
        after_integrity = sqlite_integrity(restored_db)
        after_counts = key_counts(restored_db)
        after_digest = db_digest(restored_db)
        counts_match = before_counts == after_counts
        checks.append(Check("restored_copy_integrity", "pass" if after_integrity == "ok" else "fail", after_integrity, "local_restore_rehearsal"))
        checks.append(Check("restored_key_counts", "pass" if counts_match else "fail", f"{len(after_counts)} key tables counted", "local_restore_rehearsal"))
        checks.append(Check("backup_digest_match", "pass" if backup_digest == after_digest else "fail", "restored copy matches drill backup bytes", "local_restore_rehearsal"))
        checks.append(Check("live_database_untouched", "pass" if before_digest == db_digest(DB_PATH) else "fail", "live database digest checked after drill", "local_restore_rehearsal"))

    failed = [check for check in checks if check.status != "pass"]
    rows.append(
        {
            "row_type": "summary",
            "generated_at": generated_at,
            "status": "backup_restore_drill_passed" if not failed else "backup_restore_drill_failed",
            "live_database": str(DB_PATH),
            "live_database_bytes": live_bytes,
            "project_backup_count": len(project_backups),
            "counts_matched": "yes" if before_counts == after_counts else "no",
            "production_note": "Local disposable restore passed; Supabase provider backup/PITR restore remains a production gate.",
        }
    )
    for check in checks:
        rows.append(
            {
                "row_type": "check",
                "name": check.name,
                "status": check.status,
                "evidence": check.evidence,
                "gate": check.gate,
            }
        )
    for table in sorted(set(before_counts) | set(after_counts)):
        before = before_counts.get(table)
        after = after_counts.get(table)
        rows.append(
            {
                "row_type": "count",
                "table": table,
                "before_count": before,
                "after_restore_count": after,
                "status": "pass" if before == after else "fail",
            }
        )
    write_csv(REPORTS_DIR / "backup_restore_drill.csv", rows)
    write_report(rows)
    print(f"Backup restore drill {'passed' if not failed else 'failed'} with {len(checks) - len(failed)} passed and {len(failed)} failed checks.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
