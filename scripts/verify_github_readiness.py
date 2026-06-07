#!/usr/bin/env python3
"""Verify the CHILLCRM worktree is safe to connect to GitHub."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

BLOCKED_DIR_PREFIXES = {
    ".venv/",
    ".vercel/",
    "backups/",
    "crm_database/",
    "exports/",
    "logs/",
    "raw_api_exports/",
    "reports/",
    "staging_database/",
}

BLOCKED_SUFFIXES = {
    ".db",
    ".db-shm",
    ".db-wal",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
}

REQUIRED_IGNORE_TOKENS = [
    "crm_database/",
    "staging_database/",
    "backups/",
    "raw_api_exports/",
    "exports/",
    "logs/",
    "reports/",
    ".vercel/",
    ".venv/",
    "*.sqlite",
    "*.db",
    "*.zip",
    "*.key",
    "*.pem",
]

SECRET_PATTERNS = [
    ("vercel_token", re.compile(r"\bv(?:cp|ck)_[A-Za-z0-9._-]{20,}\b")),
    ("supabase_jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")),
    ("postgres_url", re.compile(r"\bpostgres(?:ql)?://[^:\s]+:[^@\s]+@[^ \n\r\t]+")),
    ("zendesk_token", re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("secret_assignment", re.compile(r"(?i)\b(?:password|token|secret|service_role_key)\s*=\s*['\"][^'\"\n]{8,}['\"]")),
]

PLACEHOLDER_MARKERS = [
    "<owner-password>",
    "<supabase-management-token>",
    "<vercel-token>",
    "${ENCODED_PASSWORD}",
    "[YOUR-PASSWORD]",
    "REPLACE_WITH_PASSWORD",
    "replace_with_db_password",
    "your-password",
    "your-token",
    "user:pass@example.local",
    "getpass.getpass",
    "prompt_secret",
    "prompt-secrets",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def candidate_files() -> list[str]:
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    tracked = run_git(["ls-files"])
    return sorted(set(tracked + untracked))


def ignored_probe() -> dict[str, str]:
    probes = [
        "crm_database/local_crm.sqlite",
        "staging_database/zendesk_sell_staging.sqlite",
        "raw_api_exports/snapshot_20260605T042056Z/contacts.json",
        "backups/local_crm_20260606T223442Z_before_supabase_staging_seed.sqlite",
        "reports/remote_production_readiness.md",
        ".vercel/project.json",
        ".venv/pyvenv.cfg",
        "exports/latest_export.txt",
    ]
    result: dict[str, str] = {}
    for probe in probes:
        check = subprocess.run(
            ["git", "check-ignore", "-v", probe],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        result[probe] = "ignored" if check.returncode == 0 else "not_ignored"
    return result


def text_for_scan(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if b"\x00" in raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def allowed_secret_match(line: str) -> bool:
    return any(marker in line for marker in PLACEHOLDER_MARKERS)


def add_check(rows: list[dict[str, Any]], key: str, status: str, evidence: str, *, blocks_push: bool = True) -> None:
    rows.append(
        {
            "row_type": "check",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
            "blocks_push": "yes" if blocks_push else "no",
        }
    )


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    candidates = candidate_files()
    ignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8") if (PROJECT_ROOT / ".gitignore").exists() else ""

    missing_ignore_tokens = [token for token in REQUIRED_IGNORE_TOKENS if token not in ignore_text]
    add_check(
        rows,
        "required_ignore_rules_present",
        "pass" if not missing_ignore_tokens else "fail",
        f"missing={', '.join(missing_ignore_tokens) or 'none'}",
    )

    probe_results = ignored_probe()
    not_ignored = [path for path, status in probe_results.items() if status != "ignored"]
    add_check(
        rows,
        "private_data_probe_ignored",
        "pass" if not not_ignored else "fail",
        f"not_ignored={', '.join(not_ignored) or 'none'}",
    )

    blocked_candidates = []
    for candidate in candidates:
        if any(candidate.startswith(prefix) for prefix in BLOCKED_DIR_PREFIXES):
            blocked_candidates.append(candidate)
            continue
        lower = candidate.lower()
        if any(lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
            blocked_candidates.append(candidate)
    add_check(
        rows,
        "no_private_data_candidates",
        "pass" if not blocked_candidates else "fail",
        f"blocked_candidates={len(blocked_candidates)}",
    )
    for path in blocked_candidates[:50]:
        rows.append({"row_type": "finding", "key": "private_data_candidate", "status": "fail", "evidence": path, "blocks_push": "yes"})

    secret_findings = []
    for candidate in candidates:
        path = PROJECT_ROOT / candidate
        if not path.is_file():
            continue
        text = text_for_scan(path)
        if not text:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if allowed_secret_match(line):
                continue
            for pattern_name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    secret_findings.append((candidate, line_no, pattern_name))
    add_check(
        rows,
        "candidate_secret_scan",
        "pass" if not secret_findings else "fail",
        f"findings={len(secret_findings)}; values omitted",
    )
    for candidate, line_no, pattern_name in secret_findings[:100]:
        rows.append(
            {
                "row_type": "finding",
                "key": "secret_candidate",
                "status": "fail",
                "evidence": f"{candidate}:{line_no} matched {pattern_name}; value omitted",
                "blocks_push": "yes",
            }
        )

    add_check(
        rows,
        "candidate_count_reasonable",
        "pass" if 20 <= len(candidates) <= 250 else "warning",
        f"candidate_files={len(candidates)}",
        blocks_push=False,
    )

    failed = [row for row in rows if row.get("status") == "fail"]
    warnings = [row for row in rows if row.get("status") == "warning"]
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": "github_ready" if not failed else "github_not_ready",
        "production_gate": "pass" if not failed else "blocked_until_github_findings_clear",
        "candidate_files": len(candidates),
        "failed": len(failed),
        "warnings": len(warnings),
        "secret_values_stored": "no",
        "remote_push_performed": "no",
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
    summary = rows[0]
    checks = [row for row in rows if row.get("row_type") == "check"]
    findings = [row for row in rows if row.get("row_type") == "finding"]
    lines = [
        "# GitHub Readiness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report verifies the CHILLCRM local repo candidate before connecting GitHub. It does not push to GitHub, store secrets, change CRM records, deploy code, unlock writes, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Candidate files: {summary.get('candidate_files')}.",
        f"- Failed checks/findings: {summary.get('failed')}.",
        f"- Warnings: {summary.get('warnings')}.",
        "- Secret values stored: no.",
        "- Remote push performed: no.",
        "",
        "## Checks",
        "",
        "| Check | Status | Blocks Push | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row.get('key')} | {row.get('status')} | {row.get('blocks_push')} | {row.get('evidence')} |")
    lines.extend(["", "## Findings", ""])
    if findings:
        lines.extend(["| Finding | Status | Evidence |", "| --- | --- | --- |"])
        for row in findings:
            lines.append(f"| {row.get('key')} | {row.get('status')} | {row.get('evidence')} |")
    else:
        lines.append("No blocking findings.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / "github_readiness.csv", rows)
    write_report(REPORTS_DIR / "github_readiness.md", rows)
    print(json.dumps(rows[0], indent=2))
    return 0 if rows[0]["status"] == "github_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
