#!/usr/bin/env python3
"""Post approved transcript review rows to CHILLCRM."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


TYPE_ENDPOINTS = {
    "TASK": "/api/automation/add_person_task",
    "NOTE": "/api/automation/add_person_note",
    "CALL": "/api/automation/add_person_call",
}

HEADER_KEY_OVERRIDES = {
    "PERSON NAME": "person_name",
    "TYPE": "type",
    "DATE": "date",
    "DUE DATE": "due_date",
    "PROPOSED DETAIL": "proposed_detail",
    "STATUS": "status",
    "SOURCE FILE NAME": "source_file_name",
    "SOURCE FILE URL": "source_file_url",
    "SUGGESTION ID": "suggestion_id",
    "PERSON ID CANDIDATE": "person_id_candidate",
    "MATCH CONFIDENCE": "match_confidence",
}


def is_owner_task(row: dict[str, Any]) -> bool:
    return str(row.get("match_confidence") or "").strip().lower() == "owner_brief"


def owner_name_from_row(row: dict[str, Any]) -> str:
    raw_name = str(row.get("person_name") or "").strip()
    return raw_name.split("/", 1)[0].strip()


def normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def source_text(row: dict[str, Any]) -> str:
    pieces = []
    if row.get("source_file_name"):
        pieces.append(str(row["source_file_name"]))
    if row.get("source_file_url"):
        pieces.append(str(row["source_file_url"]))
    if row.get("suggestion_id"):
        pieces.append(f"suggestion_id={row['suggestion_id']}")
    return " | ".join(pieces) or "Transcript approval queue"


def person_payload(row: dict[str, Any]) -> dict[str, Any]:
    candidate = str(row.get("person_id_candidate") or "").strip()
    if re.fullmatch(r"\d+", candidate):
        return {"person_id": int(candidate)}
    return {"person_name": str(row.get("person_name") or "").strip()}


def endpoint_payload(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if is_owner_task(row):
        detail = str(row.get("proposed_detail") or "").strip()
        if not detail:
            raise ValueError("PROPOSED DETAIL is blank.")
        owner_name = owner_name_from_row(row)
        if not owner_name:
            raise ValueError("OWNER NAME is blank.")
        payload = {
            "owner_name": owner_name,
            "content": detail,
            "source": source_text(row),
        }
        due_date = normalize_date(row.get("due_date"))
        if due_date:
            payload["due_date"] = due_date
        return "/api/automation/add_owner_task", payload

    row_type = str(row.get("type") or "").strip().upper()
    if row_type not in TYPE_ENDPOINTS:
        raise ValueError(f"Unsupported TYPE: {row_type}")
    detail = str(row.get("proposed_detail") or "").strip()
    if not detail:
        raise ValueError("PROPOSED DETAIL is blank.")
    payload: dict[str, Any] = {
        **person_payload(row),
        "content": detail,
        "source": source_text(row),
    }
    due_date = normalize_date(row.get("due_date"))
    date = normalize_date(row.get("date"))
    if row_type == "TASK" and due_date:
        payload["due_date"] = due_date
    if row_type == "CALL":
        payload["date"] = date
        payload["summary"] = detail[:120]
    return TYPE_ENDPOINTS[row_type], payload


def post_to_chillcrm(base_url: str, path: str, token: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def google_token_from_service_account(service_account_json: str) -> str:
    credentials = json.loads(service_account_json)
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": credentials["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}.{b64url(json.dumps(claim, separators=(',', ':')).encode())}".encode()
    private_key = serialization.load_pem_private_key(credentials["private_key"].encode(), password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode() + "." + b64url(signature)
    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode()
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
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
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google API request failed with HTTP {exc.code}: {raw_error}") from exc
    return json.loads(raw) if raw else {}


def normalize_header(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip()).upper()
    if text in HEADER_KEY_OVERRIDES:
        return HEADER_KEY_OVERRIDES[text]
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def rows_from_sheet_values(values: list[list[Any]]) -> list[dict[str, Any]]:
    if not values:
        return []
    headers = [normalize_header(value) for value in values[0]]
    rows = []
    for index, values_row in enumerate(values[1:], start=2):
        row = {"row_number": index}
        for position, key in enumerate(headers):
            if key:
                row[key] = values_row[position] if position < len(values_row) else ""
        rows.append(row)
    return rows


def read_google_sheet_rows(spreadsheet_id: str, sheet_name: str, token: str) -> tuple[list[dict[str, Any]], int]:
    encoded_range = urllib.parse.quote(f"{sheet_name}!A:Z", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}?majorDimension=ROWS"
    values = google_request(token, url).get("values", [])
    return rows_from_sheet_values(values), len(values)


def google_sheet_id(spreadsheet_id: str, sheet_name: str, token: str) -> int:
    fields = urllib.parse.quote("sheets(properties(sheetId,title))", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields={fields}"
    metadata = google_request(token, url)
    for sheet in metadata.get("sheets", []):
        properties = sheet.get("properties", {})
        if properties.get("title") == sheet_name:
            return int(properties["sheetId"])
    raise ValueError(f"Sheet tab not found: {sheet_name}")


def delete_sheet_rows(spreadsheet_id: str, sheet_id: int, row_numbers: list[int], token: str) -> None:
    if not row_numbers:
        return
    requests = [
        {
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": row_number - 1,
                    "endIndex": row_number,
                }
            }
        }
        for row_number in sorted(set(row_numbers), reverse=True)
    ]
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    google_request(token, url, method="POST", payload={"requests": requests})


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one CHILLCRM transcript approval queue snapshot.")
    parser.add_argument("--input", default="", help="JSON file containing review rows.")
    parser.add_argument("--report", required=True, help="Where to write the no-secret result report.")
    parser.add_argument("--base-url", default="https://chillcrm.app")
    parser.add_argument("--google-sheet-id", default=os.environ.get("GOOGLE_APPROVAL_SHEET_ID", ""))
    parser.add_argument("--sheet-name", default=os.environ.get("GOOGLE_APPROVAL_SHEET_NAME", "Awaiting Approval"))
    parser.add_argument("--service-account-json-env", default="GOOGLE_SERVICE_ACCOUNT_JSON")
    parser.add_argument("--delete-processed-rows", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    google_token = ""
    sheet_value_rows = 0
    if args.google_sheet_id:
        service_account_json = os.environ.get(args.service_account_json_env, "").strip()
        if not service_account_json:
            raise SystemExit(f"{args.service_account_json_env} is required for live Google Sheet processing.")
        google_token = google_token_from_service_account(service_account_json)
        rows, sheet_value_rows = read_google_sheet_rows(args.google_sheet_id, args.sheet_name, google_token)
    elif args.input:
        rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        raise SystemExit("--input or --google-sheet-id is required.")

    token = os.environ.get("CHILLCRM_AUTOMATION_TOKEN", "").strip()
    if not token and not args.dry_run:
        token = getpass.getpass("CHILLCRM_AUTOMATION_TOKEN: ").strip()
    if not token and not args.dry_run:
        raise SystemExit("No token entered. Nothing processed.")

    results = []
    rows_to_delete = []
    for row in rows:
        row_number = row.get("row_number")
        status = str(row.get("status") or "").strip().upper()
        if status == "DELETE":
            results.append({"row_number": row_number, "action": "delete_row", "ok": True})
            if isinstance(row_number, int):
                rows_to_delete.append(row_number)
            continue
        if status != "APPROVE":
            results.append({"row_number": row_number, "action": "left_in_queue", "ok": True, "status": status})
            continue
        try:
            path, payload = endpoint_payload(row)
            if args.dry_run:
                http_status, response, ok = 0, {"ok": True, "dry_run": True}, True
            else:
                http_status, response = post_to_chillcrm(args.base_url, path, token, payload)
                ok = 200 <= http_status < 300 and bool(response.get("ok"))
            if ok and isinstance(row_number, int):
                rows_to_delete.append(row_number)
            results.append(
                {
                    "row_number": row_number,
                    "action": "posted" if ok else "post_failed",
                    "ok": ok,
                    "http_status": http_status,
                    "endpoint": path,
                    "person_name": row.get("person_name"),
                    "type": row.get("type"),
                    "response_code": response.get("code"),
                    "response_error": response.get("error"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "row_number": row_number,
                    "action": "post_failed",
                    "ok": False,
                    "person_name": row.get("person_name"),
                    "type": row.get("type"),
                    "response_error": str(exc),
                }
            )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "source": "google_sheet" if args.google_sheet_id else "local_snapshot",
        "google_sheet_id_configured": bool(args.google_sheet_id),
        "sheet_name": args.sheet_name if args.google_sheet_id else "",
        "sheet_value_rows": sheet_value_rows,
        "dry_run": args.dry_run,
        "secret_values_stored": "no",
        "processed_sheet_rows_removed": 0,
        "results": results,
    }
    if args.google_sheet_id and args.delete_processed_rows and rows_to_delete and not args.dry_run:
        sheet_id = google_sheet_id(args.google_sheet_id, args.sheet_name, google_token)
        delete_sheet_rows(args.google_sheet_id, sheet_id, rows_to_delete, google_token)
        report["processed_sheet_rows_removed"] = len(set(rows_to_delete))
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    posted = sum(1 for item in results if item.get("action") == "posted" and item.get("ok"))
    failed = sum(1 for item in results if item.get("action") == "post_failed")
    delete_rows = sum(1 for item in results if item.get("action") == "delete_row")
    print(f"Processed approval snapshot. Posted: {posted}. Failed: {failed}. Delete-only rows: {delete_rows}.")
    print(f"Report: {args.report}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
