"""🧩 Ghép ba Phố Mây (game/tile_match.py, public/js/v4/tile-match.js): 200 solvable levels with a rising difficulty,
the server-authoritative replay (a fake win, too-fast play, a skipped level, boosters not granted), the daily cap and
booster prices, the Phúc lợi buff (0.2 % a level to 100, then 0.1 %: 30 % at most) where money is earned and nowhere else, saves an
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
    s['journey']['tile'] = dict(lv=min(lv, tm.BASE_MAX), d=tm.today(), n=0, u={})
    if lv > tm.BASE_MAX:
        s['journey']['tile_hi'] = dict(lv=lv - tm.BASE_MAX)
    validate_state(s)
    return s


# ---------------------------------------------------------------- levels
class Levels(unittest.TestCase):
    def test_two_hundred_compact_rows(self):
        """Levels 1–200 (201–300: tests/test_tile_match_300.py)."""
        self.assertEqual(len(LEVELS), tm.LEVEL_MAX)
        self.assertEqual(len(SCORES), tm.LEVEL_MAX)
        self.assertEqual(tm.HI_MAX, 200)
        for row in LEVELS[:tm.HI_MAX]:
            self.assertEqual(len(row), 11)
            self.assertTrue(all(isinstance(x, (int, str, tuple)) for x in row), row)

    def test_every_level_is_solvable_by_the_solver_and_its_own_intended_order(self):
        for lv in range(1, tm.HI_MAX + 1):   # 201–300: tests/test_tile_match_300.py
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
        for lv in (1, 37, 100, 160, 200):
            self.assertEqual(json.dumps(tm.build(lv)), json.dumps(tm.build(lv)))
            pub = tm.public_level(lv)
            self.assertNotIn('solution', pub)
            self.assertEqual(pub['tiles'], tm.level(lv)['tiles'])

    def test_the_curve_adds_kinds_layers_stacks_locks_and_ice(self):
        built = [tm.build(lv) for lv in range(1, 101)]
        kinds = [len(b['icons']) for b in built]
        self.assertEqual(kinds, sorted(kinds), 'item kinds never go down')
        self.assertEqual((kinds[0], kinds[4], kinds[-1]), (3, 7, 20))
        tiles = [len(b['tiles']) for b in built]
        self.assertLess(sum(tiles[:10]) / 10, 40)
        self.assertGreater(sum(tiles[90:]) / 10, 120)
        flags = lambda b, f: sum(1 for t in b['tiles'] if t[4] & f)
        self.assertTrue(all(flags(b, tm.LOCK) == 0 for b in built[:29]))
        self.assertTrue(all(flags(b, tm.LOCK) >= 1 for b in built[29:]))
        self.assertTrue(all(flags(b, tm.ICE) == 0 for b in built[:44]))
        self.assertTrue(all(flags(b, tm.ICE) >= 2 for b in built[44:]))
        self.assertTrue(all(not b['stacks'] for b in built[:4]))
        self.assertTrue(all(b['stacks'] for b in built[4:]), 'a stack from level 5')
        self.assertTrue(all(len(b['stacks']) >= 2 for b in built[9:]))
        layers = [1 + max(t[2] for t in b['tiles'][:b['board']]) for b in built]
        self.assertTrue(all(x >= 2 for x in layers[4:]), 'stacked layers from level 5')
        self.assertGreaterEqual(sum(layers[4:20]) / 16, 3.2, 'deeper than 2.4.5 (2.0 on levels 5–20)')
        self.assertEqual(max(len(s['ids']) for s in built[-1]['stacks']), 10)
        peaks = [b['peak'] for b in built]
        self.assertEqual(peaks, sorted(peaks), 'the tray margin only tightens')
        self.assertEqual({b['shape'] for b in built[9::10]} >= {'house', 'heart', 'pagoda', 'lighthouse', 'lantern', 'boba', 'bridge'}, True)
        for b in built:   # a lock opens only once its key tile is taken
            for t, f in enumerate(x[4] for x in b['tiles']):
                if f & tm.LOCK:
                    self.assertTrue(any(b['tiles'][k][4] & tm.KEY_TILE for k in b['b'][t]))

    def test_levels_101_to_200_keep_the_icons_and_stack_deeper(self):
        """Owner 17/10: past 100, harder by more layers ("xếp nhiều lớp hơn"); 18/10: and more icons ("thêm 30 40 loại
        thoải mái"). Levels 1–100 are the 2.4.7 table, unchanged (the stored rows are what --extend kept)."""
        old = [tm.build(lv) for lv in range(91, 101)]
        hi = [tm.build(lv) for lv in range(101, 201)]
        kinds = [len(b['icons']) for b in hi]
        self.assertEqual(kinds, sorted(kinds), 'icons never go down')
        self.assertGreaterEqual(kinds[0], 21)
        self.assertGreaterEqual(kinds[-1], 38)
        self.assertTrue(all(len(set(b['icons'])) == len(b['icons']) for b in hi))
        depth = lambda b: 1 + max(t[2] for t in b['tiles'][:b['board']])
        self.assertTrue(all(depth(b) >= 8 for b in hi), [depth(b) for b in hi])   # 91–100: 4 to 7
        self.assertTrue(all(depth(b) >= 11 for b in hi[-20:]), [depth(b) for b in hi[-20:]])
        self.assertGreaterEqual(sum(depth(b) for b in hi[50:]) / 50, 12)
        self.assertGreater(sum(depth(b) for b in hi[:10]) / 10, max(depth(b) for b in old) + 1, 'deeper from level 101')
        self.assertGreater(sum(len(b['tiles']) for b in hi[50:]) / 50, sum(len(b['tiles']) for b in old) / 10)
        straight = lambda b: sum(1 for t in b['tiles'][:b['board']] if [t[0], t[1], t[2] - 1] in [u[:3] for u in b['tiles'][:b['board']]])
        self.assertTrue(all(straight(b) for b in hi), 'some layers straight on the one below')
        self.assertTrue(all(straight(tm.build(lv)) == 0 for lv in range(1, 101, 9)), 'never on levels 1–100')
        self.assertTrue(all(row[5][0] in 'DHV' and len(row[5]) == 1 or row[5][0] in 'dhv' and row[5][1:] == '3' for row in LEVELS[100:]))
        self.assertTrue(all(row[5] in 'dhv' for row in LEVELS[:100]))

    def test_difficulty_rises(self):
        dec = [sum(SCORES[i:i + 10]) / 10 for i in range(0, 100, 10)]
        self.assertEqual(dec, sorted(dec))
        self.assertTrue(all(b - a > 1.5 for a, b in zip(dec, dec[1:])), dec)
        top = 0
        for lv, d in enumerate(SCORES[:100], 1):
            self.assertGreater(d, top - 8, f'level {lv} far easier than one before it')
            top = max(top, d)
        # Spearman's rank correlation with the level number
        rank = {i: r for r, i in enumerate(sorted(range(100), key=lambda i: SCORES[i]))}
        rho = 1 - 6 * sum((rank[i] - i) ** 2 for i in range(100)) / (100 * (100 ** 2 - 1))
        self.assertGreater(rho, 0.97)
        self.assertGreaterEqual(sum(SCORES[100:]) / 100, sum(SCORES[90:100]) / 10 - 1, 'levels 101–200 no easier than 91–100')
        for lv in (1, 30, 60, 100, 150, 200):   # the stored scores are what the code computes
            self.assertAlmostEqual(tm.difficulty(tm.build(lv)), SCORES[lv - 1], places=2)

    def test_harder_from_level_5(self):
        """Owner, 14/10 "quá dễ": the 2.4.5 table let the quick player (greedy_rate) win ~every level up to 20. Now it
        loses a fair share from level 5, most mid levels and nearly every late one (each still solvable, above)."""
        rate = [tm.greedy_rate(tm.level(lv)) for lv in range(1, 101)]
        old = [tm.greedy_rate(tm.level(lv, 1)) for lv in (5, 10, 15, 20)]
        self.assertGreater(min(old), 0.95)
        dec = [sum(rate[i:i + 10]) / 10 for i in range(0, 100, 10)]
        self.assertEqual(dec, sorted(dec, reverse=True), dec)
        self.assertTrue(all(r == 1 for r in rate[:4]))
        self.assertLess(max(rate[4:]), 0.91)
        self.assertLess(sum(rate[4:20]) / 16, 0.75)
        self.assertLess(sum(rate[30:60]) / 30, 0.40)
        self.assertLess(sum(rate[70:]) / 30, 0.15)
        hi = [tm.greedy_rate(tm.level(lv)) for lv in range(101, 201, 7)]
        self.assertLess(max(hi), 0.15, 'levels 101–200 stay as hard as the last ones')

    def test_icons_are_distinct_and_draw_on_ios_15(self):
        """A kind whose emoji the phone lacks draws as a blank box (two such kinds would look alike). The game opens on
        iOS 15.0 (scripts/check_old_safari.mjs): Emoji 13 at most. Emoji 12+ objects sit from U+1FA70 (🪷 U+1FAB7, Emoji
        14, was one until 2.4.10); the one Emoji 13 icon in use below that block is listed."""
        self.assertEqual(len(set(tm.ICONS)), len(tm.ICONS))
        newer = {'🧋'}   # Emoji 13.0 (iOS 14.2)
        for icon in tm.ICONS:
            self.assertTrue(icon in newer or all(ord(c) < 0x1FA70 for c in icon), icon)
            self.assertNotIn(icon, ('🪷',))
        for lv in range(1, 101):
            icons = tm.public_level(lv)['icons']
            self.assertEqual(len(set(icons)), len(icons), lv)

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
        self.assertEqual(s['journey']['tile']['cur'], dict(lv=2, t=int(self.clock.t * 1000), b={}, p={}), 'the clock, 2.4.5 shape')
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
        s2, r = act(s, 'jr_tile_end', lv=4, moves=[])   # a stale end of a game not won: nothing changes
        self.assertFalse(r['win'])
        self.assertEqual(s2['journey']['tile'], s['journey']['tile'])
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
    def test_a_245_page_boosters_granted_first_are_not_charged_twice(self):
        s = cleared(19)
        s['journey']['tile']['u'] = dict(tm.FREE)   # today's free uses spent
        s, _ = act(s, 'jr_tile_start', lv=20)
        self.clock.tick(100)
        sol = tm.level(20)['solution']
        w = s['journey']['wallet']
        s, r = act(s, 'jr_tile_boost', kind='undo', lv=20)
        self.assertEqual(r['cost'], tm.PRICE['undo'])
        s, r = act(s, 'jr_tile_end', lv=20, moves=[sol[0], tm.MOVE['undo']] + sol)
        self.assertTrue(r['first'])
        self.assertEqual(r['cost'], 0, 'granted and paid by jr_tile_boost')
        self.assertEqual(w - s['journey']['wallet'], tm.PRICE['undo'])

    @with_clock
    def test_daily_cap_on_new_levels_replays_stay_open_and_the_next_day_resets(self):
        s = cleared(20)
        s['journey']['tile']['n'] = tm.CAP_DAY
        s, _ = act(s, 'jr_tile_start', lv=21)   # owner 14/10: no daily cap any more
        s, _ = act(s, 'jr_tile_start', lv=7)   # an old level, for fun
        self.clock.tick(24 * 3600)
        s, r = act(s, 'jr_tile_start', lv=21)
        self.assertEqual(s['journey']['tile']['n'], 0)
        self.assertEqual(s['journey']['tile']['d'], tm.today())

    @with_clock
    def test_no_daily_cap_on_new_levels(self):
        """Owner 14/10: "đừng giới hạn 1 ngày 15 màn, chơi không giới hạn"."""
        s = cleared(0)
        for lv in range(1, 18):
            s, _ = act(s, 'jr_tile_start', lv=lv)
            self.clock.tick(200)
            s, r = act(s, 'jr_tile_end', lv=lv, moves=tm.level(lv)['solution'])
            self.assertTrue(r['first'])
        self.assertEqual(s['journey']['tile']['lv'], 17)
        self.assertEqual(tm.permille(s), 34)
        self.assertLessEqual(s['journey']['tile']['n'], tm.CAP_DAY)

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
        s, _ = act(s, 'jr_tile_boost', kind='undo', lv=43)
        clock = s['journey']['tile']['cur']['t']
        s, _ = apply_action(s, None, 'reset_all', {'confirm': 'BAT DAU LAI'})
        self.assertEqual(s['journey']['tile']['lv'], 42)
        self.assertEqual(s['journey']['tile']['cur'], dict(lv=43, t=clock, b={}, p={}), 'the clock stays, the attempt goes')
        s = cleared(160)
        s, _ = apply_action(s, None, 'reset_all', {'confirm': 'BAT DAU LAI'})
        self.assertEqual(tm.cleared(s), 160)

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


class PastHundred(unittest.TestCase):
    """2.4.43, levels 101–200: journey.tile.lv and cur.lv stay within 100 (older builds' bounds), journey.tile_hi counts
    the levels cleared past 100; +0.1 % a level there, 30 % at 200."""
    @with_clock
    def test_clearing_on_past_100(self):
        s = cleared(100)
        s['journey']['tile']['cur'] = dict(lv=100, t=int(T0 * 1000), b={}, p={})
        validate_state(s)
        self.assertEqual(tm.public(s)['max'], 200)
        with self.assertRaises(GameError) as e:
            end(s, 102)
        self.assertEqual(e.exception.code, 'tile_locked')
        for lv in (101, 102):
            self.clock.tick(tm.need_ms(len(tm.level(lv)['solution'])) / 1000)
            s, r = end(s, lv)
            self.assertTrue(r['win'] and r['first'], lv)
            validate_state(s)
        self.assertEqual(s['journey']['tile']['lv'], 100)
        self.assertEqual(s['journey']['tile']['cur']['lv'], 100)
        self.assertEqual(s['journey']['tile_hi'], dict(lv=2))
        self.assertEqual((tm.cleared(s), tm.permille(s), r['tile']['pct'], r['tile']['lv']), (102, 202, '20,2', 102))
        s, r = end(s, 101)   # a replay: nothing new
        self.assertFalse(r['first'])
        self.assertEqual(tm.cleared(s), 102)
        with self.assertRaises(GameError) as e:   # 2.4.5's table has 100 levels
            end(s, 103, v=1)
        self.assertEqual(e.exception.code, 'tile_level')
        with self.assertRaises(GameError) as e:   # an older page stops at 100
            act(s, 'jr_tile_start', lv=101)
        self.assertEqual(e.exception.code, 'tile_level')

    @with_clock
    def test_a_level_played_on_the_2443_table_still_counts(self):
        """2.4.44 rebuilt levels 101–200 (table 3); a page of 2.4.43 played table 2's level and says v=2."""
        self.assertNotEqual(tm.level(101, 2)['tiles'], tm.level(101)['tiles'])
        self.assertEqual(tm.level(57, 2)['tiles'], tm.level(57)['tiles'], 'levels 1–100 are the same in every table')
        s = cleared(100)
        s['journey']['tile']['cur'] = dict(lv=100, t=int(T0 * 1000), b={}, p={})
        sol = tm.level(101, 2)['solution']
        self.clock.tick(tm.need_ms(len(sol)) / 1000)
        with self.assertRaises(GameError) as e:   # table 2's taps do not win table 3's level
            end(s, 101, moves=sol)
        self.assertEqual(e.exception.code, 'tile_invalid')
        s, r = end(s, 101, moves=sol, v=2)
        self.assertTrue(r['first'])
        self.assertEqual(tm.cleared(s), 101)
        with self.assertRaises(GameError) as e:
            end(s, 102, v=4)
        self.assertEqual(e.exception.code, 'tile_level')

    @with_clock
    def test_level_200(self):
        """The last level until 2.5.7 (201–300 and journey.tile_hi2: tests/test_tile_match_300.py)."""
        s = cleared(199)
        s['journey']['tile']['cur'] = dict(lv=100, t=int(T0 * 1000), b={}, p={})
        self.clock.tick(tm.need_ms(len(tm.level(200)['solution'])) / 1000)
        s, r = end(s, 200)
        self.assertTrue(r['first'])
        self.assertEqual((tm.cleared(s), tm.permille(s), r['tile']['pct']), (200, 300, '30'))
        self.assertNotIn('tile_hi2', s['journey'])
        with self.assertRaises(GameError) as e:
            act(s, 'jr_tile_end', n=202, moves=[])
        self.assertEqual(e.exception.code, 'tile_locked')
        validate_state(s)

    def test_validation(self):
        validate_state(cleared(200))
        for tile, hi in ((100, dict(lv=101)), (99, dict(lv=1)), (100, dict(lv=1, x=1)), (100, dict(lv='1')), (100, 'x')):
            s = cleared(tile)
            s['journey']['tile_hi'] = hi
            with self.assertRaises(GameError, msg=(tile, hi)):
                validate_state(s)
        s = cleared(0)
        del s['journey']['tile']
        s['journey']['tile_hi'] = dict(lv=1)
        with self.assertRaises(GameError):
            validate_state(s)


# ---------------------------------------------------------------- 2.4.6: a level is self-describing (one command)
def end(s, n, moves=None, ms=None, **extra):
    p = dict(n=n, moves=tm.level(n)['solution'] if moves is None else moves, **extra)
    if ms is not None:
        p['ms'] = ms
    return act(s, 'jr_tile_end', **p)


class SelfDescribing(unittest.TestCase):
    """The owner's report (14/10): "ghi nhận lỗi khi qua các màn, mãi không ghi nhận" (4 × tile_none, uid 877). A page
    that left a pending win and restarted the level sent the old win's end with the NEW attempt's moves: it did not
    replay as a win, popped `cur`, and the real win then found none. Now an end needs nothing from the server first."""

    @with_clock
    def test_end_without_a_prior_start(self):
        s = story(5000)   # no tile block at all: the page's own time, once
        with self.assertRaises(GameError) as e:
            end(s, 1, ms=5000)
        self.assertEqual(e.exception.code, 'tile_fast')
        s, r = end(s, 1, ms=25_000)
        self.assertTrue(r['win'] and r['first'])
        self.assertEqual(tm.cleared(s), 1)
        # from now on the server's clock: the next first clear needs need_ms(taps) after this one
        self.clock.tick(5)
        with self.assertRaises(GameError) as e:
            end(s, 2, ms=10**6)   # the page's claim no longer matters
        self.assertEqual(e.exception.code, 'tile_fast')
        self.clock.tick(tm.need_ms(len(tm.level(2)['solution'])) / 1000)
        s, r = end(s, 2)
        self.assertTrue(r['first'])
        validate_state(s)

    @with_clock
    def test_a_double_start_or_a_quit_never_loses_a_clear(self):
        s = cleared(3)
        s, _ = act(s, 'jr_tile_start', lv=4)
        self.clock.tick(15)
        s, _ = act(s, 'jr_tile_start', lv=4)   # the same level again (a 2.4.5 page): the clock does not move
        s, _ = act(s, 'jr_tile_quit')
        s, _ = act(s, 'jr_tile_start', lv=2)   # even another level
        self.clock.tick(10)
        s, r = act(s, 'jr_tile_end', lv=4, moves=tm.level(4)['solution'])   # 2.4.5's payload, 25 s after the first start
        self.assertTrue(r['first'])
        self.assertEqual(tm.cleared(s), 4)

    @with_clock
    def test_the_reported_race_a_stale_end_then_the_real_one(self):
        s = cleared(1)
        s, _ = act(s, 'jr_tile_start', lv=2)
        self.clock.tick(30)
        partial = tm.level(2)['solution'][:4]   # the old win's end carrying the new attempt's first taps
        s, r = act(s, 'jr_tile_end', lv=2, moves=partial)
        self.assertFalse(r['win'])
        s, r = act(s, 'jr_tile_end', lv=2, moves=tm.level(2)['solution'])   # 2.4.5: tile_none here
        self.assertTrue(r['first'])

    @with_clock
    def test_a_retry_after_a_conflict_and_a_resent_end(self):
        s = cleared(5)
        s['journey']['tile']['cur'] = dict(lv=6, t=int(T0 * 1000), b={}, p={})
        self.clock.tick(100)
        before = copy.deepcopy(s)
        # 409: the answer was computed on a save that moved; nothing was stored and the page sends it again
        # against the refreshed save, which has no attempt record of this page at all (a quit from another tab).
        moved, _ = act(before, 'jr_tile_quit')
        s1, r = end(moved, 6)
        self.assertTrue(r['first'])
        # a lost answer, the same end again after a reload: a replay (nothing more), never a second buff
        s2, r = end(s1, 6)
        self.assertTrue(r['win'])
        self.assertFalse(r['first'])
        self.assertEqual((tm.cleared(s2), s2['journey']['tile']['n'], tm.permille(s2)), (6, 1, 12))

    @with_clock
    def test_min_time_taps_and_the_daily_cap(self):
        s = cleared(0)
        s['journey']['tile']['cur'] = dict(lv=1, t=int(T0 * 1000), b={}, p={})
        for lv in range(1, 16):
            sol = tm.level(lv)['solution']
            least = tm.need_ms(len(sol)) / 1000
            self.clock.tick(least - 1)
            with self.assertRaises(GameError) as e:
                end(s, lv)
            self.assertEqual(e.exception.code, 'tile_fast')
            self.clock.tick(1)
            s, r = end(s, lv)
            self.assertTrue(r['first'], lv)
        big = next(lv for lv in range(16, 101) if len(tm.level(lv)['solution']) * tm.MIN_TAP_MS > tm.MIN_LEVEL_MS)
        self.assertGreater(tm.need_ms(len(tm.level(big)['solution'])), tm.MIN_LEVEL_MS)
        self.clock.tick(3600)
        s, r = end(s, 16)   # owner 14/10: the 16th new level of the day counts too
        self.assertTrue(r['first'])
        self.assertLessEqual(s['journey']['tile']['n'], tm.CAP_DAY)   # older builds' bound kept
        s, r = end(s, 3)   # replays stay open
        self.assertFalse(r['first'])
        self.clock.tick(24 * 3600)
        s, r = end(s, 17)
        self.assertTrue(r['first'])
        self.assertEqual(s['journey']['tile']['n'], 1)

    @with_clock
    def test_a_replay_gives_no_buff_and_a_level_ahead_is_refused(self):
        s = cleared(7)
        self.clock.tick(100)
        for n in (1, 7):
            s2, r = end(s, n)
            self.assertTrue(r['win'])
            self.assertFalse(r['first'])
            self.assertEqual((tm.cleared(s2), tm.permille(s2), s2['journey']['tile']['n']), (7, 14, 0))
        with self.assertRaises(GameError) as e:
            end(s, 9)
        self.assertEqual(e.exception.code, 'tile_locked')
        for bad in (0, 101, '8', None, 8.0):
            with self.assertRaises(GameError):
                act(s, 'jr_tile_end', n=bad, moves=[])
        with self.assertRaises(GameError):
            act(s, 'jr_tile_end', n=8, moves=[], x=1)
        with self.assertRaises(GameError) as e:
            end(s, 8, moves=tm.level(9)['solution'])
        self.assertEqual(e.exception.code, 'tile_invalid')

    @with_clock
    def test_boosters_are_priced_at_the_end(self):
        s = cleared(9, wallet=10_000)
        s['journey']['tile']['cur'] = dict(lv=10, t=int(T0 * 1000), b={}, p={})
        self.clock.tick(600)
        sol = tm.level(10)['solution']
        U = tm.MOVE['undo']
        moves = [sol[0], U, sol[0], U, sol[0], U, sol[0], U, sol[0], U] + sol   # 5 undos: 3 free, then 40, 80
        w = s['journey']['wallet']
        s2, r = end(s, 10, moves=moves)
        base = tm.PRICE['undo']
        self.assertEqual(r['cost'], base + base * 2)
        self.assertEqual(w - s2['journey']['wallet'], base * 3)
        self.assertEqual(s2['journey']['tile']['u'], {'undo': 3})
        poor = copy.deepcopy(s)
        poor['journey']['wallet'] = base
        with self.assertRaises(GameError) as e:
            end(poor, 10, moves=moves)
        self.assertEqual(e.exception.code, 'tile_poor')
        # a replay pays its paid boosters too, from today's leftovers first
        s3, r = end(s2, 4, moves=[tm.level(4)['solution'][0], U] + tm.level(4)['solution'])
        self.assertEqual(r['cost'], base)
        self.assertFalse(r['first'])

    @with_clock
    def test_public_view_carries_the_clock(self):
        s = cleared(2)
        self.assertNotIn('at', tm.public(s))
        s, _ = end(s, 3, ms=30_000)
        v = tm.public(s)
        self.assertEqual(v['at'], int(self.clock.t * 1000))
        self.assertEqual(v['day'], tm.today())
        self.assertEqual(v['min'], dict(level=tm.MIN_LEVEL_MS, tap=tm.MIN_TAP_MS))


# ---------------------------------------------------------------- the buff
class Buff(unittest.TestCase):
    def test_math(self):
        for lv, pm in ((0, 0), (1, 2), (50, 100), (99, 198), (100, 200), (101, 201), (150, 250), (200, 300)):
            self.assertEqual(tm.permille(cleared(lv)), pm)
            self.assertEqual(tm.cleared(cleared(lv)), lv)
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
            if p.name in ('tile_match.py', 'tile_match_levels.py', 'tile_match_levels_v1.py', 'tile_match_levels_v2.py'):
                continue
            src = p.read_text(encoding='utf-8')
            if re.search(r'tile_match|fund_bonus', src):
                callers.add(p.relative_to(ROOT / 'game').as_posix())
        self.assertEqual(callers, {'income_gear.py', 'employment.py', 'accounting_school.py', 'workplace_business.py',
                                   'quay_business.py', 'career_scale_contracts.py',
                                   'career_specialism_jobs.py', 'clothing_abroad.py', 'engine.py', 'journey.py',
                                   'pet_tiers.py',   # 🐾 its own fund_bonus, called from tile_match.fund_bonus
                                   'pay_boost.py',    # 💰 Tiền công +%: its own row, called from tile_match.fund_bonus (docstring)
                                   'wings.py'})   # 🪽 the worn wing's +% (2.5.4): its own row, called from tile_match.fund_bonus

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
    """2.4.6 (rel-2.4.6, the live build when the self-describing end came; 2.4.5 passes the same) reads every journey['tile'] this build
    writes, plays on it with its own start/boost/end, and this build reads its saves back: a rollback and a roll
    forward lose nothing. TILE_OLD_REF picks another build."""
    @classmethod
    def setUpClass(cls):
        if not shutil.which('git'):
            raise unittest.SkipTest('no git')
        ref = os.environ.get('TILE_OLD_REF', 'rel-2.4.6')
        cls.tmp = tempfile.mkdtemp(prefix='tile-old-')
        arch = subprocess.run(['git', 'archive', ref], cwd=ROOT, capture_output=True)
        if arch.returncode:
            raise unittest.SkipTest(f'git archive {ref}: {arch.stderr.decode()[:200]}')
        subprocess.run(['tar', '-x', '-C', cls.tmp], input=arch.stdout, check=True)
        old = Path(cls.tmp) / 'game' / 'tile_match.py'
        if not old.exists() or 'def _end(' in old.read_text(encoding='utf-8'):
            raise unittest.SkipTest(f'{ref} is not a 2.4.5-style build')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'tmp', ''), ignore_errors=True)

    def old(self, state, steps=(), now=None):
        """Run the old build on `state`: validate, then each (action, payload) at its clock; returns (tile, results)."""
        code = ('import json,sys\nfrom game.engine import validate_state,apply_action\nfrom game import tile_match as tm\n'
                'd=json.load(sys.stdin)\ns=d["s"]\nvalidate_state(s)\nout=[]\n'
                'for a,p,t in d["steps"]:\n'
                '    tm._now=(lambda t=t:t)\n'
                '    s,r=apply_action(s,None,a,p)\n'
                '    out.append({k:r.get(k) for k in ("win","first","cost")})\n'
                'validate_state(s)\nprint(json.dumps([s["journey"].get("tile"),out,s["journey"].get("tile_hi")]))')
        r = subprocess.run([sys.executable, '-I', '-c', f'import sys;sys.path.insert(0,{self.tmp!r});' + code],
                           input=json.dumps(dict(s=state, steps=list(steps))), capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        tile, out, self.hi = json.loads(r.stdout.strip().splitlines()[-1])
        return tile, out

    @with_clock
    def test_old_build_keeps_and_plays_on_what_this_build_writes(self):
        s = story(5000)
        s, _ = end(s, 1, ms=30_000)   # no start at all
        self.clock.tick(40)
        s, _ = end(s, 2)
        s, _ = end(s, 1, moves=[tm.level(1)['solution'][0], tm.MOVE['undo']] + tm.level(1)['solution'])   # a replay
        s, _ = act(s, 'jr_tile_quit')
        validate_state(s)
        mine = json.loads(json.dumps(s))
        kept, _ = self.old(mine, [('settings', {'sound': False}, self.clock.t)])
        self.assertEqual(kept, s['journey']['tile'])
        # 2.4.5 plays level 3 on it (its own start, a booster, its end 100 s later)
        t = self.clock.t
        tile, out = self.old(mine, [('jr_tile_start', {'lv': 3}, t), ('jr_tile_boost', {'kind': 'undo', 'lv': 3}, t + 1),
                                    ('jr_tile_end', {'lv': 3, 'moves': [tm.level(3, 1)['solution'][0], tm.MOVE['undo']] + tm.level(3, 1)['solution']}, t + 100)])
        self.assertTrue(out[-1]['first'])
        self.assertEqual(tile['lv'], 3)
        self.assertNotIn('cur', tile, '2.4.5 pops its attempt')
        # …and this build reads that back and goes on (the 2.4.5 save has no clock: the page's time, once)
        back = json.loads(json.dumps(s))
        back['journey']['tile'] = tile
        validate_state(back)
        self.assertEqual(tm.permille(back), 6)
        self.clock.tick(200)
        back, r = end(back, 4, ms=60_000)
        self.assertTrue(r['first'])

    @with_clock
    def test_old_build_keeps_a_save_past_level_100(self):
        """2.4.43's levels 101–200 on a rollback: the old build takes the player as level 100 and keeps tile_hi as it is."""
        s = cleared(100)
        s['journey']['tile']['cur'] = dict(lv=100, t=int(T0 * 1000), b={}, p={})
        self.clock.tick(tm.need_ms(len(tm.level(101)['solution'])) / 1000)
        s, _ = end(s, 101)
        mine = json.loads(json.dumps(s))
        tile, out = self.old(mine, [('settings', {'sound': False}, self.clock.t),
                                    ('jr_tile_end', {'lv': 100, 'moves': tm.level(100, 1)['solution']}, self.clock.t + 300)])
        self.assertEqual(self.hi, dict(lv=1))
        self.assertTrue(out[-1]['win'] and not out[-1]['first'])
        back = json.loads(json.dumps(s))
        back['journey']['tile'] = tile
        validate_state(back)
        self.assertEqual(tm.cleared(back), 101)

    @with_clock
    def test_an_attempt_a_245_page_left_mid_level_counts_here(self):
        s = cleared(5)
        t = self.clock.t
        tile, _ = self.old(json.loads(json.dumps(s)), [('jr_tile_start', {'lv': 6}, t), ('jr_tile_boost', {'kind': 'undo', 'lv': 6}, t + 1)])
        self.assertEqual(tile['cur']['b'], {'undo': 1})
        s['journey']['tile'] = tile
        validate_state(s)
        self.clock.tick(60)
        sol = tm.level(6, 1)['solution']   # the old page played 2.4.5's table
        s, r = act(s, 'jr_tile_end', lv=6, moves=[sol[0], tm.MOVE['undo']] + sol)   # the old page's end, this build
        self.assertTrue(r['first'])
        self.assertEqual(r['cost'], 0)
        self.assertEqual(s['journey']['tile']['u'], {'undo': 1}, 'the free use is counted once')


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


class PageSync(unittest.TestCase):
    """The page's queue (public/js/v4/tile-match.js): a won level is kept until the server confirms it, through a 409,
    a lost connection, "too early" and a reload, and it is never sent twice once counted."""
    def test_queue_survives_conflicts_errors_and_a_reload(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        script = ROOT / 'public' / 'js' / 'v4' / 'tile-match.js'
        sol = tm.level(1)['solution']
        code = f'''
const store=new Map();globalThis.localStorage={{getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}};
const realTimeout=globalThis.setTimeout;globalThis.setTimeout=(fn,ms)=>realTimeout(fn,0);
const {{_tileTest:X,Game,resumeTileSync}}=await import({json.dumps(script.as_uri())});
const level={json.dumps(tm.public_level(1))},sol={json.dumps(sol)};
const tile={{lv:0,n:0,cap:15,day:'2026-10-14',free:{{undo:3,shuffle:1,push:1,slot:1}},price:{{undo:40}},pct:'0'}};
const calls=[];let plan=[];
const api={{state:{{journey:{{tile,wallet:100}}}},account:{{uid:877}},clockOffset:0,command:async(a,p)=>{{
  calls.push([a,p.n,p.moves.length]);const step=plan.shift()||'ok';
  if(step!=='ok'){{const e=new Error(step);e.status=step==='net'?0:409;e.data={{code:step}};if(step==='tile_fast')e.status=400;throw e;}}
  tile.lv=Math.max(tile.lv,p.n);tile.n++;tile.at=Date.now();return {{win:true,first:true,tile}};}}}};
X.T.env={{api,toast:()=>{{}}}};
// a win: the card at once, the level queued (a copy of its moves), then confirmed after a 409, a lost connection and "too early"
X.T.lv=1;X.T.level=level;X.T.g=new Game(level);X.T.g.useFree={{}};X.T.g.usePaid={{}};X.T.g.useCost={{}};X.T.t0=Date.now()-30000;
X.T.moves=[];for(const m of sol){{X.T.g.move(m);X.T.moves.push(m);}}
plan=['revision_conflict','net','tile_fast'];
X.win(X.T.g);
const first={{view:X.T.view,sync:X.T.result.sync,stored:JSON.parse(store.get(X.SYNC_KEY)).length,local:X.localLv()}};
X.T.moves.length=0;   // a new attempt reuses nothing of the queued level
for(let i=0;i<50&&X.queue().length;i++)await new Promise(r=>realTimeout(r,5));
const after={{sync:X.T.result.sync,left:X.queue().length,stored:store.has(X.SYNC_KEY),calls:calls.map(c=>c.slice())}};
// a reload with a level already counted (its answer was lost) and one not yet: only the second is sent
store.set(X.SYNC_KEY,JSON.stringify([{{id:1,who:'877',n:1,moves:sol,t0:Date.now()-60000,taps:sol.length,first:true}},{{id:2,who:'877',n:2,moves:[1,2],t0:Date.now()-60000,taps:2,first:true}},{{id:3,who:'other',n:5,moves:[],first:true}}]));
tile.at=Date.now()-60000;X.T.q=null;calls.length=0;plan=['tile_invalid'];resumeTileSync(X.T.env);
for(let i=0;i<50&&X.queue().length;i++)await new Promise(r=>realTimeout(r,5));
console.log(JSON.stringify({{first,after,reload:{{calls,left:X.queue().length,others:JSON.parse(store.get(X.SYNC_KEY)||'[]').map(x=>x.who)}}}}));
'''
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'sync.mjs'
            f.write_text(code, encoding='utf-8')
            r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got['first'], dict(view='done', sync='wait', stored=1, local=1))
        self.assertEqual(got['after']['sync'], 'ok')
        self.assertEqual(got['after']['left'], 0)
        self.assertFalse(got['after']['stored'])
        self.assertEqual(got['after']['calls'], [['jr_tile_end', 1, len(sol)]] * 4, 'one level, sent until confirmed, its own moves')
        self.assertEqual(got['reload']['calls'], [['jr_tile_end', 2, 2]], 'the counted level is not sent again')
        self.assertEqual(got['reload']['left'], 0, 'an invalid level is dropped with its reason')
        self.assertEqual(got['reload']['others'], ['other'], "another player's queue is left alone")


class PageBoards(unittest.TestCase):
    """Owner, 14/10: "3 cái cuối không match với nhau" from level 8 (the first stack). The page never builds a level: it
    draws what /api/tile/level sends (public_level, the server's own build), so the board is the server's by
    construction. The page drew a stack tile by its place in the stack, though, so the tiles under a taken top stayed
    blank backs. For all 200 levels, at three phone stages: the page's Game clears the server's intended solution,
    every kind comes in threes, every tile the solution takes next is drawn face up and open, nothing face down is
    open, every stack shows all its tiles in turn, and every board tile sits inside the stage. 2.4.10: the tile the
    solution takes next is also the one painted on top at its centre (2.4.7–2.4.9 painted a stack's first back over
    its face-up top, so a tap there hit the back: the stack could never be taken)."""
    def test_page_draws_every_level_face_up_in_turn_and_inside_the_stage(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        src = (ROOT / 'public' / 'js' / 'v4' / 'tile-match.js').read_text(encoding='utf-8')
        self.assertIn('/api/tile/level?lv=', src)
        self.assertNotIn('function build', src, 'the page draws the server\'s level, it never builds one')
        levels = [dict(tm.public_level(lv), solution=tm.level(lv)['solution']) for lv in range(1, tm.LEVEL_MAX + 1)]
        script = ROOT / 'public' / 'js' / 'v4' / 'tile-match.js'
        code = f'''
const {{Game,geometry,place,above}}=await import({json.dumps(script.as_uri())});
let data='';process.stdin.on('data',d=>data+=d);process.stdin.on('end',()=>{{
  const out=[];
  for(const lv of JSON.parse(data)){{
    const bad=[];const cnt={{}};for(const t of lv.tiles)if(t[3]>=0)cnt[t[3]]=(cnt[t[3]]||0)+1;   // -1: a 🌈 (201–300)
    if(Object.values(cnt).some(c=>c%3))bad.push('kinds not in threes');
    for(const [W,H] of [[390,680],[360,600],[820,300]]){{
      const g=new Game(lv),geo=geometry(W,H,lv,g.cap);
      for(let t=0;t<g.n;t++){{const a=place(geo,lv,g,t);if(a.px<-0.5||a.py<-0.5||a.px+a.size>W+0.5||a.py+a.size>H+0.5){{bad.push(`tile ${{t}} outside ${{W}}x${{H}}`);break;}}}}
      for(const m of lv.solution){{
        for(let t=0;t<g.n;t++){{if(g.where[t]!=='b')continue;const a=place(geo,lv,g,t);
          if(a.back&&g.open(t)){{bad.push(`open tile ${{t}} face down`);break;}}}}
        if(!g.open(m)){{bad.push(`solution tile ${{m}} not open`);break;}}
        const a=place(geo,lv,g,m);if(a&&a.back){{bad.push(`solution tile ${{m}} face down`);break;}}
        // the tap lands on it: at its centre, the tile painted last (highest zi, then the later element) is m itself
        const cx=a.px+a.size/2,cy=a.py+a.size/2;let top=-1,tz=-1;
        for(let t=0;t<g.n;t++){{const b=place(geo,lv,g,t);if(!b||cx<b.px+1||cx>b.px+b.size-1||cy<b.py+1||cy>b.py+b.size-1)continue;
          if(b.zi>=tz){{tz=b.zi;top=t;}}}}
        if(top!==m){{bad.push(`solution tile ${{m}} painted under tile ${{top}}`);break;}}
        g.move(m);
      }}
      if(!g.won)bad.push(`not won at ${{W}}x${{H}}`);
      if(bad.length)break;
    }}
    out.push(bad.slice(0,3));
  }}
  console.log(JSON.stringify(out));}});
'''
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'boards.mjs'
            f.write_text(code, encoding='utf-8')
            r = subprocess.run([node, str(f)], input=json.dumps(levels), capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({lv: b for lv, b in enumerate(got, 1) if b}, {})
        self.assertTrue(any(l['stacks'] for l in levels))

    def test_stack_tiles_turn_face_up_one_by_one(self):
        """The 2.4.5 rule (a tile's place in its stack) against the fixed one, on level 8's first stack in 2.4.5's table."""
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        lv8 = dict(tm.level(8, 1))
        lv8.pop('solution')
        script = ROOT / 'public' / 'js' / 'v4' / 'tile-match.js'
        code = f'''
const {{Game,above}}=await import({json.dumps(script.as_uri())});
const lv={json.dumps(lv8)},g=new Game(lv),ids=lv.stacks[0].ids,out=[];
for(const t of ids){{out.push(ids.map(i=>g.where[i]==='b'?above(g,lv,i):-1));g.where[t]='g';for(const d of g.under[t])g.block[d]--;}}
console.log(JSON.stringify(out));
'''
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'stack.mjs'
            f.write_text(code, encoding='utf-8')
            r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual(json.loads(r.stdout), [[0, 1, 2], [-1, 0, 1], [-1, -1, 0]])


if __name__ == '__main__':
    unittest.main()
