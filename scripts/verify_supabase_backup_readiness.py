#!/usr/bin/env python3
"""Verify Supabase backup/PITR readiness through API or owner-recorded evidence."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SUPABASE_API = "https://api.supabase.com"
DEFAULT_PROJECT_REF = "ckjbnummsxqcyeahzynz"

BACKUPS_DOC = "https://supabase.com/docs/guides/platform/backups"
MANAGEMENT_API_DOC = "https://supabase.com/docs/reference/api/v1-list-all-backups"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(value: Any, limit: int = 160) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def plain_value(text: str, label: str) -> str:
    prefix = f"- {label}: "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip().rstrip(".")
    return ""


def backtick_value(text: str, label: str) -> str:
    value = plain_value(text, label)
    if value.startswith("`") and "`" in value[1:]:
        return value.split("`", 2)[1].strip()
    return ""


def current_local_rollback_package_detail() -> tuple[bool, str]:
    path = REPORTS_DIR / "cutover_rollback_package_readiness.md"
    if not path.exists():
        return False, "Cutover rollback package readiness report is missing."
    report = path.read_text(encoding="utf-8")
    status = plain_value(report, "Status")
    production_gate = plain_value(report, "Production gate")
    failed = plain_value(report, "Failed")
    latest_backup = backtick_value(report, "Latest backup")
    document_files = plain_value(report, "Document package files")
    storage_rows = plain_value(report, "Storage manifest rows")
    if status != "cutover_rollback_package_ready" or production_gate != "pass" or failed != "0":
        return (
            False,
            f"Cutover rollback package is not currently ready: status={status or 'missing'}, production_gate={production_gate or 'missing'}, failed={failed or 'missing'}.",
        )
    return (
        True,
        (
            "Current cutover rollback package readiness passed with 0 failures; "
            f"latest local backup={latest_backup or 'not reported'}, "
            f"document package files={document_files or 'not reported'}, "
            f"storage manifest rows={storage_rows or 'not reported'}."
        ),
    )


def request_json(path: str, access_token: str) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{SUPABASE_API}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return int(response.status), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"error": body}
        return int(exc.code), payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["result"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    checks = [row for row in rows if row["row_type"] == "check"]
    backups = [row for row in rows if row["row_type"] == "backup"]
    dashboard = [row for row in rows if row["row_type"] == "dashboard_evidence"]
    restore = [row for row in rows if row["row_type"] == "restore_evidence"]
    sources = [row for row in rows if row["row_type"] == "official_source"]
    pass_count = sum(1 for row in checks if row.get("status") == "pass")
    fail_count = sum(1 for row in checks if row.get("status") == "fail")
    input_count = sum(1 for row in checks if row.get("status") == "input_required")
    warn_count = sum(1 for row in checks if row.get("status") == "warning")
    lines = [
        "# Supabase Backup Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies Supabase database backup visibility through the read-only Management API or explicit owner-recorded Dashboard evidence. It does not restore a backup, change project settings, upload files, create users, unlock writes, or modify CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Project ref: `{summary.get('project_ref')}`.",
        f"- API checked: {summary.get('api_checked')}.",
        f"- Dashboard evidence recorded: {summary.get('dashboard_evidence_recorded')}.",
        f"- Restore/rollback evidence recorded: {summary.get('restore_evidence_recorded')}.",
        f"- Passed checks: {pass_count}.",
        f"- Warnings: {warn_count}.",
        f"- Input required: {input_count}.",
        f"- Failed checks: {fail_count}.",
        f"- Completed backups seen: {summary.get('completed_backups')}.",
        f"- PITR enabled: {summary.get('pitr_enabled')}.",
        f"- WAL-G/physical backup enabled: {summary.get('walg_enabled')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Blocks Production |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row.get('key')} | {row.get('status')} | {clip(row.get('evidence')).replace('|', '/')} | {row.get('blocks_production')} |"
        )
    if backups:
        lines.extend(
            [
                "",
                "## Backups Seen",
                "",
                "| ID | Status | Physical | Inserted At |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in backups:
            lines.append(
                f"| {row.get('backup_id')} | {row.get('status')} | {row.get('is_physical_backup')} | {row.get('inserted_at')} |"
            )
    if dashboard:
        lines.extend(
            [
                "",
                "## Dashboard Evidence",
                "",
                "| Key | Value |",
                "| --- | --- |",
            ]
        )
        for row in dashboard:
            lines.append(f"| {row.get('key')} | {clip(row.get('value'), 220).replace('|', '/')} |")
    if restore:
        lines.extend(
            [
                "",
                "## Restore/Rollback Evidence",
                "",
                "| Key | Value |",
                "| --- | --- |",
            ]
        )
        for row in restore:
            lines.append(f"| {row.get('key')} | {clip(row.get('value'), 220).replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Storage Scope",
            "",
            "Supabase database backups cover the database, not Storage API object bytes. CHILLCRM must keep the recovered-document package, storage manifest, and private Storage validation as a separate rollback path for the 203 recovered documents.",
            "",
            "## Remaining Gate",
            "",
            "This report can confirm backup availability, but it does not perform a restore. Production readiness still requires either a Supabase restore into an approved disposable target or an owner-approved rollback drill using the final frozen local package plus Supabase storage manifest.",
            "",
            "## Official Sources",
            "",
            "| Source | Detail | URL |",
            "| --- | --- | --- |",
        ]
    )
    for row in sources:
        lines.append(f"| {row.get('key')} | {row.get('detail')} | {row.get('url')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dashboard_pitr_value(value: str) -> bool | str:
    normalized = value.strip().lower()
    if normalized in {"yes", "true", "enabled", "on"}:
        return True
    if normalized in {"no", "false", "disabled", "off"}:
        return False
    return "unknown"


def build_rows(args: argparse.Namespace, access_token: str) -> list[dict[str, Any]]:
    generated_at = now_utc()
    project_ref = args.project_ref.strip()
    rows: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    api_checked = "no"
    payload: dict[str, Any] = {}
    completed_backups = 0
    pitr_enabled: bool | str = "unknown"
    walg_enabled: bool | str = "unknown"
    dashboard_evidence_recorded = bool(args.dashboard_backup_visible)
    restore_evidence_recorded = bool(args.restore_proof)
    dashboard_owner = args.dashboard_evidence_owner.strip()
    restore_owner = args.restore_proof_owner.strip()
    dashboard_completed = args.dashboard_completed_backups if args.dashboard_completed_backups is not None else 0
    dashboard_pitr = dashboard_pitr_value(args.dashboard_pitr_enabled)
    dashboard_backup_path_visible = bool(
        args.dashboard_backup_visible
        and dashboard_owner
        and (
            dashboard_completed > 0
            or bool(args.dashboard_latest_backup_at.strip())
            or dashboard_pitr is True
            or bool(args.dashboard_pitr_window.strip())
        )
    )

    if not access_token and not dashboard_backup_path_visible:
        checks.append(
            {
                "row_type": "check",
                "key": "management_api_token",
                "status": "input_required",
                "evidence": "Set SUPABASE_ACCESS_TOKEN with backups_read/database:read permission to list project backups, or record owner-confirmed Dashboard backup evidence.",
                "blocks_production": "yes",
            }
        )
    elif not access_token:
        checks.append(
            {
                "row_type": "check",
                "key": "management_api_token",
                "status": "not_used",
                "evidence": "Management API token not supplied; owner-recorded Dashboard backup evidence is being used instead.",
                "blocks_production": "no",
            }
        )
    else:
        checks.append(
            {
                "row_type": "check",
                "key": "management_api_token",
                "status": "pass",
                "evidence": "Token supplied via environment or hidden prompt; value not stored.",
                "blocks_production": "no",
            }
        )
        api_checked = "yes"
        status_code, payload = request_json(f"/v1/projects/{project_ref}/database/backups", access_token)
        if status_code == 200:
            backups = payload.get("backups") or []
            completed = [backup for backup in backups if str(backup.get("status") or "").upper() == "COMPLETED"]
            completed_backups = len(completed)
            pitr_enabled = bool(payload.get("pitr_enabled"))
            walg_enabled = bool(payload.get("walg_enabled"))
            checks.append(
                {
                    "row_type": "check",
                    "key": "list_backups_api",
                    "status": "pass",
                    "evidence": f"Management API returned {len(backups)} backup rows.",
                    "blocks_production": "no",
                }
            )
            backup_path_ok = completed_backups > 0 or bool(pitr_enabled) or bool(walg_enabled)
            checks.append(
                {
                    "row_type": "check",
                    "key": "backup_path_visible",
                    "status": "pass" if backup_path_ok else "fail",
                    "evidence": f"completed_backups={completed_backups}, pitr_enabled={pitr_enabled}, walg_enabled={walg_enabled}",
                    "blocks_production": "yes" if not backup_path_ok else "no",
                }
            )
            checks.append(
                {
                    "row_type": "check",
                    "key": "pitr_status",
                    "status": "pass" if pitr_enabled else "warning",
                    "evidence": "PITR is enabled." if pitr_enabled else "PITR is not enabled or not reported; daily/provider backups may still exist, but PITR restore granularity is not proven.",
                    "blocks_production": "no",
                }
            )
            for backup in backups[:20]:
                rows.append(
                    {
                        "row_type": "backup",
                        "backup_id": backup.get("id"),
                        "status": backup.get("status"),
                        "is_physical_backup": backup.get("is_physical_backup"),
                        "inserted_at": backup.get("inserted_at"),
                    }
                )
        elif status_code in {401, 403}:
            checks.append(
                {
                    "row_type": "check",
                    "key": "list_backups_api",
                    "status": "input_required",
                    "evidence": f"Management API returned {status_code}; token must include database:read/backups_read access.",
                    "blocks_production": "yes",
                }
            )
        else:
            checks.append(
                {
                    "row_type": "check",
                    "key": "list_backups_api",
                    "status": "fail",
                    "evidence": f"Management API returned {status_code}: {clip(payload)}",
                    "blocks_production": "yes",
                }
            )

    if dashboard_evidence_recorded:
        evidence_rows = {
            "evidence_owner": args.dashboard_evidence_owner.strip() or "unspecified",
            "backup_visible": "yes" if args.dashboard_backup_visible else "no",
            "completed_backups": dashboard_completed,
            "latest_backup_at": args.dashboard_latest_backup_at.strip() or "not supplied",
            "pitr_enabled": dashboard_pitr,
            "pitr_window": args.dashboard_pitr_window.strip() or "not supplied",
            "notes": args.dashboard_notes.strip() or "not supplied",
        }
        rows.extend({"row_type": "dashboard_evidence", "key": key, "value": value} for key, value in evidence_rows.items())
        checks.append(
            {
                "row_type": "check",
                "key": "dashboard_backup_evidence",
                "status": "pass" if dashboard_backup_path_visible else "input_required",
                "evidence": (
                    "Owner-recorded Dashboard evidence includes a visible backup/PITR path."
                    if dashboard_backup_path_visible
                    else "Dashboard evidence is incomplete; include evidence owner plus latest backup timestamp, completed backup count, or PITR recovery window."
                ),
                "blocks_production": "yes" if not dashboard_backup_path_visible else "no",
            }
        )
        if dashboard_completed > completed_backups:
            completed_backups = dashboard_completed
        if pitr_enabled == "unknown" and dashboard_pitr != "unknown":
            pitr_enabled = dashboard_pitr

    api_backup_path_visible = any(row.get("key") == "backup_path_visible" and row.get("status") == "pass" for row in checks)
    backup_path_visible = api_backup_path_visible or dashboard_backup_path_visible
    if not any(row.get("key") == "backup_path_visible" for row in checks):
        checks.append(
            {
                "row_type": "check",
                "key": "backup_path_visible",
                "status": "pass" if backup_path_visible else "input_required",
                "evidence": (
                    f"completed_backups={completed_backups}, pitr_enabled={pitr_enabled}, dashboard_evidence={dashboard_evidence_recorded}"
                    if backup_path_visible
                    else "No provider backup/PITR path has been verified through API or Dashboard evidence."
                ),
                "blocks_production": "yes" if not backup_path_visible else "no",
            }
        )

    restore_detail = args.restore_proof_detail.strip()
    restore_type = args.restore_proof_type.strip()
    local_rollback_ok = False
    local_rollback_detail = ""
    if args.use_current_local_rollback_package:
        local_rollback_ok, local_rollback_detail = current_local_rollback_package_detail()
        restore_type = restore_type or "owner_approved_local_rollback"
        restore_detail = restore_detail or local_rollback_detail
    restore_proof_ok = bool(
        args.restore_proof
        and restore_owner
        and restore_type
        and restore_detail
        and (local_rollback_ok if args.use_current_local_rollback_package else True)
    )
    if restore_evidence_recorded:
        restore_rows = {
            "proof_owner": restore_owner or "unspecified",
            "proof_type": restore_type or "unspecified",
            "proof_detail": restore_detail or "not supplied",
            "current_local_rollback_package_used": "yes" if args.use_current_local_rollback_package else "no",
            "notes": args.restore_notes.strip() or "not supplied",
        }
        rows.extend({"row_type": "restore_evidence", "key": key, "value": value} for key, value in restore_rows.items())
    checks.append(
        {
            "row_type": "check",
            "key": "restore_drill_status",
            "status": "pass" if restore_proof_ok else "input_required",
            "evidence": (
                f"Restore/rollback proof recorded: {restore_type}; {restore_detail}"
                if restore_proof_ok
                else (
                    local_rollback_detail
                    if args.use_current_local_rollback_package and not local_rollback_ok
                    else "A restore to an approved disposable target or documented owner-approved rollback drill is still required before production cutover; include proof owner and verified detail."
                )
            ),
            "blocks_production": "yes" if not restore_proof_ok else "no",
        }
    )

    checks.append(
        {
            "row_type": "check",
            "key": "storage_backup_scope",
            "status": "warning",
            "evidence": "Supabase database backups do not restore Storage API object bytes; keep CHILLCRM document package and storage manifest as a separate file rollback path.",
            "blocks_production": "no",
        }
    )

    blocking = [row for row in checks if row.get("blocks_production") == "yes" and row.get("status") != "pass"]
    status = "provider_backup_and_restore_evidence_passed"
    production_gate = "pass"
    if not access_token and not dashboard_backup_path_visible:
        status = "input_required_supabase_access_token"
    elif any(row.get("status") == "fail" for row in checks):
        status = "supabase_backup_readiness_failed"
    elif blocking:
        status = "provider_backup_partially_verified_restore_drill_pending"
    if status != "provider_backup_and_restore_evidence_passed":
        production_gate = "blocked_until_provider_backup_and_restore_evidence_pass"

    rows.insert(
        0,
        {
            "row_type": "summary",
            "generated_at": generated_at,
            "status": status,
            "project_ref": project_ref,
            "api_checked": api_checked,
            "dashboard_evidence_recorded": "yes" if dashboard_evidence_recorded else "no",
            "restore_evidence_recorded": "yes" if restore_evidence_recorded else "no",
            "completed_backups": completed_backups,
            "pitr_enabled": pitr_enabled,
            "walg_enabled": walg_enabled,
            "production_gate": production_gate,
        },
    )
    rows.extend(checks)
    rows.extend(
        [
            {
                "row_type": "official_source",
                "key": "supabase_database_backups",
                "detail": "Supabase database backup behavior, PITR notes, and storage scope caveat.",
                "url": BACKUPS_DOC,
            },
            {
                "row_type": "official_source",
                "key": "supabase_management_api_list_backups",
                "detail": "Management API endpoint used to list project database backups.",
                "url": MANAGEMENT_API_DOC,
            },
        ]
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Supabase backup/PITR readiness without restoring or changing data.")
    parser.add_argument("--project-ref", default=os.environ.get("SUPABASE_PROJECT_REF", DEFAULT_PROJECT_REF))
    parser.add_argument("--access-token-env", default="SUPABASE_ACCESS_TOKEN")
    parser.add_argument("--prompt-token", action="store_true", help="Prompt for a Supabase Management API token if the env var is missing.")
    parser.add_argument("--dashboard-backup-visible", action="store_true", help="Record that the Supabase Dashboard shows a provider backup or PITR path.")
    parser.add_argument("--dashboard-completed-backups", type=int, default=None, help="Completed backups visible in the Supabase Dashboard, if known.")
    parser.add_argument("--dashboard-latest-backup-at", default="", help="Latest backup timestamp shown in the Dashboard.")
    parser.add_argument("--dashboard-pitr-enabled", default="unknown", choices=["unknown", "yes", "no"], help="PITR status observed in the Dashboard.")
    parser.add_argument("--dashboard-pitr-window", default="", help="Earliest/latest PITR recovery window shown in the Dashboard, if enabled.")
    parser.add_argument("--dashboard-evidence-owner", default="", help="Person who observed the Dashboard evidence.")
    parser.add_argument("--dashboard-notes", default="", help="Non-secret notes about Dashboard backup evidence.")
    parser.add_argument("--restore-proof", action="store_true", help="Record that restore/rollback proof has been completed and approved.")
    parser.add_argument(
        "--restore-proof-type",
        default="",
        choices=["", "supabase_disposable_restore", "supabase_clone_restore", "owner_approved_local_rollback", "other"],
        help="Type of restore/rollback proof recorded.",
    )
    parser.add_argument("--restore-proof-detail", default="", help="Non-secret detail identifying the restore/rollback proof.")
    parser.add_argument("--restore-proof-owner", default="", help="Person who approved or observed the restore/rollback proof.")
    parser.add_argument("--use-current-local-rollback-package", action="store_true", help="Use the current passing cutover rollback package readiness report as the owner-approved local rollback proof detail.")
    parser.add_argument("--restore-notes", default="", help="Non-secret restore/rollback notes.")
    args = parser.parse_args()

    token = os.environ.get(args.access_token_env, "").strip()
    if not token and args.prompt_token:
        token = getpass.getpass("Supabase access token: ").strip()
    rows = build_rows(args, token)
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "supabase_backup_readiness.csv", rows)
    write_report(REPORTS_DIR / "supabase_backup_readiness.md", rows)
    summary = rows[0]
    print(json.dumps({"status": summary["status"], "report": str(REPORTS_DIR / "supabase_backup_readiness.md")}, indent=2))
    return 1 if str(summary["status"]).startswith("supabase_backup_readiness_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
