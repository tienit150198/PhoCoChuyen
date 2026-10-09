"""🚔 Trại tạm giữ (game/jail.py; owner 09/10: "tố cáo sai thì bị bắt tù 1 ngày trong game, còn chơi cờ bạc bị bắt 3
ngày trong game. có người bảo lãnh thì trừ 30k tiền. Này là bạn bè mới bảo lãnh được ... làm công ích thì sẽ được
giảm ngày. tỷ lệ bị bắt thấp tý nhé", "với ae ăn tiền nhiều (hơn 300k) thì mới bị bắt nhé"):
the Chợ đen raids only big winners and jail them 3 days, a false police report sometimes 1 day; inside, no work, no
Chợ đen, no shopping; a jail day ends the life day without work; công ích takes a day off; a friend's bail (30,000
xu from the friend's wallet) frees at once; nobody is stuck (the safety time, MNL_JAIL_OFF); no odds reach the client;
a jailed save still loads on 1.9.29, 1.9.32 and 1.9.33 (owner 09/10 "bị giam cần lâu hơn nhé ... 1 ngày làm nhiều việc
và đa dạng hơn": 20-minute days of 8 tasks out of 14, the day kept in journey['jail2'] beside the old block)."""
import io
import json
import os
import shutil
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
OLD_RELEASE = '9f084739'   # 1.9.29
OLD_RELEASES = {'1.9.29': OLD_RELEASE, '1.9.32': '546f777e', '1.9.33': 'bda5ffeb'}   # releases this one may be rolled back to
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

    def solve(self, s, only=None):
        """Every task of today (or the `only` ones), done right and slowly enough."""
        d = jl.day_of(s['journey'])
        for task in [t for t in d['tasks'] if t not in d['done'] and (only is None or t in only)]:
            s, r = self.act(s, 'jail_task_start', task=task)
            self.later(jl.OLD_TASK_MIN_S if d['old'] else jl.TASK_MIN_S)
            s, r = self.act(s, 'jail_task_done', task=task, ans=answer(task, r['jail']['pz']))
            self.assertTrue(r['jail']['ok'])
        return s


def answer(task, pz):
    return {'sweep': lambda: {'swept': list(pz['piles'])}, 'plant': lambda: {'steps': [list(jl.PLANT_STEPS)] * pz['holes']},
            'rice': lambda: {'scoops': list(pz['want'])}, 'paint': lambda: {'cells': list(pz['dirty'])},
            'books': lambda: {'order': sorted(range(len(pz['nums'])), key=lambda i: pz['nums'][i])},
            'laundry': lambda: {'hang': [pz['pegs'].index(it['c']) for it in pz['items']]},
            'mop': lambda: {'wipes': list(pz['dirt'])},
            'trash': lambda: {'bins': [jl.TRASH[x] for x in pz['items']]},
            'veg': lambda: {'picked': list(pz['yellow'])},
            'dishes': lambda: {'steps': [list(jl.DISH_STEPS)] * pz['bowls']},
            'chicken': lambda: {'fed': list(pz['want'])},
            'fix': lambda: {'hits': list(pz['nails'])},
            'ledger': lambda: {'counts': {k: pz['pile'].count(k) for k in pz['kinds']}},
            'fold': lambda: {'folds': [list(c) for c in pz['cards']]}}[task]()


# One wrong answer per task: a near miss (one item off), never just an empty answer.
def near_miss(task, pz):
    a = answer(task, pz)
    k, v = next(iter(a.items()))
    if task in ('sweep', 'paint', 'veg'):
        return {k: v[:-1]}                                         # one pile / panel / leaf left
    if task in ('rice', 'mop', 'fix'):
        return {k: [v[0] + 1] + v[1:]}                             # one too many
    if task == 'books':
        return {k: [v[1], v[0]] + v[2:]}                           # two swapped
    if task == 'laundry':
        return {k: [v[1], v[0]] + v[2:]}                           # two on each other's peg
    if task == 'trash':
        return {k: [{'giay': 'nhua', 'nhua': 'huu_co', 'huu_co': 'giay'}[v[0]]] + v[1:]}
    if task in ('plant', 'dishes'):
        return {k: [list(reversed(v[0]))] + v[1:]}                 # the steps out of order
    if task == 'chicken':
        return {k: [next(f for f in jl.FEED if f != v[0])] + v[1:]}
    if task == 'ledger':
        first = next(iter(v))
        return {k: dict(v, **{first: v[first] + 1})}
    return {k: [list(reversed(v[0]))] + v[1:]}                     # fold: the card read backwards


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
        self.refused(s, 'jr_profile', 'jailed', name='Bé Na')   # owner 09/10: only the camp, messages and công ích
        self.assertTrue(s['journey']['jail'])
        for name in ('settings', 'jail_end', 'jail_task_start', 'jail_task_done', 'jr_seen', 'bd_seen'):
            self.assertTrue(jl.allowed(name), name)
        for name in ('end_day', 'start_day', 'fair_bm_pay', 'jr_spend_cafe', 'jr_out_go', 'jr_needs_snack', 'iv_buy',
                     'jr_bk_open', 'as_start', 'vs_open', 'bd_post', 'qn_chat', 'jr_wd_buy', 'jr_cert_exam', 'reset_all',
                     'select_career', 'jr_equip', 'jr_profile', 'jr_withdraw'):
            self.assertFalse(jl.allowed(name), name)

    def test_internal_commands_still_run(self):
        s = self.jailed()
        jl.gate(s, 'start_day', internal=True)   # the server's own work (AI answers, gifts) is never held

    def test_ending_a_jail_day(self):
        s = self.jailed()
        day, wallet = s['journey']['life_day'], s['journey']['wallet']
        e = self.refused(s, 'jail_end', 'jail_wait', day=1)
        self.assertIn('20:00', str(e))
        self.later(jl.DAY_MIN_S - 60)
        self.refused(s, 'jail_end', 'jail_wait', day=1)
        self.later(-(jl.DAY_MIN_S - 60))
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
    def test_eight_tasks_a_day_of_fourteen(self):
        self.assertEqual(len(jl.TASKS), 14)
        self.assertEqual((jl.DAY_TASKS, jl.DAY_MIN_S), (8, 1200))
        self.assertTrue(40 <= jl.TASK_MIN_S <= 60)
        s = self.jailed()
        b, d = s['journey']['jail'], s['journey']['jail2']
        self.assertEqual(len(b['tasks']), 3)                      # the older servers' view
        self.assertEqual(b['tasks'], jl._pick(b['id'], 1))
        self.assertTrue(set(b['tasks']) <= set(jl.OLD_TASK_IDS))
        self.assertEqual(len(d['tasks']), 8)
        self.assertEqual(len(set(d['tasks'])), 8)                 # no repeats
        self.assertTrue(set(b['tasks']) <= set(d['tasks']))
        self.assertEqual(d['tasks'], jl._pick_day(b['id'], 1))    # fixed by (sentence, day)
        self.assertFalse(d['old'])
        pub = public_state(s)['jail']
        self.assertEqual([t['id'] for t in pub['tasks']], d['tasks'])
        self.assertTrue(all('pz' in t for t in pub['tasks']))
        self.assertEqual(pub['ready'], b['since'] + jl.DAY_MIN_S)
        seen = set()
        for day in range(1, 9):
            seen |= set(jl._pick_day('abc123', day))
            self.assertEqual(len(set(jl._pick_day('abc123', day))), 8)
        self.assertEqual(seen, set(jl.TASKS))                     # every kind comes up
        self.assertNotEqual(jl._pick_day('abc123', 1), jl._pick_day('abc123', 2))

    def test_too_fast_wrong_or_not_started_is_refused(self):
        for task in jl.TASKS:
            s = self.jailed()
            j = s['journey']
            rest = [t for t in jl.TASK_IDS if t not in j['jail']['tasks'] and t != task]
            j['jail2']['tasks'] = list(dict.fromkeys(j['jail']['tasks'] + [task] + rest))[:8]   # this kind today
            validate_state(s)
            with self.subTest(task=task):
                self.refused(s, 'jail_task_done', 'jail_not_started', task=task, ans={})
                s, r = self.act(s, 'jail_task_start', task=task)
                self.assertEqual(r['jail']['ready'], self.clock.t + jl.TASK_MIN_S)
                right = answer(task, r['jail']['pz'])
                self.later(jl.TASK_MIN_S - 1)
                self.refused(s, 'jail_task_done', 'jail_fast', task=task, ans=right)
                self.later(1)
                self.refused(s, 'jail_task_done', 'jail_wrong', task=task, ans={'nope': 1})
                self.refused(s, 'jail_task_done', 'jail_wrong', task=task, ans=near_miss(task, r['jail']['pz']))
                s, r = self.act(s, 'jail_task_done', task=task, ans=right)
                self.assertIn(task, s['journey']['jail2']['done'])
                self.assertEqual(s['journey']['jail']['done'], [t for t in s['journey']['jail']['tasks'] if t == task])
                s, r = self.act(s, 'jail_task_done', task=task, ans=right)   # a retry: nothing more
                self.assertTrue(r['jail']['again'])
                self.refused(s, 'jail_task_start', 'already_done', task=task)
        other = next(x for x in jl.TASKS if x not in s['journey']['jail2']['tasks'])
        self.refused(s, 'jail_task_start', 'invalid_action', task=other)

    def test_every_puzzle_checks_its_answer(self):
        for task in jl.TASKS:
            for day in (1, 2, 3, 7):
                for sid in ('abc123', 'f00d42'):
                    pz = jl.puzzle(sid, day, task)
                    with self.subTest(task=task, day=day, sid=sid):
                        self.assertEqual(pz, jl.puzzle(sid, day, task))   # seeded
                        self.assertTrue(jl._right(task, pz, answer(task, pz)))
                        self.assertFalse(jl._right(task, pz, {}))
                        self.assertFalse(jl._right(task, pz, 'x'))
                        self.assertFalse(jl._right(task, pz, near_miss(task, pz)))
                        json.dumps(pz)   # it travels in the state
        for task in jl.OLD_TASK_IDS:   # an adopted day: the old sizes, the old layouts
            pz = jl.puzzle('abc123', 1, task, old=True)
            self.assertTrue(jl._right(task, pz, answer(task, pz)))
        self.assertEqual(len(jl.puzzle('abc123', 1, 'books', old=True)['nums']), 6)
        self.assertEqual(len(jl.puzzle('abc123', 1, 'books')['nums']), 9)

    def test_puzzles_are_bigger_now(self):
        for task, size in (('sweep', lambda p: len(p['piles'])), ('plant', lambda p: p['holes']), ('rice', lambda p: len(p['want'])),
                           ('paint', lambda p: len(p['dirty'])), ('books', lambda p: len(p['nums']))):
            for day in (1, 2, 3):
                self.assertGreater(size(jl.puzzle('abc123', day, task)), size(jl.puzzle('abc123', day, task, old=True)), task)

    def test_full_cong_ich_takes_a_day_off(self):
        s = self.jailed()
        s = self.solve(s, only=jl.day_of(s['journey'])['tasks'][:7])
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=1)
        self.assertEqual(s['journey']['jail']['left'], 2)   # 7 of 8: one day only
        self.assertFalse(any('giảm thêm một ngày' in x for x in r['effects']))
        self.assertEqual((len(s['journey']['jail2']['tasks']), s['journey']['jail2']['done'], s['journey']['jail2']['day']), (8, [], 2))
        s = self.solve(s)
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=2)
        self.assertTrue(r['jail']['free'])   # all 8: the day counts two
        self.assertNotIn('jail2', s['journey'])


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
                    dict(good, extra=1), dict(good, done=['books', 'books']), dict(good, tasks=['sweep', 'plant', 'mop'])):
            with self.subTest(bad=bad):
                s = story()
                s['journey']['jail'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)
        day = self.jailed()['journey']['jail2']
        for bad in ('x', dict(day, v=2), dict(day, old=1), dict(day, extra=1), dict(day, tasks=day['tasks'] + ['fly']),
                    dict(day, tasks=day['tasks'] + [day['tasks'][0]]), dict(day, done=['fly']), dict(day, go={'t': 'fly', 'at': 1}),
                    dict(day, day=0), dict(day, id='')):
            with self.subTest(bad=bad):
                s = self.jailed()
                s['journey']['jail2'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)

    def test_a_day_left_alone_goes(self):
        s = self.jailed()
        s['journey'].pop('jail')   # an older server let the player out (bail, last day): it never knew jail2
        validate_state(s)
        s, _ = self.act(s, 'start_day', 'milk_tea')
        self.assertNotIn('jail2', s['journey'])


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
    """Saves of this build validate (and migrate) on the releases it may be rolled back to: 1.9.29, 1.9.32, 1.9.33.
    A sentence an older server began goes on here by the old rules to the end of its day, then by the new ones."""

    def old_tree(self, release):
        if os.environ.get('MNL_JAIL_OLD_TREE'):
            return Path(os.environ['MNL_JAIL_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix=f'mnl-{release}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', release, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {release} (MNL_JAIL_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_old(self, release, prog, saves):
        old = self.old_tree(release)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x),
                   MNL_JAIL_OFF='0')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    VALIDATE = ('import json,sys;from game.engine import validate_state,migrate_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'out.append([s["journey"]["life_day"],bool(s["journey"].get("jail")),s["journey"]["wallet"],'
                'sorted(s["journey"].get("jail2",{}).get("done",[]))])\nprint(json.dumps(out))')

    def saves(self):
        """A sentence going on with new task kinds done and one started, a second day, a friend who paid bail."""
        s = self.jailed()
        d = s['journey']['jail2']
        new = [t for t in d['tasks'] if t not in jl.OLD_TASK_IDS]
        old3 = s['journey']['jail']['tasks']
        s = self.solve(s, only=new[:3] + old3[:1])
        s, r = self.act(s, 'jail_task_start', task=new[3])         # a new kind going on: not the old block's business
        mid = json.loads(json.dumps(s))
        s, r = self.act(s, 'jail_task_start', task=old3[1])        # one of the three going on: mirrored
        started = json.loads(json.dumps(s))
        self.assertEqual(started['journey']['jail']['go']['t'], old3[1])
        self.later(jl.DAY_MIN_S)
        s, _ = self.act(s, 'jail_end', day=1)
        second = json.loads(json.dumps(s))
        friend = story(40000)
        jr._wallet(friend['journey'], -jl.BAIL_XU, 'life', jl.BAIL_LABEL.format(name='Bé Na'))
        validate_state(friend)
        return [mid, started, second, friend], new[:3] + old3[:1]

    def check(self, release):
        saves, done = self.saves()
        got = self.run_old(release, self.VALIDATE, saves)
        self.assertEqual([g[1] for g in got], [True, True, True, False])
        self.assertEqual(got[0][3], sorted(done))                  # jail2 is kept as it is
        self.assertEqual(got[2][0], saves[0]['journey']['life_day'] + 1)
        self.assertEqual(got[3][2], 10000)

    def test_saves_validate_on_1_9_29(self):
        self.check(OLD_RELEASES['1.9.29'])

    def test_saves_validate_on_1_9_32(self):
        self.check(OLD_RELEASES['1.9.32'])

    def test_saves_validate_on_1_9_33(self):
        self.check(OLD_RELEASES['1.9.33'])

    def test_rolled_back_mid_day_then_forward(self):
        """1.9.33 plays on the day's three tasks (and may end it); back here, nothing done is lost."""
        saves, _ = self.saves()
        s = saves[1]   # day 1: four done (one of the three), one of the three going on
        three = s['journey']['jail']['tasks']
        prog = ('import json,sys,time\nfrom game import jail as jl\nfrom game.engine import apply_action,validate_state\n'
                'jl.now=lambda: %d\n'
                's=json.load(sys.stdin)[0]\nb=s["journey"]["jail"]\nt=b["go"]["t"]\n'
                'pz=jl.puzzle(b["id"],b["day"],t)\n'
                'ans={"sweep":{"swept":pz.get("piles")},"plant":{"steps":[list(jl.PLANT_STEPS)]*pz.get("holes",0)},'
                '"rice":{"scoops":pz.get("want")},"paint":{"cells":pz.get("dirty")},'
                '"books":{"order":sorted(range(len(pz.get("nums",[]))),key=lambda i:pz["nums"][i])}}[t]\n'
                's,r=apply_action(s,None,"jail_task_done",{"task":t,"ans":ans})\nvalidate_state(s)\n'
                'print(json.dumps([s]))') % (self.clock.t + 60)
        back = self.run_old(OLD_RELEASES['1.9.33'], prog, [s])[0]
        go = s['journey']['jail']['go']['t']
        self.assertIn(go, back['journey']['jail']['done'])
        self.assertNotIn(go, back['journey']['jail2']['done'])     # the older server never touched jail2
        self.later(60)
        validate_state(back)
        pub = public_state(back)['jail']
        self.assertTrue(next(t for t in pub['tasks'] if t['id'] == go)['done'])   # merged
        self.assertEqual(len(pub['tasks']), 8)
        back, _ = self.act(back, 'settings', sound=False)
        self.assertIn(go, back['journey']['jail2']['done'])
        self.assertEqual(sorted(back['journey']['jail']['done']), sorted(x for x in three if x in back['journey']['jail2']['done']))

    def test_a_day_ended_on_an_older_server_is_adopted(self):
        """1.9.33 ended day 1 (journey['jail'] on day 2, jail2 still on day 1): day 2 here is that server's day."""
        s = self.jailed()
        b = s['journey']['jail']
        self.later(jl.OLD_DAY_MIN_S)
        b.update(day=2, left=2, since=self.clock.t, tasks=jl._pick(b['id'], 2), done=[], go=None)   # what 1.9.33's jail_end writes
        validate_state(s)
        pub = public_state(s)['jail']
        self.assertEqual(([t['id'] for t in pub['tasks']], pub['ready']), (b['tasks'], b['since'] + jl.OLD_DAY_MIN_S))
        s, _ = self.act(s, 'settings', sound=False)
        self.assertEqual((s['journey']['jail2']['day'], s['journey']['jail2']['old']), (2, True))

    def test_a_sentence_begun_on_an_older_server_goes_on_here(self):
        """1.9.33 arrests (no jail2): here that day keeps its three tasks, 2-minute day and old sizes; the next is new."""
        prog = ('import json,sys\nfrom game import jail as jl, journey as jr\nfrom game.engine import new_state,validate_state\n'
                's=new_state();jr.enable_story(s,4242);s["journey"]["gender"]="female";s["journey"]["wallet"]=50000\n'
                'validate_state(s)\nprint(json.dumps([s,jl.arrest(s["journey"],"bm",3,%d)]))') % self.clock.t
        s, days = self.run_old(OLD_RELEASES['1.9.33'], prog, [])
        self.assertEqual(days, 3)
        self.assertNotIn('jail2', s['journey'])
        validate_state(s)
        pub = public_state(s)['jail']
        b = s['journey']['jail']
        self.assertEqual([t['id'] for t in pub['tasks']], b['tasks'])   # adopted: its own three
        self.assertEqual(pub['ready'], b['since'] + jl.OLD_DAY_MIN_S)
        self.assertEqual(pub['tasks'][0]['pz'], jl.puzzle(b['id'], 1, b['tasks'][0], old=True))
        s = self.solve(s)                                           # 15 s a task, the old sizes
        self.assertTrue(s['journey']['jail2']['old'])
        self.assertEqual(sorted(s['journey']['jail']['done']), sorted(b['tasks']))
        self.later(jl.OLD_DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=1)
        self.assertEqual(s['journey']['jail']['left'], 1)          # all three: the day counted two, as it would there
        d = s['journey']['jail2']
        self.assertEqual((len(d['tasks']), d['old'], d['day']), (8, False, 2))   # the next day: the new rules
        self.assertEqual(public_state(s)['jail']['ready'], s['journey']['jail']['since'] + jl.DAY_MIN_S)


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
