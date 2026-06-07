# Project Status

## Completed

- Created local project folder in Downloads.
- Exported full Zendesk Sell data snapshot.
- Built local SQLite staging database.
- Generated migration analysis reports.
- Built first read-only local CRM interface.
- Created final normalized local CRM database.
- Wrote migration rules and verification reports.
- Updated the local CRM interface to read from the final CRM database.
- Added Status view for imported counts, a readiness checklist, snapshot metadata, cleanup progress, linked-resource counts, backups, reports, and final Zendesk optional sweep state.
- Added Project Decisions to Status for tracking major merge, archive, Application Profile, and visual redesign choices.
- Verified dashboard, lists, detail methods, cleanup API, and search methods against the final CRM database.
- Added local database backups and audit logging.
- Added editable detail fields for people, companies, leads, and deals.
- Added owner assignment and relationship editing for local records: people can change company/owner, companies and leads can change owner, and deals can change contact, organization, stage, value, hot flag, and close date with backup and audit logging.
- Added inline create/edit validation messages so invalid linked-record IDs or other save errors are shown without losing the form.
- Added inline failure handling for right-sidebar address, tag, note, task, and cleanup-flag actions.
- Added local note creation.
- Added local note editing for locally-created notes, while keeping imported Zendesk notes read-only historical records.
- Added local task creation and task completion.
- Added local task editing for task content and due dates from record detail panels and the Follow Up table, with backup and audit logging.
- Added completed-task reopening from Follow Up and record detail panels, with backup and audit logging.
- Added create-new flows for people, companies, leads, and deals, including owner assignment, stage selection, relationship suggestions, and hot-deal support where applicable.
- Added review-flag resolution.
- Added a Cleanup review queue and in-app Backup button.
- Added backup restore from the Cleanup view and maintenance script.
- Added Follow Up view for open, overdue, due soon, completed, and all tasks, with task/record text filtering, related-record-type filtering, sorting, reusable saved views, and filtered CSV export.
- Added imported/local task source labels and filters to Follow Up so historical Zendesk tasks can be separated from local CRM follow-ups.
- Added a Follow Up Transition Plan in-app, exports, and reports so imported Zendesk task reminders can be reviewed separately before creating current local CRM follow-ups, including an explicit Copy Local action for still-relevant reminders.
- Added Reset View controls to Follow Up, Activity, Tags, Custom Fields, Linked Resources, and Archive so dense saved/filter views can be cleared back to their default state.
- Added dashboard task signals for open, overdue, and due soon tasks.
- Added Activity view for recent notes, tasks, completed tasks, and local changes.
- Activity view now supports text/type/record/date filtering, reusable saved views, Dashboard shortcuts, and filtered CSV export.
- Activity now labels cleanup flag changes as cleanup decisions and shows any decision note.
- Record detail Activity entries now link to related records when the timeline item points at a connected deal, person, company, or lead.
- Record detail Activity now rolls up related note/task history from connected people, companies, deals, or matched person records.
- Added compact right-sidebar record snapshots for type, status/stage, owner, update date, and available task, flag, tag, link, and archive counts.
- Added record provenance to right-sidebar snapshots so imported-vs-local source, local audit-change counts, and last local-change dates are visible while working records.
- Added right-sidebar contact actions for email, phone, mobile, and website fields, including linked contact/organization actions on deals.
- Added task text to top search so follow-up wording can locate the related record.
- Added tag assignment matches to top search so tag names can locate assigned records.
- Added linked-resource matches to top search so migrated URLs and link sources can locate assigned records.
- Added Exports view for downloading local CRM CSVs.
- Added Tags view with search, record-type filtering, assignment counts, record type summaries, record click-through, reusable saved views, Dashboard shortcuts, and filtered tag export.
- Added local tag editing in record detail panels for people, companies, leads, and deals, with backup and audit logging.
- Added tag filters to People, Companies, Leads, and Deals list views.
- Added status/stage filters to People, Companies, Leads, and Deals list views.
- Added date-range filters to People, Companies, Leads, and Deals list views, including deal close-date filtering.
- Added sort controls and clickable sort headers to People, Companies, Leads, and Deals list views.
- Added filtered/sorted CSV exports from People, Companies, Leads, and Deals list views.
- Added reusable saved views for People, Companies, Leads, and Deals list filters/sorts with live record counts.
- Added Reset View for People, Companies, Leads, and Deals so complex filtered/saved views can be cleared back to the default updated-date list.
- Added Dashboard shortcuts for recent saved list views with live record counts.
- Added double-click local CRM starter with automatic fallback to the next open port.
- Added Custom Fields view for usage review, sample values, related records, record-type filtering, reusable saved views, Dashboard shortcuts, and filtered summary export.
- Added Linked Resources view for searching, filtering, opening, reusable saved views, Dashboard shortcuts, and exporting URL-bearing migrated custom fields and notes.
- Added a custom field promotion recommendation report and CSV candidate list.
- Added Application Profile decision evidence in Custom Fields, including live profile coverage, cleanup-dependency counts, profile export, report link, and direct handoff to the related Project Decision.
- Added an Application Profile detail section for leads and people using the high-priority application custom fields, while preserving original custom field values.
- Added Application Profile filters to People and Leads lists for Desired Growth, Time Frame, and Invest?.
- Added compact Application Profile chips to People and Leads list rows.
- Added Dashboard Application Segments for leads, with click-through into filtered lead lists.
- Added Dashboard Cleanup Review summary with click-through into open grouped cleanup queues.
- Added Application Profiles CSV export.
- Added right-sidebar address fields near the top of record details, with editable local addresses for people, companies, and leads plus read-only linked addresses for deals.
- Added Linked Resources to record detail panels and Exports for URL-bearing custom fields and notes, including call-recording Drive folders, profile links, and scheduling links.
- Ran the final read-only Zendesk Sell optional sweep and captured optional CRM history.
- Imported optional Zendesk data into a local Archive layer with calls, text messages, downloaded documents, orders, and lead conversions.
- Added Archive view, Archive CSV export, archive Status counts, archive Activity entries, and right-sidebar Archive sections for linked records.
- Archive view now supports date-range filtering, reusable saved views, Dashboard shortcuts, and matching CSV export across recovered calls, texts, documents, orders, and lead conversions.
- Added Archive decision evidence for unlinked calls/texts, including live matching counts, recommendation, report link, one-click evidence filtering/export, and direct handoff to the related Project Decision.
- Added Archive Association Coverage in Status and Archive so linked/unlinked history, 203/203 downloaded document coverage, preserved recording URLs, and the zero exact-phone-candidate finding are visible in-app.
- Added right-sidebar Archive item inspection and explicit manual archive linking so unlinked calls, texts, or other items can be attached to a selected local person, company, lead, or deal only after a backup and audit entry.
- Added Manual Archive Review Queue tracking for unlinked calls/texts, including Unreviewed, Needs Lookup, Ready to Link, and Archive-only Reviewed statuses, top-number batch shortcuts, sidebar review notes, Save & Next queue flow, filtered exports, backups, and audit entries.
- Added Archive Review Worklist report and CSV so the unlinked calls/texts queue can be printed, exported, packaged, and worked separately from already-linked document files.
- Added Archive Review Triage report, CSV, export package entry, and Archive panel so the unlinked calls/texts queue is grouped into likely archive-only, needs-lookup, ready-to-link candidate, and manual-review lanes without saving review status or linking records.
- Added Archive triage lane filtering and saved-view support so likely archive-only, needs-lookup, ready-to-link candidate, and manual-review call/text batches can be reviewed from the Archive list without saving review status or linking records.
- Added Archive Association Audit report and CSV to document linked documents, linked orders/conversions, preserved call recording URLs, and the lack of reliable resource IDs or exact phone candidates for the remaining unlinked calls/texts.
- Added owner names, owner sorting, owner filters, owner-aware saved list views, owner-aware CSV exports, and owner detail sections for people, companies, and leads.
- Added cleanup decision-readiness report and CSV to organize pending merge/cleanup policy decisions.
- Added merge policy options report and CSV to compare conservative, guided, and aggressive cleanup paths without changing records.
- Added in-app Guided cleanup policy summary, cleanup lane badges, lane filtering, lane sorting, and lane-aware cleanup exports.
- Added saveable project-level decisions with backup creation and Activity/audit logging so major choices are tracked separately from cleanup group decisions.
- Added data-backed Project Decision impact summaries for cleanup groups, Application Profile coverage, archive matching, and redesign timing.
- Added Apple-style redesign pipeline report and CSV so the later native-app visual pass is tracked with gates, phases, and must-preserve CRM behaviors before visual changes begin.
- Added Project Decision brief report and CSV for printable/exportable decision, impact, gate, preview-action, backup-safety, and restore-path status.
- Added recommended-path simulation in Status, Cleanup, Project Decisions CSV, and the decision brief without saving choices or changing records.
- Added Project Decision after-save effect panels that show what a saved decision unlocks while keeping the no-merge/no-rewrite boundary visible.
- Added live Project Decision path descriptions so selected options explain themselves before they are saved.
- Added Project Decision status guidance so selected paths are clearly marked as Pending drafts, Deferred, or active Decided paths for previews.
- Added Save & Next Decision in Project Decisions so the seven major choices can be worked in sequence while still requiring explicit saves.
- Added Project Decision staged-change indicators, per-card and all-card reset-staged controls, and disabled save buttons so filled recommendations are clearly unsaved until explicitly recorded.
- Added non-destructive Cleanup Execution Preview in Status and Cleanup, gated by saved project decisions and backups.
- Added a read-only Decision Prep Packet in Status, exports, and reports so remaining major decisions can be reviewed with recommended paths, impact facts, evidence links, CSV export, and a printable summary before any choices are saved.
- Added Project Decision Ballot report and CSV so the seven major decisions can be reviewed as a printable worksheet with options, recommended paths, evidence links, and blank choice/note fields before saving anything.
- Added cleanup execution safety plan report and CSV to document backup, restore, final-confirmation, audit, and no-auto-merge guardrails before any future mutating cleanup workflow is enabled.
- Added Backup Safety Ledger report and CSV to document available backup files, restore methods, export-package readiness, and the app actions that create pre-change backups.
- Added Migration Completion Audit report and CSV to show end-to-end migration status, completed evidence, remaining gates, and why the local CRM is operational but not fully closed.
- Added Local CRM Database Map report and CSV to document SQLite tables, row counts, columns, relationships, CSV exports, report inventory, and the read-only handoff boundary.
- Added Zendesk Independence Checklist report and CSV to document local-only operating readiness, preserved artifacts, Zendesk access boundaries, and what to download before any future Zendesk decommission decision.
- Added Remote Admin Access Plan report and CSV to document the staged path from local CRM to shared remote CRM access, including hosting posture options, managed database migration, private file storage, roles, security controls, verification, and cutover gates.
- Added Remote Admin Permissions Matrix report and CSV to map Owner, Admin, Staff, Read-only, and temporary Migration Operator roles against actual CRM actions, backups, audit needs, implementation gaps, and rollout gates before any remote users are invited.
- Added Remote Admin Implementation Blueprint report and CSV to convert the remote-admin plan into build workstreams, remote-only tables, endpoint changes, implementation steps, verification gates, and explicit open decisions before hosting is provisioned.
- Added Remote Admin Rollout Board report and CSV to convert the remote-access plan into a sequenced task board with blockers, dependencies, proof gates, decision prompts, staging validation, and cutover milestones before hosting is provisioned.
- Added Remote Hosting Decision Packet report and CSV to focus the hosting posture decision with A/B/C options, scoring criteria, minimum requirements, owner questions, and next steps before any provider is chosen.
- Added Remote Managed Cloud Provider Shortlist report and CSV to compare current official managed-cloud provider options for app hosting, hosted Postgres, private file storage, auth, backups, staging, and owner questions before any provider is chosen.
- Added Remote Staging Pricing Preflight report and CSV to translate DigitalOcean/Railway finalist options into official-source pricing components, staging estimate profiles, setup gates, cost controls, and owner questions before any provider account or payment action.
- Added Remote Staging Setup Runbook report and CSV to define the DigitalOcean/Railway staging paths, setup phases, provider-specific setup tasks, environment variables, validation gates, and approval gates before any provider account or data upload.
- Added Remote Staging Deployment Spec report and CSV to translate the setup runbook into deployment targets, app service settings, configuration variables, package inputs, implementation gaps, smoke tests, owner decisions, and next steps before any hosting is provisioned.
- Added a server-side `REMOTE_WRITE_LOCK=true` guard so hosted staging can block browser/API POST writes during read-only validation while local default use remains unlocked.
- Added `/health` and `/api/health` plus a browser environment label so hosted staging can run minimal app/database/report checks and clearly show `CRM_ENV` without exposing client counts.
- Added a server-side `EXPORT_PACKAGE_ENABLED=false` guard so hosted staging can block complete CRM/document package downloads while ordinary CSV/report exports remain available.
- Added a server-side `DOCUMENT_FILE_ACCESS_ENABLED=false` guard so hosted staging can block direct recovered-document file serving until private storage and signed/proxied access are validated.
- Added Remote Staging Validation Matrix report and CSV to give the future hosted staging load expected counts, pass/fail checks, evidence fields, blocker rules, and pilot/cutover gates before any admin invite.
- Added Remote Admin Pilot Onboarding Plan report and CSV to define one-admin staging pilot prerequisites, onboarding steps, workflows, permission probes, support watch items, blocker rules, and signoff gates before any admin invite.
- Added Remote Production Cutover Checklist report and CSV to define the local write freeze, final packages, production load, repeated validation, admin handoff, rollback triggers, first-week monitoring, communication plan, and signoff gates before the hosted CRM becomes source of truth.
- Added Hosted Database Migration Readiness report and CSV to inspect the live SQLite schema for remote promotion, including table counts, hosted/Postgres type translation, foreign keys, JSON/timestamp/file-path handling, migration requirements, and remote rollout risks.
- Added Hosted Database Schema Draft report, CSV, and SQL draft to turn the local SQLite schema and remote-only admin tables into a managed-Postgres-style staging review artifact without creating a remote database.
- Added Hosted Data Load Plan report and CSV to sequence the hosted staging load by phase, table row counts, remote seed tables, private file migration, validation checks, and cutover gates without moving data.
- Added CHILLCRM Supabase storage migration tooling and manifest report so the 203 recovered Zendesk document files have byte-verified, deterministic private Supabase Storage keys before upload.
- Updated the hosted deployment spec for the selected CHILLCRM Supabase path: database rows are staged, the health route can probe hosted Postgres schema reachability through `DATABASE_URL`, and a guarded `CHILLCRM_DATABASE_ADAPTER=postgres` app adapter beta is prepared for hosted tests while private file upload, auth, and hosted app gates remain explicit.
- Added Hosted Postgres Adapter Smoke report and script so the guarded Supabase/Postgres adapter has a dry-run proof now and a repeatable hosted smoke path for future list, detail, task, activity, archive, tag, custom-field, and linked-resource checks.
- Added hosted auth/session beta scaffolding: opt-in `CHILLCRM_AUTH_REQUIRED=true`, bootstrap owner/admin login, signed HttpOnly session cookies, logout, protected CRM/report routes, app user password hash fields in the hosted schema draft, and a local password-hash generator for provider secrets.
- Verified the local browser mode after hosted-adapter/auth changes: Dashboard loads on the local SQLite CRM, auth stays hidden in local mode, the app reports Ready, and no local browser errors were found.
- Verified the hosted-login beta against a temporary database copy: public auth status and health worked, signed-out CRM data routes returned 401, bootstrap owner/admin login loaded the dashboard summary, logout cleared the session, and the visible sign-in overlay behaved correctly.
- Prepared and deployed a Vercel staging package: `api/index.py` exposes the CRM as a Vercel Python Function, `vercel.json` uses an explicit `@vercel/python` build with catch-all routing, hosted dependencies are pinned, local-only data is excluded from the bundle, and `docs/vercel_staging_setup.md` plus `config/chillcrm_vercel.env.example` document the staging setup.
- Added Hosted App Deployment Package Verification report and CSV; the local serverless-adapter smoke passed for `/`, `/static/app.js`, and `/api/health`.
- Hardened the hosted Postgres adapter for Supabase with JSONB normalization, SQLite-to-Postgres aggregate/helper translations, a hosted statement timeout, a lighter hosted Dashboard summary, and set-based linked-resource collection.
- Ran the formal hosted Supabase adapter smoke in staging mode: 13 hosted read-path checks passed with 0 failures across health, summary, people/companies/leads/deals list and detail, tasks, activity, archive, tags, custom fields, linked resources, and runtime locks.
- Prepared hosted document download signing: when the app is running against hosted Postgres, `/api/archive_file` can redirect private document requests through short-lived Supabase Storage signed URLs from `crm.remote_file_objects` while local disk serving remains unchanged.
- Added Remote File Access Verification report and CSV; the signing helper passed against a local fake Storage endpoint without using real secrets, public file links, or uploaded document binaries.
- Applied the Supabase auth schema upgrade for hosted `app_users` password/session fields without reloading CRM data.
- Deployed CHILLCRM to Vercel staging behind Vercel Authentication and CRM auth; the locked hosted app smoke passed 9 checks with 0 failures across health, signed-out denial, owner login, summary counts, export lock, document-file lock, write lock, and logout.
- Uploaded all 203 recovered Zendesk document files, totaling 382,373,054 bytes, into the private Supabase Storage bucket and validated 203 matching `crm.remote_file_objects` rows linked back to archive document records.
- Redeployed CHILLCRM to Vercel staging with owner/admin signed document access enabled; hosted smoke passed 9 checks with 0 failures across health, signed-out denial, owner login, summary counts, export lock, signed Supabase document redirect, write lock, and logout.
- Added owner-only app-user lifecycle API foundations for remote admin rollout: list users/roles, save users and role assignments, deactivate/reactivate users, and set/reset passwords without shared admin credentials.
- Added actor-aware audit fields to `audit_log` and verified lifecycle plus permission-denial audit rows capture actor email, role snapshot, and permission action; full CRM-write actor attribution still remains behind the write-unlock gate.
- Applied the hosted schema patch for actor-aware audit fields and redeployed Vercel staging; expanded hosted smoke passed 12 checks with 0 failures across auth, counts, owner-only app-user lifecycle, read-only denial, deactivated-user login denial, export lock, signed document redirect, write lock, and logout.
- Added the owner-only Users UI for remote admin rollout: owners can create app users, assign roles, edit names/roles, deactivate/reactivate users, reset passwords, and copy one-time temporary passwords from the staged admin surface.
- Redeployed the owner Users UI to Vercel staging at `https://chillcrm-rckbjcw03-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; that deployment was ready, with full hosted login/role smoke deferred pending owner-password recovery and Vercel protection bypass automation access.
- Added full local role-matrix verification for Owner/Admin/Staff/Read-only/Migration Operator action permissions, plus local actor-aware CRM-write audit verification for approved record, tag, note, task, and cleanup-flag writes.
- Redeployed the actor-audit and upgraded role-smoke-ready bundle to Vercel staging at `https://chillcrm-beugorwj6-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; full hosted login/role smoke against the newest ready URL now needs Vercel protection bypass automation access.
- Redeployed the synced docs/report bundle to Vercel staging while preserving existing Vercel environment variables; this was an interim ready deployment, later superseded after hosted role smoke automation access was established.
- Redeployed the Supabase backup-readiness report bundle to Vercel staging at `https://chillcrm-nyyq0hefr-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected.
- Redeployed the owner-first rollout/report bundle to Vercel staging at `https://chillcrm-5zbvy5bwl-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected.
- Redeployed the consolidated production-readiness report bundle to Vercel staging at `https://chillcrm-cu0wi7pen-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected, and Vercel deployment diagnostics match the latest ready deployment.
- Redeployed the monitoring-explicit production-readiness bundle to Vercel staging at `https://chillcrm-kk8lz2e9g-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected, and Vercel deployment diagnostics match the latest ready deployment.
- Redeployed the remote monitoring-readiness bundle to Vercel staging at `https://chillcrm-g0dm2dwyh-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected, and Vercel deployment diagnostics match the latest ready deployment.
- Redeployed the pending signoff/rehearsal workflow bundle to Vercel staging at `https://chillcrm-fy0lv54ec-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public `/api/health` returns 401 behind Vercel Authentication as expected, and Vercel deployment diagnostics match the latest ready deployment.
- Redeployed the rollback-readiness production gate bundle to Vercel staging while preserving existing Vercel environment variables; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, and Vercel deployment diagnostics matched that ready deployment.
- Redeployed the hosted backup-status fix bundle to Vercel staging; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, newest hosted smoke passed 13 checks with 0 failures, and a later rollout-board sync deployment superseded it.
- Redeployed the rollout-board sync bundle to Vercel staging; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, newest hosted smoke passed 13 checks with 0 failures, and a later final source/report sync deployment superseded it.
- Redeployed the final source/report sync bundle to Vercel staging at `https://chillcrm-953nbyec9-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, newest hosted smoke passed 13 checks with 0 failures, and that deployment was later superseded by the backup-evidence packet deployment.
- Redeployed the Supabase backup evidence packet and source-sync bundle to Vercel staging at `https://chillcrm-96mw0n0k6-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, newest hosted smoke passed 13 checks with 0 failures, and that deployment was later superseded by the owner password-rotation deployment.
- Added authenticated self-service password rotation for signed-in app users while keeping public password reset disabled for the private-company CRM; owner/admin recovery remains available through Users and the private operator reset script.
- Redeployed the owner password-rotation bundle to Vercel staging at `https://chillcrm-fb0xityez-kevin-nations-projects.vercel.app` while preserving existing Vercel environment variables; public app/API/report/static probes returned 401 behind Vercel Authentication as expected, newest hosted smoke passed 14 checks with 0 failures including temporary-user password rotation, and that deployment was later superseded by the Production Gates Status deployment.
- Clarified the auth posture as a private company CRM, not a public multi-user product: no public signup or public password-reset flow, with owner/admin access managed internally.
- Added `scripts/reset_app_user_password.py` as a private owner/admin recovery path, reset the hosted `kevinnations@gmail.com` owner/admin password, and verified that login directly against the Supabase auth table without writing the temporary password to reports.
- Added the in-app Production Gates Status panel, redeployed it to Vercel staging at `https://chillcrm-njhqe1oqn-kevin-nations-projects.vercel.app`, refreshed the hosted owner/admin password privately for verification, and confirmed public protection, deployment diagnostics, and 14-check hosted smoke all pass against the newest ready deployment.
- Added the controlled hosted owner-recovery flow and Owner Intake link, redeployed to Vercel staging at `https://chillcrm-ngny5xqvf-kevin-nations-projects.vercel.app` with the non-secret recovery switch enabled, and confirmed public protection, deployment diagnostics, and 15-check hosted smoke all pass against the newest ready deployment.
- Added `scripts/verify_backup_restore_drill.py` and `reports/backup_restore_drill.md/.csv`; the disposable local restore drill passed 8 checks with 0 failures while leaving the live CRM database in place.
- Added `scripts/verify_supabase_backup_readiness.py` and `reports/supabase_backup_readiness.md/.csv` to verify Supabase provider backups through either the official Management API list-backups endpoint or owner-confirmed Dashboard evidence; current status is input-required until backup/PITR visibility and restore/rollback proof are recorded.
- Added `scripts/prepare_supabase_backup_evidence_packet.py` and `reports/supabase_backup_evidence_packet.md/.csv` as the non-secret owner/operator packet for capturing Supabase Dashboard backup/PITR facts without sharing service keys, database passwords, JWTs, or connection strings.
- Added `scripts/verify_remote_monitoring_readiness.py` and `reports/remote_monitoring_readiness.md/.csv` to verify deployment/protection, health endpoints, newest hosted smoke freshness, Supabase backup monitoring, hosted write-audit monitoring, provider log/error owner, and owner feedback cadence before source-of-truth cutover.
- Added pending signoff/rehearsal recorders and reports for the remaining owner-driven gates: `scripts/record_remote_monitoring_signoff.py`, `scripts/prepare_hosted_write_audit_rehearsal.py`, `scripts/record_owner_shakedown_signoff.py`, plus `reports/remote_monitoring_signoff.md`, `reports/hosted_write_unlock_audit_rehearsal.md`, and `reports/owner_shakedown_signoff.md`; these reports stay blocked until explicit approval or actual rehearsal evidence is recorded.
- Added `scripts/run_safe_production_gate_checks.py` and `reports/safe_production_gate_runner.md/.csv` as a guided safe runner for hosted smoke, Supabase backup visibility, and report refreshes. It stores no secrets, writes no CRM records, keeps remote writes locked, and leaves write-audit, monitoring, shakedown, restore, and cutover approvals as separate owner steps.
- Added `scripts/verify_vercel_environment_readiness.py` and `reports/vercel_environment_readiness.md/.csv` to verify Vercel environment variable names and production targets without storing values or changing provider settings.
- Added `scripts/verify_vercel_public_protection.py` and `reports/vercel_public_protection.md/.csv` to verify unauthenticated public requests cannot reach the hosted app shell, API, reports, or static bundle while Vercel Authentication is enabled.
- Added `scripts/prepare_remaining_production_gate_packet.py` and `reports/remaining_production_gates_packet.md/.csv` as the single non-secret operator packet for remaining production inputs, safe command order, proof reports, and safety boundaries.
- Added `scripts/validate_owner_gate_reply.py` and `reports/owner_gate_reply_validation.md/.csv` as the non-secret validator for owner intake answers. It currently records `input_required_owner_gate_reply` with 0/8 fields supplied, rejects token/JWT/database-URL-like values, and will turn safe owner facts into candidate gate commands without executing approvals.
- Added `scripts/verify_cutover_rollback_package_readiness.py` and `reports/cutover_rollback_package_readiness.md/.csv`; the local rollback package proof passed 14 checks with 0 failures across local database health, existing backups, prior restore-drill evidence, complete export package readiness, 203-file document package readiness, and Supabase storage manifest integrity.
- Added `scripts/verify_remaining_gate_guardrails.py` and `reports/remaining_gate_guardrails.md/.csv`; the source-level guardrail audit passed 11 checks with 0 failures, proving approval-sensitive owner recovery, write-audit, Supabase backup, monitoring, shakedown, and source-of-truth scripts refuse unsafe paths without required approvals/evidence.
- Added `scripts/verify_hosted_redeploy_preflight.py` and `reports/hosted_redeploy_preflight.md/.csv`; the redeploy preflight passed 9 checks with 0 failures and confirms the current local hosted runtime is ready for secret-prompted Vercel redeploy, hosted smoke, and safe gate refresh.
- Added `scripts/prepare_owner_approved_wave_packet.py` and `reports/owner_approved_wave_packet.md/.csv` as the non-secret next-wave packet for the owner access confirmation, recovery-disable command, redeploy/freshness fallback sequence, proof reports, and remaining separate approvals.
- Added `scripts/verify_secret_handling_boundaries.py` and `reports/secret_handling_boundaries.md/.csv`; it scans the curated app/source/docs/reports/config surface and verifies guided runners keep secrets in hidden prompts or one-shot environment values. Current result: 309 scanned files, 17 boundary checks, 0 findings, production gate pass.
- Added `scripts/verify_remaining_gate_execution_readiness.py` and `reports/remaining_gate_execution_readiness.md/.csv`; it verifies all 8 remaining blocking gates have matching needed inputs, proof reports, safe command coverage, private secret handling, and final cutover/write-audit guardrails. Current result: 9 checks passed, 0 failed, production gate pass.
- Added `scripts/verify_private_execution_inputs.py` and `reports/private_execution_inputs.md/.csv`; it maps the remaining Vercel token, owner password, Supabase database URL, deploy-time database URL, bypass, backup-token, Dashboard-evidence, and owner-approval inputs without storing secret values or calling providers.
- Added `scripts/run_owner_confirmed_production_wave.py` and `reports/owner_confirmed_production_wave.md/.csv` as the guarded next-wave coordinator for owner-confirmed recovery disable/redeploy, Supabase staging refresh, and Supabase backup API visibility. Dry-run mode is report-only; execution mode uses explicit flags and hidden prompts, and still refuses write-audit, monitoring, shakedown, and source-of-truth cutover approvals.
- Added `scripts/verify_source_of_truth_cutover_preflight.py` and `reports/source_of_truth_cutover_preflight.md/.csv` as the final non-secret guardrail before source-of-truth approval. It verifies open production gates, owner shakedown, local freeze readiness, rollback package readiness, final command shape, and approval-script protections without calling providers, approving cutover, or changing source of truth.
- Added `scripts/verify_supabase_staging_data_parity.py` and `reports/supabase_staging_data_parity.md/.csv`; it confirms current local counts against the saved Supabase staging validation and currently shows input required because local `audit_log` has 2 newer rows than the last staging load.
- Added `scripts/verify_remote_production_readiness.py` and `reports/remote_production_readiness.md/.csv` as the consolidated Supabase/Vercel production gate report; current status is blocked with 16 passing gates, 0 failing gates, and 8 input-required gates for hosted deployment freshness, temporary owner-recovery closure, Supabase staging data parity refresh, Supabase provider backup proof, hosted write-audit rehearsal, remote monitoring readiness, owner shakedown, and final source-of-truth cutover approval.
- Added `scripts/verify_supabase_staging_refresh_preflight.py` and `reports/supabase_staging_refresh_preflight.md/.csv`; the preflight passes 10 checks with 0 failures and confirms the Supabase staging refresh is needed and scoped to `audit_log local=8 remote=6` before any private database URL is used.
- Added `scripts/run_supabase_staging_refresh.py` and `reports/supabase_staging_refresh_run.md/.csv`; the runner currently records input-required/no-execute readiness, and with `--execute --prompt-secrets` it will privately prompt for the Supabase database URL, reload only staging, rerun parity, and refresh production readiness without storing the credential.
- Added the local write-freeze cutover guardrail and `scripts/verify_local_write_freeze_readiness.py` with `reports/local_write_freeze_readiness.md/.csv`; `CHILLCRM_LOCAL_WRITE_FREEZE=true` blocks local CRM mutations and restore operations during final cutover packaging while leaving final backup, read paths, reports, and exports available.
- Added a data-driven Next Action card to Status and Cleanup so the app points to the next recommended decision, evidence, or cleanup review step without saving choices or changing records.
- Added a Daily Operating Guide to Status, exports, and reports so normal local CRM work can be followed as a read-only runbook that points into Follow Up, pipeline review, New leads, Data Quality, Archive Review, Activity, Project Decisions, Cleanup Starter review, export checks, first-week handoff, pre-change safety, and recovery/portability steps.
- Added a Start Today panel to Dashboard so the first screen now shows the current Next Action and first Daily Operating Guide steps, with direct links into Status, the guide report, and the guide CSV export.
- Added an Operating Work Queue to Status so daily CRM work, imported/local follow-up counts, pipeline focus, New lead review, cleanup review, archive/link access, recent updates, and saved views stay visible while major cleanup decisions remain gated.
- Operating Work Queue now includes Archive Review, surfacing unreviewed calls/texts, needs-lookup items, ready-to-link items, archive-only reviewed progress, and top-number batch shortcuts.
- Added a Recent Local Changes lane to the Operating Work Queue so the latest audited local edits are visible from Status and can jump directly into Activity with Local Changes selected.
- Added a Data Quality card, priority list, report, CSV, focused list shortcuts, reusable list filters, filtered exports, daily work order, owner split, and safety boundary to Status for ordinary contact and pipeline hygiene that stays separate from merge cleanup.
- Added read-only Data Quality badges to People, Companies, Leads, and Deals list rows and detail panels so missing contact, email, owner, value, stage, or relationship issues are visible while working normal CRM records.
- Active People, Companies, Leads, and Deals lists now refresh after inspector edits, address saves, and tag saves, so fixed Data Quality rows leave focused queues immediately after saving.
- Kept record detail panels in a right-side inspector layout on desktop and laptop-width screens, stacking below the list only on narrower screens.
- Adjusted right-side inspector edit, address, contact-action, and task controls to use a narrow inspector layout while preserving wider form layouts after the detail panel stacks full-width.
- Added sticky detail panel headers so long records, tag details, custom-field details, and cleanup groups keep their title/context visible while scrolling.
- Added active-row highlighting to People, Companies, Leads, and Deals lists so the currently opened inspector record remains visible in the working list.
- Added top search across names, contact info, related company/contact/deal/stage/matched-person names, addresses, notes, tasks, tags, linked resources, and custom field values.
- Added grouped Cleanup review for duplicate people, duplicate leads, lead/person overlap groups, and duplicate tag definitions.
- Added Duplicate Tag decision evidence in Cleanup, including live tag batch counts, spot-check facts, report/export links, and direct handoff to the related Project Decision.
- Added Lead/Person Overlap decision evidence in Cleanup, showing the 5 high-priority overlaps, 11 related records, 22 manual fields, 12 blank-fill suggestions, 6 history signals, and direct handoff to the related Project Decision.
- Added Lead/Person Overlap Spot Check report and CSV so the next identity-policy decision has focused A/B/C evidence, overlap-group examples, and a save boundary before any group-level review.
- Added Duplicate People decision evidence in Cleanup, showing 60 groups, 144 person records, 173 manual fields, 15 blank-fill suggestions, 57 history signals, and direct handoff to the related Project Decision.
- Added Duplicate Leads decision evidence in Cleanup, showing 36 groups, 77 lead records, 121 manual fields, 41 history signals, and direct handoff to the related Project Decision.
- Added Duplicate People and Duplicate Leads Spot Check reports and CSVs so those merge-policy choices have focused A/B/C evidence, starting groups, review signals, and save boundaries before group-level review.
- Added Duplicate People Review Worksheet report and CSV so the 60 duplicate-person groups can be worked from a printable/exportable review packet with draft keepers, conflict summaries, blank-fill suggestions, history signals, current group decisions, and blank reviewer fields before any future merge execution is considered.
- Added Duplicate Leads Review Worksheet report and CSV so the 36 duplicate-lead groups can be worked from a printable/exportable review packet with draft keepers, Application Profile context, conflict summaries, history signals, current group decisions, and blank reviewer fields before any future lead merge execution is considered.
- Added duplicate people/leads worksheet links to Status decision surfaces and decision reports so Next Action, Start Today, Decision Prep, Project Decisions, sequence, ballot, brief, and option matrix all keep the policy choice tied to its review packet.
- Added Local Functional Data Integrity Verification report and CSV so the local CRM has a hosted-staging proof artifact covering count parity, record relationships, owner/user references, source-map coverage, custom fields, JSON payloads, recovered document files, backups, required reports, and explicit human review queues.
- Added Guided Review Queue in Cleanup for the 101 duplicate people, duplicate leads, and lead/person overlap groups, with review progress counts, next groups, queue filters, report/export links, and no merge execution.
- Added Cleanup Starter Packet in Status, Cleanup, exports, and reports for the first group-level review batch without merging or rewriting records.
- Added Review Remaining filtering and Save & Next in cleanup group detail panels so group-level decisions can be worked queue-style without merging records.
- Added Cleanup group search across emails, names, phone numbers, tag names, and tag resource types.
- Added Cleanup review priority guidance for duplicate and lead/person overlap groups.
- Added Cleanup priority filtering and sort controls for grouped duplicate review.
- Added filtered/sorted Cleanup group CSV export.
- Added Cleanup comparison signals for grouped records, including completeness score, tags, notes, tasks, deals, addresses, custom fields, newest, and most-complete badges.
- Added non-destructive field-difference comparison to grouped Cleanup records.
- Added Application Profile chips to grouped Cleanup records for faster duplicate and overlap comparison.
- Added Cleanup status tabs for Open, Ignored, and Resolved flags, plus reversible Resolve, Ignore, and Reopen actions.
- Added optional Cleanup decision notes for Resolve, Ignore, and Reopen actions.
- Added non-destructive Merge Drafts for duplicate people, duplicate leads, and lead/person overlap cleanup lists, details, grouped CSV exports, and detailed Exports view CSVs.
- Added saved group-level Cleanup decisions in grouped cleanup lists, detail panels, grouped CSV exports, Activity, and operation verification.
- Added grouped Cleanup filtering and sorting by saved group-level decision, including filtered CSV export verification.
- Added final optional Zendesk Sell API sweep tooling for calls, visits, text messages, documents, products, orders, sequences, nested deal contacts, order line items, and related metadata.
- Hardened backup filenames so rapid consecutive actions create separate backup files.
- Verified create, create options, create/edit validation errors, Project Decision staged-change guardrails, bulk staged reset, path guidance, status guidance, after-save effect guidance, backup creation, and audit behavior, detail action failure handling, detail record snapshots, detail contact actions, edit, owner/relationship edit, tag edit, tag record-type filtering/export/saved views, custom-field record-type filtering/export/saved views, owner filters/sorting/export/saved views, Application Profile display, filtering, status/stage filters, list date filters, list reset controls, secondary view reset controls, list sorting, list CSV export, saved list views, list chips, segment summaries, Dashboard cleanup summary, profile export, address edit, deal linked-address display, linked-resource search/filter/export/saved views, archive import/search/filter/export/saved views/detail/activity, cleanup search, duplicate tag grouped review, cleanup priority guidance, cleanup priority filtering/sorting, cleanup group CSV export, cleanup decision notes, cleanup merge draft summaries, detailed merge draft export, cleanup merge drafts, cleanup comparison signals, field differences, profile summaries, note add/edit, task text/type filter/sort/export/saved views/edit/complete/reopen, flag ignore/reopen/resolve, backup, and audit behavior against a temporary database copy.

## Current Data Shape

- People: 997
- Companies: 378
- Leads: 1,327
- Deals: 125
- Notes: 40
- Tasks: 18
- Normalized Tags: 69
- Tag Assignments: 3,032
- Custom Field Definitions: 31
- Custom Field Values: 13,653
- Imported Archive Items: 884
  - Calls: 380
  - Text Messages: 154
  - Documents: 203
  - Orders: 95
  - Lead Conversions: 52
- Downloaded Zendesk document files: 203 files, about 365 MB.
- Supabase storage: 203 recovered document files uploaded to the private `chillcrm-documents` bucket, 0 missing files, 0 size mismatches, 382,373,054 bytes, and 203 validated `crm.remote_file_objects` rows linked to document archive records.
- Supabase/Vercel staging: local CRM table counts are loaded into Supabase, Vercel staging is deployed at `https://chillcrm-jtu1u0kje-kevin-nations-projects.vercel.app`, signed-file access works on the latest full smoke-tested deployment, owner-only app-user lifecycle/read-only denial, controlled owner recovery, and temporary-user password-rotation hosted smoke passed on the latest smoke URL, the owner Users UI is deployed, the in-app Status view surfaces Production Gates and Owner Intake, local full-role plus actor-aware CRM-write audit verification passes, local disposable backup/restore rehearsal passes, cutover rollback package readiness passes, local write-freeze readiness passes, Vercel environment readiness passes, broad Vercel public protection passes, hosted redeploy preflight passes, remaining gate guardrails pass, source-of-truth cutover preflight guardrails pass while correctly keeping cutover not-ready, Supabase staging parity is instrumented and currently needs a staging refresh for 2 newer local `audit_log` rows, Supabase provider backup verification is instrumented, the safe production-gate runner is ready, and the consolidated production-readiness report has 16 passing gates with 0 failures and 8 input-required gates; local SQLite remains the source of truth until the current local runtime is redeployed, temporary owner recovery is disabled, Supabase staging data parity is refreshed, hosted write-unlock audit rehearsal, Supabase provider backup/restore evidence, monitoring, owner-shakedown, and final cutover approval gates pass.
- Relationship issues: 0 verified at staging; no missing relationship flags in final CRM.
- Known external linked data: 27 extracted Linked Resources. This includes 13 `CALL RECORDINGS:` Google Drive folder links, 12 lead `Skills` web/profile links, 1 lead `Success Is` web link, and 1 person note scheduling link. The links are preserved and surfaced; external files and pages are not copied into the local CRM.
- Data-quality review items: 118 ordinary hygiene rows. This includes 92 records with no usable contact channel, 2 leads missing email, and 24 deals missing value.

## Cleanup Signals

- Duplicate person email flags: 84 open, 1 resolved
- Duplicate lead email flags: 41
- Lead/person email overlap flags: 6
- Duplicate tag definition flags: 32
- Duplicate company name groups: 0

## Decision Readiness

- `reports/cleanup_decision_readiness.md`
- `reports/cleanup_decision_readiness.csv`
- `reports/merge_policy_options.md`
- `reports/merge_policy_options.csv`
- `reports/cleanup_merge_review_pack.md`
- `reports/cleanup_merge_review_pack.csv`
- `reports/duplicate_people_spot_check.md`
- `reports/duplicate_people_spot_check.csv`
- `reports/duplicate_people_review_worksheet.md`
- `reports/duplicate_people_review_worksheet.csv`
- `reports/duplicate_leads_spot_check.md`
- `reports/duplicate_leads_spot_check.csv`
- `reports/duplicate_leads_review_worksheet.md`
- `reports/duplicate_leads_review_worksheet.csv`
- `reports/lead_person_overlap_spot_check.md`
- `reports/lead_person_overlap_spot_check.csv`
- `reports/cleanup_review_starter_packet.md`
- `reports/cleanup_review_starter_packet.csv`
- `reports/duplicate_tag_spot_check.md`
- `reports/duplicate_tag_spot_check.csv`
- `reports/unlinked_archive_matching_candidates.md`
- `reports/unlinked_archive_matching_candidates.csv`
- `reports/unlinked_archive_matching_phone_groups.csv`
- `reports/archive_association_audit.md`
- `reports/archive_association_audit.csv`
- `reports/archive_review_worklist.md`
- `reports/archive_review_worklist.csv`
- `reports/archive_review_triage.md`
- `reports/archive_review_triage.csv`
- `reports/application_profile_editability_review.md`
- `reports/application_profile_editability_review.csv`
- `reports/local_crm_data_quality.md`
- `reports/local_crm_data_quality.csv`
- `reports/local_crm_database_map.md`
- `reports/local_crm_database_map.csv`
- `reports/zendesk_independence_checklist.md`
- `reports/zendesk_independence_checklist.csv`
- `reports/remote_admin_access_plan.md`
- `reports/remote_admin_access_plan.csv`
- `reports/remote_admin_permissions_matrix.md`
- `reports/remote_admin_permissions_matrix.csv`
- `reports/remote_admin_implementation_blueprint.md`
- `reports/remote_admin_implementation_blueprint.csv`
- `reports/remote_admin_rollout_board.md`
- `reports/remote_admin_rollout_board.csv`
- `reports/remote_hosting_decision_packet.md`
- `reports/remote_hosting_decision_packet.csv`
- `reports/remote_managed_cloud_provider_shortlist.md`
- `reports/remote_managed_cloud_provider_shortlist.csv`
- `reports/remote_staging_pricing_preflight.md`
- `reports/remote_staging_pricing_preflight.csv`
- `reports/remote_staging_setup_runbook.md`
- `reports/remote_staging_setup_runbook.csv`
- `reports/remote_staging_deployment_spec.md`
- `reports/remote_staging_deployment_spec.csv`
- `reports/remote_staging_validation_matrix.md`
- `reports/remote_staging_validation_matrix.csv`
- `reports/remote_admin_pilot_onboarding_plan.md`
- `reports/remote_admin_pilot_onboarding_plan.csv`
- `reports/remote_production_cutover_checklist.md`
- `reports/remote_production_cutover_checklist.csv`
- `reports/hosted_database_migration_readiness.md`
- `reports/hosted_database_migration_readiness.csv`
- `reports/hosted_database_schema_draft.md`
- `reports/hosted_database_schema_draft.csv`
- `reports/hosted_database_schema_draft.sql`
- `reports/hosted_database_data_load_plan.md`
- `reports/hosted_database_data_load_plan.csv`
- `reports/backup_safety_ledger.md`
- `reports/backup_safety_ledger.csv`
- `reports/migration_completion_audit.md`
- `reports/migration_completion_audit.csv`
- `reports/followup_transition_plan.md`
- `reports/followup_transition_plan.csv`
- `reports/daily_operating_guide.md`
- `reports/daily_operating_guide.csv`
- `reports/decision_prep_packet.md`
- `reports/decision_prep_packet.csv`
- `reports/project_decision_ballot.md`
- `reports/project_decision_ballot.csv`
- `reports/application_profile_cleanup_conflicts.csv`
- `reports/application_profile_cleanup_examples.csv`
- `reports/project_decision_sequence.md`
- `reports/project_decision_sequence.csv`
- `reports/project_decision_brief.md`
- `reports/project_decision_brief.csv`
- `reports/cleanup_execution_safety_plan.md`
- `reports/cleanup_execution_safety_plan.csv`

The readiness report identifies 133 open cleanup groups: 60 duplicate-person groups, 36 duplicate-lead groups, 5 lead/person overlap groups, and 32 duplicate-tag groups. The highest-priority starting point is Lead/Person Overlap, followed by high-priority Duplicate People groups.

## Design Pipeline

The native Apple-style visual redesign timing is saved as deferred until daily use. The target remains a quieter, more elegant app surface with simple native-feeling controls and spacing, but the pass stays parked until daily CRM use reveals the settled workflow.

The merge policy options report recommends the Guided path: 58 groups for manual review first, 43 shorter guided reviews, 32 duplicate-tag batch decision candidates, and 0 auto-merge candidates recommended today.

The cleanup merge review pack covers the 101 person/lead cleanup groups: 5 lead/person overlaps, 60 duplicate-person groups, and 36 duplicate-lead groups. It summarizes draft keepers, 27 blank-field suggestions, 316 manual review fields, and 104 history signals to preserve.

The duplicate tag spot-check report shows 32 duplicate-tag groups covering 2,214 tag assignments. It found 29 groups with exact same alias text in one resource type, 3 groups with the same alias text across multiple resource types, and 0 groups with spelling or formatting drift. It also includes the A/B/C decision prompt and save boundary for the Duplicate Tag policy.

The Cleanup view now shows this same duplicate-tag evidence in-app, can focus/export the tag batch candidate lane, and can open or prefill the related Project Decision without saving it.

The unlinked archive matching report reviews 472 unlinked calls/texts: 373 calls and 99 text messages. It found 0 exact unique CRM phone candidates, 0 ambiguous exact candidates, 446 items with no CRM phone match, and 26 short-code/non-contact text messages. This supports keeping those items archive-only unless another external identity source is added.

The Archive view now shows this same unlinked calls/texts evidence in-app, can filter/export the 472-item evidence set directly, and can open or prefill the related Project Decision without saving it.

The Application Profile editability report recommends keeping the profile read-only until cleanup. It identifies 3 editable-after-cleanup segment fields, 7 read-only/history fields, 39 cleanup groups with profile conflicts, and 9 groups with profile fill gaps.

The Custom Fields view now shows this same Application Profile decision evidence in-app, can export Application Profiles directly, and can open or prefill the related Project Decision without saving it.

The project decision sequence report orders the seven remaining decisions: save archive/profile/design intent first, save duplicate tag policy after its spot check, then save lead/person, duplicate people, and duplicate lead policies before group-level review. Deferred decisions are counted separately and parked behind active pending decisions.

The Status view now includes a guided Project Decision sequence panel with the next active pending decision, evidence link, and seven-step save order above the editable decision cards.

The Status view also includes a Decision Prep Packet. It summarizes remaining major decisions with pending decisions first and deferred decisions parked behind them, including current status, recommended path, supporting evidence, after-save effect, and impact facts. It exports as `local_crm_decision_prep_packet.csv` and is also available as `reports/decision_prep_packet.md` with a matching CSV.

The Project Decision Ballot now appears from the Project Decisions header and Exports. It is a printable worksheet for all seven major decisions with recommended paths, all available options, evidence links, and blank user choice/note fields. It exports as `local_crm_project_decision_ballot.csv` and is available as `reports/project_decision_ballot.md` with a matching CSV. It does not prefill or save choices.

The Project Decision Option Matrix appears from the Project Decisions header and Exports. It compares the remaining A/B/C options side by side with recommendation, tradeoff, evidence link, after-save effect, and save boundary. It exports as `local_crm_project_decision_option_matrix.csv` and is available as `reports/project_decision_option_matrix.md` with a matching CSV. It does not prefill or save choices.

Project Decision options are labeled A/B/C in the app and ballot so decision prompts can be answered quickly while still requiring an explicit Save Decision action.

Project Decision cards now support Save & Next Decision. This records only the selected card, refreshes Status, and focuses the next pending decision in the sequence, leaving deferred decisions parked until pending decisions are cleared.

The cleanup execution safety plan keeps the current preview locked, records the backup and restore posture, and states the future hard gates: fresh backup, dry-run counts, final confirmation, audit logging, no auto-merge for people/leads/overlaps, and preserve-history handling.

The Backup Safety Ledger now appears in Status, Exports, and the complete package. It lists current backup files, backup reasons, manual backup/restore paths, export-package readiness, and the local CRM actions that create a backup before mutating the database. It exports as `local_crm_backup_safety_ledger.csv` and is available as `reports/backup_safety_ledger.md` with a matching CSV.

The Migration Completion Audit now appears in Exports and the complete package. It shows the local CRM as operational with open gates, ties each migration requirement to evidence, lists the remaining decisions/cleanup/data-quality gates, and exports as `local_crm_migration_completion_audit.csv` with a printable report at `reports/migration_completion_audit.md`.

The Local CRM Database Map now appears in Exports and the complete package. It documents the SQLite tables, row counts, columns, relationships, CSV export inventory, report inventory, and read-only safety boundary. It exports as `local_crm_database_map.csv` and is available as `reports/local_crm_database_map.md` with a matching CSV.

The Zendesk Independence Checklist now appears in Exports and the complete package. It documents whether the local CRM can operate without new Zendesk writes, which raw exports/document files/backups/reports must be preserved, what remains as local governance work, and what to download before any future Zendesk decommission decision. It exports as `local_crm_zendesk_independence_checklist.csv` and is available as `reports/zendesk_independence_checklist.md` with a matching CSV.

The Next Action card now appears in Dashboard, Status, and Cleanup. It currently points to the first pending decision in the protected sequence, shows the A/B/C decision choices, can focus that decision form, can fill the recommended path without saving it, and links to the supporting evidence report.

The Daily Operating Guide now appears in Status as the live runbook for normal local CRM operation. It orders follow-ups, active pipeline review, New leads, ordinary data quality, Archive Review, recent local changes, major decision review, Cleanup Starter review, and export-package checks. The printable report also includes a first-week handoff, pre-change safety checklist, and recovery/portability checklist. It exports as `local_crm_daily_operating_guide.csv` and is available as `reports/daily_operating_guide.md` with a matching CSV. Opening guide actions navigates or exports only; it does not save choices, merge records, resolve cleanup flags, or change Zendesk Sell.

The Archive Review Worklist now appears as the dedicated report/export for unlinked calls/texts. It summarizes linked versus unlinked archive item types, top source numbers, and the first review rows. It exports as `local_crm_archive_review_worklist.csv` and is available as `reports/archive_review_worklist.md` with a matching CSV. It does not save review status or link archive items; those actions still happen explicitly from the Archive inspector.

The Archive Association Audit now appears from the Archive & Links work queue card and Exports. It documents that downloaded document files are linked to local person records, orders and lead conversions are attached through Zendesk-supplied resources, and the remaining unlinked calls/texts have no hidden resource IDs, associated deal IDs, or exact local CRM phone candidates. It exports as `local_crm_archive_association_audit.csv` and is available as `reports/archive_association_audit.md` with a matching CSV.

The Dashboard now starts with a Start Today panel. It brings the current Next Action and the first Daily Operating Guide steps onto the first screen, so normal CRM work can begin without opening Status first. Its buttons navigate or export only; it does not save choices or change records.

The Status view also has an Operating Work Queue. This separates safe daily CRM work from major cleanup decisions by surfacing imported/local follow-up counts, active pipeline deals, New leads, cleanup review progress, archive/link access, recent updates, recent audited local changes, and recent saved views in one place.

The Data Quality lane in the Operating Work Queue surfaces 118 non-destructive review rows. Use it for ordinary CRM hygiene: people/companies with no contact channel, leads missing email, and deals missing value. The report now includes a daily work order, issue summary, owner split, and safety boundary. The People, Companies, Leads, and Deals shortcuts open the normal CRM lists with a Quality filter applied, so those queues can be exported, saved as reusable views, and worked through the regular detail panel. Those same lists show read-only quality badges directly on rows, and opened records carry the same quality badges with short field guidance in the detail panel. When an inspector edit fixes a quality issue, the active list refreshes after saving so the record leaves the focused queue. It does not merge, delete, resolve, or rewrite records.

People, Companies, Leads, and Deals now also have a Source filter for Imported from Zendesk, Local only, and Has local changes. The filter works with search, tags, status/stage, profile filters, date ranges, saved views, sorting, pagination, and CSV export, and exported rows include source, Zendesk ID, and local-change counts.

The Operating Work Queue now includes Source Mix, showing imported, local-only, and locally changed counts for People, Companies, Leads, and Deals. Its shortcuts open the normal lists with the matching Source filter applied, so migrated history and local CRM work can be reviewed without saving project decisions or running cleanup.

Follow Up now distinguishes Imported Zendesk tasks from Local CRM follow-ups. The source filter, source labels, saved views, and CSV export make the old Zendesk task history easier to use without confusing it with new local work.

The Follow Up Transition Plan now appears in the Follow Up view. It shows that the current open queue is still imported Zendesk task history, gives focused shortcuts for imported open, overdue imported, and local follow-ups, and exports as `local_crm_followup_transition_plan.csv` with a printable report at `reports/followup_transition_plan.md`. The Copy Local action creates a separate local CRM follow-up only after an explicit click and due-date prompt; it does not complete or delete the imported Zendesk task.

The Cleanup view now has a Lead/Person Overlap evidence panel for the 5 overlap groups. It keeps the recommended policy visible: use the person as the client keeper while preserving lead/application history, then review the specific groups before any future merge execution path is enabled.

The Lead/Person Overlap Spot Check now appears in Exports and the complete package. It summarizes the 5 overlap groups, 11 involved records, 5 person draft keepers, 12 blank-field suggestions, 22 manual review fields, and 6 history signals, then presents the A/B/C policy choice with a save boundary. It exports as `local_crm_lead_person_overlap_spot_check.csv` and is available as `reports/lead_person_overlap_spot_check.md` with a matching CSV.

The Duplicate People and Duplicate Leads Spot Checks now appear in Exports and the complete package. They present the A/B/C merge-policy choices with focused queue summaries, starting groups, review signals, and save boundaries while leaving the full conflict detail in the broader merge review pack. They export as `local_crm_duplicate_people_spot_check.csv` and `local_crm_duplicate_leads_spot_check.csv`, with printable reports at `reports/duplicate_people_spot_check.md` and `reports/duplicate_leads_spot_check.md`.

The Duplicate People Review Worksheet now appears in Exports and the complete package. It turns the 60 duplicate-person groups into a review sheet with review order, priority lane, draft keeper, conflict summary, blank-fill summary, history-preservation summary, current group decision, and blank reviewer columns. It exports as `local_crm_duplicate_people_review_worksheet.csv` and is available as `reports/duplicate_people_review_worksheet.md` with a matching CSV.

The Duplicate Leads Review Worksheet now appears in Exports and the complete package. It turns the 36 duplicate-lead groups into a review sheet with review order, priority lane, draft keeper, Application Profile context, conflict summary, history-preservation summary, current group decision, and blank reviewer columns. It exports as `local_crm_duplicate_leads_review_worksheet.csv` and is available as `reports/duplicate_leads_review_worksheet.md` with a matching CSV.

The Cleanup view also has Duplicate People and Duplicate Leads evidence panels. These keep guided review counts, starting groups, preservation signals, worksheet links, report links, exports, and Project Decision handoffs visible before any future merge workflow is enabled.

The Guided Review Queue now links directly to the duplicate people and duplicate leads worksheets from the queue cards, so the printable review packets and worksheet CSVs are available from the same surface used for group-level review.

The Cleanup view now also has a Guided Review Queue for group-level review progress. It separates the 101 person/lead/overlap groups into Overlaps, People, and Leads; shows how many still need review; highlights high-priority remaining groups; and opens the next group without marking it approved or running a merge.

The Cleanup Starter Packet now appears in Status and Cleanup. It lists the first 12 review groups in the recommended order: lead/person overlaps first, then high-priority duplicate people, then high-priority duplicate leads. It exports as `local_crm_cleanup_starter_packet.csv` and is available as `reports/cleanup_review_starter_packet.md` with a matching CSV.

Cleanup group detail panels now support Save & Next. This saves the selected group-level decision, refreshes the Review Remaining queue, and opens the next group in the same cleanup type. It still does not merge, delete, resolve, or rewrite records.

The Exports view now includes a Complete Local CRM Package download. It creates one zip containing the current SQLite database, core CSV exports, key reports, and project docs so the local CRM can be moved, inspected, or archived without downloading every CSV separately.

Exports also includes a separate Downloaded Document Files package for the 203 Zendesk document files recovered during the final optional sweep. It keeps the main CRM package quick while still making the larger document archive portable when needed.

Status readiness now includes a Portable export packages check. It confirms the core CRM package and the downloaded-document package are both ready, then links directly to Exports.

## Recommended Next Milestone

Continue hosted staging from the verified local foundation:

- use `reports/local_functional_data_integrity.md` as the local technical gate for Supabase/hosted staging
- preserve the 2 pending and 1 deferred Project Decisions as human policy gates rather than making identity/merge choices automatically
- keep the deployed Vercel staging app behind Vercel Authentication and CRM auth, with write/export locks enabled and signed owner/admin document access monitored
- keep private storage evidence current; rerun upload/validation only if the recovered document manifest changes
- keep hosted document downloads on short-lived Supabase Storage signed URLs and add lower-role denial probes before owner-shakedown signoff or optional internal access
- finish newest-deployment hosted smoke, hosted write-unlock audit rehearsal, Supabase provider backup/restore evidence, and monitoring checks before owner shakedown signoff or source-of-truth switch
- repeat hosted smoke after any schema, adapter, deployment-package, or provider-environment change
- repeat hosted count, relationship, file, permission, health, backup, and restore validation before owner shakedown signoff or optional internal access
- keep the Daily Operating Guide and Data Quality queues for ordinary CRM work while hosted staging is built
- add duplicate merge workflows only after choosing merge rules
- plan and apply the native Apple-style visual redesign after daily CRM use reveals the settled workflow, keeping the current power under a quieter surface
