"""🎈 Rewards of the live service paid into the save (game/live_effects.py, /api/bootstrap): a date's tinh thần and
a red envelope's xu land once, whatever the retries, tabs or a crash between the two writes; only story saves are
paid; a client can never send the internal action."""
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import live_effects as lfx
from game import life
from game.engine import GameError, validate_state
from game.storage import Store
from server import GameServer


class LiveEffectsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        self.tok, _, _ = self.store.session()
        self.sid = self.store.key(self.tok)

    def state(self):
        return self.store.read(self.tok)[0]

    def add(self, eid, kind='spirit', amount=5, data=None, sid=None):
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, ?, ?, ?, 'pending', ?)",
            (eid, sid or self.sid, kind, amount, json.dumps(data or {}), time.time())))

    def status(self, eid):
        with self.store.connect() as db:
            return db.execute('SELECT status FROM live_effects WHERE id=?', (eid,)).fetchone()[0]

    def spirit(self):
        return life._state(self.state())['spirit']

    def test_spirit_paid_once(self):
        start = self.spirit()
        self.add('date:abc123abc123:aaaaaaaaaaaaaaaa')
        self.assertTrue(lfx.on_load(self.store, self.tok, self.state()))
        self.assertEqual(self.spirit(), min(100, start + 5))
        self.assertEqual(self.status('date:abc123abc123:aaaaaaaaaaaaaaaa'), 'applied')
        self.assertFalse(lfx.on_load(self.store, self.tok, self.state()))      # nothing pending: nothing moves
        self.assertEqual(self.spirit(), min(100, start + 5))
        validate_state(self.state())

    def test_crash_between_the_two_writes_is_a_no_op(self):
        self.add('env:boho:1:p', kind='coins', amount=7, data=dict(label='🧧 Lì xì phố'))
        w0 = self.state()['journey']['wallet']
        lfx.on_load(self.store, self.tok, self.state())
        self.assertEqual(self.state()['journey']['wallet'], w0 + 7)
        self.assertEqual(self.state()['journey']['history'][-1]['label'], '🧧 Lì xì phố')
        # the row is put back to pending (as if the process died before marking it): the receipt replays
        self.store.transaction(lambda db: db.execute("UPDATE live_effects SET status='pending'"))
        lfx.on_load(self.store, self.tok, self.state())
        self.assertEqual(self.state()['journey']['wallet'], w0 + 7)
        # and once the receipt is gone too, the ids kept in the save stop it
        self.store.transaction(lambda db: db.execute("UPDATE live_effects SET status='pending'"))
        self.store.transaction(lambda db: db.execute('DELETE FROM receipts'))
        lfx.on_load(self.store, self.tok, self.state())
        self.assertEqual(self.state()['journey']['wallet'], w0 + 7)
        self.assertEqual(self.status('env:boho:1:p'), 'applied')
        self.assertIn('env:boho:1:p', self.state()['journey']['live_fx'])

    def test_spirit_is_clamped(self):
        self.add('big1', amount=1000)
        lfx.on_load(self.store, self.tok, self.state())
        self.assertEqual(self.spirit(), 100)

    def test_other_saves_and_unknown_kinds_wait(self):
        other, _, _ = self.store.session()
        self.add('x-other', sid=self.store.key(other))
        self.add('x-close', kind='closeness')
        self.assertFalse(lfx.on_load(self.store, self.tok, self.state()))
        self.assertEqual((self.status('x-other'), self.status('x-close')), ('pending', 'pending'))

    def test_non_story_save_keeps_it_pending(self):
        store = Store(Path(self.tmp.name) / 'plain.db', story=False)
        self.addCleanup(store.close_pool)
        tok, _, _ = store.session()
        store.transaction(lambda db: db.execute(
            "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES('p1', ?, 'spirit', 5, '{}', 'pending', ?)",
            (store.key(tok), time.time())))
        self.assertFalse(lfx.on_load(store, tok, store.read(tok)[0]))

    def test_clients_cannot_send_it(self):
        rev = self.store.read(self.tok)[1]
        with self.assertRaises(GameError):
            self.store.command(self.tok, 'client-req-1', rev, None, lfx.ACTION, dict(id='forged1', kind='coins', amount=1000))

    def test_bad_saved_ids_are_refused(self):
        s = self.state()
        s['journey']['live_fx'] = ['ok-id', 'ok-id']
        with self.assertRaises(GameError):
            validate_state(s)

    def test_long_ids_get_a_short_request_id(self):
        eid = 'x' * 120
        self.assertLessEqual(len(lfx.request_id(eid)), 100)
        self.assertEqual(lfx.request_id('date:1:2'), 'live-date:1:2')

    def test_forget(self):
        self.add('f1')
        lfx.forget(self.store, self.tok)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM live_effects').fetchone()[0], 0)


class HTTP(unittest.TestCase):
    """Through /api/bootstrap: a pending reward is in the very save the page loads, once."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'state.db', story=True)
        self.server = GameServer(('127.0.0.1', 0), self.store)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        quiet = patch.dict(os.environ, {'QUIET': '1'})
        quiet.start()
        self.addCleanup(quiet.stop)
        self.addCleanup(self.store.close_pool)
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def boot(self, cookie=None):
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        con.request('GET', '/api/bootstrap?lite=1', headers={'Host': f'127.0.0.1:{self.server.server_port}', **({'Cookie': cookie} if cookie else {})})
        res = con.getresponse()
        body, headers = json.loads(res.read()), dict(res.getheaders())
        con.close()
        return (headers.get('Set-Cookie', '').split(';')[0] or cookie), body

    def test_bootstrap_pays_once(self):
        cookie, first = self.boot()
        sid = self.store.key(cookie.split('=', 1)[1])
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES('env:x:1:p', ?, 'coins', 9, '{}', 'pending', ?)",
            (sid, time.time())))
        w0 = first['state']['journey']['wallet']
        _, data = self.boot(cookie)
        self.assertEqual(data['state']['journey']['wallet'], w0 + 9)
        self.assertNotIn('live_fx', data['state']['journey'])     # the paid ids stay private
        _, again = self.boot(cookie)
        self.assertEqual(again['state']['journey']['wallet'], w0 + 9)


if __name__ == '__main__':
    unittest.main()
