#!/usr/bin/env python3
"""Validate non-secret owner replies for remaining production gates."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

SECRET_PATTERNS = [
    ("vercel_token", re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b")),
    ("supabase_publishable_key", re.compile(r"\bsb_publishable_[A-Za-z0-9_-]{10,}\b")),
    ("jwt_like_token", re.compile(r"\beyJ[A-Za-z0-9_-]{18,}\.[A-Za-z0-9_-]{18,}\.[A-Za-z0-9_-]{18,}\b")),
    ("database_url", re.compile(r"\b(?:postgresql|postgres)://[^\s`'\"<>]+")),
]

EXPECTED_KEYS = [
    "Latest backup timestamp or completed backup count",
    "PITR status",
    "Rollback proof approval",
    "Owner access restored and temporary recovery can be disabled",
    "Write-audit rehearsal approval",
    "Monitoring owner/cadence approval",
    "Owner shakedown signoff",
    "Source-of-truth cutover approval",
]


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


def normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().split())


def yes_no(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "approved", "approve"}:
        return "yes"
    if normalized in {"no", "n", "false", "not approved", "decline", "declined"}:
        return "no"
    if normalized in {"unknown", "not yet", "pending", ""}:
        return "unknown"
    return "unknown"


def first_value(value: str) -> str:
    return value.split(";", 1)[0].strip()


def segment_value(value: str, label: str) -> str:
    pattern = re.compile(rf"(?:^|;)\s*{re.escape(label)}\s*:\s*([^;]+)", re.IGNORECASE)
    match = pattern.search(value)
    return match.group(1).strip() if match else ""


def detect_secret_like_values(reply_text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = reply_text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for key, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    {
                        "row_type": "finding",
                        "key": key,
                        "status": "fail",
                        "line": line_number,
                        "evidence": "Secret-like value detected; value omitted from report.",
                    }
                )
    return findings


def parse_reply(reply_text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    expected = {normalize_key(key): key for key in EXPECTED_KEYS}
    for line in reply_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        canonical = expected.get(normalize_key(key))
        if canonical:
            parsed[canonical] = value.strip()
    return parsed


def quoted(value: str) -> str:
    return shlex.quote(value.strip())


def add_input(rows: list[dict[str, Any]], key: str, label: str, status: str, value: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "input",
            "key": key,
            "label": label,
            "status": status,
            "value": value,
            "evidence": " ".join(str(evidence).split()),
            "secret_values_stored": "no",
        }
    )


def add_action(rows: list[dict[str, Any]], key: str, status: str, action: str, command: str, proof_report: str) -> None:
    rows.append(
        {
            "row_type": "action",
            "key": key,
            "status": status,
            "action": action,
            "safe_command": command,
            "proof_report": proof_report,
            "provider_calls_by_validator": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def build_rows(reply_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    production = read_text("reports/remote_production_readiness.md")
    latest_url = backtick_value(production, "Latest URL")
    findings = detect_secret_like_values(reply_text)
    if findings:
        return findings
    if not reply_text.strip():
        add_input(
            rows,
            "owner_reply",
            "Owner gate reply",
            "input_required",
            "missing",
            "No owner reply supplied. Use reports/owner_gate_intake_packet.md for the safe non-secret reply template.",
        )
        return rows

    parsed = parse_reply(reply_text)
    missing = [key for key in EXPECTED_KEYS if key not in parsed]
    add_input(
        rows,
        "expected_fields",
        "Expected owner reply fields",
        "pass" if not missing else "input_required",
        f"{len(parsed)}/{len(EXPECTED_KEYS)} supplied",
        f"Missing fields: {', '.join(missing) if missing else 'none'}.",
    )

    backup_value = parsed.get("Latest backup timestamp or completed backup count", "")
    pitr_value = first_value(parsed.get("PITR status", ""))
    pitr_status = pitr_value.lower().strip()
    pitr_window = segment_value(parsed.get("PITR status", ""), "recovery window") or "unknown"
    backup_ready = bool(backup_value and backup_value.lower() != "unknown")
    add_input(
        rows,
        "supabase_backup_dashboard_fact",
        "Supabase backup Dashboard fact",
        "provided" if backup_ready else "input_required",
        backup_value or "missing",
        "Non-secret backup timestamp/count supplied." if backup_ready else "Backup timestamp or completed backup count is still needed.",
    )
    add_input(
        rows,
        "supabase_pitr_status",
        "Supabase PITR status",
        "provided" if pitr_status in {"enabled", "disabled", "unknown"} else "input_required",
        pitr_status or "missing",
        f"Recovery window: {pitr_window}.",
    )

    rollback_reply = parsed.get("Rollback proof approval", "")
    rollback_approval = yes_no(first_value(rollback_reply))
    use_current_package = yes_no(segment_value(rollback_reply, "use current local rollback package + storage manifest"))
    no_live_restore = yes_no(segment_value(rollback_reply, "no live Supabase restore was run"))
    rollback_ready = rollback_approval == "yes" and use_current_package == "yes" and no_live_restore == "yes"
    add_input(
        rows,
        "rollback_proof_approval",
        "Rollback proof approval",
        "provided" if rollback_ready else "input_required",
        f"approval={rollback_approval}; use_current_package={use_current_package}; no_live_restore={no_live_restore}",
        "Rollback proof is approved for the current local package path." if rollback_ready else "Rollback approval, current-package approval, and no-live-restore confirmation are all required.",
    )

    owner_recovery_yes = yes_no(parsed.get("Owner access restored and temporary recovery can be disabled", "")) == "yes"
    add_input(
        rows,
        "owner_recovery_disable_approval",
        "Owner access restored/recovery disable approval",
        "provided" if owner_recovery_yes else "input_required",
        "yes" if owner_recovery_yes else yes_no(parsed.get("Owner access restored and temporary recovery can be disabled", "")),
        "Owner access restored and recovery disable approved." if owner_recovery_yes else "Owner must confirm access before recovery can be disabled.",
    )

    write_audit_yes = yes_no(parsed.get("Write-audit rehearsal approval", "")) == "yes"
    add_input(
        rows,
        "write_audit_approval",
        "Hosted write-audit rehearsal approval",
        "provided" if write_audit_yes else "input_required",
        "yes" if write_audit_yes else yes_no(parsed.get("Write-audit rehearsal approval", "")),
        "Owner approved the controlled staging write-audit rehearsal." if write_audit_yes else "Write-audit approval remains pending.",
    )

    monitoring_reply = parsed.get("Monitoring owner/cadence approval", "")
    monitoring_yes = yes_no(first_value(monitoring_reply)) == "yes"
    monitoring_owner = segment_value(monitoring_reply, "monitoring owner") or "Kevin Nations"
    add_input(
        rows,
        "monitoring_approval",
        "Monitoring owner/cadence approval",
        "provided" if monitoring_yes else "input_required",
        f"approval={'yes' if monitoring_yes else yes_no(first_value(monitoring_reply))}; owner={monitoring_owner}",
        "Monitoring owner/cadence approval supplied." if monitoring_yes else "Monitoring owner/cadence approval remains pending.",
    )

    shakedown_reply = parsed.get("Owner shakedown signoff", "")
    shakedown_yes = shakedown_reply.lower().strip().startswith("yes")
    source_reply = parsed.get("Source-of-truth cutover approval", "")
    source_yes = source_reply.lower().strip().startswith("yes")
    support_window = segment_value(source_reply, "support window")
    rollback_posture = segment_value(source_reply, "rollback posture")
    add_input(
        rows,
        "owner_shakedown_signoff",
        "Owner shakedown signoff",
        "provided_after_prerequisites" if shakedown_yes else "not_yet",
        shakedown_reply or "missing",
        "Owner shakedown signoff is stated but remains prerequisite-gated." if shakedown_yes else "Owner shakedown is not ready yet.",
    )
    add_input(
        rows,
        "source_of_truth_cutover_approval",
        "Source-of-truth cutover approval",
        "provided_after_all_gates" if source_yes else "not_yet",
        source_reply or "missing",
        "Source-of-truth approval is stated but remains final-gate guarded." if source_yes else "Source-of-truth cutover approval is not ready yet.",
    )

    if backup_ready or rollback_ready:
        dashboard_args = []
        if backup_ready:
            dashboard_args.extend(["--dashboard-backup-visible", "--dashboard-latest-backup-at", quoted(backup_value)])
        if pitr_status in {"enabled", "disabled", "unknown"}:
            dashboard_args.extend(["--dashboard-pitr-enabled", quoted(pitr_status)])
        if pitr_window and pitr_window != "unknown":
            dashboard_args.extend(["--dashboard-pitr-window", quoted(pitr_window)])
        dashboard_args.extend(["--dashboard-evidence-owner", quoted(monitoring_owner)])
        if rollback_ready:
            dashboard_args.extend(["--restore-proof", "--use-current-local-rollback-package", "--restore-proof-owner", quoted(monitoring_owner)])
        add_action(
            rows,
            "record_supabase_dashboard_backup_evidence",
            "ready" if backup_ready and rollback_ready else "partial_input_ready",
            "Record non-secret Supabase Dashboard backup/rollback evidence.",
            ".venv/bin/python scripts/verify_supabase_backup_readiness.py " + " ".join(dashboard_args),
            "reports/supabase_backup_readiness.md",
        )
    if owner_recovery_yes:
        add_action(
            rows,
            "disable_owner_recovery_after_access",
            "ready_private_prompts_required",
            "Disable temporary owner recovery after owner access is confirmed.",
            ".venv/bin/python scripts/disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets",
            "reports/owner_recovery_disable_run.md; reports/owner_recovery_closure.md",
        )
    if write_audit_yes:
        add_action(
            rows,
            "record_write_audit_approval",
            "ready",
            "Record owner approval for hosted write-audit rehearsal preflight.",
            f".venv/bin/python scripts/prepare_hosted_write_audit_rehearsal.py --target-url {quoted(latest_url or '<latest-url>')} --owner-approved --notes \"Owner approved rehearsal preparation; no writes performed by this command.\"",
            "reports/hosted_write_unlock_audit_rehearsal.md",
        )
        add_action(
            rows,
            "execute_write_audit_rehearsal",
            "ready_private_prompts_required",
            "Execute the guarded hosted write-audit rehearsal after approval.",
            f".venv/bin/python scripts/execute_hosted_write_audit_rehearsal.py --url {quoted(latest_url or '<latest-url>')} --owner-approved --execute --prompt-secrets",
            "reports/hosted_write_audit_execution.md",
        )
    if monitoring_yes:
        add_action(
            rows,
            "record_monitoring_signoff",
            "ready",
            "Record monitoring owner/cadence signoff.",
            f".venv/bin/python scripts/record_remote_monitoring_signoff.py --signoff-owner {quoted(monitoring_owner)} --approve-owner --approve-cadence --approve-feedback",
            "reports/remote_monitoring_signoff.md; reports/remote_monitoring_readiness.md",
        )
    if shakedown_yes:
        add_action(
            rows,
            "record_owner_shakedown_signoff",
            "blocked_until_prerequisites_green",
            "Record owner shakedown signoff only after prerequisite gates pass.",
            f".venv/bin/python scripts/record_owner_shakedown_signoff.py --signoff-owner {quoted(monitoring_owner)} --approve",
            "reports/owner_shakedown_signoff.md",
        )
    if source_yes:
        add_action(
            rows,
            "record_source_of_truth_cutover",
            "blocked_until_all_other_gates_green",
            "Record final source-of-truth approval only after every other production gate passes.",
            (
                f".venv/bin/python scripts/record_source_of_truth_cutover_approval.py --approve-cutover --signoff-owner {quoted(monitoring_owner)} "
                f"--production-url {quoted(latest_url or '<verified-production-url>')} --support-window {quoted(support_window or '<support-window>')} "
                f"--rollback-posture {quoted(rollback_posture or '<rollback-posture>')}"
            ),
            "reports/source_of_truth_cutover_approval.md",
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
    inputs = [row for row in rows if row["row_type"] == "input"]
    actions = [row for row in rows if row["row_type"] == "action"]
    findings = [row for row in rows if row["row_type"] == "finding"]
    lines = [
        "# Owner Gate Reply Validation",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report validates a non-secret owner reply against the remaining CHILLCRM production gate intake template. It does not call providers, deploy code, unlock writes, approve gates by itself, prompt for secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Reply supplied: {summary.get('reply_supplied')}.",
        f"- Fields supplied: {summary.get('fields_supplied')}/{summary.get('fields_expected')}.",
        f"- Recordable actions: {summary.get('recordable_actions')}.",
        f"- Blocked actions: {summary.get('blocked_actions')}.",
        f"- Secret-like findings: {summary.get('secret_findings')}.",
        "- Secret values stored: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "",
    ]
    if findings:
        lines.extend(["## Secret-Like Findings", "", "| Line | Pattern | Evidence |", "| ---: | --- | --- |"])
        for row in findings:
            lines.append(f"| {row.get('line')} | {row.get('key')} | {row.get('evidence')} |")
    lines.extend(["## Parsed Inputs", "", "| Input | Status | Value | Evidence |", "| --- | --- | --- | --- |"])
    for row in inputs:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("label")),
                    str(row.get("status")),
                    str(row.get("value")).replace("|", "/"),
                    str(row.get("evidence")).replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Candidate Actions", ""])
    if actions:
        lines.extend(["| Action | Status | Proof Report | Safe Command |", "| --- | --- | --- | --- |"])
        for row in actions:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("action")).replace("|", "/"),
                        str(row.get("status")),
                        str(row.get("proof_report")),
                        str(row.get("safe_command")).replace("|", "/"),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- None yet.")
    lines.extend(
        [
            "",
            "## Safe Use",
            "",
            "Use `--reply-file <path>` or `--stdin` with the safe reply template from `reports/owner_gate_intake_packet.md`. Do not include tokens, service-role keys, database URLs, passwords, JWTs, or connection strings.",
            "",
            "## Boundary",
            "",
            "This validator turns owner facts into candidate commands only. The corresponding gate scripts still enforce prerequisites, owner approval flags, private prompts, write-lock restoration, and final cutover boundaries.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(rows: list[dict[str, Any]], reply_supplied: bool) -> dict[str, Any]:
    findings = [row for row in rows if row["row_type"] == "finding"]
    inputs = [row for row in rows if row["row_type"] == "input"]
    actions = [row for row in rows if row["row_type"] == "action"]
    supplied = next((row for row in inputs if row.get("key") == "expected_fields"), {})
    recordable_actions = [row for row in actions if str(row.get("status") or "").startswith("ready")]
    blocked_actions = [row for row in actions if str(row.get("status") or "").startswith("blocked")]
    if findings:
        status = "owner_gate_reply_rejected_secret_like_value"
    elif not reply_supplied:
        status = "input_required_owner_gate_reply"
    else:
        status = "owner_gate_reply_validated"
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "reply_supplied": "yes" if reply_supplied else "no",
        "fields_supplied": str(supplied.get("value") or "0/8").split("/", 1)[0],
        "fields_expected": len(EXPECTED_KEYS),
        "recordable_actions": len(recordable_actions),
        "blocked_actions": len(blocked_actions),
        "secret_findings": len(findings),
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }


def read_reply(args: argparse.Namespace) -> str:
    if args.reply_file:
        path = Path(args.reply_file)
        return path.read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a non-secret owner production-gate reply.")
    parser.add_argument("--reply-file", default="", help="Path to a text file containing the safe owner reply.")
    parser.add_argument("--stdin", action="store_true", help="Read the safe owner reply from stdin.")
    args = parser.parse_args()

    reply_text = read_reply(args)
    REPORTS_DIR.mkdir(exist_ok=True)
    rows_without_summary = build_rows(reply_text)
    summary = summarize(rows_without_summary, bool(reply_text.strip()))
    rows = [summary, *rows_without_summary]
    write_csv(REPORTS_DIR / "owner_gate_reply_validation.csv", rows)
    write_report(REPORTS_DIR / "owner_gate_reply_validation.md", rows)
    print(json.dumps(summary, indent=2))
    return 1 if summary["status"] == "owner_gate_reply_rejected_secret_like_value" else 0


if __name__ == "__main__":
    raise SystemExit(main())
