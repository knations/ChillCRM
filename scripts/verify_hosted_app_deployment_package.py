#!/usr/bin/env python3
"""Verify the hosted app deployment package without deploying it."""

from __future__ import annotations

import csv
import importlib
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


REPORTS_DIR = PROJECT_ROOT / "reports"


def row(rows: list[dict[str, Any]], key: str, status: str, evidence: str, gate: str = "deploy_readiness") -> None:
    rows.append(
        {
            "key": key,
            "status": status,
            "evidence": evidence,
            "gate": gate,
        }
    )


def read_url(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["key", "status", "evidence", "gate"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    passed = sum(1 for item in rows if item["status"] == "pass")
    failed = sum(1 for item in rows if item["status"] != "pass")
    lines = [
        "# Hosted App Deployment Package Verification",
        "",
        "This verifies the local deployment package for hosted staging. It does not deploy to Vercel, contact Supabase, upload files, create users, expose localhost, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        "- Target package: Vercel Python Function adapter plus Supabase/Postgres runtime variables.",
        "- Source of truth remains local SQLite until hosted Supabase validation passes.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Gate |",
        "| --- | --- | --- | --- |",
    ]
    for item in rows:
        evidence = str(item["evidence"]).replace("|", "/")
        lines.append(f"| {item['key']} | {item['status']} | {evidence} | {item['gate']} |")
    lines.extend(
        [
            "",
            "## Next Hosted Gates",
            "",
            "- Run the full hosted Vercel smoke test after any schema, adapter, deployment-package, or provider-environment change.",
            "- Keep the latest owner Users UI deployment gated until full hosted login/role smoke passes.",
            "- Complete Supabase provider backup/restore, full actor-aware CRM-write audit, monitoring, and owner-shakedown gates before remote write unlock.",
            "- Keep the deployed Vercel staging app behind Vercel Authentication and CRM auth until owner-shakedown gates pass.",
            "- Keep remote staging write/file/package locks enabled until the validation matrix passes.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows: list[dict[str, Any]] = []

    required_files = [
        "api/index.py",
        "vercel.json",
        "requirements.txt",
        ".python-version",
        ".vercelignore",
        "config/chillcrm_vercel.env.example",
        "docs/vercel_staging_setup.md",
    ]
    for relative_path in required_files:
        path = PROJECT_ROOT / relative_path
        row(rows, f"file:{relative_path}", "pass" if path.exists() else "fail", "present" if path.exists() else "missing")

    try:
        vercel_config = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))
        routes = vercel_config.get("routes") or []
        builds = vercel_config.get("builds") or []
        api_build = next((item for item in builds if item.get("src") == "api/index.py"), {})
        route_ok = any(item.get("src") == "/(.*)" and item.get("dest") == "api/index.py" for item in routes)
        row(rows, "vercel_route", "pass" if route_ok else "fail", "all paths route to api/index.py" if route_ok else "missing catch-all route")
        build_ok = api_build.get("use") == "@vercel/python"
        row(rows, "vercel_python_builder", "pass" if build_ok else "fail", api_build.get("use") or "missing")
        include_files = set((api_build.get("config") or {}).get("includeFiles") or [])
        required_includes = {"config/supabase-prod-ca-2021.crt", "crm_app/**", "docs/**", "reports/**"}
        include_ok = required_includes.issubset(include_files)
        row(rows, "vercel_includes_hosted_assets", "pass" if include_ok else "fail", ", ".join(sorted(include_files)) or "missing")
        vercelignore = (PROJECT_ROOT / ".vercelignore").read_text(encoding="utf-8") if (PROJECT_ROOT / ".vercelignore").exists() else ""
        excluded_dirs = [".venv/", "raw_api_exports/", "backups/", "crm_database/"]
        exclude_ok = all(item in vercelignore for item in excluded_dirs)
        row(rows, "vercel_excludes_local_data", "pass" if exclude_ok else "fail", "local-only paths ignored" if exclude_ok else "missing local-only ignore")
    except Exception as exc:
        row(rows, "vercel_config_parse", "fail", str(exc))

    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8") if (PROJECT_ROOT / "requirements.txt").exists() else ""
    for package in ("pg8000==", "certifi=="):
        row(rows, f"requirement:{package.rstrip('=')}", "pass" if package in requirements else "fail", "pinned" if package in requirements else "missing")

    try:
        module = importlib.import_module("api.index")
        handler = getattr(module, "handler", None)
        handler_ok = isinstance(handler, type) and issubclass(handler, server.CRMRequestHandler)
        row(rows, "serverless_handler_import", "pass" if handler_ok else "fail", "api.index.handler subclasses CRMRequestHandler" if handler_ok else "handler import failed")
    except Exception as exc:
        row(rows, "serverless_handler_import", "fail", str(exc))
        handler = None

    if isinstance(handler, type):
        env_backup = {key: os.environ.get(key) for key in ["DATABASE_URL", "CHILLCRM_DATABASE_ADAPTER", "CRM_DATABASE_ADAPTER", "CHILLCRM_AUTH_REQUIRED", "AUTH_REQUIRED"]}
        for key in env_backup:
            os.environ.pop(key, None)
        httpd: ThreadingHTTPServer | None = None
        thread: threading.Thread | None = None
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{httpd.server_port}"
            health_status, health_body = read_url(f"{base_url}/api/health")
            row(rows, "handler_health_route", "pass" if health_status == 200 and '"ok": true' in health_body else "fail", f"status={health_status}")
            index_status, index_body = read_url(f"{base_url}/")
            row(rows, "handler_index_route", "pass" if index_status == 200 and "Local CRM" in index_body else "fail", f"status={index_status}")
            row(rows, "handler_users_view_route", "pass" if index_status == 200 and 'id="usersView"' in index_body and 'data-view="users"' in index_body else "fail", "owner Users view is present in index shell")
            static_status, static_body = read_url(f"{base_url}/static/app.js")
            row(rows, "handler_static_route", "pass" if static_status == 200 and "renderDashboard" in static_body else "fail", f"status={static_status}")
            row(rows, "handler_users_static_ui", "pass" if static_status == 200 and "renderUsers" in static_body and "/api/app_users/save" in static_body else "fail", "owner Users UI code is present in static bundle")
        except Exception as exc:
            row(rows, "handler_local_smoke", "fail", str(exc))
        finally:
            if httpd:
                httpd.shutdown()
                httpd.server_close()
            if thread:
                thread.join(timeout=5)
            for key, value in env_backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    md_path = REPORTS_DIR / "hosted_app_deployment_package_verification.md"
    csv_path = REPORTS_DIR / "hosted_app_deployment_package_verification.csv"
    write_report(md_path, rows)
    write_csv(csv_path, rows)
    failed = [item for item in rows if item["status"] != "pass"]
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if failed:
        print(f"Hosted app deployment package verification failed: {len(failed)} checks.", file=sys.stderr)
        return 1
    print("Hosted app deployment package verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
