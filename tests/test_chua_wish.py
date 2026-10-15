"""🌳 Cây ước nguyện (game/chua_wish.py, owner 15/10): a player's own words hung on one of many wish trees.

The reducer half (game/chua.py 'nguyen' with a tree): cleaning and masking, strict payloads, the save keeps only what any
'nguyen' gives and still validates on the previous release. The table half (PostgreSQL): the row is written in the
save's own transaction, replays never hang twice, today's limit refuses the whole command, newest-first paging per tree,
mine, 🙏 once, reports hide, the author takes down, admins hide/show, nothing leaks the sid, account deletion forgets.
"""
import copy
import http.client
import importlib.util
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from game import chua, chua_wish as cw, pg_schema
from game.engine import GameError, validate_state
from game.storage import Store
from tests.test_chua import story, do

ROOT = Path(__file__).resolve().parents[1]
PG = os.environ.get('TEST_DATABASE_URL') and not os.environ.get('DATABASE_URL')


def wish(**more):
    return dict(dict(act='nguyen', tree='binh_an', text='Mong mẹ mau khỏe để Tết cả nhà về quê 🌸'), **more)


class WishReducer(unittest.TestCase):
    def test_a_tree_wish_gains_like_any_wish_and_keeps_the_words_out_of_the_save(self):
        s = story(spirit=40)
        out_state, result = do(s, **wish(color='vang', anon=True))
        w = result['chua_wish']
        self.assertEqual((w['tree'], w['color'], w['anon'], w['raw']), ('binh_an', 'vang', True, None))
        self.assertRegex(w['key'], r'^[0-9a-f]{24}$')
        self.assertEqual(w['text'], 'Mong mẹ mau khỏe để Tết cả nhà về quê 🌸')
        c = out_state['journey']['chua']
        self.assertIn('nguyen', c['did'])
        self.assertNotIn('cards', c, 'the words go to the table, never the save')
        self.assertNotIn('Mong mẹ', json.dumps(out_state['journey'], ensure_ascii=False))
        self.assertEqual(out_state['journey']['life']['spirit'], 43)
        self.assertIn('Cây Bình an', result['message'])
        self.assertTrue(chua.public(out_state)['wish_trees'])
        validate_state(out_state)

    def test_the_chat_mask_hides_phones_links_and_heavy_words_and_keeps_the_original_for_admins(self):
        _, result = do(story(), **wish(text='gọi mình 0912 345 678 nhé, vào www.abc.com, đéo'))
        w = result['chua_wish']
        self.assertNotIn('0912', w['text'])
        self.assertNotIn('abc.com', w['text'])
        self.assertNotIn('đéo', w['text'])
        self.assertIn('0912', w['raw'])

    def test_refusals_leave_the_save_untouched(self):
        bad = [dict(tree='nope'), dict(tree=1), dict(color='den'), dict(anon='yes'), dict(text=''), dict(text='  '),
               dict(text='ab'), dict(text='x' * (cw.TEXT_MAX + 1)), dict(text=7), dict(recipient='ca_nha'),
               dict(public=True), dict(name='Mẹ'), dict(wish='nha')]
        for extra in bad:
            s = story()
            before = copy.deepcopy(s)
            p = wish()
            p.update(extra)
            with self.assertRaises(GameError, msg=extra):
                do(s, **p)
            self.assertEqual(s, before, extra)
        for act in ('huong', 'khan', 'tung'):
            with self.assertRaises(GameError):
                do(story(), act=act, tree='binh_an', text='Mong bình an')

    def test_text_is_cleaned_not_html_and_emoji_and_three_lines_are_kept(self):
        _, result = do(story(), **wish(text='  Dòng một\n\n\n\nDòng hai  ​\nDòng ba\nDòng bốn <b>đậm</b> 🙏'))
        text = result['chua_wish']['text']
        self.assertNotIn('​', text)
        self.assertLessEqual(text.count('\n'), cw.TEXT_LINES - 1)
        self.assertIn('🙏', text)
        self.assertIn('<b>', text, 'kept as text; the page escapes it')

    def test_kill_switch_stops_new_wishes(self):
        with mock.patch.dict(os.environ, {'MNL_WISH_OFF': '1'}):
            with self.assertRaises(GameError):
                do(story(), **wish())

    def test_old_cards_and_preset_wishes_still_work(self):
        s, r = do(story(), act='nguyen', recipient='ca_nha', blessing='binh_an', message='Cả nhà bình an')
        self.assertIn('chua_card', r)
        s, r = do(s, act='nguyen', wish='nha')
        self.assertEqual(len(s['journey']['chua']['cards']), 2)
        validate_state(s)

    def test_the_previous_release_validates_a_save_with_tree_wishes(self):
        """Rollback: the save after tree wishes (did/n only) passes the chua.validate of origin/main (2.4.14)."""
        try:
            src = subprocess.run(['git', 'show', 'origin/main:game/chua.py'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('origin/main not available')
        self.assertNotIn('chua_wish', src)
        spec = importlib.util.spec_from_loader('game._chua_previous', loader=None)
        old = importlib.util.module_from_spec(spec)
        old.__package__ = 'game'
        exec(compile(src, 'origin/main:game/chua.py', 'exec'), old.__dict__)
        s = story()
        for _ in range(3):
            s, _ = do(s, **wish())
        s, _ = do(s, act='nguyen', recipient='ca_nha', blessing='binh_an')
        old.validate(s)
        self.assertEqual(old.public(s)['enabled'], True)


class QueryParsing(unittest.TestCase):
    def test_strict_query(self):
        q = lambda **kw: cw.parse_query({k: [v] for k, v in kw.items()})
        self.assertEqual(q(tree='gia_dao'), dict(tree='gia_dao'))
        self.assertEqual(q(mine='1', before='99', limit='10'), dict(mine=True, before=99, limit=10))
        for bad in (dict(), dict(tree='x'), dict(tree='gia_dao', mine='1'), dict(mine='0'), dict(tree='gia_dao', limit='0'),
                    dict(tree='gia_dao', limit='41'), dict(tree='gia_dao', before='-1'), dict(tree='gia_dao', sid='x'),
                    dict(tree='gia_dao', before='1' * 16)):
            with self.assertRaises(GameError, msg=bad):
                q(**bad)
        with self.assertRaises(GameError):
            cw.parse_query({'tree': ['gia_dao', 'binh_an']})

    def test_trees_are_many_named_and_unique(self):
        ids = [t[0] for t in cw.TREES]
        self.assertGreaterEqual(len(ids), 6)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(t[1] and t[2] and t[3] for t in cw.TREES))


@unittest.skipUnless(PG, 'requires isolated TEST_DATABASE_URL without DATABASE_URL')
class WishTable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'wish.db')
        self.addCleanup(self.store.close_pool)
        cw._invalidate()
        self.users = []
        for name in ('Lan', 'Minh', 'Hoa', 'Tú'):
            token, csrf, _ = self.store.session()
            s = story()
            s['name'] = name
            with self.store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), self.store.key(token)))
            self.users.append(dict(token=token, csrf=csrf, rev=0, n=0))

    def hang(self, u=0, **more):
        user = self.users[u]
        user['n'] += 1
        out = self.store.command(user['token'], f'wish-{u}-{user["n"]:04d}', user['rev'], None, 'jr_chua_do', wish(**more))
        user['rev'] = out['revision']
        return out

    def sid(self, u):
        return self.store.key(self.users[u]['token'])

    def test_hang_read_page_and_never_leak_the_sid(self):
        out = self.hang(0, color='hong')
        key = out['result']['chua_wish']['key']
        self.hang(1, anon=True, text='Mong thi đỗ đại học 📚', tree='hoc_hanh')
        page = cw.page(self.store, self.users[2]['token'], tree='binh_an')
        self.assertEqual(len(page['rows']), 1)
        row = page['rows'][0]
        self.assertEqual((row['name'], row['color'], row['mine'], row['prayers']), ('Lan', 'hong', False, 0))
        self.assertNotIn('key', row)
        raw = json.dumps(page, ensure_ascii=False)
        for u in range(4):
            self.assertNotIn(self.sid(u), raw)
        mine = cw.page(self.store, self.users[0]['token'], tree='binh_an')['rows'][0]
        self.assertEqual((mine['mine'], mine['key'], mine['status']), (True, key, 'live'))
        anon = cw.page(self.store, self.users[0]['token'], tree='hoc_hanh')['rows'][0]
        self.assertEqual(anon['name'], '')
        trees = cw.trees(self.store, self.users[0]['token'])
        by = {t['id']: t for t in trees['trees']}
        self.assertEqual((by['binh_an']['count'], by['binh_an']['ribbons']), (1, ['hong']))
        self.assertEqual((trees['left'], trees['per_day'], trees['mine'], trees['total']), (cw.PER_DAY - 1, cw.PER_DAY, 1, 2))
        self.assertNotIn(self.sid(0), json.dumps(trees))

    def test_replay_hangs_once_and_today_limit_refuses_the_whole_command(self):
        user = self.users[0]
        first = self.store.command(user['token'], 'wish-replay-0001', 0, None, 'jr_chua_do', wish())
        again = self.store.command(user['token'], 'wish-replay-0001', 0, None, 'jr_chua_do', wish())
        self.assertTrue(again['replayed'])
        user['rev'] = first['revision']
        for _ in range(cw.PER_DAY - 1):
            self.hang(0)
        self.assertEqual(len(cw.page(self.store, user['token'], mine=True)['rows']), cw.PER_DAY)
        state, rev, _ = self.store.read(user['token'])
        with self.assertRaises(GameError) as e:
            self.hang(0)
        self.assertEqual(e.exception.code, 'wish_limit')
        self.assertEqual(self.store.read(user['token'])[1], rev, 'the refused wish changed nothing in the save')
        self.assertEqual(cw.trees(self.store, user['token'])['left'], 0)
        with mock.patch('game.storage.OPTIMISTIC_TRIES', 0):
            with self.assertRaises(GameError):
                self.hang(0)

    def test_locked_path_writes_once(self):
        with mock.patch('game.storage.OPTIMISTIC_TRIES', 0):
            self.hang(0)
        self.assertEqual(len(cw.page(self.store, self.users[1]['token'], tree='binh_an')['rows']), 1)

    def test_paging_newest_first_by_cursor(self):
        for i in range(5):
            self.hang(0, text=f'Điều ước số {i}')
        for i in range(5):
            self.hang(1, text=f'Điều ước của Minh {i}')
        token = self.users[2]['token']
        seen, before = [], None
        while True:
            page = cw.page(self.store, token, tree='binh_an', before=before, limit=3)
            seen += [r['text'] for r in page['rows']]
            before = page['before']
            if before is None:
                break
        self.assertEqual(len(seen), 10)
        self.assertEqual(seen[0], 'Điều ước của Minh 4')
        self.assertEqual(seen[-1], 'Điều ước số 0')

    def test_pray_once_report_hides_down_and_admin(self):
        self.hang(0)
        wid = cw.page(self.store, self.users[1]['token'], tree='binh_an')['rows'][0]['id']
        with self.assertRaises(GameError):
            cw.act(self.store, self.users[0]['token'], dict(op='pray', id=wid))
        for _ in range(2):
            out = cw.act(self.store, self.users[1]['token'], dict(op='pray', id=wid))
        self.assertEqual((out['wish']['prayers'], out['wish']['prayed']), (1, True))
        # one report: gone for the reporter only; three: hidden for everyone until an admin looks
        cw.act(self.store, self.users[1]['token'], dict(op='report', id=wid, reason='rude'))
        self.assertEqual(cw.page(self.store, self.users[1]['token'], tree='binh_an')['rows'], [])
        self.assertEqual(len(cw.page(self.store, self.users[2]['token'], tree='binh_an')['rows']), 1)
        with self.assertRaises(GameError):
            cw.act(self.store, self.users[0]['token'], dict(op='report', id=wid))
        cw.act(self.store, self.users[1]['token'], dict(op='report', id=wid, reason='rude'))   # the same reporter twice counts once
        cw.act(self.store, self.users[2]['token'], dict(op='report', id=wid, reason='spam'))
        self.assertEqual(len(cw.page(self.store, self.users[3]['token'], tree='binh_an')['rows']), 1)
        cw.act(self.store, self.users[3]['token'], dict(op='report', id=wid, reason='other'))
        self.assertEqual(cw.page(self.store, self.users[3]['token'], tree='binh_an')['rows'], [])
        self.assertEqual(cw.page(self.store, self.users[0]['token'], mine=True)['rows'][0]['status'], 'hidden')
        view = cw.admin_view(self.store)
        item = view['items'][0]
        self.assertEqual((item['id'], item['reports'], item['status']), (wid, 3, 'hidden'))
        self.assertEqual(item['reasons'], dict(rude=1, spam=1, other=1))
        self.assertTrue(cw.admin_act(self.store, 'admin', dict(act='show', id=wid))['changed'])
        self.assertEqual(len(cw.page(self.store, self.users[3]['token'], tree='binh_an')['rows']), 0, 'reporters keep it hidden for themselves')
        self.assertEqual(len(cw.page(self.store, self.users[0]['token'], tree='binh_an')['rows']), 1)
        cw.admin_act(self.store, 'admin', dict(act='hide', id=wid))
        self.assertEqual(cw.page(self.store, self.users[0]['token'], tree='binh_an')['rows'], [])
        self.assertEqual(cw.page(self.store, self.users[0]['token'], mine=True)['rows'][0]['status'], 'removed')
        with self.assertRaises(GameError):
            cw.act(self.store, self.users[1]['token'], dict(op='pray', id=wid))
        # the author takes their own wish down: it stays in "Của tôi", an admin cannot put it back
        self.hang(0, text='Một điều ước khác')
        other = cw.page(self.store, self.users[0]['token'], tree='binh_an')['rows'][0]['id']
        with self.assertRaises(GameError):
            cw.act(self.store, self.users[1]['token'], dict(op='down', id=other))
        self.assertEqual(cw.act(self.store, self.users[0]['token'], dict(op='down', id=other))['wish']['status'], 'down')
        self.assertFalse(cw.admin_act(self.store, 'admin', dict(act='show', id=other))['changed'])
        self.assertEqual(cw.page(self.store, self.users[1]['token'], tree='binh_an')['rows'], [])
        for bad in (dict(op='pray'), dict(op='x', id=wid), dict(op='pray', id='1'), dict(op='pray', id=wid, reason='rude'),
                    dict(op='report', id=wid, reason='bad'), dict(op='pray', id=wid, extra=1)):
            with self.assertRaises(GameError, msg=bad):
                cw.act(self.store, self.users[1]['token'], bad)

    def test_nothing_deleted_but_by_the_players_own_account_deletion(self):
        self.hang(0)
        self.hang(1)
        lan = cw.page(self.store, self.users[0]['token'], mine=True)['rows'][0]['id']
        for u in (1, 2):   # Minh's 🙏 goes with Minh, Hoa's stays
            cw.act(self.store, self.users[u]['token'], dict(op='pray', id=lan))
        cw.forget(self.store, self.users[1]['token'])
        rows = cw.page(self.store, self.users[2]['token'], tree='binh_an')['rows']
        self.assertEqual([r['name'] for r in rows], ['Lan'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM chua_wish_prayers').fetchone()[0], 1)

    def test_schema_is_additive_and_idempotent(self):
        self.hang(0)
        with self.store.connect() as db:
            db.execute('DROP TABLE chua_wish_prayers')
            db.execute('DROP TABLE chua_wishes')
            db.execute("UPDATE mnl_meta SET value='43' WHERE key='schema_version'")
        with self.store.connect() as db:
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(pg_schema.ensure(db))
            self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT count(*) FROM chua_wishes').fetchone()[0], 0)
        self.hang(0)
        self.assertEqual(len(cw.page(self.store, self.users[1]['token'], tree='binh_an')['rows']), 1)

    def test_http_routes(self):
        from server import GameServer
        server = GameServer(('127.0.0.1', 0), self.store)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def request(path, u=None, method='GET', payload=None, csrf=True):
            headers = {'Content-Type': 'application/json'}
            if u is not None:
                headers['Cookie'] = 'mnl_session=' + self.users[u]['token']
                if csrf:
                    headers['X-Game-CSRF'] = self.users[u]['csrf']
            con = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            con.request(method, path, json.dumps(payload) if payload is not None else None, headers)
            response = con.getresponse()
            out = response.status, response.read()
            con.close()
            return out
        self.hang(0)
        self.assertEqual(request('/api/chua/trees')[0], 401)
        status, raw = request('/api/chua/trees', 1)
        self.assertEqual(status, 200, raw)
        self.assertEqual(len(json.loads(raw)['trees']), len(cw.TREES))
        status, raw = request('/api/chua/wishes?tree=binh_an&limit=5', 1)
        self.assertEqual(status, 200, raw)
        wid = json.loads(raw)['rows'][0]['id']
        for q in ('', '?tree=x', '?tree=binh_an&limit=99', '?mine=1&tree=binh_an', '?tree=binh_an&sid=1'):
            self.assertEqual(request('/api/chua/wishes' + q, 1)[0], 400, q)
        self.assertEqual(request('/api/chua/wishes', 1, 'POST', dict(op='pray', id=wid), csrf=False)[0], 403)
        status, raw = request('/api/chua/wishes', 1, 'POST', dict(op='pray', id=wid))
        self.assertEqual((status, json.loads(raw)['wish']['prayers']), (200, 1))
        self.assertEqual(request('/api/admin/wishes', 1)[0], 403)
        self.assertEqual(request('/api/admin/wishes', 1, 'POST', dict(act='hide', id=wid))[0], 403)
        # the command route caps tree wishes a minute before the reducer runs
        with mock.patch.dict(os.environ, {'WISHES_PER_MINUTE': '1'}):
            body = lambda n: dict(request_id=f'http-wish-{n:04d}', expected_revision=None, action='jr_chua_do', payload=wish())
            st, raw = self.store.read(self.users[2]['token'])[1], None
            status, raw = request('/api/command', 2, 'POST', dict(body(1), expected_revision=st))
            self.assertEqual(status, 200, raw)
            status, raw = request('/api/command', 2, 'POST', dict(body(2), expected_revision=json.loads(raw)['revision']))
            self.assertEqual(status, 429, raw)


if __name__ == '__main__':
    unittest.main()
