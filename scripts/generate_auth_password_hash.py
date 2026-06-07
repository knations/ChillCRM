#!/usr/bin/env python3
"""Generate a CHILLCRM hosted-auth password hash without storing the password."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crm_app.server import password_hash, verify_password


def main() -> int:
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        print("Passwords did not match.", file=sys.stderr)
        return 1
    if len(first) < 12:
        print("Use at least 12 characters for the hosted bootstrap password.", file=sys.stderr)
        return 1
    hashed = password_hash(first)
    if not verify_password(first, hashed):
        print("Hash verification failed.", file=sys.stderr)
        return 1
    print(hashed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
