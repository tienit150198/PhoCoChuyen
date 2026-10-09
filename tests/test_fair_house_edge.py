"""🎪 Owner 08/10: the fair opens again (the edition from 09/10) and the house always wins (game/fair.py BASES, LOC_P,
SIDE_OPEN; game/fair_scratch.py PRIZES; scripts/sim_fair_odds.py; docs/FAIR_HOUSE_EDGE.md).

* Every paid luck stall returns less than it takes, on every round: the exact figures, every other state lower, a
  Monte-Carlo check on the module's own draws (the script runs 10^6 rounds a stall), Lộc trời cho inside the edge.
* The new edition: its dates, the entry ("sắp mở" before, "đã tàn" after), a save from the last edition starting afresh
  (money, days, gift, the police's mark; its loan collected), the last edition's titles settled once even by a server
  that missed its end."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import fair_board as fb
from game import fair_cash as fc
from game import fair_scratch as xs
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_fair import AFTER, OPEN, Dice, FairBase, StoreBase, at, story

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sim_fair_odds as sim   # noqa: E402

PAID = ('bc', 'xd', 'lt', 'xs', 'dg')   # dg: 🐕 đua chó (game/fair_dog.py)
LAST_OPEN = at(2026, 10, 4, 20)       # day 2 of the last edition (03/10 → 07/10)


class HouseEdge(unittest.TestCase):
    def test_every_paid_stall_returns_less_than_it_takes(self):
        ex = sim.exact()
        for g in PAID:
            with self.subTest(game=g):
                self.assertTrue(.89 <= ex[g]['rtp'] < .97, ex[g])          # modest and fair-looking
                self.assertLess(ex[g]['loc'], .98, ex[g])                  # 🍀 with the gate always open, too
        self.assertAlmostEqual(ex['bc']['rtp'], 206 / 216)                 # honest dice, unchanged
        self.assertAlmostEqual(ex['dg']['rtp'], .95)                       # 🐕 the outsider at best
        self.assertTrue(.9 < ex['dg']['low'] <= ex['dg']['fresh'] < ex['dg']['rtp'])
        self.assertTrue(.90 <= ex['lt']['low'] < ex['lt']['rtp'])          # the 2- and 5-xu tờ round down
        # the figures the module's docstring shows
        for g in PAID:
            self.assertIn(f'{ex[g]["rtp"]:.1%}', fh.__doc__, g)
            self.assertIn(f'{ex[g]["loc"]:.1%}', fh.__doc__, g)

    def test_the_fresh_draw_is_the_most_a_round_ever_gets(self):
        for g in ('xd', 'lt', 'xs'):
            base = fh.chance_rate(g, OPEN)
            self.assertEqual([fh.chance_rate(g, OPEN + i * 977, st, net) for i, st, net in ((1, 2, 0), (9, 1000, 10**6))],
                             [base, base])
            self.assertTrue(all(fh.run_rate(g, n) <= base for n in range(1, 300)))
        self.assertLess(fh.chance_rate('xd', 0), .5)                              # even money
        self.assertLess(fh.chance_rate('lt', 0) * max(fh.LOTO_PAY.values()) / 10, 1)
        mean = sum(m * w for m, w in xs.PRIZES) / sum(w for _, w in xs.PRIZES)
        self.assertLess(fh.chance_rate('xs', 0) * mean, 1)
        # whatever came before (streaks, runs, switches, pauses), no round draws above its stall's fresh rate
        rng = __import__('random').Random(5)
        for g in ('xd', 'lt', 'xs'):
            j, t = {}, OPEN
            for _ in range(3000):
                t += rng.choice((1, 3, 30, fh.RUN_GAP + 1))
                game = rng.choice(('bc', 'xd', 'lt', 'xs', 'ring', g, g))
                p = fh.luck_p(j, None, game, t, stake=rng.choice((10, 20, 1000)))
                self.assertLessEqual(p, fh.chance_rate(game, t) + 1e-12)
                with mock.patch.object(fh, '_rng', rng):
                    if game != 'bc':
                        fh._draw_luck(j, game, p)

    def test_monte_carlo_on_the_real_draws(self):
        """A smaller run of scripts/sim_fair_odds.py (which plays 10^6 rounds a stall): below 100% every way."""
        ex = sim.exact()
        for g in PAID:
            for how in ('fresh', 'spam', 'press'):
                with self.subTest(game=g, how=how):
                    back = sim.play(g, how, 40_000, seed=7)
                    self.assertLess(back, 1, back)
                    if how == 'fresh':   # đua chó: a dog picked at random (its `fresh`), a wider spread (payouts to ×19)
                        self.assertAlmostEqual(back, ex[g].get('fresh', ex[g]['rtp']),
                                               delta=.035 if g == 'xs' else .05 if g == 'dg' else .02)
            back = sim.play(g, 'fresh', 40_000, seed=8, loc=True)
            self.assertLess(back, 1, (g, back))

    def test_loto_rounds_go_the_way_drawn(self):
        drawn, ok = sim.loto_rounds(300)
        self.assertEqual(ok, 1.0)
        self.assertAlmostEqual(drawn, fh.chance_rate('lt', 0), delta=.08)

    def test_loc_stays_inside_the_edge(self):
        self.assertEqual((fh.LOC_MULT, fh.LOC_GAP), (10, 3600))   # still ×10, at most once an hour for the server
        self.assertLessEqual(fh.LOC_P, .003)


class Reopen(FairBase):
    def test_the_new_edition(self):
        self.assertEqual((fh.edition(), fh.board()), ('fair20261009', 'fair20261009xu'))
        self.assertEqual(fh.window(), (int(at(2026, 10, 9, 0)), fh.NEVER))   # owner 09/10: no end
        self.assertEqual(fh.past(), [('fair20261003', 'fair20261003xu', int(at(2026, 10, 8, 0)))])
        s = story()
        for t, want in ((at(2026, 10, 6, 23, 58), dict(show=False)),
                        (at(2026, 10, 8, 21), dict(show=True, soon=True, open=False, forever=True)),
                        (at(2026, 10, 9, 0, 1), dict(show=True, soon=False, open=True, over=False, forever=True)),
                        (AFTER + 60, dict(show=True, open=True, over=False)),
                        (at(2027, 6, 1), dict(show=True, open=True, over=False, forever=True))):
            self.clock.t = t - 2
            v = public_state(s)['fair']
            self.assertEqual({k: v[k] for k in want}, want, t)
        self.with_end()                                                  # an edition with an end, as before
        self.assertEqual(fh.window(), (int(at(2026, 10, 9, 0)), int(at(2026, 10, 14, 0))))
        for t, want in ((at(2026, 10, 6, 23, 58), dict(show=False)),          # the last edition's "đã tàn" is over
                        (at(2026, 10, 7, 0, 1), dict(show=True, soon=True, open=False)),   # SHOW_BEFORE: "sắp mở"
                        (at(2026, 10, 8, 21), dict(show=True, soon=True, open=False)),
                        (at(2026, 10, 9, 0, 1), dict(show=True, soon=False, open=True, over=False)),
                        (at(2026, 10, 13, 23, 58), dict(show=True, open=True)),
                        (AFTER + 60, dict(show=True, open=False, over=True)),
                        (at(2026, 10, 16, 23, 58), dict(show=True, over=True)),
                        (at(2026, 10, 17, 0, 1), dict(show=False))):
            self.clock.t = t - 2
            v = public_state(s)['fair']
            self.assertEqual({k: v[k] for k in want}, want, t)
        self.clock.t = at(2026, 10, 8, 21)
        with self.assertRaises(GameError) as e:
            self.act(story(), 'fair_bc', bets={'cua': 1})
        self.assertEqual(e.exception.code, 'fair_closed')

    def last_edition_save(self):
        """A save that played the last edition: won at bầu cua, claimed its gift, a loan still open, a police mark."""
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-10-03'}):
            self.clock.t = LAST_OPEN
            s = story(1000)
            s, _ = self.act(s, 'fair_gift')
            for _ in range(3):
                self.dice(Dice(faces=['cua'] * 3))
                s, _ = self.act(s, 'fair_bc', bets={'cua': 10})
            s, _ = self.act(s, 'fair_borrow', amount=100)
            s['journey'][fh.AUDIT_KEY] = dict(ed='fair20261003', base=60000, at=int(LAST_OPEN))
            self.assertEqual(fh.money_of(s['journey']), (300, 1))   # three bão: +100 each
            validate_state(s)
        return json.loads(json.dumps(s))

    def test_a_save_from_the_last_edition_starts_afresh(self):
        s = self.last_edition_save()
        f0 = json.loads(json.dumps(s['journey']['fair']))
        self.clock.t = OPEN
        self.assertEqual(fh.money_of(s['journey']), (0, 0))          # not on the new Bảng vàng before playing
        self.assertEqual(fh.audit_base(s['journey']), 0)              # the police's mark was the last edition's
        v = public_state(s)['fair']
        self.assertEqual((v['board'], v['money'], v['cash']['gift_ready'], v['cash']['loan']),
                         ('fair20261009xu', dict(total=0, days=0), True, dict(p=100, due=fc.owed(100))))
        w = s['journey']['wallet']
        self.dice(Dice(faces=['ga'] * 3))
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})               # the last edition's loan is collected first
        f = s['journey']['fair']
        self.assertEqual(s['journey']['wallet'], w - fc.owed(100) - 10)
        self.assertIsNone(s['journey']['fair_cash']['loan'])
        self.assertEqual((f['ed'], f['pdays'], f['pts']), ('fair20261009', 1, 0))
        self.assertEqual({k: f['stats'][k] for k in fh.MONEY}, dict(won=0, lost=10, earned=0))
        self.assertEqual(f['stats']['bc'], f0['stats']['bc'] + 1)    # the stalls' lifetime counters go on
        self.assertEqual(fh.money_of(s['journey']), (-10, 1))
        s, r = self.act(s, 'fair_gift')                               # a new fair, a new gift: once
        self.assertEqual(r['fair']['gift'], fc.GIFT)
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_gift')
        self.assertEqual(e.exception.code, 'fair_gift_done')
        validate_state(migrate_state(json.loads(json.dumps(s))))

    def test_a_save_untouched_since_the_last_edition_loads(self):
        s = self.last_edition_save()
        for t in (at(2026, 10, 8, 12), OPEN, at(2026, 10, 20)):
            self.clock.t = t
            validate_state(migrate_state(json.loads(json.dumps(s))))
            public_state(s)


class ReopenBoard(StoreBase):
    def play_last_edition(self):
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-10-03'}):
            self.clock.t = LAST_OPEN
            a, b = self.player('Anh Ba'), self.player('Chị Tư')
            for tok, n in ((a, 4), (b, 2)):
                self.dice(Dice(faces=['cua'] * (3 * n)))
                for _ in range(n):
                    self.cmd(tok, 'fair_bc', {'bets': {'cua': 1}})
        return a, b

    def titles(self):
        with self.store.connect() as db:
            return sorted(r[0] for r in db.execute("SELECT id FROM live_effects WHERE kind='title'").fetchall())

    def test_a_server_that_missed_the_last_end_settles_it_once(self):
        a, b = self.play_last_edition()
        self.clock.t = OPEN
        self.assertIsNone(fb.settle(self.store, at(2026, 10, 8, 0)))   # not yet past its end + GRACE
        self.assertEqual(self.titles(), [])
        self.assertIsNone(fb.settle(self.store, OPEN))                 # the new edition is still on: nothing of it
        sa, sb = self.store.key(a), self.store.key(b)
        self.assertEqual(self.titles(), sorted([f'fair20261003:f_king:{sa}', f'fair20261003:f_master:{sb}']))
        fb._done.clear()                                               # another process: the mark stops it
        self.assertIsNone(fb.settle(self.store, AFTER + fb.GRACE))
        self.assertEqual(len(self.titles()), 2)

    def test_an_edition_already_settled_is_left_alone(self):
        self.play_last_edition()
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-10-03'}):
            got = fb.settle(self.store, at(2026, 10, 8, 0, 5))         # the server running then did it
        self.assertEqual([w['title'] for w in got], ['f_king', 'f_master'])
        fb._done.clear()
        self.clock.t = OPEN
        self.assertIsNone(fb.settle(self.store, OPEN))
        self.assertEqual(len(self.titles()), 2)


if __name__ == '__main__':
    unittest.main()
