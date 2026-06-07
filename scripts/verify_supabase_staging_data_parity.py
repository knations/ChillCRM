#!/usr/bin/env python3
"""Verify Supabase staging data still matches the current local CRM source."""

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
VALIDATION_CSV = REPORTS_DIR / "chillcrm_supabase_staging_validation.csv"
VALIDATION_REPORT = REPORTS_DIR / "chillcrm_supabase_staging_validation.md"
ADAPTER_SMOKE_REPORT = REPORTS_DIR / "hosted_postgres_adapter_smoke.md"
STORAGE_REPORT = REPORTS_DIR / "chillcrm_supabase_storage_migration.md"
STORAGE_MANIFEST = REPORTS_DIR / "chillcrm_supabase_storage_manifest.csv"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
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
    blocks_cutover: bool = True,
) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "blocks_cutover": "yes" if blocks_cutover else "no",
            "evidence": " ".join(str(evidence).split()),
            "source": source,
            "provider_calls": "no",
            "remote_write_lock_changed": "no",
            "crm_record_writes": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def sqlite_count(conn: sqlite3.Connection, table_name: str) -> int:
    quoted = '"' + table_name.replace('"', '""') + '"'
    return int(conn.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0])


def read_validation_rows() -> list[dict[str, str]]:
    if not VALIDATION_CSV.exists():
        return []
    with VALIDATION_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_storage_manifest_rows() -> list[dict[str, str]]:
    if not STORAGE_MANIFEST.exists():
        return []
    with STORAGE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_table_counts(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], int, int]:
    table_rows: list[dict[str, Any]] = []
    failures = 0
    total_remote_rows = 0
    if not SOURCE_DB.exists():
        return table_rows, 1, 0
    with sqlite3.connect(SOURCE_DB) as conn:
        for row in rows:
            table_name = row.get("table_name") or ""
            reported_local = int_value(row.get("local_count") or "")
            reported_remote = int_value(row.get("remote_count") or "")
            validation_status = row.get("status") or ""
            try:
                current_local = sqlite_count(conn, table_name)
            except sqlite3.Error:
                current_local = -1
            total_remote_rows += reported_remote
            status = "pass" if current_local == reported_local == reported_remote and validation_status == "pass" else "stale"
            if status != "pass":
                failures += 1
            table_rows.append(
                {
                    "row_type": "table",
                    "table_name": table_name,
                    "current_local_count": current_local,
                    "validation_local_count": reported_local,
                    "supabase_staging_count": reported_remote,
                    "validation_status": validation_status,
                    "status": status,
                }
            )
    return table_rows, failures, total_remote_rows


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    validation_report = read_text(VALIDATION_REPORT)
    validation_rows = read_validation_rows()
    validation_status = plain_value(validation_report, "Status")
    loaded_tables = int_value(plain_value(validation_report, "Loaded local CRM tables checked"))
    count_failures = int_value(plain_value(validation_report, "Count failures"))
    add_check(
        rows,
        "staging_validation_report_passed",
        "pass" if validation_status == "passed" and loaded_tables >= 25 and count_failures == 0 and validation_rows else "fail",
        f"status={validation_status or 'missing'}; loaded_tables={loaded_tables}; count_failures={count_failures}; csv_rows={len(validation_rows)}",
        "reports/chillcrm_supabase_staging_validation.md; reports/chillcrm_supabase_staging_validation.csv",
    )

    table_rows, table_failures, total_remote_rows = validate_table_counts(validation_rows)
    rows.extend(table_rows)
    add_check(
        rows,
        "current_local_to_supabase_count_parity",
        "pass" if validation_rows and table_failures == 0 else "input_required",
        f"tables_checked={len(table_rows)}; table_failures={table_failures}; total_remote_rows={total_remote_rows}",
        "crm_database/local_crm.sqlite; reports/chillcrm_supabase_staging_validation.csv",
    )

    adapter = read_text(ADAPTER_SMOKE_REPORT)
    adapter_failed = plain_value(adapter, "Failed")
    adapter_mode_ok = "Mode: hosted_smoke" in adapter
    adapter_enabled_ok = "database_mode=hosted_postgres_adapter_enabled" in adapter
    adapter_lock_ok = "remote_write_lock={'enabled': True" in adapter
    add_check(
        rows,
        "hosted_postgres_adapter_smoke_passed",
        "pass"
        if adapter_mode_ok
        and adapter_failed == "0"
        and adapter_enabled_ok
        and adapter_lock_ok
        else "fail",
        f"mode={'hosted_smoke' if adapter_mode_ok else 'missing'}; failed={adapter_failed or 'missing'}; adapter_enabled={adapter_enabled_ok}; remote_write_lock={adapter_lock_ok}",
        "reports/hosted_postgres_adapter_smoke.md",
    )

    storage = read_text(STORAGE_REPORT)
    storage_rows = read_storage_manifest_rows()
    storage_uploaded = sum(1 for row in storage_rows if row.get("status") == "uploaded")
    storage_status = plain_value(storage, "Status")
    manifest_files = int_value(plain_value(storage, "Document files inventoried"))
    remote_file_objects = int_value(plain_value(storage, "Remote file object rows"))
    linked_remote_documents = int_value(plain_value(storage, "Linked remote document rows"))
    missing_local_files = int_value(plain_value(storage, "Missing local files"))
    size_mismatches = int_value(plain_value(storage, "Size mismatches"))
    add_check(
        rows,
        "private_storage_manifest_parity",
        "pass"
        if storage_status == "uploaded"
        and manifest_files == remote_file_objects == linked_remote_documents == len(storage_rows) == storage_uploaded == 203
        and missing_local_files == 0
        and size_mismatches == 0
        else "fail",
        (
            f"status={storage_status or 'missing'}; manifest_files={manifest_files}; manifest_rows={len(storage_rows)}; "
            f"uploaded_rows={storage_uploaded}; remote_file_objects={remote_file_objects}; linked_remote_documents={linked_remote_documents}; "
            f"missing_local_files={missing_local_files}; size_mismatches={size_mismatches}"
        ),
        "reports/chillcrm_supabase_storage_migration.md; reports/chillcrm_supabase_storage_manifest.csv",
    )

    add_check(
        rows,
        "staging_source_of_truth_boundary",
        "pass",
        "This verifier reads existing local evidence only. It does not query Supabase, upload files, unlock hosted writes, or promote Supabase as source of truth.",
        "scripts/verify_supabase_staging_data_parity.py",
        blocks_cutover=False,
    )

    checks = [row for row in rows if row.get("row_type") == "check"]
    failed = [row for row in checks if row.get("status") == "fail"]
    input_required = [row for row in checks if row.get("status") == "input_required"]
    if table_failures and not failed:
        input_required.append({"status": "input_required"})
    if failed:
        status = "supabase_staging_data_parity_failed"
        production_gate = "blocked_until_supabase_staging_data_parity_passes"
    elif input_required:
        status = "input_required_supabase_staging_refresh"
        production_gate = "blocked_until_current_local_data_reloaded_to_supabase"
    else:
        status = "supabase_staging_data_parity_passed"
        production_gate = "pass"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": production_gate,
        "tables_checked": len(table_rows),
        "table_failures": table_failures,
        "total_remote_rows_checked": total_remote_rows,
        "document_files_checked": len(storage_rows),
        "checks_passed": len([row for row in checks if row.get("status") == "pass"]),
        "checks_input_required": len(input_required),
        "checks_failed": len(failed),
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
    table_rows = [row for row in rows if row["row_type"] == "table"]
    lines = [
        "# Supabase Staging Data Parity",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that the saved Supabase staging validation still matches the current local CRM source. It reads local database counts and existing non-secret reports only; it does not call Supabase, upload files, unlock writes, prompt for secrets, switch source of truth, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Tables checked: {summary.get('tables_checked')}.",
        f"- Table failures: {summary.get('table_failures')}.",
        f"- Total remote rows checked: {summary.get('total_remote_rows_checked')}.",
        f"- Document files checked: {summary.get('document_files_checked')}.",
        f"- Checks passed: {summary.get('checks_passed')}.",
        f"- Checks input-required: {summary.get('checks_input_required')}.",
        f"- Checks failed: {summary.get('checks_failed')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Blocks Cutover | Evidence | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("blocks_cutover")),
                    str(row.get("evidence")).replace("|", "/"),
                    str(row.get("source")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Table Counts", "", "| Table | Current Local | Supabase Staging | Status |", "| --- | ---: | ---: | --- |"])
    for row in table_rows:
        lines.append(
            f"| {row.get('table_name')} | {row.get('current_local_count')} | {row.get('supabase_staging_count')} | {row.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This report is current-state evidence, not a live Supabase query.",
            "- Rerun the Supabase staging load and validation after any local CRM data/schema changes before production cutover.",
            "- Keep local SQLite as source of truth until every production gate passes and final owner cutover approval is recorded.",
            "",
            "## Related Reports",
            "",
            "- `reports/chillcrm_supabase_staging_validation.md`",
            "- `reports/chillcrm_supabase_staging_validation.csv`",
            "- `reports/hosted_postgres_adapter_smoke.md`",
            "- `reports/chillcrm_supabase_storage_migration.md`",
            "- `reports/chillcrm_supabase_storage_manifest.csv`",
            "- `reports/remote_production_readiness.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "supabase_staging_data_parity.csv", rows)
    write_report(REPORTS_DIR / "supabase_staging_data_parity.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    summary = next(row for row in rows if row["row_type"] == "summary")
    return 1 if summary["status"] == "supabase_staging_data_parity_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
