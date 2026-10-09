"""🚔 Trại tạm giữ (game/jail.py; owner 09/10: "tố cáo sai thì bị bắt tù 1 ngày trong game, còn chơi cờ bạc bị bắt 3
ngày trong game. có người bảo lãnh thì trừ 30k tiền. Này là bạn bè mới bảo lãnh được ... làm công ích thì sẽ được
giảm ngày. tỷ lệ bị bắt thấp tý nhé", "với ae ăn tiền nhiều (hơn 300k) thì mới bị bắt nhé"):
the Chợ đen raids only big winners and jail them 3 days, a false police report sometimes 1 day; inside, no work, no
Chợ đen, no shopping; a jail day ends the life day without work; công ích takes a day off; a friend's bail (30,000
xu from the friend's wallet) frees at once; nobody is stuck (the safety time, MNL_JAIL_OFF); no odds reach the client;
a jailed save still loads on 1.9.29."""
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import fair_bm as bm
from game import jail as jl
from game import journey as jr
from game import review_police as R
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.test_black_market import BlackMarketBase, story

ROOT = Path(__file__).resolve().parents[1]
OLD_RELEASE = '9f084739'   # 1.9.29, the release this one may be rolled back to
T0 = 1_791_640_800         # 2026-10-10 20:00 Vietnam time


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class JailBase(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        self.clock = Clock(T0)
        p = mock.patch.object(jl, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def jailed(self, days=3, why='bm', wallet=50000):
        s = story(wallet)
        self.assertEqual(jl.arrest(s['journey'], why, days, self.clock.t), days)
        validate_state(s)
        return s

    def act(self, s, action, career=None, **p):
        return apply_action(s, career, action, p)

    def refused(self, s, action, code, career=None, **p):
        with self.assertRaises(GameError) as e:
            apply_action(s, career, action, p)
        self.assertEqual(e.exception.code, code, str(e.exception))
        return e.exception

    def later(self, seconds):
        self.clock.t += seconds

    def solve(self, s):
        """Every task of today, done right and slowly enough."""
        b = s['journey']['jail']
        for task in list(b['tasks']):
            s, r = self.act(s, 'jail_task_start', task=task)
            self.later(jl.TASK_MIN_S)
            s, r = self.act(s, 'jail_task_done', task=task, ans=answer(task, r['jail']['pz']))
            self.assertTrue(r['jail']['ok'])
        return s


def answer(task, pz):
    return {'sweep': lambda: {'swept': list(pz['piles'])}, 'plant': lambda: {'steps': [list(jl.PLANT_STEPS)] * pz['holes']},
            'rice': lambda: {'scoops': list(pz['want'])}, 'paint': lambda: {'cells': list(pz['dirty'])},
            'books': lambda: {'order': sorted(range(len(pz['nums'])), key=lambda i: pz['nums'][i])}}[task]()


# ---------------------------------------------------------------- who goes in
class ChoDenArrest(BlackMarketBase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        p = mock.patch.object(jl, 'now', lambda: self.clock.t)
        p.start()
        self.addCleanup(p.stop)

    def paid(self, net):
        s = story(100000)
        s, _ = self.act(s, 'fair_bm_pay')
        s['journey']['fair']['net'] = net
        validate_state(s)
        return s

    def test_never_at_or_below_300k_today(self):
        roll = mock.Mock(return_value=True)
        with mock.patch.object(bm, '_arrest_roll', roll):
            for net in (-50000, 0, 120000, bm.ARREST_FROM):
                with self.subTest(net=net):
                    s = self.paid(net)
                    s, r = self.act(s, 'fair_bc', bets={'cua': 100})
                    self.assertIn('dice', r['fair'])
                    self.assertNotIn('jail', s['journey'])
        roll.assert_not_called()   # the dice of the police are not even thrown

    def test_above_300k_the_roll_decides(self):
        s = self.paid(bm.ARREST_FROM + 1)
        with mock.patch.object(bm, '_arrest_roll', lambda *a: False):
            s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertIn('dice', r['fair'])
        s['journey']['fair']['net'] = bm.ARREST_FROM + 1
        w = s['journey']['wallet'] - 100
        with mock.patch.object(bm, '_arrest_roll', lambda *a: True):
            s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        a = r['fair']['arrest']
        self.assertEqual((a['stake'], a['fine'], a['jail']), (100, w * 30 // 100, 3))
        self.assertEqual(s['journey']['wallet'], w - w * 30 // 100)
        self.assertIn('tạm giữ 3 ngày', r['message'])
        b = s['journey']['jail']
        self.assertEqual((b['why'], b['days'], b['left'], b['day']), ('bm', 3, 3, 1))
        validate_state(s)
        self.assertEqual(public_state(s)['jail']['left'], 3)
        with self.assertRaises(GameError) as e:   # no Chợ đen from the cell (the engine's gate)
            apply_action(s, None, 'fair_bc', {'bets': {'cua': 1}})
        self.assertEqual(e.exception.code, 'jailed')
        self.assertIn('trại tạm giữ', str(e.exception))

    def test_a_big_stake_can_be_jailed_without_the_300k(self):
        """Owner 09/10 "từ 50k trở lên thì tăng tỷ lệ bị bắt": a 50,000 xu round is rolled for (1 %) at a net of 0, and
        the arrest is the same: stake, fine, the cell."""
        s = self.paid(0)
        seen = []
        with mock.patch.object(bm, '_arrest_roll', lambda p=bm.BM_ARREST_P: seen.append(p) or True):
            s, r = self.act(s, 'fair_bc', bets={'cua': 50000})
        self.assertAlmostEqual(seen[0], .01, places=9)
        w = 90000 - 50000
        a = r['fair']['arrest']
        self.assertEqual((a['stake'], a['fine'], a['jail']), (50000, w * 30 // 100, 3))
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        validate_state(s)

    def test_the_rate_is_low_and_its_own(self):
        self.assertEqual((bm.BM_ARREST_P, bm.ARREST_FROM, bm.JAIL_DAYS), (0.05, 300000, 3))
        hits = 0
        with mock.patch.object(bm, '_rng', __import__('random').Random(7)):
            hits = sum(bm._arrest_roll() for _ in range(20000))
        self.assertTrue(0.04 < hits / 20000 < 0.06, hits)

    def test_kill_switch_keeps_the_fine_but_no_cell(self):
        s = self.paid(bm.ARREST_FROM + 5)
        with mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '1'}), mock.patch.object(bm, '_arrest_roll', lambda *a: True):
            s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertEqual(r['fair']['arrest']['jail'], 0)
        self.assertNotIn('jail', s['journey'])
        self.assertNotIn('tạm giữ', r['message'])


class FalseReport(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        from tests.test_review_police import Base
        self.base = Base('run')
        self.base.setUp()
        jr.enable_story(self.base.j.state, 77)
        self.base.j.state['journey']['gender'] = 'female'
        validate_state(self.base.j.state)

    def test_reasonable_review_reported_may_jail_one_day(self):
        b = self.base
        p = b.post(3, 3)
        with mock.patch.object(R, 'jail_roll', lambda post: True):
            r = b.cop(p['id'])
        self.assertEqual((r['cop'], r['jail']), ('fair', 1))
        self.assertIn('Tố cáo sai sự thật', r['message'])
        jb = b.j.state['journey']['jail']
        self.assertEqual((jb['why'], jb['days'], jb['left']), ('cop', 1, 1))
        validate_state(b.j.state)
        with self.assertRaises(GameError) as e:   # the shop waits
            b.j.act('fb_cop', post=b.post(2, 4)['id'])
        self.assertEqual(e.exception.code, 'jailed')

    def test_not_held_most_of_the_time_and_never_when_only_unproven(self):
        b = self.base
        p = b.post(3, 3)
        with mock.patch.object(R, 'jail_roll', lambda post: False):
            r = b.cop(p['id'])
        self.assertEqual(r['cop'], 'fair')
        self.assertNotIn('jail', b.j.state['journey'])
        q = b.post(2, 5)
        with mock.patch.object(R, 'CONFIRM_PCT', 0), mock.patch.object(R, 'jail_roll', lambda post: True):
            r = b.cop(q['id'])
        self.assertEqual(r['cop'], 'unproven')
        self.assertNotIn('jail', b.j.state['journey'])

    def test_the_roll_is_seeded_and_about_a_quarter(self):
        self.assertEqual((R.JAIL_PCT, R.JAIL_DAYS), (25, 1))
        b = self.base
        posts = [b.post(3, 3) for _ in range(160)]
        self.assertEqual([R.jail_roll(p) for p in posts], [R.jail_roll(p) for p in posts])
        share = sum(R.jail_roll(p) for p in posts) / len(posts)
        self.assertTrue(0.12 < share < 0.4, share)


# ---------------------------------------------------------------- inside
class Inside(JailBase):
    def test_what_is_blocked_and_what_stays_open(self):
        s = self.jailed()
        for career, name, p in (('milk_tea', 'start_day', {}), (None, 'fair_bc', {'bets': {'cua': 1}}),
                                (None, 'jr_lux_buy', {}), (None, 'jr_spend_go', {}), (None, 'jr_abroad_go', {}),
                                (None, 'jr_garage_buy', {}), (None, 'iv_buy', {}), (None, 'jr_needs_snack', {'item': 'banh_mi'}),
                                (None, 'jr_quay_open', {}), (None, 'jr_vang_buy', {}), (None, 'jr_home_buy', {})):
            with self.subTest(name=name):
                self.refused(s, name, 'jailed', career, **p)
        s, _ = self.act(s, 'settings', sound=False)
        s, r = self.act(s, 'jr_profile', name='Bé Na')
        self.assertTrue(s['journey']['jail'])
        for name in ('jr_bk_open', 'as_start', 'vs_open', 'bd_post', 'qn_chat', 'jail_end', 'jr_wd_buy', 'jr_cert_exam'):
            self.assertTrue(jl.allowed(name), name)
        for name in ('end_day', 'start_day', 'fair_bm_pay', 'jr_spend_cafe', 'jr_out_go', 'jr_needs_snack', 'iv_buy'):
            self.assertFalse(jl.allowed(name), name)

    def test_internal_commands_still_run(self):
        s = self.jailed()
        jl.gate(s, 'start_day', internal=True)   # the server's own work (AI answers, gifts) is never held

    def test_ending_a_jail_day(self):
        s = self.jailed()
        day, wallet = s['journey']['life_day'], s['journey']['wallet']
        e = self.refused(s, 'jail_end', 'jail_wait', day=1)
        self.assertIn('2:00', str(e))
        self.later(jl.DAY_MIN_S)
        self.refused(s, 'jail_end', 'jail_stale', day=2)
        rent = jr.living_cost(s['journey'])['rent']
        s, r = self.act(s, 'jail_end', day=1)
        j = s['journey']
        self.assertEqual(j['life_day'], day + 1)
        self.assertEqual(j['wallet'], wallet - rent + (jr.WELCOME_GIFT if day == 1 else 0))
        row = next(x for x in j['history'] if x['kind'] == 'living')
        self.assertEqual((row['amount'], row['day']), (-rent, day))
        self.assertIn('cơm trại miễn phí', row['label'])
        self.assertEqual((j['jail']['left'], j['jail']['day'], j['jail']['done']), (2, 2, []))
        self.assertFalse(r['jail']['free'])
        self.refused(s, 'jail_end', 'jail_wait', day=2)   # the new jail day starts its own clock
        for _ in range(2):
            self.later(jl.DAY_MIN_S)
            s, r = self.act(s, 'jail_end', day=s['journey']['jail']['day'])
        self.assertTrue(r['jail']['free'])
        self.assertNotIn('jail', s['journey'])
        self.assertEqual(s['journey']['life_day'], day + 3)
        self.assertIsNone(public_state(s)['jail'])
        s, _ = self.act(s, 'start_day', 'milk_tea')   # back to work
        self.refused(s, 'jail_end', 'jail_none')

    def test_one_day_sentence_ends_with_its_day(self):
        s = self.jailed(1, 'cop')
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=1)
        self.assertTrue(r['jail']['free'])
        self.assertNotIn('jail', s['journey'])

    def test_needs_start_the_new_morning_fed(self):
        s = self.jailed()
        from game import needs as nd
        n = nd.ensure(s)
        n.update(full=10, wake=20)
        validate_state(s)
        self.later(jl.DAY_MIN_S)
        s, _ = self.act(s, 'jail_end', day=1)
        n = s['journey']['needs']
        self.assertEqual((n['day'], n['eve'], n['full'] >= 70, n['wake']), (s['journey']['life_day'], None, True, 85))


class CongIch(JailBase):
    def test_three_tasks_a_day_fixed_and_valid(self):
        s = self.jailed()
        b = s['journey']['jail']
        self.assertEqual(len(b['tasks']), 3)
        self.assertEqual(b['tasks'], jl._pick(b['id'], 1))
        self.assertTrue(set(b['tasks']) <= set(jl.TASKS))
        pub = public_state(s)['jail']
        self.assertEqual([t['id'] for t in pub['tasks']], b['tasks'])
        self.assertTrue(all('pz' in t for t in pub['tasks']))

    def test_too_fast_wrong_or_not_started_is_refused(self):
        s = self.jailed()
        task = s['journey']['jail']['tasks'][0]
        self.refused(s, 'jail_task_done', 'jail_not_started', task=task, ans={})
        s, r = self.act(s, 'jail_task_start', task=task)
        right = answer(task, r['jail']['pz'])
        self.later(jl.TASK_MIN_S - 1)
        self.refused(s, 'jail_task_done', 'jail_fast', task=task, ans=right)
        self.later(1)
        self.refused(s, 'jail_task_done', 'jail_wrong', task=task, ans={'nope': 1})
        s, r = self.act(s, 'jail_task_done', task=task, ans=right)
        self.assertEqual(s['journey']['jail']['done'], [task])
        s, r = self.act(s, 'jail_task_done', task=task, ans=right)   # a retry: nothing more
        self.assertTrue(r['jail']['again'])
        self.refused(s, 'jail_task_start', 'already_done', task=task)
        other = next(x for x in jl.TASKS if x not in s['journey']['jail']['tasks'])
        self.refused(s, 'jail_task_start', 'invalid_action', task=other)

    def test_every_puzzle_checks_its_answer(self):
        for task in jl.TASKS:
            for day in (1, 2, 3):
                pz = jl.puzzle('abc123', day, task)
                with self.subTest(task=task, day=day):
                    self.assertTrue(jl._right(task, pz, answer(task, pz)))
                    self.assertFalse(jl._right(task, pz, {}))
        pz = jl.puzzle('abc123', 1, 'books')
        self.assertFalse(jl._right('books', pz, {'order': list(range(6))}) and pz['nums'] != sorted(pz['nums']))
        pz = jl.puzzle('abc123', 1, 'rice')
        self.assertFalse(jl._right('rice', pz, {'scoops': [x + 1 for x in pz['want']]}))
        pz = jl.puzzle('abc123', 1, 'plant')
        self.assertFalse(jl._right('plant', pz, {'steps': [['seed', 'dig', 'water']] * 4}))

    def test_full_cong_ich_takes_a_day_off(self):
        s = self.jailed()
        s = self.solve(s)
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=1)
        self.assertEqual(s['journey']['jail']['left'], 1)   # 3 − 1 − 1
        self.assertTrue(any('giảm thêm một ngày' in x for x in r['effects']))
        s = self.solve(s)
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=2)
        self.assertTrue(r['jail']['free'])   # a 3-day sentence served in 2 days


class NobodyStuck(JailBase):
    def test_safety_release_after_the_sentence_in_real_time(self):
        s = self.jailed(3)
        self.later(3 * jl.SAFE_S - 1)
        self.assertTrue(jl.active(s['journey']))
        self.later(1)
        self.assertFalse(jl.active(s['journey']))
        self.assertIsNone(public_state(s)['jail'])
        s, _ = self.act(s, 'start_day', 'milk_tea')
        self.assertNotIn('jail', s['journey'])   # dropped by the first command

    def test_kill_switch_releases_everybody(self):
        s = self.jailed()
        with mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '1'}):
            self.assertFalse(jl.active(s['journey']))
            self.assertEqual(jl.arrest(story()['journey'], 'bm', 3), 0)
            s, _ = self.act(s, 'start_day', 'milk_tea')
        self.assertNotIn('jail', s['journey'])

    def test_a_broken_block_is_refused(self):
        good = self.jailed()['journey']['jail']
        for bad in ('x', dict(good, why='vip'), dict(good, left=9), dict(good, tasks=['sweep']), dict(good, go={'t': 'fly', 'at': 1}),
                    dict(good, extra=1), dict(good, done=['books', 'books'])):
            with self.subTest(bad=bad):
                s = story()
                s['journey']['jail'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)


class NothingShown(JailBase):
    def test_no_odds_reach_the_client(self):
        s = self.jailed()
        pub = public_state(s)['jail']
        self.assertEqual(set(pub), {'id', 'why', 'why_text', 'days', 'left', 'day', 'tasks', 'go', 'task_ready', 'ready',
                                    'ask_next', 'bail', 'now'})
        blob = json.dumps(pub, ensure_ascii=False)
        for k in ('pct', '0.05', '0.25', 'ARREST', 'safe', '300000', 'roll'):
            self.assertNotIn(k, blob)
        js = (ROOT / 'public/js/v4/jail.js').read_text(encoding='utf-8')
        self.assertNotRegex(js, r'\d+\s*%')
        for k in ('300', '25', '0.05', 'tỷ lệ', 'xác suất'):
            self.assertNotIn(k, js.replace('#3a', ''))
        for text in (jl.JAILED, jl.NOT_IN, jl.RENT_LABEL, jl.BAIL_LABEL, bm.SAY_ARREST):
            self.assertNotIn('%', text)


class OldServer(JailBase):
    """A jailed save (and the friend's after a bail) validates on 1.9.29, the release this one may be rolled back to."""

    def old_tree(self):
        if os.environ.get('MNL_JAIL_OLD_TREE'):
            return Path(os.environ['MNL_JAIL_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix='mnl-1929-')
        try:
            data = subprocess.run(['git', 'archive', OLD_RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {OLD_RELEASE} (MNL_JAIL_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_saves_validate_on_1_9_29(self):
        s = self.jailed()
        s, r = self.act(s, 'jail_task_start', task=s['journey']['jail']['tasks'][0])
        started = json.loads(json.dumps(s))
        self.later(jl.DAY_MIN_S)
        s, _ = self.act(s, 'jail_end', day=1)
        second = json.loads(json.dumps(s))
        friend = story(40000)
        jr._wallet(friend['journey'], -jl.BAIL_XU, 'life', jl.BAIL_LABEL.format(name='Bé Na'))
        validate_state(friend)
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'out.append([s["journey"]["life_day"],bool(s["journey"].get("jail")),s["journey"]["wallet"]])\nprint(json.dumps(out))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps([started, second, friend]), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout)
        self.assertEqual([g[1] for g in got], [True, True, False])
        self.assertEqual(got[1][0], started['journey']['life_day'] + 1)
        self.assertEqual(got[2][2], 10000)


# ---------------------------------------------------------------- bail: two real accounts on one store
class Bail(JailBase):
    def setUp(self):
        super().setUp()
        from game import accounts, social
        from game import marriage as mr
        from game.storage import Store
        self.mr = mr
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        h = mock.patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        h.start()
        self.addCleanup(h.stop)
        self.accounts = accounts
        self.rid = 0

    def user(self, name, wallet=50000):
        token, _, _ = self.store.session()
        tok = self.accounts.register(self.store, token, dict(username=name + '_test', password='matkhau-dai-lam', confirm='matkhau-dai-lam',
                                                             display=name.title()))['token']
        sid = self.store.key(tok)

        def fn(s):
            j = s['journey']
            j['life_day'] = 12
            j['wallet'] = wallet
            j['stats']['max_wallet'] = max(wallet, j['stats']['max_wallet'])
        self.mr._mutate(self.store, {sid: fn})
        self.mr.ensure_person(self.store, sid)
        return tok

    def sid(self, tok):
        return self.store.key(tok)

    def code(self, tok):
        with self.store.connect() as db:
            return db.execute('SELECT code FROM marriage_people WHERE sid=?', (self.sid(tok),)).fetchone()['code']

    def friends(self, a, b):
        t = self.mr.now() - 86400
        self.store.transaction(lambda db: [db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', (x, y, t))
                                           for x, y in ((self.sid(a), self.sid(b)), (self.sid(b), self.sid(a)))])

    def jail(self, tok, days=3):
        self.mr._mutate(self.store, {self.sid(tok): lambda s: jl.arrest(s['journey'], 'bm', days, self.clock.t)})

    def state(self, tok):
        return self.store.read(tok)[0]

    def act(self, tok, op, **d):
        return self.mr.act(self.store, tok, op, d)

    def cmd(self, tok, action, career=None, **p):
        self.rid += 1
        rev = self.store.read(tok)[1]
        return self.store.command(tok, f'req-{self.rid:06d}', rev, career, action, p)

    def refused(self, want, tok, op, **d):
        with self.assertRaises(self.mr.MarriageError) as cm:
            self.act(tok, op, **d)
        self.assertEqual(cm.exception.code, want, cm.exception.message)
        return cm.exception

    def requests(self, tok):
        from game import friends as fr
        with self.store.connect() as db:
            return fr.view(db, self.sid(tok))['jail']

    def notice(self, tok):
        with self.store.connect() as db:
            return db.execute('SELECT notice FROM marriage_people WHERE sid=?', (self.sid(tok),)).fetchone()['notice']

    def test_ask_then_a_friend_pays_and_frees(self):
        ann, bob, cat = self.user('ann'), self.user('bob', 45000), self.user('cat')
        self.friends(ann, bob)
        self.friends(ann, cat)
        self.jail(ann)
        out = self.act(ann, 'jail_ask')
        self.assertIn('2 người bạn', out['message'])
        self.assertEqual([x['name'] for x in self.requests(bob)], ['Ann'])
        self.assertEqual(self.requests(bob)[0]['bail'], 30000)
        self.assertIn('bảo lãnh', self.notice(cat))
        self.refused('jail_asked', ann, 'jail_ask')   # once every few minutes
        out = self.act(bob, 'jail_bail', code=self.code(ann))
        self.assertIn('Ann', out['message'])
        self.assertNotIn('jail', self.state(ann)['journey'])
        bj = self.state(bob)['journey']
        self.assertEqual(bj['wallet'], 15000)
        row = bj['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (-30000, 'life', '🚔 Bảo lãnh cho Ann'))
        self.assertIn('Bob đã bảo lãnh', self.notice(ann))
        self.assertIn('Bạn đã bảo lãnh cho Ann', self.notice(bob))
        self.assertEqual(self.requests(bob), [])
        self.assertEqual(self.requests(cat), [])
        self.refused('jail_gone', cat, 'jail_bail', code=self.code(ann))   # once per sentence
        self.assertEqual(self.state(cat)['journey']['wallet'], 50000)
        cmd = self.cmd(ann, 'start_day', 'milk_tea')   # back to work at once
        self.assertTrue(cmd['state']['careers'])

    def test_only_friends_with_the_money(self):
        ann, bob, dan = self.user('ann'), self.user('bob', 29999), self.user('dan')
        self.friends(ann, bob)
        self.jail(ann)
        self.refused('not_friend', dan, 'jail_bail', code=self.code(ann))
        self.refused('not_enough', bob, 'jail_bail', code=self.code(ann))
        self.refused('self', ann, 'jail_bail', code=self.code(ann))
        self.assertTrue(self.state(ann)['journey']['jail'])
        self.assertEqual(self.state(bob)['journey']['wallet'], 29999)
        self.assertEqual(self.state(dan)['journey']['wallet'], 50000)

    def test_nobody_to_ask_and_nothing_to_ask_for(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.refused('jail_none', ann, 'jail_ask')
        self.jail(ann)
        self.refused('no_friends', ann, 'jail_ask')
        self.friends(ann, bob)
        self.act(ann, 'jail_ask')
        self.later(jl.ASK_GAP_S)
        self.act(ann, 'jail_ask')   # again after the gap: one row, not two
        self.assertEqual(len(self.requests(bob)), 1)

    def test_out_by_its_days_clears_the_requests(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        self.jail(ann, 1)
        self.act(ann, 'jail_ask')
        self.assertEqual(len(self.requests(bob)), 1)
        self.later(jl.DAY_MIN_S)
        out = self.cmd(ann, 'jail_end', day=1)
        self.assertTrue(out['result']['jail']['free'])
        self.assertIsNone(out['state']['jail'])
        self.assertEqual(self.requests(bob), [])
        self.refused('jail_gone', bob, 'jail_bail', code=self.code(ann))

    def test_a_jailed_player_cannot_bail_another(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        self.jail(ann)
        self.jail(bob)
        self.refused('jailed', bob, 'jail_bail', code=self.code(ann))
        self.assertTrue(self.state(ann)['journey']['jail'])


if __name__ == '__main__':
    unittest.main()
