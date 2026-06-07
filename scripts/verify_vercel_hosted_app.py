#!/usr/bin/env python3
"""Smoke-test the locked Vercel-hosted CHILLCRM app."""

from __future__ import annotations

import csv
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
EXPECTED_COUNTS = {"people": 997, "companies": 378, "leads": 1327, "deals": 125}
STORAGE_MANIFEST = REPORTS_DIR / "chillcrm_supabase_storage_manifest.csv"


class HttpResult:
    def __init__(self, status: int, headers: Any, body: bytes):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self) -> dict[str, Any]:
        return json.loads(self.body.decode("utf-8")) if self.body else {}


def prompt_secret(label: str, env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    return getpass.getpass(f"{label}: ").strip()


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        raise RuntimeError("Set CHILLCRM_VERCEL_URL or pass the URL as the first argument.")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def public_app_auth_domain(base_url: str) -> bool:
    host = urllib.parse.urlparse(base_url).hostname or ""
    return host.lower() in {"chillcrm.app", "www.chillcrm.app"}


def storage_manifest_archive_ids() -> list[int]:
    if not STORAGE_MANIFEST.exists():
        return []
    ids: list[int] = []
    with STORAGE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("status") or "").strip().lower() not in {"uploaded", "ready", "skipped_existing"}:
                continue
            try:
                ids.append(int(row.get("archive_item_id") or 0))
            except (TypeError, ValueError):
                continue
    return [item_id for item_id in ids if item_id]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def request(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    bypass_secret: str = "",
) -> HttpResult:
    data = None
    headers: dict[str, str] = {"Accept": "application/json"}
    if bypass_secret:
        headers["x-vercel-protection-bypass"] = bypass_secret
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=90) as response:
            return HttpResult(response.status, response.headers, response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.headers, exc.read())


def record(rows: list[dict[str, str]], step: str, status: str, evidence: str) -> None:
    rows.append({"step": step, "status": status, "evidence": evidence})


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def body_text(result: HttpResult) -> str:
    return result.body.decode("utf-8", errors="replace")


def login_opener(base_url: str, email: str, password: str, bypass_secret: str) -> urllib.request.OpenerDirector:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login = request(opener, base_url, "POST", "/api/auth/login", {"email": email, "password": password}, bypass_secret=bypass_secret)
    assert_equal(login.status, 200, f"{email} login status")
    assert_equal(login.json().get("ok"), True, f"{email} login ok")
    return opener


def write_report(base_url: str, rows: list[dict[str, str]]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    passed = sum(1 for row in rows if row["status"] == "passed")
    failed = sum(1 for row in rows if row["status"] == "failed")
    md = [
        "# Vercel Hosted App Smoke Test",
        "",
        "This report verifies the hosted CHILLCRM staging app without writing CRM data or recording secrets.",
        "",
        f"- URL: `{base_url}`.",
        f"- Passed: `{passed}`.",
        f"- Failed: `{failed}`.",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        md.append(f"| {row['step']} | {row['status']} | {row['evidence'].replace('|', '/')} |")
    (REPORTS_DIR / "vercel_hosted_app_smoke.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (REPORTS_DIR / "vercel_hosted_app_smoke.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "status", "evidence"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    base_url = normalize_base_url(
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHILLCRM_VERCEL_URL", "")
    )
    email = os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", "").strip() or input("Admin email: ").strip()
    recovery_password = os.environ.get("CHILLCRM_OWNER_RECOVERY_PASSWORD", "").strip()
    password = recovery_password or prompt_secret("Bootstrap password", "AUTH_BOOTSTRAP_ADMIN_PASSWORD")
    bypass_secret = os.environ.get("VERCEL_PROTECTION_BYPASS_SECRET", "").strip()
    if not bypass_secret and not public_app_auth_domain(base_url) and not env_flag("CHILLCRM_SKIP_VERCEL_BYPASS"):
        bypass_secret = prompt_secret("Vercel protection bypass secret", "VERCEL_PROTECTION_BYPASS_SECRET")
    expect_document_file_access = env_flag("EXPECT_DOCUMENT_FILE_ACCESS")

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirectHandler)
    rows: list[dict[str, str]] = []

    try:
        health = request(opener, base_url, "GET", "/api/health", bypass_secret=bypass_secret)
        assert_equal(health.status, 200, "health status")
        health_payload = health.json()
        runtime = health_payload["runtime"]
        assert health_payload["ok"] is True
        assert_equal(runtime["environment"], "staging", "runtime environment")
        assert_equal(runtime["database_mode"], "hosted_postgres_adapter_enabled", "database mode")
        assert_equal(runtime["auth"]["required"], True, "auth required")
        assert_equal(runtime["remote_write_lock"]["enabled"], True, "remote write lock")
        assert_equal(runtime["bulk_package_exports"]["enabled"], False, "bulk package exports")
        assert_equal(runtime["document_file_access"]["enabled"], expect_document_file_access, "document file access")
        record(rows, "health", "passed", "hosted Postgres reachable, staging locks enabled")
    except Exception as exc:
        record(rows, "health", "failed", str(exc))

    try:
        auth_status = request(opener, base_url, "GET", "/api/auth/status", bypass_secret=bypass_secret)
        assert_equal(auth_status.status, 200, "auth status code")
        auth_payload = auth_status.json()
        assert_equal(auth_payload["auth_required"], True, "auth required status")
        assert_equal(auth_payload["authenticated"], False, "initial authenticated status")
        record(rows, "unauthenticated_status", "passed", "auth required and no user session before login")
    except Exception as exc:
        record(rows, "unauthenticated_status", "failed", str(exc))

    try:
        denied = request(opener, base_url, "GET", "/api/summary", bypass_secret=bypass_secret)
        assert_equal(denied.status, 401, "unauthenticated summary status")
        assert_equal(denied.json().get("code"), "auth_required", "unauthenticated summary code")
        record(rows, "unauthenticated_data_denied", "passed", "summary denied before login")
    except Exception as exc:
        record(rows, "unauthenticated_data_denied", "failed", str(exc))

    try:
        index = request(opener, base_url, "GET", "/", bypass_secret=bypass_secret)
        assert_equal(index.status, 200, "index status")
        index_text = body_text(index)
        if 'id="usersView"' not in index_text or 'data-view="users"' not in index_text:
            raise AssertionError("Users view shell was not present in hosted index.")
        app_js = request(opener, base_url, "GET", "/static/app.js", bypass_secret=bypass_secret)
        assert_equal(app_js.status, 200, "app js status")
        app_text = body_text(app_js)
        if "renderUsers" not in app_text or "/api/app_users/save" not in app_text:
            raise AssertionError("Users UI code was not present in hosted app bundle.")
        if 'id="passwordOverlay"' not in index_text or "/api/auth/change_password" not in app_text:
            raise AssertionError("Self-service password change UI was not present in hosted bundle.")
        if 'id="ownerRecoveryOverlay"' not in index_text or "/api/auth/owner_password_recovery" not in app_text:
            raise AssertionError("Controlled owner password recovery UI was not present in hosted bundle.")
        if "Owner Intake" not in app_text:
            raise AssertionError("Owner production-gate intake link was not present in hosted app bundle.")
        record(rows, "owner_users_ui_static", "passed", "hosted bundle includes owner Users screen and API wiring")
    except Exception as exc:
        record(rows, "owner_users_ui_static", "failed", str(exc))

    if recovery_password:
        try:
            recovery = request(
                opener,
                base_url,
                "POST",
                "/api/auth/owner_password_recovery",
                {"email": email, "new_password": recovery_password},
                bypass_secret=bypass_secret,
            )
            assert_equal(recovery.status, 200, "owner recovery status")
            recovery_payload = recovery.json()
            assert_equal(recovery_payload.get("ok"), True, "owner recovery ok")
            assert_equal(recovery_payload["auth"]["authenticated"], True, "owner recovery authenticated")
            assert any(cookie.name == "chillcrm_session" and cookie.secure for cookie in jar)
            record(rows, "owner_password_recovery", "passed", f"owner password recovery completed for {email}")
        except Exception as exc:
            record(rows, "owner_password_recovery", "failed", str(exc))

    try:
        login = request(opener, base_url, "POST", "/api/auth/login", {"email": email, "password": password}, bypass_secret=bypass_secret)
        assert_equal(login.status, 200, "login status")
        login_payload = login.json()
        assert_equal(login_payload["ok"], True, "login ok")
        assert_equal(login_payload["auth"]["authenticated"], True, "login authenticated")
        assert any(cookie.name == "chillcrm_session" and cookie.secure for cookie in jar)
        record(rows, "owner_login", "passed", f"logged in as {email}")
    except Exception as exc:
        record(rows, "owner_login", "failed", str(exc))

    try:
        summary = request(opener, base_url, "GET", "/api/summary", bypass_secret=bypass_secret)
        assert_equal(summary.status, 200, "summary status")
        payload = summary.json()
        counts = payload["counts"]
        for key, expected in EXPECTED_COUNTS.items():
            assert_equal(counts.get(key), expected, f"{key} count")
        production_gates = request(opener, base_url, "GET", "/api/production_gates", bypass_secret=bypass_secret)
        assert_equal(production_gates.status, 200, "production gates status")
        owner_intake = (((production_gates.json().get("production_gates") or {}).get("reports") or {}).get("owner_intake") or "")
        assert_equal(owner_intake, "/reports/owner_gate_intake_packet.md", "owner intake report link")
        record(rows, "authenticated_summary_counts", "passed", str({key: counts[key] for key in EXPECTED_COUNTS}))
    except Exception as exc:
        record(rows, "authenticated_summary_counts", "failed", str(exc))

    smoke_stamp = int(time.time())
    role_smoke_users: dict[str, dict[str, Any]] = {}
    try:
        app_users = request(opener, base_url, "GET", "/api/app_users", bypass_secret=bypass_secret)
        assert_equal(app_users.status, 200, "app users status")
        available_roles = {role.get("role_key") for role in app_users.json().get("roles", [])}
        for role in ["admin", "staff", "read_only", "migration_operator"]:
            if role not in available_roles:
                raise AssertionError(f"Role {role} was not available.")
            user_email = f"codex-smoke-{role.replace('_', '-')}-{smoke_stamp}@example.test"
            created = request(
                opener,
                base_url,
                "POST",
                "/api/app_users/save",
                {
                    "email": user_email,
                    "display_name": f"Codex Smoke {role}",
                    "roles": [role],
                    "generate_password": True,
                },
                bypass_secret=bypass_secret,
            )
            assert_equal(created.status, 200, f"create {role} app user status")
            created_payload = created.json()
            assert_equal(created_payload.get("ok"), True, f"create {role} app user ok")
            user_password = created_payload.get("temporary_password", "")
            user_id = int((created_payload.get("user") or {}).get("id") or 0)
            if not user_password or not user_id:
                raise AssertionError(f"Created {role} user did not include one-time password and id.")
            role_smoke_users[role] = {"email": user_email, "password": user_password, "id": user_id}
        record(rows, "app_user_lifecycle_owner_api", "passed", "owner created Admin, Staff, Read-only, and Migration Operator smoke users")
    except Exception as exc:
        record(rows, "app_user_lifecycle_owner_api", "failed", str(exc))

    if role_smoke_users:
        try:
            role_openers = {
                role: login_opener(base_url, data["email"], data["password"], bypass_secret)
                for role, data in role_smoke_users.items()
            }
            for role, role_opener in role_openers.items():
                role_summary = request(role_opener, base_url, "GET", "/api/summary", bypass_secret=bypass_secret)
                assert_equal(role_summary.status, 200, f"{role} summary status")
                role_users = request(role_opener, base_url, "GET", "/api/app_users", bypass_secret=bypass_secret)
                assert_equal(role_users.status, 403, f"{role} app users denied")
                assert_equal(role_users.json().get("code"), "permission_denied", f"{role} app users denied code")

            read_only_opener = role_openers["read_only"]
            denied_users = request(read_only_opener, base_url, "GET", "/api/app_users", bypass_secret=bypass_secret)
            assert_equal(denied_users.status, 403, "read-only app users status")
            assert_equal(denied_users.json().get("code"), "permission_denied", "read-only app users code")
            denied_write = request(
                read_only_opener,
                base_url,
                "POST",
                "/api/create_record",
                {"type": "people", "fields": {"name": "Read-only Smoke Test"}},
                bypass_secret=bypass_secret,
            )
            assert_equal(denied_write.status, 403, "read-only write status")
            assert_equal(denied_write.json().get("code"), "permission_denied", "read-only write code")
            staff_write = request(
                role_openers["staff"],
                base_url,
                "POST",
                "/api/create_record",
                {"type": "people", "fields": {"name": "Staff Smoke Test"}},
                bypass_secret=bypass_secret,
            )
            assert_equal(staff_write.status, 423, "staff write lock status")
            assert_equal(staff_write.json().get("code"), "remote_write_lock_enabled", "staff write lock code")
            admin_export = request(role_openers["admin"], base_url, "GET", "/api/export_package", bypass_secret=bypass_secret)
            assert_equal(admin_export.status, 403, "admin export package lock status")
            assert_equal(admin_export.json().get("code"), "bulk_package_exports_locked", "admin export package lock code")
            staff_export = request(role_openers["staff"], base_url, "GET", "/api/export_package", bypass_secret=bypass_secret)
            assert_equal(staff_export.status, 403, "staff export package denied status")
            assert_equal(staff_export.json().get("code"), "permission_denied", "staff export package denied code")
            migration_write = request(
                role_openers["migration_operator"],
                base_url,
                "POST",
                "/api/create_record",
                {"type": "people", "fields": {"name": "Migration Operator Smoke Test"}},
                bypass_secret=bypass_secret,
            )
            assert_equal(migration_write.status, 403, "migration operator write denied status")
            assert_equal(migration_write.json().get("code"), "permission_denied", "migration operator write denied code")
            migration_backups = request(role_openers["migration_operator"], base_url, "GET", "/api/backups", bypass_secret=bypass_secret)
            assert_equal(migration_backups.status, 200, "migration operator backups status")
            record(rows, "role_matrix_permission_denial", "passed", "role smoke users matched allowed/denied user-management, write, export, and backup expectations")
        except Exception as exc:
            record(rows, "role_matrix_permission_denial", "failed", str(exc))

    if role_smoke_users and "read_only" in role_smoke_users:
        try:
            read_only_data = role_smoke_users["read_only"]
            read_only_opener = login_opener(base_url, read_only_data["email"], read_only_data["password"], bypass_secret)
            rotated_password = f"rotated-read-only-{smoke_stamp}"
            changed = request(
                read_only_opener,
                base_url,
                "POST",
                "/api/auth/change_password",
                {"current_password": read_only_data["password"], "new_password": rotated_password},
                bypass_secret=bypass_secret,
            )
            assert_equal(changed.status, 200, "read-only self password change status")
            assert_equal(changed.json().get("ok"), True, "read-only self password change ok")
            old_login_jar = CookieJar()
            old_login_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(old_login_jar))
            old_login = request(
                old_login_opener,
                base_url,
                "POST",
                "/api/auth/login",
                {"email": read_only_data["email"], "password": read_only_data["password"]},
                bypass_secret=bypass_secret,
            )
            assert_equal(old_login.status, 401, "old read-only password login status")
            login_opener(base_url, read_only_data["email"], rotated_password, bypass_secret)
            read_only_data["password"] = rotated_password
            record(rows, "app_user_self_password_change", "passed", "temporary read-only user rotated own password without owner password change")
        except Exception as exc:
            record(rows, "app_user_self_password_change", "failed", str(exc))

    if role_smoke_users:
        try:
            for role, data in role_smoke_users.items():
                deactivated = request(
                    opener,
                    base_url,
                    "POST",
                    "/api/app_users/deactivate",
                    {"id": data["id"]},
                    bypass_secret=bypass_secret,
                )
                assert_equal(deactivated.status, 200, f"deactivate {role} app user status")
                assert_equal((deactivated.json().get("user") or {}).get("status"), "deactivated", f"{role} deactivated status")
                disabled_jar = CookieJar()
                disabled_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(disabled_jar))
                disabled_login = request(
                    disabled_opener,
                    base_url,
                    "POST",
                    "/api/auth/login",
                    {"email": data["email"], "password": data["password"]},
                    bypass_secret=bypass_secret,
                )
                assert_equal(disabled_login.status, 401, f"{role} deactivated login status")
            record(rows, "app_user_deactivation", "passed", "deactivated smoke users cannot log in")
        except Exception as exc:
            record(rows, "app_user_deactivation", "failed", str(exc))

    try:
        export_package = request(opener, base_url, "GET", "/api/export_package", bypass_secret=bypass_secret)
        assert_equal(export_package.status, 403, "export package status")
        assert_equal(export_package.json().get("code"), "bulk_package_exports_locked", "export package code")
        record(rows, "bulk_export_lock", "passed", "complete package export blocked")
    except Exception as exc:
        record(rows, "bulk_export_lock", "failed", str(exc))

    if expect_document_file_access:
        try:
            candidates: list[tuple[int, str, str]] = [
                (item_id, f"/api/archive_file?id={item_id}", "storage manifest")
                for item_id in storage_manifest_archive_ids()
            ]
            if not candidates:
                page = 1
                total = None
                page_size = 100
                while True:
                    archive = request(
                        opener,
                        base_url,
                        "GET",
                        f"/api/archive?item_type=document&page_size={page_size}&page={page}",
                        bypass_secret=bypass_secret,
                    )
                    assert_equal(archive.status, 200, f"document archive page {page} status")
                    archive_payload = archive.json()
                    items = archive_payload.get("items") or []
                    if total is None:
                        total = int(archive_payload.get("total") or 0)
                    for item in items:
                        if item.get("file_url"):
                            candidates.append((int(item["id"]), str(item["file_url"]), f"archive page {page}"))
                    if candidates or not items or page * page_size >= total:
                        break
                    page += 1
            if not candidates:
                raise AssertionError("No document archive rows with downloadable files were returned.")

            attempts: list[str] = []
            for document_id, file_url, source in candidates[:25]:
                archive_file = request(no_redirect_opener, base_url, "GET", file_url, bypass_secret=bypass_secret)
                if archive_file.status != 302:
                    attempts.append(f"{source} item {document_id} returned {archive_file.status}")
                    continue
                location = archive_file.headers.get("Location", "")
                parsed_location = urllib.parse.urlparse(location)
                if parsed_location.netloc != "ckjbnummsxqcyeahzynz.supabase.co" or "/object/sign/" not in parsed_location.path:
                    raise AssertionError("Archive file redirect did not point to a signed Supabase Storage URL.")
                record(rows, "document_file_signed_access", "passed", f"owner received signed storage redirect for {source} archive item {document_id}")
                break
            else:
                raise AssertionError("No storage-backed document produced a signed redirect: " + "; ".join(attempts[:8]))
        except Exception as exc:
            record(rows, "document_file_signed_access", "failed", str(exc))
    else:
        try:
            archive_file = request(opener, base_url, "GET", "/api/archive_file?id=1", bypass_secret=bypass_secret)
            assert_equal(archive_file.status, 403, "archive file status")
            assert_equal(archive_file.json().get("code"), "document_file_access_locked", "archive file code")
            record(rows, "document_file_lock", "passed", "document file access blocked")
        except Exception as exc:
            record(rows, "document_file_lock", "failed", str(exc))

    try:
        locked_write = request(
            opener,
            base_url,
            "POST",
            "/api/create_record",
            {"type": "people", "fields": {"name": "Smoke Test"}},
            bypass_secret=bypass_secret,
        )
        assert_equal(locked_write.status, 423, "locked write status")
        assert_equal(locked_write.json().get("code"), "remote_write_lock_enabled", "locked write code")
        record(rows, "remote_write_lock", "passed", "create_record blocked before validation unlock")
    except Exception as exc:
        record(rows, "remote_write_lock", "failed", str(exc))

    try:
        logout = request(opener, base_url, "POST", "/api/auth/logout", bypass_secret=bypass_secret)
        assert_equal(logout.status, 200, "logout status")
        after_logout = request(opener, base_url, "GET", "/api/summary", bypass_secret=bypass_secret)
        assert_equal(after_logout.status, 401, "summary after logout")
        record(rows, "logout", "passed", "session cleared and summary denied")
    except Exception as exc:
        record(rows, "logout", "failed", str(exc))

    write_report(base_url, rows)
    failed = [row for row in rows if row["status"] == "failed"]
    print(json.dumps({"url": base_url, "passed": len(rows) - len(failed), "failed": len(failed), "report": str(REPORTS_DIR / "vercel_hosted_app_smoke.md")}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
