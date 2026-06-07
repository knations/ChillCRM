#!/usr/bin/env python3
"""Record owner monitoring signoff for CHILLCRM cutover readiness."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        "# Remote Monitoring Signoff",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records owner approval for the monitoring owner, cadence, and feedback loop used during owner shakedown and the first week after remote cutover. It does not create monitors, change Vercel or Supabase settings, unlock writes, expose secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Signoff owner: {summary.get('signoff_owner')}.",
        f"- Monitoring owner: {summary.get('monitoring_owner_status')}.",
        f"- Monitoring cadence: {summary.get('monitoring_cadence_status')}.",
        f"- Owner feedback loop: {summary.get('owner_feedback_loop_status')}.",
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
            "## Approved Cadence",
            "",
            f"- Health/protection: {summary.get('health_cadence')}.",
            f"- Provider logs/errors: {summary.get('provider_log_cadence')}.",
            f"- Backup status: {summary.get('backup_cadence')}.",
            f"- Audit/file/export checks: {summary.get('audit_file_export_cadence')}.",
            f"- Owner feedback: {summary.get('owner_feedback_cadence')}.",
            "",
            "## Boundary",
            "",
            "This signoff only covers monitoring responsibility and cadence. Production still requires newest hosted smoke, Supabase backup/PITR proof, hosted write-audit rehearsal, and owner shakedown before the hosted CRM can become source of truth.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    owner_ok = bool(args.approve_owner)
    cadence_ok = bool(args.approve_cadence)
    feedback_ok = bool(args.approve_feedback)
    status = "remote_monitoring_signoff_approved" if owner_ok and cadence_ok and feedback_ok else "pending_owner_monitoring_signoff"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": "pass" if status == "remote_monitoring_signoff_approved" else "blocked_until_owner_monitoring_signoff",
        "signoff_owner": args.signoff_owner,
        "monitoring_owner_status": "approved" if owner_ok else "pending",
        "monitoring_cadence_status": "approved" if cadence_ok else "pending",
        "owner_feedback_loop_status": "approved" if feedback_ok else "pending",
        "health_cadence": args.health_cadence,
        "provider_log_cadence": args.provider_log_cadence,
        "backup_cadence": args.backup_cadence,
        "audit_file_export_cadence": args.audit_file_export_cadence,
        "owner_feedback_cadence": args.owner_feedback_cadence,
    }
    checks = [
        {
            "row_type": "check",
            "key": "monitoring_owner",
            "status": "approved" if owner_ok else "pending",
            "evidence": f"Monitoring owner: {'approved' if owner_ok else 'pending'}; responsible party={args.signoff_owner}",
        },
        {
            "row_type": "check",
            "key": "monitoring_cadence",
            "status": "approved" if cadence_ok else "pending",
            "evidence": f"Monitoring cadence: {'approved' if cadence_ok else 'pending'}; health={args.health_cadence}; backups={args.backup_cadence}",
        },
        {
            "row_type": "check",
            "key": "owner_feedback_loop",
            "status": "approved" if feedback_ok else "pending",
            "evidence": f"Owner feedback loop: {'approved' if feedback_ok else 'pending'}; cadence={args.owner_feedback_cadence}",
        },
    ]
    return [summary, *checks]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record CHILLCRM remote monitoring signoff without changing CRM data.")
    parser.add_argument("--signoff-owner", default="Owner", help="Person responsible for monitoring signoff.")
    parser.add_argument("--approve-owner", action="store_true", help="Owner approves the monitoring owner/responsible party.")
    parser.add_argument("--approve-cadence", action="store_true", help="Owner approves the monitoring cadence.")
    parser.add_argument("--approve-feedback", action="store_true", help="Owner approves the owner-feedback loop.")
    parser.add_argument("--health-cadence", default="after each deployment, during shakedown, and first day/week one")
    parser.add_argument("--provider-log-cadence", default="during shakedown, first day, and daily during week one")
    parser.add_argument("--backup-cadence", default="daily during week one before local read-only retirement")
    parser.add_argument("--audit-file-export-cadence", default="during shakedown, first day, and after any permission change")
    parser.add_argument("--owner-feedback-cadence", default="during owner shakedown and daily during week one")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows(args)
    write_csv(REPORTS_DIR / "remote_monitoring_signoff.csv", rows)
    write_report(REPORTS_DIR / "remote_monitoring_signoff.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
