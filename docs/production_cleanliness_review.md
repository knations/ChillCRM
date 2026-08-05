# CHILLCRM Production Cleanliness Review

Last reviewed: 2026-08-05

## Current Posture

CHILLCRM is a lean internal CRM runtime: a Python serverless app, static HTML/CSS/JavaScript, Supabase Postgres/storage, and Vercel hosting. The production deploy is intentionally small and excludes local databases, backups, raw exports, generated reports, scripts, virtual environments, and command helpers.

The live health endpoint at `https://chillcrm.app/api/health` is green after the latest hardening passes.

## What Is Clean

- Runtime dependencies are minimal: `certifi`, `cryptography`, and `pg8000`.
- CRM data, backups, exports, reports, profile images, record files, `.env` files, `.vercel`, and Python cache files are ignored by Git and excluded from Vercel deploys.
- Production serves HTML with `Cache-Control: no-store` so app shell updates are immediate.
- Versioned static CSS/JS paths use short-lived private caching with ETags.
- Security headers are present on live responses: CSP without inline script/style allowances, frame blocking, noindex, nosniff, referrer policy, permissions policy, and HSTS via Vercel.
- The frontend uses `escapeHtml` and `safeHref` for rendered CRM values and links.
- Stored login email is device-local only and does not store passwords or tokens.

## Recent Hardening

- Missing private Vercel/token prompt runs now write separate input-required reports instead of overwriting main proof reports.
- Operator/private prompt scripts now handle missing terminal input cleanly.
- Auth parsing and passkey signature fallback error handling were narrowed.
- Postgres SQL translation now casts `source_json` before `ILIKE` matching to avoid `jsonb ~~*` runtime errors.
- Upload base64 decode handling now catches only decode/type errors and has negative verifier coverage.
- Dashboard progress displays now use native `<progress>` elements, allowing CSP to remove `'unsafe-inline'` from `style-src`.
- Remaining-gate execution coverage now maps current Vercel diagnostics/environment blockers to the redeploy/status-refresh input, and verifier assertions recognize explicit blocked Supabase parity evidence without marking it green.
- Vercel deployment diagnostics now narrow optional event/file fetch failures to expected Vercel API, network timeout, and JSON decode errors instead of silently swallowing every exception.
- Permission-denial audit failures now leave a server-side warning instead of disappearing silently, while the browser still receives the same non-sensitive permission-denied response.
- Hosted deployment package verification now uses explicit expected parse/import/local-smoke exception classes and creates its ignored report directory on fresh clones before writing evidence.
- File serving now avoids loading uncached file payloads for `HEAD` responses, preserving headers while reducing unnecessary runtime work for static/private file probes.
- Signed-file redirects now allow app-relative paths and configured Supabase storage hosts only, rejecting arbitrary external HTTPS destinations and credential-bearing URLs.
- Signed-file redirects now explicitly declare zero-length response bodies while keeping redirects cache-locked.
- Response formatting, security headers, CSV serialization, safe download filenames, static cache rules, and file freshness checks now live in `crm_app/responses.py` with backend boundary verifier coverage.
- Retired remote-hosting and managed-provider decision exports were removed from the active app server so current exports stay focused on operational CRM use.
- Retired remote-admin planning exports are hidden from the current export manifest, with verifier coverage preventing them from returning to the normal app export list.
- Static route/action permission maps now live in `crm_app/access_control.py`, keeping auth policy visible without burying it inside the main request handler.
- Mac operator launchers now anchor themselves to the CHILLCRM project root before running scripts, preventing private-token flows from looking for `scripts/` inside `ops/operator_launchers/`.

## Parked Cleanup

- Some historical setup, staging, and cutover export routes remain callable in `crm_app/server.py` for rollback/reference safety. They are no longer advertised in the normal export manifest. Remove the underlying routes/functions only in a dedicated retirement pass with explicit approval, because that is a broad behavior deletion rather than a cosmetic cleanup.

## Verification Run

Green checks from the latest passes:

- Python compile checks for changed runtime/verifier files.
- Git whitespace checks.
- `scripts/verify_secret_handling_boundaries.py`
- `scripts/verify_hosted_app_deployment_package.py`
- `scripts/verify_hosted_postgres_adapter_smoke.py --dry-run`
- Live `https://chillcrm.app/api/health`
- GitHub `main` confirmed at the latest pushed commit after each pass.

Known non-code evidence gate:

- `scripts/verify_app_operations.py` runs through refreshed readiness-report assertions and can stop at private/provider evidence gates after `CHILLCRM server error: RuntimeError on GET /api/summary`. Treat earlier assertion failures as regressions; treat final private/provider gates as evidence refresh work.

## Recommended Boundaries

- Keep CHILLCRM focused on internal CRM productivity: people, deals, tasks, notes, purchases, files, tags, portal previews, and owner brief surfaces.
- Avoid adding heavy build tooling unless the frontend needs true modular compilation. The current deploy is simple and small.
- Prefer small hardening commits with verifier coverage over broad rewrites.
- Do not move local backup/export/report artifacts into Git or Vercel.
- Do not run production write tests without explicit owner approval.
