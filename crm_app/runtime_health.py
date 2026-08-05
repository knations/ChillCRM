"""Runtime status helpers for CHILLCRM.

These helpers keep environment/status reporting out of the main request
handler so health checks stay easy to inspect without changing route behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def remote_write_lock_status(enabled: bool, locked_post_paths: set[str]) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "mode": "locked" if enabled else "unlocked",
        "env_var": "REMOTE_WRITE_LOCK",
        "locked_post_paths": sorted(locked_post_paths),
        "message": (
            "Remote write lock is enabled; POST writes are blocked for staging validation."
            if enabled
            else "Remote write lock is off; CRM writes are available."
        ),
    }


def local_write_freeze_status(
    requested: bool,
    hosted_adapter_enabled: bool,
    locked_post_paths: set[str],
) -> dict[str, Any]:
    enabled = requested and not hosted_adapter_enabled
    if enabled:
        mode = "frozen"
        message = "Local write freeze is enabled; CRM mutations are blocked for final cutover packaging."
    elif requested and hosted_adapter_enabled:
        mode = "ignored_hosted_adapter"
        message = "Local write freeze is requested but ignored while the hosted Postgres adapter is active."
    else:
        mode = "unfrozen"
        message = "Local write freeze is off; CRM writes are available."
    return {
        "enabled": enabled,
        "requested": requested,
        "mode": mode,
        "env_var": "CHILLCRM_LOCAL_WRITE_FREEZE",
        "fallback_env_var": "LOCAL_WRITE_FREEZE",
        "applies_to": "local_sqlite",
        "ignored_when_hosted_postgres_adapter_enabled": True,
        "locked_post_paths": sorted(locked_post_paths),
        "allowed_post_paths": ["/api/backup"],
        "message": message,
    }


def bulk_package_export_status(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "mode": "enabled" if enabled else "locked",
        "env_var": "EXPORT_PACKAGE_ENABLED",
        "blocked_get_paths": ["/api/export_package", "/api/export_document_files_package"],
        "message": (
            "Bulk package exports are enabled."
            if enabled
            else "Bulk package exports are locked until permissions and staging validation are approved."
        ),
    }


def document_file_access_status(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "mode": "enabled" if enabled else "locked",
        "env_var": "DOCUMENT_FILE_ACCESS_ENABLED",
        "blocked_get_paths": ["/api/archive_file"],
        "message": (
            "Recovered document file access is enabled."
            if enabled
            else "Recovered document file access is locked until private storage and permissions are approved."
        ),
    }


def runtime_context(
    *,
    environment: str,
    database_url_configured: bool,
    hosted_adapter_enabled: bool,
    app_base_url_configured: bool,
    remote_lock: dict[str, Any],
    local_freeze: dict[str, Any],
    bulk_exports: dict[str, Any],
    document_files: dict[str, Any],
    auth_setup: dict[str, Any],
    portal_preview_enabled: bool,
) -> dict[str, Any]:
    return {
        "environment": environment,
        "environment_label": environment.replace("_", " ").replace("-", " ").title(),
        "database_mode": "hosted_postgres_adapter_enabled"
        if hosted_adapter_enabled
        else "hosted_postgres_configured_adapter_pending"
        if database_url_configured
        else "local_sqlite",
        "database_adapter": "postgres_compat" if hosted_adapter_enabled else "sqlite",
        "database_adapter_enabled": hosted_adapter_enabled,
        "database_adapter_env": "CHILLCRM_DATABASE_ADAPTER",
        "database_url_configured": database_url_configured,
        "app_base_url_configured": app_base_url_configured,
        "auth": {
            "required": auth_setup["required"],
            "session_secret_configured": auth_setup["session_secret_configured"],
            "cookie_secure": auth_setup["cookie_secure"],
        },
        "health_endpoint": "/health",
        "api_health_endpoint": "/api/health",
        "remote_write_lock": {
            "enabled": remote_lock["enabled"],
            "mode": remote_lock["mode"],
        },
        "local_write_freeze": {
            "enabled": local_freeze["enabled"],
            "requested": local_freeze["requested"],
            "mode": local_freeze["mode"],
        },
        "bulk_package_exports": {
            "enabled": bulk_exports["enabled"],
            "mode": bulk_exports["mode"],
        },
        "document_file_access": {
            "enabled": document_files["enabled"],
            "mode": document_files["mode"],
        },
        "portal_preview": {
            "enabled": portal_preview_enabled,
            "mode": "owner_only" if portal_preview_enabled else "disabled",
        },
    }


def reports_health_check(reports_dir: Path, database_url_configured: bool, reports_required: bool) -> dict[str, Any]:
    reports_present = reports_dir.exists() and reports_dir.is_dir()
    if reports_present:
        status = "ok"
        note = "Local report artifacts are available in this runtime."
    elif reports_required:
        status = "missing"
        note = "Report artifacts are required for this runtime and were not found."
    else:
        status = "omitted"
        note = "Report artifacts are private local outputs and are intentionally omitted from hosted source deployments."
    return {
        "status": status,
        "present": reports_present,
        "required": reports_required,
        "source": "private_local_artifacts",
        "note": note,
    }


def env_flag_value(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
