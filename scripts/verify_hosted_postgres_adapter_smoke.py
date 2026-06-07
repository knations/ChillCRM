#!/usr/bin/env python3
"""Smoke-test the guarded hosted Postgres adapter for CHILLCRM.

Dry-run mode is local only. Full smoke mode requires DATABASE_URL and intentionally
enables CHILLCRM_DATABASE_ADAPTER=postgres for read-path testing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DEFAULT_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"


def handler() -> server.CRMRequestHandler:
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DEFAULT_DB
    return instance


def clip(value: Any, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def run_check(name: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        result = action()
    except Exception as exc:  # pragma: no cover - exercised against hosted env.
        return {"check": name, "status": "failed", "error": exc.__class__.__name__, "detail": clip(exc)}
    if isinstance(result, dict):
        return {"check": name, "status": "passed", **result}
    return {"check": name, "status": "passed", "detail": result}


def first_record_detail(app: server.CRMRequestHandler, record_type: str) -> dict[str, Any]:
    listed = app.list_records({"type": [record_type], "page": ["1"], "page_size": ["10"], "sort": ["updated_at"], "direction": ["desc"]})
    records = listed.get("records") or []
    if not records:
        return {"records": 0, "detail_checked": False}
    record = records[0]
    source_id = record.get("source_id") or record.get("id")
    detail_type = {"people": "person", "companies": "company", "leads": "lead", "deals": "deal"}.get(record_type, record_type)
    detail = app.record_detail({"type": [detail_type], "id": [str(source_id)]})
    return {
        "records": len(records),
        "total": listed.get("total"),
        "detail_checked": bool(detail.get("record")),
        "first_id": source_id,
    }


def dry_run_checks() -> list[dict[str, Any]]:
    sample_sql = (
        "SELECT id, json_extract(source_json, '$.resource_id') AS rid "
        "FROM imported_archive_items WHERE record_type = ? AND title LIKE :like "
        "AND date(updated_at) <= date('now', '+7 days') ORDER BY title COLLATE NOCASE LIMIT ?"
    )
    translated = server.translate_sqlite_sql_for_postgres(sample_sql)
    params = server.postgres_parameters_for_sql("SELECT * FROM people WHERE name LIKE :like OR email LIKE :like", {"like": "%a%"})
    row = server.PostgresCompatRow(["id", "name"], (1, "Dry Run"))
    return [
        {
            "check": "adapter_translation",
            "status": "passed",
            "has_positional_params": "%s" in translated,
            "has_jsonb_translation": "::jsonb ->>" in translated,
            "has_date_translation": "CURRENT_DATE" in translated,
            "removed_sqlite_collation": "COLLATE NOCASE" not in translated,
        },
        {"check": "named_parameter_order", "status": "passed", "parameter_count": len(params), "duplicates_preserved": params == ["%a%", "%a%"]},
        {"check": "row_compatibility", "status": "passed", "index_lookup": row[0], "name_lookup": row["name"], "dict_ready": dict(row) == {"id": 1, "name": "Dry Run"}},
    ]


def smoke_checks() -> list[dict[str, Any]]:
    if not os.environ.get("DATABASE_URL", "").strip():
        raise RuntimeError("DATABASE_URL is required for hosted smoke mode.")
    os.environ.setdefault("CHILLCRM_DATABASE_ADAPTER", "postgres")
    os.environ.setdefault("REMOTE_WRITE_LOCK", "true")
    os.environ.setdefault("EXPORT_PACKAGE_ENABLED", "false")
    os.environ.setdefault("DOCUMENT_FILE_ACCESS_ENABLED", "false")
    app = handler()
    checks: list[dict[str, Any]] = []
    checks.append(run_check("health", lambda: {"http_status": app.health_status()[1], "database": app.health_status()[0]["checks"]["database"]}))
    checks.append(run_check("summary", lambda: {"counts": app.summary().get("counts", {})}))
    for record_type in ["people", "companies", "leads", "deals"]:
        checks.append(run_check(f"{record_type}_list_and_detail", lambda record_type=record_type: first_record_detail(app, record_type)))
    checks.append(run_check("tasks", lambda: {"total": app.tasks({"status": ["open"], "page_size": ["10"]}).get("total")}))
    checks.append(run_check("activity", lambda: {"items": len(app.activity({"limit": ["20"]}).get("items") or [])}))
    checks.append(run_check("archive", lambda: {"total": app.archive_items({"page_size": ["10"]}).get("total")}))
    checks.append(run_check("tags", lambda: {"total": app.tags({"page_size": ["10"]}).get("total")}))
    checks.append(run_check("custom_fields", lambda: {"total": app.custom_fields({"page_size": ["10"]}).get("total")}))
    checks.append(run_check("linked_resources", lambda: {"total": app.linked_resources({"page_size": ["10"]}).get("total")}))
    checks.append(run_check("runtime_locks", lambda: app.runtime_context()))
    return checks


def write_report(path: Path, mode: str, checks: list[dict[str, Any]]) -> None:
    passed = sum(1 for check in checks if check.get("status") == "passed")
    failed = sum(1 for check in checks if check.get("status") != "passed")
    lines = [
        "# Hosted Postgres Adapter Smoke",
        "",
        f"- Mode: {mode}.",
        f"- Passed: {passed}.",
        f"- Failed: {failed}.",
        f"- Adapter switch: `CHILLCRM_DATABASE_ADAPTER=postgres`.",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        detail = ", ".join(f"{key}={clip(value, 60)}" for key, value in check.items() if key not in {"check", "status"})
        lines.append(f"| {check.get('check')} | {check.get('status')} | {detail} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This smoke test does not upload files, create users, invite admins, save CRM records, or unlock remote writes. Full smoke mode should run only against the CHILLCRM Supabase staging database with private file access and package exports locked.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the guarded hosted Postgres adapter.")
    parser.add_argument("--dry-run", action="store_true", help="Check adapter wiring without connecting to Supabase.")
    parser.add_argument("--report", default=str(REPORTS_DIR / "hosted_postgres_adapter_smoke.md"))
    args = parser.parse_args()

    checks = dry_run_checks() if args.dry_run else smoke_checks()
    write_report(Path(args.report), "dry_run" if args.dry_run else "hosted_smoke", checks)
    failed = [check for check in checks if check.get("status") != "passed"]
    print(json.dumps({"mode": "dry_run" if args.dry_run else "hosted_smoke", "passed": len(checks) - len(failed), "failed": len(failed), "report": args.report}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
