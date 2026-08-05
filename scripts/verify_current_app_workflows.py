#!/usr/bin/env python3
"""Verify current read-only CHILLCRM workflows without retired migration gates."""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.index import handler


def read_json(url: str) -> tuple[int, dict[str, object]]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}
        return exc.code, payload


def main() -> int:
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
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("CHILLCRM_DATABASE_ADAPTER", None)
    os.environ.pop("CRM_DATABASE_ADAPTER", None)
    os.environ.pop("CHILLCRM_AUTH_REQUIRED", None)
    os.environ.pop("AUTH_REQUIRED", None)

    httpd: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{httpd.server_port}"

        health_status, health = read_json(f"{base_url}/api/health")
        assert health_status == 200
        assert health["ok"] is True
        assert health["service"] == "chillcrm"

        people_status, people = read_json(f"{base_url}/api/list?type=people&page_size=10")
        assert people_status == 200
        assert people["type"] == "people"
        assert int(people["total"]) > 0
        assert len(people["records"]) <= 10
        first_person = people["records"][0]
        person_id = int(first_person["source_id"])

        detail_status, detail = read_json(f"{base_url}/api/detail?type=person&id={person_id}")
        assert detail_status == 200
        assert detail["type"] == "person"
        assert detail["record"]["source_id"] == person_id
        assert isinstance(detail.get("timeline"), list)
        assert isinstance(detail.get("tasks"), list)
        assert isinstance(detail.get("purchases"), list)
        assert isinstance(detail.get("record_files"), list)

        search_q = urllib.parse.quote(str(first_person.get("name") or "")[:4])
        search_status, search = read_json(f"{base_url}/api/search?q={search_q}")
        assert search_status == 200
        assert len(search.get("results") or []) >= 1

        deals_status, deals = read_json(f"{base_url}/api/list?type=deals&page_size=10")
        assert deals_status == 200
        assert deals["type"] == "deals"
        assert "records" in deals

        board_status, board = read_json(f"{base_url}/api/pipeline_board")
        assert board_status == 200
        assert isinstance(board.get("stages"), list)
        assert isinstance(board.get("deals"), list)

        tags_status, tags = read_json(f"{base_url}/api/tags")
        assert tags_status == 200
        assert isinstance(tags.get("tags"), list)

        operations_status, operations = read_json(f"{base_url}/api/operations_status")
        assert operations_status == 200
        assert "snapshot" not in operations
        assert "optional_sweep" not in operations
        assert "counts" in operations
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

    print("CHILLCRM current workflow verifier passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
