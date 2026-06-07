#!/usr/bin/env python3
"""Generate an archive association audit for recovered Zendesk history."""

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


def clip(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            values.append(clip(row.get(key), 140).replace("|", "/"))
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


def generate_report(app: server.CRMRequestHandler, rows: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with app.db() as conn:
        audit = app.archive_association_audit_summary(conn)
    summary = audit.get("summary") or {}
    type_rows = [row for row in rows if row.get("row_type") == "archive_type"]
    communication_rows = [row for row in rows if row.get("row_type") == "unlinked_communication_signal"]
    lines = [
        "# Archive Association Audit",
        "",
        f"Generated: {generated_at}",
        "",
        "This report explains how recovered Zendesk Sell archive items are associated with local CRM records. It does not save review status, link archive items, merge records, delete records, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Total archive items: {summary.get('total_archive_items', 0):,}.",
        f"- Linked archive items: {summary.get('linked_archive_items', 0):,}.",
        f"- Unlinked archive items: {summary.get('unlinked_archive_items', 0):,}.",
        f"- Link coverage: {summary.get('link_coverage_percent', 0):,}%.",
        f"- Linked downloaded documents: {summary.get('linked_documents', 0):,} of {summary.get('document_total', 0):,}.",
        f"- Document file coverage: {summary.get('document_file_coverage_percent', 0):,}%.",
        f"- Unlinked calls/texts: {summary.get('unlinked_call_texts', 0):,}.",
        f"- Unreviewed unlinked calls/texts: {summary.get('unlinked_unreviewed_call_texts', 0):,}.",
        f"- Reviewed unlinked calls/texts: {summary.get('unlinked_reviewed_call_texts', 0):,}.",
        f"- Distinct unlinked phone/source numbers: {summary.get('distinct_unlinked_numbers', 0):,}.",
        f"- Unlinked calls with preserved recording URLs: {summary.get('unlinked_call_recording_urls', 0):,}.",
        f"- Exact CRM phone candidates among remaining calls/texts: {summary.get('exact_phone_candidates', 0):,}.",
        f"- Recommendation: {summary.get('recommendation')}",
        f"- Reason: {summary.get('reason')}",
        "",
        "## Archive Type Linkage",
        "",
        *table(
            type_rows,
            [
                ("item_type", "Type"),
                ("total", "Total"),
                ("linked", "Linked"),
                ("unlinked", "Unlinked"),
                ("downloaded_files", "Files"),
                ("external_urls", "URLs"),
                ("association_status", "Status"),
                ("recommended_action", "Recommended Action"),
            ],
        ),
        "",
        "## Remaining Communication Signals",
        "",
        *table(
            communication_rows,
            [
                ("item_type", "Type"),
                ("total", "Unlinked"),
                ("distinct_numbers", "Numbers"),
                ("has_resource_id", "Resource IDs"),
                ("has_resource_type", "Resource Types"),
                ("has_associated_deals", "Deal IDs"),
                ("has_external_url", "External URLs"),
                ("incoming_items", "Incoming"),
                ("missed_items", "Missed"),
            ],
        ),
        "",
        "## Findings",
        "",
        "- Downloaded document files are already attached to local person records and remain available in the separate document-file package.",
        "- Orders and lead conversions are linked through Zendesk-supplied resource IDs.",
        "- The remaining calls/texts do not include Zendesk resource IDs, associated deal IDs, contact IDs, lead IDs, or exact local CRM phone matches.",
        "- Call recording URLs are preserved on the relevant Archive items when Zendesk exposed them, but a recording URL is not a person/company/deal association by itself.",
        "",
        "## Recommended Next Step",
        "",
        "Use `reports/archive_review_worklist.md` and the in-app Archive Review queue for the 472 remaining calls/texts. Mark items Archive-only, Needs Lookup, or Ready to Link. Link only from the Archive inspector after the target local record is confirmed.",
        "",
        "## Related Files",
        "",
        "- `reports/archive_association_audit.csv`",
        "- `reports/archive_review_worklist.md`",
        "- `reports/unlinked_archive_matching_candidates.md`",
        "- `docs/operating_notes.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    app = handler()
    rows = app.export_archive_association_audit_rows()
    write_csv(REPORTS_DIR / "archive_association_audit.csv", rows)
    (REPORTS_DIR / "archive_association_audit.md").write_text(generate_report(app, rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} archive association audit rows to reports/archive_association_audit.md and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
