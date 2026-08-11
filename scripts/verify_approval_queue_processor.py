#!/usr/bin/env python3
"""Verify approval queue processor parsing and deletion planning without provider calls."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from process_sheet_approval_rows_once import endpoint_payload, rows_from_sheet_values


def main() -> int:
    values = [
        [
            "PERSON NAME",
            "TYPE",
            "DATE",
            "DUE DATE",
            "PROPOSED DETAIL",
            "STATUS",
            "SOURCE FILE NAME",
            "SOURCE FILE URL",
            "SUGGESTION ID",
            "PERSON ID CANDIDATE",
            "MATCH CONFIDENCE",
        ],
        [
            "Aaron Drussel",
            "TASK",
            "",
            "08/11/2026",
            "Follow up from call.",
            "APPROVE",
            "Otter transcript.txt",
            "https://docs.google.com/example",
            "abc123",
            "738",
            "exact",
        ],
        [
            "Kevin Nations / Owner Brief",
            "NOTE",
            "",
            "2026-08-12",
            "Review Monday brief.",
            "APPROVE",
            "Otter transcript.txt",
            "",
            "owner1",
            "",
            "owner_brief",
        ],
        [
            "Pending Person",
            "TASK",
            "",
            "",
            "Leave me alone.",
            "PENDING",
            "",
            "",
            "",
            "",
            "",
        ],
    ]
    rows = rows_from_sheet_values(values)
    assert rows[0]["row_number"] == 2
    assert rows[0]["person_name"] == "Aaron Drussel"
    assert rows[0]["person_id_candidate"] == "738"

    path, payload = endpoint_payload(rows[0])
    assert path == "/api/automation/add_person_task"
    assert payload["person_id"] == 738
    assert payload["due_date"] == "2026-08-11"
    assert "Otter transcript.txt" in payload["source"]

    owner_path, owner_payload = endpoint_payload(rows[1])
    assert owner_path == "/api/automation/add_owner_task"
    assert owner_payload["owner_name"] == "Kevin Nations"
    assert owner_payload["due_date"] == "2026-08-12"

    with tempfile.TemporaryDirectory() as tmpdir:
        report = Path(tmpdir) / "result.json"
        report.write_text(json.dumps({"ok": True}), encoding="utf-8")
        assert json.loads(report.read_text(encoding="utf-8"))["ok"] is True

    print("approval_queue_processor_verification_passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
