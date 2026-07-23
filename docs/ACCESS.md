# Access Boundary

This document separates internal CHILLCRM roles from future ChillPortal roles.

## Confirmed Internal CHILLCRM Roles

The current CRM permission model includes internal roles such as:

- owner
- admin
- staff
- read_only
- migration_operator

These roles control internal CRM actions such as viewing records, editing
records, notes/tasks/follow-ups, backups, restores, exports, user management,
merge actions, and webhook handling.

## Recommended Portal Roles

Portal users should not receive internal CRM roles.

- `portal_client`: a client account user who can view only approved
  client-facing data for their Person-linked portal.
- `portal_contact`: an invited client-side contact who can view only assigned
  client-safe Person-linked portal data.

## Portal Permission Actions

Recommended client-facing actions:

- view own portal dashboard
- view own shared documents
- view own next steps
- view own client-visible notes

Recommended internal portal-management actions:

- manage portal visibility
- preview portal experience
- manage portal invites
- publish portal dashboard content

## Forbidden For Portal Users

Portal users should not access:

- full CRM people/company/deal lists
- other People records
- company dashboards
- internal notes
- internal call logs
- internal tasks
- audit logs
- cleanup tools
- exports
- admin user management
- migration or archive evidence

## Requires Explicit Approval

- creating live portal users
- sending invites
- changing authentication providers
- changing production role rules
- exposing any existing CRM field to clients
- exposing existing internal notes or call logs to clients
