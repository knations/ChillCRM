#!/usr/bin/env python3
"""Verify final source-of-truth cutover preflight guardrails."""

from __future__ import annotations

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


def read_csv(relative_path: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def add_check(
    rows: list[dict[str, Any]],
    *,
    key: str,
    status: str,
    evidence: str,
    required_for_cutover: bool = True,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "required_for_cutover": "yes" if required_for_cutover else "no",
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def open_blocking_gates() -> list[dict[str, str]]:
    return [
        row
        for row in read_csv("reports/remote_production_readiness.csv")
        if row.get("row_type") == "gate"
        and row.get("blocks_production") == "yes"
        and row.get("status") != "pass"
        and row.get("key") != "source_of_truth_cutover_approval"
    ]


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    production = read_text("reports/remote_production_readiness.md")
    approval = read_text("reports/source_of_truth_cutover_approval.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    owner_shakedown = read_text("reports/owner_shakedown_signoff.md")
    local_freeze = read_text("reports/local_write_freeze_readiness.md")
    rollback = read_text("reports/cutover_rollback_package_readiness.md")
    owner_wave = read_text("reports/owner_confirmed_production_wave.md")
    remaining_packet = read_text("reports/remaining_production_gates_packet.md")
    approval_script = read_text("scripts/record_source_of_truth_cutover_approval.py")
    blockers = open_blocking_gates()

    latest_url = backtick_value(production, "Latest URL")
    public_url = backtick_value(production, "Public URL") or backtick_value(custom_domain, "Canonical URL")
    latest_smoke_url = backtick_value(production, "Latest smoke-tested URL")
    production_status = plain_value(production, "Status")
    production_gate = plain_value(production, "Production gate")
    approval_status = plain_value(approval, "Status")
    approval_gate = plain_value(approval, "Production gate")
    source_changed = plain_value(approval, "Source of truth changed by this script")
    owner_shakedown_status = plain_value(owner_shakedown, "Status")
    owner_shakedown_gate = plain_value(owner_shakedown, "Production gate")
    local_freeze_status = plain_value(local_freeze, "Status")
    local_freeze_gate = plain_value(local_freeze, "Production gate")
    rollback_status = plain_value(rollback, "Status")
    rollback_gate = plain_value(rollback, "Production gate")
    owner_wave_status = plain_value(owner_wave, "Status")
    custom_domain_status = plain_value(custom_domain, "Status")
    custom_domain_gate = plain_value(custom_domain, "Production gate")

    guarded_tokens = [
        "--approve-cutover",
        "--support-window",
        "--rollback-posture",
        "other_blocking_gates",
        "source_of_truth_changed",
        "owner_shakedown_signed_off",
    ]
    missing_guard_tokens = [token for token in guarded_tokens if token not in approval_script]

    command_tokens = [
        "record_source_of_truth_cutover_approval.py --approve-cutover",
        "--support-window",
        "--rollback-posture",
        "--production-url",
    ]
    missing_packet_tokens = [token for token in command_tokens if token not in remaining_packet]

    add_check(
        rows,
        key="production_readiness_available",
        status="pass" if production_status and production_gate else "input_required",
        evidence=f"status={production_status or 'missing'}, production_gate={production_gate or 'missing'}, latest_url={latest_url or 'missing'}, public_url={public_url or 'missing'}, latest_smoke_url={latest_smoke_url or 'missing'}",
    )
    add_check(
        rows,
        key="public_custom_domain_ready",
        status="pass" if custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass" else "input_required",
        evidence=f"public_url={public_url or 'missing'}, status={custom_domain_status or 'missing'}, production_gate={custom_domain_gate or 'missing'}",
    )
    add_check(
        rows,
        key="public_url_smoke_tested",
        status="pass" if public_url and latest_smoke_url == public_url else "input_required",
        evidence=f"public_url={public_url or 'missing'}, latest_smoke_url={latest_smoke_url or 'missing'}",
    )
    add_check(
        rows,
        key="open_gates_before_final_cutover",
        status="input_required" if blockers else "pass",
        evidence="Open gates: "
        + (
            ", ".join(f"{row.get('gate')}={row.get('status')}" for row in blockers)
            if blockers
            else "none"
        ),
    )
    add_check(
        rows,
        key="final_approval_still_pending",
        status="pass" if approval_status != "source_of_truth_cutover_approved" and approval_gate == "blocked_until_owner_cutover_approval" else "input_required",
        evidence=f"status={approval_status or 'missing'}, production_gate={approval_gate or 'missing'}, source_changed={source_changed or 'missing'}",
    )
    add_check(
        rows,
        key="approval_script_guarded",
        status="pass" if not missing_guard_tokens else "fail",
        evidence=f"missing_guard_tokens={', '.join(missing_guard_tokens) or 'none'}",
    )
    add_check(
        rows,
        key="operator_packet_has_final_command_shape",
        status="pass" if not missing_packet_tokens else "fail",
        evidence=f"missing_command_tokens={', '.join(missing_packet_tokens) or 'none'}",
    )
    add_check(
        rows,
        key="owner_shakedown_blocks_cutover_until_signed",
        status="input_required" if owner_shakedown_status != "owner_shakedown_signed_off" else "pass",
        evidence=f"status={owner_shakedown_status or 'missing'}, production_gate={owner_shakedown_gate or 'missing'}",
    )
    add_check(
        rows,
        key="local_freeze_guardrail_ready",
        status="pass" if local_freeze_status == "local_write_freeze_ready" and local_freeze_gate == "pass" else "input_required",
        evidence=f"status={local_freeze_status or 'missing'}, production_gate={local_freeze_gate or 'missing'}",
    )
    add_check(
        rows,
        key="rollback_package_ready",
        status="pass" if rollback_status == "cutover_rollback_package_ready" and rollback_gate == "pass" else "input_required",
        evidence=f"status={rollback_status or 'missing'}, production_gate={rollback_gate or 'missing'}",
    )
    add_check(
        rows,
        key="owner_confirmed_wave_available",
        status="pass" if owner_wave_status == "owner_confirmed_wave_plan_ready" else "input_required",
        evidence=f"status={owner_wave_status or 'missing'}",
        required_for_cutover=False,
    )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [row for row in rows if row["row_type"] == "check"]
    failed = [row for row in checks if row["status"] == "fail"]
    input_required = [row for row in checks if row["status"] == "input_required"]
    passed = [row for row in checks if row["status"] == "pass"]
    cutover_ready = not failed and not input_required
    if failed:
        status = "source_of_truth_cutover_preflight_failed"
        gate = "blocked_until_source_of_truth_preflight_fixed"
    elif cutover_ready:
        status = "source_of_truth_cutover_preflight_ready"
        gate = "pass"
    else:
        status = "source_of_truth_cutover_preflight_guarded"
        gate = "pass"
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "preflight_gate": gate,
        "cutover_ready": "yes" if cutover_ready else "no",
        "passed": len(passed),
        "input_required": len(input_required),
        "failed": len(failed),
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }


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
        "# Source-Of-Truth Cutover Preflight",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies final CHILLCRM source-of-truth cutover guardrails before owner approval. It does not call providers, unlock writes, approve cutover, switch source of truth, expose secrets, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Preflight gate: {summary.get('preflight_gate')}.",
        f"- Cutover ready: {summary.get('cutover_ready')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Input required: {summary.get('input_required')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Required For Cutover | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row.get('key')} | {row.get('status')} | {row.get('required_for_cutover')} | {str(row.get('evidence') or '').replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Final Approval Boundary",
            "",
            "The final approval command remains separate and should only be run after this preflight reports `Cutover ready: yes`, every blocking production gate has passed, the support window and rollback posture are supplied, and the owner explicitly approves hosted Supabase/Vercel as the company CRM source of truth.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    rows_with_summary = [summarize(rows), *rows]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "source_of_truth_cutover_preflight.csv", rows_with_summary)
    write_report(REPORTS_DIR / "source_of_truth_cutover_preflight.md", rows_with_summary)
    print(json.dumps(rows_with_summary[0], indent=2))
    return 1 if rows_with_summary[0]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
