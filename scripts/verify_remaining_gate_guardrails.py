#!/usr/bin/env python3
"""Verify approval-sensitive production gate scripts are guarded."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_source(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def add_check(
    rows: list[dict[str, Any]],
    *,
    script: str,
    key: str,
    requirement: str,
    tokens: list[str],
    evidence: str,
) -> None:
    source = read_source(script)
    missing = [token for token in tokens if token not in source]
    rows.append(
        {
            "row_type": "guardrail",
            "script": script,
            "key": key,
            "status": "pass" if not missing else "fail",
            "requirement": requirement,
            "evidence": evidence if not missing else "Missing source tokens: " + ", ".join(missing),
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checks = [
        {
            "script": "scripts/disable_owner_recovery_after_access.py",
            "key": "owner_recovery_requires_owner_access_confirmation",
            "requirement": "Temporary owner recovery cannot be disabled unless owner access is explicitly confirmed.",
            "tokens": [
                "--owner-confirmed-access",
                "input_required_owner_confirmation",
                "owner confirms they can sign in with their own password",
                "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED",
            ],
            "evidence": "Disable script requires --owner-confirmed-access and records input_required when confirmation is missing.",
        },
        {
            "script": "scripts/disable_owner_recovery_after_access.py",
            "key": "owner_recovery_disable_refreshes_freshness",
            "requirement": "Recovery-disable deployment refreshes hosted smoke/readiness evidence without storing credentials.",
            "tokens": [
                "--prompt-secrets",
                "getpass.getpass",
                "run_newest_hosted_smoke_with_vercel_bypass.py",
                "verify_hosted_deployment_freshness.py",
                "secret",
            ],
            "evidence": "Disable script uses hidden prompts, refreshes hosted smoke and deployment freshness, and omits secret values from reports.",
        },
        {
            "script": "scripts/execute_hosted_write_audit_rehearsal.py",
            "key": "write_audit_requires_owner_approval_and_execute",
            "requirement": "Hosted write-audit execution cannot run without both explicit owner approval and execution confirmation.",
            "tokens": [
                "--owner-approved",
                "--execute",
                "input_required_hosted_write_audit_execution",
                "Run with --owner-approved only after explicit owner approval",
                "Run with --execute to temporarily unlock writes",
            ],
            "evidence": "Execution script records input_required unless both --owner-approved and --execute are present.",
        },
        {
            "script": "scripts/execute_hosted_write_audit_rehearsal.py",
            "key": "write_audit_restores_remote_write_lock",
            "requirement": "Hosted write-audit execution must restore REMOTE_WRITE_LOCK and prove writes are blocked again.",
            "tokens": [
                "deploy_write_lock(token, True)",
                "verify_relocked_runtime",
                "verify_write_lock_blocks_again",
                "remote_write_lock_enabled",
                "Not marked passed because relock and blocked-write proof are incomplete.",
            ],
            "evidence": "Execution script deploys the write lock back on and refuses pass status without relock and blocked-write proof.",
        },
        {
            "script": "scripts/prepare_hosted_write_audit_rehearsal.py",
            "key": "write_audit_preflight_cannot_mark_passed_without_execution_proof",
            "requirement": "Write-audit preflight cannot pass production without owner approval, execution evidence, and lock restoration evidence.",
            "tokens": [
                "--owner-approved",
                "--mark-passed",
                "--execution-evidence",
                "--write-lock-restored",
                "execution_evidence_incomplete",
            ],
            "evidence": "Preflight script separates approval from pass marking and requires execution plus lock-restoration evidence.",
        },
        {
            "script": "scripts/verify_supabase_backup_readiness.py",
            "key": "supabase_backup_accepts_token_or_dashboard_evidence_only",
            "requirement": "Supabase backup gate needs a Management API token or non-secret owner dashboard evidence.",
            "tokens": [
                "SUPABASE_ACCESS_TOKEN",
                "dashboard-backup-visible",
                "dashboard_latest_backup_at",
                "Authorization",
                "getpass.getpass",
                "input_required",
            ],
            "evidence": "Backup verifier supports hidden token use or explicit dashboard facts and does not store token values.",
        },
        {
            "script": "scripts/verify_supabase_backup_readiness.py",
            "key": "supabase_restore_proof_is_explicit",
            "requirement": "Backup visibility alone is not enough; restore or rollback proof must be explicit.",
            "tokens": [
                "--restore-proof",
                "--use-current-local-rollback-package",
                "current_local_rollback_package_detail",
                "restore_evidence_recorded",
            ],
            "evidence": "Backup verifier has separate restore-proof and current rollback package evidence paths.",
        },
        {
            "script": "scripts/record_remote_monitoring_signoff.py",
            "key": "monitoring_signoff_requires_three_owner_approvals",
            "requirement": "Monitoring readiness signoff requires owner, cadence, and feedback-loop approvals.",
            "tokens": [
                "--approve-owner",
                "--approve-cadence",
                "--approve-feedback",
                "pending_owner_monitoring_signoff",
                "remote_monitoring_signoff_approved",
            ],
            "evidence": "Monitoring signoff remains pending unless all three approval flags are supplied.",
        },
        {
            "script": "scripts/record_owner_shakedown_signoff.py",
            "key": "owner_shakedown_requires_green_prerequisites",
            "requirement": "Owner shakedown signoff cannot pass until smoke, deployment freshness, backup, write-audit, and monitoring gates are green.",
            "tokens": [
                "--approve",
                "pending_prerequisites_before_owner_shakedown",
                "hosted_deployment_freshness",
                "supabase_backup_pitr_proof",
                "hosted_write_audit_rehearsal",
                "remote_monitoring_readiness",
            ],
            "evidence": "Owner shakedown script checks all prerequisite production gates before accepting approval.",
        },
        {
            "script": "scripts/record_source_of_truth_cutover_approval.py",
            "key": "source_of_truth_cutover_is_final_and_separate",
            "requirement": "Source-of-truth cutover approval is separate, final, and cannot pass while other production gates are open.",
            "tokens": [
                "--approve-cutover",
                "other_blocking_gates",
                "pending_prerequisites_before_source_of_truth_cutover",
                "source_of_truth_changed",
                "support_window",
                "rollback_posture",
            ],
            "evidence": "Cutover approval script checks other blocking gates, support window, rollback posture, and records no source-of-truth change by itself.",
        },
        {
            "script": "scripts/run_safe_production_gate_checks.py",
            "key": "safe_runner_does_not_approve_owner_only_steps",
            "requirement": "The safe runner can refresh reports and prompted safe checks, but cannot sign owner approvals or unlock writes.",
            "tokens": [
                "requires_separate_owner_approval",
                "This runner will not approve write-audit rehearsal",
                "This runner will not sign monitoring cadence",
                "remote_write_lock_changed",
                "source_of_truth_changed",
            ],
            "evidence": "Safe runner records write-audit, owner signoffs, and source-of-truth cutover as separate owner-approved steps.",
        },
    ]
    for check in checks:
        add_check(rows, **check)
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
    checks = [row for row in rows if row["row_type"] == "guardrail"]
    lines = [
        "# Remaining Gate Guardrails",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that approval-sensitive CHILLCRM production gate scripts are guarded at the source level. It reads local source files only; it does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Guardrails checked: {summary.get('guardrails_checked')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        "- Provider calls: no.",
        "- Remote write lock changed: no.",
        "- CRM record writes: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Guardrails",
        "",
        "| Script | Guardrail | Status | Requirement | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("script")),
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("requirement")).replace("|", "/"),
                    str(row.get("evidence")).replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a source-level guardrail audit. It proves the scripts contain the expected approvals and refusal paths; it does not replace live provider smoke, owner approvals, Supabase backup evidence, write-audit execution, or final cutover signoff.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    checks = build_rows()
    failed = [row for row in checks if row["status"] != "pass"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "remaining_gate_guardrails_passed" if not failed else "remaining_gate_guardrails_failed",
        "guardrails_checked": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "provider_calls": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    rows = [summary, *checks]
    write_csv(REPORTS_DIR / "remaining_gate_guardrails.csv", rows)
    write_report(REPORTS_DIR / "remaining_gate_guardrails.md", rows)
    print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
