#!/usr/bin/env python3
"""Verify the local write-freeze cutover guardrail without changing CRM data."""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def compact(text: str) -> str:
    return " ".join(str(text).split())


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str, source: str) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": compact(evidence),
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
    checks = [row for row in rows if row["row_type"] == "check"]
    lines = [
        "# Local Write Freeze Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies the local write-freeze guardrail for the final Supabase/Vercel production cutover. It reads local source and report files only. It does not enable the freeze, write CRM records, create backups, restore databases, deploy code, call providers, expose secrets, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Checks passed: {summary.get('passed')}.",
        f"- Checks failed: {summary.get('failed')}.",
        f"- Freeze env var: `{summary.get('freeze_env_var')}`.",
        f"- Fallback env var: `{summary.get('fallback_env_var')}`.",
        f"- Backup path remains allowed: {summary.get('backup_path_allowed')}.",
        "- Provider calls: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Source |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("evidence", "")).replace("|", "/"),
                    str(row.get("source", "")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Operator Boundary",
            "",
            "Use `CHILLCRM_LOCAL_WRITE_FREEZE=true` only during the final local packaging and production validation window. The guard blocks local CRM mutations and restore operations while leaving `/api/backup`, read paths, reports, and exports available so the final rollback package can still be created after the freeze.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def token_check(text: str, tokens: list[str]) -> bool:
    return all(token in text for token in tokens)


def runtime_behavior_checks() -> tuple[bool, list[str]]:
    saved_env = {
        key: os.environ.get(key)
        for key in [
            "CHILLCRM_LOCAL_WRITE_FREEZE",
            "LOCAL_WRITE_FREEZE",
            "DATABASE_URL",
            "CHILLCRM_DATABASE_ADAPTER",
            "CRM_DATABASE_ADAPTER",
        ]
    }
    handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    handler.db_path = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
    evidence: list[str] = []
    try:
        os.environ.pop("LOCAL_WRITE_FREEZE", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
        os.environ.pop("CRM_DATABASE_ADAPTER", None)
        os.environ["CHILLCRM_LOCAL_WRITE_FREEZE"] = "true"
        frozen_status = handler.local_write_freeze_status()
        local_update_blocked = handler.should_block_local_write("/api/update_record")
        backup_blocked = handler.should_block_local_write("/api/backup")
        evidence.append(f"local_enabled={frozen_status.get('enabled')}")
        evidence.append(f"local_mode={frozen_status.get('mode')}")
        evidence.append(f"update_record_blocked={local_update_blocked}")
        evidence.append(f"backup_blocked={backup_blocked}")

        os.environ["DATABASE_URL"] = "postgresql://user:pass@example.local:5432/postgres"
        os.environ["CHILLCRM_DATABASE_ADAPTER"] = "postgres"
        hosted_status = handler.local_write_freeze_status()
        evidence.append(f"hosted_enabled={hosted_status.get('enabled')}")
        evidence.append(f"hosted_mode={hosted_status.get('mode')}")

        ok = (
            frozen_status.get("enabled") is True
            and frozen_status.get("mode") == "frozen"
            and local_update_blocked is True
            and backup_blocked is False
            and hosted_status.get("enabled") is False
            and hosted_status.get("mode") == "ignored_hosted_adapter"
        )
        return ok, evidence
    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    server_py = read_text("crm_app/server.py")
    cutover_report = read_text("reports/remote_production_cutover_checklist.md")
    rows: list[dict[str, Any]] = []

    add_check(
        rows,
        "freeze_env_switch",
        "pass"
        if token_check(
            server_py,
            [
                "CHILLCRM_LOCAL_WRITE_FREEZE",
                "LOCAL_WRITE_FREEZE",
                "local_write_freeze_enabled",
                "local_write_freeze_status",
            ],
        )
        else "fail",
        "Server exposes the local write-freeze env switch and status helpers.",
        "crm_app/server.py",
    )
    add_check(
        rows,
        "local_only_boundary",
        "pass"
        if token_check(
            server_py,
            [
                "not self.hosted_postgres_adapter_enabled()",
                "ignored_when_hosted_postgres_adapter_enabled",
                "ignored_hosted_adapter",
            ],
        )
        else "fail",
        "Freeze applies only to local SQLite mode and is ignored for hosted Postgres adapter runtime.",
        "crm_app/server.py",
    )
    add_check(
        rows,
        "mutation_guard",
        "pass"
        if token_check(
            server_py,
            [
                "local_write_freeze_post_paths",
                "should_block_local_write",
                "send_local_write_frozen",
                "local_write_freeze_enabled",
            ],
        )
        else "fail",
        "Server has a local write-freeze POST guard and dedicated locked response.",
        "crm_app/server.py",
    )
    add_check(
        rows,
        "backup_path_allowed",
        "pass" if token_check(server_py, ['path != "/api/backup"', '"allowed_post_paths": ["/api/backup"]']) else "fail",
        "The freeze excludes /api/backup so the final local rollback package can still be created after the freeze.",
        "crm_app/server.py",
    )
    add_check(
        rows,
        "runtime_visibility",
        "pass"
        if server_py.count('"local_write_freeze"') >= 4 and "runtime_context" in server_py and "migration_status" in server_py
        else "fail",
        "Runtime, dashboard, hosted summary, and Status payloads expose local write-freeze state.",
        "crm_app/server.py",
    )
    runtime_ok, runtime_evidence = runtime_behavior_checks()
    add_check(
        rows,
        "runtime_behavior",
        "pass" if runtime_ok else "fail",
        "; ".join(runtime_evidence),
        "crm_app/server.py",
    )
    add_check(
        rows,
        "cutover_checklist_alignment",
        "pass"
        if token_check(cutover_report, ["Local write freeze", "Enforce local write freeze", "Create final SQLite backup"])
        else "fail",
        "The production cutover checklist already requires local freeze, freeze enforcement, and final backup/package creation.",
        "reports/remote_production_cutover_checklist.md",
    )
    add_check(
        rows,
        "safe_boundary",
        "pass",
        "This verifier reads local source/report files and environment flags only; it does not enable freeze or change CRM/provider state.",
        "scripts/verify_local_write_freeze_readiness.py",
    )

    checks = [row for row in rows if row["row_type"] == "check"]
    failed = [row for row in checks if row["status"] == "fail"]
    passed = [row for row in checks if row["status"] == "pass"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "local_write_freeze_ready" if not failed else "local_write_freeze_not_ready",
        "production_gate": "pass" if not failed else "fail",
        "passed": len(passed),
        "failed": len(failed),
        "freeze_env_var": "CHILLCRM_LOCAL_WRITE_FREEZE",
        "fallback_env_var": "LOCAL_WRITE_FREEZE",
        "backup_path_allowed": "yes" if not failed else "unknown",
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    rows_with_summary = [summary, *rows]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "local_write_freeze_readiness.csv", rows_with_summary)
    write_report(REPORTS_DIR / "local_write_freeze_readiness.md", rows_with_summary)
    print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
