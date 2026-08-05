#!/usr/bin/env python3
"""Build a SQLite staging database from a Zendesk Sell JSON snapshot."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


COLLECTION_FILES = [
    "users",
    "contacts",
    "leads",
    "deals",
    "notes",
    "tasks",
    "tags",
    "pipelines",
    "stages",
    "sources",
    "loss_reasons",
    "lead_custom_fields",
    "contact_custom_fields",
    "deal_custom_fields",
    "prospect_and_customer_custom_fields",
    "calls",
    "call_outcomes",
    "visits",
    "visit_outcomes",
    "text_messages",
    "documents",
    "products",
    "orders",
    "line_items",
    "sequences",
    "sequence_enrollments",
    "collaborations",
    "associated_contacts",
    "lead_conversions",
    "lead_sources",
    "deal_sources",
    "lead_unqualified_reasons",
    "deal_unqualified_reasons",
    "appointments",
]


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_records(snapshot_dir: Path, name: str) -> list[dict[str, Any]]:
    path = snapshot_dir / f"{name}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("records") or []


def latest_snapshot(root: Path) -> Path:
    latest_file = root / "raw_api_exports" / "latest_snapshot.txt"
    if latest_file.exists():
        return Path(latest_file.read_text(encoding="utf-8").strip())
    snapshots = sorted((root / "raw_api_exports").glob("snapshot_*"))
    if not snapshots:
        raise FileNotFoundError("No Zendesk Sell snapshot found.")
    return snapshots[-1]


def display_name(record: dict[str, Any]) -> str | None:
    if record.get("name"):
        return record.get("name")
    parts = [record.get("first_name"), record.get("last_name")]
    name = " ".join(str(part).strip() for part in parts if part)
    return name or record.get("organization_name")


def lower_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE snapshot_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE raw_records (
            collection TEXT NOT NULL,
            source_id INTEGER,
            name TEXT,
            created_at TEXT,
            updated_at TEXT,
            owner_id INTEGER,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (collection, source_id)
        );

        CREATE TABLE users (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            role TEXT,
            status TEXT,
            sell_login_disabled INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE contacts (
            source_id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,
            name TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            normalized_email TEXT,
            phone TEXT,
            mobile TEXT,
            owner_id INTEGER,
            creator_id INTEGER,
            parent_organization_id INTEGER,
            customer_status TEXT,
            prospect_status TEXT,
            created_at TEXT,
            updated_at TEXT,
            tags_json TEXT NOT NULL,
            custom_fields_json TEXT NOT NULL,
            address_json TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE leads (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            first_name TEXT,
            last_name TEXT,
            organization_name TEXT,
            email TEXT,
            normalized_email TEXT,
            phone TEXT,
            mobile TEXT,
            status TEXT,
            owner_id INTEGER,
            creator_id INTEGER,
            source_id_ref INTEGER,
            unqualified_reason_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            tags_json TEXT NOT NULL,
            custom_fields_json TEXT NOT NULL,
            address_json TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE deals (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL,
            currency TEXT,
            stage_id INTEGER,
            pipeline_id INTEGER,
            contact_id INTEGER,
            organization_id INTEGER,
            owner_id INTEGER,
            creator_id INTEGER,
            source_id_ref INTEGER,
            loss_reason_id INTEGER,
            unqualified_reason_id INTEGER,
            hot INTEGER,
            estimated_close_date TEXT,
            last_activity_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            tags_json TEXT NOT NULL,
            custom_fields_json TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE notes (
            source_id INTEGER PRIMARY KEY,
            resource_type TEXT,
            resource_id INTEGER,
            creator_id INTEGER,
            type TEXT,
            is_important INTEGER,
            created_at TEXT,
            updated_at TEXT,
            content TEXT,
            tags_json TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE tasks (
            source_id INTEGER PRIMARY KEY,
            resource_type TEXT,
            resource_id INTEGER,
            owner_id INTEGER,
            creator_id INTEGER,
            completed INTEGER,
            completed_at TEXT,
            due_date TEXT,
            remind_at TEXT,
            overdue INTEGER,
            content TEXT,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE tags (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            resource_type TEXT,
            creator_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE pipelines (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            disabled INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE stages (
            source_id INTEGER PRIMARY KEY,
            pipeline_id INTEGER,
            name TEXT,
            position INTEGER,
            category TEXT,
            likelihood INTEGER,
            active INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE sources (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            resource_type TEXT,
            creator_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE loss_reasons (
            source_id INTEGER PRIMARY KEY,
            name TEXT,
            creator_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE custom_field_definitions (
            resource_type TEXT NOT NULL,
            source_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            field_type TEXT,
            created_at TEXT,
            updated_at TEXT,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE custom_field_values (
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            PRIMARY KEY (record_type, record_id, field_name)
        );

        CREATE TABLE tag_assignments (
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            tag TEXT NOT NULL
        );

        CREATE INDEX idx_contacts_kind ON contacts(kind);
        CREATE INDEX idx_contacts_email ON contacts(normalized_email);
        CREATE INDEX idx_contacts_name ON contacts(name);
        CREATE INDEX idx_leads_email ON leads(normalized_email);
        CREATE INDEX idx_leads_name ON leads(name);
        CREATE INDEX idx_deals_stage ON deals(stage_id);
        CREATE INDEX idx_notes_resource ON notes(resource_type, resource_id);
        CREATE INDEX idx_tasks_resource ON tasks(resource_type, resource_id);
        CREATE INDEX idx_custom_field_values_name ON custom_field_values(field_name);
        CREATE INDEX idx_tag_assignments_tag ON tag_assignments(tag);

        CREATE VIEW companies AS
            SELECT * FROM contacts WHERE kind = 'company';

        CREATE VIEW people AS
            SELECT * FROM contacts WHERE kind = 'person';
        """
    )


def insert_raw(conn: sqlite3.Connection, collection: str, record: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO raw_records
            (collection, source_id, name, created_at, updated_at, owner_id, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            collection,
            record.get("id"),
            display_name(record),
            record.get("created_at"),
            record.get("updated_at"),
            record.get("owner_id"),
            as_json(record),
        ),
    )


def insert_tags_and_fields(
    conn: sqlite3.Connection,
    record_type: str,
    record_id: int | None,
    tags: list[Any] | None,
    custom_fields: dict[str, Any] | None,
) -> None:
    if record_id is None:
        return
    for tag in tags or []:
        conn.execute(
            "INSERT INTO tag_assignments (record_type, record_id, tag) VALUES (?, ?, ?)",
            (record_type, record_id, str(tag)),
        )
    for field_name, field_value in (custom_fields or {}).items():
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_field_values
                (record_type, record_id, field_name, field_value)
            VALUES (?, ?, ?, ?)
            """,
            (record_type, record_id, str(field_name), None if field_value is None else str(field_value)),
        )


def populate(conn: sqlite3.Connection, snapshot_dir: Path) -> None:
    manifest_path = snapshot_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ["snapshot_name", "created_at", "base_url"]:
            conn.execute("INSERT INTO snapshot_info (key, value) VALUES (?, ?)", (key, manifest.get(key)))
        conn.execute("INSERT INTO snapshot_info (key, value) VALUES (?, ?)", ("manifest_json", as_json(manifest)))

    loaded: dict[str, list[dict[str, Any]]] = {
        name: load_records(snapshot_dir, name) for name in COLLECTION_FILES
    }

    for collection, records in loaded.items():
        for record in records:
            insert_raw(conn, collection, record)

    for record in loaded["users"]:
        conn.execute(
            """
            INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("id"),
                record.get("name"),
                record.get("email"),
                record.get("role"),
                record.get("status"),
                1 if record.get("sell_login_disabled") else 0,
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record),
            ),
        )

    for record in loaded["contacts"]:
        kind = "company" if record.get("is_organization") else "person"
        conn.execute(
            """
            INSERT INTO contacts VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                record.get("id"),
                kind,
                display_name(record),
                record.get("first_name"),
                record.get("last_name"),
                record.get("email"),
                lower_or_none(record.get("email")),
                record.get("phone"),
                record.get("mobile"),
                record.get("owner_id"),
                record.get("creator_id"),
                record.get("parent_organization_id") or record.get("contact_id"),
                record.get("customer_status"),
                record.get("prospect_status"),
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record.get("tags") or []),
                as_json(record.get("custom_fields") or {}),
                as_json(record.get("address") or {}),
                as_json(record),
            ),
        )
        insert_tags_and_fields(
            conn, "contact", record.get("id"), record.get("tags"), record.get("custom_fields")
        )

    for record in loaded["leads"]:
        conn.execute(
            """
            INSERT INTO leads VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                record.get("id"),
                display_name(record),
                record.get("first_name"),
                record.get("last_name"),
                record.get("organization_name"),
                record.get("email"),
                lower_or_none(record.get("email")),
                record.get("phone"),
                record.get("mobile"),
                record.get("status"),
                record.get("owner_id"),
                record.get("creator_id"),
                record.get("source_id"),
                record.get("unqualified_reason_id"),
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record.get("tags") or []),
                as_json(record.get("custom_fields") or {}),
                as_json(record.get("address") or {}),
                as_json(record),
            ),
        )
        insert_tags_and_fields(conn, "lead", record.get("id"), record.get("tags"), record.get("custom_fields"))

    for record in loaded["deals"]:
        conn.execute(
            """
            INSERT INTO deals VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                record.get("id"),
                record.get("name"),
                record.get("value"),
                record.get("currency"),
                record.get("stage_id"),
                None,
                record.get("contact_id"),
                record.get("organization_id"),
                record.get("owner_id"),
                record.get("creator_id"),
                record.get("source_id"),
                record.get("loss_reason_id"),
                record.get("unqualified_reason_id"),
                1 if record.get("hot") else 0,
                record.get("estimated_close_date"),
                record.get("last_activity_at"),
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record.get("tags") or []),
                as_json(record.get("custom_fields") or {}),
                as_json(record),
            ),
        )
        insert_tags_and_fields(conn, "deal", record.get("id"), record.get("tags"), record.get("custom_fields"))

    for record in loaded["notes"]:
        conn.execute(
            """
            INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("id"),
                record.get("resource_type"),
                record.get("resource_id"),
                record.get("creator_id"),
                record.get("type"),
                1 if record.get("is_important") else 0,
                record.get("created_at"),
                record.get("updated_at"),
                record.get("content"),
                as_json(record.get("tags") or []),
                as_json(record),
            ),
        )
        insert_tags_and_fields(conn, "note", record.get("id"), record.get("tags"), None)

    for record in loaded["tasks"]:
        conn.execute(
            """
            INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("id"),
                record.get("resource_type"),
                record.get("resource_id"),
                record.get("owner_id"),
                record.get("creator_id"),
                1 if record.get("completed") else 0,
                record.get("completed_at"),
                record.get("due_date"),
                record.get("remind_at"),
                1 if record.get("overdue") else 0,
                record.get("content"),
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record),
            ),
        )

    for table_name in ["tags", "sources"]:
        for record in loaded[table_name]:
            conn.execute(
                f"""
                INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("id"),
                    record.get("name"),
                    record.get("resource_type") if table_name != "loss_reasons" else record.get("creator_id"),
                    record.get("creator_id") if table_name != "loss_reasons" else record.get("created_at"),
                    record.get("created_at") if table_name != "loss_reasons" else record.get("updated_at"),
                    record.get("updated_at") if table_name != "loss_reasons" else as_json(record),
                    as_json(record) if table_name != "loss_reasons" else None,
                )
            )

    for record in loaded["loss_reasons"]:
        conn.execute(
            "INSERT INTO loss_reasons VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("id"),
                record.get("name"),
                record.get("creator_id"),
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record),
            ),
        )

    for record in loaded["pipelines"]:
        conn.execute(
            "INSERT INTO pipelines VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.get("id"),
                record.get("name"),
                1 if record.get("disabled") else 0,
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record),
            ),
        )

    stage_to_pipeline: dict[int, int] = {}
    for record in loaded["stages"]:
        stage_to_pipeline[record.get("id")] = record.get("pipeline_id")
        conn.execute(
            "INSERT INTO stages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.get("id"),
                record.get("pipeline_id"),
                record.get("name"),
                record.get("position"),
                record.get("category"),
                record.get("likelihood"),
                1 if record.get("active") else 0,
                record.get("created_at"),
                record.get("updated_at"),
                as_json(record),
            ),
        )

    for deal_id, stage_id in conn.execute("SELECT source_id, stage_id FROM deals").fetchall():
        conn.execute(
            "UPDATE deals SET pipeline_id = ? WHERE source_id = ?",
            (stage_to_pipeline.get(stage_id), deal_id),
        )

    custom_field_sources = [
        ("lead", loaded["lead_custom_fields"]),
        ("contact", loaded["contact_custom_fields"]),
        ("deal", loaded["deal_custom_fields"]),
        ("prospect_and_customer", loaded["prospect_and_customer_custom_fields"]),
    ]
    for resource_type, records in custom_field_sources:
        for record in records:
            conn.execute(
                "INSERT INTO custom_field_definitions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    resource_type,
                    record.get("id"),
                    record.get("name"),
                    record.get("type"),
                    record.get("created_at"),
                    record.get("updated_at"),
                    as_json(record),
                ),
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SQLite staging database from Zendesk Sell snapshot.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--snapshot-dir")
    parser.add_argument("--db-path", default="staging_database/zendesk_sell_staging.sqlite")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    snapshot_dir = Path(args.snapshot_dir).resolve() if args.snapshot_dir else latest_snapshot(project_root)
    db_path = (project_root / args.db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        create_schema(conn)
        populate(conn, snapshot_dir)
        conn.commit()
    finally:
        conn.close()

    print(f"Built staging database: {db_path}")
    print(f"Source snapshot: {snapshot_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
