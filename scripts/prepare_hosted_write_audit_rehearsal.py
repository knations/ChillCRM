#!/usr/bin/env python3
"""Prepare the hosted write-unlock audit rehearsal gate without unlocking writes."""

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


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def int_value(value: str) -> int:
    return int(value) if value.strip().isdigit() else 0


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str, source: str) -> None:
    rows.append(
        {
            "row_type": "preflight_check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "source": source,
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
    checks = [row for row in rows if row["row_type"] == "preflight_check"]
    steps = [row for row in rows if row["row_type"] == "step"]
    lines = [
        "# Hosted Write-Unlock Audit Rehearsal",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report prepares the hosted write-unlock actor-audit rehearsal. It does not lift REMOTE_WRITE_LOCK, write CRM records, create users, change Vercel/Supabase settings, expose secrets, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Approval status: {summary.get('approval_status')}.",
        f"- Preflight status: {summary.get('preflight_status')}.",
        f"- Preflight passed/input/failed: {summary.get('preflight_passed')}/{summary.get('preflight_input_required')}/{summary.get('preflight_failed')}.",
        f"- Execution evidence recorded: {summary.get('execution_evidence_recorded')}.",
        f"- Write lock restored evidence: {summary.get('write_lock_restored_evidence')}.",
        f"- Target URL: `{summary.get('target_url') or 'latest staging URL'}`.",
        f"- Notes: {summary.get('notes')}",
        "",
        "## Preflight Checks",
        "",
        "| Check | Status | Evidence | Source |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row.get('key')} | {row.get('status')} | {str(row.get('evidence') or '').replace('|', '/')} | {row.get('source')} |"
        )
    lines.extend(
        [
            "",
            "## Rehearsal Steps",
            "",
            "| Order | Step | Status | Evidence Required |",
            "| ---: | --- | --- | --- |",
        ]
    )
    for row in steps:
        lines.append(f"| {row.get('order')} | {row.get('step')} | {row.get('status')} | {str(row.get('evidence_required') or '').replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Safe Execution Boundary",
            "",
            "- Requires explicit owner approval before any hosted write lock is lifted.",
            "- Preflight must pass before the owner-approved rehearsal is executed.",
            "- Use a safe staging target only, not a production source-of-truth app.",
            "- Capture actor-aware audit rows for approved record/tag/note/task/cleanup-flag test writes.",
            "- Re-enable `REMOTE_WRITE_LOCK=true` immediately after rehearsal.",
            "- This report cannot be marked passed without explicit execution evidence and write-lock restoration evidence.",
            "- Rerun hosted smoke, monitoring readiness, and production readiness after the rehearsal.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    smoke = read_text("reports/vercel_hosted_app_smoke.md")
    environment = read_text("reports/vercel_environment_readiness.md")
    readiness = read_text("reports/remote_production_readiness.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    server_py = read_text("crm_app/server.py")
    requested_url = normalize_url(args.target_url)
    latest_url = normalize_url(backtick_value(deployment, "URL"))
    public_url = normalize_url(backtick_value(readiness, "Public URL") or backtick_value(custom_domain, "Canonical URL"))
    target_url = requested_url or public_url or latest_url
    target_equivalents = {value for value in [latest_url, public_url] if value}
    deployment_state = backtick_value(deployment, "Ready state")
    smoke_url = normalize_url(backtick_value(smoke, "URL"))
    smoke_passed = int_value(backtick_value(smoke, "Passed"))
    smoke_failed = int_value(backtick_value(smoke, "Failed"))
    readiness_status = plain_value(readiness, "Status")
    readiness_gate = plain_value(readiness, "Production gate")

    rows: list[dict[str, Any]] = []
    add_check(
        rows,
        "target_deployment_ready",
        "pass" if target_url in target_equivalents and latest_url and deployment_state == "READY" else "input_required",
        (
            f"target_url={target_url or 'missing'}, latest_url={latest_url or 'missing'}, "
            f"public_url={public_url or 'missing'}, state={deployment_state or 'missing'}"
        ),
        "reports/vercel_staging_deployment_status.md; reports/custom_domain_readiness.md",
    )
    add_check(
        rows,
        "newest_hosted_smoke_current",
        "pass" if smoke_url in target_equivalents and smoke_passed >= 14 and smoke_failed == 0 else "input_required",
        (
            f"smoke_url={smoke_url or 'missing'}, target_url={target_url or 'missing'}, "
            f"public_url={public_url or 'missing'}, passed={smoke_passed}, failed={smoke_failed}"
        ),
        "reports/vercel_hosted_app_smoke.md; reports/custom_domain_readiness.md",
    )
    lock_evidence = all(
        token in smoke
        for token in [
            "| health | passed | hosted Postgres reachable, staging locks enabled |",
            "| remote_write_lock | passed | create_record blocked before validation unlock |",
            "| bulk_export_lock | passed | complete package export blocked |",
        ]
    ) and "| REMOTE_WRITE_LOCK | plain_value_sanity | pass |" in environment
    add_check(
        rows,
        "locked_staging_runtime",
        "pass" if lock_evidence else "input_required",
        "Hosted smoke and Vercel environment evidence show REMOTE_WRITE_LOCK=true and export package lock enabled." if lock_evidence else "Current smoke/environment reports do not prove locked staging runtime.",
        "reports/vercel_hosted_app_smoke.md; reports/vercel_environment_readiness.md",
    )
    actor_schema_ready = all(
        token in server_py
        for token in [
            "app_user_id",
            "actor_email",
            "actor_roles",
            "permission_action",
            "insert_audit_log",
        ]
    )
    add_check(
        rows,
        "actor_audit_wiring",
        "pass" if actor_schema_ready else "input_required",
        "Server audit wiring includes actor identity, role snapshot, permission action, and audit insertion support." if actor_schema_ready else "Actor-aware audit wiring evidence is incomplete.",
        "crm_app/server.py",
    )
    role_denial_ready = all(
        token in smoke
        for token in [
            "| role_matrix_permission_denial | passed |",
            "| app_user_lifecycle_owner_api | passed |",
            "| app_user_deactivation | passed |",
        ]
    )
    add_check(
        rows,
        "role_denial_and_user_lifecycle_smoke",
        "pass" if role_denial_ready else "input_required",
        "Hosted smoke proves owner user lifecycle, role denials, and deactivated-user denial." if role_denial_ready else "Hosted role/user lifecycle smoke evidence is incomplete.",
        "reports/vercel_hosted_app_smoke.md",
    )
    source_truth_ready = (
        readiness_status == "blocked_until_production_gates_pass"
        and readiness_gate == "blocked"
        and "Local remains source of truth until gates pass | pass" in readiness
    )
    add_check(
        rows,
        "non_source_of_truth_target",
        "pass" if source_truth_ready else "input_required",
        "Production readiness confirms hosted staging is not source of truth and local SQLite remains authoritative." if source_truth_ready else "Source-of-truth boundary is not proven by the current production readiness report.",
        "reports/remote_production_readiness.md",
    )
    preflight_checks = [row for row in rows if row["row_type"] == "preflight_check"]
    preflight_failed = sum(1 for row in preflight_checks if row.get("status") == "fail")
    preflight_input = sum(1 for row in preflight_checks if row.get("status") == "input_required")
    preflight_passed = sum(1 for row in preflight_checks if row.get("status") == "pass")
    preflight_ready = preflight_failed == 0 and preflight_input == 0
    approved = bool(args.owner_approved)
    execution_evidence = args.execution_evidence.strip()
    write_lock_restored = bool(args.write_lock_restored)
    passed = bool(args.mark_passed and approved and preflight_ready and execution_evidence and write_lock_restored)
    status = "pending_owner_approval"
    if preflight_failed:
        status = "preflight_failed"
    elif not preflight_ready:
        status = "preflight_input_required"
    if passed:
        status = "hosted_write_unlock_audit_rehearsal_passed"
    elif args.mark_passed:
        status = "execution_evidence_incomplete"
    elif approved and preflight_ready:
        status = "approved_not_executed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if passed else "blocked_until_hosted_write_audit_rehearsal_passes",
        "approval_status": "approved" if approved else "pending",
        "preflight_status": "ready" if preflight_ready else "not_ready",
        "preflight_passed": preflight_passed,
        "preflight_input_required": preflight_input,
        "preflight_failed": preflight_failed,
        "execution_evidence_recorded": "yes" if execution_evidence else "no",
        "write_lock_restored_evidence": "yes" if write_lock_restored else "no",
        "target_url": target_url,
        "notes": args.notes,
    }
    step_specs = [
        ("Confirm owner approval", "Owner approval captured before lifting hosted write lock."),
        ("Pass preflight", "Latest staging target, locked runtime, actor-audit wiring, and source-of-truth boundary are verified."),
        ("Temporarily lift write lock", "`REMOTE_WRITE_LOCK=false` applied only to the safe staging target."),
        ("Run actor-aware write probes", "Approved record/tag/note/task/cleanup-flag writes create actor-aware audit rows."),
        ("Restore write lock", "`REMOTE_WRITE_LOCK=true` restored and verified."),
        ("Refresh smoke/readiness", "Hosted smoke, monitoring readiness, and production readiness reports are regenerated."),
    ]
    rows.insert(0, summary)
    for order, (step, evidence) in enumerate(step_specs, start=1):
        rows.append(
            {
                "row_type": "step",
                "order": order,
                "step": step,
                "status": "completed" if passed else "pending",
                "evidence_required": evidence,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare hosted write-audit rehearsal without changing remote state.")
    parser.add_argument("--target-url", default="", help="Safe staging target URL for the eventual rehearsal.")
    parser.add_argument("--owner-approved", action="store_true", help="Record that owner approved the rehearsal.")
    parser.add_argument("--mark-passed", action="store_true", help="Only use after the full hosted write-audit rehearsal has actually passed.")
    parser.add_argument("--execution-evidence", default="", help="Required non-secret evidence summary when marking the rehearsal passed.")
    parser.add_argument("--write-lock-restored", action="store_true", help="Required when marking passed; confirms REMOTE_WRITE_LOCK=true was restored and verified.")
    parser.add_argument("--notes", default="No owner approval recorded yet; no remote writes were performed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "hosted_write_unlock_audit_rehearsal.csv", rows)
    write_report(REPORTS_DIR / "hosted_write_unlock_audit_rehearsal.md", rows)
    summary = next(row for row in rows if row["row_type"] == "summary")
    print(json.dumps(summary, indent=2))
    return 1 if args.mark_passed and summary["status"] != "hosted_write_unlock_audit_rehearsal_passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
