# CHILLCRM And ChillPortal Project Map

## Confirmed

CHILLCRM is the internal sales command center. It owns:

- contacts, companies, leads, deals, and pipeline
- internal notes, tasks, calls, purchases, files, and relationship history
- owner/stage/status/next-action tracking
- duplicate protection, cleanup, audit evidence, exports, and admin controls

ChillPortal is the future client-facing surface. The current foundation is
internal-only and can prepare:

- Person-first client dashboard
- shared documents
- client next steps
- separate client-visible notes

## Recommended Boundary

- Internal operators work in CHILLCRM.
- Clients work in ChillPortal.
- A Portal belongs to a Person record.
- Company context is optional and secondary.
- Portal features read only approved client-safe slices of CRM/project data.
- Portal write actions should stay deferred until the read-only dashboard
  surface is approved and verified.

## Unknown

- Whether ChillPortal ships as routes inside this app or as a separate app that
  shares the same database.
- Which client-visible fields are approved.
- Whether client-visible notes are read-only, commentable, or both.
- Which provider owns auth and document storage.

## Approval Gates

Before moving past the internal foundation, approve:

- client-visible data contract
- auth and invite model
- portal route/domain
- production database migrations
- provider integrations
- monitoring/check ownership
- production deployment
