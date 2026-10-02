"""Smaller state answers (game/state_delta.py, server.py json(known=...), public/js/api.js inflate):
the parts a page holds come back as references, the page rebuilds exactly the server's state; pages and
servers that know nothing of it talk as before."""
import copy
import gzip
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import fastjson as fj
from game import state_delta as sd
from game.engine import public_state
from game.storage import Store
from server import GameServer
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


def canon(x):
    """The state's JSON, keys sorted, without the fair's clock (game/fair.py public(): the second it was read)."""
    x = json.loads(fj.dumps_body(x))
    if isinstance(x.get('fair'), dict):
        x['fair'].pop('now', None)
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def answer(state, holder):
    """The server's encoding of `state` for `holder`, through the JSON text a page would parse, taken by it:
    (the answer's text, the state the holder rebuilt)."""
    body, d = sd.encode(state, sd.parse_known(holder.known()))
    text = b'{"state":' + body + b',"delta":' + fj.dumps_body(d) + b'}'
    wire = json.loads(text)
    return text, wire['delta'], holder.take(wire['state'], wire['delta'])


def played():
    """A milk-tea counter through a few customers: (career, action) and the public state after each."""
    j = Journey('milk_tea')
    from game import boba
    out = [public_state(copy.deepcopy(j.state))]
    for _ in range(60):
        c = j.c
        active = [t for t in c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
        if not active:
            try:
                j.act('more_work')
            except Exception:
                break
        else:
            t = next((t for t in active if t['id'] == c['active_task']), active[0])
            action, payload = boba.next_move(c, t)
            try:
                j.act(action, **payload)
            except Exception:
                break
        out.append(public_state(copy.deepcopy(j.state)))
    return out


class Encoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = played()

    def test_round_trip_through_a_session_of_answers(self):
        """Every answer, rebuilt from the parts held after the previous one, is the server's state exactly;
        after the first, most of it comes as references and the answer is a fraction of the whole."""
        h = sd.Holder()
        small = 0
        for i, st in enumerate(self.states):
            text, delta, got = answer(st, h)
            self.assertEqual(canon(got), canon(st), i)
            if i:
                self.assertTrue(delta['refs'], i)
                small += len(gzip.compress(text, 4)) < len(gzip.compress(fj.dumps_body(st), 4)) / 2
        self.assertGreater(small, len(self.states) * 0.8)

    def test_key_order_is_kept(self):
        h = sd.Holder()
        for st in self.states[:6]:
            _, _, got = answer(st, h)
            self.assertEqual(json.dumps(got, ensure_ascii=False), json.dumps(json.loads(fj.dumps_body(st)), ensure_ascii=False))

    def test_nothing_known_is_whole(self):
        """No `known` (first command, a cleared page): no references, the state is complete; every named part
        is listed with its path."""
        st = self.states[-1]
        body, d = sd.encode(st)
        self.assertEqual(d['refs'], [])
        self.assertEqual(json.loads(body), json.loads(fj.dumps_body(st)))
        self.assertTrue(d['keys'])
        for path, h in d['keys']:
            node = st
            for k in path:
                node = node[k]
            self.assertEqual(h, sd.digest(fj.dumps_body(node)))

    def test_a_part_held_is_referenced_whole(self):
        """The same state again: the top-level parts the page holds are references (nothing looked into)."""
        h = sd.Holder()
        answer(self.states[-1], h)
        body, d = sd.encode(self.states[-1], sd.parse_known(h.known()))
        self.assertTrue(all(len(path) == 1 for path, _ in d['refs']))
        self.assertLess(len(body), 4096)

    def test_unknown_hashes_and_other_saves_change_nothing(self):
        """References are by content: hashes the page does not hold (another save, a server restart, an
        import), junk or a cut `known` never make a part come back as a reference it cannot fill."""
        st = self.states[-1]
        other = Journey('grocery')
        h = sd.Holder()
        answer(public_state(other.state), h)
        _, _, got = answer(st, h)
        self.assertEqual(canon(got), canon(st))
        for junk in (None, 5, '', 'abc', 'x' * 9, ['abcdefgh'], {'a': 1}, 'z' * 8 * (sd.MAX_KNOWN + 1)):
            self.assertEqual(sd.parse_known(junk), frozenset(), junk)
            body, d = sd.encode(st, sd.parse_known(junk))
            self.assertEqual(d['refs'], [])
            self.assertEqual(json.loads(body), json.loads(fj.dumps_body(st)))

    def test_moved_parts_and_shifted_lists(self):
        """A post put in front of a list, members renamed, parts moved elsewhere: the rest is still referenced."""
        base = {'a': {'feed': [{'id': i, 'text': 'x' * 300} for i in range(12)], 'n': 1}, 'b': {'big': 'y' * 3000}, 'c': 1}
        h = sd.Holder()
        answer(base, h)
        nxt = copy.deepcopy(base)
        nxt['a']['feed'].insert(0, {'id': 99, 'text': 'new' * 100})
        nxt['moved'] = nxt.pop('b')
        nxt['c'] = 2
        _, delta, got = answer(nxt, h)
        self.assertEqual(json.dumps(got), json.dumps(nxt))
        self.assertEqual(len([r for r in delta['refs'] if r[0][:2] == ['a', 'feed']]), 12)
        self.assertIn(['moved'], [r[0] for r in delta['refs']])

    def test_named_parts_inside_a_reused_part_stay_held(self):
        """A part reused whole keeps lending its own named parts: the answer after next still references
        the posts of a list that came whole as one reference in between."""
        base = {'feed': [{'id': i, 'text': 'x' * 300} for i in range(12)], 'clock': 1}
        h = sd.Holder()
        answer(base, h)
        tick = dict(base, clock=2)
        _, delta, _ = answer(tick, h)
        self.assertEqual([r[0] for r in delta['refs']], [['feed']])
        post = dict(tick, feed=[{'id': 99, 'text': 'z' * 300}] + tick['feed'])
        _, delta, got = answer(post, h)
        self.assertEqual(got, post)
        self.assertEqual(len(delta['refs']), 12)

    def test_odd_values(self):
        """Non-text keys, tuples, NaN, empty containers, deep nesting: the same JSON as before."""
        st = {'k': {1: 'a' * 3000, 2: 'b'}, 't': tuple(range(900)), 'nan': float('nan'), 'e': {}, 'l': [],
              'deep': {'a': {'b': {'c': {'d': {'e': {'f': {'g': ['h' * 400] * 20}}}}}}}}
        h = sd.Holder()
        for _ in range(2):
            _, _, got = answer(st, h)
            self.assertEqual(json.dumps(got, sort_keys=True), json.dumps(json.loads(fj.dumps_body(st)), sort_keys=True))

    def test_holder_refuses_what_it_cannot_fill(self):
        h = sd.Holder()
        with self.assertRaises(KeyError):
            h.take({'a': 0}, {'refs': [[['a'], 'AAAAAAAA']], 'keys': []})
        h.parts['AAAAAAAA'] = {'x': 1}
        with self.assertRaises(ValueError):
            h.take({'a': 5}, {'refs': [[['a'], 'AAAAAAAA']], 'keys': []})


class Client(unittest.TestCase):
    """public/js/api.js inflate() on the server's own answers (node)."""

    def test_inflate_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        states = played()[:25]
        h = sd.Holder()
        answers = []
        for st in states:
            known = h.known()
            body, d = sd.encode(st, sd.parse_known(known))
            text = (b'{"state":' + body + b',"delta":' + fj.dumps_body(d) + b',"revision":1}').decode()
            h.take(json.loads(body), json.loads(fj.dumps_body(d)))
            answers.append(dict(text=text, known=known, whole=json.loads(fj.dumps_body(st))))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'answers.json'
            p.write_text(json.dumps(answers, ensure_ascii=False), encoding='utf-8')
            out = subprocess.run([node, str(ROOT / 'tests' / 'state_delta.mjs'), str(p)], cwd=ROOT, capture_output=True, text=True,
                                 encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('ok', out.stdout)


class HTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db', story=True))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()
        cls.quiet.stop()

    def setUp(self):
        self.cookie = self.csrf = None
        self.n = 0

    def req(self, path, method='GET', body=None, delta=True, gz=False):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if delta:
            h['X-Game-Delta'] = '1'
        if gz:
            h['Accept-Encoding'] = 'gzip'
        if self.cookie:
            h['Cookie'] = self.cookie
        if self.csrf:
            h['X-Game-CSRF'] = self.csrf
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        data = res.read()
        headers = dict(res.getheaders())
        con.close()
        if headers.get('Content-Encoding') == 'gzip':
            data = gzip.decompress(data)
        return res.status, headers, data

    def boot(self, delta=True):
        status, headers, body = self.req('/api/bootstrap?lite=1', delta=delta)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        data = json.loads(body)
        self.csrf = data['csrf']
        self.rev = data['revision']
        return data

    def cmd(self, career, action, known=None, delta=True, rev=None, **payload):
        self.n += 1
        body = dict(request_id=f'delta-test-{self.n:04d}-{id(self)}', expected_revision=self.rev if rev is None else rev,
                    career=career, action=action, payload=payload)
        if known is not None:
            body['known'] = known
        status, _, raw = self.req('/api/command', 'POST', body, delta=delta)
        data = json.loads(raw)
        if status == 200:
            self.rev = data['revision']
        return status, data, raw

    def whole(self):
        return json.loads(self.req('/api/state', delta=False)[2])['state']

    def test_old_page_gets_the_answer_of_before(self):
        """No header: no `delta` member and the whole state, even with a `known` in the body."""
        data = self.boot(delta=False)
        self.assertNotIn('delta', data)
        status, out, _ = self.cmd(None, 'jr_profile', delta=False, known='AAAAAAAA', gender='female', name='Lan')
        self.assertEqual(status, 200)
        self.assertNotIn('delta', out)
        self.assertEqual(canon(out['state']), canon(self.whole()))

    def test_session_of_commands_rebuilds_the_server_state(self):
        data = self.boot()
        h = sd.Holder()
        h.take(data['state'], data['delta'])
        self.assertEqual(data['delta']['refs'], [])
        steps = [(None, 'jr_profile', dict(gender='female', name='Lan')), ('milk_tea', 'select_career', {}),
                 ('milk_tea', 'start_day', {}), ('milk_tea', 'more_work', {})]
        sizes = []
        for career, action, payload in steps:
            status, out, raw = self.cmd(career, action, known=h.known(), **payload)
            self.assertEqual(status, 200, out)
            got = h.take(out['state'], out['delta'])
            self.assertEqual(canon(got), canon(self.whole()), action)
            sizes.append((len(raw), len(fj.dumps_body(got))))
        self.assertLess(sizes[-1][0], sizes[-1][1] / 2)
        # GET /api/state with the header: whole, its parts named (a page can reference them on its next command)
        st = json.loads(self.req('/api/state')[2])
        self.assertEqual(st['delta']['refs'], [])
        h2 = sd.Holder()
        h2.take(st['state'], st['delta'])
        status, out, _ = self.cmd(None, 'settings', known=h2.known(), reduceMotion=True)
        self.assertEqual(status, 200, out)
        self.assertTrue(out['delta']['refs'])
        self.assertEqual(canon(h2.take(out['state'], out['delta'])), canon(self.whole()))

    def test_conflict_and_replay(self):
        """409: the whole state (no references, whatever `known` said); a replayed request references parts
        against the `known` it carries, as the first answer did."""
        data = self.boot()
        h = sd.Holder()
        h.take(data['state'], data['delta'])
        self.cmd(None, 'jr_profile', known=h.known(), gender='male', name='Tùng')
        status, out, _ = self.cmd('milk_tea', 'select_career', known=h.known(), rev=0)
        self.assertEqual(status, 409)
        self.assertEqual(out['delta']['refs'], [])
        self.assertEqual(canon(out['state']), canon(self.whole()))
        h.take(out['state'], out['delta'])
        known = h.known()
        self.n += 1
        body = dict(request_id=f'delta-replay-{id(self)}', expected_revision=self.rev, career='milk_tea', action='select_career', payload={}, known=known)
        first = json.loads(self.req('/api/command', 'POST', body)[2])
        again = json.loads(self.req('/api/command', 'POST', body)[2])
        self.assertTrue(again['replayed'])
        for out in (first, again):
            self.assertTrue(out['delta']['refs'])
            h2 = sd.Holder()
            h2.parts, h2.kids = dict(h.parts), dict(h.kids)
            self.assertEqual(canon(h2.take(out['state'], out['delta'])), canon(self.whole()))

    def test_errors_and_other_answers_are_untouched(self):
        """A refused command, the save export: no `delta`, as before."""
        self.boot()
        status, out, _ = self.cmd('milk_tea', 'select_career', known='')
        self.assertEqual(status, 400)
        self.assertNotIn('delta', out)
        st, _, body = self.req('/api/save/export')
        self.assertNotIn('delta', json.loads(body))

    def test_gzip_answer(self):
        data = self.boot()
        h = sd.Holder()
        h.take(data['state'], data['delta'])
        self.cmd(None, 'jr_profile', known=h.known(), gender='female', name='Mai')
        status, headers, body = self.req('/api/state', gz=True)
        self.assertEqual(status, 200)
        self.assertIn('delta', json.loads(body))


if __name__ == '__main__':
    unittest.main()
