# CHILLCRM Build Boundaries

This document is the quick map for keeping CHILLCRM lean as the project grows.

## Production Runtime

These files are the live app surface:

- `api/index.py`
- `crm_app/server.py`
- `crm_app/static/`
- `requirements.txt`
- `vercel.json`
- `.python-version`
- `.vercelignore`

Treat changes here as production app changes. Verify auth, data access, UI behavior, and hosted health when these files move.

## Configuration And Project Guidance

These files guide the build but are not CRM data:

- `README.md`
- `AGENTS.md`
- `docs/`
- `.gitignore`

Keep these current enough that a new task can understand the app as an operational CRM.

## Operator Tooling

These files support verification, provider setup, evidence reports, and owner-approved operations:

- `scripts/`
- `ops/operator_launchers/`

They are intentionally excluded from Vercel deployment. Use them for controlled checks and maintenance, but do not treat them as daily product UI.

## Private Local Data

These folders are local/private and should not be committed or deployed:

- `crm_database/`
- `staging_database/`
- `backups/`
- `raw_api_exports/`
- `exports/`
- `logs/`
- `reports/`
- `profile_images/`
- `record_files/`
- `ops/local_private_launchers/`
- `.env*`
- `.vercel/`
- `.venv/`

## Cleanup Rule

When adding a new file, place it by purpose:

- production behavior goes in `crm_app/` or `api/`
- reusable verification goes in `scripts/`
- Mac click-to-run operator helpers go in `ops/operator_launchers/`
- private machine-only helpers go in `ops/local_private_launchers/`
- product/build doctrine goes in `docs/`

This keeps the CRM itself clean while preserving the operator and verification tools that still matter.
