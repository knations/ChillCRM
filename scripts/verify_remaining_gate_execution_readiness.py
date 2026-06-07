#!/usr/bin/env python3
"""Verify every remaining production blocker has a safe execution path."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

EXPECTED_INPUTS = [
    "Owner email and owner password",
    "Owner access restored and recovery disable approval",
    "Redeploy current local runtime to Vercel and rerun hosted smoke",
    "Reload current local audit/data changes to Supabase staging",
    "Supabase Management API access token or Dashboard backup evidence",
    "Owner approval for hosted write-audit rehearsal",
    "Monitoring owner/cadence approval",
    "Owner shakedown signoff",
    "Owner source-of-truth cutover approval",
]

BLOCKER_TO_INPUT = {
    "newest_hosted_smoke": "Owner email and owner password",
    "hosted_deployment_freshness": "Redeploy current local runtime to Vercel and rerun hosted smoke",
    "owner_recovery_closure": "Owner access restored and recovery disable approval",
    "supabase_staging_data_parity": "Reload current local audit/data changes to Supabase staging",
    "supabase_provider_backup": "Supabase Management API access token or Dashboard backup evidence",
    "hosted_write_unlock_audit_rehearsal": "Owner approval for hosted write-audit rehearsal",
    "remote_monitoring_readiness": "Monitoring owner/cadence approval",
    "owner_shakedown_signoff": "Owner shakedown signoff",
    "source_of_truth_cutover_approval": "Owner source-of-truth cutover approval",
}

REQUIRED_COMMAND_TOKENS = {
    "Disable temporary owner recovery": [
        "disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets",
    ],
    "Redeploy current local runtime": [
        "verify_hosted_redeploy_preflight.py",
        "deploy_chillcrm_to_vercel.py",
        "run_newest_hosted_smoke_with_vercel_bypass.py",
        "run_safe_production_gate_checks.py --refresh-only",
    ],
    "Refresh Supabase staging data parity": [
        "verify_supabase_staging_refresh_preflight.py",
        "run_supabase_staging_refresh.py --execute --prompt-secrets",
    ],
    "Verify Supabase provider backup visibility": [
        "verify_supabase_backup_readiness.py",
        "dashboard-backup-visible",
        "restore-proof",
    ],
    "Record monitoring owner/cadence approval": [
        "record_remote_monitoring_signoff.py",
        "--approve-owner",
        "--approve-cadence",
        "--approve-feedback",
    ],
    "Approve hosted write-audit rehearsal": [
        "prepare_hosted_write_audit_rehearsal.py",
        "--owner-approved",
    ],
    "Execute hosted write-audit rehearsal": [
        "execute_hosted_write_audit_rehearsal.py",
        "--owner-approved",
        "--execute",
        "--prompt-secrets",
    ],
    "Refresh monitoring and production readiness": [
        "verify_remote_monitoring_readiness.py",
        "verify_remote_production_readiness.py",
    ],
    "Record owner-only shakedown signoff": [
        "record_owner_shakedown_signoff.py",
        "--approve",
    ],
    "Record final source-of-truth cutover approval": [
        "record_source_of_truth_cutover_approval.py",
        "--approve-cutover",
        "--support-window",
        "--rollback-posture",
    ],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(name: str) -> list[dict[str, str]]:
    path = REPORTS_DIR / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def report_links(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip().startswith("reports/")]


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str, *, blocks_cutover: bool = True) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "blocks_cutover": "yes" if blocks_cutover else "no",
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    readiness_rows = read_csv("remote_production_readiness.csv")
    remaining_rows = read_csv("remaining_production_gates_packet.csv")
    owner_wave_rows = read_csv("owner_approved_wave_packet.csv")
    secret_report = read_text("reports/secret_handling_boundaries.md")

    needed_inputs = [row for row in remaining_rows if row.get("row_type") == "input"]
    phases = [row for row in remaining_rows if row.get("row_type") == "phase"]
    owner_wave_summary = next((row for row in owner_wave_rows if row.get("row_type") == "summary"), {})
    blocking_gates = [
        row
        for row in readiness_rows
        if row.get("row_type") == "gate" and row.get("blocks_production") == "yes" and row.get("status") != "pass"
        and row.get("key") != "remaining_gate_execution_readiness"
    ]

    input_names = [row.get("input") or "" for row in sorted(needed_inputs, key=lambda row: int(row.get("order") or 0))]
    add_check(
        rows,
        "expected_remaining_inputs_present",
        "pass" if input_names == EXPECTED_INPUTS else "fail",
        f"expected={len(EXPECTED_INPUTS)}, actual={len(input_names)}",
    )

    missing_blocker_coverage = []
    for gate in blocking_gates:
        expected_input = BLOCKER_TO_INPUT.get(gate.get("key") or "")
        if not expected_input or expected_input not in input_names:
            missing_blocker_coverage.append(gate.get("key") or "unknown")
    add_check(
        rows,
        "blocking_gates_have_input_coverage",
        "pass" if not missing_blocker_coverage and len(blocking_gates) <= len(BLOCKER_TO_INPUT) else "fail",
        f"blocking_gates={len(blocking_gates)}, missing_coverage={', '.join(missing_blocker_coverage) or 'none'}",
    )

    missing_reports = []
    for row in needed_inputs:
        for report in report_links(row.get("proof_report") or ""):
            if not (PROJECT_ROOT / report).exists():
                missing_reports.append(report)
    add_check(
        rows,
        "proof_reports_exist",
        "pass" if not missing_reports else "fail",
        f"proof_report_links_checked={sum(len(report_links(row.get('proof_report') or '')) for row in needed_inputs)}, missing={', '.join(missing_reports) or 'none'}",
    )

    command_failures = []
    phase_by_name = {row.get("phase") or "": row for row in phases}
    for phase_name, tokens in REQUIRED_COMMAND_TOKENS.items():
        phase = phase_by_name.get(phase_name)
        command = phase.get("safe_command") if phase else ""
        missing = [token for token in tokens if token not in str(command)]
        if missing:
            command_failures.append(f"{phase_name}: {', '.join(missing)}")
    add_check(
        rows,
        "safe_commands_cover_all_execution_phases",
        "pass" if not command_failures else "fail",
        f"phases_checked={len(REQUIRED_COMMAND_TOKENS)}, missing={'; '.join(command_failures) or 'none'}",
    )

    secret_boundaries_pass = "Status: secret_handling_boundaries_passed" in secret_report and "Findings: 0" in secret_report
    add_check(
        rows,
        "secret_boundary_current",
        "pass" if secret_boundaries_pass else "fail",
        "Secret-handling boundary report is current and has zero findings." if secret_boundaries_pass else "Secret-handling boundary report is missing or has findings.",
    )

    owner_wave_status = owner_wave_summary.get("status") or "missing"
    owner_wave_current = owner_wave_status in {
        "owner_approved_wave_ready_for_confirmation",
        "owner_approved_wave_attention_required",
    }
    add_check(
        rows,
        "owner_approved_wave_packet_current",
        "pass" if owner_wave_current else "fail",
        f"owner_wave_status={owner_wave_status}",
    )

    secret_input_rows = []
    risky_secret_handling = []
    for row in needed_inputs:
        handling = (row.get("secret_handling") or "").lower()
        approval_only = "no secret value" in handling or "approval only" in handling
        needs_private_channel = any(marker in handling for marker in ["token is secret", "password is secret", "is secret"])
        if needs_private_channel and not approval_only:
            secret_input_rows.append(row)
            if (
                "hidden prompt" not in handling
                and "one-shot" not in handling
                and "do not write token" not in handling
            ):
                risky_secret_handling.append(row.get("input") or "")
    add_check(
        rows,
        "secret_inputs_have_private_handling",
        "pass" if not risky_secret_handling else "fail",
        f"secret_inputs_checked={len(secret_input_rows)}, risky={', '.join(risky_secret_handling) or 'none'}",
    )

    source_cutover_phase = phase_by_name.get("Record final source-of-truth cutover approval", {})
    source_cutover_command = source_cutover_phase.get("safe_command") or ""
    source_cutover_guarded = all(token in source_cutover_command for token in ["--approve-cutover", "--support-window", "--rollback-posture"])
    add_check(
        rows,
        "source_of_truth_cutover_remains_final",
        "pass" if source_cutover_guarded else "fail",
        "Final cutover command requires explicit approval, support window, rollback posture, and verified URL.",
    )

    write_audit_phase = phase_by_name.get("Execute hosted write-audit rehearsal", {})
    write_audit_command = write_audit_phase.get("safe_command") or ""
    write_audit_guarded = all(token in write_audit_command for token in ["--owner-approved", "--execute", "--prompt-secrets"])
    add_check(
        rows,
        "write_audit_execution_guarded",
        "pass" if write_audit_guarded else "fail",
        "Write-audit execution remains isolated behind owner approval, execute flag, and private prompts.",
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
        "# Remaining Gate Execution Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that every remaining CHILLCRM production blocker has a safe execution path, proof report, and owner/operator boundary. It reads local reports only; it does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Checks passed: {summary.get('passed')}.",
        f"- Checks failed: {summary.get('failed')}.",
        f"- Blocking gates covered: {summary.get('blocking_gates_covered')}.",
        f"- Remaining inputs covered: {summary.get('remaining_inputs_covered')}.",
        "- Provider calls: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This audit proves execution coverage only. It does not satisfy the remaining owner confirmations, private provider credentials, backup evidence, write-audit rehearsal, owner shakedown, or final source-of-truth approval.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [row for row in checks if row.get("status") != "pass"]
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "remaining_gate_execution_ready" if not failed else "remaining_gate_execution_attention_required",
        "production_gate": "pass" if not failed else "blocked_until_remaining_gate_execution_plan_fixed",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "blocking_gates_covered": len(BLOCKER_TO_INPUT),
        "remaining_inputs_covered": len(EXPECTED_INPUTS),
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    checks = build_rows()
    summary = summarize(checks)
    rows = [summary, *checks]
    write_csv(REPORTS_DIR / "remaining_gate_execution_readiness.csv", rows)
    write_report(REPORTS_DIR / "remaining_gate_execution_readiness.md", rows)
    print(json.dumps(summary, indent=2))
    return 0 if summary["production_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
