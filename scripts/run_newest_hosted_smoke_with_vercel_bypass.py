#!/usr/bin/env python3
"""Run newest hosted smoke by reading a Vercel automation bypass in memory."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERCEL_API = "https://api.vercel.com"
DEFAULT_PROJECT_ID = "prj_BW7lf5NVtOGjZ8eA28pIVOBIACgh"
DEFAULT_TEAM_SLUG = "kevin-nations-projects"
DEFAULT_OWNER_EMAIL = "kevinnations@gmail.com"


def prompt_secret(label: str, env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    return getpass.getpass(f"{label}: ").strip()


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def public_app_auth_domain(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    return host.lower() in {"chillcrm.app", "www.chillcrm.app"}


def read_latest_url() -> str:
    report = PROJECT_ROOT / "reports" / "vercel_staging_deployment_status.md"
    if not report.exists():
        return ""
    for line in report.read_text(encoding="utf-8").splitlines():
        if line.startswith("- URL: `") and line.endswith("`."):
            return line.split("`", 2)[1].strip()
    return ""


def request_json(method: str, path: str, token: str, *, query: dict[str, str], body: Any | None = None) -> dict[str, Any]:
    url = f"{VERCEL_API}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vercel request failed with {exc.code}: {raw[:500]}") from exc


def read_bypass_secret(token: str, project_id: str, team_slug: str, *, generate_if_missing: bool) -> str:
    query = {"slug": team_slug} if team_slug else {}
    project = request_json("GET", f"/v9/projects/{project_id}", token, query=query)
    protection = project.get("protectionBypass") or {}
    if not protection and generate_if_missing:
        generated = request_json("PATCH", f"/v1/projects/{project_id}/protection-bypass", token, query=query, body={})
        protection = generated.get("protectionBypass") or {}
    if not protection:
        raise RuntimeError("No Vercel automation bypass secret is available for this project.")
    return str(next(iter(protection.keys())))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run hosted smoke using an in-memory Vercel protection bypass secret. No secret values are written to reports."
    )
    parser.add_argument("--url", default=os.environ.get("CHILLCRM_VERCEL_URL", "") or read_latest_url())
    parser.add_argument("--project-id", default=os.environ.get("VERCEL_PROJECT_ID", DEFAULT_PROJECT_ID))
    parser.add_argument("--team-slug", default=os.environ.get("VERCEL_TEAM_SLUG", DEFAULT_TEAM_SLUG))
    parser.add_argument("--owner-email", default=os.environ.get("AUTH_BOOTSTRAP_ADMIN_EMAIL", DEFAULT_OWNER_EMAIL))
    parser.add_argument("--generate-bypass-if-missing", action="store_true")
    parser.add_argument("--no-vercel-bypass", action="store_true", help="Use app-level authentication only; do not prompt for a Vercel token or bypass secret.")
    args = parser.parse_args()

    if not args.url:
        raise SystemExit("Missing hosted URL. Pass --url or refresh reports/vercel_staging_deployment_status.md.")

    skip_bypass = bool(args.no_vercel_bypass or public_app_auth_domain(args.url))
    token = "" if skip_bypass else prompt_secret("Vercel token", "VERCEL_TOKEN")
    use_owner_recovery = env_flag("CHILLCRM_USE_OWNER_RECOVERY")
    owner_password = prompt_secret(
        "Owner recovery new password" if use_owner_recovery else "Owner password",
        "CHILLCRM_OWNER_RECOVERY_PASSWORD" if use_owner_recovery else "AUTH_BOOTSTRAP_ADMIN_PASSWORD",
    )
    bypass_secret = ""
    if not skip_bypass:
        bypass_secret = os.environ.get("VERCEL_PROTECTION_BYPASS_SECRET", "").strip() or read_bypass_secret(
            token,
            args.project_id,
            args.team_slug,
            generate_if_missing=args.generate_bypass_if_missing,
        )

    env = os.environ.copy()
    env.update(
        {
            "CHILLCRM_VERCEL_URL": args.url,
            "AUTH_BOOTSTRAP_ADMIN_EMAIL": args.owner_email,
            "AUTH_BOOTSTRAP_ADMIN_PASSWORD": owner_password,
            "VERCEL_PROTECTION_BYPASS_SECRET": bypass_secret,
            "EXPECT_DOCUMENT_FILE_ACCESS": "true",
            "PYTHONPYCACHEPREFIX": env.get("PYTHONPYCACHEPREFIX", "/private/tmp/chillcrm_pycache"),
        }
    )
    if use_owner_recovery:
        env["CHILLCRM_OWNER_RECOVERY_PASSWORD"] = owner_password
    for key in ["VERCEL_TOKEN"]:
        env.pop(key, None)

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_vercel_hosted_app.py")],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=900,
    )
    output = (result.stdout or result.stderr or "").strip()
    print(output)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
