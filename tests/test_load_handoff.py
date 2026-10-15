"""A load's business_sync starts from the read's own parse (Store.command `own`, business.on_load_result own=True).

GET /api/state reads the save (Store.read) and, when staff work is due, runs the internal business_sync. That
command used to fetch and parse the same save a second time; it now takes over the read's parse when the save is
still at that revision, and reads as before in every other case. The stored save and the view are the same.
"""
import copy
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import business, operations as ops, storage
from game.engine import validate_state
from game.storage import Store
from tests.helpers import Journey

FORMAT = 'mot-ngay-lam-nghe/save-v4'


class LoadHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'handoff')
        j = Journey('accounting')
        with patch('game.business.time.time', return_value=2000000000):
            ops.action(j.state, j.c, 'accounting', 'ops_hire', {'candidate': 'accounting-staff-1', 'confirm': True})
        self.at = min(p['at'] for p in j.c['ops']['business']['pending'].values())
        validate_state(j.state)
        self.tokens = []
        for i in range(2):  # two saves, the same game: one synced the old way, one with the handoff
            token, _, _ = self.store.session()
            self.store.command(token, 'import-handoff', 0, None, 'import_save', {'save': {'format': FORMAT, 'state': copy.deepcopy(j.state)}})
            self.tokens.append(token)

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def stored(self, token):
        sid = self.store.key(token)
        with self.store.connect() as db:
            row = db.execute('SELECT state,revision FROM sessions WHERE sid=?', (sid,)).fetchone()
        return row['state'], row['revision']

    def sync(self, token, own, between=None, hand=None):
        """read, then the load's sync; returns (the sync's answer, saves parsed by the sync)."""
        state, _, _ = self.store.read(token)
        if between:
            between()
        parsed = []
        real = storage.Store.parse_state

        def counted(store, text, sid):
            parsed.append(sid)
            return real(store, text, sid)
        with patch.object(storage.Store, 'parse_state', counted):
            out = business.on_load_result(self.store, token, hand(state) if hand else state, own=own)
        return out, len(parsed)

    def test_handoff_gives_the_same_save_and_view_without_a_second_parse(self):
        with patch('game.business.time.time', return_value=self.at):
            plain, n_plain = self.sync(self.tokens[0], False)
            kept, n_kept = self.sync(self.tokens[1], True)
        self.assertEqual(n_plain, 1)
        self.assertEqual(n_kept, 0)  # the read's parse was used
        self.assertEqual(plain['state'], kept['state'])
        self.assertEqual(plain['result'], kept['result'])
        self.assertEqual(plain['revision'], kept['revision'])
        self.assertEqual(self.stored(self.tokens[0]), self.stored(self.tokens[1]))
        self.assertEqual(kept['state']['careers']['accounting']['ops']['business']['served'], 1)

    def test_a_save_that_moved_since_the_read_is_read_again(self):
        def bump(token):
            return lambda: self.store.command(token, 'bump-' + token[:12], self.stored(token)[1], None, 'settings', {'musicVolume': 12})
        with patch('game.business.time.time', return_value=self.at):
            plain, _ = self.sync(self.tokens[0], False, between=bump(self.tokens[0]))
            kept, n_kept = self.sync(self.tokens[1], True, between=bump(self.tokens[1]))
        self.assertEqual(n_kept, 1)  # the stored save of the newer revision, parsed as usual
        self.assertEqual(plain['state'], kept['state'])
        self.assertEqual(self.stored(self.tokens[0]), self.stored(self.tokens[1]))
        self.assertEqual(kept['state']['settings']['musicVolume'], 12)

    def test_only_the_object_the_read_returned_is_taken_over(self):
        with patch('game.business.time.time', return_value=self.at):
            plain, _ = self.sync(self.tokens[0], False)
            kept, n_kept = self.sync(self.tokens[1], True, hand=copy.deepcopy)
        self.assertEqual(n_kept, 1)
        self.assertEqual(plain['state'], kept['state'])
        self.assertEqual(self.stored(self.tokens[0]), self.stored(self.tokens[1]))

    def test_a_handoff_is_used_once(self):
        state, _, _ = self.store.read(self.tokens[1])
        with patch('game.business.time.time', return_value=self.at):
            business.on_load_result(self.store, self.tokens[1], state, own=True)
            # the same object again (it was changed by the first sync): never taken over twice
            parsed = []
            real = storage.Store.parse_state
            with patch.object(storage.Store, 'parse_state', lambda store, text, sid: parsed.append(sid) or real(store, text, sid)):
                out = self.store.command(self.tokens[1], 'business-again-1', None, None, business.ACTION, {}, internal=True, own=state)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(out['state']['careers']['accounting']['ops']['business']['served'], 1)

    def test_http_state_settles_from_its_read(self):
        from server import GameServer
        server = GameServer(('127.0.0.1', 0), self.store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch('game.business.time.time', return_value=self.at):
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                with patch.object(self.store, 'parse_state', wraps=self.store.parse_state) as parses:
                    conn.request('GET', '/api/state', headers={'Cookie': 'mnl_session=' + self.tokens[1]})
                    response = conn.getresponse()
                    body = json.loads(response.read())
                    conn.close()
                self.assertEqual(response.status, 200, body)
                self.assertEqual(parses.call_count, 1)  # the read's; the sync took it over
                self.assertEqual(body['state']['careers']['accounting']['ops']['business']['served'], 1)
                self.assertEqual(body['revision'], self.stored(self.tokens[1])[1])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
