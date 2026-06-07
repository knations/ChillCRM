#!/usr/bin/env python3
"""Create the final local CRM database from the Zendesk Sell staging database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def jload(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def bool_int(value: Any) -> int:
    return 1 if value else 0


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE migration_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            zendesk_user_id INTEGER UNIQUE,
            name TEXT,
            email TEXT,
            role TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_contact_id INTEGER UNIQUE,
            name TEXT,
            normalized_name TEXT,
            email TEXT,
            normalized_email TEXT,
            phone TEXT,
            website TEXT,
            owner_user_id INTEGER,
            customer_status TEXT,
            prospect_status TEXT,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_contact_id INTEGER UNIQUE,
            company_id INTEGER REFERENCES companies(id),
            first_name TEXT,
            last_name TEXT,
            name TEXT,
            normalized_name TEXT,
            email TEXT,
            normalized_email TEXT,
            phone TEXT,
            mobile TEXT,
            title TEXT,
            owner_user_id INTEGER,
            customer_status TEXT,
            prospect_status TEXT,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_lead_id INTEGER UNIQUE,
            possible_person_id INTEGER REFERENCES people(id),
            first_name TEXT,
            last_name TEXT,
            name TEXT,
            normalized_name TEXT,
            organization_name TEXT,
            email TEXT,
            normalized_email TEXT,
            phone TEXT,
            mobile TEXT,
            status TEXT,
            source_id INTEGER,
            unqualified_reason_id INTEGER,
            owner_user_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_pipeline_id INTEGER UNIQUE,
            name TEXT,
            disabled INTEGER,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_stage_id INTEGER UNIQUE,
            pipeline_id INTEGER REFERENCES pipelines(id),
            name TEXT,
            position INTEGER,
            category TEXT,
            likelihood INTEGER,
            active INTEGER,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_deal_id INTEGER UNIQUE,
            person_id INTEGER REFERENCES people(id),
            company_id INTEGER REFERENCES companies(id),
            pipeline_id INTEGER REFERENCES pipelines(id),
            stage_id INTEGER REFERENCES stages(id),
            name TEXT,
            value REAL,
            currency TEXT,
            source_id INTEGER,
            loss_reason_id INTEGER,
            unqualified_reason_id INTEGER,
            hot INTEGER,
            estimated_close_date TEXT,
            last_activity_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_note_id INTEGER UNIQUE,
            record_type TEXT,
            record_id INTEGER,
            creator_user_id INTEGER,
            content TEXT,
            note_type TEXT,
            is_important INTEGER,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_task_id INTEGER UNIQUE,
            record_type TEXT,
            record_id INTEGER,
            owner_user_id INTEGER,
            creator_user_id INTEGER,
            content TEXT,
            completed INTEGER,
            completed_at TEXT,
            due_date TEXT,
            remind_at TEXT,
            overdue INTEGER,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_name TEXT UNIQUE,
            display_name TEXT,
            definition_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE tag_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL REFERENCES tags(id),
            zendesk_tag_id INTEGER,
            source_name TEXT,
            resource_type TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE tag_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL REFERENCES tags(id),
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            source_name TEXT
        );

        CREATE TABLE custom_field_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zendesk_field_id INTEGER UNIQUE,
            resource_type TEXT NOT NULL,
            name TEXT NOT NULL,
            field_type TEXT,
            created_at TEXT,
            updated_at TEXT,
            source_json TEXT NOT NULL
        );

        CREATE TABLE custom_field_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT
        );

        CREATE TABLE source_map (
            local_table TEXT NOT NULL,
            local_id INTEGER NOT NULL,
            zendesk_collection TEXT NOT NULL,
            zendesk_id INTEGER NOT NULL,
            PRIMARY KEY (local_table, local_id, zendesk_collection, zendesk_id)
        );

        CREATE TABLE review_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_id INTEGER,
            related_record_type TEXT,
            related_record_id INTEGER,
            flag_key TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_people_email ON people(normalized_email);
        CREATE INDEX idx_people_company ON people(company_id);
        CREATE INDEX idx_companies_name ON companies(normalized_name);
        CREATE INDEX idx_leads_email ON leads(normalized_email);
        CREATE INDEX idx_deals_stage ON deals(stage_id);
        CREATE INDEX idx_notes_record ON notes(record_type, record_id);
        CREATE INDEX idx_tasks_record ON tasks(record_type, record_id);
        CREATE INDEX idx_tag_assignments_record ON tag_assignments(record_type, record_id);
        CREATE INDEX idx_custom_field_values_record ON custom_field_values(record_type, record_id);
        CREATE INDEX idx_review_flags_status ON review_flags(status, flag_type);
        """
    )


def insert_source_map(conn: sqlite3.Connection, table: str, local_id: int, collection: str, zendesk_id: int | None) -> None:
    if zendesk_id is None:
        return
    conn.execute(
        """
        INSERT OR REPLACE INTO source_map (local_table, local_id, zendesk_collection, zendesk_id)
        VALUES (?, ?, ?, ?)
        """,
        (table, local_id, collection, zendesk_id),
    )


def mapped_id(conn: sqlite3.Connection, local_table: str, collection: str, zendesk_id: int | None) -> int | None:
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
    return row["local_id"] if row else None


def add_flag(
    conn: sqlite3.Connection,
    flag_type: str,
    severity: str,
    record_type: str,
    record_id: int | None,
    description: str,
    related_record_type: str | None = None,
    related_record_id: int | None = None,
    flag_key: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO review_flags (
            flag_type, severity, record_type, record_id, related_record_type,
            related_record_id, flag_key, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            flag_type,
            severity,
            record_type,
            record_id,
            related_record_type,
            related_record_id,
            flag_key,
            description,
        ),
    )


def migrate_users(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM users ORDER BY source_id"):
        dst.execute(
            """
            INSERT INTO users (zendesk_user_id, name, email, role, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                row["name"],
                row["email"],
                row["role"],
                row["status"],
                row["created_at"],
                row["updated_at"],
            ),
        )
        insert_source_map(dst, "users", dst.execute("SELECT last_insert_rowid()").fetchone()[0], "users", row["source_id"])


def migrate_companies(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM contacts WHERE kind = 'company' ORDER BY source_id"):
        raw = jload(row["raw_json"], {})
        dst.execute(
            """
            INSERT INTO companies (
                zendesk_contact_id, name, normalized_name, email, normalized_email,
                phone, website, owner_user_id, customer_status, prospect_status,
                created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                row["name"],
                normalize_text(row["name"]),
                row["email"],
                row["normalized_email"],
                row["phone"],
                raw.get("website"),
                row["owner_id"],
                row["customer_status"],
                row["prospect_status"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        insert_source_map(dst, "companies", dst.execute("SELECT last_insert_rowid()").fetchone()[0], "contacts", row["source_id"])


def migrate_people(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM contacts WHERE kind = 'person' ORDER BY source_id"):
        raw = jload(row["raw_json"], {})
        company_id = mapped_id(dst, "companies", "contacts", row["parent_organization_id"])
        if row["parent_organization_id"] and company_id is None:
            add_flag(
                dst,
                "missing_company_mapping",
                "medium",
                "person",
                None,
                f"Person {row['name']} references missing Zendesk company {row['parent_organization_id']}.",
                flag_key=str(row["parent_organization_id"]),
            )
        dst.execute(
            """
            INSERT INTO people (
                zendesk_contact_id, company_id, first_name, last_name, name, normalized_name,
                email, normalized_email, phone, mobile, title, owner_user_id,
                customer_status, prospect_status, created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                company_id,
                row["first_name"],
                row["last_name"],
                row["name"],
                normalize_text(row["name"]),
                row["email"],
                row["normalized_email"],
                row["phone"],
                row["mobile"],
                raw.get("title"),
                row["owner_id"],
                row["customer_status"],
                row["prospect_status"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        local_id = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        insert_source_map(dst, "people", local_id, "contacts", row["source_id"])


def migrate_pipeline(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM pipelines ORDER BY source_id"):
        dst.execute(
            """
            INSERT INTO pipelines (zendesk_pipeline_id, name, disabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row["source_id"], row["name"], row["disabled"], row["created_at"], row["updated_at"]),
        )
        insert_source_map(dst, "pipelines", dst.execute("SELECT last_insert_rowid()").fetchone()[0], "pipelines", row["source_id"])

    for row in src.execute("SELECT * FROM stages ORDER BY position"):
        pipeline_id = mapped_id(dst, "pipelines", "pipelines", row["pipeline_id"])
        dst.execute(
            """
            INSERT INTO stages (
                zendesk_stage_id, pipeline_id, name, position, category, likelihood,
                active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                pipeline_id,
                row["name"],
                row["position"],
                row["category"],
                row["likelihood"],
                row["active"],
                row["created_at"],
                row["updated_at"],
            ),
        )
        insert_source_map(dst, "stages", dst.execute("SELECT last_insert_rowid()").fetchone()[0], "stages", row["source_id"])


def migrate_leads(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM leads ORDER BY source_id"):
        possible_person_id = None
        if row["normalized_email"]:
            person = dst.execute(
                "SELECT id FROM people WHERE normalized_email = ? ORDER BY updated_at DESC, id LIMIT 1",
                (row["normalized_email"],),
            ).fetchone()
            possible_person_id = person["id"] if person else None
        dst.execute(
            """
            INSERT INTO leads (
                zendesk_lead_id, possible_person_id, first_name, last_name, name, normalized_name,
                organization_name, email, normalized_email, phone, mobile, status, source_id,
                unqualified_reason_id, owner_user_id, created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                possible_person_id,
                row["first_name"],
                row["last_name"],
                row["name"],
                normalize_text(row["name"]),
                row["organization_name"],
                row["email"],
                row["normalized_email"],
                row["phone"],
                row["mobile"],
                row["status"],
                row["source_id_ref"],
                row["unqualified_reason_id"],
                row["owner_id"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        local_id = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        insert_source_map(dst, "leads", local_id, "leads", row["source_id"])
        if possible_person_id:
            add_flag(
                dst,
                "lead_person_email_overlap",
                "medium",
                "lead",
                local_id,
                f"Lead {row['name']} has the same email as an existing person.",
                related_record_type="person",
                related_record_id=possible_person_id,
                flag_key=row["normalized_email"],
            )


def migrate_deals(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM deals ORDER BY source_id"):
        person_id = mapped_id(dst, "people", "contacts", row["contact_id"])
        company_id = mapped_id(dst, "companies", "contacts", row["organization_id"])
        pipeline_id = mapped_id(dst, "pipelines", "pipelines", row["pipeline_id"])
        stage_id = mapped_id(dst, "stages", "stages", row["stage_id"])
        dst.execute(
            """
            INSERT INTO deals (
                zendesk_deal_id, person_id, company_id, pipeline_id, stage_id, name, value,
                currency, source_id, loss_reason_id, unqualified_reason_id, hot,
                estimated_close_date, last_activity_at, created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                person_id,
                company_id,
                pipeline_id,
                stage_id,
                row["name"],
                row["value"],
                row["currency"],
                row["source_id_ref"],
                row["loss_reason_id"],
                row["unqualified_reason_id"],
                row["hot"],
                row["estimated_close_date"],
                row["last_activity_at"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        local_id = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        insert_source_map(dst, "deals", local_id, "deals", row["source_id"])
        if row["contact_id"] and person_id is None:
            add_flag(dst, "missing_deal_person", "high", "deal", local_id, f"Deal {row['name']} references missing Zendesk contact {row['contact_id']}.")
        if row["organization_id"] and company_id is None:
            add_flag(dst, "missing_deal_company", "high", "deal", local_id, f"Deal {row['name']} references missing Zendesk organization {row['organization_id']}.")


def map_resource(dst: sqlite3.Connection, resource_type: str | None, resource_id: int | None) -> tuple[str | None, int | None]:
    if resource_type is None or resource_id is None:
        return None, None
    if resource_type == "contact":
        person_id = mapped_id(dst, "people", "contacts", resource_id)
        if person_id is not None:
            return "person", person_id
        company_id = mapped_id(dst, "companies", "contacts", resource_id)
        if company_id is not None:
            return "company", company_id
        return "contact", None
    if resource_type == "deal":
        return "deal", mapped_id(dst, "deals", "deals", resource_id)
    if resource_type == "lead":
        return "lead", mapped_id(dst, "leads", "leads", resource_id)
    return resource_type, None


def migrate_notes_and_tasks(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM notes ORDER BY source_id"):
        record_type, record_id = map_resource(dst, row["resource_type"], row["resource_id"])
        dst.execute(
            """
            INSERT INTO notes (
                zendesk_note_id, record_type, record_id, creator_user_id, content,
                note_type, is_important, created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                record_type,
                record_id,
                row["creator_id"],
                row["content"],
                row["type"],
                row["is_important"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        local_id = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        insert_source_map(dst, "notes", local_id, "notes", row["source_id"])
        if row["resource_id"] and record_id is None:
            add_flag(dst, "missing_note_resource", "medium", "note", local_id, f"Note references missing {row['resource_type']} {row['resource_id']}.")

    for row in src.execute("SELECT * FROM tasks ORDER BY source_id"):
        record_type, record_id = map_resource(dst, row["resource_type"], row["resource_id"])
        dst.execute(
            """
            INSERT INTO tasks (
                zendesk_task_id, record_type, record_id, owner_user_id, creator_user_id,
                content, completed, completed_at, due_date, remind_at, overdue,
                created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                record_type,
                record_id,
                row["owner_id"],
                row["creator_id"],
                row["content"],
                row["completed"],
                row["completed_at"],
                row["due_date"],
                row["remind_at"],
                row["overdue"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )
        local_id = dst.execute("SELECT last_insert_rowid()").fetchone()[0]
        insert_source_map(dst, "tasks", local_id, "tasks", row["source_id"])
        if row["resource_id"] and record_id is None:
            add_flag(dst, "missing_task_resource", "medium", "task", local_id, f"Task references missing {row['resource_type']} {row['resource_id']}.")


def ensure_tag(dst: sqlite3.Connection, tag_name: str) -> int:
    normalized = normalize_text(tag_name)
    if not normalized:
        normalized = "(blank)"
    row = dst.execute("SELECT id FROM tags WHERE normalized_name = ?", (normalized,)).fetchone()
    if row:
        return row["id"]
    dst.execute(
        "INSERT INTO tags (normalized_name, display_name, definition_count) VALUES (?, ?, 0)",
        (normalized, tag_name.strip() if tag_name else normalized),
    )
    return dst.execute("SELECT last_insert_rowid()").fetchone()[0]


def migrate_tags(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    tag_counts: dict[int, int] = {}
    for row in src.execute("SELECT * FROM tags ORDER BY lower(name), source_id"):
        tag_id = ensure_tag(dst, row["name"] or "")
        tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1
        dst.execute(
            """
            INSERT INTO tag_aliases (
                tag_id, zendesk_tag_id, source_name, resource_type, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tag_id, row["source_id"], row["name"], row["resource_type"], row["created_at"], row["updated_at"]),
        )

    for tag_id, count in tag_counts.items():
        dst.execute("UPDATE tags SET definition_count = ? WHERE id = ?", (count, tag_id))
        if count > 1:
            tag = dst.execute("SELECT display_name FROM tags WHERE id = ?", (tag_id,)).fetchone()
            add_flag(dst, "duplicate_tag_definition", "low", "tag", tag_id, f"Tag '{tag['display_name']}' has {count} Zendesk definitions.")

    assignments = src.execute("SELECT record_type, record_id, tag FROM tag_assignments ORDER BY record_type, record_id").fetchall()
    for row in assignments:
        tag_id = ensure_tag(dst, row["tag"])
        local_type, local_id = map_assignment_record(dst, row["record_type"], row["record_id"])
        if local_id is None:
            add_flag(dst, "missing_tag_record", "medium", row["record_type"], None, f"Tag assignment references missing {row['record_type']} {row['record_id']}.", flag_key=row["tag"])
            continue
        dst.execute(
            "INSERT INTO tag_assignments (tag_id, record_type, record_id, source_name) VALUES (?, ?, ?, ?)",
            (tag_id, local_type, local_id, row["tag"]),
        )


def map_assignment_record(dst: sqlite3.Connection, record_type: str, record_id: int) -> tuple[str, int | None]:
    if record_type == "contact":
        person_id = mapped_id(dst, "people", "contacts", record_id)
        if person_id is not None:
            return "person", person_id
        return "company", mapped_id(dst, "companies", "contacts", record_id)
    if record_type == "lead":
        return "lead", mapped_id(dst, "leads", "leads", record_id)
    if record_type == "deal":
        return "deal", mapped_id(dst, "deals", "deals", record_id)
    if record_type == "note":
        return "note", mapped_id(dst, "notes", "notes", record_id)
    return record_type, None


def migrate_custom_fields(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    for row in src.execute("SELECT * FROM custom_field_definitions ORDER BY resource_type, source_id"):
        dst.execute(
            """
            INSERT INTO custom_field_definitions (
                zendesk_field_id, resource_type, name, field_type, created_at, updated_at, source_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["source_id"],
                row["resource_type"],
                row["name"],
                row["field_type"],
                row["created_at"],
                row["updated_at"],
                row["raw_json"],
            ),
        )

    for row in src.execute("SELECT * FROM custom_field_values ORDER BY record_type, record_id, field_name"):
        local_type, local_id = map_assignment_record(dst, row["record_type"], row["record_id"])
        if local_id is None:
            add_flag(dst, "missing_custom_field_record", "medium", row["record_type"], None, f"Custom field references missing {row['record_type']} {row['record_id']}.", flag_key=row["field_name"])
            continue
        dst.execute(
            """
            INSERT INTO custom_field_values (record_type, record_id, field_name, field_value)
            VALUES (?, ?, ?, ?)
            """,
            (local_type, local_id, row["field_name"], row["field_value"]),
        )


def create_review_flags(dst: sqlite3.Connection) -> None:
    for row in dst.execute(
        """
        SELECT normalized_email, count(*) AS count
        FROM people
        WHERE normalized_email IS NOT NULL
        GROUP BY normalized_email
        HAVING count(*) > 1
        """
    ):
        people = dst.execute("SELECT id, name FROM people WHERE normalized_email = ? ORDER BY updated_at DESC, id", (row["normalized_email"],)).fetchall()
        primary = people[0]["id"]
        for person in people[1:]:
            add_flag(
                dst,
                "duplicate_person_email",
                "medium",
                "person",
                person["id"],
                f"Person {person['name']} shares email {row['normalized_email']} with another person.",
                related_record_type="person",
                related_record_id=primary,
                flag_key=row["normalized_email"],
            )

    for row in dst.execute(
        """
        SELECT normalized_email, count(*) AS count
        FROM leads
        WHERE normalized_email IS NOT NULL
        GROUP BY normalized_email
        HAVING count(*) > 1
        """
    ):
        leads = dst.execute("SELECT id, name FROM leads WHERE normalized_email = ? ORDER BY updated_at DESC, id", (row["normalized_email"],)).fetchall()
        primary = leads[0]["id"]
        for lead in leads[1:]:
            add_flag(
                dst,
                "duplicate_lead_email",
                "low",
                "lead",
                lead["id"],
                f"Lead {lead['name']} shares email {row['normalized_email']} with another lead.",
                related_record_type="lead",
                related_record_id=primary,
                flag_key=row["normalized_email"],
            )


def write_summary(dst: sqlite3.Connection, report_path: Path, db_path: Path) -> None:
    count_rows = [
        ("Users", "users"),
        ("Companies", "companies"),
        ("People", "people"),
        ("Leads", "leads"),
        ("Deals", "deals"),
        ("Notes", "notes"),
        ("Tasks", "tasks"),
        ("Tags", "tags"),
        ("Tag Assignments", "tag_assignments"),
        ("Custom Field Values", "custom_field_values"),
        ("Review Flags", "review_flags"),
    ]
    counts = [(label, dst.execute(f"SELECT count(*) FROM {table}").fetchone()[0]) for label, table in count_rows]
    flag_counts = dst.execute(
        """
        SELECT flag_type, severity, count(*) AS count
        FROM review_flags
        GROUP BY flag_type, severity
        ORDER BY severity DESC, flag_type
        """
    ).fetchall()
    stage_rows = dst.execute(
        """
        SELECT s.position, s.name, s.category, count(d.id) AS deal_count, coalesce(round(sum(d.value), 2), 0) AS total_value
        FROM stages s
        LEFT JOIN deals d ON d.stage_id = s.id
        GROUP BY s.id
        ORDER BY s.position
        """
    ).fetchall()

    def table(headers: list[str], data: list[tuple[Any, ...]]) -> str:
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in data:
            lines.append("| " + " | ".join(str(value) if value is not None else "" for value in row) + " |")
        return "\n".join(lines)

    lines = [
        "# Local CRM Migration Summary",
        "",
        f"Database: `{db_path}`",
        "",
        "## Counts",
        "",
        table(["Object", "Count"], counts),
        "",
        "## Review Flags",
        "",
        table(["Flag Type", "Severity", "Count"], [(row["flag_type"], row["severity"], row["count"]) for row in flag_counts]),
        "",
        "## Deal Pipeline",
        "",
        table(["Position", "Stage", "Category", "Deals", "Total Value"], [(row["position"], row["name"], row["category"], row["deal_count"], row["total_value"]) for row in stage_rows]),
        "",
        "## Migration Rules",
        "",
        "See `docs/migration_rules.md`.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def migrate(staging_path: Path, output_path: Path, report_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    src = sqlite3.connect(staging_path)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(output_path)
    dst.row_factory = sqlite3.Row
    try:
        create_schema(dst)
        dst.execute("INSERT INTO migration_info (key, value) VALUES (?, ?)", ("source_staging_db", str(staging_path)))
        snapshot = src.execute("SELECT value FROM snapshot_info WHERE key = 'snapshot_name'").fetchone()
        if snapshot:
            dst.execute("INSERT INTO migration_info (key, value) VALUES (?, ?)", ("snapshot_name", snapshot["value"]))

        migrate_users(src, dst)
        migrate_companies(src, dst)
        migrate_people(src, dst)
        migrate_pipeline(src, dst)
        migrate_leads(src, dst)
        migrate_deals(src, dst)
        migrate_notes_and_tasks(src, dst)
        migrate_tags(src, dst)
        migrate_custom_fields(src, dst)
        create_review_flags(dst)
        dst.commit()
        write_summary(dst, report_path, output_path)
    finally:
        src.close()
        dst.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate staging database to final local CRM database.")
    parser.add_argument("--staging-db", default="staging_database/zendesk_sell_staging.sqlite")
    parser.add_argument("--output-db", default="crm_database/local_crm.sqlite")
    parser.add_argument("--summary", default="reports/local_crm_migration_summary.md")
    args = parser.parse_args()

    staging_path = Path(args.staging_db).resolve()
    output_path = Path(args.output_db).resolve()
    report_path = Path(args.summary).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    migrate(staging_path, output_path, report_path)
    print(f"Built local CRM database: {output_path}")
    print(f"Wrote migration summary: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
