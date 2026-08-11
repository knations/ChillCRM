#!/usr/bin/env python3
"""Verify transcript intake planning without provider calls."""

from __future__ import annotations

from scan_drive_transcripts_to_approval_sheet import (
    APPROVAL_HEADERS,
    existing_suggestion_ids,
    heuristic_suggestions,
    processed_log,
    rows_for_sheet,
)


def main() -> int:
    log = processed_log(
        [
            ["FILE ID", "MODIFIED TIME", "FILE NAME"],
            ["doc_1", "2026-08-11T14:00:00.000Z", "First Transcript"],
            ["", "ignored", "Missing ID"],
        ]
    )
    assert log == {"doc_1": "2026-08-11T14:00:00.000Z"}

    existing = existing_suggestion_ids(
        [
            APPROVAL_HEADERS,
            ["Aaron Drussel", "TASK", "", "2026-08-12", "Existing", "PENDING", "File", "", "sid_1", "", "exact"],
        ]
    )
    assert existing == {"sid_1"}

    item = {
        "id": "doc_2",
        "name": "Dax Moy Onboarding.",
        "modifiedTime": "2026-08-11T15:02:21.501Z",
        "webViewLink": "https://docs.google.com/document/d/doc_2/edit",
    }
    transcript = (
        "Kevin Nations: Dax Moy is rebuilding the offer and onboarding path. "
        "Alicia should follow up with Dax Moy about the shipping address. "
        "Vince Gabriele has momentum but Kevin should review the proposal before Monday."
    )
    suggestions = heuristic_suggestions(transcript, item)
    assert any(row["PERSON NAME"] == "Dax Moy" and row["TYPE"] == "NOTE" for row in suggestions)
    assert any(row["PERSON NAME"] == "Dax Moy" and row["TYPE"] == "TASK" for row in suggestions)
    assert all(row["STATUS"] == "PENDING" for row in suggestions)

    rows = rows_for_sheet(suggestions, set())
    assert rows
    assert len(rows[0]) == len(APPROVAL_HEADERS)

    duplicate_rows = rows_for_sheet(suggestions, {row[8] for row in rows})
    assert duplicate_rows == []

    print("transcript_intake_bot_verification_passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
