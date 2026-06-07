"""Vercel Python Function adapter for CHILLCRM.

Vercel invokes a BaseHTTPRequestHandler subclass named `handler`. The CRM
application already uses that interface locally, so the adapter keeps the
hosted entrypoint thin and lets the existing route code stay authoritative.
"""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crm_app.server import CRMRequestHandler, DEFAULT_DB


class handler(CRMRequestHandler, BaseHTTPRequestHandler):
    db_path = DEFAULT_DB
