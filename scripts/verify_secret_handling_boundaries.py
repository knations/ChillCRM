#!/usr/bin/env python3
"""Verify CHILLCRM production files do not carry secret values."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SELF_RELATIVE_PATH = "scripts/verify_secret_handling_boundaries.py"

TEXT_SUFFIXES = {
    ".csv",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".txt",
}
SCAN_ROOTS = [
    "api",
    "config",
    "crm_app",
    "docs",
    "reports",
    "scripts",
]
SCAN_FILES = [
    "README.md",
    "requirements.txt",
    "vercel.json",
]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "backups",
    "crm_database",
    "exports",
    "raw_api_exports",
    "staging_database",
}
EXCLUDED_FILES = {
    SELF_RELATIVE_PATH,
    "reports/secret_handling_boundaries.md",
    "reports/secret_handling_boundaries.csv",
}


@dataclass(frozen=True)
class SecretPattern:
    key: str
    label: str
    pattern: re.Pattern[str]


SECRET_PATTERNS = [
    SecretPattern("vercel_token", "Vercel token", re.compile(r"\bv(?:cp|ck)_[A-Za-z0-9._-]{20,}\b")),
    SecretPattern("supabase_publishable_key", "Supabase publishable key", re.compile(r"\bsb_publishable_[A-Za-z0-9_-]{10,}\b")),
    SecretPattern(
        "jwt_like_secret",
        "JWT-like token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{18,}\.[A-Za-z0-9_-]{18,}\.[A-Za-z0-9_-]{18,}\b"),
    ),
    SecretPattern(
        "postgres_connection_url",
        "Postgres connection URL",
        re.compile(r"\b(?:postgresql|postgres)://[^\s`'\"<>]+"),
    ),
    SecretPattern(
        "secret_env_assignment",
        "Secret environment assignment",
        re.compile(
            r"\b(?:AUTH_BOOTSTRAP_ADMIN_PASSWORD|CHILLCRM_DATABASE_URL|CHILLCRM_OWNER_RECOVERY_PASSWORD|"
            r"CHILLCRM_APP_USER_PASSWORD|DATABASE_URL|SUPABASE_ACCESS_TOKEN|SUPABASE_SERVICE_ROLE_KEY|SERVICE_ROLE_KEY|VERCEL_TOKEN)"
            r"\s*=\s*([^\s`'\"<>][^\s`'\"]{8,})"
        ),
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def is_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def iter_scan_paths() -> Iterable[Path]:
    yielded: set[str] = set()
    for scan_file in SCAN_FILES:
        path = PROJECT_ROOT / scan_file
        if path.exists() and relative(path) not in EXCLUDED_FILES:
            yielded.add(relative(path))
            yield path
    for root_name in SCAN_ROOTS:
        root = PROJECT_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            rel = relative(path)
            parts = set(path.relative_to(PROJECT_ROOT).parts)
            if path.is_dir() or parts & EXCLUDED_DIRS or rel in EXCLUDED_FILES:
                continue
            if not is_text_path(path):
                continue
            if rel in yielded:
                continue
            yielded.add(rel)
            yield path


def allowed_match(pattern_key: str, match_text: str, path: str) -> bool:
    clean = match_text.strip()
    lowered = clean.lower()
    if pattern_key == "postgres_connection_url":
        return any(
            marker in lowered
            for marker in [
                "<",
                "[your-password]",
                "example.local",
                "localhost",
                "127.0.0.1",
                "user:pass@",
            ]
        )
    if pattern_key == "secret_env_assignment":
        return any(marker in clean for marker in ["<", "[", "example", "unit-test", "placeholder"])
    return False


def scan_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = relative(path)
    findings: list[dict[str, Any]] = []
    line_offsets: list[int] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        line_offsets.append(cursor)
        cursor += len(line)
    for secret_pattern in SECRET_PATTERNS:
        for match in secret_pattern.pattern.finditer(text):
            match_text = match.group(0)
            if allowed_match(secret_pattern.key, match_text, rel):
                continue
            line_number = 1
            for index, offset in enumerate(line_offsets, start=1):
                if offset > match.start():
                    break
                line_number = index
            findings.append(
                {
                    "row_type": "finding",
                    "file": rel,
                    "line": line_number,
                    "pattern": secret_pattern.key,
                    "label": secret_pattern.label,
                    "status": "fail",
                    "evidence": "Potential secret value matched; value omitted from report.",
                }
            )
    return findings


def source_contains(relative_path: str, tokens: list[str]) -> tuple[bool, str]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return False, "Missing source file."
    source = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in source]
    if missing:
        return False, "Missing source tokens: " + ", ".join(missing)
    return True, "Required private-prompt and no-storage source tokens are present."


def add_boundary_check(
    rows: list[dict[str, Any]],
    *,
    key: str,
    source: str,
    requirement: str,
    tokens: list[str],
) -> None:
    passed, evidence = source_contains(source, tokens)
    rows.append(
        {
            "row_type": "boundary",
            "key": key,
            "source": source,
            "status": "pass" if passed else "fail",
            "requirement": requirement,
            "evidence": evidence,
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def add_report_check(rows: list[dict[str, Any]], *, key: str, report: str, tokens: list[str]) -> None:
    passed, evidence = source_contains(report, tokens)
    rows.append(
        {
            "row_type": "report_boundary",
            "key": key,
            "source": report,
            "status": "pass" if passed else "fail",
            "requirement": "Report records no stored secret values and preserves the production safety boundary.",
            "evidence": evidence,
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
        }
    )


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scanned_paths = list(iter_scan_paths())
    findings: list[dict[str, Any]] = []
    for path in scanned_paths:
        findings.extend(scan_file(path))

    rows.append(
        {
            "row_type": "scan",
            "key": "curated_source_report_secret_scan",
            "status": "pass" if not findings else "fail",
            "scanned_files": len(scanned_paths),
            "findings": len(findings),
            "scope": "api, config, crm_app, docs, reports, scripts, README, requirements, vercel.json",
            "exclusions": "raw_api_exports, backups, crm_database, staging_database, exports, virtualenv, generated self-report",
            "provider_calls": "no",
            "crm_record_writes": "no",
            "remote_write_lock_changed": "no",
            "source_of_truth_changed": "no",
            "secret_values_stored": "no",
            "evidence": "No secret-like values found in curated source/report/config surface." if not findings else "Potential secret-like values found; see finding rows.",
        }
    )
    rows.extend(findings)

    add_boundary_check(
        rows,
        key="safe_runner_private_prompts",
        source="scripts/run_safe_production_gate_checks.py",
        requirement="Safe runner prompts privately for optional secrets, stores no values, and refuses approval-only actions.",
        tokens=[
            "getpass.getpass",
            "--prompt-secrets",
            "Secret values stored: no",
            "This runner will not approve write-audit rehearsal",
            "This runner will not sign monitoring cadence",
        ],
    )
    add_boundary_check(
        rows,
        key="private_execution_inputs_no_secret_storage",
        source="scripts/verify_private_execution_inputs.py",
        requirement="Private execution input map records only presence/absence, prompt paths, owner inputs, and proof reports.",
        tokens=[
            "Private Execution Inputs",
            "secret_values_stored",
            "Secret values stored: no",
            "VERCEL_TOKEN",
            "AUTH_BOOTSTRAP_ADMIN_PASSWORD",
            "CHILLCRM_DATABASE_URL",
            "SUPABASE_ACCESS_TOKEN",
        ],
    )
    add_boundary_check(
        rows,
        key="owner_confirmed_wave_private_prompts",
        source="scripts/run_owner_confirmed_production_wave.py",
        requirement="Owner-confirmed production wave runner requires explicit execution flags, private prompts, and no source-of-truth/write-lock changes.",
        tokens=[
            "getpass.getpass",
            "--owner-confirmed-access",
            "--execute-owner-recovery-wave",
            "--execute-supabase-staging-refresh",
            "--verify-supabase-backup-api",
            "Secret values stored",
            "This runner does not approve or execute the hosted write-audit rehearsal",
        ],
    )
    add_boundary_check(
        rows,
        key="source_of_truth_cutover_preflight_no_secret_storage",
        source="scripts/verify_source_of_truth_cutover_preflight.py",
        requirement="Source-of-truth cutover preflight is report-only and preserves no provider calls, no writes, and no source-of-truth changes.",
        tokens=[
            "Source-Of-Truth Cutover Preflight",
            "provider_calls",
            "crm_record_writes",
            "remote_write_lock_changed",
            "source_of_truth_changed",
            "secret_values_stored",
        ],
    )
    add_boundary_check(
        rows,
        key="supabase_refresh_private_database_url",
        source="scripts/run_supabase_staging_refresh.py",
        requirement="Supabase staging refresh uses private database URL handling and reloads staging only when explicitly executed.",
        tokens=[
            "getpass.getpass",
            "--execute",
            "--prompt-secrets",
            "Database URL source",
            "secret_values_stored",
            "migrate_chillcrm_to_supabase.py",
        ],
    )
    add_boundary_check(
        rows,
        key="owner_recovery_disable_private_prompts",
        source="scripts/disable_owner_recovery_after_access.py",
        requirement="Owner recovery disable requires owner-confirmed access and private prompts for provider/owner secrets.",
        tokens=[
            "getpass.getpass",
            "--owner-confirmed-access",
            "--prompt-secrets",
            "Secret values stored: no",
            "owner confirms they can sign in with their own password",
        ],
    )
    add_boundary_check(
        rows,
        key="hosted_smoke_wrapper_memory_only_bypass",
        source="scripts/run_newest_hosted_smoke_with_vercel_bypass.py",
        requirement="Hosted smoke wrapper reads Vercel token/bypass in memory and passes only transient env values to smoke verification.",
        tokens=[
            "getpass.getpass",
            "read_bypass_secret",
            "VERCEL_TOKEN",
            "env.pop(key, None)",
            "No secret values are written to reports",
        ],
    )
    add_boundary_check(
        rows,
        key="write_audit_owner_approved_private_execution",
        source="scripts/execute_hosted_write_audit_rehearsal.py",
        requirement="Hosted write-audit execution requires owner approval, private prompts, and lock restoration before pass.",
        tokens=[
            "getpass.getpass",
            "--owner-approved",
            "--execute",
            "--prompt-secrets",
            "Secret values stored: no",
            "deploy_write_lock(token, True)",
        ],
    )

    add_report_check(
        rows,
        key="safe_runner_report_no_secrets",
        report="reports/safe_production_gate_runner.md",
        tokens=["Secret values stored: no", "CRM record writes: no", "Remote write lock changed: no", "Source of truth changed: no"],
    )
    add_report_check(
        rows,
        key="private_execution_inputs_report_no_secrets",
        report="reports/private_execution_inputs.md",
        tokens=["Secret values stored: no", "Secret env values present:", "Provider calls: no", "CRM record writes: no"],
    )
    add_report_check(
        rows,
        key="owner_confirmed_wave_report_no_secrets",
        report="reports/owner_confirmed_production_wave.md",
        tokens=["Secret values stored: no", "Remote write lock changed: no", "Source of truth changed: no"],
    )
    add_report_check(
        rows,
        key="source_of_truth_cutover_preflight_report_no_secrets",
        report="reports/source_of_truth_cutover_preflight.md",
        tokens=["Secret values stored: no", "Remote write lock changed: no", "Source of truth changed: no"],
    )
    add_report_check(
        rows,
        key="supabase_refresh_report_no_secrets",
        report="reports/supabase_staging_refresh_run.md",
        tokens=["Secret values stored: no", "Database URL source:", "Provider calls:", "Source of truth changed: no"],
    )
    add_report_check(
        rows,
        key="owner_wave_packet_no_secrets",
        report="reports/owner_approved_wave_packet.md",
        tokens=["Secret values required for this packet: no", "Secret values stored: no", "Do not share the password"],
    )
    add_report_check(
        rows,
        key="remaining_gates_packet_no_secrets",
        report="reports/remaining_production_gates_packet.md",
        tokens=["does not store secrets", "Supply tokens/passwords through hidden prompts", "run_safe_production_gate_checks.py --all-safe --prompt-secrets"],
    )
    add_report_check(
        rows,
        key="write_audit_report_no_secrets",
        report="reports/hosted_write_audit_execution.md",
        tokens=["Secret values stored: no", "Source of truth changed: no", "Write lock restored:"],
    )
    add_report_check(
        rows,
        key="owner_recovery_disable_report_no_secrets",
        report="reports/owner_recovery_disable_run.md",
        tokens=["Secret values stored: no", "CRM record writes: no", "Source of truth changed: no"],
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
    scan = next(row for row in rows if row["row_type"] == "scan")
    checks = [row for row in rows if row["row_type"] in {"boundary", "report_boundary"}]
    findings = [row for row in rows if row["row_type"] == "finding"]
    lines = [
        "# Secret-Handling Boundaries",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies that CHILLCRM production source, reports, docs, and config examples are not carrying secret values. It also checks that the guided production runners use hidden prompts or one-shot environment values and record no secrets. It does not read raw Zendesk exports, database files, backups, or document archives.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Scanned files: {summary.get('scanned_files')}.",
        f"- Boundary checks: {summary.get('boundary_checks')}.",
        f"- Findings: {summary.get('findings')}.",
        f"- Failed checks: {summary.get('failed_checks')}.",
        "- Provider calls: no.",
        "- CRM record writes: no.",
        "- Remote write lock changed: no.",
        "- Source of truth changed: no.",
        "- Secret values stored: no.",
        "",
        "## Scan Scope",
        "",
        f"- Included: {scan.get('scope')}.",
        f"- Excluded: {scan.get('exclusions')}.",
        "",
        "## Boundary Checks",
        "",
        "| Key | Status | Source | Requirement | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("source")),
                    str(row.get("requirement")).replace("|", "/"),
                    str(row.get("evidence")).replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        lines.extend(["| File | Line | Pattern | Evidence |", "| --- | ---: | --- | --- |"])
        for row in findings:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("file")),
                        str(row.get("line")),
                        str(row.get("pattern")),
                        str(row.get("evidence")).replace("|", "/"),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a local source/report/config audit only. It does not prove provider accounts are configured correctly, run hosted smoke, reload Supabase staging, approve owner gates, unlock writes, or switch source of truth.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scan = next(row for row in rows if row["row_type"] == "scan")
    findings = [row for row in rows if row["row_type"] == "finding"]
    checks = [row for row in rows if row["row_type"] in {"boundary", "report_boundary"}]
    failed_checks = [row for row in checks if row["status"] != "pass"]
    passed = not findings and not failed_checks and scan["status"] == "pass"
    return {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "secret_handling_boundaries_passed" if passed else "secret_handling_boundaries_failed",
        "production_gate": "pass" if passed else "blocked_until_secret_handling_findings_cleared",
        "scanned_files": scan["scanned_files"],
        "boundary_checks": len(checks),
        "findings": len(findings),
        "failed_checks": len(failed_checks),
        "provider_calls": "no",
        "crm_record_writes": "no",
        "remote_write_lock_changed": "no",
        "source_of_truth_changed": "no",
        "secret_values_stored": "no",
    }


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows_without_summary = build_rows()
    summary = summarize(rows_without_summary)
    rows = [summary, *rows_without_summary]
    write_csv(REPORTS_DIR / "secret_handling_boundaries.csv", rows)
    write_report(REPORTS_DIR / "secret_handling_boundaries.md", rows)
    print(json.dumps(summary, indent=2))
    return 0 if summary["production_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
