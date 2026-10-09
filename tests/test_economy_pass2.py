"""Paid fair stakes and owner-approved business expenses (05/10 follow-up)."""
import copy
import random
from unittest.mock import patch
from game import fair as fh, fair_knife as kn, fair_scratch as xs
from game.engine import GameError, validate_state, public_state
from tests.test_fair import Dice, FairBase, story
from tests.test_fair_knife import safe_taps


class PaidStakeLimits(FairBase):
    def test_large_payouts_and_raid_cross_old_net_bound_safely(self):
        state=story(10000)
        state['journey']['fair']=dict(fh.initial(), date=fh.vn_date(self.clock.t), net=fh.NET_SAFE-1000)
        self.dice(random.Random(11))   # 07/10: a seed whose raid draw is under WEALTH_RAID_P .35 (seed 1's .445 was under .70)
        with patch.object(xs, 'prize_mult', return_value=50):
            state,result=self.act(state,'fair_xs',price=500)
        self.assertEqual(result['fair']['prize'],25000)
        self.assertEqual(result['fair']['wealth_raid']['amount'],10350)
        self.assertEqual(state['journey']['fair']['net'],fh.NET_SAFE-1000+24500-10350)
        validate_state(state)
        with self.assertRaises(GameError):self.act(state,'fair_xs',price=2)
        state=story(10000)
        state['journey']['fair']=dict(fh.initial(), date=fh.vn_date(self.clock.t), net=-999499)
        self.dice(Dice(draws=[0]))
        state,result=self.act(state,'fair_xd',side='chan',stake=500)
        self.assertEqual(state['journey']['fair']['net'],-1000124)
        validate_state(state)

    def test_pending_knife_prize_crosses_old_bound_once(self):
        state,_=self.act(story(10000),'fair_kn_start',stake=500)
        run=state['journey']['fair_kn']['run']
        run.update(sg='choice',lv=9,day=fh.vn_date(self.clock.t))
        state['journey']['fair']['net']=999999
        state,result=self.act(state,'fair_kn_stop')
        self.assertEqual(result['fair']['prize'],kn.prize(500,9))   # 3900 on the ladder, no cap since 09/10
        self.assertEqual(state['journey']['fair']['net'],999999+kn.prize(500,9))
        validate_state(state)
        wallet=state['journey']['wallet']
        state,result=self.act(state,'fair_kn_stop')
        self.assertTrue(result['fair']['again']);self.assertEqual(state['journey']['wallet'],wallet)

    def test_new_knife_gentler_board_old_active_keeps_old_schedule(self):
        state, result = self.act(story(1000), 'fair_kn_start', stake=500)
        board = result['fair']['run']['board']
        run = state['journey']['fair_kn']['run']
        legacy = kn.schedule(run['sd'], run['lv'], run['hot'])
        soft = kn.SOFT_DIFFICULTY   # levels started since 06/10 use the softer board (WP6), not 135%
        self.assertEqual(board['need'], (legacy['need']*soft+99)//100)
        # since 09/10 the twist board (faster, telegraphed turn-backs), with the soft board's knives
        self.assertEqual(board['segs'], kn.twist_schedule(run['sd'], run['lv'], run['hot'])['segs'])
        self.assertFalse(board.get('chance', False))
        self.assertEqual(state['journey'].pop('fair_kn_skill')['difficulty'], 135)
        state['journey'].pop('fair_kn_soft', None)   # a level started by an older worker carries no marker
        state['journey'].pop(fh.KN_TWIST_KEY, None)
        state = copy.deepcopy(state)
        self.assertEqual(public_state(state)['fair']['knife']['run']['board']['need'], legacy['need'])
        self.dice(Dice(draws=[.1]))
        taps = safe_taps(legacy, legacy['need'])
        self.clock.t += taps[-1] / 1000
        state, result = self.act(state, 'fair_kn_throw', lv=1, taps=taps)
        self.assertTrue(result['fair']['cleared'])
        state, result = self.act(state, 'fair_kn_next')
        nxt = state['journey']['fair_kn']['run']
        self.assertEqual(result['fair']['run']['board']['need'], fh._kn_sched(nxt, state['journey'])['need'])
        validate_state(state)

    def test_new_knife_partial_10_tap_save_validates_and_finishes(self):
        state, result = self.act(story(1000), 'fair_kn_start', stake=500)
        legacy = kn.schedule(state['journey']['fair_kn']['run']['sd'], 1, state['journey']['fair_kn']['run']['hot'])
        self.assertEqual(result['fair']['run']['board']['need'], (legacy['need']*kn.SOFT_DIFFICULTY+99)//100)
        sc = fh._kn_sched(state['journey']['fair_kn']['run'], state['journey'])
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        state, _ = self.act(state, 'fair_kn_throw', lv=1, taps=taps[:sc['need'] - 1])   # one short of clearing
        validate_state(copy.deepcopy(state))
        self.dice(Dice(draws=[.1]))
        state, result = self.act(state, 'fair_kn_throw', lv=1, taps=taps)
        self.assertTrue(result['fair']['cleared'])
        state, result = self.act(state, 'fair_kn_next')
        nxt = state['journey']['fair_kn']['run']
        self.assertEqual(result['fair']['run']['board']['need'], fh._kn_sched(nxt, state['journey'])['need'])
        self.assertEqual(state['journey']['fair_kn_skill']['difficulty'], 135)   # what an older worker validates

    def test_each_paid_game_accepts_500_and_roundtrips(self):
        for name, payload in [('fair_bc', {'bets': {'bau': 300, 'cua': 200}}),
                              ('fair_xd', {'side': 'chan', 'stake': 500}),
                              ('fair_kn_start', {'stake': 500}),
                              ('fair_xs', {'price': 500}),
                              ('fair_loto_buy', {'tier': 'dac_biet', 'n': 1})]:
            with self.subTest(name=name):
                self.dice(random.Random(41))
                state, _ = self.act(story(10000), name, **payload)
                validate_state(copy.deepcopy(state))

    def test_big_stakes_are_taken_and_invalid_ones_refused(self):
        # owner 08/10 "mn đặt cược bao nhiêu thoải mái nhé": no per-round maximum on bầu cua and chiếu trong
        self.dice(random.Random(5))
        for name, payload in [('fair_bc', {'bets': {'bau': 3000, 'cua': 2001}}),
                              ('fair_xd', {'side': 'chan', 'stake': 50001}),
                              ('fair_loto_buy', {'tier': 'dac_biet', 'n': 2})]:   # 1000: what a saved round holds
            with self.subTest(name=name):
                state, _ = self.act(story(10**5), name, **payload)
                validate_state(state)
        for name, payload in [('fair_bc', {'bets': {'bau': 0}}), ('fair_bc', {'bets': {'bau': 1.5}}),
                              ('fair_bc', {'bets': {'bau': fh.STAKE_MAX + 1}}),
                              ('fair_xd', {'side': 'chan', 'stake': fh.XD_MIN - 1}),
                              ('fair_xd', {'side': 'chan', 'stake': '50'}),
                              ('fair_xd', {'side': 'chan', 'stake': 2000}),      # more than the wallet
                              ('fair_kn_start', {'stake': 501}),               # the knife's menu (its stake is saved)
                              ('fair_xs', {'price': 501}),                     # the scratch cards' prices
                              ('fair_loto_buy', {'tier': 'nghin', 'n': 2})]:   # past what a saved round holds
            with self.subTest(name=name, payload=payload), self.assertRaises(GameError):
                self.act(story(1000), name, **payload)

    @patch.object(fh, 'SIDE_OPEN', True)   # closed since 08/10; rounds bought before still validate
    def test_loto_combined_budget_and_saved_validation(self):
        state, result = self.act(story(10000), 'fair_loto_buy', tier='cao', n=2, cl=['chan', 100])
        self.assertEqual(result['fair']['cost'], 500)
        validate_state(state)
        state['journey']['fair']['loto']['tier'] = 'nghin'   # 2 × 1000 + 100: past what a saved round holds
        with self.assertRaises(GameError): validate_state(state)

    def test_old_stakes_remain_supported_and_prizes_scale(self):
        self.assertTrue({2, 5, 10, 20, 50, 100, 200, 500} <= set(kn.STAKES))
        self.assertTrue({2, 5, 10, 20, 50, 100, 200, 500} <= set(xs.TIERS))
        self.assertEqual(kn.prize(500, 10), kn.prize(10, 10)*50)
        self.assertEqual(set(xs.NAMES), set(xs.TIERS))

    def test_raid_increases_ten_percent_relative_only_on_chieu(self):
        self.assertAlmostEqual(fh.RAID_PCT, .88)   # 07/10: half of 1.76%
        for draw, raid in [(.008799, True), (.0088, False)]:
            self.dice(Dice(draws=[draw, .1]))
            _, result = self.act(story(1000), 'fair_xd', side='chan', stake=500)
            self.assertEqual(result['fair']['raid'], raid)
