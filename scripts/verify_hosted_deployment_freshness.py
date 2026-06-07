#!/usr/bin/env python3
"""Verify whether local hosted runtime inputs are newer than the latest Vercel deploy."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"

DEPLOYED_RUNTIME_PATHS = [
    "api",
    "crm_app",
    "config/supabase-prod-ca-2021.crt",
    "docs",
    "vercel.json",
    "requirements.txt",
    ".python-version",
    ".vercelignore",
]
REPORT_NAME = "hosted_deployment_freshness"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def latest_deployment_report_path() -> Path:
    return REPORTS_DIR / "vercel_staging_deployment_status.md"


def latest_deployment_reference_time() -> tuple[float, str, str]:
    report = latest_deployment_report_path()
    if not report.exists():
        return 0.0, "", "missing"
    text = report.read_text(encoding="utf-8")
    deployment_id = ""
    for line in text.splitlines():
        if line.startswith("- Deployment ID:") and "`" in line:
            deployment_id = line.split("`", 2)[1].strip()
            break
    return report.stat().st_mtime, deployment_id, relative(report)


def iter_runtime_files() -> list[Path]:
    files: list[Path] = []
    for entry in DEPLOYED_RUNTIME_PATHS:
        path = PROJECT_ROOT / entry
        if not path.exists():
            continue
        if path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())
        else:
            files.append(path)
    return sorted(set(files), key=lambda item: relative(item))


def build_rows() -> list[dict[str, Any]]:
    deployment_time, deployment_id, source_report = latest_deployment_reference_time()
    runtime_files = iter_runtime_files()
    changed = [path for path in runtime_files if deployment_time <= 0 or path.stat().st_mtime > deployment_time + 1]
    changed_rows = [
        {
            "row_type": "changed_runtime_file",
            "path": relative(path),
            "modified_at": iso_from_timestamp(path.stat().st_mtime),
            "deployment_reference_at": iso_from_timestamp(deployment_time) if deployment_time else "missing",
            "requires_redeploy": "yes",
        }
        for path in changed
    ]
    status = "hosted_deployment_fresh"
    production_gate = "pass"
    next_action = "No local hosted runtime files are newer than the latest Vercel deployment evidence."
    if not deployment_time:
        status = "input_required_latest_deployment_reference"
        production_gate = "blocked_until_latest_deployment_reference_exists"
        next_action = "Run the Vercel deployment or refresh deployment status before production cutover."
    elif changed:
        status = "input_required_redeploy_current_local_runtime"
        production_gate = "blocked_until_current_local_runtime_deployed"
        next_action = "Redeploy the current local hosted runtime to Vercel, then rerun hosted smoke and safe gate refreshes."
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "production_gate": production_gate,
        "latest_deployment_id": deployment_id,
        "deployment_reference_at": iso_from_timestamp(deployment_time) if deployment_time else "missing",
        "deployment_reference_report": source_report,
        "runtime_files_checked": len(runtime_files),
        "changed_runtime_files": len(changed_rows),
        "secret_values_stored": "no",
        "provider_calls": "no",
        "remote_write_lock_changed": "no",
        "crm_record_writes": "no",
        "source_of_truth_changed": "no",
        "next_action": next_action,
    }
    return [summary, *changed_rows]


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
    changed = [row for row in rows if row["row_type"] == "changed_runtime_file"]
    lines = [
        "# Hosted Deployment Freshness",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report checks whether the local hosted runtime package is newer than the latest Vercel deployment evidence. It does not contact providers, deploy code, unlock writes, store secrets, change CRM records, or switch source of truth.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Production gate: {summary.get('production_gate')}.",
        f"- Latest deployment: `{summary.get('latest_deployment_id') or 'missing'}`.",
        f"- Deployment reference time: {summary.get('deployment_reference_at')}.",
        f"- Runtime files checked: {summary.get('runtime_files_checked')}.",
        f"- Changed runtime files: {summary.get('changed_runtime_files')}.",
        f"- Secret values stored: {summary.get('secret_values_stored')}.",
        f"- Provider calls: {summary.get('provider_calls')}.",
        f"- Remote write lock changed: {summary.get('remote_write_lock_changed')}.",
        f"- CRM record writes: {summary.get('crm_record_writes')}.",
        f"- Source of truth changed: {summary.get('source_of_truth_changed')}.",
        f"- Next action: {summary.get('next_action')}",
        "",
        "## Changed Runtime Files",
        "",
        "| Path | Modified At | Deployment Reference | Requires Redeploy |",
        "| --- | --- | --- | --- |",
    ]
    if changed:
        for row in changed[:200]:
            lines.append(
                f"| {row.get('path')} | {row.get('modified_at')} | {row.get('deployment_reference_at')} | {row.get('requires_redeploy')} |"
            )
    else:
        lines.append("| none | - | - | no |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a freshness gate only. A blocked status means local hosted runtime code has changed since the latest deployment evidence and should be redeployed before production cutover review.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = build_rows()
    write_csv(REPORTS_DIR / f"{REPORT_NAME}.csv", rows)
    write_report(REPORTS_DIR / f"{REPORT_NAME}.md", rows)
    print(json.dumps(next(row for row in rows if row["row_type"] == "summary"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
