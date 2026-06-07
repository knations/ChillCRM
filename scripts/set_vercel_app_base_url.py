#!/usr/bin/env python3
"""Set the non-secret Vercel APP_BASE_URL for CHILLCRM."""

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
        "# Vercel APP_BASE_URL Cleanup",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the non-secret Vercel APP_BASE_URL cleanup for the CHILLCRM custom domain. It does not deploy code, unlock writes, create users, expose secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- App base URL: `{summary.get('app_base_url')}`.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        f"- Execution requested: {summary.get('execution_requested')}.",
        "- Secret values stored: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    app_base_url = args.app_base_url.rstrip("/")
    link = read_vercel_link()
    project_id = args.project_id.strip() or link.get("projectId", "")
    team_slug = args.team_slug.strip() or link.get("teamSlug", "") or DEFAULT_TEAM_SLUG
    team_id = link.get("orgId", "")
    query = team_query(team_id, team_slug)
    rows: list[dict[str, Any]] = []

    if not args.execute:
        rows.append(
            {
                "row_type": "step",
                "key": "execution_confirmation",
                "status": "input_required",
                "evidence": "Run with --execute after owner/operator approval to upsert APP_BASE_URL in Vercel.",
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

    token = ""
    token_source = "not_requested"
    if args.execute and project_id:
        token, token_source = prompt_secret("Vercel token", "VERCEL_TOKEN", prompt=args.prompt_token)
        if not token:
            rows.append(
                {
                    "row_type": "step",
                    "key": "vercel_token",
                    "status": "input_required",
                    "evidence": "Missing Vercel token. Use --prompt-token or VERCEL_TOKEN.",
                }
            )
    if token:
        body = {
            "key": "APP_BASE_URL",
            "value": app_base_url,
            "type": "plain",
            "target": ["production", "preview", "development"],
        }
        request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
        rows.append(
            {
                "row_type": "step",
                "key": "app_base_url_upsert",
                "status": "passed",
                "evidence": f"APP_BASE_URL upserted for production, preview, and development; token_source={token_source}; token value not stored.",
            }
        )

    failed = [row for row in rows if row["status"] == "failed"]
    input_required = [row for row in rows if row["status"] == "input_required"]
    status = "vercel_app_base_url_set" if not failed and not input_required else "input_required_vercel_app_base_url"
    if failed:
        status = "vercel_app_base_url_failed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "vercel_app_base_url_set" else "non_blocking_cleanup_pending",
        "app_base_url": app_base_url,
        "project_id": project_id,
        "team_slug": team_slug,
        "execution_requested": "yes" if args.execute else "no",
    }
    return [summary, *rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Set Vercel APP_BASE_URL for CHILLCRM custom domain.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prompt-token", action="store_true")
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", ""))
    args = parser.parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "vercel_app_base_url_cleanup.csv", rows)
    write_report(REPORTS_DIR / "vercel_app_base_url_cleanup.md", rows)
    summary = rows[0]
    print(json.dumps(summary, indent=2))
    return 1 if summary["status"].endswith("_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
