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
    app_js = (PROJECT_ROOT / "crm_app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "portal-readiness-pill" not in app_js
    assert "Needed ·" not in app_js
    assert "<h3>History</h3>" in app_js
    assert "showCallLogFormButton" in app_js
    assert 'id="callLogForm" class="call-log-form" hidden' in app_js
    assert "<h3>Conversation</h3>" not in app_js
    assert "Calls and internal notes for this person." not in app_js
    assert "function linkifyText" in app_js
    assert "call-log-note-text" in app_js
    assert 'target="_blank" rel="noopener noreferrer"' in app_js
    index_html = (PROJECT_ROOT / "crm_app" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'data-view="calendar"' not in index_html
    assert 'id="calendarView"' not in index_html
    assert 'id="dashboardFocusView"' in index_html
    assert 'id="environmentBadge"' not in index_html
    assert 'id="statusText" class="status-text" hidden' in index_html
    assert "actionCalendarPanel" in app_js
    assert "wireActionCalendarControls(els.dashboard, renderDashboard)" in app_js
    assert "renderDashboardFocus" in app_js
    assert "dashboard-focus-back" in app_js
    assert "/api/calendar_events" in app_js
    assert "local_today" in app_js
    assert "/api/complete_scheduled_call" in app_js
    assert "auth-change-password" not in app_js
    assert "function followupTaskCard" in app_js
    assert "followup-task-list" in app_js

    timeline_probe = handler.__new__(handler)
    timeline = timeline_probe.person_timeline(
        {"id": 7, "name": "Timeline Probe", "created_at": "2026-08-05T10:00:00+00:00"},
        purchases=[],
        call_logs=[
            {
                "source_id": 44,
                "summary": "Call at 11:30",
                "notes": "Reviewed next move: https://example.com/recording",
                "occurred_at": "2026-08-05T11:30:00+00:00",
                "direction_label": "General",
                "recording_url": "",
                "scheduled": True,
            },
            {
                "source_id": 45,
                "summary": "Completed call",
                "notes": "Completed notes",
                "occurred_at": "2026-08-05T10:30:00+00:00",
                "direction_label": "General",
                "recording_url": "",
                "scheduled": False,
            }
        ],
        notes=[],
        tasks=[],
        activity=[
            {
                "activity_type": "audit",
                "action": "add_call_log",
                "record_type": "person",
                "record_id": 7,
                "summary": "Added call log",
                "occurred_at": "2026-08-05T11:31:00+00:00",
            },
            {
                "activity_type": "audit",
                "action": "update_record",
                "record_type": "person",
                "record_id": 7,
                "summary": "Updated person",
                "occurred_at": "2026-08-05T11:32:00+00:00",
            }
        ],
        tags=["Owner Facing Tag"],
        linked_resources=[
            {
                "source_type": "note",
                "source_label": "Note #44",
                "kind": "Profile/Web Link",
                "url": "https://example.com/recording",
                "context": "Reviewed next move: https://example.com/recording",
                "created_at": "2026-08-05T11:30:00+00:00",
            }
        ],
        record_files=[],
        archive_items=[],
        deals=[],
    )
    call_events = [event for event in timeline if event.get("event_type") == "call"]
    assert len(call_events) == 1
    assert call_events[0]["title"] == "Completed call"
    assert not [event for event in timeline if event.get("event_type") == "link"]
    assert not [event for event in timeline if event.get("event_type") == "audit"]
    assert not [event for event in timeline if event.get("event_type") == "tags"]

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

        calendar_status, calendar = read_json(f"{base_url}/api/calendar_events?local_today=2026-08-05")
        assert calendar_status == 200
        assert "overdue" in calendar
        assert "day" in calendar
        assert "selected_date" in calendar
        assert calendar["today"] == "2026-08-05"
        assert calendar["today_source"] == "browser_local_date"
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
