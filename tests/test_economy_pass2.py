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
        state['journey']['fair']=dict(fh.initial(), date=fh.vn_date(self.clock.t), net=999000)
        self.dice(random.Random(11))   # 07/10: a seed whose raid draw is under WEALTH_RAID_P .35 (seed 1's .445 was under .70)
        with patch.object(xs, 'prize_mult', return_value=50):
            state,result=self.act(state,'fair_xs',price=500)
        self.assertEqual(result['fair']['prize'],25000)
        self.assertEqual(result['fair']['wealth_raid']['amount'],10350)
        self.assertEqual(state['journey']['fair']['net'],1023500-10350)
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
        self.assertEqual(result['fair']['prize'],3900)
        self.assertEqual(state['journey']['fair']['net'],1003899)
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
        self.assertEqual(board['segs'], [[ms,speed*(soft/100),ramp] for ms,speed,ramp in legacy['segs']])
        self.assertFalse(board.get('chance', False))
        self.assertEqual(state['journey'].pop('fair_kn_skill')['difficulty'], 135)
        state['journey'].pop('fair_kn_soft', None)   # a level started by an older worker carries neither marker
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

    def test_over_500_is_rejected_for_every_paid_game(self):
        for name, payload in [('fair_bc', {'bets': {'bau': 300, 'cua': 201}}),
                              ('fair_xd', {'side': 'chan', 'stake': 501}),
                              ('fair_kn_start', {'stake': 501}),
                              ('fair_xs', {'price': 501}),
                              ('fair_loto_buy', {'tier': 'dac_biet', 'n': 2}),
                              ('fair_loto_buy', {'tier': 'dac_biet', 'n': 1, 'cl': ['chan', 2]})]:
            with self.subTest(name=name), self.assertRaises(GameError):
                self.act(story(10000), name, **payload)

    def test_loto_combined_budget_and_saved_validation(self):
        state, result = self.act(story(10000), 'fair_loto_buy', tier='cao', n=2, cl=['chan', 100])
        self.assertEqual(result['fair']['cost'], 500)
        validate_state(state)
        state['journey']['fair']['loto']['sb']['cot'] = [0, 2]
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
