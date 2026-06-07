#!/usr/bin/env python3
"""Generate a read-only managed-cloud provider shortlist."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
REPORTS_DIR = PROJECT_ROOT / "reports"


def handler() -> server.CRMRequestHandler:
    server.ensure_runtime_schema(DB_PATH)
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = DB_PATH
    return instance


def clip(value: Any, limit: int = 150) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def rows_of_type(rows: list[dict[str, Any]], row_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == row_type]


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int = 150) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), limit).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


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


def generate_report(rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = rows_of_type(rows, "summary")[0]
    provider_stacks = rows_of_type(rows, "provider_stack")
    criteria = rows_of_type(rows, "evaluation_criterion")
    sources = rows_of_type(rows, "official_source")
    recommendations = rows_of_type(rows, "shortlist_recommendation")
    owner_questions = rows_of_type(rows, "owner_question")
    next_steps = rows_of_type(rows, "next_step")

    lines = [
        "# Remote Managed Cloud Provider Shortlist",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a read-only shortlist for choosing the managed-cloud provider stack that can move the CRM from local-only use into secure remote access. It uses official provider documentation reviewed on 2026-06-05 and does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.",
        "",
        "## Summary",
        "",
        f"- Status: {summary.get('status')}.",
        f"- Decision needed: {summary.get('decision_needed')}.",
        f"- Recommended hosting path: {summary.get('recommended_hosting_path')}.",
        f"- Front-runner to price/test: {summary.get('front_runner_to_price_and_test')}.",
        f"- Alternate finalist: {summary.get('alternate_finalist')}.",
        f"- Source basis: {summary.get('source_basis')}",
        f"- Source of truth until cutover: {summary.get('source_of_truth_until_cutover')}.",
        f"- Local database bytes: {int(summary.get('local_database_bytes') or 0):,}.",
        f"- Local records: {int(summary.get('people') or 0):,} people, {int(summary.get('companies') or 0):,} companies, {int(summary.get('leads') or 0):,} leads, {int(summary.get('deals') or 0):,} deals.",
        f"- Archive/files: {int(summary.get('archive_items') or 0):,} archive items, {int(summary.get('linked_resources') or 0):,} linked resources, {int(summary.get('document_file_count') or 0):,} document files.",
        f"- Open gates: {int(summary.get('pending_project_decisions') or 0):,} pending project decisions, {int(summary.get('open_cleanup_groups') or 0):,} open cleanup groups.",
        f"- Reports ready: {int(summary.get('reports_ready') or 0):,} of {int(summary.get('reports_total') or 0):,}; backups available: {int(summary.get('backups_available') or 0):,}.",
        f"- Export packages: {int(summary.get('export_packages_ready') or 0):,} of {int(summary.get('export_packages_total') or 0):,} ready.",
        f"- CSV export: `{summary.get('export_url')}`.",
        "",
        "## Provider Shortlist",
        "",
        *table(
            provider_stacks,
            [
                ("rank", "Rank"),
                ("provider_stack", "Stack"),
                ("fit", "Fit"),
                ("ops_load", "Ops Load"),
                ("strength", "Strength"),
                ("watch_item", "Watch Item"),
                ("best_next_step", "Best Next Step"),
            ],
            190,
        ),
        "",
        "## Evaluation Criteria",
        "",
        *table(
            criteria,
            [
                ("order", "Order"),
                ("criterion", "Criterion"),
                ("requirement", "Requirement"),
                ("shortlist_reading", "Shortlist Reading"),
            ],
            190,
        ),
        "",
        "## Official Sources",
        "",
        *table(
            sources,
            [
                ("source_name", "Source"),
                ("supports", "Supports"),
                ("source_url", "URL"),
            ],
            220,
        ),
        "",
        "## Recommendation",
        "",
        *table(
            recommendations,
            [
                ("order", "Order"),
                ("recommendation", "Recommendation"),
                ("rationale", "Rationale"),
                ("boundary", "Boundary"),
            ],
            190,
        ),
        "",
        "## Owner Questions",
        "",
        *table(
            owner_questions,
            [
                ("order", "Order"),
                ("question", "Question"),
                ("recommended_answer", "Recommended Answer"),
                ("impact", "Impact"),
            ],
            190,
        ),
        "",
        "## Next Steps",
        "",
        *table(
            next_steps,
            [
                ("order", "Order"),
                ("step", "Step"),
                ("owner_role", "Owner Role"),
                ("gate", "Gate"),
            ],
            180,
        ),
        "",
        "## Safety Boundary",
        "",
        "This shortlist is planning only. It does not choose a provider, provision hosting, create accounts, enter payment details, create a remote database, upload files, create users, invite admins, save decisions, expose this machine, or change local CRM records.",
        "",
        "## Related Files",
        "",
        "- `reports/remote_managed_cloud_provider_shortlist.csv`",
        "- `reports/remote_hosting_decision_packet.md`",
        "- `reports/remote_staging_pricing_preflight.md`",
        "- `reports/remote_staging_setup_runbook.md`",
        "- `reports/remote_staging_deployment_spec.md`",
        "- `reports/remote_staging_validation_matrix.md`",
        "- `reports/remote_admin_pilot_onboarding_plan.md`",
        "- `reports/remote_production_cutover_checklist.md`",
        "- `reports/remote_admin_access_plan.md`",
        "- `reports/remote_admin_permissions_matrix.md`",
        "- `reports/remote_admin_implementation_blueprint.md`",
        "- `reports/remote_admin_rollout_board.md`",
        "- `reports/hosted_database_migration_readiness.md`",
        "- `reports/hosted_database_schema_draft.md`",
        "- `reports/hosted_database_data_load_plan.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_remote_managed_cloud_provider_shortlist_rows()
    write_csv(REPORTS_DIR / "remote_managed_cloud_provider_shortlist.csv", rows)
    (REPORTS_DIR / "remote_managed_cloud_provider_shortlist.md").write_text(generate_report(rows), encoding="utf-8")
    print(
        "Wrote "
        f"{len(rows):,} remote managed cloud provider rows to "
        "reports/remote_managed_cloud_provider_shortlist.md and .csv"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
