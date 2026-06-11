#!/usr/bin/env python3
"""Set the server-side Zapier purchase webhook secret in Vercel."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
VERCEL_API = "https://api.vercel.com"
VERCEL_LINK_PATH = PROJECT_ROOT / ".vercel" / "project.json"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
DEFAULT_SECRET_KEY = "CHILLCRM_ZAPIER_WEBHOOK_SECRET"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def prompt_secret(label: str, env_name: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


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


def upsert_secret(token: str, project_id: str, query: dict[str, str], secret_key: str, secret_value: str) -> str:
    body = {
        "key": secret_key,
        "value": secret_value,
        "type": "encrypted",
        "target": ["production", "preview", "development"],
    }
    try:
        request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
        return "encrypted"
    except RuntimeError:
        body["type"] = "sensitive"
        request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
        return "sensitive"


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
    summary = rows[0]
    steps = [row for row in rows if row.get("row_type") == "step"]
    lines = [
        "# Vercel Zapier Webhook Secret Status",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records non-secret evidence for the CHILLCRM Zapier purchase webhook secret. It does not store the Vercel token or webhook secret, deploy code, unlock writes, create users, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        f"- Secret key: `{summary.get('secret_key')}`.",
        f"- Secret source: `{summary.get('secret_source')}`.",
        "- Secret values stored: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        lines.append(f"| {row.get('step')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    link = read_vercel_link()
    project_id = args.project_id.strip() or link.get("projectId", "")
    team_slug = args.team_slug.strip() or link.get("teamSlug", "") or DEFAULT_TEAM_SLUG
    team_id = link.get("orgId", "")
    query = team_query(team_id, team_slug)
    rows: list[dict[str, Any]] = []
    generated_secret = ""

    if not args.execute:
        rows.append(
            {
                "row_type": "step",
                "step": "execution_confirmation",
                "status": "input_required",
                "evidence": "Run with --execute after owner/operator approval to upsert the Zapier webhook secret in Vercel.",
            }
        )
    if not project_id:
        rows.append(
            {
                "row_type": "step",
                "step": "project_link",
                "status": "input_required",
                "evidence": "Missing Vercel project ID; link the project or pass --project-id.",
            }
        )

    token = ""
    token_source = "not_requested"
    secret_value = ""
    secret_source = "not_requested"
    if args.execute and project_id:
        token, token_source = prompt_secret("Vercel token", "VERCEL_TOKEN", prompt=args.prompt_token)
        if args.generate_secret:
            generated_secret = secrets.token_urlsafe(48)
            secret_value = generated_secret
            secret_source = "generated"
        else:
            secret_value, secret_source = prompt_secret(args.secret_key, args.secret_key, prompt=args.prompt_secret)
        if not token:
            rows.append(
                {
                    "row_type": "step",
                    "step": "vercel_token",
                    "status": "input_required",
                    "evidence": "Missing Vercel token. Use --prompt-token or VERCEL_TOKEN.",
                }
            )
        if not secret_value:
            rows.append(
                {
                    "row_type": "step",
                    "step": "webhook_secret",
                    "status": "input_required",
                    "evidence": f"Missing {args.secret_key}. Use --generate-secret, --prompt-secret, or the environment variable.",
                }
            )

    if token and secret_value:
        env_type = upsert_secret(token, project_id, query, args.secret_key, secret_value)
        rows.append(
            {
                "row_type": "step",
                "step": "zapier_webhook_secret_upsert",
                "status": "passed",
                "evidence": f"{args.secret_key} upserted for production, preview, and development as {env_type}; token_source={token_source}; secret_source={secret_source}; secret values not stored.",
            }
        )

    failed = [row for row in rows if row.get("status") == "failed"]
    input_required = [row for row in rows if row.get("status") == "input_required"]
    status = "vercel_zapier_webhook_secret_set" if not failed and not input_required else "input_required_vercel_zapier_webhook_secret"
    if failed:
        status = "vercel_zapier_webhook_secret_failed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "vercel_zapier_webhook_secret_set" else "blocked_until_webhook_secret_set",
        "project_id": project_id,
        "team_slug": team_slug,
        "secret_key": args.secret_key,
        "secret_source": secret_source,
        "execution_requested": "yes" if args.execute else "no",
        "secret_values_stored": "no",
        "provider_calls": "vercel_env_upsert" if token and secret_value else "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
    }
    return [summary, *rows], generated_secret


def main() -> int:
    parser = argparse.ArgumentParser(description="Set CHILLCRM Zapier purchase webhook secret in Vercel.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prompt-token", action="store_true")
    parser.add_argument("--prompt-secret", action="store_true")
    parser.add_argument("--generate-secret", action="store_true")
    parser.add_argument("--secret-key", default=DEFAULT_SECRET_KEY)
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", ""))
    args = parser.parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows, generated_secret = build_rows(args)
    write_csv(REPORTS_DIR / "vercel_zapier_webhook_secret_status.csv", rows)
    write_report(REPORTS_DIR / "vercel_zapier_webhook_secret_status.md", rows)
    output = dict(rows[0])
    if generated_secret:
        output["generated_webhook_secret_for_zapier"] = generated_secret
    print(json.dumps(output, indent=2))
    return 1 if rows[0]["status"].endswith("_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
