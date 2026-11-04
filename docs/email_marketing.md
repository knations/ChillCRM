# Email marketing

ChillCRM owns consent, audience review, broadcasts, and CRM triggers. Resend owns delivery and the autoresponder editor, delays, conditions, and running sequences. Only owners and admins can access the Email workspace. New installations default to disabled; schema setup and import are explicit operator actions.

## Migration policy

The ActiveCampaign importer skips all suppressed contacts entirely, before matching existing CRM people. It creates no person, email contact, suppression marker, or tag assignment for them and leaves any existing ChillCRM records unchanged. Their suppression evidence remains in the legacy archive. Reports include `skipped_suppressed`. Unknown-consent contacts are also skipped (`skipped_unknown`). For eligible contacts, normalized email matches existing CRM people; missing people are created. Multiple existing matches are held out entirely (`skipped_ambiguous`) until reconciled rather than creating an unlinked marketing contact. Imports fill blank first-name, last-name, and phone fields, preserve every existing nonblank field, combine existing CRM and imported tags without triggering sequences, and retain source subscription evidence for imported contacts. Repeated imports add no duplicate people or tag assignments.

Until individual list preferences are mapped, any email-list unsubscribe or bounce excludes the contact from import. Unknown consent cannot send. Existing ChillCRM marketing suppression cannot be reversed by an import, provider update, or contact synchronization. The raw archive remains separate from the operational CRM import.

Kevin subsequently approved exceptions for seven identified existing contacts whose Forum Members, Have Fun Get Rich, or Master List unsubscribes represent internal group administration. Pass the private `--consent-policy /absolute/path/policy.json` to preview/apply these exact source-ID/email/list exceptions. The policy records owner authorization and is retained in import evidence. It does not override other-list unsubscribes, bounces, complaints, existing ChillCRM suppression, or provider unsubscribe state, and does not apply to everyone on those lists. The fifteen identified Chillionaire App contacts remain excluded; Kevin requested their permanent deletion, which requires a separate production verification and deletion operation. No deletion is performed by this importer.

## Operator setup

Use a backed-up, isolated database first. Commands default to dry run and never read `.env` automatically. Local operations require an existing explicit database; hosted operations require `--hosted` and the environment-configured hosted adapter. Both respect CRM write locks. Production schema/data changes require Kevin's approval.

```sh
python3 scripts/manage_email_marketing.py setup --db /absolute/path/test.sqlite --apply
python3 scripts/manage_email_marketing.py import --db /absolute/path/test.sqlite --archive /absolute/path/archive
# Review matches, new people, skipped suppression, and unknowns before applying.
python3 scripts/manage_email_marketing.py import --db /absolute/path/test.sqlite --archive /absolute/path/archive --apply
```

Configure server-side secrets through the deployment secret store, never source control or chat:

- `RESEND_API_KEY`: appropriate contact, broadcast, template, automation, and event access.
- `RESEND_FROM`: sender on an already verified domain.
- `RESEND_WEBHOOK_SECRET`: secret for `https://chillcrm.app/api/webhooks/resend`; subscribe to contact changes/deletions and email delivery, bounce, complaint, and engagement events.
- `CHILLCRM_EMAIL_TEST_RECIPIENTS`: comma-separated explicit test allowlist.
- `CHILLCRM_EMAIL_ENABLED=true`: master gate, only after setup and sending approval.
- `CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED=false`: default test-only gate. Only allowlisted addresses can enter broadcast audiences or autoresponders, and dispatch checks this again. Customer release requires separate owner approval to set this true.
- `CHILLCRM_EMAIL_AUTOMATIONS_ENABLED=true`: separate autoresponder gate, only after billing confirmation.
- `CHILLCRM_EMAIL_CONTACT_LIMIT`: defaults to 5000 per broadcast.
- `CHILLCRM_EMAIL_MONTHLY_ENROLLMENT_LIMIT`: defaults to 10000 local sequence enrollments; this is not an account-wide billing cap.

No DNS, billing, account, or deployment settings are changed by this implementation.

## Dispatch and verification

The web app queues work; a separate durable operator scheduler must run the dispatcher. No production scheduler is installed by this change. Do not run network dispatch inside a Vercel request or assume an in-memory timer persists.

```sh
python3 scripts/manage_email_marketing.py process --hosted --max-jobs 20 --apply
```

Choose and approve a frequent scheduler before launch, with one dispatcher, sufficient runtime, monitored failures, and protected credentials. Broadcast audience synchronization advances twenty contacts per job and throttles provider requests. Large first-time audiences can take tens of minutes to prepare; schedule well in advance. This release does not use bulk contact import. Suppressions and cancellations take priority over other pending jobs.

Before a broadcast can queue, send an allowlisted test, review the current audience and fingerprint, and explicitly confirm. A successful test job means provider acceptance, not inbox delivery: check the mailbox too. History separates dispatch status from signed provider events. Webhooks verify the exact body, reject stale signatures, deduplicate events, and never use a late subscription update to undo suppression.

Autoresponders are saved paused. Create a matching custom-event trigger in Resend, using the generated event name. Publish templates with `{{{RESEND_UNSUBSCRIBE_URL}}}`. Activation checks the provider flow, trigger, supported steps, and published templates. Pause and reactivate after editing the provider flow to repeat validation. Tag additions and purchases enroll a contact once per rule; historical imports never enroll. Re-entry, arbitrary visual workflow editing inside ChillCRM, and per-contact cancellation of an existing sequence are outside this release. Pause prevents new enrollments; Request stop in Resend stops the entire provider automation. Unsubscribing prevents subsequent sequence emails according to Resend's rules.

## Failure recovery and rollback

An uncertain provider result becomes `needs_review`; a crashed claimed job stays `processing`. Neither automatically retries. A definite HTTP 429 rejection may retry. Before changing a stalled job, inspect Resend for the exact contact, custom event/run, segment, and broadcast. Never retry an event or broadcast send merely because ChillCRM did not record success. Reconcile provider IDs and outcome with an approved operator data repair; there is no automatic recovery button in this release.

Disable both email gates and stop the dispatcher to prevent new work. This does not cancel provider-scheduled broadcasts or running sequences: cancel/stop those in Resend explicitly. Preserve schema, consent evidence, and event history. Roll application code back through the normal approved deployment process; do not drop data as a rollback shortcut.

## Launch gates

Local synthetic checks cover consent, skipping suppressed contacts with and without existing CRM matches, repeatable import, permissions, signatures/replays, template requirements, chunked dispatch, cancellation, and uncertain-result handling. Actual hosted Postgres and live Resend integration still require a staging verification. Confirm signed webhooks, real test delivery, domain verification, scheduler monitoring, and production import preview before launch.

Resend's marketing contact pricing and autoresponder run/email usage are separate considerations. Confirm the actual account's plan and automation charges before enabling sequences; this implementation does not promise an all-in $40 monthly bill.

## Current rollout evidence (November 4, 2026)

The production contact import has been applied and verified: 176 existing matches combined, 1,466 people added, 733 suppressed contacts excluded, two unknown-consent contacts excluded, and 51 ambiguous email matches held out. Production has 2,474 people and 1,644 marketing contacts: 1,642 imported subscribers plus two owner-approved test contacts. Approved legacy fields/notes are applied; all remaining 185 legacy values are archive-only by owner instruction. The earlier fifteen-contact deletion remains a separate outstanding cleanup; no deletion is implied by this release.

Chillionaire.com is verified in Resend. Direct test messages from `kevin@chillionaire.com` to the two designated test inboxes were reported delivered. KevinNations.com remains registered in a different Resend team; it is not the rollout sender. Kevin separately approved connecting the Resend webhook at `https://chillcrm.app/api/webhooks/resend`: twelve delivery/contact/suppression event types are registered, with the signing secret stored privately and installed as an encrypted production Vercel secret. A real provider event returned HTTP 200; its replay was deduplicated, and an invalid signature returned HTTP 401. No recurring dispatcher is installed.

The supervised provider integration test also passed: ChillCRM's real outbox sent a two-recipient native broadcast and triggered a one-email native autoresponder for the same two allowlisted test contacts. Resend reported all four deliveries, plus the required preliminary preview, as delivered. Test marketing contacts were explicitly consented for this purpose without creating CRM people. The test rule was paused locally and the provider automation disabled after completion. No customer jobs were queued. The Vercel sending/enrollment flags stayed false throughout: only the bounded operator process temporarily enabled allowlisted test dispatch. Private receipts hold actual inbox addresses, provider IDs and delivery evidence.

The first deployment is draft-only: all three sending/enrollment flags remain false. After that smoke check, the separately approved test configuration enables only allowlisted addresses. Until a recurring dispatcher is approved and installed, use the explicit bounded operator command above for supervised tests; this release is not ready for unattended customer campaigns or autoresponders.

Provider references: [automations](https://resend.com/docs/dashboard/automations/introduction), [send-email steps](https://resend.com/docs/dashboard/automations/send-email), [automation API](https://resend.com/docs/api-reference/automations/get-automation), [template API](https://resend.com/docs/api-reference/templates/get-template).

## Automatic dispatcher

Vercel cron calls `GET /api/email/dispatch` every minute. Set an encrypted
`CRON_SECRET` of at least 32 random characters and
`CHILLCRM_EMAIL_DISPATCH_ENABLED=true` only for an approved deployment. Vercel
supplies the bearer header. HEAD requests are rejected without processing work.
The master sending gate, recipient allowlist, and CRM write locks still apply.
Each invocation advances one outbox job (broadcast synchronization remains
limited to 20 contacts per step). A PostgreSQL session advisory lock prevents
overlapping scheduled runs across instances; local runs use a process lock.
The keeper commits immediately so no idle transaction spans network work.
A crashed processing job requires provider reconciliation before operator retry.
No schema migration is needed. Turning off the dispatcher flag pauses future
runs; it does not cancel an already submitted provider broadcast or sequence.

The first enabled release must keep customer sends disabled, allow only
kevinnations@gmail.com and alicianations@gmail.com, and use the verified
`Kevin Nations <kevin@chillionaire.com>` sender. Owner UI sign-in and live
scheduled delivery verification remain release checks.
