#!/usr/bin/env python3
"""Scan Google Drive transcripts and append tentative CHILLCRM approval rows."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


APPROVAL_HEADERS = [
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
]

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
SUPPORTED_TEXT_MIMES = {GOOGLE_DOC_MIME, "text/plain"}
DEFAULT_MODEL = "gpt-5-mini"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def google_token_from_service_account(service_account_json: str, scopes: list[str]) -> str:
    credentials = json.loads(service_account_json)
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": credentials["client_email"],
        "scope": " ".join(scopes),
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}.{b64url(json.dumps(claim, separators=(',', ':')).encode())}".encode()
    private_key = serialization.load_pem_private_key(credentials["private_key"].encode(), password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode() + "." + b64url(signature)
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode()
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["access_token"]


def google_request(token: str, url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google API request failed with HTTP {exc.code}: {raw_error}") from exc
    return json.loads(raw) if raw else {}


def google_bytes(token: str, url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google file request failed with HTTP {exc.code}: {raw_error}") from exc


def list_drive_children(token: str, folder_id: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page_token = ""
    while True:
        query = urllib.parse.quote(f"'{folder_id}' in parents and trashed = false", safe="")
        fields = urllib.parse.quote("nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink)", safe="")
        url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields={fields}&pageSize=1000&supportsAllDrives=true&includeItemsFromAllDrives=true"
        if page_token:
            url += f"&pageToken={urllib.parse.quote(page_token)}"
        payload = google_request(token, url)
        files.extend(payload.get("files", []))
        page_token = payload.get("nextPageToken") or ""
        if not page_token:
            break
    return files


def walk_drive_transcripts(token: str, root_folder_id: str) -> list[dict[str, Any]]:
    pending = [root_folder_id]
    transcripts: list[dict[str, Any]] = []
    seen_folders: set[str] = set()
    while pending:
        folder_id = pending.pop(0)
        if folder_id in seen_folders:
            continue
        seen_folders.add(folder_id)
        for item in list_drive_children(token, folder_id):
            if item.get("mimeType") == GOOGLE_FOLDER_MIME:
                pending.append(item["id"])
            elif is_transcript_file(item):
                transcripts.append(item)
    transcripts.sort(key=lambda item: str(item.get("modifiedTime") or ""), reverse=True)
    return transcripts


def is_transcript_file(item: dict[str, Any]) -> bool:
    mime = item.get("mimeType") or ""
    return mime in SUPPORTED_TEXT_MIMES


def download_transcript_text(token: str, item: dict[str, Any]) -> str:
    file_id = item["id"]
    if item.get("mimeType") == GOOGLE_DOC_MIME:
        url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(file_id)}/export?mimeType=text/plain"
        return google_bytes(token, url).decode("utf-8", errors="replace")
    url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(file_id)}?alt=media&supportsAllDrives=true"
    return google_bytes(token, url).decode("utf-8", errors="replace")


def sheet_metadata(token: str, spreadsheet_id: str) -> dict[str, Any]:
    fields = urllib.parse.quote("sheets(properties(sheetId,title,hidden))", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields={fields}"
    return google_request(token, url)


def sheet_id_by_name(token: str, spreadsheet_id: str, sheet_name: str) -> int | None:
    for sheet in sheet_metadata(token, spreadsheet_id).get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == sheet_name:
            return int(props["sheetId"])
    return None


def ensure_sheet(token: str, spreadsheet_id: str, sheet_name: str, headers: list[str], hidden: bool = False) -> int:
    existing_id = sheet_id_by_name(token, spreadsheet_id, sheet_name)
    if existing_id is None:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        google_request(token, url, method="POST", payload={"requests": [{"addSheet": {"properties": {"title": sheet_name, "hidden": hidden}}}]})
        existing_id = sheet_id_by_name(token, spreadsheet_id, sheet_name)
        if existing_id is None:
            raise RuntimeError(f"Could not create sheet tab {sheet_name!r}.")
    existing_headers = read_sheet_values(token, spreadsheet_id, sheet_name, "A1:Z1")
    if not existing_headers:
        append_sheet_rows(token, spreadsheet_id, sheet_name, [headers])
    return existing_id


def read_sheet_values(token: str, spreadsheet_id: str, sheet_name: str, range_suffix: str = "A:Z") -> list[list[Any]]:
    encoded_range = urllib.parse.quote(f"{sheet_name}!{range_suffix}", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}?majorDimension=ROWS"
    return google_request(token, url).get("values", [])


def append_sheet_rows(token: str, spreadsheet_id: str, sheet_name: str, rows: list[list[Any]]) -> None:
    if not rows:
        return
    encoded_range = urllib.parse.quote(f"{sheet_name}!A:Z", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    google_request(token, url, method="POST", payload={"values": rows})


def processed_log(values: list[list[Any]]) -> dict[str, str]:
    output: dict[str, str] = {}
    for row in values[1:]:
        if len(row) >= 2 and row[0]:
            output[str(row[0])] = str(row[1] or "")
    return output


def existing_suggestion_ids(values: list[list[Any]]) -> set[str]:
    if not values:
        return set()
    headers = [str(item or "").strip().upper() for item in values[0]]
    try:
        index = headers.index("SUGGESTION ID")
    except ValueError:
        return set()
    return {str(row[index]).strip() for row in values[1:] if len(row) > index and str(row[index]).strip()}


def source_date(item: dict[str, Any]) -> str:
    raw = str(item.get("modifiedTime") or "")
    return raw[:10] if re.match(r"\d{4}-\d{2}-\d{2}", raw) else datetime.now(timezone.utc).date().isoformat()


def clean_text(value: Any, limit: int = 600) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def suggestion_id(file_id: str, row_type: str, person_name: str, detail: str) -> str:
    digest = hashlib.sha256(f"{file_id}|{row_type}|{person_name}|{detail}".encode("utf-8")).hexdigest()[:14]
    return f"{file_id}:{digest}"


def normalize_suggestion(raw: dict[str, Any], item: dict[str, Any]) -> dict[str, str] | None:
    row_type = str(raw.get("type") or "").strip().upper()
    if row_type not in {"TASK", "NOTE", "CALL"}:
        return None
    person_name = clean_text(raw.get("person_name"), 120)
    detail = clean_text(raw.get("proposed_detail") or raw.get("detail"), 1200)
    if not person_name or not detail:
        return None
    due_date = clean_text(raw.get("due_date"), 20)
    date = clean_text(raw.get("date"), 20) or source_date(item)
    confidence = clean_text(raw.get("match_confidence") or raw.get("confidence") or "ai", 80)
    return {
        "PERSON NAME": person_name,
        "TYPE": row_type,
        "DATE": date if row_type == "CALL" else "",
        "DUE DATE": due_date if row_type == "TASK" else "",
        "PROPOSED DETAIL": detail,
        "STATUS": "PENDING",
        "SOURCE FILE NAME": str(item.get("name") or ""),
        "SOURCE FILE URL": str(item.get("webViewLink") or ""),
        "SUGGESTION ID": suggestion_id(str(item.get("id") or ""), row_type, person_name, detail),
        "PERSON ID CANDIDATE": "",
        "MATCH CONFIDENCE": confidence,
    }


def openai_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for output in payload.get("output", []) or []:
        for content in output.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def analyze_with_openai(transcript_text: str, item: dict[str, Any], model: str) -> list[dict[str, str]]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return []
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "person_name": {"type": "string"},
                        "type": {"type": "string", "enum": ["TASK", "NOTE", "CALL"]},
                        "date": {"type": "string"},
                        "due_date": {"type": "string"},
                        "proposed_detail": {"type": "string"},
                        "match_confidence": {"type": "string"},
                    },
                    "required": ["person_name", "type", "date", "due_date", "proposed_detail", "match_confidence"],
                },
            }
        },
        "required": ["suggestions"],
    }
    prompt = f"""
Review this Otter/Zoom transcript for CHILLCRM. Propose tentative CRM entries only when a named client/person is clearly discussed.

Rules:
- Output TASK, NOTE, or CALL rows only.
- Use first and last names when available.
- Never invent a person.
- TASK means Kevin/Alicia should do something later. Include a due_date only if the transcript clearly gives or strongly implies one; otherwise blank.
- NOTE means stable state-of-client intelligence: wins, needs, risks, missing pieces, decisions, or useful context.
- CALL means a client-specific call/conversation occurred and should be logged; make the detail a concise call summary.
- Do not create owner/global tasks unless the transcript explicitly names Kevin Nations or Alicia Nations as the owner of the action.
- Avoid duplicates and low-value fluff. Prefer fewer, sharper suggestions.

Source file: {item.get("name")}
Source date: {source_date(item)}

Transcript:
{transcript_text[:50000]}
"""
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": "You are a careful CRM transcript analyst. Return only valid JSON matching the schema."},
            {"role": "user", "content": prompt},
        ],
        "text": {"format": {"type": "json_schema", "name": "chillcrm_transcript_suggestions", "schema": schema, "strict": True}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error = json.loads(raw_error)
            error = parsed_error.get("error", {})
            error_type = clean_text(error.get("type"), 120)
            error_code = clean_text(error.get("code"), 120)
            detail = f"type={error_type or 'unknown'} code={error_code or 'unknown'}"
        except json.JSONDecodeError:
            detail = "unparseable_error_body"
        raise RuntimeError(f"OpenAI transcript review failed with HTTP {exc.code}: {detail}") from exc
    raw_text = openai_response_text(response_payload)
    parsed = json.loads(raw_text)
    return [row for row in (normalize_suggestion(item_payload, item) for item_payload in parsed.get("suggestions", [])) if row]


NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
ACTION_WORDS = re.compile(r"\b(follow up|send|ask|review|schedule|call|connect|introduce|help|get|confirm|check|prepare)\b", re.I)


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", compact) if sentence.strip()]


def heuristic_suggestions(transcript_text: str, item: dict[str, Any]) -> list[dict[str, str]]:
    sentences = split_sentences(transcript_text)
    candidates: dict[str, list[str]] = {}
    for sentence in sentences:
        for match in NAME_PATTERN.finditer(sentence):
            name = match.group(1).strip()
            if name.lower() in {"Kevin Nations", "Alicia Nations"}:
                continue
            if len(name.split()) < 2:
                continue
            candidates.setdefault(name, []).append(sentence)
    raw: list[dict[str, Any]] = []
    for name, name_sentences in candidates.items():
        action_sentences = [sentence for sentence in name_sentences if ACTION_WORDS.search(sentence)]
        context = clean_text(" ".join(name_sentences[:3]), 900)
        if context:
            raw.append({"person_name": name, "type": "NOTE", "date": "", "due_date": "", "proposed_detail": context, "match_confidence": "heuristic_name"})
        if action_sentences:
            raw.append({"person_name": name, "type": "TASK", "date": "", "due_date": "", "proposed_detail": clean_text(action_sentences[0], 700), "match_confidence": "heuristic_action"})
    return [row for row in (normalize_suggestion(item_payload, item) for item_payload in raw[:40]) if row]


def transcript_suggestions(transcript_text: str, item: dict[str, Any], model: str) -> tuple[list[dict[str, str]], str]:
    if os.environ.get("OPENAI_API_KEY", "").strip():
        try:
            return analyze_with_openai(transcript_text, item, model), "openai"
        except Exception as exc:
            print(f"OpenAI transcript review failed for {item.get('name')}; using conservative heuristic fallback: {exc}")
            return heuristic_suggestions(transcript_text, item), "heuristic_after_openai_error"
    return heuristic_suggestions(transcript_text, item), "heuristic"


def rows_for_sheet(suggestions: list[dict[str, str]], existing_ids: set[str]) -> list[list[str]]:
    rows = []
    seen = set(existing_ids)
    for suggestion in suggestions:
        sid = suggestion["SUGGESTION ID"]
        if sid in seen:
            continue
        seen.add(sid)
        rows.append([suggestion.get(header, "") for header in APPROVAL_HEADERS])
    return rows


def log_rows_for_files(files: list[dict[str, Any]], status: str, analyzer: str, suggestion_count: int) -> list[list[str]]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for item in files:
        rows.append([item.get("id", ""), item.get("modifiedTime", ""), item.get("name", ""), now, status, analyzer, str(suggestion_count)])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan new Drive transcripts and add PENDING suggestions to the CHILLCRM approval sheet.")
    parser.add_argument("--drive-folder-id", default=os.environ.get("GOOGLE_TRANSCRIPT_FOLDER_ID", ""))
    parser.add_argument("--google-sheet-id", default=os.environ.get("GOOGLE_APPROVAL_SHEET_ID", ""))
    parser.add_argument("--approval-sheet-name", default=os.environ.get("GOOGLE_APPROVAL_SHEET_NAME", "Awaiting Approval"))
    parser.add_argument("--log-sheet-name", default=os.environ.get("GOOGLE_TRANSCRIPT_LOG_SHEET_NAME", "Transcript Intake Log"))
    parser.add_argument("--service-account-json-env", default="GOOGLE_SERVICE_ACCOUNT_JSON")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL)
    parser.add_argument("--max-files", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    if not args.drive_folder_id:
        raise SystemExit("--drive-folder-id or GOOGLE_TRANSCRIPT_FOLDER_ID is required.")
    if not args.google_sheet_id:
        raise SystemExit("--google-sheet-id or GOOGLE_APPROVAL_SHEET_ID is required.")
    service_account_json = os.environ.get(args.service_account_json_env, "").strip()
    if not service_account_json:
        raise SystemExit(f"{args.service_account_json_env} is required.")

    token = google_token_from_service_account(
        service_account_json,
        ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"],
    )
    ensure_sheet(token, args.google_sheet_id, args.approval_sheet_name, APPROVAL_HEADERS)
    ensure_sheet(token, args.google_sheet_id, args.log_sheet_name, ["FILE ID", "MODIFIED TIME", "FILE NAME", "PROCESSED AT", "STATUS", "ANALYZER", "SUGGESTIONS"], hidden=False)
    processed = processed_log(read_sheet_values(token, args.google_sheet_id, args.log_sheet_name))
    existing_ids = existing_suggestion_ids(read_sheet_values(token, args.google_sheet_id, args.approval_sheet_name))
    files = walk_drive_transcripts(token, args.drive_folder_id)
    new_files = [item for item in files if processed.get(str(item.get("id"))) != str(item.get("modifiedTime") or "")][: max(0, args.max_files)]

    appended_rows: list[list[str]] = []
    log_rows: list[list[str]] = []
    file_results = []
    failures = 0
    for item in new_files:
        try:
            text = download_transcript_text(token, item)
            suggestions, analyzer = transcript_suggestions(text, item, args.model)
            rows = rows_for_sheet(suggestions, existing_ids)
            existing_ids.update(row[8] for row in rows if len(row) > 8)
            appended_rows.extend(rows)
            log_rows.extend(log_rows_for_files([item], "processed", analyzer, len(rows)))
            file_results.append({"file_id": item.get("id"), "file_name": item.get("name"), "ok": True, "analyzer": analyzer, "suggestions": len(rows)})
        except Exception as exc:
            failures += 1
            file_results.append({"file_id": item.get("id"), "file_name": item.get("name"), "ok": False, "error": str(exc)})

    if appended_rows and not args.dry_run:
        append_sheet_rows(token, args.google_sheet_id, args.approval_sheet_name, appended_rows)
    if log_rows and not args.dry_run:
        append_sheet_rows(token, args.google_sheet_id, args.log_sheet_name, log_rows)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dry_run": args.dry_run,
        "drive_folder_id": args.drive_folder_id,
        "google_sheet_id_configured": bool(args.google_sheet_id),
        "approval_sheet_name": args.approval_sheet_name,
        "log_sheet_name": args.log_sheet_name,
        "files_seen": len(files),
        "new_files_considered": len(new_files),
        "approval_rows_appended": 0 if args.dry_run else len(appended_rows),
        "approval_rows_planned": len(appended_rows),
        "failures": failures,
        "openai_enabled": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
        "secret_values_stored": "no",
        "crm_record_writes": "no",
        "file_results": file_results,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Transcript scan complete. New files: {len(new_files)}. Planned rows: {len(appended_rows)}. Appended: {0 if args.dry_run else len(appended_rows)}. Failures: {failures}.")
    print(f"Report: {args.report}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
