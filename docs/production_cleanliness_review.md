# CHILLCRM Production Cleanliness Review

Last reviewed: 2026-08-05

## Current Posture

CHILLCRM is a lean internal CRM runtime: a Python serverless app, static HTML/CSS/JavaScript, Supabase Postgres/storage, and Vercel hosting. The production deploy is intentionally small and excludes local databases, backups, raw exports, generated reports, scripts, virtual environments, and command helpers.

The live health endpoint at `https://chillcrm.app/api/health` is green after the latest hardening passes.

## What Is Clean

- Runtime dependencies are minimal: `certifi`, `cryptography`, and `pg8000`.
- Local CRM data, backups, exports, reports, profile images, record files, `.env` files, `.vercel`, and Python cache files are ignored by Git and excluded from Vercel deploys.
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

- `scripts/verify_app_operations.py` runs through the changed code paths and then stops at the existing final production readiness assertion after `CHILLCRM server error: RuntimeError on GET /api/summary`. Treat this as the standing private/provider readiness evidence gate until fresh owner/provider smoke evidence is supplied. Do not interpret it as a regression from the latest hardening commits unless an earlier assertion fails.

## Recommended Boundaries

- Keep CHILLCRM focused on internal CRM productivity: people, deals, tasks, notes, purchases, files, tags, portal previews, and owner brief surfaces.
- Avoid adding heavy build tooling unless the frontend needs true modular compilation. The current deploy is simple and small.
- Prefer small hardening commits with verifier coverage over broad rewrites.
- Do not move local backup/export/report artifacts into Git or Vercel.
- Do not run production write tests without explicit owner approval.
