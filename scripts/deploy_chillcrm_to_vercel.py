#!/usr/bin/env python3
"""Create/update the locked CHILLCRM Vercel staging deployment.

Secrets are read from prompts or environment variables and are not written to
project files or reports. The report records only non-secret deployment facts.
"""

from __future__ import annotations

import csv
import base64
import getpass
import hashlib
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crm_app.server import password_hash


REPORTS_DIR = PROJECT_ROOT / "reports"
PROJECT_NAME = "chillcrm"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
DEPLOY_TARGET = "production"
VERCEL_API = "https://api.vercel.com"
VERCEL_ROOT_DIRECTORY: str | None = None
UPLOAD_CACHE_PATH = PROJECT_ROOT / ".vercel" / "uploaded_file_shas.json"
VERCEL_LINK_PATH = PROJECT_ROOT / ".vercel" / "project.json"

DEPLOY_PATHS = [
    ".python-version",
    ".vercelignore",
    "README.md",
    "api",
    "config/supabase-prod-ca-2021.crt",
    "crm_app",
    "docs",
    "reports",
    "requirements.txt",
    "vercel.json",
]

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".vercel",
    "__pycache__",
    "backups",
    "crm_database",
    "exports",
    "logs",
    "raw_api_exports",
    "staging_database",
}

SECRET_KEYS = {
    "DATABASE_URL",
    "SESSION_SECRET",
    "AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH",
    "CHILLCRM_SUPABASE_SERVICE_ROLE_KEY",
}


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def prompt_secret(label: str, env_key: str | None = None) -> str:
    value = os.environ.get(env_key or "", "").strip() if env_key else ""
    if value:
        return value
    return getpass.getpass(f"{label}: ").strip()


def request_json(
    method: str,
    path: str,
    token: str,
    *,
    body: Any | None = None,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> Any:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data: bytes | None = None
    request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {raw[:1000]}") from exc


def request_bytes(
    method: str,
    path: str,
    token: str,
    *,
    data: bytes,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> Any:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {raw[:1000]}") from exc


def team_query(team_id: str | None, slug: str | None) -> dict[str, str]:
    if slug:
        return {"slug": slug}
    if team_id:
        return {"teamId": team_id}
    return {}


def read_vercel_link() -> dict[str, str]:
    link: dict[str, Any] = {}
    if VERCEL_LINK_PATH.exists():
        try:
            loaded = json.loads(VERCEL_LINK_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                link = loaded
        except json.JSONDecodeError:
            link = {}
    return {
        "projectId": os.environ.get("VERCEL_PROJECT_ID", "").strip() or str(link.get("projectId") or "").strip(),
        "orgId": (
            os.environ.get("VERCEL_TEAM_ID", "").strip()
            or os.environ.get("VERCEL_ORG_ID", "").strip()
            or str(link.get("orgId") or "").strip()
        ),
        "teamSlug": os.environ.get("VERCEL_TEAM_SLUG", "").strip() or str(link.get("teamSlug") or "").strip(),
        "projectName": str(link.get("projectName") or "").strip(),
    }


def choose_team(token: str, link: dict[str, str]) -> dict[str, Any]:
    if link.get("orgId") or link.get("teamSlug"):
        slug = link.get("teamSlug") or DEFAULT_TEAM_SLUG
        return {
            "id": link.get("orgId"),
            "slug": slug,
            "name": f"Linked Vercel org {slug or link.get('orgId')}",
        }
    teams = request_json("GET", "/v2/teams", token).get("teams", [])
    configured = os.environ.get("VERCEL_TEAM_SLUG", "").strip() or DEFAULT_TEAM_SLUG
    for team in teams:
        if team.get("slug") == configured:
            return team
    if len(teams) == 1:
        return teams[0]
    raise RuntimeError("Set VERCEL_TEAM_SLUG before deploying; multiple or no Vercel teams were found.")


def user_email(token: str) -> str:
    data = request_json("GET", "/v2/user", token)
    user = data.get("user") or data
    email = str(user.get("email") or "").strip()
    if not email:
        raise RuntimeError("Vercel user email was not available; set AUTH_BOOTSTRAP_ADMIN_EMAIL.")
    return email


def find_project(token: str, query: dict[str, str]) -> dict[str, Any] | None:
    data = request_json("GET", "/v9/projects", token, query={**query, "limit": "100"})
    for project in data.get("projects", []):
        if project.get("name") == PROJECT_NAME:
            return project
    return None


def create_or_get_project(token: str, query: dict[str, str], linked_project_id: str = "") -> dict[str, Any]:
    if linked_project_id:
        project = request_json("GET", f"/v9/projects/{linked_project_id}", token, query=query)
        return update_project_settings(token, query, project)
    project = find_project(token, query)
    if project:
        return update_project_settings(token, query, project)
    body = {
        "name": PROJECT_NAME,
        "framework": "python",
        "rootDirectory": VERCEL_ROOT_DIRECTORY,
        "buildCommand": None,
        "installCommand": None,
        "outputDirectory": None,
        "enablePreviewFeedback": False,
        "enableProductionFeedback": False,
    }
    try:
        return request_json("POST", "/v9/projects", token, query=query, body=body)
    except RuntimeError as exc:
        if "already exists" in str(exc).lower() or "conflict" in str(exc).lower():
            project = find_project(token, query)
            if project:
                return project
        raise


def update_project_settings(token: str, query: dict[str, str], project: dict[str, Any]) -> dict[str, Any]:
    project_id = str(project.get("id") or project.get("name") or PROJECT_NAME)
    desired = {
        "framework": "python",
        "rootDirectory": VERCEL_ROOT_DIRECTORY,
        "buildCommand": None,
        "installCommand": None,
        "outputDirectory": None,
        "enablePreviewFeedback": False,
        "enableProductionFeedback": False,
    }
    needs_update = any(project.get(key) != value for key, value in desired.items())
    if not needs_update:
        return project
    return request_json("PATCH", f"/v9/projects/{project_id}", token, query=query, body=desired)


def write_vercel_link(project: dict[str, Any], team: dict[str, Any]) -> None:
    vercel_dir = PROJECT_ROOT / ".vercel"
    vercel_dir.mkdir(exist_ok=True)
    link = {
        "projectId": project.get("id"),
        "orgId": team.get("id") or project.get("accountId"),
        "projectName": project.get("name"),
        "teamSlug": team.get("slug"),
    }
    (vercel_dir / "project.json").write_text(json.dumps(link, indent=2) + "\n", encoding="utf-8")


def make_env_values(token: str) -> tuple[dict[str, str], str, str]:
    admin_email = os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", "").strip() or user_email(token)
    admin_password = os.environ.get("AUTH_BOOTSTRAP_ADMIN_PASSWORD", "").strip() or secrets.token_urlsafe(18)
    document_file_access = os.environ.get("DOCUMENT_FILE_ACCESS_ENABLED", "").strip().lower()
    service_role_key = (
        os.environ.get("CHILLCRM_SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
    values = {
        "CRM_ENV": "staging",
        "CHILLCRM_DATABASE_ADAPTER": "postgres",
        "DATABASE_URL": prompt_secret("Supabase DATABASE_URL", "CHILLCRM_VERCEL_DATABASE_URL"),
        "CHILLCRM_SSLROOTCERT": "config/supabase-prod-ca-2021.crt",
        "CHILLCRM_POSTGRES_STATEMENT_TIMEOUT_MS": "8000",
        "APP_BASE_URL": os.environ.get("APP_BASE_URL", "").strip() or "https://chillcrm.app",
        "CHILLCRM_AUTH_REQUIRED": "true",
        "SESSION_SECRET": os.environ.get("SESSION_SECRET", "").strip() or secrets.token_urlsafe(48),
        "SESSION_COOKIE_SECURE": "true",
        "AUTH_BOOTSTRAP_ADMIN_EMAIL": admin_email,
        "AUTH_BOOTSTRAP_ADMIN_NAME": os.environ.get("AUTH_BOOTSTRAP_ADMIN_NAME", "").strip() or admin_email,
        "AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH": password_hash(admin_password),
        "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED": "true" if env_truthy("CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED") else "false",
        "REMOTE_WRITE_LOCK": "true",
        "EXPORT_PACKAGE_ENABLED": "false",
        "DOCUMENT_FILE_ACCESS_ENABLED": "true" if document_file_access in {"1", "true", "yes", "on", "enabled"} else "false",
        "CHILLCRM_SUPABASE_URL": "https://ckjbnummsxqcyeahzynz.supabase.co",
        "CHILLCRM_SUPABASE_STORAGE_BUCKET": "chillcrm-documents",
        "CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS": "300",
    }
    if service_role_key:
        values["CHILLCRM_SUPABASE_SERVICE_ROLE_KEY"] = service_role_key
    return values, admin_email, admin_password


def upsert_env(token: str, project_id: str, query: dict[str, str], env_values: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    targets = ["production", "preview", "development"]
    for key, value in env_values.items():
        env_type = "encrypted" if key in SECRET_KEYS else "plain"
        body = {"key": key, "value": value, "type": env_type, "target": targets}
        try:
            request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
            rows.append({"key": key, "status": "upserted", "secret": str(key in SECRET_KEYS).lower()})
        except RuntimeError as exc:
            if env_type == "encrypted":
                body["type"] = "sensitive"
                request_json("POST", f"/v10/projects/{project_id}/env", token, query={**query, "upsert": "true"}, body=body)
                rows.append({"key": key, "status": "upserted_sensitive", "secret": "true"})
            else:
                raise exc
    return rows


def iter_deploy_files() -> list[Path]:
    files: list[Path] = []
    for item in DEPLOY_PATHS:
        path = PROJECT_ROOT / item
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for child in path.rglob("*"):
            if not child.is_file():
                continue
            parts = set(child.relative_to(PROJECT_ROOT).parts)
            if parts & EXCLUDE_DIRS:
                continue
            if child.name == ".DS_Store" or child.suffix == ".pyc":
                continue
            files.append(child)
    return sorted(files)


def upload_files(token: str, query: dict[str, str], files: list[Path]) -> list[dict[str, Any]]:
    cache = load_upload_cache()
    use_cache = not env_truthy("CHILLCRM_DISABLE_VERCEL_UPLOAD_CACHE")
    refs: list[dict[str, Any]] = []
    uploaded = 0
    cached = 0
    try:
        for path in files:
            data = path.read_bytes()
            sha = hashlib.sha1(data).hexdigest()
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if use_cache and sha in cache:
                cached += 1
            else:
                request_bytes(
                    "POST",
                    "/v2/files",
                    token,
                    data=data,
                    query=query,
                    headers={
                        "Content-Type": content_type,
                        "Content-Length": str(len(data)),
                        "x-vercel-digest": sha,
                    },
                    timeout=120,
                )
                cache[sha] = {
                    "last_path": relative,
                    "size": len(data),
                    "uploaded_at": datetime_now(),
                }
                uploaded += 1
            refs.append({"file": relative, "sha": sha, "size": len(data)})
    finally:
        if use_cache:
            write_upload_cache(cache)
        upload_files.last_stats = {"uploaded": uploaded, "cached": cached, "total": len(refs), "cache_enabled": use_cache}
    return refs


def inline_files(files: list[Path]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    total_bytes = 0
    for path in files:
        data = path.read_bytes()
        total_bytes += len(data)
        refs.append(
            {
                "file": path.relative_to(PROJECT_ROOT).as_posix(),
                "data": base64.b64encode(data).decode("ascii"),
                "encoding": "base64",
            }
        )
    inline_files.last_stats = {"total": len(refs), "bytes": total_bytes}
    return refs


def datetime_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_upload_cache() -> dict[str, dict[str, Any]]:
    if not UPLOAD_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(UPLOAD_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def write_upload_cache(cache: dict[str, dict[str, Any]]) -> None:
    UPLOAD_CACHE_PATH.parent.mkdir(exist_ok=True)
    UPLOAD_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_deployment(token: str, query: dict[str, str], project: dict[str, Any], refs: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        "name": PROJECT_NAME,
        "project": project.get("id") or PROJECT_NAME,
        "files": refs,
        "target": DEPLOY_TARGET,
        "meta": {
            "source": "chillcrm-local-migration",
            "crm_env": "staging",
        },
        "projectSettings": {
            "framework": "python",
            "buildCommand": None,
            "installCommand": None,
            "outputDirectory": None,
        },
    }
    return request_json(
        "POST",
        "/v13/deployments",
        token,
        query={**query, "forceNew": "1", "skipAutoDetectionConfirmation": "1"},
        body=body,
        timeout=120,
    )


def poll_deployment(token: str, query: dict[str, str], deployment_id: str) -> dict[str, Any]:
    last: dict[str, Any] = {}
    for _ in range(90):
        last = request_json("GET", f"/v13/deployments/{deployment_id}", token, query=query, timeout=60)
        state = last.get("readyState") or last.get("status")
        if state in {"READY", "ERROR", "CANCELED"}:
            return last
        time.sleep(4)
    return last


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


def write_report(path: Path, rows: list[dict[str, Any]], deployment: dict[str, Any]) -> None:
    document_file_access = os.environ.get("DOCUMENT_FILE_ACCESS_ENABLED", "").strip().lower()
    environment_preserved = any(row.get("step") == "environment" and row.get("status") == "preserved" for row in rows)
    document_file_clause = (
        "existing recovered-document file access setting preserved"
        if environment_preserved and not document_file_access
        else (
            "recovered-document file access enabled for owner/admin short-lived Supabase Storage redirects"
            if document_file_access in {"1", "true", "yes", "on", "enabled"}
            else "recovered-document file access locked"
        )
    )
    lines = [
        "# Vercel Staging Deployment Status",
        "",
        "This report records non-secret CHILLCRM Vercel staging deployment facts. It does not include the Vercel token, database password, session secret, bootstrap password hash, service-role key, or bootstrap password.",
        "",
        "## Summary",
        "",
        f"- Project: `{PROJECT_NAME}`.",
        f"- Deployment ID: `{deployment.get('id')}`.",
        f"- Ready state: `{deployment.get('readyState') or deployment.get('status')}`.",
        f"- URL: `https://{deployment.get('url')}`." if deployment.get("url") else "- URL: pending.",
        f"- Target: `{deployment.get('target') or DEPLOY_TARGET}`.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row.get('step')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            f"The hosted app is configured as CHILLCRM staging with auth required, remote writes locked, complete-package exports locked, and {document_file_clause}. The local SQLite CRM remains the source of truth until hosted auth, file storage, backup/restore, audit, and owner-shakedown gates pass.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    token = prompt_secret("Vercel token", "VERCEL_TOKEN")
    if not token:
        raise RuntimeError("Vercel token is required.")
    rows: list[dict[str, Any]] = []

    link = read_vercel_link()
    team = choose_team(token, link)
    query = team_query(str(team.get("id") or "").strip(), str(team.get("slug") or "").strip())
    rows.append({"step": "account_scope", "status": "ok", "evidence": f"{team.get('name')} ({team.get('slug')})"})

    project = create_or_get_project(token, query, link.get("projectId", ""))
    write_vercel_link(project, team)
    rows.append({"step": "project", "status": "ready", "evidence": f"{project.get('name')} / {project.get('id')}"})

    skip_env_upsert = env_truthy("CHILLCRM_SKIP_ENV_UPSERT") or env_truthy("VERCEL_SKIP_ENV_UPSERT")
    if skip_env_upsert:
        admin_email = os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", "").strip() or "existing Vercel env"
        rows.append({"step": "environment", "status": "preserved", "evidence": "existing Vercel environment variables reused"})
        if "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED" in os.environ:
            recovery_value = "true" if env_truthy("CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED") else "false"
            upsert_env(token, str(project.get("id")), query, {"CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED": recovery_value})
            rows.append(
                {
                    "step": "owner_password_recovery_env",
                    "status": "upserted_plain",
                    "evidence": f"CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED={recovery_value}",
                }
            )
        if "REMOTE_WRITE_LOCK" in os.environ:
            lock_value = "true" if env_truthy("REMOTE_WRITE_LOCK") else "false"
            upsert_env(token, str(project.get("id")), query, {"REMOTE_WRITE_LOCK": lock_value})
            rows.append(
                {
                    "step": "remote_write_lock_env",
                    "status": "upserted_plain",
                    "evidence": f"REMOTE_WRITE_LOCK={lock_value}",
                }
            )
    else:
        env_values, admin_email, admin_password = make_env_values(token)
        env_rows = upsert_env(token, str(project.get("id")), query, env_values)
        rows.append({"step": "environment", "status": "upserted", "evidence": f"{len(env_rows)} variables, secrets not written to report"})

    files = iter_deploy_files()
    if env_truthy("CHILLCRM_VERCEL_INLINE_FILES"):
        file_refs = inline_files(files)
        inline_stats = getattr(inline_files, "last_stats", {"total": len(file_refs), "bytes": 0})
        rows.append(
            {
                "step": "file_upload",
                "status": "inlined",
                "evidence": f"{inline_stats['total']} files; bytes={inline_stats['bytes']}; upload_endpoint_used=false",
            }
        )
    else:
        file_refs = upload_files(token, query, files)
        upload_stats = getattr(upload_files, "last_stats", {"uploaded": len(file_refs), "cached": 0, "total": len(file_refs), "cache_enabled": False})
        rows.append(
            {
                "step": "file_upload",
                "status": "uploaded",
                "evidence": (
                    f"{upload_stats['total']} files; uploaded={upload_stats['uploaded']}; "
                    f"cache_reused={upload_stats['cached']}; cache_enabled={str(upload_stats['cache_enabled']).lower()}"
                ),
            }
        )

    deployment = create_deployment(token, query, project, file_refs)
    rows.append({"step": "deployment_create", "status": deployment.get("readyState") or deployment.get("status") or "created", "evidence": deployment.get("id")})

    deployment = poll_deployment(token, query, str(deployment.get("id")))
    ready_state = deployment.get("readyState") or deployment.get("status")
    rows.append({"step": "deployment_poll", "status": str(ready_state or "unknown").lower(), "evidence": deployment.get("url")})

    REPORTS_DIR.mkdir(exist_ok=True)
    write_report(REPORTS_DIR / "vercel_staging_deployment_status.md", rows, deployment)
    write_csv(REPORTS_DIR / "vercel_staging_deployment_status.csv", rows)

    output = {
        "project_id": project.get("id"),
        "team_slug": team.get("slug"),
        "deployment_id": deployment.get("id"),
        "ready_state": ready_state,
        "url": f"https://{deployment.get('url')}" if deployment.get("url") else "",
        "admin_email": admin_email,
        "bootstrap_password_status": "configured but not printed",
        "report": str(REPORTS_DIR / "vercel_staging_deployment_status.md"),
    }
    print(json.dumps(output, indent=2))
    return 0 if ready_state == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
