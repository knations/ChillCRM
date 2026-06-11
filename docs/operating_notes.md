# Operating Notes

## Start Local CRM

Double-click `Start Local CRM.command` from the project folder.

The starter opens the local CRM in the default browser. If `http://127.0.0.1:8765` is already busy, it automatically uses the next open local port and prints the exact address.

## Status

The Dashboard opens with Start Today. This first-screen panel shows the current Next Action and the first Daily Operating Guide steps, then links into Status, the printable guide, and the guide CSV export. Use it when you want the shortest path into normal local CRM work.

The sidebar Status view summarizes the migration at a glance:

- readiness checklist with Done, Needs Attention, and Waiting states
- imported local CRM counts
- latest Zendesk snapshot metadata
- final optional Zendesk sweep status
- project-level decisions that still need a saved path
- daily operating guide for the current runbook
- operating work queue for safe daily CRM work
- data-quality review for ordinary contact and pipeline hygiene
- cleanup review progress
- linked-resource counts
- backup count and latest backup
- portable export package readiness
- verification/report links

Use this view when deciding whether the local CRM is ready for daily use or what still needs attention.

Use `reports/migration_completion_audit.md` when you want the current end-to-end migration status in one place. It marks the local CRM operational for daily work while keeping the remaining Project Decisions, cleanup review, and ordinary data-quality gates visible. The matching export is `local_crm_migration_completion_audit.csv`, and both are included in the Complete Local CRM Package.

Use `reports/local_crm_database_map.md` when you want the handoff map for the local database itself. It lists the SQLite tables, row counts, columns, relationships, report inventory, CSV export inventory, and the read-only safety boundary. The matching export is `local_crm_database_map.csv`, and both are included in the Complete Local CRM Package.

Use `reports/zendesk_independence_checklist.md` when you want the local-only readiness checklist. It shows what proves the local CRM can operate without new Zendesk writes, what raw exports/document files/backups/reports must be preserved, and what to download before any future Zendesk decommission decision. The matching export is `local_crm_zendesk_independence_checklist.csv`, and both are included in the Complete Local CRM Package.

Use `reports/remote_admin_access_plan.md` when planning remote access for you and admins. It lays out the recommended managed-cloud path, self-hosted and hybrid alternatives, hosted database migration, private file storage, user roles, security controls, staging verification, and cutover steps. The matching export is `local_crm_remote_admin_access_plan.csv`. This plan does not expose localhost, provision hosting, invite users, migrate data, or save the hosting decision.

Use `reports/remote_admin_permissions_matrix.md` when deciding how you and admins should access/update the remote CRM. It maps Owner, Admin, Staff, Read-only, and temporary Migration Operator roles against the CRM's actual actions: record edits, notes/tasks, archive review, archive linking, cleanup decisions, project decisions, exports, backups, restore, user management, and cutover. The matching export is `local_crm_remote_admin_permissions_matrix.csv`. It does not create users, grant access, expose localhost, migrate data, or change CRM records.

Use `reports/remote_admin_implementation_blueprint.md` when turning the remote access plan into a build sequence. It defines hosted app workstreams, remote-only tables, endpoint changes, implementation steps, verification gates, and open decisions for the shared CRM. The matching export is `local_crm_remote_admin_implementation_blueprint.csv`. It does not provision hosting, create users, invite admins, migrate data, expose localhost, save decisions, or change CRM records.

Use `reports/remote_admin_rollout_board.md` when managing the selected Supabase/Vercel private-company CRM rollout. It turns the plan into a task board with completed staging work, remaining blockers, owner roles, proof gates, decision prompts, staging validation, owner shakedown, optional internal-user timing, and cutover milestones. The matching export is `local_crm_remote_admin_rollout_board.csv`. It does not unlock hosted writes, create users, invite internal users, save decisions, switch source of truth, expose localhost, or change CRM records.

Use `reports/remote_hosting_decision_packet.md` when choosing the hosting posture that unlocks the remote CRM build. It compares A managed cloud, B self-hosted, and C hybrid transition paths with scores, minimum requirements, owner questions, and next steps. The matching export is `local_crm_remote_hosting_decision_packet.csv`. It does not choose a provider, provision hosting, migrate data, create users, upload files, invite admins, save decisions, expose localhost, or change CRM records.

Use `reports/remote_managed_cloud_provider_shortlist.md` when narrowing the managed-cloud stack after the hosting posture is confirmed. It compares current official provider options for app hosting, managed Postgres, private file storage, auth, backups, staging, owner questions, and next steps. The matching export is `local_crm_remote_managed_cloud_provider_shortlist.csv`. It does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.

Use `reports/remote_staging_pricing_preflight.md` before opening or using any provider account. It turns the DigitalOcean/Railway finalists into official-source pricing components, first-month staging estimate profiles, preflight setup gates, cost controls, owner questions, and next steps. The matching export is `local_crm_remote_staging_pricing_preflight.csv`. It does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.

Use `reports/remote_staging_setup_runbook.md` after the budget/preflight worksheet and before any provisioning. It defines the DigitalOcean/Railway staging paths, setup phases, provider-specific setup tasks, environment variables, validation gates, approval gates, and official setup sources. The matching export is `local_crm_remote_staging_setup_runbook.csv`. It does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.

Use `reports/remote_staging_deployment_spec.md` after the setup runbook and before provisioning. It turns the runbook into deployment targets, app service settings, configuration variables, package inputs, implementation gaps, smoke tests, owner decisions, and next steps. The matching export is `local_crm_remote_staging_deployment_spec.csv`. It does not choose a provider, provision hosting, create accounts, enter payment details, migrate data, upload files, create users, invite admins, save decisions, expose localhost, or change CRM records.

For hosted staging, set `REMOTE_WRITE_LOCK=true` before exposing the app to validation users. The server then blocks browser/API POST writes while read-only routes, reports, and exports remain available for validation. Local default use stays unlocked unless that environment variable is explicitly enabled.

Hosted staging can use `/health` or `/api/health` for provider health checks. The payload confirms app/database/report readiness, `CRM_ENV`, and write-lock mode without returning client counts or record details. The browser top bar also shows the current environment label so local, staging, and production copies are easier to tell apart.

Set `EXPORT_PACKAGE_ENABLED=false` in hosted staging until export permissions are validated. This blocks the Complete Local CRM Package and Downloaded Document Files package endpoints with a 403 response while leaving ordinary CSV/report exports available. Local default use stays enabled unless that environment variable is explicitly disabled.

Keep `DOCUMENT_FILE_ACCESS_ENABLED=true` only in hosted staging where private Supabase Storage, CRM auth, role checks, and signed document redirects have passed smoke. If storage privacy, auth, or signed-link validation regresses, set it back to `false` so `/api/archive_file` returns a 403 while the issue is fixed. Local default file access remains available for normal local archive review.

Use `POST https://chillcrm.app/api/webhooks/zapier_purchase` for Zapier shopping-cart purchase intake after setting the server-side `CHILLCRM_ZAPIER_WEBHOOK_SECRET` environment variable in Vercel. Zapier should send `Content-Type: application/json` and either `Authorization: Bearer <secret>` or `X-CHILLCRM-WEBHOOK-SECRET: <secret>`. The payload must include a customer email and may include `name`, `first_name`, `last_name`, `phone`, `mobile`, `order_id`, `transaction_id`, `product_name`, `total`, `currency`, and `purchased_at`. CHILLCRM finds an existing Person by email, fills only blank contact basics, appends the purchase as a local note, skips duplicate order/transaction deliveries, and creates a new Person only when the email is not already present.

Use `reports/remote_staging_validation_matrix.md` as the pass/fail worksheet for the hosted Supabase/Vercel staging load. It includes expected local counts, validation sections, detailed checks, evidence fields, blocker rules, owner-shakedown gates, optional internal-user gates, and cutover gates. The matching export is `local_crm_remote_staging_validation_matrix.csv`. It does not unlock writes, create users, invite internal users, save decisions, switch source of truth, expose localhost, or change CRM records.

Use `reports/remote_admin_pilot_onboarding_plan.md` after staging validation passes for the owner-only CHILLCRM shakedown. It defines private-company roles, prerequisites, onboarding steps, shakedown workflows, permission probes, support watch items, blocker rules, signoff gates, and the optional internal-admin-later path. The matching export is `local_crm_remote_admin_pilot_onboarding_plan.csv`. It does not unlock hosted writes, create users, invite internal users, save decisions, switch source of truth, expose localhost, or change CRM records.

Use `reports/remote_production_cutover_checklist.md` after provider backup/restore proof, newest hosted smoke, hosted write-audit rehearsal, and owner shakedown are signed off, before making the hosted CRM the source of truth. It defines the local write freeze, final backup/package/document package, production load, repeated validation, owner/internal handoff, rollback triggers, first-week monitoring, communication plan, and signoff gates. The matching export is `local_crm_remote_production_cutover_checklist.csv`. It does not unlock hosted writes, create users, invite internal users, switch source of truth, save decisions, expose localhost, or change CRM records.

Use `reports/local_write_freeze_readiness.md` before the production cutover window to verify the local read-only freeze control. During the final package/load window, set `CHILLCRM_LOCAL_WRITE_FREEZE=true` only on the local SQLite app. The guard blocks local CRM mutations and restore operations while keeping `/api/backup`, read paths, reports, and exports available for final rollback/package evidence. The matching CSV is `reports/local_write_freeze_readiness.csv`, generated by `scripts/verify_local_write_freeze_readiness.py`; it does not enable the freeze, deploy code, call providers, switch source of truth, or change CRM records.

Use `reports/vercel_environment_readiness.md` to verify Vercel environment variable names and production targets without storing values. It confirms the locked staging runtime keys for hosted Postgres, auth, remote write lock, export lock, Supabase Storage, and private document signing are present. The matching CSV is `reports/vercel_environment_readiness.csv`, generated by `scripts/verify_vercel_environment_readiness.py`. It does not deploy, change provider settings, expose secrets, unlock writes, switch source of truth, or change CRM records.

Use `reports/vercel_public_protection.md` to verify Vercel Authentication blocks public unauthenticated access across the hosted app shell, API routes, report files, and static bundle. The matching CSV is `reports/vercel_public_protection.csv`, generated by `scripts/verify_vercel_public_protection.py`. It uses no bypass secret, does not log in, does not expose secrets, and does not change CRM records.

Use `reports/supabase_backup_evidence_packet.md` before trying to clear the Supabase backup/PITR gate. It gives the owner/operator a non-secret Dashboard checklist, the exact backup/PITR facts that are safe to share, and the matching command options for either Management API token evidence or owner-confirmed Dashboard evidence. The matching CSV is `reports/supabase_backup_evidence_packet.csv`, generated by `scripts/prepare_supabase_backup_evidence_packet.py`. It does not call Supabase, restore backups, unlock writes, expose secrets, switch source of truth, or change CRM records.

Use `reports/remote_monitoring_readiness.md` before owner shakedown and source-of-truth cutover. It verifies the non-secret monitoring evidence for Vercel deployment/protection, health endpoints, newest hosted smoke, Supabase backup monitoring, hosted write-audit evidence, provider log/error ownership, and owner feedback cadence. The matching CSV is `reports/remote_monitoring_readiness.csv`. It does not create monitors, change provider settings, unlock writes, expose secrets, or change CRM records.

Use `reports/remote_monitoring_signoff.md`, `reports/hosted_write_unlock_audit_rehearsal.md`, and `reports/owner_shakedown_signoff.md` as the pending approval/rehearsal records for the last production gates. The corresponding scripts are `scripts/record_remote_monitoring_signoff.py`, `scripts/prepare_hosted_write_audit_rehearsal.py`, and `scripts/record_owner_shakedown_signoff.py`. The pending reports do not pass production gates until explicit owner approval or actual rehearsal evidence is recorded.

Use `reports/remaining_production_gates_packet.md` as the single operator packet for the remaining secrets, approvals, command order, proof reports, and safety boundaries. The matching CSV is `reports/remaining_production_gates_packet.csv`, generated by `scripts/prepare_remaining_production_gate_packet.py`. It does not store secrets, run hosted smoke, call Supabase, unlock writes, switch source of truth, or change CRM records.

Use `reports/owner_approved_wave_packet.md` after the owner has successfully signed in and before disabling temporary owner recovery. It gives the exact owner reply, recovery-disable command, redeploy/freshness fallback sequence, secret-handling boundaries, proof reports, and remaining separate owner approvals. The matching CSV is `reports/owner_approved_wave_packet.csv`, generated by `scripts/prepare_owner_approved_wave_packet.py`. It does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.

Use `reports/owner_gate_reply_validation.md` after owner intake answers are supplied. The matching CSV is `reports/owner_gate_reply_validation.csv`, generated by `scripts/validate_owner_gate_reply.py`; it accepts `--reply-file` or `--stdin`, rejects secret-like values, classifies non-secret approvals/facts, and produces candidate gate commands without executing them. It does not call providers, deploy code, unlock writes, prompt for secrets, approve gates by itself, switch source of truth, or change CRM records.

Use `reports/remaining_gate_guardrails.md` as the source-level proof that approval-sensitive production scripts are guarded before the owner-approved wave begins. The matching CSV is `reports/remaining_gate_guardrails.csv`, generated by `scripts/verify_remaining_gate_guardrails.py`. It reads local source files only and does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.

Use `reports/remaining_gate_execution_readiness.md` as the execution-coverage proof for the remaining production blockers. The matching CSV is `reports/remaining_gate_execution_readiness.csv`, generated by `scripts/verify_remaining_gate_execution_readiness.py`. It verifies that every blocking gate has a matching needed input, proof report, safe command sequence, owner/operator boundary, private secret-handling path, and final cutover guardrail; it does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.

Use `reports/private_execution_inputs.md` as the non-secret private-input map for the remaining Supabase/Vercel production steps. The matching CSV is `reports/private_execution_inputs.csv`, generated by `scripts/verify_private_execution_inputs.py`. It records only whether Vercel, owner-password, Supabase database, backup/PITR, bypass, and deploy-time database inputs are present or can be handled by hidden prompts; it never stores token, password, database URL, service-role, or bypass-secret values, and it does not call providers, unlock writes, approve gates, switch source of truth, or change CRM records.

Use `reports/owner_confirmed_production_wave.md` after owner hosted access is confirmed to coordinate the next private execution wave. The matching CSV is `reports/owner_confirmed_production_wave.csv`, generated by `scripts/run_owner_confirmed_production_wave.py`. Dry-run mode is report-only; execution mode requires explicit flags such as `--owner-confirmed-access --execute-owner-recovery-wave --prompt-secrets` and still does not approve write-audit rehearsal, sign monitoring/shakedown/cutover, change `REMOTE_WRITE_LOCK`, store secrets, or declare hosted Supabase/Vercel as source of truth.

Use `reports/secret_handling_boundaries.md` as the source/report/config proof that CHILLCRM production files do not carry secret values. The matching CSV is `reports/secret_handling_boundaries.csv`, generated by `scripts/verify_secret_handling_boundaries.py`. It scans the curated app, source, docs, reports, and config-example surface while excluding raw exports, database files, backups, and document archives; it does not call providers, unlock writes, prompt for secrets, switch source of truth, or change CRM records.

Use `reports/hosted_redeploy_preflight.md` before the next Vercel redeploy. It proves the local hosted runtime package, deployment freshness blocker, locked staging environment, public protection, Vercel ignore rules, deploy helper, hosted smoke wrapper, and operator packet are ready before private Vercel/owner credentials are used. The matching CSV is `reports/hosted_redeploy_preflight.csv`, generated by `scripts/verify_hosted_redeploy_preflight.py`. It does not call providers, deploy code, unlock writes, prompt for secrets, approve gates, switch source of truth, or change CRM records.

Use `reports/supabase_staging_data_parity.md` before source-of-truth cutover to verify the saved Supabase staging validation still matches the current local CRM source. The matching CSV is `reports/supabase_staging_data_parity.csv`, generated by `scripts/verify_supabase_staging_data_parity.py`. It reads local counts and existing non-secret reports only; it does not call Supabase, upload files, unlock writes, prompt for secrets, switch source of truth, or change CRM records.

Use `reports/supabase_staging_refresh_preflight.md` before reloading Supabase staging from local data. It verifies the local database, rollback package, schema SQL, migration-script guardrails, SSL root certificate, staged lock boundary, and exact stale-table scope before any database URL is supplied. The matching CSV is `reports/supabase_staging_refresh_preflight.csv`, generated by `scripts/verify_supabase_staging_refresh_preflight.py`. It does not call Supabase, reset schemas, upload files, unlock writes, prompt for secrets, switch source of truth, or change CRM records.

Use `reports/supabase_staging_refresh_run.md` as the execution record for refreshing Supabase staging. The matching script is `scripts/run_supabase_staging_refresh.py`; without `--execute` it records readiness/input-required only, and with `--execute --prompt-secrets` it prompts privately for the Supabase database URL, runs the preflight, reloads only the staging `crm` schema, reruns parity, and refreshes production readiness without storing the credential.

Use `scripts/run_safe_production_gate_checks.py` as the guided safe runner for the remaining non-destructive production checks. `--refresh-only` refreshes non-secret gate reports, including cutover rollback package readiness, local write-freeze readiness, hosted redeploy preflight, remaining gate execution readiness, private execution inputs, secret-handling boundaries, Supabase staging refresh preflight, Supabase staging refresh run readiness, Supabase staging data parity, and remaining gate guardrails. `--all-safe --prompt-secrets` runs hosted smoke, Supabase backup visibility, and report refreshes with hidden prompts. The matching proof is `reports/safe_production_gate_runner.md`. It does not store secrets, write CRM records, unlock writes, approve write-audit rehearsal, sign monitoring, sign owner shakedown, restore backups, or switch source of truth; hosted smoke may create and deactivate temporary app users to prove role behavior.

Use `reports/cutover_rollback_package_readiness.md` to verify the local rollback package before any production source-of-truth switch. It checks local database health, existing project backups, the prior disposable restore drill, export package readiness, document package readiness, and the Supabase storage manifest for 203 uploaded document files. The matching CSV is `reports/cutover_rollback_package_readiness.csv`, generated by `scripts/verify_cutover_rollback_package_readiness.py`. It does not create backups, restore databases, upload files, change hosted settings, unlock writes, switch source of truth, expose secrets, or change CRM records.

Use `reports/source_of_truth_cutover_preflight.md` immediately before any final source-of-truth approval attempt. The matching CSV is `reports/source_of_truth_cutover_preflight.csv`, generated by `scripts/verify_source_of_truth_cutover_preflight.py`. It proves the final approval script is guarded, the operator packet has the support-window and rollback-posture command shape, local freeze and rollback package evidence are ready, and open production gates still block cutover; it does not call providers, unlock writes, approve cutover, expose secrets, switch source of truth, or change CRM records.

Use `reports/remote_production_readiness.md` as the single current-source production gate report. It consolidates local integrity, latest Vercel deployment readiness, Vercel public protection, secret-handling boundaries, remaining gate execution readiness, hosted smoke freshness, local restore drill, local write-freeze readiness, cutover rollback package readiness, Supabase provider backup readiness, hosted write-audit rehearsal, remote monitoring readiness, and owner-shakedown signoff. The matching CSV is `reports/remote_production_readiness.csv`. It does not unlock writes, restore backups, create users, expose secrets, switch source of truth, or change CRM records.

Use `reports/hosted_database_migration_readiness.md` as the technical preflight for moving the local CRM database to a hosted shared database. It inspects the live SQLite schema, row counts, type translations, foreign keys, JSON/timestamp/file-path columns, migration requirements, and remote rollout risks. The matching export is `local_crm_hosted_database_migration_readiness.csv`. It does not create a remote database, provision hosting, migrate data, or change CRM records.

Use `reports/hosted_database_schema_draft.md` and `reports/hosted_database_schema_draft.sql` when you want the provider-neutral hosted database shape. The draft translates the local CRM tables into a managed-Postgres-style schema and adds remote-only app user, role, permission, audit, private file, saved view, and migration-run tables. The matching export is `local_crm_hosted_schema_draft.csv`. It is for staging review only and does not create a remote database, provision hosting, migrate data, create users, or change CRM records.

Use `reports/hosted_database_data_load_plan.md` when planning the first hosted staging load. It sequences the live local CRM tables by load phase and row count, then lists remote seed data, private-file migration, validation checks, and cutover gates. The matching export is `local_crm_hosted_data_load_plan.csv`. It does not create a remote database, upload files, provision hosting, migrate data, create users, or change CRM records.

The Daily Operating Guide in Status is the current live runbook. It organizes the recommended daily order across Follow Up, active pipeline deals, New leads, Data Quality, Archive Review, recent local changes, Project Decisions, Cleanup Starter review, and export-package checks. Its printable report also includes the first-week handoff, pre-change safety checklist, and recovery/portability checklist. Opening a step navigates to an existing CRM surface or report; the guide itself does not save decisions, merge records, resolve cleanup flags, or change Zendesk Sell.

Use `reports/daily_operating_guide.md` when you want the printable checklist, or export `local_crm_daily_operating_guide.csv` when you want the same runbook as a portable working sheet. The Archive Review step links to `reports/archive_review_worklist.md` and exports `local_crm_archive_review_worklist.csv` for the call/text review queue.

The Operating Work Queue in Status separates safe daily CRM work from major cleanup decisions. Use it to jump to Follow Up, active pipeline deals, New leads, Data Quality, Archive Review, Cleanup review, Archive, Linked Resources, Activity, recent records, recent local changes, and recent saved views without saving project decisions or running cleanup.

The Follow Up card shows imported/local task counts. Imported tasks came from Zendesk Sell and may represent historical reminders; local tasks are follow-ups created inside this CRM.

The Follow Up view includes a Transition Plan for moving from old Zendesk reminders into local CRM follow-ups. Use Show Imported Open and Show Overdue Imported to review historical tasks first. If a reminder is still relevant, use Copy Local on that imported task row and choose a fresh local due date, or leave the due date blank. Copy Local creates a separate local follow-up; it does not complete or delete the imported Zendesk task.

Pipeline Focus in the Operating Work Queue shows active non-won/non-unqualified deals and the newest New leads. Open Active Deals sorts the Deals list by value; Open New Leads opens the Leads list filtered to New.

The Data Quality card and list in the Operating Work Queue show ordinary CRM hygiene items: records with no usable contact channel, leads missing email, deals missing value, and any owner/stage/relationship gaps if they appear. Use the People, Companies, Leads, or Deals shortcuts to open the normal CRM lists with the matching Quality filter applied. From there, you can open records in the detail panel, edit known values locally, save the filtered view, reset the view, or export the filtered CSV. The printable report includes the daily work order, issue summary, owner split, and safety boundary. When an edit fixes the active quality issue, the focused list refreshes after saving so the corrected record drops out of that queue.

Archive Review in the Operating Work Queue shows unreviewed calls/texts, needs-lookup items, ready-to-link items, archive-only reviewed progress, and the highest-volume unlinked numbers. Its shortcuts open Archive with the matching review-status or phone-number queue already selected. Opening these queues does not save review status or link anything; those actions still require explicit sidebar buttons.

Open `reports/archive_review_worklist.md` from Status when you want the printable Archive Review queue, or export `local_crm_archive_review_worklist.csv` when you want a portable working sheet. It includes the archive linkage snapshot, top unlinked numbers, and first review items without changing any records.

Open `reports/archive_review_triage.md` when you want suggested review lanes for the same unlinked calls/texts. It groups items as likely archive-only, needs lookup, ready-to-link candidate, or manual review using phone-match evidence, repeated sender patterns, short-code/service signals, promotional language, and call-duration/recording clues. The Archive screen can also filter by these triage lanes and save the filtered view for reuse. These are suggestions only; saving a review status still happens explicitly from the Archive inspector.

Open `reports/archive_association_audit.md` from the Archive & Links work queue card when you want the broader association audit. It confirms which recovered data is already linked, how document files are handled, which call recording URLs were preserved, and why the remaining calls/texts should not be auto-linked.

People, Companies, Leads, and Deals list rows and opened detail panels also show read-only Quality badges. These badges make missing contact, email, owner, value, stage, or relationship issues visible while working normal records; they do not change records or mark anything resolved.

On desktop and laptop-width screens, opened records stay in the right-side inspector while the list remains visible. On narrower screens, the inspector stacks below the list so the record forms and tables still fit.

When the inspector is narrow, edit fields, address fields, contact-action buttons, and task controls use a single-column inspector layout. When the inspector stacks full-width, those forms can use wider layouts again.

Long detail panels keep the record, tag, custom-field, or cleanup-group title pinned at the top of the inspector while you scroll through fields, activity, notes, tasks, archive items, or review evidence.

When a People, Companies, Leads, or Deals row is open in the inspector, the matching list row is highlighted so you can keep your place while working through a queue.

Recent Local Changes in the Operating Work Queue shows the latest audited local edits, creates, notes, tasks, tag saves, address saves, cleanup decisions, and project decisions. Open Local Changes jumps into Activity with the Local Changes filter selected. This is read-only visibility into what changed locally.

Source Mix in the Operating Work Queue shows imported, local-only, and locally changed counts for People, Companies, Leads, and Deals. Use its buttons to open the matching list with the Source filter already applied. This is read-only navigation; it does not save decisions, merge records, or change Zendesk Sell.

Portable export package readiness in Status confirms whether the Complete Local CRM Package and Downloaded Document Files package are available. Open Packages jumps to Exports.

Open the report from Status when you want the printable summary, or use the CSV for the full working list. This is separate from Cleanup and does not merge, delete, resolve, or rewrite records.

## Archive Linking

The Archive view preserves recovered Zendesk Sell calls, text messages, documents, orders, and lead conversions. Documents, orders, and lead conversions were linked automatically when Zendesk supplied a clear related record. Remaining unlinked calls and texts stay searchable as historical archive items.

Use the Manual Archive Review Queue in Archive to work unlinked calls/texts in batches. The queue shows review counts and the highest-volume unlinked numbers. Use a review-status shortcut to filter Unreviewed, Needs Lookup, Ready to Link, or Archive-only Reviewed items, or use a top-number shortcut to focus the table on one phone/source number.

Use `reports/archive_review_worklist.md` beside the in-app queue when you want a printable or exportable worklist. Use `reports/archive_association_audit.md` when you want the proof behind the linkage split. The audit makes the key split explicit: downloaded document files are already linked to local person records, while the remaining call/text items do not have hidden Zendesk resource IDs, associated deal IDs, or exact local CRM phone candidates.

Use `reports/archive_review_triage.md` beside the worklist when deciding review order. Start with high-confidence likely archive-only groups, or use the Archive triage lane filter to open that batch directly in the app, then move to needs-lookup items. Only use Ready to Link when a target record is confirmed. The triage packet and lane filter do not save review status, link archive items, or change CRM data.

Use Inspect on an Archive row to open the right-sidebar Archive item panel. If the item is unlinked, search for a local target record or enter the local record type and ID, then use Link Archive Item only when you are confident the history belongs to that record.

From the same inspector, save a Review Status before linking if you want to track progress without attaching the item. Use Save Review to stay on the item, or Save & Next to record the status and open the next item in the current Archive queue. Archive-only Reviewed means the item should remain historical context. Needs Lookup means another source is needed before a target can be chosen. Ready to Link means the likely target has been identified and the item can be linked after confirmation.

Manual archive linking creates a local backup and audit entry before attaching the archive item. It does not change Zendesk Sell, merge records, delete records, or relink items that are already attached.

Saving an archive review status also creates a local backup and audit entry. Filtered Archive CSV exports include review status and review notes.

## Follow Up Source

Follow Up can filter task source:

- All sources shows everything.
- Imported from Zendesk shows historical Zendesk Sell tasks.
- Local only shows tasks created inside this local CRM.

The source selection is saved in Follow Up saved views and included in filtered task CSV exports. Task rows and record-detail task cards show Imported or Local labels.

## Project Decisions

Use the Project Decisions section in Status to track the major choices that affect future merge execution, Application Profile editability, archive matching, and the Apple-style visual redesign.

Each Project Decision shows impact facts from the local data, such as affected cleanup groups, profile coverage, unlinked archive items, or readiness context.

Saving a Project Decision creates a local backup first, then records the selected path and note in the local database, Activity, and audit log. It does not merge, delete, resolve, or rewrite CRM records.

Use `reports/project_decision_brief.md` or the Project Decisions CSV export when you want a printable/exportable snapshot of the current decision state, impact facts, execution gates, preview actions, backup safety, and restore path.

Use `reports/project_decision_sequence.md` when saving the remaining Project Decisions. It orders the seven recommended paths and explains what each choice unlocks without saving decisions or changing records.

The Status view also shows this sequence directly above the Project Decision cards. Use the in-app sequence when working through the decisions one by one; use the report when you want a printable/exportable reference.

The Decision Prep Packet in Status is a read-only review packet for the remaining major choices. It shows active pending decisions first, parks deferred decisions after them, and includes the recommended path, impact facts, evidence links, an Export Packet CSV, and a printable report at `reports/decision_prep_packet.md`. Opening or exporting the packet does not save choices or change CRM records.

For the duplicate people and duplicate leads policy decisions, Status also links directly to the matching review worksheet from Next Action, Start Today, Decision Prep, the Project Decision card, and the printable decision reports. Use the spot-check evidence to decide the A/B/C policy, then use the worksheet to review the individual groups; neither link saves a policy or group decision.

Use `reports/project_decision_ballot.md` when you want a mark-up worksheet before saving decisions. It lists each major choice, all available options, the recommended path, evidence links, and blank choice/note fields. The matching CSV export is `local_crm_project_decision_ballot.csv`. Opening or exporting the ballot does not prefill or save any Project Decision.

Use `reports/project_decision_option_matrix.md` when you want a compact side-by-side comparison of the remaining A/B/C choices. It shows the recommendation, tradeoff, evidence report, after-save effect, and save boundary for each option. The matching CSV export is `local_crm_project_decision_option_matrix.csv`. Opening or exporting the matrix does not prefill or save any Project Decision.

Project Decision options are labeled A/B/C in the Status path menu and in the ballot. These letters are review aids only; a decision is still recorded only after choosing a path and clicking Save Decision.

Each Project Decision card shows an After Save effect. This explains what the saved choice would unlock while keeping the boundary clear: saving a Project Decision records intent only and does not merge, delete, resolve, ignore, or rewrite CRM records.

The Next Action card in Dashboard, Status, and Cleanup points to the immediate next recommended step. When the next step is a Project Decision, it shows the A/B/C answer choices directly, Open Decision focuses the exact form, and Fill Recommended fills the suggested path without saving it.

The Recommended Path Simulation shows what would unlock if all recommended Project Decision paths were saved. It is hypothetical only; it does not save those choices.

Use Fill Recommended to pre-fill decision forms with the recommended path. This only changes the visible form fields; the decision is not recorded until Save Decision is clicked.

The Path field explains the currently selected option directly on the card, so you can compare a path before saving it.

When a path is selected, the form explains whether it is still a Pending draft, Deferred, or an active Decided path for previews.

When a Project Decision form has a staged change, it shows an unsaved-change note. Use Reset Staged to return one form to its last saved state, or Reset All Staged to clear every staged Project Decision at once. Save buttons stay disabled until the form has a valid change to record.

Use Save & Next Decision when working through the seven major choices in order. It saves only the current Project Decision, refreshes Status, and focuses the next pending decision card; deferred decisions stay parked until no pending decisions remain. It does not save other decisions, merge records, or run cleanup.

The Cleanup view also includes focused evidence panels for decisions. Duplicate People Evidence and Duplicate Leads Evidence filter into their guided review queues, show starting groups, link to `reports/duplicate_people_spot_check.md` and `reports/duplicate_leads_spot_check.md`, open the matching people/leads review worksheets, export worksheet CSVs, export the current evidence set, and can fill their recommended policy choices without saving them. Lead/Person Overlap Evidence filters to the 5 high-priority overlap groups and links to `reports/lead_person_overlap_spot_check.md` for the focused A/B/C identity-policy evidence. Duplicate Tag Evidence filters to the normalized tag batch candidates.

The Guided Review Queue in Cleanup is the working surface for group-level review after the related Project Decisions are saved. It summarizes the Overlaps, People, and Leads queues; shows how many groups still need review; shows Merge Later and Keep Separate progress; opens the next recommended group; links to the people/leads worksheets; and exports the review drafts. It does not merge, delete, resolve, or rewrite records.

Use `reports/duplicate_people_review_worksheet.md` when you want a focused working sheet for duplicate-person review. It lists all 60 duplicate-person groups with review order, draft keeper, conflict summary, blank-field suggestions, history signals, current group decision, and blank reviewer columns. The matching CSV export is `local_crm_duplicate_people_review_worksheet.csv`. Opening or exporting the worksheet does not save the duplicate people policy, save group decisions, merge records, resolve cleanup flags, or change Zendesk Sell.

Use `reports/duplicate_leads_review_worksheet.md` when you want a focused working sheet for duplicate-lead review. It lists all 36 duplicate-lead groups with review order, draft keeper, Application Profile context, conflict summary, history signals, current group decision, and blank reviewer columns. The matching CSV export is `local_crm_duplicate_leads_review_worksheet.csv`. Opening or exporting the worksheet does not save the duplicate leads policy, save group decisions, merge records, resolve cleanup flags, or change Zendesk Sell.

The Cleanup Starter Packet appears in Status and Cleanup. It is a read-only first batch for group-level review: lead/person overlaps first, then high-priority duplicate people and duplicate leads. Use `reports/cleanup_review_starter_packet.md` or its CSV when you want a printable/exportable starting list. Opening a starter group does not merge, delete, resolve, or rewrite records.

## Cleanup Execution Preview

Status and Cleanup show a Cleanup Execution Preview. This is a non-destructive gate check for future cleanup execution.

The preview stays locked until the required cleanup Project Decisions are saved and a backup is available. When a policy and group-level decisions make an action eligible, the preview shows counts and sample groups; it still does not merge, delete, resolve, or rewrite CRM records.

Use `reports/cleanup_execution_safety_plan.md` before any future cleanup execution work is enabled. It documents the hard safety gates: a fresh backup at execution time, dry-run counts, final confirmation, audit logging, restore path, no automatic person/lead/overlap merges, and preservation of notes, tasks, tags, archive links, linked resources, addresses, and custom fields.

## Backup

The local CRM creates SQLite backups in `backups/`.

Use `reports/backup_safety_ledger.md` when you want the printable backup inventory and safety posture. The matching CSV export is `local_crm_backup_safety_ledger.csv`, and both are included in the Complete Local CRM Package.

Backups are created:

- manually from the Cleanup view
- automatically before record edits
- automatically before address edits
- automatically before record creation
- automatically before note creation
- automatically before task creation
- automatically before task completion
- automatically before manual archive review saves
- automatically before manual archive linking
- automatically before review-flag resolution
- automatically before backup restore

Manual backup command:

```sh
python3 scripts/local_crm_maintenance.py backup --reason manual
```

Restore from the app:

- Open Cleanup.
- Use Restore beside the backup you want.
- A pre-restore backup is created first.

Restore from the command line:

```sh
python3 scripts/local_crm_maintenance.py restore backups/local_crm_YYYYMMDDTHHMMSSffffffZ_manual.sqlite
```

Before saving a batch of major Project Decisions or enabling any future cleanup execution, create a fresh manual backup from Cleanup or the maintenance script. The ledger should show that fresh backup as the latest row.

## Audit Log

Local changes are written to `audit_log` in `crm_database/local_crm.sqlite`.

The Activity view and each record detail timeline show those local changes in readable language. Cleanup flag actions appear as Cleanup Decision entries, including whether a flag was resolved, ignored, or reopened and any decision note that was entered.

The Activity view can filter by text, activity type, related record type, and date range. Save View stores the current Activity filters for reuse, and saved Activity views appear in the Activity saved-view menu and Dashboard shortcuts. Export CSV downloads the currently filtered activity timeline.

Use Reset View in Activity to clear timeline search, activity type, record type, date range, and saved view.

In record detail timelines, activity that belongs to a related record shows that target as a link, so a person or company timeline can jump directly into the connected deal or record behind the activity.

Record detail timelines also roll up note and task history from closely connected records: people show related deal activity, companies show activity from their people and deals, deals show activity from their linked contact and organization, and leads show activity from a matched person when one exists.

Tracked actions:

- `update_record`
- `add_note`
- `update_note`
- `add_task`
- `update_task`
- `complete_task`
- `save_archive_review`
- `link_archive_item`
- `resolve_flag`
- `update_address`
- `update_tags`
- `create_record`
- `restore_backup`

Locally-created notes can be edited from record detail panels. Imported Zendesk notes remain read-only historical records; add a new local note when you need to record a correction or follow-up context. Editing a local note creates a backup first and writes the change to Activity/audit.

## Follow Up

The Follow Up view shows:

- open tasks
- overdue tasks
- tasks due soon
- completed tasks
- all tasks

Use the Follow Up filter to search task text or the related record. Use the record-type menu to show all tasks, people, companies, leads, deals, or tasks with no linked record. Sort the task list by due date, task text, related record, status, created date, or updated date.

Use Save View in Follow Up to keep a reusable task queue, such as open people follow-ups or overdue deal tasks. Saved Follow Up views remember the status tab, filter text, record-type filter, sort field, and sort direction. They also appear in Dashboard saved-view shortcuts with live task counts.

Use Reset View in Follow Up to return to open tasks, clear filter text and record type, and restore due-date sorting.

Use Export CSV from Follow Up to download the current task queue. The CSV follows the active status tab, filter text, record-type filter, sort field, and sort direction.

Use `reports/followup_transition_plan.md` or `local_crm_followup_transition_plan.csv` when you want a printable/exportable checklist of imported open Zendesk reminders to review.

Task content and due dates can be edited from record detail panels or directly in the Follow Up table. Saving an edit creates a backup first and writes the change to Activity/audit.

Open tasks can be completed from the Follow Up view or from a record detail panel. Completed tasks can be reopened from the Completed or All task views, and from record detail panels. Completing or reopening a task creates a backup first and writes the change to Activity/audit.

Copy Local on an imported task creates a separate local CRM follow-up with no Zendesk task ID, creates a backup first, and writes a `copy_imported_task_to_local` audit entry. Use it only when an old imported reminder still needs current action in the local CRM.

## Tags

Tags are available from the sidebar Tags view.

The Tags view shows:

- all normalized tags
- how many local records use each tag
- how many Zendesk Sell tag definitions fed into each normalized tag
- which record types use the tag

Use the record-type filter to focus tags used by people, companies, leads, or deals. Click a tag name to see the records assigned to it in the detail panel; when a record-type filter is active, the detail panel keeps that same focus.

Use Save View in Tags to keep reusable tag slices, such as people-only tags or deal tags. Saved Tag views appear in the Tags saved-view menu and Dashboard shortcuts with live tag counts.

Use Reset View in Tags to clear the tag search, record-type filter, saved view, and pagination.

Export CSV from Tags downloads the current tag slice, including the active search and record-type filter.

The People, Companies, Leads, and Deals list views also include an All tags filter.

Record detail panels show a tag editor. Edit the comma-separated tag list and click Save to update that local record's tags. New tag names are normalized into the local tag list, a backup is created first, and the change is written to Activity/audit. This does not update Zendesk Sell.

## Custom Fields

The Custom Fields view shows migrated Zendesk custom field usage by record type.

Use the search and record-type filter to focus the summary on people, companies, leads, or deals before opening a field.

Use it to inspect:

- how many records use each field
- how many distinct values each field has
- sample values
- records carrying a selected field

Use Save View in Custom Fields to keep reusable review slices, such as lead-only application fields or people-only profile fields. Saved Custom Fields views appear in the Custom Fields saved-view menu and Dashboard shortcuts with live field counts.

Use Reset View in Custom Fields to clear the field search, record-type filter, saved view, and pagination.

Export Summary downloads the current custom-field summary slice, including the active search and record-type filter. Custom field values are also available as the full raw migrated value export from Custom Fields and the Exports view.

The custom field promotion report recommends which migrated fields are worth turning into first-class local CRM fields:

```sh
python3 scripts/analyze_custom_field_promotion.py
```

The current recommendation is to promote the high-coverage application fields into a shared Application Profile section, while keeping import-style contact fragments as review-only until individual records are checked.

The Application Profile evidence panel in Custom Fields summarizes the current editability recommendation and cleanup dependency. Use Open Decision to jump to the related Project Decision; use Fill Recommended to prefill the read-only-until-cleanup path without saving it; use Export Profiles to download the promoted Application Profile records.

Lead and person detail panels now show an Application Profile section for those high-priority fields. This is a read-only promoted view over the preserved custom field values; it does not rename, delete, or rewrite the original migrated values.

The People and Leads lists can filter by the profile fields that work well as segments:

- Desired Growth
- Time Frame
- Invest?

People and Leads list rows also show those profile values as compact chips, so segmented lists can be scanned without opening each record.

The Dashboard shows those same lead Application Segments. Clicking a segment opens the Leads list with that profile filter applied.

The Dashboard also shows Cleanup Review shortcuts for the open grouped cleanup queues. Clicking one opens Cleanup with that group type selected and sorted by priority.

## Linked Resources

Record detail panels show a Linked Resources section when migrated custom fields or notes contain URLs.

The sidebar Linked Resources view shows all extracted links in one place. Use it to:

- search link text, URLs, record names, and source fields
- filter by link type, such as Call Recording Folder or Profile Link
- filter by record type
- open the source CRM record
- open the external link
- save reusable link views, such as call-recording folders or profile links
- export the current filtered link list as CSV

The current Linked Resources export contains 27 extracted links:

- 13 call-recording Google Drive folder links from `CALL RECORDINGS:`
- 12 lead profile/web links from `Skills`
- 1 lead web link from `Success Is`
- 1 scheduling link from a person note

Saved Linked Resource views appear in the Linked Resources saved-view menu and Dashboard shortcuts with live link counts.

Use Reset View in Linked Resources to clear link search, link-type filter, record-type filter, saved view, and pagination.

The Linked Resources export downloads the same link index as CSV. These links remain connected to their original custom field or note source. The external files or pages are not copied into the local CRM unless a separate export/download process is run.

## Archive

The Archive view contains recovered optional Zendesk Sell data from the final read-only sweep:

- calls
- text messages
- downloaded documents
- orders
- lead conversions

Archive items can be searched, filtered by item type, filtered by linked or unlinked record type, filtered by date range, opened from linked CRM records, saved as reusable views, and exported as CSV. Saved Archive views appear in the Archive saved-view menu and Dashboard shortcuts with live item counts. The CSV export follows the active search, type, linkage, preset, and date filters. Downloaded PDFs open from the Archive view or from the right sidebar Archive section on linked records.

Use Reset View in Archive to clear archive search, item type, linked-record filter, date range, unlinked evidence preset, saved view, and pagination.

Some calls and text messages arrived from Zendesk without a linked contact/lead/deal ID. Those items remain in the Archive as unlinked records and are searchable by message text or phone number. They were not force-linked by phone unless a safe single CRM match was available.

The Unlinked Calls/Texts evidence panel in Archive summarizes the matching evidence behind the current recommendation. Use Show Evidence Set to focus the table and export on unlinked calls/texts only; use Open Decision to jump to the related Project Decision; use Fill Recommended to prefill the recommended archive-only path without saving it; use Open Report for the printable matching analysis.

## List Sorting

People, Companies, Leads, and Deals can be sorted from their list toolbar or by clicking sortable table headers.

Each list has its own useful sort fields. People and Companies include name, contact fields, visible status, customer/prospect statuses, and dates. Leads include status, organization, contact fields, and dates. Deals include stage, value, contact, close date, and dates.

## Status And Stage Filters

People and Companies can be filtered by customer status or prospect status. Leads can be filtered by lead status. Deals can be filtered by deal stage.

These filters work with search, tag filters, Application Profile filters, sorting, and pagination.

## List Source Filters

People, Companies, Leads, and Deals can be filtered by source: Imported from Zendesk, Local only, or Has local changes.

Use Imported from Zendesk to review original migrated records, Local only to see records created after the migration, and Has local changes to focus records that have local audit history.

Source filters work with search, tags, status/stage filters, Application Profile filters, owner filters, date filters, sorting, saved views, pagination, and CSV export.

## List Date Filters

People, Companies, Leads, and Deals can be filtered by created or updated date. Deals can also be filtered by estimated close date.

Date filters work with search, tags, status/stage filters, Application Profile filters, owner filters, sorting, saved views, pagination, and CSV export.

## List Exports

Use Export CSV from a People, Companies, Leads, or Deals list to download the current view.

The CSV follows the active search, tag filter, status/stage filter, source filter, date filter, Application Profile filter, sort field, and sort direction. People and Leads exports include Application Profile summary columns when those values exist.

List exports include source, Zendesk ID, and local-change count columns so imported records, locally-created records, and locally-edited records remain distinguishable outside the app.

## Saved List Views

Use Save View from a People, Companies, Leads, or Deals list to save the current search, filters, source filter, date range, sort field, and sort direction.

Saved views appear in the Saved views menu for that same list type and as Dashboard shortcuts, with live counts for matching records or tasks. Choosing one restores its saved controls. Delete removes the selected saved view only; it does not remove CRM records or tasks.

Use Reset View on People, Companies, Leads, or Deals to clear the active search, filters, saved-view selection, pagination, and custom sort back to the default updated-date list.

## Record Editing

The right sidebar starts each record detail with a compact snapshot for type, imported/local source, status or stage, owner, last updated date, local audit-change count, last local-change date, and available task, review-flag, tag, linked-resource, and archive counts.

The right sidebar Edit section can update core local CRM fields with backup and audit logging.

The right sidebar Contact Actions section appears when a record has email, phone, mobile, or website data. It provides Mail, Call, Open Website, and Copy controls without changing CRM data. Deal records can also show actions from their linked contact or organization.

People can edit contact fields, company assignment, owner assignment, and customer/prospect status. Companies can edit company fields and owner assignment. Leads can edit lead fields, status, and owner assignment.

Deals can edit name, linked contact ID, linked organization ID, stage, value, currency, hot flag, and estimated close date. Changing a deal stage also updates the linked pipeline behind the scenes.

Use New from People, Companies, Leads, or Deals to create a local record with the same core management fields. New people can be assigned to a company and owner, new companies and leads can be assigned to an owner, and new deals can be linked to a contact/organization, stage, value, currency, hot flag, and close date. Contact and organization fields accept IDs and show local suggestions.

If a linked owner, contact, company, or stage ID is invalid, the form stays open and shows the validation message in the right sidebar.

Address, tag, note, task, and cleanup-flag actions also show right-sidebar error messages if a save fails, and the action button is re-enabled.

These edits change only the local CRM database. They do not update Zendesk Sell.

## Addresses

The right sidebar shows address fields near the top of each record detail.

People, companies, and leads have editable address fields. Deals show read-only addresses from their linked contact or organization.

Address fields initially read from the original Zendesk snapshot fields:

- primary address
- billing address, when present
- shipping address, when present

When saved, address changes are stored as local CRM overrides. The original Zendesk snapshot remains unchanged.

The top search can find records by name, contact info, related company/contact/deal/stage/matched-person names, address, note text, task text, tag name, linked resource URL/source, and custom field values.

## Cleanup

The Cleanup view includes grouped review for:

- duplicate people by email
- duplicate leads by email
- lead/person email overlaps
- duplicate tag definitions

Click Review beside a group to inspect the related records in the right sidebar.

Use the grouped review search to find duplicate groups by email, record name, phone number, tag name, or tag resource type.

Use the priority filter, decision filter, and sort menu to work the highest-risk cleanup groups first or batch groups by saved decision.

Use the Guided lane filter to work from the merge policy plan inside the app. The lanes separate lead/person policy review, priority manual review, conflict-heavy review, shorter guided review, and duplicate tag batch candidates. Lane filtering and lane sorting do not merge, delete, or resolve records.

Use Export CSV from Grouped Review to download the current cleanup queue with the active type, status, search, priority, and sort settings.

Grouped records show review priority guidance and comparison signals to help decide what to inspect first: completeness score, field differences, Application Profile chips, tags, notes, tasks, deals, address blocks, custom fields, last update, newest badge, and most-complete badge. These are decision aids only, not automatic merge rules.

Cleanup groups can save a group-level decision: Needs Review, Merge Later, Keep Separate, Already Handled, or False Positive. These decisions appear in the grouped review list, group detail panel, grouped CSV export, and Activity. The grouped review list can filter or sort by decision, including groups with no decision yet. Saving a group decision does not merge, delete, resolve, or ignore any records.

Use the Review Remaining decision filter to show groups with no saved decision or a saved Needs Review decision. In a cleanup group detail panel, Save Decision records the current group decision. Save & Next records the decision, refreshes Review Remaining, and opens the next group in the same queue. This still does not merge, delete, resolve, or rewrite any records.

Duplicate people, duplicate leads, and lead/person overlap groups also show Merge Draft summaries in the group list and grouped CSV export. Detail panels show the fuller draft. This is review-only. It suggests a draft keeper, blank fields that could be filled from another record, conflicting filled fields that need manual review, and history signals such as notes, tasks, deals, tags, addresses, and custom fields that should be preserved if a future merge rule is chosen.

Use `reports/merge_policy_options.md` to compare cleanup approaches before enabling any future merge operation. The current recommendation is the Guided path: review priority and conflict-heavy groups first, work smaller duplicate reviews with draft keepers as decision aids, and treat duplicate tag definitions as the only batch-decision candidate.

Use `reports/lead_person_overlap_spot_check.md` before saving the Lead/person overlap policy. It summarizes the 5 high-priority overlap groups, person draft keepers, blank-field suggestions, manual review fields, history signals, and A/B/C choices. Use `reports/cleanup_merge_review_pack.md` for the broader duplicate people, duplicate leads, and overlap merge review context. Both reports are review-only and do not merge, delete, resolve, ignore, or rewrite any records.

Use `reports/duplicate_people_spot_check.md` and `reports/duplicate_leads_spot_check.md` before saving the matching duplicate merge policies. They summarize the queue totals, starting groups, review signals, A/B/C choices, and save boundary. Use `reports/duplicate_people_review_worksheet.md` and `reports/duplicate_leads_review_worksheet.md` after that when you want the duplicate groups in practical review sheets with blank reviewer columns. The broader `reports/cleanup_merge_review_pack.md` remains the full detail pack for conflicts, draft keepers, blank-fill suggestions, and history preservation.

Use `reports/duplicate_tag_spot_check.md` before saving the Duplicate Tag project decision. It now includes the A/B/C decision prompt, what each path means, the backup/audit save boundary, each duplicate tag alias, assignment count, assigned record types, and sample assigned records. This report is review-only; it does not merge, delete, resolve, ignore, or rewrite any records.

The Duplicate Tag evidence panel in Cleanup summarizes the tag batch candidate. Use Show Tag Batch Candidates to focus grouped review on the duplicate-tag lane; use Open Decision to jump to the related Project Decision; use Fill Recommended to prefill the normalized-tag-handled path without saving it; use Export Evidence for the filtered cleanup queue.

Use `reports/unlinked_archive_matching_candidates.md` before saving the Unlinked Calls/Texts project decision. It reviews the 472 unlinked call/text archive items against CRM phone numbers. The current result is 0 exact CRM phone candidates, which supports keeping these items archive-only for now. Use `reports/archive_review_worklist.md` for the day-to-day queue after that evidence review.

Use `reports/archive_association_audit.md` when checking overall archive association progress. It shows that documents, orders, and lead conversions are linked through clear Zendesk-supplied evidence, while the remaining communication records need review rather than automatic linking.

Use `reports/application_profile_editability_review.md` before saving the Application Profile project decision. It recommends keeping Application Profile read-only until cleanup, then considering a hybrid model where Desired Growth, Time Frame, and Invest? become editable operational segment fields while application identifiers, timestamps, and long-form intake answers remain preserved history.

The Cleanup view has Open, Ignored, and Resolved tabs. Resolve means the item was reviewed and accepted as handled. Ignore means the item is a false positive or not useful right now. Reopen moves ignored or resolved items back into the Open queue.

Resolve, Ignore, and Reopen actions ask for an optional decision note. Saved notes appear with the review flag and are preserved in exports and the audit trail.

Resolving, ignoring, or reopening cleanup flags does not merge or delete records.

## Final Zendesk Sell Sweep

Zendesk Sell is now treated as frozen. No new local CRM work depends on ongoing Zendesk updates.

The final read-only optional sweep has been completed and imported into the Archive. The latest snapshot is `snapshot_20260605T042056Z`.

If a fresh token is available and the sweep ever needs to be rerun:

```sh
python3 scripts/export_zendesk_sell.py --include-extended --download-documents
python3 scripts/build_staging_database.py
python3 scripts/import_zendesk_optional_archive.py
```

This checks less common Sell categories such as calls, visits, text messages, documents, products, orders, sequences, nested deal contacts, order line items, and related metadata. If Zendesk document attachments exist, the document files are saved under `document_files/` inside the new snapshot folder. Optional endpoint errors are recorded in the snapshot instead of blocking the core migration.

The current migrated data also includes 13 `CALL RECORDINGS:` custom field links to Google Drive folders. Those links are preserved as Linked Resources; the external Drive files are separate from the Zendesk document downloads.

## Visual Design Pipeline

The native Apple-style redesign is intentionally deferred until daily CRM use reveals the settled workflow. The visual direction remains:

- quieter app chrome
- simpler navigation
- calmer typography and spacing
- more elegant detail panels
- powerful filters/search preserved under a cleaner surface

This is intentionally parked as a later design pass so the visual system can wrap the real working rhythm instead of chasing moving requirements.

## Exports

The Exports view can download a Complete Local CRM Package as one zip file. The package includes the current SQLite database, core CSV exports, key reports, and project docs. Use it when you want a portable snapshot of the local CRM without downloading every CSV separately.

The individual CSV exports and the complete package include `local_crm_followup_transition_plan.csv`, `local_crm_daily_operating_guide.csv`, `local_crm_archive_review_worklist.csv`, `local_crm_archive_review_triage.csv`, `local_crm_archive_association_audit.csv`, `local_crm_backup_safety_ledger.csv`, `local_crm_migration_completion_audit.csv`, `local_crm_database_map.csv`, `local_crm_zendesk_independence_checklist.csv`, `local_crm_remote_admin_access_plan.csv`, `local_crm_remote_admin_permissions_matrix.csv`, `local_crm_remote_admin_implementation_blueprint.csv`, `local_crm_remote_admin_rollout_board.csv`, `local_crm_remote_hosting_decision_packet.csv`, `local_crm_remote_managed_cloud_provider_shortlist.csv`, `local_crm_remote_staging_pricing_preflight.csv`, `local_crm_remote_staging_setup_runbook.csv`, `local_crm_remote_staging_deployment_spec.csv`, `local_crm_remote_staging_validation_matrix.csv`, `local_crm_remote_admin_pilot_onboarding_plan.csv`, `local_crm_remote_production_cutover_checklist.csv`, `local_crm_hosted_database_migration_readiness.csv`, `local_crm_hosted_schema_draft.csv`, `local_crm_hosted_data_load_plan.csv`, `local_crm_lead_person_overlap_spot_check.csv`, `local_crm_duplicate_people_spot_check.csv`, `local_crm_duplicate_people_review_worksheet.csv`, `local_crm_duplicate_leads_spot_check.csv`, `local_crm_duplicate_leads_review_worksheet.csv`, `local_crm_decision_prep_packet.csv`, `local_crm_project_decision_ballot.csv`, `local_crm_project_decision_option_matrix.csv`, `local_crm_design_pipeline.csv`, `local_crm_cleanup_starter_packet.csv`, plus the matching reports for the follow-up transition plan, daily operating guide, archive review worklist, archive review triage, archive association audit, backup safety ledger, migration completion audit, local database map, Zendesk independence checklist, remote admin access plan, remote admin permissions matrix, remote admin implementation blueprint, remote admin rollout board, remote hosting decision packet, remote managed cloud provider shortlist, remote staging pricing preflight, remote staging setup runbook, remote staging deployment spec, remote staging validation matrix, remote admin pilot onboarding plan, remote production cutover checklist, hosted database migration readiness, hosted database schema draft, hosted data load plan, Lead/person overlap spot check, duplicate people/leads spot checks, duplicate people/leads review worksheets, decision prep packet, project decision ballot, option matrix, Apple-style redesign pipeline, and cleanup starter packet. The complete package also includes `reports/hosted_database_schema_draft.sql` for staging review.

The Exports view also has a Downloaded Document Files package. Use it when you want the recovered Zendesk document files as a separate zip; it includes a document manifest so the files can be matched back to Archive records.

The Exports view also downloads local CRM data as individual CSV files, including addresses and Application Profiles. It includes Cleanup Merge Drafts, a detailed review worksheet for open duplicate people, duplicate leads, and lead/person overlap groups. Tags can also be exported from the Tags view.

## Verification

Verify migration counts:

```sh
python3 scripts/verify_local_crm.py
```

Verify write operations against a temporary database copy:

```sh
PYTHONPATH=. python3 scripts/verify_app_operations.py
```
