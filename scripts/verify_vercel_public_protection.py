#!/usr/bin/env python3
"""Verify the Vercel-hosted CHILLCRM deployment is not publicly exposed."""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
PROTECTED_PATHS = [
    ("/", "app_shell"),
    ("/api/health", "health_api"),
    ("/api/auth/status", "auth_status_api"),
    ("/api/summary", "summary_api"),
    ("/api/list?type=people&page_size=1", "people_list_api"),
    ("/reports/remote_production_readiness.md", "production_report"),
    ("/static/app.js", "static_bundle"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def latest_url() -> str:
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    readiness = read_text("reports/remote_production_readiness.md")
    return backtick_value(deployment, "URL") or backtick_value(readiness, "Latest URL")


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def request_status(url: str) -> tuple[int | None, str]:
    request = urllib.request.Request(url, headers={"Accept": "text/html,application/json,text/plain,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return int(response.status), body
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode("utf-8", errors="replace")
        return int(exc.code), body
    except Exception as exc:  # noqa: BLE001 - report records probe failures.
        return None, exc.__class__.__name__


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
    checks = [row for row in rows if row["row_type"] == "check"]
    lines = [
        "# Vercel Public Protection",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that the current Vercel-hosted CHILLCRM staging deployment does not expose CRM pages, APIs, reports, or static bundles to unauthenticated public requests. It does not use bypass secrets, log in, create users, unlock writes, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Target URL: `{summary.get('target_url') or 'missing'}`.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        "- Secrets used: no.",
        "- CRM record writes: no.",
        "",
        "## Checks",
        "",
        "| Path | Surface | Status | HTTP Status | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("path")),
                    str(row.get("surface")),
                    str(row.get("status")),
                    str(row.get("http_status")),
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
            "This is a public unauthenticated probe only. Hosted smoke still requires a Vercel protection bypass secret plus owner credentials to test authenticated app behavior.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows(base_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, surface in PROTECTED_PATHS:
        status, body = request_status(f"{base_url}{path}")
        protected = status in {401, 403}
        public_success = status is not None and 200 <= status < 300
        evidence = "protected response body omitted" if protected else ("public success response" if public_success else str(body)[:120])
        rows.append(
            {
                "row_type": "check",
                "path": path,
                "surface": surface,
                "status": "pass" if protected else "fail",
                "http_status": status if status is not None else "network_error",
                "evidence": evidence,
            }
        )
    failed = [row for row in rows if row["status"] != "pass"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "vercel_public_protection_passed" if not failed else "vercel_public_protection_failed",
        "production_gate": "pass" if not failed else "blocked_until_public_protection_restored",
        "target_url": base_url,
        "passed": len(rows) - len(failed),
        "failed": len(failed),
    }
    return [summary, *rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Vercel public protection across CHILLCRM public surfaces.")
    parser.add_argument("--url", default="", help="Vercel deployment URL. Defaults to the latest deployment report URL.")
    args = parser.parse_args()
    base_url = normalize_url(args.url or latest_url())
    if not base_url:
        raise RuntimeError("Set --url or generate reports/vercel_staging_deployment_status.md first.")
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(base_url)
    write_csv(REPORTS_DIR / "vercel_public_protection.csv", rows)
    write_report(REPORTS_DIR / "vercel_public_protection.md", rows)
    summary = rows[0]
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "vercel_public_protection_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
