"""Small server-only Resend transport; never logs provider bodies or credentials."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request


class ProviderError(RuntimeError):
    def __init__(self, status: int = 0):
        self.status = status
        super().__init__(f"Email provider request failed ({status or 'network'}).")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward bearer credentials to a redirected destination.
        return None


class ResendClient:
    def __init__(self):
        self.last_request = 0.0

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if not path.startswith('/') or path.startswith('//') or '?' in path:
            raise ValueError('Invalid email provider path.')
        key = os.environ.get('RESEND_API_KEY', '').strip()
        if not key:
            raise ValueError('Resend API key is not configured.')
        time.sleep(max(0, .55 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        req = urllib.request.Request('https://api.resend.com' + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                     'User-Agent': 'ChillCRM/1.0'}, method=method)
        # No automatic retries: event and broadcast POSTs have no documented
        # idempotency contract. An ambiguous result requires reconciliation.
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
                result = json.load(response)
                if not isinstance(result, dict):
                    raise ProviderError()
                return result
        except urllib.error.HTTPError as exc:
            raise ProviderError(exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ProviderError() from None


def verify_webhook(raw: bytes, headers, secret: str, now: int | None = None) -> dict:
    """Verify the Standard Webhooks/Svix signature over the exact received bytes."""
    try:
        event_id = headers.get('svix-id', '')
        timestamp = headers.get('svix-timestamp', '')
        if not event_id or abs((now if now is not None else int(time.time())) - int(timestamp)) > 300:
            raise ValueError()
        key = base64.b64decode(secret.removeprefix('whsec_'), validate=True)
        if not key:
            raise ValueError()
        signed = event_id.encode() + b'.' + timestamp.encode() + b'.' + raw
        expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        signatures = [part.split(',', 1) for part in headers.get('svix-signature', '').split()]
        if not any(version == 'v1' and hmac.compare_digest(signature, expected)
                   for version, signature in signatures if version and signature):
            raise ValueError()
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), dict):
            raise ValueError()
        payload['_verified_id'] = event_id
        return payload
    except (ValueError, TypeError, UnicodeError):
        raise ValueError('Invalid email webhook signature or payload.') from None
