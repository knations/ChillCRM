#!/usr/bin/env python3
"""Record owner-only CHILLCRM staging shakedown signoff."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def hosted_write_audit_execution_ready(
    execution_report: str,
    smoke_report: str,
) -> tuple[bool, str]:
    execution_status = plain_value(execution_report, "Status")
    execution_gate = plain_value(execution_report, "Production gate")
    if execution_status == "hosted_write_audit_execution_passed" and execution_gate == "pass":
        return True, "execution_check=hosted_write_audit_execution_passed"
    smoke_passed = backtick_value(smoke_report, "Passed")
    smoke_failed = backtick_value(smoke_report, "Failed")
    current_smoke_passed = smoke_passed.isdigit() and int(smoke_passed) >= 14 and smoke_failed == "0"
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
        and execution_gate == "blocked_until_hosted_write_audit_rehearsal_passes"
        and current_smoke_passed
        and "approved_staging_write_audit_probe_people" in smoke_report
        and all(token in execution_report for token in required_tokens)
    )
    if reconciled:
        return True, "execution_check=hosted_write_audit_execution_reconciled_after_current_smoke"
    return False, f"execution_status={execution_status or 'missing'}; execution_gate={execution_gate or 'missing'}"


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
        "# Owner Shakedown Signoff",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records owner-only staging shakedown signoff for CHILLCRM. It does not unlock writes, create users, change provider settings, switch source of truth, expose secrets, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Approval requested: {summary.get('approval_requested')}.",
        f"- Prerequisites passed: {summary.get('prerequisites_passed')}.",
        f"- Owner shakedown signoff: {summary.get('owner_shakedown_signoff')}.",
        f"- Signoff owner: {summary.get('signoff_owner')}.",
        f"- Notes: {summary.get('notes')}.",
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
            "This signoff is valid only after hosted deployment freshness, newest hosted smoke, Supabase backup/PITR proof, hosted write-audit rehearsal, and remote monitoring readiness are green. Local SQLite remains source of truth until every production gate passes and owner cutover approval is explicit.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prerequisite_checks() -> list[dict[str, Any]]:
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    smoke = read_text("reports/vercel_hosted_app_smoke.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    deployment_freshness = read_text("reports/hosted_deployment_freshness.md")
    supabase_backup = read_text("reports/supabase_backup_readiness.md")
    write_audit = read_text("reports/hosted_write_unlock_audit_rehearsal.md")
    write_audit_execution = read_text("reports/hosted_write_audit_execution.md")
    monitoring = read_text("reports/remote_monitoring_readiness.md")

    latest_url = backtick_value(deployment, "URL")
    public_url = backtick_value(custom_domain, "Canonical URL")
    custom_domain_status = plain_value(custom_domain, "Status")
    custom_domain_gate = plain_value(custom_domain, "Production gate")
    expected_smoke_url = (
        public_url
        if public_url and custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass"
        else latest_url
    )
    smoke_url = backtick_value(smoke, "URL")
    smoke_failed = backtick_value(smoke, "Failed")
    deployment_freshness_status = plain_value(deployment_freshness, "Status")
    deployment_freshness_gate = plain_value(deployment_freshness, "Production gate")
    supabase_status = plain_value(supabase_backup, "Status")
    supabase_gate = plain_value(supabase_backup, "Production gate")
    write_audit_status = plain_value(write_audit, "Status")
    write_audit_gate = plain_value(write_audit, "Production gate")
    write_audit_execution_status = plain_value(write_audit_execution, "Status")
    write_audit_execution_gate = plain_value(write_audit_execution, "Production gate")
    write_audit_execution_ok, write_audit_execution_evidence = hosted_write_audit_execution_ready(write_audit_execution, smoke)
    monitoring_status = plain_value(monitoring, "Status")
    monitoring_gate = plain_value(monitoring, "Production gate")

    return [
        {
            "row_type": "check",
            "key": "newest_hosted_smoke_current",
            "status": "pass" if expected_smoke_url and expected_smoke_url == smoke_url and smoke_failed == "0" else "input_required",
            "evidence": f"latest_url={latest_url or 'missing'}; public_url={public_url or 'missing'}; expected_smoke_url={expected_smoke_url or 'missing'}; smoke_url={smoke_url or 'missing'}; failed={smoke_failed or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "hosted_deployment_freshness",
            "status": "pass" if deployment_freshness_status == "hosted_deployment_fresh" and deployment_freshness_gate == "pass" else "input_required",
            "evidence": f"status={deployment_freshness_status or 'missing'}; production_gate={deployment_freshness_gate or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "supabase_backup_pitr_proof",
            "status": "pass" if supabase_status == "provider_backup_and_restore_evidence_passed" and supabase_gate == "pass" else "input_required",
            "evidence": f"status={supabase_status or 'missing'}; production_gate={supabase_gate or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "hosted_write_audit_rehearsal",
            "status": (
                "pass"
                if write_audit_status == "hosted_write_unlock_audit_rehearsal_passed"
                and write_audit_gate == "pass"
                and write_audit_execution_ok
                else "input_required"
            ),
            "evidence": (
                f"status={write_audit_status or 'missing'}; production_gate={write_audit_gate or 'missing'}; "
                f"execution_status={write_audit_execution_status or 'missing'}; execution_gate={write_audit_execution_gate or 'missing'}; "
                f"{write_audit_execution_evidence}"
            ),
        },
        {
            "row_type": "check",
            "key": "remote_monitoring_readiness",
            "status": "pass" if monitoring_status == "remote_monitoring_ready" and monitoring_gate == "pass" else "input_required",
            "evidence": f"status={monitoring_status or 'missing'}; production_gate={monitoring_gate or 'missing'}",
        },
    ]


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    prereqs = prerequisite_checks()
    prereqs_passed = all(row["status"] == "pass" for row in prereqs)
    approval_requested = bool(args.approve)
    approved = approval_requested and prereqs_passed
    status = "owner_shakedown_signed_off" if approved else "pending_owner_shakedown"
    if approval_requested and not prereqs_passed:
        status = "pending_prerequisites_before_owner_shakedown"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if approved else "blocked_until_owner_shakedown_signoff",
        "approval_requested": "yes" if approval_requested else "no",
        "prerequisites_passed": "yes" if prereqs_passed else "no",
        "owner_shakedown_signoff": "approved" if approved else "pending",
        "signoff_owner": args.signoff_owner,
        "notes": args.notes,
    }
    checks = [
        {
            "row_type": "check",
            "key": "owner_only_staging_shakedown",
            "status": "approved" if approved else "pending",
            "evidence": (
                "Owner shakedown signoff: approved"
                if approved
                else "Owner shakedown signoff remains pending until prerequisite gates are green and owner approval is recorded."
            ),
        },
        {
            "row_type": "check",
            "key": "source_of_truth_boundary",
            "status": "documented",
            "evidence": "Local SQLite remains source of truth until all production gates pass and owner cutover approval is explicit.",
        },
    ]
    return [summary, *prereqs, *checks]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record owner-only CHILLCRM shakedown signoff.")
    parser.add_argument("--signoff-owner", default="Owner", help="Person giving the shakedown signoff.")
    parser.add_argument("--approve", action="store_true", help="Record owner approval for shakedown signoff.")
    parser.add_argument("--notes", default="No owner shakedown signoff recorded yet.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "owner_shakedown_signoff.csv", rows)
    write_report(REPORTS_DIR / "owner_shakedown_signoff.md", rows)
    summary = next(row for row in rows if row["row_type"] == "summary")
    print(json.dumps(summary, indent=2))
    return 1 if args.approve and summary["status"] != "owner_shakedown_signed_off" else 0


if __name__ == "__main__":
    raise SystemExit(main())
