#!/usr/bin/env python3
"""Privately set a GitHub Actions secret from the clipboard."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def read_clipboard_json() -> str:
    result = subprocess.run(["pbpaste"], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def validate_service_account_json(raw_json: str) -> dict[str, str]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"That was not valid JSON: {exc}") from exc

    required = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [key for key in required if not str(payload.get(key) or "").strip()]
    if missing:
        raise ValueError(f"Missing required service-account fields: {', '.join(missing)}")
    if payload.get("type") != "service_account":
        raise ValueError('The JSON "type" must be "service_account".')
    if "BEGIN PRIVATE KEY" not in payload.get("private_key", ""):
        raise ValueError("The JSON does not contain a service-account private key.")
    return payload


def validate_automation_token(raw_token: str) -> str:
    token = raw_token.strip()
    if not token:
        raise ValueError("Token is blank.")
    if token.startswith("{") or '"type"' in token or '"private_key"' in token or '"client_email"' in token:
        raise ValueError("Clipboard looks like Google service-account JSON, not the ChillCRM automation token.")
    if "\n" in token or "\r" in token:
        raise ValueError("Automation token should be a single line.")
    if len(token) < 20:
        raise ValueError("Automation token looks too short.")
    return token


def validate_granola_api_key(raw_token: str) -> str:
    token = raw_token.strip()
    if not token:
        raise ValueError("Granola API key is blank.")
    if token.startswith("{") or '"type"' in token or '"private_key"' in token or '"client_email"' in token:
        raise ValueError("Clipboard looks like Google service-account JSON, not a Granola API key.")
    if "\n" in token or "\r" in token:
        raise ValueError("Granola API key should be a single line.")
    if not token.startswith("grn_"):
        raise ValueError("Granola API key should begin with grn_.")
    if len(token) < 20:
        raise ValueError("Granola API key looks too short.")
    return token


def set_github_secret(secret_name: str, secret_value: str) -> None:
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI is not installed or not available in this Terminal path.")

    subprocess.run([gh, "secret", "set", secret_name], input=secret_value, text=True, check=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: set_github_actions_secret_from_clipboard.py SECRET_NAME")
        return 1
    secret_name = sys.argv[1].strip()
    raw_value = read_clipboard_json()
    if not raw_value:
        print("Clipboard is empty. Nothing changed.")
        return 1

    try:
        if secret_name == "GOOGLE_SERVICE_ACCOUNT_JSON":
            payload = validate_service_account_json(raw_value)
            value = raw_value
            print()
            print("JSON validated.")
            print(f"Service account email to share the Google Sheet with: {payload['client_email']}")
            print()
        elif secret_name == "CHILLCRM_AUTOMATION_TOKEN":
            value = validate_automation_token(raw_value)
            print()
            print("Automation token validated.")
            print()
        elif secret_name == "GRANOLA_API_KEY":
            value = validate_granola_api_key(raw_value)
            print()
            print("Granola API key validated.")
            print()
        else:
            print(f"Unsupported secret name: {secret_name}")
            return 1
    except ValueError as exc:
        print(f"Validation failed: {exc}")
        return 1

    try:
        set_github_secret(secret_name, value)
    except Exception as exc:
        print(f"Could not set the GitHub secret automatically: {exc}")
        print()
        print(f"Manual fallback: add the clipboard value as GitHub secret {secret_name}.")
        return 1

    print(f"GitHub secret {secret_name} has been set.")
    print("No secret value was written to project files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
