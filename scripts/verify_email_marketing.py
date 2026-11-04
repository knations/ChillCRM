#!/usr/bin/env python3
"""Synthetic-only integration checks for consent, queues and Resend boundaries."""
import base64
import hashlib
import hmac
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from crm_app import email_marketing as em
from crm_app.resend_client import ProviderError, verify_webhook
from crm_app.server import CRMRequestHandler
from crm_app import access_control
from scripts.manage_email_marketing import import_contacts


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.contacts = {}
        self.error_path = None
        self.rule = {}

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if self.error_path and self.error_path in path:
            raise ProviderError(503)
        if path.startswith('/templates/') and method == 'GET':
            return {'status': 'published', 'html': em.UNSUBSCRIBE}
        if path.startswith('/automations/') and method == 'GET':
            return self.rule
        if path.startswith('/contacts/') and method == 'GET':
            import urllib.parse
            address = urllib.parse.unquote(path[len('/contacts/'):])
            if address not in self.contacts:
                raise ProviderError(404)
            return self.contacts[address]
        if path == '/contacts':
            self.contacts[payload['email']] = {'id': 'contact-' + str(len(self.contacts)), 'unsubscribed': payload['unsubscribed']}
            return self.contacts[payload['email']]
        if path.endswith('/stop') or path.endswith('/send') or path == '/events/send':
            return {'id': 'accepted'}
        return {'id': 'provider-id'}


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite'
        self.env = patch.dict(os.environ, {'CHILLCRM_EMAIL_ENABLED': 'true',
            'CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED': 'true',
            'CHILLCRM_EMAIL_AUTOMATIONS_ENABLED': 'true', 'RESEND_API_KEY': 'synthetic-key',
            'RESEND_FROM': 'Tests <test@example.test>', 'RESEND_WEBHOOK_SECRET': 'synthetic-secret',
            'CHILLCRM_EMAIL_TEST_RECIPIENTS': 'test@example.test'}, clear=True)
        self.env.start()
        with self.db() as conn:
            conn.execute('CREATE TABLE people (id INTEGER PRIMARY KEY, email TEXT)')
            em.install(conn)
        self.client = FakeProvider()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def db(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def contact(self, address='one@example.test', status='subscribed'):
        with self.db() as c:
            em.upsert_contact(c, {'email': address, 'status': status, 'tags': ['Interested']}, 'synthetic opt-in')
            c.commit()

    def draft(self):
        with self.db() as c:
            em.action(c, {'action': 'campaign', 'name': 'Test <campaign>', 'subject': 'Hello', 'body': 'Hello <script>alert(1)</script>'}, {})
            return em.row(c, 'SELECT * FROM email_campaigns')['id']

    def ready(self, cid):
        with self.db() as c:
            em.enqueue(c, 'test', 'test-fixture', 'test@example.test', cid)
            c.execute("UPDATE email_outbox SET state = 'done' WHERE kind = 'test'")
            p = em.action(c, {'action': 'preview'}, {})
            em.action(c, {'action': 'queue_campaign', 'id': cid, 'fingerprint': p['fingerprint']}, {})

    def test_consent_and_provider_suppression_never_reactivate(self):
        self.contact(status='unsubscribed')
        self.contact()
        with self.db() as c:
            self.assertEqual(em.audience(c)['count'], 0)
        self.contact('two@example.test')
        self.client.contacts['two@example.test'] = {'id': 'two', 'unsubscribed': True}
        with self.db() as c:
            contact = em.row(c, 'SELECT * FROM email_contacts WHERE email = ?', ('two@example.test',))
            self.assertIsNone(em.sync_contact(c, self.client, contact))
            self.assertEqual(em.audience(c)['count'], 0)

    def test_default_test_mode_limits_audience_and_enrollment(self):
        self.contact()
        self.contact('test@example.test')
        with patch.dict(os.environ):
            os.environ.pop('CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED')
            with self.db() as c:
                preview = em.audience(c)
                self.assertEqual([r['email'] for r in preview['contacts']], ['test@example.test'])
                self.assertEqual(preview['excluded']['test_mode'], 1)
                c.execute("INSERT INTO people VALUES (1,'one@example.test'),(2,'test@example.test')")
                c.execute("INSERT INTO email_automations VALUES ('rule','Rule','flow','purchase','','evt',1,?)", (em.stamp(),))
                em.queue_crm_event(c, 1, 'purchase', 'customer-order')
                em.queue_crm_event(c, 2, 'purchase', 'test-order')
                c.commit()
                self.assertEqual(c.execute('SELECT count(*) FROM email_outbox').fetchone()[0], 1)
                self.assertEqual(em.row(c, 'SELECT email FROM email_outbox')['email'], 'test@example.test')
            # Removing approval after queueing must also stop dispatch.
            os.environ['CHILLCRM_EMAIL_TEST_RECIPIENTS'] = ''
            em.process_one(self.db, self.client)
            self.assertEqual(self.client.calls, [])
            with self.db() as c:
                self.assertEqual(em.row(c, 'SELECT state FROM email_outbox')['state'], 'cancelled')

    def test_switching_to_test_mode_blocks_queued_customer_broadcast(self):
        self.contact()
        cid = self.draft()
        self.ready(cid)
        with patch.dict(os.environ, {'CHILLCRM_EMAIL_CUSTOMER_SENDS_ENABLED': 'false'}):
            em.process_one(self.db, self.client)
        self.assertEqual(self.client.calls, [])
        with self.db() as c:
            self.assertEqual(em.row(c, "SELECT state FROM email_outbox WHERE kind='broadcast'")['state'], 'needs_review')

    def test_changed_identity_cancels_queued_autoresponder(self):
        self.contact()
        with self.db() as c:
            c.execute("INSERT INTO people VALUES (1,'one@example.test')")
            c.execute('UPDATE email_contacts SET person_id=1')
            c.execute("INSERT INTO email_automations VALUES ('rule','Rule','flow','purchase','','evt',1,?)", (em.stamp(),))
            em.queue_crm_event(c, 1, 'purchase', 'order')
            c.execute("UPDATE people SET email='changed@example.test' WHERE id=1")
            c.commit()
        em.process_one(self.db, self.client)
        self.assertEqual(self.client.calls, [])
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_outbox')['state'], 'cancelled')

    def test_broadcast_requires_test_and_current_audience(self):
        self.contact()
        cid = self.draft()
        with self.db() as c:
            with self.assertRaisesRegex(ValueError, 'test'):
                em.action(c, {'action': 'queue_campaign', 'id': cid}, {})
            em.enqueue(c, 'test', 'test-fixture', 'test@example.test', cid)
            c.execute("UPDATE email_outbox SET state = 'done'")
            with self.assertRaisesRegex(ValueError, 'Audience changed'):
                em.action(c, {'action': 'queue_campaign', 'id': cid, 'fingerprint': 'stale'}, {})
        self.ready(cid)
        self.assertTrue(em.process_one(self.db, self.client))
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_campaigns')['state'], 'sent')
        sent = [x for x in self.client.calls if x[1] == '/broadcasts']
        self.assertIn('&lt;script&gt;', sent[0][2]['html'])
        self.assertIn(em.UNSUBSCRIBE, sent[0][2]['html'])
        self.assertEqual(sum(x[1].endswith('/send') for x in self.client.calls), 1)
        self.assertFalse(em.process_one(self.db, self.client))

    def test_multi_batch_broadcast_stays_pending(self):
        for i in range(21):
            self.contact(f'person{i}@example.test')
        cid = self.draft()
        self.ready(cid)
        with patch.object(em.time, 'sleep'):
            em.process_one(self.db, self.client)
            with self.db() as c:
                self.assertEqual(em.row(c, "SELECT state FROM email_outbox WHERE kind = 'broadcast'")['state'], 'pending')
            self.assertFalse(any(x[1].endswith('/send') for x in self.client.calls))
            em.process_one(self.db, self.client)
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_campaigns')['state'], 'sent')

    def test_tag_enrollment_is_once_and_failed_submission_is_not_retried(self):
        self.contact()
        with self.db() as c:
            c.execute("INSERT INTO people VALUES (1, 'one@example.test')")
            em.action(c, {'action': 'automation', 'name': 'Welcome', 'provider_id': 'flow-1', 'trigger_kind': 'tag_added', 'tag': 'Interested'}, {})
            rule = em.row(c, 'SELECT * FROM email_automations')
            self.client.rule = {'status': 'enabled', 'steps': [{'type': 'trigger', 'config': {'event_name': rule['event_name']}}, {'type': 'send_email', 'config': {'template': {'id': 'template-1'}}}]}
            em.action(c, {'action': 'automation_toggle', 'id': rule['id'], 'enabled': True}, {}, self.client)
            em.queue_crm_event(c, 1, 'tag_added', 'event1', ['Interested'])
            em.queue_crm_event(c, 1, 'tag_added', 'event2', ['Interested'])
            c.commit()
            self.assertEqual(c.execute('SELECT count(*) FROM email_outbox').fetchone()[0], 1)
        self.client.error_path = '/events/send'
        em.process_one(self.db, self.client)
        self.assertFalse(em.process_one(self.db, self.client))
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_outbox')['state'], 'needs_review')

    def test_unsubscribe_before_dispatch_cancels_enrollment(self):
        self.contact()
        with self.db() as c:
            c.execute("INSERT INTO people VALUES (1, 'one@example.test')")
            c.execute("INSERT INTO email_automations VALUES ('rule', 'Rule', 'flow', 'purchase', '', 'evt', 1, ?)", (em.stamp(),))
            em.queue_crm_event(c, 1, 'purchase', 'order1')
            c.execute("UPDATE email_contacts SET status = 'unsubscribed'")
            c.commit()
        em.process_one(self.db, self.client)
        self.assertEqual(self.client.calls, [])
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_outbox')['state'], 'cancelled')

    def test_cancel_queued_campaign_cannot_send(self):
        self.contact()
        cid = self.draft()
        self.ready(cid)
        with self.db() as c:
            em.action(c, {'action': 'cancel_campaign', 'id': cid}, {})
        for _ in range(3):
            em.process_one(self.db, self.client)
        self.assertFalse(any(x[1].endswith('/send') for x in self.client.calls))

    def test_signature_replay_and_out_of_order_resubscribe(self):
        self.contact()
        key = b'synthetic-webhook-key'
        secret = 'whsec_' + base64.b64encode(key).decode()
        raw = json.dumps({'type': 'contact.updated', 'data': {'email': 'one@example.test', 'unsubscribed': True}}).encode()
        signed = b'event-1.1000.' + raw
        signature = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        headers = {'svix-id': 'event-1', 'svix-timestamp': '1000', 'svix-signature': 'v1,' + signature}
        event = verify_webhook(raw, headers, secret, now=1000)
        with self.assertRaises(ValueError):
            verify_webhook(raw + b' ', headers, secret, now=1000)
        with self.assertRaises(ValueError):
            verify_webhook(raw, headers, secret, now=1400)
        with self.db() as c:
            em.receive_webhook(c, event)
            self.assertTrue(em.receive_webhook(c, event)['duplicate'])
            em.receive_webhook(c, {'_verified_id': 'event-2', 'type': 'contact.updated', 'data': {'email': 'one@example.test', 'unsubscribed': False}})
            self.assertEqual(em.audience(c)['count'], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM email_events').fetchone()[0], 2)

    def test_provider_suppression_blocks_and_removal_never_resubscribes(self):
        for origin, expected in [('manual', 'unsubscribed'), ('bounce', 'bounced'), ('complaint', 'complained')]:
            address = origin + '@example.test'
            self.contact(address)
            with self.db() as c:
                em.receive_webhook(c, {'_verified_id': origin, 'type': 'suppression.added',
                                      'data': {'email': address, 'origin': origin}})
                em.receive_webhook(c, {'_verified_id': origin + '-removed', 'type': 'suppression.removed',
                                      'data': {'email': address}})
                em.receive_webhook(c, {'_verified_id': origin + '-suppressed', 'type': 'email.suppressed',
                                      'data': {'to': [address]}})
                self.assertEqual(em.row(c, 'SELECT status FROM email_contacts WHERE email=?', (address,))['status'], expected)

    def test_dispatcher_route_auth_methods_and_locks(self):
        h = CRMRequestHandler.__new__(CRMRequestHandler)
        h.path = '/api/email/dispatch'
        h.command = 'GET'
        h.headers = {}
        responses = []
        h.send_json = lambda data, status=200: responses.append(status)
        h.send_server_error = lambda exc: self.fail(str(exc))
        h.db = self.db
        h.should_block_remote_write = lambda path: False
        h.should_block_local_write = lambda path: False
        h.send_remote_write_locked = lambda path: responses.append(423)
        h.send_local_write_frozen = lambda path: responses.append(423)
        with patch.dict(os.environ, {'CRON_SECRET': 's' * 32}), patch.object(em, 'dispatch') as work:
            h.do_GET()
            self.assertEqual(responses[-1], 401)
            h.headers = {'Authorization': 'Bearer ' + 's' * 32}
            h.command = 'HEAD'
            h.do_HEAD()
            self.assertEqual(responses[-1], 405)
            h.command = 'GET'
            h.should_block_remote_write = lambda path: True
            h.do_GET()
            self.assertEqual(responses[-1], 423)
            h.should_block_remote_write = lambda path: False
            h.should_block_local_write = lambda path: True
            h.do_GET()
            self.assertEqual(responses[-1], 423)
            work.assert_not_called()
            h.should_block_local_write = lambda path: False
            work.return_value = {'ok': True}
            h.do_GET()
            work.assert_called_once_with(self.db)
        self.assertFalse(em.dispatch_authorized('Bearer '))
        self.assertIn(h.path, CRMRequestHandler.local_write_freeze_post_paths)

    def test_dispatcher_hosted_session_lock(self):
        os.environ['CHILLCRM_EMAIL_DISPATCH_ENABLED'] = 'true'
        keeper = MagicMock()
        keeper.execute.return_value.fetchone.return_value = [False]
        with patch.object(em, 'process_one', return_value=True) as work:
            self.assertTrue(em.dispatch(lambda: keeper)['busy'])
            work.assert_not_called()
            keeper.commit.assert_called_once()
            keeper.close.assert_called_once()
            keeper.reset_mock()
            keeper.execute.return_value.fetchone.return_value = [True]
            self.assertTrue(em.dispatch(lambda: keeper)['processed'])
            work.assert_called_once()
            keeper.commit.assert_called_once()
            keeper.close.assert_called_once()

    def test_dispatcher_bounded_overlap_and_failure(self):
        with patch.object(em, 'process_one', return_value=True) as work:
            self.assertTrue(em.dispatch(self.db)['disabled'])
            work.assert_not_called()
            os.environ['CHILLCRM_EMAIL_DISPATCH_ENABLED'] = 'true'
            em._DISPATCH_LOCK.acquire()
            try:
                self.assertTrue(em.dispatch(self.db)['busy'])
                work.assert_not_called()
            finally:
                em._DISPATCH_LOCK.release()
            self.assertTrue(em.dispatch(self.db)['processed'])
            work.assert_called_once()
            work.side_effect = RuntimeError('synthetic failure')
            with self.assertRaises(RuntimeError):
                em.dispatch(self.db)
            self.assertFalse(em._DISPATCH_LOCK.locked())

    def test_auth_and_write_lock_routes(self):
        self.assertEqual(access_control.POST_PERMISSION_ACTIONS['/api/email/action'], 'manage_email_marketing')
        self.assertNotIn('staff', access_control.ACTION_ROLE_PERMISSIONS['manage_email_marketing'])
        self.assertIn('/api/webhooks/resend', CRMRequestHandler.write_locked_post_paths)
        self.assertIn('/api/email/action', CRMRequestHandler.local_write_freeze_post_paths)
        h = CRMRequestHandler.__new__(CRMRequestHandler)
        h.path = '/api/email/action'
        h.post_origin_allowed = lambda: True
        h.current_auth_user = lambda: None
        h.should_require_auth_for_post = lambda p: True
        responses = []
        h.send_auth_required = lambda p: responses.append(401)
        h.do_POST()
        self.assertEqual(responses, [401])
        h.current_auth_user = lambda: {'roles': ['staff']}
        h.auth_required_enabled = lambda: True
        h.send_permission_denied = lambda *args: responses.append(403)
        h.do_POST()
        self.assertEqual(responses[-1], 403)

    def test_template_unsubscribe_is_required(self):
        with self.db() as c:
            em.action(c, {'action': 'automation', 'name': 'Unsafe template', 'provider_id': 'flow', 'trigger_kind': 'purchase'}, {})
            rule = em.row(c, 'SELECT * FROM email_automations')
            self.client.rule = {'status': 'enabled', 'steps': [
                {'type': 'trigger', 'config': {'event_name': rule['event_name']}},
                {'type': 'send_email', 'config': {'template': {'id': 'bad-template'}}}]}
            original = self.client.request
            def unsafe(method, path, payload=None):
                return {'status': 'published', 'html': 'Missing footer'} if path.startswith('/templates/') else original(method, path, payload)
            self.client.request = unsafe
            with self.assertRaisesRegex(ValueError, 'unsubscribe'):
                em.action(c, {'action': 'automation_toggle', 'id': rule['id'], 'enabled': True}, {}, self.client)
            self.assertFalse(em.row(c, 'SELECT enabled FROM email_automations')['enabled'])

    def test_ambiguous_broadcast_send_is_not_repeated(self):
        self.contact()
        cid = self.draft()
        self.ready(cid)
        self.client.error_path = '/send'
        em.process_one(self.db, self.client)
        self.assertFalse(em.process_one(self.db, self.client))
        with self.db() as c:
            self.assertEqual(em.row(c, "SELECT state FROM email_outbox WHERE kind = 'broadcast'")['state'], 'needs_review')
        self.assertEqual(sum(x[1].endswith('/send') for x in self.client.calls), 1)

    def test_definite_rate_limit_allows_safe_retry(self):
        self.contact()
        cid = self.draft()
        self.ready(cid)
        original = self.client.request
        attempted = []
        def limited(method, path, payload=None):
            if path.endswith('/send') and not attempted:
                attempted.append(True)
                raise ProviderError(429)
            return original(method, path, payload)
        self.client.request = limited
        em.process_one(self.db, self.client)
        with self.db() as c:
            self.assertEqual(em.row(c, "SELECT state FROM email_outbox WHERE kind = 'broadcast'")['state'], 'pending')
        em.process_one(self.db, self.client)
        with self.db() as c:
            self.assertEqual(em.row(c, 'SELECT state FROM email_campaigns')['state'], 'sent')

    def test_import_enriches_blanks_and_skips_ambiguous_and_unknown(self):
        archive = Path(self.tmp.name) / 'merge-archive'
        archive.mkdir()
        fixture = {'contacts': [
            {'id': 'a', 'email': 'one@example.test', 'firstName': 'Source', 'lastName': 'Added', 'phone': '555-0100'},
            {'id': 'b', 'email': 'duplicate@example.test'},
            {'id': 'c', 'email': 'unknown@example.test'}],
            'contactLists': [{'contact': 'a', 'status': '1'}, {'contact': 'b', 'status': '1'}],
            'tags': [], 'contactTags': []}
        manifest = {'collections': {}}
        for name, values in fixture.items():
            (archive / name).mkdir()
            (archive / name / '000.json').write_text(json.dumps({name: values}))
            manifest['collections'][name] = {'status': 'complete', 'key': name}
        (archive / 'manifest.json').write_text(json.dumps(manifest))
        class Handler:
            def tags_for(self, *a): return []
            def insert_audit_log(self, *a, **kw): pass
        with self.db() as c:
            for field in ('first_name', 'last_name', 'phone', 'updated_at'):
                c.execute('ALTER TABLE people ADD COLUMN ' + field + ' TEXT')
            c.execute("INSERT INTO people (id,email,first_name) VALUES (1,'one@example.test','Operator')")
            c.execute("INSERT INTO people (id,email) VALUES (2,'duplicate@example.test'),(3,'duplicate@example.test')")
            preview = import_contacts(Handler(), c, archive)
            self.assertEqual(preview['blank_fields_filled'], 2)
            self.assertIsNone(em.row(c, 'SELECT phone FROM people WHERE id = 1')['phone'])
            result = import_contacts(Handler(), c, archive, apply=True)
            self.assertEqual(result['skipped_ambiguous'], 1)
            self.assertEqual(result['skipped_unknown'], 1)
            person = em.row(c, 'SELECT * FROM people WHERE id = 1')
            self.assertEqual((person['first_name'], person['last_name'], person['phone']), ('Operator', 'Added', '555-0100'))
            self.assertEqual(c.execute('SELECT count(*) FROM email_contacts').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM people').fetchone()[0], 3)
            again = import_contacts(Handler(), c, archive, apply=True)
            self.assertEqual(again['blank_fields_filled'], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM email_outbox').fetchone()[0], 0)

    def test_import_is_conservative_repeatable_and_silent(self):
        archive = Path(self.tmp.name) / 'archive'
        archive.mkdir()
        fixture = {'contacts': [{'id': 'ac1', 'email': 'one@example.test', 'firstName': 'One'},
                                {'id': 'ac2', 'email': 'absent@example.test'}],
            'contactLists': [{'contact': 'ac1', 'status': '1'}, {'contact': 'ac1', 'status': '2'},
                             {'contact': 'ac2', 'status': '2'}],
            'tags': [{'id': 'tag1', 'tag': 'Interested'}], 'contactTags': [{'id': 'link1', 'contact': 'ac1', 'tag': 'tag1'}]}
        manifest = {'collections': {}}
        for name, values in fixture.items():
            (archive / name).mkdir()
            (archive / name / '000.json').write_text(json.dumps({name: values}))
            manifest['collections'][name] = {'status': 'complete', 'key': name}
        (archive / 'manifest.json').write_text(json.dumps(manifest))
        class ImportHandler:
            def ensure_tag(self, c, name): return 1
            def tags_for(self, *a): return ['Existing CRM tag']
            def next_hosted_primary_key(self, *a): return None
            def insert_audit_log(self, *a, **kw): pass
        with self.db() as c:
            c.execute("INSERT INTO people VALUES (1, 'one@example.test')")
            c.execute('CREATE TABLE tag_assignments (id INTEGER PRIMARY KEY, tag_id INTEGER, record_type TEXT, record_id INTEGER, source_name TEXT)')
            for _ in range(2):
                result = import_contacts(ImportHandler(), c, archive, apply=True)
                self.assertEqual(result['suppressed'], 2)
                self.assertEqual(result['skipped_suppressed'], 2)
                self.assertEqual(result['matched_people'], 0)
                self.assertEqual(result['new_people'], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM people').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM email_contacts').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT email FROM people WHERE id = 1').fetchone()[0], 'one@example.test')
            self.assertIsNone(em.row(c, 'SELECT * FROM email_contacts WHERE email = ?', ('absent@example.test',)))
            self.assertEqual(em.audience(c)['count'], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM email_outbox').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM tag_assignments').fetchone()[0], 0)
            policy = {'authorization': 'Synthetic owner-approved internal group unsubscribe',
                'internal_unsubscribe_exceptions': [{'source_id': 'ac1', 'email': 'one@example.test', 'list_ids': ['internal']}]}
            # No exception for another list or another contact.
            self.assertEqual(import_contacts(ImportHandler(), c, archive, consent_policy=policy)['skipped_suppressed'], 2)
            policy['internal_unsubscribe_exceptions'][0]['list_ids'] = ['']
            # Fixture memberships have no list ID; add one explicitly.
            fixture['contactLists'][1]['list'] = 'internal'
            (archive / 'contactLists' / '000.json').write_text(json.dumps({'contactLists': fixture['contactLists']}))
            policy['internal_unsubscribe_exceptions'][0]['list_ids'] = ['internal']
            approved = import_contacts(ImportHandler(), c, archive, apply=True, consent_policy=policy)
            self.assertEqual(approved['subscribed'], 1)
            self.assertEqual(approved['skipped_suppressed'], 1)
            self.assertEqual(em.row(c, 'SELECT status FROM email_contacts')['status'], 'subscribed')
            self.assertIn('Existing CRM tag', json.loads(em.row(c, 'SELECT tags_json FROM email_contacts')['tags_json']))
            self.assertIsNone(em.row(c, 'SELECT * FROM email_contacts WHERE email = ?', ('absent@example.test',)))


if __name__ == '__main__':
    unittest.main()
