# ChillPortal Schema Plan

This is the Person-first schema blueprint for the Portal foundation. The local
runtime can create these tables as needed, but this document does not apply a
production migration or change production data.

## Confirmed Direction

- ChillPortal is Person-first.
- A portal belongs to one CHILLCRM Person record.
- Company context is optional background only.
- Portal data is separate from internal CRM data unless manually shared.
- Portal launch should be read-only for clients.

## Foundation Tables

### `portal_profiles`

Purpose: one portal dashboard per approved person.

Recommended fields:

- `id`
- `person_id`
- `status`
- `display_name`
- `company_id`
- `created_at`
- `updated_at`

Notes:

- `person_id` points to the internal People record.
- `company_id` is optional.
- No company-owned portal is planned.

### `portal_shared_documents`

Purpose: documents manually shared to a Person portal.

Recommended fields:

- `id`
- `person_id`
- `archive_item_id`
- `record_file_id`
- `title`
- `visibility_status`
- `shared_at`
- `shared_by_user_id`

Notes:

- Existing files do not become visible automatically.
- Each file must be explicitly shared.
- Internal archive files and CRM files remain private unless shared.

### `portal_next_steps`

Purpose: separate client-visible next steps.

Recommended fields:

- `id`
- `person_id`
- `title`
- `details`
- `due_at`
- `status`
- `sort_order`
- `created_at`
- `updated_at`

Notes:

- These are not internal CRM tasks.
- Internal tasks should not appear in ChillPortal by default.

### `portal_client_notes`

Purpose: separate client-visible notes.

Recommended fields:

- `id`
- `person_id`
- `title`
- `body`
- `visibility_status`
- `published_at`
- `published_by_user_id`
- `created_at`
- `updated_at`

Notes:

- These are not internal CRM notes.
- These are not call logs.
- Internal notes, call summaries, task notes, audit notes, and archive notes
  remain private by default.

## Deferred

- Client replies/comments.
- Company portals.
- Billing/payment visibility.
- Proposal approvals.
- Support tickets.
- Client self-editing.
- Notifications.

## Approval Required Before Build

- Production migration SQL.
- Portal auth/invite model.
- Which internal users can publish portal items.
- Whether portal items can be unpublished or archived.
- Production migration.
- Production deployment.
