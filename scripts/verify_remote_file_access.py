#!/usr/bin/env python3
"""Verify hosted remote document-file access helpers without real secrets."""

from __future__ import annotations

import csv
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import crm_app.server as server


REPORTS_DIR = PROJECT_ROOT / "reports"


class FakeStorageHandler(BaseHTTPRequestHandler):
    seen: dict[str, Any] = {}

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        FakeStorageHandler.seen = {
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
            "apikey": self.headers.get("apikey"),
            "body": json.loads(body or "{}"),
        }
        payload = json.dumps({"signedURL": "/storage/v1/object/sign/chillcrm-documents/fake.pdf?token=test"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def app() -> server.CRMRequestHandler:
    instance = server.CRMRequestHandler.__new__(server.CRMRequestHandler)
    instance.db_path = server.DEFAULT_DB
    return instance


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "status", "evidence"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    passed = sum(1 for row in rows if row["status"] == "pass")
    failed = sum(1 for row in rows if row["status"] != "pass")
    lines = [
        "# Remote File Access Verification",
        "",
        "This verifies hosted document-file signing helpers without using real Supabase secrets, uploading files, exposing local files, or changing CRM records.",
        "",
        "## Summary",
        "",
        f"- Passed: {passed}.",
        f"- Failed: {failed}.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['key']} | {row['status']} | {str(row['evidence']).replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The real hosted download path still requires private Supabase Storage upload, `crm.remote_file_objects` rows, hosted auth, and a server-side service-role key in the deployment environment.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows: list[dict[str, Any]] = []
    env_keys = [
        "CHILLCRM_SUPABASE_URL",
        "CHILLCRM_SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS",
    ]
    backup = {key: os.environ.get(key) for key in env_keys}
    try:
        test_app = app()
        os.environ.pop("CHILLCRM_SUPABASE_URL", None)
        os.environ.pop("CHILLCRM_SUPABASE_SERVICE_ROLE_KEY", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        try:
            test_app.signed_storage_url("bucket", "path/file.pdf")
            rows.append({"key": "missing_config", "status": "fail", "evidence": "signed without required config"})
        except RuntimeError as exc:
            rows.append({"key": "missing_config", "status": "pass", "evidence": str(exc).split(".")[0]})

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeStorageHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            os.environ["CHILLCRM_SUPABASE_URL"] = f"http://127.0.0.1:{httpd.server_port}"
            os.environ["CHILLCRM_SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"
            os.environ["CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS"] = "90"
            signed = test_app.signed_storage_url("chillcrm-documents", "folder/test file.pdf")
            rows.append(
                {
                    "key": "signed_url",
                    "status": "pass" if signed.startswith(os.environ["CHILLCRM_SUPABASE_URL"]) and "token=test" in signed else "fail",
                    "evidence": signed,
                }
            )
            seen = FakeStorageHandler.seen
            path_ok = seen.get("path") == "/storage/v1/object/sign/chillcrm-documents/folder/test%20file.pdf"
            auth_ok = seen.get("authorization") == "Bearer test-service-key" and seen.get("apikey") == "test-service-key"
            ttl_ok = (seen.get("body") or {}).get("expiresIn") == 90
            rows.append(
                {
                    "key": "signing_request",
                    "status": "pass" if path_ok and auth_ok and ttl_ok else "fail",
                    "evidence": f"path_ok={path_ok}, auth_ok={auth_ok}, ttl_ok={ttl_ok}",
                }
            )
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)
    finally:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    md_path = REPORTS_DIR / "remote_file_access_verification.md"
    csv_path = REPORTS_DIR / "remote_file_access_verification.csv"
    write_report(md_path, rows)
    write_csv(csv_path, rows)
    failed = [row for row in rows if row["status"] != "pass"]
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if failed:
        print(f"Remote file access verification failed: {len(failed)} checks.", file=sys.stderr)
        return 1
    print("Remote file access verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
