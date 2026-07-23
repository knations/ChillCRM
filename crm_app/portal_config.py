"""ChillPortal configuration scaffold for CHILLCRM.

This module is intentionally conservative. It reserves names, routes, roles,
and feature flags for the future client-facing portal while keeping client
access, invitations, and provider integrations disabled until explicitly
approved.
"""

from __future__ import annotations


PORTAL_ROUTE_PREFIX = "/portal"
PORTAL_DEFAULT_ROUTE = "/portal"
PORTAL_PRIMARY_RECORD_TYPE = "people"
PORTAL_OPTIONAL_CONTEXT_RECORD_TYPES = ("companies",)

PORTAL_STATUS_LABELS = (
    "draft",
    "invited",
    "active",
    "paused",
    "completed",
    "archived",
)

PORTAL_NAV_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "route": "/portal",
        "enabled_flag": "CHILLPORTAL_FEATURE_DASHBOARD",
    },
    {
        "key": "shared_documents",
        "label": "Shared Documents",
        "route": "/portal#documents",
        "enabled_flag": "CHILLPORTAL_FEATURE_DOCUMENTS",
    },
    {
        "key": "client_next_steps",
        "label": "Client Next Steps",
        "route": "/portal#next-steps",
        "enabled_flag": "CHILLPORTAL_FEATURE_NEXT_STEPS",
    },
    {
        "key": "calls_notes",
        "label": "Client Notes",
        "route": "/portal#client-notes",
        "enabled_flag": "CHILLPORTAL_FEATURE_CLIENT_NOTES",
    },
)

PORTAL_FEATURE_FLAGS = {
    "CHILLPORTAL_ENABLED": False,
    "CHILLPORTAL_FEATURE_DASHBOARD": False,
    "CHILLPORTAL_FEATURE_DOCUMENTS": False,
    "CHILLPORTAL_FEATURE_NEXT_STEPS": False,
    "CHILLPORTAL_FEATURE_CLIENT_NOTES": False,
}

PORTAL_SCHEMA_PLAN = {
    "portal_profiles": {
        "purpose": "One portal dashboard per approved person record.",
        "owner_record_type": "people",
        "required_fields": (
            "id",
            "person_id",
            "status",
            "display_name",
            "company_id",
            "created_at",
            "updated_at",
        ),
    },
    "portal_shared_documents": {
        "purpose": "Manual client-visible document links for one person portal.",
        "owner_record_type": "people",
        "required_fields": (
            "id",
            "person_id",
            "record_file_id",
            "title",
            "visibility_status",
            "shared_at",
            "shared_by_user_id",
        ),
    },
    "portal_next_steps": {
        "purpose": "Separate client-visible next steps, not internal CRM tasks.",
        "owner_record_type": "people",
        "required_fields": (
            "id",
            "person_id",
            "title",
            "details",
            "due_at",
            "status",
            "sort_order",
            "created_at",
            "updated_at",
        ),
    },
    "portal_client_notes": {
        "purpose": "Separate client-visible notes, not internal notes or call logs.",
        "owner_record_type": "people",
        "required_fields": (
            "id",
            "person_id",
            "title",
            "body",
            "visibility_status",
            "published_at",
            "published_by_user_id",
            "created_at",
            "updated_at",
        ),
    },
}

PORTAL_ROLES = {
    "portal_client": {
        "label": "Portal Client",
        "scope": "client_visible_records_only",
    },
    "portal_contact": {
        "label": "Portal Contact",
        "scope": "assigned_client_account_only",
    },
}

INTERNAL_PORTAL_PERMISSION_ACTIONS = {
    "manage_portal_visibility": ("owner", "admin"),
    "preview_portal_experience": ("owner", "admin", "staff"),
    "manage_portal_invites": ("owner", "admin"),
    "publish_portal_status_updates": ("owner", "admin", "staff"),
}

PORTAL_USER_PERMISSION_ACTIONS = {
    "view_own_portal_dashboard": ("portal_client", "portal_contact"),
    "view_own_shared_documents": ("portal_client", "portal_contact"),
    "view_own_next_steps": ("portal_client", "portal_contact"),
    "view_own_client_notes": ("portal_client", "portal_contact"),
}

PORTAL_FORBIDDEN_INTERNAL_SCOPES = (
    "crm_people_list",
    "crm_company_list",
    "crm_deal_pipeline",
    "internal_notes",
    "internal_call_logs",
    "internal_tasks",
    "audit_log",
    "cleanup",
    "exports",
    "admin_users",
)
