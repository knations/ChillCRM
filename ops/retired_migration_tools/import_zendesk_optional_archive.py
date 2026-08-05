#!/usr/bin/env python3
"""Import optional Zendesk Sell records into the local CRM archive layer."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LATEST_SNAPSHOT = PROJECT_ROOT / "raw_api_exports" / "latest_snapshot.txt"
CRM_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_records(snapshot_dir: Path, name: str) -> list[dict[str, Any]]:
    path = snapshot_dir / f"{name}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("records") or []


def latest_snapshot_dir() -> Path:
    text = LATEST_SNAPSHOT.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("latest_snapshot.txt is empty.")
    path = Path(text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        raise RuntimeError(f"Snapshot not found: {path}")
    return path


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS imported_archive_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            source_collection TEXT NOT NULL,
            zendesk_record_id INTEGER,
            record_type TEXT,
            record_id INTEGER,
            related_record_type TEXT,
            related_record_id INTEGER,
            original_resource_type TEXT,
            original_resource_id INTEGER,
            title TEXT,
            body TEXT,
            direction TEXT,
            occurred_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            user_id INTEGER,
            duration_seconds INTEGER,
            phone_number TEXT,
            content_type TEXT,
            size_bytes INTEGER,
            local_file TEXT,
            url TEXT,
            status TEXT,
            source_json TEXT NOT NULL,
            UNIQUE(source_collection, zendesk_record_id)
        );

        CREATE INDEX IF NOT EXISTS idx_imported_archive_record
        ON imported_archive_items(record_type, record_id, occurred_at DESC);

        CREATE INDEX IF NOT EXISTS idx_imported_archive_type
        ON imported_archive_items(item_type, occurred_at DESC);

        CREATE INDEX IF NOT EXISTS idx_imported_archive_related
        ON imported_archive_items(related_record_type, related_record_id, occurred_at DESC);
        """
    )


def mapped_id(conn: sqlite3.Connection, local_table: str, collection: str, zendesk_id: Any) -> int | None:
    if zendesk_id is None:
        return None
    row = conn.execute(
        """
        SELECT local_id
        FROM source_map
        WHERE local_table = ? AND zendesk_collection = ? AND zendesk_id = ?
        """,
        (local_table, collection, zendesk_id),
    ).fetchone()
    return int(row["local_id"]) if row else None


def map_resource(conn: sqlite3.Connection, resource_type: Any, resource_id: Any) -> tuple[str | None, int | None]:
    if resource_type is None or resource_id is None:
        return None, None
    if resource_type == "contact":
        person_id = mapped_id(conn, "people", "contacts", resource_id)
        if person_id is not None:
            return "person", person_id
        company_id = mapped_id(conn, "companies", "contacts", resource_id)
        if company_id is not None:
            return "company", company_id
        return "contact", None
    if resource_type == "lead":
        return "lead", mapped_id(conn, "leads", "leads", resource_id)
    if resource_type == "deal":
        return "deal", mapped_id(conn, "deals", "deals", resource_id)
    return str(resource_type), None


def first_associated_deal(conn: sqlite3.Connection, record: dict[str, Any]) -> tuple[str | None, int | None]:
    for deal_id in record.get("associated_deal_ids") or []:
        local_id = mapped_id(conn, "deals", "deals", deal_id)
        if local_id is not None:
            return "deal", local_id
    return None, None


def call_outcomes(records: list[dict[str, Any]]) -> dict[int, str]:
    outcomes = {}
    for record in records:
        if record.get("id") is not None and record.get("name"):
            outcomes[int(record["id"])] = str(record["name"])
    return outcomes


def normalize_phone(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 7:
        return None
    return digits[-10:] if len(digits) >= 10 else digits


def phone_index(conn: sqlite3.Connection) -> dict[str, tuple[str, int]]:
    candidates: dict[str, list[tuple[str, int]]] = {}
    for table, record_type, fields in [
        ("people", "person", ["phone", "mobile"]),
        ("companies", "company", ["phone"]),
        ("leads", "lead", ["phone", "mobile"]),
    ]:
        field_sql = ", ".join(["id", *fields])
        for row in conn.execute(f"SELECT {field_sql} FROM {table}"):
            for field in fields:
                key = normalize_phone(row[field])
                if key:
                    candidates.setdefault(key, []).append((record_type, int(row["id"])))
    unique: dict[str, tuple[str, int]] = {}
    for key, matches in candidates.items():
        deduped = sorted(set(matches))
        if len(deduped) == 1:
            unique[key] = deduped[0]
    return unique


def map_by_phone(index: dict[str, tuple[str, int]], value: Any) -> tuple[str | None, int | None]:
    key = normalize_phone(value)
    if not key:
        return None, None
    return index.get(key, (None, None))


def sanitized_document_json(record: dict[str, Any]) -> str:
    clean = dict(record)
    clean.pop("download_url", None)
    return jdump(clean)


def upsert_item(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    fields = [
        "item_type",
        "source_collection",
        "zendesk_record_id",
        "record_type",
        "record_id",
        "related_record_type",
        "related_record_id",
        "original_resource_type",
        "original_resource_id",
        "title",
        "body",
        "direction",
        "occurred_at",
        "created_at",
        "updated_at",
        "user_id",
        "duration_seconds",
        "phone_number",
        "content_type",
        "size_bytes",
        "local_file",
        "url",
        "status",
        "source_json",
    ]
    placeholders = ", ".join("?" for _ in fields)
    updates = ", ".join(f"{field} = excluded.{field}" for field in fields if field not in {"source_collection", "zendesk_record_id"})
    conn.execute(
        f"""
        INSERT INTO imported_archive_items ({", ".join(fields)})
        VALUES ({placeholders})
        ON CONFLICT(source_collection, zendesk_record_id) DO UPDATE SET {updates}
        """,
        [item.get(field) for field in fields],
    )


def import_calls(conn: sqlite3.Connection, records: list[dict[str, Any]], outcomes: dict[int, str], phones: dict[str, tuple[str, int]]) -> int:
    count = 0
    for record in records:
        record_type, record_id = map_resource(conn, record.get("resource_type"), record.get("resource_id"))
        related_type, related_id = first_associated_deal(conn, record)
        if record_type is None:
            record_type, record_id = map_by_phone(phones, record.get("phone_number"))
        if record_type is None and related_type:
            record_type, record_id = related_type, related_id
            related_type, related_id = None, None
        direction = "Incoming" if record.get("incoming") else "Outgoing"
        outcome = outcomes.get(record.get("outcome_id"))
        missed = " missed" if record.get("missed") else ""
        title = f"{direction}{missed} call"
        if outcome:
            title = f"{title}: {outcome}"
        summary = record.get("summary") or ""
        body_parts = [summary]
        if record.get("duration") is not None:
            body_parts.append(f"Duration: {record.get('duration')} seconds")
        if record.get("phone_number"):
            body_parts.append(f"Phone: {record.get('phone_number')}")
        upsert_item(
            conn,
            {
                "item_type": "call",
                "source_collection": "calls",
                "zendesk_record_id": record.get("id"),
                "record_type": record_type,
                "record_id": record_id,
                "related_record_type": related_type,
                "related_record_id": related_id,
                "original_resource_type": record.get("resource_type"),
                "original_resource_id": record.get("resource_id"),
                "title": title,
                "body": "\n".join(part for part in body_parts if part),
                "direction": direction.lower(),
                "occurred_at": record.get("made_at") or record.get("updated_at"),
                "created_at": record.get("made_at"),
                "updated_at": record.get("updated_at"),
                "user_id": record.get("user_id"),
                "duration_seconds": record.get("duration"),
                "phone_number": record.get("phone_number"),
                "url": record.get("public_api_recording_url") or record.get("recording_url"),
                "status": "missed" if record.get("missed") else outcome,
                "source_json": jdump(record),
            },
        )
        count += 1
    return count


def import_text_messages(conn: sqlite3.Connection, records: list[dict[str, Any]], phones: dict[str, tuple[str, int]]) -> int:
    count = 0
    for record in records:
        record_type, record_id = map_resource(conn, record.get("resource_type"), record.get("resource_id"))
        related_type, related_id = first_associated_deal(conn, record)
        if record_type is None:
            record_type, record_id = map_by_phone(phones, record.get("resource_phone_number"))
        if record_type is None and related_type:
            record_type, record_id = related_type, related_id
            related_type, related_id = None, None
        direction = "Incoming" if record.get("incoming") else "Outgoing"
        phone = record.get("resource_phone_number") or record.get("user_phone_number")
        upsert_item(
            conn,
            {
                "item_type": "text_message",
                "source_collection": "text_messages",
                "zendesk_record_id": record.get("id"),
                "record_type": record_type,
                "record_id": record_id,
                "related_record_type": related_type,
                "related_record_id": related_id,
                "original_resource_type": record.get("resource_type"),
                "original_resource_id": record.get("resource_id"),
                "title": f"{direction} text message",
                "body": record.get("content"),
                "direction": direction.lower(),
                "occurred_at": record.get("sent_at") or record.get("created_at") or record.get("updated_at"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "user_id": record.get("user_id"),
                "phone_number": phone,
                "source_json": jdump(record),
            },
        )
        count += 1
    return count


def import_documents(conn: sqlite3.Connection, snapshot_dir: Path, records: list[dict[str, Any]]) -> int:
    count = 0
    for record in records:
        record_type, record_id = map_resource(conn, record.get("resource_type"), record.get("resource_id"))
        local_file = None
        if record.get("local_file"):
            local_file = (Path("raw_api_exports") / snapshot_dir.name / str(record["local_file"])).as_posix()
        size = record.get("size")
        body_parts = [record.get("content_type")]
        if size:
            body_parts.append(f"{round(float(size) / 1024)} KB")
        upsert_item(
            conn,
            {
                "item_type": "document",
                "source_collection": "documents",
                "zendesk_record_id": record.get("id"),
                "record_type": record_type,
                "record_id": record_id,
                "original_resource_type": record.get("resource_type"),
                "original_resource_id": record.get("resource_id"),
                "title": record.get("name") or f"Document #{record.get('id')}",
                "body": " · ".join(part for part in body_parts if part),
                "occurred_at": record.get("created_at") or record.get("updated_at"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "user_id": record.get("creator_id"),
                "content_type": record.get("content_type"),
                "size_bytes": record.get("size"),
                "local_file": local_file,
                "status": record.get("download_status"),
                "source_json": sanitized_document_json(record),
            },
        )
        count += 1
    return count


def import_orders(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> int:
    count = 0
    for record in records:
        deal_id = mapped_id(conn, "deals", "deals", record.get("deal_id"))
        discount = record.get("discount")
        upsert_item(
            conn,
            {
                "item_type": "order",
                "source_collection": "orders",
                "zendesk_record_id": record.get("id"),
                "record_type": "deal" if deal_id is not None else None,
                "record_id": deal_id,
                "original_resource_type": "deal",
                "original_resource_id": record.get("deal_id"),
                "title": f"Order #{record.get('id')}",
                "body": f"Discount: {discount}" if discount is not None else "",
                "occurred_at": record.get("created_at") or record.get("updated_at"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "source_json": jdump(record),
            },
        )
        count += 1
    return count


def import_lead_conversions(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> int:
    count = 0
    for record in records:
        lead_id = mapped_id(conn, "leads", "leads", record.get("lead_id"))
        person_id = mapped_id(conn, "people", "contacts", record.get("individual_id"))
        company_id = mapped_id(conn, "companies", "contacts", record.get("organization_id"))
        deal_id = mapped_id(conn, "deals", "deals", record.get("deal_id"))
        related_type, related_id = (("person", person_id) if person_id is not None else ("company", company_id) if company_id is not None else ("deal", deal_id) if deal_id is not None else (None, None))
        body_parts = []
        if person_id is not None:
            body_parts.append(f"Converted to person #{person_id}")
        if company_id is not None:
            body_parts.append(f"Converted to company #{company_id}")
        if deal_id is not None:
            body_parts.append(f"Created deal #{deal_id}")
        upsert_item(
            conn,
            {
                "item_type": "lead_conversion",
                "source_collection": "lead_conversions",
                "zendesk_record_id": record.get("id"),
                "record_type": "lead" if lead_id is not None else related_type,
                "record_id": lead_id if lead_id is not None else related_id,
                "related_record_type": related_type,
                "related_record_id": related_id,
                "original_resource_type": "lead",
                "original_resource_id": record.get("lead_id"),
                "title": "Lead converted",
                "body": " · ".join(body_parts),
                "occurred_at": record.get("created_at"),
                "created_at": record.get("created_at"),
                "user_id": record.get("creator_id"),
                "source_json": jdump(record),
            },
        )
        count += 1
    return count


def main() -> int:
    snapshot_dir = latest_snapshot_dir()
    with sqlite3.connect(CRM_DB) as conn:
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        conn.execute("DELETE FROM imported_archive_items")
        phones = phone_index(conn)
        counts = {
            "calls": import_calls(conn, load_records(snapshot_dir, "calls"), call_outcomes(load_records(snapshot_dir, "call_outcomes")), phones),
            "text_messages": import_text_messages(conn, load_records(snapshot_dir, "text_messages"), phones),
            "documents": import_documents(conn, snapshot_dir, load_records(snapshot_dir, "documents")),
            "orders": import_orders(conn, load_records(snapshot_dir, "orders")),
            "lead_conversions": import_lead_conversions(conn, load_records(snapshot_dir, "lead_conversions")),
        }
        conn.execute(
            """
            INSERT INTO local_settings (key, value, updated_at)
            VALUES ('optional_archive_snapshot', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (snapshot_dir.name,),
        )
        conn.commit()
    print(f"Imported optional archive from {snapshot_dir.name}")
    for name, count in counts.items():
        print(f"- {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
