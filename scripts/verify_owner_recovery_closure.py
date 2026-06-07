#!/usr/bin/env python3
"""Verify the temporary hosted owner-recovery switch is closed before cutover."""

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


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def recovery_switch_value(deployment: str) -> str:
    match = re.search(
        r"owner_password_recovery_env\s*\|\s*upserted_plain\s*\|\s*CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=(true|false)",
        deployment,
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else "unknown"


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


def build_rows() -> list[dict[str, Any]]:
    deployment = read_text("reports/vercel_staging_deployment_status.md")
    smoke = read_text("reports/vercel_hosted_app_smoke.md")
    recovery_value = recovery_switch_value(deployment)
    status = (
        "owner_recovery_closed"
        if recovery_value == "false"
        else "input_required_owner_recovery_disable"
        if recovery_value == "true"
        else "input_required_owner_recovery_evidence"
    )
    gate = "pass" if status == "owner_recovery_closed" else "blocked_until_owner_recovery_disabled"
    rows: list[dict[str, Any]] = [
        {
            "row_type": "summary",
            "generated_at": now_utc(),
            "status": status,
            "production_gate": gate,
            "latest_deployment_id": backtick_value(deployment, "Deployment ID"),
            "latest_url": backtick_value(deployment, "URL"),
            "owner_recovery_switch": recovery_value,
            "hosted_recovery_smoke_seen": "yes" if "owner_password_recovery | passed" in smoke else "no",
            "secret_values_stored": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
        },
        {
            "row_type": "check",
            "key": "owner_recovery_switch_disabled",
            "status": "pass" if recovery_value == "false" else "input_required",
            "evidence": (
                "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=false"
                if recovery_value == "false"
                else f"CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED={recovery_value}"
            ),
            "next_action": (
                "Keep the switch disabled unless owner lockout recovery is explicitly needed."
                if recovery_value == "false"
                else "After the owner confirms they can sign in with their own password, redeploy with CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=false and rerun this report."
            ),
        },
        {
            "row_type": "check",
            "key": "owner_login_recovery_path",
            "status": "pass" if "owner_password_recovery | passed" in smoke else "input_required",
            "evidence": "Latest hosted smoke includes owner_password_recovery." if "owner_password_recovery | passed" in smoke else "Latest hosted smoke does not include owner_password_recovery.",
            "next_action": "Use owner recovery only to restore owner access, then disable it.",
        },
    ]
    return rows


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    summary = next(row for row in rows if row["row_type"] == "summary")
    checks = [row for row in rows if row["row_type"] == "check"]
    lines = [
        "# Owner Recovery Closure",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that the temporary hosted owner-recovery switch is closed before source-of-truth cutover. It does not call providers, expose secrets, unlock writes, create users, change CRM records, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Owner recovery switch: {summary.get('owner_recovery_switch')}.",
        f"- Hosted recovery smoke seen: {summary.get('hosted_recovery_smoke_seen')}.",
        "- Secret values stored: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Next Action |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("evidence")).replace("|", "/"),
                    str(row.get("next_action")).replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Disable Command",
            "",
            "Run this only after the owner confirms they can sign in with their own password:",
            "",
            "```bash",
            "CHILLCRM_SKIP_ENV_UPSERT=1 CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=0 .venv/bin/python scripts/deploy_chillcrm_to_vercel.py",
            ".venv/bin/python scripts/verify_owner_recovery_closure.py",
            "```",
            "",
            "## Boundary",
            "",
            "A blocked status here is expected while the owner is still recovering access. Do not leave the recovery switch enabled for production cutover.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "owner_recovery_closure.csv", rows)
    write_report(REPORTS_DIR / "owner_recovery_closure.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
