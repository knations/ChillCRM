#!/usr/bin/env python3
"""Reset a CHILLCRM app-user password through a private operator path."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


DEFAULT_DB_PATH = PROJECT_ROOT / "crm_database" / "local_crm.sqlite"
DEFAULT_SSL_ROOT_CERT = PROJECT_ROOT / "config" / "supabase-prod-ca-2021.crt"


def prompt_password() -> str:
    env_password = os.environ.get("CHILLCRM_APP_USER_PASSWORD", "").strip()
    if env_password:
        if len(env_password) < 12:
            raise ValueError("Use at least 12 characters.")
        return env_password
    first = getpass.getpass("New password: ")
    second = getpass.getpass("Confirm new password: ")
    if first != second:
        raise ValueError("Passwords did not match.")
    if len(first) < 12:
        raise ValueError("Use at least 12 characters.")
    return first


def make_handler(db_path: Path, database_url: str, ssl_root_cert: str) -> server.CRMRequestHandler:
    if database_url:
        os.environ["DATABASE_URL"] = database_url
        os.environ["CHILLCRM_DATABASE_ADAPTER"] = "postgres"
        if ssl_root_cert:
            os.environ["CHILLCRM_SSLROOTCERT"] = ssl_root_cert
    else:
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
        server.ensure_runtime_schema(db_path)
    handler = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    handler.db_path = db_path
    return handler


def row_to_dict(row: Any) -> dict[str, Any] | None:
    return server.row_to_dict(row)


def ensure_user_and_roles(
    handler: server.CRMRequestHandler,
    email: str,
    display_name: str,
    new_password: str,
    roles: list[str],
) -> dict[str, Any]:
    password_digest = server.password_hash(new_password)
    with handler.db() as conn:
        handler.seed_auth_roles(conn)
        existing = handler.load_app_user_by_email(conn, email)
        old_public = handler.public_app_user(existing)
        if existing:
            user_id = int(existing["id"])
            conn.execute(
                """
                UPDATE app_users
                SET display_name = ?, password_hash = ?, password_updated_at = CURRENT_TIMESTAMP,
                    status = 'active', deactivated_at = NULL
                WHERE id = ?
                """,
                (display_name or existing.get("display_name") or email, password_digest, user_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO app_users (email, display_name, password_hash, password_updated_at, status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'active')
                """,
                (email, display_name or email, password_digest),
            )
            user_id = int(conn.execute("SELECT id FROM app_users WHERE lower(email) = lower(?)", (email,)).fetchone()["id"])

        clean_roles = handler.clean_app_role_keys(conn, roles, default=["owner", "admin"])
        handler.sync_app_user_roles(conn, user_id, clean_roles, {"id": user_id, "email": email, "roles": clean_roles})
        updated = handler.load_app_user(conn, user_id)
        handler.insert_audit_log(
            conn,
            action="app_user_password_recovery",
            record_type="app_user",
            record_id=user_id,
            field_name="password_hash",
            old_value={"user": old_public, "password_configured": bool(existing and existing.get("password_hash"))},
            new_value={"user": handler.public_app_user(updated), "password_configured": True},
            note="Private operator password recovery completed.",
            actor_user={"id": user_id, "email": email, "roles": updated.get("roles") if updated else clean_roles},
            permission_action="manage_users_roles",
        )
        conn.commit()
        return handler.public_app_user(updated) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Privately reset a CHILLCRM app-user password.")
    parser.add_argument("--email", required=True, help="App-user email to reset.")
    parser.add_argument("--display-name", default="", help="Display name to keep or set.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="Local SQLite database path.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""), help="Hosted Postgres DATABASE_URL.")
    parser.add_argument("--ssl-root-cert", default=str(DEFAULT_SSL_ROOT_CERT), help="Hosted Postgres root CA path.")
    parser.add_argument("--hosted", action="store_true", help="Require hosted Postgres mode instead of local SQLite fallback.")
    parser.add_argument("--generate", action="store_true", help="Generate and print a one-time temporary password.")
    parser.add_argument("--owner", action="store_true", help="Ensure owner/admin roles after reset.")
    parser.add_argument("--admin", action="store_true", help="Ensure admin role after reset.")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if "@" not in email:
        raise SystemExit("A valid email is required.")
    if args.generate:
        new_password = secrets.token_urlsafe(18)
    else:
        try:
            new_password = prompt_password()
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    roles = ["owner", "admin"] if args.owner else ["admin"] if args.admin else ["owner", "admin"]
    database_url = args.database_url.strip()
    if args.hosted and not database_url:
        raise SystemExit("Hosted reset requires --database-url or DATABASE_URL.")
    handler = make_handler(Path(args.db_path), database_url, args.ssl_root_cert.strip())
    user = ensure_user_and_roles(handler, email, args.display_name.strip(), new_password, roles)

    print(f"Password reset for {user.get('email') or email}.")
    print(f"Roles: {', '.join(user.get('roles') or [])}.")
    if args.generate:
        print(f"Temporary password: {new_password}")
    else:
        print("Password was set from secure prompt input.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
