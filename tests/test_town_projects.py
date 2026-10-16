"""🏗️ Công trình của phố (game/town_projects.py; owner 16/10 "góp tiền và có bảng tài trợ, có mục tiêu … thời gian xây
dựng là 2 ngày"): the catalogue, the contribution (validation, the wallet then the bank, a pure sink), the save block
(absent, strict, a newer build's), the database written in the save's own transaction (the goal never overshot, also
with two players closing it at once), 48 hours of building then completion and the next project (idempotent, several
processes), the boards, the titles paid through live_effects, and saves crossing an older build (OldServer)."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import journey as jr
from game import live_effects as fx
from game import spend as sp
from game import spend_content as SC
from game import town_projects as tp
from game import town_projects_content as C
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_791_400_000.0
H48 = 48 * 3600


def TB(s):
    return s['journey']['town']


def money(s):
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def rich(wallet=50_000_000, bank=0):
    s = story(wallet + bank)
    if bank:
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=bank)
    return s


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


class Catalogue(unittest.TestCase):
    def test_projects_in_order_with_goals_where_the_money_is(self):
        ids = [p['id'] for p in C.PROJECTS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, ['cong_vien', 'rap_phim', 'thu_vien', 'san_van_dong', 'cau_ra_dao', 'benh_vien'])
        goals = [p['goal'] for p in C.PROJECTS]
        self.assertEqual(goals, sorted(goals))
        self.assertTrue(all(10_000_000 <= g <= 200_000_000 for g in goals))   # the richest hold 13–48 M (16/10)
        self.assertEqual(C.BUILD_SECS, 48 * 3600)                              # owner: "2 ngày"
        for p in C.PROJECTS:
            self.assertRegex(p['id'], tp.ID_RE.pattern)
            self.assertIn(p['title'], SC.STYLE_ITEMS)
        self.assertEqual({x['id'] for x in SC.TOWN_TITLES}, set(tp.TITLE_IDS))
        self.assertTrue(all(len(x['id']) <= 24 and x.get('earn') and x['price'] == 0 for x in SC.TOWN_TITLES))

    def test_titles_by_rank(self):
        self.assertEqual(tp.titles_for(1, 'rap_phim'), ['t_ct_rap_phim', 't_ct_vang', 't_ct_gach'])
        self.assertEqual(tp.titles_for(3, 'rap_phim'), ['t_ct_vang', 't_ct_gach'])
        self.assertEqual(tp.titles_for(4, 'rap_phim'), ['t_ct_bac', 't_ct_gach'])
        self.assertEqual(tp.titles_for(10, 'rap_phim'), ['t_ct_bac', 't_ct_gach'])
        self.assertEqual(tp.titles_for(11, 'rap_phim'), ['t_ct_gach'])

    def test_a_pure_sink(self):
        import inspect
        src = inspect.getsource(tp)
        self.assertNotIn('_wallet(', src)          # never pays into a wallet
        self.assertNotIn("'salary'", src)


class Contribution(unittest.TestCase):
    def test_wallet_then_bank_never_a_loan(self):
        s = rich(1_000_000, bank=3_000_000)
        before = money(s)
        s, r = act(s, 'jr_town_give', project='cong_vien', amount=2_500_000, confirm=True)
        self.assertEqual(money(s), before - 2_500_000)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 1_500_000)
        self.assertIn('từ tài khoản', r['message'])
        self.assertEqual(s['journey']['history'][-1]['kind'], 'life')
        self.assertEqual(r['town'], dict(project='cong_vien', amount=2_500_000))
        b = TB(s)
        self.assertEqual((b['n'], b['sum'], b['by']), (1, 2_500_000, {'cong_vien': 2_500_000}))
        self.assertEqual({k for k in b['last']}, set(tp.LAST_KEYS))
        refused(self, s, 'jr_town_give', 'not_enough', project='cong_vien', amount=1_600_000, confirm=True)
        s['journey']['wallet'] = -5
        refused(self, s, 'jr_town_give', 'not_enough', project='cong_vien', amount=1_000, confirm=True)   # a wallet in debt

    def test_validation(self):
        s = rich()
        refused(self, s, 'jr_town_give', project='cong_vien', amount=999, confirm=True)         # under the minimum
        refused(self, s, 'jr_town_give', project='cong_vien', amount=10_000_001, confirm=True)  # more than once allows
        refused(self, s, 'jr_town_give', project='cong_vien', amount=1000.0, confirm=True)
        refused(self, s, 'jr_town_give', project='cong_vien', amount=True, confirm=True)
        refused(self, s, 'jr_town_give', project='nope', amount=5000, confirm=True)
        refused(self, s, 'jr_town_give', project='cong_vien', amount=5000)                        # no confirmation
        refused(self, s, 'jr_town_give', project='cong_vien', amount=5000, anon='yes', confirm=True)
        refused(self, s, 'jr_town_give', project='cong_vien', amount=5000, extra=1, confirm=True)
        free = story(5_000_000)
        free['journey']['story'] = False
        with self.assertRaises(GameError):
            act(free, 'jr_town_give', project='cong_vien', amount=5000, confirm=True)
        self.assertNotIn('town', s['journey'])


class Saves(unittest.TestCase):
    def test_absent_strict_and_a_newer_builds_block(self):
        s = story(100)
        self.assertNotIn('town', s['journey'])
        validate_state(s)
        s2 = rich()
        s2, _ = act(s2, 'jr_town_give', project='cong_vien', amount=10_000, confirm=True)
        validate_state(s2)
        j = copy.deepcopy(s2['journey'])
        j['town']['future'] = {'x': 1}
        j['town']['by']['a_new_project'] = 5000
        j['town']['last']['more'] = 1
        tp.upgrade(j)
        self.assertNotIn('future', j['town'])
        self.assertEqual(j['town']['by'], {'cong_vien': 10_000, 'a_new_project': 5000})      # kept by shape
        self.assertEqual(j['town']['last']['p'], 'cong_vien')
        t = dict(s2, journey=j)
        validate_state(t)
        self.assertEqual(tp.public(t)['by'], {'cong_vien': 10_000})                         # not shown
        for bad in ({'n': -1}, {'by': {'X': 1}}, {'last': dict(TB(s2)['last'], n=7)}, {'v': 2}):
            b = copy.deepcopy(s2)
            TB(b).update(bad)
            with self.assertRaises(GameError):
                validate_state(b)
        mig = migrate_state(copy.deepcopy(t))
        validate_state(mig)


class Titles(unittest.TestCase):
    def pay(self, s, eid, data):
        return act(s, 'live_fx', id=eid, kind='town', amount=1, data=data)

    def test_paid_once_for_good(self):
        s = story(100)
        data = dict(project='cong_vien', rank=1, xu=5_000_000, titles=tp.titles_for(1, 'cong_vien'))
        from game.engine import apply_action
        s, r = apply_action(s, None, 'live_fx', dict(id='town:cong_vien:0123456789abcdef', kind='town', amount=1, data=data), internal=True)
        own = s['journey']['spend']['own']
        self.assertTrue(all(own[t] == SC.PERMANENT for t in ('t_ct_cong_vien', 't_ct_vang', 't_ct_gach')))
        self.assertIn('Người dựng công viên', r['message'])
        validate_state(s)
        s2, r2 = apply_action(s, None, 'live_fx', dict(id='town:cong_vien:0123456789abcdef', kind='town', amount=1, data=data), internal=True)
        self.assertEqual(r2['live']['amount'], 0)                     # the same row: nothing again
        self.assertTrue(sp.public(s2))
        for bad in (dict(data, titles=['t_dai_gia']), dict(data, project='x'), dict(data, rank=0), dict(data, titles=[])):
            with self.assertRaises(GameError):
                apply_action(s, None, 'live_fx', dict(id='town:x:0123456789abcdee', kind='town', amount=1, data=bad), internal=True)
        # worn like any title (game/spend.py jr_spend_wear): the live service shows it beside the name
        s3, _ = act(s, 'jr_spend_wear', kind='title', id='t_ct_cong_vien')
        self.assertEqual(sp.style_now(s3).get('t'), 't_ct_cong_vien')


class Database(unittest.TestCase):
    """Rows written in the save's own transaction (game/storage.py → town_projects.command_commit), the lazy advance."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        tp._VIEW.clear()
        self.addCleanup(tp._VIEW.clear)
        self.t = [T0]
        p = patch.object(tp, 'now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)

    def player(self, wallet=60_000_000, name='Lan', account=None):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {self.store.key(token): fn})
        if account:
            with self.store.connect() as db:
                sid = self.store.key(token)
                db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES(?, ?, 'x', ?)", (account.lower().replace(' ', ''), account, sid))
                db.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'x')", (self.store.digest(token), sid))   # still signed in
        return token

    def give(self, token, amount, project='cong_vien', n=[0], **p):
        n[0] += 1
        return self.store.command(token, f'town-{n[0]:08d}-{os.getpid()}', self.store.read(token)[1], None, 'jr_town_give',
                                  dict(project=project, amount=amount, confirm=True, **p))

    def wallet(self, token):
        return self.store.read(token)[0]['journey']['wallet']

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def view(self, token=None):
        tp._VIEW.clear()
        return tp.view(self.store, token)

    def proj(self, v, pid):
        return next(p for p in v['projects'] if p['id'] == pid)

    def test_the_first_project_opens_on_the_first_look(self):
        v = self.view()
        self.assertEqual(v['current'], 'cong_vien')
        self.assertEqual([p['status'] for p in v['projects']], ['funding', 'soon', 'soon', 'soon', 'soon', 'soon'])
        self.assertEqual(self.rows("SELECT ref FROM news WHERE kind='town'"), [dict(ref='town:open:cong_vien')])
        self.assertEqual(tp.advance(self.store), [])                    # nothing due: one read, no lock

    def test_contribution_goal_cap_and_closed(self):
        self.view()
        a, b = self.player(account='Lan Mây'), self.player(name='Minh')
        self.give(a, 10_000_000)
        self.give(a, 5_000_000)
        self.assertEqual(self.wallet(a), 45_000_000)
        with self.assertRaises(GameError) as cm:                         # more than what is left: refused, nothing paid
            self.give(b, 5_000_001)
        self.assertEqual(cm.exception.code, 'over')
        self.assertIn('5.000.000', str(cm.exception))
        self.assertEqual(self.wallet(b), 60_000_000)
        with self.assertRaises(GameError):                               # not open yet
            self.give(b, 10_000, project='rap_phim')
        self.assertEqual(self.wallet(b), 60_000_000)
        self.give(b, 5_000_000)                                          # exactly what is left: building starts
        v = self.view(a)
        p = self.proj(v, 'cong_vien')
        self.assertEqual((p['status'], p['raised'], p['people']), ('building', 20_000_000, 2))
        self.assertEqual(p['ready'], T0 + H48)
        self.assertEqual(v['current'], 'cong_vien')
        with self.assertRaises(GameError) as cm:
            self.give(b, 1_000)
        self.assertEqual(cm.exception.code, 'closed')
        self.assertEqual(self.wallet(b), 55_000_000)
        refs = [r['ref'] for r in self.rows("SELECT ref FROM news WHERE kind='town' ORDER BY id")]
        self.assertIn('town:goal:cong_vien', refs)
        self.assertEqual(sum(1 for r in refs if r.startswith('town:') and r.count(':') == 2 and r.split(':')[1] not in ('open', 'goal', 'done')), 2)
        self.assertEqual(self.rows('SELECT SUM(amount) AS xu FROM town_gifts')[0]['xu'], 20_000_000)
        self.assertEqual(v['mine'], dict(xu=15_000_000, by={'cong_vien': 15_000_000}))
        self.assertEqual([(x['name'], x['xu'], x['me']) for x in p['top']], [('Lan Mây', 15_000_000, True), (tp.GUEST_NAME, 5_000_000, False)])

    def test_two_players_closing_the_goal_at_once(self):
        self.view()
        a = self.player()
        self.give(a, 10_000_000)
        self.give(a, 9_000_000)
        others = [self.player(name=f'P{i}') for i in range(4)]
        out, errors = [], []
        go = threading.Barrier(len(others))

        def run(tok):
            go.wait()
            try:
                self.give(tok, 1_000_000)
                out.append(tok)
            except GameError as e:
                errors.append(e.code)
        ts = [threading.Thread(target=run, args=(t,)) for t in others]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(out), 1, (out, errors))
        self.assertTrue(set(errors) <= {'closed', 'over'}, errors)
        self.assertEqual(self.rows("SELECT raised, status FROM town_projects WHERE id='cong_vien'"), [dict(raised=20_000_000, status='building')])
        self.assertEqual(sum(self.wallet(t) for t in others), 4 * 60_000_000 - 1_000_000)   # only the winner paid

    def test_48_hours_then_done_titles_and_the_next_project(self):
        self.view()
        a, b, c = self.player(account='An'), self.player(account='Bình'), self.player(name='Chi')
        self.give(a, 3_000_000)
        self.give(b, 9_000_000, anon=True)
        self.give(c, 3_000_000)
        self.give(a, 5_000_000)                                          # An 8 M, the goal reached
        self.t[0] = T0 + H48 - 1
        self.assertEqual(tp.advance(self.store), [])
        self.assertEqual(self.proj(self.view(), 'cong_vien')['status'], 'building')
        self.t[0] = T0 + H48 + 5
        with patch('game.live_chat.notify') as notify:
            out = tp.advance(self.store)
        self.assertEqual(out, [('done', 'cong_vien'), ('open', 'rap_phim')])
        ops = [x.args[1]['op'] for x in notify.call_args_list]
        self.assertIn('fireworks', ops)
        show = next(x.args[1] for x in notify.call_args_list if x.args[1]['op'] == 'fireworks')
        import re
        self.assertRegex(show['id'], r'^[0-9a-f]{16}:[0-9]{1,10}$')        # live/fireworks.py ID_RE
        self.assertEqual((show['size'], show['pid'], show['name']), ('dai_tiec', '', ''))
        self.assertLessEqual(len(show['wish']), 40)
        self.assertEqual(tp.advance(self.store), [])                    # idempotent
        v = self.view()
        self.assertEqual([p['status'] for p in v['projects']][:2], ['done', 'funding'])
        self.assertEqual(self.proj(v, 'cong_vien')['done'], T0 + H48)
        self.assertEqual(v['current'], 'rap_phim')
        fxs = {r['sid']: json.loads(r['data']) for r in self.rows("SELECT sid, data FROM live_effects WHERE kind='town'")}
        sid = self.store.key
        self.assertEqual(fxs[sid(b)]['rank'], 1)                       # anonymous on the plaque, still the title
        self.assertEqual(fxs[sid(b)]['titles'], ['t_ct_cong_vien', 't_ct_vang', 't_ct_gach'])
        self.assertEqual(fxs[sid(a)]['rank'], 2)
        self.assertEqual(fxs[sid(c)]['titles'], ['t_ct_vang', 't_ct_gach'])
        self.assertEqual([x['name'] for x in self.proj(v, 'cong_vien')['top']], [tp.ANON_NAME, 'An', tp.GUEST_NAME])
        refs = [r['ref'] for r in self.rows("SELECT ref FROM news WHERE kind='town' ORDER BY id")]
        self.assertIn('town:done:cong_vien', refs)
        self.assertIn('town:open:rap_phim', refs)
        self.assertEqual(len(self.rows("SELECT id FROM chat_messages WHERE channel='town' AND name='🏗️ Công trình phố'")), 1)
        # the titles reach the save on its next load, once
        fx.on_load(self.store, b, self.store.read(b)[0])
        own = self.store.read(b)[0]['journey']['spend']['own']
        self.assertEqual(own.get('t_ct_cong_vien'), SC.PERMANENT)
        self.assertEqual(self.rows("SELECT status FROM live_effects WHERE sid=?", (sid(b),)), [dict(status='applied')])
        self.assertFalse(fx.on_load(self.store, b, self.store.read(b)[0]))

    def test_several_processes_finish_once(self):
        from game.storage import Store
        self.view()
        a = self.player()
        self.give(a, 10_000_000)
        self.give(a, 10_000_000)
        other = Store(Path(self.tmp.name) / 's.db', story=True)          # another worker on the same database
        self.addCleanup(other.close_pool)
        self.t[0] = T0 + H48
        got = []
        go = threading.Barrier(2)

        def run(st):
            go.wait()
            got.append(tp.advance(st))
        ts = [threading.Thread(target=run, args=(st,)) for st in (self.store, other)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(len(x) for x in got), [0, 2])
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE kind='town'")), 1)
        self.assertEqual(len(self.rows("SELECT id FROM news WHERE ref='town:done:cong_vien'")), 1)
        self.assertEqual(self.rows("SELECT id, status FROM town_projects ORDER BY seq"),
                         [dict(id='cong_vien', status='done'), dict(id='rap_phim', status='funding')])

    def test_boards_paged_list_all_time_and_erasure(self):
        self.view()
        tokens = [self.player(account=f'Người {i:02d}') for i in range(tp.PAGE + 3)]
        for i, tok in enumerate(tokens):
            self.t[0] = T0 + i
            self.give(tok, 10_000 + (i % 5) * 1000)
        page0 = tp.board(self.store, tokens[4], 'cong_vien', 0)
        self.assertEqual((page0['people'], page0['more'], len(page0['rows'])), (tp.PAGE + 3, True, tp.PAGE))
        xs = [r['xu'] for r in page0['rows']]
        self.assertEqual(xs, sorted(xs, reverse=True))
        self.assertEqual(page0['rows'][0]['name'], 'Người 04')            # 14,000, the earliest of them
        self.assertTrue(page0['rows'][0]['me'])
        page1 = tp.board(self.store, None, 'cong_vien', 1)
        self.assertEqual((page1['more'], len(page1['rows']), page1['rows'][0]['rank']), (False, 3, tp.PAGE + 1))
        with self.assertRaises(GameError):
            tp.board(self.store, None, 'nope', 0)
        v = self.view(tokens[0])
        self.assertEqual(len(v['all']), tp.TOP)
        self.assertEqual(v['people'], tp.PAGE + 3)
        self.assertEqual(v['mine']['xu'], 10_000)
        self.store.delete(tokens[4])                                      # erased: the gift stays, anonymous
        v = self.view()
        self.assertEqual(self.proj(v, 'cong_vien')['top'][0]['name'], tp.ANON_NAME)
        self.assertEqual(self.proj(v, 'cong_vien')['raised'], sum(10_000 + (i % 5) * 1000 for i in range(tp.PAGE + 3)))

    def test_schema(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 52)
        self.assertIn('town_projects', pg_schema.TABLE)
        self.assertIn('town_gifts', pg_schema.TABLE)


class OldServer(unittest.TestCase):
    """The rollback floor (2.4.27) and 2.4.34 keep, validate and write every save this build writes."""

    def trees(self):
        found = []
        for old in (os.environ.get('MNL_OLD_TREE'), str(ROOT.parents[3] / '_wmain') if len(ROOT.parents) > 3 else None,
                    r'D:\projects\Mot_ngay_lam_nghe\_wmain'):
            if old and (Path(old) / 'game' / 'engine.py').is_file() and old not in found:
                found.append(old)
        if not found:
            self.skipTest('no older tree (MNL_OLD_TREE)')
        return found

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old)
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def test_saves_cross_older_builds_both_ways(self):
        from game.engine import apply_action
        s = rich(30_000_000, bank=5_000_000)
        s, _ = act(s, 'jr_town_give', project='cong_vien', amount=10_000_000, confirm=True)
        s, _ = act(s, 'jr_town_give', project='cong_vien', amount=2_000_000, confirm=True)
        s, _ = act(s, 'jr_town_give', project='cong_vien', amount=1_000, anon=True, confirm=True)
        data = dict(project='cong_vien', rank=1, xu=12_001_000, titles=tp.titles_for(1, 'cong_vien'))
        s, _ = apply_action(s, None, 'live_fx', dict(id='town:cong_vien:0123456789abcdef', kind='town', amount=1, data=data), internal=True)
        s, _ = act(s, 'jr_spend_wear', kind='title', id='t_ct_cong_vien')
        validate_state(s)
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError;'
                'from game.content import CAREERS;s=json.load(sys.stdin);'
                's["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's["journey"]["unlocked"]=[c for c in s["journey"]["unlocked"] if c in CAREERS];'
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,None,"jr_seen",{"ids":["x"]});validate_state(s);'
                'code="";\n'
                'try:\n apply_action(s,None,"jr_town_give",{"project":"cong_vien","amount":1000,"confirm":True})\n'
                'except GameError as e:\n code=e.code\n'
                'print(json.dumps(dict(s=s,code=code)))')
        for old in self.trees():
            got = self.run_old(old, prog, s)
            self.assertEqual(got['code'], 'unknown_action', old)
            back = got['s']
            self.assertEqual(back['journey']['town'], s['journey']['town'], old)
            self.assertEqual(back['journey']['spend']['own']['t_ct_cong_vien'], SC.PERMANENT)
            back = migrate_state(back)
            validate_state(back)
            back, _ = act(back, 'jr_town_give', project='cong_vien', amount=5_000, confirm=True)
            self.assertEqual(TB(back)['n'], 4)


if __name__ == '__main__':
    unittest.main()
