# Email workspace release review — November 4, 2026

## Approval boundary

Kevin approved the draft-only deployment on November 4, 2026, subsequently authorized committing and pushing completed, verified changes as the standing workflow, and separately requested the Resend webhook connection. The webhook signing secret is installed as an encrypted production variable. Customer sending, provider sending-key installation, and a recurring dispatcher remain outside this rollout approval. The first release adds the owner/admin Email workspace in **draft-only mode**.

Target: existing Vercel project `chillcrm` (`prj_BW7lf5NVtOGjZ8eA28pIVOBIACgh`), public host `https://chillcrm.app`. Base: GitHub `knations/ChillCRM`, `main`, commit `167355c34ac74c5b228b6e3cb1d01e5a1d47a99d`; confirmed current remotely during preparation. Release source is the reviewed patch on that base, frozen in the generated release manifest; the publication receipt records the resulting commit and deployment.

## What changes

- Owner/admin Email workspace: broadcast drafts, explicit audience review, test-send controls, paused autoresponder connections, consent and delivery history.
- Signed Resend webhook route; invalid signatures are rejected and repeated events are deduplicated. Existing CRM write locks still apply.
- Durable database outbox, with a bounded operator dispatcher. No timer runs inside a web request. Uncertain provider submissions require manual reconciliation.
- Separate server-enforced customer gate. Without an explicit customer release, broadcast audiences and autoresponder enrollments are limited to allowlisted test addresses. Dispatch repeats the checks, including for previously queued work.
- Audience identity checks use one CRM lookup instead of a database query per subscriber. Changed identities cannot trigger a queued sequence.

Existing contacts, legacy fields/notes, and the completed import are not changed by deploying this code. No new schema migration is required: the six email tables already exist in production. The earlier fifteen-contact deletion and 51 ambiguous email matches remain separate outstanding work. The remaining 185 legacy values stay archive-only.

## Stage 1 — proposed approval now

1. Freeze the exact source hashes and verify the isolated runtime package contains no credentials, databases, exports, reports, or unrelated operator helpers.
2. Retain the current production deployment ID/URL as the rollback target before uploading anything.
3. Build against the existing production project/environment with these deployment overrides all false:

```text
CHILLCRM_EMAIL_ENABLED=false
CHILLCRM_EMAIL_AUTOMATIONS_ENABLED=false
CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED=false
```

4. Use the isolated release directory and existing project link. With an authenticated Vercel CLI, the planned command is:

```sh
vercel deploy --prod --skip-domain --cwd RELEASE_DIRECTORY --yes \
  --env CHILLCRM_EMAIL_ENABLED=false \
  --env CHILLCRM_EMAIL_AUTOMATIONS_ENABLED=false \
  --env CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED=false
```

`RELEASE_DIRECTORY` is replaced by the exact directory in the generated manifest. This produces a staged production build; public aliases are not promoted until the smoke checks pass. Preserve existing authentication, database, storage, write-lock, and recovery settings. Do not run the old all-purpose deployment helper: it can update unrelated project settings and upload reports.

5. Verify deployed health, sign-in, ordinary people/deal workflows, Email access for owner/admin, denial for staff/read-only users, disabled send controls, static assets, and invalid-webhook rejection. No test contact or campaign is created in production in Stage 1.
6. Only after passing, promote that exact URL using `vercel promote DEPLOYMENT_URL --yes --scope kevin-nations-projects`. Do not push unrelated files. A focused Git commit/push needs Kevin's explicit authorization if it is to accompany publication.

## Stage 2 — separate supervised test approval

After Stage 1 works, prepare the exact provider/settings changes for approval:

- Install `RESEND_API_KEY` and `RESEND_WEBHOOK_SECRET` as encrypted Vercel secrets, never public or plain-text variables.
- Sender: `Kevin Nations <kevin@chillionaire.com>`. Chillionaire.com is verified and two direct provider tests were reported delivered. The KevinNations.com team conflict is separate and remains unresolved.
- Allowlist: the two owner-approved test inboxes, recorded only in private configuration.
- Register `https://chillcrm.app/api/webhooks/resend` in Resend after the route exists, subscribing only to supported email delivery/bounce/complaint/engagement and contact update/deletion events. Confirm the current API event names before creation. Store the returned signing secret privately.
- Enable the master flag only for supervised testing, keep `CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED=false`, and leave autoresponder enrollment off until its specific test is prepared.
- Use only the two approved test marketing contacts, with recorded owner-requested test consent and no customer modifications. The initial production read-only preview correctly excluded all 1,642 imported customer contacts; the supervised tests subsequently added only the two approved test contacts without creating CRM people.
- Run a bounded manual dispatcher from a trusted operator environment with secrets loaded privately:

```sh
.venv/bin/python scripts/manage_email_marketing.py process --hosted --max-jobs 20 --apply
```

- Prove one test broadcast, one short test autoresponder, signed webhook delivery, and unsubscribe propagation. Stop on uncertain provider results rather than repeat a send.

No recurring dispatcher is installed in either prepared Stage 1 or the manual test plan. Before unattended use, a durable scheduled runner, cadence, runtime limit, credential scope, monitoring, and cost must be selected and approved. Customer sending is blocked until this and provider automation billing are confirmed. The marketing plan alone is not a confirmed all-in automation budget.

## Verification evidence

- 17 synthetic email checks pass, covering consent, repeatable import, suppression exclusions, permissions, signatures, provider templates, chunked dispatch, cancellation, ambiguous failures, test-only gating, stale queued work, changed identities, and account-level provider suppressions. Suppression-removal events do not resubscribe contacts.
- Python compilation, JavaScript syntax checks, backend boundaries, operational CRM verifier, and current app workflows pass.
- Read-only hosted Postgres preview passes: zero eligible test contacts, 1,642 excluded by the test-mode gate, zero pending jobs; preview completed in 0.53 seconds.
- Desktop 1440px and mobile 390px previews show disabled send controls without page overflow. Synthetic preview data only.
- Real Resend direct delivery, the native broadcast/autoresponder operator paths, and live signed-webhook receipt/replay tests pass. Authenticated owner web UI testing is a separate check and is not claimed by these operator tests.

The supervised operator tests are complete: the real application outbox sent the native two-recipient broadcast and one-email native autoresponder, and Resend reported all deliveries successful. A preliminary preview was also delivered. The test automation is paused locally and disabled at the provider. The public webhook accepted a real provider event, rejected a bad signature, and deduplicated a provider replay. All actual test inboxes and provider receipt IDs remain in private local evidence. No customer sends, recurring dispatcher, or web UI sending flags were enabled by these tests; Vercel stays draft-only.

## Risks and rollback

The new webhook is intentionally unsigned-session accessible but requires a valid provider signature. Provider account access and delivery metadata remain owner/admin only. The first release does not solve unattended scheduling, automatic recovery of uncertain jobs, sequence re-entry, or per-contact cancellation of an existing provider sequence. Large broadcasts require preparation time while the audience synchronizes.

If Stage 1 smoke checks fail, do not promote. If a promoted build regresses, keep all sending flags false and promote the retained prior production deployment. Retain email tables, consent evidence, imported contacts, and notes; no database rollback is needed for a code-only deployment. If any provider-scheduled sends or runs are introduced during later testing, cancel/stop them in Resend explicitly; changing app flags alone does not cancel provider work.
