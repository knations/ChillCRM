# ZendDeskSellProject

Local Zendesk Sell migration and CRM project.

## ChillPortal

ChillPortal is now represented as an internal-only CHILLCRM foundation for a
future Person-first client portal. The local app can prepare Portal status,
shared documents, client next steps, and separate client-visible notes from a
Person record. A disabled-by-default staff preview is available at
`/portal?person_id=<id>` only when `CHILLPORTAL_ENABLED=true`, but there is not
yet a client login, invitation flow, storage provider change, or production
cutover.

## Current Status

- Zendesk Sell API access verified.
- Full read-only API snapshot exported locally.
- SQLite staging database created from the snapshot.
- Migration analysis reports generated.
- Final normalized local CRM database created.
- Local CRM browser built against the final CRM database.
- Status view added for migration health, a readiness checklist, snapshot details, cleanup progress, linked-resource counts, backups, reports, and final Zendesk sweep state.
- Final Zendesk Sell optional sweep completed and imported into a local Archive layer.
- Project Decisions added to Status for tracking major cleanup, archive, Application Profile, and visual redesign choices with backup and audit logging.
- Core record editing, local notes, review-flag resolution, backup creation, and audit logging added.
- Owner assignment and relationship editing added for local CRM records: people can change company/owner, companies and leads can change owner, and deals can change contact, organization, stage, value, hot flag, and close date.
- Create and edit forms now show inline validation messages for bad linked-record IDs or other save errors, without losing the form.
- Right-sidebar address, tag, note, task, and cleanup-flag actions now use the same inline failure handling instead of dropping errors silently.
- Locally-created notes can now be edited from record detail panels; imported Zendesk notes remain read-only historical records.
- Create-new flows added for people, companies, leads, and deals, including owner assignment, stage selection, relationship suggestions, and hot-deal support where applicable.
- Task creation and task completion added.
- Follow-up tasks can now edit local task text and due dates from record detail panels and the Follow Up table, with backup and audit logging.
- Completed tasks can now be reopened from Follow Up or record detail panels, with backup and audit logging.
- Backup restore added from the app and maintenance script.
- Follow Up view added for open, overdue, due soon, completed, and all tasks, with task/record text filtering, related-record-type filtering, sorting, reusable saved views, and filtered CSV export.
- Follow Up now labels and filters imported Zendesk tasks versus local CRM follow-ups, with source-aware saved views and exports.
- Follow Up now includes a Transition Plan that separates imported Zendesk reminders from local CRM follow-ups, with focused filter shortcuts, Copy Local for explicit local follow-up creation, printable report, CSV export, and package export.
- Follow Up, Tags, Custom Fields, Linked Resources, Archive, and Activity include Reset View controls for quickly clearing saved/filter state.
- Tags view added with tag search, record-type filtering, assignment counts, record click-through, reusable saved views, Dashboard shortcuts, and filtered CSV export.
- Record detail panels can now save local tag edits for people, companies, leads, and deals with backup and audit logging.
- People, Companies, Leads, and Deals lists can be filtered by tag, status/stage, and date range.
- People, Companies, Leads, and Deals lists can be sorted by useful fields such as name, dates, status, stage, and value from the toolbar or sortable table headers.
- People, Companies, Leads, and Deals lists can export the current filtered and sorted view as CSV.
- People, Companies, Leads, and Deals lists can save reusable views for common filter/sort combinations with live record counts.
- People, Companies, Leads, and Deals lists include Reset View to quickly clear active filters, saved-view selection, pagination, and custom sorting.
- People and Leads lists can be filtered by Application Profile fields: Desired Growth, Time Frame, and Invest?.
- People and Leads list rows show compact Application Profile chips for quick scanning.
- Dashboard now shows saved-view shortcuts, Cleanup Review shortcuts, and Application Segments for leads with click-through into filtered lists and queues.
- Custom Fields view added for reviewing usage, sample values, related records, record-type slices, reusable saved views, Dashboard shortcuts, and filtered summary export.
- Linked Resources view added for searching, filtering, opening, saving reusable views, Dashboard shortcuts, and exporting URL-bearing migrated fields and notes.
- Archive view added for searching, filtering, opening, and exporting recovered optional Zendesk data: calls, text messages, downloaded documents, orders, and lead conversions.
- Archive view now includes an Unlinked Calls/Texts evidence panel with live matching counts, recommendation, report link, one-click evidence filtering/export, and direct handoff to the related Project Decision.
- Archive and Status now show Association Coverage for recovered history, including linked/unlinked archive counts, 203/203 document-file coverage, preserved recording URLs, and the zero exact-phone-candidate finding for remaining unlinked calls/texts.
- Archive rows now open a right-sidebar inspector, and unlinked archive items can be manually linked to a chosen person, company, lead, or deal with a backup and audit entry.
- Archive now includes a Manual Review Queue for unlinked calls/texts, with review-status filters, top-number batch shortcuts, sidebar review notes, Save & Next queue flow, CSV export support, backups, and audit logging.
- Custom Fields now includes an Application Profile evidence panel with live profile coverage, cleanup-dependency counts, report link, profile export, and direct handoff to the related Project Decision.
- Custom field promotion recommendation report generated for deciding which migrated fields should become first-class local CRM fields.
- Application Profile section added to lead/person sidebars for the high-priority application custom fields.
- Activity and Exports views added for recent local CRM activity and CSV downloads, including Application Profiles.
- Activity view now supports text/type/record/date filtering, reusable saved views, Dashboard shortcuts, and filtered CSV export.
- Record detail Activity entries link to related records when the timeline item points at a connected deal, person, company, or lead.
- Record detail Activity now rolls up related note/task history from connected people, companies, deals, or matched person records.
- Right sidebar detail panels now start with a compact record snapshot for type, status/stage, owner, update date, and available task/flag/tag/link/archive counts.
- Record snapshots now show whether a record was imported from Zendesk or created locally, plus local audit-change counts and last local-change date when available.
- Right sidebar contact actions now provide Mail, Call, Open Website, and Copy controls for available contact fields.
- Right sidebar now shows address fields near the top; people, companies, and leads can save local address edits, and deals show linked contact/company addresses.
- Right sidebar now surfaces link-bearing migrated data as Linked Resources, including call-recording Drive folders, profile links, and scheduling links.
- Top search now finds names, contact info, related company/contact/deal/stage/matched-person names, addresses, notes, tasks, tags, linked resources, and custom field values.
- Cleanup view now groups duplicate people, duplicate leads, lead/person overlaps, and duplicate tag definitions, with search, review priority guidance, priority filtering/sorting, CSV export, comparison signals, field differences, Application Profile chips, Open/Ignored/Resolved tabs, reversible flag actions, and optional decision notes.
- Cleanup now includes a Duplicate Tag evidence panel with live tag batch counts, spot-check facts, report/export links, and direct handoff to the Duplicate Tag Project Decision.
- Duplicate Tag Spot Check now includes the A/B/C decision prompt and save boundary so the next cleanup policy choice can be made from the evidence report.
- Cleanup group lists, details, grouped CSV exports, and the Exports view now include non-destructive Merge Draft information for duplicate/overlap reviews, with a suggested keeper, blank-field fill suggestions, conflicting fields, and history signals to preserve.
- Cleanup group lists, details, grouped CSV exports, and Activity now include saved group-level decisions such as Merge Later, Keep Separate, Already Handled, and False Positive.
- Grouped Cleanup review can now filter and sort by saved decision so duplicate review can be managed in batches.
- Cleanup decision-readiness report and CSV added for planning duplicate/merge policy decisions.
- Merge policy options report and CSV added to compare conservative, guided, and aggressive cleanup paths before any merge work is enabled.
- Cleanup now shows the Guided merge-policy summary in-app, with lane filters for priority manual review, conflict-heavy review, short guided review, lead/person policy review, and tag batch candidates.
- Status now includes a saveable Project Decisions center for the few major choices that unlock future merge execution and design work.
- Apple-style redesign pipeline report and CSV added so the later native-app visual pass has explicit gates, phases, and preservation requirements without changing CRM records.
- Project Decisions now show data-backed impact facts, including affected cleanup groups, archive linkage, Application Profile coverage, and readiness context.
- Project Decision brief report and CSV added for printing/exporting current decisions, impacts, gates, preview actions, backup safety, and restore path.
- Project Decisions and the decision brief now include a recommended-path simulation, showing what would unlock if recommended choices were saved without actually saving them.
- Project Decisions can pre-fill recommended paths in the form while still requiring an explicit Save Decision click for each saved choice.
- Project Decision cards now show what saving that decision would unlock while reminding that saving does not merge or rewrite CRM records.
- Project Decision path choices now explain the selected option directly on the card before anything is saved.
- Project Decision forms now clarify whether a selected path is only a Pending draft, Deferred, or an active Decided path for previews.
- Project Decision forms now show unsaved staged changes, can reset staged changes per card or all at once, and keep save buttons disabled until a valid change is ready to record.
- Project Decisions now include Save & Next Decision so the seven major choices can be worked in sequence while still requiring an explicit save for each one; deferred decisions are parked behind active pending decisions.
- Project Decision options now show A/B/C choice codes in the app and ballot so major choices can be reviewed quickly without saving anything automatically.
- Status now includes a read-only Decision Prep Packet that summarizes remaining major decisions, recommended paths, evidence links, impact facts, a CSV export, and a printable report without saving choices.
- Project Decision Ballot report and CSV added so the seven major choices can be reviewed, marked up, and discussed before saving anything in Status.
- Project Decision Option Matrix report and CSV added so remaining A/B/C choices can be compared side by side with recommendation, tradeoff, evidence, and save boundary.
- Status and Cleanup now show a non-destructive Cleanup Execution Preview that stays locked until required project decisions are saved and shows which actions would become eligible.
- Cleanup execution safety plan report and CSV added to document backup, restore, final-confirmation, and no-auto-merge guardrails before any future mutating cleanup workflow is enabled.
- Backup Safety Ledger report and CSV added to document the current backup inventory, restore posture, and the local actions that create pre-change backups.
- Migration Completion Audit report and CSV added to show end-to-end migration status, completed evidence, remaining gates, and why the local CRM is operational but not fully closed.
- Local CRM Database Map report and CSV added to document SQLite tables, row counts, columns, relationships, CSV exports, report inventory, and the read-only handoff boundary.
- Zendesk Independence Checklist report and CSV added to document local-only operating readiness, preserved artifacts, Zendesk access boundaries, and what to download before any future Zendesk decommission decision.
- Remote Admin Access Plan report and CSV added to map the path from this local prototype to a secure shared remote CRM with hosted database, private file storage, roles, audit controls, staging verification, and cutover gates.
- Remote Admin Implementation Blueprint report and CSV added to translate the remote plan into build workstreams, remote-only tables, endpoint changes, verification gates, and cutover sequence before any hosting or user invites happen.
- Remote Admin Rollout Board report and CSV added to turn the remote plan into a sequenced task board with blockers, dependencies, proof gates, decision prompts, staging validation, and cutover milestones without provisioning hosting or changing CRM records.
- Remote Hosting Decision Packet report and CSV added to make the hosting posture choice concrete with A/B/C options, scoring, minimum requirements, owner questions, and next steps before any hosting is provisioned.
- Remote Managed Cloud Provider Shortlist report and CSV added to compare current official provider options for managed app hosting, hosted Postgres, private file storage, auth, backups, staging, and owner questions before any provider is chosen.
- Remote Staging Pricing Preflight report and CSV added to turn the provider shortlist into official-source budget components, staging estimate profiles, setup gates, cost controls, and owner questions before any provider account or payment action.
- Remote Staging Setup Runbook report and CSV added to define the DigitalOcean/Railway staging paths, phases, setup tasks, environment variables, validation gates, and approval gates before any hosting is provisioned or data uploaded.
- Remote Staging Deployment Spec report and CSV added to translate the setup runbook into deployment targets, app service settings, configuration variables, package inputs, implementation gaps, smoke tests, owner decisions, and next steps before any hosting is provisioned.
- Remote write lock guard added for hosted staging: setting `REMOTE_WRITE_LOCK=true` blocks browser/API POST writes while leaving local default use unlocked.
- Remote health and environment markers added for hosted staging: `/health` and `/api/health` return a minimal app/database/report status without client counts, and the browser shows the current `CRM_ENV` label.
- Remote bulk package export guard added for hosted staging: setting `EXPORT_PACKAGE_ENABLED=false` blocks the Complete Local CRM Package and Downloaded Document Files package while leaving ordinary CSV/report exports available.
- Remote document-file access guard added for hosted staging: setting `DOCUMENT_FILE_ACCESS_ENABLED=false` blocks direct recovered-document file serving from `/api/archive_file` until private storage and permissions are validated.
- Remote Staging Validation Matrix report and CSV added to give the future hosted staging load expected counts, validation checks, evidence fields, blocker rules, and pilot/cutover gates before any admin invite.
- Remote Admin Pilot Onboarding Plan report and CSV added to define the first-admin pilot roles, prerequisites, onboarding steps, workflows, permission probes, support watch items, blocker rules, and signoff gates before any admin invite.
- Remote Production Cutover Checklist report and CSV added to define the local write freeze, final packages, production load, repeated validation, admin handoff, rollback triggers, first-week monitoring, communication plan, and signoff gates before the hosted CRM becomes source of truth.
- Hosted Database Migration Readiness report and CSV added to inspect the live SQLite schema, table counts, hosted/Postgres type translations, foreign keys, JSON/timestamp/file-path handling, migration requirements, and remote rollout risks.
- Hosted Database Schema Draft report, CSV, and SQL draft added to translate the current local CRM tables plus remote-only app user, role, audit, file, and migration tables into a staging-review schema before any remote database is created.
- Hosted Data Load Plan report and CSV added to sequence the staging data load by table, row count, remote seed data, private files, validation checks, and cutover gates without moving data.
- Dashboard, Status, and Cleanup now show a data-driven Next Action card that points to the next recommended decision, evidence, or cleanup review step, including A/B/C choices for decision prompts, without saving or changing records.
- Status now includes a Daily Operating Guide that turns the Next Action, Operating Work Queue, Decision Prep Packet, Cleanup Starter Packet, Data Quality, Activity, and export checks into a single read-only daily runbook with report and CSV export.
- Daily Operating Guide now includes a first-week handoff, pre-change safety checklist, and recovery/portability checklist for operating the local CRM without relying on Zendesk Sell.
- Dashboard now includes a Start Today panel that surfaces the current Next Action and first Daily Operating Guide steps from the first screen, with links into Status, the guide report, and the guide CSV export.
- Status now includes an Operating Work Queue that separates safe daily CRM work from major cleanup decisions, with imported/local follow-up counts, pipeline focus, New lead review, cleanup review, archive/link access, recent updates, and saved views.
- Operating Work Queue and Start Today now surface Archive Review, including unreviewed calls/texts, needs-lookup items, ready-to-link items, and top-number batch shortcuts.
- Archive Review now has a printable/exportable Worklist report and CSV so the 472 unlinked calls/texts can be reviewed in order while already-linked documents stay separate.
- Archive Review Triage report and CSV added so unlinked calls/texts are grouped into likely archive-only, needs-lookup, ready-to-link candidate, and manual-review lanes without saving review status or linking anything.
- Archive triage lanes are now usable as in-app Archive filters and saved views, with matching CSV exports and row-level triage hints for reviewing unlinked calls/texts in batches.
- Archive & Links now includes an Archive Association Audit report and CSV that documents which recovered archive data is already linked, which communication items remain unlinked, and why the remaining calls/texts should not be auto-linked.
- Operating Work Queue now includes Recent Local Changes, showing the latest audited local edits and opening Activity pre-filtered to Local Changes.
- Status now includes Data Quality in the Operating Work Queue, with a non-destructive report, CSV, and one-click focused list queues for ordinary contact and pipeline hygiene.
- Data Quality report now includes a daily work order, issue summary, owner split, and safety boundary so ordinary CRM hygiene stays separate from merge cleanup.
- People, Companies, Leads, and Deals list rows and detail panels now show read-only Data Quality badges such as No contact, Missing email, and Missing value.
- Inspector edits, address saves, and tag saves now refresh the active People, Companies, Leads, or Deals list after saving, so fixed Data Quality rows drop out of focused queues without a manual refresh.
- Record detail panels stay as a right-side inspector on desktop and laptop-width screens, then stack below the list only on narrower screens.
- Right-side inspector edit, address, contact-action, and task controls adapt to the narrower inspector width instead of squeezing wide form rows.
- Detail panels now keep a sticky record header visible while scrolling long records, tag details, custom-field details, and cleanup groups.
- People, Companies, Leads, and Deals lists now highlight the row currently open in the detail inspector.
- People, Companies, Leads, and Deals lists now include a Source filter for Imported from Zendesk, Local only, and Has local changes; filtered exports include source, Zendesk ID, and local-change counts.
- Status now includes Source Mix in the Operating Work Queue, with imported/local/changed counts and shortcuts into Source-filtered People, Companies, Leads, and Deals lists.
- Cleanup now includes Lead/Person Overlap evidence with person-keeper history preservation counts, review/report/export links, and direct handoff to the related Project Decision.
- Lead/Person Overlap Spot Check report and CSV added so the next identity-policy decision has focused A/B/C evidence, group examples, and a save boundary separate from the broader merge review pack.
- Cleanup now includes Duplicate People and Duplicate Leads evidence with guided-review counts, starting groups, preservation signals, report/export links, and direct handoff to their Project Decisions.
- Duplicate People and Duplicate Leads Spot Check reports and CSVs added so their merge-policy choices have focused A/B/C evidence, starting groups, and save boundaries separate from the broader merge review pack.
- Duplicate People Review Worksheet report and CSV added so the 60 duplicate-person groups can be worked from a printable/exportable review packet with draft keepers, conflict summaries, blank-fill suggestions, history signals, and blank reviewer fields before any group-level decisions are saved.
- Duplicate Leads Review Worksheet report and CSV added so the 36 duplicate-lead groups can be worked from a printable/exportable review packet with draft keepers, Application Profile context, conflict summaries, history signals, and blank reviewer fields before any group-level decisions are saved.
- Cleanup evidence panels and the Guided Review Queue now link directly to the duplicate people/leads worksheets and worksheet CSVs, so review packets are available from the working cleanup surface.
- Status decision cards, Next Action, Start Today, Decision Prep, the decision sequence, ballot, brief, and option matrix now also surface duplicate people/leads worksheet links so the policy choice and group-review packet stay together.
- Cleanup now includes a Guided Review Queue for duplicate people, duplicate leads, and lead/person overlaps, with review progress counts, next groups, queue filters, report/export links, and no merge execution.
- Cleanup and Status now include a read-only Cleanup Starter Packet for the first group-level review batch, with printable report and CSV export.
- Cleanup group review now has a Review Remaining decision filter and a Save & Next action so reviewed groups can be worked as a queue without merging records.
- Activity now shows cleanup flag decisions with resolved/ignored/reopened status and any decision note.
- Final optional Zendesk Sell API sweep captured calls, texts, documents, orders, lead conversions, optional metadata, and downloaded document files.
- Archive view now supports date-range filtering, reusable saved views, Dashboard shortcuts, and matching CSV export across recovered calls, texts, documents, orders, and conversions.
- Exports now includes a Complete Local CRM Package zip containing the current SQLite database, core CSV exports, key reports, and project docs, plus a separate Downloaded Document Files zip for recovered Zendesk document files.
- Status readiness now tracks whether the portable export packages are ready, including the recovered Zendesk document-file package.
- Added a double-click local CRM starter that opens the app and automatically uses the next open port if the default port is busy.
- Count verification passed against the staging database.
- Native Apple-style visual redesign timing is saved as deferred until daily use, preserving the CRM power under the current functional surface until the working shape settles.
- Duplicate Tag policy choice C is saved: duplicate Zendesk tag aliases remain visible for audit/history while normalized local tag assignments stay preserved.

## Local CRM

Start the local CRM:

Double-click:

```text
Start Local CRM.command
```

Or start from Terminal:

```sh
cd /Users/kevinsvault/Downloads/ZendDeskSellProject
python3 crm_app/server.py --host 127.0.0.1 --port 8765 --auto-port --open
```

The app prints the exact local address. It normally opens:

```text
http://127.0.0.1:8765
```

If that port is already busy, it will use the next open port, such as `8766` or `8767`.

## Final Zendesk Sell Sweep

The final read-only optional sweep has been run. It captured:

- 380 calls
- 154 text messages
- 203 documents and 203 downloaded document files
- 95 orders
- 52 lead conversions
- optional metadata such as call outcomes and unqualified reasons

The latest snapshot is `snapshot_20260605T042056Z`, and the recovered optional records are imported into the local CRM Archive.

To rerun the sweep later:

```sh
python3 scripts/export_zendesk_sell.py --include-extended --download-documents
python3 scripts/build_staging_database.py
python3 scripts/import_zendesk_optional_archive.py
```

This requires `ZENDESK_SELL_ACCESS_TOKEN` to be set in the terminal environment. The token is not stored in this project.

## Project Structure

- `raw_api_exports/`: Timestamped Zendesk Sell JSON snapshots.
- `staging_database/`: Local SQLite staging database.
- `crm_database/`: Final normalized local CRM database.
- `reports/`: Migration reports and cleanup CSVs.
- `scripts/`: Export, staging, and analysis scripts.
- `crm_app/`: Local CRM browser.
- `docs/`: Planning notes.
- `logs/`: Runtime logs if needed.
- `backups/`: Timestamped SQLite backups.
- `exports/`: Timestamped CSV exports from the local CRM.

## ChillPortal

ChillPortal is reserved as the future client-facing dashboard that stays
separate from the internal CHILLCRM operator workspace. The approved MVP scope
is a Person-first portal with Shared Documents, Client Next Steps, and separate
client-visible notes only. The current repository contains only a disabled
configuration scaffold and documentation:

- `crm_app/portal_config.py`: route, role, permission, and feature-flag names.
- `config/chillportal.env.example`: placeholder-only environment names.
- `docs/CHILLPORTAL.md`: portal scope, unknowns, and approval gates.
- `docs/PORTAL_CONFIG.md`: config map and rollback notes.
- `docs/ACCESS.md`: internal CRM versus client portal access boundary.
- `docs/PROJECT_MAP.md`: ownership map between CHILLCRM and ChillPortal.
- `docs/PORTAL_SCHEMA_PLAN.md`: Person-first schema blueprint.

This scaffold does not create client-facing routes, database tables, provider
integrations, invitations, access changes, or production data changes.

## Key Files

- `staging_database/zendesk_sell_staging.sqlite`
- `crm_database/local_crm.sqlite`
- `reports/local_crm_verification.md`
- `reports/local_crm_migration_summary.md`
- `reports/zendesk_sell_optional_data_sweep.md`
- `reports/cleanup_decision_readiness.md`
- `reports/merge_policy_options.md`
- `reports/cleanup_merge_review_pack.md`
- `reports/cleanup_review_starter_packet.md`
- `reports/duplicate_people_spot_check.md`
- `reports/duplicate_people_review_worksheet.md`
- `reports/duplicate_leads_spot_check.md`
- `reports/duplicate_leads_review_worksheet.md`
- `reports/lead_person_overlap_spot_check.md`
- `reports/duplicate_tag_spot_check.md`
- `reports/unlinked_archive_matching_candidates.md`
- `reports/archive_association_audit.md`
- `reports/archive_review_worklist.md`
- `reports/archive_review_triage.md`
- `reports/application_profile_editability_review.md`
- `reports/local_crm_data_quality.md`
- `reports/local_crm_database_map.md`
- `reports/zendesk_independence_checklist.md`
- `reports/remote_admin_access_plan.md`
- `reports/remote_admin_permissions_matrix.md`
- `reports/remote_admin_implementation_blueprint.md`
- `reports/remote_admin_rollout_board.md`
- `reports/remote_hosting_decision_packet.md`
- `reports/remote_managed_cloud_provider_shortlist.md`
- `reports/remote_staging_pricing_preflight.md`
- `reports/remote_staging_setup_runbook.md`
- `reports/remote_staging_deployment_spec.md`
- `reports/remote_staging_validation_matrix.md`
- `reports/remote_admin_pilot_onboarding_plan.md`
- `reports/remote_production_cutover_checklist.md`
- `reports/hosted_database_migration_readiness.md`
- `reports/hosted_database_schema_draft.md`
- `reports/hosted_database_schema_draft.sql`
- `reports/hosted_database_data_load_plan.md`
- `reports/backup_safety_ledger.md`
- `reports/migration_completion_audit.md`
- `reports/followup_transition_plan.md`
- `reports/daily_operating_guide.md`
- `reports/decision_prep_packet.md`
- `reports/project_decision_ballot.md`
- `reports/project_decision_sequence.md`
- `reports/project_decision_brief.md`
- `reports/cleanup_execution_safety_plan.md`
- `reports/staging_analysis.md`
- `docs/migration_rules.md`
- `docs/design_pipeline.md`
- `raw_api_exports/latest_snapshot.txt`
- `scripts/export_zendesk_sell.py`
- `scripts/build_staging_database.py`
- `scripts/import_zendesk_optional_archive.py`
- `scripts/analyze_staging_database.py`
- `scripts/analyze_custom_field_promotion.py`
- `scripts/analyze_cleanup_readiness.py`
- `scripts/analyze_merge_policy_options.py`
- `scripts/analyze_cleanup_merge_review_pack.py`
- `scripts/analyze_cleanup_review_starter_packet.py`
- `scripts/analyze_archive_review_triage.py`
- `scripts/analyze_remote_admin_access_plan.py`
- `scripts/analyze_remote_admin_rollout_board.py`
- `scripts/analyze_remote_hosting_decision_packet.py`
- `scripts/analyze_remote_managed_cloud_provider_shortlist.py`
- `scripts/analyze_remote_staging_pricing_preflight.py`
- `scripts/analyze_remote_staging_setup_runbook.py`
- `scripts/analyze_remote_staging_deployment_spec.py`
- `scripts/analyze_remote_staging_validation_matrix.py`
- `scripts/analyze_remote_admin_pilot_onboarding_plan.py`
- `scripts/analyze_remote_production_cutover_checklist.py`
- `scripts/analyze_hosted_database_migration_readiness.py`
- `scripts/analyze_hosted_schema_draft.py`
- `scripts/analyze_hosted_data_load_plan.py`
- `scripts/analyze_duplicate_cleanup_spot_checks.py`
- `scripts/analyze_duplicate_people_review_worksheet.py`
- `scripts/analyze_duplicate_leads_review_worksheet.py`
- `scripts/analyze_lead_person_overlap_spot_check.py`
- `scripts/analyze_duplicate_tag_spot_check.py`
- `scripts/analyze_unlinked_archive_matching.py`
- `scripts/analyze_archive_association_audit.py`
- `scripts/analyze_archive_review_worklist.py`
- `scripts/analyze_application_profile_editability.py`
- `scripts/analyze_project_decision_sequence.py`
- `scripts/analyze_project_decisions.py`
- `scripts/analyze_cleanup_execution_safety.py`
- `scripts/analyze_local_crm_data_quality.py`
- `scripts/analyze_local_crm_database_map.py`
- `scripts/analyze_zendesk_independence.py`
- `scripts/analyze_backup_safety_ledger.py`
- `scripts/analyze_remote_admin_permissions_matrix.py`
- `scripts/analyze_remote_admin_implementation_blueprint.py`
- `scripts/analyze_migration_completion_audit.py`
- `scripts/analyze_followup_transition_plan.py`
- `scripts/analyze_daily_operating_guide.py`
- `scripts/analyze_decision_prep_packet.py`
- `scripts/analyze_project_decision_ballot.py`
- `scripts/migrate_to_local_crm.py`
- `scripts/verify_local_crm.py`
- `scripts/local_crm_maintenance.py`
- `scripts/verify_app_operations.py`
- `crm_app/server.py`
