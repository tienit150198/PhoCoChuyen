"""🧩 Ghép ba Phố Mây, levels 201–300 (2.5.7, owner 23/10 "thêm mở tới màn 300 nhé, khó hơn, với có item ẩn … học candy
fruits"): the table (deterministic, every level won by its intended solution and by the independent solver), the four
special tiles' rules (🎁 box, 🌈 joker, ⛓️ chain, 💣 bomb) replayed by the server and bit for bit by the page, the progress
past 200 in journey.tile_hi2 (a rollback to 2.5.6.1 keeps the save valid), +0.1 % a level to +40 % at 300, the 🎁
chests, the ⭐ stars, and booster prices that did not move.

The full solver pass over all 100 new levels is `python scripts/build_tile_levels.py --check`; here every level is built
and won by its intended solution, and a fixed sample (every intro, every tray-of-6 level and every seventh) is solved."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from game import price_index
from game import tile_match as tm
from game.engine import GameError, apply_action, validate_state
from game.tile_match_levels import LEVELS, SCORES
from tests.test_bank import story
from tests.test_tile_match import T0, act, with_clock

ROOT = Path(__file__).resolve().parents[1]
NEW = range(201, 301)


def cleared(lv, wallet=5000, clock=True):
    s = story(wallet)
    s['journey']['tile'] = dict(lv=min(lv, tm.BASE_MAX), d=tm.today(), n=0, u={})
    if lv > tm.BASE_MAX:
        s['journey']['tile_hi'] = dict(lv=min(lv, tm.HI_MAX) - tm.BASE_MAX)
    if lv > tm.HI_MAX:
        s['journey']['tile_hi2'] = dict(lv=lv - tm.HI_MAX)
    if clock:
        s['journey']['tile']['cur'] = dict(lv=min(lv + 1, tm.BASE_MAX), t=int(T0 * 1000), b={}, p={})
    validate_state(s)
    return s


def end(s, n, moves=None, **extra):
    return act(s, 'jr_tile_end', n=n, moves=tm.level(n)['solution'] if moves is None else moves, **extra)


def count(level, flag):
    return sum(1 for t in level['tiles'] if t[4] & flag)


def mini(tiles, b=None, chain=(), fuse=(), cap=7, seed=5):
    """A hand-made level: tiles [x, y, z, kind, flags] (no stacks)."""
    n = len(tiles)
    out = dict(lv=999, v=3, seed=seed, shape='o3', cap=cap, w=14, h=16, icons=['🍜', '🐶', '☕', '👗', '💐'],
               tiles=[list(t) for t in tiles], b=b or [[] for _ in range(n)], stacks=[], board=n)
    if chain:
        out['chain'] = [list(c) for c in chain]
        for t, _ in chain:
            out['tiles'][t][4] |= tm.CHAIN
    if fuse:
        out['fuse'] = [list(f) for f in fuse]
    return out


# ---------------------------------------------------------------- the table
class Table(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = {lv: tm.build(lv) for lv in NEW}

    def test_rows(self):
        self.assertEqual((tm.LEVEL_MAX, len(LEVELS), len(SCORES)), (300, 300, 300))
        for lv, row in enumerate(LEVELS, 1):
            self.assertEqual(len(row), 16 if lv > 200 else 11, lv)
            self.assertTrue(all(isinstance(x, (int, str, tuple)) for x in row), row)

    def test_every_new_level_is_won_by_its_intended_solution(self):
        for lv, level in self.built.items():
            items = [t for t in level['tiles'] if not t[4] & tm.JOKER]
            for k in set(t[3] for t in items):
                self.assertEqual(sum(1 for t in items if t[3] == k) % 3, 0, (lv, k))
            self.assertTrue(all(t[3] == -1 for t in level['tiles'] if t[4] & tm.JOKER), lv)
            self.assertTrue(tm.replay(level, level['solution']).won, lv)

    def test_a_sample_is_solved_by_the_independent_solver(self):
        sample = sorted({201, 211, 221, 231, 225, 250, 275, 300} | set(range(203, 301, 7)))
        for lv in sample:
            level = self.built[lv]
            path = tm.solve(level)
            self.assertIsNotNone(path, f'level {lv}: the solver finds no way')
            self.assertTrue(tm.replay(level, path).won, lv)

    def test_deterministic_and_no_solution_for_the_page(self):
        for lv in (201, 233, 300):
            self.assertEqual(json.dumps(tm.build(lv)), json.dumps(tm.build(lv)))
            pub = tm.public_level(lv)
            self.assertNotIn('solution', pub)
            self.assertNotIn('peak', pub)
            self.assertEqual(pub['tiles'], tm.level(lv)['tiles'])
            self.assertEqual(pub.get('fuse'), tm.level(lv).get('fuse'))
            self.assertEqual(pub.get('chain'), tm.level(lv).get('chain'))

    def test_specials_come_in_one_by_one_with_their_intro_levels(self):
        first = {}
        for f in (tm.BOX, tm.JOKER, tm.CHAIN, tm.BOMB):
            first[f] = min(lv for lv, b in self.built.items() if count(b, f))
        self.assertEqual(first, {tm.BOX: 201, tm.JOKER: 211, tm.CHAIN: 221, tm.BOMB: 231})
        for lv, b in self.built.items():
            row = tm._row(LEVELS[lv - 1])
            self.assertEqual([count(b, f) for f in (tm.BOX, tm.JOKER, tm.CHAIN, tm.BOMB)], list(row[11:15]), lv)
            self.assertEqual(b['cap'], 6 if lv % 25 == 0 else 7, lv)
        late = [self.built[lv] for lv in range(291, 301)]
        self.assertTrue(all(count(b, tm.BOMB) == 3 and count(b, tm.JOKER) == 2 and count(b, tm.CHAIN) >= 7 for b in late))
        for b in self.built.values():   # a special tile is never also a 🔒, 🔑 or 🧊 and never in a stack
            for t, x in enumerate(b['tiles']):
                if x[4] & (tm.BOX | tm.JOKER | tm.CHAIN | tm.BOMB):
                    self.assertEqual(bin(x[4]).count('1'), 1, (b['lv'], t, x))
                    self.assertLess(t, b['board'])
            self.assertTrue(all(1 <= c <= tm.CHAIN_MAX for _, c in b.get('chain', ())))
            self.assertTrue(all(f >= 5 for _, f in b.get('fuse', ())))

    def test_harder_than_191_to_200(self):
        old = [tm.build(lv) for lv in range(191, 201)]
        new = list(self.built.values())
        kinds = [len(b['icons']) for b in new]
        self.assertGreaterEqual(min(kinds[1:10]), max(len(b['icons']) for b in old))
        self.assertEqual(kinds[-1], 48, 'every icon at 300')
        no_intro = [k for lv, k in zip(NEW, kinds) if lv not in (201, 211, 221, 231)]
        self.assertEqual(no_intro, sorted(no_intro), 'icons never go down but on an intro level')
        self.assertTrue(all(len(set(b['icons'])) == len(b['icons']) for b in new))
        locks = [count(b, tm.LOCK) for b in new]
        ice = [count(b, tm.ICE) for b in new]
        self.assertGreaterEqual(min(locks), 12)
        self.assertGreaterEqual(min(ice), 30)
        self.assertEqual(locks, sorted(locks))
        self.assertEqual(ice, sorted(ice))
        self.assertGreaterEqual(sum(SCORES[200:]) / 100, sum(SCORES[190:200]) / 10 - 1, 'no easier than 191–200')
        for lv in (201, 250, 300):
            self.assertAlmostEqual(tm.difficulty(self.built[lv]), SCORES[lv - 1], places=2)
        self.assertEqual(tm.public_level(201)['icons'], tm.level(201)['icons'])
        for icon in tm.ICONS:   # the oldest phone's emoji (see test_tile_match)
            self.assertTrue(icon == '🧋' or all(ord(c) < 0x1FA70 for c in icon), icon)

    def test_levels_1_to_200_did_not_move(self):
        """Saves, replays and pages of 2.5.6.1 play the same levels 1–200 (the old table rows are kept as they were)."""
        self.assertTrue(all(len(r) == 11 for r in LEVELS[:200]))
        for lv in (1, 57, 100, 101, 160, 200):
            level = tm.build(lv)
            self.assertNotIn('chain', level)
            self.assertNotIn('fuse', level)
            self.assertEqual(level['cap'], 7)
            self.assertFalse(any(t[4] & ~7 for t in level['tiles']))


# ---------------------------------------------------------------- the rules
def joker_level(cap=7):
    """🌈: A A A A A A (kind 0, tiles 0–5), B B B (6–8), 🌈 (9). Tiles 2 and 5 lie lowest (z 0)."""
    z = [1, 2, 0, 3, 1, 0, 1, 1, 1, 1]
    tiles = [[2 * i, 0, z[i], 0, 0] for i in range(6)] + [[2 * i, 4, 1, 1, 0] for i in range(3)] + [[0, 8, 1, -1, tm.JOKER]]
    return mini(tiles, cap=cap)


def bomb_level(fuse=3, ice=False):
    """💣 tile 0 (item 0) with its mates 1 and 2; items 1 (3–5) and 2 (6–8)."""
    tiles = [[0, 0, 0, 0, tm.BOMB], [2, 0, 0, 0, 0], [4, 0, 0, 0, 0]] + [[2 * i, 4, 0, 1 + (i - 3) // 3, 0] for i in range(3, 9)]
    if ice:
        tiles[3][4] = tm.ICE
    return mini(tiles, fuse=[[0, fuse]])


class Joker(unittest.TestCase):
    def level(self, cap=7):
        return joker_level(cap)

    def test_a_joker_finishes_a_pair_and_pulls_the_third_off_the_board(self):
        g = tm.Game(self.level())
        g.tap(1)
        g.tap(3)
        out = g.tap(9)
        self.assertEqual(out, [1, 3, 9, 2], 'the pair, the 🌈, then the lowest A on the board (z 0, then the lowest number)')
        self.assertEqual((g.tray, g.where[2], g.done, g.gone, g.clears), ([], 'g', 3, 4, 1))
        for t in (0, 4, 5):
            g.tap(t)
        for t in (6, 7, 8):
            g.tap(t)
        self.assertTrue(g.won)

    def test_a_joker_waits_in_the_tray_for_the_next_pair(self):
        g = tm.Game(self.level())
        self.assertEqual(g.tap(9), 'tray')
        g.tap(6)
        self.assertEqual(g.tray, [6, 9], 'a new item sits before the waiting 🌈')
        out = g.tap(7)
        self.assertEqual(out, [6, 7, 9, 8])
        self.assertEqual(g.tray, [])

    def test_the_leftmost_pair_and_never_a_lost_level(self):
        g = tm.Game(self.level())
        for t in (6, 7, 0, 1):
            g.tap(t)
        self.assertEqual(g.tray, [6, 7, 0, 1])
        out = g.tap(9)
        self.assertEqual(out, [6, 7, 9, 8], 'B is the leftmost pair')
        self.assertEqual(g.tray, [0, 1])
        for t in (2, 3, 4, 5):
            g.tap(t)
        self.assertTrue(g.won)

    def test_a_leftover_joker_vanishes_with_the_win_and_shuffle_never_moves_it(self):
        g = tm.Game(self.level())
        for t in range(9):
            g.tap(t)
        self.assertTrue(g.won, 'every item gone: won with the 🌈 still on the board')
        self.assertEqual(g.where[9], 'b')
        g = tm.Game(self.level())
        for _ in range(5):
            g.shuffle()
            self.assertEqual(g.kind[9], -1)
        self.assertEqual(sorted(g.kind), sorted(tm.Game(self.level()).kind))

    def test_undo_stops_at_a_joker_clear_and_the_joker_takes_a_slot(self):
        g = tm.Game(self.level())
        g.tap(1)
        g.tap(3)
        g.tap(9)
        with self.assertRaises(tm.Bad):
            g.undo()
        g = tm.Game(self.level(cap=3))
        g.tap(9)
        g.tap(6)
        g.tap(0)
        self.assertTrue(g.lost, 'a waiting 🌈 fills the tray like a tile')

    def test_a_pulled_tile_comes_from_the_holding_row_too(self):
        g = tm.Game(self.level())
        g.tap(0)
        g.push()
        self.assertEqual(g.hold, [0])
        g.tap(1)
        g.tap(3)
        self.assertEqual(g.tap(9), [1, 3, 9, 2], 'the lowest layer first: tile 2 (z 0) on the board, not tile 0 (z 1) held')
        self.assertEqual(g.hold, [0])
        g2 = tm.Game(self.level())
        for t in (2, 5):
            g2.tap(t)
        g2.push()
        g2.tap(1)
        g2.tap(3)
        self.assertEqual(g2.tray, [1, 3])
        out = g2.tap(9)
        self.assertEqual(out, [1, 3, 9, 2], 'tile 2 (z 0) from the holding row')
        self.assertEqual(g2.hold, [5])


class Chain(unittest.TestCase):
    def test_a_chained_tile_opens_after_its_triples(self):
        tiles = [[2 * i, 0, 0, i // 3, 0] for i in range(9)]
        level = mini(tiles, chain=[[6, 2]])
        g = tm.Game(level)
        self.assertFalse(g.open(6))
        with self.assertRaises(tm.Bad):
            g.tap(6)
        for t in (0, 1, 2):
            g.tap(t)
        self.assertEqual(g.clears, 1)
        self.assertFalse(g.open(6))
        for t in (3, 4, 5):
            g.tap(t)
        self.assertTrue(g.open(6))
        for t in (6, 7, 8):
            g.tap(t)
        self.assertTrue(g.won)
        self.assertTrue(tm.replay(level, tm.solve(level)).won)

    def test_the_solver_honours_chains(self):
        tiles = [[2 * i, 0, 0, i // 3, 0] for i in range(9)]
        level = mini(tiles, chain=[[0, 2], [1, 2], [2, 2]])
        path = tm.solve(level)
        self.assertIsNotNone(path)
        self.assertEqual(set(path[-3:]), {0, 1, 2})
        self.assertTrue(tm.replay(level, path).won)


class Bomb(unittest.TestCase):
    def level(self, fuse=3, ice=False):
        return bomb_level(fuse, ice)

    def test_lit_when_open_ticks_on_every_tap_and_goes_off_at_zero(self):
        g = tm.Game(self.level())
        self.assertEqual(g.lit, {0: 3}, 'open at the start: lit')
        g.tap(3)
        g.tap(4)
        self.assertEqual(g.lit[0], 1)
        g.tap(6)
        self.assertTrue(g.lost)
        self.assertEqual(g.boom, 0)

    def test_matched_in_time_it_is_defused_and_boosters_never_tick(self):
        g = tm.Game(self.level())
        g.tap(1)
        g.undo()
        g.slot()
        g.shuffle()
        self.assertEqual(g.lit[0], 2, 'one tap so far; ↩ ➕ 🔀 never tick, ↩ never gives a tap back')
        g = tm.Game(self.level())
        g.tap(0)
        g.tap(1)
        g.tap(2)
        self.assertEqual(g.where[0], 'g')
        for t in range(3, 9):
            g.tap(t)
        self.assertTrue(g.won and not g.lost)

    def test_an_ice_crack_is_a_tap(self):
        g = tm.Game(self.level(ice=True))
        self.assertEqual(g.tap(3), 'ice')
        self.assertEqual(g.lit[0], 2)

    def test_lit_only_once_open(self):
        level = self.level()
        level['tiles'].append([0, 1, 1, 4, 0])   # covers the bomb
        level['tiles'] += [[8, 8, 0, 4, 0], [10, 8, 0, 4, 0]]
        level['b'] = [[9]] + [[] for _ in range(11)]
        level['board'] = 12
        g = tm.Game(level)
        self.assertEqual(g.lit, {})
        g.tap(3)
        self.assertEqual(g.lit, {})
        g.tap(9)
        self.assertEqual(g.lit, {0: 3}, 'uncovered: lit, the count starts with the next tap')
        self.assertIsNotNone(tm.solve(level))

    def test_the_solver_never_lets_a_bomb_go_off(self):
        level = self.level(fuse=3)
        path = tm.solve(level)
        self.assertIsNotNone(path)
        self.assertTrue(tm.replay(level, path).won)
        self.assertEqual(set(path[:3]), {0, 1, 2}, 'the bomb and its mates first')


class Box(unittest.TestCase):
    def test_a_box_changes_no_rule(self):
        """🎁 only hides the item on the page while the tile is covered: the same moves give the same game."""
        level = tm.level(201)
        self.assertGreater(count(level, tm.BOX), 0)
        plain = json.loads(json.dumps(level))
        for t in plain['tiles']:
            t[4] &= ~tm.BOX
        a, b = tm.replay(level, level['solution']), tm.replay(plain, level['solution'])
        self.assertEqual((a.where, a.taps, a.won), (b.where, b.taps, b.won))
        self.assertTrue(all(level['b'][t] for t, x in enumerate(level['tiles']) if x[4] & tm.BOX), 'covered at the start')


# ---------------------------------------------------------------- the server: progress, reward, chests, stars
class Progress(unittest.TestCase):
    @with_clock
    def test_past_200_in_its_own_key_and_the_reward(self):
        s = cleared(200)
        with self.assertRaises(GameError) as e:
            end(s, 202)
        self.assertEqual(e.exception.code, 'tile_locked')
        self.assertEqual(tm.public(s)['max'], 200, 'pages of 2.4.43–2.5.6.1 stop at 200')
        self.assertEqual(tm.public(s)['last'], 300)
        self.clock.tick(tm.need_ms(len(tm.level(201)['solution'])) / 1000)
        s, r = end(s, 201)
        self.assertTrue(r['win'] and r['first'])
        j = s['journey']
        self.assertEqual((j['tile']['lv'], j['tile']['cur']['lv'], j['tile_hi'], j['tile_hi2']), (100, 100, dict(lv=100), dict(lv=1)))
        self.assertEqual((tm.cleared(s), tm.permille(s), r['tile']['pct'], r['tile']['lv']), (201, 301, '30,1', 201))
        self.assertIn('+30,1%', r['message'])
        validate_state(s)
        s2, r = end(s, 201)
        self.assertFalse(r['first'])
        for lv, pm, pct in ((201, 301, '30,1'), (250, 350, '35'), (300, 400, '40')):
            self.assertEqual((tm.permille(cleared(lv)), tm.pct_text(tm.permille(cleared(lv)))), (pm, pct))
        self.assertEqual(tm.extra(cleared(300), 1000, 'k'), 400)
        self.assertEqual(tm.extra(cleared(250), 1000, 'k'), 350)

    @with_clock
    def test_the_last_level_and_bounds(self):
        s = cleared(299)
        self.clock.tick(tm.need_ms(len(tm.level(300)['solution'])) / 1000)
        s, r = end(s, 300)
        self.assertTrue(r['first'])
        self.assertEqual((tm.cleared(s), r['tile']['pct'], s['journey']['tile_hi2']['lv']), (300, '40', 100))
        with self.assertRaises(GameError) as e:
            end(s, 301, moves=[])
        self.assertEqual(e.exception.code, 'tile_level')
        for v in (1, 2):   # the older tables stop at 100 and 200
            with self.assertRaises(GameError) as e:
                end(s, 250, v=v)
            self.assertEqual(e.exception.code, 'tile_level')
        with self.assertRaises(GameError) as e:   # an older page's start stops at 100
            act(s, 'jr_tile_start', lv=201)
        self.assertEqual(e.exception.code, 'tile_level')
        validate_state(s)

    @with_clock
    def test_a_lost_or_fake_game_never_counts(self):
        s = cleared(230)
        self.clock.tick(3600)
        level = tm.level(231)
        bomb = level['fuse'][0][0]
        g = tm.Game(level)
        moves = []
        while not g.over:   # tap anything but the bomb's item until it goes off (or the tray fills)
            t = next((t for t in range(g.n) if g.open(t) and g.kind[t] != g.kind[bomb] and not g.joker[t]), None)
            if t is None:
                break
            g.tap(t)
            moves.append(t)
        self.assertTrue(g.lost)
        s2, r = end(s, 231, moves=moves)
        self.assertFalse(r['win'])
        self.assertEqual(tm.cleared(s2), 230)
        with self.assertRaises(GameError) as e:   # a tap the rules refuse (a chained tile at the start)
            ch = tm.level(221)['chain'][0][0]
            end(cleared(220), 221, moves=[ch])
        self.assertEqual(e.exception.code, 'tile_invalid')

    def test_validation(self):
        validate_state(cleared(300))
        good = cleared(250)
        good['journey']['tile_hi2']['b'] = {'undo': 2}
        good['journey']['tile_st'] = '3' * 250
        validate_state(good)
        for hi2, hi in ((dict(lv=101), 100), (dict(lv=1), 99), (dict(lv=1, x=1), 100), (dict(lv='1'), 100), ('x', 100),
                        (dict(lv=1, b={}), 100), (dict(lv=1, b={'undo': 0}), 100), (dict(lv=1, b={'x': 1}), 100),
                        (dict(lv=1, b={'undo': 100}), 100), (dict(b={'undo': 1}), 100)):
            s = cleared(200)
            s['journey']['tile_hi'] = dict(lv=hi)
            s['journey']['tile_hi2'] = hi2
            with self.assertRaises(GameError, msg=(hi2, hi)):
                validate_state(s)
        for st in ('', '4', 'x', '3' * 301, 3):
            s = cleared(10)
            s['journey']['tile_st'] = st
            with self.assertRaises(GameError, msg=st):
                validate_state(s)

    @with_clock
    def test_reset_all_keeps_levels_past_200_chests_and_stars(self):
        s = cleared(230)
        s['journey']['tile_hi2']['b'] = {'shuffle': 1}
        s['journey']['tile_st'] = '321'
        s, _ = apply_action(s, None, 'reset_all', {'confirm': 'BAT DAU LAI'})
        self.assertEqual((tm.cleared(s), s['journey']['tile_hi2'], s['journey']['tile_st']), (230, dict(lv=30, b={'shuffle': 1}), '321'))


class Chests(unittest.TestCase):
    @with_clock
    def test_a_chest_every_ten_levels_used_after_the_days_own(self):
        self.assertEqual([lv for lv in range(1, 301) if tm.chest(lv)], list(range(210, 301, 10)))
        self.assertEqual(tm.chest(250), {k: 2 * v for k, v in tm.CHEST.items()})
        s = cleared(209, wallet=10_000)
        self.clock.tick(3600)
        s, r = end(s, 210)
        self.assertEqual(r['chest'], tm.CHEST)
        self.assertEqual(s['journey']['tile_hi2'], dict(lv=10, b=tm.CHEST))
        pub = tm.public(s)
        self.assertEqual(pub['chest'], tm.CHEST)
        self.assertEqual(pub['free']['undo'], tm.FREE['undo'] + tm.CHEST['undo'])
        s, r = end(s, 210)   # a replay: no second chest
        self.assertNotIn('chest', r)
        self.assertEqual(s['journey']['tile_hi2']['b'], tm.CHEST)
        # level 211 with 5 undos: today's 3, then the chest's 2, nothing to pay; the chest's undo is gone
        sol = tm.level(211)['solution']
        U = tm.MOVE['undo']
        self.clock.tick(3600)
        w = s['journey']['wallet']
        s, r = end(s, 211, moves=[sol[0], U] * 5 + sol)
        self.assertEqual((r['cost'], s['journey']['wallet'], s['journey']['tile']['u']), (0, w, {'undo': 3}))
        self.assertEqual(s['journey']['tile_hi2']['b'], {k: v for k, v in tm.CHEST.items() if k != 'undo'})
        validate_state(s)
        # one more undo is paid at the base price (unchanged)
        s, r = end(s, 205, moves=[tm.level(205)['solution'][0], U] + tm.level(205)['solution'])
        self.assertEqual(r['cost'], tm.PRICE['undo'])

    def test_booster_prices_did_not_move(self):
        self.assertEqual(tm.PRICE, {k: price_index.price(v) for k, v in {'undo': 40, 'shuffle': 80, 'push': 100, 'slot': 150}.items()})
        self.assertEqual(tm.FREE, {'undo': 3, 'shuffle': 1, 'push': 1, 'slot': 1})
        self.assertEqual([tm.price('undo', n) for n in range(3)], [tm.PRICE['undo'] * m for m in (1, 2, 4)])


class Stars(unittest.TestCase):
    @with_clock
    def test_the_best_stars_are_kept(self):
        self.assertEqual([tm.stars(n) for n in (0, 1, 2, 3, 9)], [3, 2, 2, 1, 1])
        s = cleared(4)
        self.clock.tick(3600)
        U = tm.MOVE['undo']
        sol = tm.level(5)['solution']
        s, r = end(s, 5, moves=[sol[0], U, sol[0], U, sol[0], U] + sol)
        self.assertEqual((r['stars'], r['best'], s['journey']['tile_st']), (1, True, '00001'))
        s, r = end(s, 5, moves=[sol[0], U] + sol)
        self.assertEqual((r['stars'], r['best'], s['journey']['tile_st']), (2, True, '00002'))
        s, r = end(s, 5, moves=[sol[0], U, sol[0], U, sol[0], U] + sol)
        self.assertEqual((r['best'], s['journey']['tile_st']), (False, '00002'))
        s, r = end(s, 2)
        self.assertEqual((r['stars'], s['journey']['tile_st'], tm.public(s)['st']), (3, '03002', '03002'))
        validate_state(s)


# ---------------------------------------------------------------- a rollback to 2.5.6.1
class Rollback(unittest.TestCase):
    """2.5.6.1 (origin/main 40d43f6d, TILE_OLD_REF2 picks another) reads a save of this build past 200: it validates it,
    keeps tile_hi2 and tile_st as they are, takes the player as level 200 (its own last) and plays on; this build reads
    the result back."""
    @classmethod
    def setUpClass(cls):
        if not shutil.which('git'):
            raise unittest.SkipTest('no git')
        ref = os.environ.get('TILE_OLD_REF2', '40d43f6d')
        cls.tmp = tempfile.mkdtemp(prefix='tile-2561-')
        # only the game package, its data (reference/) and the top-level modules it imports: the whole tree takes minutes
        arch = subprocess.run(['git', 'archive', ref, 'game', 'reference', 'market_data.py', 'business_view.py', 'command_metrics.py'],
                              cwd=ROOT, capture_output=True)
        if arch.returncode:
            raise unittest.SkipTest(f'git archive {ref}: {arch.stderr.decode()[:200]}')
        subprocess.run(['tar', '-x', '-C', cls.tmp], input=arch.stdout, check=True)
        old = (Path(cls.tmp) / 'game' / 'tile_match.py').read_text(encoding='utf-8')
        if 'LEVEL_MAX = 200' not in old or 'KEY_HI2' in old:
            raise unittest.SkipTest(f'{ref} is not a 2.4.44–2.5.6.1 build')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'tmp', ''), ignore_errors=True)

    def old(self, state, steps=()):
        code = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state\nfrom game import tile_match as tm\n'
                'd=json.load(sys.stdin)\ns=d["s"]\nvalidate_state(s)\nout=[]\n'
                'for a,p,t in d["steps"]:\n'
                '    tm._now=(lambda t=t:t)\n'
                '    s,r=apply_action(s,None,a,p)\n'
                '    out.append({k:r.get(k) for k in ("win","first","cost")})\n'
                'validate_state(s)\npub=tm.public(s)\n'
                'print(json.dumps([s["journey"],out,{k:pub[k] for k in ("lv","max","pct")}]))')
        r = subprocess.run([sys.executable, '-I', '-c', f'import sys;sys.path.insert(0,{self.tmp!r});' + code],
                           input=json.dumps(dict(s=state, steps=list(steps))), capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    @with_clock
    def test_the_old_build_keeps_and_plays_on_a_save_past_200(self):
        s = cleared(249, wallet=10_000)
        self.clock.tick(3600)
        s, r = end(s, 250)
        self.assertTrue(r['first'])
        self.assertEqual(s['journey']['tile_hi2'], dict(lv=50, b={k: 2 * v for k, v in tm.CHEST.items()}))
        self.assertEqual(s['journey']['tile_st'][249], '3')
        mine = json.loads(json.dumps(s))
        t = self.clock.t + 10
        sol = tm.level(200)['solution']
        journey, out, pub = self.old(mine, [('settings', {'sound': False}, t),
                                            ('jr_tile_end', {'n': 200, 'moves': [sol[0], tm.MOVE['undo']] + sol, 'v': 3}, t + 300)])
        self.assertEqual(pub, dict(lv=200, max=200, pct='30'), 'the old build counts the player at its own last level')
        self.assertTrue(out[-1]['win'] and not out[-1]['first'])
        self.assertEqual(journey['tile_hi2'], s['journey']['tile_hi2'], 'kept as it is')
        self.assertEqual(journey['tile_st'], s['journey']['tile_st'])
        self.assertEqual(journey['tile_hi'], dict(lv=100))
        back = json.loads(json.dumps(s))
        back['journey'] = journey
        validate_state(back)
        self.assertEqual((tm.cleared(back), tm.permille(back)), (250, 350))
        self.clock.tick(3600)
        back, r = end(back, 251)
        self.assertTrue(r['first'])
        validate_state(back)


# ---------------------------------------------------------------- the page
class Page(unittest.TestCase):
    def node(self, code, data=None):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 't.mjs'
            f.write_text(code, encoding='utf-8')
            r = subprocess.run([node, str(f)], input=json.dumps(data) if data is not None else '', capture_output=True,
                               text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_js_game_matches_python_on_the_special_tiles(self):
        script = (ROOT / 'public' / 'js' / 'v4' / 'tile-match.js').as_uri()
        cases = []
        levels = [tm.public_level(lv) for lv in (201, 211, 221, 225, 231, 262, 300)] + [joker_level(), bomb_level(), bomb_level(6, True)]
        for i, level in enumerate(levels):
            for seed in range(4):
                g = tm.Game(level)
                r = tm.Rng(i * 97 + seed)
                moves = []
                for _ in range(500):
                    if g.over:
                        break
                    opts = [t for t in range(g.n) if g.open(t)]
                    if g.undo_stack:
                        opts.append(tm.MOVE['undo'])
                    if not g.hold and g.tray:
                        opts.append(tm.MOVE['push'])
                    if g.slots < tm.SLOT_MAX:
                        opts.append(tm.MOVE['slot'])
                    if seed % 2:
                        opts.append(tm.MOVE['shuffle'])
                    if not opts:
                        break
                    m = r.pick(opts)
                    try:
                        g.move(m)
                    except tm.Bad:
                        continue
                    moves.append(m)
                cases.append(dict(level=level, moves=moves, want=dict(
                    kind=g.kind, where=g.where, tray=g.tray, hold=g.hold, cap=g.cap, gone=g.gone, done=g.done, clears=g.clears,
                    lost=g.lost, won=g.won, taps=g.taps, boom=g.boom, lit=sorted([b, v] for b, v in g.lit.items()))))
            if level['lv'] != 999:
                cases.append(dict(level=level, moves=tm.level(level['lv'])['solution'], want='won'))
        got = self.node(f'''
import {{Game}} from {json.dumps(script)};
let data='';process.stdin.on('data',d=>data+=d);process.stdin.on('end',()=>{{
  const out=[];
  for(const c of JSON.parse(data)){{const g=new Game(c.level);for(const m of c.moves)g.move(m);
    out.push({{kind:g.kind,where:g.where,tray:g.tray,hold:g.hold,cap:g.cap,gone:g.gone,done:g.done,clears:g.clears,lost:g.lost,won:g.won,
      taps:g.taps,boom:g.boom,lit:[...g.lit].sort((a,b)=>a[0]-b[0])}});}}
  console.log(JSON.stringify(out));}});
''', cases)
        self.assertTrue(any(c['want'] != 'won' and c['want']['clears'] for c in cases))
        self.assertTrue(any(c['want'] != 'won' and c['want']['boom'] is not None for c in cases), 'a bomb went off somewhere')
        for c, o in zip(cases, got):
            if c['want'] == 'won':
                self.assertTrue(o['won'], c['level']['lv'])
            else:
                self.assertEqual(o, c['want'], c['level']['lv'])

    def test_cards_stars_chests_and_the_map(self):
        script = (ROOT / 'public' / 'js' / 'v4' / 'tile-match.js').as_uri()
        lv = {n: tm.public_level(n) for n in (200, 201, 211, 231)}
        got = self.node(f'''
const store=new Map();globalThis.localStorage={{getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}};
const M=await import({json.dumps(script)});
const lv={json.dumps(lv)};
const X=M._tileTest;X.T.env={{api:{{state:{{journey:{{tile:{{lv:212,max:200,last:300,st:'3'.repeat(200)+'21',free:{{}},price:{{}}}}}}}},account:{{uid:1}}}}}};
const intro=n=>M.introsFor(lv[n],[]).map(x=>x[0]);
const map=X.mapCells(212,300);
console.log(JSON.stringify({{intro:[intro(200),intro(201),intro(211),intro(231)],seen:M.introsFor(lv[231],['bomb','box']).map(x=>x[0]),
  stars:[0,1,2,3,7].map(M.starsOf),chest:[200,205,210,250,300].map(M.chestOf),best:[X.bestStars(201),X.bestStars(202),X.bestStars(203)],
  cells:(map.match(/class="tm-lvbtn/g)||[]).length,locked:(map.match(/tm-locked/g)||[]).length,now:/tm-now[^>]*data-lv="213"/.test(map),boxes:(map.match(/tm-cbox/g)||[]).length}}));
''')
        keys = (('box', tm.BOX), ('joker', tm.JOKER), ('chain', tm.CHAIN), ('bomb', tm.BOMB))
        self.assertEqual(got['intro'], [[k for k, f in keys if count(tm.level(n), f)] for n in (200, 201, 211, 231)])
        self.assertEqual(got['intro'][:3], [[], ['box'], ['box', 'joker']])
        self.assertNotIn('bomb', got['seen'])
        self.assertEqual(got['stars'], [3, 2, 2, 1, 1])
        self.assertEqual(got['chest'], [None, None, tm.CHEST, tm.chest(250), tm.chest(300)])
        self.assertEqual(got['best'], [2, 1, 0])
        self.assertEqual((got['cells'], got['locked'], got['now']), (300, 300 - 213, True))
        self.assertEqual(got['boxes'], 9, 'the chests not reached yet show on the map (220 … 300)')


    def test_a_won_level_shows_its_card(self):
        # the page's "shown" flag must not collide with Game.done (the count of matched tiles)
        script = (ROOT / 'public' / 'js' / 'v4' / 'tile-match.js').as_uri()
        got = self.node(f'''
const store=new Map();globalThis.localStorage={{getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}};
const M=await import({json.dumps(script)});const X=M._tileTest;
X.T.env={{api:{{state:{{journey:{{tile:{{lv:239,max:200,last:300,st:'3'.repeat(239),free:{{}},price:{{}}}}}}}},account:{{uid:1}}}},toast:()=>{{}}}};
const level={json.dumps(tm.public_level(240))};
X.T.lv=240;X.T.level=level;X.T.g=new M.Game(level);X.T.t0=Date.now();X.T.moves=[];
for(const m of {json.dumps(tm.level(240)['solution'])}){{X.T.g.move(m);X.T.moves.push(m);}}
X.win(X.T.g);const r=X.T.result;X.win(X.T.g);
console.log(JSON.stringify({{won:X.T.g.won,view:X.T.view,stars:r.stars,first:r.first,chest:r.chest,queued:X.queue().length}}));process.exit(0);
''')
        self.assertEqual(got, dict(won=True, view='done', stars=3, first=True, chest=tm.CHEST, queued=1))


if __name__ == '__main__':
    unittest.main()
