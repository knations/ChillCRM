#!/usr/bin/env python3
"""Generate a non-destructive local CRM data-quality report."""

from __future__ import annotations

import csv
import sys
from collections import Counter
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


def clip(value: Any, limit: int = 96) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> list[str]:
    visible_rows = rows[:limit] if limit else rows
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in visible_rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), 120).replace("|", "/"))
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


def issue_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issue_order = [
        ("person_missing_contact", "People missing contact", "Open People gaps"),
        ("lead_missing_email", "Leads missing email", "Open Leads gaps"),
        ("deal_missing_value", "Deals missing value", "Open Deals gaps"),
        ("company_missing_contact", "Companies missing contact", "Open Companies gaps"),
        ("records_missing_owner", "Records missing owner", "Open owner gaps"),
        ("deal_missing_relationship", "Deals missing contact/company", "Open relationship gaps"),
        ("deal_missing_stage", "Deals missing stage", "Open stage gaps"),
    ]
    counts = Counter(str(row.get("issue_key") or "") for row in rows)
    return [
        {
            "issue": label,
            "count": counts.get(issue_key, 0),
            "queue": queue,
        }
        for issue_key, label, queue in issue_order
        if counts.get(issue_key, 0)
    ]


def owner_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owner_counts = Counter(str(row.get("owner_name") or "Unassigned") for row in rows)
    issue_counts_by_owner: dict[str, Counter[str]] = {}
    for row in rows:
        owner = str(row.get("owner_name") or "Unassigned")
        issue_counts_by_owner.setdefault(owner, Counter())[str(row.get("issue_key") or "unknown")] += 1
    output = []
    for owner, count in owner_counts.most_common(8):
        issue_counts = issue_counts_by_owner.get(owner, Counter())
        issue_summary = ", ".join(
            f"{label}: {issue_counts[key]}"
            for key, label in [
                ("person_missing_contact", "people"),
                ("company_missing_contact", "companies"),
                ("lead_missing_email", "leads"),
                ("deal_missing_value", "deals"),
            ]
            if issue_counts.get(key)
        )
        output.append({"owner": owner, "rows": count, "issue_mix": issue_summary})
    return output


def work_order_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(row.get("issue_key") or "") for row in rows)
    work_order = [
        {
            "order": 1,
            "queue": "People missing contact",
            "count": counts.get("person_missing_contact", 0),
            "why_first": "Real client records need a reachable email, phone, or mobile before daily use.",
            "edit_when_known": "Email, phone, mobile, owner/status notes if obvious.",
            "skip_when": "The person is historical, duplicate-suspect, or needs identity review.",
        },
        {
            "order": 2,
            "queue": "Leads missing email",
            "count": counts.get("lead_missing_email", 0),
            "why_first": "Lead follow-up depends on a usable email or a clear reason to leave the lead as historical.",
            "edit_when_known": "Email, phone/mobile, status, owner.",
            "skip_when": "The lead looks like a test row or historical application with no usable identity.",
        },
        {
            "order": 3,
            "queue": "Deals missing value",
            "count": counts.get("deal_missing_value", 0),
            "why_first": "Pipeline reporting is clearer once known deal values are entered.",
            "edit_when_known": "Deal value, stage, close date, contact/company if missing.",
            "skip_when": "The amount is genuinely unknown or the deal is only historical context.",
        },
        {
            "order": 4,
            "queue": "Companies missing contact",
            "count": counts.get("company_missing_contact", 0),
            "why_first": "Company gaps are useful enrichment, but lower priority than reachable people and active leads.",
            "edit_when_known": "Company email, phone, website, address.",
            "skip_when": "The company is only a container for people and not a working account.",
        },
    ]
    return [row for row in work_order if row["count"]]


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    summary = app.data_quality_summary()
    totals = summary.get("totals") or {}
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    issue_rows = issue_summary_rows(rows)
    owner_rows = owner_summary_rows(rows)
    work_rows = work_order_rows(rows)
    lines = [
        "# Local CRM Data Quality",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a non-destructive review report. It does not edit, merge, delete, resolve, or rewrite CRM records.",
        "",
        "## Summary",
        "",
        f"- Records needing attention: {int(totals.get('attention_records') or 0):,}.",
        f"- Records with no usable contact channel: {int(totals.get('missing_contact_channel') or 0):,}.",
        f"- People with no email or phone/mobile: {int(totals.get('people_missing_contact') or 0):,}.",
        f"- Companies with no email or phone: {int(totals.get('companies_missing_contact') or 0):,}.",
        f"- Leads missing email: {int(totals.get('leads_missing_email') or 0):,}.",
        f"- Deals with no value: {int(totals.get('deals_missing_value') or 0):,}.",
        f"- Deals missing linked contact/company: {int(totals.get('deals_missing_relationship') or 0):,}.",
        f"- Deals missing stage: {int(totals.get('deals_missing_stage') or 0):,}.",
        f"- Records missing owner: {int(totals.get('records_missing_owner') or 0):,}.",
        "",
        "## Daily Work Order",
        "",
        "Use this as a practical daily queue. Open the matching Data Quality shortcut in Status, work known values in the normal right-side detail panel, and leave uncertain identity/merge questions for Cleanup.",
        "",
        *table(
            work_rows,
            [
                ("order", "Order"),
                ("queue", "Queue"),
                ("count", "Rows"),
                ("why_first", "Why"),
                ("edit_when_known", "Edit When Known"),
                ("skip_when", "Skip When"),
            ],
        ),
        "",
        "## Issue Summary",
        "",
        *table(
            issue_rows,
            [
                ("issue", "Issue"),
                ("count", "Rows"),
                ("queue", "Status Shortcut"),
            ],
        ),
        "",
        "## Owner Split",
        "",
        *table(
            owner_rows,
            [
                ("owner", "Owner"),
                ("rows", "Rows"),
                ("issue_mix", "Issue Mix"),
            ],
        ),
        "",
        "## Safety Boundary",
        "",
        "- Data Quality work is ordinary CRM hygiene, separate from duplicate/merge cleanup.",
        "- Edit only values you actually know; do not invent contact details or deal values.",
        "- Local record edits create a backup first and write Activity/audit entries.",
        "- Do not use this queue to merge records, resolve cleanup flags, or decide duplicate identity questions.",
        "- If a row looks like a duplicate, overlap, or historical record, park it for Cleanup instead of forcing a value.",
        "",
        "## Priority Samples",
        "",
        *table(
            summary.get("priority_records") or [],
            [
                ("type", "Type"),
                ("source_id", "ID"),
                ("name", "Name"),
                ("email", "Email"),
                ("match_context", "Issue"),
                ("updated_at", "Updated"),
            ],
        ),
        "",
        "## Export Rows",
        "",
        f"`reports/local_crm_data_quality.csv` contains {len(rows):,} issue rows for review.",
        "",
        *table(
            rows,
            [
                ("issue_label", "Issue"),
                ("record_type", "Type"),
                ("record_id", "ID"),
                ("record_name", "Record"),
                ("email", "Email"),
                ("phone", "Phone"),
                ("owner_name", "Owner"),
                ("status_or_stage", "Status/Stage"),
                ("updated_at", "Updated"),
            ],
            limit=24,
        ),
        "",
        "## Practical Use",
        "",
        "- Start with people and leads that have no practical contact channel.",
        "- Treat company contact gaps as lower-priority enrichment unless the company itself is the working account.",
        "- Deal value gaps are ordinary pipeline hygiene; filling them does not affect merge cleanup.",
        "- Owner, stage, and deal relationship gaps are included in the CSV if they appear.",
        "- In Status, use the Data Quality shortcuts to open focused People, Companies, Leads, and Deals queues.",
        "- Use local edits from record detail panels when a value is known.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_data_quality_rows()
    write_csv(REPORTS_DIR / "local_crm_data_quality.csv", rows)
    (REPORTS_DIR / "local_crm_data_quality.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} data-quality rows to reports/local_crm_data_quality.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
