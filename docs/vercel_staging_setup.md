# CHILLCRM Vercel Staging Setup

This documents Vercel as the locked staging app host for the Supabase-backed CRM. The app is deployed for smoke testing with private Supabase document access enabled for authorized owner/admin sessions, but it does not invite admins, unlock writes, expose local data, or make Supabase the source of truth.

## Current Status

- Vercel project: `chillcrm`.
- Latest deployed URL: `https://chillcrm-jtu1u0kje-kevin-nations-projects.vercel.app` with existing Vercel environment variables preserved and the non-secret owner recovery switch enabled for staging.
- Latest smoke-tested URL: `https://chillcrm-jtu1u0kje-kevin-nations-projects.vercel.app`.
- Deployment protection: Vercel Authentication is enabled; automation smoke uses Vercel Protection Bypass for Automation without writing the bypass secret to reports.
- CRM app auth: `CHILLCRM_AUTH_REQUIRED=true`, with bootstrap owner/admin login verified.
- Staging locks: `REMOTE_WRITE_LOCK=true` and `EXPORT_PACKAGE_ENABLED=false` were verified.
- Private document access: `DOCUMENT_FILE_ACCESS_ENABLED=true` is enabled in Vercel staging after private Supabase Storage upload validation; owner/admin document requests now redirect to short-lived Supabase signed URLs.
- Smoke report: `reports/vercel_hosted_app_smoke.md` passed 15 checks with 0 failures, including controlled owner recovery, owner-only app-user lifecycle, multi-role denial probes, temporary-user password rotation, migration-operator hosted backup status, signed document access, and remote write/export locks.
- Private-company auth posture: no public signup; owner/admin access is managed internally, and the hosted owner recovery button appears only while the private recovery switch is enabled.
- Owner recovery: `scripts/reset_app_user_password.py` remains available as a private operator path, and the hosted login page now has an audited owner-only recovery flow controlled by `CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED`.
- Owner UI, actor-aware CRM-write audit wiring, and the synced report/docs bundle are built and deployed to the current staging bundle; full hosted login/role smoke against the newest URL passed through Vercel Protection Bypass for Automation without writing the bypass secret to reports. Local hosted runtime files have changed since that deployment, so `reports/hosted_deployment_freshness.md` remains blocked until the current local runtime is redeployed and smoke-tested again.

## What Is Prepared

- `api/index.py` exposes the existing CRM request handler as a Vercel Python Function.
- `vercel.json` uses an explicit `@vercel/python` build and routes all paths through that function so `/`, `/static/*`, `/api/*`, and `/reports/*` keep using the existing CRM routes.
- `requirements.txt` pins the hosted runtime dependencies used by the Supabase/Postgres adapter.
- `.vercelignore` and the deployment helper keep local-only exports, backups, raw Zendesk snapshots, and SQLite databases out of the hosted bundle.
- `config/chillcrm_vercel.env.example` lists the staging variables to enter in Vercel Project Settings; real values belong only in Vercel/Supabase secret managers.
- `scripts/reset_app_user_password.py` provides private owner/admin password recovery for this internal CRM without exposing a public reset endpoint.

## Why This Shape

Vercel's Python runtime runs Python files as Functions and supports `BaseHTTPRequestHandler` entrypoints under `api/`. The current CRM already uses `BaseHTTPRequestHandler`, so the adapter can stay thin. Vercel Functions have a read-only deployed filesystem with `/tmp` scratch space, so hosted staging must use Supabase Postgres and Supabase Storage instead of local SQLite or local document files.

Official references:

- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/functions/runtimes
- https://vercel.com/docs/project-configuration/vercel-json

## Staging Environment Variables

Use `config/chillcrm_vercel.env.example` as the checklist. Real values belong only in Vercel Project Settings.

Required before hosted smoke:

- `DATABASE_URL`
- `CHILLCRM_DATABASE_ADAPTER=postgres`
- `CHILLCRM_POSTGRES_STATEMENT_TIMEOUT_MS=8000`
- `CRM_ENV=staging`
- `CHILLCRM_AUTH_REQUIRED=true`
- `SESSION_SECRET`
- `SESSION_COOKIE_SECURE=true`
- `AUTH_BOOTSTRAP_ADMIN_EMAIL`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD_HASH`
- `REMOTE_WRITE_LOCK=true`
- `EXPORT_PACKAGE_ENABLED=false`
- `DOCUMENT_FILE_ACCESS_ENABLED=true` after private storage upload validation
- `CHILLCRM_SUPABASE_URL`
- `CHILLCRM_SUPABASE_STORAGE_BUCKET=chillcrm-documents`
- `CHILLCRM_STORAGE_SIGNED_URL_TTL_SECONDS=300`
- `CHILLCRM_SUPABASE_SERVICE_ROLE_KEY`

## Remaining Gates

- Keep the 203 recovered document files in private Supabase Storage and rerun storage validation after any manifest change.
- Keep `crm.remote_file_objects` validation current; current coverage is 203/203 document files with matching bytes.
- Repeat hosted smoke after any schema, adapter, deployment-package, or provider-environment change.
- Keep the latest owner UI deployment smoke-gated before owner shakedown signoff or optional internal-user access; rerun full hosted login/role smoke after any schema, adapter, deployment, auth, or provider-environment change.
- Hosted multi-role denial/login smoke for app users passed on the latest deployment; rerun it before optional internal-user access if anything material changes.
- Complete hosted actor-aware CRM-write audit and Supabase provider backup/restore validation before any write unlock or owner shakedown signoff; the local disposable restore drill has passed, and `reports/supabase_backup_readiness.md` is waiting on a Supabase Management API token with backup-read permission.
- Keep `REMOTE_WRITE_LOCK=true` and `EXPORT_PACKAGE_ENABLED=false` until the validation matrix passes; signed document access may stay enabled only while auth, role, and storage smoke remain green.
- Add any optional internal user only after hosted smoke, storage privacy, auth, backup/restore, audit, and owner-shakedown gates are green.
- Use `reports/remote_production_readiness.md` as the single current production gate summary before considering any source-of-truth switch.
