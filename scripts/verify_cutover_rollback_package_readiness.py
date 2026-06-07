#!/usr/bin/env python3
"""Verify local rollback package readiness before CHILLCRM production cutover."""

from __future__ import annotations

import csv
import hashlib
import os
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
BACKUP_DIR = PROJECT_ROOT / "backups"
REPORTS_DIR = PROJECT_ROOT / "reports"
BACKUP_DRILL_REPORT = REPORTS_DIR / "backup_restore_drill.md"
STORAGE_MANIFEST = REPORTS_DIR / "chillcrm_supabase_storage_manifest.csv"
STORAGE_REPORT = REPORTS_DIR / "chillcrm_supabase_storage_migration.md"

CORE_TABLE_MINIMUMS = {
    "people": 997,
    "companies": 378,
    "leads": 1327,
    "deals": 125,
    "tasks": 18,
    "notes": 40,
    "imported_archive_items": 884,
}


@dataclass
class Check:
    name: str
    status: str
    evidence: str
    gate: str


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(value: Any, limit: int = 260) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def sqlite_check(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        return str(conn.execute("PRAGMA quick_check").fetchone()[0])
    finally:
        conn.close()


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def force_local_sqlite() -> Iterator[None]:
    keys = ["DATABASE_URL", "CHILLCRM_DATABASE_ADAPTER", "CRM_DATABASE_ADAPTER"]
    original = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def export_status() -> dict[str, Any]:
    with force_local_sqlite():
        handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
        handler.db_path = DB_PATH
        return handler.export_package_status()


def read_storage_manifest() -> list[dict[str, str]]:
    if not STORAGE_MANIFEST.exists():
        return []
    with STORAGE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["result"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], checks: list[Check], table_rows: list[dict[str, Any]]) -> None:
    failed = [check for check in checks if check.status != "pass"]
    lines = [
        "# Cutover Rollback Package Readiness",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "This report verifies that the current local CRM rollback package is ready enough for production-cutover planning. It checks the live local database, existing backups, the prior disposable restore drill, package export availability, and the Supabase document-storage manifest. It does not create backups, restore databases, upload files, change hosted settings, unlock writes, switch source of truth, expose secrets, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary['status']}.",
        f"- Production gate: {summary['production_gate']}.",
        f"- Passed: {summary['passed']}.",
        f"- Failed: {summary['failed']}.",
        f"- Local database: `{summary['local_database']}`.",
        f"- Local database bytes: {int(summary['local_database_bytes']):,}.",
        f"- Existing project backups: {summary['backup_count']}.",
        f"- Latest backup: `{summary['latest_backup']}`.",
        f"- Export packages ready: {summary['export_packages_ready']} of {summary['export_packages_total']}.",
        f"- Document package files: {summary['document_package_files']}.",
        f"- Document package bytes: {int(summary['document_package_bytes']):,}.",
        f"- Storage manifest rows: {summary['storage_manifest_rows']}.",
        f"- Storage manifest bytes: {int(summary['storage_manifest_bytes']):,}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Gate |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            f"| {check.name} | {check.status} | {check.evidence.replace('|', '/')} | {check.gate} |"
        )
    lines.extend(
        [
            "",
            "## Core Counts",
            "",
            "| Table | Count | Minimum | Status |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in table_rows:
        lines.append(f"| {row['table']} | {row['count']} | {row['minimum']} | {row['status']} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This clears only the local rollback-package readiness proof. It is not the final cutover freeze package, does not prove Supabase provider backup/PITR visibility, does not run the newest hosted smoke, does not approve hosted write-unlock audit, and does not make the hosted CRM the source of truth.",
            "",
            "## Next Gate",
            "",
            "After owner approval for cutover, create a final freeze package immediately before any production source-of-truth switch, rerun this verifier, run the newest hosted smoke, confirm Supabase provider backup/PITR visibility, and complete owner shakedown signoff.",
            "",
            "## Related Files",
            "",
            "- `reports/cutover_rollback_package_readiness.csv`",
            "- `reports/backup_restore_drill.md`",
            "- `reports/chillcrm_supabase_storage_manifest.csv`",
            "- `reports/chillcrm_supabase_storage_migration.md`",
            "- `reports/remote_production_cutover_checklist.md`",
        ]
    )
    if failed:
        lines.extend(["", "## Failed Checks", ""])
        for check in failed:
            lines.append(f"- {check.name}: {check.evidence}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    checks: list[Check] = []
    table_rows: list[dict[str, Any]] = []

    db_exists = DB_PATH.exists() and DB_PATH.is_file()
    db_bytes = DB_PATH.stat().st_size if db_exists else 0
    checks.append(Check("local_database_exists", "pass" if db_exists and db_bytes > 0 else "fail", f"{db_bytes} bytes", "rollback_package"))
    if db_exists:
        quick = sqlite_check(DB_PATH)
        checks.append(Check("local_database_quick_check", "pass" if quick == "ok" else "fail", quick, "rollback_package"))

        conn = sqlite3.connect(DB_PATH)
        try:
            core_count_failures = []
            for table, minimum in CORE_TABLE_MINIMUMS.items():
                count = table_count(conn, table)
                status = "pass" if count >= minimum else "fail"
                table_rows.append({"row_type": "table_count", "table": table, "count": count, "minimum": minimum, "status": status})
                if status != "pass":
                    core_count_failures.append(f"{table}={count} below {minimum}")
            document_rows = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM imported_archive_items
                    WHERE item_type = 'document'
                      AND local_file IS NOT NULL
                      AND local_file != ''
                    """
                ).fetchone()[0]
            )
            checks.append(
                Check(
                    "core_table_counts",
                    "pass" if not core_count_failures else "fail",
                    "All core migrated counts meet expected minimums." if not core_count_failures else "; ".join(core_count_failures),
                    "rollback_package",
                )
            )
            checks.append(
                Check(
                    "document_archive_rows",
                    "pass" if document_rows >= 203 else "fail",
                    f"{document_rows} document archive rows with local files",
                    "document_rollback_package",
                )
            )
            archive_ids = {
                str(row[0])
                for row in conn.execute(
                    """
                    SELECT id
                    FROM imported_archive_items
                    WHERE item_type = 'document'
                      AND local_file IS NOT NULL
                      AND local_file != ''
                    """
                ).fetchall()
            }
        finally:
            conn.close()
    else:
        archive_ids = set()

    backup_text = BACKUP_DRILL_REPORT.read_text(encoding="utf-8") if BACKUP_DRILL_REPORT.exists() else ""
    checks.append(
        Check(
            "backup_restore_drill_report",
            "pass" if "Status: backup_restore_drill_passed" in backup_text and "Failed: 0" in backup_text else "fail",
            "Prior disposable local restore drill passed with zero failures." if backup_text else "Missing backup restore drill report.",
            "rollback_package",
        )
    )

    backups = sorted(BACKUP_DIR.glob("local_crm_*.sqlite")) if BACKUP_DIR.exists() else []
    latest_backup = backups[-1] if backups else None
    checks.append(
        Check(
            "project_backup_inventory",
            "pass" if backups and all(path.stat().st_size > 0 for path in backups) else "fail",
            f"{len(backups)} backup files present; latest={latest_backup.name if latest_backup else 'missing'}",
            "rollback_package",
        )
    )
    if latest_backup:
        latest_backup_check = sqlite_check(latest_backup)
        checks.append(
            Check(
                "latest_backup_quick_check",
                "pass" if latest_backup_check == "ok" else "fail",
                latest_backup_check,
                "rollback_package",
            )
        )

    package_status = export_status()
    core_package = package_status.get("core_package") or {}
    document_package = package_status.get("document_package") or {}
    ready_count = int(package_status.get("ready_count") or 0)
    total_count = int(package_status.get("total_count") or 0)
    document_package_files = int(document_package.get("file_count") or 0)
    document_package_bytes = int(document_package.get("bytes") or 0)
    checks.append(
        Check(
            "export_package_status",
            "pass" if package_status.get("status") == "complete" and ready_count == total_count == 2 and core_package.get("ready") else "fail",
            f"status={package_status.get('status')}; ready={ready_count}/{total_count}",
            "rollback_package",
        )
    )
    checks.append(
        Check(
            "document_package_status",
            "pass" if document_package.get("ready") and document_package_files >= 203 and document_package_bytes > 100_000_000 else "fail",
            f"ready={document_package.get('ready')}; files={document_package_files}; bytes={document_package_bytes}",
            "document_rollback_package",
        )
    )

    manifest_rows = read_storage_manifest()
    manifest_total_bytes = 0
    missing_files: list[str] = []
    mismatched_sizes: list[str] = []
    mismatched_hashes: list[str] = []
    bad_statuses: list[str] = []
    bad_buckets: list[str] = []
    missing_archive_ids: list[str] = []
    storage_keys_missing = 0
    for row in manifest_rows:
        archive_id = str(row.get("archive_item_id") or "")
        local_file = row.get("local_file") or ""
        local_path = PROJECT_ROOT / local_file
        expected_size = int(row.get("size_bytes") or 0)
        actual_size = int(row.get("actual_bytes") or 0)
        expected_hash = row.get("sha256") or ""
        manifest_total_bytes += actual_size
        if row.get("status") != "uploaded":
            bad_statuses.append(archive_id)
        if row.get("storage_bucket") != "chillcrm-documents":
            bad_buckets.append(archive_id)
        if not row.get("storage_key"):
            storage_keys_missing += 1
        if archive_ids and archive_id not in archive_ids:
            missing_archive_ids.append(archive_id)
        if not local_path.exists() or not local_path.is_file():
            missing_files.append(local_file)
            continue
        file_size = local_path.stat().st_size
        if expected_size != actual_size or file_size != actual_size:
            mismatched_sizes.append(f"{archive_id}:{file_size}/{expected_size}/{actual_size}")
        if expected_hash and sha256_file(local_path) != expected_hash:
            mismatched_hashes.append(archive_id)

    checks.append(
        Check(
            "storage_manifest_rows",
            "pass" if len(manifest_rows) >= 203 else "fail",
            f"{len(manifest_rows)} manifest rows",
            "document_rollback_package",
        )
    )
    checks.append(
        Check(
            "storage_manifest_statuses",
            "pass" if manifest_rows and not bad_statuses and not bad_buckets and storage_keys_missing == 0 else "fail",
            f"bad_statuses={len(bad_statuses)}, bad_buckets={len(bad_buckets)}, missing_keys={storage_keys_missing}",
            "document_rollback_package",
        )
    )
    checks.append(
        Check(
            "storage_manifest_local_files",
            "pass" if manifest_rows and not missing_files and not mismatched_sizes and not mismatched_hashes else "fail",
            clip(f"missing_files={len(missing_files)}, size_mismatches={len(mismatched_sizes)}, hash_mismatches={len(mismatched_hashes)}"),
            "document_rollback_package",
        )
    )
    checks.append(
        Check(
            "storage_manifest_archive_links",
            "pass" if manifest_rows and not missing_archive_ids else "fail",
            f"missing_archive_ids={len(missing_archive_ids)}",
            "document_rollback_package",
        )
    )
    storage_text = STORAGE_REPORT.read_text(encoding="utf-8") if STORAGE_REPORT.exists() else ""
    checks.append(
        Check(
            "storage_migration_report",
            "pass"
            if "Status: uploaded" in storage_text
            and "Document files inventoried: 203" in storage_text
            and "Uploaded: 203" in storage_text
            and "Remote file object rows: 203" in storage_text
            and "Linked remote document rows: 203" in storage_text
            else "fail",
            "Supabase storage migration report shows 203 uploaded, 203 remote objects, and 203 linked documents." if storage_text else "Missing storage migration report.",
            "document_rollback_package",
        )
    )

    failed = [check for check in checks if check.status != "pass"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "cutover_rollback_package_ready" if not failed else "cutover_rollback_package_attention",
        "production_gate": "pass" if not failed else "blocked",
        "passed": sum(1 for check in checks if check.status == "pass"),
        "failed": len(failed),
        "local_database": str(DB_PATH),
        "local_database_bytes": db_bytes,
        "backup_count": len(backups),
        "latest_backup": str(latest_backup.relative_to(PROJECT_ROOT)) if latest_backup else "missing",
        "export_packages_ready": ready_count,
        "export_packages_total": total_count,
        "document_package_files": document_package_files,
        "document_package_bytes": document_package_bytes,
        "storage_manifest_rows": len(manifest_rows),
        "storage_manifest_bytes": manifest_total_bytes,
    }
    rows: list[dict[str, Any]] = [summary]
    rows.extend({"row_type": "check", **check.__dict__} for check in checks)
    rows.extend(table_rows)
    write_csv(REPORTS_DIR / "cutover_rollback_package_readiness.csv", rows)
    write_report(REPORTS_DIR / "cutover_rollback_package_readiness.md", summary, checks, table_rows)
    print(
        {
            "status": summary["status"],
            "production_gate": summary["production_gate"],
            "passed": summary["passed"],
            "failed": summary["failed"],
        }
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
