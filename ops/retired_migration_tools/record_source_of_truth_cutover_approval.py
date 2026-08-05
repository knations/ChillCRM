#!/usr/bin/env python3
"""Record final owner approval for CHILLCRM source-of-truth cutover."""

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
READINESS_CSV = REPORTS_DIR / "remote_production_readiness.csv"
SELF_GATE_KEY = "source_of_truth_cutover_approval"


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
        "# Source Of Truth Cutover Approval",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records final owner approval for CHILLCRM to move from local SQLite source-of-truth posture to hosted Supabase/Vercel source-of-truth posture. It does not unlock writes, migrate data, create users, change provider settings, expose secrets, switch source of truth by itself, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Approval requested: {summary.get('approval_requested')}.",
        f"- Other production gates passed: {summary.get('other_production_gates_passed')}.",
        f"- Owner cutover approval: {summary.get('owner_cutover_approval')}.",
        f"- Signoff owner: {summary.get('signoff_owner')}.",
        f"- Production URL: `{summary.get('production_url') or 'missing'}`.",
        f"- Latest smoke-tested URL: `{summary.get('latest_smoke_url') or 'missing'}`.",
        f"- Support window: {summary.get('support_window')}.",
        f"- Rollback posture: {summary.get('rollback_posture')}.",
        f"- Source of truth changed by this script: {summary.get('source_of_truth_changed')}.",
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
            "This approval is the final decision artifact only. It should be recorded after the technical gates are green and before owner/internal handoff declares the hosted CRM the company source of truth. Keep the final local package and document package as rollback evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def readiness_rows() -> list[dict[str, str]]:
    if not READINESS_CSV.exists():
        return []
    with READINESS_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def other_blocking_gates() -> list[dict[str, str]]:
    rows = readiness_rows()
    blockers: list[dict[str, str]] = []
    for row in rows:
        if row.get("row_type") != "gate":
            continue
        if row.get("key") == SELF_GATE_KEY:
            continue
        if row.get("blocks_production") == "yes" and row.get("status") != "pass":
            blockers.append(row)
    return blockers


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    production = read_text("reports/remote_production_readiness.md")
    smoke = read_text("reports/vercel_hosted_app_smoke.md")
    custom_domain = read_text("reports/custom_domain_readiness.md")
    owner_shakedown = read_text("reports/owner_shakedown_signoff.md")
    cutover_checklist = read_text("reports/remote_production_cutover_checklist.md")

    latest_url = backtick_value(production, "Latest URL")
    public_url = backtick_value(production, "Public URL") or backtick_value(custom_domain, "Canonical URL")
    latest_smoke_url = backtick_value(production, "Latest smoke-tested URL") or backtick_value(smoke, "URL")
    custom_domain_status = plain_value(custom_domain, "Status")
    custom_domain_gate = plain_value(custom_domain, "Production gate")
    shakedown_status = plain_value(owner_shakedown, "Status")
    shakedown_gate = plain_value(owner_shakedown, "Production gate")
    cutover_status = plain_value(cutover_checklist, "Status")
    blockers = other_blocking_gates()

    production_url = args.production_url.strip() or latest_url
    other_gates_passed = not blockers
    approval_requested = bool(args.approve_cutover)
    approved_urls = {url for url in [latest_url, public_url] if url and url != "missing"}
    url_is_known = production_url in approved_urls
    public_url_ok = production_url == public_url and custom_domain_status == "custom_domain_ready_with_app_auth" and custom_domain_gate == "pass"
    raw_url_ok = production_url == latest_url
    url_ok = bool(production_url and url_is_known and latest_smoke_url == production_url and (raw_url_ok or public_url_ok))
    shakedown_ok = shakedown_status == "owner_shakedown_signed_off" and shakedown_gate == "pass"
    checklist_ok = cutover_status == "remote_production_cutover_checklist_ready"
    support_ok = bool(args.support_window.strip())
    rollback_ok = bool(args.rollback_posture.strip())
    approved = approval_requested and other_gates_passed and url_ok and shakedown_ok and checklist_ok and support_ok and rollback_ok

    status = "source_of_truth_cutover_approved" if approved else "pending_owner_cutover_approval"
    if approval_requested and not approved:
        status = "pending_prerequisites_before_source_of_truth_cutover"

    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if approved else "blocked_until_owner_cutover_approval",
        "approval_requested": "yes" if approval_requested else "no",
        "other_production_gates_passed": "yes" if other_gates_passed else "no",
        "owner_cutover_approval": "approved" if approved else "pending",
        "signoff_owner": args.signoff_owner,
        "production_url": production_url,
        "latest_smoke_url": latest_smoke_url,
        "support_window": args.support_window.strip() or "not supplied",
        "rollback_posture": args.rollback_posture.strip() or "not supplied",
        "source_of_truth_changed": "no",
        "notes": args.notes,
    }
    checks: list[dict[str, Any]] = [
        {
            "row_type": "check",
            "key": "other_production_gates",
            "status": "pass" if other_gates_passed else "input_required",
            "evidence": "All blocking production gates except final cutover approval are passed."
            if other_gates_passed
            else "Open gates: " + ", ".join(f"{row.get('gate')}={row.get('status')}" for row in blockers),
        },
        {
            "row_type": "check",
            "key": "production_url_matches_verified_smoke",
            "status": "pass" if url_ok else "input_required",
            "evidence": f"production_url={production_url or 'missing'}; latest_url={latest_url or 'missing'}; public_url={public_url or 'missing'}; latest_smoke_url={latest_smoke_url or 'missing'}; custom_domain={custom_domain_status or 'missing'}/{custom_domain_gate or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "owner_shakedown_signed_off",
            "status": "pass" if shakedown_ok else "input_required",
            "evidence": f"status={shakedown_status or 'missing'}; production_gate={shakedown_gate or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "cutover_checklist_ready",
            "status": "pass" if checklist_ok else "input_required",
            "evidence": f"status={cutover_status or 'missing'}",
        },
        {
            "row_type": "check",
            "key": "support_window_supplied",
            "status": "pass" if support_ok else "input_required",
            "evidence": args.support_window.strip() or "Support window is required for cutover approval.",
        },
        {
            "row_type": "check",
            "key": "rollback_posture_supplied",
            "status": "pass" if rollback_ok else "input_required",
            "evidence": args.rollback_posture.strip() or "Rollback posture is required for cutover approval.",
        },
        {
            "row_type": "check",
            "key": "owner_cutover_approval",
            "status": "approved" if approved else "pending",
            "evidence": "Owner approved hosted CRM as company source of truth."
            if approved
            else "Owner cutover approval remains pending.",
        },
    ]
    return [summary, *checks]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record final CHILLCRM source-of-truth cutover approval.")
    parser.add_argument("--approve-cutover", action="store_true", help="Record final owner approval only after all prerequisite gates pass.")
    parser.add_argument("--signoff-owner", default="Owner", help="Person giving final cutover approval.")
    parser.add_argument("--production-url", default="", help="Hosted URL being approved as the source-of-truth CRM.")
    parser.add_argument("--support-window", default="", help="Non-secret cutover support window/cadence.")
    parser.add_argument("--rollback-posture", default="", help="Non-secret rollback posture retained for cutover.")
    parser.add_argument("--notes", default="No source-of-truth cutover approval recorded yet.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "source_of_truth_cutover_approval.csv", rows)
    write_report(REPORTS_DIR / "source_of_truth_cutover_approval.md", rows)
    summary = next(row for row in rows if row["row_type"] == "summary")
    print(json.dumps(summary, indent=2))
    return 1 if args.approve_cutover and summary["status"] != "source_of_truth_cutover_approved" else 0


if __name__ == "__main__":
    raise SystemExit(main())
