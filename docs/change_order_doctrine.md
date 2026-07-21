# CHILLCRM Change Order Doctrine

## North Star

CHILLCRM is a sales command center, not a contact list. Every active lead, person, company, and deal should quickly answer:

- Who owns it?
- What stage is it in?
- What is it worth?
- What happened last?
- What happens next?
- When does that next action need to happen?

## Change Order Rule

Every change should either increase sales clarity, protect the data, reduce owner/admin friction, or make the app feel calmer and faster to use. If a change does not clearly do one of those things, park it.

## Safety Rules

- Do not change production CRM records unless the owner explicitly approves that write.
- Schema and code changes must preserve imported history, audit evidence, attached files, notes, tasks, tags, purchases, and relationships.
- New automation must append evidence instead of overwriting useful context.
- New enforcement rules should be introduced in stages: show warnings first, support the required fields second, enforce only after the user flow is obvious.
- Keep local/export packages and Git history usable as rollback evidence.

## Definition of Done

A change is not done until:

- The feature is visible where a real user would expect it.
- The mobile and desktop experiences still work.
- Existing CRM powers still work: search, filters, editing, notes, tasks, files, tags, purchases, calls, exports, and record opening.
- Verification checks pass locally.
- The change is committed and pushed to GitHub.
- Vercel has deployed the pushed version or a specific deploy blocker is recorded.

## Roadmap Order

### Wave 1: Today Cockpit And Next Action Visibility

Goal: make the dashboard answer what needs attention now.

Prerequisites:

- Use existing tasks, deals, stages, leads, and audit data.
- Do not require production data edits.
- Treat local open tasks on deals as the first version of “next action.”

Deliverables:

- Dashboard block for overdue follow-ups, due-today follow-ups, active deals missing a local next action, stagnant active deals, hot deals, and new leads.
- Short lists that open the relevant record or work queue.
- No hard enforcement yet.

### Wave 2: Required Next Action Capture

Goal: every active deal has a clear next step.

Prerequisites:

- Wave 1 exposes missing-next-action deals.
- Deal detail view has an easy task/next-action creation path.

Deliverables:

- Active deal detail warning when no local open next action exists.
- Stage-change warning before moving an active deal without a next action.
- Later, optional enforcement once the workflow feels natural.

### Wave 3: Visual Pipeline Board

Goal: make deals easier to manage visually.

Prerequisites:

- Stage categories and active/won/lost handling are confirmed.
- Deal cards show name, stage, value, probability/readiness, close date, owner, and next action.

Deliverables:

- Drag/drop pipeline board.
- Stage movement with audit trail.
- Stale and no-next-action badges.

### Wave 4: Deal Record Upgrade

Goal: make deals first-class sales files.

Prerequisites:

- Pipeline board exists or is in progress.
- Required deal fields are agreed.

Deliverables:

- Qualification fields: need, budget, authority, timeline, service interest, urgency, fit score, objections.
- Deal activity timeline.
- Deal-linked notes, calls, files, proposals, tasks, and contacts.

### Wave 5: Proposal And E-Signature Tracking

Goal: track offers through acceptance.

Prerequisites:

- Decide whether proposals are internal records only, uploaded files, or connected to an e-signature provider.
- Choose provider only when needed.

Deliverables:

- Proposal statuses: drafted, sent, viewed, negotiating, accepted, declined, expired.
- Proposal files and links tied to deals/people.
- E-signature integration when it saves real manual work.

### Wave 6: Won/Lost Handoff

Goal: closing a deal should produce the next operational step.

Prerequisites:

- Clear won/lost statuses and reason list.
- Decide what a won deal becomes: client, project, onboarding room, invoice, or task list.

Deliverables:

- Won/lost reason capture.
- Automatic client/project/onboarding task handoff.
- Lost-lead nurture list.

### Wave 7: Dashboards And Forecasting

Goal: make revenue and pipeline health obvious.

Prerequisites:

- Deals have reliable stage, value, expected close date, and next action data.

Deliverables:

- Pipeline value, weighted forecast, deals by stage, overdue follow-ups, stagnant deals, close rate, lead source, and sales velocity.

### Wave 8: AI Sales Assistant

Goal: reduce thinking tax without hiding the source data.

Prerequisites:

- Timeline, tasks, deals, notes, calls, and purchases are structured enough to summarize.

Deliverables:

- Call note cleanup.
- Follow-up drafts.
- Deal summaries.
- Stale-deal warnings.
- Next-best-action suggestions.

## Parking Lot

These are useful, but should not interrupt the core command center unless they become urgent:

- Multi-company tenancy.
- Full email/calendar sync.
- Client portal/onboarding room.
- Advanced campaign attribution.
- Custom drag/reorder layout builder.

## Current Approved Next Move

Start Wave 1 now: build Today Cockpit and next-action visibility without modifying CRM records.
