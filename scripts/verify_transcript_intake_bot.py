#!/usr/bin/env python3
"""Verify transcript intake planning without provider calls."""

from __future__ import annotations

from scan_drive_transcripts_to_approval_sheet import (
    APPROVAL_HEADERS,
    STATUS_OPTIONS,
    approval_control_format_requests,
    clean_format_request,
    existing_suggestion_ids,
    heuristic_suggestions,
    proposed_detail_format_requests,
    processed_log,
    row_dicts_for_report,
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
    row_report = row_dicts_for_report(rows)
    assert row_report[0]["STATUS"] == "PENDING"
    assert set(row_report[0]) == set(APPROVAL_HEADERS)

    duplicate_rows = rows_for_sheet(suggestions, {row[8] for row in rows})
    assert duplicate_rows == []

    clean_request = clean_format_request(123, 20, 11)
    assert clean_request["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] == {"red": 1, "green": 1, "blue": 1}
    assert clean_request["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"]["bold"] is False

    detail_requests = proposed_detail_format_requests(123, 12)
    assert detail_requests[0]["repeatCell"]["cell"]["userEnteredFormat"]["wrapStrategy"] == "WRAP"
    assert detail_requests[1]["updateDimensionProperties"]["properties"]["pixelSize"] == 620
    assert detail_requests[2]["autoResizeDimensions"]["dimensions"]["dimension"] == "ROWS"

    control_requests = approval_control_format_requests(123, 100)
    due_date_validation = control_requests[0]["setDataValidation"]["rule"]
    assert due_date_validation["condition"]["type"] == "DATE_IS_VALID"
    assert due_date_validation["showCustomUi"] is True
    due_date_format = control_requests[1]["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]
    assert due_date_format == {"type": "DATE", "pattern": "mm/dd/yyyy"}
    status_validation = control_requests[2]["setDataValidation"]["rule"]
    assert status_validation["condition"]["type"] == "ONE_OF_LIST"
    assert [value["userEnteredValue"] for value in status_validation["condition"]["values"]] == STATUS_OPTIONS
    assert status_validation["strict"] is True
    assert status_validation["showCustomUi"] is True

    print("transcript_intake_bot_verification_passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
