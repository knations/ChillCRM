# CHILLCRM Operations Tools

This folder separates operator and migration-era tooling from the production CRM runtime.

## Folders

- `operator_launchers/` contains tracked Mac launchers for owner-approved hosted smoke checks, Vercel checks, Supabase checks, and historical migration/cutover operations.
- `local_private_launchers/` is ignored by Git. It is for local credential or provider helper launchers that should stay on this machine only.

## Boundary

The production app does not need this folder at runtime. Vercel excludes `ops/`, `scripts/`, local data folders, reports, and `.command` files from deployment.

Keep `Start Local CRM.command` at the project root because it is the daily local app starter.
