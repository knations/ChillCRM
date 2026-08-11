#!/usr/bin/env python3
"""Verify Granola intake planning without provider calls."""

from __future__ import annotations

from scan_granola_notes_to_approval_sheet import (
    granola_note_text,
    log_row_for_note,
    note_date,
    note_title,
    note_url,
    note_version,
    suggestion_item,
    transcript_line_text,
)


def main() -> int:
    note = {
        "id": "not_123",
        "title": "Forum weekly call",
        "created_at": "2026-08-11T16:30:00Z",
        "updated_at": "2026-08-11T17:00:00Z",
        "url": "https://notes.granola.ai/not_123",
        "summary": "Vince needs onboarding support.",
        "transcript": [
            {"speaker": {"name": "Kevin Nations"}, "text": "Vince needs a clearer onboarding plan."},
            {"speaker": {"diarization_label": "Speaker B"}, "text": "We should follow up next week."},
            "Plain transcript line.",
        ],
    }

    assert note_title(note) == "Forum weekly call"
    assert note_version(note) == "2026-08-11T17:00:00Z"
    assert note_date(note) == "2026-08-11"
    assert note_url(note) == "https://notes.granola.ai/not_123"
    assert transcript_line_text(note["transcript"][0]) == "Kevin Nations: Vince needs a clearer onboarding plan."
    assert transcript_line_text(note["transcript"][1]) == "Speaker B: We should follow up next week."
    assert transcript_line_text(note["transcript"][2]) == "Plain transcript line."

    text = granola_note_text(note)
    assert "Granola note: Forum weekly call" in text
    assert "Summary:" in text
    assert "Transcript:" in text
    assert "Vince needs a clearer onboarding plan." in text

    item = suggestion_item(note)
    assert item["id"] == "not_123"
    assert item["name"] == "Forum weekly call"
    assert item["modifiedTime"] == "2026-08-11T17:00:00Z"
    assert item["webViewLink"] == "https://notes.granola.ai/not_123"

    log_row = log_row_for_note(note, "processed", "openai", 3)
    assert log_row[:3] == ["not_123", "2026-08-11T17:00:00Z", "Forum weekly call"]
    assert log_row[4:] == ["processed", "openai", "3"]

    print("granola_intake_bot_verification_passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
