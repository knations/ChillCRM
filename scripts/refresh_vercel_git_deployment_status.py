#!/usr/bin/env python3
"""Refresh non-secret Vercel deployment evidence for the connected Git deployment."""

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
DEFAULT_PROJECT_ID = "prj_BW7lf5NVtOGjZ8eA28pIVOBIACgh"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
DEFAULT_TARGET = "production"


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


def run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def normalize_github_repo(value: str) -> str:
    value = value.strip().removesuffix(".git").strip("/")
    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:")
    elif "github.com/" in value:
        value = value.split("github.com/", 1)[1]
    return value.strip("/")


def local_github_repo() -> str:
    return normalize_github_repo(run_git("remote", "get-url", "origin"))


def request_json(path: str, token: str, query: dict[str, str]) -> Any:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
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
        raise RuntimeError(f"Vercel request failed with {exc.code}: {raw[:500]}") from exc


def deployment_created_at(deployment: dict[str, Any]) -> int:
    value = deployment.get("createdAt") or deployment.get("created")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def deployment_url(deployment: dict[str, Any]) -> str:
    url = str(deployment.get("url") or "")
    if not url:
        return ""
    return url if url.startswith("https://") else f"https://{url}"


def deployment_id(deployment: dict[str, Any]) -> str:
    return str(deployment.get("uid") or deployment.get("id") or "")


def deployment_state(deployment: dict[str, Any]) -> str:
    return str(deployment.get("readyState") or deployment.get("state") or deployment.get("status") or "")


def deployment_target(deployment: dict[str, Any]) -> str:
    return str(deployment.get("target") or "")


def deployment_meta(deployment: dict[str, Any]) -> dict[str, Any]:
    meta = deployment.get("meta")
    return meta if isinstance(meta, dict) else {}


def meta_value(meta: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = meta.get(key)
        if value:
            return str(value)
    return ""


def list_latest_deployment(project_id: str, team_slug: str, target: str, token: str) -> dict[str, Any]:
    query = {
        "projectId": project_id,
        "target": target,
        "limit": "20",
    }
    if team_slug:
        query["slug"] = team_slug
    payload = request_json("/v6/deployments", token, query)
    deployments = payload.get("deployments") if isinstance(payload, dict) else []
    if not isinstance(deployments, list):
        deployments = []
    candidates = [item for item in deployments if isinstance(item, dict)]
    if target:
        targeted = [item for item in candidates if deployment_target(item) in {"", target}]
        candidates = targeted or candidates
    candidates.sort(key=deployment_created_at, reverse=True)
    return candidates[0] if candidates else {}


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "check",
            "step": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "secret_values_stored": "no",
        }
    )


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    local_link = read_vercel_link()
    project_id = args.project_id.strip() or local_link.get("projectId", "") or DEFAULT_PROJECT_ID
    team_slug = args.team_slug.strip() or local_link.get("teamSlug", "") or DEFAULT_TEAM_SLUG
    target = args.target.strip() or DEFAULT_TARGET
    expected_sha = run_git("rev-parse", "HEAD")
    expected_repo = local_github_repo()
    rows: list[dict[str, Any]] = []

    token, token_source = prompt_secret("Vercel API token", "VERCEL_TOKEN", prompt=args.prompt_token)
    if not token:
        add_check(rows, "vercel_token", "input_required", "Missing Vercel API token. Run with --prompt-token or VERCEL_TOKEN.")
        deployment: dict[str, Any] = {}
    else:
        try:
            deployment = list_latest_deployment(project_id, team_slug, target, token)
            add_check(
                rows,
                "vercel_deployment_lookup",
                "pass" if deployment else "input_required",
                f"token_source={token_source}; deployment={'present' if deployment else 'missing'}",
            )
        except Exception as exc:
            deployment = {}
            add_check(rows, "vercel_deployment_lookup", "fail", str(exc))

    meta = deployment_meta(deployment)
    actual_sha = meta_value(meta, "githubCommitSha", "githubCommitSHA", "gitCommitSha")
    actual_ref = meta_value(meta, "githubCommitRef", "gitCommitRef", "branch")
    actual_repo = "/".join(
        part
        for part in [
            meta_value(meta, "githubOrg", "githubOwner", "gitOrg"),
            meta_value(meta, "githubRepo", "gitRepo"),
        ]
        if part
    )
    if not actual_repo:
        actual_repo = meta_value(meta, "repo", "repository")
    actual_repo = normalize_github_repo(actual_repo)
    state = deployment_state(deployment)
    target_seen = deployment_target(deployment) or target

    state_ok = state == "READY"
    commit_ok = bool(expected_sha and actual_sha and actual_sha.startswith(expected_sha[:12]))
    repo_ok = not expected_repo or not actual_repo or expected_repo.lower() == actual_repo.lower()
    target_ok = target_seen == target

    if deployment:
        add_check(rows, "deployment_ready", "pass" if state_ok else "fail", f"state={state or 'missing'}")
        add_check(
            rows,
            "deployment_commit_matches_local_head",
            "pass" if commit_ok else "fail",
            f"local_head={expected_sha[:12] or 'missing'}; deployment_sha={actual_sha[:12] or 'missing'}",
        )
        add_check(
            rows,
            "deployment_repo_matches_origin",
            "pass" if repo_ok else "fail",
            f"origin_repo={expected_repo or 'missing'}; deployment_repo={actual_repo or 'missing_or_unreported'}",
        )
        add_check(rows, "deployment_target", "pass" if target_ok else "fail", f"target={target_seen or 'missing'}")

    failed = [row for row in rows if row.get("status") == "fail"]
    input_required = [row for row in rows if row.get("status") == "input_required"]
    if failed:
        status = "vercel_git_deployment_refresh_failed"
        gate = "blocked_until_vercel_git_deployment_matches_local_head"
    elif input_required:
        status = "input_required_vercel_git_deployment_refresh"
        gate = "blocked_until_vercel_git_deployment_verified"
    else:
        status = "vercel_git_deployment_current"
        gate = "pass"

    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": gate,
        "project_id": project_id,
        "team_slug": team_slug,
        "target": target,
        "deployment_id": deployment_id(deployment),
        "ready_state": state,
        "url": deployment_url(deployment),
        "local_head": expected_sha,
        "deployment_sha": actual_sha,
        "github_ref": actual_ref,
        "origin_repo": expected_repo,
        "deployment_repo": actual_repo,
        "failed": len(failed),
        "input_required": len(input_required),
        "secret_values_stored": "no",
        "provider_calls": "vercel_deployments_read_only" if token else "no",
        "deploy_performed": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
    }
    return [summary, *rows]


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


def write_git_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = rows[0]
    checks = [row for row in rows if row.get("row_type") == "check"]
    lines = [
        "# Vercel Git Deployment Status",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report reads Vercel deployment metadata for the connected GitHub deployment. It does not deploy code, write provider settings, store secrets, unlock writes, change CRM records, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Project ID: `{summary.get('project_id') or 'missing'}`.",
        f"- Team slug: `{summary.get('team_slug') or 'missing'}`.",
        f"- Target: `{summary.get('target') or 'missing'}`.",
        f"- Deployment ID: `{summary.get('deployment_id') or 'missing'}`.",
        f"- Ready state: `{summary.get('ready_state') or 'missing'}`.",
        f"- URL: `{summary.get('url') or 'missing'}`.",
        f"- Local HEAD: `{str(summary.get('local_head') or '')[:12] or 'missing'}`.",
        f"- Deployment SHA: `{str(summary.get('deployment_sha') or '')[:12] or 'missing'}`.",
        f"- GitHub ref: `{summary.get('github_ref') or 'missing'}`.",
        f"- Origin repo: `{summary.get('origin_repo') or 'missing'}`.",
        f"- Deployment repo: `{summary.get('deployment_repo') or 'missing_or_unreported'}`.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        "- Secret values stored: no.",
        "- Deploy performed: no.",
        "- CRM record writes: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row.get('step')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_staging_deployment_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = rows[0]
    checks = [row for row in rows if row.get("row_type") == "check"]
    lines = [
        "# Vercel Staging Deployment Status",
        "",
        "This report records non-secret CHILLCRM Vercel deployment facts for the connected GitHub production deployment. It does not include the Vercel token, database password, session secret, bootstrap password hash, service-role key, or bootstrap password.",
        "",
        "## Summary",
        "",
        "- Project: `chillcrm`.",
        f"- Deployment ID: `{summary.get('deployment_id') or 'missing'}`.",
        f"- Ready state: `{summary.get('ready_state') or 'missing'}`.",
        f"- URL: `{summary.get('url') or 'missing'}`.",
        f"- Target: `{summary.get('target') or 'production'}`.",
        "- Source: `github`.",
        f"- GitHub ref: `{summary.get('github_ref') or 'missing'}`.",
        f"- Git commit: `{summary.get('deployment_sha') or 'missing'}`.",
        f"- Local HEAD match: `{'yes' if summary.get('production_gate') == 'pass' else 'no'}`.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row.get('step')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "The hosted app is configured as CHILLCRM staging with auth required, remote writes locked, complete-package exports locked, and recovered-document file access controlled by the hosted app. The local SQLite CRM remains the source of truth until hosted auth, file storage, backup/restore, audit, and owner-shakedown gates pass.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Vercel deployment evidence for the connected GitHub deployment.")
    parser.add_argument("--prompt-token", action="store_true", help="Prompt privately for VERCEL_TOKEN if missing.")
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", ""))
    parser.add_argument("--target", default=os.environ.get("VERCEL_TARGET", DEFAULT_TARGET))
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "vercel_git_deployment_status.csv", rows)
    write_git_report(REPORTS_DIR / "vercel_git_deployment_status.md", rows)
    if rows[0]["production_gate"] == "pass":
        write_csv(REPORTS_DIR / "vercel_staging_deployment_status.csv", rows)
        write_staging_deployment_report(REPORTS_DIR / "vercel_staging_deployment_status.md", rows)
    print(json.dumps(rows[0], indent=2))
    return 0 if rows[0]["production_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
