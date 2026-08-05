"""Request body parsing helpers for CHILLCRM."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any


class RequestBodyTooLarge(ValueError):
    pass


def read_body_text(rfile: Any, headers: Any, max_body_bytes: int) -> str:
    try:
        length = int(headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Invalid request body length.") from exc
    if length < 0:
        raise ValueError("Invalid request body length.")
    if length == 0:
        return ""
    if length > max_body_bytes:
        raise RequestBodyTooLarge("Request body is too large.")
    try:
        return rfile.read(length).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Request body must be valid UTF-8.") from exc


def read_json_body(rfile: Any, headers: Any, max_body_bytes: int) -> dict[str, Any]:
    raw = read_body_text(rfile, headers, max_body_bytes)
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload


def read_webhook_body(rfile: Any, headers: Any, max_body_bytes: int) -> dict[str, Any]:
    raw = read_body_text(rfile, headers, max_body_bytes)
    if not raw:
        return {}
    content_type = str(headers.get("Content-Type", "")).lower()
    if "json" in content_type:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return {str(key): value for key, value in payload.items()}
    parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
    if parsed:
        return {str(key): values[-1] if values else "" for key, values in parsed.items()}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return {str(key): value for key, value in payload.items()}
