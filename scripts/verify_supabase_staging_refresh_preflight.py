#!/usr/bin/env python3
"""Verify readiness to refresh Supabase staging from the current local CRM."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SOURCE_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
SCHEMA_SQL = PROJECT_ROOT / "reports" / "hosted_database_schema_draft.sql"
SSL_CERT = PROJECT_ROOT / "config" / "supabase-prod-ca-2021.crt"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def plain_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+(.+?)\.?$", text, re.MULTILINE)
    return match.group(1).strip().rstrip(".") if match else ""


def int_value(value: str) -> int:
    text = str(value or "").replace(",", "").strip()
    return int(text) if text.isdigit() else 0


def add_check(
    rows: list[dict[str, Any]],
    key: str,
    status: str,
    evidence: str,
    source: str,
    *,
    required_for_refresh: bool = True,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "required_for_refresh": "yes" if required_for_refresh else "no",
            "evidence": " ".join(str(evidence).split()),
            "source": source,
            "provider_calls": "no",
            "remote_write_lock_changed": "no",
            "crm_record_writes": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def sqlite_quick_check(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        with sqlite3.connect(path) as conn:
            return str(conn.execute("PRAGMA quick_check").fetchone()[0])
    except sqlite3.Error as exc:
        return f"error: {exc}"


def stale_table_summary(parity_csv: Path) -> tuple[int, str]:
    if not parity_csv.exists():
        return 0, "missing parity csv"
    stale: list[str] = []
    with parity_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("row_type") == "table" and row.get("status") != "pass":
                stale.append(
                    f"{row.get('table_name')} local={row.get('current_local_count')} remote={row.get('supabase_staging_count')}"
                )
    return len(stale), "; ".join(stale) if stale else "none"


def token_check(source: str, tokens: list[str]) -> tuple[bool, str]:
    missing = [token for token in tokens if token not in source]
    return not missing, "all expected source tokens present" if not missing else "missing source tokens: " + ", ".join(missing)


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    local_integrity = read_text("reports/local_functional_data_integrity.md")
    rollback = read_text("reports/cutover_rollback_package_readiness.md")
    parity = read_text("reports/supabase_staging_data_parity.md")
    adapter = read_text("reports/hosted_postgres_adapter_smoke.md")
    migration_script = read_text("scripts/migrate_chillcrm_to_supabase.py")
    schema_sql = SCHEMA_SQL.read_text(encoding="utf-8") if SCHEMA_SQL.exists() else ""

    quick_check = sqlite_quick_check(SOURCE_DB)
    add_check(
        rows,
        "source_database_ready",
        "pass" if quick_check == "ok" else "fail",
        f"quick_check={quick_check}; path={SOURCE_DB}",
        "crm_database/local_crm.sqlite",
    )
    add_check(
        rows,
        "local_integrity_still_green",
        "pass" if "Blocking failures: 0" in local_integrity and "Hosted staging gate: pass" in local_integrity else "fail",
        "local functional integrity remains green" if local_integrity else "missing local functional integrity report",
        "reports/local_functional_data_integrity.md",
    )
    rollback_status = plain_value(rollback, "Status")
    rollback_gate = plain_value(rollback, "Production gate")
    add_check(
        rows,
        "rollback_package_ready",
        "pass" if rollback_status == "cutover_rollback_package_ready" and rollback_gate == "pass" else "fail",
        f"status={rollback_status or 'missing'}; production_gate={rollback_gate or 'missing'}",
        "reports/cutover_rollback_package_readiness.md",
    )
    parity_status = plain_value(parity, "Status")
    parity_gate = plain_value(parity, "Production gate")
    parity_table_failures = int_value(plain_value(parity, "Table failures"))
    stale_count, stale_detail = stale_table_summary(REPORTS_DIR / "supabase_staging_data_parity.csv")
    refresh_required = parity_status == "input_required_supabase_staging_refresh" and parity_table_failures > 0
    add_check(
        rows,
        "staging_refresh_needed_and_scoped",
        "pass" if refresh_required or parity_status == "supabase_staging_data_parity_passed" else "fail",
        f"status={parity_status or 'missing'}; production_gate={parity_gate or 'missing'}; table_failures={parity_table_failures}; stale_tables={stale_detail}",
        "reports/supabase_staging_data_parity.md; reports/supabase_staging_data_parity.csv",
        required_for_refresh=refresh_required,
    )
    add_check(
        rows,
        "schema_sql_available",
        "pass"
        if "CREATE SCHEMA IF NOT EXISTS crm" in schema_sql
        and 'CREATE TABLE IF NOT EXISTS crm."audit_log"' in schema_sql
        and 'CREATE TABLE IF NOT EXISTS crm."remote_file_objects"' in schema_sql
        else "fail",
        f"schema_exists={SCHEMA_SQL.exists()}; bytes={SCHEMA_SQL.stat().st_size if SCHEMA_SQL.exists() else 0}",
        "reports/hosted_database_schema_draft.sql",
    )
    script_ok, script_evidence = token_check(
        migration_script,
        [
            "CHILLCRM_DATABASE_URL is required.",
            "--reset-crm-schema",
            "DROP SCHEMA IF EXISTS crm CASCADE",
            "Refusing to load over existing CRM rows without --allow-existing-rows",
            "validate_counts",
            "Do not hard-code credentials",
        ],
    )
    add_check(
        rows,
        "migration_script_guardrails_ready",
        "pass" if script_ok else "fail",
        script_evidence,
        "scripts/migrate_chillcrm_to_supabase.py",
    )
    add_check(
        rows,
        "ssl_root_cert_available",
        "pass" if SSL_CERT.exists() and SSL_CERT.stat().st_size > 0 else "fail",
        f"path=config/supabase-prod-ca-2021.crt; bytes={SSL_CERT.stat().st_size if SSL_CERT.exists() else 0}",
        "config/supabase-prod-ca-2021.crt",
    )
    adapter_hosted_smoke = "Mode: hosted_smoke" in adapter
    adapter_failed_zero = "Failed: 0" in adapter
    adapter_remote_write_lock = "remote_write_lock={'enabled': True" in adapter
    add_check(
        rows,
        "hosted_adapter_lock_boundary",
        "pass"
        if adapter_hosted_smoke
        and adapter_failed_zero
        and adapter_remote_write_lock
        else "fail",
        f"hosted_smoke={adapter_hosted_smoke}; failed_zero={adapter_failed_zero}; remote_write_lock={adapter_remote_write_lock}",
        "reports/hosted_postgres_adapter_smoke.md",
    )
    add_check(
        rows,
        "secret_handling_boundary",
        "pass",
        "Database URL must be supplied only as CHILLCRM_DATABASE_URL through a hidden prompt or one-shot environment variable; this preflight stores no secret values.",
        "scripts/verify_supabase_staging_refresh_preflight.py",
        required_for_refresh=False,
    )
    add_check(
        rows,
        "source_of_truth_boundary",
        "pass",
        "Refreshing Supabase staging does not make hosted Supabase the source of truth and does not unlock hosted CRM writes.",
        "reports/remote_production_readiness.md",
        required_for_refresh=False,
    )

    checks = [row for row in rows if row["row_type"] == "check"]
    failed = [row for row in checks if row["status"] != "pass"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "supabase_staging_refresh_preflight_ready" if not failed else "supabase_staging_refresh_preflight_failed",
        "preflight_gate": "pass" if not failed else "fail",
        "refresh_required": "yes" if refresh_required else "no",
        "stale_table_count": stale_count,
        "stale_table_detail": stale_detail,
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "provider_calls": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }
    return [summary, *rows]


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
        "# Supabase Staging Refresh Preflight",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies readiness to refresh Supabase staging from the current local CRM. It reads local source files and non-secret reports only; it does not connect to Supabase, reset schemas, upload files, unlock writes, prompt for secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Preflight gate: {summary.get('preflight_gate')}.",
        f"- Refresh required: {summary.get('refresh_required')}.",
        f"- Stale table count: {summary.get('stale_table_count')}.",
        f"- Stale table detail: {summary.get('stale_table_detail')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Required | Evidence | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("required_for_refresh")),
                    str(row.get("evidence")).replace("|", "/"),
                    str(row.get("source")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Safe Refresh Command",
            "",
            "Use this only after supplying the Supabase database URL privately:",
            "",
            "```bash",
            "CHILLCRM_DATABASE_URL=<supabase-database-url> CHILLCRM_SSLROOTCERT=config/supabase-prod-ca-2021.crt .venv/bin/python scripts/migrate_chillcrm_to_supabase.py --reset-crm-schema --source-backup-name <current-local-backup-or-package-name>",
            ".venv/bin/python scripts/verify_supabase_staging_data_parity.py",
            ".venv/bin/python scripts/verify_remote_production_readiness.py",
            "```",
            "",
            "## Boundary",
            "",
            "- This preflight does not use or store database credentials.",
            "- The staging refresh command resets only the `crm` schema in Supabase staging.",
            "- Local SQLite remains the source of truth until every production gate passes and final owner cutover approval is recorded.",
            "",
            "## Related Reports",
            "",
            "- `reports/supabase_staging_data_parity.md`",
            "- `reports/chillcrm_supabase_staging_validation.md`",
            "- `reports/cutover_rollback_package_readiness.md`",
            "- `reports/hosted_database_schema_draft.sql`",
            "- `reports/hosted_postgres_adapter_smoke.md`",
            "- `reports/remote_production_readiness.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "supabase_staging_refresh_preflight.csv", rows)
    write_report(REPORTS_DIR / "supabase_staging_refresh_preflight.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0 if next(row for row in rows if row["row_type"] == "summary")["preflight_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
