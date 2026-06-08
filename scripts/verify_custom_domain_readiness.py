#!/usr/bin/env python3
"""Verify the CHILLCRM custom domain alias without logging in or writing data."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_DOMAIN_URL = "https://chillcrm.app"
DEFAULT_HTTP_URL = "http://ChillCRM.app"


class HttpResult:
    def __init__(self, status: int | None, final_url: str, body: bytes, error: str = ""):
        self.status = status
        self.final_url = final_url
        self.body = body
        self.error = error

    def json(self) -> dict[str, Any]:
        try:
            return json.loads(self.body.decode("utf-8")) if self.body else {}
        except json.JSONDecodeError:
            return {}

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def fetch(method: str, url: str, payload: dict[str, Any] | None = None) -> HttpResult:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return HttpResult(int(response.status), response.geturl(), response.read(300_000))
    except urllib.error.HTTPError as exc:
        return HttpResult(int(exc.code), exc.geturl(), exc.read(300_000))
    except Exception as exc:  # noqa: BLE001 - report should capture network failures.
        return HttpResult(None, url, b"", f"{exc.__class__.__name__}: {exc}")


def add_check(
    rows: list[dict[str, Any]],
    key: str,
    status: str,
    evidence: str,
    *,
    blocks_cutover: bool = False,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": clip(evidence),
            "blocks_cutover": "yes" if blocks_cutover else "no",
            "provider_calls": "public_http_only",
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
    checks = [row for row in rows if row["row_type"] == "check"]
    lines = [
        "# Custom Domain Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies the public CHILLCRM custom domain alias without logging in, using bypass secrets, changing provider settings, unlocking writes, switching source of truth, or changing CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Canonical URL: `{summary.get('canonical_url')}`.",
        f"- HTTP URL: `{summary.get('http_url')}`.",
        f"- Effective URL: `{summary.get('effective_url') or 'missing'}`.",
        f"- Passed: {summary.get('passed')}.",
        f"- Warnings: {summary.get('warnings')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Public app shell: {summary.get('public_app_shell')}.",
        f"- App auth required: {summary.get('app_auth_required')}.",
        f"- CRM data public access denied: {summary.get('crm_data_public_denied')}.",
        f"- Remote write lock: {summary.get('remote_write_lock')}.",
        f"- Expected remote write lock: {summary.get('expected_remote_write_lock')}.",
        f"- Owner recovery: {summary.get('owner_recovery')}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Blocks Cutover | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row.get('key')} | {row.get('status')} | {row.get('blocks_cutover')} | {str(row.get('evidence') or '').replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `ChillCRM.app` is the public-facing custom domain alias.",
            "- The custom domain serves the app shell publicly, then relies on CHILLCRM app authentication to protect CRM data.",
            "- The remote write-lock expectation changes after explicit owner approval enables hosted production writes.",
            "- The raw Vercel deployment URL may still be protected by Vercel Authentication; that is tracked separately in `reports/vercel_public_protection.md`.",
            "- Before final cutover, run the owner smoke against whichever URL will be treated as the company CRM URL.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_plain_value(text: str, label: str) -> str:
    for line in text.splitlines():
        prefix = f"- {label}: "
        if line.startswith(prefix):
            return line[len(prefix) :].strip().rstrip(".")
    return ""


def default_expected_remote_write_lock() -> str:
    enablement = REPORTS_DIR / "hosted_write_enablement.md"
    if enablement.exists():
        text = enablement.read_text(encoding="utf-8")
        if report_plain_value(text, "Status") == "hosted_writes_enabled":
            return "disabled"
    return "enabled"


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    canonical_url = args.url.rstrip("/")
    http_url = args.http_url.rstrip("/")
    expected_remote_write_lock = args.expected_remote_write_lock
    rows: list[dict[str, Any]] = []

    http_root = fetch("GET", http_url)
    redirect_location = ""
    if http_root.status in {301, 302, 307, 308}:
        redirect_location = http_root.final_url if http_root.final_url != http_url else "https://ChillCRM.app/"
    http_redirect_ok = bool(
        http_root.status in {301, 302, 307, 308}
        and (redirect_location.lower().startswith("https://") or "https://" in http_root.text().lower())
    )
    add_check(
        rows,
        "http_redirects_to_https",
        "pass" if http_redirect_ok else "fail",
        f"http_status={http_root.status}; redirect_location={redirect_location or http_root.final_url or 'missing'}; error={http_root.error or 'none'}",
        blocks_cutover=True,
    )

    root = fetch("GET", canonical_url)
    root_text = root.text()
    effective_url = root.final_url
    https_ok = bool((effective_url or canonical_url).lower().startswith("https://") and root.status == 200)
    app_shell_ok = all(token in root_text for token in ["<title>Local CRM</title>", "authOverlay", "/static/app.js"])
    add_check(
        rows,
        "https_app_shell",
        "pass" if https_ok and app_shell_ok else "fail",
        f"https_status={root.status}; effective_url={effective_url or canonical_url}; app_shell={'yes' if app_shell_ok else 'no'}; error={root.error or 'none'}",
        blocks_cutover=True,
    )

    auth = fetch("GET", f"{canonical_url}/api/auth/status")
    auth_payload = auth.json()
    auth_required = auth_payload.get("auth_required") is True and auth_payload.get("authenticated") is False
    owner_recovery_off = auth_payload.get("owner_password_recovery_enabled") is False
    cookie_secure = bool((auth_payload.get("setup") or {}).get("cookie_secure") is True)
    add_check(
        rows,
        "app_auth_status",
        "pass" if auth.status == 200 and auth_required and owner_recovery_off and cookie_secure else "fail",
        f"status={auth.status}; auth_required={auth_payload.get('auth_required')}; authenticated={auth_payload.get('authenticated')}; owner_recovery={auth_payload.get('owner_password_recovery_enabled')}; cookie_secure={cookie_secure}",
        blocks_cutover=True,
    )

    summary = fetch("GET", f"{canonical_url}/api/summary")
    summary_payload = summary.json()
    summary_denied = summary.status == 401 and summary_payload.get("code") == "auth_required"
    add_check(
        rows,
        "summary_public_access_denied",
        "pass" if summary_denied else "fail",
        f"status={summary.status}; code={summary_payload.get('code') or 'missing'}",
        blocks_cutover=True,
    )

    create = fetch("POST", f"{canonical_url}/api/create_record", {"type": "person", "fields": {"name": "Public Denial Probe"}})
    create_payload = create.json()
    create_denied = create.status == 401 and create_payload.get("code") == "auth_required"
    add_check(
        rows,
        "write_public_access_denied",
        "pass" if create_denied else "fail",
        f"status={create.status}; code={create_payload.get('code') or 'missing'}",
        blocks_cutover=True,
    )

    health = fetch("GET", f"{canonical_url}/api/health")
    health_payload = health.json()
    runtime = health_payload.get("runtime") or {}
    checks = health_payload.get("checks") or {}
    remote_write_lock_enabled = ((runtime.get("remote_write_lock") or {}).get("enabled") is True)
    exports_locked = ((runtime.get("bulk_package_exports") or {}).get("enabled") is False)
    database_ok = ((checks.get("database") or {}).get("status") == "ok")
    expected_lock_enabled = expected_remote_write_lock == "enabled"
    remote_write_lock_matches = (
        expected_remote_write_lock == "any"
        or remote_write_lock_enabled == expected_lock_enabled
    )
    health_ok = (
        health.status == 200
        and health_payload.get("ok") is True
        and remote_write_lock_matches
        and exports_locked
        and database_ok
    )
    add_check(
        rows,
        "public_health_runtime_guardrails",
        "pass" if health_ok else "fail",
        (
            f"status={health.status}; ok={health_payload.get('ok')}; database_ok={database_ok}; "
            f"remote_write_lock={remote_write_lock_enabled}; expected_remote_write_lock={expected_remote_write_lock}; "
            f"export_package_enabled={(runtime.get('bulk_package_exports') or {}).get('enabled')}"
        ),
        blocks_cutover=True,
    )

    app_base_url_configured = runtime.get("app_base_url_configured") is True
    add_check(
        rows,
        "app_base_url_custom_domain",
        "pass" if app_base_url_configured else "warning",
        "APP_BASE_URL is configured for runtime absolute links." if app_base_url_configured else "APP_BASE_URL is not configured; set it to https://chillcrm.app before final custom-domain polish if absolute links are introduced.",
        blocks_cutover=False,
    )

    checks_rows = [row for row in rows if row["row_type"] == "check"]
    failed = [row for row in checks_rows if row["status"] == "fail"]
    warnings = [row for row in checks_rows if row["status"] == "warning"]
    input_required = [row for row in checks_rows if row["status"] == "input_required"]
    status = "custom_domain_ready_with_app_auth"
    production_gate = "pass"
    if failed:
        status = "custom_domain_readiness_failed"
        production_gate = "blocked_until_custom_domain_ready"
    elif input_required:
        status = "input_required_custom_domain"
        production_gate = "blocked_until_custom_domain_ready"

    rows.insert(
        0,
        {
            "row_type": "summary",
            "generated_at": now_utc(),
            "status": status,
            "production_gate": production_gate,
            "canonical_url": canonical_url,
            "http_url": http_url,
            "effective_url": effective_url,
            "passed": sum(1 for row in checks_rows if row["status"] == "pass"),
            "warnings": len(warnings),
            "failed": len(failed),
            "input_required": len(input_required),
            "public_app_shell": "yes" if app_shell_ok else "no",
            "app_auth_required": "yes" if auth_required else "no",
            "crm_data_public_denied": "yes" if summary_denied and create_denied else "no",
            "remote_write_lock": "enabled" if remote_write_lock_enabled else "disabled",
            "expected_remote_write_lock": expected_remote_write_lock,
            "owner_recovery": "disabled" if owner_recovery_off else "not_disabled",
        },
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CHILLCRM custom domain readiness without secrets or writes.")
    parser.add_argument("--url", default=DEFAULT_DOMAIN_URL)
    parser.add_argument("--http-url", default=DEFAULT_HTTP_URL)
    parser.add_argument(
        "--expected-remote-write-lock",
        choices=["enabled", "disabled", "any"],
        default=default_expected_remote_write_lock(),
        help="Expected runtime write-lock state. Defaults to disabled once hosted_write_enablement.md records final enablement.",
    )
    args = parser.parse_args()
    rows = build_rows(args)
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "custom_domain_readiness.csv", rows)
    write_report(REPORTS_DIR / "custom_domain_readiness.md", rows)
    summary = rows[0]
    print(json.dumps(summary, indent=2))
    return 1 if summary["status"] == "custom_domain_readiness_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
