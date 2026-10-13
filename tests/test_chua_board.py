"""Explicit temple-card publication: private by default, owner-only and transactional."""
import copy
import http.client
import importlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from game import chua, pg_schema
from game.engine import GameError, validate_state
from game.storage import Store
from tests.test_chua import story, do


def board():
    return importlib.import_module('game.chua_board')


class CardVisibilityReducer(unittest.TestCase):
    def test_default_private_explicit_public_and_capability(self):
        for visibility in (None, False, True):
            payload = dict(act='nguyen', recipient='ca_nha', blessing='may_man')
            if visibility is not None:
                payload['public'] = visibility
            state, result = do(story(), **payload)
            card = state['journey']['chua']['cards'][-1]
            self.assertEqual(result['chua_card'], dict(id=card['id'], public=visibility is True))
            self.assertNotIn('public', card, 'canonical backups never carry publication authority')
            self.assertTrue(chua.public(state)['sharing'])
            validate_state(state)

    def test_visibility_is_boolean_and_only_for_cards(self):
        for value in ('public', 1, 0, [], {}, None):
            state = story()
            before = copy.deepcopy(state)
            with self.assertRaises(GameError):
                do(state, act='nguyen', wish='nha', public=value)
            self.assertEqual(state, before)
        with self.assertRaises(GameError):
            do(story(), act='huong', public=True)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL') and not os.environ.get('DATABASE_URL'),
                     'requires isolated TEST_DATABASE_URL without DATABASE_URL')
class CardBoardFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'temple.db')
        self.addCleanup(self.store.close_pool)
        self.owner, self.csrf, _ = self.store.session()
        self.other, self.other_csrf, _ = self.store.session()
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(story()), self.store.key(self.owner)))
        self.rev = 0

    def create(self, public=None):
        p = dict(act='nguyen', recipient='ca_nha', blessing='may_man', name='Mẹ', message='Mong mẹ vui khỏe.')
        if public is not None:
            p['public'] = public
        out = self.store.command(self.owner, f'card-create-{self.rev:05d}', self.rev, None, 'jr_chua_do', p)
        self.rev = out['revision']
        return out['state']['chua']['cards'][-1], out, p


class CardBoardStore(CardBoardFixture):
    def test_only_explicit_publish_is_visible_and_replay_does_not_republish(self):
        private, _, _ = self.create()
        explicit_private, _, _ = self.create(False)
        public, out, payload = self.create(True)
        page = board().page(self.store, self.other)
        self.assertEqual([r['id'] for r in page['rows']], [public['id']])
        self.assertNotIn(self.store.key(self.owner), json.dumps(page))
        self.assertNotIn('sid', page['rows'][0])
        self.assertEqual(page['rows'][0]['message'], public['message'])
        mine = board().page(self.store, self.owner, scope='mine')
        self.assertEqual([r['public'] for r in mine['rows']], [True, False, False])
        board().set_visibility(self.store, self.owner, dict(id=public['id'], public=False))
        replay = self.store.command(self.owner, 'card-create-00002', 2, None, 'jr_chua_do', payload)
        self.assertTrue(replay['replayed'])
        self.assertEqual(board().page(self.store, self.other)['rows'], [])
        self.assertNotEqual(private['id'], explicit_private['id'])

    def test_owner_toggle_is_idempotent_and_others_cannot_change_or_read_private(self):
        card, _, _ = self.create(False)
        for public in (True, False):
            with self.assertRaises(GameError):
                board().set_visibility(self.store, self.other, dict(id=card['id'], public=public))
        self.assertEqual(board().page(self.store, self.other, scope='mine')['rows'], [])
        for public in (True, True, False, False, True):
            result = board().set_visibility(self.store, self.owner, dict(id=card['id'], public=public))
            self.assertEqual(result, dict(id=card['id'], public=public))
            self.assertEqual(len(board().page(self.store, self.other)['rows']), int(public))
        self.assertEqual(self.store.read(self.owner)[1], self.rev)

    def test_archived_cards_support_cursor_and_no_cursor_toggle(self):
        cards = [self.create(i == 0)[0] for i in range(43)]
        first = board().page(self.store, self.owner, scope='mine', limit=40)
        self.assertEqual(len(first['rows']), 40)
        old = board().page(self.store, self.owner, scope='mine', before=first['before'], limit=40)
        self.assertEqual([r['id'] for r in old['rows']], [r['id'] for r in reversed(cards[:3])])
        for row in old['rows']:
            board().set_visibility(self.store, self.owner, dict(id=row['id'], public=True, position=row['position']))
        self.assertEqual(len(board().page(self.store, self.other)['rows']), 3)

        board().set_visibility(self.store, self.owner, dict(id=cards[0]['id'], public=False))
        board().set_visibility(self.store, self.owner, dict(id=cards[0]['id'], public=True))
        self.assertEqual(len(board().page(self.store, self.other)['rows']), 3)

    def test_owner_pagination_is_consistent_during_concurrent_archive_rollover(self):
        from game.db import PgConnection
        cards = [self.create(False)[0] for _ in range(40)]
        original_execute = PgConnection.execute
        fired = []
        def execute(db, sql, *args, **kw):
            if not fired and 'COALESCE(MAX(seq)+1,0)' in sql and 'archive WHERE' in sql:
                fired.append(True)
                self.create(False)
            return original_execute(db, sql, *args, **kw)
        with mock.patch.object(PgConnection, 'execute', execute):
            mine = board().page(self.store, self.owner, scope='mine', limit=50)
        self.assertEqual(len({r['id'] for r in mine['rows']}), len(mine['rows']))
        self.assertEqual(mine['total'], 40)
        oldest = mine['rows'][-1]
        self.assertEqual((oldest['id'], oldest['position']), (cards[0]['id'], 0))
        board().set_visibility(self.store, self.owner, dict(id=oldest['id'], position=oldest['position'], public=True))

    def test_paging_queries_are_strict_and_no_private_ids_leak(self):
        published = [self.create(True)[0] for _ in range(3)]
        hidden, _, _ = self.create(False)
        first = board().page(self.store, self.other, limit=2)
        last = board().page(self.store, self.other, before=first['before'], limit=2)
        self.assertEqual([r['id'] for r in first['rows'] + last['rows']], [r['id'] for r in reversed(published)])
        self.assertIsNone(last['before'])
        self.assertNotIn(hidden['id'], json.dumps(first) + json.dumps(last))
        for kw in (dict(scope='all'), dict(limit=0), dict(limit=51), dict(limit=True), dict(before=-1),
                   dict(before=True), dict(before='1'), dict(before=2**63)):
            with self.assertRaises(GameError, msg=kw):
                board().page(self.store, self.owner, **kw)
        for patch in (dict(id=[]), dict(id='x'), dict(public=1), dict(public='false'), dict(public=None),
                      dict(position=True), dict(position=-1), dict(position=2**63), dict(sid='other')):
            with self.assertRaises(GameError, msg=patch):
                board().set_visibility(self.store, self.owner, dict(id=hidden['id'], public=True) | patch)
        with self.assertRaises(GameError):
            board().page(self.store, 'x'*64)

    def test_public_query_uses_projection_without_reading_any_save_or_archive(self):
        self.create(True)
        with mock.patch.object(self.store, 'read', side_effect=AssertionError('read save')), \
             mock.patch.object(self.store, 'archive_page', side_effect=AssertionError('read archive')):
            self.assertEqual(len(board().page(self.store, self.other)['rows']), 1)

    def test_untrusted_imported_archive_rows_cannot_break_mine_or_publish(self):
        card, _, _ = self.create(False)
        with self.store.connect() as db:
            for pos, row in enumerate(({'id': []}, card | {'public': True})):
                db.execute('INSERT INTO archive(sid,career,kind,seq,day,row) VALUES(?,?,?,?,?,?)',
                           (self.store.key(self.owner), '', 'chua.cards', pos, 1, json.dumps(row)))
        mine = board().page(self.store, self.owner, scope='mine')
        self.assertEqual(len(mine['rows']), 1)
        self.assertFalse(mine['rows'][0]['public'])
        self.assertEqual(board().page(self.store, self.other)['rows'], [])

    def test_failed_commit_rolls_back_publication_and_receipt(self):
        real = board().command_commit
        def fail(*a, **kw):
            real(*a, **kw)
            raise RuntimeError('rollback publication')
        with mock.patch.object(board(), 'command_commit', side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.create(True)
        self.assertEqual(self.store.read(self.owner)[1], 0)
        self.assertEqual(board().page(self.store, self.other)['rows'], [])
        self.create(True)
        self.assertEqual(len(board().page(self.store, self.other)['rows']), 1)

    def test_locked_command_path_publishes_once(self):
        with mock.patch('game.storage.OPTIMISTIC_TRIES', 0):
            card, _, _ = self.create(True)
        self.assertEqual(board().page(self.store, self.other)['rows'][0]['id'], card['id'])

    def test_import_reset_and_delete_revoke_and_never_auto_publish(self):
        card, _, _ = self.create(True)
        state, _, _ = self.store.read(self.owner)
        out = self.store.command(self.owner, 'import-card-001', self.rev, None, 'import_save',
                                 dict(save=dict(format='mot-ngay-lam-nghe/save-v4', state=state)))
        self.rev = out['revision']
        self.assertEqual(board().page(self.store, self.other)['rows'], [])
        self.assertFalse(board().page(self.store, self.owner, scope='mine')['rows'][0]['public'])
        board().set_visibility(self.store, self.owner, dict(id=card['id'], public=True))
        out = self.store.command(self.owner, 'reset-card-001', self.rev, None, 'reset_all', dict(confirm='BAT DAU LAI'))
        self.rev = out['revision']
        self.assertEqual(board().page(self.store, self.other)['rows'], [])
        self.create(True)
        self.store.delete(self.owner)
        self.assertEqual(board().page(self.store, self.other)['rows'], [])

    def test_schema_upgrade_is_additive_idempotent_and_does_not_publish_old_cards(self):
        self.create(False)
        with self.store.connect() as db:
            db.execute('DROP TABLE chua_public_cards')
            db.execute("UPDATE mnl_meta SET value='41' WHERE key='schema_version'")
        with self.store.connect() as db:
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(pg_schema.ensure(db))
            self.assertEqual(db.execute('SELECT count(*) FROM chua_public_cards').fetchone()[0], 0)
            indexes = list(db.execute("SELECT indexdef FROM pg_indexes WHERE tablename='chua_public_cards' AND schemaname=current_schema()"))
            self.assertEqual(len(indexes), 2)
        self.assertEqual(len(board().page(self.store, self.owner, scope='mine')['rows']), 1)


class CardBoardHTTP(CardBoardFixture):
    def test_http_auth_csrf_strict_query_and_immediate_revoke(self):
        from server import GameServer
        server = GameServer(('127.0.0.1', 0), self.store)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, token=None, method='GET', payload=None, csrf=None, origin=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Cookie'] = 'mnl_session=' + token
            if csrf:
                headers['X-Game-CSRF'] = csrf
            if origin:
                headers['Origin'] = origin
            con = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            con.request(method, path, json.dumps(payload) if payload is not None else None, headers)
            response = con.getresponse()
            result = response.status, dict(response.getheaders()), response.read()
            con.close()
            return result
        card, _, _ = self.create(False)
        path = '/api/chua/cards/visibility'
        payload = dict(id=card['id'], public=True)
        self.assertEqual(request('/api/chua/cards')[0], 401)
        self.assertEqual(request(path, self.owner, 'POST', payload)[0], 403)
        self.assertEqual(request(path, self.owner, 'POST', payload, self.csrf, 'https://attacker.example')[0], 403)
        self.assertEqual(request(path, self.other, 'POST', payload, self.other_csrf)[0], 400)
        self.assertEqual(request(path, self.owner, 'POST', payload, self.csrf)[0], 200)
        status, headers, raw = request('/api/chua/cards?scope=public', self.other)
        self.assertEqual(status, 200, raw)
        self.assertEqual(headers.get('Cache-Control'), 'no-store')
        self.assertEqual(json.loads(raw)['rows'][0]['id'], card['id'])
        for query in ('limit=0', 'limit=51', 'limit=true', 'limit=1&limit=2', 'scope=other', 'before=-1', 'before=', 'sid=other'):
            self.assertEqual(request('/api/chua/cards?'+query, self.owner)[0], 400, query)
        with mock.patch('server.jail.marked_token', return_value=True):
            self.assertEqual(request(path, self.owner, 'POST', payload | {'public': False}, self.csrf)[0], 200,
                             'privacy withdrawal stays available while jailed')
        self.assertEqual(json.loads(request('/api/chua/cards', self.other)[2])['rows'], [])

