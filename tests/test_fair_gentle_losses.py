"""Compulsory fair losses: owner 11/10, a police fine is 30% of the caught round's own stake (fair_bm.round_fine), never
a share of the wallet or the day's winnings; the Chợ đen's arrest roll seizes the stake too, a skill stall's watch
cancels it. Legacy collections keep the small loss_limits ceiling."""
import copy
import os
import unittest
from unittest import mock

from game import bank as bk, fair as fh, fair_bm as bm, fair_hai as hai
from game import fair_watch as watch
from game.engine import GameError, validate_state
from tests import test_fair as base
from tests import test_black_market as black
from tests import test_fair_watch as watched
from tests.test_fair_knife import safe_taps


def cap(wallet, due=10**9):
    return min(due, wallet * 2 // 100, 2000, max(0, wallet - 100))


class FineBoundaries(unittest.TestCase):
    def test_watch_arrest_cancels_stake_and_takes_30_percent_of_it_from_the_wallet(self):
        for wallet, stake in ((0, 0), (1, 1), (99, 99), (100, 100), (101, 101), (1000, 1000), (10**6, 10**6),
                              (100, 1000), (0, 1000), (10**6, 10)):
            with self.subTest(wallet=wallet, stake=stake):
                s = base.story(wallet)
                j = s['journey']; f = j['fair'] = fh.initial()
                j['bank'] = dict(bk.initial(j['seed'], j['life_day']), balance=10**6)
                bank = copy.deepcopy(j['bank'])
                pay = mock.Mock()
                receipt = bm.arrest(j, f, base.OPEN, 'kn', stake, pay)
                fine = min(wallet, stake * 30 // 100)
                self.assertEqual(receipt['fine'], fine)
                pay.assert_not_called()
                self.assertEqual(j['wallet'], wallet - fine)
                self.assertEqual(j['bank'], bank)   # the watch's fine is the wallet's only
                self.assertTrue(receipt['canceled'])
                self.assertEqual((receipt['seized'], receipt['say']), (0, bm.SAY_ARREST))
                self.assertEqual(f['net'], -fine)
                self.assertEqual(f['stats']['lost'], fine)

    def test_seizing_arrest_takes_the_stake_then_30_percent_from_wallet_and_bank(self):
        for wallet, stake, balance in ((1000, 1000, 0), (1000, 1000, 10**6), (10**6, 400000, 0), (400000, 400000, 50000),
                                       (10, 10, 0)):
            with self.subTest(wallet=wallet, stake=stake, balance=balance):
                s = base.story(wallet)
                j = s['journey']; f = j['fair'] = fh.initial()
                j['bank'] = dict(bk.initial(j['seed'], j['life_day']), balance=balance)
                paid = []

                def pay(amount):
                    paid.append(amount)
                    j['wallet'] += amount
                receipt = bm.arrest(j, f, base.OPEN, 'xd', stake, pay, seize=True)
                due = stake * 30 // 100
                fine = min(due, wallet - stake + balance)
                self.assertEqual(paid, [-stake])
                self.assertEqual((receipt['fine'], receipt['seized'], receipt['canceled']), (fine, stake, False))
                self.assertEqual(receipt['say'], bm.SAY_SEIZE)
                self.assertEqual(j['wallet'], max(0, wallet - stake - due))
                self.assertEqual(j['bank']['balance'], balance - max(0, fine - (wallet - stake)))
                self.assertEqual(f['stats']['lost'], fine)

    def test_legacy_hai_fines_never_use_bank_or_savings(self):
        for wallet in (0, 1, 99, 100, 101, 1000, 10**6):
            with self.subTest(wallet=wallet):
                s = base.story(wallet)
                j = s['journey']; f = j['fair'] = fh.initial()
                j['bank'] = bk.initial(j['seed'], j['life_day'])
                j['bank']['balance'] = 10**6
                before = copy.deepcopy(j['bank'])
                fine = hai.seize(s, j, f, 10**6)
                self.assertEqual(fine, cap(wallet))
                self.assertEqual(j['wallet'], wallet - fine)
                self.assertEqual(j['bank'], before)
                self.assertEqual(f['stats']['lost'], fine)

    def test_hai_device_fine_is_half_of_wallet_and_bank(self):
        """Owner 11/10 "phạt 50% ví (tổng tiền, có trừ cả ví ngân hàng)": the wallet first, then the bank."""
        for wallet in (0, 1, 99, 100, 101, 1000, 10**6, 3 * 10**6):
            with self.subTest(wallet=wallet):
                s = base.story(wallet)
                j = s['journey']; f = j['fair'] = fh.initial()
                j['bank'] = bk.initial(j['seed'], j['life_day'])
                j['bank']['balance'] = 10**6
                fine = hai.device_fine(s, j, f)
                self.assertEqual(fine, (wallet + 10**6) // 2)
                self.assertEqual(j['wallet'], max(0, wallet - fine))
                self.assertEqual(j['bank']['balance'], 10**6 - max(0, fine - wallet))
                self.assertEqual(f['stats']['lost'], fine)

    def test_legacy_seizure_does_not_stack_an_arrest_fine(self):
        s = base.story(1000)
        j = s['journey']; f = j['fair'] = fh.initial()
        seized = hai.seize(s, j, f, 5000)
        with self.assertRaises(fh._Caught) as caught:
            fh._arrested(j, f, base.OPEN, 'oaq', seized, lambda amount: None, 'oaq_win')
        self.assertEqual(j['wallet'], 980)
        self.assertEqual(caught.exception.result['fair']['arrest']['fine'], 0)


class PaidRaids(black.BlackMarketBase):
    def test_all_paid_raids_seize_the_stake_and_fine_30_percent_of_it(self):
        paid = {k: v for k, v in black.PAID.items() if k != 'kn'}
        paid['dg'] = ('fair_dg', {'race': fh.dog.race(self.clock.t + 12), 'lane': 0, 'stake': 1000}, 1000)
        for game, (name, payload, stake) in paid.items():
            with self.subTest(game=game):
                s = black.story(10000)
                s, _ = self.act(s, 'fair_bm_pay')
                self.rich(s)
                before = copy.deepcopy(s['journey'].get('bank'))
                if game == 'dg':
                    payload['race'] = fh.dog.race(self.clock.t + 6)
                self.caught()
                s, r = self.act(s, name, **payload)
                a = r['fair']['arrest']
                fine = stake * 30 // 100
                self.assertEqual((a['stake'], a['seized'], a['fine'], a['canceled']), (stake, stake, fine, False))
                self.assertEqual(s['journey']['wallet'], 10000 - stake - fine)
                self.assertEqual(s['journey'].get('bank'), before)
                self.assertEqual(s['journey']['fair']['stats']['lost'], stake + fine)
                self.assertEqual(s['journey']['fair']['net'], bm.ARREST_FROM + 1 - stake - fine)
                self.assertEqual(sum(row['amount'] for row in s['journey']['history'] if row['kind'] == 'fair'), -stake - fine)
                validate_state(s)


class OwnChecks(base.FairBase):
    def test_xd_cancels_whole_wallet_bet_but_keeps_cooldown(self):
        for wallet in (10, 99, 100, 101, 1000, 10**6):
            with self.subTest(wallet=wallet):
                self.dice(base.Dice(draws=[0]))
                s = base.story(wallet)   # today's winnings past ARREST_FROM: a round the police watch (bm.arrest_p > 0)
                s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(base.OPEN), ed=fh.edition(), net=bm.ARREST_FROM + 1)
                s, r = self.act(s, 'fair_xd', side='chan', stake=wallet)
                fine = max(fh.FINE_MIN, wallet * 30 // 100)   # owner 11/10: 30% of the round's stake
                self.assertEqual(fine, fh.xd_fine(wallet))
                self.assertEqual(r['fair']['net'], -fine)
                self.assertEqual(s['journey']['wallet'], wallet - fine)
                self.assertTrue(r['fair']['canceled'])
                self.assertGreater(s['journey']['fair']['raid_until'], self.clock.t)
                self.assertIn('30% tiền cược ván này', r['message'])
                validate_state(s)

    def test_a_small_unwatched_round_is_never_dep_chieu(self):
        """Owner 11/10 "đánh nhiều mới bị phạt thôi": no big stake, no big winnings, no dẹp chiếu draw."""
        self.dice(base.Dice(draws=[0]))
        s, r = self.act(base.story(1000), 'fair_xd', side='chan', stake=1000)
        self.assertFalse(r['fair'].get('raid'))
        self.assertIn('coins', r['fair'])
        validate_state(s)

    def test_wallet_and_asset_checks_are_off(self):
        """Owner 11/10: the wallet raid and the asset check (fines on the wallet or the profit) no longer run."""
        self.assertIs(fh.WALLET_CHECKS, False)
        s = base.story(10**6)
        j = s['journey']; f = j['fair'] = dict(fh.initial(), date=fh.vn_date(base.OPEN), ed=fh.edition(), net=60000)
        f['stats']['won'] = 200000
        j['bank'] = dict(bk.initial(j['seed'], j['life_day']), balance=10**6)
        bank = copy.deepcopy(j['bank'])
        self.dice(base.Dice(draws=[0, 0]))
        s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        j = s['journey']
        self.assertNotIn('wealth_raid', r['fair'])
        self.assertNotIn('audit', r['fair'])
        self.assertNotIn(fh.AUDIT_KEY, j)
        self.assertEqual(j['wallet'], 10**6 - 1)
        self.assertEqual(j['bank'], bank)
        self.assertEqual(j['fair']['stats']['lost'], 1)
        validate_state(s)

    @mock.patch.object(fh, 'WALLET_CHECKS', True)   # off since owner 11/10: the dormant code keeps its bounds
    def test_wealth_and_audit_share_one_budget_and_keep_each_cooldown(self):
        for wallet in (1, 99, 100, 101, 1000, 10**6):
            with self.subTest(wallet=wallet):
                s = base.story(wallet)
                j = s['journey']; f = j['fair'] = dict(fh.initial(), date=fh.vn_date(base.OPEN), ed=fh.edition(), net=60000)
                f['stats']['won'] = 200000
                j['bank'] = dict(bk.initial(j['seed'], j['life_day']), balance=10**6)
                bank = copy.deepcopy(j['bank'])
                self.dice(base.Dice(draws=[0, 0]))
                s, r = self.act(s, 'fair_bc', bets={'cua': 1})
                j = s['journey']; fine = cap(wallet - 1)
                self.assertEqual(j['wallet'], wallet - 1 - fine)
                self.assertEqual(j['bank'], bank)
                self.assertEqual(j['fair']['stats']['lost'], 1 + fine)
                self.assertEqual(fh.money_of(j)[0], 200000 - 1 - fine)
                self.assertEqual(j['fair_audit']['base'], fh.money_of(j)[0])
                self.assertIn('wealth_check_at', j['fair'])
                self.assertEqual(r['fair']['audit']['bank'], 0)
                self.assertEqual(sum(row['amount'] for row in j['history'] if row['kind'] == 'fair'), -1 - fine)
                validate_state(s)

    def test_kinh_false_claim_keeps_the_reserve(self):
        s, _ = self.act(base.story(1000), 'fair_loto_buy')
        rv = fh.round_view(s['journey']['fair']['loto'])
        for wallet in (0, 1, 99, 100, 101, 1000):
            with self.subTest(wallet=wallet):
                s['journey']['wallet'] = wallet
                uncalled = next(n for row in rv['cards'][0] for n in row if n not in rv['seq'][:1])
                s, r = self.act(s, 'fair_loto_kinh', card=0, at=1, marks=[uncalled])
                self.assertEqual(r['fair']['fine'], cap(wallet, fh.KINH_FINE))
                self.assertEqual(s['journey']['wallet'], wallet - cap(wallet, fh.KINH_FINE))


class KnifeCancellation(watched.WatchBase):
    def test_legacy_later_level_refunds_without_guessing_daily_origin(self):
        s, _ = self.act(self.inside(1000), 'fair_kn_start', stake=1000)
        s, _ = self.throw(s, safe_taps(self.board(s), self.board(s)['need']))
        s, _ = self.act(s, 'fair_kn_next')
        s['journey'].pop(fh.KN_STAKE_KEY)  # a still-playing level from an older server
        before_net = s['journey']['fair']['net']
        before_day = copy.deepcopy(s['journey']['fair_day'])
        taps = safe_taps(self.board(s), self.board(s)['need'])
        with mock.patch.object(watch, 'kn_throw', return_value=True):
            s, r = self.throw(s, taps)
        self.assertEqual((s['journey']['wallet'], s['journey']['fair']['stats']['lost']), (700, 300))   # 30% of 1000
        self.assertEqual(fh.money_of(s['journey'])[0], -300)
        self.assertEqual(s['journey']['fair']['net'], before_net - 300)
        self.assertEqual(s['journey']['fair_day'], before_day)
        with mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '1'}), self.assertRaises(GameError):
            self.throw(s, taps)
        validate_state(s)

    def test_bad_optional_stake_metadata_is_rejected(self):
        s, _ = self.act(self.inside(1000), 'fair_kn_start', stake=1000)
        for patch in ({'refunded': -1}, {'fine': 2001}, {'day': 'x' * 11}, {'seed': True}, {'at': -1}):
            bad = copy.deepcopy(s)
            bad['journey'][fh.KN_STAKE_KEY].update(patch)
            with self.subTest(patch=patch), self.assertRaises(GameError):
                validate_state(bad)

    def test_refund_after_cross_midnight_level_uses_original_stake_day(self):
        self.t = base.at(2026, 10, 10, 23, 59, 59)
        s, _ = self.act(self.inside(1000), 'fair_kn_start', stake=1000)
        taps = safe_taps(self.board(s), self.board(s)['need'], start=2000)
        s, _ = self.throw(s, taps)
        s, _ = self.act(s, 'fair_kn_next')
        with mock.patch.object(watch, 'kn_throw', return_value=True):
            s, _ = self.throw(s, safe_taps(self.board(s), self.board(s)['need']))
        self.assertEqual(s['journey']['fair']['net'], -300)
        self.assertEqual(s['journey']['fair_day']['kn'], 0)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 300)
        view = fh.knife_public(s['journey'], s['journey']['fair'], self.t)['run']
        self.assertTrue(view['canceled'])
        self.assertEqual((view['refunded'], view['fine']), (1000, 300))
        validate_state(s)

    def test_started_run_refund_once_without_wins_earnings_or_day_cap_credit(self):
        s = self.inside(1000)
        s, _ = self.act(s, 'fair_kn_start', stake=1000)
        taps = safe_taps(self.board(s), self.board(s)['need'])
        with mock.patch.object(watch, 'kn_throw', return_value=True):
            s, r = self.throw(s, taps)
        a = r['fair']['arrest']; j = s['journey']; f = j['fair']
        self.assertEqual((a['refunded'], a['fine'], j['wallet']), (1000, 300, 700))
        self.assertEqual((f['net'], f['stats']['lost'], f['stats']['won'], f['stats']['earned']), (-300, 300, 0, 0))
        self.assertEqual(j['fair_day']['kn'], 0)
        self.assertEqual((j['fair_kn']['w'], j['fair_kn']['top']), (0, 0))
        self.assertEqual(sum(row['amount'] for row in j['history'] if row['kind'] == 'fair'), -300)
        before = copy.deepcopy(s)
        with mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '1'}), self.assertRaises(GameError):
            self.throw(s, taps)
        self.assertEqual(s, before)
        validate_state(s)

    def test_canceled_start_does_not_debit_daily_cap(self):
        with mock.patch.object(watch, 'kn_start', return_value=True):
            s, r = self.act(self.inside(1000), 'fair_kn_start', stake=1000)
        self.assertEqual(s['journey']['fair_day'].get('kn', 0), 0)
        self.assertEqual(s['journey']['wallet'], 700)
        self.assertEqual(s['journey']['fair']['stats']['lost'], 300)


class StoredFines(base.StoreBase):
    def test_replay_weekly_loss_and_other_account_only_see_actual_fine(self):
        from game import fair_loss as fl, marriage as mr
        tok = self.player('Lan', wallet=1000)
        other = self.player('Mai', wallet=1000)
        untouched = copy.deepcopy(self.store.read(other)[0])
        def prepare(s):
            s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(self.clock.t), ed=fh.edition(), net=300001)
        mr._mutate(self.store, {self.store.key(tok): prepare})
        args = (tok, 'gentle-fair-raid-01', self.store.read(tok)[1], None, 'fair_bc', {'bets': {'cua': 100}})
        with mock.patch.dict(os.environ, {'MNL_BM_OFF': '0'}), mock.patch.object(bm, '_arrest_roll', return_value=True), \
                mock.patch.object(fl, 'now', side_effect=lambda: self.clock.t):
            first = self.store.command(*args)
            replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        saved = self.store.read(tok)[0]['journey']
        self.assertEqual((saved['wallet'], saved['fair']['stats']['lost']), (870, 130))   # 100 seized + its 30 fine
        self.assertEqual(self.store.read(other)[0], untouched)
        with self.store.connect() as db:
            rows = list(db.execute('SELECT sid,net FROM fair_loss_week'))
        self.assertEqual([(r['sid'], r['net']) for r in rows], [(self.store.key(tok), -130)])
