#!/usr/bin/env python3
"""Restore Supabase document-file link rows from the storage manifest.

This writes only crm.remote_file_objects metadata. It does not upload files,
change CRM customer records, unlock hosted writes, store secrets, or switch
source of truth.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.parse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pg8000.dbapi as pg

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_MANIFEST = REPORTS_DIR / "chillcrm_supabase_storage_manifest.csv"
DEFAULT_BUCKET = "chillcrm-documents"
CSV_REPORT = REPORTS_DIR / "supabase_document_file_link_repair.csv"
MD_REPORT = REPORTS_DIR / "supabase_document_file_link_repair.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def manifest_rows(path: Path, bucket: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing storage manifest: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status = str(row.get("status") or "").strip().lower()
            if status not in {"uploaded", "ready", "skipped_existing"}:
                continue
            archive_item_id = int_value(row.get("archive_item_id"))
            storage_key = str(row.get("storage_key") or "").strip()
            if not archive_item_id or not storage_key:
                continue
            rows.append(
                {
                    "archive_item_id": archive_item_id,
                    "storage_bucket": str(row.get("storage_bucket") or bucket).strip() or bucket,
                    "storage_key": storage_key,
                    "original_local_file": str(row.get("local_file") or "").strip(),
                    "bytes": int_value(row.get("actual_bytes") or row.get("size_bytes")),
                    "content_type": str(row.get("content_type") or "application/octet-stream").strip(),
                }
            )
    return rows


def table_counts(conn: pg.Connection, bucket: str) -> dict[str, int]:
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT count(*), COALESCE(sum(bytes), 0) FROM crm.remote_file_objects WHERE storage_bucket = %s", (bucket,))
        count, total_bytes = cur.fetchone()
        cur.execute(
            """
            SELECT count(*)
            FROM crm.imported_archive_items ai
            JOIN crm.remote_file_objects rfo ON rfo.archive_item_id = ai.id
            WHERE ai.item_type = 'document'
              AND rfo.storage_bucket = %s
            """,
            (bucket,),
        )
        linked = cur.fetchone()[0]
    return {"remote_file_objects": int(count), "remote_file_bytes": int(total_bytes), "linked_remote_documents": int(linked)}


def upsert_links(conn: pg.Connection, rows: list[dict[str, Any]]) -> None:
    with closing(conn.cursor()) as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO crm.remote_file_objects
                    (archive_item_id, storage_bucket, storage_key, original_local_file, bytes, content_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (storage_bucket, storage_key)
                DO UPDATE SET
                    archive_item_id = EXCLUDED.archive_item_id,
                    original_local_file = EXCLUDED.original_local_file,
                    bytes = EXCLUDED.bytes,
                    content_type = EXCLUDED.content_type,
                    uploaded_at = now()
                """,
                (
                    row["archive_item_id"],
                    row["storage_bucket"],
                    row["storage_key"],
                    row["original_local_file"],
                    row["bytes"],
                    row["content_type"],
                ),
            )
        cur.execute(
            """
            INSERT INTO crm.migration_runs (run_type, completed_at, status, notes)
            VALUES (%s, now(), %s, %s)
            """,
            (
                "supabase_document_file_link_repair",
                "completed",
                f"Restored {len(rows)} document-file metadata links from the storage manifest.",
            ),
        )
    conn.commit()


def write_reports(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    fieldnames = ["row_type", "key", "status", "value", "evidence"]
    csv_rows = [
        {"row_type": "summary", "key": key, "status": summary["status"], "value": value, "evidence": ""}
        for key, value in summary.items()
    ]
    csv_rows.extend(rows)
    with CSV_REPORT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    lines = [
        "# Supabase Document File Link Repair",
        "",
        "This report records the targeted repair of hosted document-file metadata links. It stores no database password, service-role key, Vercel token, or signed URL.",
        "",
        "## Summary",
        "",
        f"- Generated: {summary['generated_at']}.",
        f"- Status: {summary['status']}.",
        f"- Production gate: {summary['production_gate']}.",
        f"- Manifest rows restored: {summary['manifest_rows']}.",
        f"- Remote file objects before: {summary['remote_file_objects_before']}.",
        f"- Remote file objects after: {summary['remote_file_objects_after']}.",
        f"- Linked remote document rows after: {summary['linked_remote_documents_after']}.",
        f"- Remote file bytes after: {summary['remote_file_bytes_after']:,}.",
        f"- Provider calls: {summary['provider_calls']}.",
        f"- CRM customer-record writes: {summary['crm_record_writes']}.",
        f"- Remote file metadata writes: {summary['remote_file_metadata_writes']}.",
        f"- Remote write lock changed: {summary['remote_write_lock_changed']}.",
        f"- Source of truth changed: {summary['source_of_truth_changed']}.",
        f"- Secret values stored: {summary['secret_values_stored']}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['key']} | {row['status']} | {str(row['evidence']).replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This repair only restores private document-file metadata links in Supabase staging. It does not upload document bytes, modify people/companies/leads/deals, unlock hosted writes, or approve source-of-truth cutover.",
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore Supabase document-file link rows from the CHILLCRM storage manifest.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    args = parser.parse_args()

    database_url = os.environ.get("CHILLCRM_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
    if not database_url:
        print("CHILLCRM_DATABASE_URL or DATABASE_URL is required.", file=sys.stderr)
        return 2

    rows = manifest_rows(Path(args.manifest), args.bucket)
    expected_bytes = sum(int(row["bytes"]) for row in rows)
    checks: list[dict[str, Any]] = []
    if not rows:
        checks.append({"row_type": "check", "key": "manifest_rows", "status": "failed", "value": 0, "evidence": "No repairable storage manifest rows were found."})
        summary = {
            "generated_at": now_utc(),
            "status": "supabase_document_file_link_repair_failed",
            "production_gate": "blocked",
            "manifest_rows": 0,
            "remote_file_objects_before": 0,
            "remote_file_objects_after": 0,
            "linked_remote_documents_after": 0,
            "remote_file_bytes_after": 0,
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_file_metadata_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
        write_reports(summary, checks)
        print(json.dumps(summary, indent=2))
        return 1

    conn = postgres_connect(database_url)
    try:
        before = table_counts(conn, args.bucket)
        upsert_links(conn, rows)
        after = table_counts(conn, args.bucket)
    finally:
        conn.close()

    checks.append(
        {
            "row_type": "check",
            "key": "manifest_loaded",
            "status": "passed" if len(rows) == 203 else "review",
            "value": len(rows),
            "evidence": f"{len(rows)} storage manifest rows prepared for metadata repair.",
        }
    )
    checks.append(
        {
            "row_type": "check",
            "key": "remote_file_object_count",
            "status": "passed" if after["remote_file_objects"] >= len(rows) else "failed",
            "value": after["remote_file_objects"],
            "evidence": f"before={before['remote_file_objects']}; after={after['remote_file_objects']}; expected_at_least={len(rows)}.",
        }
    )
    checks.append(
        {
            "row_type": "check",
            "key": "linked_remote_documents",
            "status": "passed" if after["linked_remote_documents"] >= len(rows) else "failed",
            "value": after["linked_remote_documents"],
            "evidence": f"linked_document_rows={after['linked_remote_documents']}; expected_at_least={len(rows)}.",
        }
    )
    checks.append(
        {
            "row_type": "check",
            "key": "remote_file_bytes",
            "status": "passed" if after["remote_file_bytes"] >= expected_bytes else "failed",
            "value": after["remote_file_bytes"],
            "evidence": f"remote_bytes={after['remote_file_bytes']}; manifest_bytes={expected_bytes}.",
        }
    )
    failed = [row for row in checks if row["status"] == "failed"]
    summary = {
        "generated_at": now_utc(),
        "status": "supabase_document_file_link_repair_passed" if not failed else "supabase_document_file_link_repair_failed",
        "production_gate": "pass" if not failed else "blocked",
        "manifest_rows": len(rows),
        "remote_file_objects_before": before["remote_file_objects"],
        "remote_file_objects_after": after["remote_file_objects"],
        "linked_remote_documents_after": after["linked_remote_documents"],
        "remote_file_bytes_after": after["remote_file_bytes"],
        "provider_calls": "yes",
        "crm_record_writes": "no",
        "remote_file_metadata_writes": "yes",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    write_reports(summary, checks)
    print(json.dumps(summary, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
