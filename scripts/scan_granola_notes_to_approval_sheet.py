#!/usr/bin/env python3
"""Scan Granola notes and append tentative CHILLCRM approval rows."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scan_drive_transcripts_to_approval_sheet import (
    APPROVAL_HEADERS,
    append_sheet_rows,
    apply_clean_sheet_format,
    clean_text,
    ensure_sheet,
    existing_suggestion_ids,
    google_token_from_service_account,
    processed_log,
    read_sheet_values,
    row_dicts_for_report,
    rows_for_sheet,
    transcript_suggestions,
)


GRANOLA_BASE_URL = "https://public-api.granola.ai/v1"
DEFAULT_MODEL = "gpt-5-mini"


def granola_request(api_key: str, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{GRANOLA_BASE_URL}{path}{query}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Granola API request failed with HTTP {exc.code}: {raw_error}") from exc
    return json.loads(raw) if raw else {}


def list_granola_notes(api_key: str, created_after: str, max_notes: int) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    cursor = ""
    while len(notes) < max_notes:
        params: dict[str, str] = {}
        if created_after:
            params["created_after"] = created_after
        if cursor:
            params["cursor"] = cursor
        payload = granola_request(api_key, "/notes", params)
        batch = payload.get("notes") or []
        if not isinstance(batch, list):
            raise RuntimeError("Granola notes response did not include a notes list.")
        notes.extend([note for note in batch if isinstance(note, dict)])
        if not payload.get("hasMore") or not payload.get("cursor"):
            break
        cursor = str(payload["cursor"])
        time.sleep(0.2)
    return notes[:max_notes]


def get_granola_note(api_key: str, note_id: str) -> dict[str, Any]:
    return granola_request(api_key, f"/notes/{urllib.parse.quote(note_id)}", {"include": "transcript"})


def first_string(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def note_version(note: dict[str, Any]) -> str:
    return first_string(note, ["updated_at", "updatedAt", "modified_at", "modifiedAt", "created_at", "createdAt", "created"])


def note_date(note: dict[str, Any]) -> str:
    raw = note_version(note)
    return raw[:10] if len(raw) >= 10 else datetime.now(timezone.utc).date().isoformat()


def note_title(note: dict[str, Any]) -> str:
    return first_string(note, ["title", "name"]) or f"Granola note {note.get('id', '')}".strip()


def note_url(note: dict[str, Any]) -> str:
    return first_string(note, ["url", "web_url", "webUrl", "share_url", "shareUrl", "app_url", "appUrl"])


def transcript_line_text(line: Any) -> str:
    if isinstance(line, str):
        return line.strip()
    if not isinstance(line, dict):
        return ""
    text = str(line.get("text") or "").strip()
    speaker = line.get("speaker") if isinstance(line.get("speaker"), dict) else {}
    speaker_name = first_string(speaker, ["name", "diarization_label", "label", "source"])
    if speaker_name and text:
        return f"{speaker_name}: {text}"
    return text


def granola_note_text(note: dict[str, Any]) -> str:
    pieces = [
        f"Granola note: {note_title(note)}",
        f"Date: {note_date(note)}",
    ]
    summary = first_string(note, ["summary", "notes", "ai_summary", "aiSummary"])
    if summary:
        pieces.extend(["Summary:", summary])
    transcript = note.get("transcript") or []
    if isinstance(transcript, list):
        transcript_text = "\n".join(line for line in (transcript_line_text(item) for item in transcript) if line)
        if transcript_text:
            pieces.extend(["Transcript:", transcript_text])
    return "\n\n".join(pieces)


def suggestion_item(note: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(note.get("id") or ""),
        "name": note_title(note),
        "modifiedTime": note_version(note),
        "webViewLink": note_url(note),
    }


def log_row_for_note(note: dict[str, Any], status: str, analyzer: str, suggestion_count: int) -> list[str]:
    return [
        str(note.get("id") or ""),
        note_version(note),
        note_title(note),
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status,
        analyzer,
        str(suggestion_count),
    ]


def default_created_after(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan new Granola notes and add PENDING suggestions to the CHILLCRM approval sheet.")
    parser.add_argument("--google-sheet-id", default=os.environ.get("GOOGLE_APPROVAL_SHEET_ID", ""))
    parser.add_argument("--approval-sheet-name", default=os.environ.get("GOOGLE_APPROVAL_SHEET_NAME", "Awaiting Approval"))
    parser.add_argument("--log-sheet-name", default=os.environ.get("GOOGLE_GRANOLA_LOG_SHEET_NAME", "Granola Intake Log"))
    parser.add_argument("--service-account-json-env", default="GOOGLE_SERVICE_ACCOUNT_JSON")
    parser.add_argument("--granola-api-key-env", default="GRANOLA_API_KEY")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL)
    parser.add_argument("--created-after", default=os.environ.get("GRANOLA_CREATED_AFTER", ""))
    parser.add_argument("--lookback-days", type=int, default=int(os.environ.get("GRANOLA_LOOKBACK_DAYS", "30")))
    parser.add_argument("--max-notes", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    if not args.google_sheet_id:
        raise SystemExit("--google-sheet-id or GOOGLE_APPROVAL_SHEET_ID is required.")
    service_account_json = os.environ.get(args.service_account_json_env, "").strip()
    if not service_account_json:
        raise SystemExit(f"{args.service_account_json_env} is required.")
    granola_api_key = os.environ.get(args.granola_api_key_env, "").strip()
    if not granola_api_key:
        raise SystemExit(f"{args.granola_api_key_env} is required.")

    google_token = google_token_from_service_account(
        service_account_json,
        ["https://www.googleapis.com/auth/spreadsheets"],
    )
    ensure_sheet(google_token, args.google_sheet_id, args.approval_sheet_name, APPROVAL_HEADERS)
    ensure_sheet(
        google_token,
        args.google_sheet_id,
        args.log_sheet_name,
        ["NOTE ID", "VERSION", "TITLE", "PROCESSED AT", "STATUS", "ANALYZER", "SUGGESTIONS"],
        hidden=False,
    )

    processed = processed_log(read_sheet_values(google_token, args.google_sheet_id, args.log_sheet_name))
    existing_ids = existing_suggestion_ids(read_sheet_values(google_token, args.google_sheet_id, args.approval_sheet_name))
    created_after = args.created_after or default_created_after(max(args.lookback_days, 1))
    notes = list_granola_notes(granola_api_key, created_after, max(args.max_notes, 0))
    new_notes = [note for note in notes if processed.get(str(note.get("id") or "")) != note_version(note)]

    appended_rows: list[list[str]] = []
    log_rows: list[list[str]] = []
    note_results = []
    failures = 0
    for note in new_notes:
        note_id = str(note.get("id") or "")
        try:
            full_note = get_granola_note(granola_api_key, note_id)
            full_note = {**note, **full_note}
            text = granola_note_text(full_note)
            suggestions, analyzer = transcript_suggestions(text, suggestion_item(full_note), args.model)
            rows = rows_for_sheet(suggestions, existing_ids)
            existing_ids.update(row[8] for row in rows if len(row) > 8)
            appended_rows.extend(rows)
            log_rows.append(log_row_for_note(full_note, "processed", analyzer, len(rows)))
            note_results.append(
                {
                    "note_id": note_id,
                    "version": note_version(full_note),
                    "title": note_title(full_note),
                    "ok": True,
                    "analyzer": analyzer,
                    "suggestions": len(rows),
                }
            )
        except Exception as exc:
            failures += 1
            note_results.append({"note_id": note_id, "version": note_version(note), "title": note_title(note), "ok": False, "error": str(exc)})

    if appended_rows and not args.dry_run:
        append_sheet_rows(google_token, args.google_sheet_id, args.approval_sheet_name, appended_rows)
    if log_rows and not args.dry_run:
        append_sheet_rows(google_token, args.google_sheet_id, args.log_sheet_name, log_rows)
    if not args.dry_run:
        apply_clean_sheet_format(google_token, args.google_sheet_id, [args.approval_sheet_name, args.log_sheet_name], args.approval_sheet_name)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dry_run": args.dry_run,
        "created_after": created_after,
        "google_sheet_id_configured": bool(args.google_sheet_id),
        "approval_sheet_name": args.approval_sheet_name,
        "log_sheet_name": args.log_sheet_name,
        "notes_seen": len(notes),
        "new_notes_considered": len(new_notes),
        "approval_rows_appended": 0 if args.dry_run else len(appended_rows),
        "approval_rows_planned": len(appended_rows),
        "failures": failures,
        "openai_enabled": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
        "secret_values_stored": "no",
        "crm_record_writes": "no",
        "planned_rows": row_dicts_for_report(appended_rows),
        "note_results": note_results,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Granola scan complete. New notes: {len(new_notes)}. Planned rows: {len(appended_rows)}. Appended: {0 if args.dry_run else len(appended_rows)}. Failures: {failures}.")
    print(f"Report: {args.report}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
