#!/usr/bin/env python3
"""Verify the current CHILLCRM operational app surface."""

from __future__ import annotations

import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.index import handler
from crm_app import database
from crm_app import runtime_health

LEGACY_PROVIDER = "Zen" + "desk"
LEGACY_STATUS = "Migration" + " Status"
LEGACY_STATUS_API = "/api/" + "migration" + "_status"


def read_url(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    app_js = (PROJECT_ROOT / "crm_app" / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (PROJECT_ROOT / "crm_app" / "static" / "index.html").read_text(encoding="utf-8")
    server_py = (PROJECT_ROOT / "crm_app" / "server.py").read_text(encoding="utf-8")
    database_py = (PROJECT_ROOT / "crm_app" / "database.py").read_text(encoding="utf-8")
    runtime_health_py = (PROJECT_ROOT / "crm_app" / "runtime_health.py").read_text(encoding="utf-8")

    assert "ChillCRM" in index_html
    assert "Have Fun Get Rich" in index_html
    assert "operationsStatusView" in index_html
    assert "/api/operations_status" in app_js
    assert LEGACY_STATUS_API not in app_js
    assert LEGACY_STATUS not in app_js
    assert f"{LEGACY_PROVIDER} Snapshot" not in app_js
    assert f"Final {LEGACY_PROVIDER}" not in app_js
    assert "Complete CRM Package" in app_js
    assert "Document Files" in app_js
    assert "def operations_status" in server_py
    assert 'elif path == "/api/operations_status"' in server_py
    assert "from crm_app import runtime_health" in server_py
    assert "from crm_app.database import" in server_py
    assert "class PostgresCompatConnection" in database_py
    assert "def runtime_context" in runtime_health_py
    assert database.postgres_parameters_for_sql("SELECT * FROM people WHERE email LIKE :email", {"email": "%@%"}) == ["%@%"]
    assert runtime_health.remote_write_lock_status(False, set())["mode"] == "unlocked"
    assert runtime_health.bulk_package_export_status(True)["mode"] == "enabled"

    env_backup = {
        key: os.environ.get(key)
        for key in [
            "DATABASE_URL",
            "CHILLCRM_DATABASE_ADAPTER",
            "CRM_DATABASE_ADAPTER",
            "CHILLCRM_AUTH_REQUIRED",
            "AUTH_REQUIRED",
        ]
    }
    for key in env_backup:
        os.environ.pop(key, None)

    httpd: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{httpd.server_port}"

        health_status, health_body = read_url(f"{base_url}/api/health")
        assert health_status == 200
        assert '"ok": true' in health_body
        assert '"service": "chillcrm"' in health_body

        index_status, index_body = read_url(f"{base_url}/")
        assert index_status == 200
        assert "ChillCRM" in index_body

        static_status, static_body = read_url(f"{base_url}/static/app.js")
        assert static_status == 200
        assert "/api/operations_status" in static_body
        assert LEGACY_STATUS_API not in static_body

        operations_status, operations_body = read_url(f"{base_url}/api/operations_status")
        assert operations_status in {200, 401}
        assert f"{LEGACY_PROVIDER} Snapshot" not in operations_body
        assert f"Final {LEGACY_PROVIDER}" not in operations_body
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        if thread:
            thread.join(timeout=5)
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print("CHILLCRM operational verifier passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
