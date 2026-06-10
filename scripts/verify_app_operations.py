#!/usr/bin/env python3
"""Verify local CRM write operations against a temporary database copy."""

from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


SOURCE_DB = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"


def normalized_text(value: object) -> str:
    return str(value or "").casefold()


def assert_sorted(values: list[object], reverse: bool = False) -> None:
    normalized = [normalized_text(value) for value in values]
    assert normalized == sorted(normalized, reverse=reverse)


def assert_numeric_sorted(values: list[object], reverse: bool = False) -> None:
    normalized = [float(value or 0) for value in values]
    assert normalized == sorted(normalized, reverse=reverse)


def main() -> int:
    app_js = (PROJECT_ROOT / "crm_app" / "static" / "app.js").read_text(encoding="utf-8")
    server_py = (PROJECT_ROOT / "crm_app" / "server.py").read_text(encoding="utf-8")
    styles_css = (PROJECT_ROOT / "crm_app" / "static" / "styles.css").read_text(encoding="utf-8")
    index_html = (PROJECT_ROOT / "crm_app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "<title>ChillCRM</title>" in index_html
    assert "<h1>ChillCRM</h1>" in index_html
    assert "Have Fun Get Rich" in index_html
    reset_script = (PROJECT_ROOT / "scripts" / "reset_app_user_password.py").read_text(encoding="utf-8")
    backup_restore_script = (PROJECT_ROOT / "scripts" / "verify_backup_restore_drill.py").read_text(encoding="utf-8")
    cutover_rollback_script = (PROJECT_ROOT / "scripts" / "verify_cutover_rollback_package_readiness.py").read_text(encoding="utf-8")
    supabase_backup_script = (PROJECT_ROOT / "scripts" / "verify_supabase_backup_readiness.py").read_text(encoding="utf-8")
    supabase_backup_evidence_packet_script = (PROJECT_ROOT / "scripts" / "prepare_supabase_backup_evidence_packet.py").read_text(encoding="utf-8")
    monitoring_readiness_script = (PROJECT_ROOT / "scripts" / "verify_remote_monitoring_readiness.py").read_text(encoding="utf-8")
    monitoring_signoff_script = (PROJECT_ROOT / "scripts" / "record_remote_monitoring_signoff.py").read_text(encoding="utf-8")
    owner_shakedown_signoff_script = (PROJECT_ROOT / "scripts" / "record_owner_shakedown_signoff.py").read_text(encoding="utf-8")
    write_audit_rehearsal_script = (PROJECT_ROOT / "scripts" / "prepare_hosted_write_audit_rehearsal.py").read_text(encoding="utf-8")
    write_audit_execution_script = (PROJECT_ROOT / "scripts" / "execute_hosted_write_audit_rehearsal.py").read_text(encoding="utf-8")
    safe_gate_runner_script = (PROJECT_ROOT / "scripts" / "run_safe_production_gate_checks.py").read_text(encoding="utf-8")
    remaining_gate_guardrails_script = (PROJECT_ROOT / "scripts" / "verify_remaining_gate_guardrails.py").read_text(encoding="utf-8")
    remaining_gate_execution_readiness_script = (PROJECT_ROOT / "scripts" / "verify_remaining_gate_execution_readiness.py").read_text(encoding="utf-8")
    secret_handling_boundaries_script = (PROJECT_ROOT / "scripts" / "verify_secret_handling_boundaries.py").read_text(encoding="utf-8")
    local_write_freeze_readiness_script = (PROJECT_ROOT / "scripts" / "verify_local_write_freeze_readiness.py").read_text(encoding="utf-8")
    private_execution_inputs_script = (PROJECT_ROOT / "scripts" / "verify_private_execution_inputs.py").read_text(encoding="utf-8")
    owner_confirmed_wave_script = (PROJECT_ROOT / "scripts" / "run_owner_confirmed_production_wave.py").read_text(encoding="utf-8")
    source_cutover_preflight_script = (PROJECT_ROOT / "scripts" / "verify_source_of_truth_cutover_preflight.py").read_text(encoding="utf-8")
    vercel_environment_script = (PROJECT_ROOT / "scripts" / "verify_vercel_environment_readiness.py").read_text(encoding="utf-8")
    vercel_public_protection_script = (PROJECT_ROOT / "scripts" / "verify_vercel_public_protection.py").read_text(encoding="utf-8")
    deployment_freshness_script = (PROJECT_ROOT / "scripts" / "verify_hosted_deployment_freshness.py").read_text(encoding="utf-8")
    hosted_redeploy_preflight_script = (PROJECT_ROOT / "scripts" / "verify_hosted_redeploy_preflight.py").read_text(encoding="utf-8")
    supabase_staging_refresh_preflight_script = (PROJECT_ROOT / "scripts" / "verify_supabase_staging_refresh_preflight.py").read_text(encoding="utf-8")
    supabase_staging_refresh_run_script = (PROJECT_ROOT / "scripts" / "run_supabase_staging_refresh.py").read_text(encoding="utf-8")
    supabase_staging_data_parity_script = (PROJECT_ROOT / "scripts" / "verify_supabase_staging_data_parity.py").read_text(encoding="utf-8")
    hosted_smoke_script = (PROJECT_ROOT / "scripts" / "verify_vercel_hosted_app.py").read_text(encoding="utf-8")
    hosted_smoke_wrapper = (PROJECT_ROOT / "scripts" / "run_newest_hosted_smoke_with_vercel_bypass.py").read_text(encoding="utf-8")
    deploy_script = (PROJECT_ROOT / "scripts" / "deploy_chillcrm_to_vercel.py").read_text(encoding="utf-8")
    remaining_gates_packet_script = (PROJECT_ROOT / "scripts" / "prepare_remaining_production_gate_packet.py").read_text(encoding="utf-8")
    owner_gate_reply_validation_script = (PROJECT_ROOT / "scripts" / "validate_owner_gate_reply.py").read_text(encoding="utf-8")
    owner_approved_wave_packet_script = (PROJECT_ROOT / "scripts" / "prepare_owner_approved_wave_packet.py").read_text(encoding="utf-8")
    owner_gate_intake_packet_script = (PROJECT_ROOT / "scripts" / "prepare_owner_gate_intake_packet.py").read_text(encoding="utf-8")
    production_readiness_script = (PROJECT_ROOT / "scripts" / "verify_remote_production_readiness.py").read_text(encoding="utf-8")
    owner_recovery_closure_script = (PROJECT_ROOT / "scripts" / "verify_owner_recovery_closure.py").read_text(encoding="utf-8")
    owner_recovery_disable_script = (PROJECT_ROOT / "scripts" / "disable_owner_recovery_after_access.py").read_text(encoding="utf-8")
    source_cutover_approval_script = (PROJECT_ROOT / "scripts" / "record_source_of_truth_cutover_approval.py").read_text(encoding="utf-8")
    assert "PostgresCompatConnection" in server_py
    assert "translate_sqlite_sql_for_postgres" in server_py
    assert "CHILLCRM_DATABASE_ADAPTER" in server_py
    assert "CHILLCRM_LOCAL_WRITE_FREEZE" in server_py
    assert "local_write_freeze_status" in server_py
    assert "should_block_local_write" in server_py
    assert "send_local_write_frozen" in server_py
    translated_sql = server.translate_sqlite_sql_for_postgres(
        "SELECT id, json_extract(source_json, '$.resource_id') AS rid FROM people "
        "WHERE id = ? AND name LIKE :like AND date(updated_at) >= date('now') "
        "ORDER BY name COLLATE NOCASE LIMIT ?"
    )
    assert "%s" in translated_sql
    assert "ILIKE" in server.translate_sqlite_sql_for_postgres(
        "SELECT * FROM people WHERE name LIKE ? OR email NOT LIKE ?"
    )
    assert "NOT ILIKE" in server.translate_sqlite_sql_for_postgres(
        "SELECT * FROM people WHERE email NOT LIKE ?"
    )
    assert "source_json::jsonb ->> 'resource_id'" in translated_sql
    assert "CAST(updated_at AS date) >= CURRENT_DATE" in translated_sql
    assert "COLLATE NOCASE" not in translated_sql
    assert server.postgres_parameters_for_sql(
        "SELECT * FROM people WHERE name LIKE :like OR email LIKE :like",
        {"like": "%kevin%"},
    ) == ["%kevin%", "%kevin%"]
    row = server.PostgresCompatRow(["id", "name"], (7, "Adapter Probe"))
    assert row[0] == 7
    assert row["name"] == "Adapter Probe"
    assert dict(row) == {"id": 7, "name": "Adapter Probe"}
    original_database_url = os.environ.pop("DATABASE_URL", None)
    original_adapter = os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
    original_legacy_adapter = os.environ.pop("CRM_DATABASE_ADAPTER", None)
    original_local_write_freeze = os.environ.pop("CHILLCRM_LOCAL_WRITE_FREEZE", None)
    original_legacy_write_freeze = os.environ.pop("LOCAL_WRITE_FREEZE", None)
    original_crm_env = os.environ.pop("CRM_ENV", None)
    original_app_base_url = os.environ.pop("APP_BASE_URL", None)
    try:
        runtime_handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
        runtime_handler.db_path = SOURCE_DB
        assert server.hosted_postgres_adapter_enabled_from_env() is False
        assert runtime_handler.runtime_context()["database_mode"] == "local_sqlite"
        assert runtime_handler.runtime_context()["local_write_freeze"]["enabled"] is False
        os.environ["CHILLCRM_LOCAL_WRITE_FREEZE"] = "1"
        local_freeze_runtime = runtime_handler.runtime_context()
        assert local_freeze_runtime["local_write_freeze"]["enabled"] is True
        assert local_freeze_runtime["local_write_freeze"]["mode"] == "frozen"
        assert runtime_handler.should_block_local_write("/api/update_record") is True
        assert runtime_handler.should_block_local_write("/api/backup") is False
        os.environ["DATABASE_URL"] = "postgresql://user:pass@example.local:5432/postgres"
        assert runtime_handler.runtime_context()["database_mode"] == "hosted_postgres_configured_adapter_pending"
        assert runtime_handler.runtime_context()["database_adapter_enabled"] is False
        os.environ["CHILLCRM_DATABASE_ADAPTER"] = "postgres"
        assert server.hosted_postgres_adapter_enabled_from_env() is True
        hosted_runtime = runtime_handler.runtime_context()
        assert hosted_runtime["database_mode"] == "hosted_postgres_adapter_enabled"
        assert hosted_runtime["database_adapter"] == "postgres_compat"
        assert hosted_runtime["database_adapter_enabled"] is True
        assert hosted_runtime["local_write_freeze"]["enabled"] is False
        assert hosted_runtime["local_write_freeze"]["mode"] == "ignored_hosted_adapter"
        assert json.loads(runtime_handler.audit_value_for_storage("from google")) == "from google"
        assert json.loads(runtime_handler.audit_value_for_storage(["from google", "BMSE July 2026"])) == [
            "from google",
            "BMSE July 2026",
        ]
        assert runtime_handler.next_hosted_primary_key(
            type(
                "ProbeConn",
                (),
                {
                    "execute": lambda self, sql: type(
                        "ProbeCursor",
                        (),
                        {"fetchone": lambda self: {"next_id": 72}},
                    )()
                },
            )(),
            "tags",
        ) == 72
        assert runtime_handler.next_hosted_primary_key(
            type(
                "ProbeConn",
                (),
                {
                    "execute": lambda self, sql: type(
                        "ProbeCursor",
                        (),
                        {"fetchone": lambda self: {"next_id": 73}},
                    )()
                },
            )(),
            "tag_assignments",
        ) == 73
        assert runtime_handler.next_hosted_primary_key(
            type(
                "ProbeConn",
                (),
                {
                    "execute": lambda self, sql: type(
                        "ProbeCursor",
                        (),
                        {"fetchone": lambda self: {"next_id": 74}},
                    )()
                },
            )(),
            "notes",
        ) == 74
        assert runtime_handler.next_hosted_primary_key(
            type(
                "ProbeConn",
                (),
                {
                    "execute": lambda self, sql: type(
                        "ProbeCursor",
                        (),
                        {"fetchone": lambda self: {"next_id": 75}},
                    )()
                },
            )(),
            "local_addresses",
        ) == 75
        os.environ["CRM_ENV"] = "staging"
        assert runtime_handler.runtime_context()["environment"] == "staging"
        os.environ["APP_BASE_URL"] = "https://chillcrm.app"
        production_runtime = runtime_handler.runtime_context()
        assert production_runtime["environment"] == "production"
        assert production_runtime["environment_label"] == "Production"
    finally:
        if original_database_url is not None:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        if original_adapter is not None:
            os.environ["CHILLCRM_DATABASE_ADAPTER"] = original_adapter
        else:
            os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
        if original_legacy_adapter is not None:
            os.environ["CRM_DATABASE_ADAPTER"] = original_legacy_adapter
        else:
            os.environ.pop("CRM_DATABASE_ADAPTER", None)
        if original_local_write_freeze is not None:
            os.environ["CHILLCRM_LOCAL_WRITE_FREEZE"] = original_local_write_freeze
        else:
            os.environ.pop("CHILLCRM_LOCAL_WRITE_FREEZE", None)
        if original_legacy_write_freeze is not None:
            os.environ["LOCAL_WRITE_FREEZE"] = original_legacy_write_freeze
        else:
            os.environ.pop("LOCAL_WRITE_FREEZE", None)
        if original_crm_env is not None:
            os.environ["CRM_ENV"] = original_crm_env
        else:
            os.environ.pop("CRM_ENV", None)
        if original_app_base_url is not None:
            os.environ["APP_BASE_URL"] = original_app_base_url
        else:
            os.environ.pop("APP_BASE_URL", None)
    assert "grid-template-columns: 208px minmax(0, 1fr) 360px" in styles_css
    assert "@media (max-width: 1040px)" in styles_css
    assert "grid-column: 1 / -1" in styles_css
    assert ".table-tools {\n    align-items: stretch;\n    flex-direction: column;" in styles_css
    assert ".pager {\n    flex-wrap: wrap;\n    justify-content: flex-start;" in styles_css
    assert ".table-scroll" in styles_css
    assert "overflow-x: auto" in styles_css
    assert "min-width: 720px" in styles_css
    assert '<div class="table-scroll">' in app_js
    assert ".detail-panel .edit-grid" in styles_css
    assert ".detail-panel .address-fields" in styles_css
    assert ".record-file-facts" in styles_css
    assert ".record-lifecycle-body" in styles_css
    assert "grid-template-columns: 1fr;" in styles_css
    assert ".detail-panel .contact-action-row {\n    grid-template-columns: 1fr;" in styles_css
    assert ".detail-panel .task-edit-row {\n    grid-template-columns: 1fr;" in styles_css
    assert ".detail-panel .task-line {\n    flex-wrap: wrap;\n    justify-content: flex-start;" in styles_css
    assert "grid-template-columns: 1fr 1fr;" in styles_css
    assert "/api/vcard" in server_py
    assert "def vcard_contact_card(" in server_py
    assert "def render_vcard(" in server_py
    assert "text/vcard" in server_py
    assert "Contact Card" in app_js
    assert "contactCardHref(" in app_js
    assert "contact-card-strip" in app_js
    assert ".contact-card-strip" in styles_css
    assert ".contact-card-button" in styles_css
    assert "<h3>Actions</h3>" in app_js
    assert "<h3>Contact Actions</h3>" not in app_js
    assert "<h3>Edit</h3>" not in app_js
    assert app_js.index('${contactActions(detail)}') < app_js.index('${editForm(detail)}') < app_js.index('${recordFileHero(detail)}')
    assert app_js.index('addRow(source, "phone"') < app_js.index('addRow(source, "email"')
    assert app_js.index("${renderContactRows(primaryRows)}") < app_js.index("${contactCardStrip(cardSources)}") < app_js.index("${renderContactRows(secondaryRows)}")
    assert "/api/profile_image" in server_py
    assert "/api/upload_profile_image" in server_py
    assert "record_profile_images" in server_py
    assert "personProfileImageControl" in app_js
    assert "showProfileImageFallback" in app_js
    assert "person-profile-image-frame person-profile-upload-button" in app_js
    assert 'data-action-label="${escapeHtml(actionLabel)}"' in app_js
    assert "Change photo" in app_js
    assert "Change Photo" not in app_js
    assert "Add Photo" not in app_js
    assert "person-profile-remove-button" not in app_js
    assert 'alt=""' in app_js
    assert "prepareProfileImageUpload" in app_js
    assert ".person-profile-image-control" in styles_css
    assert ".person-profile-image-frame.image-failed" in styles_css
    assert "content: attr(data-action-label)" in styles_css
    assert 'content: "+"' not in styles_css
    assert ".person-profile-image-actions" not in styles_css
    assert "profile_images/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert 'credentials: "same-origin"' in app_js
    assert "Server returned an unexpected response" in app_js
    assert 'id="saveRecordButton" type="button"' in app_js
    assert 'addEventListener("submit"' in app_js
    assert "mobileDetailOpen" in app_js
    assert "openMobileDetailView(" in app_js
    assert "closeMobileDetailView(" in app_js
    assert "captureInputFocus(" in app_js
    assert "restoreInputFocus(focusState)" in app_js
    assert "activateSearchWorkspace(" in app_js
    assert "showOnlyMainView(els.list)" in app_js
    assert "listTagSearch" in app_js
    assert "listTagSuggestions" in app_js
    assert "tagSuggestionOptions(" in app_js
    assert "fetchListTagSuggestions(" in app_js
    assert "openAddPersonTagButton" in app_js
    assert "personTagSuggestions" in app_js
    assert "wirePersonTagPicker(" in app_js
    assert "resolvePersonTagChoice(" in app_js
    assert "/api/create_tag" in app_js
    assert "/api/rename_tag" in app_js
    assert "createTagForm" in app_js
    assert "rename-tag-button" in app_js
    assert ".person-tag-picker" in styles_css
    assert ".tag-create-form" in styles_css
    assert ".tag-row-actions" in styles_css
    assert 'id="listTagFilter"' not in app_js
    assert ".tag-search-filter" in styles_css
    assert "state.searchRequestId" in app_js
    assert "searchReturnView" in app_js
    assert "timeoutMs: 12000" in app_js
    assert "mode=quick" in app_js
    assert "Search took too long" in app_js
    assert "Search did not complete" in app_js
    assert 'event.key !== "Enter"' in app_js
    assert "globalSearchForm" in index_html
    assert "globalSearchClear" in index_html
    assert ".search-form" in styles_css
    assert 'self.send_header("Cache-Control", "no-store")' in server_py
    assert '"mode": "quick"' in server_py
    assert "Fast search covers records and direct relationships" in server_py
    assert "mobileDetailBackLabel(" in app_js
    assert "Back to ${state.mobileDetailReturnLabel" in app_js
    assert "state.mobileDetailReturnLabel = \"Search\"" in app_js
    assert "mobile-detail-open" in styles_css
    assert ".mobile-detail-back" in styles_css
    assert ".app-shell.mobile-detail-open .sidebar,\n  .app-shell.mobile-detail-open .main {\n    display: none;" in styles_css
    assert ".app-shell.mobile-detail-open .detail-panel" in styles_css
    assert "position: fixed" in styles_css
    assert "height: 100svh" in styles_css
    assert "detailHeader(" in app_js
    assert "detail-masthead" in app_js
    assert "detail-close-button" in app_js
    assert "closeCurrentRecordDetail" in app_js
    assert "detail-collapsed" in app_js
    assert ".detail-masthead" in styles_css
    assert ".app-shell.detail-collapsed" in styles_css
    assert ".app-shell.detail-collapsed .detail-panel" in styles_css
    assert "position: sticky" in styles_css
    assert "top: 0" in styles_css
    assert "listRowAttributes(" in app_js
    assert "recordIsCurrentDetail(" in app_js
    assert "syncActiveListRows()" in app_js
    assert "active-record-row" in app_js
    assert ".data-table tbody tr.active-record-row" in styles_css
    assert "backdrop-filter: blur(18px)" in styles_css
    assert "scroll-snap-type: x proximity" in styles_css
    assert ".data-table thead {\n    display: none;" in styles_css
    assert ".table-tools .filter-row {\n    background: transparent;" in styles_css
    assert "#globalSearch,\n  .table-tools input,\n  .filter-row input," in styles_css
    assert "search-results-table" in app_js
    assert "record-list-table" in app_js
    assert "tag-list-table" in app_js
    assert ".data-table td::before" in styles_css
    assert ".archive-table td:nth-child(7)::before" in styles_css
    assert ".cleanup-group-table td:nth-child(9)::before" in styles_css
    assert ".app-shell.mobile-detail-open .edit-grid label" in styles_css
    assert ".app-shell.mobile-detail-open .archive-target-search" in styles_css
    assert 'aria-current="true"' in app_js
    assert "listTypeForDetailType" in app_js
    assert "detailBelongsToCurrentList" in app_js
    assert "refreshCurrentListForDetail" in app_js
    assert "await refreshCurrentListForDetail(updated.detail)" in app_js
    assert "fillAllRecommendedDecisions" in app_js
    assert "resetAllProjectDecisions" in app_js
    assert "fillRecommendedDecision" in app_js
    assert "Save & Next Decision" in app_js
    assert "save-project-decision-next" in app_js
    assert "nextPendingProjectDecisionKey" in app_js
    assert "nextProjectDecisionSequenceItem" in app_js
    assert "nextActionChoices" in app_js
    assert "decisionKey && action.recommended_value && action.secondary_action" in app_js
    assert "querySelector('select[name=\"status\"]')?.value === \"pending\"" in app_js
    assert "querySelector('select[name=\"status\"]')?.value === \"deferred\"" in app_js
    assert "project-decision-unsaved" in app_js
    assert "reset-project-decision" in app_js
    assert "Reset Staged" in app_js
    assert "project-decision-option-detail" in app_js
    assert "projectDecisionOptionDetail" in app_js
    assert "projectDecisionOptionCode" in app_js
    assert "projectDecisionChoiceCode" in app_js
    assert "data-code" in app_js
    assert "updateProjectDecisionOptionDetail" in app_js
    assert "Choose a path to see what it means before saving" in app_js
    assert "project-decision-save-effect" in app_js
    assert "projectDecisionSaveEffect" in app_js
    assert "Records this decision only" in app_js
    assert "project-decision-status-guidance" in app_js
    assert "updateProjectDecisionStatusGuidance" in app_js
    assert "projectDecisionStatusGuidanceText" in app_js
    assert "Saving as Pending records a draft only" in app_js
    assert ".next-action-choices" in styles_css
    assert "operationalWorkQueuePanel" in app_js
    assert "workQueueCard" in app_js
    assert "miniActivityList" in app_js
    assert "wireWorkQueuePresets" in app_js
    assert "Pipeline Focus" in app_js
    assert "Open Active Deals" in app_js
    assert "Open New Leads" in app_js
    assert "Recent Local Changes" in app_js
    assert "Open Local Changes" in app_js
    assert 'state.activityType = "local_change"' in app_js
    assert "Data Quality" in app_js
    assert "/reports/local_crm_data_quality.md" in app_js
    assert "quality_people_missing_contact" in app_js
    assert "quality_companies_missing_contact" in app_js
    assert "quality_leads_missing_email" in app_js
    assert "quality_deals_missing_value" in app_js
    assert "listQualityIssue" in app_js
    assert "quality_issue" in app_js
    assert "listProvenanceFilter" in app_js
    assert "provenanceChips" in app_js
    assert "All sources" in app_js
    assert "Has local changes" in app_js
    assert "Source Mix" in app_js
    assert "sourceMixList" in app_js
    assert "sourceMatch" in app_js
    assert "^source_(people|companies|leads|deals)_(imported|local|changed)$" in app_js
    assert "openSourcePreset" in app_js
    assert "Archive Review" in app_js
    assert "archiveReviewGroupList" in app_js
    assert "openArchiveReviewPreset" in app_js
    assert "Association Coverage" in app_js
    assert "archiveAssociationCoveragePanel" in app_js
    assert "archiveAssociationMiniList" in app_js
    assert "No auto-link candidates" in app_js
    assert "Archive Review Triage" in app_js
    assert "archiveReviewTriagePanel" in app_js
    assert "archiveTriageLaneFilter" in app_js
    assert "archiveTriageLaneOptions" in app_js
    assert "archive-triage-filter-button" in app_js
    assert "archive-triage-row-hint" in app_js
    assert "archive_review_unreviewed" in app_js
    assert "archive_review" in server_py
    assert "archive_review_triage" in server_py
    assert "triage_lane" in server_py
    assert "enrich_archive_triage_rows" in server_py
    assert "local_crm_archive_review_triage.csv" in server_py
    assert "archive_review_triage.md" in server_py
    assert "link_coverage_percent" in server_py
    assert "unlinked_unreviewed_call_texts" in server_py
    assert "migration_completion_audit" in server_py
    assert "local_crm_migration_completion_audit.csv" in server_py
    assert "migration_completion_audit.md" in server_py
    assert "database_map" in server_py
    assert "local_crm_database_map.csv" in server_py
    assert "local_crm_database_map.md" in server_py
    assert "zendesk_independence" in server_py
    assert "local_crm_zendesk_independence_checklist.csv" in server_py
    assert "zendesk_independence_checklist.md" in server_py
    assert "remote_admin_access_plan" in server_py
    assert "local_crm_remote_admin_access_plan.csv" in server_py
    assert "remote_admin_access_plan.md" in server_py
    assert "remote_admin_permissions_matrix" in server_py
    assert "local_crm_remote_admin_permissions_matrix.csv" in server_py
    assert "remote_admin_permissions_matrix.md" in server_py
    assert "remote_admin_implementation_blueprint" in server_py
    assert "local_crm_remote_admin_implementation_blueprint.csv" in server_py
    assert "remote_admin_implementation_blueprint.md" in server_py
    assert "remote_admin_rollout_board" in server_py
    assert "local_crm_remote_admin_rollout_board.csv" in server_py
    assert "remote_admin_rollout_board.md" in server_py
    assert "remote_hosting_decision_packet" in server_py
    assert "local_crm_remote_hosting_decision_packet.csv" in server_py
    assert "remote_hosting_decision_packet.md" in server_py
    assert "remote_managed_cloud_provider_shortlist" in server_py
    assert "local_crm_remote_managed_cloud_provider_shortlist.csv" in server_py
    assert "remote_managed_cloud_provider_shortlist.md" in server_py
    assert "remote_staging_pricing_preflight" in server_py
    assert "local_crm_remote_staging_pricing_preflight.csv" in server_py
    assert "remote_staging_pricing_preflight.md" in server_py
    assert "remote_staging_setup_runbook" in server_py
    assert "local_crm_remote_staging_setup_runbook.csv" in server_py
    assert "remote_staging_setup_runbook.md" in server_py
    assert "remote_staging_deployment_spec" in server_py
    assert "local_crm_remote_staging_deployment_spec.csv" in server_py
    assert "remote_staging_deployment_spec.md" in server_py
    assert "remote_staging_validation_matrix" in server_py
    assert "local_crm_remote_staging_validation_matrix.csv" in server_py
    assert "remote_staging_validation_matrix.md" in server_py
    assert "remote_admin_pilot_onboarding_plan" in server_py
    assert "local_crm_remote_admin_pilot_onboarding_plan.csv" in server_py
    assert "remote_admin_pilot_onboarding_plan.md" in server_py
    assert "remote_production_cutover_checklist" in server_py
    assert "local_crm_remote_production_cutover_checklist.csv" in server_py
    assert "remote_production_cutover_checklist.md" in server_py
    assert "local_write_freeze_readiness.md" in server_py
    assert "private_execution_inputs.md" in server_py
    assert "owner_confirmed_production_wave.md" in server_py
    assert "hosted_database_migration_readiness" in server_py
    assert "local_crm_hosted_database_migration_readiness.csv" in server_py
    assert "hosted_database_migration_readiness.md" in server_py
    assert "hosted_schema_draft" in server_py
    assert "local_crm_hosted_schema_draft.csv" in server_py
    assert "hosted_database_schema_draft.md" in server_py
    assert "hosted_database_schema_draft.sql" in server_py
    assert "hosted_data_load_plan" in server_py
    assert "local_crm_hosted_data_load_plan.csv" in server_py
    assert "hosted_database_data_load_plan.md" in server_py
    assert "lead_person_overlap_spot_check" in server_py
    assert "local_crm_lead_person_overlap_spot_check.csv" in server_py
    assert "lead_person_overlap_spot_check.md" in server_py
    assert "duplicate_people_spot_check" in server_py
    assert "local_crm_duplicate_people_spot_check.csv" in server_py
    assert "duplicate_people_spot_check.md" in server_py
    assert "duplicate_people_review_worksheet" in server_py
    assert "local_crm_duplicate_people_review_worksheet.csv" in server_py
    assert "duplicate_people_review_worksheet.md" in server_py
    assert "duplicate_leads_spot_check" in server_py
    assert "local_crm_duplicate_leads_spot_check.csv" in server_py
    assert "duplicate_leads_spot_check.md" in server_py
    assert "duplicate_leads_review_worksheet" in server_py
    assert "local_crm_duplicate_leads_review_worksheet.csv" in server_py
    assert "duplicate_leads_review_worksheet.md" in server_py
    assert "Open Worksheet" in app_js
    assert "Worksheet CSV" in app_js
    assert "record_sources" in server_py
    assert "operational_source_mix" in server_py
    assert ".source-mix-row" in styles_css
    assert ".archive-review-mini-row" in styles_css
    assert ".archive-association-panel" in styles_css
    assert ".archive-triage-panel" in styles_css
    assert ".archive-triage-row-hint" in styles_css
    duplicate_tag_report = (PROJECT_ROOT / "reports" / "duplicate_tag_spot_check.md").read_text(encoding="utf-8")
    assert "## Decision Prompt" in duplicate_tag_report
    assert "## Save Boundary" in duplicate_tag_report
    assert "Answer A, B, or C in Status" in duplicate_tag_report
    assert "Even with A saved" in duplicate_tag_report
    overlap_spot_check_report = (PROJECT_ROOT / "reports" / "lead_person_overlap_spot_check.md").read_text(encoding="utf-8")
    assert "## Decision Prompt" in overlap_spot_check_report
    assert "## Why A Is Recommended" in overlap_spot_check_report
    assert "## Overlap Groups" in overlap_spot_check_report
    assert "## Save Boundary" in overlap_spot_check_report
    assert "Answer A, B, or C in Status" in overlap_spot_check_report
    people_spot_check_report = (PROJECT_ROOT / "reports" / "duplicate_people_spot_check.md").read_text(encoding="utf-8")
    assert "## Decision Prompt" in people_spot_check_report
    assert "## Starting Groups" in people_spot_check_report
    assert "## Review Signals" in people_spot_check_report
    assert "## Save Boundary" in people_spot_check_report
    people_worksheet_report = (PROJECT_ROOT / "reports" / "duplicate_people_review_worksheet.md").read_text(encoding="utf-8")
    assert "## How To Use" in people_worksheet_report
    assert "## First High-Priority Groups" in people_worksheet_report
    assert "## Worksheet Columns" in people_worksheet_report
    assert "Reviewer Choice" in people_worksheet_report
    assert "Reviewer Notes" in people_worksheet_report
    assert "does not save the duplicate people policy" in people_worksheet_report
    leads_spot_check_report = (PROJECT_ROOT / "reports" / "duplicate_leads_spot_check.md").read_text(encoding="utf-8")
    assert "## Decision Prompt" in leads_spot_check_report
    assert "## Starting Groups" in leads_spot_check_report
    assert "## Review Signals" in leads_spot_check_report
    assert "## Save Boundary" in leads_spot_check_report
    leads_worksheet_report = (PROJECT_ROOT / "reports" / "duplicate_leads_review_worksheet.md").read_text(encoding="utf-8")
    assert "## How To Use" in leads_worksheet_report
    assert "## First High-Priority Groups" in leads_worksheet_report
    assert "## Worksheet Columns" in leads_worksheet_report
    assert "Application Profile" in leads_worksheet_report
    assert "Reviewer Choice" in leads_worksheet_report
    assert "does not save the duplicate leads policy" in leads_worksheet_report
    archive_triage_report = (PROJECT_ROOT / "reports" / "archive_review_triage.md").read_text(encoding="utf-8")
    assert "## Triage Lanes" in archive_triage_report
    assert "Likely archive-only" in archive_triage_report
    assert "does not save review status" in archive_triage_report
    assert "Archive triage lane filter" in archive_triage_report
    assert "qualityIssueChips" in app_js
    assert "quality-chip-list" in app_js
    assert "detailQualityPanel(detail)" in app_js
    assert "data-quality-detail" in app_js
    assert "qualityGuidanceText" in app_js
    assert "Email, phone, or mobile needed." in app_js
    data_quality_report = (PROJECT_ROOT / "reports" / "local_crm_data_quality.md").read_text(encoding="utf-8")
    assert "## Daily Work Order" in data_quality_report
    assert "## Issue Summary" in data_quality_report
    assert "## Owner Split" in data_quality_report
    assert "## Safety Boundary" in data_quality_report
    assert "Local record edits create a backup first" in data_quality_report
    assert "Operating Work Queue" in app_js
    assert "Safe daily-use work is separated" in app_js
    daily_guide_report = (PROJECT_ROOT / "reports" / "daily_operating_guide.md").read_text(encoding="utf-8")
    assert "## First Week Handoff" in daily_guide_report
    assert "## Before You Change Anything" in daily_guide_report
    assert "## Recovery And Portability" in daily_guide_report
    assert "Download Complete Local CRM Package" in daily_guide_report
    assert "Use Restore beside the desired backup" in daily_guide_report
    database_map_report = (PROJECT_ROOT / "reports" / "local_crm_database_map.md").read_text(encoding="utf-8")
    assert "Read-only database inventory" in database_map_report
    assert "## Table Map" in database_map_report
    assert "## Relationship Map" in database_map_report
    assert "## Export Inventory" in database_map_report
    assert "## Safety Boundary" in database_map_report
    independence_report = (PROJECT_ROOT / "reports" / "zendesk_independence_checklist.md").read_text(encoding="utf-8")
    assert "## Independence Requirements" in independence_report
    assert "## Preserve Before Decommission" in independence_report
    assert "## Zendesk Access Boundary" in independence_report
    assert "No Zendesk writes needed" in independence_report
    remote_access_report = (PROJECT_ROOT / "reports" / "remote_admin_access_plan.md").read_text(encoding="utf-8")
    assert "## Hosting Posture" in remote_access_report
    assert "Managed cloud app" in remote_access_report
    assert "## Security Controls" in remote_access_report
    assert "does not provision hosting" in remote_access_report
    remote_permissions_report = (PROJECT_ROOT / "reports" / "remote_admin_permissions_matrix.md").read_text(encoding="utf-8")
    assert "## Role Matrix" in remote_permissions_report
    assert "## Action Permissions" in remote_permissions_report
    assert "## Audit Requirements" in remote_permissions_report
    assert "does not create users" in remote_permissions_report
    assert "Current identity source" in remote_permissions_report
    remote_implementation_report = (PROJECT_ROOT / "reports" / "remote_admin_implementation_blueprint.md").read_text(encoding="utf-8")
    assert "## Build Workstreams" in remote_implementation_report
    assert "## Remote-Only Tables" in remote_implementation_report
    assert "## Endpoint Changes" in remote_implementation_report
    assert "## Verification Gates" in remote_implementation_report
    assert "does not provision hosting" in remote_implementation_report
    remote_rollout_report = (PROJECT_ROOT / "reports" / "remote_admin_rollout_board.md").read_text(encoding="utf-8")
    assert "## Rollout Lanes" in remote_rollout_report
    assert "## Rollout Tasks" in remote_rollout_report
    assert "## Decision Prompts" in remote_rollout_report
    assert "## Verification Gates" in remote_rollout_report
    assert "does not unlock hosted writes" in remote_rollout_report
    remote_hosting_report = (PROJECT_ROOT / "reports" / "remote_hosting_decision_packet.md").read_text(encoding="utf-8")
    assert "## Hosting Options" in remote_hosting_report
    assert "## Decision Scores" in remote_hosting_report
    assert "## Minimum Requirements" in remote_hosting_report
    assert "## Owner Questions" in remote_hosting_report
    assert "does not choose a provider" in remote_hosting_report
    remote_provider_report = (PROJECT_ROOT / "reports" / "remote_managed_cloud_provider_shortlist.md").read_text(encoding="utf-8")
    assert "## Provider Shortlist" in remote_provider_report
    assert "## Evaluation Criteria" in remote_provider_report
    assert "## Official Sources" in remote_provider_report
    assert "DigitalOcean App Platform" in remote_provider_report
    assert "Railway app" in remote_provider_report
    assert "does not choose a provider" in remote_provider_report
    remote_pricing_report = (PROJECT_ROOT / "reports" / "remote_staging_pricing_preflight.md").read_text(encoding="utf-8")
    assert "## Pricing Components" in remote_pricing_report
    assert "## Estimate Profiles" in remote_pricing_report
    assert "## Preflight Items" in remote_pricing_report
    assert "## Risk Controls" in remote_pricing_report
    assert "$32.15/month baseline" in remote_pricing_report
    assert "does not choose a provider" in remote_pricing_report
    remote_setup_report = (PROJECT_ROOT / "reports" / "remote_staging_setup_runbook.md").read_text(encoding="utf-8")
    assert "## Provider Paths" in remote_setup_report
    assert "## Staging Phases" in remote_setup_report
    assert "## Setup Tasks" in remote_setup_report
    assert "## Environment Variables" in remote_setup_report
    assert "## Verification Gates" in remote_setup_report
    assert "DATABASE_URL" in remote_setup_report
    assert "DOCUMENT_FILE_ACCESS_ENABLED" in remote_setup_report
    assert "does not choose a provider" in remote_setup_report
    remote_deployment_report = (PROJECT_ROOT / "reports" / "remote_staging_deployment_spec.md").read_text(encoding="utf-8")
    assert "## Deployment Targets" in remote_deployment_report
    assert "## App Service Spec" in remote_deployment_report
    assert "## Configuration Variables" in remote_deployment_report
    assert "## Deployment Inputs" in remote_deployment_report
    assert "## Implementation Gaps" in remote_deployment_report
    assert "## Staging Smoke Tests" in remote_deployment_report
    assert "supabase_staging_vercel_signed_file_smoke_passed" in remote_deployment_report
    assert "Supabase CHILLCRM" in remote_deployment_report
    assert "/health or /api/health" in remote_deployment_report
    assert "DOCUMENT_FILE_ACCESS_ENABLED" in remote_deployment_report
    assert "Health and error monitoring" in remote_deployment_report
    assert "partial" in remote_deployment_report
    assert "does not invite admins" in remote_deployment_report
    remote_validation_report = (PROJECT_ROOT / "reports" / "remote_staging_validation_matrix.md").read_text(encoding="utf-8")
    assert "## Expected Counts" in remote_validation_report
    assert "## Validation Sections" in remote_validation_report
    assert "## Validation Checks" in remote_validation_report
    assert "## Blocker Rules" in remote_validation_report
    assert "Restore drill passes" in remote_validation_report
    assert "does not unlock hosted writes" in remote_validation_report
    remote_pilot_report = (PROJECT_ROOT / "reports" / "remote_admin_pilot_onboarding_plan.md").read_text(encoding="utf-8")
    assert "## Shakedown Roles" in remote_pilot_report
    assert "## Prerequisites" in remote_pilot_report
    assert "## Shakedown Workflows" in remote_pilot_report
    assert "## Permission Probes" in remote_pilot_report
    assert "## Signoff Gates" in remote_pilot_report
    assert "owner_only_first_optional_internal_admin_later" in remote_pilot_report
    assert "does not unlock hosted writes" in remote_pilot_report
    remote_cutover_report = (PROJECT_ROOT / "reports" / "remote_production_cutover_checklist.md").read_text(encoding="utf-8")
    assert "## Cutover Phases" in remote_cutover_report
    assert "## Checklist" in remote_cutover_report
    assert "## Rollback Triggers" in remote_cutover_report
    assert "## First-Week Monitoring" in remote_cutover_report
    assert "## Communication Plan" in remote_cutover_report
    assert "## Signoff Gates" in remote_cutover_report
    assert "remote_production_cutover_checklist_ready" in remote_cutover_report
    assert "does not unlock hosted writes" in remote_cutover_report
    local_write_freeze_report = (PROJECT_ROOT / "reports" / "local_write_freeze_readiness.md").read_text(encoding="utf-8")
    assert "Status: local_write_freeze_ready" in local_write_freeze_report
    assert "Production gate: pass" in local_write_freeze_report
    assert "CHILLCRM_LOCAL_WRITE_FREEZE" in local_write_freeze_report
    assert "Backup path remains allowed: yes" in local_write_freeze_report
    assert "does not enable the freeze" in local_write_freeze_report
    assert "local_write_freeze_ready" in local_write_freeze_readiness_script
    assert "CHILLCRM_LOCAL_WRITE_FREEZE" in local_write_freeze_readiness_script
    assert "backup_blocked is False" in local_write_freeze_readiness_script
    assert "not self.hosted_postgres_adapter_enabled()" in server_py
    hosted_db_report = (PROJECT_ROOT / "reports" / "hosted_database_migration_readiness.md").read_text(encoding="utf-8")
    assert "## Type Translation" in hosted_db_report
    assert "managed_postgres_recommended" in hosted_db_report
    assert "## Migration Requirements" in hosted_db_report
    assert "does not create a remote database" in hosted_db_report
    hosted_schema_report = (PROJECT_ROOT / "reports" / "hosted_database_schema_draft.md").read_text(encoding="utf-8")
    hosted_schema_sql = (PROJECT_ROOT / "reports" / "hosted_database_schema_draft.sql").read_text(encoding="utf-8")
    assert "## Source Table DDL" in hosted_schema_report
    assert "## Remote-Only Tables" in hosted_schema_report
    assert "## Validation Queries" in hosted_schema_report
    assert "does not create a remote database" in hosted_schema_report
    assert "CREATE SCHEMA IF NOT EXISTS crm" in hosted_schema_sql
    assert 'CREATE TABLE IF NOT EXISTS crm."people"' in hosted_schema_sql
    assert 'CREATE TABLE IF NOT EXISTS crm."app_users"' in hosted_schema_sql
    assert '"password_hash" text' in hosted_schema_sql
    assert '"password_updated_at" timestamptz' in hosted_schema_sql
    assert 'CREATE TABLE IF NOT EXISTS crm."remote_audit_events"' in hosted_schema_sql
    hosted_load_report = (PROJECT_ROOT / "reports" / "hosted_database_data_load_plan.md").read_text(encoding="utf-8")
    assert "## Load Phases" in hosted_load_report
    assert "## Table Load Order" in hosted_load_report
    assert "## Remote Seed Data" in hosted_load_report
    assert "## Validation Checks" in hosted_load_report
    assert "does not create a remote database" in hosted_load_report
    hosted_adapter_smoke_report = (PROJECT_ROOT / "reports" / "hosted_postgres_adapter_smoke.md").read_text(encoding="utf-8")
    assert "Hosted Postgres Adapter Smoke" in hosted_adapter_smoke_report
    assert "Mode: dry_run" in hosted_adapter_smoke_report or "Mode: hosted_smoke" in hosted_adapter_smoke_report
    assert "Failed: 0" in hosted_adapter_smoke_report
    assert "CHILLCRM_DATABASE_ADAPTER=postgres" in hosted_adapter_smoke_report
    assert "active saved path for previews" in app_js
    assert "backupName" in app_js
    assert "Project decision saved${backupText}" in app_js
    assert "hasProjectDecisionChanges" in app_js
    assert "isProjectDecisionSavable" in app_js
    assert "updateProjectDecisionFormState" in app_js
    assert "updateProjectDecisionBulkResetState" in app_js
    assert "resetProjectDecisionForm" in app_js
    assert "Unsaved changes staged on this card" in app_js
    assert "Staged decision changes reset" in app_js
    assert "All staged decision changes reset" in app_js
    assert "/api/update_tags" in app_js
    assert "saveTagsButton" in app_js
    assert "Task reopened" in app_js
    assert "data-completed" in app_js
    assert "/api/update_task" in app_js
    assert "/api/copy_imported_task_to_local" in app_js
    assert "copy-imported-task-button" in app_js
    assert "copy_imported_task_to_local" in server_py
    assert "/api/archive_item" in app_js
    assert "/api/link_archive_item" in app_js
    assert "archive-detail-button" in app_js
    assert "archiveTargetSearch" in app_js
    assert "archive-target-button" in app_js
    assert "link_archive_item" in server_py
    assert "before_archive_link_" in server_py
    assert "Linked archive item" in server_py
    assert "/api/save_archive_review" in app_js
    assert "archiveReviewStatusFilter" in app_js
    assert "archiveReviewQueuePanel" in app_js
    assert "archive-review-filter-button" in app_js
    assert "Save & Next" in app_js
    assert "saveArchiveReviewNextButton" in app_js
    assert "nextArchiveItemAfterReview" in app_js
    assert "state.archiveLastItems = data.items || []" in app_js
    assert "save_archive_review" in server_py
    assert "archive_review_decisions" in server_py
    assert "Archive item" in server_py and "marked" in server_py
    assert ".archive-target-button" in styles_css
    assert ".archive-review-panel" in styles_css
    assert ".archive-review-actions" in styles_css
    assert "save-task-button" in app_js
    assert "task-edit-content" in app_js
    assert "task-table-textarea" in app_js
    assert "taskSource" in app_js
    assert "taskSourceOptions" in app_js
    assert "Imported from Zendesk" in app_js
    assert "Local only" in app_js
    assert "Follow Up Transition Plan" in app_js
    assert "followupTransitionPanel" in app_js
    assert "followup_imported_open" in app_js
    assert "followup_transition_plan" in server_py
    assert "local_crm_followup_transition_plan.csv" in server_py
    assert "followup-transition-panel" in styles_css
    assert "detailMatchesCurrent" in app_js
    assert "taskSearch" in app_js
    assert "taskRecordType" in app_js
    assert "taskRecordTypeOptions" in app_js
    assert "taskSavedView" in app_js
    assert "taskSavedViewControls" in app_js
    assert "currentTaskSettings" in app_js
    assert "applyTaskSettings" in app_js
    assert "taskSortField" in app_js
    assert "taskSortOptions" in app_js
    assert "type: \"tasks\"" in app_js
    assert "record_type: state.taskRecordType" in app_js
    assert "status: state.taskStatus" in app_js
    assert "/api/update_note" in app_js
    assert "save-note-button" in app_js
    assert "owner_user_id" in app_js
    assert "editOptions(detail" in app_js
    assert "/api/create_options" in app_js
    assert "relationshipDatalist" in app_js
    assert "showDetailFormError" in app_js
    assert "detailFormError" in app_js
    assert "showDetailActionError" in app_js
    assert "detailActionError" in app_js
    assert "runDetailAction" in app_js
    assert "recordSnapshot(detail)" in app_js
    assert "recordSnapshotStatus(detail)" in app_js
    assert "provenance" in app_js
    assert "record_provenance" in server_py
    assert "Imported from Zendesk" in server_py
    assert "Local only" in server_py
    assert "Local Changes" in app_js
    assert "Last Local" in app_js
    assert "record-snapshot" in app_js
    assert "Open Tasks" in app_js
    assert "Review Flags" in app_js
    assert "contactActions(detail)" in app_js
    assert "contact-copy-button" in app_js
    assert "copyTextToClipboard" in app_js
    assert "mailto:" in app_js
    assert "tel:" in app_js
    assert "listDateFilterControls" in app_js
    assert "listDateField" in app_js
    assert "date_field: dateFilter.field" in app_js
    assert "resetCurrentListView" in app_js
    assert "resetListViewButton" in app_js
    assert "Reset View" in app_js
    assert "resetTaskView" in app_js
    assert "resetTaskViewButton" in app_js
    assert "resetActivityView" in app_js
    assert "resetActivityViewButton" in app_js
    assert "resetTagView" in app_js
    assert "resetTagViewButton" in app_js
    assert "resetLinkedResourceView" in app_js
    assert "resetLinkedResourceViewButton" in app_js
    assert "resetArchiveView" in app_js
    assert "resetArchiveViewButton" in app_js
    assert "resetCustomFieldView" in app_js
    assert "resetCustomFieldViewButton" in app_js
    assert "Complete Local CRM Package" in app_js
    assert "/api/export_package" in app_js
    assert "Downloaded Document Files" in app_js
    assert "/api/export_document_files_package" in app_js
    assert "Download Documents" in app_js
    assert "Package Locked" in app_js
    assert "Documents Locked" in app_js
    assert "bulk_package_export_status" in server_py
    assert "send_bulk_package_export_locked" in server_py
    assert "EXPORT_PACKAGE_ENABLED" in server_py
    assert "document_file_access_status" in server_py
    assert "send_document_file_access_locked" in server_py
    assert "DOCUMENT_FILE_ACCESS_ENABLED" in server_py
    assert "formatBytes" in app_js
    assert "package-content-list" in app_js
    assert "export_package" in server_py
    assert "document_file_package_entries" in server_py
    assert "send_document_files_package" in server_py
    assert "export_package_status" in server_py
    assert "Portable export packages ready" in server_py
    assert "project_decision_prep_packet" in server_py
    assert "decision_prep_packet" in server_py
    assert "decision_prep_packet.md" in server_py
    assert "project_decision_ballot" in server_py
    assert "local_crm_project_decision_ballot.csv" in server_py
    assert "project_decision_ballot.md" in server_py
    assert "project_decision_option_matrix" in server_py
    assert "local_crm_project_decision_option_matrix.csv" in server_py
    assert "project_decision_option_matrix.md" in server_py
    assert "design_pipeline" in server_py
    assert "local_crm_design_pipeline.csv" in server_py
    assert "apple_style_redesign_pipeline.md" in server_py
    assert "Open Ballot" in app_js
    assert "Ballot CSV" in app_js
    assert "Option Matrix" in app_js
    assert "Matrix CSV" in app_js
    assert "cleanup_review_starter_packet" in server_py
    assert "cleanup_starter_packet" in server_py
    assert "/api/merge_duplicate_people" in server_py
    assert "/api/merge_duplicate_people" in app_js
    assert "merge_duplicate_people" in server_py
    assert "applyDuplicatePeopleMergeButton" in app_js
    assert "duplicatePeopleMergePanel" in app_js
    assert "wireDuplicatePeopleMerge" in app_js
    assert "Duplicate people are marked inactive, not deleted." in app_js
    assert ".merge-apply-panel" in styles_css
    assert "Decision Prep Packet" in app_js
    assert "decisionPrepPacketPanel" in app_js
    assert "worksheetActionLinks" in app_js
    assert "Cleanup Starter Packet" in app_js
    assert "cleanupStarterPacketPanel" in app_js
    assert "daily_operating_guide" in server_py
    assert "local_crm_daily_operating_guide.csv" in server_py
    assert "archive_review_worklist" in server_py
    assert "local_crm_archive_review_worklist.csv" in server_py
    assert "archive_review_worklist.md" in server_py
    assert "archive_association_audit" in server_py
    assert "local_crm_archive_association_audit.csv" in server_py
    assert "archive_association_audit.md" in server_py
    assert "backup_safety_ledger" in server_py
    assert "local_crm_backup_safety_ledger.csv" in server_py
    assert "backup_safety_ledger.md" in server_py
    assert "backup_safety_ledger.md" in app_js
    assert "/health" in server_py
    assert "health_status" in server_py
    assert "runtime_context" in server_py
    assert "CHILLCRM_AUTH_REQUIRED" in server_py
    assert "AUTH_BOOTSTRAP_ADMIN_EMAIL" in server_py
    assert "/api/auth/login" in server_py
    assert "/api/auth/status" in server_py
    assert "/api/auth/change_password" in server_py
    assert "/api/auth/owner_password_recovery" in server_py
    assert "/api/production_gates" in server_py
    assert "change_current_app_user_password" in server_py
    assert "app_user_password_self_change" in server_py
    assert "owner_password_recovery_enabled" in server_py
    assert "owner_password_recovery_response" in server_py
    assert "Owner password recovery is not currently enabled." in server_py
    assert "owner_password_recovery" in server_py
    assert "authOverlay" in app_js
    assert "initializeAuth" in app_js
    assert "passwordChangeForm" in app_js
    assert "/api/auth/change_password" in app_js
    assert "ownerRecoveryForm" in app_js
    assert "ownerRecoveryOpen" in app_js
    assert "/api/auth/owner_password_recovery" in app_js
    assert "productionGatePanel" in app_js
    assert "Production Gates" in app_js
    assert "Next Owner Action" in app_js
    assert "Next Operator Action" in app_js
    assert "production-next-owner-action" in app_js
    assert "production-next-operator-action" in app_js
    assert "reportLinks" in app_js
    assert "production_gate_status" in server_py
    assert "remote_production_readiness.csv" in server_py
    assert "remaining_production_gates_packet.csv" in server_py
    assert "next_owner_action" in server_py
    assert "next_operator_action" in server_py
    assert "next_production_action" in server_py
    assert "next_owner_gate_action" in server_py
    assert "next_operator_gate_action" in server_py
    assert "next_production_gate_action" in server_py
    assert "is_owner_needed_input" in server_py
    assert "is_operator_needed_input" in server_py
    assert "report_links_for_field" in server_py
    assert "proof_links" in server_py
    assert "source_links" in server_py
    assert "owner_gate_intake_packet.md" in server_py
    assert "owner_gate_reply_validation.md" in server_py
    assert "owner_recovery_closure.md" in server_py
    assert "owner_recovery_disable_run.md" in server_py
    assert "owner_approved_wave_packet.md" in server_py
    assert "secret_handling_boundaries.md" in server_py
    assert "source_of_truth_cutover_preflight.md" in server_py
    assert "source_of_truth_cutover_approval.md" in server_py
    assert "hosted_write_audit_execution.md" in server_py
    assert "hosted_deployment_freshness.md" in server_py
    assert "hosted_redeploy_preflight.md" in server_py
    assert "remaining_gate_execution_readiness.md" in server_py
    assert "local_write_freeze_readiness.md" in server_py
    assert "Owner Intake" in app_js
    assert "auth-control" in styles_css
    assert "auth-change-password" in styles_css
    assert ".production-next-owner-action" in styles_css
    assert ".production-next-action" in styles_css
    assert 'data-view="users"' in index_html
    assert 'id="usersView"' in index_html
    assert 'id="passwordOverlay"' in index_html
    assert 'id="ownerRecoveryOpen"' in index_html
    assert 'id="ownerRecoveryOverlay"' in index_html
    assert "Owner password recovery is available only when the private recovery switch is enabled." in index_html
    assert "owner-only-nav" in index_html
    assert "currentUserCanManageUsers" in app_js
    assert "updateOwnerNavigation" in app_js
    assert "renderUsers" in app_js
    assert "appUserCreateForm" in app_js
    assert "appUserEditForm" in app_js
    assert "/api/app_users/save" in app_js
    assert "/api/app_users/deactivate" in app_js
    assert "/api/app_users/reactivate" in app_js
    assert "/api/app_users/set_password" in app_js
    assert "temporary-password-row" in app_js
    assert ".role-check-grid" in styles_css
    assert ".app-user-notice" in styles_css
    assert "--hosted" in reset_script
    assert "Private operator password recovery completed." in reset_script
    assert "app_user_password_recovery" in reset_script
    assert "Hosted reset requires --database-url or DATABASE_URL." in reset_script
    assert "Backup restore drill" in backup_restore_script
    assert "Supabase provider backup/PITR restore remains a production gate." in backup_restore_script
    assert "database/backups" in supabase_backup_script
    assert "SUPABASE_ACCESS_TOKEN" in supabase_backup_script
    assert "blocked_until_provider_backup_and_restore_evidence_pass" in supabase_backup_script
    assert (PROJECT_ROOT / "reports" / "supabase_backup_readiness.md").exists()
    assert "Remote Monitoring Readiness" in monitoring_readiness_script
    assert "input_required_remote_monitoring" in monitoring_readiness_script
    assert "remote_monitoring_signoff.md" in monitoring_readiness_script
    assert "newest_hosted_smoke_current" in monitoring_readiness_script
    assert "Remote Monitoring Signoff" in monitoring_signoff_script
    assert "pending_owner_monitoring_signoff" in monitoring_signoff_script
    assert "--approve-owner" in monitoring_signoff_script
    assert "Owner Shakedown Signoff" in owner_shakedown_signoff_script
    assert "pending_owner_shakedown" in owner_shakedown_signoff_script
    assert "--approve" in owner_shakedown_signoff_script
    assert "pending_prerequisites_before_owner_shakedown" in owner_shakedown_signoff_script
    assert "prerequisite_checks" in owner_shakedown_signoff_script
    assert "hosted_deployment_freshness" in owner_shakedown_signoff_script
    assert "provider_backup_and_restore_evidence_passed" in owner_shakedown_signoff_script
    assert "hosted_write_unlock_audit_rehearsal_passed" in owner_shakedown_signoff_script
    assert "hosted_write_audit_execution_reconciled_after_current_smoke" in owner_shakedown_signoff_script
    assert "remote_monitoring_ready" in owner_shakedown_signoff_script
    assert "Source Of Truth Cutover Approval" in source_cutover_approval_script
    assert "pending_owner_cutover_approval" in source_cutover_approval_script
    assert "pending_prerequisites_before_source_of_truth_cutover" in source_cutover_approval_script
    assert "--approve-cutover" in source_cutover_approval_script
    assert "other_blocking_gates" in source_cutover_approval_script
    assert "SELF_GATE_KEY" in source_cutover_approval_script
    assert "source_of_truth_changed" in source_cutover_approval_script
    assert "Hosted Write-Unlock Audit Rehearsal" in write_audit_rehearsal_script
    assert "pending_owner_approval" in write_audit_rehearsal_script
    assert "hosted_write_unlock_audit_rehearsal_passed" in write_audit_rehearsal_script
    assert "Preflight Checks" in write_audit_rehearsal_script
    assert "execution_evidence_incomplete" in write_audit_rehearsal_script
    assert "--execution-evidence" in write_audit_rehearsal_script
    assert "--write-lock-restored" in write_audit_rehearsal_script
    assert "newest_hosted_smoke_current" in write_audit_rehearsal_script
    assert "locked_staging_runtime" in write_audit_rehearsal_script
    assert 'return 1 if args.mark_passed' in write_audit_rehearsal_script
    assert "Hosted Write-Audit Rehearsal Execution" in write_audit_execution_script
    assert "--owner-approved" in write_audit_execution_script
    assert "--execute" in write_audit_execution_script
    assert "--prompt-secrets" in write_audit_execution_script
    assert "REMOTE_WRITE_LOCK" in write_audit_execution_script
    assert "CHILLCRM_VERCEL_INLINE_FILES" in write_audit_execution_script
    assert "remote_write_lock_enabled" in write_audit_execution_script
    assert "create_edit_records" in write_audit_execution_script
    assert "x-vercel-protection-bypass" in write_audit_execution_script
    assert "mark_rehearsal_passed" in write_audit_execution_script
    assert "Not marked passed because" in write_audit_execution_script
    assert "hosted_write_audit_execution.md" in write_audit_execution_script
    assert "Remaining Production Gates Packet" in remaining_gates_packet_script
    assert "Vercel bypass is not required for https://chillcrm.app." in remaining_gates_packet_script
    assert "SUPABASE_ACCESS_TOKEN=<supabase-management-token>" in remaining_gates_packet_script
    assert "owner-confirmed Dashboard evidence" in remaining_gates_packet_script
    assert "Redeploy current local runtime" in remaining_gates_packet_script
    assert "verify_hosted_redeploy_preflight.py" in remaining_gates_packet_script
    assert "hosted_redeploy_preflight.md" in remaining_gates_packet_script
    assert "verify_hosted_deployment_freshness.py" in remaining_gates_packet_script
    assert "hosted_deployment_freshness.md" in remaining_gates_packet_script
    assert "remaining_gate_guardrails.md" in remaining_gates_packet_script
    assert "private_execution_inputs.md" in remaining_gates_packet_script
    assert "owner_confirmed_production_wave.md" in remaining_gates_packet_script
    assert "run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets" in remaining_gates_packet_script
    assert "owner_gate_intake_packet.md" in remaining_gates_packet_script
    assert "owner_gate_reply_validation.md" in remaining_gates_packet_script
    assert "owner_approved_wave_packet.md" in remaining_gates_packet_script
    assert "Reload current local audit/data changes to Supabase staging" in remaining_gates_packet_script
    assert "run_supabase_staging_refresh.py" in remaining_gates_packet_script
    assert "supabase_staging_refresh_run.md" in remaining_gates_packet_script
    assert "verify_supabase_staging_refresh_preflight.py" in remaining_gates_packet_script
    assert "supabase_staging_refresh_preflight.md" in remaining_gates_packet_script
    assert "verify_supabase_staging_data_parity.py" in remaining_gates_packet_script
    assert "supabase_staging_data_parity.md" in remaining_gates_packet_script
    assert "run_supabase_staging_refresh.py --execute --prompt-secrets" in remaining_gates_packet_script
    assert "owner_recovery_closure.md" in remaining_gates_packet_script
    assert "Disable temporary owner recovery" in remaining_gates_packet_script
    assert "Execute hosted write-audit rehearsal" in remaining_gates_packet_script
    assert "execute_hosted_write_audit_rehearsal.py" in remaining_gates_packet_script
    assert "hosted_write_audit_execution.md" in remaining_gates_packet_script
    assert "record_owner_shakedown_signoff.py" in remaining_gates_packet_script
    assert "verify_source_of_truth_cutover_preflight.py" in remaining_gates_packet_script
    assert "source_of_truth_cutover_preflight.md" in remaining_gates_packet_script
    assert "record_source_of_truth_cutover_approval.py" in remaining_gates_packet_script
    assert "Record final source-of-truth cutover approval" in remaining_gates_packet_script
    assert "Owner Approved Wave Packet" in owner_approved_wave_packet_script
    assert "owner_approved_wave_ready_for_confirmation" in owner_approved_wave_packet_script
    assert "Set Owner Password" in owner_approved_wave_packet_script
    assert "I'm in, disable recovery" in owner_approved_wave_packet_script
    assert "disable_owner_recovery_after_access.py --owner-confirmed-access --prompt-secrets" in owner_approved_wave_packet_script
    assert "run_newest_hosted_smoke_with_vercel_bypass.py" in owner_approved_wave_packet_script
    assert "Refresh Supabase staging data parity" in owner_approved_wave_packet_script
    assert "run_supabase_staging_refresh.py" in owner_approved_wave_packet_script
    assert "supabase_staging_refresh_run.md" in owner_approved_wave_packet_script
    assert "verify_supabase_staging_refresh_preflight.py" in owner_approved_wave_packet_script
    assert "supabase_staging_data_parity.md" in owner_approved_wave_packet_script
    assert "local_write_freeze_readiness.md" in owner_approved_wave_packet_script
    assert "private_execution_inputs.md" in owner_approved_wave_packet_script
    assert "owner_confirmed_production_wave.md" in owner_approved_wave_packet_script
    assert "verify_source_of_truth_cutover_preflight.py" in owner_approved_wave_packet_script
    assert "source_of_truth_cutover_preflight.md" in owner_approved_wave_packet_script
    assert "record_source_of_truth_cutover_approval.py" in owner_approved_wave_packet_script
    assert "yes_when_later_explicitly_approved_for_probe_only" in owner_approved_wave_packet_script
    assert "Owner Production Gate Intake Packet" in owner_gate_intake_packet_script
    assert "Owner Access Restoration" in owner_gate_intake_packet_script
    assert "Set Owner Password" in owner_gate_intake_packet_script
    assert "Safe Reply Template" in owner_gate_intake_packet_script
    assert "owner_gate_intake_packet.csv" in owner_gate_intake_packet_script
    assert "owner_gate_reply_validation.md" in owner_gate_intake_packet_script
    assert "Owner recovery closure" in owner_gate_intake_packet_script
    assert "owner_recovery_closure.md" in owner_gate_intake_packet_script
    assert "hosted_deployment_freshness.md" in owner_gate_intake_packet_script
    assert "source_of_truth_cutover_approval.md" in owner_gate_intake_packet_script
    assert "Owner Gate Reply Validation" in owner_gate_reply_validation_script
    assert "owner_gate_reply_rejected_secret_like_value" in owner_gate_reply_validation_script
    assert "input_required_owner_gate_reply" in owner_gate_reply_validation_script
    assert "SECRET_PATTERNS" in owner_gate_reply_validation_script
    assert "--reply-file" in owner_gate_reply_validation_script
    assert "--stdin" in owner_gate_reply_validation_script
    assert "recordable_actions" in owner_gate_reply_validation_script
    assert "This validator turns owner facts into candidate commands only" in owner_gate_reply_validation_script
    assert "Owner Recovery Closure" in owner_recovery_closure_script
    assert "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED=false" in owner_recovery_closure_script
    assert "Disable hosted owner recovery after the owner confirms access is restored." in owner_recovery_disable_script
    assert "--owner-confirmed-access" in owner_recovery_disable_script
    assert "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED" in owner_recovery_disable_script
    assert "CHILLCRM_VERCEL_INLINE_FILES" in owner_recovery_disable_script
    assert "run_newest_hosted_smoke_with_vercel_bypass.py" in owner_recovery_disable_script
    assert "verify_hosted_deployment_freshness.py" in owner_recovery_disable_script
    assert "hosted_deployment_freshness" in owner_recovery_disable_script
    assert "deployment_freshness_checked" in owner_recovery_disable_script
    assert "Supabase Backup Evidence Packet" in supabase_backup_evidence_packet_script
    assert "dashboard-backup-visible" in supabase_backup_script
    assert "restore-proof-type" in supabase_backup_script
    assert "use-current-local-rollback-package" in supabase_backup_script
    assert "current_local_rollback_package_detail" in supabase_backup_script
    assert "Hosted Deployment Freshness" in deployment_freshness_script
    assert "input_required_redeploy_current_local_runtime" in deployment_freshness_script
    assert "blocked_until_current_local_runtime_deployed" in deployment_freshness_script
    assert "DEPLOYED_RUNTIME_PATHS" in deployment_freshness_script
    assert "crm_app" in deployment_freshness_script
    assert "provider_calls" in deployment_freshness_script
    assert "Hosted Redeploy Preflight" in hosted_redeploy_preflight_script
    assert "hosted_redeploy_preflight_ready" in hosted_redeploy_preflight_script
    assert "verify_hosted_app_deployment_package.py" in hosted_redeploy_preflight_script
    assert "verify_hosted_deployment_freshness.py" in hosted_redeploy_preflight_script
    assert "deploy_script_secret_safe_mode" in hosted_redeploy_preflight_script
    assert "operator_packet_has_redeploy_sequence" in hosted_redeploy_preflight_script
    assert "CHILLCRM_SKIP_ENV_UPSERT=1" in hosted_redeploy_preflight_script
    assert "CHILLCRM_VERCEL_INLINE_FILES=1" in hosted_redeploy_preflight_script
    assert "Supabase Staging Refresh Preflight" in supabase_staging_refresh_preflight_script
    assert "supabase_staging_refresh_preflight_ready" in supabase_staging_refresh_preflight_script
    assert "verify_supabase_staging_data_parity.py" in supabase_staging_refresh_preflight_script or "supabase_staging_data_parity.csv" in supabase_staging_refresh_preflight_script
    assert "migrate_chillcrm_to_supabase.py" in supabase_staging_refresh_preflight_script
    assert "CHILLCRM_DATABASE_URL=<supabase-database-url>" in supabase_staging_refresh_preflight_script
    assert "secret_values_stored" in supabase_staging_refresh_preflight_script
    assert "provider_calls" in supabase_staging_refresh_preflight_script
    assert "stale_table_detail" in supabase_staging_refresh_preflight_script
    assert "Supabase Staging Refresh Run" in supabase_staging_refresh_run_script
    assert "input_required_supabase_staging_refresh_execution" in supabase_staging_refresh_run_script
    assert "--execute" in supabase_staging_refresh_run_script
    assert "--prompt-secrets" in supabase_staging_refresh_run_script
    assert "getpass.getpass" in supabase_staging_refresh_run_script
    assert "migrate_chillcrm_to_supabase.py" in supabase_staging_refresh_run_script
    assert "verify_supabase_staging_data_parity.py" in supabase_staging_refresh_run_script
    assert "verify_remote_production_readiness.py" in supabase_staging_refresh_run_script
    assert "secret_values_stored" in supabase_staging_refresh_run_script
    assert "database_url" in supabase_staging_refresh_run_script
    assert "Supabase Staging Data Parity" in supabase_staging_data_parity_script
    assert "input_required_supabase_staging_refresh" in supabase_staging_data_parity_script
    assert "blocked_until_current_local_data_reloaded_to_supabase" in supabase_staging_data_parity_script
    assert "chillcrm_supabase_staging_validation.csv" in supabase_staging_data_parity_script
    assert "hosted_postgres_adapter_smoke.md" in supabase_staging_data_parity_script
    assert "chillcrm_supabase_storage_migration.md" in supabase_staging_data_parity_script
    assert "provider_calls" in supabase_staging_data_parity_script
    assert "Remaining Gate Guardrails" in remaining_gate_guardrails_script
    assert "remaining_gate_guardrails_passed" in remaining_gate_guardrails_script
    assert "owner_recovery_requires_owner_access_confirmation" in remaining_gate_guardrails_script
    assert "write_audit_requires_owner_approval_and_execute" in remaining_gate_guardrails_script
    assert "write_audit_restores_remote_write_lock" in remaining_gate_guardrails_script
    assert "supabase_backup_accepts_token_or_dashboard_evidence_only" in remaining_gate_guardrails_script
    assert "source_of_truth_cutover_is_final_and_separate" in remaining_gate_guardrails_script
    assert "provider_calls" in remaining_gate_guardrails_script
    assert "Remaining Gate Execution Readiness" in remaining_gate_execution_readiness_script
    assert "remaining_gate_execution_ready" in remaining_gate_execution_readiness_script
    assert "BLOCKER_TO_INPUT" in remaining_gate_execution_readiness_script
    assert "EXPECTED_INPUTS" in remaining_gate_execution_readiness_script
    assert 'row.get("key") != "remaining_gate_execution_readiness"' in remaining_gate_execution_readiness_script
    assert "safe_commands_cover_all_execution_phases" in remaining_gate_execution_readiness_script
    assert "source_of_truth_cutover_remains_final" in remaining_gate_execution_readiness_script
    assert "write_audit_execution_guarded" in remaining_gate_execution_readiness_script
    assert "secret_inputs_have_private_handling" in remaining_gate_execution_readiness_script
    assert (PROJECT_ROOT / "reports" / "remaining_gate_execution_readiness.md").exists()
    remaining_gate_execution_readiness_report = (PROJECT_ROOT / "reports" / "remaining_gate_execution_readiness.md").read_text(encoding="utf-8")
    assert "Remaining Gate Execution Readiness" in remaining_gate_execution_readiness_report
    assert "Status: remaining_gate_execution_ready" in remaining_gate_execution_readiness_report
    assert "Production gate: pass" in remaining_gate_execution_readiness_report
    assert "Checks failed: 0" in remaining_gate_execution_readiness_report
    assert "Blocking gates covered: 9" in remaining_gate_execution_readiness_report
    assert "Remaining inputs covered: 9" in remaining_gate_execution_readiness_report
    assert "safe_commands_cover_all_execution_phases" in remaining_gate_execution_readiness_report
    assert "Local Write Freeze Readiness" in local_write_freeze_readiness_script
    assert "local_write_freeze_ready" in local_write_freeze_readiness_script
    assert "CHILLCRM_LOCAL_WRITE_FREEZE" in local_write_freeze_readiness_script
    assert "Backup path remains allowed" in local_write_freeze_readiness_script
    assert "Private Execution Inputs" in private_execution_inputs_script
    assert "private_execution_inputs_mapped" in private_execution_inputs_script
    assert "Secret values stored: no" in private_execution_inputs_script
    assert "VERCEL_TOKEN" in private_execution_inputs_script
    assert "AUTH_BOOTSTRAP_ADMIN_PASSWORD" in private_execution_inputs_script
    assert "CHILLCRM_OWNER_RECOVERY_PASSWORD" in private_execution_inputs_script
    assert "CHILLCRM_DATABASE_URL" in private_execution_inputs_script
    assert "CHILLCRM_VERCEL_DATABASE_URL" in private_execution_inputs_script
    assert "VERCEL_PROTECTION_BYPASS_SECRET" in private_execution_inputs_script
    assert "SUPABASE_ACCESS_TOKEN" in private_execution_inputs_script
    assert "dashboard evidence path remains available" in private_execution_inputs_script
    assert "Secret env values present" in private_execution_inputs_script
    assert "Owner-Confirmed Production Wave Runner" in owner_confirmed_wave_script
    assert "--owner-confirmed-access" in owner_confirmed_wave_script
    assert "--execute-owner-recovery-wave" in owner_confirmed_wave_script
    assert "--execute-supabase-staging-refresh" in owner_confirmed_wave_script
    assert "--verify-supabase-backup-api" in owner_confirmed_wave_script
    assert "getpass.getpass" in owner_confirmed_wave_script
    assert "disable_owner_recovery_after_access.py" in owner_confirmed_wave_script
    assert "run_supabase_staging_refresh.py" in owner_confirmed_wave_script
    assert "verify_supabase_backup_readiness.py" in owner_confirmed_wave_script
    assert "This runner does not approve or execute the hosted write-audit rehearsal" in owner_confirmed_wave_script
    assert "source_of_truth_changed" in owner_confirmed_wave_script
    assert "remote_write_lock_changed" in owner_confirmed_wave_script
    assert "Source-Of-Truth Cutover Preflight" in source_cutover_preflight_script
    assert "source_of_truth_cutover_preflight_guarded" in source_cutover_preflight_script
    assert "open_gates_before_final_cutover" in source_cutover_preflight_script
    assert "approval_script_guarded" in source_cutover_preflight_script
    assert "operator_packet_has_final_command_shape" in source_cutover_preflight_script
    assert "owner_shakedown_blocks_cutover_until_signed" in source_cutover_preflight_script
    assert "source_of_truth_changed" in source_cutover_preflight_script
    assert "remote_write_lock_changed" in source_cutover_preflight_script
    assert "Secret-Handling Boundaries" in secret_handling_boundaries_script
    assert "secret_handling_boundaries_passed" in secret_handling_boundaries_script
    assert "curated_source_report_secret_scan" in secret_handling_boundaries_script
    assert "raw_api_exports" in secret_handling_boundaries_script
    assert "getpass.getpass" in secret_handling_boundaries_script
    assert "Secret values stored: no" in secret_handling_boundaries_script
    assert "safe_runner_private_prompts" in secret_handling_boundaries_script
    assert "supabase_refresh_private_database_url" in secret_handling_boundaries_script
    assert "owner_recovery_disable_private_prompts" in secret_handling_boundaries_script
    assert "write_audit_owner_approved_private_execution" in secret_handling_boundaries_script
    assert "private_execution_inputs_no_secret_storage" in secret_handling_boundaries_script
    assert "private_execution_inputs_report_no_secrets" in secret_handling_boundaries_script
    assert "owner_confirmed_wave_private_prompts" in secret_handling_boundaries_script
    assert "owner_confirmed_wave_report_no_secrets" in secret_handling_boundaries_script
    assert "source_of_truth_cutover_preflight_no_secret_storage" in secret_handling_boundaries_script
    assert "source_of_truth_cutover_preflight_report_no_secrets" in secret_handling_boundaries_script
    assert (PROJECT_ROOT / "reports" / "private_execution_inputs.md").exists()
    private_execution_inputs_report = (PROJECT_ROOT / "reports" / "private_execution_inputs.md").read_text(encoding="utf-8")
    assert "Private Execution Inputs" in private_execution_inputs_report
    assert "Status: private_execution_inputs_mapped" in private_execution_inputs_report
    assert "Production gate: pass" in private_execution_inputs_report
    assert "Secret values stored: no" in private_execution_inputs_report
    assert "Provider calls: no" in private_execution_inputs_report
    assert "CRM record writes: no" in private_execution_inputs_report
    assert "Remote write lock changed: no" in private_execution_inputs_report
    assert "Source of truth changed: no" in private_execution_inputs_report
    assert "`VERCEL_TOKEN`" in private_execution_inputs_report
    assert "`AUTH_BOOTSTRAP_ADMIN_PASSWORD`" in private_execution_inputs_report
    assert "`CHILLCRM_OWNER_RECOVERY_PASSWORD`" in private_execution_inputs_report
    assert "`CHILLCRM_DATABASE_URL`" in private_execution_inputs_report
    assert "`CHILLCRM_VERCEL_DATABASE_URL`" in private_execution_inputs_report
    assert "`VERCEL_PROTECTION_BYPASS_SECRET`" in private_execution_inputs_report
    assert "`SUPABASE_ACCESS_TOKEN`" in private_execution_inputs_report
    assert (PROJECT_ROOT / "reports" / "owner_confirmed_production_wave.md").exists()
    owner_confirmed_wave_report = (PROJECT_ROOT / "reports" / "owner_confirmed_production_wave.md").read_text(encoding="utf-8")
    assert "Owner-Confirmed Production Wave Runner" in owner_confirmed_wave_report
    assert "Status: owner_confirmed_wave_plan_ready" in owner_confirmed_wave_report
    assert "Production gate: pass" in owner_confirmed_wave_report
    assert "Owner recovery wave requested: no" in owner_confirmed_wave_report
    assert "Supabase staging refresh requested: no" in owner_confirmed_wave_report
    assert "Provider calls: no" in owner_confirmed_wave_report
    assert "Remote write lock changed: no" in owner_confirmed_wave_report
    assert "Source of truth changed: no" in owner_confirmed_wave_report
    assert "Secret values stored: no" in owner_confirmed_wave_report
    assert "run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets" in owner_confirmed_wave_report
    assert (PROJECT_ROOT / "reports" / "source_of_truth_cutover_preflight.md").exists()
    source_cutover_preflight_report = (PROJECT_ROOT / "reports" / "source_of_truth_cutover_preflight.md").read_text(encoding="utf-8")
    assert "Source-Of-Truth Cutover Preflight" in source_cutover_preflight_report
    assert "Status: source_of_truth_cutover_preflight_guarded" in source_cutover_preflight_report
    assert "Preflight gate: pass" in source_cutover_preflight_report
    assert "Cutover ready: no" in source_cutover_preflight_report
    assert "open_gates_before_final_cutover" in source_cutover_preflight_report
    assert "approval_script_guarded" in source_cutover_preflight_report
    assert "operator_packet_has_final_command_shape" in source_cutover_preflight_report
    assert "Remote write lock changed: no" in source_cutover_preflight_report
    assert "Source of truth changed: no" in source_cutover_preflight_report
    assert "Secret values stored: no" in source_cutover_preflight_report
    assert (PROJECT_ROOT / "reports" / "secret_handling_boundaries.md").exists()
    secret_handling_boundaries_report = (PROJECT_ROOT / "reports" / "secret_handling_boundaries.md").read_text(encoding="utf-8")
    assert "Secret-Handling Boundaries" in secret_handling_boundaries_report
    assert "Status: secret_handling_boundaries_passed" in secret_handling_boundaries_report
    assert "Production gate: pass" in secret_handling_boundaries_report
    assert "Findings: 0" in secret_handling_boundaries_report
    assert "Failed checks: 0" in secret_handling_boundaries_report
    assert "Secret values stored: no" in secret_handling_boundaries_report
    assert "reports/supabase_staging_refresh_run.md" in secret_handling_boundaries_report
    assert (PROJECT_ROOT / "reports" / "supabase_backup_evidence_packet.md").exists()
    backup_evidence_packet_report = (PROJECT_ROOT / "reports" / "supabase_backup_evidence_packet.md").read_text(encoding="utf-8")
    assert "Supabase Backup Evidence Packet" in backup_evidence_packet_report
    assert "Secret values required for this packet: no" in backup_evidence_packet_report
    assert "Dashboard Checklist" in backup_evidence_packet_report
    assert (PROJECT_ROOT / "reports" / "owner_gate_intake_packet.md").exists()
    owner_gate_intake_packet_report = (PROJECT_ROOT / "reports" / "owner_gate_intake_packet.md").read_text(encoding="utf-8")
    assert "Owner Production Gate Intake Packet" in owner_gate_intake_packet_report
    assert "Owner Access Restoration" in owner_gate_intake_packet_report
    assert "Set Owner Password" in owner_gate_intake_packet_report
    assert "choose a private owner password" in owner_gate_intake_packet_report
    assert "Safe Reply Template" in owner_gate_intake_packet_report
    assert "Secret values required for this packet: no" in owner_gate_intake_packet_report
    assert "Write-audit rehearsal approval" in owner_gate_intake_packet_report
    assert "Owner recovery closure" in owner_gate_intake_packet_report
    assert "owner_gate_reply_validation.md" in owner_gate_intake_packet_report
    assert (PROJECT_ROOT / "reports" / "owner_gate_reply_validation.md").exists()
    owner_gate_reply_validation_report = (PROJECT_ROOT / "reports" / "owner_gate_reply_validation.md").read_text(encoding="utf-8")
    assert "Owner Gate Reply Validation" in owner_gate_reply_validation_report
    assert "Status: input_required_owner_gate_reply" in owner_gate_reply_validation_report
    assert "Reply supplied: no" in owner_gate_reply_validation_report
    assert "Fields supplied: 0/8" in owner_gate_reply_validation_report
    assert "Secret-like findings: 0" in owner_gate_reply_validation_report
    assert "Secret values stored: no" in owner_gate_reply_validation_report
    assert "Use `--reply-file <path>` or `--stdin`" in owner_gate_reply_validation_report
    assert (PROJECT_ROOT / "reports" / "owner_recovery_closure.md").exists()
    owner_recovery_closure_report = (PROJECT_ROOT / "reports" / "owner_recovery_closure.md").read_text(encoding="utf-8")
    assert "Owner Recovery Closure" in owner_recovery_closure_report
    assert "Secret values stored: no" in owner_recovery_closure_report
    assert "CRM record writes: no" in owner_recovery_closure_report
    assert (PROJECT_ROOT / "reports" / "owner_recovery_disable_run.md").exists()
    owner_recovery_disable_report = (PROJECT_ROOT / "reports" / "owner_recovery_disable_run.md").read_text(encoding="utf-8")
    assert "Owner Recovery Disable Run" in owner_recovery_disable_report
    assert "Secret values stored: no" in owner_recovery_disable_report
    assert "CRM record writes: no" in owner_recovery_disable_report
    assert "Deployment freshness checked:" in owner_recovery_disable_report
    assert (PROJECT_ROOT / "reports" / "owner_approved_wave_packet.md").exists()
    owner_approved_wave_packet_report = (PROJECT_ROOT / "reports" / "owner_approved_wave_packet.md").read_text(encoding="utf-8")
    assert "Owner Approved Wave Packet" in owner_approved_wave_packet_report
    assert (
        "Status: owner_approved_wave_ready_for_confirmation" in owner_approved_wave_packet_report
        or "Status: owner_approved_wave_attention_required" in owner_approved_wave_packet_report
    )
    assert "Owner reply required: `I'm in, disable recovery`" in owner_approved_wave_packet_report
    assert "Set Owner Password" in owner_approved_wave_packet_report
    assert "choose a private owner password" in owner_approved_wave_packet_report
    assert "Secret values required for this packet: no" in owner_approved_wave_packet_report
    assert "Provider calls: no" in owner_approved_wave_packet_report
    assert "CRM record writes: no" in owner_approved_wave_packet_report
    assert "Disable temporary owner recovery" in owner_approved_wave_packet_report
    assert "Redeploy current hosted runtime" in owner_approved_wave_packet_report
    assert "private_execution_inputs.md" in owner_approved_wave_packet_report
    assert "owner_confirmed_production_wave.md" in owner_approved_wave_packet_report
    assert "source_of_truth_cutover_preflight.md" in owner_approved_wave_packet_report
    assert (PROJECT_ROOT / "reports" / "remote_monitoring_readiness.md").exists()
    remote_monitoring_readiness_report = (PROJECT_ROOT / "reports" / "remote_monitoring_readiness.md").read_text(encoding="utf-8")
    assert "Remote Monitoring Readiness" in remote_monitoring_readiness_report
    assert "Production gate:" in remote_monitoring_readiness_report
    assert "Blocking Monitoring Inputs" in remote_monitoring_readiness_report
    assert "public_protection_health_probe" in remote_monitoring_readiness_report
    assert "provider_log_error_monitoring_owner" in remote_monitoring_readiness_report
    assert (PROJECT_ROOT / "reports" / "hosted_deployment_freshness.md").exists()
    deployment_freshness_report = (PROJECT_ROOT / "reports" / "hosted_deployment_freshness.md").read_text(encoding="utf-8")
    assert "Hosted Deployment Freshness" in deployment_freshness_report
    assert "Secret values stored: no" in deployment_freshness_report
    assert "Provider calls: no" in deployment_freshness_report
    assert "Source of truth changed: no" in deployment_freshness_report
    assert (PROJECT_ROOT / "reports" / "hosted_redeploy_preflight.md").exists()
    hosted_redeploy_preflight_report = (PROJECT_ROOT / "reports" / "hosted_redeploy_preflight.md").read_text(encoding="utf-8")
    assert "Hosted Redeploy Preflight" in hosted_redeploy_preflight_report
    assert (
        "Status: hosted_redeploy_preflight_ready" in hosted_redeploy_preflight_report
        or "Status: hosted_redeploy_not_required" in hosted_redeploy_preflight_report
    )
    assert "Preflight gate: pass" in hosted_redeploy_preflight_report
    assert "Redeploy required:" in hosted_redeploy_preflight_report
    assert "Provider calls: no" in hosted_redeploy_preflight_report
    assert "deploy_script_secret_safe_mode" in hosted_redeploy_preflight_report
    assert (PROJECT_ROOT / "reports" / "supabase_staging_refresh_preflight.md").exists()
    supabase_staging_refresh_preflight_report = (PROJECT_ROOT / "reports" / "supabase_staging_refresh_preflight.md").read_text(encoding="utf-8")
    assert "Supabase Staging Refresh Preflight" in supabase_staging_refresh_preflight_report
    assert "Status: supabase_staging_refresh_preflight_ready" in supabase_staging_refresh_preflight_report
    assert "Preflight gate: pass" in supabase_staging_refresh_preflight_report
    assert "Refresh required:" in supabase_staging_refresh_preflight_report
    assert "Stale table detail:" in supabase_staging_refresh_preflight_report
    assert "Passed: 10" in supabase_staging_refresh_preflight_report
    assert "Failed: 0" in supabase_staging_refresh_preflight_report
    assert "Provider calls: no" in supabase_staging_refresh_preflight_report
    assert "Secret values stored: no" in supabase_staging_refresh_preflight_report
    assert (PROJECT_ROOT / "reports" / "supabase_staging_refresh_run.md").exists()
    supabase_staging_refresh_run_report = (PROJECT_ROOT / "reports" / "supabase_staging_refresh_run.md").read_text(encoding="utf-8")
    assert "Supabase Staging Refresh Run" in supabase_staging_refresh_run_report
    assert (
        "Status: input_required_supabase_staging_refresh_execution" in supabase_staging_refresh_run_report
        or "Status: supabase_staging_refresh_current" in supabase_staging_refresh_run_report
    )
    assert "Production gate:" in supabase_staging_refresh_run_report
    assert "Execution requested: no" in supabase_staging_refresh_run_report
    assert "Database URL source: not_requested" in supabase_staging_refresh_run_report
    assert "Provider calls: no" in supabase_staging_refresh_run_report
    assert "Secret values stored: no" in supabase_staging_refresh_run_report
    assert "run_supabase_staging_refresh.py --execute --prompt-secrets" in supabase_staging_refresh_run_report
    assert (PROJECT_ROOT / "reports" / "supabase_staging_data_parity.md").exists()
    supabase_staging_data_parity_report = (PROJECT_ROOT / "reports" / "supabase_staging_data_parity.md").read_text(encoding="utf-8")
    assert "Supabase Staging Data Parity" in supabase_staging_data_parity_report
    assert (
        "Status: input_required_supabase_staging_refresh" in supabase_staging_data_parity_report
        or "Status: supabase_staging_data_parity_passed" in supabase_staging_data_parity_report
    )
    assert "Production gate:" in supabase_staging_data_parity_report
    assert "Table failures:" in supabase_staging_data_parity_report
    assert "Checks failed: 0" in supabase_staging_data_parity_report
    assert "Total remote rows checked:" in supabase_staging_data_parity_report
    assert "Provider calls: no" in supabase_staging_data_parity_report
    assert "CRM record writes: no" in supabase_staging_data_parity_report
    assert (PROJECT_ROOT / "reports" / "remaining_gate_guardrails.md").exists()
    remaining_gate_guardrails_report = (PROJECT_ROOT / "reports" / "remaining_gate_guardrails.md").read_text(encoding="utf-8")
    assert "Remaining Gate Guardrails" in remaining_gate_guardrails_report
    assert "Status: remaining_gate_guardrails_passed" in remaining_gate_guardrails_report
    assert "Guardrails checked: 11" in remaining_gate_guardrails_report
    assert "Provider calls: no" in remaining_gate_guardrails_report
    assert "write_audit_restores_remote_write_lock" in remaining_gate_guardrails_report
    assert (PROJECT_ROOT / "reports" / "remote_monitoring_signoff.md").exists()
    assert (PROJECT_ROOT / "reports" / "owner_shakedown_signoff.md").exists()
    assert (PROJECT_ROOT / "reports" / "source_of_truth_cutover_approval.md").exists()
    assert (PROJECT_ROOT / "reports" / "hosted_write_unlock_audit_rehearsal.md").exists()
    assert (PROJECT_ROOT / "reports" / "hosted_write_audit_execution.md").exists()
    remote_monitoring_signoff_report = (PROJECT_ROOT / "reports" / "remote_monitoring_signoff.md").read_text(encoding="utf-8")
    owner_shakedown_signoff_report = (PROJECT_ROOT / "reports" / "owner_shakedown_signoff.md").read_text(encoding="utf-8")
    source_cutover_approval_report = (PROJECT_ROOT / "reports" / "source_of_truth_cutover_approval.md").read_text(encoding="utf-8")
    write_audit_rehearsal_report = (PROJECT_ROOT / "reports" / "hosted_write_unlock_audit_rehearsal.md").read_text(encoding="utf-8")
    write_audit_execution_report = (PROJECT_ROOT / "reports" / "hosted_write_audit_execution.md").read_text(encoding="utf-8")
    assert any(
        f"Status: {status}" in remote_monitoring_signoff_report
        for status in ["pending_owner_monitoring_signoff", "remote_monitoring_signoff_approved"]
    )
    assert any(
        f"Monitoring owner: {status}" in remote_monitoring_signoff_report
        for status in ["pending", "approved"]
    )
    assert any(
        f"Status: {status}" in owner_shakedown_signoff_report
        for status in ["pending_owner_shakedown", "owner_shakedown_signed_off"]
    )
    assert any(
        f"Prerequisites passed: {status}" in owner_shakedown_signoff_report
        for status in ["no", "yes"]
    )
    assert "supabase_backup_pitr_proof" in owner_shakedown_signoff_report
    assert "hosted_write_audit_rehearsal" in owner_shakedown_signoff_report
    assert "remote_monitoring_readiness" in owner_shakedown_signoff_report
    assert any(
        f"Owner shakedown signoff: {status}" in owner_shakedown_signoff_report
        for status in ["pending", "approved"]
    )
    assert "Source Of Truth Cutover Approval" in source_cutover_approval_report
    assert any(
        f"Status: {status}" in source_cutover_approval_report
        for status in ["pending_owner_cutover_approval", "source_of_truth_cutover_approved"]
    )
    assert any(
        f"Other production gates passed: {status}" in source_cutover_approval_report
        for status in ["no", "yes"]
    )
    assert any(
        f"Owner cutover approval: {status}" in source_cutover_approval_report
        for status in ["pending", "approved"]
    )
    assert "Source of truth changed by this script: no" in source_cutover_approval_report
    assert "Hosted Write-Unlock Audit Rehearsal" in write_audit_rehearsal_report
    assert any(
        f"Status: {status}" in write_audit_rehearsal_report
        for status in [
            "pending_owner_approval",
            "approved_not_executed",
            "execution_evidence_incomplete",
            "hosted_write_unlock_audit_rehearsal_passed",
        ]
    )
    assert "Preflight status: ready" in write_audit_rehearsal_report
    assert "Preflight passed/input/failed: 6/0/0" in write_audit_rehearsal_report
    if "Status: hosted_write_unlock_audit_rehearsal_passed" in write_audit_rehearsal_report:
        assert "Execution evidence recorded: yes" in write_audit_rehearsal_report
        assert "Write lock restored evidence: yes" in write_audit_rehearsal_report
    else:
        assert "Production gate: blocked_until_hosted_write_audit_rehearsal_passes" in write_audit_rehearsal_report
    assert "locked_staging_runtime" in write_audit_rehearsal_report
    assert "non_source_of_truth_target" in write_audit_rehearsal_report
    assert "Requires explicit owner approval before any hosted write lock is lifted." in write_audit_rehearsal_report
    assert "Hosted Write-Audit Rehearsal Execution" in write_audit_execution_report
    assert any(
        f"Status: {status}" in write_audit_execution_report
        for status in [
            "input_required_hosted_write_audit_execution",
            "hosted_write_audit_execution_failed",
            "write_lock_restore_unverified",
            "hosted_write_audit_execution_passed",
        ]
    )
    assert "Secret values stored: no" in write_audit_execution_report
    assert "Source of truth changed: no" in write_audit_execution_report
    assert "Safe Production Gate Runner" in safe_gate_runner_script
    assert '"reports/vercel_staging_deployment_status.md"' in safe_gate_runner_script
    assert "--all-safe" in safe_gate_runner_script
    assert "--prompt-secrets" in safe_gate_runner_script
    assert "verify_owner_recovery_closure.py" in safe_gate_runner_script
    assert "prepare_owner_approved_wave_packet.py" in safe_gate_runner_script
    assert "validate_owner_gate_reply.py" in safe_gate_runner_script
    assert "record_source_of_truth_cutover_approval.py" in safe_gate_runner_script
    assert "reports/source_of_truth_cutover_approval.md" in safe_gate_runner_script
    assert "verify_hosted_deployment_freshness.py" in safe_gate_runner_script
    assert "reports/hosted_deployment_freshness.md" in safe_gate_runner_script
    assert "verify_hosted_redeploy_preflight.py" in safe_gate_runner_script
    assert "reports/hosted_redeploy_preflight.md" in safe_gate_runner_script
    assert "verify_supabase_staging_data_parity.py" in safe_gate_runner_script
    assert "reports/supabase_staging_data_parity.md" in safe_gate_runner_script
    assert "verify_supabase_staging_refresh_preflight.py" in safe_gate_runner_script
    assert "reports/supabase_staging_refresh_preflight.md" in safe_gate_runner_script
    assert "run_supabase_staging_refresh.py" in safe_gate_runner_script
    assert "reports/supabase_staging_refresh_run.md" in safe_gate_runner_script
    assert "verify_remaining_gate_guardrails.py" in safe_gate_runner_script
    assert "reports/remaining_gate_guardrails.md" in safe_gate_runner_script
    assert "verify_remaining_gate_execution_readiness.py" in safe_gate_runner_script
    assert "reports/remaining_gate_execution_readiness.md" in safe_gate_runner_script
    assert "verify_private_execution_inputs.py" in safe_gate_runner_script
    assert "reports/private_execution_inputs.md" in safe_gate_runner_script
    assert "run_owner_confirmed_production_wave.py" in safe_gate_runner_script
    assert "reports/owner_confirmed_production_wave.md" in safe_gate_runner_script
    assert "verify_secret_handling_boundaries.py" in safe_gate_runner_script
    assert "reports/secret_handling_boundaries.md" in safe_gate_runner_script
    assert "verify_local_write_freeze_readiness.py" in safe_gate_runner_script
    assert "reports/local_write_freeze_readiness.md" in safe_gate_runner_script
    assert "verify_source_of_truth_cutover_preflight.py" in safe_gate_runner_script
    assert "reports/source_of_truth_cutover_preflight.md" in safe_gate_runner_script
    assert "creates_and_deactivates_temp_app_users_no_crm_record_writes" in safe_gate_runner_script
    assert "will not approve write-audit rehearsal" in safe_gate_runner_script
    assert "execute_hosted_write_audit_rehearsal.py" in safe_gate_runner_script
    assert "reports/hosted_write_audit_execution.md" in safe_gate_runner_script
    assert "source-of-truth cutover" in safe_gate_runner_script
    assert (PROJECT_ROOT / "reports" / "safe_production_gate_runner.md").exists()
    safe_gate_runner_report = (PROJECT_ROOT / "reports" / "safe_production_gate_runner.md").read_text(encoding="utf-8")
    assert "Safe Production Gate Runner" in safe_gate_runner_report
    assert "Secret values stored: no" in safe_gate_runner_report
    assert "Remote write lock changed: no" in safe_gate_runner_report
    assert "verify_hosted_redeploy_preflight.py" in safe_gate_runner_report
    assert "verify_supabase_staging_data_parity.py" in safe_gate_runner_report
    assert "verify_supabase_staging_refresh_preflight.py" in safe_gate_runner_report
    assert "run_supabase_staging_refresh.py" in safe_gate_runner_report
    assert "verify_remaining_gate_guardrails.py" in safe_gate_runner_report
    assert "verify_remaining_gate_execution_readiness.py" in safe_gate_runner_report
    assert "verify_private_execution_inputs.py" in safe_gate_runner_report
    assert "run_owner_confirmed_production_wave.py" in safe_gate_runner_report
    assert "verify_secret_handling_boundaries.py" in safe_gate_runner_report
    assert "verify_local_write_freeze_readiness.py" in safe_gate_runner_report
    assert "verify_source_of_truth_cutover_preflight.py" in safe_gate_runner_report
    assert "validate_owner_gate_reply.py" in safe_gate_runner_report
    assert "prepare_owner_approved_wave_packet.py" in safe_gate_runner_report
    assert "app_user_self_password_change" in hosted_smoke_script
    assert "owner_password_recovery" in hosted_smoke_script
    assert "CHILLCRM_OWNER_RECOVERY_PASSWORD" in hosted_smoke_script
    assert "/api/auth/change_password" in hosted_smoke_script
    assert "/api/auth/owner_password_recovery" in hosted_smoke_script
    assert "/api/production_gates" in hosted_smoke_script
    assert "Owner Intake" in hosted_smoke_script
    assert "owner_gate_intake_packet.md" in hosted_smoke_script
    assert "STAGING_WRITE_AUDIT_PROBE_PREFIX" in hosted_smoke_script
    assert "hosted_count_evidence" in hosted_smoke_script
    assert "CHILLCRM_USE_OWNER_RECOVERY" in hosted_smoke_wrapper
    assert "Owner recovery new password" in hosted_smoke_wrapper
    assert "CHILLCRM_OWNER_RECOVERY_PASSWORD" in hosted_smoke_wrapper
    assert "CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED" in deploy_script
    assert "owner_password_recovery_env" in deploy_script
    assert "UPLOAD_CACHE_PATH" in deploy_script
    assert "CHILLCRM_DISABLE_VERCEL_UPLOAD_CACHE" in deploy_script
    assert "cache_reused" in deploy_script
    assert "CHILLCRM_VERCEL_INLINE_FILES" in deploy_script
    assert "inline_files" in deploy_script
    assert '"encoding": "base64"' in deploy_script
    assert "upload_endpoint_used=false" in deploy_script
    assert '"CRM_ENV": os.environ.get("CRM_ENV", "").strip() or "production"' in deploy_script
    assert "Vercel Environment Readiness" in vercel_environment_script
    assert "REQUIRED_STAGING_KEYS" in vercel_environment_script
    assert '"CRM_ENV": "production"' in vercel_environment_script
    assert "values_stored" in vercel_environment_script
    assert "secrets_read_or_stored" in vercel_environment_script
    assert (PROJECT_ROOT / "reports" / "vercel_environment_readiness.md").exists()
    vercel_environment_report = (PROJECT_ROOT / "reports" / "vercel_environment_readiness.md").read_text(encoding="utf-8")
    assert "Vercel Environment Readiness" in vercel_environment_report
    assert "Values stored: no" in vercel_environment_report
    assert "Secrets read or stored: no" in vercel_environment_report
    assert "Vercel Public Protection" in vercel_public_protection_script
    assert "PROTECTED_PATHS" in vercel_public_protection_script
    assert "vercel_public_protection_passed" in vercel_public_protection_script
    assert (PROJECT_ROOT / "reports" / "vercel_public_protection.md").exists()
    vercel_public_protection_report = (PROJECT_ROOT / "reports" / "vercel_public_protection.md").read_text(encoding="utf-8")
    assert "Vercel Public Protection" in vercel_public_protection_report
    assert "Secrets used: no" in vercel_public_protection_report
    assert "CRM record writes: no" in vercel_public_protection_report
    assert (PROJECT_ROOT / "reports" / "remaining_production_gates_packet.md").exists()
    remaining_gates_packet_report = (PROJECT_ROOT / "reports" / "remaining_production_gates_packet.md").read_text(encoding="utf-8")
    assert "Remaining Production Gates Packet" in remaining_gates_packet_report
    assert "Guided Safe Runner" in remaining_gates_packet_report
    assert "Owner-Approved Wave Packet" in remaining_gates_packet_report
    assert "run_safe_production_gate_checks.py --all-safe --prompt-secrets" in remaining_gates_packet_report
    assert "remaining_gate_execution_readiness.md" in remaining_gates_packet_report
    assert "private_execution_inputs.md" in remaining_gates_packet_report
    assert "owner_confirmed_production_wave.md" in remaining_gates_packet_report
    assert "run_owner_confirmed_production_wave.py --owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets" in remaining_gates_packet_report
    assert "source_of_truth_cutover_preflight.md" in remaining_gates_packet_report
    assert "verify_source_of_truth_cutover_preflight.py" in remaining_gates_packet_report
    assert "secret_handling_boundaries.md" in remaining_gates_packet_report
    assert "Public URL: `https://chillcrm.app`" in remaining_gates_packet_report
    assert "Newest hosted smoke current:" in remaining_gates_packet_report
    assert "https://chillcrm.app" in remaining_gates_packet_report
    assert "owner_approved_wave_packet.md" in remaining_gates_packet_report
    assert "supabase_staging_refresh_run.md" in remaining_gates_packet_report
    assert "supabase_staging_refresh_preflight.md" in remaining_gates_packet_report
    assert "local_write_freeze_readiness.md" in remaining_gates_packet_report
    assert "hosted_redeploy_preflight.md" in remaining_gates_packet_report
    assert "Supabase Management API access token" in remaining_gates_packet_report
    assert "Owner shakedown signoff" in remaining_gates_packet_report
    assert "Owner source-of-truth cutover approval" in remaining_gates_packet_report
    assert "Remote Production Readiness" in production_readiness_script
    assert "blocked_until_production_gates_pass" in production_readiness_script
    assert "vercel_environment_readiness" in production_readiness_script
    assert "reports/vercel_environment_readiness.md" in production_readiness_script
    assert "vercel_broad_public_protection" in production_readiness_script
    assert "reports/vercel_public_protection.md" in production_readiness_script
    assert "secret_handling_boundaries" in production_readiness_script
    assert "reports/secret_handling_boundaries.md" in production_readiness_script
    assert "remaining_gate_execution_readiness" in production_readiness_script
    assert "reports/remaining_gate_execution_readiness.md" in production_readiness_script
    assert "local_write_freeze_readiness" in production_readiness_script
    assert "reports/local_write_freeze_readiness.md" in production_readiness_script
    assert "Local write-freeze readiness" in production_readiness_script
    assert "cutover_rollback_package_readiness" in production_readiness_script
    assert "reports/cutover_rollback_package_readiness.md" in production_readiness_script
    assert "source_of_truth_cutover_preflight" in production_readiness_script
    assert "reports/source_of_truth_cutover_preflight.md" in production_readiness_script
    assert "supabase_staging_data_parity" in production_readiness_script
    assert "reports/supabase_staging_data_parity.md" in production_readiness_script
    assert "reports/supabase_staging_refresh_preflight.md" in production_readiness_script
    assert "reports/supabase_staging_refresh_run.md" in production_readiness_script
    assert "refresh_preflight" in production_readiness_script
    assert "refresh_run" in production_readiness_script
    assert "Run the Supabase staging refresh preflight" in production_readiness_script
    assert "hosted_write_unlock_audit_rehearsal" in production_readiness_script
    assert "hosted_write_unlock_audit_rehearsal_passed" in production_readiness_script
    assert "hosted_write_audit_execution.md" in production_readiness_script
    assert "hosted_write_audit_execution_passed" in production_readiness_script
    assert "hosted_write_audit_execution_reconciled_after_current_smoke" in production_readiness_script
    assert "hosted_write_audit_execution_reconciled_after_current_smoke" in monitoring_readiness_script
    assert "execute_hosted_write_audit_rehearsal.py" in production_readiness_script
    assert "hosted_deployment_freshness" in production_readiness_script
    assert "hosted_deployment_fresh" in production_readiness_script
    assert "hosted_redeploy_preflight.md" in production_readiness_script
    assert "Redeploy current local hosted runtime" in production_readiness_script
    assert "remote_monitoring_readiness" in production_readiness_script
    assert "owner_shakedown_signoff" in production_readiness_script
    assert "owner_shakedown_signed_off" in production_readiness_script
    assert "source_of_truth_cutover_approval" in production_readiness_script
    assert "source_of_truth_cutover_approved" in production_readiness_script
    remote_production_readiness_report = (PROJECT_ROOT / "reports" / "remote_production_readiness.md").read_text(encoding="utf-8")
    assert "Remote Production Readiness" in remote_production_readiness_report
    assert "Production gate:" in remote_production_readiness_report
    assert "Input-required gates:" in remote_production_readiness_report
    assert "Public URL: `https://chillcrm.app`" in remote_production_readiness_report
    assert "Public custom domain readiness" in remote_production_readiness_report
    assert "Newest hosted smoke" in remote_production_readiness_report
    assert "Source-of-truth cutover preflight guardrails" in remote_production_readiness_report
    assert "Owner recovery switch disabled" in remote_production_readiness_report
    assert "Supabase staging data parity" in remote_production_readiness_report
    assert "refresh_preflight=supabase_staging_refresh_preflight_ready/pass" in remote_production_readiness_report
    assert "reports/supabase_staging_refresh_run.md" in remote_production_readiness_report
    assert "run_supabase_staging_refresh.py --execute --prompt-secrets" in remote_production_readiness_report
    assert "Supabase provider backup/PITR visibility" in remote_production_readiness_report
    assert "Vercel environment readiness" in remote_production_readiness_report
    assert "Vercel broad public protection" in remote_production_readiness_report
    assert "Secret-handling boundary" in remote_production_readiness_report
    assert "Remaining gate execution readiness" in remote_production_readiness_report
    assert "Cutover rollback package readiness" in remote_production_readiness_report
    assert "Remote monitoring readiness" in remote_production_readiness_report
    assert "Owner source-of-truth cutover approval" in remote_production_readiness_report
    assert "Cutover Rollback Package Readiness" in cutover_rollback_script
    assert "cutover_rollback_package_ready" in cutover_rollback_script
    assert "chillcrm_supabase_storage_manifest.csv" in cutover_rollback_script
    assert "does not create backups" in cutover_rollback_script
    cutover_rollback_report = (PROJECT_ROOT / "reports" / "cutover_rollback_package_readiness.md").read_text(encoding="utf-8")
    assert "Cutover Rollback Package Readiness" in cutover_rollback_report
    assert "Production gate: pass" in cutover_rollback_report
    assert "Failed: 0" in cutover_rollback_report
    assert "environmentBadge" in app_js
    assert "setRuntimeContext" in app_js
    assert ".environment-badge" in styles_css
    assert ".inline-actions" in styles_css
    assert "Daily Operating Guide" in app_js
    assert "dailyOperatingGuidePanel" in app_js
    assert "dashboard_start_today" in server_py
    assert "start_today" in server_py
    assert "Start Work" in server_py
    assert "System Status" in server_py
    assert "Hosted Staging" not in server_py
    assert "Remote staging is read-only" not in server_py
    assert "Start Today" in app_js
    assert "startTodayPanel" in app_js
    assert "productionStatusPanel" in app_js
    assert "decision-prep-band" in styles_css
    assert "cleanup-starter-panel" in styles_css
    assert "daily-guide-panel" in styles_css
    assert "start-today-panel" in styles_css
    assert "production-status-panel" in styles_css
    assert "application/zip" in server_py
    assert ".package-content-list" in styles_css
    assert 'state.listDateFilters[state.listType] = { field: "", from: "", to: "" }' in app_js
    assert 'state.listSort[state.listType] = { field: "updated_at", direction: "desc" }' in app_js
    assert 'state.taskStatus = "open"' in app_js
    assert 'state.archivePreset = ""' in app_js
    assert "Address save failed" in app_js
    assert "Task completion failed" in app_js
    assert "Create failed" in app_js
    assert "Save failed" in app_js
    assert "payload.error || payload.message" in app_js
    assert "stage_id" in app_js
    assert "Hot Deal" in app_js
    assert "/reports/project_decision_sequence.md" in app_js
    with tempfile.TemporaryDirectory() as actor_temp_dir:
        actor_temp_path = Path(actor_temp_dir)
        actor_db = actor_temp_path / "local_crm_actor_audit_test.sqlite"
        shutil.copy2(SOURCE_DB, actor_db)
        original_actor_backup_dir = server.BACKUP_DIR
        original_profile_image_dir = server.PROFILE_IMAGE_DIR
        server.BACKUP_DIR = actor_temp_path / "backups"
        server.PROFILE_IMAGE_DIR = actor_temp_path / "profile_images"
        try:
            server.ensure_runtime_schema(actor_db)
            actor_handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
            actor_handler.db_path = actor_db
            actor_user = {"id": 101, "email": "staff-actor@example.test", "roles": ["staff"]}
            owner_actor = {"id": 102, "email": "owner-actor@example.test", "roles": ["owner"]}
            with actor_handler.db() as conn:
                person_id = conn.execute("SELECT id FROM people ORDER BY id LIMIT 1").fetchone()["id"]
                flag_id = conn.execute("SELECT id FROM review_flags WHERE status = 'open' ORDER BY id LIMIT 1").fetchone()["id"]
            actor_handler.update_record(
                {"type": "person", "id": person_id, "fields": {"title": "Actor Audit Probe"}},
                actor_user,
                "create_edit_records",
            )
            actor_handler.update_tags(
                {"type": "person", "id": person_id, "tags": ["Actor Audit Probe"]},
                actor_user,
                "edit_addresses_tags",
            )
            actor_handler.add_note(
                {"type": "person", "id": person_id, "content": "Actor-aware audit probe note."},
                actor_user,
                "notes_tasks_followups",
            )
            actor_handler.add_task(
                {"type": "person", "id": person_id, "content": "Actor-aware audit probe task."},
                actor_user,
                "notes_tasks_followups",
            )
            actor_handler.resolve_flag(
                {"id": flag_id, "status": "ignored", "note": "actor audit probe"},
                owner_actor,
                "resolve_cleanup_flags",
            )
            with actor_handler.db() as conn:
                actor_write_rows = server.rows_to_dicts(
                    conn.execute(
                        """
                        SELECT action, actor_email, actor_roles, permission_action
                        FROM audit_log
                        WHERE action IN ('update_record', 'update_tags', 'add_note', 'add_task', 'resolve_flag')
                        ORDER BY id
                        """
                    ).fetchall()
                )
            expected_actor_actions = {
                "update_record": ("staff-actor@example.test", "create_edit_records"),
                "update_tags": ("staff-actor@example.test", "edit_addresses_tags"),
                "add_note": ("staff-actor@example.test", "notes_tasks_followups"),
                "add_task": ("staff-actor@example.test", "notes_tasks_followups"),
                "resolve_flag": ("owner-actor@example.test", "resolve_cleanup_flags"),
            }
            for action, (email, permission_action) in expected_actor_actions.items():
                matching = [row for row in actor_write_rows if row["action"] == action]
                assert matching, f"Missing actor-aware audit row for {action}"
                assert matching[-1]["actor_email"] == email
                assert matching[-1]["permission_action"] == permission_action
                assert matching[-1]["actor_roles"]
            actor_record_activity = actor_handler.activity(
                {"type": ["person"], "id": [str(person_id)], "limit": ["50"]}
            )["activity"]
            assert any(
                row["activity_type"] == "audit"
                and row.get("actor_email") == "staff-actor@example.test"
                and row.get("permission_action") == "create_edit_records"
                and row.get("actor_roles")
                for row in actor_record_activity
            )
            assert any(
                row["activity_type"] == "audit"
                and row.get("actor_email") == "staff-actor@example.test"
                and row.get("permission_action") == "notes_tasks_followups"
                and row.get("actor_roles")
                for row in actor_record_activity
            )
            tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
            profile_upload = actor_handler.upload_profile_image(
                {
                    "type": "person",
                    "id": person_id,
                    "filename": "actor-profile.png",
                    "content_type": "image/png",
                    "image_data_url": f"data:image/png;base64,{tiny_png}",
                    "width": 1,
                    "height": 1,
                },
                actor_user,
                "create_edit_records",
            )
            assert profile_upload["detail"]["profile_image"]["url"].startswith("/api/profile_image?type=person")
            assert profile_upload["detail"]["profile_image"]["content_type"] == "image/png"
            with actor_handler.db() as conn:
                image_row = server.row_to_dict(
                    conn.execute(
                        """
                        SELECT storage_backend, local_file, actor_email
                        FROM record_profile_images
                        WHERE record_type = 'person' AND record_id = ? AND status = 'active'
                        """,
                        (person_id,),
                    ).fetchone()
                )
            assert image_row["storage_backend"] == "local"
            assert image_row["local_file"]
            assert image_row["actor_email"] == "staff-actor@example.test"
            profile_remove = actor_handler.remove_profile_image(
                {"type": "person", "id": person_id},
                actor_user,
                "create_edit_records",
            )
            assert profile_remove["detail"]["profile_image"] is None
            with actor_handler.db() as conn:
                profile_audit_rows = server.rows_to_dicts(
                    conn.execute(
                        """
                        SELECT action, actor_email, permission_action
                        FROM audit_log
                        WHERE action IN ('update_profile_image', 'remove_profile_image')
                          AND record_type = 'person'
                          AND record_id = ?
                        ORDER BY id
                        """,
                        (person_id,),
                    ).fetchall()
                )
            assert [row["action"] for row in profile_audit_rows][-2:] == ["update_profile_image", "remove_profile_image"]
            assert all(row["actor_email"] == "staff-actor@example.test" for row in profile_audit_rows[-2:])
            assert all(row["permission_action"] == "create_edit_records" for row in profile_audit_rows[-2:])
        finally:
            server.BACKUP_DIR = original_actor_backup_dir
            server.PROFILE_IMAGE_DIR = original_profile_image_dir
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_db = temp_path / "local_crm_operations_test.sqlite"
        shutil.copy2(SOURCE_DB, test_db)
        server.BACKUP_DIR = temp_path / "backups"
        server.ensure_runtime_schema(test_db)

        handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
        handler.db_path = test_db
        assert handler.auth_required_enabled() is False
        assert handler.auth_status_payload()["auth_required"] is False
        assert handler.runtime_context()["auth"]["required"] is False
        assert handler.should_require_auth_for_get("/api/summary") is False
        hashed = server.password_hash("correct horse")
        assert server.verify_password("correct horse", hashed)
        assert not server.verify_password("wrong horse", hashed)
        token = server.signed_session_token({"uid": 1, "exp": 4_102_444_800}, "secret")
        assert server.verify_signed_session_token(token, "secret")["uid"] == 1
        assert server.verify_signed_session_token(token, "other-secret") is None
        original_auth_env = {
            key: os.environ.get(key)
            for key in [
                "CHILLCRM_AUTH_REQUIRED",
                "SESSION_SECRET",
                "AUTH_BOOTSTRAP_ADMIN_EMAIL",
                "AUTH_BOOTSTRAP_ADMIN_PASSWORD",
                "AUTH_BOOTSTRAP_ADMIN_NAME",
                "SESSION_COOKIE_SECURE",
            ]
        }
        try:
            os.environ["CHILLCRM_AUTH_REQUIRED"] = "true"
            os.environ["SESSION_SECRET"] = "unit-test-session-secret"
            os.environ["AUTH_BOOTSTRAP_ADMIN_EMAIL"] = "owner@example.test"
            os.environ["AUTH_BOOTSTRAP_ADMIN_PASSWORD"] = "unit-test-password"
            os.environ["AUTH_BOOTSTRAP_ADMIN_NAME"] = "Owner Test"
            os.environ["SESSION_COOKIE_SECURE"] = "false"
            auth_status = handler.auth_status_payload({})
            assert auth_status["auth_required"] is True
            assert auth_status["authenticated"] is False
            assert auth_status["setup"]["session_secret_configured"] is True
            assert handler.should_require_auth_for_get("/api/summary") is True
            assert handler.should_require_auth_for_get("/") is False
            assert handler.should_require_auth_for_get("/static/app.js") is False
            assert handler.should_require_auth_for_post("/api/update_record") is True
            assert handler.should_require_auth_for_post("/api/auth/login") is False
            assert handler.authenticate_app_user("owner@example.test", "wrong") is None
            auth_user = handler.authenticate_app_user("owner@example.test", "unit-test-password")
            assert auth_user is not None
            assert auth_user["email"] == "owner@example.test"
            assert "owner" in auth_user["roles"]
            assert "admin" in auth_user["roles"]
            session_token = handler.create_session_token(auth_user)
            session_payload = server.verify_signed_session_token(session_token, "unit-test-session-secret")
            assert session_payload["email"] == "owner@example.test"
            assert handler.session_cookie_header(session_token).startswith("chillcrm_session=")
            assert "HttpOnly" in handler.session_cookie_header(session_token)
            owner_user = {"roles": ["owner"]}
            admin_user = {"roles": ["admin"]}
            staff_user = {"roles": ["staff"]}
            read_only_user = {"roles": ["read_only"]}
            migration_user = {"roles": ["migration_operator"]}
            role_users = {
                "owner": owner_user,
                "admin": admin_user,
                "staff": staff_user,
                "read_only": read_only_user,
                "migration_operator": migration_user,
            }
            for action, allowed_roles in handler.action_role_permissions.items():
                for role_key, role_user in role_users.items():
                    assert handler.user_can_perform(role_user, action) is (role_key in allowed_roles), f"{action} / {role_key}"
            for route_map in [handler.get_permission_actions, handler.post_permission_actions]:
                for route, action in route_map.items():
                    assert action in handler.action_role_permissions, f"{route} maps to unknown action {action}"
            for write_path in handler.write_locked_post_paths:
                assert write_path in handler.post_permission_actions, f"{write_path} missing POST permission action"
            assert handler.permission_action_for_get("/api/summary") == "view_dashboard_reports"
            assert handler.permission_action_for_get("/reports/project_status.md") == "view_dashboard_reports"
            assert handler.permission_action_for_get("/api/export_package") == "export_complete_package"
            assert handler.permission_action_for_get("/api/archive_file") == "download_document_files"
            assert handler.permission_action_for_post("/api/update_record") == "create_edit_records"
            assert handler.permission_action_for_post("/api/save_project_decision") == "save_project_decision"
            assert handler.permission_action_for_post("/api/auth/change_password") == "change_own_password"
            assert "/api/auth/change_password" not in handler.write_locked_post_paths
            assert handler.user_can_perform(read_only_user, "view_dashboard_reports")
            assert not handler.user_can_perform(read_only_user, "create_edit_records")
            assert not handler.user_can_perform(read_only_user, "export_csv_reports")
            assert handler.user_can_perform(read_only_user, "change_own_password")
            assert handler.user_can_perform(staff_user, "create_edit_records")
            assert handler.user_can_perform(staff_user, "notes_tasks_followups")
            assert not handler.user_can_perform(staff_user, "link_archive_item")
            assert not handler.user_can_perform(staff_user, "restore_backup")
            assert handler.user_can_perform(admin_user, "export_complete_package")
            assert not handler.user_can_perform(admin_user, "restore_backup")
            assert handler.user_can_perform(owner_user, "restore_backup")
            assert handler.user_can_perform(owner_user, "manage_users_roles")
            assert handler.user_can_perform(migration_user, "manual_backup")
            assert not handler.user_can_perform(migration_user, "create_edit_records")
            assert not handler.user_can_perform(None, "view_dashboard_reports")
            assert "Secure" not in handler.session_cookie_header(session_token)
            assert handler.permission_action_for_get("/api/app_users") == "manage_users_roles"
            assert handler.permission_action_for_post("/api/app_users/save") == "manage_users_roles"
            assert handler.permission_action_for_post("/api/app_users/deactivate") == "manage_users_roles"
            user_admin_payload = handler.app_users_payload()
            assert any(role["role_key"] == "read_only" for role in user_admin_payload["roles"])
            assert any(user["email"] == "owner@example.test" for user in user_admin_payload["users"])
            created_user = handler.save_app_user(
                {
                    "email": "pilot-admin@example.test",
                    "display_name": "Pilot Admin",
                    "roles": ["staff"],
                    "generate_password": True,
                },
                auth_user,
            )
            assert created_user["ok"] is True
            assert "temporary_password" in created_user
            assert "password_hash" not in created_user["user"]
            assert created_user["user"]["roles"] == ["staff"]
            pilot_password = created_user["temporary_password"]
            pilot_user = handler.authenticate_app_user("pilot-admin@example.test", pilot_password)
            assert pilot_user is not None
            assert pilot_user["roles"] == ["staff"]
            assert not handler.user_can_perform(pilot_user, "manage_users_roles")
            updated_user = handler.save_app_user(
                {
                    "email": "pilot-admin@example.test",
                    "display_name": "Pilot Readonly",
                    "roles": ["read_only"],
                },
                auth_user,
            )
            assert updated_user["user"]["roles"] == ["read_only"]
            reset_user = handler.set_app_user_password({"id": updated_user["user"]["id"], "password": "new-pilot-password"}, auth_user)
            assert reset_user["ok"] is True
            assert handler.authenticate_app_user("pilot-admin@example.test", pilot_password) is None
            read_only_auth_user = handler.authenticate_app_user("pilot-admin@example.test", "new-pilot-password")
            assert read_only_auth_user is not None
            assert read_only_auth_user["roles"] == ["read_only"]
            try:
                handler.change_current_app_user_password(
                    {"current_password": "wrong-password", "new_password": "rotated-pilot-password"},
                    read_only_auth_user,
                )
                raise AssertionError("Wrong current password should not change password.")
            except ValueError as exc:
                assert "Current password is incorrect." in str(exc)
            own_password_change = handler.change_current_app_user_password(
                {"current_password": "new-pilot-password", "new_password": "rotated-pilot-password"},
                read_only_auth_user,
            )
            assert own_password_change["ok"] is True
            assert handler.authenticate_app_user("pilot-admin@example.test", "new-pilot-password") is None
            read_only_auth_user = handler.authenticate_app_user("pilot-admin@example.test", "rotated-pilot-password")
            assert read_only_auth_user is not None
            deactivated_user = handler.change_app_user_status({"id": updated_user["user"]["id"]}, "deactivated", auth_user)
            assert deactivated_user["user"]["status"] == "deactivated"
            assert handler.authenticate_app_user("pilot-admin@example.test", "rotated-pilot-password") is None
            reactivated_user = handler.change_app_user_status({"id": updated_user["user"]["id"]}, "active", auth_user)
            assert reactivated_user["user"]["status"] == "active"
            read_only_auth_user = handler.authenticate_app_user("pilot-admin@example.test", "rotated-pilot-password")
            assert read_only_auth_user is not None
            handler.record_permission_denial("/api/update_record", "create_edit_records", read_only_auth_user)
            with handler.db() as conn:
                actor_audit_rows = server.rows_to_dicts(
                    conn.execute(
                        """
                        SELECT action, actor_email, actor_roles, permission_action
                        FROM audit_log
                        WHERE action IN ('app_user_save', 'app_user_status', 'app_user_password', 'app_user_password_self_change', 'permission_denied')
                        ORDER BY id
                        """
                    ).fetchall()
                )
            assert any(row["action"] == "app_user_save" and row["actor_email"] == "owner@example.test" for row in actor_audit_rows)
            assert any(row["action"] == "app_user_password" and row["permission_action"] == "manage_users_roles" for row in actor_audit_rows)
            assert any(row["action"] == "app_user_password_self_change" and row["permission_action"] == "change_own_password" for row in actor_audit_rows)
            assert any(row["action"] == "permission_denied" and row["actor_email"] == "pilot-admin@example.test" for row in actor_audit_rows)
        finally:
            for key, value in original_auth_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        person = handler.list_records({"type": ["people"], "page_size": ["1"]})["records"][0]
        person_id = person["source_id"]
        updated = handler.update_record(
            {
                "type": "person",
                "id": person_id,
                "fields": {"title": "Operations Verification"},
            }
        )
        assert updated["ok"] is True
        assert updated["detail"]["record"]["title"] == "Operations Verification"
        assert updated["detail"]["provenance"]["source"] == "zendesk"
        assert updated["detail"]["provenance"]["label"] == "Imported from Zendesk"
        assert updated["detail"]["provenance"]["zendesk_id"]
        assert updated["detail"]["provenance"]["local_change_count"] >= 1
        assert updated["detail"]["provenance"]["last_local_change"] == "Updated title"
        assert updated["detail"]["provenance"]["last_local_change_at"]
        with sqlite3.connect(test_db) as conn:
            current_person = conn.execute("SELECT owner_user_id, company_id FROM people WHERE id = ?", (person_id,)).fetchone()
            owner_row = conn.execute(
                """
                SELECT zendesk_user_id
                FROM users
                WHERE zendesk_user_id IS NOT NULL
                  AND coalesce(zendesk_user_id, 0) != coalesce(?, 0)
                ORDER BY name COLLATE NOCASE
                LIMIT 1
                """,
                (current_person[0],),
            ).fetchone()
            company_row = conn.execute(
                """
                SELECT id
                FROM companies
                WHERE coalesce(id, 0) != coalesce(?, 0)
                ORDER BY name COLLATE NOCASE
                LIMIT 1
                """,
                (current_person[1],),
            ).fetchone()
        owner_id = owner_row[0]
        company_id = company_row[0]
        relationship_updated = handler.update_record(
            {
                "type": "person",
                "id": person_id,
                "fields": {"owner_user_id": str(owner_id), "company_id": str(company_id)},
            }
        )
        assert relationship_updated["ok"] is True
        assert relationship_updated["detail"]["record"]["owner_user_id"] == owner_id
        assert relationship_updated["detail"]["owner"]["source_id"] == owner_id
        assert relationship_updated["detail"]["record"]["company_id"] == company_id
        assert relationship_updated["detail"]["company"]["source_id"] == company_id
        assert relationship_updated["detail"]["edit_options"]["owners"]
        deal = handler.list_records({"type": ["deals"], "page_size": ["1"]})["records"][0]
        deal_id = deal["source_id"]
        deal_detail = handler.record_detail({"type": ["deal"], "id": [str(deal_id)]})
        with sqlite3.connect(test_db) as conn:
            current_deal = conn.execute("SELECT person_id, company_id, stage_id FROM deals WHERE id = ?", (deal_id,)).fetchone()
            new_person = conn.execute(
                "SELECT id FROM people WHERE coalesce(id, 0) != coalesce(?, 0) ORDER BY name COLLATE NOCASE LIMIT 1",
                (current_deal[0],),
            ).fetchone()
            new_company = conn.execute(
                "SELECT id FROM companies WHERE coalesce(id, 0) != coalesce(?, 0) ORDER BY name COLLATE NOCASE LIMIT 1",
                (current_deal[1],),
            ).fetchone()
            new_stage = conn.execute(
                "SELECT id, pipeline_id FROM stages WHERE coalesce(id, 0) != coalesce(?, 0) ORDER BY position, name COLLATE NOCASE LIMIT 1",
                (current_deal[2],),
            ).fetchone()
        assert deal_detail["edit_options"]["stages"]
        deal_updated = handler.update_record(
            {
                "type": "deal",
                "id": deal_id,
                "fields": {
                    "person_id": str(new_person[0]),
                    "company_id": str(new_company[0]),
                    "stage_id": str(new_stage[0]),
                    "value": "12345.67",
                    "hot": "1",
                },
            }
        )
        assert deal_updated["ok"] is True
        assert deal_updated["detail"]["record"]["person_id"] == new_person[0]
        assert deal_updated["detail"]["record"]["company_id"] == new_company[0]
        assert deal_updated["detail"]["record"]["stage_id"] == new_stage[0]
        assert deal_updated["detail"]["record"]["pipeline_id"] == new_stage[1]
        assert deal_updated["detail"]["record"]["value"] == 12345.67
        assert deal_updated["detail"]["record"]["hot"] == 1
        assert deal_updated["detail"]["contact"]["source_id"] == new_person[0]
        assert deal_updated["detail"]["organization"]["source_id"] == new_company[0]
        try:
            handler.update_record(
                {
                    "type": "person",
                    "id": person_id,
                    "fields": {"company_id": "999999999"},
                }
            )
            raise AssertionError("Expected invalid company update to fail")
        except ValueError as exc:
            assert "Company 999999999 not found" in str(exc)
        try:
            handler.create_record(
                {
                    "type": "deal",
                    "fields": {"name": "Operations Invalid Relationship Deal", "person_id": "999999999"},
                }
            )
            raise AssertionError("Expected invalid deal create to fail")
        except ValueError as exc:
            assert "Person 999999999 not found" in str(exc)
        tagged = handler.update_tags(
            {
                "type": "person",
                "id": person_id,
                "tags": "Operations Verification Tag, Priority Client, operations verification tag",
            }
        )
        assert tagged["ok"] is True
        assert "Operations Verification Tag" in tagged["detail"]["tags"]
        assert "Priority Client" in tagged["detail"]["tags"]
        assert tagged["detail"]["tags"].count("Operations Verification Tag") == 1
        with sqlite3.connect(test_db) as conn:
            tag_row = conn.execute(
                "SELECT id, normalized_name, definition_count FROM tags WHERE normalized_name = ?",
                ("operations verification tag",),
            ).fetchone()
            assert tag_row is not None
            assert tag_row[2] == 0
            tag_assignment_count = conn.execute(
                "SELECT count(*) FROM tag_assignments WHERE record_type = 'person' AND record_id = ? AND tag_id = ?",
                (person_id, tag_row[0]),
            ).fetchone()[0]
            assert tag_assignment_count == 1
        tagged_people = handler.list_records({"type": ["people"], "tag_id": [str(tag_row[0])], "page_size": ["10"]})
        assert any(row["source_id"] == person_id for row in tagged_people["records"])
        tag_search = handler.search({"q": ["operations verification tag"]})["results"]
        assert any(
            row["type"] == "person"
            and row["source_id"] == person_id
            and row.get("match_context", "").startswith("Tag:")
            for row in tag_search
        )
        created_tag = handler.create_tag({"name": "Operations Verification Empty Tag"})
        assert created_tag["ok"] is True
        assert created_tag["created"] is True
        created_tag_id = created_tag["tag"]["source_id"]
        existing_tag = handler.create_tag({"name": "operations verification empty tag"})
        assert existing_tag["created"] is False
        assert existing_tag["tag"]["source_id"] == created_tag_id
        renamed_tag = handler.rename_tag({"id": created_tag_id, "name": "Operations Verification Renamed Tag"})
        assert renamed_tag["ok"] is True
        assert renamed_tag["changed"] is True
        assert renamed_tag["tag"]["display_name"] == "Operations Verification Renamed Tag"
        assert renamed_tag["tag"]["normalized_name"] == "operations verification renamed tag"
        try:
            handler.rename_tag({"id": created_tag_id, "name": "Priority Client"})
            raise AssertionError("Expected duplicate tag rename to fail")
        except ValueError as exc:
            assert "Tag name already exists" in str(exc)
        with sqlite3.connect(test_db) as conn:
            renamed_row = conn.execute(
                "SELECT display_name, normalized_name FROM tags WHERE id = ?",
                (created_tag_id,),
            ).fetchone()
            assert renamed_row == ("Operations Verification Renamed Tag", "operations verification renamed tag")
            assert conn.execute("SELECT count(*) FROM audit_log WHERE action = 'create_tag'").fetchone()[0] >= 1
            assert conn.execute("SELECT count(*) FROM audit_log WHERE action = 'rename_tag'").fetchone()[0] >= 1
        addressed_person = handler.record_detail({"type": ["person"], "id": ["2"]})
        assert addressed_person["address_fields_available"] is True
        assert addressed_person["addresses"], "Expected address fields for person 2"
        assert addressed_person["addresses"][0]["line1"] == "242 E North Broadway"
        addressed = handler.update_addresses(
            {
                "type": "person",
                "id": 2,
                "addresses": [
                    {
                        "address_key": "address",
                        "line1": "242 E North Broadway",
                        "line2": "Suite Verification",
                        "city": "Columbus Verification",
                        "state": "OH",
                        "postal_code": "43214",
                        "country": "USA",
                    }
                ],
            }
        )
        assert addressed["ok"] is True
        assert addressed["detail"]["addresses"][0]["city"] == "Columbus Verification"
        assert addressed["detail"]["addresses"][0]["source"] == "local"
        address_search = handler.search({"q": ["Suite Verification"]})["results"]
        assert any(row["type"] == "person" and row["source_id"] == 2 for row in address_search)
        imported_address_search = handler.search({"q": ["Chicago"]})["results"]
        assert any(row.get("match_context", "").startswith("Primary Address") for row in imported_address_search)

        noted = handler.add_note(
            {
                "type": "person",
                "id": person_id,
                "content": "Operations verification note",
            }
        )
        assert noted["ok"] is True
        assert any(note["content"] == "Operations verification note" for note in noted["detail"]["notes"])
        local_note = next(note for note in noted["detail"]["notes"] if note["content"] == "Operations verification note")
        assert local_note["editable"] == 1
        note_updated = handler.update_note({"id": local_note["source_id"], "content": "Operations verification note edited"})
        assert note_updated["ok"] is True
        assert any(note["content"] == "Operations verification note edited" for note in note_updated["detail"]["notes"])
        note_search = handler.search({"q": ["verification note"]})["results"]
        assert any(row["type"] == "person" and row["source_id"] == person_id and row.get("match_context", "").startswith("Note:") for row in note_search)
        edited_note_search = handler.search({"q": ["note edited"]})["results"]
        assert any(row["type"] == "person" and row["source_id"] == person_id and row.get("match_context", "").startswith("Note:") for row in edited_note_search)
        with sqlite3.connect(test_db) as conn:
            imported_note_id = conn.execute("SELECT id FROM notes WHERE zendesk_note_id IS NOT NULL LIMIT 1").fetchone()[0]
        try:
            handler.update_note({"id": imported_note_id, "content": "Should not edit imported note"})
            raise AssertionError("Expected imported note edit to fail")
        except ValueError as exc:
            assert "read-only" in str(exc)
        custom_value_search = handler.search({"q": ["steady continuous sustainable growth"]})["results"]
        assert any(row.get("match_context", "").startswith("Custom Field:") for row in custom_value_search)
        profile_fields = [
            "APP Number",
            "Date Created",
            "Desired Growth",
            "Time Frame",
            "Invest?",
            "Experience",
            "Skills",
            "Success Is",
            "Why Waiting",
            "Why a Fit",
        ]
        with sqlite3.connect(test_db) as conn:
            lead_profile_id = conn.execute(
                """
                SELECT record_id
                FROM custom_field_values
                WHERE record_type = 'lead'
                  AND field_name IN ({})
                GROUP BY record_id
                ORDER BY count(*) DESC, record_id
                LIMIT 1
                """.format(",".join("?" for _ in profile_fields)),
                profile_fields,
            ).fetchone()[0]
            person_profile_id = conn.execute(
                """
                SELECT record_id
                FROM custom_field_values
                WHERE record_type = 'person'
                  AND field_name IN ({})
                GROUP BY record_id
                ORDER BY count(*) DESC, record_id
                LIMIT 1
                """.format(",".join("?" for _ in profile_fields)),
                profile_fields,
            ).fetchone()[0]
        lead_profile = handler.record_detail({"type": ["lead"], "id": [str(lead_profile_id)]})["application_profile"]
        person_profile = handler.record_detail({"type": ["person"], "id": [str(person_profile_id)]})["application_profile"]
        assert [field["field_name"] for field in lead_profile] == profile_fields
        assert [field["field_name"] for field in person_profile] == profile_fields
        assert all(field["field_value"] for field in lead_profile + person_profile)
        lead_filter_options = handler.profile_filters({"type": ["leads"]})
        person_filter_options = handler.profile_filters({"type": ["people"]})
        assert [field["field_name"] for field in lead_filter_options["fields"]] == ["Desired Growth", "Time Frame", "Invest?"]
        assert [field["field_name"] for field in person_filter_options["fields"]] == ["Desired Growth", "Time Frame", "Invest?"]
        lead_growth_value = lead_filter_options["fields"][0]["values"][0]["value"]
        person_growth_value = person_filter_options["fields"][0]["values"][0]["value"]
        with sqlite3.connect(test_db) as conn:
            expected_leads = conn.execute(
                """
                SELECT count(DISTINCT record_id)
                FROM custom_field_values
                WHERE record_type = 'lead'
                  AND field_name = 'Desired Growth'
                  AND trim(field_value) = ?
                """,
                (lead_growth_value,),
            ).fetchone()[0]
            expected_people = conn.execute(
                """
                SELECT count(DISTINCT record_id)
                FROM custom_field_values
                WHERE record_type = 'person'
                  AND field_name = 'Desired Growth'
                  AND trim(field_value) = ?
                """,
                (person_growth_value,),
            ).fetchone()[0]
        filtered_leads = handler.list_records(
            {
                "type": ["leads"],
                "profile_field": ["Desired Growth"],
                "profile_value": [lead_growth_value],
                "page_size": ["10"],
            }
        )
        filtered_people = handler.list_records(
            {
                "type": ["people"],
                "profile_field": ["Desired Growth"],
                "profile_value": [person_growth_value],
                "page_size": ["10"],
            }
        )
        assert filtered_leads["total"] == expected_leads
        assert filtered_people["total"] == expected_people
        assert filtered_leads["records"]
        assert filtered_people["records"]
        assert {item["field_name"] for item in filtered_leads["records"][0]["profile_summary"]} == {
            "Desired Growth",
            "Time Frame",
            "Invest?",
        }
        assert {item["field_name"] for item in filtered_people["records"][0]["profile_summary"]} == {
            "Desired Growth",
            "Time Frame",
            "Invest?",
        }
        assert any(item["field_value"] == lead_growth_value for item in filtered_leads["records"][0]["profile_summary"])
        assert any(item["field_value"] == person_growth_value for item in filtered_people["records"][0]["profile_summary"])
        summary = handler.summary()
        summary_segments = summary["profile_segments"]
        assert [field["field_name"] for field in summary_segments] == ["Desired Growth", "Time Frame", "Invest?"]
        assert summary_segments[0]["values"][0]["value"] == "$5k - $20k"
        assert summary_segments[0]["values"][0]["count"] > 0
        assert summary["remote_write_lock"]["enabled"] is False
        assert summary["remote_write_lock"]["mode"] == "unlocked"
        assert "/api/create_record" in summary["remote_write_lock"]["locked_post_paths"]
        assert summary["runtime"]["environment"] == "local"
        assert summary["runtime"]["environment_label"] == "Local"
        assert summary["runtime"]["database_mode"] == "local_sqlite"
        assert summary["runtime"]["health_endpoint"] == "/health"
        assert summary["runtime"]["bulk_package_exports"]["enabled"] is True
        assert summary["runtime"]["bulk_package_exports"]["mode"] == "enabled"
        assert summary["runtime"]["document_file_access"]["enabled"] is True
        assert summary["runtime"]["document_file_access"]["mode"] == "enabled"
        original_health_reports_required = os.environ.pop("CHILLCRM_REPORTS_REQUIRED", None)
        try:
            health_payload, health_status = handler.health_status()
            assert health_status == 200
            assert health_payload["ok"] is True
            assert health_payload["service"] == "local_crm"
            assert health_payload["checks"]["database"]["status"] == "ok"
            assert health_payload["checks"]["database"]["reachable"] is True
            assert health_payload["checks"]["reports"]["status"] == "ok"
            assert health_payload["checks"]["reports"]["present"] is True
            assert health_payload["checks"]["reports"]["required"] is True
            assert health_payload["runtime"]["environment"] == "local"
            assert "people" not in health_payload
        finally:
            if original_health_reports_required is None:
                os.environ.pop("CHILLCRM_REPORTS_REQUIRED", None)
            else:
                os.environ["CHILLCRM_REPORTS_REQUIRED"] = original_health_reports_required
        original_crm_env = os.environ.get("CRM_ENV")
        original_app_base_url = os.environ.get("APP_BASE_URL")
        try:
            os.environ["CRM_ENV"] = "staging"
            staging_context = handler.runtime_context()
            assert staging_context["environment"] == "staging"
            assert staging_context["environment_label"] == "Staging"
            os.environ["APP_BASE_URL"] = "https://chillcrm.app"
            production_context = handler.runtime_context()
            assert production_context["environment"] == "production"
            assert production_context["environment_label"] == "Production"
        finally:
            if original_crm_env is None:
                os.environ.pop("CRM_ENV", None)
            else:
                os.environ["CRM_ENV"] = original_crm_env
            if original_app_base_url is None:
                os.environ.pop("APP_BASE_URL", None)
            else:
                os.environ["APP_BASE_URL"] = original_app_base_url
        original_database_url = os.environ.get("DATABASE_URL")
        original_adapter = os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
        original_legacy_adapter = os.environ.pop("CRM_DATABASE_ADAPTER", None)
        original_hosted_reports_required = os.environ.pop("CHILLCRM_REPORTS_REQUIRED", None)
        try:
            os.environ["DATABASE_URL"] = "postgresql://"
            with tempfile.TemporaryDirectory() as missing_reports_root:
                original_reports_dir = server.REPORTS_DIR
                try:
                    server.REPORTS_DIR = Path(missing_reports_root) / "missing_reports"
                    hosted_payload, hosted_status = handler.health_status()
                finally:
                    server.REPORTS_DIR = original_reports_dir
            assert hosted_status == 503
            assert hosted_payload["runtime"]["database_url_configured"] is True
            assert hosted_payload["checks"]["database"]["mode"] == "hosted_postgres"
            assert hosted_payload["checks"]["database"]["status"] == "invalid_database_url"
            assert hosted_payload["checks"]["database"]["adapter"] == "pending"
            assert hosted_payload["checks"]["reports"]["status"] == "omitted"
            assert hosted_payload["checks"]["reports"]["present"] is False
            assert hosted_payload["checks"]["reports"]["required"] is False
        finally:
            if original_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = original_database_url
            if original_adapter is not None:
                os.environ["CHILLCRM_DATABASE_ADAPTER"] = original_adapter
            else:
                os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
            if original_legacy_adapter is not None:
                os.environ["CRM_DATABASE_ADAPTER"] = original_legacy_adapter
            else:
                os.environ.pop("CRM_DATABASE_ADAPTER", None)
            if original_hosted_reports_required is None:
                os.environ.pop("CHILLCRM_REPORTS_REQUIRED", None)
            else:
                os.environ["CHILLCRM_REPORTS_REQUIRED"] = original_hosted_reports_required
        original_export_package_enabled = os.environ.get("EXPORT_PACKAGE_ENABLED")
        try:
            os.environ["EXPORT_PACKAGE_ENABLED"] = "false"
            bulk_status = handler.bulk_package_export_status()
            assert bulk_status["enabled"] is False
            assert bulk_status["mode"] == "locked"
            assert "/api/export_package" in bulk_status["blocked_get_paths"]
            locked_export_status = handler.export_package_status()
            assert locked_export_status["status"] == "locked"
            assert locked_export_status["ready_count"] == 0
            assert locked_export_status["core_package"]["ready"] is False
            assert locked_export_status["core_package"]["enabled"] is False
            assert locked_export_status["document_package"]["ready"] is False
            assert locked_export_status["document_package"]["enabled"] is False
        finally:
            if original_export_package_enabled is None:
                os.environ.pop("EXPORT_PACKAGE_ENABLED", None)
            else:
                os.environ["EXPORT_PACKAGE_ENABLED"] = original_export_package_enabled
        original_document_file_access_enabled = os.environ.get("DOCUMENT_FILE_ACCESS_ENABLED")
        try:
            os.environ["DOCUMENT_FILE_ACCESS_ENABLED"] = "false"
            document_file_status = handler.document_file_access_status()
            assert document_file_status["enabled"] is False
            assert document_file_status["mode"] == "locked"
            assert "/api/archive_file" in document_file_status["blocked_get_paths"]
            locked_context = handler.runtime_context()
            assert locked_context["document_file_access"]["enabled"] is False
            assert locked_context["document_file_access"]["mode"] == "locked"
        finally:
            if original_document_file_access_enabled is None:
                os.environ.pop("DOCUMENT_FILE_ACCESS_ENABLED", None)
            else:
                os.environ["DOCUMENT_FILE_ACCESS_ENABLED"] = original_document_file_access_enabled
        original_remote_write_lock = os.environ.get("REMOTE_WRITE_LOCK")
        try:
            os.environ["REMOTE_WRITE_LOCK"] = "true"
            locked_status = handler.remote_write_lock_status()
            assert locked_status["enabled"] is True
            assert locked_status["mode"] == "locked"
            assert handler.should_block_remote_write("/api/create_record")
            assert handler.should_block_remote_write("/api/save_project_decision")
            assert handler.should_block_remote_write("/api/restore_backup")
            assert not handler.should_block_remote_write("/api/export")
        finally:
            if original_remote_write_lock is None:
                os.environ.pop("REMOTE_WRITE_LOCK", None)
            else:
                os.environ["REMOTE_WRITE_LOCK"] = original_remote_write_lock
        original_database_url = os.environ.get("DATABASE_URL")
        original_adapter = os.environ.get("CHILLCRM_DATABASE_ADAPTER")
        original_legacy_adapter = os.environ.get("CRM_DATABASE_ADAPTER")
        try:
            os.environ["DATABASE_URL"] = "postgresql://user:pass@example.local:5432/postgres"
            os.environ["CHILLCRM_DATABASE_ADAPTER"] = "postgres"
            os.environ.pop("CRM_DATABASE_ADAPTER", None)
            hosted_backups = handler.backups()
            assert hosted_backups["mode"] == "hosted_postgres"
            assert hosted_backups["backups"] == []
            assert hosted_backups["provider_backup_required"] is True
            assert hosted_backups["provider_backup_report"] == "/reports/supabase_backup_readiness.md"
            assert "read-only hosted filesystem" in hosted_backups["message"]
            hosted_backup_marker = handler.create_backup("before_create_person")
            assert hosted_backup_marker.name == "supabase_provider_backup_before_create_person"
            assert not hosted_backup_marker.exists()
            with sqlite3.connect(test_db) as conn:
                conn.row_factory = sqlite3.Row
                next_person_id = int(conn.execute("SELECT COALESCE(max(id), 0) + 1 FROM people").fetchone()[0])
                created_hosted_person_id = handler.create_person(
                    conn,
                    {"name": "Hosted Primary Key Verification Person", "email": "hosted-pk@example.test"},
                    server.now_iso(),
                )
                assert created_hosted_person_id == next_person_id
                hosted_person = conn.execute("SELECT id, name FROM people WHERE id = ?", (created_hosted_person_id,)).fetchone()
                assert hosted_person["name"] == "Hosted Primary Key Verification Person"
                conn.execute("DELETE FROM people WHERE id = ?", (created_hosted_person_id,))
                conn.commit()
        finally:
            if original_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = original_database_url
            if original_adapter is None:
                os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
            else:
                os.environ["CHILLCRM_DATABASE_ADAPTER"] = original_adapter
            if original_legacy_adapter is None:
                os.environ.pop("CRM_DATABASE_ADAPTER", None)
            else:
                os.environ["CRM_DATABASE_ADAPTER"] = original_legacy_adapter
        cleanup_summary = summary["cleanup_summary"]
        cleanup_group_types = ["duplicate_people", "duplicate_leads", "lead_person_overlap", "duplicate_tags"]
        expected_cleanup_open_groups = sum(
            handler.cleanup_groups({"type": [group_type], "status": ["open"], "page_size": ["10"]})["total"]
            for group_type in cleanup_group_types
        )
        assert cleanup_summary["open_groups"] == expected_cleanup_open_groups
        assert [group["type"] for group in cleanup_summary["groups"]] == cleanup_group_types
        assert sum(cleanup_summary["priority_counts"].values()) == cleanup_summary["open_groups"]
        assert all(group["top_group"] for group in cleanup_summary["groups"] if group["open_groups"])
        start_today = summary["start_today"]
        assert start_today["title"] == "Start Today"
        assert start_today["action"] == "Open Daily Guide"
        assert start_today["view"] == "migrationStatus"
        assert start_today["report"] == "/reports/daily_operating_guide.md"
        assert start_today["export_url"] == "/api/export?type=daily_operating_guide"
        assert start_today["next_action"]["title"]
        assert start_today["step_count"] == 8
        assert [step["key"] for step in start_today["steps"]] == ["followup", "pipeline", "quality", "archive_review"]
        hosted_summary = handler.hosted_summary()
        hosted_start_today = hosted_summary["start_today"]
        assert hosted_start_today["title"] == "Start Work"
        assert "staging" not in hosted_start_today["message"].lower()
        assert hosted_start_today["action"] == "Open People"
        assert hosted_start_today["view"] == "people"
        assert hosted_start_today["next_action"]["title"] == "Open The Client Workspace"
        assert hosted_start_today["step_count"] == 0
        assert hosted_start_today["steps"] == []
        hosted_production_status = hosted_summary["production_status"]
        assert hosted_production_status["title"] == "System Status"
        assert hosted_production_status["action"] == "Open Status"
        assert hosted_production_status["step_count"] == 4
        assert [step["key"] for step in hosted_production_status["steps"]] == [
            "hosted_writes",
            "private_documents",
            "status_evidence",
            "export_packages",
        ]
        cleanup_data = handler.cleanup()
        cleanup_policy = cleanup_data["merge_policy"]
        assert cleanup_data["next_action"]["title"]
        assert cleanup_data["next_action"]["kind"] in {
            "project_decision",
            "backup",
            "cleanup_preview",
            "group_review",
            "stabilize",
        }
        duplicate_tag_decision = cleanup_data["duplicate_tag_decision"]
        assert duplicate_tag_decision["recommendation"] == "Mark normalized tags handled"
        assert duplicate_tag_decision["open_groups"] >= 32
        assert duplicate_tag_decision["affected_assignments"] >= 2214
        assert duplicate_tag_decision["definition_count"] >= 67
        assert duplicate_tag_decision["exact_alias_groups"] >= 29
        assert duplicate_tag_decision["cross_resource_same_alias_groups"] >= 3
        assert duplicate_tag_decision["alias_drift_groups"] == 0
        assert duplicate_tag_decision["recommended_simulated_groups"] >= 32
        assert duplicate_tag_decision["recommended_simulated_records"] >= 2214
        assert duplicate_tag_decision["report"] == "/reports/duplicate_tag_spot_check.md"
        assert duplicate_tag_decision["export_url"].startswith("/api/export_cleanup_groups?type=duplicate_tags")
        overlap_decision = cleanup_data["lead_person_overlap_decision"]
        assert overlap_decision["recommendation"] == "Person keeper, preserve lead history"
        assert overlap_decision["open_groups"] >= 5
        assert overlap_decision["record_count"] >= 11
        assert overlap_decision["people_count"] >= 5
        assert overlap_decision["lead_count"] >= 6
        assert overlap_decision["high_priority_groups"] >= 5
        assert overlap_decision["manual_review_fields"] >= 22
        assert overlap_decision["blank_field_suggestions"] >= 12
        assert overlap_decision["history_records"] >= 5
        assert overlap_decision["history_signals"] >= 6
        assert overlap_decision["person_keeper_drafts"] >= 5
        assert overlap_decision["top_groups"], "Expected lead/person overlap starting groups"
        assert overlap_decision["report"] == "/reports/lead_person_overlap_spot_check.md"
        assert overlap_decision["csv"] == "/reports/lead_person_overlap_spot_check.csv"
        assert overlap_decision["export_url"].startswith("/api/export_cleanup_groups?type=lead_person_overlap")
        duplicate_people_decision = cleanup_data["duplicate_people_decision"]
        assert duplicate_people_decision["recommendation"] == "Guided review, then merge"
        assert duplicate_people_decision["open_groups"] >= 60
        assert duplicate_people_decision["record_count"] >= 144
        assert duplicate_people_decision["people_count"] >= 144
        assert duplicate_people_decision["high_priority_groups"] >= 34
        assert duplicate_people_decision["medium_priority_groups"] >= 26
        assert duplicate_people_decision["manual_review_fields"] >= 173
        assert duplicate_people_decision["blank_field_suggestions"] >= 15
        assert duplicate_people_decision["history_records"] >= 52
        assert duplicate_people_decision["history_signals"] >= 57
        assert duplicate_people_decision["person_keeper_drafts"] >= 60
        assert duplicate_people_decision["top_groups"], "Expected duplicate people starting groups"
        assert duplicate_people_decision["report"] == "/reports/duplicate_people_spot_check.md"
        assert duplicate_people_decision["csv"] == "/reports/duplicate_people_spot_check.csv"
        assert duplicate_people_decision["export_url"].startswith("/api/export_cleanup_groups?type=duplicate_people")
        assert duplicate_people_decision["worksheet_report"] == "/reports/duplicate_people_review_worksheet.md"
        assert duplicate_people_decision["worksheet_export_url"] == "/api/export?type=duplicate_people_review_worksheet"
        duplicate_leads_decision = cleanup_data["duplicate_leads_decision"]
        assert duplicate_leads_decision["recommendation"] == "Guided review, then merge"
        assert duplicate_leads_decision["open_groups"] >= 36
        assert duplicate_leads_decision["record_count"] >= 77
        assert duplicate_leads_decision["lead_count"] >= 77
        assert duplicate_leads_decision["high_priority_groups"] >= 10
        assert duplicate_leads_decision["medium_priority_groups"] >= 26
        assert duplicate_leads_decision["manual_review_fields"] >= 121
        assert duplicate_leads_decision["history_records"] >= 41
        assert duplicate_leads_decision["history_signals"] >= 41
        assert duplicate_leads_decision["lead_keeper_drafts"] >= 36
        assert duplicate_leads_decision["top_groups"], "Expected duplicate leads starting groups"
        assert duplicate_leads_decision["report"] == "/reports/duplicate_leads_spot_check.md"
        assert duplicate_leads_decision["csv"] == "/reports/duplicate_leads_spot_check.csv"
        assert duplicate_leads_decision["export_url"].startswith("/api/export_cleanup_groups?type=duplicate_leads")
        assert duplicate_leads_decision["worksheet_report"] == "/reports/duplicate_leads_review_worksheet.md"
        assert duplicate_leads_decision["worksheet_export_url"] == "/api/export?type=duplicate_leads_review_worksheet"
        guided_review_queue = cleanup_data["guided_review_queue"]
        assert guided_review_queue["title"] == "Guided Review Queue"
        assert guided_review_queue["report"] == "/reports/cleanup_merge_review_pack.md"
        assert guided_review_queue["export_url"] == "/api/export?type=cleanup_merge_drafts&status=open"
        assert [queue["group_type"] for queue in guided_review_queue["queues"]] == [
            "lead_person_overlap",
            "duplicate_people",
            "duplicate_leads",
        ]
        review_queue_open_groups = sum(queue["open_groups"] for queue in guided_review_queue["queues"])
        expected_merge_review_groups = sum(
            handler.cleanup_groups({"type": [group_type], "status": ["open"], "page_size": ["10"]})["total"]
            for group_type in ["duplicate_people", "duplicate_leads", "lead_person_overlap"]
        )
        assert review_queue_open_groups == expected_merge_review_groups
        assert guided_review_queue["totals"]["open_groups"] == expected_merge_review_groups
        assert guided_review_queue["totals"]["review_remaining"] + guided_review_queue["totals"]["concrete_decisions"] == expected_merge_review_groups
        assert guided_review_queue["totals"]["manual_review_fields"] >= 316
        assert guided_review_queue["totals"]["history_signals"] >= 104
        assert guided_review_queue["next_queue"]["group_type"] in {"lead_person_overlap", "duplicate_people", "duplicate_leads"}
        for queue in guided_review_queue["queues"]:
            counts = queue["decision_counts"]
            assert sum(counts.values()) == queue["open_groups"]
            assert queue["review_remaining"] + queue["concrete_decisions"] == queue["open_groups"]
            assert queue["next_group"] or queue["open_groups"] == 0
            assert queue["export_url"].startswith(f"/api/export_cleanup_groups?type={queue['group_type']}")
        queue_by_type = {queue["group_type"]: queue for queue in guided_review_queue["queues"]}
        assert queue_by_type["duplicate_people"]["worksheet_report"] == "/reports/duplicate_people_review_worksheet.md"
        assert queue_by_type["duplicate_people"]["worksheet_export_url"] == "/api/export?type=duplicate_people_review_worksheet"
        assert queue_by_type["duplicate_leads"]["worksheet_report"] == "/reports/duplicate_leads_review_worksheet.md"
        assert queue_by_type["duplicate_leads"]["worksheet_export_url"] == "/api/export?type=duplicate_leads_review_worksheet"
        cleanup_starter_packet = cleanup_data["cleanup_starter"]
        assert cleanup_starter_packet["title"] == "Cleanup Starter Packet"
        assert cleanup_starter_packet["report"] == "/reports/cleanup_review_starter_packet.md"
        assert cleanup_starter_packet["csv"] == "/reports/cleanup_review_starter_packet.csv"
        assert cleanup_starter_packet["groups"][0]["group_type"] == "lead_person_overlap"
        assert cleanup_starter_packet["groups"][0]["draft_keeper"]
        assert cleanup_policy["recommendation"] == "Guided"
        assert cleanup_policy["totals"]["open_groups"] == expected_cleanup_open_groups
        assert cleanup_policy["totals"]["auto_merge_recommended"] == 0
        assert cleanup_policy["lanes"], "Expected guided cleanup policy lanes"
        assert sum(lane["groups"] for lane in cleanup_policy["lanes"]) == expected_cleanup_open_groups
        assert any(lane["lane"] == "tag_batch_candidate" for lane in cleanup_policy["lanes"])
        people_by_name = handler.list_records({"type": ["people"], "sort": ["name"], "direction": ["asc"], "page_size": ["20"]})
        companies_by_name = handler.list_records({"type": ["companies"], "sort": ["name"], "direction": ["asc"], "page_size": ["20"]})
        people_by_status = handler.list_records({"type": ["people"], "sort": ["status"], "direction": ["asc"], "page_size": ["20"]})
        companies_by_status = handler.list_records({"type": ["companies"], "sort": ["status"], "direction": ["asc"], "page_size": ["20"]})
        leads_by_status = handler.list_records({"type": ["leads"], "sort": ["status"], "direction": ["asc"], "page_size": ["20"]})
        people_by_owner = handler.list_records({"type": ["people"], "sort": ["owner"], "direction": ["asc"], "page_size": ["20"]})
        companies_by_owner = handler.list_records({"type": ["companies"], "sort": ["owner"], "direction": ["asc"], "page_size": ["20"]})
        leads_by_owner = handler.list_records({"type": ["leads"], "sort": ["owner"], "direction": ["asc"], "page_size": ["20"]})
        deals_by_value = handler.list_records({"type": ["deals"], "sort": ["value"], "direction": ["desc"], "page_size": ["20"]})
        fallback_sort = handler.list_records({"type": ["people"], "sort": ["unsupported"], "direction": ["sideways"], "page_size": ["10"]})
        assert people_by_name["sort"] == "name"
        assert companies_by_name["sort"] == "name"
        assert people_by_status["sort"] == "status"
        assert companies_by_status["sort"] == "status"
        assert leads_by_status["sort"] == "status"
        assert people_by_owner["sort"] == "owner"
        assert companies_by_owner["sort"] == "owner"
        assert leads_by_owner["sort"] == "owner"
        assert deals_by_value["sort"] == "value"
        assert fallback_sort["sort"] == "updated_at"
        assert fallback_sort["direction"] == "desc"
        assert_sorted([record["name"] for record in people_by_name["records"]])
        assert_sorted([record["name"] for record in companies_by_name["records"]])
        assert_sorted([record["status"] for record in people_by_status["records"]])
        assert_sorted([record["status"] for record in companies_by_status["records"]])
        assert_sorted([record["status"] for record in leads_by_status["records"]])
        assert_sorted([record["owner_name"] for record in people_by_owner["records"]])
        assert_sorted([record["owner_name"] for record in companies_by_owner["records"]])
        assert_sorted([record["owner_name"] for record in leads_by_owner["records"]])
        assert_numeric_sorted([record["value"] for record in deals_by_value["records"]], reverse=True)
        with sqlite3.connect(test_db) as conn:
            expected_current_people = conn.execute("SELECT count(*) FROM people WHERE customer_status = 'current'").fetchone()[0]
            expected_current_companies = conn.execute("SELECT count(*) FROM companies WHERE customer_status = 'current'").fetchone()[0]
            expected_unqualified_leads = conn.execute("SELECT count(*) FROM leads WHERE status = 'Unqualified'").fetchone()[0]
            people_owner_id, expected_owned_people = conn.execute(
                """
                SELECT owner_user_id, count(*)
                FROM people
                WHERE owner_user_id IS NOT NULL
                GROUP BY owner_user_id
                ORDER BY count(*) DESC, owner_user_id
                LIMIT 1
                """
            ).fetchone()
            lead_owner_id, expected_owned_leads = conn.execute(
                """
                SELECT owner_user_id, count(*)
                FROM leads
                WHERE owner_user_id IS NOT NULL
                GROUP BY owner_user_id
                ORDER BY count(*) ASC, owner_user_id
                LIMIT 1
                """
            ).fetchone()
            expected_application_deals = conn.execute(
                """
                SELECT count(*)
                FROM deals d
                JOIN stages s ON s.id = d.stage_id
                WHERE s.name = 'Application'
                """
            ).fetchone()[0]
            expected_recent_people = conn.execute(
                """
                SELECT count(*)
                FROM people
                WHERE substr(coalesce(updated_at, ''), 1, 10) >= '2026-01-01'
                """
            ).fetchone()[0]
            expected_2021_2022_deal_closes = conn.execute(
                """
                SELECT count(*)
                FROM deals
                WHERE substr(coalesce(estimated_close_date, ''), 1, 10) >= '2021-01-01'
                  AND substr(coalesce(estimated_close_date, ''), 1, 10) <= '2022-12-31'
                """
            ).fetchone()[0]
            expected_imported_people = conn.execute("SELECT count(*) FROM people WHERE zendesk_contact_id IS NOT NULL").fetchone()[0]
            expected_local_people = conn.execute("SELECT count(*) FROM people WHERE zendesk_contact_id IS NULL").fetchone()[0]
            expected_changed_people = conn.execute(
                "SELECT count(DISTINCT record_id) FROM audit_log WHERE record_type = 'person'"
            ).fetchone()[0]
            expected_people_missing_contact = conn.execute(
                """
                SELECT count(*)
                FROM people
                WHERE coalesce(trim(email), '') = ''
                  AND coalesce(trim(phone), '') = ''
                  AND coalesce(trim(mobile), '') = ''
                """
            ).fetchone()[0]
            expected_companies_missing_contact = conn.execute(
                """
                SELECT count(*)
                FROM companies
                WHERE coalesce(trim(email), '') = ''
                  AND coalesce(trim(phone), '') = ''
                """
            ).fetchone()[0]
            expected_leads_missing_email = conn.execute(
                "SELECT count(*) FROM leads WHERE coalesce(trim(email), '') = ''"
            ).fetchone()[0]
            expected_deals_missing_value = conn.execute(
                "SELECT count(*) FROM deals WHERE value IS NULL OR value = 0"
            ).fetchone()[0]
        current_people = handler.list_records(
            {"type": ["people"], "status_field": ["customer_status"], "status_value": ["current"], "page_size": ["20"]}
        )
        current_companies = handler.list_records(
            {"type": ["companies"], "status_field": ["customer_status"], "status_value": ["current"], "page_size": ["20"]}
        )
        unqualified_leads = handler.list_records(
            {"type": ["leads"], "status_field": ["status"], "status_value": ["Unqualified"], "page_size": ["20"]}
        )
        application_deals = handler.list_records(
            {"type": ["deals"], "status_field": ["stage_name"], "status_value": ["Application"], "page_size": ["20"]}
        )
        assert current_people["total"] == expected_current_people
        assert current_companies["total"] == expected_current_companies
        assert unqualified_leads["total"] == expected_unqualified_leads
        assert application_deals["total"] == expected_application_deals
        assert current_people["status_field"] == "customer_status"
        assert current_companies["status_field"] == "customer_status"
        assert unqualified_leads["status_field"] == "status"
        assert application_deals["status_field"] == "stage_name"
        assert all(record["status"] == "current" for record in current_people["records"])
        assert all(record["status"] == "current" for record in current_companies["records"])
        assert all(record["status"] == "Unqualified" for record in unqualified_leads["records"])
        assert all(record["stage_name"] == "Application" for record in application_deals["records"])
        recent_people = handler.list_records(
            {"type": ["people"], "date_field": ["updated_at"], "date_from": ["2026-01-01"], "page_size": ["20"]}
        )
        bounded_close_deals = handler.list_records(
            {
                "type": ["deals"],
                "date_field": ["estimated_close_date"],
                "date_from": ["2021-01-01"],
                "date_to": ["2022-12-31"],
                "page_size": ["20"],
            }
        )
        invalid_date_filter = handler.list_records(
            {"type": ["people"], "date_field": ["estimated_close_date"], "date_from": ["2026-01-01"], "page_size": ["20"]}
        )
        assert recent_people["date_field"] == "updated_at"
        assert recent_people["date_from"] == "2026-01-01"
        assert recent_people["date_to"] == ""
        assert recent_people["total"] == expected_recent_people
        assert bounded_close_deals["date_field"] == "estimated_close_date"
        assert bounded_close_deals["date_from"] == "2021-01-01"
        assert bounded_close_deals["date_to"] == "2022-12-31"
        assert bounded_close_deals["total"] == expected_2021_2022_deal_closes
        assert invalid_date_filter["date_field"] is None
        assert all((record["updated_at"] or "")[:10] >= "2026-01-01" for record in recent_people["records"])
        assert all("2021-01-01" <= (record["estimated_close_date"] or "")[:10] <= "2022-12-31" for record in bounded_close_deals["records"])
        imported_people = handler.list_records(
            {"type": ["people"], "provenance": ["imported"], "page_size": ["20"]}
        )
        local_people_before_create = handler.list_records(
            {"type": ["people"], "provenance": ["local"], "page_size": ["20"]}
        )
        changed_people = handler.list_records(
            {"type": ["people"], "provenance": ["changed"], "page_size": ["20"]}
        )
        invalid_provenance_filter = handler.list_records(
            {"type": ["people"], "provenance": ["unsupported"], "page_size": ["20"]}
        )
        assert imported_people["provenance"] == "imported"
        assert local_people_before_create["provenance"] == "local"
        assert changed_people["provenance"] == "changed"
        assert invalid_provenance_filter["provenance"] is None
        assert imported_people["total"] == expected_imported_people
        assert local_people_before_create["total"] == expected_local_people
        assert changed_people["total"] == expected_changed_people
        assert any(item["value"] == "imported" and item["count"] == expected_imported_people for item in imported_people["provenance_options"])
        assert any(item["value"] == "local" and item["count"] == expected_local_people for item in imported_people["provenance_options"])
        assert any(item["value"] == "changed" and item["count"] == expected_changed_people for item in imported_people["provenance_options"])
        assert all(record["provenance_source"] == "zendesk" for record in imported_people["records"])
        assert all(record["provenance_label"] == "Imported from Zendesk" for record in imported_people["records"])
        assert all(record["local_change_count"] > 0 for record in changed_people["records"])
        people_missing_contact = handler.list_records(
            {"type": ["people"], "quality_issue": ["missing_contact"], "page_size": ["20"]}
        )
        companies_missing_contact = handler.list_records(
            {"type": ["companies"], "quality_issue": ["missing_contact"], "page_size": ["20"]}
        )
        leads_missing_email = handler.list_records(
            {"type": ["leads"], "quality_issue": ["missing_email"], "page_size": ["20"]}
        )
        deals_missing_value = handler.list_records(
            {"type": ["deals"], "quality_issue": ["missing_value"], "page_size": ["20"]}
        )
        invalid_quality_filter = handler.list_records(
            {"type": ["people"], "quality_issue": ["unsupported"], "page_size": ["20"]}
        )
        assert people_missing_contact["quality_issue"] == "missing_contact"
        assert companies_missing_contact["quality_issue"] == "missing_contact"
        assert leads_missing_email["quality_issue"] == "missing_email"
        assert deals_missing_value["quality_issue"] == "missing_value"
        assert invalid_quality_filter["quality_issue"] is None
        assert people_missing_contact["total"] == expected_people_missing_contact
        assert companies_missing_contact["total"] == expected_companies_missing_contact
        assert leads_missing_email["total"] == expected_leads_missing_email
        assert deals_missing_value["total"] == expected_deals_missing_value
        assert any(item["issue"] == "missing_contact" and item["count"] == expected_people_missing_contact for item in people_missing_contact["quality_options"])
        assert any(item["issue"] == "missing_contact" and item["count"] == expected_companies_missing_contact for item in companies_missing_contact["quality_options"])
        assert any(item["issue"] == "missing_email" and item["count"] == expected_leads_missing_email for item in leads_missing_email["quality_options"])
        assert any(item["issue"] == "missing_value" and item["count"] == expected_deals_missing_value for item in deals_missing_value["quality_options"])
        assert all(not (record["email"] or record["phone"] or record["mobile"]) for record in people_missing_contact["records"])
        assert all(not (record["email"] or record["phone"]) for record in companies_missing_contact["records"])
        assert all(not record["email"] for record in leads_missing_email["records"])
        assert all(not record["value"] for record in deals_missing_value["records"])
        assert all(
            any(issue["issue"] == "missing_contact" and issue["label"] == "No contact" for issue in record["quality_issues"])
            for record in people_missing_contact["records"]
        )
        assert all(
            any(issue["issue"] == "missing_contact" and issue["label"] == "No contact" for issue in record["quality_issues"])
            for record in companies_missing_contact["records"]
        )
        assert all(
            any(issue["issue"] in {"missing_email", "missing_contact"} for issue in record["quality_issues"])
            for record in leads_missing_email["records"]
        )
        assert all(
            any(issue["issue"] == "missing_value" and issue["label"] == "Missing value" for issue in record["quality_issues"])
            for record in deals_missing_value["records"]
        )
        missing_person_detail = handler.record_detail({"type": ["person"], "id": [str(people_missing_contact["records"][0]["source_id"])]})
        missing_company_detail = handler.record_detail({"type": ["company"], "id": [str(companies_missing_contact["records"][0]["source_id"])]})
        missing_lead_detail = handler.record_detail({"type": ["lead"], "id": [str(leads_missing_email["records"][0]["source_id"])]})
        relationship_deal_record = next(
            (
                record
                for record in deals_missing_value["records"]
                if record.get("contact_name") or record.get("organization_name")
            ),
            deals_missing_value["records"][0],
        )
        missing_deal_detail = handler.record_detail({"type": ["deal"], "id": [str(relationship_deal_record["source_id"])]})
        assert any(issue["issue"] == "missing_contact" for issue in missing_person_detail["record"]["quality_issues"])
        assert any(issue["issue"] == "missing_contact" for issue in missing_company_detail["record"]["quality_issues"])
        assert any(issue["issue"] in {"missing_email", "missing_contact"} for issue in missing_lead_detail["record"]["quality_issues"])
        assert any(issue["issue"] == "missing_value" for issue in missing_deal_detail["record"]["quality_issues"])
        if missing_deal_detail["record"].get("person_id") is not None or missing_deal_detail["record"].get("company_id") is not None:
            assert all(issue["issue"] != "missing_relationship" for issue in missing_deal_detail["record"]["quality_issues"])
        owned_people = handler.list_records(
            {"type": ["people"], "owner_user_id": [str(people_owner_id)], "page_size": ["20"]}
        )
        owned_leads = handler.list_records(
            {"type": ["leads"], "owner_user_id": [str(lead_owner_id)], "page_size": ["20"]}
        )
        owner_ignored_deals = handler.list_records(
            {"type": ["deals"], "owner_user_id": [str(people_owner_id)], "page_size": ["20"]}
        )
        assert owned_people["owner_user_id"] == people_owner_id
        assert owned_leads["owner_user_id"] == lead_owner_id
        assert owned_people["total"] == expected_owned_people
        assert owned_leads["total"] == expected_owned_leads
        assert owner_ignored_deals["owner_user_id"] is None
        assert owner_ignored_deals["owner_options"] == []
        assert all(record["owner_user_id"] == people_owner_id for record in owned_people["records"])
        assert all(record["owner_user_id"] == lead_owner_id for record in owned_leads["records"])
        assert all(record["owner_name"] for record in owned_people["records"])
        assert any(str(option["value"]) == str(people_owner_id) for option in owned_people["owner_options"])
        owner_detail = handler.record_detail({"type": ["person"], "id": [str(owned_people["records"][0]["source_id"])]})
        assert owner_detail["owner"]["source_id"] == people_owner_id
        assert owner_detail["owner"]["name"]
        exported_unqualified_leads = handler.export_list_rows(
            {
                "type": ["leads"],
                "status_field": ["status"],
                "status_value": ["Unqualified"],
                "sort": ["name"],
                "direction": ["asc"],
            }
        )
        exported_application_deals = handler.export_list_rows(
            {
                "type": ["deals"],
                "status_field": ["stage_name"],
                "status_value": ["Application"],
                "sort": ["value"],
                "direction": ["desc"],
            }
        )
        exported_profile_people = handler.export_list_rows(
            {
                "type": ["people"],
                "profile_field": ["Desired Growth"],
                "profile_value": [person_growth_value],
            }
        )
        exported_owned_people = handler.export_list_rows(
            {
                "type": ["people"],
                "owner_user_id": [str(people_owner_id)],
                "sort": ["owner"],
                "direction": ["asc"],
            }
        )
        exported_recent_people = handler.export_list_rows(
            {
                "type": ["people"],
                "date_field": ["updated_at"],
                "date_from": ["2026-01-01"],
                "sort": ["updated_at"],
                "direction": ["desc"],
            }
        )
        exported_quality_deals = handler.export_list_rows(
            {
                "type": ["deals"],
                "quality_issue": ["missing_value"],
                "sort": ["updated_at"],
                "direction": ["desc"],
            }
        )
        assert exported_unqualified_leads["filename"] == "local_crm_leads_filtered.csv"
        assert len(exported_unqualified_leads["rows"]) == expected_unqualified_leads
        assert len(exported_application_deals["rows"]) == expected_application_deals
        assert len(exported_profile_people["rows"]) == expected_people
        assert len(exported_owned_people["rows"]) == expected_owned_people
        assert len(exported_recent_people["rows"]) == expected_recent_people
        assert len(exported_quality_deals["rows"]) == expected_deals_missing_value
        assert all(row["status"] == "Unqualified" for row in exported_unqualified_leads["rows"])
        assert all(row["stage_name"] == "Application" for row in exported_application_deals["rows"])
        assert all(row["Desired Growth"] == person_growth_value for row in exported_profile_people["rows"])
        assert all(row["owner_user_id"] == people_owner_id for row in exported_owned_people["rows"])
        assert all(row["owner_name"] for row in exported_owned_people["rows"])
        assert all((row["updated_at"] or "")[:10] >= "2026-01-01" for row in exported_recent_people["rows"])
        assert all(not row["value"] for row in exported_quality_deals["rows"])
        corrected_quality_person = handler.update_record(
            {
                "type": "person",
                "id": people_missing_contact["records"][0]["source_id"],
                "fields": {"email": "quality-verification@example.com"},
            }
        )
        assert corrected_quality_person["ok"] is True
        assert all(issue["issue"] != "missing_contact" for issue in corrected_quality_person["detail"]["record"]["quality_issues"])
        refreshed_people_missing_contact = handler.list_records(
            {"type": ["people"], "quality_issue": ["missing_contact"], "page_size": ["20"]}
        )
        assert refreshed_people_missing_contact["total"] == expected_people_missing_contact - 1
        assert all(
            record["source_id"] != people_missing_contact["records"][0]["source_id"]
            for record in refreshed_people_missing_contact["records"]
        )
        quality_saved_view = handler.save_view(
            {
                "type": "deals",
                "name": "Verification Deals Missing Value",
                "settings": {
                    "quality_issue": "missing_value",
                    "sort": "updated_at",
                    "direction": "desc",
                },
            }
        )
        assert quality_saved_view["ok"] is True
        assert quality_saved_view["view"]["record_count"] == expected_deals_missing_value
        assert quality_saved_view["view"]["settings"]["quality_issue"] == "missing_value"
        assert handler.delete_view({"id": quality_saved_view["view"]["id"]})["ok"] is True
        owner_saved_view = handler.save_view(
            {
                "type": "people",
                "name": "Verification Owner People",
                "settings": {
                    "owner_user_id": str(people_owner_id),
                    "sort": "owner",
                    "direction": "asc",
                },
            }
        )
        assert owner_saved_view["ok"] is True
        assert owner_saved_view["view"]["record_count"] == expected_owned_people
        assert owner_saved_view["view"]["settings"]["owner_user_id"] == str(people_owner_id)
        assert handler.delete_view({"id": owner_saved_view["view"]["id"]})["ok"] is True
        date_saved_view = handler.save_view(
            {
                "type": "deals",
                "name": "Verification Close Date Deals",
                "settings": {
                    "date_field": "estimated_close_date",
                    "date_from": "2021-01-01",
                    "date_to": "2022-12-31",
                    "sort": "estimated_close_date",
                    "direction": "asc",
                },
            }
        )
        assert date_saved_view["ok"] is True
        assert date_saved_view["view"]["record_count"] == expected_2021_2022_deal_closes
        assert date_saved_view["view"]["settings"]["date_field"] == "estimated_close_date"
        assert date_saved_view["view"]["settings"]["date_from"] == "2021-01-01"
        assert date_saved_view["view"]["settings"]["date_to"] == "2022-12-31"
        assert handler.delete_view({"id": date_saved_view["view"]["id"]})["ok"] is True
        saved_view = handler.save_view(
            {
                "type": "leads",
                "name": "Verification Unqualified Leads",
                "settings": {
                    "status_field": "status",
                    "status_value": "Unqualified",
                    "sort": "updated_at",
                    "direction": "desc",
                },
            }
        )
        assert saved_view["ok"] is True
        assert saved_view["view"]["record_count"] == expected_unqualified_leads
        saved_views = handler.saved_views({"type": ["leads"]})["views"]
        matching_views = [view for view in saved_views if view["name"] == "Verification Unqualified Leads"]
        assert len(matching_views) == 1
        assert matching_views[0]["record_count"] == expected_unqualified_leads
        saved_settings = matching_views[0]["settings"]
        assert saved_settings["status_field"] == "status"
        assert saved_settings["status_value"] == "Unqualified"
        assert saved_settings["sort"] == "updated_at"
        assert saved_settings["direction"] == "desc"
        summary_saved_views = handler.summary()["saved_views"]
        summary_view = next(view for view in summary_saved_views if view["name"] == "Verification Unqualified Leads")
        assert summary_view["record_count"] == expected_unqualified_leads
        refreshed_from_view = handler.list_records(
            {
                "type": ["leads"],
                "status_field": [saved_settings["status_field"]],
                "status_value": [saved_settings["status_value"]],
                "sort": [saved_settings["sort"]],
                "direction": [saved_settings["direction"]],
                "page_size": ["20"],
            }
        )
        assert refreshed_from_view["total"] == expected_unqualified_leads
        deleted_view = handler.delete_view({"id": matching_views[0]["id"]})
        assert deleted_view["ok"] is True
        assert not [
            view
            for view in handler.saved_views({"type": ["leads"]})["views"]
            if view["name"] == "Verification Unqualified Leads"
        ]

        person_create_options = handler.create_options({"type": ["person"]})
        deal_create_options = handler.create_options({"type": ["deal"]})
        assert person_create_options["edit_options"]["owners"]
        assert person_create_options["edit_options"]["companies"]
        assert deal_create_options["edit_options"]["people"]
        assert deal_create_options["edit_options"]["companies"]
        assert deal_create_options["edit_options"]["stages"]

        company = handler.create_record(
            {
                "type": "company",
                "fields": {
                    "name": "Operations Verification Co",
                    "email": "ops-company@example.com",
                    "owner_user_id": str(owner_id),
                    "customer_status": "current",
                    "prospect_status": "none",
                },
            }
        )
        assert company["ok"] is True
        company_id = company["detail"]["record"]["source_id"]
        assert company["detail"]["record"]["owner_user_id"] == owner_id
        assert company["detail"]["owner"]["source_id"] == owner_id
        assert company["detail"]["record"]["customer_status"] == "current"

        created_person = handler.create_record(
            {
                "type": "person",
                "fields": {
                    "name": "Operations Verification Person",
                    "email": "ops-person@example.com",
                    "company_id": str(company_id),
                    "owner_user_id": str(owner_id),
                    "customer_status": "current",
                    "prospect_status": "lead",
                },
            }
        )
        assert created_person["ok"] is True
        created_person_id = created_person["detail"]["record"]["source_id"]
        assert created_person["detail"]["company"]["name"] == "Operations Verification Co"
        assert created_person["detail"]["owner"]["source_id"] == owner_id
        assert created_person["detail"]["record"]["customer_status"] == "current"
        assert created_person["detail"]["record"]["prospect_status"] == "lead"
        assert created_person["detail"]["provenance"]["source"] == "local"
        assert created_person["detail"]["provenance"]["label"] == "Local only"
        assert created_person["detail"]["provenance"]["zendesk_id"] is None
        assert created_person["detail"]["provenance"]["local_change_count"] >= 1
        assert created_person["detail"]["provenance"]["last_local_change"] == "Created record"
        local_people_after_create = handler.list_records(
            {"type": ["people"], "provenance": ["local"], "page_size": ["20"]}
        )
        assert local_people_after_create["total"] == expected_local_people + 1
        assert any(record["source_id"] == created_person_id for record in local_people_after_create["records"])
        assert all(record["provenance_source"] == "local" for record in local_people_after_create["records"])
        exported_local_people = handler.export_list_rows({"type": ["people"], "provenance": ["local"]})
        assert any(row["source_id"] == created_person_id and row["source"] == "Local only" for row in exported_local_people["rows"])
        assert all("local_change_count" in row for row in exported_local_people["rows"])
        contact_rollup_note = handler.add_note(
            {
                "type": "person",
                "id": created_person_id,
                "content": "Operations verification contact rollup note",
            }
        )
        assert contact_rollup_note["ok"] is True

        lead = handler.create_record(
            {
                "type": "lead",
                "fields": {"name": "Operations Verification Lead", "email": "ops-lead@example.com", "owner_user_id": str(owner_id)},
            }
        )
        assert lead["ok"] is True
        assert lead["detail"]["record"]["status"] == "New"
        assert lead["detail"]["owner"]["source_id"] == owner_id
        matched_lead = handler.create_record(
            {
                "type": "lead",
                "fields": {
                    "name": "Operations Verification Matched Lead",
                    "email": "ops-person@example.com",
                },
            }
        )
        assert matched_lead["ok"] is True
        matched_lead_id = matched_lead["detail"]["record"]["source_id"]

        deal = handler.create_record(
            {
                "type": "deal",
                "fields": {
                    "name": "Operations Verification Deal",
                    "person_id": str(created_person_id),
                    "company_id": str(company_id),
                    "stage_id": str(new_stage[0]),
                    "value": "1234",
                    "currency": "USD",
                    "hot": "1",
                },
            }
        )
        assert deal["ok"] is True
        deal_id = deal["detail"]["record"]["source_id"]
        assert deal["detail"]["record"]["value"] == 1234
        assert deal["detail"]["record"]["stage_id"] == new_stage[0]
        assert deal["detail"]["record"]["pipeline_id"] == new_stage[1]
        assert deal["detail"]["record"]["currency"] == "USD"
        assert deal["detail"]["record"]["hot"] == 1
        assert deal["detail"]["address_fields_available"] is True
        assert deal["detail"]["address_editable"] is False
        assert any(address["label"].startswith("Contact: Operations Verification Person") for address in deal["detail"]["addresses"])
        assert any(address["label"].startswith("Organization: Operations Verification Co") for address in deal["detail"]["addresses"])
        deal_rollup_note = handler.add_note(
            {
                "type": "deal",
                "id": deal_id,
                "content": "Operations verification deal rollup note",
            }
        )
        assert deal_rollup_note["ok"] is True
        company_relationship_search = handler.search({"q": ["Operations Verification Co"]})["results"]
        assert any(
            row["type"] == "person"
            and row["source_id"] == created_person_id
            and row.get("match_context", "").startswith("Company:")
            for row in company_relationship_search
        )
        assert any(
            row["type"] == "deal"
            and row["source_id"] == deal_id
            and row.get("match_context", "").startswith("Company:")
            for row in company_relationship_search
        )
        contact_relationship_search = handler.search({"q": ["Operations Verification Person"]})["results"]
        assert any(
            row["type"] == "company"
            and row["source_id"] == company_id
            and row.get("match_context", "").startswith("Contact:")
            for row in contact_relationship_search
        )
        assert any(
            row["type"] == "lead"
            and row["source_id"] == matched_lead_id
            and row.get("match_context", "").startswith("Matched Person:")
            for row in contact_relationship_search
        )
        assert any(
            row["type"] == "deal"
            and row["source_id"] == deal_id
            and row.get("match_context", "").startswith("Contact:")
            for row in contact_relationship_search
        )
        deal_relationship_search = handler.search({"q": ["Operations Verification Deal"]})["results"]
        assert any(
            row["type"] == "person"
            and row["source_id"] == created_person_id
            and row.get("match_context", "").startswith("Deal:")
            for row in deal_relationship_search
        )
        assert any(
            row["type"] == "company"
            and row["source_id"] == company_id
            and row.get("match_context", "").startswith("Deal:")
            for row in deal_relationship_search
        )

        task = handler.add_task(
            {
                "type": "person",
                "id": created_person_id,
                "content": "Operations verification task",
                "due_date": "2026-06-05",
            }
        )
        assert task["ok"] is True
        task_id = task["detail"]["tasks"][0]["source_id"]
        assert task["detail"]["tasks"][0]["task_source"] == "local"
        assert task["detail"]["tasks"][0]["task_source_label"] == "Local"
        open_tasks = handler.tasks({"status": ["open"], "page_size": ["10"]})
        assert any(row["source_id"] == task_id for row in open_tasks["tasks"])
        assert open_tasks["source_counts"]["local"] >= 1
        assert open_tasks["source_counts"]["imported"] >= 1
        assert any(row["task_source"] == "imported" and row["task_source_label"] == "Imported" for row in open_tasks["tasks"])
        transition_plan = open_tasks["transition_plan"]
        assert transition_plan["title"] == "Follow Up Transition Plan"
        assert transition_plan["export_url"] == "/api/export?type=followup_transition_plan"
        assert transition_plan["report"] == "/reports/followup_transition_plan.md"
        assert transition_plan["counts"]["open_imported"] >= 1
        assert transition_plan["counts"]["open_local"] >= 1
        assert transition_plan["steps"][0]["preset"] == "followup_imported_open"
        assert transition_plan["steps"][1]["preset"] == "followup_imported_overdue"
        assert transition_plan["steps"][2]["preset"] == "followup_local_open"
        assert all(row["task_source"] == "imported" for row in transition_plan["imported_open_tasks"])
        imported_tasks = handler.tasks({"status": ["open"], "source": ["imported"], "page_size": ["50"]})
        assert imported_tasks["source"] == "imported"
        assert imported_tasks["total"] >= 1
        assert all(row["task_source"] == "imported" for row in imported_tasks["tasks"])
        imported_task_id = imported_tasks["tasks"][0]["source_id"]
        copied_task = handler.copy_imported_task_to_local({"id": imported_task_id, "due_date": "2026-06-07"})
        assert copied_task["ok"] is True
        copied_task_id = copied_task["task_id"]
        copied_detail_task = next(row for row in copied_task["detail"]["tasks"] if row["source_id"] == copied_task_id)
        assert copied_detail_task["task_source"] == "local"
        assert copied_detail_task["zendesk_task_id"] is None
        assert copied_detail_task["due_date"] == "2026-06-07"
        imported_task_after_copy = handler.tasks({"status": ["open"], "source": ["imported"], "page_size": ["50"]})
        assert any(row["source_id"] == imported_task_id and row["task_source"] == "imported" for row in imported_task_after_copy["tasks"])
        local_tasks = handler.tasks({"status": ["open"], "source": ["local"], "page_size": ["50"]})
        assert local_tasks["source"] == "local"
        assert any(row["source_id"] == task_id for row in local_tasks["tasks"])
        assert any(row["source_id"] == copied_task_id for row in local_tasks["tasks"])
        assert all(row["task_source"] == "local" for row in local_tasks["tasks"])
        assert handler.summary()["counts"]["open_tasks"] >= 1

        task_updated = handler.update_task(
            {
                "id": task_id,
                "content": "Operations verification task edited",
                "due_date": "2026-06-06",
            }
        )
        assert task_updated["ok"] is True
        edited_task = next(row for row in task_updated["detail"]["tasks"] if row["source_id"] == task_id)
        assert edited_task["content"] == "Operations verification task edited"
        assert edited_task["due_date"] == "2026-06-06"
        edited_open_tasks = handler.tasks({"status": ["open"], "page_size": ["50"]})
        assert any(
            row["source_id"] == task_id and row["content"] == "Operations verification task edited"
            for row in edited_open_tasks["tasks"]
        )
        filtered_open_tasks = handler.tasks(
            {
                "status": ["open"],
                "q": ["verification task edited"],
                "record_type": ["person"],
                "source": ["local"],
                "sort": ["record"],
                "direction": ["asc"],
                "page_size": ["50"],
            }
        )
        assert filtered_open_tasks["q"] == "verification task edited"
        assert filtered_open_tasks["record_type"] == "person"
        assert filtered_open_tasks["source"] == "local"
        assert filtered_open_tasks["sort"] == "record"
        assert filtered_open_tasks["direction"] == "asc"
        assert any(row["source_id"] == task_id for row in filtered_open_tasks["tasks"])
        task_sorted_open_tasks = handler.tasks({"status": ["open"], "sort": ["task"], "direction": ["asc"], "page_size": ["50"]})
        assert task_sorted_open_tasks["sort"] == "task"
        assert_sorted([row["content"] for row in task_sorted_open_tasks["tasks"]])
        task_filtered_export = handler.export_rows(
            {
                "type": ["tasks"],
                "status": ["open"],
                "q": ["verification task edited"],
                "record_type": ["person"],
                "source": ["local"],
                "sort": ["record"],
                "direction": ["asc"],
            }
        )
        assert task_filtered_export["filename"] == "local_crm_tasks_open_filtered.csv"
        assert any(
            row["source_id"] == task_id
            and row["record_type"] == "person"
            and row["record_name"] == "Operations Verification Person"
            and row["task_source"] == "local"
            and row["task_source_label"] == "Local"
            for row in task_filtered_export["rows"]
        )
        task_saved_view = handler.save_view(
            {
                "type": "tasks",
                "name": "Verification People Follow Up",
                "settings": {
                    "status": "open",
                    "q": "verification task edited",
                    "record_type": "person",
                    "source": "local",
                    "sort": "record",
                    "direction": "asc",
                },
            }
        )
        assert task_saved_view["ok"] is True
        assert task_saved_view["view"]["record_count"] == len(task_filtered_export["rows"])
        assert task_saved_view["view"]["settings"]["record_type"] == "person"
        assert task_saved_view["view"]["settings"]["source"] == "local"
        task_saved_views = handler.saved_views({"type": ["tasks"]})["views"]
        matching_task_views = [view for view in task_saved_views if view["name"] == "Verification People Follow Up"]
        assert len(matching_task_views) == 1
        assert matching_task_views[0]["record_count"] == len(task_filtered_export["rows"])
        assert handler.delete_view({"id": matching_task_views[0]["id"]})["ok"] is True
        task_search = handler.search({"q": ["verification task edited"]})["results"]
        assert any(
            row["type"] == "person"
            and row["source_id"] == created_person_id
            and row.get("match_context", "").startswith("Task:")
            for row in task_search
        )

        completed = handler.complete_task({"id": task_id, "completed": True})
        assert completed["ok"] is True
        assert completed["detail"]["tasks"][0]["completed"] == 1
        completed_tasks = handler.tasks({"status": ["completed"], "page_size": ["10"]})
        assert any(row["source_id"] == task_id for row in completed_tasks["tasks"])
        reopened = handler.complete_task({"id": task_id, "completed": False})
        assert reopened["ok"] is True
        assert next(row for row in reopened["detail"]["tasks"] if row["source_id"] == task_id)["completed"] == 0
        reopened_open_tasks = handler.tasks({"status": ["open"], "page_size": ["50"]})
        assert any(row["source_id"] == task_id and not row["completed"] for row in reopened_open_tasks["tasks"])

        restore_anchor = handler.create_backup("restore_anchor")
        extra_person = handler.create_record(
            {
                "type": "person",
                "fields": {"name": "Operations Restore Extra", "email": "ops-restore-extra@example.com"},
            }
        )
        assert extra_person["ok"] is True
        assert handler.summary()["counts"]["people"] == 999
        restored = handler.restore_backup({"name": restore_anchor.name})
        assert restored["ok"] is True
        assert restored["summary"]["counts"]["people"] == 998
        assert "pre_restore" in restored["pre_restore_backup"]

        activity = handler.activity({"limit": ["25"]})
        assert activity["activity"], "Expected global activity rows"
        filtered_activity = handler.activity(
            {
                "q": ["deal rollup note"],
                "activity_type": ["note"],
                "record_type": ["deal"],
                "date_from": ["2026-01-01"],
                "date_to": ["2026-12-31"],
                "limit": ["25"],
            }
        )
        assert filtered_activity["q"] == "deal rollup note"
        assert filtered_activity["activity_type"] == "note"
        assert filtered_activity["record_type"] == "deal"
        assert filtered_activity["date_from"] == "2026-01-01"
        assert filtered_activity["date_to"] == "2026-12-31"
        assert filtered_activity["total"] >= 1
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "deal"
            and row["record_id"] == deal_id
            and row["summary"] == "Operations verification deal rollup note"
            for row in filtered_activity["activity"]
        )
        filtered_activity_export = handler.export_rows(
            {
                "type": ["activity"],
                "q": ["deal rollup note"],
                "activity_type": ["note"],
                "record_type": ["deal"],
                "date_from": ["2026-01-01"],
                "date_to": ["2026-12-31"],
            }
        )
        assert filtered_activity_export["filename"] == "local_crm_activity_filtered.csv"
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "deal"
            and row["record_id"] == deal_id
            and row["summary"] == "Operations verification deal rollup note"
            for row in filtered_activity_export["rows"]
        )
        activity_saved_view = handler.save_view(
            {
                "type": "activity",
                "name": "Verification Deal Note Activity",
                "settings": {
                    "q": "deal rollup note",
                    "activity_type": "note",
                    "record_type": "deal",
                    "date_from": "2026-01-01",
                    "date_to": "2026-12-31",
                },
            }
        )
        assert activity_saved_view["ok"] is True
        assert activity_saved_view["view"]["record_count"] == len(filtered_activity_export["rows"])
        assert activity_saved_view["view"]["settings"]["activity_type"] == "note"
        assert activity_saved_view["view"]["settings"]["date_from"] == "2026-01-01"
        assert activity_saved_view["view"]["settings"]["date_to"] == "2026-12-31"
        activity_saved_views = handler.saved_views({"type": ["activity"]})["views"]
        matching_activity_views = [view for view in activity_saved_views if view["name"] == "Verification Deal Note Activity"]
        assert len(matching_activity_views) == 1
        assert matching_activity_views[0]["record_count"] == len(filtered_activity_export["rows"])
        assert handler.delete_view({"id": matching_activity_views[0]["id"]})["ok"] is True
        person_activity = handler.activity({"type": ["person"], "id": [str(created_person_id)], "limit": ["25"]})
        assert any(row["activity_type"] in {"task", "task_completed"} for row in person_activity["activity"])
        assert any(
            row["activity_type"] == "deal" and row["record_type"] == "deal" and row["record_id"] == deal_id
            for row in person_activity["activity"]
        )
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "deal"
            and row["record_id"] == deal_id
            and row["summary"] == "Operations verification deal rollup note"
            for row in person_activity["activity"]
        )
        company_activity = handler.activity({"type": ["company"], "id": [str(company_id)], "limit": ["25"]})
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "person"
            and row["record_id"] == created_person_id
            and row["summary"] == "Operations verification contact rollup note"
            for row in company_activity["activity"]
        )
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "deal"
            and row["record_id"] == deal_id
            and row["summary"] == "Operations verification deal rollup note"
            for row in company_activity["activity"]
        )
        deal_activity = handler.activity({"type": ["deal"], "id": [str(deal_id)], "limit": ["25"]})
        assert any(
            row["activity_type"] == "note"
            and row["record_type"] == "person"
            and row["record_id"] == created_person_id
            and row["summary"] == "Operations verification contact rollup note"
            for row in deal_activity["activity"]
        )
        tags = handler.tags({"page_size": ["10"]})
        assert tags["tags"], "Expected tag rows"
        assert tags["total_assignments"] >= tags["tags"][0]["assignment_count"]
        assert "tagSavedView" in app_js
        assert "currentTagSettings" in app_js
        assert "applyTagSettings" in app_js
        person_tag = next(tag for tag in tags["tags"] if "person" in tag["record_types"])
        person_tags = handler.tags({"record_type": ["person"], "page_size": ["100"]})
        assert person_tags["record_type"] == "person"
        assert person_tags["total"] >= 1
        assert person_tags["total_assignments"] == sum(row["assignment_count"] for row in person_tags["tags"])
        assert all(row["record_types"] == ["person"] for row in person_tags["tags"])
        person_tag_export = handler.export_rows({"type": ["tags"], "record_type": ["person"]})
        assert person_tag_export["filename"] == "local_crm_tags_filtered.csv"
        assert len(person_tag_export["rows"]) == person_tags["total"]
        assert all(row["record_types"] == "person" for row in person_tag_export["rows"])
        tagged_people = handler.list_records({"type": ["people"], "tag_id": [str(person_tag["source_id"])], "page_size": ["10"]})
        assert tagged_people["total"] > 0
        with sqlite3.connect(test_db) as conn:
            expected_tagged_people = conn.execute(
                "SELECT count(*) FROM tag_assignments WHERE record_type = 'person' AND tag_id = ?",
                (person_tag["source_id"],),
            ).fetchone()[0]
        assert tagged_people["total"] == expected_tagged_people
        tag_detail = handler.tags({"id": [str(tags["tags"][0]["source_id"])], "page_size": ["10"]})
        assert tag_detail["tag"]["source_id"] == tags["tags"][0]["source_id"]
        assert tag_detail["records"], "Expected tagged records"
        person_tag_detail = handler.tags({"id": [str(person_tag["source_id"])], "record_type": ["person"], "page_size": ["100"]})
        assert person_tag_detail["record_type"] == "person"
        assert person_tag_detail["total"] == expected_tagged_people
        assert all(row["record_type"] == "person" for row in person_tag_detail["records"])
        tag_saved_view = handler.save_view(
            {
                "type": "tags",
                "name": "Verification Person Tags",
                "settings": {"record_type": "person"},
            }
        )
        assert tag_saved_view["ok"] is True
        assert tag_saved_view["view"]["record_count"] == person_tags["total"]
        assert tag_saved_view["view"]["settings"]["record_type"] == "person"
        assert any(view["name"] == "Verification Person Tags" for view in handler.saved_views({"type": ["tags"]})["views"])
        assert any(view["name"] == "Verification Person Tags" for view in handler.summary()["saved_views"])
        for group_type in ["duplicate_people", "duplicate_leads", "lead_person_overlap", "duplicate_tags"]:
            cleanup_groups = handler.cleanup_groups({"type": [group_type], "page_size": ["10"]})
            assert cleanup_groups["groups"], f"Expected cleanup groups for {group_type}"
            group_guidance = cleanup_groups["groups"][0]["guidance"]
            policy_lane = cleanup_groups["groups"][0]["policy_lane"]
            assert group_guidance["priority"] in {"High", "Medium", "Low"}
            assert group_guidance["score"] >= 0
            assert group_guidance["headline"]
            assert group_guidance["reasons"]
            assert policy_lane["lane"] in server.CLEANUP_POLICY_LANES
            assert policy_lane["label"]
            assert policy_lane["action"]
            assert policy_lane["reason"]
            group_draft_summary = cleanup_groups["groups"][0].get("merge_draft_summary")
            if group_type == "duplicate_tags":
                assert group_draft_summary is None
            else:
                assert group_draft_summary
                assert group_draft_summary["keeper_record_key"]
                assert group_draft_summary["keeper_name"]
                assert group_draft_summary["keeper_score"] >= 1
                assert group_draft_summary["fill_suggestion_count"] >= 0
                assert group_draft_summary["conflict_count"] >= 0
                assert group_draft_summary["preserve_signal_count"] >= 0
            priority_groups = handler.cleanup_groups(
                {"type": [group_type], "priority": [group_guidance["priority"].lower()], "page_size": ["50"]}
            )
            assert priority_groups["priority"] == group_guidance["priority"].lower()
            assert priority_groups["groups"], f"Expected priority-filtered cleanup groups for {group_type}"
            assert all(group["guidance"]["priority"] == group_guidance["priority"] for group in priority_groups["groups"])
            assert any(group["group_key"] == cleanup_groups["groups"][0]["group_key"] for group in priority_groups["groups"])
            lane_groups = handler.cleanup_groups(
                {"type": [group_type], "policy_lane": [policy_lane["lane"]], "page_size": ["50"]}
            )
            assert lane_groups["policy_lane"] == policy_lane["lane"]
            assert lane_groups["groups"], f"Expected lane-filtered cleanup groups for {group_type}"
            assert all(group["policy_lane"]["lane"] == policy_lane["lane"] for group in lane_groups["groups"])
            policy_sorted = handler.cleanup_groups({"type": [group_type], "sort": ["policy"], "page_size": ["50"]})
            assert policy_sorted["sort"] == "policy"
            policy_orders = [group["policy_lane"]["sort"] for group in policy_sorted["groups"]]
            assert policy_orders == sorted(policy_orders)
            priority_export = handler.export_cleanup_group_rows(
                {"type": [group_type], "priority": [group_guidance["priority"].lower()], "sort": ["priority"]}
            )
            assert priority_export["filename"] == f"local_crm_cleanup_{group_type}_groups.csv"
            assert len(priority_export["rows"]) == priority_groups["total"]
            assert all(row["priority"] == group_guidance["priority"] for row in priority_export["rows"])
            assert priority_export["rows"][0]["review_score"] >= priority_export["rows"][-1]["review_score"]
            assert "draft_keeper" in priority_export["rows"][0]
            assert "draft_manual_review_fields" in priority_export["rows"][0]
            assert "policy_lane" in priority_export["rows"][0]
            assert "policy_action" in priority_export["rows"][0]
            if group_type == "duplicate_tags":
                assert priority_export["rows"][0]["draft_keeper"] is None
            else:
                assert priority_export["rows"][0]["draft_keeper"]
                assert priority_export["rows"][0]["draft_keeper_score"] >= 1
                assert priority_export["rows"][0]["draft_manual_review_fields"] >= 0
            priority_sorted = handler.cleanup_groups({"type": [group_type], "sort": ["priority"], "page_size": ["50"]})
            priority_scores = [group["guidance"]["score"] for group in priority_sorted["groups"]]
            assert priority_scores == sorted(priority_scores, reverse=True)
            email_sorted = handler.cleanup_groups({"type": [group_type], "sort": ["email"], "page_size": ["50"]})
            email_keys = [group.get("display_name") or group["group_key"] for group in email_sorted["groups"]]
            assert email_sorted["sort"] == "email"
            assert email_keys == sorted(email_keys, key=lambda value: str(value).casefold())
            email_export = handler.export_cleanup_group_rows({"type": [group_type], "sort": ["email"]})
            assert [row["group_label"] for row in email_export["rows"][: len(email_keys)]] == email_keys
            cleanup_detail = handler.cleanup_groups(
                {"type": [group_type], "key": [cleanup_groups["groups"][0]["group_key"]]}
            )
            assert cleanup_detail["records"], f"Expected cleanup group records for {group_type}"
            detail_guidance = cleanup_detail["guidance"]
            assert detail_guidance["priority"] in {"High", "Medium", "Low"}
            assert detail_guidance["score"] >= group_guidance["score"]
            assert detail_guidance["action"]
            assert detail_guidance["reasons"]
            group_key = cleanup_groups["groups"][0]["group_key"]
            if group_type == "duplicate_tags":
                assert cleanup_detail["merge_draft"] is None
                assert cleanup_detail["aliases"], "Expected duplicate tag aliases"
                assert cleanup_detail["counts"]["definition_count"] > 1
                assert cleanup_detail["counts"]["display_name"]
                tag_matches = handler.cleanup_groups(
                    {"type": [group_type], "q": [cleanup_detail["counts"]["display_name"]], "page_size": ["50"]}
                )
                assert any(group["group_key"] == group_key for group in tag_matches["groups"])
            else:
                name_query = next((record["name"] for record in cleanup_detail["records"] if record.get("name")), None)
                phone_query = next(
                    ((record.get("phone") or record.get("mobile")) for record in cleanup_detail["records"] if record.get("phone") or record.get("mobile")),
                    None,
                )
                if name_query:
                    name_matches = handler.cleanup_groups({"type": [group_type], "q": [name_query], "page_size": ["50"]})
                    assert any(group["group_key"] == group_key for group in name_matches["groups"])
                if phone_query:
                    phone_matches = handler.cleanup_groups({"type": [group_type], "q": [phone_query], "page_size": ["50"]})
                    assert any(group["group_key"] == group_key for group in phone_matches["groups"])
                assert cleanup_detail["field_comparison"], f"Expected cleanup field comparisons for {group_type}"
                for comparison in cleanup_detail["field_comparison"]:
                    assert comparison["field_name"]
                    assert comparison["distinct_count"] >= 2
                    assert len(comparison["values"]) == len(cleanup_detail["records"])
                assert any("Most complete" in record["badges"] for record in cleanup_detail["records"])
                merge_draft = cleanup_detail["merge_draft"]
                assert merge_draft
                assert merge_draft["keeper"]["record_key"]
                assert merge_draft["keeper"]["record_type"] in {"person", "lead"}
                assert merge_draft["keeper"]["completeness_score"] >= 1
                assert merge_draft["warnings"]
                assert any("Draft only" in warning for warning in merge_draft["warnings"])
                if group_type == "lead_person_overlap":
                    assert any("user decision" in warning for warning in merge_draft["warnings"])
                    assert merge_draft["keeper"]["record_type"] == "person"
                assert "fill_suggestions" in merge_draft
                assert "conflicts" in merge_draft
                assert merge_draft["fill_suggestions"] or merge_draft["conflicts"]
                for suggestion in merge_draft["fill_suggestions"]:
                    assert suggestion["field_name"]
                    assert suggestion["value"]
                    assert suggestion["from_record_key"]
                for conflict in merge_draft["conflicts"]:
                    assert conflict["field_name"]
                    assert conflict["alternatives"]
            for record in cleanup_detail["records"]:
                assert "stats" in record
                if record["record_type"] in {"person", "lead"}:
                    assert "profile_summary" in record
                    assert isinstance(record["profile_summary"], list)
                assert record["completeness_score"] == record["stats"]["completeness_score"]
                if group_type != "duplicate_tags":
                    assert record["stats"]["core_field_count"] >= 1
                for stat in [
                    "address_count",
                    "tag_count",
                    "note_count",
                    "task_count",
                    "open_task_count",
                    "deal_count",
                    "custom_field_count",
                ]:
                    assert record["stats"][stat] >= 0
        custom_fields = handler.custom_fields({"page_size": ["10"]})
        assert custom_fields["fields"], "Expected custom field summaries"
        profile_decision = custom_fields["application_profile_decision"]
        assert profile_decision["recommendation"] == "Read-only until cleanup"
        assert profile_decision["lead_profile_records"] >= 1327
        assert profile_decision["person_profile_records"] >= 50
        assert profile_decision["value_rows"] >= 13626
        assert len(profile_decision["editable_after_cleanup_fields"]) == 3
        assert len(profile_decision["read_only_history_fields"]) == 7
        assert profile_decision["cleanup_conflict_groups"] >= 39
        assert profile_decision["cleanup_fill_gap_groups"] >= 9
        assert profile_decision["report"] == "/reports/application_profile_editability_review.md"
        app_js = (server.PROJECT_ROOT / "crm_app" / "static" / "app.js").read_text(encoding="utf-8")
        assert "Application Profile Evidence" in app_js
        assert 'data-key="application_profile_editability"' in app_js
        assert "Duplicate Tag Evidence" in app_js
        assert 'data-key="duplicate_tag_policy"' in app_js
        assert "Show Tag Batch Candidates" in app_js
        assert "Lead/Person Overlap Evidence" in app_js
        assert 'data-key="lead_person_overlap_policy"' in app_js
        assert "Show Overlap Review" in app_js
        assert "Duplicate People Evidence" in app_js
        assert 'data-key="${escapeHtml(options.decisionKey)}"' in app_js
        assert "duplicate_people_merge_policy" in app_js
        assert "Show People Review" in app_js
        assert "Duplicate Leads Evidence" in app_js
        assert "duplicate_leads_merge_policy" in app_js
        assert "Show Leads Review" in app_js
        assert "Guided Review Queue" in app_js
        assert "queue-review-button" in app_js
        assert "Open Policy" in app_js
        assert "Export Drafts" in app_js
        assert "Review remaining" in app_js
        assert "Save & Next" in app_js
        assert "nextCleanupReviewGroup" in app_js
        assert "activityRecordLink" in app_js
        assert "activity-target" in app_js
        assert "activitySearch" in app_js
        assert "activityTypeFilter" in app_js
        assert "activityRecordTypeFilter" in app_js
        assert "activityDateFrom" in app_js
        assert "activityDateTo" in app_js
        assert "activitySavedViewControls" in app_js
        assert "saveActivityViewButton" in app_js
        assert "customFieldRecordTypeFilter" in app_js
        assert "customFieldSavedView" in app_js
        assert "currentCustomFieldSettings" in app_js
        assert "applyCustomFieldSettings" in app_js
        custom_field = custom_fields["fields"][0]
        custom_detail = handler.custom_fields(
            {
                "record_type": [custom_field["record_type"]],
                "field_name": [custom_field["field_name"]],
                "page_size": ["10"],
            }
        )
        assert custom_detail["records"], "Expected custom field records"
        lead_custom_fields = handler.custom_fields({"record_type": ["lead"], "page_size": ["100"]})
        assert lead_custom_fields["record_type"] == "lead"
        assert lead_custom_fields["total"] >= 1
        assert all(field["record_type"] == "lead" for field in lead_custom_fields["fields"])
        lead_summary_export = handler.export_rows({"type": ["custom_field_summary"], "record_type": ["lead"]})
        assert lead_summary_export["filename"] == "local_crm_custom_field_summary_filtered.csv"
        assert len(lead_summary_export["rows"]) == lead_custom_fields["total"]
        assert all(row["record_type"] == "lead" for row in lead_summary_export["rows"])
        custom_field_saved_view = handler.save_view(
            {
                "type": "custom_fields",
                "name": "Verification Lead Custom Fields",
                "settings": {"record_type": "lead"},
            }
        )
        assert custom_field_saved_view["ok"]
        assert custom_field_saved_view["view"]["settings"]["record_type"] == "lead"
        assert custom_field_saved_view["view"]["record_count"] == lead_custom_fields["total"]
        custom_field_saved_views = handler.saved_views({"type": ["custom_fields"]})
        assert any(view["id"] == custom_field_saved_view["view"]["id"] for view in custom_field_saved_views["views"])
        assert any(view["id"] == custom_field_saved_view["view"]["id"] for view in handler.summary()["saved_views"])
        manifest = handler.export_manifest()
        assert any(item["type"] == "people" for item in manifest["exports"])
        assert any(item["type"] == "linked_resources" for item in manifest["exports"])
        assert any(item["type"] == "imported_archive" for item in manifest["exports"])
        assert any(item["type"] == "application_profiles" for item in manifest["exports"])
        assert any(item["type"] == "project_decisions" for item in manifest["exports"])
        assert any(item["type"] == "followup_transition_plan" for item in manifest["exports"])
        assert any(item["type"] == "daily_operating_guide" for item in manifest["exports"])
        assert any(item["type"] == "archive_review_worklist" for item in manifest["exports"])
        assert any(item["type"] == "archive_review_triage" for item in manifest["exports"])
        assert any(item["type"] == "archive_association_audit" for item in manifest["exports"])
        assert any(item["type"] == "backup_safety_ledger" for item in manifest["exports"])
        assert any(item["type"] == "migration_completion_audit" for item in manifest["exports"])
        assert any(item["type"] == "database_map" for item in manifest["exports"])
        assert any(item["type"] == "zendesk_independence" for item in manifest["exports"])
        assert any(item["type"] == "remote_admin_access_plan" for item in manifest["exports"])
        assert any(item["type"] == "remote_admin_permissions_matrix" for item in manifest["exports"])
        assert any(item["type"] == "remote_admin_implementation_blueprint" for item in manifest["exports"])
        assert any(item["type"] == "remote_admin_rollout_board" for item in manifest["exports"])
        assert any(item["type"] == "remote_hosting_decision_packet" for item in manifest["exports"])
        assert any(item["type"] == "remote_managed_cloud_provider_shortlist" for item in manifest["exports"])
        assert any(item["type"] == "remote_staging_pricing_preflight" for item in manifest["exports"])
        assert any(item["type"] == "remote_staging_setup_runbook" for item in manifest["exports"])
        assert any(item["type"] == "remote_staging_deployment_spec" for item in manifest["exports"])
        assert any(item["type"] == "remote_staging_validation_matrix" for item in manifest["exports"])
        assert any(item["type"] == "remote_admin_pilot_onboarding_plan" for item in manifest["exports"])
        assert any(item["type"] == "remote_production_cutover_checklist" for item in manifest["exports"])
        assert any(item["type"] == "hosted_database_migration_readiness" for item in manifest["exports"])
        assert any(item["type"] == "hosted_schema_draft" for item in manifest["exports"])
        assert any(item["type"] == "hosted_data_load_plan" for item in manifest["exports"])
        assert any(item["type"] == "lead_person_overlap_spot_check" for item in manifest["exports"])
        assert any(item["type"] == "duplicate_people_spot_check" for item in manifest["exports"])
        assert any(item["type"] == "duplicate_people_review_worksheet" for item in manifest["exports"])
        assert any(item["type"] == "duplicate_leads_spot_check" for item in manifest["exports"])
        assert any(item["type"] == "duplicate_leads_review_worksheet" for item in manifest["exports"])
        assert any(item["type"] == "decision_prep_packet" for item in manifest["exports"])
        assert any(item["type"] == "project_decision_ballot" for item in manifest["exports"])
        assert any(item["type"] == "project_decision_option_matrix" for item in manifest["exports"])
        assert any(item["type"] == "design_pipeline" for item in manifest["exports"])
        assert any(item["type"] == "cleanup_starter_packet" for item in manifest["exports"])
        assert any(item["type"] == "data_quality" for item in manifest["exports"])
        assert any(item["type"] == "cleanup_merge_drafts" for item in manifest["exports"])
        assert manifest["bulk_export"]["enabled"] is True
        assert manifest["bulk_export"]["mode"] == "enabled"
        assert manifest["package"]["url"] == "/api/export_package"
        assert manifest["package"]["enabled"] is True
        assert "SQLite database" in manifest["package"]["contents"]
        document_package = manifest["document_package"]
        assert document_package["url"] == "/api/export_document_files_package"
        assert document_package["enabled"] is True
        assert document_package["available"] is True
        assert document_package["file_count"] >= 203
        assert document_package["bytes"] > 100_000_000
        document_entries = handler.document_file_package_entries()
        assert len(document_entries) == document_package["file_count"]
        assert sum(entry["bytes"] for entry in document_entries) == document_package["bytes"]
        assert all(entry["path"].exists() and entry["archive_path"].startswith("document_files/") for entry in document_entries)
        document_manifest_rows = handler.document_file_package_manifest_rows(document_entries)
        assert len(document_manifest_rows) == document_package["file_count"]
        assert any(row["package_path"].startswith("document_files/") and row["local_file"] for row in document_manifest_rows)
        package = handler.export_package()
        assert package["filename"].startswith("local_crm_complete_package_")
        assert package["filename"].endswith(".zip")
        assert package["manifest"]["database"]["path"] == "database/local_crm.sqlite"
        with zipfile.ZipFile(io.BytesIO(package["payload"])) as package_zip:
            package_names = set(package_zip.namelist())
            assert "package_manifest.json" in package_names
            assert "database/local_crm.sqlite" in package_names
            assert "csv/local_crm_people.csv" in package_names
            assert "csv/local_crm_project_decisions.csv" in package_names
            assert "csv/local_crm_followup_transition_plan.csv" in package_names
            assert "csv/local_crm_daily_operating_guide.csv" in package_names
            assert "csv/local_crm_archive_review_worklist.csv" in package_names
            assert "csv/local_crm_archive_review_triage.csv" in package_names
            assert "csv/local_crm_archive_association_audit.csv" in package_names
            assert "csv/local_crm_backup_safety_ledger.csv" in package_names
            assert "csv/local_crm_migration_completion_audit.csv" in package_names
            assert "csv/local_crm_database_map.csv" in package_names
            assert "csv/local_crm_zendesk_independence_checklist.csv" in package_names
            assert "csv/local_crm_remote_admin_access_plan.csv" in package_names
            assert "csv/local_crm_remote_admin_permissions_matrix.csv" in package_names
            assert "csv/local_crm_remote_admin_implementation_blueprint.csv" in package_names
            assert "csv/local_crm_remote_admin_rollout_board.csv" in package_names
            assert "csv/local_crm_remote_hosting_decision_packet.csv" in package_names
            assert "csv/local_crm_remote_managed_cloud_provider_shortlist.csv" in package_names
            assert "csv/local_crm_remote_staging_pricing_preflight.csv" in package_names
            assert "csv/local_crm_remote_staging_setup_runbook.csv" in package_names
            assert "csv/local_crm_remote_staging_deployment_spec.csv" in package_names
            assert "csv/local_crm_remote_staging_validation_matrix.csv" in package_names
            assert "csv/local_crm_remote_admin_pilot_onboarding_plan.csv" in package_names
            assert "csv/local_crm_remote_production_cutover_checklist.csv" in package_names
            assert "csv/local_crm_hosted_database_migration_readiness.csv" in package_names
            assert "csv/local_crm_hosted_schema_draft.csv" in package_names
            assert "csv/local_crm_hosted_data_load_plan.csv" in package_names
            assert "csv/local_crm_lead_person_overlap_spot_check.csv" in package_names
            assert "csv/local_crm_duplicate_people_spot_check.csv" in package_names
            assert "csv/local_crm_duplicate_people_review_worksheet.csv" in package_names
            assert "csv/local_crm_duplicate_leads_spot_check.csv" in package_names
            assert "csv/local_crm_duplicate_leads_review_worksheet.csv" in package_names
            assert "csv/local_crm_decision_prep_packet.csv" in package_names
            assert "csv/local_crm_project_decision_ballot.csv" in package_names
            assert "csv/local_crm_project_decision_option_matrix.csv" in package_names
            assert "csv/local_crm_design_pipeline.csv" in package_names
            assert "csv/local_crm_cleanup_starter_packet.csv" in package_names
            assert "csv/local_crm_data_quality.csv" in package_names
            assert "reports/daily_operating_guide.md" in package_names
            assert "reports/daily_operating_guide.csv" in package_names
            assert "reports/archive_review_worklist.md" in package_names
            assert "reports/archive_review_worklist.csv" in package_names
            assert "reports/archive_review_triage.md" in package_names
            assert "reports/archive_review_triage.csv" in package_names
            assert "reports/archive_association_audit.md" in package_names
            assert "reports/archive_association_audit.csv" in package_names
            assert "reports/backup_safety_ledger.md" in package_names
            assert "reports/backup_safety_ledger.csv" in package_names
            assert "reports/migration_completion_audit.md" in package_names
            assert "reports/migration_completion_audit.csv" in package_names
            assert "reports/local_crm_database_map.md" in package_names
            assert "reports/local_crm_database_map.csv" in package_names
            assert "reports/zendesk_independence_checklist.md" in package_names
            assert "reports/zendesk_independence_checklist.csv" in package_names
            assert "reports/remote_admin_access_plan.md" in package_names
            assert "reports/remote_admin_access_plan.csv" in package_names
            assert "reports/remote_admin_permissions_matrix.md" in package_names
            assert "reports/remote_admin_permissions_matrix.csv" in package_names
            assert "reports/remote_admin_implementation_blueprint.md" in package_names
            assert "reports/remote_admin_implementation_blueprint.csv" in package_names
            assert "reports/remote_admin_rollout_board.md" in package_names
            assert "reports/remote_admin_rollout_board.csv" in package_names
            assert "reports/remote_hosting_decision_packet.md" in package_names
            assert "reports/remote_hosting_decision_packet.csv" in package_names
            assert "reports/remote_managed_cloud_provider_shortlist.md" in package_names
            assert "reports/remote_managed_cloud_provider_shortlist.csv" in package_names
            assert "reports/remote_staging_pricing_preflight.md" in package_names
            assert "reports/remote_staging_pricing_preflight.csv" in package_names
            assert "reports/remote_staging_setup_runbook.md" in package_names
            assert "reports/remote_staging_setup_runbook.csv" in package_names
            assert "reports/remote_staging_deployment_spec.md" in package_names
            assert "reports/remote_staging_deployment_spec.csv" in package_names
            assert "reports/remote_staging_validation_matrix.md" in package_names
            assert "reports/remote_staging_validation_matrix.csv" in package_names
            assert "reports/remote_admin_pilot_onboarding_plan.md" in package_names
            assert "reports/remote_admin_pilot_onboarding_plan.csv" in package_names
            assert "reports/remote_production_cutover_checklist.md" in package_names
            assert "reports/remote_production_cutover_checklist.csv" in package_names
            assert "reports/cutover_rollback_package_readiness.md" in package_names
            assert "reports/cutover_rollback_package_readiness.csv" in package_names
            assert "reports/vercel_environment_readiness.md" in package_names
            assert "reports/vercel_environment_readiness.csv" in package_names
            assert "reports/vercel_public_protection.md" in package_names
            assert "reports/vercel_public_protection.csv" in package_names
            assert "reports/hosted_deployment_freshness.md" in package_names
            assert "reports/hosted_deployment_freshness.csv" in package_names
            assert "reports/hosted_redeploy_preflight.md" in package_names
            assert "reports/hosted_redeploy_preflight.csv" in package_names
            assert "reports/supabase_staging_refresh_preflight.md" in package_names
            assert "reports/supabase_staging_refresh_preflight.csv" in package_names
            assert "reports/supabase_staging_refresh_run.md" in package_names
            assert "reports/supabase_staging_refresh_run.csv" in package_names
            assert "reports/supabase_staging_data_parity.md" in package_names
            assert "reports/supabase_staging_data_parity.csv" in package_names
            assert "reports/remote_monitoring_readiness.md" in package_names
            assert "reports/remote_monitoring_readiness.csv" in package_names
            assert "reports/remote_monitoring_signoff.md" in package_names
            assert "reports/remote_monitoring_signoff.csv" in package_names
            assert "reports/hosted_write_unlock_audit_rehearsal.md" in package_names
            assert "reports/hosted_write_unlock_audit_rehearsal.csv" in package_names
            assert "reports/hosted_write_audit_execution.md" in package_names
            assert "reports/hosted_write_audit_execution.csv" in package_names
            assert "reports/remaining_gate_guardrails.md" in package_names
            assert "reports/remaining_gate_guardrails.csv" in package_names
            assert "reports/remaining_gate_execution_readiness.md" in package_names
            assert "reports/remaining_gate_execution_readiness.csv" in package_names
            assert "reports/private_execution_inputs.md" in package_names
            assert "reports/private_execution_inputs.csv" in package_names
            assert "reports/owner_confirmed_production_wave.md" in package_names
            assert "reports/owner_confirmed_production_wave.csv" in package_names
            assert "reports/secret_handling_boundaries.md" in package_names
            assert "reports/secret_handling_boundaries.csv" in package_names
            assert "reports/local_write_freeze_readiness.md" in package_names
            assert "reports/local_write_freeze_readiness.csv" in package_names
            assert "reports/owner_shakedown_signoff.md" in package_names
            assert "reports/owner_shakedown_signoff.csv" in package_names
            assert "reports/safe_production_gate_runner.md" in package_names
            assert "reports/safe_production_gate_runner.csv" in package_names
            assert "reports/remaining_production_gates_packet.md" in package_names
            assert "reports/remaining_production_gates_packet.csv" in package_names
            assert "reports/owner_gate_intake_packet.md" in package_names
            assert "reports/owner_gate_intake_packet.csv" in package_names
            assert "reports/owner_gate_reply_validation.md" in package_names
            assert "reports/owner_gate_reply_validation.csv" in package_names
            assert "reports/owner_approved_wave_packet.md" in package_names
            assert "reports/owner_approved_wave_packet.csv" in package_names
            assert "reports/owner_recovery_closure.md" in package_names
            assert "reports/owner_recovery_closure.csv" in package_names
            assert "reports/owner_recovery_disable_run.md" in package_names
            assert "reports/owner_recovery_disable_run.csv" in package_names
            assert "reports/source_of_truth_cutover_preflight.md" in package_names
            assert "reports/source_of_truth_cutover_preflight.csv" in package_names
            assert "reports/source_of_truth_cutover_approval.md" in package_names
            assert "reports/source_of_truth_cutover_approval.csv" in package_names
            assert "reports/remote_production_readiness.md" in package_names
            assert "reports/remote_production_readiness.csv" in package_names
            assert "reports/hosted_database_migration_readiness.md" in package_names
            assert "reports/hosted_database_migration_readiness.csv" in package_names
            assert "reports/hosted_database_schema_draft.md" in package_names
            assert "reports/hosted_database_schema_draft.csv" in package_names
            assert "reports/hosted_database_schema_draft.sql" in package_names
            assert "reports/hosted_database_data_load_plan.md" in package_names
            assert "reports/hosted_database_data_load_plan.csv" in package_names
            assert "reports/lead_person_overlap_spot_check.md" in package_names
            assert "reports/lead_person_overlap_spot_check.csv" in package_names
            assert "reports/duplicate_people_spot_check.md" in package_names
            assert "reports/duplicate_people_spot_check.csv" in package_names
            assert "reports/duplicate_people_review_worksheet.md" in package_names
            assert "reports/duplicate_people_review_worksheet.csv" in package_names
            assert "reports/duplicate_leads_spot_check.md" in package_names
            assert "reports/duplicate_leads_spot_check.csv" in package_names
            assert "reports/duplicate_leads_review_worksheet.md" in package_names
            assert "reports/duplicate_leads_review_worksheet.csv" in package_names
            assert "reports/followup_transition_plan.md" in package_names
            assert "reports/followup_transition_plan.csv" in package_names
            assert "reports/decision_prep_packet.md" in package_names
            assert "reports/decision_prep_packet.csv" in package_names
            assert "reports/project_decision_ballot.md" in package_names
            assert "reports/project_decision_ballot.csv" in package_names
            assert "reports/project_decision_option_matrix.md" in package_names
            assert "reports/project_decision_option_matrix.csv" in package_names
            assert "reports/apple_style_redesign_pipeline.md" in package_names
            assert "reports/apple_style_redesign_pipeline.csv" in package_names
            assert "reports/cleanup_review_starter_packet.md" in package_names
            assert "reports/cleanup_review_starter_packet.csv" in package_names
            assert "reports/project_decision_brief.md" in package_names
            assert "reports/local_crm_data_quality.md" in package_names
            assert "README.md" in package_names
            assert "docs/operating_notes.md" in package_names
            package_manifest = json.loads(package_zip.read("package_manifest.json").decode("utf-8"))
            assert package_manifest["database"]["path"] == "database/local_crm.sqlite"
            assert any(item["path"] == "csv/local_crm_people.csv" and item["rows"] >= 997 for item in package_manifest["csv_exports"])
            assert any(item["path"] == "csv/local_crm_followup_transition_plan.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/followup_transition_plan.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_daily_operating_guide.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/daily_operating_guide.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_archive_review_worklist.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/archive_review_worklist.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_archive_review_triage.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/archive_review_triage.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_archive_association_audit.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/archive_association_audit.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_backup_safety_ledger.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/backup_safety_ledger.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_migration_completion_audit.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/migration_completion_audit.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_database_map.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/local_crm_database_map.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_zendesk_independence_checklist.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/zendesk_independence_checklist.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_admin_access_plan.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_admin_access_plan.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_admin_permissions_matrix.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_admin_permissions_matrix.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_admin_implementation_blueprint.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_admin_implementation_blueprint.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_admin_rollout_board.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_admin_rollout_board.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_hosting_decision_packet.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_hosting_decision_packet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_managed_cloud_provider_shortlist.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_managed_cloud_provider_shortlist.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_staging_pricing_preflight.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_staging_pricing_preflight.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_staging_setup_runbook.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_staging_setup_runbook.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_staging_deployment_spec.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_staging_deployment_spec.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_staging_validation_matrix.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_staging_validation_matrix.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_admin_pilot_onboarding_plan.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_admin_pilot_onboarding_plan.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_remote_production_cutover_checklist.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/remote_production_cutover_checklist.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/cutover_rollback_package_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/cutover_rollback_package_readiness.csv" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/vercel_environment_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/vercel_public_protection.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/hosted_deployment_freshness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/hosted_redeploy_preflight.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/supabase_staging_refresh_preflight.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/supabase_staging_refresh_run.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/supabase_staging_data_parity.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remote_monitoring_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remote_monitoring_signoff.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/hosted_write_unlock_audit_rehearsal.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/hosted_write_audit_execution.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remaining_gate_guardrails.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remaining_gate_execution_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/private_execution_inputs.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_confirmed_production_wave.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/secret_handling_boundaries.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/local_write_freeze_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_shakedown_signoff.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/safe_production_gate_runner.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remaining_production_gates_packet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_gate_intake_packet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_gate_reply_validation.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_approved_wave_packet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_recovery_closure.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/owner_recovery_disable_run.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/source_of_truth_cutover_preflight.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/source_of_truth_cutover_approval.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/remote_production_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_hosted_database_migration_readiness.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/hosted_database_migration_readiness.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_hosted_schema_draft.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/hosted_database_schema_draft.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/hosted_database_schema_draft.sql" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_hosted_data_load_plan.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/hosted_database_data_load_plan.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_lead_person_overlap_spot_check.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/lead_person_overlap_spot_check.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_duplicate_people_spot_check.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/duplicate_people_spot_check.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_duplicate_people_review_worksheet.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/duplicate_people_review_worksheet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_duplicate_leads_spot_check.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/duplicate_leads_spot_check.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_duplicate_leads_review_worksheet.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/duplicate_leads_review_worksheet.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_project_decision_ballot.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/project_decision_ballot.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_project_decision_option_matrix.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/project_decision_option_matrix.md" for item in package_manifest["reports"])
            assert any(item["path"] == "csv/local_crm_design_pipeline.csv" for item in package_manifest["csv_exports"])
            assert any(item["path"] == "reports/apple_style_redesign_pipeline.md" for item in package_manifest["reports"])
            assert any(item["path"] == "reports/project_decision_brief.md" for item in package_manifest["reports"])
        migration_status = handler.migration_status()
        assert migration_status["counts"]["people"] >= 997
        assert migration_status["counts"]["linked_resources"] >= 27
        assert migration_status["counts"]["archive_items"] >= 884
        assert migration_status["imported_archive"]["total"] >= 884
        archive_association = migration_status["imported_archive"]["association"]
        archive_association_summary = archive_association["summary"]
        assert archive_association["report"] == "/reports/archive_association_audit.md"
        assert archive_association_summary["linked_archive_items"] >= 400
        assert archive_association_summary["unlinked_archive_items"] >= 400
        assert archive_association_summary["link_coverage_percent"] > 40
        assert archive_association_summary["linked_documents"] >= 203
        assert archive_association_summary["document_total"] >= 203
        assert archive_association_summary["document_file_coverage_percent"] == 100
        assert archive_association_summary["exact_phone_candidates"] == 0
        assert archive_association_summary["unlinked_unreviewed_call_texts"] >= 1
        assert migration_status["snapshot"]["snapshot_name"]
        assert migration_status["optional_sweep"]["status"] in {"complete", "waiting_for_token"}
        assert migration_status["cleanup"]["status_counts"]["open"] >= 1
        assert migration_status["reports"]
        production_gates = migration_status["production_gates"]
        assert production_gates["latest_url"].startswith("https://chillcrm-")
        assert production_gates["passed"] >= 15
        assert production_gates["failed"] == 0
        blocking_gate_keys = {item["key"] for item in production_gates["blocking_gate_items"]}
        redeploy_required = "hosted_deployment_freshness" in blocking_gate_keys
        allowed_blocking_gate_keys = {
            "hosted_write_unlock_audit_rehearsal",
            "remote_monitoring_readiness",
            "owner_shakedown_signoff",
            "source_of_truth_cutover_approval",
            "supabase_provider_backup",
            "newest_hosted_smoke",
            "hosted_deployment_freshness",
        }
        assert blocking_gate_keys <= allowed_blocking_gate_keys
        if blocking_gate_keys:
            assert {"owner_shakedown_signoff", "source_of_truth_cutover_approval"} & blocking_gate_keys
        else:
            assert production_gates["production_gate"] == "pass"
            assert production_gates["status"] == "ready_for_owner_cutover_review"
        assert production_gates["input_required"] == len(blocking_gate_keys)
        assert production_gates["blocking_gates"] == len(blocking_gate_keys)
        hosted_write_enablement_status = (production_gates.get("hosted_write_enablement") or {}).get("status")
        if production_gates["production_gate"] != "pass":
            expected_source_of_truth = "local_sqlite"
        elif hosted_write_enablement_status == "hosted_writes_enabled":
            expected_source_of_truth = "hosted_remote_crm"
        else:
            expected_source_of_truth = "hosted_ready_for_owner_cutover_review"
        assert production_gates["source_of_truth"] == expected_source_of_truth
        if "hosted_write_unlock_audit_rehearsal" in blocking_gate_keys:
            assert production_gates["next_owner_action"]["title"] == "Hosted write-audit rehearsal"
            assert "controlled staging-only write rehearsal" in production_gates["next_owner_action"]["detail"]
            assert production_gates["next_owner_action"]["owner_reply"] == "I approve the hosted write-audit rehearsal"
            assert {link["url"] for link in production_gates["next_owner_action"]["proof_links"]} == {
                "/reports/hosted_write_unlock_audit_rehearsal.md",
                "/reports/hosted_write_audit_execution.md",
            }
        if redeploy_required:
            assert production_gates["next_operator_action"]["title"] == "Redeploy current hosted runtime"
            assert production_gates["next_operator_action"]["input"] == "Redeploy current local runtime to Vercel and rerun hosted smoke"
            assert {link["url"] for link in production_gates["next_operator_action"]["proof_links"]} == {
                "/reports/owner_approved_wave_packet.md",
                "/reports/hosted_redeploy_preflight.md",
                "/reports/hosted_deployment_freshness.md",
                "/reports/vercel_hosted_app_smoke.md",
            }
            assert production_gates["next_production_action"]["title"] == "Redeploy current hosted runtime"
            assert production_gates["next_production_action"]["input"] == "Redeploy current local runtime to Vercel and rerun hosted smoke"
        elif "supabase_provider_backup" in blocking_gate_keys:
            assert production_gates["next_operator_action"]["title"] == "Supabase backup evidence"
            assert production_gates["next_operator_action"]["input"] == "Supabase Management API access token or Dashboard backup evidence"
            assert {link["url"] for link in production_gates["next_operator_action"]["proof_links"]} == {
                "/reports/supabase_backup_readiness.md",
            }
            assert production_gates["next_production_action"]["title"] == "Supabase backup evidence"
            assert production_gates["next_production_action"]["input"] == "Supabase Management API access token or Dashboard backup evidence"
        if "hosted_write_unlock_audit_rehearsal" in blocking_gate_keys:
            write_audit_gate = next(item for item in production_gates["blocking_gate_items"] if item["key"] == "hosted_write_unlock_audit_rehearsal")
            assert {link["url"] for link in write_audit_gate["source_links"]} == {
                "/reports/hosted_write_unlock_audit_rehearsal.md",
                "/reports/hosted_write_audit_execution.md",
            }
        expected_needed_input_order = []
        if "newest_hosted_smoke" in blocking_gate_keys:
            expected_needed_input_order.append("Owner email and owner password")
        if redeploy_required:
            expected_needed_input_order.append("Redeploy current local runtime to Vercel and rerun hosted smoke")
        if "supabase_provider_backup" in blocking_gate_keys:
            expected_needed_input_order.append("Supabase Management API access token or Dashboard backup evidence")
        if "hosted_write_unlock_audit_rehearsal" in blocking_gate_keys:
            expected_needed_input_order.append("Owner approval for hosted write-audit rehearsal")
        if "remote_monitoring_readiness" in blocking_gate_keys:
            expected_needed_input_order.append("Monitoring owner/cadence approval")
        if "owner_shakedown_signoff" in blocking_gate_keys:
            expected_needed_input_order.append("Owner shakedown signoff")
        if "source_of_truth_cutover_approval" in blocking_gate_keys:
            expected_needed_input_order.append("Owner source-of-truth cutover approval")
        assert [item["order"] for item in production_gates["needed_inputs"]] == list(
            range(1, len(expected_needed_input_order) + 1)
        )
        assert [item["input"] for item in production_gates["needed_inputs"]] == expected_needed_input_order
        if "hosted_write_unlock_audit_rehearsal" in blocking_gate_keys:
            write_audit_input = next(item for item in production_gates["needed_inputs"] if item["input"] == "Owner approval for hosted write-audit rehearsal")
            assert {link["url"] for link in write_audit_input["proof_links"]} == {
                "/reports/hosted_write_unlock_audit_rehearsal.md",
                "/reports/hosted_write_audit_execution.md",
            }
        if "supabase_provider_backup" in blocking_gate_keys:
            backup_input = next(item for item in production_gates["needed_inputs"] if item["input"] == "Supabase Management API access token or Dashboard backup evidence")
            assert {link["url"] for link in backup_input["proof_links"]} == {
                "/reports/supabase_backup_readiness.md",
            }
        assert production_gates["reports"]["readiness"] == "/reports/remote_production_readiness.md"
        assert production_gates["reports"]["remaining_packet"] == "/reports/remaining_production_gates_packet.md"
        assert production_gates["reports"]["owner_intake"] == "/reports/owner_gate_intake_packet.md"
        assert production_gates["reports"]["owner_wave"] == "/reports/owner_approved_wave_packet.md"
        assert production_gates["reports"]["secret_boundaries"] == "/reports/secret_handling_boundaries.md"
        export_package_status = migration_status["export_packages"]
        assert export_package_status["status"] == "complete"
        assert export_package_status["ready_count"] == export_package_status["total_count"] == 2
        assert export_package_status["bulk_export"]["enabled"] is True
        assert export_package_status["core_package"]["ready"] is True
        assert export_package_status["core_package"]["enabled"] is True
        assert export_package_status["core_package"]["url"] == "/api/export_package"
        assert export_package_status["document_package"]["ready"] is True
        assert export_package_status["document_package"]["enabled"] is True
        assert export_package_status["document_package"]["url"] == "/api/export_document_files_package"
        assert export_package_status["document_package"]["file_count"] >= 203
        assert export_package_status["document_package"]["bytes"] > 100_000_000
        readiness_by_title = {item["title"]: item for item in migration_status["readiness"]}
        export_readiness = readiness_by_title["Portable export packages ready"]
        assert export_readiness["status"] == "complete"
        assert export_readiness["view"] == "exports"
        assert "recovered document files" in export_readiness["detail"]
        assert migration_status["project_decisions"]["total"] == len(server.PROJECT_DECISIONS)
        assert sum(migration_status["project_decisions"]["status_counts"].values()) == len(server.PROJECT_DECISIONS)
        assert all(decision["recommended_option"] for decision in migration_status["project_decisions"]["decisions"])
        assert all(decision["impact"]["summary"] and decision["impact"]["facts"] for decision in migration_status["project_decisions"]["decisions"])
        assert all(decision["sequence"]["step"] >= 1 for decision in migration_status["project_decisions"]["decisions"])
        assert len(migration_status["project_decisions"]["sequence"]) == len(server.PROJECT_DECISION_SEQUENCE)
        assert migration_status["project_decisions"]["sequence"][0]["key"] == "unlinked_archive_matching"
        assert migration_status["next_action"]["title"]
        assert migration_status["next_action"]["kind"] in {
            "project_decision",
            "backup",
            "cleanup_preview",
            "group_review",
            "stabilize",
        }
        active_pending_decisions = [
            item["decision"]
            for item in migration_status["project_decisions"]["sequence"]
            if (item.get("decision") or {}).get("status") == "pending"
        ]
        parked_deferred_decisions = [
            item["decision"]
            for item in migration_status["project_decisions"]["sequence"]
            if (item.get("decision") or {}).get("status") == "deferred"
        ]
        if migration_status["project_decisions"]["pending"]:
            assert migration_status["next_action"]["kind"] == "project_decision"
            assert migration_status["next_action"]["decision_key"] == active_pending_decisions[0]["key"]
            assert migration_status["next_action"]["choices"][0]["code"] == "A"
            assert any(choice["recommended"] for choice in migration_status["next_action"]["choices"])
            assert migration_status["next_action"]["recommended_code"] == "A"
            if active_pending_decisions[0]["key"] in {"duplicate_people_merge_policy", "duplicate_leads_merge_policy"}:
                assert migration_status["next_action"]["worksheet_report"]
                assert migration_status["next_action"]["worksheet_export_url"]
        elif parked_deferred_decisions:
            assert migration_status["next_action"]["kind"] == "project_decision"
            assert migration_status["next_action"]["decision_key"] == parked_deferred_decisions[0]["key"]
        decision_by_key = {
            item["decision"]["key"]: item["decision"]
            for item in migration_status["project_decisions"]["sequence"]
            if item.get("decision")
        }
        assert decision_by_key["duplicate_people_merge_policy"]["worksheet_report"] == "/reports/duplicate_people_review_worksheet.md"
        assert decision_by_key["duplicate_people_merge_policy"]["worksheet_export_url"] == "/api/export?type=duplicate_people_review_worksheet"
        assert decision_by_key["duplicate_leads_merge_policy"]["worksheet_report"] == "/reports/duplicate_leads_review_worksheet.md"
        assert decision_by_key["duplicate_leads_merge_policy"]["worksheet_export_url"] == "/api/export?type=duplicate_leads_review_worksheet"
        decision_prep = migration_status["decision_prep"]
        assert decision_prep["title"] == "Decision Prep Packet"
        assert decision_prep["export_url"] == "/api/export?type=decision_prep_packet"
        assert decision_prep["remaining_count"] == migration_status["project_decisions"]["pending"] + migration_status["project_decisions"]["deferred"]
        assert decision_prep["remaining_count"] == len(decision_prep["decisions"])
        if active_pending_decisions:
            assert decision_prep["decisions"][0]["key"] == active_pending_decisions[0]["key"]
        elif parked_deferred_decisions:
            assert decision_prep["decisions"][0]["key"] == parked_deferred_decisions[0]["key"]
        assert decision_prep["decisions"][0]["recommended_label"]
        assert decision_prep["decisions"][0]["facts"]
        prep_by_key = {decision["key"]: decision for decision in decision_prep["decisions"]}
        if "duplicate_people_merge_policy" in prep_by_key:
            assert prep_by_key["duplicate_people_merge_policy"]["worksheet_report"] == "/reports/duplicate_people_review_worksheet.md"
            assert prep_by_key["duplicate_people_merge_policy"]["worksheet_export_url"] == "/api/export?type=duplicate_people_review_worksheet"
        if "duplicate_leads_merge_policy" in prep_by_key:
            assert prep_by_key["duplicate_leads_merge_policy"]["worksheet_report"] == "/reports/duplicate_leads_review_worksheet.md"
            assert prep_by_key["duplicate_leads_merge_policy"]["worksheet_export_url"] == "/api/export?type=duplicate_leads_review_worksheet"
        cleanup_starter = migration_status["cleanup_starter"]
        assert cleanup_starter["title"] == "Cleanup Starter Packet"
        assert cleanup_starter["export_url"] == "/api/export?type=cleanup_starter_packet"
        assert cleanup_starter["report"] == "/reports/cleanup_review_starter_packet.md"
        assert cleanup_starter["group_count"] == len(cleanup_starter["groups"]) >= 1
        assert cleanup_starter["groups"][0]["group_type"] == "lead_person_overlap"
        assert cleanup_starter["groups"][0]["group_key"]
        daily_guide = migration_status["daily_guide"]
        assert daily_guide["title"] == "Daily Operating Guide"
        assert daily_guide["export_url"] == "/api/export?type=daily_operating_guide"
        assert daily_guide["report"] == "/reports/daily_operating_guide.md"
        daily_step_keys = {step["key"] for step in daily_guide["steps"]}
        assert {"followup", "pipeline", "quality", "archive_review", "decisions", "cleanup_starter", "source_exports"}.issubset(daily_step_keys)
        assert daily_guide["steps"][0]["key"] == "followup"
        assert daily_guide["steps"][0]["secondary_preset"] == "followup_imported_open"
        assert daily_guide["steps"][0]["report"] == "/reports/followup_transition_plan.md"
        assert daily_guide["steps"][0]["export_url"] == "/api/export?type=followup_transition_plan"
        archive_step = next(step for step in daily_guide["steps"] if step["key"] == "archive_review")
        assert archive_step["report"] == "/reports/archive_review_worklist.md"
        assert archive_step["export_url"] == "/api/export?type=archive_review_worklist"
        assert any(step["metrics"] for step in daily_guide["steps"])
        decision_by_key = {decision["key"]: decision for decision in migration_status["project_decisions"]["decisions"]}
        duplicate_people_facts = {fact["label"]: fact["value"] for fact in decision_by_key["duplicate_people_merge_policy"]["impact"]["facts"]}
        archive_facts = {fact["label"]: fact["value"] for fact in decision_by_key["unlinked_archive_matching"]["impact"]["facts"]}
        profile_facts = {fact["label"]: fact["value"] for fact in decision_by_key["application_profile_editability"]["impact"]["facts"]}
        assert duplicate_people_facts["Open groups"] >= 1
        assert archive_facts["Unlinked calls"] >= 1
        assert archive_facts["Unlinked texts"] >= 1
        assert profile_facts["Lead profile records"] >= 1
        assert any(report["name"] == "project_decision_brief.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "followup_transition_plan.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "daily_operating_guide.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "archive_review_worklist.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "archive_review_triage.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "archive_association_audit.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "backup_safety_ledger.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "migration_completion_audit.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "local_crm_database_map.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "zendesk_independence_checklist.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_admin_access_plan.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_admin_permissions_matrix.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_admin_implementation_blueprint.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_admin_rollout_board.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_hosting_decision_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_managed_cloud_provider_shortlist.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_staging_pricing_preflight.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_staging_setup_runbook.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_staging_deployment_spec.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_staging_validation_matrix.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_admin_pilot_onboarding_plan.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_production_cutover_checklist.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "local_write_freeze_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "cutover_rollback_package_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "supabase_backup_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "supabase_backup_evidence_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "vercel_environment_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "vercel_public_protection.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_deployment_freshness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_redeploy_preflight.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "supabase_staging_refresh_preflight.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "supabase_staging_refresh_run.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "supabase_staging_data_parity.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_monitoring_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_monitoring_signoff.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_write_unlock_audit_rehearsal.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_write_audit_execution.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remaining_gate_guardrails.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_shakedown_signoff.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "source_of_truth_cutover_preflight.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "source_of_truth_cutover_approval.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "safe_production_gate_runner.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remaining_gate_execution_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "private_execution_inputs.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_confirmed_production_wave.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "secret_handling_boundaries.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remaining_production_gates_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_approved_wave_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_gate_reply_validation.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "remote_production_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_recovery_closure.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "owner_recovery_disable_run.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_database_migration_readiness.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_database_schema_draft.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_database_schema_draft.sql" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_database_data_load_plan.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "hosted_postgres_adapter_smoke.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "lead_person_overlap_spot_check.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "duplicate_people_spot_check.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "duplicate_people_review_worksheet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "duplicate_leads_spot_check.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "duplicate_leads_review_worksheet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "decision_prep_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "project_decision_ballot.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "project_decision_option_matrix.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "apple_style_redesign_pipeline.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "cleanup_review_starter_packet.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "cleanup_merge_review_pack.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "duplicate_tag_spot_check.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "unlinked_archive_matching_candidates.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "application_profile_editability_review.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "local_crm_data_quality.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "project_decision_sequence.md" and report["exists"] for report in migration_status["reports"])
        assert any(report["name"] == "cleanup_execution_safety_plan.md" and report["exists"] for report in migration_status["reports"])
        data_quality = migration_status["data_quality"]
        data_quality_totals = data_quality["totals"]
        assert data_quality["report"] == "/reports/local_crm_data_quality.md"
        assert data_quality["export_url"] == "/reports/local_crm_data_quality.csv"
        assert data_quality_totals["attention_records"] >= 1
        assert data_quality_totals["missing_contact_channel"] >= 1
        assert data_quality_totals["people_missing_contact"] >= 1
        assert data_quality_totals["companies_missing_contact"] >= 1
        assert data_quality_totals["leads_missing_email"] >= 1
        assert data_quality_totals["deals_missing_value"] >= 1
        assert len(data_quality["priority_records"]) <= 8
        assert len(data_quality["people_missing_contact"]) <= 6
        assert len(data_quality["companies_missing_contact"]) <= 6
        assert len(data_quality["leads_missing_email"]) <= 6
        assert len(data_quality["deals_missing_value"]) <= 6
        expected_source_mix = {}
        with sqlite3.connect(test_db) as conn:
            for record_type, table, source_column, audit_record_type in [
                ("people", "people", "zendesk_contact_id", "person"),
                ("companies", "companies", "zendesk_contact_id", "company"),
                ("leads", "leads", "zendesk_lead_id", "lead"),
                ("deals", "deals", "zendesk_deal_id", "deal"),
            ]:
                imported = conn.execute(f"SELECT count(*) FROM {table} WHERE {source_column} IS NOT NULL").fetchone()[0]
                local = conn.execute(f"SELECT count(*) FROM {table} WHERE {source_column} IS NULL").fetchone()[0]
                changed = conn.execute(
                    f"""
                    SELECT count(*)
                    FROM {table} records
                    WHERE EXISTS (
                        SELECT 1
                        FROM audit_log al
                        WHERE al.record_type = ?
                          AND al.record_id = records.id
                    )
                    """,
                    (audit_record_type,),
                ).fetchone()[0]
                expected_source_mix[record_type] = {
                    "imported": imported,
                    "local": local,
                    "changed": changed,
                    "total": imported + local,
                }
        work_queue = migration_status["operational_work_queue"]
        assert work_queue["title"] == "Operating Work Queue"
        assert len(work_queue["cards"]) >= 5
        work_card_keys = {card["key"] for card in work_queue["cards"]}
        assert {"project_gate", "followup", "record_sources", "cleanup_review", "pipeline_focus", "data_quality", "archive_review", "archive_links", "recent_work"}.issubset(work_card_keys)
        followup_card = next(card for card in work_queue["cards"] if card["key"] == "followup")
        followup_metrics = {item["label"]: item["value"] for item in followup_card["metrics"]}
        assert followup_metrics["Open"] >= 1
        assert "Imported" in followup_metrics
        assert "Local" in followup_metrics
        assert "imported from Zendesk" in followup_card["detail"]
        archive_review_card = next(card for card in work_queue["cards"] if card["key"] == "archive_review")
        archive_review_metrics = {item["label"]: item["value"] for item in archive_review_card["metrics"]}
        assert archive_review_metrics["Unreviewed"] >= 1
        assert "Needs lookup" in archive_review_metrics
        assert archive_review_card["preset"] == "archive_review_unreviewed"
        assert archive_review_card["report"] == "/reports/archive_review_worklist.md"
        assert archive_review_card["secondary_report"] == "/reports/archive_review_worklist.csv"
        assert work_queue["archive_review"]["total"] >= 1
        assert work_queue["archive_review"]["top_numbers"]
        archive_links_card = next(card for card in work_queue["cards"] if card["key"] == "archive_links")
        assert archive_links_card["report"] == "/reports/archive_association_audit.md"
        assert archive_links_card["secondary_report"] == "/reports/archive_association_audit.csv"
        archive_links_metrics = {item["label"]: item["value"] for item in archive_links_card["metrics"]}
        assert archive_links_metrics["Documents"] >= 203
        source_mix = work_queue["source_mix"]
        source_rows = {row["type"]: row for row in source_mix["rows"]}
        assert set(expected_source_mix).issubset(source_rows)
        for record_type, expected_counts in expected_source_mix.items():
            source_row = source_rows[record_type]
            assert source_row["imported"] == expected_counts["imported"]
            assert source_row["local"] == expected_counts["local"]
            assert source_row["changed"] == expected_counts["changed"]
            assert source_row["total"] == expected_counts["total"]
            assert source_row["presets"]["imported"] == f"source_{record_type}_imported"
            assert source_row["presets"]["local"] == f"source_{record_type}_local"
            assert source_row["presets"]["changed"] == f"source_{record_type}_changed"
        source_totals = source_mix["totals"]
        assert source_totals["imported"] == sum(item["imported"] for item in expected_source_mix.values())
        assert source_totals["local"] == sum(item["local"] for item in expected_source_mix.values())
        assert source_totals["changed"] == sum(item["changed"] for item in expected_source_mix.values())
        assert source_totals["total"] == sum(item["total"] for item in expected_source_mix.values())
        assert source_mix["primary_preset"].startswith("source_")
        source_card = next(card for card in work_queue["cards"] if card["key"] == "record_sources")
        source_metrics = {item["label"]: item["value"] for item in source_card["metrics"]}
        assert source_card["preset"] == source_mix["primary_preset"]
        assert source_metrics["Imported"] == source_totals["imported"]
        assert source_metrics["Local only"] == source_totals["local"]
        assert source_metrics["Changed"] == source_totals["changed"]
        pipeline_card = next(card for card in work_queue["cards"] if card["key"] == "pipeline_focus")
        assert pipeline_card["preset"] == "active_deals"
        assert pipeline_card["secondary_preset"] == "new_leads"
        assert work_queue["pipeline_focus"]["active_deals"] >= 1
        assert work_queue["pipeline_focus"]["active_value"] >= 1
        assert work_queue["pipeline_focus"]["new_leads"] >= 1
        assert len(work_queue["pipeline_focus_items"]) <= 6
        assert len(work_queue["new_lead_items"]) <= 6
        assert all(row["type"] == "deal" for row in work_queue["pipeline_focus_items"])
        assert all(row["type"] == "lead" for row in work_queue["new_lead_items"])
        data_quality_card = next(card for card in work_queue["cards"] if card["key"] == "data_quality")
        data_quality_metrics = {item["label"]: item["value"] for item in data_quality_card["metrics"]}
        assert data_quality_card["report"] == "/reports/local_crm_data_quality.md"
        assert data_quality_card["secondary_report"] == "/reports/local_crm_data_quality.csv"
        assert data_quality_metrics["No contact"] == data_quality_totals["missing_contact_channel"]
        assert data_quality_metrics["Lead email gaps"] == data_quality_totals["leads_missing_email"]
        assert data_quality_metrics["No deal value"] == data_quality_totals["deals_missing_value"]
        assert work_queue["data_quality"]["totals"]["attention_records"] == data_quality_totals["attention_records"]
        assert len(work_queue["data_quality"]["priority_records"]) <= 8
        assert work_queue["cleanup_queue"]["totals"]["review_remaining"] >= 1
        assert work_queue["cleanup_queue"]["next_queue"]["group_type"] in {
            "lead_person_overlap",
            "duplicate_people",
            "duplicate_leads",
        }
        assert len(work_queue["upcoming_tasks"]) <= 6
        assert len(work_queue["recent_records"]) <= 6
        assert len(work_queue["local_change_items"]) <= 6
        assert work_queue["local_change_items"]
        assert all(
            row["activity_type"] in {"audit", "cleanup_decision", "project_decision"}
            for row in work_queue["local_change_items"]
        )
        assert len(work_queue["saved_views"]) <= 6
        assert any(card["view"] == "followup" for card in work_queue["cards"])
        assert any(card.get("secondary_view") == "linkedResources" for card in work_queue["cards"])
        recent_work_card = next(card for card in work_queue["cards"] if card["key"] == "recent_work")
        assert recent_work_card["preset"] == "local_changes"
        assert recent_work_card["action"] == "Open Local Changes"
        project_decision_export_rows = handler.export_project_decision_rows()
        assert len(project_decision_export_rows) == len(server.PROJECT_DECISIONS)
        assert all(row["after_save"] for row in project_decision_export_rows)
        assert all(row["save_creates_backup"] == "yes" for row in project_decision_export_rows)
        assert all("Activity" in row["save_records"] for row in project_decision_export_rows)
        assert all("merge" in row["save_does_not"] for row in project_decision_export_rows)
        assert all("rewrite" in row["save_does_not"] for row in project_decision_export_rows)
        assert all("backup first" in row["save_safety"] for row in project_decision_export_rows)
        assert all("Backups restore" in row["restore_path"] for row in project_decision_export_rows)
        redesign_export = next(row for row in project_decision_export_rows if row["key"] == "apple_native_redesign_timing")
        assert redesign_export["recommended_label"] == "After functional cleanup"
        assert redesign_export["report"] == "/reports/apple_style_redesign_pipeline.md"
        cleanup_execution_preview = migration_status["cleanup_execution_preview"]
        assert cleanup_execution_preview["non_destructive"] is True
        assert cleanup_execution_preview["status"] in {"locked", "preview_ready", "waiting_for_group_decisions", "no_actions"}
        assert cleanup_execution_preview["totals"]["open_groups"] >= 1
        assert cleanup_execution_preview["totals"]["cleanup_policy_decisions_required"] == 4
        assert cleanup_execution_preview["warnings"]
        assert {action["action_type"] for action in cleanup_execution_preview["actions"]} == {
            "merge_duplicate_people",
            "merge_duplicate_leads",
            "merge_lead_person_overlaps",
            "mark_duplicate_tags_handled",
        }
        recommended_preview = migration_status["recommended_execution_preview"]
        assert recommended_preview["simulation"] is True
        assert recommended_preview["non_destructive"] is True
        assert recommended_preview["totals"]["blocked_gates"] == 0
        tag_simulation = next(action for action in recommended_preview["actions"] if action["action_type"] == "mark_duplicate_tags_handled")
        assert tag_simulation["status"] == "eligible"
        assert tag_simulation["eligible_groups"] >= 1
        readiness_titles = {item["title"] for item in migration_status["readiness"]}
        assert "Core CRM data imported" in readiness_titles
        assert "Cleanup review" in readiness_titles
        assert "Major project decisions" in readiness_titles
        assert "Optional archive imported" in readiness_titles
        assert "Final Zendesk optional sweep" in readiness_titles
        if migration_status["optional_sweep"]["status"] != "complete":
            assert any(item["status"] == "waiting" for item in migration_status["readiness"])
        assert any(item["status"] == "attention" for item in migration_status["readiness"])
        people_export_rows = handler.export_rows({"type": ["people"]})["rows"]
        assert people_export_rows
        assert "owner_name" in people_export_rows[0]
        assert handler.export_rows({"type": ["tasks"]})["rows"]
        assert handler.export_rows({"type": ["tags"]})["rows"]
        assert handler.export_rows({"type": ["custom_field_values"]})["rows"]
        data_quality_export = handler.export_rows({"type": ["data_quality"]})
        assert data_quality_export["filename"] == "local_crm_data_quality.csv"
        expected_data_quality_rows = (
            data_quality_totals["people_missing_contact"]
            + data_quality_totals["companies_missing_contact"]
            + data_quality_totals["leads_missing_email"]
            + data_quality_totals["deals_missing_value"]
            + data_quality_totals["records_missing_owner"]
            + data_quality_totals["deals_missing_relationship"]
            + data_quality_totals["deals_missing_stage"]
        )
        assert len(data_quality_export["rows"]) == expected_data_quality_rows
        assert {"person_missing_contact", "company_missing_contact", "lead_missing_email", "deal_missing_value"}.issubset(
            {row["issue_key"] for row in data_quality_export["rows"]}
        )
        project_decision_rows = handler.export_rows({"type": ["project_decisions"]})["rows"]
        assert len(project_decision_rows) == len(server.PROJECT_DECISIONS)
        assert all(row["impact_summary"] and row["recommended_label"] for row in project_decision_rows)
        assert all(int(row["sequence_step"]) >= 1 for row in project_decision_rows)
        tag_decision_export = next(row for row in project_decision_rows if row["key"] == "duplicate_tag_policy")
        people_decision_export = next(row for row in project_decision_rows if row["key"] == "duplicate_people_merge_policy")
        lead_decision_export = next(row for row in project_decision_rows if row["key"] == "duplicate_leads_merge_policy")
        overlap_decision_export = next(row for row in project_decision_rows if row["key"] == "lead_person_overlap_policy")
        archive_decision_export = next(row for row in project_decision_rows if row["key"] == "unlinked_archive_matching")
        profile_decision_export = next(row for row in project_decision_rows if row["key"] == "application_profile_editability")
        redesign_decision_export = next(row for row in project_decision_rows if row["key"] == "apple_native_redesign_timing")
        assert people_decision_export["report"] == "/reports/duplicate_people_spot_check.md"
        assert lead_decision_export["report"] == "/reports/duplicate_leads_spot_check.md"
        assert people_decision_export["worksheet_report"] == "/reports/duplicate_people_review_worksheet.md"
        assert people_decision_export["worksheet_export_url"] == "/api/export?type=duplicate_people_review_worksheet"
        assert lead_decision_export["worksheet_report"] == "/reports/duplicate_leads_review_worksheet.md"
        assert lead_decision_export["worksheet_export_url"] == "/api/export?type=duplicate_leads_review_worksheet"
        assert overlap_decision_export["report"] == "/reports/lead_person_overlap_spot_check.md"
        assert tag_decision_export["report"] == "/reports/duplicate_tag_spot_check.md"
        assert archive_decision_export["report"] == "/reports/unlinked_archive_matching_candidates.md"
        assert profile_decision_export["report"] == "/reports/application_profile_editability_review.md"
        assert redesign_decision_export["report"] == "/reports/apple_style_redesign_pipeline.md"
        assert tag_decision_export["recommended_path_simulated_status"] == "eligible"
        assert int(tag_decision_export["recommended_path_simulated_eligible_groups"]) >= 1
        option_matrix_export = handler.export_rows({"type": ["project_decision_option_matrix"]})
        assert option_matrix_export["filename"] == "local_crm_project_decision_option_matrix.csv"
        option_matrix_rows = option_matrix_export["rows"]
        assert option_matrix_rows[0]["row_type"] == "summary"
        assert int(option_matrix_rows[0]["remaining_decisions"]) == migration_status["project_decisions"]["pending"] + migration_status["project_decisions"]["deferred"]
        if tag_decision_export["status"] == "pending":
            assert any(row["row_type"] == "option" and row["decision_key"] == "duplicate_tag_policy" and row["option_code"] == "A" and row["recommended"] == "yes" for row in option_matrix_rows)
            assert any(row["row_type"] == "option" and row["decision_key"] == "duplicate_tag_policy" and row["option_code"] == "C" for row in option_matrix_rows)
        else:
            assert tag_decision_export["status"] == "decided"
            assert tag_decision_export["choice"]
            assert not any(row.get("decision_key") == "duplicate_tag_policy" for row in option_matrix_rows if row.get("row_type") == "option")
        assert all(row.get("save_boundary") for row in option_matrix_rows if row.get("row_type") == "option")
        if people_decision_export["status"] != "decided":
            assert any(row.get("decision_key") == "duplicate_people_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_people_review_worksheet.md" for row in option_matrix_rows)
        if lead_decision_export["status"] != "decided":
            assert any(row.get("decision_key") == "duplicate_leads_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_leads_review_worksheet.md" for row in option_matrix_rows)
        design_pipeline_export = handler.export_rows({"type": ["design_pipeline"]})
        assert design_pipeline_export["filename"] == "local_crm_design_pipeline.csv"
        design_pipeline_rows = design_pipeline_export["rows"]
        assert design_pipeline_rows[0]["row_type"] == "summary"
        assert design_pipeline_rows[0]["decision_key"] == "apple_native_redesign_timing"
        assert design_pipeline_rows[0]["report"] == "/reports/apple_style_redesign_pipeline.md"
        assert any(row["row_type"] == "gate" and row["key"] == "settle_cleanup_policies" for row in design_pipeline_rows)
        assert any(row["row_type"] == "phase" and row["key"] == "inspector_detail" for row in design_pipeline_rows)
        assert any(row["row_type"] == "preservation_contract" and row["key"] == "backup_audit" for row in design_pipeline_rows)
        prep_packet_rows = handler.export_rows({"type": ["decision_prep_packet"]})["rows"]
        assert len(prep_packet_rows) == migration_status["decision_prep"]["remaining_count"]
        if active_pending_decisions:
            assert prep_packet_rows[0]["key"] == active_pending_decisions[0]["key"]
        elif parked_deferred_decisions:
            assert prep_packet_rows[0]["key"] == parked_deferred_decisions[0]["key"]
        assert prep_packet_rows[0]["recommended_label"]
        assert prep_packet_rows[0]["sequence_report"] == "/reports/project_decision_sequence.md"
        assert prep_packet_rows[0]["brief_report"] == "/reports/project_decision_brief.md"
        assert prep_packet_rows[0]["fact_1_label"]
        if people_decision_export["status"] != "decided":
            assert any(row.get("key") == "duplicate_people_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_people_review_worksheet.md" for row in prep_packet_rows)
        if lead_decision_export["status"] != "decided":
            assert any(row.get("key") == "duplicate_leads_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_leads_review_worksheet.md" for row in prep_packet_rows)
        ballot_rows = handler.export_rows({"type": ["project_decision_ballot"]})["rows"]
        assert ballot_rows[0]["row_type"] == "summary"
        assert int(ballot_rows[0]["total_decisions"]) == len(server.PROJECT_DECISIONS)
        assert any(row["row_type"] == "decision" and row["key"] == "unlinked_archive_matching" for row in ballot_rows)
        assert any(row["row_type"] == "decision" and row.get("recommended_code") for row in ballot_rows)
        assert any(row["row_type"] == "decision" and row.get("key") == "duplicate_people_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_people_review_worksheet.md" for row in ballot_rows)
        assert any(row["row_type"] == "decision" and row.get("key") == "duplicate_leads_merge_policy" and row.get("worksheet_report") == "/reports/duplicate_leads_review_worksheet.md" for row in ballot_rows)
        assert any(row["row_type"] == "option" and row.get("option_code") == "A" and row["recommended"] == "yes" for row in ballot_rows)
        assert any(row["row_type"] == "option" and row.get("option_display", "").startswith("A. ") for row in ballot_rows)
        assert all(row.get("your_choice", "") == "" for row in ballot_rows if row["row_type"] == "decision")
        daily_guide_rows = handler.export_rows({"type": ["daily_operating_guide"]})["rows"]
        assert len(daily_guide_rows) == len(migration_status["daily_guide"]["steps"])
        assert daily_guide_rows[0]["key"] == "followup"
        assert int(daily_guide_rows[0]["order"]) == 1
        assert daily_guide_rows[0]["metric_1_label"]
        assert any(row["key"] == "source_exports" and row["view"] == "exports" for row in daily_guide_rows)
        archive_guide_row = next(row for row in daily_guide_rows if row["key"] == "archive_review")
        assert archive_guide_row["report"] == "/reports/archive_review_worklist.md"
        assert archive_guide_row["export_url"] == "/api/export?type=archive_review_worklist"
        archive_review_rows = handler.export_rows({"type": ["archive_review_worklist"]})["rows"]
        assert archive_review_rows[0]["row_type"] == "summary"
        assert any(row["row_type"] == "top_number" for row in archive_review_rows)
        assert any(
            row["row_type"] == "archive_item" and row["review_status"] == "unreviewed"
            for row in archive_review_rows
        )
        archive_triage_export = handler.export_rows({"type": ["archive_review_triage"]})
        assert archive_triage_export["filename"] == "local_crm_archive_review_triage.csv"
        archive_triage_rows = archive_triage_export["rows"]
        assert archive_triage_rows[0]["row_type"] == "summary"
        assert int(archive_triage_rows[0]["total"]) >= 472
        assert archive_triage_rows[0]["save_boundary"]
        assert any(row["row_type"] == "lane_summary" and row["triage_lane"] == "batch_archive_only" for row in archive_triage_rows)
        assert any(row["row_type"] == "suggested_status_summary" and row["suggested_status"] == "archive_only" for row in archive_triage_rows)
        assert any(row["row_type"] == "top_group" and row["triage_lane"] for row in archive_triage_rows)
        assert any(
            row["row_type"] == "archive_item"
            and row["suggested_status"] in {"archive_only", "needs_lookup"}
            and row["reason"]
            and row["save_boundary"]
            for row in archive_triage_rows
        )
        archive_association_rows = handler.export_rows({"type": ["archive_association_audit"]})["rows"]
        assert archive_association_rows[0]["row_type"] == "summary"
        assert int(archive_association_rows[0]["linked_documents"]) >= 203
        assert int(archive_association_rows[0]["document_total"]) >= 203
        assert float(archive_association_rows[0]["document_file_coverage_percent"]) == 100
        assert float(archive_association_rows[0]["link_coverage_percent"]) > 40
        assert int(archive_association_rows[0]["unlinked_unreviewed_call_texts"]) >= 1
        assert int(archive_association_rows[0]["exact_phone_candidates"]) == 0
        assert any(row["row_type"] == "archive_type" and row["item_type"] == "document" for row in archive_association_rows)
        assert any(
            row["row_type"] == "unlinked_communication_signal"
            and row["item_type"] == "call"
            and int(row["has_resource_id"]) == 0
            for row in archive_association_rows
        )
        backup_ledger_rows = handler.export_rows({"type": ["backup_safety_ledger"]})["rows"]
        assert backup_ledger_rows[0]["row_type"] == "summary"
        assert int(backup_ledger_rows[0]["backup_count"]) >= 1
        assert backup_ledger_rows[0]["restore_path"]
        assert any(row["row_type"] == "backup" and row["backup_name"].endswith(".sqlite") for row in backup_ledger_rows)
        assert any(row["row_type"] == "protected_action" and "project decision" in row["action"].lower() for row in backup_ledger_rows)
        completion_audit_export = handler.export_rows({"type": ["migration_completion_audit"]})
        assert completion_audit_export["filename"] == "local_crm_migration_completion_audit.csv"
        completion_audit_rows = completion_audit_export["rows"]
        assert completion_audit_rows[0]["row_type"] == "summary"
        assert completion_audit_rows[0]["overall_status"] == "operational_with_open_gates"
        assert int(completion_audit_rows[0]["reports_ready"]) == int(completion_audit_rows[0]["reports_total"])
        assert any(row["row_type"] == "requirement" and row["key"] == "local_database" and row["status"] == "complete" for row in completion_audit_rows)
        assert any(row["row_type"] == "remaining_gate" and row["key"] == "save_next_project_decision" for row in completion_audit_rows)
        database_map_export = handler.export_rows({"type": ["database_map"]})
        assert database_map_export["filename"] == "local_crm_database_map.csv"
        database_map_rows = database_map_export["rows"]
        assert database_map_rows[0]["row_type"] == "summary"
        assert int(database_map_rows[0]["table_count"]) >= 1
        assert any(row["row_type"] == "table" and row["table_name"] == "people" and int(row["row_count"]) >= 997 for row in database_map_rows)
        assert any(row["row_type"] == "column" and row["table_name"] == "people" and row["column_name"] == "name" for row in database_map_rows)
        assert any(row["row_type"] == "csv_export" and row["export_type"] == "people" for row in database_map_rows)
        assert any(row["row_type"] == "report" and row["report_name"] == "migration_completion_audit.md" for row in database_map_rows)
        independence_export = handler.export_rows({"type": ["zendesk_independence"]})
        assert independence_export["filename"] == "local_crm_zendesk_independence_checklist.csv"
        independence_rows = independence_export["rows"]
        assert independence_rows[0]["row_type"] == "summary"
        assert independence_rows[0]["status"] == "local_operational_with_open_gates"
        assert int(independence_rows[0]["reports_ready"]) == int(independence_rows[0]["reports_total"])
        assert any(row["row_type"] == "requirement" and row["key"] == "local_database_ready" and row["status"] == "complete" for row in independence_rows)
        assert any(row["row_type"] == "preserve_item" and row["path"] == "raw_api_exports/" for row in independence_rows)
        assert any(row["row_type"] == "boundary" and "Zendesk API" in row["title"] for row in independence_rows)
        remote_access_export = handler.export_rows({"type": ["remote_admin_access_plan"]})
        assert remote_access_export["filename"] == "local_crm_remote_admin_access_plan.csv"
        remote_access_rows = remote_access_export["rows"]
        assert remote_access_rows[0]["row_type"] == "summary"
        assert remote_access_rows[0]["status"] == "planning_ready_local_prototype"
        assert remote_access_rows[0]["recommended_path"] == "managed_cloud_app_managed_postgres_private_file_storage"
        assert remote_access_rows[0]["decision_needed"] == "hosting_posture"
        assert any(row["row_type"] == "hosting_option" and row["choice_code"] == "A" and row["recommendation"] == "Recommended" for row in remote_access_rows)
        assert any(row["row_type"] == "security_control" and row["key"] == "audit_log" for row in remote_access_rows)
        assert any(row["row_type"] == "role" and row["key"] == "admin" for row in remote_access_rows)
        assert any(row["row_type"] == "data_migration_check" and row["key"] == "row_counts" for row in remote_access_rows)
        assert any(row["row_type"] == "cutover_step" and row["key"] == "production_migration" for row in remote_access_rows)
        assert all(row.get("save_boundary") for row in remote_access_rows if row["row_type"] in {"hosting_option", "open_decision"})
        remote_permissions_export = handler.export_rows({"type": ["remote_admin_permissions_matrix"]})
        assert remote_permissions_export["filename"] == "local_crm_remote_admin_permissions_matrix.csv"
        remote_permissions_rows = remote_permissions_export["rows"]
        assert remote_permissions_rows[0]["row_type"] == "summary"
        assert remote_permissions_rows[0]["status"] == "permissions_design_ready"
        assert remote_permissions_rows[0]["remote_identity_needed"] == "yes"
        assert any(row["row_type"] == "role" and row["role_key"] == "owner" for row in remote_permissions_rows)
        assert any(row["row_type"] == "role" and row["role_key"] == "admin" for row in remote_permissions_rows)
        assert any(row["row_type"] == "permission" and row["action_key"] == "link_archive_item" and row["admin"] == "allow" for row in remote_permissions_rows)
        assert any(row["row_type"] == "permission" and row["action_key"] == "restore_backup" and row["owner"].startswith("allow") for row in remote_permissions_rows)
        assert any(row["row_type"] == "permission" and row["action_key"] == "save_project_decision" and row["staff"] == "deny" for row in remote_permissions_rows)
        assert any(row["row_type"] == "audit_requirement" and row["key"] == "actor_identity" for row in remote_permissions_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "app_user_lifecycle_api_beta" for row in remote_permissions_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "audit_actor_api_beta" for row in remote_permissions_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "role_middleware_beta" for row in remote_permissions_rows)
        assert any(row["row_type"] == "rollout_gate" and row["key"] == "admin_pilot" for row in remote_permissions_rows)
        remote_implementation_export = handler.export_rows({"type": ["remote_admin_implementation_blueprint"]})
        assert remote_implementation_export["filename"] == "local_crm_remote_admin_implementation_blueprint.csv"
        remote_implementation_rows = remote_implementation_export["rows"]
        assert remote_implementation_rows[0]["row_type"] == "summary"
        assert remote_implementation_rows[0]["status"] == "implementation_blueprint_ready"
        assert remote_implementation_rows[0]["source_of_truth_until_cutover"] == "local_crm_sqlite"
        assert any(row["row_type"] == "workstream" and row["key"] == "hosted_database" for row in remote_implementation_rows)
        assert any(row["row_type"] == "remote_table" and row["table_name"] == "app_users" for row in remote_implementation_rows)
        assert any(row["row_type"] == "remote_table" and row["table_name"] == "remote_file_objects" for row in remote_implementation_rows)
        assert any(row["row_type"] == "endpoint_change" and row["key"] == "restore_backup" for row in remote_implementation_rows)
        assert any(row["row_type"] == "implementation_step" and row["key"] == "production_cutover" for row in remote_implementation_rows)
        assert any(row["row_type"] == "verification_gate" and row["key"] == "permission_denials" for row in remote_implementation_rows)
        assert all(row.get("save_boundary") for row in remote_implementation_rows if row["row_type"] == "open_decision")
        remote_rollout_export = handler.export_rows({"type": ["remote_admin_rollout_board"]})
        assert remote_rollout_export["filename"] == "local_crm_remote_admin_rollout_board.csv"
        remote_rollout_rows = remote_rollout_export["rows"]
        assert remote_rollout_rows[0]["row_type"] == "summary"
        assert remote_rollout_rows[0]["status"] == "remote_rollout_board_ready"
        assert remote_rollout_rows[0]["current_blocker"] == "provider_backup_write_unlock_monitoring_shakedown"
        assert int(remote_rollout_rows[0]["task_count"]) >= 20
        assert any(row["row_type"] == "lane" and row["key"] == "database" for row in remote_rollout_rows)
        assert any(row["row_type"] == "task" and row["key"] == "choose_hosting_posture" and row["status"] == "complete_supabase_vercel_selected" for row in remote_rollout_rows)
        assert any(row["row_type"] == "task" and row["key"] == "load_staging_database" for row in remote_rollout_rows)
        assert any(row["row_type"] == "task" and row["key"] == "migrate_private_document_files" for row in remote_rollout_rows)
        assert any(row["row_type"] == "task" and row["key"] == "protect_remote_endpoints" for row in remote_rollout_rows)
        assert any(row["row_type"] == "task" and row["key"] == "owner_staging_shakedown" for row in remote_rollout_rows)
        assert any(row["row_type"] == "decision_prompt" and row["key"] == "production_gates" and row["recommended_option"] == "A" for row in remote_rollout_rows)
        assert any(row["row_type"] == "verification_gate" and row["key"] == "permission_denials" for row in remote_rollout_rows)
        assert any(row["row_type"] == "milestone" and row["key"] == "production_cutover" for row in remote_rollout_rows)
        remote_hosting_export = handler.export_rows({"type": ["remote_hosting_decision_packet"]})
        assert remote_hosting_export["filename"] == "local_crm_remote_hosting_decision_packet.csv"
        remote_hosting_rows = remote_hosting_export["rows"]
        assert remote_hosting_rows[0]["row_type"] == "summary"
        assert remote_hosting_rows[0]["status"] == "hosting_decision_packet_ready"
        assert remote_hosting_rows[0]["decision_needed"] == "hosting_posture"
        assert remote_hosting_rows[0]["recommended_option"] == "A"
        assert any(row["row_type"] == "hosting_option" and row["choice_code"] == "A" and row["recommendation"] == "Recommended" for row in remote_hosting_rows)
        assert any(row["row_type"] == "decision_score" and row["key"] == "low_maintenance" for row in remote_hosting_rows)
        assert any(row["row_type"] == "minimum_requirement" and row["key"] == "private_files" for row in remote_hosting_rows)
        assert any(row["row_type"] == "owner_question" and row["key"] == "budget" for row in remote_hosting_rows)
        assert any(row["row_type"] == "next_step" and row["key"] == "choose_posture" for row in remote_hosting_rows)
        remote_provider_export = handler.export_rows({"type": ["remote_managed_cloud_provider_shortlist"]})
        assert remote_provider_export["filename"] == "local_crm_remote_managed_cloud_provider_shortlist.csv"
        remote_provider_rows = remote_provider_export["rows"]
        assert remote_provider_rows[0]["row_type"] == "summary"
        assert remote_provider_rows[0]["status"] == "provider_shortlist_ready"
        assert remote_provider_rows[0]["front_runner_to_price_and_test"] == "digitalocean_app_platform_managed_postgres_spaces"
        assert any(row["row_type"] == "provider_stack" and row["key"] == "digitalocean_app_platform_managed_postgres_spaces" for row in remote_provider_rows)
        assert any(row["row_type"] == "provider_stack" and row["key"] == "railway_app_postgres_private_buckets" for row in remote_provider_rows)
        assert any(row["row_type"] == "evaluation_criterion" and row["key"] == "private_object_storage" for row in remote_provider_rows)
        assert any(row["row_type"] == "official_source" and row["key"] == "digitalocean_app_platform_storage" for row in remote_provider_rows)
        assert any(row["row_type"] == "shortlist_recommendation" and row["key"] == "first_finalist" for row in remote_provider_rows)
        assert any(row["row_type"] == "owner_question" and row["key"] == "monthly_budget" for row in remote_provider_rows)
        assert any(row["row_type"] == "next_step" and row["key"] == "build_pricing_sheet" for row in remote_provider_rows)
        remote_pricing_export = handler.export_rows({"type": ["remote_staging_pricing_preflight"]})
        assert remote_pricing_export["filename"] == "local_crm_remote_staging_pricing_preflight.csv"
        remote_pricing_rows = remote_pricing_export["rows"]
        assert remote_pricing_rows[0]["row_type"] == "summary"
        assert remote_pricing_rows[0]["status"] == "remote_staging_pricing_preflight_ready"
        assert remote_pricing_rows[0]["recommended_first_finalist"] == "digitalocean_app_platform_managed_postgres_spaces"
        assert float(remote_pricing_rows[0]["local_database_mib"]) > 0
        assert float(remote_pricing_rows[0]["document_file_gib"]) > 0
        assert any(row["row_type"] == "pricing_component" and row["key"] == "managed_postgres_basic_1gb" and "$15.15" in row["unit_price"] for row in remote_pricing_rows)
        assert any(row["row_type"] == "pricing_component" and row["key"] == "spaces_standard_storage" and "$5.00" in row["unit_price"] for row in remote_pricing_rows)
        assert any(row["row_type"] == "pricing_component" and row["key"] == "bucket_storage" and "$0.015" in row["unit_price"] for row in remote_pricing_rows)
        assert any(row["row_type"] == "estimate_profile" and row["key"] == "digitalocean_staging_managed_pg" and "$32.15" in row["baseline_estimate"] for row in remote_pricing_rows)
        assert any(row["row_type"] == "preflight_item" and row["key"] == "budget_cap" for row in remote_pricing_rows)
        assert any(row["row_type"] == "risk_control" and row["key"] == "usage_limit" for row in remote_pricing_rows)
        assert any(row["row_type"] == "owner_question" and row["key"] == "budget_cap" for row in remote_pricing_rows)
        assert any(row["row_type"] == "official_source" and row["key"] == "digitalocean_app_platform_pricing" for row in remote_pricing_rows)
        remote_setup_export = handler.export_rows({"type": ["remote_staging_setup_runbook"]})
        assert remote_setup_export["filename"] == "local_crm_remote_staging_setup_runbook.csv"
        remote_setup_rows = remote_setup_export["rows"]
        assert remote_setup_rows[0]["row_type"] == "summary"
        assert remote_setup_rows[0]["status"] == "remote_staging_setup_runbook_ready"
        assert remote_setup_rows[0]["recommended_first_path"] == "digitalocean_staging_managed_postgres_spaces"
        assert any(row["row_type"] == "provider_path" and row["provider"] == "digitalocean" for row in remote_setup_rows)
        assert any(row["row_type"] == "provider_path" and row["provider"] == "railway" for row in remote_setup_rows)
        assert any(row["row_type"] == "staging_phase" and row["key"] == "validate" for row in remote_setup_rows)
        assert any(row["row_type"] == "setup_task" and row["key"] == "create_app_platform_app" for row in remote_setup_rows)
        assert any(row["row_type"] == "setup_task" and row["key"] == "create_postgres_service" for row in remote_setup_rows)
        assert any(row["row_type"] == "environment_variable" and row["key"] == "DATABASE_URL" and row["secret"] == "yes" for row in remote_setup_rows)
        assert any(row["row_type"] == "environment_variable" and row["key"] == "DOCUMENT_FILE_ACCESS_ENABLED" and row["required_for_staging"] == "yes" for row in remote_setup_rows)
        assert any(row["row_type"] == "verification_gate" and row["key"] == "restore" for row in remote_setup_rows)
        assert any(row["row_type"] == "approval_gate" and row["key"] == "before_payment" for row in remote_setup_rows)
        assert any(row["row_type"] == "official_source" and row["key"] == "digitalocean_environment_variables" for row in remote_setup_rows)
        remote_deployment_export = handler.export_rows({"type": ["remote_staging_deployment_spec"]})
        assert remote_deployment_export["filename"] == "local_crm_remote_staging_deployment_spec.csv"
        remote_deployment_rows = remote_deployment_export["rows"]
        assert remote_deployment_rows[0]["row_type"] == "summary"
        assert remote_deployment_rows[0]["status"] == "supabase_staging_vercel_signed_file_smoke_passed"
        assert remote_deployment_rows[0]["deployment_boundary"] == "vercel_staging_deployed_read_only_locked_signed_file_access_owner_admin_no_pilot_admin_access"
        assert any(row["row_type"] == "deployment_target" and row["key"] == "supabase_data_layer" for row in remote_deployment_rows)
        assert any(row["row_type"] == "deployment_target" and row["key"] == "vercel_staging" and row["status"] == "deployed_smoke_passed_signed_files_enabled" for row in remote_deployment_rows)
        assert any(row["row_type"] == "app_service_spec" and row["key"] == "start_command" for row in remote_deployment_rows)
        assert any(row["row_type"] == "app_service_spec" and row["key"] == "vercel_entrypoint" and row["value"] == "api/index.py via @vercel/python" for row in remote_deployment_rows)
        assert any(row["row_type"] == "app_service_spec" and row["key"] == "health_check" and row["value"] == "/health or /api/health" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CRM_ENV" and row["implementation_state"] == "supported_now" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "DATABASE_URL" and row["implementation_state"] == "health_probe_supported_adapter_beta" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_DATABASE_ADAPTER" and row["implementation_state"] == "adapter_beta_supported" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_SSLROOTCERT" and row["implementation_state"] == "supported_now" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_POSTGRES_STATEMENT_TIMEOUT_MS" and row["implementation_state"] == "supported_now" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_AUTH_REQUIRED" and row["implementation_state"] == "auth_beta_supported" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH" and row["implementation_state"] == "auth_beta_supported" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "REMOTE_WRITE_LOCK" and row["implementation_state"] == "supported_now" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "EXPORT_PACKAGE_ENABLED" and row["implementation_state"] == "supported_now" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "DOCUMENT_FILE_ACCESS_ENABLED" and row["implementation_state"] == "signed_file_access_validated" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS" and row["implementation_state"] == "signed_file_access_supported" for row in remote_deployment_rows)
        assert any(row["row_type"] == "configuration_variable" and row["key"] == "CHILLCRM_SUPABASE_SERVICE_ROLE_KEY" and row["implementation_state"] == "configured_server_only_signed_access_validated" for row in remote_deployment_rows)
        assert any(row["row_type"] == "deployment_input" and row["key"] == "complete_package" for row in remote_deployment_rows)
        assert any(row["row_type"] == "deployment_input" and row["key"] == "adapter_smoke" for row in remote_deployment_rows)
        assert any(row["row_type"] == "deployment_input" and row["key"] == "vercel_package" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "postgres_adapter" and row["status"] == "passed_hosted_and_vercel" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "auth_sessions" and row["status"] == "owner_ui_deployed_newest_role_smoke_pending" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "actor_audit" and row["status"] == "local_crm_write_actor_audit_passed_hosted_unlock_pending" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "private_file_storage" and row["status"] == "passed_private_storage_signed_access" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "vercel_app_host" and row["status"] == "deployed_signed_file_smoke_passed" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "write_lock_enforcement" and row["status"] == "implemented" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "bulk_export_permissions" and row["status"] == "partial" for row in remote_deployment_rows)
        assert any(row["row_type"] == "implementation_gap" and row["key"] == "health_monitoring" and row["status"] == "partial" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "app_boot" and "health returns 200" in row["pass_criteria"] for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "vercel_package" and row["status"] == "passed_local" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "hosted_adapter_read_paths" and row["status"] == "passed_hosted" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "schema_apply" and row["status"] == "passed_supabase" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "data_load_counts" and row["status"] == "passed_supabase" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "report_access" and "403" in row["pass_criteria"] for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "file_private" and row["status"] == "passed_private_storage_signed_access" for row in remote_deployment_rows)
        assert any(row["row_type"] == "staging_smoke_test" and row["key"] == "backup_restore" and row["severity"] == "P0" for row in remote_deployment_rows)
        remote_validation_export = handler.export_rows({"type": ["remote_staging_validation_matrix"]})
        assert remote_validation_export["filename"] == "local_crm_remote_staging_validation_matrix.csv"
        remote_validation_rows = remote_validation_export["rows"]
        assert remote_validation_rows[0]["row_type"] == "summary"
        assert remote_validation_rows[0]["status"] == "remote_staging_validation_matrix_ready"
        assert remote_validation_rows[0]["stage"] == "pre_provisioning_validation_template"
        assert any(row["row_type"] == "expected_count" and row["key"] == "people" and int(row["expected_count"]) >= 997 for row in remote_validation_rows)
        assert any(row["row_type"] == "expected_count" and row["key"] == "document_files" and int(row["expected_count"]) >= 203 for row in remote_validation_rows)
        assert any(row["row_type"] == "validation_section" and row["key"] == "backup_restore" for row in remote_validation_rows)
        assert any(row["row_type"] == "validation_check" and row["key"] == "core_counts" and row["severity"] == "P0" for row in remote_validation_rows)
        assert any(row["row_type"] == "validation_check" and row["key"] == "unauthorized_download" and row["blocks_pilot"] == "yes" for row in remote_validation_rows)
        assert any(row["row_type"] == "blocker_rule" and row["key"] == "restore_unproven" for row in remote_validation_rows)
        assert any(row["row_type"] == "next_step" and row["key"] == "before_pilot" for row in remote_validation_rows)
        remote_pilot_export = handler.export_rows({"type": ["remote_admin_pilot_onboarding_plan"]})
        assert remote_pilot_export["filename"] == "local_crm_remote_admin_pilot_onboarding_plan.csv"
        remote_pilot_rows = remote_pilot_export["rows"]
        assert remote_pilot_rows[0]["row_type"] == "summary"
        assert remote_pilot_rows[0]["status"] == "remote_admin_pilot_onboarding_plan_ready"
        assert remote_pilot_rows[0]["pilot_size"] == "owner_only_first_optional_internal_admin_later"
        assert any(row["row_type"] == "pilot_role" and row["key"] == "optional_internal_admin" for row in remote_pilot_rows)
        assert any(row["row_type"] == "pilot_prerequisite" and row["key"] == "validation_p0_passed" for row in remote_pilot_rows)
        assert any(row["row_type"] == "onboarding_step" and row["key"] == "first_login_check" for row in remote_pilot_rows)
        assert any(row["row_type"] == "pilot_workflow" and row["key"] == "safe_note_test" for row in remote_pilot_rows)
        assert any(row["row_type"] == "permission_probe" and row["key"] == "read_only_write_denied" for row in remote_pilot_rows)
        assert any(row["row_type"] == "support_watch_item" and row["key"] == "audit_gap" for row in remote_pilot_rows)
        assert any(row["row_type"] == "pilot_blocker_rule" and row["key"] == "restore_not_proven" for row in remote_pilot_rows)
        assert any(row["row_type"] == "pilot_signoff_gate" and row["key"] == "optional_internal_admin" for row in remote_pilot_rows)
        remote_cutover_export = handler.export_rows({"type": ["remote_production_cutover_checklist"]})
        assert remote_cutover_export["filename"] == "local_crm_remote_production_cutover_checklist.csv"
        remote_cutover_rows = remote_cutover_export["rows"]
        assert remote_cutover_rows[0]["row_type"] == "summary"
        assert remote_cutover_rows[0]["status"] == "remote_production_cutover_checklist_ready"
        assert remote_cutover_rows[0]["source_of_truth_after_cutover"] == "hosted_remote_crm"
        assert any(row["row_type"] == "cutover_phase" and row["key"] == "freeze" for row in remote_cutover_rows)
        assert any(row["row_type"] == "checklist_item" and row["key"] == "final_complete_package" for row in remote_cutover_rows)
        assert any(row["row_type"] == "checklist_item" and row["key"] == "owner_shakedown_signoff" for row in remote_cutover_rows)
        assert any(row["row_type"] == "rollback_trigger" and row["key"] == "audit_gap" and row["severity"] == "P0" for row in remote_cutover_rows)
        assert any(row["row_type"] == "monitoring_check" and row["key"] == "backup_status" for row in remote_cutover_rows)
        assert any(row["row_type"] == "communication" and row["key"] == "remote_ready" for row in remote_cutover_rows)
        assert any(row["row_type"] == "signoff_gate" and row["key"] == "before_source_switch" for row in remote_cutover_rows)
        hosted_db_export = handler.export_rows({"type": ["hosted_database_migration_readiness"]})
        assert hosted_db_export["filename"] == "local_crm_hosted_database_migration_readiness.csv"
        hosted_db_rows = hosted_db_export["rows"]
        assert hosted_db_rows[0]["row_type"] == "summary"
        assert hosted_db_rows[0]["status"] == "ready_for_staging_schema_design"
        assert hosted_db_rows[0]["target_database"] == "managed_postgres_recommended"
        assert int(hosted_db_rows[0]["table_count"]) >= 25
        assert int(hosted_db_rows[0]["column_count"]) >= 1
        assert int(hosted_db_rows[0]["total_source_rows"]) >= 1
        assert any(row["row_type"] == "table_migration" and row["table_name"] == "people" and int(row["row_count"]) >= 997 for row in hosted_db_rows)
        assert any(row["row_type"] == "column_migration" and row["table_name"] == "people" and row["column_name"] == "id" and row["postgres_type"] == "bigint" for row in hosted_db_rows)
        assert any(row["row_type"] == "migration_requirement" and row["key"] == "remote_user_identity" for row in hosted_db_rows)
        assert any(row["row_type"] == "risk" and row["key"] == "local_file_paths" for row in hosted_db_rows)
        hosted_schema_export = handler.export_rows({"type": ["hosted_schema_draft"]})
        assert hosted_schema_export["filename"] == "local_crm_hosted_schema_draft.csv"
        hosted_schema_rows = hosted_schema_export["rows"]
        assert hosted_schema_rows[0]["row_type"] == "summary"
        assert hosted_schema_rows[0]["status"] == "draft_ready_for_staging_review"
        assert hosted_schema_rows[0]["target_database"] == "managed_postgres_recommended"
        assert any(row["row_type"] == "table_ddl" and row["table_name"] == "people" and 'crm."people"' in row["sql"] for row in hosted_schema_rows)
        assert any(row["row_type"] == "remote_table_ddl" and row["table_name"] == "app_users" for row in hosted_schema_rows)
        assert any(row["row_type"] == "remote_table_ddl" and row["table_name"] == "remote_file_objects" for row in hosted_schema_rows)
        assert any(row["row_type"] == "foreign_key_ddl" for row in hosted_schema_rows)
        assert any(row["row_type"] == "validation_query" and row["key"] == "people_count" for row in hosted_schema_rows)
        assert any(row["row_type"] == "schema_requirement" and row["key"] == "staging_only" for row in hosted_schema_rows)
        hosted_load_export = handler.export_rows({"type": ["hosted_data_load_plan"]})
        assert hosted_load_export["filename"] == "local_crm_hosted_data_load_plan.csv"
        hosted_load_rows = hosted_load_export["rows"]
        assert hosted_load_rows[0]["row_type"] == "summary"
        assert hosted_load_rows[0]["status"] == "staging_load_plan_ready"
        assert int(hosted_load_rows[0]["source_table_count"]) >= 25
        assert any(row["row_type"] == "load_phase" and row["phase"] == "Core CRM records" for row in hosted_load_rows)
        assert any(row["row_type"] == "table_load" and row["table_name"] == "people" and int(row["row_count"]) >= 997 for row in hosted_load_rows)
        assert any(row["row_type"] == "table_load" and row["table_name"] == "imported_archive_items" for row in hosted_load_rows)
        assert any(row["row_type"] == "remote_seed" and row["table_name"] == "app_roles" for row in hosted_load_rows)
        assert any(row["row_type"] == "file_migration_step" and row["key"] == "remote_file_objects" for row in hosted_load_rows)
        assert any(row["row_type"] == "validation_check" and row["key"] == "permission_denials" for row in hosted_load_rows)
        assert any(row["row_type"] == "validation_check" and row["key"] == "files" for row in hosted_load_rows)
        assert any(row["row_type"] == "cutover_gate" and row["key"] == "local_freeze" for row in hosted_load_rows)
        overlap_spot_check_export = handler.export_rows({"type": ["lead_person_overlap_spot_check"]})
        assert overlap_spot_check_export["filename"] == "local_crm_lead_person_overlap_spot_check.csv"
        overlap_spot_check_rows = overlap_spot_check_export["rows"]
        assert overlap_spot_check_rows[0]["row_type"] == "summary"
        assert int(overlap_spot_check_rows[0]["open_groups"]) >= 5
        assert int(overlap_spot_check_rows[0]["person_keeper_drafts"]) >= 5
        assert any(row["row_type"] == "option" and row["decision_key"] == "lead_person_overlap_policy" and row["option_code"] == "A" and row["recommended"] == "yes" for row in overlap_spot_check_rows)
        assert any(row["row_type"] == "option" and row["decision_key"] == "lead_person_overlap_policy" and row["option_code"] == "C" for row in overlap_spot_check_rows)
        assert any(row["row_type"] == "group" and row["group_type"] == "lead_person_overlap" and row["draft_keeper_type"] == "person" for row in overlap_spot_check_rows)
        people_spot_check_export = handler.export_rows({"type": ["duplicate_people_spot_check"]})
        assert people_spot_check_export["filename"] == "local_crm_duplicate_people_spot_check.csv"
        people_spot_check_rows = people_spot_check_export["rows"]
        assert people_spot_check_rows[0]["row_type"] == "summary"
        assert int(people_spot_check_rows[0]["open_groups"]) >= 60
        assert any(row["row_type"] == "option" and row["decision_key"] == "duplicate_people_merge_policy" and row["option_code"] == "A" and row["recommended"] == "yes" for row in people_spot_check_rows)
        assert any(row["row_type"] == "group" and row["group_type"] == "duplicate_people" and row["draft_keeper_type"] == "person" for row in people_spot_check_rows)
        people_worksheet_export = handler.export_rows({"type": ["duplicate_people_review_worksheet"]})
        assert people_worksheet_export["filename"] == "local_crm_duplicate_people_review_worksheet.csv"
        people_worksheet_rows = people_worksheet_export["rows"]
        assert people_worksheet_rows[0]["row_type"] == "summary"
        assert people_worksheet_rows[0]["report"] == "/reports/duplicate_people_review_worksheet.md"
        assert int(people_worksheet_rows[0]["open_groups"]) >= 60
        assert int(people_worksheet_rows[0]["review_remaining"]) >= 60
        assert any(row["row_type"] == "instruction" and "project" in str(row["title"]).lower() for row in people_worksheet_rows)
        assert any(row["row_type"] == "lane_summary" and int(row["group_count"]) >= 1 for row in people_worksheet_rows)
        assert any(row["row_type"] == "group" and row["group_type"] == "duplicate_people" and row["reviewer_choice"] == "" for row in people_worksheet_rows)
        assert any(row["row_type"] == "group" and row["conflict_summary"] for row in people_worksheet_rows)
        assert any(row["row_type"] == "group" and row["history_summary"] for row in people_worksheet_rows)
        leads_spot_check_export = handler.export_rows({"type": ["duplicate_leads_spot_check"]})
        assert leads_spot_check_export["filename"] == "local_crm_duplicate_leads_spot_check.csv"
        leads_spot_check_rows = leads_spot_check_export["rows"]
        assert leads_spot_check_rows[0]["row_type"] == "summary"
        assert int(leads_spot_check_rows[0]["open_groups"]) >= 36
        assert any(row["row_type"] == "option" and row["decision_key"] == "duplicate_leads_merge_policy" and row["option_code"] == "A" and row["recommended"] == "yes" for row in leads_spot_check_rows)
        assert any(row["row_type"] == "group" and row["group_type"] == "duplicate_leads" and row["draft_keeper_type"] == "lead" for row in leads_spot_check_rows)
        leads_worksheet_export = handler.export_rows({"type": ["duplicate_leads_review_worksheet"]})
        assert leads_worksheet_export["filename"] == "local_crm_duplicate_leads_review_worksheet.csv"
        leads_worksheet_rows = leads_worksheet_export["rows"]
        assert leads_worksheet_rows[0]["row_type"] == "summary"
        assert leads_worksheet_rows[0]["report"] == "/reports/duplicate_leads_review_worksheet.md"
        assert int(leads_worksheet_rows[0]["open_groups"]) >= 36
        assert int(leads_worksheet_rows[0]["review_remaining"]) >= 36
        assert any(row["row_type"] == "instruction" and "project" in str(row["title"]).lower() for row in leads_worksheet_rows)
        assert any(row["row_type"] == "lane_summary" and int(row["group_count"]) >= 1 for row in leads_worksheet_rows)
        assert any(row["row_type"] == "group" and row["group_type"] == "duplicate_leads" and row["reviewer_choice"] == "" for row in leads_worksheet_rows)
        assert any(row["row_type"] == "group" and row["conflict_summary"] for row in leads_worksheet_rows)
        assert any(row["row_type"] == "group" and row["profile_summary"] for row in leads_worksheet_rows)
        transition_rows = handler.export_rows({"type": ["followup_transition_plan"]})["rows"]
        assert any(row["row_type"] == "transition_step" and row["key"] == "review_imported" for row in transition_rows)
        assert any(row["row_type"] == "imported_open_task" and row["zendesk_task_id"] for row in transition_rows)
        cleanup_starter_rows = handler.export_rows({"type": ["cleanup_starter_packet"]})["rows"]
        assert len(cleanup_starter_rows) == migration_status["cleanup_starter"]["group_count"]
        assert cleanup_starter_rows[0]["group_type"] == "lead_person_overlap"
        assert cleanup_starter_rows[0]["group_key"]
        assert cleanup_starter_rows[0]["draft_keeper"]
        assert cleanup_starter_rows[0]["report"] == "/reports/cleanup_review_starter_packet.md"
        assert cleanup_starter_rows[0]["merge_review_report"] == "/reports/cleanup_merge_review_pack.md"
        linked_resource_rows = handler.export_rows({"type": ["linked_resources"]})["rows"]
        assert len(linked_resource_rows) >= 17
        assert any(row["kind"] == "Call Recording Folder" and "drive.google.com" in row["url"] for row in linked_resource_rows)
        assert any(row["source_type"] == "note" and "oncehub.com" in row["url"] for row in linked_resource_rows)
        linked_resource_page = handler.linked_resources({"page_size": ["10"]})
        assert linked_resource_page["total"] == len(linked_resource_rows)
        assert linked_resource_page["resources"]
        assert any(row["value"] == "Call Recording Folder" for row in linked_resource_page["kind_counts"])
        linked_resource_kind_page = handler.linked_resources({"kind": ["Call Recording Folder"], "page_size": ["50"]})
        assert linked_resource_kind_page["total"] == 13
        assert all(row["kind"] == "Call Recording Folder" for row in linked_resource_kind_page["resources"])
        linked_resource_search_page = handler.linked_resources({"q": ["oncehub"], "page_size": ["50"]})
        assert linked_resource_search_page["total"] >= 1
        assert any("oncehub.com" in row["url"] for row in linked_resource_search_page["resources"])
        linked_resource_global_search = handler.search({"q": ["drive.google.com"]})["results"]
        assert any(row.get("match_context", "").startswith("Linked Resource:") for row in linked_resource_global_search)
        linked_resource_filtered_export = handler.export_rows({"type": ["linked_resources"], "kind": ["Call Recording Folder"]})["rows"]
        assert len(linked_resource_filtered_export) == 13
        assert all(row["kind"] == "Call Recording Folder" for row in linked_resource_filtered_export)
        assert "linkedResourceSavedView" in app_js
        assert "currentLinkedResourceSettings" in app_js
        assert "applyLinkedResourceSettings" in app_js
        linked_resource_saved_view = handler.save_view(
            {
                "type": "linked_resources",
                "name": "Verification Call Recording Links",
                "settings": {"kind": "Call Recording Folder"},
            }
        )
        assert linked_resource_saved_view["ok"] is True
        assert linked_resource_saved_view["view"]["record_count"] == len(linked_resource_filtered_export)
        assert linked_resource_saved_view["view"]["settings"]["kind"] == "Call Recording Folder"
        linked_resource_saved_views = handler.saved_views({"type": ["linked_resources"]})["views"]
        matching_linked_resource_views = [
            view for view in linked_resource_saved_views if view["name"] == "Verification Call Recording Links"
        ]
        assert matching_linked_resource_views
        assert matching_linked_resource_views[0]["record_count"] == len(linked_resource_filtered_export)
        assert any(view["name"] == "Verification Call Recording Links" for view in handler.summary()["saved_views"])
        linked_resource_sample = next(row for row in linked_resource_rows if row["kind"] == "Call Recording Folder")
        linked_resource_detail = handler.record_detail(
            {"type": [linked_resource_sample["record_type"]], "id": [str(linked_resource_sample["record_id"])]}
        )
        assert any(resource["url"] == linked_resource_sample["url"] for resource in linked_resource_detail["linked_resources"])
        archive_page = handler.archive_items({"page_size": ["10"]})
        assert archive_page["total"] >= 884
        archive_counts = {row["value"]: row["count"] for row in archive_page["item_type_counts"]}
        assert archive_counts["document"] == 203
        assert archive_counts["call"] == 380
        assert archive_counts["text_message"] == 154
        archive_page_association = archive_page["association"]
        assert archive_page_association["summary"]["linked_documents"] == 203
        assert archive_page_association["summary"]["document_file_coverage_percent"] == 100
        assert archive_page_association["summary"]["exact_phone_candidates"] == 0
        assert archive_page_association["summary"]["unlinked_unreviewed_call_texts"] >= 1
        archive_evidence = archive_page["unlinked_communications"]
        assert archive_evidence["total"] >= 472
        assert archive_evidence["type_counts"]["call"] >= 373
        assert archive_evidence["type_counts"]["text_message"] >= 99
        assert archive_evidence["classification_counts"]["exact_unique_candidate"] == 0
        assert archive_evidence["classification_counts"]["ambiguous_exact_candidates"] == 0
        assert archive_evidence["recommendation"] == "Archive-only for now"
        assert archive_evidence["report"] == "/reports/unlinked_archive_matching_candidates.md"
        archive_triage = archive_page["archive_triage"]
        assert archive_triage["title"] == "Archive Review Triage"
        assert archive_triage["report"] == "/reports/archive_review_triage.md"
        assert archive_triage["export_url"] == "/api/export?type=archive_review_triage"
        assert archive_triage["total"] == archive_evidence["total"]
        assert archive_triage["unreviewed"] >= 1
        triage_lane_by_key = {row["triage_lane"]: row for row in archive_triage["lane_counts"]}
        triage_status_by_key = {row["suggested_status"]: row for row in archive_triage["suggested_status_counts"]}
        assert triage_lane_by_key["batch_archive_only"]["count"] >= 1
        assert triage_lane_by_key["batch_archive_only"]["triage_lane_label"] == "Likely archive-only"
        assert triage_status_by_key["archive_only"]["count"] >= 1
        assert archive_triage["top_groups"]
        assert archive_triage["sample_items"]
        assert archive_triage["sample_items"][0]["reason"]
        batch_archive_only_page = handler.archive_items(
            {"triage_lane": ["batch_archive_only"], "page_size": ["50"]}
        )
        assert batch_archive_only_page["preset"] == "unlinked_communications"
        assert batch_archive_only_page["triage_lane"] == "batch_archive_only"
        assert batch_archive_only_page["total"] == triage_lane_by_key["batch_archive_only"]["count"]
        assert all(row["triage_lane"] == "batch_archive_only" for row in batch_archive_only_page["items"])
        assert all(row["triage_lane_label"] == "Likely archive-only" for row in batch_archive_only_page["items"])
        needs_lookup_triage_page = handler.archive_items(
            {"triage_lane": ["needs_lookup"], "review_status": ["unreviewed"], "page_size": ["50"]}
        )
        assert needs_lookup_triage_page["triage_lane"] == "needs_lookup"
        assert needs_lookup_triage_page["review_status"] == "unreviewed"
        assert needs_lookup_triage_page["total"] == triage_lane_by_key["needs_lookup"]["count"]
        assert all(row["triage_lane"] == "needs_lookup" for row in needs_lookup_triage_page["items"])
        assert 'data-key="unlinked_archive_matching"' in app_js
        assert "Show Evidence Set" in app_js
        assert "archiveSavedView" in app_js
        assert "currentArchiveSettings" in app_js
        assert "applyArchiveSettings" in app_js
        document_page = handler.archive_items({"item_type": ["document"], "page_size": ["10"]})
        assert document_page["total"] == 203
        assert document_page["items"][0]["file_url"]
        assert document_page["items"][0]["size_label"]
        unlinked_archive = handler.archive_items({"record_type": ["unlinked"], "page_size": ["10"]})
        assert unlinked_archive["total"] >= 1
        unlinked_communications = handler.archive_items({"preset": ["unlinked_communications"], "page_size": ["50"]})
        assert unlinked_communications["preset"] == "unlinked_communications"
        assert unlinked_communications["total"] == archive_evidence["total"]
        review_count_map = {row["value"]: row["count"] for row in unlinked_communications["review_status_counts"]}
        assert review_count_map["unreviewed"] == archive_evidence["total"]
        assert review_count_map["needs_lookup"] == 0
        assert review_count_map["ready_to_link"] == 0
        assert review_count_map["archive_only"] == 0
        assert all(row["item_type"] in {"call", "text_message"} and not row.get("record_id") for row in unlinked_communications["items"])
        unreviewed_communications = handler.archive_items(
            {"preset": ["unlinked_communications"], "review_status": ["unreviewed"], "page_size": ["50"]}
        )
        assert unreviewed_communications["total"] == archive_evidence["total"]
        archive_search = handler.archive_items({"q": ["Release Form"], "page_size": ["50"]})
        assert archive_search["total"] >= 1
        assert any(row["item_type"] == "document" for row in archive_search["items"])
        dated_archive = handler.archive_items(
            {
                "item_type": ["document"],
                "date_from": ["2025-01-01"],
                "date_to": ["2025-12-31"],
                "page_size": ["50"],
            }
        )
        assert dated_archive["date_from"] == "2025-01-01"
        assert dated_archive["date_to"] == "2025-12-31"
        assert dated_archive["total"] >= 1
        assert all("2025-01-01" <= row["occurred_at"][:10] <= "2025-12-31" for row in dated_archive["items"])
        archive_export = handler.export_rows({"type": ["imported_archive"]})["rows"]
        assert len(archive_export) >= 884
        assert any(row["item_type"] == "document" and row["local_file"] for row in archive_export)
        dated_archive_export = handler.export_rows(
            {
                "type": ["imported_archive"],
                "item_type": ["document"],
                "date_from": ["2025-01-01"],
                "date_to": ["2025-12-31"],
            }
        )["rows"]
        assert len(dated_archive_export) == dated_archive["total"]
        assert all("2025-01-01" <= row["occurred_at"][:10] <= "2025-12-31" for row in dated_archive_export)
        archive_saved_view = handler.save_view(
            {
                "type": "archive",
                "name": "Verification 2025 Documents",
                "settings": {
                    "item_type": "document",
                    "date_from": "2025-01-01",
                    "date_to": "2025-12-31",
                },
            }
        )
        assert archive_saved_view["ok"] is True
        assert archive_saved_view["view"]["record_count"] == len(dated_archive_export)
        assert archive_saved_view["view"]["settings"]["item_type"] == "document"
        assert archive_saved_view["view"]["settings"]["date_from"] == "2025-01-01"
        archive_saved_views = handler.saved_views({"type": ["archive"]})["views"]
        matching_archive_views = [view for view in archive_saved_views if view["name"] == "Verification 2025 Documents"]
        assert matching_archive_views
        assert matching_archive_views[0]["record_count"] == len(dated_archive_export)
        assert any(view["name"] == "Verification 2025 Documents" for view in handler.summary()["saved_views"])
        archive_triage_saved_view = handler.save_view(
            {
                "type": "archive",
                "name": "Verification Likely Archive Only",
                "settings": {
                    "triage_lane": "batch_archive_only",
                    "review_status": "unreviewed",
                },
            }
        )
        assert archive_triage_saved_view["ok"] is True
        assert archive_triage_saved_view["view"]["settings"]["preset"] == "unlinked_communications"
        assert archive_triage_saved_view["view"]["settings"]["triage_lane"] == "batch_archive_only"
        assert archive_triage_saved_view["view"]["settings"]["review_status"] == "unreviewed"
        assert archive_triage_saved_view["view"]["record_count"] == batch_archive_only_page["total"]
        archive_evidence_export = handler.export_rows({"type": ["imported_archive"], "preset": ["unlinked_communications"]})
        assert archive_evidence_export["filename"] == "local_crm_imported_archive_unlinked_calls_texts.csv"
        assert len(archive_evidence_export["rows"]) == archive_evidence["total"]
        assert all(row["item_type"] in {"call", "text_message"} and not row.get("record_id") for row in archive_evidence_export["rows"])
        batch_archive_only_export = handler.export_rows(
            {"type": ["imported_archive"], "triage_lane": ["batch_archive_only"]}
        )
        assert batch_archive_only_export["filename"] == "local_crm_imported_archive_batch_archive_only.csv"
        assert len(batch_archive_only_export["rows"]) == batch_archive_only_page["total"]
        assert all(row["triage_lane"] == "batch_archive_only" for row in batch_archive_only_export["rows"])
        assert all(row["suggested_review_status"] == "archive_only" for row in batch_archive_only_export["rows"])
        linked_archive_record = next(row for row in document_page["items"] if row.get("record_type") and row.get("record_id"))
        linked_archive_detail = handler.record_detail(
            {"type": [linked_archive_record["record_type"]], "id": [str(linked_archive_record["record_id"])]}
        )
        assert linked_archive_detail["archive_items"]
        assert any(item["id"] == linked_archive_record["id"] for item in linked_archive_detail["archive_items"])
        archive_activity = handler.activity({"limit": ["100"]})["activity"]
        assert any(row["activity_type"].startswith("archive_") for row in archive_activity)
        manual_archive_item = unlinked_communications["items"][0]
        assert not manual_archive_item.get("record_id")
        before_archive_review_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        archive_item_detail = handler.archive_item_detail(manual_archive_item["id"])
        assert archive_item_detail["item"]["id"] == manual_archive_item["id"]
        reviewed_archive = handler.save_archive_review(
            {"id": manual_archive_item["id"], "status": "needs_lookup", "note": "verification lookup"}
        )
        assert reviewed_archive["ok"] is True
        assert reviewed_archive["archive_item"]["review_status"] == "needs_lookup"
        assert reviewed_archive["archive_item"]["review_note"] == "verification lookup"
        after_archive_review_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        assert len(after_archive_review_backups - before_archive_review_backups) == 1
        lookup_archive = handler.archive_items(
            {"preset": ["unlinked_communications"], "review_status": ["needs_lookup"], "page_size": ["50"]}
        )
        assert lookup_archive["total"] == 1
        assert lookup_archive["items"][0]["id"] == manual_archive_item["id"]
        reviewed_export = handler.export_rows(
            {"type": ["imported_archive"], "preset": ["unlinked_communications"], "review_status": ["needs_lookup"]}
        )["rows"]
        assert len(reviewed_export) == 1
        assert reviewed_export[0]["review_status"] == "needs_lookup"
        assert reviewed_export[0]["review_note"] == "verification lookup"
        archive_review_activity = handler.activity({"type": ["local_change"], "limit": ["100"]})["activity"]
        assert any(
            row["summary"] == f"Archive item #{manual_archive_item['id']} marked Needs lookup"
            for row in archive_review_activity
        )
        before_archive_link_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        linked_archive = handler.link_archive_item(
            {"id": manual_archive_item["id"], "record_type": "person", "record_id": person_id}
        )
        assert linked_archive["ok"] is True
        assert linked_archive["archive_item"]["record_type"] == "person"
        assert linked_archive["archive_item"]["record_id"] == person_id
        assert any(item["id"] == manual_archive_item["id"] for item in linked_archive["detail"]["archive_items"])
        after_archive_link_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        assert len(after_archive_link_backups - before_archive_link_backups) == 1
        with sqlite3.connect(test_db) as conn:
            row = conn.execute(
                "SELECT record_type, record_id FROM imported_archive_items WHERE id = ?",
                (manual_archive_item["id"],),
            ).fetchone()
            assert row == ("person", person_id)
            audit_row = conn.execute(
                """
                SELECT action, record_type, record_id, field_name, old_value, new_value, note
                FROM audit_log
                WHERE action = 'link_archive_item'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            assert audit_row is not None
            assert audit_row[1] == "person"
            assert audit_row[2] == person_id
            assert audit_row[3] == "archive_item.link"
            assert str(manual_archive_item["id"]) in audit_row[5]
            assert "Backup:" in audit_row[6]
        archive_link_activity = handler.activity(
            {"type": ["local_change"], "record_type": ["person"], "limit": ["100"]}
        )["activity"]
        assert any(
            row["summary"] == f"Linked archive item #{manual_archive_item['id']}"
            for row in archive_link_activity
        )
        try:
            handler.link_archive_item({"id": manual_archive_item["id"], "record_type": "person", "record_id": person_id})
            raise AssertionError("Expected already-linked archive item to be rejected")
        except ValueError as exc:
            assert "already linked" in str(exc)
        cleanup_merge_export = handler.export_rows({"type": ["cleanup_merge_drafts"]})
        assert cleanup_merge_export["filename"] == "local_crm_cleanup_merge_drafts_open.csv"
        assert cleanup_merge_export["rows"]
        cleanup_merge_row_types = {row["row_type"] for row in cleanup_merge_export["rows"]}
        assert "draft_summary" in cleanup_merge_row_types
        assert "manual_review_field" in cleanup_merge_row_types
        assert "warning" in cleanup_merge_row_types
        assert any(row.get("keeper_name") for row in cleanup_merge_export["rows"])
        assert any(row.get("keeper_reason") for row in cleanup_merge_export["rows"])
        assert any(row.get("field_name") for row in cleanup_merge_export["rows"] if row["row_type"] == "manual_review_field")
        merge_group_key = "merge.unit@example.test"
        with sqlite3.connect(test_db) as conn:
            company_for_merge = conn.execute("SELECT id FROM companies ORDER BY id LIMIT 1").fetchone()[0]
            stage_for_merge = conn.execute("SELECT id, pipeline_id FROM stages ORDER BY position, id LIMIT 1").fetchone()
            conn.execute(
                """
                INSERT INTO people (
                    zendesk_contact_id, company_id, first_name, last_name, name, normalized_name,
                    email, normalized_email, phone, mobile, title, owner_user_id,
                    customer_status, prospect_status, created_at, updated_at, source_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    company_for_merge,
                    "Merge",
                    "Keeper",
                    "Merge Keeper",
                    "merge keeper",
                    "merge.unit@example.test",
                    merge_group_key,
                    None,
                    None,
                    "Keeper Title",
                    None,
                    "none",
                    "none",
                    "2026-06-09T10:00:00+00:00",
                    "2026-06-09T10:00:00+00:00",
                    "{}",
                ),
            )
            merge_keeper_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO people (
                    zendesk_contact_id, company_id, first_name, last_name, name, normalized_name,
                    email, normalized_email, phone, mobile, title, owner_user_id,
                    customer_status, prospect_status, created_at, updated_at, source_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    company_for_merge,
                    "Merge",
                    "Duplicate",
                    "Merge Duplicate",
                    "merge duplicate",
                    "merge.unit@example.test",
                    merge_group_key,
                    "555-222-3333",
                    "555-333-4444",
                    "Loser Alternate Title",
                    owner_id,
                    "VIP",
                    "Hot Prospect",
                    "2026-06-09T11:00:00+00:00",
                    "2026-06-09T11:00:00+00:00",
                    "{}",
                ),
            )
            merge_loser_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO tags (normalized_name, display_name, definition_count) VALUES (?, ?, 0)",
                ("merge verification tag", "Merge Verification Tag"),
            )
            merge_tag_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO tag_assignments (tag_id, record_type, record_id, source_name) VALUES (?, 'person', ?, ?)",
                (merge_tag_id, merge_loser_id, "Merge Verification Tag"),
            )
            conn.execute(
                """
                INSERT INTO notes (
                    zendesk_note_id, record_type, record_id, creator_user_id, content,
                    note_type, is_important, created_at, updated_at, source_json
                )
                VALUES (?, 'person', ?, ?, ?, 'zendesk', 0, ?, ?, ?)
                """,
                (None, merge_loser_id, None, "Loser note should move to keeper.", "2026-06-09T11:05:00+00:00", "2026-06-09T11:05:00+00:00", "{}"),
            )
            conn.execute(
                """
                INSERT INTO tasks (
                    zendesk_task_id, record_type, record_id, owner_user_id, creator_user_id,
                    content, completed, completed_at, due_date, remind_at, overdue,
                    created_at, updated_at, source_json
                )
                VALUES (?, 'person', ?, ?, ?, ?, 0, NULL, ?, NULL, 0, ?, ?, ?)
                """,
                (
                    None,
                    merge_loser_id,
                    None,
                    None,
                    "Loser task should move to keeper.",
                    "2026-06-12",
                    "2026-06-09T11:06:00+00:00",
                    "2026-06-09T11:06:00+00:00",
                    "{}",
                ),
            )
            conn.execute(
                """
                INSERT INTO deals (
                    zendesk_deal_id, person_id, company_id, pipeline_id, stage_id, name, value,
                    currency, source_id, loss_reason_id, unqualified_reason_id, hot,
                    estimated_close_date, last_activity_at, created_at, updated_at, source_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    merge_loser_id,
                    company_for_merge,
                    stage_for_merge[1],
                    stage_for_merge[0],
                    "Loser Deal Should Move",
                    123.0,
                    "USD",
                    None,
                    None,
                    None,
                    0,
                    None,
                    "2026-06-09T11:07:00+00:00",
                    "2026-06-09T11:07:00+00:00",
                    "2026-06-09T11:07:00+00:00",
                    "{}",
                ),
            )
            merge_deal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO local_addresses (
                    record_type, record_id, address_key, label, line1, line2, city, state,
                    postal_code, country, source, created_at, updated_at
                )
                VALUES ('person', ?, 'address', 'Primary Address', '1 Keeper Way', NULL, 'Keeper City', 'KS', '11111', 'USA', 'local', ?, ?)
                """,
                (merge_keeper_id, "2026-06-09T11:08:00+00:00", "2026-06-09T11:08:00+00:00"),
            )
            conn.execute(
                """
                INSERT INTO local_addresses (
                    record_type, record_id, address_key, label, line1, line2, city, state,
                    postal_code, country, source, created_at, updated_at
                )
                VALUES ('person', ?, 'address', 'Primary Address', '2 Loser Lane', NULL, 'Loser City', 'LS', '22222', 'USA', 'local', ?, ?)
                """,
                (merge_loser_id, "2026-06-09T11:09:00+00:00", "2026-06-09T11:09:00+00:00"),
            )
            conn.execute(
                """
                INSERT INTO local_addresses (
                    record_type, record_id, address_key, label, line1, line2, city, state,
                    postal_code, country, source, created_at, updated_at
                )
                VALUES ('person', ?, 'shipping_address', 'Shipping Address', '3 Shipping Way', NULL, 'Ship City', 'SS', '33333', 'USA', 'local', ?, ?)
                """,
                (merge_loser_id, "2026-06-09T11:10:00+00:00", "2026-06-09T11:10:00+00:00"),
            )
            conn.execute(
                "INSERT INTO custom_field_values (record_type, record_id, field_name, field_value) VALUES ('person', ?, ?, ?)",
                (merge_keeper_id, "Merge Field", "Keeper Value"),
            )
            conn.execute(
                "INSERT INTO custom_field_values (record_type, record_id, field_name, field_value) VALUES ('person', ?, ?, ?)",
                (merge_loser_id, "Merge Field", "Loser Value"),
            )
            conn.execute(
                "INSERT INTO custom_field_values (record_type, record_id, field_name, field_value) VALUES ('person', ?, ?, ?)",
                (merge_loser_id, "Loser Only Field", "Loser Only Value"),
            )
            conn.execute(
                """
                INSERT INTO imported_archive_items (
                    item_type, source_collection, zendesk_record_id, record_type, record_id,
                    related_record_type, related_record_id, original_resource_type, original_resource_id,
                    title, body, direction, occurred_at, created_at, updated_at, user_id,
                    duration_seconds, phone_number, content_type, size_bytes, local_file, url, status, source_json
                )
                VALUES ('document', 'verification_merge_direct', 900001, 'person', ?, NULL, NULL, 'person', ?, 'Merge Direct File', 'Direct archive should move', NULL, ?, ?, ?, NULL, NULL, NULL, 'text/plain', 10, NULL, NULL, NULL, ?)
                """,
                (merge_loser_id, merge_loser_id, "2026-06-09T11:11:00+00:00", "2026-06-09T11:11:00+00:00", "2026-06-09T11:11:00+00:00", "{}"),
            )
            conn.execute(
                """
                INSERT INTO imported_archive_items (
                    item_type, source_collection, zendesk_record_id, record_type, record_id,
                    related_record_type, related_record_id, original_resource_type, original_resource_id,
                    title, body, direction, occurred_at, created_at, updated_at, user_id,
                    duration_seconds, phone_number, content_type, size_bytes, local_file, url, status, source_json
                )
                VALUES ('call', 'verification_merge_related', 900002, NULL, NULL, 'person', ?, 'person', ?, 'Merge Related Call', 'Related archive should move', 'outbound', ?, ?, ?, NULL, 90, '5552223333', NULL, NULL, NULL, NULL, NULL, ?)
                """,
                (merge_loser_id, merge_loser_id, "2026-06-09T11:12:00+00:00", "2026-06-09T11:12:00+00:00", "2026-06-09T11:12:00+00:00", "{}"),
            )
            conn.execute(
                """
                INSERT INTO record_profile_images (
                    record_type, record_id, storage_backend, storage_bucket, storage_key, local_file,
                    original_filename, content_type, bytes, sha256, width, height, status,
                    app_user_id, actor_email, created_at, updated_at
                )
                VALUES ('person', ?, 'local', NULL, 'profile-images/people/test.png', NULL,
                    'merge-loser.png', 'image/png', 12, 'merge-test-sha', 100, 100, 'active',
                    NULL, NULL, ?, ?)
                """,
                (merge_loser_id, "2026-06-09T11:13:00+00:00", "2026-06-09T11:13:00+00:00"),
            )
            for record_id, related_id in [(merge_keeper_id, merge_loser_id), (merge_loser_id, merge_keeper_id)]:
                conn.execute(
                    """
                    INSERT INTO review_flags (
                        flag_type, severity, record_type, record_id, related_record_type,
                        related_record_id, flag_key, description
                    )
                    VALUES ('duplicate_person_email', 'medium', 'person', ?, 'person', ?, ?, ?)
                    """,
                    (record_id, related_id, merge_group_key, "Verification duplicate people merge group."),
                )
            conn.commit()
        merge_detail_before = handler.cleanup_groups(
            {"type": ["duplicate_people"], "status": ["open"], "key": [merge_group_key], "page_size": ["10"]}
        )
        assert merge_detail_before["merge_draft"]
        before_merge_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        merged_people = handler.merge_duplicate_people(
            {
                "key": merge_group_key,
                "keeper_id": merge_keeper_id,
                "status": "open",
                "note": "verification duplicate merge",
            }
        )
        assert merged_people["ok"] is True
        assert merged_people["keeper_id"] == merge_keeper_id
        assert merged_people["merged_ids"] == [merge_loser_id]
        assert merged_people["summary"]["moved"]["notes"] == 1
        assert merged_people["summary"]["moved"]["tasks"] == 1
        assert merged_people["summary"]["moved"]["deals"] == 1
        assert merged_people["summary"]["moved"]["archive_items"] == 2
        assert merged_people["summary"]["profile_image"]["moved"] == 1
        assert any(item["field"] == "phone" for item in merged_people["summary"]["filled_fields"])
        assert any(item["field"] == "title" for item in merged_people["summary"]["field_conflicts"])
        assert any(item["address_key"] == "shipping_address" for item in merged_people["summary"]["address_fills"])
        assert any(item["address_key"] == "address" for item in merged_people["summary"]["address_conflicts"])
        assert any(item["field"] == "Merge Field" for item in merged_people["summary"]["custom_field_conflicts"])
        after_merge_backups = {path.name for path in server.BACKUP_DIR.glob("*.sqlite")}
        assert len(after_merge_backups - before_merge_backups) == 1
        merged_detail = merged_people["detail"]
        assert merged_detail["record"]["phone"] == "555-222-3333"
        assert merged_detail["record"]["mobile"] == "555-333-4444"
        assert merged_detail["record"]["title"] == "Keeper Title"
        assert merged_detail["record"]["customer_status"] == "VIP"
        assert "Merge Verification Tag" in merged_detail["tags"]
        assert any(note["content"] == "Loser note should move to keeper." for note in merged_detail["notes"])
        merge_note = next(note for note in merged_detail["notes"] if "Merged duplicate people into this record." in note["content"])
        assert "Loser Alternate Title" in merge_note["content"]
        assert "2 Loser Lane" in merge_note["content"]
        assert "verification duplicate merge" in merge_note["content"]
        assert any(task["content"] == "Loser task should move to keeper." for task in merged_detail["tasks"])
        assert any(deal["source_id"] == merge_deal_id for deal in merged_detail["deals"])
        assert any(item["title"] == "Merge Direct File" for item in merged_detail["archive_items"])
        assert any(item["title"] == "Merge Related Call" for item in merged_detail["archive_items"])
        assert any(address["address_key"] == "shipping_address" and address["line1"] == "3 Shipping Way" for address in merged_detail["addresses"])
        assert any(field["field_name"] == "Loser Only Field" and field["field_value"] == "Loser Only Value" for field in merged_detail["custom_fields"])
        assert merged_detail["profile_image"]
        with sqlite3.connect(test_db) as conn:
            assert conn.execute(
                "SELECT count(*) FROM tag_assignments WHERE record_type = 'person' AND record_id = ?",
                (merge_loser_id,),
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT lifecycle_status FROM local_record_lifecycle WHERE record_type = 'person' AND record_id = ?",
                (merge_loser_id,),
            ).fetchone()[0] == "inactive"
            assert conn.execute("SELECT person_id FROM deals WHERE id = ?", (merge_deal_id,)).fetchone()[0] == merge_keeper_id
            assert conn.execute(
                "SELECT count(*) FROM review_flags WHERE flag_key = ? AND status = 'open'",
                (merge_group_key,),
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT count(*) FROM review_flags WHERE flag_key = ? AND status = 'resolved'",
                (merge_group_key,),
            ).fetchone()[0] == 2
            merge_audit = conn.execute(
                """
                SELECT action, record_type, record_id, field_name, new_value, note, permission_action
                FROM audit_log
                WHERE action = 'merge_duplicate_people'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            assert merge_audit is not None
            assert merge_audit[1] == "person"
            assert merge_audit[2] == merge_keeper_id
            assert merge_audit[3] == "duplicate_people"
            assert str(merge_loser_id) in merge_audit[4]
            assert "Backup:" in merge_audit[5]
            assert merge_audit[6] == "merge_duplicate_people"
        active_people_after_merge = handler.list_records(
            {"type": ["people"], "q": [merge_group_key], "page_size": ["10"]}
        )
        all_people_after_merge = handler.list_records(
            {"type": ["people"], "q": [merge_group_key], "lifecycle": ["all"], "page_size": ["10"]}
        )
        assert active_people_after_merge["lifecycle_filter"] == "active"
        assert all_people_after_merge["lifecycle_filter"] == "all"
        assert active_people_after_merge["lifecycle_counts"]["inactive"] >= 1
        assert {record["source_id"] for record in active_people_after_merge["records"]} == {merge_keeper_id}
        assert {record["source_id"] for record in all_people_after_merge["records"]} == {merge_keeper_id, merge_loser_id}
        inactive_merge_record = next(record for record in all_people_after_merge["records"] if record["source_id"] == merge_loser_id)
        assert inactive_merge_record["lifecycle_status"] == "inactive"
        exported_all_people_after_merge = handler.export_list_rows(
            {"type": ["people"], "q": [merge_group_key], "lifecycle": ["all"]}
        )
        exported_inactive_merge_record = next(row for row in exported_all_people_after_merge["rows"] if row["source_id"] == merge_loser_id)
        assert exported_inactive_merge_record["lifecycle_status"] == "inactive"
        merge_activity = handler.activity({"type": ["person"], "id": [str(merge_keeper_id)], "limit": ["50"]})["activity"]
        assert any(row["activity_type"] == "cleanup_decision" and "Merged duplicate people" in row["summary"] for row in merge_activity)
        application_profile_rows = handler.export_rows({"type": ["application_profiles"]})["rows"]
        assert application_profile_rows
        assert any(row["record_type"] == "lead" and row["APP Number"] for row in application_profile_rows)
        with sqlite3.connect(test_db) as conn:
            expected_profile_rows = conn.execute(
                """
                SELECT count(*)
                FROM (
                    SELECT record_type, record_id
                    FROM custom_field_values
                    WHERE record_type IN ('lead', 'person')
                      AND field_name IN ({})
                    GROUP BY record_type, record_id
                )
                """.format(",".join("?" for _ in profile_fields)),
                profile_fields,
            ).fetchone()[0]
        assert len(application_profile_rows) == expected_profile_rows
        address_rows = handler.export_rows({"type": ["addresses"]})["rows"]
        assert any(row["record_type"] == "person" and row["record_id"] == 2 and row["city"] == "Columbus Verification" for row in address_rows)

        flags = handler.review_flags({"status": ["open"], "page_size": ["50"]})["flags"]
        assert flags, "Expected at least one open review flag"
        group_type_by_flag = {
            "duplicate_person_email": "duplicate_people",
            "duplicate_lead_email": "duplicate_leads",
            "lead_person_email_overlap": "lead_person_overlap",
        }
        flag = next(row for row in flags if row["flag_type"] in group_type_by_flag)
        cleanup_before = handler.cleanup()
        assert cleanup_before["status_counts"]["open"] >= 1
        group_type = group_type_by_flag[flag["flag_type"]]
        decision_saved = handler.save_cleanup_decision(
            {
                "type": group_type,
                "key": flag["flag_key"],
                "status": "open",
                "decision": "merge_later",
                "note": "verification group decision",
            }
        )
        assert decision_saved["ok"] is True
        assert decision_saved["decision"]["decision"] == "merge_later"
        assert decision_saved["decision"]["note"] == "verification group decision"
        decision_detail = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "key": [flag["flag_key"]], "page_size": ["10"]}
        )
        assert decision_detail["decision"]["decision"] == "merge_later"
        decision_list = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "page_size": ["50"]}
        )["groups"]
        assert any(row["group_key"] == flag["flag_key"] and row["decision"]["decision"] == "merge_later" for row in decision_list)
        decision_filtered = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "decision": ["merge_later"], "page_size": ["50"]}
        )
        assert decision_filtered["decision"] == "merge_later"
        assert decision_filtered["total"] >= 1
        assert all(row["decision"]["decision"] == "merge_later" for row in decision_filtered["groups"])
        assert any(row["group_key"] == flag["flag_key"] for row in decision_filtered["groups"])
        no_decision_filtered = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "decision": ["none"], "page_size": ["50"]}
        )
        assert no_decision_filtered["decision"] == "none"
        assert all(not row["decision"] for row in no_decision_filtered["groups"])
        review_remaining_filtered = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "decision": ["review_remaining"], "page_size": ["50"]}
        )
        assert review_remaining_filtered["decision"] == "review_remaining"
        assert all(
            not row["decision"] or row["decision"]["decision"] == "needs_review"
            for row in review_remaining_filtered["groups"]
        )
        assert not any(row["group_key"] == flag["flag_key"] for row in review_remaining_filtered["groups"])
        decision_sorted = handler.cleanup_groups(
            {"type": [group_type], "status": ["open"], "sort": ["decision"], "page_size": ["50"]}
        )
        assert decision_sorted["sort"] == "decision"
        decision_export = handler.export_cleanup_group_rows({"type": [group_type], "status": ["open"]})["rows"]
        assert any(
            row["group_key"] == flag["flag_key"]
            and row["decision"] == "merge_later"
            and row["decision_note"] == "verification group decision"
            for row in decision_export
        )
        decision_export_filtered = handler.export_cleanup_group_rows(
            {"type": [group_type], "status": ["open"], "decision": ["merge_later"]}
        )["rows"]
        assert decision_export_filtered
        assert all(row["decision_filter"] == "merge_later" and row["decision"] == "merge_later" for row in decision_export_filtered)
        review_remaining_export = handler.export_cleanup_group_rows(
            {"type": [group_type], "status": ["open"], "decision": ["review_remaining"]}
        )["rows"]
        assert all(row["decision_filter"] == "review_remaining" for row in review_remaining_export)
        assert all(not row["decision"] or row["decision"] == "needs_review" for row in review_remaining_export)
        ignored = handler.resolve_flag({"id": flag["id"], "status": "ignored", "note": "verification ignore"})
        assert ignored["ok"] is True
        ignored_flags = handler.review_flags({"status": ["ignored"], "page_size": ["10"]})["flags"]
        assert any(row["id"] == flag["id"] for row in ignored_flags)
        assert next(row for row in ignored_flags if row["id"] == flag["id"])["resolution_note"] == "verification ignore"
        ignored_group = handler.cleanup_groups(
            {"type": [group_type], "status": ["ignored"], "key": [flag["flag_key"]], "page_size": ["10"]}
        )
        assert any(row["id"] == flag["id"] for row in ignored_group["flags"])
        reopened = handler.resolve_flag({"id": flag["id"], "status": "open", "note": "verification reopen"})
        assert reopened["ok"] is True
        reopened_flags = handler.review_flags({"status": ["open"], "page_size": ["10"]})["flags"]
        assert any(row["id"] == flag["id"] for row in reopened_flags)
        assert next(row for row in reopened_flags if row["id"] == flag["id"])["resolution_note"] == "verification reopen"
        resolved = handler.resolve_flag({"id": flag["id"], "status": "resolved", "note": "verification"})
        assert resolved["ok"] is True
        resolved_flags = handler.review_flags({"status": ["resolved"], "page_size": ["10"]})["flags"]
        assert any(row["id"] == flag["id"] for row in resolved_flags)
        assert next(row for row in resolved_flags if row["id"] == flag["id"])["resolution_note"] == "verification"
        global_activity = handler.activity({"limit": ["100"]})["activity"]
        record_activity = handler.activity(
            {"type": [flag["record_type"]], "id": [str(flag["record_id"])], "limit": ["50"]}
        )["activity"]
        assert any(
            row["activity_type"] == "cleanup_decision"
            and row["record_type"] == flag["record_type"]
            and row["record_id"] == flag["record_id"]
            and "Cleanup flag" in row["summary"]
            and "resolved" in row["summary"]
            and "verification" in row["summary"]
            for row in global_activity
        )
        assert any(
            row["activity_type"] == "cleanup_decision"
            and row["record_type"] == "cleanup_group"
            and "Cleanup group decision" in row["summary"]
            and "Merge Later" in row["summary"]
            and "verification group decision" in row["summary"]
            for row in global_activity
        )
        assert any(
            row["activity_type"] == "cleanup_decision"
            and "Cleanup flag" in row["summary"]
            and "resolved" in row["summary"]
            and "verification" in row["summary"]
            for row in record_activity
        )
        project_decision = handler.save_project_decision(
            {
                "key": "duplicate_tag_policy",
                "status": "decided",
                "choice": "mark_normalized_tags_handled",
                "note": "verification project decision",
            }
        )
        assert project_decision["ok"] is True
        assert project_decision["backup"]
        project_decision_backup = Path(project_decision["backup"])
        assert project_decision_backup.exists()
        assert "_before_project_decision_duplicate_tag" in project_decision_backup.name
        assert project_decision["decision"]["status"] == "decided"
        assert project_decision["decision"]["choice"] == "mark_normalized_tags_handled"
        assert project_decision["decision"]["note"] == "verification project decision"
        project_decisions_after = handler.project_decisions()
        assert project_decisions_after["decided"] >= 1
        assert next(item for item in project_decisions_after["decisions"] if item["key"] == "duplicate_tag_policy")["choice_label"] == "Mark normalized tags handled"
        execution_preview_after = handler.cleanup_execution_preview(project_decisions_after)
        tag_action = next(action for action in execution_preview_after["actions"] if action["action_type"] == "mark_duplicate_tags_handled")
        assert tag_action["status"] == "eligible"
        assert tag_action["eligible_groups"] >= 1
        assert execution_preview_after["status"] == "locked"
        assert execution_preview_after["totals"]["blocked_gates"] >= 1
        project_activity = handler.activity({"limit": ["100"]})["activity"]
        assert any(
            row["activity_type"] == "project_decision"
            and "Project decision saved" in row["summary"]
            and "Duplicate tag policy" in row["summary"]
            and "verification project decision" in row["summary"]
            for row in project_activity
        )

        with sqlite3.connect(test_db) as conn:
            audit_count = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]
            assert audit_count >= 14
            address_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'update_address'").fetchone()[0]
            assert address_audit_count >= 1
            tag_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'update_tags'").fetchone()[0]
            assert tag_audit_count >= 1
            note_update_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'update_note'").fetchone()[0]
            assert note_update_audit_count >= 1
            task_update_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'update_task'").fetchone()[0]
            assert task_update_audit_count >= 1
            task_copy_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'copy_imported_task_to_local'").fetchone()[0]
            assert task_copy_audit_count >= 1
            task_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'complete_task'").fetchone()[0]
            assert task_audit_count >= 2
            flag_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'resolve_flag'").fetchone()[0]
            assert flag_audit_count >= 3
            restore_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'restore_backup'").fetchone()[0]
            assert restore_count == 1
            group_decision_count = conn.execute("SELECT count(*) FROM cleanup_group_decisions").fetchone()[0]
            assert group_decision_count >= 1
            group_decision_audit_count = conn.execute("SELECT count(*) FROM audit_log WHERE action = 'save_cleanup_decision'").fetchone()[0]
            assert group_decision_audit_count >= 1

        backups = sorted((temp_path / "backups").glob("local_crm_*.sqlite"))
        assert len(backups) >= 18
        assert sum(1 for backup in backups if "_before_tags_" in backup.name) >= 1
        assert sum(1 for backup in backups if "_before_note_update_" in backup.name) >= 1
        assert sum(1 for backup in backups if "_before_task_update_" in backup.name) >= 1
        assert sum(1 for backup in backups if "_before_flag_" in backup.name) >= 3
        assert sum(1 for backup in backups if "_before_cleanup_decision_" in backup.name) >= 1
        assert sum(1 for backup in backups if "_before_project_decision_" in backup.name) >= 1

    print("Local CRM operations verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
