"""File and image upload helpers for CHILLCRM."""

from __future__ import annotations

import base64
import binascii
import mimetypes
import re
from pathlib import Path
from typing import Any


PROFILE_IMAGE_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
PROFILE_IMAGE_MAX_BYTES = 2_500_000
RECORD_FILE_MAX_BYTES = 3_000_000


def normalize_profile_image_type(content_type: Any) -> str:
    normalized = str(content_type or "").split(";", 1)[0].strip().lower()
    if normalized == "image/jpg":
        normalized = "image/jpeg"
    if normalized not in PROFILE_IMAGE_ALLOWED_CONTENT_TYPES:
        raise ValueError("Use a JPEG, PNG, or WebP image.")
    return normalized


def profile_image_magic_matches(content_type: str, payload: bytes) -> bool:
    if content_type == "image/jpeg":
        return payload.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return payload.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"
    return False


def decode_profile_image_upload(payload: dict[str, Any], max_bytes: int = PROFILE_IMAGE_MAX_BYTES) -> tuple[bytes, str]:
    data_url = str(payload.get("image_data_url") or "").strip()
    encoded = str(payload.get("image_base64") or "").strip()
    if data_url:
        match = re.match(r"^data:([^;,]+);base64,(.+)$", data_url, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError("Profile image upload was not a valid image payload.")
        content_type = normalize_profile_image_type(match.group(1))
        encoded = match.group(2).strip()
    else:
        content_type = normalize_profile_image_type(payload.get("content_type"))
    if not encoded:
        raise ValueError("Choose an image before uploading.")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Profile image upload was not valid base64.") from exc
    if not image_bytes:
        raise ValueError("Choose an image before uploading.")
    if len(image_bytes) > max_bytes:
        raise ValueError("Profile image is too large after resizing. Choose a smaller image.")
    if not profile_image_magic_matches(content_type, image_bytes):
        raise ValueError("Profile image content did not match its image type.")
    return image_bytes, content_type


def optional_dimension(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(parsed, 10_000))


def safe_original_filename(value: Any) -> str | None:
    filename = Path(str(value or "").replace("\\", "/")).name.strip()
    if not filename:
        return None
    safe = re.sub(r"[^A-Za-z0-9._ -]+", "_", filename).strip(" ._-")
    return safe[:180] or None


def normalize_record_file_type(content_type: Any, filename: Any = None) -> str:
    normalized = str(content_type or "").split(";", 1)[0].strip().lower()
    if not normalized and filename:
        normalized = (mimetypes.guess_type(str(filename))[0] or "").strip().lower()
    if not normalized:
        normalized = "application/octet-stream"
    return normalized[:120]


def decode_record_file_upload(payload: dict[str, Any], max_bytes: int = RECORD_FILE_MAX_BYTES) -> tuple[bytes, str]:
    filename = safe_original_filename(payload.get("filename")) or "attachment"
    data_url = str(payload.get("file_data_url") or "").strip()
    encoded = str(payload.get("file_base64") or "").strip()
    if data_url:
        match = re.match(r"^data:([^;,]+);base64,(.+)$", data_url, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError("File upload was not a valid file payload.")
        content_type = normalize_record_file_type(match.group(1), filename)
        encoded = match.group(2).strip()
    else:
        content_type = normalize_record_file_type(payload.get("content_type"), filename)
    if not encoded:
        raise ValueError("Choose a file before uploading.")
    try:
        file_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("File upload was not valid base64.") from exc
    if not file_bytes:
        raise ValueError("Choose a file before uploading.")
    if len(file_bytes) > max_bytes:
        raise ValueError("File is too large. Choose a file under 3 MB for now.")
    return file_bytes, content_type


def record_file_storage_key(record_type: str, record_id: int, digest: str, original_filename: str | None, content_type: str) -> str:
    safe_name = safe_original_filename(original_filename) or "attachment"
    suffix = Path(safe_name).suffix.strip().lower()
    if not suffix:
        guessed = mimetypes.guess_extension(content_type) or ".bin"
        suffix = guessed if guessed.startswith(".") else f".{guessed}"
        safe_name = f"{Path(safe_name).stem or 'attachment'}{suffix}"
    return f"record-files/{record_type}/{record_id}/{digest[:24]}-{safe_name}"


def profile_image_storage_key(record_id: int, digest: str, content_type: str) -> str:
    extension = PROFILE_IMAGE_ALLOWED_CONTENT_TYPES[content_type]
    return f"profile-images/people/{record_id}/{digest[:24]}.{extension}"


def profile_image_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "content_type": row.get("content_type"),
        "bytes": row.get("bytes"),
        "sha256": row.get("sha256"),
        "width": row.get("width"),
        "height": row.get("height"),
        "original_filename": row.get("original_filename"),
        "storage_backend": row.get("storage_backend"),
        "updated_at": row.get("updated_at") or row.get("created_at"),
    }


def record_file_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "record_type": row.get("record_type"),
        "record_id": row.get("record_id"),
        "original_filename": row.get("original_filename"),
        "content_type": row.get("content_type"),
        "bytes": row.get("bytes"),
        "sha256": row.get("sha256"),
        "storage_backend": row.get("storage_backend"),
        "updated_at": row.get("updated_at") or row.get("created_at"),
    }
