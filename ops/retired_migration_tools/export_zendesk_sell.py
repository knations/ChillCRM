#!/usr/bin/env python3
"""Export Zendesk Sell data into a local timestamped JSON snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://api.getbase.com"
USER_AGENT = "ZendeskSellLocalExporter/1.0"

COLLECTIONS = [
    ("users", "/v2/users"),
    ("contacts", "/v2/contacts"),
    ("leads", "/v2/leads"),
    ("deals", "/v2/deals"),
    ("notes", "/v2/notes"),
    ("tasks", "/v2/tasks"),
    ("tags", "/v2/tags"),
    ("pipelines", "/v2/pipelines"),
    ("stages", "/v2/stages"),
]

CUSTOM_FIELD_ENDPOINTS = [
    ("lead_custom_fields", "/v2/lead/custom_fields"),
    ("contact_custom_fields", "/v2/contact/custom_fields"),
    ("deal_custom_fields", "/v2/deal/custom_fields"),
    ("prospect_and_customer_custom_fields", "/v2/prospect_and_customer/custom_fields"),
]

OPTIONAL_METADATA_ENDPOINTS = [
    ("sources", "/v2/sources"),
    ("loss_reasons", "/v2/loss_reasons"),
]

EXTENDED_OPTIONAL_ENDPOINTS = [
    ("calls", "/v2/calls"),
    ("call_outcomes", "/v2/call_outcomes"),
    ("visits", "/v2/visits"),
    ("visit_outcomes", "/v2/visit_outcomes"),
    ("text_messages", "/v2/text_messages"),
    ("products", "/v2/products"),
    ("orders", "/v2/orders"),
    ("sequences", "/v2/sequences"),
    ("sequence_enrollments", "/v2/sequence_enrollments"),
    ("collaborations", "/v2/collaborations"),
    ("lead_conversions", "/v2/lead_conversions"),
    ("lead_sources", "/v2/lead_sources"),
    ("deal_sources", "/v2/deal_sources"),
    ("lead_unqualified_reasons", "/v2/lead_unqualified_reasons"),
    ("deal_unqualified_reasons", "/v2/deal_unqualified_reasons"),
]


class ApiError(Exception):
    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def request_json(token: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = path if path.startswith(("http://", "https://")) else f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(exc.code, exc.reason, body) from exc
    except urllib.error.URLError as exc:
        raise ApiError(0, str(exc.reason)) from exc


def fetch_collection(
    token: str,
    path: str,
    per_page: int,
    pause: float,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    page_number = 1
    records: list[dict[str, Any]] = []
    next_path = path

    while True:
        params = {"page": page_number, "per_page": per_page}
        if extra_params:
            params.update(extra_params)
        if next_path.startswith(("http://", "https://")):
            payload = request_json(token, next_path)
        else:
            payload = request_json(token, next_path, params)
        items = payload.get("items") or []
        records.extend(item.get("data") for item in items if item.get("data") is not None)

        meta = payload.get("meta") or {}
        links = meta.get("links") or {}
        next_link = links.get("next") or links.get("next_page")
        if next_link:
            next_path = next_link
        elif next_path.startswith(("http://", "https://")) or len(items) < per_page:
            break
        elif not items:
            break
        page_number += 1
        time.sleep(pause)

    return records


def fetch_single_response_items(token: str, path: str) -> list[dict[str, Any]]:
    payload = request_json(token, path)
    return [item.get("data") for item in payload.get("items", []) if item.get("data") is not None]


def write_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(encoded + b"\n")
    return hashlib.sha256(encoded).hexdigest()


def read_snapshot_records(snapshot_dir: Path, name: str) -> list[dict[str, Any]]:
    path = snapshot_dir / f"{name}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("records") or []


def record_ids(records: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for record in records:
        record_id = record.get("id")
        if isinstance(record_id, int):
            ids.append(record_id)
    return ids


def batched(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def safe_filename(value: Any, fallback: str) -> str:
    text = str(value or fallback).strip() or fallback
    text = re.sub(r"[^A-Za-z0-9._ -]+", "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:160] or fallback


def download_binary(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            with output_path.open("wb") as handle:
                shutil.copyfileobj(response, handle)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(exc.code, exc.reason, body) from exc
    except urllib.error.URLError as exc:
        raise ApiError(0, str(exc.reason)) from exc


def write_export_payload(
    snapshot_dir: Path,
    name: str,
    endpoint: str,
    records: list[dict[str, Any]],
    started_at: str,
    extra_payload: dict[str, Any] | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    output_path = snapshot_dir / f"{name}.json"
    payload = {
        "name": name,
        "endpoint": endpoint,
        "base_url": BASE_URL,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "count": len(records),
        "records": records,
    }
    if extra_payload:
        payload.update(extra_payload)
    checksum = write_json(output_path, payload)
    return {
        "name": name,
        "endpoint": endpoint,
        "status": status,
        "count": len(records),
        "file": output_path.name,
        "sha256": checksum,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def export_endpoint(
    token: str,
    snapshot_dir: Path,
    name: str,
    path: str,
    per_page: int,
    pause: float,
    optional: bool = False,
    paginated: bool = True,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output_path = snapshot_dir / f"{name}.json"

    try:
        if paginated:
            records = fetch_collection(token, path, per_page, pause)
        else:
            records = fetch_single_response_items(token, path)
        return write_export_payload(snapshot_dir, name, path, records, started_at)
    except ApiError as exc:
        if not optional:
            raise
        payload = {
            "name": name,
            "endpoint": path,
            "base_url": BASE_URL,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "error",
            "http_status": exc.status,
            "error": exc.body[:1000] if exc.body else str(exc),
            "records": [],
        }
        checksum = write_json(output_path, payload)
        return {
            "name": name,
            "endpoint": path,
            "status": "error",
            "http_status": exc.status,
            "count": 0,
            "file": output_path.name,
            "sha256": checksum,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def export_documents(
    token: str,
    snapshot_dir: Path,
    per_page: int,
    pause: float,
    download_files: bool = False,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    resource_sources = [
        ("contact", "contacts"),
        ("lead", "leads"),
        ("deal", "deals"),
    ]
    for resource_type, collection_name in resource_sources:
        ids = record_ids(read_snapshot_records(snapshot_dir, collection_name))
        for id_batch in batched(ids, 50):
            params = {
                "resource_type": resource_type,
                "resource_id": ",".join(str(value) for value in id_batch),
            }
            try:
                batch_records = fetch_collection(token, "/v2/documents", per_page, pause, params)
            except ApiError as exc:
                errors.append(
                    {
                        "resource_type": resource_type,
                        "resource_ids": id_batch,
                        "http_status": exc.status,
                        "error": exc.body[:500] if exc.body else str(exc),
                    }
                )
                continue
            queries.append(
                {
                    "resource_type": resource_type,
                    "resource_count": len(id_batch),
                    "documents_found": len(batch_records),
                }
            )
            for record in batch_records:
                key = (
                    record.get("id"),
                    record.get("resource_type"),
                    record.get("resource_id"),
                    record.get("name"),
                    record.get("size"),
                )
                if key in seen:
                    continue
                seen.add(key)
                record_with_file = dict(record)
                if download_files and record.get("download_url"):
                    document_id = record.get("id") or len(records) + 1
                    filename = safe_filename(record.get("name"), f"document_{document_id}")
                    local_path = (
                        snapshot_dir
                        / "document_files"
                        / str(record.get("resource_type") or "unknown")
                        / str(record.get("resource_id") or "unknown")
                        / f"{document_id}_{filename}"
                    )
                    try:
                        download_binary(str(record["download_url"]), local_path)
                        record_with_file["local_file"] = local_path.relative_to(snapshot_dir).as_posix()
                        record_with_file["download_status"] = "ok"
                    except ApiError as exc:
                        record_with_file["download_status"] = "error"
                        record_with_file["download_error"] = exc.body[:500] if exc.body else str(exc)
                        errors.append(
                            {
                                "document_id": record.get("id"),
                                "resource_type": record.get("resource_type"),
                                "resource_id": record.get("resource_id"),
                                "http_status": exc.status,
                                "error": exc.body[:500] if exc.body else str(exc),
                            }
                        )
                records.append(record_with_file)

    status = "partial_error" if errors else "ok"
    return write_export_payload(
        snapshot_dir,
        "documents",
        "/v2/documents",
        records,
        started_at,
        {"download_files": download_files, "queries": queries, "errors": errors},
        status=status,
    )


def export_associated_contacts(token: str, snapshot_dir: Path, per_page: int, pause: float) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for deal_id in record_ids(read_snapshot_records(snapshot_dir, "deals")):
        endpoint = f"/v2/deals/{deal_id}/associated_contacts"
        try:
            deal_records = fetch_collection(token, endpoint, per_page, pause)
        except ApiError as exc:
            errors.append(
                {
                    "deal_id": deal_id,
                    "http_status": exc.status,
                    "error": exc.body[:500] if exc.body else str(exc),
                }
            )
            continue
        for record in deal_records:
            record_with_deal = dict(record)
            record_with_deal["deal_id"] = deal_id
            key = (deal_id, record.get("contact_id"), record.get("role"))
            if key in seen:
                continue
            seen.add(key)
            records.append(record_with_deal)

    status = "partial_error" if errors else "ok"
    return write_export_payload(
        snapshot_dir,
        "associated_contacts",
        "/v2/deals/:deal_id/associated_contacts",
        records,
        started_at,
        {"deals_checked": len(record_ids(read_snapshot_records(snapshot_dir, "deals"))), "errors": errors},
        status=status,
    )


def export_line_items(token: str, snapshot_dir: Path, per_page: int, pause: float) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    order_ids = record_ids(read_snapshot_records(snapshot_dir, "orders"))
    for order_id in order_ids:
        endpoint = f"/v2/orders/{order_id}/line_items"
        try:
            order_records = fetch_collection(token, endpoint, per_page, pause)
        except ApiError as exc:
            errors.append(
                {
                    "order_id": order_id,
                    "http_status": exc.status,
                    "error": exc.body[:500] if exc.body else str(exc),
                }
            )
            continue
        for record in order_records:
            record_with_order = dict(record)
            record_with_order["order_id"] = order_id
            key = (order_id, record.get("id"))
            if key in seen:
                continue
            seen.add(key)
            records.append(record_with_order)

    status = "partial_error" if errors else "ok"
    return write_export_payload(
        snapshot_dir,
        "line_items",
        "/v2/orders/:order_id/line_items",
        records,
        started_at,
        {"orders_checked": len(order_ids), "errors": errors},
        status=status,
    )


def write_counts_csv(snapshot_dir: Path, manifest: dict[str, Any]) -> None:
    with (snapshot_dir / "counts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "status", "count", "file", "endpoint"])
        writer.writeheader()
        for row in manifest["exports"]:
            writer.writerow(
                {
                    "name": row.get("name"),
                    "status": row.get("status"),
                    "count": row.get("count"),
                    "file": row.get("file"),
                    "endpoint": row.get("endpoint"),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a read-only Zendesk Sell snapshot.")
    parser.add_argument("--output-root", default="raw_api_exports")
    parser.add_argument("--per-page", type=int, default=100, choices=range(1, 101))
    parser.add_argument("--pause", type=float, default=0.15)
    parser.add_argument(
        "--include-extended",
        action="store_true",
        help="Also probe/export optional Sell categories such as calls, visits, documents, texts, products, orders, and sequences.",
    )
    parser.add_argument(
        "--download-documents",
        action="store_true",
        help="When used with --include-extended, download Zendesk document files into the snapshot folder while their download URLs are fresh.",
    )
    args = parser.parse_args()

    token = os.environ.get("ZENDESK_SELL_ACCESS_TOKEN")
    if not token:
        print("Missing ZENDESK_SELL_ACCESS_TOKEN.", file=sys.stderr)
        return 2

    snapshot_name = f"snapshot_{utc_stamp()}"
    snapshot_dir = Path(args.output_root) / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    try:
        account = request_json(token, "/v2/accounts/self").get("data")
        user = request_json(token, "/v2/users/self").get("data")
    except ApiError as exc:
        print(f"Could not authenticate: {exc}", file=sys.stderr)
        if exc.body:
            print(exc.body[:500], file=sys.stderr)
        return 1

    manifest: dict[str, Any] = {
        "snapshot_name": snapshot_name,
        "snapshot_dir": str(snapshot_dir),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "account": {
            "id": account.get("id"),
            "name": account.get("name"),
            "subdomain": account.get("subdomain"),
            "timezone": account.get("timezone"),
            "currency": account.get("currency"),
        },
        "authenticated_user": {
            "id": user.get("id"),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role"),
        },
        "exports": [],
        "include_extended": args.include_extended,
        "download_documents": args.download_documents,
    }

    for name, path in COLLECTIONS + CUSTOM_FIELD_ENDPOINTS:
        print(f"Exporting {name}...")
        paginated = (name, path) not in CUSTOM_FIELD_ENDPOINTS
        manifest["exports"].append(
            export_endpoint(token, snapshot_dir, name, path, args.per_page, args.pause, paginated=paginated)
        )

    for name, path in OPTIONAL_METADATA_ENDPOINTS:
        print(f"Exporting optional {name}...")
        manifest["exports"].append(
            export_endpoint(token, snapshot_dir, name, path, args.per_page, args.pause, optional=True)
        )

    if args.include_extended:
        for name, path in EXTENDED_OPTIONAL_ENDPOINTS:
            print(f"Exporting extended optional {name}...")
            manifest["exports"].append(
                export_endpoint(token, snapshot_dir, name, path, args.per_page, args.pause, optional=True)
            )
        print("Exporting extended optional documents...")
        manifest["exports"].append(
            export_documents(token, snapshot_dir, args.per_page, args.pause, args.download_documents)
        )
        print("Exporting extended optional associated_contacts...")
        manifest["exports"].append(export_associated_contacts(token, snapshot_dir, args.per_page, args.pause))
        print("Exporting extended optional line_items...")
        manifest["exports"].append(export_line_items(token, snapshot_dir, args.per_page, args.pause))

    manifest_path = snapshot_dir / "manifest.json"
    manifest["manifest_sha256"] = write_json(manifest_path, manifest)
    write_counts_csv(snapshot_dir, manifest)

    latest_path = Path(args.output_root) / "latest_snapshot.txt"
    latest_path.write_text(str(snapshot_dir.resolve()) + "\n", encoding="utf-8")

    print()
    print(f"Snapshot complete: {snapshot_dir}")
    print("Counts:")
    for row in manifest["exports"]:
        status = row["status"]
        count = row["count"]
        print(f"- {row['name']}: {count} ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
