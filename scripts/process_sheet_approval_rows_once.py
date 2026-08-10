#!/usr/bin/env python3
"""Post approved transcript review rows to CHILLCRM using a private token prompt."""

from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


TYPE_ENDPOINTS = {
    "TASK": "/api/automation/add_person_task",
    "NOTE": "/api/automation/add_person_note",
    "CALL": "/api/automation/add_person_call",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one CHILLCRM transcript approval queue snapshot.")
    parser.add_argument("--input", required=True, help="JSON file containing review rows.")
    parser.add_argument("--report", required=True, help="Where to write the no-secret result report.")
    parser.add_argument("--base-url", default="https://chillcrm.app")
    args = parser.parse_args()

    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    token = getpass.getpass("CHILLCRM_AUTOMATION_TOKEN: ").strip()
    if not token:
        raise SystemExit("No token entered. Nothing processed.")

    results = []
    for row in rows:
        row_number = row.get("row_number")
        status = str(row.get("status") or "").strip().upper()
        if status == "DELETE":
            results.append({"row_number": row_number, "action": "delete_row", "ok": True})
            continue
        if status != "APPROVE":
            results.append({"row_number": row_number, "action": "left_in_queue", "ok": True, "status": status})
            continue
        try:
            path, payload = endpoint_payload(row)
            http_status, response = post_to_chillcrm(args.base_url, path, token, payload)
            ok = 200 <= http_status < 300 and bool(response.get("ok"))
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
        "secret_values_stored": "no",
        "results": results,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    posted = sum(1 for item in results if item.get("action") == "posted" and item.get("ok"))
    failed = sum(1 for item in results if item.get("action") == "post_failed")
    delete_rows = sum(1 for item in results if item.get("action") == "delete_row")
    print(f"Processed approval snapshot. Posted: {posted}. Failed: {failed}. Delete-only rows: {delete_rows}.")
    print(f"Report: {args.report}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
