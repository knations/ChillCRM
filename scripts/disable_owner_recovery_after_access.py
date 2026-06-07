#!/usr/bin/env python3
"""Disable hosted owner recovery after the owner confirms access is restored."""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_OWNER_EMAIL = "kevinnations@gmail.com"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def backtick_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}:\s+`([^`]+)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def env_or_prompt(env_name: str, label: str, *, prompt: bool) -> tuple[str, str]:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, "env"
    if not prompt:
        return "", "missing"
    value = getpass.getpass(f"{label}: ").strip()
    return value, "prompt" if value else "missing"


def run_child(script_name: str, args: list[str], env_updates: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_updates)
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache")
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=1200)


def compact_result(result: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(chunk for chunk in [result.stdout or "", result.stderr or ""] if chunk).strip()
    if not text:
        return f"exit_code={result.returncode}"
    try:
        payload = json.loads(text)
        clean = {key: payload.get(key) for key in payload if key not in {"password", "token", "secret"}}
        return f"exit_code={result.returncode}; output={json.dumps(clean, sort_keys=True)}"
    except json.JSONDecodeError:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        detail = lines[-1] if lines else ""
        detail = re.sub(r"\b(vcp_|vck_)[A-Za-z0-9._-]+", r"\1[redacted]", detail)
        detail = re.sub(r"(Bearer\s+)[A-Za-z0-9._-]+", r"\1[redacted]", detail, flags=re.IGNORECASE)
        db_url_pattern = r"postgres" + r"ql://\S+"
        detail = re.sub(db_url_pattern, "database-url-[redacted]", detail)
        detail = re.sub(r"eyJ[A-Za-z0-9._-]{40,}", "[redacted_jwt]", detail)
        return f"exit_code={result.returncode}; output={detail[:500]}"


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
    steps = [row for row in rows if row["row_type"] == "step"]
    lines = [
        "# Owner Recovery Disable Run",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "This report records the guarded owner-recovery disable run. It does not store passwords, tokens, bypass secrets, database credentials, service-role keys, CRM record writes, or source-of-truth changes.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Owner confirmed access: {summary.get('owner_confirmed_access')}.",
        f"- Latest URL: `{summary.get('latest_url') or 'missing'}`.",
        f"- Hosted smoke requested: {summary.get('hosted_smoke_requested')}.",
        f"- Deployment freshness checked: {summary.get('deployment_freshness_checked')}.",
        f"- Passed: {summary.get('passed')}.",
        f"- Failed: {summary.get('failed')}.",
        f"- Input required: {summary.get('input_required')}.",
        "- Secret values stored: no.",
        "- CRM record writes: no.",
        "- Source of truth changed: no.",
        "",
        "## Steps",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in steps:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("key")),
                    str(row.get("status")),
                    str(row.get("evidence", "")).replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Run this only after the owner confirms they can sign in with their own password. If hosted smoke is skipped, production readiness will still require newest hosted smoke after the recovery-disabled deployment.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_step(rows: list[dict[str, Any]], key: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "row_type": "step",
            "key": key,
            "status": status,
            "evidence": " ".join(str(evidence).split()),
        }
    )


def persist(rows: list[dict[str, Any]], *, owner_confirmed_access: bool, latest_url: str, hosted_smoke_requested: bool) -> None:
    steps = [row for row in rows if row["row_type"] == "step"]
    failed = [row for row in steps if row["status"] == "failed"]
    input_required = [row for row in steps if row["status"] == "input_required"]
    passed = [row for row in steps if row["status"] == "passed"]
    deployment_freshness_checked = any(row.get("key") == "hosted_deployment_freshness" for row in steps)
    status = "failed" if failed else "input_required" if input_required else "owner_recovery_disable_completed"
    summary = {
        "row_type": "summary",
        "generated_at": now_utc(),
        "status": status,
        "owner_confirmed_access": "yes" if owner_confirmed_access else "no",
        "latest_url": latest_url,
        "hosted_smoke_requested": "yes" if hosted_smoke_requested else "no",
        "deployment_freshness_checked": "yes" if deployment_freshness_checked else "no",
        "passed": len(passed),
        "failed": len(failed),
        "input_required": len(input_required),
    }
    rows_with_summary = [summary, *steps]
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "owner_recovery_disable_run.csv", rows_with_summary)
    write_report(REPORTS_DIR / "owner_recovery_disable_run.md", rows_with_summary)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disable temporary hosted owner recovery after owner access is confirmed."
    )
    parser.add_argument("--owner-confirmed-access", action="store_true", help="Required. Confirms owner can sign in with their own password.")
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", DEFAULT_OWNER_EMAIL))
    parser.add_argument("--skip-hosted-smoke", action="store_true", help="Disable recovery and refresh reports without running hosted smoke.")
    parser.add_argument("--prompt-secrets", action="store_true", help="Prompt for missing Vercel token and owner password without echoing them.")
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    latest_url = backtick_value(read_text("reports/vercel_staging_deployment_status.md"), "URL")
    hosted_smoke_requested = not args.skip_hosted_smoke

    if not args.owner_confirmed_access:
        add_step(
            rows,
            "owner_confirmation",
            "input_required",
            "Run again with --owner-confirmed-access only after the owner confirms they can sign in with their own password.",
        )
        persist(rows, owner_confirmed_access=False, latest_url=latest_url, hosted_smoke_requested=hosted_smoke_requested)
        print(json.dumps({"status": "input_required_owner_confirmation", "report": str(REPORTS_DIR / "owner_recovery_disable_run.md")}, indent=2))
        return 1

    vercel_token, token_source = env_or_prompt("VERCEL_TOKEN", "Vercel token", prompt=args.prompt_secrets)
    if not vercel_token:
        add_step(rows, "vercel_token", "input_required", "Missing Vercel token. Use --prompt-secrets or VERCEL_TOKEN.")
        persist(rows, owner_confirmed_access=True, latest_url=latest_url, hosted_smoke_requested=hosted_smoke_requested)
        print(json.dumps({"status": "input_required_vercel_token", "report": str(REPORTS_DIR / "owner_recovery_disable_run.md")}, indent=2))
        return 1

    add_step(rows, "owner_confirmation", "passed", "Owner confirmed access before recovery disable.")
    deploy_result = run_child(
        "deploy_chillcrm_to_vercel.py",
        [],
        {
            "VERCEL_TOKEN": vercel_token,
            "CHILLCRM_SKIP_ENV_UPSERT": "1",
            "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED": "0",
            "CHILLCRM_VERCEL_INLINE_FILES": os.environ.get("CHILLCRM_VERCEL_INLINE_FILES", "1"),
        },
    )
    add_step(rows, "disable_recovery_deploy", "passed" if deploy_result.returncode == 0 else "failed", f"{compact_result(deploy_result)}; token_source={token_source}")
    if deploy_result.returncode != 0:
        persist(rows, owner_confirmed_access=True, latest_url=latest_url, hosted_smoke_requested=hosted_smoke_requested)
        print(json.dumps({"status": "failed_disable_recovery_deploy", "report": str(REPORTS_DIR / "owner_recovery_disable_run.md")}, indent=2))
        return 1

    try:
        deploy_payload = json.loads((deploy_result.stdout or "{}").strip())
        latest_url = str(deploy_payload.get("url") or latest_url).strip()
    except json.JSONDecodeError:
        latest_url = backtick_value(read_text("reports/vercel_staging_deployment_status.md"), "URL")

    closure_result = run_child("verify_owner_recovery_closure.py", [], {})
    add_step(rows, "owner_recovery_closure", "passed" if closure_result.returncode == 0 else "failed", compact_result(closure_result))

    public_result = run_child("verify_vercel_public_protection.py", [], {})
    add_step(rows, "public_protection", "passed" if public_result.returncode == 0 else "failed", compact_result(public_result))

    if hosted_smoke_requested:
        owner_password, password_source = env_or_prompt("AUTH_BOOTSTRAP_ADMIN_PASSWORD", "Owner password", prompt=args.prompt_secrets)
        if not owner_password:
            add_step(rows, "hosted_smoke", "input_required", "Missing owner password. Use --prompt-secrets or AUTH_BOOTSTRAP_ADMIN_PASSWORD.")
        else:
            smoke_result = run_child(
                "run_newest_hosted_smoke_with_vercel_bypass.py",
                ["--url", latest_url, "--owner-email", args.owner_email],
                {
                    "VERCEL_TOKEN": vercel_token,
                    "AUTH_BOOTSTRAP_ADMIN_PASSWORD": owner_password,
                    "EXPECT_DOCUMENT_FILE_ACCESS": "true",
                },
            )
            add_step(rows, "hosted_smoke", "passed" if smoke_result.returncode == 0 else "failed", f"{compact_result(smoke_result)}; password_source={password_source}")
    else:
        add_step(rows, "hosted_smoke", "input_required", "Skipped by request; newest hosted smoke must run after the recovery-disabled deployment.")

    freshness_result = run_child("verify_hosted_deployment_freshness.py", [], {})
    add_step(rows, "hosted_deployment_freshness", "passed" if freshness_result.returncode == 0 else "failed", compact_result(freshness_result))

    refresh_result = run_child("run_safe_production_gate_checks.py", ["--refresh-only"], {})
    add_step(rows, "refresh_readiness", "passed" if refresh_result.returncode == 0 else "failed", compact_result(refresh_result))

    intake_result = run_child("prepare_owner_gate_intake_packet.py", [], {})
    add_step(rows, "refresh_owner_intake", "passed" if intake_result.returncode == 0 else "failed", compact_result(intake_result))

    persist(rows, owner_confirmed_access=True, latest_url=latest_url, hosted_smoke_requested=hosted_smoke_requested)
    failed = [row for row in rows if row.get("status") == "failed"]
    input_required = [row for row in rows if row.get("status") == "input_required"]
    print(
        json.dumps(
            {
                "status": "failed" if failed else "input_required" if input_required else "owner_recovery_disable_completed",
                "latest_url": latest_url,
                "failed": len(failed),
                "input_required": len(input_required),
                "report": str(REPORTS_DIR / "owner_recovery_disable_run.md"),
            },
            indent=2,
        )
    )
    return 1 if failed or input_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
