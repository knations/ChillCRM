"""Password and signed-session primitives for CHILLCRM."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


def b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def b64url_decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode((payload + padding).encode("ascii"))


def password_hash(password: str, iterations: int = 260_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${b64url_encode(salt)}${b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iteration_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iteration_text)
        expected = b64url_decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b64url_decode(salt_text), iterations)
        return hmac.compare_digest(actual, expected)
    except (binascii.Error, TypeError, ValueError):
        return False


def signed_session_token(payload: dict[str, Any], secret: str) -> str:
    encoded_payload = b64url_encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{b64url_encode(signature)}"


def verify_signed_session_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = b64url_encode(hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(encoded_signature, expected):
            return None
        payload = json.loads(b64url_decode(encoded_payload))
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
        return payload
    except (binascii.Error, json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
        return None
