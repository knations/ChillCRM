# CHILLCRM Operating Notes

CHILLCRM is the current operational CRM. Treat it as the working system for daily sales, client follow-up, purchases, files, notes, tasks, pipeline, and owner/admin operations.

## Start Local App

Double-click `Start CHILLCRM.command` from the project folder.

The starter opens CHILLCRM in the default browser. If `http://127.0.0.1:8765` is busy, it automatically uses the next open local port and prints the exact address.

## Daily Flow

- Start on Dashboard for priority signals.
- Use People for client/contact work.
- Use Deals and Pipeline for revenue movement.
- Use Follow Up for calls, reminders, overdue tasks, and due-today work.
- Use Activity for recent notes, tasks, calls, purchases, and record changes.
- Use Cleanup only for intentional data hygiene work.

## People Records

People records are the main operating file. A Person can hold:

- email and phone
- primary, billing, and shipping addresses
- operator avatar
- notes
- tasks
- calls
- purchases
- files
- tags
- linked resources
- archive items
- profile fields
- activity history

Use the record detail screen as the client file. Add new context as notes, calls, tasks, purchases, files, or tags instead of scattering it outside the CRM.

## Calls

Use the People detail call section to log conversations. Include the date/time, type, summary, and notes. Call history becomes part of the Person timeline.

## Purchases

Zapier shopping-cart purchase intake is available for approved cart automations.

Approved inbound purchase webhooks should post to:

```text
https://chillcrm.app/api/webhooks/zapier_purchase
```

The webhook must include the configured server-side secret. The app matches existing People by email, fills blank basics when appropriate, creates a purchase entry, and avoids duplicate deliveries when an order or transaction ID is repeated.

## Automation Task Intake

Codex/Otter debrief automations may create approved follow-up items on existing People records through narrow server-to-server endpoints:

```text
POST https://chillcrm.app/api/automation/add_person_task
POST https://chillcrm.app/api/automation/add_person_note
POST https://chillcrm.app/api/automation/add_person_call
POST https://chillcrm.app/api/automation/add_owner_task
```

These endpoints require the server-side `CHILLCRM_AUTOMATION_TOKEN` and accept it only as a bearer token or `X-CHILLCRM-AUTOMATION-TOKEN` header. The token is not a general CRM session and does not permit broad reads or writes. Automation must identify a Person by `person_id`, exact email, or exact case-insensitive name; ambiguous matches stop without guessing.

Owner tasks use `/api/automation/add_owner_task` and identify an active app user by `owner_id`, exact `owner_email`, or exact case-insensitive `owner_name`. Owner tasks appear in the dashboard/calendar work queue without attaching to a Person, Company, Lead, or Deal.

The Google Sheet approval queue is designed to run without daily copy/paste:

- `PENDING` rows stay in the sheet.
- `APPROVE` rows are posted to CHILLCRM through the narrow automation endpoints, then removed from the sheet after a successful post.
- `DELETE` rows are removed from the sheet without posting.
- Failed rows stay in the sheet for review.
- The scheduled GitHub Action uses repository secrets `CHILLCRM_AUTOMATION_TOKEN` and `GOOGLE_SERVICE_ACCOUNT_JSON`; it does not use the production database URL.

The approval queue Sheet is `Awaiting Approval` in spreadsheet `1IDZbgwlAMts05cgKwmcF5ACPDeJKcArC7mu8v38UnTQ`.

## Transcript Intake Bot

The transcript intake bot scans the Google Drive folder `My Drive/AAA BUSINESS BLUEPRINT/Otter Transcripts` and its subfolders for Google Docs or text transcript files. Its default Drive folder ID is `1TQR1D0dxTEitoUNDHVoR8bg3bRrdhiaZ`.

The bot adds tentative `PENDING` rows only to the `Awaiting Approval` Sheet. It never writes directly to CHILLCRM. Approved rows are still posted later by the approval queue processor.

To avoid duplicate reviews, the bot records processed Drive file IDs and modified times in the `Transcript Intake Log` tab. A file is skipped after it has been scanned at the same modified time. If Otter updates the same document later, the changed modified time allows one new scan.

The GitHub Action is `Scan Drive Transcripts To Approval Sheet`. It can be run manually from GitHub Actions, and it also runs daily at 10:00 AM Pacific during daylight time. Manual runs default to dry-run mode so the report can be checked before appending rows.

Required GitHub secret:

```text
GOOGLE_SERVICE_ACCOUNT_JSON
```

Recommended GitHub secret for higher-quality transcript analysis:

```text
OPENAI_API_KEY
```

If `OPENAI_API_KEY` is missing or temporarily fails, the bot falls back to conservative name/action heuristics.

## Files

Files added to a Person should stay attached to that Person. Hosted production file access is private and served through authenticated app routes and short-lived storage links.

## Tags

Tags are operational labels. Add and remove tags from Person detail on desktop, and manage tag names from the Tags view when needed.

## Search And Filters

Use top search for broad CRM lookup across records, notes, tasks, tags, links, addresses, and related records. Use page filters when narrowing a specific list.

## Security

- Production requires login.
- Secure cookies are enabled.
- Passkeys are supported.
- Private files require authenticated access.
- Role checks protect admin functions.
- Sensitive provider keys belong only in provider secret managers or private local prompts.

## Verification

Before pushing production app changes, run the relevant checks:

```sh
python3 -m py_compile crm_app/server.py api/index.py
python3 scripts/verify_hosted_app_deployment_package.py
python3 scripts/verify_secret_handling_boundaries.py
python3 scripts/verify_operational_crm.py
```

For broader behavior changes, run:

```sh
python3 scripts/verify_app_operations.py
```

The operational verifier checks the current product surface. The broad verifier includes older private/provider evidence gates; a stop at those final gates is not automatically a code failure, but earlier assertion failures should be treated as regressions.

## Deployment Boundary

Vercel deploys the production runtime only. Local databases, backups, exports, reports, downloaded files, scripts, ops launchers, virtual environments, `.env*`, and `.vercel/` are excluded from the hosted runtime.
