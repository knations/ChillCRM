# Project Agent Rules

Use this file as the reusable `AGENTS.md` template for ChillCRM and related ChillCRM services.

## Project Overview

Project name: ChillCRM

Purpose: Build and maintain a sales, CRM, and client-pipeline command center for tracking leads, contacts, companies, deals, follow-ups, proposals, client handoffs, and operational health. The product should make it obvious who owns each relationship, what happened last, what happens next, and where revenue or client risk needs attention.

Primary users: Kevin, authorized sales operators, client-success users, admins, and any approved internal collaborators who manage leads, pipeline, accounts, or client onboarding.

Production environment: `https://chillcrm.app`, served from the GitHub repository `knations/ChillCRM` and deployed through Vercel. Known related service: Cloudflare Worker `chillcrm-ops-pulse`, which monitors `https://chillcrm.app/api/health`, stores snapshots in Cloudflare D1, and serves a private operations dashboard.

Key technologies: Python, Vercel Python serverless entrypoint `api/index.py`, the CRM server in `crm_app/server.py`, backend support modules in `crm_app/auth_tokens.py`, `crm_app/database.py`, `crm_app/exporting.py`, `crm_app/file_assets.py`, `crm_app/request_io.py`, and `crm_app/runtime_health.py`, vanilla HTML/CSS/JavaScript in `crm_app/static/`, hosted Supabase/Postgres production data access, private Supabase Storage, pg8000, project verification scripts, GitHub, Vercel, and related Cloudflare monitoring services. Agents must inspect the active repository before assuming any runtime details.

## Agent Operating Style

Agents working in this project should:

- inspect before editing
- prefer existing project patterns
- keep changes focused
- preserve user work
- verify before reporting completion
- communicate in plain language
- ask before risky actions

## Files And Folders

Treat these as source code:

- `api/`
- `crm_app/`
- `crm_app/static/`
- `tests/`
- `scripts/` when the task is verification, reporting, deployment support, or data tooling
- `ops/operator_launchers/` only when the task is owner-approved provider or operator launcher maintenance

Treat these as configuration:

- `requirements.txt`
- `vercel.json`
- `.vercelignore`
- `.python-version`
- `.gitignore`
- `wrangler.*` for related Cloudflare services
- `.env.example`
- deployment manifests
- `docs/build_boundaries.md`

Treat these as read-only unless explicitly instructed:

- generated files
- lockfiles during unrelated tasks
- synced reference materials
- vendor folders
- production exports

Project-specific read-only paths:

- `.env`
- `.env.*`
- `.vercel/`
- `.venv/`
- `crm_database/`
- `staging_database/`
- `backups/`
- `raw_api_exports/`
- `exports/`
- `logs/`
- `record_files/`
- `profile_images/`
- `ops/local_private_launchers/`
- generated archives such as `.zip`, `.tar`, `.tar.gz`, and `.tgz`
- production exports, customer/client data exports, CRM imports, historical snapshots, and local database files
- synced reference materials

## Before Editing

Before making non-trivial changes, agents should:

- read this file
- inspect relevant source files
- search for existing helpers or patterns
- identify the likely verification command
- check for existing user changes when git is available

## Coding Standards

Agents should:

- use the project's existing language, framework, and style
- keep functions small and named clearly
- avoid adding dependencies unless justified
- avoid broad formatting-only changes
- write clear errors and user-facing messages
- keep secrets out of code and logs

## Testing And Verification

Expected verification commands:

- `python3 -m py_compile crm_app/server.py crm_app/auth_tokens.py crm_app/database.py crm_app/exporting.py crm_app/file_assets.py crm_app/request_io.py crm_app/runtime_health.py api/index.py`
- `python3 scripts/verify_operational_crm.py`
- `python3 scripts/verify_backend_boundaries.py`
- `python3 scripts/verify_current_app_workflows.py`
- `python3 scripts/verify_app_operations.py` only when touching broad workflow behavior or updating legacy operational verifier expectations
- targeted verification scripts under `scripts/verify_*.py` when the change touches a specific deployment, hosted database, security, backup, or Vercel pathway
- local manual verification with `python3 crm_app/server.py --host 127.0.0.1 --port 8765 --auto-port` when UI or route behavior changes

For frontend work:

- verify layout at mobile and desktop sizes
- check important interaction states
- confirm text does not overlap or overflow
- keep CRM workflows dense, scannable, and action-focused rather than marketing-style
- ensure pipeline boards, dashboards, tables, sidebars, and forms remain usable with realistic long names, deal titles, statuses, and notes

For backend work:

- test changed routes, handlers, jobs, or services
- check auth and permission boundaries
- validate error handling
- protect CRM records, tokens, private dashboards, and production data by default
- verify lead/contact/deal ownership, filtering, and access behavior when relevant
- preserve SQLite/local behavior and hosted Supabase/Postgres behavior; check SQL compatibility when changing queries
- for health monitoring, confirm scheduled checks, manual checks, D1 writes, and auth-gated dashboard/API access

For AI agent work:

- test expected happy path
- test at least one failure path
- confirm tool permissions and approval gates

If a check cannot be run, agents must say why.

## Git Rules

Agents must:

- avoid reverting user changes
- keep commits focused when asked to commit
- avoid destructive git commands unless approved
- avoid force-pushes unless approved

Agents should not create commits unless Kevin asks for them.

The main ChillCRM repo is `https://github.com/knations/ChillCRM.git` on branch `main`. Before pushing, agents must check repo status, avoid staging unrelated local helper files, and summarize exactly what will be committed.

## Deployment Rules

Deployment requires explicit approval unless Kevin says otherwise in the current task.

Before deployment, agents must provide:

- target environment
- branch or commit
- change summary
- verification completed
- risks
- rollback plan
- deployment command or platform action

## Security Rules

Agents must:

- never commit secrets
- never print secrets in chat
- avoid weakening authentication or authorization
- flag suspicious access patterns
- ask before modifying production data
- ask before changing DNS, billing, auth, or account settings
- treat leads, contacts, companies, deals, notes, proposals, tokens, and dashboard sessions as sensitive data
- avoid logging full CRM records, private notes, bearer tokens, cookies, or secret values

## Communication Rules

Agents should provide:

- short progress updates for longer work
- concise final summaries
- verification results
- important file paths
- unresolved risks

Avoid dumping raw logs unless Kevin asks for them.

## Definition Of Done

The task is done when:

- the requested outcome is complete
- changes are focused and understandable
- verification was run or clearly explained
- no required approval is pending
- risks and next steps are clear
