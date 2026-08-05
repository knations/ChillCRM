"""HTTP response helpers for CHILLCRM."""

from __future__ import annotations

import csv
import email.utils
import hashlib
import io
import re
import urllib.parse
from datetime import timezone
from pathlib import Path
from typing import Any


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-DNS-Prefetch-Control": "off",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex, nofollow",
    "X-Permitted-Cross-Domain-Policies": "none",
    "X-Download-Options": "noopen",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Origin-Agent-Cluster": "?1",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), fullscreen=(self)",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: https://*.supabase.co; "
        "object-src 'none'; "
        "frame-src 'none'; "
        "style-src 'self'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


VERSIONED_STATIC_SUFFIXES = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}


def should_write_response_body(command: str | None) -> bool:
    return (command or "GET") != "HEAD"


def response_filename(filename: Any, fallback: str = "download") -> str:
    safe = Path(str(filename or "").replace("\\", "/")).name.strip()
    safe = re.sub(r"[\r\n\"]+", "", safe).strip(" .")
    return safe[:180] or fallback


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["result"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def static_file_cache_control(request_path: str, file_path: Path) -> str:
    parsed = urllib.parse.urlparse(request_path or "")
    is_versioned_static = parsed.path.startswith("/static/") and bool(urllib.parse.parse_qs(parsed.query).get("v"))
    if is_versioned_static and file_path.suffix.lower() in VERSIONED_STATIC_SUFFIXES:
        return "private, max-age=300, must-revalidate"
    return "no-store"


def file_etag(payload: bytes) -> str:
    return f'"{hashlib.sha256(payload).hexdigest()[:32]}"'


def last_modified_http_date(modified_at: float) -> str:
    return email.utils.formatdate(modified_at, usegmt=True)


def client_has_fresh_file(headers: Any, modified_at: float, etag: str = "") -> bool:
    if_none_match = str(headers.get("If-None-Match", "") if hasattr(headers, "get") else "").strip()
    if etag and if_none_match:
        supplied = {item.strip() for item in if_none_match.split(",")}
        if etag in supplied or "*" in supplied:
            return True
    if_modified_since = str(headers.get("If-Modified-Since", "") if hasattr(headers, "get") else "").strip()
    if not if_modified_since:
        return False
    try:
        parsed = email.utils.parsedate_to_datetime(if_modified_since)
    except (TypeError, ValueError):
        return False
    if parsed is None:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp() >= int(modified_at)
