"""🧩 Ghép ba Phố Mây (game/tile_match.py, public/js/v4/tile-match.js): 100 solvable levels with a rising difficulty,
the server-authoritative replay (a fake win, too-fast play, a skipped level, boosters not granted), the daily cap and
booster prices, the Phúc lợi buff (0.2 % a level, 20 % at most) where money is earned and nowhere else, saves an
older build accepts, and the page's rules bit for bit the server's."""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import tile_match as tm
from game.engine import GameError, apply_action, new_state, validate_state
from game.tile_match_levels import LEVELS, SCORES
from tests.test_bank import story

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_792_000_000.0   # a fixed server clock


def act(s, name, **p):
    return apply_action(s, None, name, p)


class Clock:
    """Patch tile_match's clock; `tick(sec)` moves it."""
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, sec):
        self.t += sec


def with_clock(test):
    def run(self, *a, **k):
        self.clock = Clock()
        with mock.patch.object(tm, '_now', self.clock):
            return test(self, *a, **k)
    run.__name__ = test.__name__
    return run


def cleared(lv, wallet=5000):
    s = story(wallet)
    s['journey']['tile'] = dict(lv=lv, d=tm.today(), n=0, u={})
    validate_state(s)
    return s


# ---------------------------------------------------------------- levels
class Levels(unittest.TestCase):
    def test_hundred_compact_rows(self):
        self.assertEqual(len(LEVELS), 100)
        self.assertEqual(len(SCORES), 100)
        for row in LEVELS:
            self.assertEqual(len(row), 11)
            self.assertTrue(all(isinstance(x, (int, str, tuple)) for x in row), row)

    def test_every_level_is_solvable_by_the_solver_and_its_own_intended_order(self):
        for lv in range(1, 101):
            level = tm.build(lv)
            n = len(level['tiles'])
            self.assertEqual(n % 3, 0, lv)
            for k in set(t[3] for t in level['tiles']):
                self.assertEqual(sum(1 for t in level['tiles'] if t[3] == k) % 3, 0, (lv, k))
            path = tm.solve(level)
            self.assertIsNotNone(path, f'level {lv}: the solver finds no way')
            self.assertTrue(tm.replay(level, path).won, lv)
            self.assertTrue(tm.replay(level, level['solution']).won, lv)

    def test_generation_is_deterministic_and_the_page_never_gets_the_solution(self):
        for lv in (1, 37, 100):
            self.assertEqual(json.dumps(tm.build(lv)), json.dumps(tm.build(lv)))
            pub = tm.public_level(lv)
            self.assertNotIn('solution', pub)
            self.assertEqual(pub['tiles'], tm.level(lv)['tiles'])

    def test_the_curve_adds_kinds_layers_stacks_locks_and_ice(self):
        built = [tm.build(lv) for lv in range(1, 101)]
        kinds = [len(b['icons']) for b in built]
        self.assertEqual(kinds, sorted(kinds), 'item kinds never go down')
        self.assertEqual((kinds[0], kinds[-1]), (3, 17))
        tiles = [len(b['tiles']) for b in built]
        self.assertLess(sum(tiles[:10]) / 10, 30)
        self.assertGreater(sum(tiles[90:]) / 10, 120)
        flags = lambda b, f: sum(1 for t in b['tiles'] if t[4] & f)
        self.assertTrue(all(flags(b, tm.LOCK) == 0 for b in built[:39]))
        self.assertTrue(all(flags(b, tm.LOCK) >= 1 for b in built[39:]))
        self.assertTrue(all(flags(b, tm.ICE) == 0 for b in built[:54]))
        self.assertTrue(all(flags(b, tm.ICE) >= 2 for b in built[54:]))
        self.assertTrue(all(not b['stacks'] for b in built[:7]))
        self.assertTrue(all(b['stacks'] for b in built[7:]))
        self.assertEqual(max(len(s['ids']) for s in built[-1]['stacks']), 10)
        peaks = [b['peak'] for b in built]
        self.assertEqual(peaks, sorted(peaks), 'the tray margin only tightens')
        self.assertEqual({b['shape'] for b in built[9::10]} >= {'house', 'heart', 'pagoda', 'lighthouse', 'lantern', 'boba', 'bridge'}, True)
        for b in built:   # a lock opens only once its key tile is taken
            for t, f in enumerate(x[4] for x in b['tiles']):
                if f & tm.LOCK:
                    self.assertTrue(any(b['tiles'][k][4] & tm.KEY_TILE for k in b['b'][t]))

    def test_difficulty_rises(self):
        dec = [sum(SCORES[i:i + 10]) / 10 for i in range(0, 100, 10)]
        self.assertEqual(dec, sorted(dec))
        self.assertTrue(all(b - a > 2 for a, b in zip(dec, dec[1:])), dec)
        top = 0
        for lv, d in enumerate(SCORES, 1):
            self.assertGreater(d, top - 8, f'level {lv} far easier than one before it')
            top = max(top, d)
        # Spearman's rank correlation with the level number
        rank = {i: r for r, i in enumerate(sorted(range(100), key=lambda i: SCORES[i]))}
        rho = 1 - 6 * sum((rank[i] - i) ** 2 for i in range(100)) / (100 * (100 ** 2 - 1))
        self.assertGreater(rho, 0.97)
        for lv in (1, 30, 60, 100):   # the stored scores are what the code computes
            self.assertAlmostEqual(tm.difficulty(tm.build(lv)), SCORES[lv - 1], places=2)

    def test_the_rng_is_deterministic_32_bit(self):
        a, b = tm.Rng(99), tm.Rng(99)
        xs = [a.next() for _ in range(50)]
        self.assertEqual(xs, [b.next() for _ in range(50)])
        self.assertTrue(all(0 <= x < 2 ** 32 for x in xs))
        self.assertEqual(len(set(xs)), 50)


# ---------------------------------------------------------------- rules
class Rules(unittest.TestCase):
    def setUp(self):
        self.level = tm.level(1)

    def test_tray_groups_triples_vanish_and_a_full_tray_loses(self):
        g = tm.Game(self.level)
        k = g.kind
        a, b = [t for t in range(g.n) if k[t] == 0][:2]
        g.tap(a)
        c = next(t for t in range(g.n) if k[t] == 1 and g.open(t))
        g.tap(c)
        g.tap(b)
        self.assertEqual(g.tray, [a, b, c], 'same items sit together')
        third = next(t for t in range(g.n) if k[t] == 0 and g.where[t] == 'b')
        self.assertEqual(sorted(g.tap(third)), sorted([a, b, third]))
        self.assertEqual(g.tray, [c])
        lv = dict(self.level, cap=2)
        g = tm.Game(lv)
        g.tap(next(t for t in range(g.n) if k[t] == 0))
        g.tap(next(t for t in range(g.n) if k[t] == 1))
        self.assertTrue(g.lost)
        with self.assertRaises(tm.Bad):
            g.tap(next(t for t in range(g.n) if g.where[t] == 'b'))

    def test_covered_tiles_and_stacks_cannot_be_tapped(self):
        level = tm.level(30)
        g = tm.Game(level)
        covered = next(t for t in range(g.n) if level['b'][t])
        with self.assertRaises(tm.Bad):
            g.tap(covered)
        st = level['stacks'][0]['ids']
        self.assertTrue(g.open(st[0]))
        self.assertFalse(g.open(st[1]))

    def test_boosters(self):
        level = tm.level(20)
        g = tm.Game(level)
        with self.assertRaises(tm.Bad):
            g.undo()
        t = next(t for t in range(g.n) if g.open(t))
        g.tap(t)
        g.undo()
        self.assertEqual(g.where[t], 'b')
        before = list(g.kind)
        g.shuffle()
        self.assertEqual(sorted(before), sorted(g.kind))
        self.assertNotEqual(before, g.kind)
        g2 = tm.Game(level)
        g2.shuffle()
        self.assertEqual(g.kind, g2.kind, 'a shuffle is the same on every replay')
        opens = [t for t in range(g.n) if g.open(t)]
        for t in opens[:2]:
            g.tap(t)
        n = min(3, len(g.tray))
        first = g.tray[:n]
        g.push()
        self.assertEqual(g.hold, first)
        with self.assertRaises(tm.Bad):
            g.push()
        h = g.hold[0]
        g.tap(h)
        self.assertEqual(g.where[h], 't')
        g.slot()
        self.assertEqual(g.cap, 8)
        with self.assertRaises(tm.Bad):
            g.slot()

    def test_ice_needs_two_taps(self):
        level = tm.level(60)
        g = tm.Game(level)
        ice = [t for t in range(g.n) if level['tiles'][t][4] & tm.ICE]
        self.assertTrue(ice)
        path = level['solution']
        self.assertEqual(len(path), g.n + len(ice))


# ---------------------------------------------------------------- commands and anti-cheat
class Commands(unittest.TestCase):
    @with_clock
    def test_first_clear_counts_once_and_gives_the_buff(self):
        s = cleared(0)
        s, r = act(s, 'jr_tile_start', lv=1)
        self.clock.tick(30)
        moves = tm.level(1)['solution']
        s, r = act(s, 'jr_tile_end', lv=1, moves=moves)
        self.assertTrue(r['win'] and r['first'])
        self.assertEqual(s['journey']['tile']['lv'], 1)
        self.assertEqual(tm.permille(s), 2)
        self.assertIn('Phúc lợi +0,2%', r['message'])
        self.assertNotIn('cur', s['journey']['tile'])
        # a replay for fun: allowed, nothing more
        s, _ = act(s, 'jr_tile_start', lv=1)
        self.clock.tick(30)
        s, r = act(s, 'jr_tile_end', lv=1, moves=moves)
        self.assertTrue(r['win'])
        self.assertFalse(r['first'])
        self.assertEqual(s['journey']['tile']['lv'], 1)
        self.assertEqual(s['journey']['tile']['n'], 1)
        validate_state(s)

    @with_clock
    def test_a_fake_win_is_refused(self):
        s = cleared(0)
        s, _ = act(s, 'jr_tile_start', lv=1)
        self.clock.tick(60)
        sol = tm.level(1)['solution']
        s2, r = act(s, 'jr_tile_end', lv=1, moves=sol[:-3])   # not cleared
        self.assertFalse(r['win'])
        self.assertEqual(s2['journey']['tile']['lv'], 0)
        level = tm.level(12)
        s, _ = act(cleared(11), 'jr_tile_start', lv=12)
        self.clock.tick(60)
        covered = next(t for t in range(len(level['tiles'])) if level['b'][t])
        for fake in ([covered] + level['solution'], level['solution'] + [0], [9999], ['1'], list(range(len(level['tiles'])))):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_tile_end', lv=12, moves=fake)
            self.assertEqual(e.exception.code, 'tile_invalid', fake[:4])
        with self.assertRaises(GameError):
            act(s, 'jr_tile_end', lv=12, moves=tm.level(11)['solution'])   # another level's win

    @with_clock
    def test_too_fast_play_is_refused(self):
        s = cleared(9)
        s, _ = act(s, 'jr_tile_start', lv=10)
        sol = tm.level(10)['solution']
        self.clock.tick(19)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_end', lv=10, moves=sol)
        self.assertEqual(e.exception.code, 'tile_fast')
        self.clock.tick(len(sol) * 0.25 - 19 - 0.5 + 20)   # 20 s passed, but not 0.25 s a tap on a big level
        if len(sol) * 0.25 > 20.5:
            with self.assertRaises(GameError):
                act(s, 'jr_tile_end', lv=10, moves=sol)
        self.clock.tick(5)
        s, r = act(s, 'jr_tile_end', lv=10, moves=sol)
        self.assertTrue(r['first'])

    @with_clock
    def test_a_skipped_level_and_a_stale_end_are_refused(self):
        s = cleared(3)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_start', lv=5)
        self.assertEqual(e.exception.code, 'tile_locked')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_end', lv=4, moves=[])
        self.assertEqual(e.exception.code, 'tile_none')
        s, _ = act(s, 'jr_tile_start', lv=4)
        self.clock.tick(100)
        with self.assertRaises(GameError):
            act(s, 'jr_tile_end', lv=5, moves=tm.level(5)['solution'])
        for bad in (0, 101, '4', None, 4.0):
            with self.assertRaises(GameError):
                act(s, 'jr_tile_start', lv=bad)
        with self.assertRaises(GameError):
            act(story(), 'jr_tile_start', lv=2)   # a save with no levels yet starts at 1
        plain = new_state()
        with self.assertRaises(GameError):
            act(plain, 'jr_tile_start', lv=1)

    @with_clock
    def test_boosters_must_be_granted_first(self):
        s = cleared(19)
        s, _ = act(s, 'jr_tile_start', lv=20)
        self.clock.tick(100)
        sol = tm.level(20)['solution']
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_end', lv=20, moves=[sol[0], tm.MOVE['undo']] + sol)
        self.assertEqual(e.exception.code, 'tile_invalid')
        s, r = act(s, 'jr_tile_boost', kind='undo', lv=20)
        s, r = act(s, 'jr_tile_end', lv=20, moves=[sol[0], tm.MOVE['undo']] + sol)
        self.assertTrue(r['first'])

    @with_clock
    def test_daily_cap_on_new_levels_replays_stay_open_and_the_next_day_resets(self):
        s = cleared(20)
        s['journey']['tile']['n'] = tm.CAP_DAY
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_start', lv=21)
        self.assertEqual(e.exception.code, 'tile_cap')
        s, _ = act(s, 'jr_tile_start', lv=7)   # an old level, for fun
        self.clock.tick(24 * 3600)
        s, r = act(s, 'jr_tile_start', lv=21)
        self.assertEqual(s['journey']['tile']['n'], 0)
        self.assertEqual(s['journey']['tile']['d'], tm.today())

    @with_clock
    def test_fifteen_new_levels_a_day(self):
        s = cleared(0)
        for lv in range(1, 17):
            if lv == 16:
                with self.assertRaises(GameError):
                    act(s, 'jr_tile_start', lv=lv)
                break
            s, _ = act(s, 'jr_tile_start', lv=lv)
            self.clock.tick(200)
            s, r = act(s, 'jr_tile_end', lv=lv, moves=tm.level(lv)['solution'])
            self.assertTrue(r['first'])
        self.assertEqual(s['journey']['tile']['lv'], 15)
        self.assertEqual(tm.permille(s), 30)

    @with_clock
    def test_booster_prices_free_then_doubling_within_a_level(self):
        s = cleared(9, wallet=10_000)
        s, _ = act(s, 'jr_tile_start', lv=10)
        w = s['journey']['wallet']
        costs = []
        for _ in range(6):
            s, r = act(s, 'jr_tile_boost', kind='undo', lv=10)
            costs.append(r['cost'])
        base = tm.PRICE['undo']
        self.assertEqual(costs, [0, 0, 0, base, base * 2, base * 4])
        self.assertEqual(w - s['journey']['wallet'], base * 7)
        s, r = act(s, 'jr_tile_boost', kind='shuffle', lv=10)
        self.assertEqual(r['cost'], 0)
        s, r = act(s, 'jr_tile_boost', kind='shuffle', lv=10)
        self.assertEqual(r['cost'], tm.PRICE['shuffle'])
        s, r = act(s, 'jr_tile_boost', kind='slot', lv=10)
        with self.assertRaises(GameError):
            act(s, 'jr_tile_boost', kind='slot', lv=10)
        # a new level: paid prices start again from the base; the free ones are spent for today
        s, _ = act(s, 'jr_tile_start', lv=9)
        s, r = act(s, 'jr_tile_boost', kind='undo', lv=9)
        self.assertEqual(r['cost'], base)
        self.assertEqual(tm.public(s)['free']['undo'], 0)
        self.clock.tick(24 * 3600)
        self.assertEqual(tm.public(s)['free'], tm.FREE)
        poor = cleared(0, wallet=0)
        poor['journey']['tile']['u'] = dict(tm.FREE)
        poor, _ = act(poor, 'jr_tile_start', lv=1)
        with self.assertRaises(GameError):
            act(poor, 'jr_tile_boost', kind='undo', lv=1)
        for bad in ('x', None):
            with self.assertRaises(GameError):
                act(s, 'jr_tile_boost', kind=bad, lv=9)
        validate_state(s)

    @with_clock
    def test_reset_all_keeps_the_levels(self):
        s = cleared(42)
        s, _ = act(s, 'jr_tile_start', lv=43)
        s, _ = apply_action(s, None, 'reset_all', {'confirm': 'BAT DAU LAI'})
        self.assertEqual(s['journey']['tile']['lv'], 42)
        self.assertNotIn('cur', s['journey']['tile'])

    def test_public_view_without_a_save_block(self):
        v = tm.public(story())
        self.assertEqual((v['lv'], v['pm'], v['pct'], v['n']), (0, 0, '0', 0))
        self.assertEqual(v['free'], tm.FREE)
        self.assertNotIn('tile', apply_action(story(), None, 'jr_tile_quit', {})[0]['journey'], 'nothing saved until played')
        from game.engine import public_state
        self.assertEqual(public_state(story())['journey']['tile']['lv'], 0)

    def test_validation(self):
        s = cleared(10)
        for bad in (dict(lv=101, d='2026-10-14', n=0, u={}), dict(lv=1, d='x', n=0, u={}), dict(lv=1, d=tm.today(), n=16, u={}),
                    dict(lv=1, d=tm.today(), n=0, u={'undo': 9}), dict(lv=1, d=tm.today(), n=0, u={}, x=1),
                    dict(lv=1, d=tm.today(), n=0, u={}, cur=dict(lv=5, t=0, b={}, p={})), 'x'):
            s2 = copy.deepcopy(s)
            s2['journey']['tile'] = bad
            with self.assertRaises(GameError):
                validate_state(s2)


# ---------------------------------------------------------------- the buff
class Buff(unittest.TestCase):
    def test_math(self):
        for lv, pm in ((0, 0), (1, 2), (50, 100), (99, 198), (100, 200)):
            self.assertEqual(tm.permille(cleared(lv)), pm)
        self.assertEqual(tm.pct_text(2), '0,2')
        self.assertEqual(tm.pct_text(200), '20')
        s = cleared(100)
        self.assertEqual(tm.extra(s, 1000, 'k'), 200)
        self.assertEqual(tm.extra(cleared(50), 1000, 'k'), 100)
        self.assertEqual(tm.extra(cleared(0), 1000, 'k'), 0)
        self.assertEqual(tm.extra(s, -50, 'k'), 0)
        self.assertEqual(tm.extra(s, 7, 'k'), tm.extra(s, 7, 'k'), 'the same event, the same xu')
        one = cleared(1)
        total = sum(tm.extra(one, 37, f'job-{i}') for i in range(4000))
        self.assertAlmostEqual(total / 4000, 37 * 0.002, delta=0.02, msg='fractions are fair on average')

    def test_own_job_completion(self):
        from game.engine import task_done
        out = []
        for lv in (0, 50):
            s = cleared(lv)
            c = s['careers']['mother_baby']
            t = dict(id='test-tile', career='mother_baby', npc='mai', title='Đơn kiểm thử', mistakes=0)
            before = c['money']
            with mock.patch('game.engine.fbk.make_review', return_value={'text': 'OK', 'stars': 4, 'feedback': {}, 'aside': False}), \
                    mock.patch('game.engine.life.after_task'), mock.patch('game.engine.ovt.on_job'):
                task_done(s, c, t, 200, 'Hoàn thành')
            out.append(c['money'] - before)
            rows = [r for r in c['ops']['finance']['ledger'] if r['reason'].startswith(tm.PREFIX)]
            self.assertEqual(len(rows), 1 if lv else 0)
            f = c['ops']['finance']
            self.assertEqual(c['money'], f['opening_balance'] + sum(x['amount'] for x in f['ledger']))
        self.assertEqual(out, [200, 220])

    def test_salary(self):
        from game import employment
        from tests.helpers import Journey
        got = []
        for lv in (0, 100):
            j = Journey('teacher')
            j.state['journey']['tile'] = dict(lv=lv, d=tm.today(), n=0, u={})
            j.c['day_completed'] = 1
            note = employment.on_close(j.state, j.c, 'teacher')
            got.append(note['salary'])
        self.assertEqual(got[1], got[0] + tm.extra(cleared(100), got[0], f"salary-1|Lương ngày 1|1"))
        self.assertAlmostEqual(got[1] / got[0], 1.2, delta=0.02)

    def test_staff_orders(self):
        from game import workplace_business as wb
        from tests.test_workplace_business import WorkplaceBusinessTests
        sample = WorkplaceBusinessTests()
        s, c, e = sample.sample()
        other = copy.deepcopy(s)
        other['journey']['tile'] = dict(lv=100, d=tm.today(), n=0, u={})
        at = sample.next(c)
        wb.settle(s, at)
        wb.settle(other, at)
        boosted = other['careers']['accounting']
        self.assertGreater(boosted['money'], c['money'])
        rows = [r for r in boosted['ops']['finance']['ledger'] if r['reason'].startswith(tm.PREFIX)]
        self.assertTrue(rows)
        self.assertEqual(wb._recent(boosted)[-1]['net'], wb._recent(c)[-1]['net'], 'the receipt keeps its own sums')
        f = boosted['ops']['finance']
        self.assertEqual(boosted['money'], f['opening_balance'] + sum(x['amount'] for x in f['ledger']))
        wb.validate(boosted, 'accounting')

    def test_counter_sales(self):
        from game import quay_business as qb
        from tests.test_quay_business import fixture
        s, st = fixture()
        qb.initialize(s, st, 1000)
        plain = copy.deepcopy(st)
        s['journey']['tile'] = dict(lv=100, d=tm.today(), n=0, u={})
        dish = next(iter(st['business']['stock']))
        st['business']['stock'][dish] = plain['business']['stock'][dish] = 20
        for n in range(10):
            qb.sale(st, [dish], 1000000 + n, owner=s)
            qb.sale(plain, [dish], 1000000 + n)
        self.assertEqual(st['business']['revenue'], plain['business']['revenue'])
        self.assertEqual(st['business']['profit_boost'], plain['business']['profit_boost'])
        gain = st['till'] - plain['till']
        self.assertGreater(gain, 0)
        s0 = copy.deepcopy(s)
        s0['journey']['tile']['lv'] = 0
        again = copy.deepcopy(plain)
        qb.sale(again, [dish], 2000000, owner=s0)
        qb.sale(plain, [dish], 2000000)
        self.assertEqual(again, plain, 'no levels: exactly as before')

    def test_settlements_book_their_own_row(self):
        src = (ROOT / 'game' / 'career_scale_contracts.py').read_text(encoding='utf-8')
        self.assertRegex(src, r"tile_match\.extra\(s,max\(0,receipt\['net'\]\)")
        src = (ROOT / 'game' / 'career_specialism_jobs.py').read_text(encoding='utf-8')
        self.assertRegex(src, r"tile_match\.extra\(s,max\(0,receipt\['net'\]\)")

    def test_never_twice_on_the_x3_day(self):
        from game import journey as jr, x3_week as x3
        s = story()
        cid = 'milk_tea'
        with mock.patch.object(x3, 'on', lambda c, t=None: c == cid):
            res = {'summary': {'net': 140, 'tile': 40, 'job': {}}}
            jr._end_of_day(s, cid, res)
        rows = [r['amount'] for r in s['journey']['history'] if r['label'].startswith('🔥')]
        self.assertEqual(rows, [x3.bonus(100)])

    def test_day_total_reads_only_the_buff_rows(self):
        s = cleared(100)
        c = s['careers']['mother_baby']
        from game.engine import money
        money(s, c, 50, 'Hoàn thành: x')
        tm.fund_bonus(s, c, 500, 'Đơn', 'r1')
        tm.fund_bonus(s, c, 100, 'Đơn', 'r2', direct=True)
        self.assertEqual(tm.day_total(c, c['day']), 120)
        self.assertEqual(tm.day_total(c, c['day'] + 1), 0)

    def test_only_earning_places_call_it(self):
        """The buff lives at the earning hooks; bank interest, Mây Coin, gold, the fair and black market, dog bark,
        auctions, transfers, gifts and mishaps never reach it."""
        callers = set()
        for p in (ROOT / 'game').rglob('*.py'):
            if p.name in ('tile_match.py', 'tile_match_levels.py'):
                continue
            src = p.read_text(encoding='utf-8')
            if re.search(r'tile_match|fund_bonus', src):
                callers.add(p.relative_to(ROOT / 'game').as_posix())
        self.assertEqual(callers, {'income_gear.py', 'employment.py', 'accounting_school.py', 'workplace_business.py',
                                   'quay_business.py', 'career_scale_contracts.py',
                                   'career_specialism_jobs.py', 'clothing_abroad.py', 'engine.py', 'journey.py'})

    def test_gifts_and_bank_interest_are_untouched(self):
        from game import bank as bk, system_gift
        out = []
        for lv in (0, 100):
            s = cleared(lv)
            s, _ = system_gift.apply(s, dict(id='g-tile-1', coins=1000))
            out.append(s['journey']['wallet'])
        self.assertEqual(out[0], out[1])
        src = (ROOT / 'game' / 'bank.py').read_text(encoding='utf-8')
        self.assertNotIn('tile_match', src)


# ---------------------------------------------------------------- saves an older build reads
class OlderBuild(unittest.TestCase):
    """2.4.2 (origin/main at this branch's base) keeps journey['tile'] and validates the save; a rollback and a roll
    forward lose nothing."""
    @classmethod
    def setUpClass(cls):
        if not shutil.which('git'):
            raise unittest.SkipTest('no git')
        ref = os.environ.get('TILE_OLD_REF', 'origin/main')
        cls.tmp = tempfile.mkdtemp(prefix='tile-old-')
        arch = subprocess.run(['git', 'archive', ref], cwd=ROOT, capture_output=True)
        if arch.returncode:
            raise unittest.SkipTest(f'git archive {ref}: {arch.stderr.decode()[:200]}')
        subprocess.run(['tar', '-x', '-C', cls.tmp], input=arch.stdout, check=True)
        if (Path(cls.tmp) / 'game' / 'tile_match.py').exists():
            raise unittest.SkipTest(f'{ref} already has the mini-game')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'tmp', ''), ignore_errors=True)

    def old(self, state, action=None):
        code = ('import json,sys\nfrom game.engine import validate_state,apply_action\n'
                's=json.load(sys.stdin)\nvalidate_state(s)\n'
                + (f's,_=apply_action(s,None,{action!r},{{"sound":False}})\n' if action else '')
                + 'print(json.dumps(s["journey"].get("tile")))')
        r = subprocess.run([sys.executable, '-I', '-c', f'import sys;sys.path.insert(0,{self.tmp!r});' + code],
                           input=json.dumps(state), capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    @with_clock
    def test_old_build_keeps_the_block_and_new_build_reads_it_back(self):
        s = cleared(5)
        s, _ = act(s, 'jr_tile_start', lv=6)
        s, _ = act(s, 'jr_tile_boost', kind='undo', lv=6)
        validate_state(s)
        kept = self.old(json.loads(json.dumps(s)), 'settings')
        self.assertEqual(kept, s['journey']['tile'])
        back = json.loads(json.dumps(s))
        back['journey']['tile'] = kept
        validate_state(back)
        self.assertEqual(tm.permille(back), 10)


# ---------------------------------------------------------------- the page plays the same rules
class PageParity(unittest.TestCase):
    def test_js_game_matches_python(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        cases = []
        for lv in (3, 22, 47, 64, 88):
            level = tm.public_level(lv)
            g = tm.Game(level)
            r = tm.Rng(lv * 31 + 7)
            moves = []
            for _ in range(400):
                if g.over:
                    break
                opts = [t for t in range(g.n) if g.open(t)]
                if g.undo_stack:
                    opts.append(tm.MOVE['undo'])
                if not g.hold and g.tray:
                    opts.append(tm.MOVE['push'])
                if g.slots < tm.SLOT_MAX:
                    opts.append(tm.MOVE['slot'])
                opts.append(tm.MOVE['shuffle'])
                m = r.pick(opts)
                try:
                    g.move(m)
                except tm.Bad:
                    continue
                moves.append(m)
            cases.append(dict(level=level, moves=moves, want=dict(kind=g.kind, where=g.where, tray=g.tray, hold=g.hold,
                                                                   cap=g.cap, gone=g.gone, lost=g.lost, taps=g.taps)))
            cases.append(dict(level=level, moves=tm.level(lv)['solution'], want=None))
        rngs = [[r.next() for _ in range(5)] for r in map(tm.Rng, (0, 1, 123456789, 4294967295))]
        script = ROOT / 'public' / 'js' / 'v4' / 'tile-match.js'
        code = f'''
import {{Game,rng,shuffleSeed}} from {json.dumps(script.as_uri())};
let data='';process.stdin.on('data',d=>data+=d);process.stdin.on('end',()=>{{
  const {{cases,seeds}}=JSON.parse(data);const out=[];
  for(const c of cases){{const g=new Game(c.level);for(const m of c.moves)g.move(m);
    out.push({{kind:g.kind,where:g.where,tray:g.tray,hold:g.hold,cap:g.cap,gone:g.gone,lost:g.lost,taps:g.taps,won:g.won}});}}
  const rs=seeds.map(s=>{{const r=rng(s);return [r.next(),r.next(),r.next(),r.next(),r.next()];}});
  console.log(JSON.stringify({{out,rs,ss:[shuffleSeed(77,0),shuffleSeed(4294967295,3)]}}));}});
'''
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'parity.mjs'
            f.write_text(code, encoding='utf-8')
            r = subprocess.run([node, str(f)], input=json.dumps(dict(cases=cases, seeds=[0, 1, 123456789, 4294967295])),
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(got['rs'], rngs)
        self.assertEqual(got['ss'], [tm.shuffle_seed(77, 0), tm.shuffle_seed(4294967295, 3)])
        for c, o in zip(cases, got['out']):
            if c['want'] is None:
                self.assertTrue(o['won'])
            else:
                won = o.pop('won')
                self.assertEqual(o, c['want'])
                self.assertEqual(won, c['want']['gone'] == len(c['level']['tiles']))


if __name__ == '__main__':
    unittest.main()
