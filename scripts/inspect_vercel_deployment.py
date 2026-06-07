#!/usr/bin/env python3
"""Fetch non-secret Vercel deployment diagnostics."""

from __future__ import annotations

import csv
import getpass
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
VERCEL_API = "https://api.vercel.com"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"


def prompt_secret(label: str, env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    return getpass.getpass(f"{label}: ").strip()


def request_json(path: str, token: str, query: dict[str, str] | None = None) -> Any:
    url = f"{VERCEL_API}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def deployment_id_from_report() -> str:
    report = REPORTS_DIR / "vercel_staging_deployment_status.md"
    if not report.exists():
        return ""
    for line in report.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Deployment ID:"):
            return line.split("`", 2)[1].strip()
    return ""


def simplify_event(event: dict[str, Any]) -> dict[str, str]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    text = (
        event.get("text")
        or event.get("message")
        or payload.get("text")
        or payload.get("message")
        or payload.get("info")
        or ""
    )
    return {
        "created": str(event.get("created") or event.get("createdAt") or ""),
        "type": str(event.get("type") or event.get("name") or payload.get("type") or ""),
        "status": str(event.get("status") or payload.get("status") or ""),
        "text": " ".join(str(text).split()),
    }


def flatten_files(entries: Any, prefix: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not isinstance(entries, list):
        return rows
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "")
        path = f"{prefix}/{name}".strip("/")
        entry_type = str(entry.get("type") or "")
        rows.append({"path": path, "type": entry_type, "content_type": str(entry.get("contentType") or "")})
        rows.extend(flatten_files(entry.get("children"), path))
    return rows


def write_report(deployment: dict[str, Any], events: list[dict[str, str]], files: list[dict[str, str]]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    md = REPORTS_DIR / "vercel_deployment_diagnostics.md"
    csv_path = REPORTS_DIR / "vercel_deployment_diagnostics.csv"
    normalized_paths = {str(row.get("path") or "").removeprefix("src/") for row in files}

    lines = [
        "# Vercel Deployment Diagnostics",
        "",
        "This report records non-secret deployment state and build events from Vercel.",
        "",
        "## Deployment",
        "",
        f"- ID: `{deployment.get('uid') or deployment.get('id')}`.",
        f"- State: `{deployment.get('readyState') or deployment.get('status')}`.",
        f"- URL: `https://{deployment.get('url')}`." if deployment.get("url") else "- URL: pending.",
        "",
        "## Recent Events",
        "",
        "| Created | Type | Status | Text |",
        "| --- | --- | --- | --- |",
    ]
    for event in events:
        text = event["text"].replace("|", "/")
        lines.append(f"| {event['created']} | {event['type']} | {event['status']} | {text} |")
    lines.extend([
        "",
        "## Deployment Files",
        "",
        f"- File tree entries: `{len(files)}`.",
        f"- `api/index.py` present: `{'yes' if 'api/index.py' in normalized_paths else 'no'}`.",
        "",
        "| Path | Type | Content Type |",
        "| --- | --- | --- |",
    ])
    for row in files[:250]:
        lines.append(f"| {row['path']} | {row['type']} | {row['content_type']} |")

    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["created", "type", "status", "text"])
        writer.writeheader()
        writer.writerows(events)
    with (REPORTS_DIR / "vercel_deployment_files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "type", "content_type"])
        writer.writeheader()
        writer.writerows(files)


def main() -> int:
    token = prompt_secret("Vercel token", "VERCEL_TOKEN")
    deployment_id = (os.environ.get("VERCEL_DEPLOYMENT_ID") or deployment_id_from_report()).strip()
    if not token:
        raise RuntimeError("Vercel token is required.")
    if not deployment_id:
        raise RuntimeError("Deployment ID is required.")

    team_slug = os.environ.get("VERCEL_TEAM_SLUG", DEFAULT_TEAM_SLUG)
    query = {"slug": team_slug}
    deployment = request_json(f"/v13/deployments/{deployment_id}", token, query)

    raw_events: list[dict[str, Any]] = []
    for endpoint in (f"/v2/deployments/{deployment_id}/events", f"/v3/deployments/{deployment_id}/events"):
        try:
            payload = request_json(endpoint, token, query)
        except Exception:
            continue
        if isinstance(payload, dict):
            events = payload.get("events") or payload.get("logs") or []
        else:
            events = payload
        if isinstance(events, list):
            raw_events.extend(event for event in events if isinstance(event, dict))
        if raw_events:
            break

    events = [simplify_event(event) for event in raw_events]
    try:
        files_payload = request_json(f"/v6/deployments/{deployment_id}/files", token, query)
        files = flatten_files(files_payload)
    except Exception:
        files = []

    write_report(deployment, events, files)
    print(json.dumps({"deployment_id": deployment_id, "state": deployment.get("readyState"), "events": len(events), "files": len(files)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
