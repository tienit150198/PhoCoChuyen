"""Owner 05/10: one repetition floor, 20% fewer raids. Owner 07/10: 50% won rounds, a long run of one stall cools to
40% (bầu cua exempt: honest dice)."""
import unittest

from game import fair as fh
from game import fair_scratch as xs
from game import fair_knife as kn
from game.engine import GameError, public_state, validate_state
from tests.test_fair import OPEN, Dice, FairBase, StoreBase, story
from tests.test_fair_knife import safe_taps, crash_tap


class EventOdds(unittest.TestCase):
    def test_each_chance_stall_starts_at_requested_rate(self):
        for game in fh.CHANCE_GAMES:   # owner 08/10: each stall's fresh draw (BASES), below what breaks even
            with self.subTest(game=game):
                self.assertAlmostEqual(fh.luck_p({}, None, game, OPEN), fh.BASES.get(game, fh.LUCK_BASE))
        self.assertEqual((xs.P_HI, xs.P_LO), (fh.BASES['xs'], fh.BASES['xs']))

    def test_repetition_cools_every_luck_stall_but_bau_cua(self):
        for game in fh.CHANCE_GAMES:
            j = {}
            rates = [fh.luck_p(j, None, game, OPEN + i * 5) for i in range(100)]
            base = fh.chance_rate(game, OPEN)
            if game == 'bc':   # honest dice: exempt
                self.assertEqual(set(rates), {base})
                continue
            floor = fh.XD_FLOOR if game == 'xd' else fh.P_FLOOR
            self.assertEqual(rates[:fh.RUN_FREE], [base] * fh.RUN_FREE)
            self.assertAlmostEqual(rates[fh.RUN_FREE], base - fh.RUN_STEP)
            self.assertEqual(rates, sorted(rates, reverse=True))
            self.assertEqual(rates[30:], [floor] * 70)

    def test_switch_or_break_resets_run(self):
        j = {}
        for i in range(40):
            fh.luck_p(j, None, 'bc', OPEN + i)
        self.assertEqual(fh.luck_p(j, None, 'lt', OPEN + 40), fh.chance_rate('lt', OPEN + 40))
        self.assertEqual(fh.luck_p(j, None, 'bc', OPEN + 41), fh.chance_rate('bc', OPEN + 41))
        for i in range(40):
            fh.luck_p(j, None, 'bc', OPEN + 42 + i)
        self.assertEqual(fh.luck_p(j, None, 'bc', OPEN + 82 + 181), fh.chance_rate('bc', OPEN + 263))

    def test_profit_does_not_matter_and_spam_never_breaches_the_floor(self):
        f = dict(fh.initial(), date=fh.vn_date(OPEN), net=100000)
        for game in fh.CHANCE_GAMES:
            j = {}
            rates = [fh.luck_p(j, f, game, OPEN + i) for i in range(300)]
            self.assertTrue(all(p >= fh.P_FLOOR for p in rates))
            self.assertEqual(rates[0], fh.chance_rate(game, OPEN))


class RaidOdds(FairBase):
    def test_raid_rate_increases_ten_percent_from_previous_1_6_percent(self):
        self.assertAlmostEqual(fh.RAID_PCT, .88)   # 07/10: half of 1.76%
        for draw, expected in [(.008799, True), (.0088, False), (.0176, False)]:
            with self.subTest(draw=draw):
                self.dice(Dice(draws=[draw, .1]))
                _, result = self.act(story(100), 'fair_xd', side='chan', stake=10)
                self.assertEqual(result['fair']['raid'], expected)


class ServerDecides(FairBase):
    def test_old_chance_knife_finishes_without_a_random_collision(self):
        for draw in (.699999, .70, .999999):
            s, result = self.act(story(100), 'fair_kn_start', stake=10)
            s['journey'].pop('fair_kn_skill')
            fh._set_chance(s['journey'], 'kn', s['journey']['fair_kn']['run'], .70)
            s['journey']['fair_chance']['kn']['difficulty'] = 135
            count = result['fair']['run']['board']['need']
            self.dice(Dice(draws=[draw]))
            taps = list(range(0, count * kn.MIN_TAP, kn.MIN_TAP))
            s, partial = self.act(s, 'fair_kn_throw', lv=1, taps=taps[:2])
            self.assertEqual(partial['fair']['run']['stage'], 'play')
            s, result = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
            self.assertTrue(result['fair'].get('cleared', False))
            self.assertFalse(result['fair'].get('lost', False))
            validate_state(s)
            with self.assertRaises(GameError):
                self.act(s, 'fair_kn_throw', lv=1, taps=taps)

    def test_ring_win_means_at_least_one_prize_and_loss_means_zero(self):
        p = fh.chance_rate('ring', OPEN)
        for draw, won in [(p - .000001, True), (p, False)]:
            s, result = self.act(story(100), 'fair_ring_start')
            self.assertTrue(result['fair']['round']['chance'])
            self.dice(Dice(draws=[draw]))
            s, result = self.act(s, 'fair_ring_throw', id=result['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
            self.assertEqual(result['fair']['prize'] > 0, won)
            self.assertEqual(result['fair']['n'] > 0, won)
            self.assertEqual(s['journey']['fair_run3']['n'], 1)
            validate_state(s)

    def test_skill_knife_counts_purchases_without_reducing_odds(self):
        s = story(1000)
        for i in range(26):
            self.dice(Dice(draws=[.99]))
            s, result = self.act(s, 'fair_kn_start', stake=2)
            self.assertFalse(result['fair']['run']['chance'])
            self.assertNotIn('kn', s['journey'].get('fair_chance', {}))
            sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
            taps = safe_taps(sc, 2)
            s, _ = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
            self.assertEqual(s['journey']['fair_kn']['n'], i + 1)
            taps.append(crash_tap(sc, taps))
            self.clock.t += taps[-1] / 1000
            s, result = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
            self.assertTrue(result['fair']['lost'])
        self.assertEqual(s['journey']['fair_kn']['n'], 26)
        validate_state(s)

    def test_knife_next_keeps_skill_rules_and_does_not_count_a_new_purchase(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=2)
        sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        s, _ = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
        s, result = self.act(s, 'fair_kn_next')
        self.assertFalse(result['fair']['run']['chance'])
        self.assertEqual(s['journey']['fair_kn']['n'], 1)
        self.assertNotIn('kn', s['journey'].get('fair_chance', {}))
        self.assertEqual(s['journey']['fair_kn_skill']['difficulty'], 135)
        validate_state(s)

    def test_old_round_without_chance_metadata_stays_skill_based(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=2)
        s['journey'].pop('fair_kn_skill')
        self.assertFalse(public_state(s)['fair']['knife']['run']['board'].get('chance', False))
        validate_state(s)

    def test_ring_spam_metadata_survives_reload_and_cannot_go_below_floor(self):
        import json
        s = story(100)
        for i in range(50):
            s, _ = self.act(s, 'fair_ring_start')
            s = json.loads(json.dumps(s))
            p = s['journey']['fair_chance']['ring']['p']
            self.assertEqual(p, round(fh.run_rate('ring', i + 1) * 1000))   # 07/10: 503 cooling to 400, within the older validator's 400..700
            self.assertTrue(400 <= p <= 700)
            validate_state(s)
        self.assertEqual(p, 400)
        self.assertTrue(public_state(s)['fair']['ring']['chance'])

    def test_raid_round_also_counts_in_repetition(self):
        self.dice(Dice(draws=[.001]))
        s, _ = self.act(story(100), 'fair_xd', side='chan', stake=10)
        self.assertEqual(s['journey']['fair_run']['n'], 1)

    def test_switching_to_o_an_quan_keeps_the_spam_decay(self):
        s, _ = self.act(story(100), 'fair_ring_start')
        s, _ = self.act(s, 'fair_oaq_start', lv='kho')
        self.assertNotIn('fair_run3', s['journey'])                   # the older run key only (07/10)
        self.assertEqual(s['journey'][fh.COOL_KEY]['ring']['n'], 1)
        self.assertEqual(s['journey']['fair']['oaq']['lv'], 'kho')


class ChanceIdempotency(StoreBase):
    def test_retrying_completed_ring_does_not_draw_or_pay_twice(self):
        tok = self.player('Lan')
        start = self.cmd(tok, 'fair_ring_start', {})
        rid = start['result']['fair']['round']['id']
        self.dice(Dice(draws=[.1], coins=[4, 0, 1, 2, 3, 4]))
        rev = self.store.read(tok)[1]
        args = (tok, 'ring-chance-retry-01', rev, None, 'fair_ring_throw', dict(id=rid, taps=[0, 300, 600, 900, 1200]))
        first = self.store.command(*args)
        wallet = self.store.read(tok)[0]['journey']['wallet']
        streak = dict(self.store.read(tok)[0]['journey']['fair_balance'])
        self.dice(Dice(draws=[.99]))
        replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        self.assertEqual(wallet, self.store.read(tok)[0]['journey']['wallet'])
        self.assertEqual(first['result']['fair']['prize'], 23)
        self.assertEqual(self.store.read(tok)[0]['journey']['fair_balance'], streak)

    def test_retrying_skill_knife_does_not_change_win_or_pay_twice(self):
        tok = self.player('Lan')
        start = self.cmd(tok, 'fair_kn_start', dict(stake=10))
        state = self.store.read(tok)[0]
        sc = fh._kn_sched(state['journey']['fair_kn']['run'], state['journey'])
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        rev = self.store.read(tok)[1]
        args = (tok, 'knife-skill-retry-01', rev, None, 'fair_kn_throw', dict(lv=1, taps=taps))
        first = self.store.command(*args)
        self.dice(Dice(draws=[.99]))
        replay = self.store.command(*args)
        self.assertTrue(first['result']['fair']['cleared'])
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['result'], replay['result'])
        self.cmd(tok, 'fair_kn_stop', {})
        wallet = self.store.read(tok)[0]['journey']['wallet']
        self.cmd(tok, 'fair_kn_stop', {})
        self.assertEqual(self.store.read(tok)[0]['journey']['wallet'], wallet)
