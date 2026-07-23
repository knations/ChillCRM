# ChillPortal Foundation

ChillPortal is the future client-facing companion to CHILLCRM. This document
defines the boundary before any client route, invitation, provider, or
production access is turned on.

## Confirmed

- CHILLCRM owns internal operator workflows: people, companies, leads, deals,
  pipeline, notes, tasks, calls, files, purchases, archive history, cleanup,
  exports, audit evidence, and owner/admin controls.
- ChillPortal should be separate from the internal CRM interface.
- ChillPortal is Person-first; each portal belongs to one Person record.
- Company context is optional only.
- The current foundation is internal-only: CHILLCRM can prepare Person-linked
  Portal status, shared documents, client next steps, and client-visible notes.
- `/portal?person_id=<id>` is a disabled-by-default staff preview route gated by
  `CHILLPORTAL_ENABLED`; it is not client login or public portal access.
- The approved Portal MVP is a client dashboard with Shared Documents,
  Client Next Steps, and separate client-visible notes only.
- `crm_app/portal_config.py` defines reserved portal route, navigation,
  feature flag, role, schema-plan, and permission-action names.
- `config/chillportal.env.example` contains placeholders only.
- `docs/PORTAL_SCHEMA_PLAN.md` defines the table blueprint reflected by local
  runtime schema helpers.

## Recommended

- Keep ChillPortal at a route boundary such as `/portal`.
- Attach portal data to People first.
- Keep portal users out of internal CRM roles.
- Show only client-safe dashboard data in the portal: shared documents,
  client next steps, and separate client-visible notes.
- Internal CRM notes, call logs, task notes, audit notes, and archive notes
  must not appear in the portal by default.
- Build portal features behind explicit feature flags.
- Keep all internal Portal preparation controls write-locked in hosted
  environments until explicitly approved.
- Use the staff preview only to verify the client-facing shape before adding
  invitations or client auth.

## Unknown

- Production portal URL.
- Auth provider and invitation flow.
- Document storage provider.
- Client-visible field list.
- Whether client-visible notes are read-only, commentable, or both.
- Launch date and launch users.
- Monitoring owner and external monitoring provider for the portal surface.

## Requires Explicit Approval

- Live domain or DNS changes.
- Production auth changes.
- Production environment variables.
- Document integrations.
- Production database migrations or data backfills.
- Any rule that exposes existing CRM notes or call logs to clients.
- Client invitations or client-visible notifications.
- Deploying a portal route to production.

## Not Included In This Foundation

- No enabled client-facing pages.
- No enabled production client routes.
- No production database migration has been applied by this document.
- No storage buckets.
- No invitations.
- No provider integrations.
- No client access changes.
- No production CRM data changes.
