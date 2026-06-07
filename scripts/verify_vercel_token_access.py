#!/usr/bin/env python3
"""Verify a Vercel token can access the linked CHILLCRM project."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
VERCEL_API = "https://api.vercel.com"
LINK_PATH = PROJECT_ROOT / ".vercel" / "project.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_link() -> dict[str, str]:
    if not LINK_PATH.exists():
        return {}
    try:
        payload = json.loads(LINK_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def prompt_secret(env_name: str, label: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def scrub(text: str) -> str:
    text = re.sub(r"\b(vcp_|vck_)[A-Za-z0-9._-]+", r"\1[redacted]", text)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9._-]+", r"\1[redacted]", text, flags=re.IGNORECASE)
    return " ".join(text.split())[:700]


def request_json(path: str, token: str, query: dict[str, str] | None = None) -> dict[str, Any]:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed with {exc.code}: {scrub(body)}") from exc


def add_step(rows: list[dict[str, Any]], key: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "step",
            "key": key,
            "status": status,
            "evidence": scrub(evidence),
            "provider_calls": "metadata_read_only",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


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
        "# Vercel Token Access Check",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that a Vercel API token can access the linked CHILLCRM project metadata. It does not deploy, update environment variables, expose token values, unlock writes, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Project name: `{summary.get('project_name') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        f"- Token source: {summary.get('token_source')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        "- Provider calls: metadata_read_only.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "A pass here means the token can see the linked Vercel project and read environment metadata. The owner recovery deployment still runs separately through the guarded launcher.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(rows: list[dict[str, Any]], *, link: dict[str, str], token_source: str) -> dict[str, Any]:
    steps = [row for row in rows if row["row_type"] == "step"]
    failed = [row for row in steps if row["status"] == "failed"]
    input_required = [row for row in steps if row["status"] == "input_required"]
    passed = [row for row in steps if row["status"] == "passed"]
    status = "vercel_token_access_failed" if failed else "input_required_vercel_token" if input_required else "vercel_token_access_passed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "vercel_token_access_passed" else "blocked_until_working_vercel_token",
        "project_id": link.get("projectId", ""),
        "project_name": link.get("projectName", ""),
        "team_slug": link.get("teamSlug", ""),
        "token_source": token_source,
        "passed": len(passed),
        "failed": len(failed),
        "input_required": len(input_required),
    }
    all_rows = [summary, *steps]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "vercel_token_access_check.csv", all_rows)
    write_report(REPORTS_DIR / "vercel_token_access_check.md", all_rows)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a Vercel token can access the linked CHILLCRM project.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt privately for VERCEL_TOKEN if missing.")
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    link = read_link()
    project_id = link.get("projectId", "")
    team_slug = link.get("teamSlug", "")
    org_id = link.get("orgId", "")
    if not project_id:
        add_step(rows, "project_link", "failed", ".vercel/project.json is missing a projectId.")
        summary = persist(rows, link=link, token_source="not_requested")
        print(json.dumps(summary, indent=2))
        return 1

    token, token_source = prompt_secret("VERCEL_TOKEN", "Vercel API token", prompt=args.prompt_secrets)
    if not token:
        add_step(rows, "vercel_token", "input_required", "Missing Vercel API token.")
        summary = persist(rows, link=link, token_source="missing")
        print(json.dumps(summary, indent=2))
        return 1

    if not (token.startswith("vcp_") or token.startswith("vck_")):
        add_step(rows, "token_shape", "failed", "Token does not look like a Vercel API token. Use the Vercel API token, not the Vercel project passcode.")
        summary = persist(rows, link=link, token_source=token_source)
        print(json.dumps(summary, indent=2))
        return 1
    add_step(rows, "token_shape", "passed", "Token shape matches a Vercel API token prefix.")

    queries = []
    if team_slug:
        queries.append(("team_slug", {"slug": team_slug}))
    if org_id:
        queries.append(("team_id", {"teamId": org_id}))
    queries.append(("no_team_scope", {}))

    user_error = ""
    try:
        user = request_json("/v2/user", token)
        account = user.get("user") or user
        add_step(rows, "account_visible", "passed", f"Vercel account visible; username={account.get('username') or 'available'}.")
    except RuntimeError as exc:
        user_error = str(exc)
        add_step(rows, "account_visible", "failed", user_error)

    project_payload: dict[str, Any] | None = None
    project_errors: list[str] = []
    for label, query in queries:
        try:
            project_payload = request_json(f"/v9/projects/{project_id}", token, query)
            add_step(rows, "project_visible", "passed", f"Project metadata visible using {label}; name={project_payload.get('name') or 'available'}.")
            break
        except RuntimeError as exc:
            project_errors.append(f"{label}: {exc}")
    if not project_payload:
        add_step(rows, "project_visible", "failed", "; ".join(project_errors) or "Project metadata was not visible.")

    if project_payload:
        env_ok = False
        env_errors: list[str] = []
        for label, query in queries:
            try:
                env_payload = request_json(f"/v10/projects/{project_id}/env", token, query)
                env_count = len(env_payload.get("envs") or env_payload.get("env") or [])
                add_step(rows, "environment_metadata_visible", "passed", f"Environment metadata visible using {label}; env_count={env_count}.")
                env_ok = True
                break
            except RuntimeError as exc:
                env_errors.append(f"{label}: {exc}")
        if not env_ok:
            add_step(rows, "environment_metadata_visible", "failed", "; ".join(env_errors) or "Environment metadata was not visible.")

    summary = persist(rows, link=link, token_source=token_source)
    print(json.dumps(summary, indent=2))
    return 0 if summary["production_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
