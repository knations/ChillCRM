#!/usr/bin/env python3
"""Export local CRM tables to CSV files."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "exports"

sys.path.insert(0, str(PROJECT_ROOT))
import crm_app.server as crm_server  # noqa: E402


EXPORTS = {
    "people": "SELECT id, zendesk_contact_id, company_id, name, first_name, last_name, email, phone, mobile, title, customer_status, prospect_status, created_at, updated_at FROM people ORDER BY name COLLATE NOCASE",
    "companies": "SELECT id, zendesk_contact_id, name, email, phone, website, customer_status, prospect_status, created_at, updated_at FROM companies ORDER BY name COLLATE NOCASE",
    "leads": "SELECT id, zendesk_lead_id, possible_person_id, name, first_name, last_name, organization_name, email, phone, mobile, status, created_at, updated_at FROM leads ORDER BY updated_at DESC",
    "deals": "SELECT d.id, d.zendesk_deal_id, d.name, d.value, d.currency, s.name AS stage, p.name AS person, c.name AS company, d.hot, d.estimated_close_date, d.created_at, d.updated_at FROM deals d LEFT JOIN stages s ON s.id = d.stage_id LEFT JOIN people p ON p.id = d.person_id LEFT JOIN companies c ON c.id = d.company_id ORDER BY d.updated_at DESC",
    "tasks": "SELECT id, record_type, record_id, content, completed, completed_at, due_date, remind_at, created_at, updated_at FROM tasks ORDER BY updated_at DESC",
    "notes": "SELECT id, record_type, record_id, content, note_type, is_important, created_at, updated_at FROM notes ORDER BY created_at DESC",
    "addresses": None,
    "application_profiles": None,
    "custom_field_definitions": "SELECT id, zendesk_field_id, resource_type, name, field_type, created_at, updated_at FROM custom_field_definitions ORDER BY resource_type, name COLLATE NOCASE",
    "custom_field_values": "SELECT id, record_type, record_id, field_name, field_value FROM custom_field_values ORDER BY record_type, field_name, record_id",
    "tags": "SELECT id, normalized_name, display_name, definition_count FROM tags ORDER BY display_name COLLATE NOCASE",
    "tag_assignments": "SELECT ta.id, t.display_name AS tag, t.normalized_name, ta.record_type, ta.record_id, ta.source_name FROM tag_assignments ta JOIN tags t ON t.id = ta.tag_id ORDER BY t.display_name COLLATE NOCASE, ta.record_type, ta.record_id",
    "review_flags": "SELECT id, flag_type, severity, record_type, record_id, related_record_type, related_record_id, flag_key, description, status, created_at, resolved_at, resolution_note FROM review_flags ORDER BY status, severity, created_at DESC",
    "audit_log": "SELECT id, action, record_type, record_id, field_name, old_value, new_value, note, created_at FROM audit_log ORDER BY created_at DESC",
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def export_table(conn: sqlite3.Connection, db_path: Path, output_dir: Path, export_type: str) -> Path:
    if export_type in {"addresses", "application_profiles"}:
        handler = crm_server.CRMRequestHandler.__new__(crm_server.CRMRequestHandler)
        handler.db_path = db_path
        rows = handler.export_address_rows() if export_type == "addresses" else handler.export_application_profile_rows()
    else:
        query = EXPORTS[export_type]
        if query is None:
            raise ValueError(f"Missing export query for {export_type}.")
        rows = [dict(row) for row in conn.execute(query).fetchall()]
    output_path = output_dir / f"local_crm_{export_type}.csv"
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["result"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export local CRM data to CSV.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--only", choices=sorted(EXPORTS), action="append")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    output_dir = Path(args.output_root) / f"local_crm_exports_{stamp()}"
    output_dir.mkdir(parents=True, exist_ok=False)

    crm_server.ensure_runtime_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        selected = args.only or sorted(EXPORTS)
        for export_type in selected:
            path = export_table(conn, db_path, output_dir, export_type)
            print(path)
    finally:
        conn.close()

    (Path(args.output_root) / "latest_export.txt").write_text(str(output_dir.resolve()) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
