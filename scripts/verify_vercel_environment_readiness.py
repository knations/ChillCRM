#!/usr/bin/env python3
"""Verify non-secret Vercel environment readiness for CHILLCRM."""

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

REQUIRED_STAGING_KEYS = [
    "CRM_ENV",
    "CHILLCRM_DATABASE_ADAPTER",
    "DATABASE_URL",
    "CHILLCRM_SSLROOTCERT",
    "CHILLCRM_POSTGRES_STATEMENT_TIMEOUT_MS",
    "CHILLCRM_AUTH_REQUIRED",
    "SESSION_SECRET",
    "SESSION_COOKIE_SECURE",
    "AUTH_BOOTSTRAP_ADMIN_EMAIL",
    "AUTH_BOOTSTRAP_ADMIN_NAME",
    "AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH",
    "REMOTE_WRITE_LOCK",
    "EXPORT_PACKAGE_ENABLED",
    "DOCUMENT_FILE_ACCESS_ENABLED",
    "CHILLCRM_SUPABASE_URL",
    "CHILLCRM_SUPABASE_STORAGE_BUCKET",
    "CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS",
    "CHILLCRM_SUPABASE_SERVICE_ROLE_KEY",
]
RECOMMENDED_CUTOVER_KEYS = [
    "APP_BASE_URL",
]
SECRET_KEYS = {
    "DATABASE_URL",
    "SESSION_SECRET",
    "AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH",
    "CHILLCRM_SUPABASE_SERVICE_ROLE_KEY",
}
EXPECTED_PRODUCTION_VALUES = {
    "CRM_ENV": "staging",
    "CHILLCRM_DATABASE_ADAPTER": "postgres",
    "CHILLCRM_AUTH_REQUIRED": "true",
    "SESSION_COOKIE_SECURE": "true",
    "REMOTE_WRITE_LOCK": "true",
    "EXPORT_PACKAGE_ENABLED": "false",
    "DOCUMENT_FILE_ACCESS_ENABLED": "true",
    "CHILLCRM_SUPABASE_URL": "https://ckjbnummsxqcyeahzynz.supabase.co",
    "CHILLCRM_SUPABASE_STORAGE_BUCKET": "chillcrm-documents",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prompt_secret(label: str, env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    return getpass.getpass(f"{label}: ").strip()


def read_project_link() -> dict[str, str]:
    path = PROJECT_ROOT / ".vercel" / "project.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in payload.items() if value}


def request_json(path: str, token: str, query: dict[str, str]) -> dict[str, Any]:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vercel environment request failed with {exc.code}: {body[:500]}") from exc


def target_names(value: Any) -> list[str]:
    if isinstance(value, list):
        return sorted(str(item) for item in value)
    if isinstance(value, str) and value:
        return [value]
    return []


def env_payload_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("envs") or payload.get("env") or []
    return [item for item in items if isinstance(item, dict)]


def build_rows(project_id: str, team_slug: str, env_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_key: dict[str, list[dict[str, Any]]] = {}
    for item in env_items:
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        by_key.setdefault(key, []).append(item)

    for key in REQUIRED_STAGING_KEYS:
        entries = by_key.get(key, [])
        targets = sorted({target for entry in entries for target in target_names(entry.get("target"))})
        production_present = "production" in targets
        env_type = sorted({str(entry.get("type") or "unknown") for entry in entries})
        expected_secret = key in SECRET_KEYS
        type_ok = not expected_secret or any(kind in {"encrypted", "sensitive"} for kind in env_type)
        status = "pass" if entries and production_present and type_ok else "input_required"
        evidence = (
            f"targets={','.join(targets) or 'none'}; type={','.join(env_type) or 'missing'}; "
            f"production_present={production_present}; secret_type_ok={type_ok}"
        )
        rows.append(
            {
                "row_type": "check",
                "key": key,
                "category": "required_locked_staging",
                "status": status,
                "blocks_remote_shakedown": "yes",
                "expected_secret": "yes" if expected_secret else "no",
                "expected_value_checked": "no",
                "targets_seen": ",".join(targets),
                "evidence": evidence,
            }
        )

    for key in RECOMMENDED_CUTOVER_KEYS:
        entries = by_key.get(key, [])
        targets = sorted({target for entry in entries for target in target_names(entry.get("target"))})
        production_present = "production" in targets
        rows.append(
            {
                "row_type": "check",
                "key": key,
                "category": "recommended_cutover",
                "status": "pass" if production_present else "warning",
                "blocks_remote_shakedown": "no",
                "expected_secret": "no",
                "expected_value_checked": "no",
                "targets_seen": ",".join(targets),
                "evidence": f"targets={','.join(targets) or 'none'}; recommended for absolute links/custom domain cutover.",
            }
        )

    visible_expected_keys = [key for key in EXPECTED_PRODUCTION_VALUES if key not in SECRET_KEYS]
    for key in visible_expected_keys:
        entries = by_key.get(key, [])
        production_entries = [entry for entry in entries if "production" in target_names(entry.get("target"))]
        sample = production_entries[0] if production_entries else {}
        value = str(sample.get("value") or "") if sample else ""
        # Vercel may omit values in some contexts. Treat absence as unverified, not failed.
        expected = EXPECTED_PRODUCTION_VALUES[key]
        if not value:
            status = "unverified"
            evidence = "Vercel did not return a plain value through this API response."
        else:
            status = "pass" if value == expected else "warning"
            evidence = f"plain value {'matches expected' if value == expected else 'differs from expected'}."
        rows.append(
            {
                "row_type": "plain_value_check",
                "key": key,
                "category": "plain_value_sanity",
                "status": status,
                "blocks_remote_shakedown": "no",
                "expected_secret": "no",
                "expected_value_checked": "yes",
                "targets_seen": "production" if production_entries else "",
                "evidence": evidence,
            }
        )

    checks = [row for row in rows if row["row_type"] == "check"]
    required = [row for row in checks if row["category"] == "required_locked_staging"]
    required_missing = [row for row in required if row["status"] != "pass"]
    warnings = [row for row in rows if row["status"] == "warning"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "vercel_environment_ready" if not required_missing else "input_required_vercel_environment",
        "project_id": project_id,
        "team_slug": team_slug,
        "required_passed": len(required) - len(required_missing),
        "required_input_required": len(required_missing),
        "warnings": len(warnings),
        "values_stored": "no",
        "secrets_read_or_stored": "no",
        "production_gate": "pass" if not required_missing else "blocked_until_vercel_environment_ready",
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


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    checks = [row for row in rows if row["row_type"] != "summary"]
    lines = [
        "# Vercel Environment Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies Vercel environment variable names and targets without storing secret values. It does not deploy, change provider settings, unlock writes, create users, expose secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Project ID: `{summary.get('project_id')}`.",
        f"- Team slug: `{summary.get('team_slug')}`.",
        f"- Required keys passed: {summary.get('required_passed')}.",
        f"- Required keys input-required: {summary.get('required_input_required')}.",
        f"- Warnings: {summary.get('warnings')}.",
        "- Values stored: no.",
        "- Secrets read or stored: no.",
        "",
        "## Checks",
        "",
        "| Key | Category | Status | Blocks Remote Shakedown | Targets Seen | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("category")),
                    str(row.get("status")),
                    str(row.get("blocks_remote_shakedown")),
                    str(row.get("targets_seen") or ""),
                    str(row.get("evidence") or "").replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a metadata-only provider audit. It proves required environment keys are present for the locked staging deployment, but it does not reveal or validate secret contents. Hosted smoke and health checks remain the runtime proof that those settings behave correctly.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify non-secret Vercel environment variable readiness.")
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", ""))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", DEFAULT_TEAM_SLUG))
    args = parser.parse_args()

    link = read_project_link()
    project_id = args.project_id.strip() or link.get("projectId", "")
    team_slug = args.team_slug.strip() or link.get("teamSlug", DEFAULT_TEAM_SLUG)
    token = prompt_secret("Vercel token", "VERCEL_TOKEN")
    if not token:
        raise RuntimeError("Vercel token is required.")
    if not project_id:
        raise RuntimeError("Vercel project id is required. Link the project or pass --project-id.")
    payload = request_json(f"/v10/projects/{project_id}/env", token, {"slug": team_slug})
    rows = build_rows(project_id, team_slug, env_payload_items(payload))
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "vercel_environment_readiness.csv", rows)
    write_report(REPORTS_DIR / "vercel_environment_readiness.md", rows)
    summary = next(row for row in rows if row["row_type"] == "summary")
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "vercel_environment_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
