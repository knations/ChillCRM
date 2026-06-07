#!/usr/bin/env python3
"""Generate the Apple-style redesign pipeline report."""

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


def clip(value: Any, limit: int = 140) -> str:
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
            values.append(clip(row.get(key)).replace("|", "/"))
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
    summary = next((row for row in rows if row.get("row_type") == "summary"), {})
    gates = [row for row in rows if row.get("row_type") == "gate"]
    phases = [row for row in rows if row.get("row_type") == "phase"]
    contracts = [row for row in rows if row.get("row_type") == "preservation_contract"]
    lines = [
        "# Apple-Style Redesign Pipeline",
        "",
        f"Generated: {generated_at}",
        "",
        "This is a planning report only. It does not redesign screens, save project decisions, merge records, delete records, link archive items, or update Zendesk Sell.",
        "",
        "## Summary",
        "",
        f"- Pipeline status: {summary.get('status') or 'queued'}.",
        f"- Recommended timing: {summary.get('recommended_timing') or 'After functional cleanup'}.",
        f"- Redesign decision status: {summary.get('decision_status') or 'pending'}.",
        f"- Pending project decisions: {summary.get('pending_project_decisions', 0):,}.",
        f"- Deferred project decisions: {summary.get('deferred_project_decisions', 0):,}.",
        f"- Cleanup policies pending: {summary.get('cleanup_policies_pending', 0):,}.",
        f"- Open cleanup groups: {summary.get('open_cleanup_groups', 0):,}.",
        f"- Archive link coverage: {summary.get('archive_link_coverage_percent', 0):,}%.",
        f"- Document file coverage: {summary.get('document_file_coverage_percent', 0):,}%.",
        "",
        "## Gates",
        "",
        *table(
            gates,
            [
                ("order", "Order"),
                ("title", "Gate"),
                ("status", "Status"),
                ("evidence", "Evidence"),
                ("next_step", "Next Step"),
            ],
        ),
        "",
        "## Redesign Phases",
        "",
        *table(
            phases,
            [
                ("order", "Order"),
                ("title", "Phase"),
                ("description", "Intent"),
                ("scope", "Scope"),
                ("timing", "Timing"),
            ],
        ),
        "",
        "## Preservation Contract",
        "",
        *table(
            contracts,
            [
                ("order", "Order"),
                ("key", "Area"),
                ("title", "Must Preserve"),
            ],
        ),
        "",
        "## Recommendation",
        "",
        "Keep the visual redesign queued until the functional CRM, cleanup policies, archive review model, export/backup paths, and daily operating workflow are stable. Then redesign the shell, inspector, lists, command center, and review surfaces around the settled CRM shape.",
        "",
        "## Related Files",
        "",
        "- `docs/design_pipeline.md`",
        "- `reports/project_decision_sequence.md`",
        "- `reports/project_decision_ballot.md`",
        "- `reports/cleanup_execution_safety_plan.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    app = handler()
    rows = app.export_design_pipeline_rows()
    REPORTS_DIR.mkdir(exist_ok=True)
    write_csv(REPORTS_DIR / "apple_style_redesign_pipeline.csv", rows)
    (REPORTS_DIR / "apple_style_redesign_pipeline.md").write_text(generate_report(rows), encoding="utf-8")
    print(f"Wrote {len(rows):,} design pipeline rows to reports/apple_style_redesign_pipeline.md and .csv")


if __name__ == "__main__":
    main()
