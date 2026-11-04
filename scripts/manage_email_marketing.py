#!/usr/bin/env python3
"""Explicit email schema setup, consent import, and bounded outbox processing.

Defaults to a dry run. Never reads .env files or writes production implicitly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from crm_app import email_marketing as email
from crm_app.server import CRMRequestHandler


def import_contacts(handler, conn, archive, apply=False, consent_policy=None):
    manifest = json.loads((archive / 'manifest.json').read_text())
    def load(name):
        entry = manifest['collections'].get(name, {})
        if entry.get('status') != 'complete':
            raise ValueError('Import requires a verified ' + name + ' collection.')
        return [r for p in sorted((archive / name).glob('*.json'))
                for r in json.loads(p.read_text()).get(entry['key'], [])]
    contacts, memberships = load('contacts'), load('contactLists')
    approvals = {}
    if consent_policy and not str(consent_policy.get('authorization') or '').strip():
        raise ValueError('Consent exceptions require an explicit owner authorization record.')
    for approval in (consent_policy or {}).get('internal_unsubscribe_exceptions', []):
        key = (str(approval['source_id']), email.email_address(approval['email']))
        approvals[key] = {str(value) for value in approval['list_ids']}
    tags = {str(x['id']): x['tag'] for x in load('tags')}
    tag_map, lists = {}, {}
    for item in load('contactTags'):
        tag_map.setdefault(str(item['contact']), []).append(tags.get(str(item['tag']), ''))
    for item in memberships:
        lists.setdefault(str(item['contact']), []).append(item)
    report = {'contacts': 0, 'subscribed': 0, 'suppressed': 0, 'unknown': 0,
              'matched_people': 0, 'new_people': 0, 'ambiguous_matches': 0, 'invalid_email': 0,
              'skipped_suppressed': 0, 'skipped_unknown': 0, 'skipped_ambiguous': 0,
              'blank_fields_filled': 0}
    existing_statuses = {r['email']: r['status'] for r in email.rows(conn, 'SELECT email, status FROM email_contacts')} if email.installed(conn) else {}
    people_by_email = {}
    for person in email.rows(conn, 'SELECT * FROM people'):
        people_by_email.setdefault(str(person.get('email') or '').strip().lower(), []).append(person)
    seen = set()
    for item in contacts:
        try:
            address = email.email_address(item.get('email'))
        except ValueError:
            report['invalid_email'] += 1
            continue
        if address in seen:
            raise ValueError('Duplicate source email; reconcile before importing.')
        seen.add(address)
        sid = str(item['id'])
        subscriptions = lists.get(sid, [])
        # Owner-approved exceptions are exact source-contact/email/list matches,
        # never a blanket resubscription of everyone on an internal list.
        internal_lists = approvals.get((sid, address), set())
        email_lists = [x for x in subscriptions
                       if str(x.get('channel', 'email')).lower() in {'email', '1', ''}]
        ignored = [x for x in email_lists if str(x.get('status')) == '2' and str(x.get('list')) in internal_lists]
        statuses = {str(x.get('status')) for x in email_lists
                    if not (str(x.get('status')) == '2' and str(x.get('list')) in internal_lists)}
        desired = 'bounced' if '3' in statuses else 'unsubscribed' if '2' in statuses else 'subscribed' if '1' in statuses or ignored else 'unknown'
        if str(item.get('bounced_hard') or '0') not in {'0', '', 'None'}:
            desired = 'bounced'
        if existing_statuses.get(address) in email.BLOCKED:
            desired = existing_statuses[address]
        # Suppressed source contacts stay exclusively in the legacy archive.
        # Skip before matching or changing any existing CRM records or tags.
        if desired in email.BLOCKED:
            report['contacts'] += 1
            report['suppressed'] += 1
            report['skipped_suppressed'] += 1
            continue
        if desired != 'subscribed':
            report['contacts'] += 1
            report['unknown'] += 1
            report['skipped_unknown'] += 1
            continue
        matches = people_by_email.get(address, [])
        if len(matches) > 1:
            report['ambiguous_matches'] += 1
            report['skipped_ambiguous'] += 1
            report['contacts'] += 1
            report['unknown'] += 1
            continue
        elif matches:
            report['matched_people'] += 1
            person_id = matches[0]['id']
            # Enrich only blanks; never replace an operator's existing values.
            for field, source_field in (('first_name', 'firstName'), ('last_name', 'lastName'), ('phone', 'phone')):
                value = str(item.get(source_field) or '').strip()
                if field in matches[0] and not str(matches[0][field] or '').strip() and value:
                    report['blank_fields_filled'] += 1
                    if apply:
                        conn.execute(f'UPDATE people SET {field} = ?, updated_at = ? WHERE id = ?', (value, email.stamp(), person_id))
        else:
            report['new_people'] += 1
            person_id = None
            if apply:
                person_id = handler.create_person(conn, {'first_name': item.get('firstName'),
                    'last_name': item.get('lastName'), 'name': ' '.join(str(item.get(k) or '') for k in ('firstName', 'lastName')).strip() or address,
                    'email': address, 'phone': item.get('phone')}, email.stamp())
        report['contacts'] += 1
        report['subscribed' if desired == 'subscribed' else 'suppressed' if desired in email.BLOCKED else 'unknown'] += 1
        if apply:
            merged_tags = [t for t in tag_map.get(sid, []) if t]
            if person_id is not None:
                merged_tags += handler.tags_for(conn, 'person', person_id)
            previous = email.row(conn, 'SELECT tags_json FROM email_contacts WHERE email = ?', (address,))
            if previous:
                merged_tags += json.loads(previous['tags_json'])
            email.upsert_contact(conn, {'email': address, 'person_id': person_id,
                'first_name': item.get('firstName'), 'last_name': item.get('lastName'),
                'tags': merged_tags, 'status': desired},
                {'provider': 'activecampaign', 'source_id': sid, 'lists': subscriptions,
                 'internal_unsubscribe_exception': sorted(internal_lists) if ignored else [],
                 'policy_authorization': (consent_policy or {}).get('authorization') if ignored else None}, imported=True)
            # Preserve existing CRM tags and add imported assignments. No call to
            # update_tags: an import must never emit tag-added automation events.
            if person_id is not None:
                for name in tag_map.get(sid, []):
                    if not name:
                        continue
                    tid = handler.ensure_tag(conn, name)
                    if not conn.execute("SELECT 1 FROM tag_assignments WHERE record_type = 'person' AND record_id = ? AND tag_id = ?", (person_id, tid)).fetchone():
                        aid = handler.next_hosted_primary_key(conn, 'tag_assignments')
                        if aid is None:
                            conn.execute("INSERT INTO tag_assignments (tag_id, record_type, record_id, source_name) VALUES (?, 'person', ?, ?)", (tid, person_id, name))
                        else:
                            conn.execute("INSERT INTO tag_assignments (id, tag_id, record_type, record_id, source_name) VALUES (?, ?, 'person', ?, ?)", (aid, tid, person_id, name))
    if apply:
        handler.insert_audit_log(conn, action='import_activecampaign_email', record_type='email',
            note=json.dumps(report), permission_action='manage_email_marketing')
        conn.commit()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['setup', 'import', 'process'])
    parser.add_argument('--db', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--consent-policy', type=Path, help='Private owner-approved exact-contact internal-list exceptions')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--hosted', action='store_true', help='Explicitly select the environment-configured hosted database')
    parser.add_argument('--max-jobs', type=int, default=1)
    args = parser.parse_args()
    h = CRMRequestHandler.__new__(CRMRequestHandler)
    if args.hosted:
        if not h.hosted_postgres_adapter_enabled() or args.db:
            parser.error('Hosted mode requires the configured hosted adapter and no --db.')
    else:
        if h.hosted_postgres_adapter_enabled():
            parser.error('Hosted adapter is configured. Explicit --hosted is required.')
        if not args.db or not args.db.is_file():
            parser.error('An existing local database must be selected explicitly with --db.')
        h.db_path = args.db
    if args.apply and (h.remote_write_lock_enabled() or h.local_write_freeze_enabled()):
        parser.error('CRM writes are locked. Resolve the lock through the owner-approved workflow.')
    if args.operation == 'setup':
        with h.db() as conn:
            if args.apply:
                email.install(conn)
            print(json.dumps({'installed': email.installed(conn), 'applied': args.apply}))
    elif args.operation == 'import':
        if not args.archive:
            parser.error('--archive is required.')
        with h.db() as conn:
            if args.apply and not email.installed(conn):
                parser.error('Run email schema setup first.')
            policy = json.loads(args.consent_policy.read_text()) if args.consent_policy else None
            print(json.dumps(import_contacts(h, conn, args.archive, args.apply, policy)))
    else:
        if not args.apply:
            print('Dry run: no provider requests. Use --apply only after activation and sending approval.')
            return
        if not 1 <= args.max_jobs <= 100:
            parser.error('--max-jobs must be between 1 and 100.')
        done = 0
        for _ in range(args.max_jobs):
            if not email.process_one(h.db):
                break
            done += 1
        print(json.dumps({'jobs_processed': done}))


if __name__ == '__main__':
    main()
