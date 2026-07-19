#!/usr/bin/env python3
"""Set CHILLCRM Twilio webhook configuration in Vercel.

Secrets are read from environment variables or private prompts and are not
written to project files or reports.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
VERCEL_API = "https://api.vercel.com"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
DEFAULT_APP_BASE_URL = "https://chillcrm.app"
DEFAULT_TWILIO_PHONE_NUMBER = "6147146700"
VERCEL_LINK_PATH = PROJECT_ROOT / ".vercel" / "project.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prompt_secret(label: str, env_name: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def read_vercel_link() -> dict[str, str]:
    if not VERCEL_LINK_PATH.exists():
        return {}
    try:
        payload = json.loads(VERCEL_LINK_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def team_query(team_id: str | None, slug: str | None) -> dict[str, str]:
    if slug:
        return {"slug": slug}
    if team_id:
        return {"teamId": team_id}
    return {}


def request_json(
    method: str,
    path: str,
    token: str,
    *,
    query: dict[str, str] | None = None,
    body: Any | None = None,
) -> dict[str, Any]:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {raw[:500]}") from exc


def upsert_env(
    token: str,
    project_id: str,
    query: dict[str, str],
    key: str,
    value: str,
    *,
    secret: bool,
) -> str:
    body = {
        "key": key,
        "value": value,
        "type": "encrypted" if secret else "plain",
        "target": ["production", "preview", "development"],
    }
    try:
        request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
        return "upserted_encrypted" if secret else "upserted_plain"
    except RuntimeError as exc:
        if not secret:
            raise
        body["type"] = "sensitive"
        request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
        return "upserted_sensitive"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["result"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    steps = [row for row in rows if row["row_type"] == "step"]
    lines = [
        "# Vercel Twilio Config",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records Vercel environment configuration for CHILLCRM Twilio call recording. It does not deploy code, expose secrets, change CRM records, or configure the Twilio phone number webhook.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- App base URL: `{summary.get('app_base_url')}`.",
        f"- Twilio CRM number: `{summary.get('twilio_phone_number')}`.",
        f"- Forward-to configured: {summary.get('forward_to_configured')}.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        "- Secret values stored in report: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        evidence = str(row.get("evidence") or "").replace("|", "/")
        lines.append(f"| {row.get('key')} | {row.get('status')} | {evidence} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_phone(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit() or ch == "+")


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    link = read_vercel_link()
    project_id = args.project_id.strip() or link.get("projectId", "")
    team_slug = args.team_slug.strip() or link.get("teamSlug", "") or DEFAULT_TEAM_SLUG
    team_id = link.get("orgId", "")
    query = team_query(team_id, team_slug)
    app_base_url = args.app_base_url.rstrip("/")
    twilio_phone_number = clean_phone(args.twilio_phone_number)
    forward_to = clean_phone(args.forward_to or os.environ.get("CHILLCRM_TWILIO_FORWARD_TO", ""))
    rows: list[dict[str, Any]] = []

    if not args.execute:
        rows.append(
            {
                "row_type": "step",
                "key": "execution_confirmation",
                "status": "input_required",
                "evidence": "Run with --execute after owner/operator approval to upsert Twilio env in Vercel.",
            }
        )
    if not project_id:
        rows.append(
            {
                "row_type": "step",
                "key": "project_link",
                "status": "input_required",
                "evidence": "Missing Vercel project ID; link the project or pass --project-id.",
            }
        )
    if not twilio_phone_number:
        rows.append(
            {
                "row_type": "step",
                "key": "twilio_phone_number",
                "status": "input_required",
                "evidence": "Missing CHILLCRM_TWILIO_PHONE_NUMBER.",
            }
        )
    if not forward_to:
        rows.append(
            {
                "row_type": "step",
                "key": "twilio_forward_to",
                "status": "input_required",
                "evidence": "Missing CHILLCRM_TWILIO_FORWARD_TO.",
            }
        )

    token = ""
    twilio_auth_token = ""
    token_source = "not_requested"
    twilio_token_source = "not_requested"
    if args.execute and project_id and twilio_phone_number and forward_to:
        token, token_source = prompt_secret("Vercel token", "VERCEL_TOKEN", prompt=args.prompt_secrets)
        twilio_auth_token, twilio_token_source = prompt_secret(
            "Twilio Auth Token",
            "CHILLCRM_TWILIO_AUTH_TOKEN",
            prompt=args.prompt_secrets,
        )
        if not token:
            rows.append(
                {
                    "row_type": "step",
                    "key": "vercel_token",
                    "status": "input_required",
                    "evidence": "Missing Vercel token. Use --prompt-secrets or VERCEL_TOKEN.",
                }
            )
        if not twilio_auth_token:
            rows.append(
                {
                    "row_type": "step",
                    "key": "twilio_auth_token",
                    "status": "input_required",
                    "evidence": "Missing Twilio Auth Token. Use --prompt-secrets or CHILLCRM_TWILIO_AUTH_TOKEN.",
                }
            )
    if token and twilio_auth_token:
        env_values = [
            ("APP_BASE_URL", app_base_url, False),
            ("CHILLCRM_TWILIO_AUTH_TOKEN", twilio_auth_token, True),
            ("CHILLCRM_TWILIO_PHONE_NUMBER", twilio_phone_number, False),
            ("CHILLCRM_TWILIO_FORWARD_TO", forward_to, False),
        ]
        for key, value, secret in env_values:
            status = upsert_env(token, project_id, query, key, value, secret=secret)
            evidence = "value set; secret not reported" if secret else "value set"
            rows.append({"row_type": "step", "key": key, "status": status, "evidence": evidence})
        rows.append(
            {
                "row_type": "step",
                "key": "credential_sources",
                "status": "recorded",
                "evidence": f"vercel_token_source={token_source}; twilio_auth_token_source={twilio_token_source}; values not stored.",
            }
        )

    failed = [row for row in rows if row["status"] == "failed"]
    input_required = [row for row in rows if row["status"] == "input_required"]
    status = "vercel_twilio_config_set" if not failed and not input_required else "input_required_vercel_twilio_config"
    if failed:
        status = "vercel_twilio_config_failed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "app_base_url": app_base_url,
        "twilio_phone_number": twilio_phone_number,
        "forward_to_configured": "yes" if forward_to else "no",
        "project_id": project_id,
        "team_slug": team_slug,
        "execution_requested": "yes" if args.execute else "no",
    }
    return [summary, *rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Set Vercel Twilio env for CHILLCRM call recording.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prompt-secrets", action="store_true")
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument("--twilio-phone-number", default=DEFAULT_TWILIO_PHONE_NUMBER)
    parser.add_argument("--forward-to", default="")
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", ""))
    args = parser.parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "vercel_twilio_config.csv", rows)
    write_report(REPORTS_DIR / "vercel_twilio_config.md", rows)
    print(json.dumps(rows[0], indent=2))
    return 1 if rows[0]["status"].endswith("_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
