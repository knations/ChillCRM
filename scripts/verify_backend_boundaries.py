#!/usr/bin/env python3
"""Verify current CHILLCRM backend module boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.auth_tokens as auth_tokens
import crm_app.database as database
import crm_app.exporting as exporting
import crm_app.file_assets as file_assets
import crm_app.request_io as request_io
import crm_app.runtime_health as runtime_health
import crm_app.server as server


def main() -> int:
    server_py = (PROJECT_ROOT / "crm_app" / "server.py").read_text(encoding="utf-8")
    auth_tokens_py = (PROJECT_ROOT / "crm_app" / "auth_tokens.py").read_text(encoding="utf-8")
    database_py = (PROJECT_ROOT / "crm_app" / "database.py").read_text(encoding="utf-8")
    exporting_py = (PROJECT_ROOT / "crm_app" / "exporting.py").read_text(encoding="utf-8")
    file_assets_py = (PROJECT_ROOT / "crm_app" / "file_assets.py").read_text(encoding="utf-8")
    request_io_py = (PROJECT_ROOT / "crm_app" / "request_io.py").read_text(encoding="utf-8")
    runtime_health_py = (PROJECT_ROOT / "crm_app" / "runtime_health.py").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "crm_app" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (PROJECT_ROOT / "crm_app" / "static" / "index.html").read_text(encoding="utf-8")

    assert "from crm_app.auth_tokens import" in server_py
    assert "from crm_app.database import" in server_py
    assert "from crm_app import exporting" in server_py
    assert "from crm_app import file_assets" in server_py
    assert "from crm_app import runtime_health" in server_py
    assert "from crm_app import request_io" in server_py
    assert "class PostgresCompatConnection" not in server_py
    assert "def translate_sqlite_sql_for_postgres" not in server_py
    assert "def get_json_route_handlers" in server_py
    assert "def get_csv_route_handlers" in server_py
    assert "def post_json_route_handlers" in server_py
    assert "def password_hash" in auth_tokens_py
    assert "def signed_session_token" in auth_tokens_py
    assert "def read_webhook_body" in request_io_py
    assert "def export_package_status" in exporting_py
    assert "def decode_profile_image_upload" in file_assets_py
    assert "payment=(), usb=(), fullscreen=(self)" in server_py
    assert "class PostgresCompatConnection" in database_py
    assert "def translate_sqlite_sql_for_postgres" in database_py
    assert "def runtime_context" in runtime_health_py
    assert "def reports_health_check" in runtime_health_py

    hashed = auth_tokens.password_hash("correct horse")
    assert auth_tokens.verify_password("correct horse", hashed)
    assert not auth_tokens.verify_password("wrong horse", hashed)
    token = auth_tokens.signed_session_token({"uid": 1, "exp": 4_102_444_800}, "secret")
    assert auth_tokens.verify_signed_session_token(token, "secret")["uid"] == 1
    assert auth_tokens.verify_signed_session_token(token, "other-secret") is None
    translated = database.translate_sqlite_sql_for_postgres(
        "SELECT id FROM people WHERE source_json LIKE :needle AND date(updated_at) >= date('now')"
    )
    assert "CAST(source_json AS TEXT) ILIKE" in translated
    assert "CAST(updated_at AS date) >= CURRENT_DATE" in translated
    assert database.postgres_parameters_for_sql("SELECT * FROM people WHERE email LIKE :email", {"email": "%@%"}) == ["%@%"]
    assert database.PostgresCompatRow(["id", "name"], (1, "Probe"))[0] == 1
    assert server.PostgresCompatRow(["id"], (2,))[0] == 2

    assert runtime_health.remote_write_lock_status(False, set())["mode"] == "unlocked"
    assert runtime_health.bulk_package_export_status(True)["mode"] == "enabled"
    assert runtime_health.document_file_access_status(True)["mode"] == "enabled"
    assert request_io.read_webhook_body(
        rfile=type("Body", (), {"read": lambda self, length: b"email=test@example.com&name=Test"})(),
        headers={"Content-Length": "32", "Content-Type": "application/x-www-form-urlencoded"},
        max_body_bytes=100,
    )["email"] == "test@example.com"
    assert file_assets.profile_image_magic_matches("image/png", b"\x89PNG\r\n\x1a\nsample")
    assert file_assets.safe_original_filename("../Bad:name?.pdf") == "Bad_name_.pdf"
    assert file_assets.record_file_storage_key("person", 7, "abcdef1234567890abcdef123456", "Call Notes", "text/plain").endswith("Call Notes.txt")
    assert exporting.complete_package_filename("20260805T000000Z") == "chillcrm_complete_package_20260805T000000Z.zip"
    assert exporting.include_report_in_package("local_crm_data_quality.md")
    assert not exporting.include_report_in_package("source_of_truth_cutover_preflight.md")
    route_probe = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    assert "/api/list" in route_probe.get_json_route_handlers({})
    assert "/api/export" in route_probe.get_csv_route_handlers({})
    assert "/api/update_record" in route_probe.post_json_route_handlers({}, None, None)

    active_public_text = "\n".join([app_js, index_html])
    legacy_provider = "Zen" + "desk"
    for old_label in [
        f"{legacy_provider} Snapshot",
        f"Final {legacy_provider}",
        "Migration" + " Status",
        "Complete Local " + "CRM",
        "Downloaded Document " + "Files",
    ]:
        assert old_label not in active_public_text
    assert "ChillCRM" in index_html
    assert "Have Fun Get Rich" in index_html
    assert exporting.COMPLETE_PACKAGE_FILENAME == "chillcrm_complete_package.zip"
    assert exporting.DOCUMENT_FILES_PACKAGE_FILENAME == "chillcrm_document_files.zip"

    print("CHILLCRM backend boundary verifier passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
