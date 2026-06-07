#!/usr/bin/env python3
"""Prepare and upload recovered CHILLCRM document files to Supabase Storage.

Default mode is manifest-only and does not contact Supabase.

Upload mode expects:
  CHILLCRM_SUPABASE_URL
  CHILLCRM_SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY
  CHILLCRM_DATABASE_URL, unless --no-remote-records is used

Do not hard-code credentials into this file or into generated reports.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import ssl
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
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
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_BUCKET = "chillcrm-documents"


@dataclass
class DocumentObject:
    archive_item_id: int
    original_resource_id: int | None
    title: str
    content_type: str
    size_bytes: int
    local_file: str
    absolute_path: Path
    actual_bytes: int
    sha256: str
    storage_bucket: str
    storage_key: str
    status: str
    detail: str


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_type_for(row: sqlite3.Row, path: Path) -> str:
    explicit = str(row["content_type"] or "").strip()
    if explicit:
        return explicit
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def storage_key_for(row: sqlite3.Row, digest: str, path: Path) -> str:
    archive_id = int(row["id"])
    resource_id = row["original_resource_id"]
    resource_part = str(resource_id) if resource_id is not None else "unknown"
    suffix = path.suffix.lower()
    if not suffix or len(suffix) > 20:
        suffix = ".bin"
    return f"zendesk-documents/archive_item_{archive_id}/resource_{resource_part}_{digest[:16]}{suffix}"


def read_document_objects(sqlite_conn: sqlite3.Connection, bucket: str, limit: int | None = None) -> list[DocumentObject]:
    sql = """
        SELECT id, original_resource_id, title, content_type, size_bytes, local_file
        FROM imported_archive_items
        WHERE item_type = 'document'
        ORDER BY id
    """
    if limit is not None:
        sql += " LIMIT ?"
        rows = sqlite_conn.execute(sql, (limit,)).fetchall()
    else:
        rows = sqlite_conn.execute(sql).fetchall()
    objects: list[DocumentObject] = []
    for row in rows:
        local_file = str(row["local_file"] or "")
        absolute_path = PROJECT_ROOT / local_file if local_file else PROJECT_ROOT
        if not local_file:
            objects.append(
                DocumentObject(
                    archive_item_id=int(row["id"]),
                    original_resource_id=row["original_resource_id"],
                    title=str(row["title"] or ""),
                    content_type=str(row["content_type"] or ""),
                    size_bytes=int(row["size_bytes"] or 0),
                    local_file=local_file,
                    absolute_path=absolute_path,
                    actual_bytes=0,
                    sha256="",
                    storage_bucket=bucket,
                    storage_key="",
                    status="missing_local_file",
                    detail="Archive row has no local_file value.",
                )
            )
            continue
        if not absolute_path.exists():
            objects.append(
                DocumentObject(
                    archive_item_id=int(row["id"]),
                    original_resource_id=row["original_resource_id"],
                    title=str(row["title"] or ""),
                    content_type=content_type_for(row, absolute_path),
                    size_bytes=int(row["size_bytes"] or 0),
                    local_file=local_file,
                    absolute_path=absolute_path,
                    actual_bytes=0,
                    sha256="",
                    storage_bucket=bucket,
                    storage_key="",
                    status="missing_file",
                    detail="Local document file does not exist.",
                )
            )
            continue
        actual_bytes = absolute_path.stat().st_size
        digest = sha256_file(absolute_path)
        expected_bytes = int(row["size_bytes"] or 0)
        status = "ready"
        detail = "Ready for private storage upload."
        if expected_bytes and expected_bytes != actual_bytes:
            status = "size_mismatch"
            detail = f"Database size {expected_bytes} differs from file size {actual_bytes}."
        objects.append(
            DocumentObject(
                archive_item_id=int(row["id"]),
                original_resource_id=row["original_resource_id"],
                title=str(row["title"] or ""),
                content_type=content_type_for(row, absolute_path),
                size_bytes=expected_bytes,
                local_file=local_file,
                absolute_path=absolute_path,
                actual_bytes=actual_bytes,
                sha256=digest,
                storage_bucket=bucket,
                storage_key=storage_key_for(row, digest, absolute_path),
                status=status,
                detail=detail,
            )
        )
    return objects


def storage_base_url() -> str:
    supabase_url = os.environ.get("CHILLCRM_SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise RuntimeError("CHILLCRM_SUPABASE_URL is required for upload mode.")
    return f"{supabase_url}/storage/v1"


def storage_key() -> str:
    key = os.environ.get("CHILLCRM_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("CHILLCRM_SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY is required for upload mode.")
    return key


def storage_request(
    method: str,
    path: str,
    bearer: str,
    *,
    json_body: dict[str, Any] | None = None,
    file_path: Path | None = None,
    content_type: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    headers = {
        "Authorization": f"Bearer {bearer}",
        "apikey": bearer,
    }
    if extra_headers:
        headers.update(extra_headers)
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif file_path is not None:
        data = file_path.read_bytes()
        headers["Content-Type"] = content_type or "application/octet-stream"
    request = urllib.request.Request(f"{storage_base_url()}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as error:
        return int(error.code), error.read()


def bucket_path(bucket: str) -> str:
    return "/" + urllib.parse.quote(bucket, safe="")


def object_path(bucket: str, key: str, *, info: bool = False) -> str:
    prefix = "/object/info" if info else "/object"
    return f"{prefix}/{urllib.parse.quote(bucket, safe='')}/{urllib.parse.quote(key, safe='/')}"


def ensure_private_bucket(bucket: str, bearer: str) -> None:
    status, body = storage_request("GET", "/bucket", bearer)
    if status == 200:
        buckets = json.loads(body.decode("utf-8") or "[]")
        for existing in buckets:
            if existing.get("id") == bucket or existing.get("name") == bucket:
                if existing.get("public") is True:
                    raise RuntimeError(f"Bucket {bucket} exists but is public. Stop and make it private before uploading CRM documents.")
                return
    status, body = storage_request("POST", "/bucket", bearer, json_body={"id": bucket, "name": bucket, "public": False})
    if status in {200, 201}:
        return
    text = body.decode("utf-8", errors="replace")
    if status in {400, 409} and "already" in text.casefold():
        return
    raise RuntimeError(f"Could not create private bucket {bucket}: HTTP {status} {text[:300]}")


def object_exists(bucket: str, key: str, bearer: str) -> bool:
    status, _ = storage_request("HEAD", object_path(bucket, key, info=True), bearer)
    return status in {200, 204}


def upload_object(obj: DocumentObject, bearer: str, *, skip_existing: bool, upsert: bool) -> str:
    if skip_existing and object_exists(obj.storage_bucket, obj.storage_key, bearer):
        return "skipped_existing"
    headers = {"cache-control": "3600"}
    if upsert:
        headers["x-upsert"] = "true"
    status, body = storage_request(
        "POST",
        object_path(obj.storage_bucket, obj.storage_key),
        bearer,
        file_path=obj.absolute_path,
        content_type=obj.content_type,
        extra_headers=headers,
    )
    if status in {200, 201}:
        return "uploaded"
    if upsert and status in {400, 409}:
        status, body = storage_request(
            "PUT",
            object_path(obj.storage_bucket, obj.storage_key),
            bearer,
            file_path=obj.absolute_path,
            content_type=obj.content_type,
            extra_headers={"cache-control": "3600"},
        )
        if status in {200, 201}:
            return "updated"
    text = body.decode("utf-8", errors="replace")
    raise RuntimeError(f"Upload failed for archive item {obj.archive_item_id}: HTTP {status} {text[:300]}")


def upsert_remote_file_objects(pg_conn: pg.Connection, objects: list[DocumentObject]) -> None:
    with closing(pg_conn.cursor()) as cur:
        for obj in objects:
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
                    obj.archive_item_id,
                    obj.storage_bucket,
                    obj.storage_key,
                    obj.local_file,
                    obj.actual_bytes,
                    obj.content_type,
                ),
            )
        cur.execute(
            """
            INSERT INTO crm.migration_runs (run_type, completed_at, status, notes)
            VALUES (%s, now(), %s, %s)
            """,
            (
                "supabase_storage_upload",
                "completed",
                f"Uploaded or verified {len(objects)} recovered document files in private Supabase Storage.",
            ),
        )
    pg_conn.commit()


def validate_remote_file_objects(pg_conn: pg.Connection, expected_count: int, expected_bytes: int, bucket: str) -> dict[str, int]:
    with closing(pg_conn.cursor()) as cur:
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
        linked_count = cur.fetchone()[0]
    return {
        "expected_count": int(expected_count),
        "expected_bytes": int(expected_bytes),
        "remote_file_objects": int(count),
        "remote_file_bytes": int(total_bytes),
        "linked_document_rows": int(linked_count),
    }


def write_csv(path: Path, objects: list[DocumentObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "archive_item_id",
        "original_resource_id",
        "title",
        "content_type",
        "size_bytes",
        "actual_bytes",
        "sha256",
        "storage_bucket",
        "storage_key",
        "local_file",
        "status",
        "detail",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for obj in objects:
            writer.writerow({field: getattr(obj, field) for field in fieldnames})


def write_markdown(
    path: Path,
    objects: list[DocumentObject],
    *,
    mode: str,
    bucket: str,
    upload_counts: dict[str, int] | None = None,
    remote_counts: dict[str, int] | None = None,
) -> None:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    total = len(objects)
    ready = sum(1 for obj in objects if obj.status in {"ready", "uploaded", "updated", "skipped_existing"})
    missing = sum(1 for obj in objects if obj.status.startswith("missing"))
    mismatched = sum(1 for obj in objects if obj.status == "size_mismatch")
    bytes_total = sum(obj.actual_bytes for obj in objects)
    status = "ready_for_upload" if mode == "manifest" and ready == total and not missing and not mismatched else mode
    if mode == "upload" and upload_counts and not missing and not mismatched:
        status = "uploaded" if ready == total else "partial_upload"
    lines = [
        "# CHILLCRM Supabase Storage Migration",
        "",
        f"Generated: {generated}",
        "",
        "This report tracks recovered Zendesk document file movement into private Supabase Storage. It does not include service-role keys, database passwords, signed URLs, or public file links.",
        "",
        "## Summary",
        "",
        f"- Mode: {mode}.",
        f"- Status: {status}.",
        f"- Bucket: `{bucket}`.",
        f"- Document files inventoried: {total}.",
        f"- Ready or uploaded rows: {ready}.",
        f"- Missing local files: {missing}.",
        f"- Size mismatches: {mismatched}.",
        f"- Local bytes: {bytes_total:,}.",
    ]
    if upload_counts:
        lines.extend(
            [
                f"- Uploaded: {upload_counts.get('uploaded', 0)}.",
                f"- Updated: {upload_counts.get('updated', 0)}.",
                f"- Skipped existing: {upload_counts.get('skipped_existing', 0)}.",
            ]
        )
    if remote_counts:
        lines.extend(
            [
                f"- Remote file object rows: {remote_counts.get('remote_file_objects', 0)}.",
                f"- Remote file object bytes: {remote_counts.get('remote_file_bytes', 0):,}.",
                f"- Linked remote document rows: {remote_counts.get('linked_document_rows', 0)}.",
            ]
        )
    lines.extend(
        [
            "",
            "## Storage Key Strategy",
            "",
            "Storage keys are deterministic and avoid customer names in the object path: `zendesk-documents/archive_item_[id]/resource_[zendesk_resource_id]_[sha16].[ext]`.",
            "",
            "## Next Gate",
            "",
        ]
    )
    if mode == "manifest":
        lines.append("Run upload mode only after the private Supabase service-role key is available in the environment and the bucket should be created as private.")
    else:
        lines.append("After upload, enable `DOCUMENT_FILE_ACCESS_ENABLED` only after hosted auth and signed/proxied download behavior are verified; keep `reports/vercel_hosted_app_smoke.md` as the current signed-access proof.")
    lines.extend(
        [
            "",
            "## Source Notes",
            "",
            "- Supabase Storage buckets can be private by default and are governed by storage access policies.",
            "- Supabase Storage object metadata is separate from file content; CHILLCRM records its own `crm.remote_file_objects` mapping for app use and migration audit.",
            "",
            "## Related Files",
            "",
            "- `reports/chillcrm_supabase_storage_manifest.csv`",
            "- `reports/chillcrm_supabase_staging_validation.md`",
            "- `reports/hosted_database_data_load_plan.md`",
            "- `reports/remote_staging_deployment_spec.md`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or upload CHILLCRM recovered document files to private Supabase Storage.")
    parser.add_argument("--sqlite-db", default=str(DEFAULT_SQLITE_DB))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--mode", choices=["manifest", "upload", "validate"], default="manifest")
    parser.add_argument("--limit", type=int, default=0, help="Optional document limit for smoke testing.")
    parser.add_argument("--skip-existing", action="store_true", help="Do not re-upload objects that already exist.")
    parser.add_argument("--upsert", action="store_true", help="Allow replacing existing objects at the same storage key.")
    parser.add_argument("--no-create-bucket", action="store_true", help="Do not create the bucket in upload mode.")
    parser.add_argument("--no-remote-records", action="store_true", help="Upload files without writing crm.remote_file_objects rows.")
    args = parser.parse_args()

    sqlite_conn = sqlite_connect(Path(args.sqlite_db))
    try:
        objects = read_document_objects(sqlite_conn, args.bucket, args.limit or None)
    finally:
        sqlite_conn.close()

    csv_path = Path(args.reports_dir) / "chillcrm_supabase_storage_manifest.csv"
    md_path = Path(args.reports_dir) / "chillcrm_supabase_storage_migration.md"
    blockers = [obj for obj in objects if obj.status != "ready"]
    upload_counts: dict[str, int] = {}
    remote_counts: dict[str, int] | None = None

    if args.mode == "manifest":
        write_csv(csv_path, objects)
        write_markdown(md_path, objects, mode=args.mode, bucket=args.bucket)
        print(f"Wrote {md_path}")
        print(f"Wrote {csv_path}")
        if blockers:
            print(f"Manifest has blockers: {len(blockers)}", file=sys.stderr)
            return 1
        print("CHILLCRM Supabase storage manifest is ready.")
        return 0

    if blockers:
        write_csv(csv_path, objects)
        write_markdown(md_path, objects, mode=args.mode, bucket=args.bucket)
        print(f"Local file blockers must be resolved before {args.mode}: {len(blockers)}", file=sys.stderr)
        return 1

    database_url = os.environ.get("CHILLCRM_DATABASE_URL", "")
    if args.mode in {"upload", "validate"} and not args.no_remote_records and not database_url:
        print("CHILLCRM_DATABASE_URL is required unless --no-remote-records is used.", file=sys.stderr)
        return 2

    if args.mode == "upload":
        bearer = storage_key()
        if not args.no_create_bucket:
            ensure_private_bucket(args.bucket, bearer)
        completed: list[DocumentObject] = []
        for obj in objects:
            result = upload_object(obj, bearer, skip_existing=args.skip_existing, upsert=args.upsert)
            upload_counts[result] = upload_counts.get(result, 0) + 1
            obj.status = result
            obj.detail = f"Storage object {result}."
            completed.append(obj)
        if not args.no_remote_records:
            pg_conn = postgres_connect(database_url)
            try:
                upsert_remote_file_objects(pg_conn, completed)
                remote_counts = validate_remote_file_objects(pg_conn, len(objects), sum(obj.actual_bytes for obj in objects), args.bucket)
            finally:
                pg_conn.close()
    elif args.mode == "validate" and not args.no_remote_records:
        pg_conn = postgres_connect(database_url)
        try:
            remote_counts = validate_remote_file_objects(pg_conn, len(objects), sum(obj.actual_bytes for obj in objects), args.bucket)
        finally:
            pg_conn.close()

    write_csv(csv_path, objects)
    write_markdown(md_path, objects, mode=args.mode, bucket=args.bucket, upload_counts=upload_counts, remote_counts=remote_counts)
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if remote_counts and (
        remote_counts["remote_file_objects"] < remote_counts["expected_count"]
        or remote_counts["remote_file_bytes"] != remote_counts["expected_bytes"]
        or remote_counts["linked_document_rows"] < remote_counts["expected_count"]
    ):
        print("Remote storage metadata validation did not fully match expected document coverage.", file=sys.stderr)
        return 1
    print("CHILLCRM Supabase storage migration step completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
