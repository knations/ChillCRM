#!/usr/bin/env python3
"""Summarize CHILLCRM remote production readiness from existing evidence."""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass
class Gate:
    key: str
    gate: str
    status: str
    blocks_production: str
    evidence: str
    source: str
    next_action: str


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(value: Any, limit: int = 220) -> str:
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


def public_health_status(base_url: str) -> tuple[int | None, str]:
    if not base_url:
        return None, "No Vercel URL is available."
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/health", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read(200)
            return int(response.status), "Public health request returned a non-protected response."
    except urllib.error.HTTPError as exc:
        exc.read(200)
        return int(exc.code), "Protected response body omitted from report."
    except Exception as exc:  # noqa: BLE001 - evidence report should capture network failures.
        return None, str(exc)


def add_gate(gates: list[Gate], key: str, gate: str, status: str, blocks: bool, evidence: str, source: str, next_action: str) -> None:
    gates.append(
        Gate(
            key=key,
            gate=gate,
            status=status,
            blocks_production="yes" if blocks else "no",
            evidence=clip(evidence),
            source=source,
            next_action=clip(next_action),
        )
    )


def build_gates() -> tuple[dict[str, Any], list[Gate]]:
    gates: list[Gate] = []
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    diagnostics = read_text("reports/vercel_deployment_diagnostics.md")
    vercel_environment = read_text("reports/vercel_environment_readiness.md")
    public_protection = read_text("reports/vercel_public_protection.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    deployment_freshness = read_text("reports/hosted_deployment_freshness.md")
    redeploy_preflight = read_text("reports/hosted_redeploy_preflight.md")
    remaining_execution = read_text("reports/remaining_gate_execution_readiness.md")
    secret_boundaries = read_text("reports/secret_handling_boundaries.md")
    package_report = read_text("reports/hosted_app_deployment_package_verification.md")
    integrity_report = read_text("reports/local_functional_data_integrity.md")
    backup_drill = read_text("reports/backup_restore_drill.md")
    local_write_freeze = read_text("reports/local_write_freeze_readiness.md")
    cutover_rollback = read_text("reports/cutover_rollback_package_readiness.md")
    source_cutover_preflight = read_text("reports/source_of_truth_cutover_preflight.md")
    staging_parity = read_text("reports/supabase_staging_data_parity.md")
    staging_refresh_preflight = read_text("reports/supabase_staging_refresh_preflight.md")
    staging_refresh_run = read_text("reports/supabase_staging_refresh_run.md")
    supabase_backup = read_text("reports/supabase_backup_readiness.md")
    smoke_report = read_text("reports/vercel_hosted_app_smoke.md")
    rollout = read_text("reports/remote_admin_rollout_board.md")
    shakedown = read_text("reports/remote_admin_pilot_onboarding_plan.md")
    cutover = read_text("reports/remote_production_cutover_checklist.md")
    monitoring = read_text("reports/remote_monitoring_readiness.md")
    write_audit = read_text("reports/hosted_write_unlock_audit_rehearsal.md")
    write_audit_execution = read_text("reports/hosted_write_audit_execution.md")
    owner_signoff = read_text("reports/owner_shakedown_signoff.md")
    owner_recovery = read_text("reports/owner_recovery_closure.md")
    source_cutover = read_text("reports/source_of_truth_cutover_approval.md")

    deployment_id = backtick_value(deployment, "Deployment ID")
    deployment_state = backtick_value(deployment, "Ready state")
    latest_url = backtick_value(deployment, "URL")
    diagnostics_id = backtick_value(diagnostics, "ID")
    diagnostics_state = backtick_value(diagnostics, "State")
    diagnostics_url = backtick_value(diagnostics, "URL")
    smoke_url, smoke_passed, smoke_failed = smoke_summary(smoke_report)
    public_url = backtick_value(custom_domain, "Canonical URL")

    add_gate(
        gates,
        "local_data_integrity",
        "Local CRM data integrity",
        "pass" if "Blocking failures: 0" in integrity_report and "Hosted staging gate: pass" in integrity_report else "fail",
        True,
        "Local functional integrity report has 0 blocking failures and hosted staging gate pass." if integrity_report else "Missing local functional integrity report.",
        "reports/local_functional_data_integrity.md",
        "Fix local integrity failures before any production cutover." if not integrity_report else "Keep this report current after material local data/schema changes.",
    )
    add_gate(
        gates,
        "hosted_deployment_package",
        "Hosted deployment package",
        "pass" if "Failed: 0" in package_report and "handler_users_static_ui | pass" in package_report else "fail",
        True,
        "Deployment package verification passed with owner Users UI in the static bundle." if package_report else "Missing hosted package verification report.",
        "reports/hosted_app_deployment_package_verification.md",
        "Rerun scripts/verify_hosted_app_deployment_package.py after package, route, or static bundle changes.",
    )
    add_gate(
        gates,
        "vercel_deployment_ready",
        "Latest Vercel deployment ready",
        "pass" if deployment_state == "READY" and latest_url else "fail",
        True,
        f"deployment_id={deployment_id or 'missing'}, state={deployment_state or 'missing'}, url={latest_url or 'missing'}",
        "reports/vercel_staging_deployment_status.md",
        "Redeploy and wait for READY if this gate fails.",
    )
    add_gate(
        gates,
        "vercel_diagnostics_match_latest",
        "Vercel diagnostics match latest deployment",
        "pass" if diagnostics_id == deployment_id and diagnostics_state == "READY" and diagnostics_url == latest_url and "`api/index.py` present: `yes`" in diagnostics else "fail",
        True,
        f"diagnostics_id={diagnostics_id or 'missing'}, deployment_id={deployment_id or 'missing'}, api/index.py present={'yes' if '`api/index.py` present: `yes`' in diagnostics else 'no'}",
        "reports/vercel_deployment_diagnostics.md",
        "Refresh scripts/inspect_vercel_deployment.py after each deployment.",
    )
    deployment_freshness_status = plain_value(deployment_freshness, "Status")
    deployment_freshness_gate = plain_value(deployment_freshness, "Production gate")
    deployment_freshness_changed = plain_value(deployment_freshness, "Changed runtime files")
    redeploy_preflight_status = plain_value(redeploy_preflight, "Status")
    redeploy_preflight_gate = plain_value(redeploy_preflight, "Preflight gate")
    add_gate(
        gates,
        "hosted_deployment_freshness",
        "Hosted deployment matches local runtime",
        "pass" if deployment_freshness_status == "hosted_deployment_fresh" and deployment_freshness_gate == "pass" else "input_required",
        True,
        (
            f"status={deployment_freshness_status or 'missing'}, production_gate={deployment_freshness_gate or 'missing'}, "
            f"changed_runtime_files={deployment_freshness_changed or 'missing'}, "
            f"redeploy_preflight={redeploy_preflight_status or 'missing'}/{redeploy_preflight_gate or 'missing'}"
            if deployment_freshness
            else "Missing hosted deployment freshness report."
        ),
        "reports/hosted_deployment_freshness.md; reports/hosted_redeploy_preflight.md",
        "Redeploy current local hosted runtime to Vercel, then rerun hosted smoke and safe production-gate refreshes.",
    )
    vercel_environment_status = plain_value(vercel_environment, "Status")
    vercel_environment_gate = plain_value(vercel_environment, "Production gate")
    vercel_environment_required_missing = plain_value(vercel_environment, "Required keys input-required")
    add_gate(
        gates,
        "vercel_environment_readiness",
        "Vercel environment readiness",
        "pass" if vercel_environment_status == "vercel_environment_ready" and vercel_environment_gate == "pass" else "input_required",
        True,
        (
            f"status={vercel_environment_status or 'missing'}, production_gate={vercel_environment_gate or 'missing'}, required_input_required={vercel_environment_required_missing or 'missing'}"
            if vercel_environment
            else "Missing Vercel environment readiness report."
        ),
        "reports/vercel_environment_readiness.md",
        "Run scripts/verify_vercel_environment_readiness.py with a Vercel token to verify required environment variable names and production targets without storing values.",
    )

    public_status, public_evidence = public_health_status(latest_url)
    add_gate(
        gates,
        "vercel_public_protection",
        "Vercel public protection remains enabled",
        "pass" if public_status in {401, 403} else "fail",
        True,
        f"Unauthenticated /api/health returned {public_status}; {public_evidence}",
        "https://latest-deployment/api/health",
        "Keep Vercel Authentication enabled until owner-shakedown gates pass.",
    )
    public_protection_status = plain_value(public_protection, "Status")
    public_protection_gate = plain_value(public_protection, "Production gate")
    public_protection_failed = plain_value(public_protection, "Failed")
    add_gate(
        gates,
        "vercel_broad_public_protection",
        "Vercel broad public protection",
        "pass" if public_protection_status == "vercel_public_protection_passed" and public_protection_gate == "pass" else "fail",
        True,
        (
            f"status={public_protection_status or 'missing'}, production_gate={public_protection_gate or 'missing'}, failed={public_protection_failed or 'missing'}"
            if public_protection
            else "Missing Vercel public protection report."
        ),
        "reports/vercel_public_protection.md",
        "Run scripts/verify_vercel_public_protection.py to confirm app, API, report, and static bundle routes remain protected from public unauthenticated access.",
    )
    custom_domain_status = plain_value(custom_domain, "Status")
    custom_domain_gate = plain_value(custom_domain, "Production gate")
    custom_domain_denied = plain_value(custom_domain, "CRM data public access denied")
    custom_domain_lock = plain_value(custom_domain, "Remote write lock")
    add_gate(
        gates,
        "custom_domain_readiness",
        "Public custom domain readiness",
        "pass" if custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass" else "input_required",
        True,
        (
            f"url={public_url or 'missing'}, status={custom_domain_status or 'missing'}, production_gate={custom_domain_gate or 'missing'}, data_public_denied={custom_domain_denied or 'missing'}, remote_write_lock={custom_domain_lock or 'missing'}"
            if custom_domain
            else "Missing custom domain readiness report."
        ),
        "reports/custom_domain_readiness.md",
        "Run scripts/verify_custom_domain_readiness.py after Vercel custom-domain or DNS changes; use ChillCRM.app as the owner-facing production URL once this passes.",
    )
    secret_boundaries_status = plain_value(secret_boundaries, "Status")
    secret_boundaries_gate = plain_value(secret_boundaries, "Production gate")
    secret_boundaries_findings = plain_value(secret_boundaries, "Findings")
    secret_boundaries_failed = plain_value(secret_boundaries, "Failed checks")
    add_gate(
        gates,
        "secret_handling_boundaries",
        "Secret-handling boundary",
        "pass" if secret_boundaries_status == "secret_handling_boundaries_passed" and secret_boundaries_gate == "pass" else "fail",
        True,
        (
            f"status={secret_boundaries_status or 'missing'}, production_gate={secret_boundaries_gate or 'missing'}, findings={secret_boundaries_findings or 'missing'}, failed_checks={secret_boundaries_failed or 'missing'}"
            if secret_boundaries
            else "Missing secret-handling boundary report."
        ),
        "reports/secret_handling_boundaries.md",
        "Run scripts/verify_secret_handling_boundaries.py after source, report, config, or runner changes and clear any secret-like findings before production cutover.",
    )
    remaining_execution_status = plain_value(remaining_execution, "Status")
    remaining_execution_gate = plain_value(remaining_execution, "Production gate")
    remaining_execution_failed = plain_value(remaining_execution, "Checks failed")
    add_gate(
        gates,
        "remaining_gate_execution_readiness",
        "Remaining gate execution readiness",
        "pass" if remaining_execution_status == "remaining_gate_execution_ready" and remaining_execution_gate == "pass" else "fail",
        True,
        (
            f"status={remaining_execution_status or 'missing'}, production_gate={remaining_execution_gate or 'missing'}, failed={remaining_execution_failed or 'missing'}"
            if remaining_execution
            else "Missing remaining gate execution readiness report."
        ),
        "reports/remaining_gate_execution_readiness.md",
        "Run scripts/verify_remaining_gate_execution_readiness.py to confirm every remaining blocker has a safe command, proof report, and owner/operator boundary.",
    )
    add_gate(
        gates,
        "previous_hosted_smoke",
        "Prior full hosted smoke",
        "pass" if smoke_failed == 0 and (smoke_passed or 0) >= 12 else "fail",
        False,
        f"prior_smoke_url={smoke_url or 'missing'}, passed={smoke_passed}, failed={smoke_failed}",
        "reports/vercel_hosted_app_smoke.md",
        "Use as historical proof only; latest deployment still needs smoke if URLs differ.",
    )
    public_url_active = bool(public_url and custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass")
    expected_smoke_url = public_url if public_url_active else latest_url
    newest_smoke_current = smoke_failed == 0 and smoke_url == expected_smoke_url
    add_gate(
        gates,
        "newest_hosted_smoke",
        "Newest hosted smoke",
        "pass" if newest_smoke_current else "input_required",
        True,
        f"latest_url={latest_url or 'missing'}, public_url={public_url or 'missing'}, expected_smoke_url={expected_smoke_url or 'missing'}, smoke_url={smoke_url or 'missing'}, failed={smoke_failed}",
        "scripts/verify_vercel_hosted_app.py",
        (
            "Newest hosted smoke is current; rerun after deployment, schema, auth, storage, or provider-environment changes."
            if newest_smoke_current
            else "Run newest hosted smoke against the current owner-facing URL with owner email, owner password, and EXPECT_DOCUMENT_FILE_ACCESS=true."
        ),
    )
    owner_recovery_status = plain_value(owner_recovery, "Status")
    owner_recovery_gate = plain_value(owner_recovery, "Production gate")
    owner_recovery_switch = plain_value(owner_recovery, "Owner recovery switch")
    add_gate(
        gates,
        "owner_recovery_closure",
        "Owner recovery switch disabled",
        "pass" if owner_recovery_status == "owner_recovery_closed" and owner_recovery_gate == "pass" else "input_required",
        True,
        (
            f"status={owner_recovery_status or 'missing'}, production_gate={owner_recovery_gate or 'missing'}, switch={owner_recovery_switch or 'missing'}"
            if owner_recovery
            else "Missing owner recovery closure report."
        ),
        "reports/owner_recovery_closure.md",
        "After the owner confirms they can sign in with their own password, redeploy with CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=false and rerun owner recovery closure verification.",
    )
    add_gate(
        gates,
        "local_backup_restore_drill",
        "Local disposable backup/restore drill",
        "pass" if "Status: backup_restore_drill_passed" in backup_drill and "Failed: 0" in backup_drill else "fail",
        True,
        "Local disposable restore drill passed without touching the live database." if backup_drill else "Missing backup restore drill report.",
        "reports/backup_restore_drill.md",
        "Rerun scripts/verify_backup_restore_drill.py after material local data/schema changes.",
    )
    local_freeze_status = plain_value(local_write_freeze, "Status")
    local_freeze_gate = plain_value(local_write_freeze, "Production gate")
    local_freeze_failed = plain_value(local_write_freeze, "Checks failed")
    add_gate(
        gates,
        "local_write_freeze_readiness",
        "Local write-freeze readiness",
        "pass" if local_freeze_status == "local_write_freeze_ready" and local_freeze_gate == "pass" else "fail",
        True,
        (
            f"status={local_freeze_status or 'missing'}, production_gate={local_freeze_gate or 'missing'}, failed={local_freeze_failed or 'missing'}"
            if local_write_freeze
            else "Missing local write-freeze readiness report."
        ),
        "reports/local_write_freeze_readiness.md",
        "Run scripts/verify_local_write_freeze_readiness.py before final production packaging, and set CHILLCRM_LOCAL_WRITE_FREEZE=true only during the approved local cutover freeze window.",
    )
    cutover_rollback_status = plain_value(cutover_rollback, "Status")
    cutover_rollback_gate = plain_value(cutover_rollback, "Production gate")
    cutover_rollback_failed = plain_value(cutover_rollback, "Failed")
    add_gate(
        gates,
        "cutover_rollback_package_readiness",
        "Cutover rollback package readiness",
        "pass" if cutover_rollback_status == "cutover_rollback_package_ready" and cutover_rollback_gate == "pass" else "fail",
        True,
        (
            f"status={cutover_rollback_status or 'missing'}, production_gate={cutover_rollback_gate or 'missing'}, failed={cutover_rollback_failed or 'missing'}"
            if cutover_rollback
            else "Missing cutover rollback package readiness report."
        ),
        "reports/cutover_rollback_package_readiness.md",
        "Run scripts/verify_cutover_rollback_package_readiness.py after material local data, backup, package, or document-storage changes.",
    )
    source_cutover_preflight_status = plain_value(source_cutover_preflight, "Status")
    source_cutover_preflight_gate = plain_value(source_cutover_preflight, "Preflight gate")
    source_cutover_preflight_ready = plain_value(source_cutover_preflight, "Cutover ready")
    source_cutover_preflight_failed = plain_value(source_cutover_preflight, "Failed")
    add_gate(
        gates,
        "source_of_truth_cutover_preflight",
        "Source-of-truth cutover preflight guardrails",
        "pass" if source_cutover_preflight_gate == "pass" and source_cutover_preflight_failed == "0" else "fail",
        True,
        (
            f"status={source_cutover_preflight_status or 'missing'}, preflight_gate={source_cutover_preflight_gate or 'missing'}, cutover_ready={source_cutover_preflight_ready or 'missing'}, failed={source_cutover_preflight_failed or 'missing'}"
            if source_cutover_preflight
            else "Missing source-of-truth cutover preflight report."
        ),
        "reports/source_of_truth_cutover_preflight.md",
        "Run scripts/verify_source_of_truth_cutover_preflight.py before final owner cutover approval; final cutover still requires all blocking gates, support window, rollback posture, and explicit owner approval.",
    )
    staging_parity_status = plain_value(staging_parity, "Status")
    staging_parity_gate = plain_value(staging_parity, "Production gate")
    staging_parity_table_failures = plain_value(staging_parity, "Table failures")
    staging_parity_checks_failed = plain_value(staging_parity, "Checks failed")
    staging_preflight_status = plain_value(staging_refresh_preflight, "Status")
    staging_preflight_gate = plain_value(staging_refresh_preflight, "Preflight gate")
    staging_run_status = plain_value(staging_refresh_run, "Status")
    staging_run_gate = plain_value(staging_refresh_run, "Production gate")
    add_gate(
        gates,
        "supabase_staging_data_parity",
        "Supabase staging data parity",
        "pass" if staging_parity_status == "supabase_staging_data_parity_passed" and staging_parity_gate == "pass" else "input_required",
        True,
        (
            f"status={staging_parity_status or 'missing'}, production_gate={staging_parity_gate or 'missing'}, table_failures={staging_parity_table_failures or 'missing'}, checks_failed={staging_parity_checks_failed or 'missing'}, refresh_preflight={staging_preflight_status or 'missing'}/{staging_preflight_gate or 'missing'}, refresh_run={staging_run_status or 'missing'}/{staging_run_gate or 'missing'}"
            if staging_parity
            else "Missing Supabase staging data parity report."
        ),
        "reports/supabase_staging_data_parity.md; reports/supabase_staging_refresh_preflight.md; reports/supabase_staging_refresh_run.md",
        "Run the Supabase staging refresh preflight, then use scripts/run_supabase_staging_refresh.py --execute --prompt-secrets to reload current local CRM data into Supabase staging and rerun staging validation/parity.",
    )
    supabase_backup_status = plain_value(supabase_backup, "Status")
    production_gate = plain_value(supabase_backup, "Production gate")
    add_gate(
        gates,
        "supabase_provider_backup",
        "Supabase provider backup/PITR visibility",
        "pass" if production_gate and not production_gate.startswith("blocked") and "input_required" not in supabase_backup_status else "input_required",
        True,
        f"status={supabase_backup_status or 'missing'}, production_gate={production_gate or 'missing'}",
        "reports/supabase_backup_readiness.md",
        "Run scripts/verify_supabase_backup_readiness.py with SUPABASE_ACCESS_TOKEN, or record owner-confirmed Supabase Dashboard backup evidence plus restore/rollback proof.",
    )
    write_audit_status = plain_value(write_audit, "Status")
    write_audit_gate = plain_value(write_audit, "Production gate")
    write_audit_execution_status = plain_value(write_audit_execution, "Status")
    write_audit_execution_gate = plain_value(write_audit_execution, "Production gate")
    add_gate(
        gates,
        "hosted_write_unlock_audit_rehearsal",
        "Hosted write-unlock actor-audit rehearsal",
        (
            "pass"
            if write_audit_status == "hosted_write_unlock_audit_rehearsal_passed"
            and write_audit_gate == "pass"
            and write_audit_execution_status == "hosted_write_audit_execution_passed"
            and write_audit_execution_gate == "pass"
            else "input_required"
        ),
        True,
        (
            f"preflight_status={write_audit_status or 'missing'}, preflight_gate={write_audit_gate or 'missing'}, "
            f"execution_status={write_audit_execution_status or 'missing'}, execution_gate={write_audit_execution_gate or 'missing'}"
        ),
        "reports/hosted_write_unlock_audit_rehearsal.md; reports/hosted_write_audit_execution.md",
        "Requires explicit owner approval before temporarily lifting REMOTE_WRITE_LOCK on a safe staging target, then execution through scripts/execute_hosted_write_audit_rehearsal.py.",
    )
    monitoring_status = plain_value(monitoring, "Status")
    monitoring_gate = plain_value(monitoring, "Production gate")
    monitoring_inputs = plain_value(monitoring, "Input required")
    monitoring_failed = plain_value(monitoring, "Failed checks")
    add_gate(
        gates,
        "remote_monitoring_readiness",
        "Remote monitoring readiness",
        "pass" if monitoring_status == "remote_monitoring_ready" and monitoring_gate == "pass" else "input_required",
        True,
        (
            f"status={monitoring_status or 'missing'}, production_gate={monitoring_gate or 'missing'}, input_required={monitoring_inputs or 'missing'}, failed={monitoring_failed or 'missing'}"
            if monitoring
            else "Missing remote monitoring readiness report."
        ),
        "reports/remote_monitoring_readiness.md",
        "Run scripts/verify_remote_monitoring_readiness.py, then complete owner/cadence, backup, audit, file, export, and feedback monitoring inputs.",
    )
    owner_signoff_status = plain_value(owner_signoff, "Status")
    owner_signoff_gate = plain_value(owner_signoff, "Production gate")
    add_gate(
        gates,
        "owner_shakedown_signoff",
        "Owner-only staging shakedown signoff",
        "pass" if owner_signoff_status == "owner_shakedown_signed_off" and owner_signoff_gate == "pass" else "input_required",
        True,
        (
            f"status={owner_signoff_status or 'missing'}, production_gate={owner_signoff_gate or 'missing'}"
            if owner_signoff
            else ("Owner shakedown plan exists, but no owner signoff report exists yet." if shakedown else "Missing owner shakedown plan.")
        ),
        "reports/owner_shakedown_signoff.md",
        "Run owner-only staging shakedown after hosted smoke, backup/restore, and write-audit gates are green.",
    )
    source_cutover_status = plain_value(source_cutover, "Status")
    source_cutover_gate = plain_value(source_cutover, "Production gate")
    source_cutover_owner = plain_value(source_cutover, "Owner cutover approval")
    add_gate(
        gates,
        "source_of_truth_cutover_approval",
        "Owner source-of-truth cutover approval",
        "pass" if source_cutover_status == "source_of_truth_cutover_approved" and source_cutover_gate == "pass" else "input_required",
        True,
        (
            f"status={source_cutover_status or 'missing'}, production_gate={source_cutover_gate or 'missing'}, approval={source_cutover_owner or 'missing'}"
            if source_cutover
            else "Missing final source-of-truth cutover approval report."
        ),
        "reports/source_of_truth_cutover_approval.md",
        "After every other production gate passes, record explicit owner approval before declaring hosted Supabase/Vercel as the company CRM source of truth.",
    )
    add_gate(
        gates,
        "source_of_truth_lock",
        "Local remains source of truth until gates pass",
        "pass" if "local_crm_sqlite" in rollout and "source of truth" in cutover.lower() else "warning",
        False,
        "Rollout and cutover reports preserve local SQLite as source of truth until production gates pass.",
        "reports/remote_admin_rollout_board.md",
        "Do not declare hosted CRM source of truth until all blocking gates pass.",
    )

    blocking = [gate for gate in gates if gate.blocks_production == "yes" and gate.status != "pass"]
    failures = [gate for gate in gates if gate.status == "fail"]
    inputs = [gate for gate in gates if gate.status == "input_required"]
    warnings = [gate for gate in gates if gate.status == "warning"]
    passes = [gate for gate in gates if gate.status == "pass"]
    summary = {
        "generated_at": now_utc(),
        "status": "ready_for_owner_cutover_review" if not blocking else "blocked_until_production_gates_pass",
        "latest_deployment_id": deployment_id,
        "latest_url": latest_url,
        "public_url": public_url,
        "latest_smoke_url": smoke_url,
        "passed": len(passes),
        "failed": len(failures),
        "input_required": len(inputs),
        "warnings": len(warnings),
        "blocking_gates": len(blocking),
        "production_gate": "pass" if not blocking else "blocked",
    }
    return summary, gates


def write_csv(path: Path, summary: dict[str, Any], gates: list[Gate]) -> None:
    rows: list[dict[str, Any]] = [{"row_type": "summary", **summary}]
    rows.extend({"row_type": "gate", **gate.__dict__} for gate in gates)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], gates: list[Gate]) -> None:
    blocking = [gate for gate in gates if gate.blocks_production == "yes" and gate.status != "pass"]
    newest_smoke_gate = next((gate for gate in gates if gate.key == "newest_hosted_smoke"), None)
    newest_smoke_command = (
        "- Newest hosted smoke: current for this deployment; rerun with the Vercel bypass and owner credentials only after deployment, schema, auth, storage, or provider-environment changes."
        if newest_smoke_gate and newest_smoke_gate.status == "pass"
        else "- Newest hosted smoke: run `scripts/verify_vercel_hosted_app.py` against `https://chillcrm.app` with owner email/password and `EXPECT_DOCUMENT_FILE_ACCESS=true` supplied through environment variables or hidden prompts. Vercel bypass is not required for the public custom domain."
    )
    lines = [
        "# Remote Production Readiness",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "This report consolidates the current non-secret production gates for CHILLCRM Supabase/Vercel cutover. It does not unlock writes, restore backups, create users, upload files, expose secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary['status']}.",
        f"- Production gate: {summary['production_gate']}.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Public URL: `{summary.get('public_url') or 'missing'}`.",
        f"- Latest smoke-tested URL: `{summary.get('latest_smoke_url') or 'missing'}`.",
        f"- Passing gates: {summary['passed']}.",
        f"- Input-required gates: {summary['input_required']}.",
        f"- Warning gates: {summary['warnings']}.",
        f"- Failed gates: {summary['failed']}.",
        f"- Blocking gates remaining: {summary['blocking_gates']}.",
        "",
        "## Gate Results",
        "",
        "| Gate | Status | Blocks Production | Evidence | Source | Next Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for gate in gates:
        lines.append(
            "| "
            + " | ".join(
                [
                    gate.gate.replace("|", "/"),
                    gate.status,
                    gate.blocks_production,
                    gate.evidence.replace("|", "/"),
                    gate.source,
                    gate.next_action.replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Blocking Gates", ""])
    if blocking:
        for gate in blocking:
            lines.append(f"- {gate.gate}: {gate.status}. {gate.next_action}")
    else:
        lines.append("- None. Owner cutover review can begin, but source-of-truth switch still requires explicit owner approval.")
    lines.extend(
        [
            "",
            "## Safe Next Commands",
            "",
            newest_smoke_command,
            "- Supabase backup visibility: run `scripts/verify_supabase_backup_readiness.py` with `SUPABASE_ACCESS_TOKEN` supplied through the environment or hidden prompt, or record owner-confirmed Dashboard backup evidence using the dashboard flags shown in `reports/remaining_production_gates_packet.md`.",
            "- Owner recovery closure: after owner access is confirmed, redeploy with `CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=false` and rerun `scripts/verify_owner_recovery_closure.py`.",
            "- Hosted deployment freshness: after local hosted runtime changes, redeploy with `CHILLCRM_VERCEL_INLINE_FILES=1`, rerun hosted smoke, and refresh safe gate reports.",
            "- Local write-freeze readiness: run `scripts/verify_local_write_freeze_readiness.py` before the final production package; set `CHILLCRM_LOCAL_WRITE_FREEZE=true` only during the approved local cutover freeze window.",
            "- Cutover rollback package readiness: run `scripts/verify_cutover_rollback_package_readiness.py` after material local data, backup, package, or document-storage changes.",
            "- Supabase staging data parity: run `scripts/verify_supabase_staging_refresh_preflight.py`, then use `scripts/run_supabase_staging_refresh.py --execute --prompt-secrets` to rerun the Supabase staging load/validation after local data changes and refresh parity.",
            "- Hosted write-audit rehearsal: requires explicit owner approval before temporarily lifting `REMOTE_WRITE_LOCK` on a safe staging target.",
            "- Hosted write-audit execution: run `scripts/execute_hosted_write_audit_rehearsal.py --owner-approved --execute --prompt-secrets` only after explicit owner approval; it restores `REMOTE_WRITE_LOCK=true` before it can pass.",
            "- Remote monitoring readiness: run `scripts/verify_remote_monitoring_readiness.py`, then confirm the owner/cadence for health, provider logs/errors, backups, audit rows, file access, exports, and owner feedback before source-of-truth cutover.",
            "- Source-of-truth cutover approval: after all other blocking gates pass, run `scripts/record_source_of_truth_cutover_approval.py --approve-cutover` with the owner, support window, rollback posture, and verified production URL.",
            "",
            "## Boundary",
            "",
            "This is a gate report only. A blocked status is expected until the remaining external proofs and owner shakedown are complete. Do not make the hosted CRM the source of truth until all blocking gates pass and the owner approves cutover.",
            "",
            "## Related Files",
            "",
            "- `reports/vercel_staging_deployment_status.md`",
            "- `reports/vercel_deployment_diagnostics.md`",
            "- `reports/vercel_environment_readiness.md`",
            "- `reports/vercel_public_protection.md`",
            "- `reports/custom_domain_readiness.md`",
            "- `reports/secret_handling_boundaries.md`",
            "- `reports/remaining_gate_execution_readiness.md`",
            "- `reports/hosted_deployment_freshness.md`",
            "- `reports/vercel_hosted_app_smoke.md`",
            "- `reports/owner_recovery_closure.md`",
            "- `reports/source_of_truth_cutover_approval.md`",
            "- `reports/hosted_write_audit_execution.md`",
            "- `reports/supabase_backup_readiness.md`",
            "- `reports/remote_monitoring_readiness.md`",
            "- `reports/backup_restore_drill.md`",
            "- `reports/local_write_freeze_readiness.md`",
            "- `reports/cutover_rollback_package_readiness.md`",
            "- `reports/supabase_staging_data_parity.md`",
            "- `reports/supabase_staging_refresh_preflight.md`",
            "- `reports/supabase_staging_refresh_run.md`",
            "- `reports/remote_admin_rollout_board.md`",
            "- `reports/remote_production_cutover_checklist.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    summary, gates = build_gates()
    write_csv(REPORTS_DIR / "remote_production_readiness.csv", summary, gates)
    write_report(REPORTS_DIR / "remote_production_readiness.md", summary, gates)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
