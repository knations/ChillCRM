#!/usr/bin/env python3
"""Verify narrow automation Person endpoints without production writes."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.index import handler
from crm_app.server import DEFAULT_DB, ensure_runtime_schema


TOKEN = "unit-test-automation-token"


def first_person_id(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM people ORDER BY id LIMIT 1").fetchone()
    assert row is not None
    return int(row[0])


def first_owner(db_path: Path) -> tuple[int, str]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, display_name FROM app_users WHERE status = 'active' ORDER BY id LIMIT 1"
        ).fetchone()
    assert row is not None
    return int(row[0]), str(row[1])


def task_count_for_person(db_path: Path, person_id: int, content: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                "SELECT count(*) FROM tasks WHERE record_type = 'person' AND record_id = ? AND content = ?",
                (person_id, content),
            ).fetchone()[0]
        )


def task_source_for_person(db_path: Path, person_id: int, content: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT source_json FROM tasks WHERE record_type = 'person' AND record_id = ? AND content = ? ORDER BY id DESC LIMIT 1",
            (person_id, content),
        ).fetchone()
    assert row is not None
    return json.loads(row[0] or "{}")


def task_count_for_owner(db_path: Path, owner_id: int, content: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                "SELECT count(*) FROM tasks WHERE record_type = 'owner' AND record_id = ? AND content = ?",
                (owner_id, content),
            ).fetchone()[0]
        )


def task_source_for_owner(db_path: Path, owner_id: int, content: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT source_json FROM tasks WHERE record_type = 'owner' AND record_id = ? AND content = ? ORDER BY id DESC LIMIT 1",
            (owner_id, content),
        ).fetchone()
    assert row is not None
    return json.loads(row[0] or "{}")


def note_count_for_person(db_path: Path, person_id: int, content: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                """
                SELECT count(*)
                FROM notes
                WHERE record_type = 'person'
                  AND record_id = ?
                  AND content = ?
                  AND coalesce(note_type, '') != 'call_log'
                """,
                (person_id, content),
            ).fetchone()[0]
        )


def call_count_for_person(db_path: Path, person_id: int, summary: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                """
                SELECT count(*)
                FROM notes
                WHERE record_type = 'person'
                  AND record_id = ?
                  AND note_type = 'call_log'
                  AND source_json LIKE ?
                """,
                (person_id, f'%"{summary}"%'),
            ).fetchone()[0]
        )


def insert_ambiguous_people(db_path: Path) -> str:
    ambiguous_name = "Automation Ambiguous Person"
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        next_id = int(conn.execute("SELECT COALESCE(max(id), 0) + 1 FROM people").fetchone()[0])
        rows = [
            (next_id, ambiguous_name, "ambiguous-one@example.local", timestamp, timestamp, "{}"),
            (next_id + 1, ambiguous_name, "ambiguous-two@example.local", timestamp, timestamp, "{}"),
        ]
        conn.executemany(
            """
            INSERT INTO people (id, name, email, created_at, updated_at, source_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    return ambiguous_name


def main() -> int:
    env_backup = {
        key: os.environ.get(key)
        for key in [
            "CHILLCRM_AUTOMATION_TOKEN",
            "DATABASE_URL",
            "CHILLCRM_DATABASE_ADAPTER",
            "CRM_DATABASE_ADAPTER",
            "REMOTE_WRITE_LOCK",
            "CHILLCRM_LOCAL_WRITE_FREEZE",
            "LOCAL_WRITE_FREEZE",
        ]
    }
    with tempfile.TemporaryDirectory(prefix="chillcrm-automation-test-") as tmp_name:
        tmp_dir = Path(tmp_name)
        tmp_db = tmp_dir / "local_crm.sqlite"
        shutil.copy2(DEFAULT_DB, tmp_db)
        ensure_runtime_schema(tmp_db)
        person_id = first_person_id(tmp_db)
        owner_id, owner_name = first_owner(tmp_db)
        ambiguous_name = insert_ambiguous_people(tmp_db)

        class TestHandler(handler):
            db_path = tmp_db

            def create_backup(self, label: str) -> Path:
                backup_path = tmp_dir / f"{label}.sqlite"
                shutil.copy2(self.db_path, backup_path)
                return backup_path

        try:
            os.environ.pop("DATABASE_URL", None)
            os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
            os.environ.pop("CRM_DATABASE_ADAPTER", None)
            os.environ.pop("REMOTE_WRITE_LOCK", None)
            os.environ.pop("CHILLCRM_LOCAL_WRITE_FREEZE", None)
            os.environ.pop("LOCAL_WRITE_FREEZE", None)
            os.environ.pop("CHILLCRM_AUTOMATION_TOKEN", None)

            probe = TestHandler.__new__(TestHandler)
            probe.headers = {}

            payload, status = probe.automation_authorization_error()
            assert status == 503, payload
            assert payload["code"] == "automation_token_not_configured"

            os.environ["CHILLCRM_AUTOMATION_TOKEN"] = TOKEN
            payload, status = probe.automation_authorization_error()
            assert status == 401, payload
            assert payload["code"] == "automation_token_required"

            probe.headers = {"Authorization": "Bearer wrong-token"}
            payload, status = probe.automation_authorization_error()
            assert status == 403, payload
            assert payload["code"] == "automation_token_invalid"

            probe.headers = {"Authorization": f"Bearer {TOKEN}"}
            assert probe.automation_authorization_error() is None

            content = "Automation verifier task"
            assert task_count_for_person(tmp_db, person_id, content) == 0
            payload, status = probe.add_automation_person_task(
                {
                    "person_id": person_id,
                    "content": "Automation verifier task",
                    "due_date": "2026-08-11",
                    "source": "Otter debrief verifier",
                },
            )
            assert status == 200, payload
            assert payload["ok"] is True
            assert payload["automation"]["person_id"] == person_id
            assert task_count_for_person(tmp_db, person_id, content) == 1
            source = task_source_for_person(tmp_db, person_id, content)
            assert source["local_source"] == "automation_transcript_task"
            assert source["notes"] == "Otter debrief verifier"

            owner_content = "Automation verifier owner task"
            assert task_count_for_owner(tmp_db, owner_id, owner_content) == 0
            payload, status = probe.add_automation_owner_task(
                {
                    "owner_name": owner_name,
                    "content": "Automation verifier owner task",
                    "due_date": "2026-08-14",
                    "source": "Otter owner brief verifier",
                },
            )
            assert status == 200, payload
            assert payload["ok"] is True
            assert payload["automation"]["owner_id"] == owner_id
            assert task_count_for_owner(tmp_db, owner_id, owner_content) == 1
            source = task_source_for_owner(tmp_db, owner_id, owner_content)
            assert source["local_source"] == "automation_transcript_task"
            assert source["notes"] == "Otter owner brief verifier"

            note_content = "Automation verifier note\n\nSource: Otter debrief verifier"
            assert note_count_for_person(tmp_db, person_id, note_content) == 0
            payload, status = probe.add_automation_person_note(
                {
                    "person_id": person_id,
                    "content": "Automation verifier note",
                    "source": "Otter debrief verifier",
                },
            )
            assert status == 200, payload
            assert payload["ok"] is True
            assert payload["automation"]["person_id"] == person_id
            assert note_count_for_person(tmp_db, person_id, note_content) == 1

            call_summary = "Automation verifier call"
            assert call_count_for_person(tmp_db, person_id, call_summary) == 0
            payload, status = probe.add_automation_person_call(
                {
                    "person_id": person_id,
                    "summary": call_summary,
                    "content": "Discussed follow-up from transcript.",
                    "date": "2026-08-10",
                    "source": "Otter debrief verifier",
                },
            )
            assert status == 200, payload
            assert payload["ok"] is True
            assert payload["automation"]["person_id"] == person_id
            assert call_count_for_person(tmp_db, person_id, call_summary) == 1

            payload, status = probe.add_automation_person_task(
                {"person_name": ambiguous_name, "content": "Should not create"},
            )
            assert status == 400, payload
            assert payload["code"] == "person_match_ambiguous"
            assert len(payload["possible_matches"]) == 2

            payload, status = probe.add_automation_person_note(
                {"person_name": ambiguous_name, "content": "Should not create"},
            )
            assert status == 400, payload
            assert payload["code"] == "person_match_ambiguous"
        finally:
            for key, value in env_backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    print("CHILLCRM automation Person endpoints verifier passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
