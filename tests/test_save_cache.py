"""The parsed-save cache (game/savecache.py, Store.command): hits skip the parse and change
nothing else; anything the cache cannot vouch for is a miss. Every test runs the cache in
"strict" mode: each hit is compared with the stored text and each put is checked for a
plain JSON tree that nothing else references (AssertionError otherwise)."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import savecache
from game.engine import GameError
from game.savecache import SaveCache, impure
from game.storage import Store


def strict_store(path, mb=50.0, entries=None):
    store = Store(path)
    store.saves = SaveCache(mb=mb, entries=entries, verify='strict')
    return store


class SaveCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'game.db'
        self.store = strict_store(self.path)
        self.token, self.csrf, _ = self.store.session()
        self.sid = self.store.key(self.token)
        self.rev = 0
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, action, career='mother_baby', store=None, **payload):
        self.n += 1
        out = (store or self.store).command(self.token, f'request-{self.n:04d}', self.rev, career, action, payload)
        self.rev = out['revision']
        return out

    def stored(self):
        with self.store.connect() as db:
            row = db.execute('SELECT state,revision FROM sessions WHERE sid=?', (self.sid,)).fetchone()
        return json.loads(row['state']), row['revision']

    def play(self, career, days=2):
        self.cmd('select_career', career)
        for _ in range(days):
            self.cmd('start_day', career)
            for _ in range(4):
                for action in ('advance', 'more_work'):
                    try:
                        self.cmd(action, career)
                    except GameError:
                        pass
            self.cmd('end_day', career, carry_event=True)

    def test_hit_skips_the_parse_and_stores_the_same_save(self):
        self.store.saves = SaveCache(mb=50, verify=0)  # (strict mode parses the stored text to compare)
        self.cmd('start_day')
        self.assertEqual(self.store.saves.stats()['entries'], 1)
        with patch.object(self.store, 'parse_state', side_effect=AssertionError('parsed on a hit')):
            out = self.cmd('advance')
        s = self.store.saves.stats()
        self.assertEqual((s['hits'], s['misses'], s['mismatches']), (1, 1, 0))
        state, rev = self.stored()
        self.assertEqual(rev, out['revision'])
        self.assertTrue(savecache.same(state, self.store.saves.entries[self.sid][1]))

    def test_a_long_game_through_the_cache_matches_the_database(self):
        for career in ('mother_baby', 'grocery', 'florist', 'milk_tea'):
            self.play(career)
        s = self.store.saves.stats()
        self.assertGreater(s['hits'], 40)
        self.assertEqual(s['mismatches'], 0)  # strict: every hit was compared with the stored text

    def test_miss_after_another_worker_wrote(self):
        self.cmd('start_day')
        other = strict_store(self.path)  # another process: its own cache
        self.cmd('advance', store=other)
        self.cmd('advance')  # this process holds revision 1, the database has 2
        s = self.store.saves.stats()
        self.assertEqual((s['hits'], s['stale']), (0, 1))
        state, rev = self.stored()
        self.assertEqual(rev, 3)
        self.assertTrue(savecache.same(state, self.store.saves.entries[self.sid][1]))

    def test_edit_that_keeps_the_revision_is_seen_on_postgresql(self):
        if not self.store.pg:
            self.skipTest('SQLite has no row version (the cache is off there by default)')
        self.cmd('start_day')
        state, rev = self.stored()
        state['name'] = 'Sửa tay'
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state, ensure_ascii=False), self.sid))
        out = self.cmd('advance')
        self.assertEqual(out['state']['name'], 'Sửa tay')
        self.assertEqual(self.store.saves.stats()['stale'], 1)

    def test_failed_command_does_not_poison_the_cache(self):
        self.cmd('start_day')
        real = self.store._apply

        def half_then_fail(raw, *args, **kw):
            raw['name'] = 'half changed'  # the reducer changed the dict, then failed
            raise GameError('boom')
        with patch.object(self.store, '_apply', side_effect=half_then_fail):
            with self.assertRaises(GameError):
                self.cmd('advance')
        self.assertNotIn(self.sid, self.store.saves.entries)
        with patch.object(self.store, '_apply', side_effect=real):
            out = self.cmd('advance')
        self.assertNotEqual(out['state']['name'], 'half changed')
        self.assertNotEqual(self.stored()[0]['name'], 'half changed')

    def test_revision_conflict_keeps_the_entry(self):
        self.cmd('start_day')
        with self.assertRaises(Exception):
            self.store.command(self.token, 'request-conflict', 0, 'mother_baby', 'advance', {})
        self.assertIn(self.sid, self.store.saves.entries)
        self.cmd('advance')
        self.assertEqual(self.store.saves.stats()['hits'], 2)

    def test_concurrent_commands_on_one_save(self):
        self.cmd('start_day')
        errors = []

        def rename(i):
            try:
                self.store.command(self.token, f'rename-{i:03d}', None, None, 'settings', dict(name=f'Tên {i}'), internal=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=rename, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        state, rev = self.stored()
        self.assertEqual(rev, 13)
        self.assertEqual(self.store.saves.stats()['mismatches'], 0)
        self.rev = rev
        out = self.cmd('advance')  # whatever the cache holds now, it is the stored save
        self.assertEqual(out['state']['name'], state['name'])

    def test_memory_cap_and_entry_cap_evict_the_oldest(self):
        size = len(self.stored()[0] and json.dumps(self.stored()[0])) * savecache.BYTES_PER_CHAR
        self.store.saves = SaveCache(mb=2.5 * size / 1048576, verify='strict')
        tokens = [self.store.session()[0] for _ in range(4)]
        for i, tok in enumerate(tokens):
            self.store.command(tok, f'cap-req-{i:04d}', 0, 'mother_baby', 'select_career', {})
        s = self.store.saves
        self.assertLessEqual(s.bytes, s.cap)
        self.assertEqual(len(s.entries), 2)
        self.assertEqual(list(s.entries), [self.store.key(t) for t in tokens[2:]])  # least recently used went first
        self.assertEqual(s.evicted, 2)
        self.store.saves = SaveCache(mb=50, entries=3, verify='strict')
        for i, tok in enumerate(tokens):
            self.store.command(tok, f'cap2-req-{i:04d}', 1, 'mother_baby', 'start_day', {})
        self.assertEqual(len(self.store.saves.entries), 3)

    def test_kill_switch(self):
        with patch.dict(os.environ, {'SAVE_CACHE_MB': '0'}):
            store = Store(self.path)
        self.assertFalse(store.saves.on)
        self.cmd('start_day', store=store)
        self.cmd('advance', store=store)
        self.assertEqual(store.saves.stats()['entries'], 0)
        self.assertEqual(store.saves.stats()['hits'], 0)
        with patch.dict(os.environ, {'SAVE_CACHE_MB': '64'}):
            self.assertTrue(Store(self.path).saves.on)  # SQLite too, when asked for

    def test_detached_view_and_result(self):
        out = self.cmd('start_day')
        cached = self.store.saves.entries[self.sid][1]
        self.assertIsNone(impure(cached))  # (strict mode checked it on put too)
        mine = {id(x) for x in _containers(out)}
        self.assertFalse(mine & {id(x) for x in _containers(cached)})

    def test_mismatch_turns_the_cache_off_outside_strict_mode(self):
        self.store.saves = SaveCache(mb=50, verify=1)
        self.cmd('start_day')
        self.store.saves.entries[self.sid][1]['name'] = 'not what is stored'
        err = []
        with patch('sys.stderr') as fake:
            fake.write.side_effect = err.append
            out = self.cmd('advance')
        self.assertNotEqual(out['state']['name'], 'not what is stored')
        self.assertFalse(self.store.saves.on)
        self.assertTrue(any('[save-cache]' in line for line in err))

    def test_impure_trees_are_refused(self):
        shared = [1]
        self.assertIsNone(impure({'a': [{'b': 'c'}], 'd': 1.5}))
        self.assertIn('non-str key', impure({1: 'x'}))
        self.assertIn('tuple', impure({'a': (1, 2)}))
        self.assertIn('also reached', impure({'a': shared, 'b': shared}))
        self.assertIn('outside', impure({'a': shared}))


def _containers(o):
    out = []
    stack = [o]
    while stack:
        x = stack.pop()
        if type(x) is dict:
            out.append(x)
            stack.extend(x.values())
        elif type(x) is list:
            out.append(x)
            stack.extend(x)
    return out


class SaveCacheHTTPTests(unittest.TestCase):
    """The HTTP route keeps the save aside until its response is encoded (hold + release)."""
    def setUp(self):
        from server import GameServer
        self.tmp = tempfile.TemporaryDirectory()
        store = strict_store(Path(self.tmp.name) / 'state.db')
        self.server = GameServer(('127.0.0.1', 0), store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.quiet = patch.dict(os.environ, {'QUIET': '1'})
        self.quiet.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()
        self.quiet.stop()

    def req(self, path, method='GET', body=None):
        h = {'Host': f'127.0.0.1:{self.server.server_port}'}
        if getattr(self, 'cookie', None):
            h.update(Cookie=self.cookie, **{'X-Game-CSRF': self.csrf})
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        out = res.status, dict(res.getheaders()), res.read()
        con.close()
        return out

    def test_commands_hit_the_cache_and_health_shows_it(self):
        status, headers, body = self.req('/api/bootstrap')
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = json.loads(body)['csrf']
        rev = 0
        for i, action in enumerate(('start_day', 'advance', 'advance')):
            status, _, body = self.req('/api/command', 'POST', dict(request_id=f'http-cache-{i:03d}', expected_revision=rev,
                                                                    career='mother_baby', action=action, payload={}))
            self.assertEqual(status, 200, body[:300])
            rev = json.loads(body)['revision']
        health = json.loads(self.req('/api/health')[2])['save_cache']
        self.assertEqual((health['hits'], health['misses'], health['mismatches']), (2, 1, 0))
        self.assertEqual(health['entries'], 1)


if __name__ == '__main__':
    unittest.main()
