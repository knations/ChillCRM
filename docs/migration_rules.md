# Local CRM Migration Rules

These rules convert the Zendesk Sell staging database into the final local CRM database.

## Guiding Principle

Preserve first, clean second.

No record is deleted or silently merged during migration. Records that look related or duplicated are kept and flagged for review.

## Entity Rules

### People

- Zendesk contacts where `is_organization = false` become local people.
- Original Zendesk contact IDs are stored on every person.
- Email is normalized to lowercase for search and duplicate detection.
- If a person points to a Zendesk organization, the local person is linked to the matching local company.
- Missing company links are flagged only if the source relationship points to a non-existent organization.

### Companies

- Zendesk contacts where `is_organization = true` become local companies.
- Original Zendesk contact IDs are stored on every company.
- Company names are preserved exactly and also normalized for search.

### Leads

- Zendesk leads remain local leads.
- Leads are not automatically merged into people.
- If a lead email matches a person email, the lead is linked as a possible match and flagged for review.

### Deals

- Zendesk deals become local opportunities.
- Deal stage, pipeline, contact, organization, source, loss reason, value, and timestamps are preserved.
- Missing contact or organization references are flagged.

### Notes And Tasks

- Notes and tasks are copied to the matching local record when a mapping exists.
- If the linked Zendesk resource cannot be mapped, the item is preserved and flagged.

### Tags

- Tag definitions are normalized by lowercase trimmed name.
- Duplicate tag definitions become one local tag with source aliases.
- Original source tag names remain attached to assignments for traceability.

### Custom Fields

- Custom field definitions are copied.
- Custom field values are copied exactly.
- No custom field is promoted or renamed automatically.
- High-priority application fields may be surfaced in the app as a read-only Application Profile view, but the original custom field values remain preserved.

## Review Flags

The final database creates review flags for:

- duplicate person emails
- duplicate lead emails
- lead/person email overlaps
- duplicate tag definitions
- missing relationship mappings

Flags are stored in `review_flags` and can be resolved later without losing source data.

## Source Traceability

Every migrated record that came from Zendesk has a row in `source_map`.

The source map preserves:

- local table
- local ID
- Zendesk collection
- Zendesk ID
