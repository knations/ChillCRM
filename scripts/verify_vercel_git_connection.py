#!/usr/bin/env python3
"""Verify whether the linked Vercel project has a Git repository connected."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import subprocess
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


def prompt_secret(label: str, env_name: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def git_remote_repo() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    value = result.stdout.strip()
    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:").removesuffix(".git")
    elif "github.com/" in value:
        value = value.split("github.com/", 1)[1].removesuffix(".git")
    return value.strip("/")


def request_project(project_id: str, team_slug: str, token: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"slug": team_slug}) if team_slug else ""
    url = f"{VERCEL_API}/v9/projects/{urllib.parse.quote(project_id)}"
    if query:
        url += f"?{query}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vercel project lookup failed with {exc.code}: {raw[:400]}") from exc


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


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str, *, blocks_git_deploy: bool = True) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "blocks_git_deploy": "yes" if blocks_git_deploy else "no",
            "secret_values_stored": "no",
        }
    )


def safe_link_summary(link: dict[str, Any]) -> dict[str, Any]:
    deploy_hooks = link.get("deployHooks") if isinstance(link.get("deployHooks"), list) else []
    return {
        "type": link.get("type") or "",
        "org": link.get("org") or "",
        "repo": link.get("repo") or "",
        "repo_id": link.get("repoId") or "",
        "production_branch": link.get("productionBranch") or "",
        "sourceless": link.get("sourceless"),
        "deploy_hook_count": len(deploy_hooks),
        "deploy_hook_refs": ", ".join(str(item.get("ref") or "") for item in deploy_hooks if isinstance(item, dict) and item.get("ref")),
    }


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    local_link = read_vercel_link()
    project_id = args.project_id.strip() or local_link.get("projectId", "")
    team_slug = args.team_slug.strip() or local_link.get("teamSlug", "")
    expected_repo = args.expected_repo.strip().removesuffix(".git").strip("/")
    if not expected_repo:
        expected_repo = git_remote_repo()

    add_check(
        rows,
        "local_vercel_project_link",
        "pass" if project_id else "input_required",
        f"project_id={'present' if project_id else 'missing'}, team_slug={team_slug or 'missing'}",
    )

    token, token_source = prompt_secret("Vercel API token", "VERCEL_TOKEN", prompt=args.prompt_token)
    if not token:
        add_check(
            rows,
            "vercel_api_token",
            "input_required",
            "Missing Vercel API token. Run with --prompt-token or provide VERCEL_TOKEN as a one-shot environment variable.",
        )
        project: dict[str, Any] = {}
    else:
        try:
            project = request_project(project_id, team_slug, token)
            add_check(rows, "vercel_project_lookup", "pass", f"project={project.get('name') or project_id}; token_source={token_source}")
        except Exception as exc:
            project = {}
            add_check(rows, "vercel_project_lookup", "fail", str(exc))

    link = project.get("link") if isinstance(project.get("link"), dict) else {}
    link_summary = safe_link_summary(link)
    connected = link_summary["type"] == "github" and bool(link_summary["repo"])
    add_check(
        rows,
        "connected_git_repository",
        "pass" if connected else ("input_required" if not token else "fail"),
        (
            f"type={link_summary['type'] or 'missing'}, repo={link_summary['repo'] or 'missing'}, "
            f"production_branch={link_summary['production_branch'] or 'missing'}"
        ),
    )

    if expected_repo:
        expected_status = "pass" if link_summary["repo"].lower() == expected_repo.lower() else ("input_required" if not token else "fail")
        add_check(
            rows,
            "expected_repo_matches",
            expected_status,
            f"expected={expected_repo}, actual={link_summary['repo'] or 'missing'}",
        )
    else:
        add_check(
            rows,
            "expected_repo_matches",
            "warning",
            "No local git origin or --expected-repo was supplied, so the verifier can prove whether Git is connected but not whether it is the intended repo.",
            blocks_git_deploy=False,
        )

    if connected:
        rows.append(
            {
                "row_type": "git_link",
                "key": "vercel_git_link",
                "status": "pass",
                **link_summary,
                "secret_values_stored": "no",
            }
        )

    failed = [row for row in rows if row.get("status") == "fail"]
    input_required = [row for row in rows if row.get("status") == "input_required"]
    warnings = [row for row in rows if row.get("status") == "warning"]
    if failed:
        status = "vercel_git_connection_failed"
        gate = "blocked_until_vercel_git_connection_fixed"
    elif input_required:
        status = "input_required_vercel_git_connection"
        gate = "blocked_until_vercel_git_connection_verified"
    else:
        status = "vercel_git_connection_verified"
        gate = "pass"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": gate,
        "project_id": project_id,
        "team_slug": team_slug,
        "expected_repo": expected_repo,
        "connected_repo": link_summary["repo"],
        "git_type": link_summary["type"],
        "production_branch": link_summary["production_branch"],
        "failed": len(failed),
        "input_required": len(input_required),
        "warnings": len(warnings),
        "secret_values_stored": "no",
        "remote_push_performed": "no",
        "deploy_performed": "no",
    }
    return [summary, *rows]


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = rows[0]
    checks = [row for row in rows if row.get("row_type") == "check"]
    links = [row for row in rows if row.get("row_type") == "git_link"]
    lines = [
        "# Vercel Git Connection",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies whether the linked CHILLCRM Vercel project has a Git repository connected. It does not push to GitHub, deploy code, change Vercel settings, store secrets, unlock writes, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        f"- Expected repo: `{summary.get('expected_repo') or 'not supplied'}`.",
        f"- Connected repo: `{summary.get('connected_repo') or 'missing'}`.",
        f"- Git type: `{summary.get('git_type') or 'missing'}`.",
        f"- Production branch: `{summary.get('production_branch') or 'missing'}`.",
        f"- Failed checks: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Warnings: {summary.get('warnings')}.",
        "- Secret values stored: no.",
        "- Remote push performed: no.",
        "- Deploy performed: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Blocks Git Deploy | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {row.get('blocks_git_deploy')} | {row.get('evidence')} |")
    lines.extend(["", "## Git Link", ""])
    if links:
        lines.append("| Type | Org | Repo | Production Branch | Repo ID | Deploy Hook Count | Deploy Hook Refs |")
        lines.append("| --- | --- | --- | --- | --- | ---: | --- |")
        for row in links:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("type") or ""),
                        str(row.get("org") or ""),
                        str(row.get("repo") or ""),
                        str(row.get("production_branch") or ""),
                        str(row.get("repo_id") or ""),
                        str(row.get("deploy_hook_count") or 0),
                        str(row.get("deploy_hook_refs") or ""),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No verified Git link recorded yet.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Vercel Git repository connection for CHILLCRM.")
    parser.add_argument("--prompt-token", action="store_true", help="Prompt privately for VERCEL_TOKEN if missing.")
    parser.add_argument("--expected-repo", default=os.environ.get("CHILLCRM_EXPECTED_GITHUB_REPO", ""))
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", ""))
    args = parser.parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "vercel_git_connection.csv", rows)
    write_report(REPORTS_DIR / "vercel_git_connection.md", rows)
    print(json.dumps(rows[0], indent=2))
    return 0 if rows[0]["status"] == "vercel_git_connection_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
