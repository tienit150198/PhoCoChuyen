"""Free Chợ đen entry (10/10), safe legacy entry commands and unchanged police enforcement.
Covers empty wallets, old saves/bans, arrests/fines, hidden rates and rollback validation."""
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tokenize
import unittest
from pathlib import Path
from unittest import mock

from game import bank as bk
from game import fair as fh
from game import fair_bm as bm
from game import fair_knife as knife
from game import fair_scratch as scratch
from game import journey as jr
from game.engine import GameError, dormant_out, new_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
VN = fh.VN
OLD_RELEASE = '7b46fa1b'   # 1.9.26, the release this one may be rolled back to


def at(y, m, d, hh=12, mm=0, ss=0):
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=VN).timestamp()


OPEN = at(2026, 10, 10, 20)   # day 2 of the edition (09/10 → 13/10)


def story(wallet=50000):
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey']['gender'] = 'female'
    s['journey']['wallet'] = wallet
    validate_state(s)
    return s


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        self.t += 6   # past the pause between rounds (bầu cua's bowl too)
        return self.t


PAID = {   # every stall that takes a stake: (command, payload, stake)
    'bc': ('fair_bc', {'bets': {'cua': 100}}, 100),
    'xd': ('fair_xd', {'side': 'chan', 'stake': 50}, 50),
    'lt': ('fair_loto_buy', {'tier': 'lon', 'n': 1}, 10),
    'xs': ('fair_xs', {'price': scratch.TIERS[3]}, scratch.TIERS[3]),
    'kn': ('fair_kn_start', {'stake': knife.STAKES[2]}, knife.STAKES[2]),
}


class BlackMarketBase(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_BM_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        for k in ('MNL_FAIR_START', 'MNL_FAIR_DAYS'):
            os.environ.pop(k, None)
        self.clock = Clock(OPEN)
        p = mock.patch.object(fh, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.ask(True)   # the đàn em ask (hên xui: tests/AskedOrNot covers the roll)

    def ask(self, on=True):
        p = mock.patch.object(bm, 'asked', lambda j, t: on)
        p.start()
        self.addCleanup(p.stop)

    def act(self, s, name, **p):
        return fh.action(s, name, p)

    def refused(self, s, name, code, **p):
        with self.assertRaises(GameError) as e:
            fh.action(s, name, p)
        self.assertEqual(e.exception.code, code)
        return e.exception

    def rich(self, s, net=None):
        """Today's Chợ đen net above fair_bm.ARREST_FROM: the police come only for the big winners (owner 09/10)."""
        s['journey']['fair']['net'] = bm.ARREST_FROM + 1 if net is None else net
        validate_state(s)
        return s

    def caught(self, on=True):
        p = mock.patch.object(bm, '_arrest_roll', lambda *a: on)
        p.start()
        self.addCleanup(p.stop)


class Gate(BlackMarketBase):
    def test_free_entry_at_every_wallet_and_with_old_ask_enabled(self):
        for wallet in (0, -500, 9999, 12345, 10**9):
            with self.subTest(wallet=wallet):
                s = story(wallet)
                b = fh.public(s)['bm']
                self.assertEqual((b['st'], b['inside'], b['ban'], b['fee']), ('free', True, False, 0))
                s, r = self.act(s, 'fair_oaq_start', lv='de')
                self.assertEqual(s['journey']['wallet'], wallet)

    def test_old_pay_and_refuse_commands_never_touch_money_or_history(self):
        for wallet in (0, -500, 9999, 12345, 10**9):
            for command in bm.COMMANDS:
                with self.subTest(wallet=wallet, command=command):
                    s = story(wallet)
                    s['journey']['bank'] = bk.initial(1, 1)
                    s['journey']['bank']['balance'] = 80000
                    before = json.loads(json.dumps(s['journey']['history']))
                    for _ in range(2):
                        s, r = self.act(s, command)
                        self.assertTrue(r['fair']['again'])
                        self.assertNotIn('paid', r['fair'])
                        self.assertNotIn('robbed', r['fair'])
                    self.assertEqual(s['journey']['wallet'], wallet)
                    self.assertEqual(s['journey']['bank']['balance'], 80000)
                    self.assertEqual(s['journey']['history'], before)
                    self.assertEqual(s['journey']['fair']['net'], 0)
                    self.assertEqual(s['journey']['fair']['stats']['lost'], 0)
                    self.assertNotIn('fair_bm', s['journey'])
                    validate_state(s)

    def test_enforcement_switch_does_not_control_free_entry(self):
        for switch in (None, '1'):
            with mock.patch.dict(os.environ):
                if switch is None:
                    os.environ.pop('MNL_BM_OFF', None)
                else:
                    os.environ['MNL_BM_OFF'] = switch
                self.assertEqual(bm._gate_on(), switch is None)
                s = story(0)
                self.assertTrue(fh.public(s)['bm']['inside'])
                for command in bm.COMMANDS:
                    s, _ = self.act(s, command)
                self.assertEqual(s['journey']['wallet'], 0)
                self.assertNotIn('fair_bm', s['journey'])

    def test_entry_stays_free_across_vietnam_midnight(self):
        for day in (10, 11, 12, 13):
            self.clock.t = at(2026, 10, day, 0, 0)
            self.assertEqual(fh.public(story(0))['bm']['st'], 'free')

    def test_old_paid_robbed_and_ban_saves_remain_readable(self):
        for status in bm.STATES:
            s = story()
            s['journey']['fair_bm'] = {'d': '2026-10-10', 's': status}
            validate_state(s)
            before = json.loads(json.dumps(s['journey']['fair_bm']))
            for command in bm.COMMANDS:
                s, r = self.act(s, command)
                self.assertEqual(s['journey']['fair_bm'], before)
                self.assertEqual(s['journey']['wallet'], 50000)
            self.assertEqual(fh.public(s)['bm']['ban'], status == 'ban')
            self.clock.t = at(2026, 10, 11, 9)
            self.assertEqual(fh.public(s)['bm']['st'], 'free')
            self.clock.t = OPEN

    def test_police_still_arrest_after_free_entry(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.rich(s)
        self.caught(True)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('arrest', r['fair'])

    def test_closed_market_compatibility_commands_remain_closed(self):
        os.environ['MNL_FAIR_DAYS'] = '5'
        self.clock.t = at(2026, 10, 14, 0, 0)
        for command in bm.COMMANDS:
            self.refused(story(), command, 'fair_closed')

    def test_client_has_no_payment_or_refusal_controls(self):
        js = (ROOT / 'public/js/v4/fair.js').read_text(encoding='utf-8')
        self.assertNotIn("send('fair_bm_pay'", js)
        self.assertNotIn("send('fair_bm_refuse'", js)
        self.assertNotIn('Nộp bảo kê', js)


class Arrest(BlackMarketBase):
    def test_every_paid_stall_can_be_raided(self):
        for game, (name, p, stake) in PAID.items():
            if game == 'kn':   # a skill game since owner 09/10: not rolled (tests/test_fair_watch.py)
                continue
            with self.subTest(game=game):
                s = story(10000)
                s, _ = self.act(s, 'fair_bm_pay')   # 10,000 left
                self.rich(s)
                with mock.patch.object(bm, '_arrest_roll', lambda *a: True):
                    s, r = self.act(s, name, **p)
                a = r['fair']['arrest']
                fine = stake * 30 // 100   # owner 11/10: the stake is seized, the fine is 30% of it (bm.round_fine)
                self.assertEqual((r['fair']['game'], a['stake'], a['fine'], a['seized']), (game, stake, fine, stake))
                self.assertEqual(s['journey']['wallet'], 10000 - stake - fine)
                self.assertFalse(a['canceled'])
                self.assertEqual(a['say'], bm.SAY_SEIZE)
                self.assertEqual(a['wallet'], s['journey']['wallet'])
                self.assertNotIn('fair_bm', s['journey'])
                self.assertNotIn('dice', r['fair'])   # no outcome
                last = s['journey']['history'][-1]
                self.assertEqual((last['amount'], last['label']), (-fine, bm.FINE_LABEL))
                self.assertEqual([r['amount'] for r in s['journey']['history'] if r['kind'] == 'fair'], [-stake, -fine])
                self.assertEqual(s['journey']['fair']['net'], bm.ARREST_FROM + 1 - stake - fine)
                self.assertIn(f'Tịch thu {stake} xu tiền cược', r['message'])
                self.assertIn('f_raid', s['journey']['titles'])
                self.assertIn('Công an ập vào', r['message'])
                pub = fh.public(s)['bm']
                self.assertEqual((pub['ban'], pub['inside']), (False, True))   # no ban since owner 09/10 "bỏ cấm"
                self.assertNotIn('đuổi', r['message'])
                s, r2 = self.act(s, 'fair_snack', item='nuoc_mia')   # still in the Chợ đen
                validate_state(s)

    def test_the_skill_stalls_are_never_rolled(self):
        """Owner 09/10 "phóng dao, ô ăn quan thì chơi hệ kĩ năng": a rich player's big knife run is not rolled for."""
        s = story(3 * 10**6)
        s, _ = self.act(s, 'fair_bm_pay')
        self.rich(s, 10**6)
        roll = mock.Mock(return_value=True)
        with mock.patch.object(bm, '_arrest_roll', roll):
            s, r = self.act(s, 'fair_kn_start', stake=1000)
            self.assertNotIn('arrest', r['fair'])
            s, r = self.act(s, 'fair_oaq_start', lv='kho')
            self.assertNotIn('arrest', r['fair'])
        roll.assert_not_called()

    def test_a_saved_same_day_ban_still_blocks_entry(self):
        s = story()
        s['journey']['fair_bm'] = {'d': '2026-10-10', 's': 'ban'}
        validate_state(s)
        b = fh.public(s)['bm']
        self.assertEqual((b['st'], b['inside'], b['ban']), ('ban', False, True))
        self.refused(s, 'fair_bc', 'fair_bm_gate', bets={'cua': 10})

    def test_no_arrest_plays_the_round(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertIn('dice', r['fair'])
        self.assertNotIn('arrest', r['fair'])
        self.assertNotIn('fair_bm', s['journey'])

    def test_round_begun_still_finishes_after_a_ban(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(False)
        s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=1)
        self.caught(True)
        self.rich(s)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('arrest', r['fair'])
        s, r = self.act(s, 'fair_loto_fold')   # LATE: finishing what was begun
        self.assertTrue(r['fair']['folded'])

    def test_the_fine_never_makes_debt(self):
        s = story(50)
        s, _ = self.act(s, 'fair_bm_pay')   # compatibility no-op; 50 left
        self.caught(True)
        self.rich(s)
        s, r = self.act(s, 'fair_xd', side='le', stake=50)   # the stake is seized: nothing left for its 15 xu fine
        self.assertEqual((r['fair']['arrest']['seized'], r['fair']['arrest']['fine']), (50, 0))
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertFalse(s['journey']['in_debt'])
        self.assertNotIn('phạt thêm', r['message'])
        validate_state(s)

    def test_the_fine_is_the_round_s_whatever_the_day_won(self):
        """Owner 11/10 "phải tính tiền phạt của 1 trận": a 400,000 round caught = the stake seized + 120,000, whatever
        today's net."""
        for net in (0, bm.ARREST_FROM + 1, 2 * 10**6, 10**8):
            with self.subTest(net=net):
                s = story(10**6)
                s, _ = self.act(s, 'fair_bm_pay')
                self.rich(s, net)
                self.caught(True)
                s, r = self.act(s, 'fair_xd', side='chan', stake=400000)
                a = r['fair']['arrest']
                self.assertEqual((a['seized'], a['fine']), (400000, 120000))   # (the cell: tests/test_jail.py)
                self.assertEqual(s['journey']['wallet'], 10**6 - 520000)
                self.assertEqual(s['journey']['fair']['net'], net - 520000)
                self.assertIn('Tịch thu 400.000 xu tiền cược, phạt thêm 120.000 xu', r['message'])
                validate_state(s)

    def test_the_fine_takes_the_bank_after_the_wallet(self):
        """What the wallet cannot pay comes from the bank: its account, the demand pot, then a term deposit (closed
        early, the rest back to the account); never below zero, no loss_limits ceiling."""
        s = story(450000)
        j = s['journey']
        b = j['bank'] = bk.initial(j['seed'], j['life_day'])
        b['balance'], b['demand'] = 30000, 20000
        b['terms'].append(dict(id='t1', amount=100000, term=30, rate=bk.TERM_RATE[30], start=j['life_day'],
                               due=j['life_day'] + 30, renew=False))
        b['seq'] = 1
        validate_state(s)
        self.caught(True)
        s, r = self.act(s, 'fair_xd', side='chan', stake=400000)   # 50,000 left in the wallet; the fine is 120,000
        a = r['fair']['arrest']
        b = s['journey']['bank']
        self.assertEqual((a['seized'], a['fine'], a['wallet']), (400000, 120000, 0))
        # wallet 50k, account 30k, demand 20k, then 20k of the 100k term: closed, its 80k back to the account
        self.assertEqual((s['journey']['wallet'], b['balance'], b['demand'], b['terms']), (0, 80000, 0, []))
        self.assertEqual(s['journey']['fair']['net'], -520000)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 520000)
        validate_state(s)

    def test_a_fine_too_big_for_wallet_and_bank_stops_at_zero(self):
        s = story(400000)
        j = s['journey']
        j['bank'] = bk.initial(j['seed'], j['life_day'])
        j['bank']['balance'] = 70000
        validate_state(s)
        self.caught(True)
        s, r = self.act(s, 'fair_xd', side='chan', stake=400000)
        self.assertEqual(r['fair']['arrest']['fine'], 70000)
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 0))
        self.assertFalse(s['journey']['in_debt'])
        validate_state(s)

    def test_next_day_back_in(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(True)
        self.rich(s)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('arrest', r['fair'])
        self.clock.t = at(2026, 10, 11, 9)
        self.assertEqual(fh.public(s)['bm'], dict(fee=0, st='free', inside=True, ban=False, who=list(bm.GUARD)))
        s, _ = self.act(s, 'fair_bm_refuse')
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('dice', r['fair'])

    def test_the_roll(self):
        class R:
            def __init__(self, x):
                self.x = x

            def random(self):
                return self.x
        self.assertEqual((bm.BM_ARREST_P, bm.ARREST_FROM), (0.02, 300000))   # owner 11/10 (later): "tỷ lệ bị bắt giảm thấp"
        with mock.patch.object(bm, '_rng', R(.0199)):
            self.assertTrue(bm._arrest_roll())
        with mock.patch.object(bm, '_rng', R(.02)):
            self.assertFalse(bm._arrest_roll())

    def test_arrests_leave_the_stalls_draws_alone(self):
        """The arrest has its own random source: a stall's scripted draws (fair._rng) are not consumed by it."""
        gate = fh._loc_gate.set(False)  # isolate arrest draws from the optional Lộc bonus
        self.addCleanup(fh._loc_gate.reset, gate)
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        seen = []

        class Dice:
            def choice(self, seq):
                seen.append('c')
                return seq[1]

            def random(self):
                seen.append('r')
                return .99

            def randrange(self, n):
                return 0

            def getrandbits(self, n):
                return 7
        with mock.patch.object(fh, '_rng', Dice()), mock.patch.object(bm, '_rng') as arr:
            arr.random.return_value = .9
            s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertEqual(r['fair']['dice'], ['cua', 'cua', 'cua'])
        self.assertEqual(seen, ['c', 'c', 'c'])   # three dice and nothing else: as before the Chợ đen


class BigStake(BlackMarketBase):
    """Owner 11/10 (later): the raid chance is today's winnings' share (PROFIT_CURVE) plus the stake's (STAKE_CURVE),
    never above ARREST_CAP; hidden from the client."""

    POOR, RICH = {'net': 0}, {'net': bm.ARREST_FROM + 1}

    def test_the_constants(self):
        self.assertEqual((bm.BIG_STAKE_FROM, bm.STAKE_TOP_PCT, bm.ARREST_CAP, bm.FINE_PCT), (50000, 90, .90, 30))
        self.assertEqual(bm.STAKE_CURVE, ((50_000, 2, 300_000, 10), (300_000, 30, 1_000_000, 50),
                                          (1_000_000, 50, 10_000_000, 80)))
        self.assertEqual(bm.PROFIT_CURVE, ((300_000, 2), (1_000_000, 5), (3_000_000, 10), (10_000_000, 20)))
        for gone in ('BIG_STAKE_STEP', 'BIG_STAKE_PCT', 'profit_fine'):
            self.assertFalse(hasattr(bm, gone), gone)

    def test_the_stake_curve(self):
        for stake, pct in ((None, 0), ('60000', 0), (60000.0, 0), (True, 0), (10, 0), (49999, 0), (50000, 2),
                           (60000, 2.32), (100000, 3.6), (175000, 6), (299999, 9.999968), (300000, 30),
                           (650000, 40), (999999, 49.9999714), (10**6, 50), (5_500_000, 65), (9_999_999, 79.9999967),
                           (10**7, 90), (10**9, 90)):
            with self.subTest(stake=stake):
                self.assertAlmostEqual(bm.big_stake_pct(stake), pct, places=6)

    def test_the_profit_curve(self):
        for net, pct in ((None, 0), (-10**6, 0), (0, 0), (300000, 0), (300001, 2), (10**6, 2), (10**6 + 1, 5),
                         (3 * 10**6, 5), (3 * 10**6 + 1, 10), (10**7, 10), (10**7 + 1, 20), (10**9, 20)):
            with self.subTest(net=net):
                self.assertEqual(bm.profit_pct(None if net is None else {'net': net}), pct)

    def test_the_boundaries(self):
        for stake, poor, rich in ((10, 0, .02), (49999, 0, .02), (50000, .02, .04), (60000, .0232, .0432),
                                  (100000, .036, .056), (300000, .30, .32), (10**6, .50, .52),
                                  (10**7, .90, .90), (10**7 - 1, .7999999667, .8199999667)):
            with self.subTest(stake=stake):
                self.assertAlmostEqual(bm.arrest_p(self.POOR, stake), poor, places=9)
                self.assertAlmostEqual(bm.arrest_p(self.RICH, stake), rich, places=9)
                self.assertLessEqual(bm.arrest_p(self.RICH, stake), bm.ARREST_CAP)
        self.assertEqual(bm.arrest_p(self.POOR, 49999), 0)   # below 50k and not rich: nobody rolls
        self.assertEqual(bm.arrest_p({'net': bm.ARREST_FROM}, 49999), 0)   # 300k is not "above 300k"
        self.assertAlmostEqual(bm.arrest_p({'net': 2 * 10**6}, 400000), .05 + (30 + 20 / 7) / 100, places=9)   # 5% + 32.86%
        self.assertAlmostEqual(bm.arrest_p({'net': 10**8}, 10), .20, places=9)
        self.assertEqual(bm.arrest_p({'net': 10**8}, 10**7), .90)   # 20% + 90%, capped
        for odd in (None, '60000', 60000.0, True):
            self.assertEqual(bm.arrest_p(self.POOR, odd), 0)

    def test_curve_is_monotone_and_capped(self):
        stakes = [0, 49999] + list(range(50000, 10**7 + 1, 50000)) + [2 * 10**7]
        for net in (-100000, 0, 300000, 300001, 10**6 + 1, 3 * 10**6 + 1, 10**7 + 1):
            rates = [bm.arrest_p({'net': net}, stake) for stake in stakes]
            self.assertEqual(rates, sorted(rates), 'larger stakes never make arrest less likely')
            for rate in rates:
                self.assertLessEqual(rate, bm.ARREST_CAP)
        for stake in (10, 60000, 400000, 2 * 10**6):
            rates = [bm.arrest_p({'net': net}, stake) for net in (0, 300001, 10**6 + 1, 3 * 10**6 + 1, 10**7 + 1)]
            self.assertEqual(rates, sorted(rates), 'bigger winnings never make arrest less likely')

    def test_the_roll_takes_the_rate(self):
        class R:
            def __init__(self, x):
                self.x = x

            def random(self):
                return self.x
        with mock.patch.object(bm, '_rng', R(.4999)):
            self.assertTrue(bm._arrest_roll(bm.arrest_p(self.POOR, 10**6)))
        with mock.patch.object(bm, '_rng', R(.52)):
            self.assertFalse(bm._arrest_roll(bm.arrest_p(self.RICH, 10**6)))
        with mock.patch.object(bm, '_rng', R(.0231)):
            self.assertTrue(bm._arrest_roll(bm.arrest_p(self.POOR, 60000)))
        with mock.patch.object(bm, '_rng', R(.0232)):
            self.assertFalse(bm._arrest_roll(bm.arrest_p(self.POOR, 60000)))

    def rolls(self, stake, net=0, on=False):
        """One chiếu trong round of `stake` with today's net at `net`: the rates the police rolled with."""
        s = story(3 * 10**6)
        s, _ = self.act(s, 'fair_bm_pay')
        self.rich(s, net)
        seen = []

        def roll(p=bm.BM_ARREST_P):
            seen.append(p)
            return on
        with mock.patch.object(bm, '_arrest_roll', roll), mock.patch.object(fh._rng, 'random', return_value=.99):
            s, r = self.act(s, 'fair_xd', side='chan', stake=stake)
        return s, r, seen

    def test_below_50k_and_not_rich_nobody_rolls(self):
        for stake in (10, 49999):
            with self.subTest(stake=stake):
                s, r, seen = self.rolls(stake)
                self.assertEqual(seen, [])
                self.assertNotIn('arrest', r['fair'])

    def test_big_stakes_are_rolled_whatever_the_net(self):
        for stake, net, p in ((50000, 0, .02), (59999, -10**5, .02319968), (60000, 0, .0232), (60000, bm.ARREST_FROM + 1, .0432),
                              (100000, bm.ARREST_FROM, .036), (10**6, 0, .50), (10**6, bm.ARREST_FROM + 1, .52),
                              (10**6, 10**6 + 1, .55)):
            with self.subTest(stake=stake, net=net):
                s, r, seen = self.rolls(stake, net)
                self.assertEqual(len(seen), 1)
                self.assertAlmostEqual(seen[0], p, places=9)
                self.assertNotIn('arrest', r['fair'])
                self.assertIn('coins', r['fair'])   # not caught: the round played
        s, r, seen = self.rolls(49999, bm.ARREST_FROM + 1)   # small stakes: today's winnings alone (PROFIT_CURVE)
        self.assertAlmostEqual(seen[0], .02, places=9)
        s, r, seen = self.rolls(49999, 3 * 10**6 + 1)
        self.assertAlmostEqual(seen[0], .10, places=9)

    def test_caught_with_a_big_stake_and_a_small_net(self):
        s, r, seen = self.rolls(80000, 0, on=True)
        a = r['fair']['arrest']
        w = 3 * 10**6 - bm.BM_FEE
        self.assertEqual((a['stake'], a['seized'], a['fine']), (80000, 80000, 24000))   # (the cell: tests/test_jail.py)
        self.assertEqual(s['journey']['wallet'], w - 80000 - 24000)
        self.assertEqual(re.findall(r'[\d.,]+\s*%', r['message']), ['30%'])   # the fine's share of the stake, no rate
        validate_state(s)
        f = json.dumps(fh.public(s), ensure_ascii=False)
        for k in ('big_stake', 'arrest_p', '0.3', '0.04'):
            self.assertNotIn(k, f)

    def test_the_dog_race_too(self):
        s = story(3 * 10**6)
        s, _ = self.act(s, 'fair_bm_pay')
        seen = []
        n = fh.dog.race(self.clock.t + 6)
        with mock.patch.object(bm, '_arrest_roll', lambda p=bm.BM_ARREST_P: seen.append(p) or False):
            s, r = self.act(s, 'fair_dg', race=n, lane=0, stake=200000)
        self.assertAlmostEqual(seen[0], .068, places=9)   # 200,000: 2% + 8% × 150/250


class NothingShown(BlackMarketBase):
    def test_no_rate_reaches_the_client(self):
        s = story()
        f = fh.public(s)
        self.assertEqual(set(f['bm']), {'fee', 'st', 'inside', 'ban', 'who'})
        blob = json.dumps(f, ensure_ascii=False)
        for k in ('arrest_p', 'big_stake', 'arrest_cap', 'rob_pct', 'fine_pct', 'BM_ARREST', 'arrest_from', '300000', '300.000'):
            self.assertNotIn(k, blob)
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(True)
        self.rich(s)
        s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertEqual(set(r['fair']['arrest']), {'game', 'stake', 'fine', 'wallet', 'say', 'jail', 'canceled', 'seized'})
        self.assertEqual(re.findall(r'[\d.,]+\s*%', r['message']), ['30%'])   # owner 11/10: the fine is 30% of the stake
        for text in (bm.NEED_IN, bm.BANNED, bm.SAY_ARREST, bm.SAY_SEIZE,
                     bm.FINE_LABEL,):
            self.assertNotIn('%', text)
            self.assertNotIn('30', text)

    def test_the_client_prints_no_percentage(self):
        js = (ROOT / 'public/js/v4/fair.js').read_text(encoding='utf-8')
        part = js[js.index('/* ---- 🕶️ Chợ đen'):js.index('// 🥶 playing one stall too fast')]
        self.assertIn('bmGate', part)
        self.assertNotRegex(part, r'\d+\s*%')
        self.assertNotIn('30', re.sub(r'#[0-9a-f]{3,6}|\b\d{1,2}px', '', part))


class OldServer(BlackMarketBase):
    """Current and historical saves validate on 1.9.26, the release this one may be rolled back to."""

    def old_tree(self):
        if os.environ.get('MNL_BM_OLD_TREE'):
            return Path(os.environ['MNL_BM_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix='mnl-1926-')
        try:
            data = subprocess.run(['git', 'archive', OLD_RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {OLD_RELEASE} (MNL_BM_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_new_saves_validate_on_1_9_26(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        paid = json.loads(json.dumps(s))
        self.caught(True)
        self.rich(s)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 100})
        banned = json.loads(json.dumps(s))
        s2 = story(5000)
        s2, _ = self.act(s2, 'fair_bm_refuse')
        historical = []
        for status in bm.STATES:
            old_save = story()
            old_save['journey']['fair_bm'] = {'d': '2026-10-10', 's': status}
            historical.append(old_save)
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'out.append(s["journey"].get("fair_bm"))\nprint(json.dumps(out))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps([dormant_out(x) for x in [paid, banned, s2] + historical]), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(json.loads(out.stdout), [None, None, None] +
                         [{'d': '2026-10-10', 's': status} for status in bm.STATES])

    def test_bad_blocks_are_refused(self):
        for bad in ({'d': '2026-10-10'}, {'d': '2026-10-10', 's': 'vip'}, {'d': 'hôm nay!!!', 's': 'paid'}, 'paid'):
            with self.subTest(bad=bad):
                s = story()
                s['journey']['fair_bm'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)


class Renamed(unittest.TestCase):
    """Players see "Chợ đen": no "Hội chợ" left in the fair's strings (comments and quotes of the owner aside)."""
    PY = ('game/fair.py', 'game/fair_bm.py', 'game/fair_cash.py', 'game/fair_food.py', 'game/fair_photo.py',
          'live/fair.py')
    JS = ('public/js/v4/fair.js', 'public/js/v4/fair-booth.js', 'public/js/v4/fair-knife.js', 'public/js/v4/fair-walk.js',
          'public/js/v4/fair-scratch.js', 'public/js/v4/fair-loto.js', 'public/js/v4/honours.js', 'public/js/v4/journey.js',
          'public/js/v4/town-walk.js', 'public/js/scenes/town-place.js', 'public/js/scenes/fair-place.js', 'public/js/app.js')
    OLD = re.compile(r'[Hh]ội chợ')

    def test_python_strings(self):
        for f in self.PY:
            src = (ROOT / f).read_text(encoding='utf-8')
            lines = src.splitlines()
            for t in tokenize.generate_tokens(io.StringIO(src).readline):
                if t.type != tokenize.STRING or t.string.lstrip('rbfuRBFU').startswith(('"""', "'''")):
                    continue
                if '_OLD' in lines[t.start[0] - 1]:   # the former name, to keep today's older Sổ ví rows
                    continue
                with self.subTest(file=f, line=t.start[0]):
                    self.assertNotRegex(t.string, self.OLD)

    def test_js_code_lines(self):
        for f in self.JS:
            for i, ln in enumerate((ROOT / f).read_text(encoding='utf-8').splitlines(), 1):
                st = ln.lstrip()
                if st.startswith(('/*', '*', '//')):
                    continue
                code = ln.split('  // ')[0]
                with self.subTest(file=f, line=i):
                    self.assertNotRegex(code, self.OLD)

    def test_entry_and_title(self):
        self.assertIn('🕶️ Chợ đen', (ROOT / 'public/js/v4/town-walk.js').read_text(encoding='utf-8'))
        self.assertIn('<h2 id="fh-title">Chợ đen</h2>', (ROOT / 'public/js/v4/fair.js').read_text(encoding='utf-8'))
        names = {tid: name for tid, _, name, _ in fh.TITLE_ROWS}
        self.assertEqual(names['f_master'], 'Cao thủ chợ đen')
        self.assertTrue(all(v.endswith('chợ đen') for v in fh.LABELS.values()))


if __name__ == '__main__':
    unittest.main()
