#!/usr/bin/env python3
"""Verify the local hosted runtime is ready for the next Vercel redeploy."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_NAME = "hosted_redeploy_preflight"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def backtick_value(text: str, label: str) -> str:
    value = plain_value(text, label)
    if value.startswith("`") and "`" in value[1:]:
        return value.split("`", 2)[1].strip()
    return ""


def int_value(value: str) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


def compact_result(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        return f"exit_code={result.returncode}"
    first_line = text.splitlines()[0]
    return f"exit_code={result.returncode}; output={first_line[:220]}"


def run_child(script_name: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name)]
    return subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=900)


def add_check(
    rows: list[dict[str, Any]],
    key: str,
    status: str,
    evidence: str,
    source: str,
    *,
    required_for_redeploy: bool = True,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "source": source,
            "required_for_redeploy": "yes" if required_for_redeploy else "no",
            "provider_calls": "no",
            "remote_write_lock_changed": "no",
            "crm_record_writes": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def token_check(source: str, tokens: list[str]) -> tuple[bool, str]:
    missing = [token for token in tokens if token not in source]
    return not missing, "all expected source tokens present" if not missing else "missing source tokens: " + ", ".join(missing)


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    package_result = run_child("verify_hosted_app_deployment_package.py")
    add_check(
        rows,
        "deployment_package_verification",
        "pass" if package_result.returncode == 0 else "fail",
        compact_result(package_result),
        "reports/hosted_app_deployment_package_verification.md",
    )

    freshness_result = run_child("verify_hosted_deployment_freshness.py")
    freshness = read_text("reports/hosted_deployment_freshness.md")
    freshness_status = plain_value(freshness, "Status")
    freshness_gate = plain_value(freshness, "Production gate")
    changed_runtime_files = int_value(plain_value(freshness, "Changed runtime files"))
    latest_deployment = backtick_value(freshness, "Latest deployment")
    freshness_ok = freshness_result.returncode == 0 and freshness_status in {
        "hosted_deployment_fresh",
        "input_required_redeploy_current_local_runtime",
    }
    add_check(
        rows,
        "deployment_freshness_report_current",
        "pass" if freshness_ok else "fail",
        f"status={freshness_status or 'missing'}; production_gate={freshness_gate or 'missing'}; changed_runtime_files={changed_runtime_files}",
        "reports/hosted_deployment_freshness.md",
    )

    deployment_report = read_text("reports/vercel_staging_deployment_status.md")
    latest_url = backtick_value(deployment_report, "URL")
    ready_state = backtick_value(deployment_report, "Ready state")
    add_check(
        rows,
        "latest_deployment_reference_ready",
        "pass" if latest_deployment and latest_url and ready_state == "READY" else "fail",
        f"deployment_id={latest_deployment or 'missing'}; url={latest_url or 'missing'}; ready_state={ready_state or 'missing'}",
        "reports/vercel_staging_deployment_status.md",
    )

    environment = read_text("reports/vercel_environment_readiness.md")
    environment_status = plain_value(environment, "Status")
    environment_gate = plain_value(environment, "Production gate")
    remote_lock_ok = "| REMOTE_WRITE_LOCK | plain_value_sanity | pass |" in environment
    export_lock_ok = "| EXPORT_PACKAGE_ENABLED | plain_value_sanity | pass |" in environment
    add_check(
        rows,
        "locked_staging_environment_ready",
        "pass" if environment_status == "vercel_environment_ready" and environment_gate == "pass" and remote_lock_ok and export_lock_ok else "fail",
        f"status={environment_status or 'missing'}; production_gate={environment_gate or 'missing'}; remote_write_lock={remote_lock_ok}; export_lock={export_lock_ok}",
        "reports/vercel_environment_readiness.md",
    )

    public = read_text("reports/vercel_public_protection.md")
    public_status = plain_value(public, "Status")
    public_gate = plain_value(public, "Production gate")
    add_check(
        rows,
        "public_protection_ready",
        "pass" if public_status == "vercel_public_protection_passed" and public_gate == "pass" else "fail",
        f"status={public_status or 'missing'}; production_gate={public_gate or 'missing'}",
        "reports/vercel_public_protection.md",
    )

    deploy_script = read_text("scripts/deploy_chillcrm_to_vercel.py")
    deploy_tokens_ok, deploy_tokens_evidence = token_check(
        deploy_script,
        [
            "CHILLCRM_SKIP_ENV_UPSERT",
            "CHILLCRM_VERCEL_INLINE_FILES",
            "DEPLOY_PATHS",
            "EXCLUDE_DIRS",
            "SECRET_KEYS",
            "prompt_secret",
        ],
    )
    add_check(
        rows,
        "deploy_script_secret_safe_mode",
        "pass" if deploy_tokens_ok else "fail",
        deploy_tokens_evidence,
        "scripts/deploy_chillcrm_to_vercel.py",
    )

    vercelignore = read_text(".vercelignore")
    required_ignores = [".venv/", "raw_api_exports/", "backups/", "exports/", "logs/", "staging_database/", "crm_database/", "*.sqlite"]
    missing_ignores = [item for item in required_ignores if item not in vercelignore]
    add_check(
        rows,
        "vercelignore_excludes_local_data",
        "pass" if not missing_ignores else "fail",
        "local-only directories and SQLite files excluded" if not missing_ignores else "missing ignores: " + ", ".join(missing_ignores),
        ".vercelignore",
    )

    wrapper = read_text("scripts/run_newest_hosted_smoke_with_vercel_bypass.py")
    wrapper_ok, wrapper_evidence = token_check(
        wrapper,
        ["prompt_secret", "getpass.getpass", "VERCEL_TOKEN", "AUTH_BOOTSTRAP_ADMIN_PASSWORD", "verify_vercel_hosted_app.py"],
    )
    add_check(
        rows,
        "hosted_smoke_wrapper_ready",
        "pass" if wrapper_ok else "fail",
        wrapper_evidence,
        "scripts/run_newest_hosted_smoke_with_vercel_bypass.py",
    )

    packet = read_text("reports/remaining_production_gates_packet.md")
    packet_ok = (
        "CHILLCRM_SKIP_ENV_UPSERT=1 CHILLCRM_VERCEL_INLINE_FILES=1" in packet
        and "run_newest_hosted_smoke_with_vercel_bypass.py" in packet
        and "run_safe_production_gate_checks.py --refresh-only" in packet
    )
    add_check(
        rows,
        "operator_packet_has_redeploy_sequence",
        "pass" if packet_ok else "fail",
        "operator packet includes deploy, hosted smoke, freshness, and safe refresh sequence" if packet_ok else "operator packet redeploy sequence is incomplete",
        "reports/remaining_production_gates_packet.md",
    )

    return rows


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
        "# Hosted Redeploy Preflight",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that the current local hosted runtime is ready for the next Vercel redeploy. It may run local package/freshness verifiers, but it does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Preflight gate: {summary.get('preflight_gate')}.",
        f"- Redeploy required: {summary.get('redeploy_required')}.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Changed runtime files: {summary.get('changed_runtime_files')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        f"- Next action: {summary.get('next_action')}",
        "",
        "## Checks",
        "",
        "| Check | Status | Required | Evidence | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("required_for_redeploy")),
                    str(row.get("evidence")).replace("|", "/"),
                    str(row.get("source")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safe Redeploy Boundary",
            "",
            "- Redeploy only with private Vercel token handling; do not paste token values into reports, docs, or chat.",
            "- Preserve existing Vercel environment values with `CHILLCRM_SKIP_ENV_UPSERT=1` unless a specific owner-approved environment toggle is being changed.",
            "- Use `CHILLCRM_VERCEL_INLINE_FILES=1` for the current deployment helper path.",
            "- Rerun newest hosted smoke and safe production gate refreshes after any redeploy.",
            "- Local SQLite remains source of truth until all production gates pass and owner cutover approval is explicit.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    checks = build_rows()
    failed = [row for row in checks if row["status"] != "pass" and row.get("required_for_redeploy") == "yes"]
    freshness = read_text("reports/hosted_deployment_freshness.md")
    latest_deployment_id = backtick_value(freshness, "Latest deployment")
    changed_runtime_files = int_value(plain_value(freshness, "Changed runtime files"))
    latest_url = backtick_value(read_text("reports/vercel_staging_deployment_status.md"), "URL")
    redeploy_required = changed_runtime_files > 0
    status = "hosted_redeploy_preflight_ready"
    preflight_gate = "pass"
    next_action = "Run the secret-prompted Vercel redeploy, hosted smoke, and safe gate refresh sequence."
    if failed:
        status = "hosted_redeploy_preflight_failed"
        preflight_gate = "blocked_until_preflight_passes"
        next_action = "Fix failed preflight checks before redeploying."
    elif not redeploy_required:
        status = "hosted_redeploy_not_required"
        next_action = "No hosted redeploy is required by the current freshness evidence."
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "preflight_gate": preflight_gate,
        "redeploy_required": "yes" if redeploy_required else "no",
        "latest_deployment_id": latest_deployment_id,
        "latest_url": latest_url,
        "changed_runtime_files": changed_runtime_files,
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "provider_calls": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
        "next_action": next_action,
    }
    rows = [summary, *checks]
    write_csv(REPORTS_DIR / f"{REPORT_NAME}.csv", rows)
    write_report(REPORTS_DIR / f"{REPORT_NAME}.md", rows)
    print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
