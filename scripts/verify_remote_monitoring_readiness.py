#!/usr/bin/env python3
"""Verify CHILLCRM remote monitoring readiness from non-secret evidence."""

from __future__ import annotations

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


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def smoke_summary(text: str) -> tuple[str, int | None, int | None]:
    url = backtick_value(text, "URL")
    passed_text = backtick_value(text, "Passed")
    failed_text = backtick_value(text, "Failed")
    passed = int(passed_text) if passed_text.isdigit() else None
    failed = int(failed_text) if failed_text.isdigit() else None
    return url, passed, failed


def hosted_write_audit_execution_ready(
    execution_report: str,
    smoke_report: str,
    smoke_passed: int | None,
    smoke_failed: int | None,
) -> tuple[bool, str]:
    execution_status = plain_value(execution_report, "Status")
    if execution_status == "hosted_write_audit_execution_passed":
        return True, "execution_check=hosted_write_audit_execution_passed"
    current_smoke_passed = bool(smoke_passed and smoke_passed >= 14 and smoke_failed == 0)
    required_tokens = [
        "- Owner approved: yes.",
        "- Execution requested: yes.",
        "- Write lock restored: yes.",
        "- Secret values stored: no.",
        "- Source of truth changed: no.",
        "| deploy_write_lock_off | passed |",
        "| verify_unlocked_runtime | passed |",
        "| owner_login_unlocked | passed |",
        "| create_probe_record | passed |",
        "| verify_actor_audit | passed |",
        "| deploy_write_lock_on | passed |",
        "| verify_relocked_runtime | passed |",
        "| verify_write_lock_blocks_again | passed |",
    ]
    reconciled = (
        execution_status == "hosted_write_audit_execution_failed"
        and current_smoke_passed
        and "approved_staging_write_audit_probe_people" in smoke_report
        and all(token in execution_report for token in required_tokens)
    )
    if reconciled:
        return True, "execution_check=hosted_write_audit_execution_reconciled_after_current_smoke"
    return False, f"execution_status={execution_status or 'missing'}"


def public_health_status(base_url: str) -> tuple[int | None, str]:
    if not base_url:
        return None, "No Vercel URL is available."
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/health", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read(200)
            return int(response.status), "Public health returned an unprotected response."
    except urllib.error.HTTPError as exc:
        exc.read(200)
        return int(exc.code), "Protected response body omitted from report."
    except Exception as exc:  # noqa: BLE001 - report should record network evidence.
        return None, exc.__class__.__name__


def add_check(
    rows: list[dict[str, Any]],
    key: str,
    status: str,
    evidence: str,
    blocks_production: bool,
    owner: str,
    cadence: str,
    next_action: str,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": clip(evidence),
            "blocks_production": "yes" if blocks_production else "no",
            "owner": owner,
            "cadence": cadence,
            "next_action": clip(next_action),
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
    pass_count = sum(1 for row in checks if row.get("status") == "pass")
    fail_count = sum(1 for row in checks if row.get("status") == "fail")
    input_count = sum(1 for row in checks if row.get("status") == "input_required")
    warning_count = sum(1 for row in checks if row.get("status") == "warning")
    lines = [
        "# Remote Monitoring Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies the non-secret monitoring evidence needed before CHILLCRM becomes the remote source of truth. It does not create monitors, change Vercel or Supabase settings, unlock writes, create users, expose secrets, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Public URL: `{summary.get('public_url') or 'missing'}`.",
        f"- Latest smoke-tested URL: `{summary.get('latest_smoke_url') or 'missing'}`.",
        f"- Passed checks: {pass_count}.",
        f"- Input required: {input_count}.",
        f"- Warnings: {warning_count}.",
        f"- Failed checks: {fail_count}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Blocks Production | Owner | Cadence | Evidence | Next Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("blocks_production")),
                    str(row.get("owner")),
                    str(row.get("cadence")),
                    str(row.get("evidence")).replace("|", "/"),
                    str(row.get("next_action")).replace("|", "/"),
                ]
            )
            + " |"
        )
    blocking = [row for row in checks if row.get("blocks_production") == "yes" and row.get("status") != "pass"]
    lines.extend(["", "## Blocking Monitoring Inputs", ""])
    if blocking:
        for row in blocking:
            lines.append(f"- {row.get('key')}: {row.get('status')}. {row.get('next_action')}")
    else:
        lines.append("- None. Monitoring readiness can move to owner cutover review.")
    lines.extend(
        [
            "",
            "## Monitoring Scope",
            "",
            "- App health and Vercel protection.",
            "- Hosted login/session behavior and role-denial smoke evidence.",
            "- Supabase provider backup/PITR status.",
            "- Actor-aware audit rows after approved writes.",
            "- Private document access and unauthorized/public denial.",
            "- Bulk export controls and owner-approved package access.",
            "- Owner feedback during shakedown and first-week remote use.",
            "",
            "## Boundary",
            "",
            "A blocked status is expected until external provider proof, newest hosted smoke, write-audit rehearsal, owner/cadence signoff, and owner shakedown are complete. Local SQLite remains the source of truth until all production gates pass.",
            "",
            "## Related Files",
            "",
            "- `reports/vercel_staging_deployment_status.md`",
            "- `reports/vercel_deployment_diagnostics.md`",
            "- `reports/vercel_hosted_app_smoke.md`",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/remote_production_cutover_checklist.md`",
            "- `reports/remote_production_readiness.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows() -> list[dict[str, Any]]:
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    diagnostics = read_text("reports/vercel_deployment_diagnostics.md")
    smoke_report = read_text("reports/vercel_hosted_app_smoke.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    supabase_backup = read_text("reports/supabase_backup_readiness.md")
    cutover = read_text("reports/remote_production_cutover_checklist.md")
    server_py = read_text("crm_app/server.py")

    deployment_id = backtick_value(deployment, "Deployment ID")
    deployment_state = backtick_value(deployment, "Ready state")
    latest_url = backtick_value(deployment, "URL")
    diagnostics_id = backtick_value(diagnostics, "ID")
    diagnostics_state = backtick_value(diagnostics, "State")
    diagnostics_url = backtick_value(diagnostics, "URL")
    smoke_url, smoke_passed, smoke_failed = smoke_summary(smoke_report)
    public_url = backtick_value(custom_domain, "Canonical URL")
    custom_domain_status = plain_value(custom_domain, "Status")
    custom_domain_gate = plain_value(custom_domain, "Production gate")
    public_url_active = bool(public_url and custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass")
    expected_smoke_url = public_url if public_url_active else latest_url
    supabase_status = plain_value(supabase_backup, "Status")
    supabase_gate = plain_value(supabase_backup, "Production gate")

    rows: list[dict[str, Any]] = []
    add_check(
        rows,
        "latest_deployment_reference",
        "pass" if deployment_state == "READY" and latest_url and deployment_id else "fail",
        f"deployment_id={deployment_id or 'missing'}, state={deployment_state or 'missing'}, url={latest_url or 'missing'}",
        True,
        "Migration Operator",
        "after_each_deploy",
        "Redeploy or refresh reports/vercel_staging_deployment_status.md until the latest deployment is READY.",
    )
    add_check(
        rows,
        "vercel_diagnostics_reference",
        "pass" if diagnostics_id == deployment_id and diagnostics_state == "READY" and diagnostics_url == latest_url else "fail",
        f"diagnostics_id={diagnostics_id or 'missing'}, diagnostics_state={diagnostics_state or 'missing'}, diagnostics_url={diagnostics_url or 'missing'}",
        True,
        "Migration Operator",
        "after_each_deploy",
        "Refresh scripts/inspect_vercel_deployment.py after deployment changes.",
    )
    public_status, public_evidence = public_health_status(latest_url)
    add_check(
        rows,
        "public_protection_health_probe",
        "pass" if public_status in {401, 403} else "fail",
        f"Unauthenticated /api/health returned {public_status}; {public_evidence}",
        True,
        "Migration Operator",
        "after_each_deploy",
        "Keep Vercel Authentication enabled until owner shakedown and cutover gates pass.",
    )
    health_ready = all(token in server_py for token in ["def health_status", "/api/health", "hosted_postgres_health_check", "runtime_context"])
    add_check(
        rows,
        "health_endpoint_implementation",
        "pass" if health_ready else "fail",
        "Server implements /health and /api/health with runtime and hosted Postgres checks." if health_ready else "Health endpoint implementation evidence is missing.",
        True,
        "Migration Operator",
        "before_cutover",
        "Keep health routes wired into local and hosted runtime checks.",
    )
    expected_monitoring = [
        "App health",
        "Login sessions",
        "Write/audit checks",
        "Denied actions",
        "Private file access",
        "Backup status",
        "Export/package control",
        "Owner/internal feedback",
    ]
    missing_monitoring = [item for item in expected_monitoring if item not in cutover]
    add_check(
        rows,
        "first_week_monitoring_template",
        "pass" if not missing_monitoring else "fail",
        f"expected_checks={len(expected_monitoring)}, missing={', '.join(missing_monitoring) if missing_monitoring else 'none'}",
        True,
        "Owner + Migration Operator",
        "before_cutover",
        "Keep the cutover checklist monitoring section complete before owner handoff.",
    )
    newest_smoke_current = smoke_url == expected_smoke_url and smoke_failed == 0
    add_check(
        rows,
        "newest_hosted_smoke_current",
        "pass" if newest_smoke_current else "input_required",
        f"latest_url={latest_url or 'missing'}, public_url={public_url or 'missing'}, expected_smoke_url={expected_smoke_url or 'missing'}, smoke_url={smoke_url or 'missing'}, passed={smoke_passed}, failed={smoke_failed}",
        True,
        "Migration Operator",
        "after_each_deploy",
        (
            "Newest hosted smoke is current; rerun after deployment, schema, auth, storage, or provider-environment changes."
            if newest_smoke_current
            else "Run the hosted smoke test against https://chillcrm.app with owner credentials; Vercel bypass is not required for the public custom domain."
        ),
    )
    backup_ready = bool(supabase_gate) and not supabase_gate.startswith("blocked") and "input_required" not in supabase_status
    add_check(
        rows,
        "supabase_backup_monitoring_source",
        "pass" if backup_ready else "input_required",
        f"supabase_status={supabase_status or 'missing'}, production_gate={supabase_gate or 'missing'}",
        True,
        "Migration Operator",
        "daily_week_one",
        "Run Supabase backup readiness with a Management API token or owner-confirmed Dashboard evidence, then complete the restore/rollback proof.",
    )
    write_audit_report = read_text("reports/hosted_write_unlock_audit_rehearsal.md")
    write_audit_execution_report = read_text("reports/hosted_write_audit_execution.md")
    write_audit_status = plain_value(write_audit_report, "Status")
    write_audit_execution_status = plain_value(write_audit_execution_report, "Status")
    write_audit_execution_ok, write_audit_execution_evidence = hosted_write_audit_execution_ready(
        write_audit_execution_report,
        smoke_report,
        smoke_passed,
        smoke_failed,
    )
    add_check(
        rows,
        "hosted_write_audit_monitoring_source",
        (
            "pass"
            if write_audit_status == "hosted_write_unlock_audit_rehearsal_passed"
            and write_audit_execution_ok
            else "input_required"
        ),
        f"hosted_write_audit_status={write_audit_status or 'missing'}, execution_status={write_audit_execution_status or 'missing'}, {write_audit_execution_evidence}",
        True,
        "Migration Operator",
        "first_day",
        "After explicit owner approval, run the guarded execution script to temporarily lift the staging write lock, verify actor-aware audit rows, and restore the lock.",
    )
    monitoring_signoff = REPORTS_DIR / "remote_monitoring_signoff.md"
    monitoring_signoff_text = monitoring_signoff.read_text(encoding="utf-8") if monitoring_signoff.exists() else ""
    owner_cadence_ok = "Monitoring owner: approved" in monitoring_signoff_text and "Monitoring cadence: approved" in monitoring_signoff_text
    add_check(
        rows,
        "provider_log_error_monitoring_owner",
        "pass" if owner_cadence_ok else "input_required",
        "Monitoring owner/cadence signoff exists." if owner_cadence_ok else "No monitoring owner/cadence signoff report exists yet.",
        True,
        "Owner",
        "before_cutover",
        "Confirm who watches Vercel/Supabase logs, errors, health, backups, and audit evidence during shakedown and week one.",
    )
    feedback_ok = "Owner feedback loop: approved" in monitoring_signoff_text
    add_check(
        rows,
        "owner_feedback_monitoring_cadence",
        "pass" if feedback_ok else "input_required",
        "Owner feedback loop signoff exists." if feedback_ok else "No owner feedback monitoring signoff exists yet.",
        True,
        "Owner",
        "daily_week_one",
        "Confirm how owner feedback, missing fields, slow views, and workflow issues will be captured during shakedown and week one.",
    )

    checks = [row for row in rows if row["row_type"] == "check"]
    failed = sum(1 for row in checks if row["status"] == "fail")
    input_required = sum(1 for row in checks if row["status"] == "input_required")
    warnings = sum(1 for row in checks if row["status"] == "warning")
    status = "remote_monitoring_ready" if failed == 0 and input_required == 0 else "input_required_remote_monitoring"
    if failed:
        status = "remote_monitoring_failed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "remote_monitoring_ready" else "blocked_until_remote_monitoring_ready",
        "latest_deployment_id": deployment_id,
        "latest_url": latest_url,
        "public_url": public_url,
        "latest_smoke_url": smoke_url,
        "passed": sum(1 for row in checks if row["status"] == "pass"),
        "failed": failed,
        "input_required": input_required,
        "warnings": warnings,
    }
    return [summary, *rows]


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "remote_monitoring_readiness.csv", rows)
    write_report(REPORTS_DIR / "remote_monitoring_readiness.md", rows)
    summary = next(row for row in rows if row["row_type"] == "summary")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
