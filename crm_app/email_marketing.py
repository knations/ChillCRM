"""Broadcasts, consent, and event-driven Resend autoresponder connections.

All state lives in the CRM database. Schema installation and source imports are
explicit operator actions. Historical imports never enqueue automation events.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import uuid
from datetime import datetime, timezone

try:
    from crm_app.resend_client import ProviderError, ResendClient
except ImportError:
    from resend_client import ProviderError, ResendClient

UNSUBSCRIBE = '{{{RESEND_UNSUBSCRIBE_URL}}}'
BLOCKED = {'unsubscribed', 'bounced', 'complained'}
SCHEMA = [
    '''CREATE TABLE IF NOT EXISTS email_contacts (
        email TEXT PRIMARY KEY, person_id INTEGER, first_name TEXT NOT NULL DEFAULT '',
        last_name TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'unknown', evidence_json TEXT NOT NULL DEFAULT '{}',
        provider_id TEXT, updated_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS email_campaigns (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
        tag_filter TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'draft',
        audience_json TEXT NOT NULL DEFAULT '[]', provider_id TEXT, segment_id TEXT,
        scheduled_at TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS email_automations (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, provider_id TEXT NOT NULL,
        trigger_kind TEXT NOT NULL, tag_name TEXT NOT NULL DEFAULT '',
        event_name TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS email_outbox (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, dedup_key TEXT NOT NULL UNIQUE,
        email TEXT, resource_id TEXT, payload_json TEXT NOT NULL DEFAULT '{}',
        state TEXT NOT NULL DEFAULT 'pending', lease TEXT, error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''',
    '''CREATE TABLE IF NOT EXISTS email_events (
        id TEXT PRIMARY KEY, email TEXT, event_type TEXT NOT NULL, provider_email_id TEXT,
        occurred_at TEXT NOT NULL, received_at TEXT NOT NULL)''',
    'CREATE INDEX IF NOT EXISTS idx_email_outbox_state ON email_outbox(state, created_at)',
    'CREATE INDEX IF NOT EXISTS idx_email_events_email ON email_events(email, received_at)',
]


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def flag(name):
    return os.environ.get(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


def install(conn):
    for sql in SCHEMA:
        conn.execute(sql)
    conn.commit()


def installed(conn):
    # Do not probe nonexistent tables inside a Postgres transaction (that would
    # abort it). Catalog reads are compatible with the existing adapter.
    if hasattr(conn, 'conn'):
        return bool(conn.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'crm' AND table_name = 'email_contacts'").fetchone())
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'email_contacts'").fetchone())


def row(conn, sql, args=()):
    value = conn.execute(sql, args).fetchone()
    return dict(value) if value is not None else None


def rows(conn, sql, args=()):
    return [dict(value) for value in conn.execute(sql, args).fetchall()]


def email_address(value):
    value = str(value or '').strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value):
        raise ValueError('A valid email address is required.')
    return value


def provider_id(value):
    value = str(value or '').strip()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', value):
        raise ValueError('A valid Resend identifier is required.')
    return value


def require_live(automations=False):
    if not flag('CHILLCRM_EMAIL_ENABLED') or not os.environ.get('RESEND_API_KEY'):
        raise ValueError('Live email is disabled or Resend is not configured.')
    if not os.environ.get('RESEND_FROM'):
        raise ValueError('A verified sender must be configured.')
    if not os.environ.get('RESEND_WEBHOOK_SECRET'):
        raise ValueError('Configure signed delivery and subscription webhooks first.')
    if automations and not flag('CHILLCRM_EMAIL_AUTOMATIONS_ENABLED'):
        raise ValueError('Autoresponder activation and its billing must be enabled separately.')


def status(conn, query=""):
    ready = installed(conn)
    data = {'installed': ready, 'enabled': flag('CHILLCRM_EMAIL_ENABLED'),
            'provider_configured': bool(os.environ.get('RESEND_API_KEY')),
            'sender_configured': bool(os.environ.get('RESEND_FROM')),
            'webhook_configured': bool(os.environ.get('RESEND_WEBHOOK_SECRET')),
            'automations_enabled': flag('CHILLCRM_EMAIL_AUTOMATIONS_ENABLED'),
            'customer_sends_enabled': flag('CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED')}
    if not ready:
        return {**data, 'contacts': [], 'campaigns': [], 'automations': [], 'outbox': [], 'events': []}
    return {**data,
        'counts': rows(conn, 'SELECT status, count(*) AS total FROM email_contacts GROUP BY status'),
        'contacts': rows(conn, 'SELECT * FROM email_contacts WHERE email LIKE ? OR first_name LIKE ? OR last_name LIKE ? ORDER BY email LIMIT 100', tuple('%' + query[:200] + '%' for _ in range(3))),
        'tag_options': sorted({tag for contact in rows(conn, 'SELECT tags_json FROM email_contacts') for tag in json.loads(contact['tags_json'])}, key=str.casefold),
        'campaigns': rows(conn, 'SELECT * FROM email_campaigns ORDER BY created_at DESC LIMIT 100'),
        'automations': rows(conn, 'SELECT * FROM email_automations ORDER BY name'),
        'outbox': rows(conn, 'SELECT id, kind, email, resource_id, state, error, updated_at FROM email_outbox ORDER BY updated_at DESC LIMIT 100'),
        'events': rows(conn, 'SELECT * FROM email_events ORDER BY received_at DESC LIMIT 100')}


def upsert_contact(conn, data, evidence, imported=False):
    address = email_address(data.get('email'))
    old = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (address,))
    desired = data.get('status', 'unknown')
    if desired not in {'unknown', 'subscribed'} | BLOCKED:
        raise ValueError('Unknown subscription status.')
    # Suppression is monotonic. Re-consent requires a future dedicated, audited
    # double-opt-in flow, never an import or ordinary synchronization.
    if old and old['status'] in BLOCKED:
        desired = old['status']
    if desired == 'subscribed' and not evidence:
        raise ValueError('Subscription evidence is required.')
    tags = sorted({str(t).strip() for t in data.get('tags', json.loads(old['tags_json']) if old else []) if str(t).strip()}, key=str.casefold)
    conn.execute('''INSERT INTO email_contacts
        (email, person_id, first_name, last_name, tags_json, status, evidence_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(email) DO UPDATE SET
        person_id = COALESCE(excluded.person_id, email_contacts.person_id),
        first_name = excluded.first_name, last_name = excluded.last_name,
        tags_json = excluded.tags_json, status = excluded.status,
        evidence_json = excluded.evidence_json, updated_at = excluded.updated_at''',
        (address, data.get('person_id'), str(data.get('first_name', old['first_name'] if old else '') or '')[:200],
         str(data.get('last_name', old['last_name'] if old else '') or '')[:200], json.dumps(tags), desired,
         json.dumps({'source': evidence, 'imported': imported, 'previous_status': old['status'] if old else None}), stamp()))
    return address


def recipient_allowed(address):
    if flag('CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED'):
        return True
    return address in {a.strip().lower() for a in os.environ.get('CHILLCRM_EMAIL_TEST_RECIPIENTS', '').split(',') if a.strip()}


def identity_matches(conn, contact):
    if not contact['person_id']:
        return True
    person = row(conn, 'SELECT email FROM people WHERE id = ?', (contact['person_id'],))
    return bool(person and str(person['email'] or '').strip().lower() == contact['email'])


def audience(conn, tag=''):
    selected, excluded = [], {'not_subscribed': 0, 'tag_mismatch': 0, 'identity_changed': 0, 'test_mode': 0}
    identities = {p['id']: str(p['email'] or '').strip().lower() for p in rows(conn, 'SELECT id, email FROM people')}
    for contact in rows(conn, 'SELECT * FROM email_contacts ORDER BY email'):
        if contact['status'] != 'subscribed':
            excluded['not_subscribed'] += 1
            continue
        if not recipient_allowed(contact['email']):
            excluded['test_mode'] += 1
            continue
        if tag and tag.casefold() not in {str(t).casefold() for t in json.loads(contact['tags_json'])}:
            excluded['tag_mismatch'] += 1
            continue
        if contact['person_id']:
            if identities.get(contact['person_id']) != contact['email']:
                excluded['identity_changed'] += 1
                continue
        selected.append(contact)
    return {'contacts': selected, 'count': len(selected), 'excluded': excluded,
            'fingerprint': hashlib.sha256(json.dumps([c['email'] for c in selected]).encode()).hexdigest()}


def enqueue(conn, kind, key, address=None, resource=None, payload=None):
    oid = str(uuid.uuid4())
    conn.execute('''INSERT INTO email_outbox
        (id, kind, dedup_key, email, resource_id, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(dedup_key) DO NOTHING''',
        (oid, kind, key, address, resource, json.dumps(payload or {}), stamp(), stamp()))
    return oid


def queue_crm_event(conn, person_id, kind, identity, added_tags=()):
    if not flag('CHILLCRM_EMAIL_ENABLED') or not flag('CHILLCRM_EMAIL_AUTOMATIONS_ENABLED') or not installed(conn):
        return
    person = row(conn, 'SELECT email FROM people WHERE id = ?', (person_id,))
    if not person:
        return
    address = str(person['email'] or '').strip().lower()
    contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (address,))
    if not contact or contact['status'] != 'subscribed' or not recipient_allowed(address):
        return
    for rule in rows(conn, 'SELECT * FROM email_automations WHERE enabled = 1 AND trigger_kind = ?', (kind,)):
        if kind == 'tag_added' and rule['tag_name'].casefold() not in {t.casefold() for t in added_tags}:
            continue
        # One enrollment per contact/rule. Explicit re-enrollment is intentionally
        # excluded from the first release.
        enqueue(conn, 'event', 'enroll:' + rule['id'] + ':' + address, address, rule['id'],
                {'event': rule['event_name'], 'source_identity': str(identity)})


def campaign_html(body):
    return '<div>' + '<br>'.join(html.escape(body).splitlines()) + '</div><p><a href="' + UNSUBSCRIBE + '">Unsubscribe</a></p>'


def action(conn, payload, actor, client=None, audit=None):
    if not installed(conn):
        raise ValueError('Install the email schema with the operator setup script first.')
    op = payload.get('action')
    client = client or ResendClient()
    if op == 'preview':
        preview = audience(conn, str(payload.get('tag') or '').strip())
        return {k: v for k, v in preview.items() if k != 'contacts'} | {'sample': [c['email'] for c in preview['contacts'][:20]]}
    if op == 'contact':
        address = upsert_contact(conn, payload, str(payload.get('evidence') or '').strip())
        if payload.get('status') in BLOCKED:
            enqueue(conn, 'suppress', 'suppress:' + address + ':' + stamp(), address)
    elif op == 'campaign':
        name, subject, body = [str(payload.get(k) or '').strip() for k in ('name', 'subject', 'body')]
        if not name or not subject or not body or '\n' in subject or '\r' in subject:
            raise ValueError('Name, a one-line subject, and message are required.')
        if len(name) > 200 or len(subject) > 998 or len(body) > 100000:
            raise ValueError('Email content is too long.')
        cid = str(uuid.uuid4())
        conn.execute('''INSERT INTO email_campaigns
            (id, name, subject, body, tag_filter, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (cid, name, subject, body, str(payload.get('tag') or '').strip(), stamp(), stamp()))
    elif op == 'queue_campaign':
        require_live()
        campaign = row(conn, 'SELECT * FROM email_campaigns WHERE id = ?', (str(payload.get('id')),))
        if not campaign or campaign['state'] != 'draft':
            raise ValueError('Only a draft can be queued.')
        if not row(conn, "SELECT id FROM email_outbox WHERE kind = 'test' AND resource_id = ? AND state = 'done' LIMIT 1", (campaign['id'],)):
            raise ValueError('Send and review a test before queuing this broadcast.')
        preview = audience(conn, campaign['tag_filter'])
        if not preview['count'] or preview['count'] > int(os.environ.get('CHILLCRM_EMAIL_CONTACT_LIMIT', '5000')):
            raise ValueError('Audience is empty or exceeds the configured contact limit.')
        if payload.get('fingerprint') != preview['fingerprint']:
            raise ValueError('Audience changed. Preview it again before sending.')
        scheduled = str(payload.get('scheduled_at') or '').strip() or None
        if scheduled:
            try:
                when = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
                if when.tzinfo is None or when <= datetime.now(timezone.utc):
                    raise ValueError()
            except ValueError:
                raise ValueError('Schedule must be a future date with a timezone.') from None
        conn.execute("UPDATE email_campaigns SET state = 'queued', audience_json = ?, scheduled_at = ?, updated_at = ? WHERE id = ? AND state = 'draft'",
                     (json.dumps([c['email'] for c in preview['contacts']]), scheduled, stamp(), campaign['id']))
        enqueue(conn, 'broadcast', 'broadcast:' + campaign['id'], resource=campaign['id'])
    elif op == 'test':
        require_live()
        target = email_address(payload.get('email'))
        allowed = {x.strip().lower() for x in os.environ.get('CHILLCRM_EMAIL_TEST_RECIPIENTS', '').split(',') if x.strip()}
        if target not in allowed:
            raise ValueError('Test recipient is not on the server-configured test allowlist.')
        campaign = row(conn, 'SELECT * FROM email_campaigns WHERE id = ?', (str(payload.get('id')),))
        if not campaign:
            raise ValueError('Draft not found.')
        enqueue(conn, 'test', 'test:' + str(uuid.uuid4()), target, campaign['id'])
    elif op == 'automation':
        trigger = str(payload.get('trigger_kind') or '')
        if trigger not in {'tag_added', 'purchase'}:
            raise ValueError('Choose tag added or purchase.')
        name = str(payload.get('name') or '').strip()[:200]
        tag = str(payload.get('tag') or '').strip()[:200]
        if not name or (trigger == 'tag_added' and not tag):
            raise ValueError('Name and trigger tag are required.')
        aid = str(uuid.uuid4())
        conn.execute('''INSERT INTO email_automations
            (id, name, provider_id, trigger_kind, tag_name, event_name, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (aid, name, provider_id(payload.get('provider_id')), trigger, tag, 'chillcrm.sequence.' + aid.replace('-', ''), stamp()))
    elif op == 'automation_toggle':
        rule = row(conn, 'SELECT * FROM email_automations WHERE id = ?', (str(payload.get('id')),))
        if not rule:
            raise ValueError('Autoresponder not found.')
        enabled = bool(payload.get('enabled'))
        if enabled:
            require_live(automations=True)
            remote = client.request('GET', '/automations/' + provider_id(rule['provider_id']))
            triggers = [s.get('config', {}).get('event_name') for s in remote.get('steps', []) if s.get('type') == 'trigger']
            if rule['event_name'] not in triggers or remote.get('status') != 'enabled':
                raise ValueError('Publish the Resend automation with the exact trigger event shown here before enabling enrollment.')
            email_steps = [step for step in remote.get('steps', []) if step.get('type') == 'send_email']
            if not email_steps:
                raise ValueError('The autoresponder must contain at least one email step.')
            for step in remote.get('steps', []):
                if step.get('type') not in {'trigger', 'condition', 'delay', 'wait_for_event', 'send_email'}:
                    raise ValueError('This connection supports email, delay, wait and condition steps only.')
            for step in email_steps:
                tid = provider_id(step.get('config', {}).get('template', {}).get('id'))
                template = client.request('GET', '/templates/' + tid)
                if template.get('status') != 'published' or template.get('has_unpublished_versions'):
                    raise ValueError('Publish all template edits before enabling enrollment.')
                if UNSUBSCRIBE not in str(template.get('html') or '') + str(template.get('text') or ''):
                    raise ValueError('Every autoresponder template must include the Resend unsubscribe variable.')

        conn.execute('UPDATE email_automations SET enabled = ?, updated_at = ? WHERE id = ?', (int(enabled), stamp(), rule['id']))
    elif op in {'cancel_campaign', 'stop_automation'}:
        table = 'email_campaigns' if op == 'cancel_campaign' else 'email_automations'
        item = row(conn, 'SELECT * FROM ' + table + ' WHERE id = ?', (str(payload.get('id')),))
        if not item:
            raise ValueError('Item not found.')
        if op == 'cancel_campaign':
            if item['state'] == 'draft':
                conn.execute("UPDATE email_campaigns SET state = 'cancelled', updated_at = ? WHERE id = ?", (stamp(), item['id']))
            else:
                conn.execute("UPDATE email_campaigns SET state = 'cancel_requested', updated_at = ? WHERE id = ?", (stamp(), item['id']))
                enqueue(conn, 'cancel_broadcast', 'cancel:' + item['id'], resource=item['id'])
        else:
            conn.execute('UPDATE email_automations SET enabled = 0, updated_at = ? WHERE id = ?', (stamp(), item['id']))
            enqueue(conn, 'stop_automation', 'stop:' + item['id'], resource=item['id'])
    else:
        raise ValueError('Unknown email action.')
    if audit:
        audit(conn, op, actor)
    conn.commit()
    return {'ok': True}


def receive_webhook(conn, payload):
    event_id, kind = payload['_verified_id'], str(payload.get('type') or '')[:100]
    if row(conn, 'SELECT id FROM email_events WHERE id = ?', (event_id,)):
        return {'ok': True, 'duplicate': True}
    data = payload['data']
    addresses = data.get('to') or ([data['email']] if data.get('email') else [])
    if isinstance(addresses, str):
        addresses = [addresses]
    address = str(addresses[0]).lower().strip() if addresses else None
    blocked = {'email.bounced': 'bounced', 'email.complained': 'complained'}
    if kind in blocked and address:
        conn.execute('UPDATE email_contacts SET status = ?, updated_at = ? WHERE email = ?', (blocked[kind], stamp(), address))
    if kind in {'contact.updated', 'contact.deleted'}:
        if data.get('unsubscribed') is True or kind == 'contact.deleted':
            if address:
                conn.execute("UPDATE email_contacts SET status = 'unsubscribed', updated_at = ? WHERE email = ?", (stamp(), address))
            elif data.get('id'):
                conn.execute("UPDATE email_contacts SET status = 'unsubscribed', updated_at = ? WHERE provider_id = ?", (stamp(), data['id']))
    conn.execute('''INSERT INTO email_events (id, email, event_type, provider_email_id, occurred_at, received_at)
        VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING''',
        (event_id, address, kind, data.get('email_id'), str(payload.get('created_at') or stamp()), stamp()))
    conn.commit()
    return {'ok': True}


def sync_contact(conn, client, contact):
    address = contact['email']
    path = '/contacts/' + urllib.parse.quote(address, safe='')
    try:
        remote = client.request('GET', path)
    except ProviderError as exc:
        if exc.status != 404:
            raise
        if contact['status'] != 'subscribed':
            return None
        remote = client.request('POST', '/contacts', {'email': address,
            'first_name': contact['first_name'], 'last_name': contact['last_name'],
            'unsubscribed': contact['status'] != 'subscribed'})
    if remote.get('unsubscribed') is True:
        conn.execute("UPDATE email_contacts SET status = 'unsubscribed', updated_at = ? WHERE email = ?", (stamp(), address))
        conn.commit()
        return None
    if contact['status'] != 'subscribed':
        client.request('PATCH', path, {'unsubscribed': True})
        return None
    pid = provider_id(remote['id'])
    conn.execute('UPDATE email_contacts SET provider_id = ?, updated_at = ? WHERE email = ?', (pid, stamp(), address))
    conn.commit()
    return pid


def process_one(conn_factory, client=None):
    """Bounded work per invocation; safe to call from a scheduled operator job.

    A claimed job is never automatically reclaimed after a crash. The operator
    reconciles it against Resend first, preventing duplicate event submissions.
    """
    require_live()
    client = client or ResendClient()
    with conn_factory() as conn:
        job = row(conn, "SELECT * FROM email_outbox WHERE state = 'pending' ORDER BY CASE WHEN kind IN ('suppress', 'cancel_broadcast', 'stop_automation') THEN 0 ELSE 1 END, created_at, id LIMIT 1")
        if not job:
            return False
        token = str(uuid.uuid4())
        conn.execute("UPDATE email_outbox SET state = 'processing', lease = ?, updated_at = ? WHERE id = ? AND state = 'pending'",
                     (token, stamp(), job['id']))
        conn.commit()
        claimed = row(conn, 'SELECT lease FROM email_outbox WHERE id = ?', (job['id'],))
        if not claimed or claimed['lease'] != token:
            return True
    try:
        with conn_factory() as conn:
            if job['kind'] == 'event':
                require_live(automations=True)
                rule = row(conn, 'SELECT * FROM email_automations WHERE id = ?', (job['resource_id'],))
                contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (job['email'],))
                if (not rule or not rule['enabled'] or not contact or contact['status'] != 'subscribed'
                        or not recipient_allowed(job['email']) or not identity_matches(conn, contact)):
                    finish(conn, job, 'cancelled')
                    return True
                pid = sync_contact(conn, client, contact)
                if not pid:
                    finish(conn, job, 'cancelled')
                    return True
                limit = int(os.environ.get('CHILLCRM_EMAIL_MONTHLY_ENROLLMENT_LIMIT', '10000'))
                month = stamp()[:7] + '%'
                total = conn.execute("SELECT count(*) FROM email_outbox WHERE kind = 'event' AND state IN ('done', 'processing', 'needs_review') AND created_at LIKE ?", (month,)).fetchone()[0]
                if total > limit:
                    raise ValueError('Monthly autoresponder enrollment limit reached; review usage before proceeding.')
                current = row(conn, 'SELECT enabled FROM email_automations WHERE id = ?', (rule['id'],))
                contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (job['email'],))
                if (not current['enabled'] or not contact or contact['status'] != 'subscribed'
                        or not recipient_allowed(job['email']) or not identity_matches(conn, contact)):
                    finish(conn, job, 'cancelled')
                    return True
                client.request('POST', '/events/send', {'event': rule['event_name'], 'contact_id': pid,
                    'payload': {'chillcrm_source': json.loads(job['payload_json']).get('source_identity')}})
            elif job['kind'] == 'suppress':
                contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (job['email'],))
                if contact:
                    sync_contact(conn, client, contact)
            elif job['kind'] == 'test':
                allowed = {a.strip().lower() for a in os.environ.get('CHILLCRM_EMAIL_TEST_RECIPIENTS', '').split(',')}
                if job['email'] not in allowed:
                    raise ValueError('Test recipient is no longer on the allowlist.')
                campaign = row(conn, 'SELECT * FROM email_campaigns WHERE id = ?', (job['resource_id'],))
                # Test sends do not enroll contacts or reuse a real unsubscribe URL.
                body = campaign_html(campaign['body']).replace(UNSUBSCRIBE, '#test-unsubscribe')
                client.request('POST', '/emails', {'from': os.environ['RESEND_FROM'], 'to': [job['email']],
                    'subject': '[TEST] ' + campaign['subject'], 'html': body})
            elif job['kind'] == 'broadcast':
                if process_broadcast(conn, client, job) is False:
                    return True
            elif job['kind'] == 'cancel_broadcast':
                campaign = row(conn, 'SELECT * FROM email_campaigns WHERE id = ?', (job['resource_id'],))
                if campaign and campaign['provider_id']:
                    client.request('POST', '/broadcasts/' + provider_id(campaign['provider_id']) + '/cancel', {})
                conn.execute("UPDATE email_campaigns SET state = 'cancelled', updated_at = ? WHERE id = ?", (stamp(), job['resource_id']))
            elif job['kind'] == 'stop_automation':
                rule = row(conn, 'SELECT * FROM email_automations WHERE id = ?', (job['resource_id'],))
                client.request('POST', '/automations/' + provider_id(rule['provider_id']) + '/stop', {})
            else:
                raise ValueError('Unknown email job.')
            finish(conn, job, 'done')
    except Exception as exc:
        with conn_factory() as conn:
            # Only a definite 429 rejection is automatically retriable. Network
            # errors/5xx might have happened after the provider accepted a POST.
            state = 'pending' if isinstance(exc, ProviderError) and exc.status == 429 else 'needs_review'
            if state == 'pending' and job['kind'] == 'broadcast':
                conn.execute("UPDATE email_campaigns SET state = 'preparing' WHERE id = ? AND state = 'sending'", (job['resource_id'],))
            safe_error = str(exc) if isinstance(exc, (ProviderError, ValueError)) else 'Email job failed; inspect provider status before retrying.'
            finish(conn, job, state, safe_error)
    return True


def finish(conn, job, state, error=None):
    conn.execute('UPDATE email_outbox SET state = ?, error = ?, updated_at = ? WHERE id = ?', (state, error, stamp(), job['id']))
    conn.commit()


def process_broadcast(conn, client, job):
    campaign = row(conn, 'SELECT * FROM email_campaigns WHERE id = ?', (job['resource_id'],))
    if not campaign or campaign['state'] in {'cancelled', 'cancel_requested'}:
        return
    if campaign['state'] not in {'queued', 'preparing'}:
        raise ValueError('Broadcast requires reconciliation before another send attempt.')
    addresses = json.loads(campaign['audience_json'])
    if any(not recipient_allowed(address) for address in addresses):
        raise ValueError('Customer sending is disabled. Review this broadcast in test-only mode.')
    conn.execute("UPDATE email_campaigns SET state = 'preparing', updated_at = ? WHERE id = ?", (stamp(), campaign['id']))
    conn.commit()
    if not campaign['segment_id']:
        segment = client.request('POST', '/segments', {'name': 'ChillCRM ' + campaign['id']})
        campaign['segment_id'] = provider_id(segment['id'])
        conn.execute('UPDATE email_campaigns SET segment_id = ? WHERE id = ?', (campaign['segment_id'], campaign['id']))
        conn.commit()
    # Each job advances at most 20 contacts. This bounds serverless/operator
    # execution; synchronization progress is durable and recoverable.
    progress = json.loads(job['payload_json'])
    offset = int(progress.get('offset', 0))
    for address in addresses[offset:offset + 20]:
        contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (address,))
        if contact and contact['status'] == 'subscribed':
            pid = sync_contact(conn, client, contact)
            if pid:
                client.request('POST', '/contacts/' + pid + '/segments/' + campaign['segment_id'], {})
        offset += 1
        conn.execute('UPDATE email_outbox SET payload_json = ? WHERE id = ?', (json.dumps({'offset': offset}), job['id']))
        conn.commit()
        time.sleep(.25)
    if offset < len(addresses):
        finish(conn, job, 'pending')
        return False
    # Recheck suppressed contacts before final send; Resend also enforces its
    # unsubscribe state at delivery time, including scheduled Broadcasts.
    for address in addresses:
        contact = row(conn, 'SELECT * FROM email_contacts WHERE email = ?', (address,))
        if contact and contact['status'] != 'subscribed':
            sync_contact(conn, client, contact)
        elif contact and contact['person_id']:
            person = row(conn, 'SELECT email FROM people WHERE id = ?', (contact['person_id'],))
            if not person or str(person['email'] or '').strip().lower() != address:
                raise ValueError('A recipient identity changed after audience approval; review the campaign before sending.')
    if not campaign['provider_id']:
        draft = client.request('POST', '/broadcasts', {'segment_id': campaign['segment_id'],
            'from': os.environ['RESEND_FROM'], 'name': campaign['name'], 'subject': campaign['subject'],
            'html': campaign_html(campaign['body']), 'send': False})
        campaign['provider_id'] = provider_id(draft['id'])
        conn.execute('UPDATE email_campaigns SET provider_id = ? WHERE id = ?', (campaign['provider_id'], campaign['id']))
        conn.commit()
    conn.execute("UPDATE email_campaigns SET state = 'sending', updated_at = ? WHERE id = ? AND state = 'preparing'", (stamp(), campaign['id']))
    conn.commit()
    latest = row(conn, 'SELECT state FROM email_campaigns WHERE id = ?', (campaign['id'],))
    if latest['state'] != 'sending':
        return
    if any(not recipient_allowed(address) for address in addresses):
        raise ValueError('Customer sending is disabled; broadcast requires review.')
    data = {'scheduled_at': campaign['scheduled_at']} if campaign['scheduled_at'] else {}
    client.request('POST', '/broadcasts/' + campaign['provider_id'] + '/send', data)
    conn.execute("UPDATE email_campaigns SET state = ?, updated_at = ? WHERE id = ? AND state = 'sending'",
                 ('scheduled' if campaign['scheduled_at'] else 'sent', stamp(), campaign['id']))


def contact_events(conn, address):
    if not address or not installed(conn):
        return []
    return rows(conn, 'SELECT event_type, occurred_at FROM email_events WHERE email = ? ORDER BY received_at DESC LIMIT 50', (str(address).strip().lower(),))
