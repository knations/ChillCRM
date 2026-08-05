"""Export/package helper functions for CHILLCRM."""

from __future__ import annotations

from typing import Any


COMPLETE_PACKAGE_FILENAME = "chillcrm_complete_package.zip"
DOCUMENT_FILES_PACKAGE_FILENAME = "chillcrm_document_files.zip"
RETIRED_REPORT_TOKENS = (
    "zendesk",
    "migration_completion",
    "hosted_database_migration",
    "staging_refresh",
    "staging_data",
    "source_of_truth_cutover",
    "cutover_rollback",
)


def complete_package_filename(stamp: str) -> str:
    return f"chillcrm_complete_package_{stamp}.zip"


def document_files_package_filename(stamp: str) -> str:
    return f"chillcrm_document_files_{stamp}.zip"


def export_package_status(manifest: dict[str, Any], fallback_bulk_export: dict[str, Any]) -> dict[str, Any]:
    package = manifest.get("package") or {}
    document_package = manifest.get("document_package") or {}
    bulk_export = manifest.get("bulk_export") or fallback_bulk_export
    bulk_enabled = bool(bulk_export.get("enabled"))
    package_ready = bool(package.get("url")) and bulk_enabled
    document_ready = bool(document_package.get("available")) and bulk_enabled
    total_count = 2
    ready_count = int(package_ready) + int(document_ready)
    return {
        "status": "complete" if ready_count == total_count else "locked" if not bulk_enabled else "attention",
        "ready_count": ready_count,
        "total_count": total_count,
        "bulk_export": bulk_export,
        "core_package": {
            "label": package.get("label"),
            "url": package.get("url"),
            "filename": package.get("filename"),
            "ready": package_ready,
            "enabled": bulk_enabled,
        },
        "document_package": {
            "label": document_package.get("label"),
            "url": document_package.get("url"),
            "filename": document_package.get("filename"),
            "ready": document_ready,
            "enabled": bulk_enabled,
            "file_count": int(document_package.get("file_count") or 0),
            "bytes": int(document_package.get("bytes") or 0),
        },
    }


def document_file_package_manifest_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "archive_item_id": entry["id"],
            "title": entry.get("title"),
            "record_type": entry.get("record_type"),
            "record_id": entry.get("record_id"),
            "source_collection": entry.get("source_collection"),
            "zendesk_record_id": entry.get("zendesk_record_id"),
            "occurred_at": entry.get("occurred_at"),
            "local_file": entry.get("local_file"),
            "package_path": entry.get("archive_path"),
            "bytes": entry.get("bytes"),
        }
        for entry in entries
    ]


def document_file_package_manifest(generated_at: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "source": "CHILLCRM document files",
        "file_count": len(entries),
        "bytes": sum(int(entry.get("bytes") or 0) for entry in entries),
        "documents": document_file_package_manifest_rows(entries),
    }


def complete_package_manifest(generated_at: str) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "source": "CHILLCRM",
        "database": None,
        "csv_exports": [],
        "reports": [],
        "docs": [],
    }


def include_report_in_package(filename: str) -> bool:
    lowered = filename.lower()
    return not any(token in lowered for token in RETIRED_REPORT_TOKENS)
