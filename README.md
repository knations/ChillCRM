# CHILLCRM

CHILLCRM is the private operational CRM for `https://chillcrm.app`.

It is treated as the production sales and client command center.

## What It Does

- Manage People, Companies, Leads, Deals, Pipeline, Tags, Custom Fields, Linked Resources, Archive, Follow Up, Activity, Exports, Users, and Cleanup.
- Track notes, tasks, calls, purchases, files, addresses, tags, ownership, lifecycle state, deal stages, deal value, next action, and follow-up dates.
- Support owner-only portal preview foundations through ChillPortal.
- Accept approved inbound purchase webhooks.
- Protect production with login, role checks, audit logging, private file access, secure headers, and provider-managed hosting.

## Production Runtime

- App: `https://chillcrm.app`
- Host: Vercel
- Database/files: Supabase Postgres and private Supabase Storage
- Server entrypoint: `api/index.py`
- Main app server: `crm_app/server.py`
- Frontend: `crm_app/static/`

## Local Development

Double-click:

```text
Start CHILLCRM.command
```

Or run:

```sh
cd /path/to/CHILLCRM
python3 crm_app/server.py --host 127.0.0.1 --port 8765 --auto-port --open
```

## Project Layout

- `api/` - Vercel Python entrypoint.
- `crm_app/` - production CRM server and static frontend.
- `docs/` - current product, build, access, and operating documentation.
- `scripts/` - verification and controlled operator utilities.
- `ops/` - Mac click-to-run operator launchers and local-private helpers.
- `config/` - non-secret configuration examples and certificates.

Private local data folders such as `crm_database/`, `reports/`, `record_files/`, `backups/`, `exports/`, `.env*`, `.vercel/`, and `.venv/` are ignored and excluded from deployment.

See [`docs/build_boundaries.md`](docs/build_boundaries.md) for the clean source/tooling/data boundary.

## Verification

Core checks:

```sh
python3 -m py_compile crm_app/server.py api/index.py
python3 scripts/verify_hosted_app_deployment_package.py
python3 scripts/verify_secret_handling_boundaries.py
python3 scripts/verify_operational_crm.py
```

The operational verifier checks the current product surface. The older broad operations verifier remains available for deep legacy/provider evidence checks when needed.

## Deployment Notes

- GitHub `main` deploys through Vercel.
- `.vercelignore` excludes local data, generated reports, scripts, ops launchers, and command helpers from the hosted runtime.
- Production write behavior is controlled by hosted environment settings and app auth, not by local files.
- Do not commit secrets, databases, exports, downloaded files, generated reports, or provider tokens.
