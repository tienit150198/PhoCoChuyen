"""The two golden days use one persisted clock and never publish their draw rate."""
import contextvars
import json
import random
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from game import fair as fh
from game import fair_golden_days as golden
from game import fair_scratch as scratch
from game import engine
from game.storage import Store
from tests.test_fair import OPEN, Dice, FairBase, StoreBase, marks_for, story
from tests.test_fair_scratch import Draws


EVENT_KEY = 'fair_golden_days_20261011'


class GoldenDays(StoreBase):
    def setUp(self):
        super().setUp()
        golden.clear()
        self.addCleanup(golden.clear)

    def activate(self, at=int(OPEN)):
        with self.store.connect() as db:
            return golden.activate(db, at=at)

    def test_persisted_activation_boosts_each_eligible_paid_stall(self):
        with self.store.connect() as db:
            db.execute('INSERT INTO mnl_meta (key, value) VALUES (?, ?)', (EVENT_KEY, str(int(OPEN))))
        for game, action in [('xd', 'fair_xd'), ('lt', 'fair_loto_buy'), ('xs', 'fair_xs')]:
            with self.subTest(game=game), self.store.connect() as db:
                fh.loc_prepare(db, action)
                self.assertEqual(fh.luck_p({}, None, game, OPEN + 30, stake=10), .70)

    def test_activation_is_exactly_48_hours_and_retry_never_renews(self):
        first = self.activate()
        self.assertTrue(first['created'])
        self.assertEqual(first['ends'] - first['starts'], 48 * 3600)
        with self.store.connect() as db:
            for t, active in [(OPEN - .001, False), (OPEN, True),
                              (first['ends'] - .001, True), (first['ends'], False)]:
                self.assertIs(golden.status(db, at=t)['active'], active)
        replay = self.activate(first['ends'] + 100)
        self.assertFalse(replay['created'])
        self.assertFalse(replay['active'])
        self.assertEqual((replay['starts'], replay['ends']), (first['starts'], first['ends']))
        self.assertNotIn('70', first['title'])
        self.assertEqual(set(first), {'id', 'title', 'active', 'starts', 'ends', 'created'})

    def test_default_activation_uses_database_clock_and_status_does_not_activate(self):
        with self.store.connect() as db:
            self.assertIsNone(golden.status(db)['starts'])
            before = golden._now(db)
            event = golden.activate(db)
            after = golden._now(db)
            self.assertLessEqual(before, event['starts'])
            self.assertLessEqual(event['starts'], after)
            self.assertTrue(event['active'])
            self.assertEqual(event['ends'] - event['starts'], golden.DURATION)

    def test_concurrent_activations_choose_one_immutable_window(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.activate, (int(OPEN), int(OPEN) + 30)))
        self.assertEqual(sum(r['created'] for r in results), 1)
        self.assertEqual(results[0]['starts'], results[1]['starts'])
        self.assertEqual(results[0]['ends'], results[1]['ends'])

    def test_new_worker_and_store_reload_read_the_same_window_without_cache(self):
        def draw_in_worker(store, t):
            with store.connect() as db:
                fh.loc_prepare(db, 'fair_xs')
            return fh.luck_p({}, None, 'xs', t, stake=10)
        worker = contextvars.Context()
        self.assertEqual(worker.run(draw_in_worker, self.store, OPEN), fh.BASES['xs'])
        event = self.activate()
        self.assertEqual(worker.run(draw_in_worker, self.store, OPEN + 1), golden.WIN_P)
        restarted = Store(self.store.path, story=True)
        self.addCleanup(restarted.close_pool)
        fresh_worker = contextvars.Context()
        self.assertEqual(fresh_worker.run(draw_in_worker, restarted, OPEN + 2), golden.WIN_P)
        self.assertEqual(fresh_worker.run(draw_in_worker, restarted, event['ends']), fh.BASES['xs'])

    def test_request_context_clears_for_other_commands_missing_rows_and_bad_rows(self):
        self.activate()
        with self.store.connect() as db:
            fh.loc_prepare(db, 'fair_xs')
            self.assertTrue(golden.active('xs', OPEN))
            fh.loc_prepare(db, 'jr_wait')
            self.assertFalse(golden.active('xs', OPEN))
            fh.loc_prepare(db, 'fair_xs')
            db.execute('UPDATE mnl_meta SET value=? WHERE key=?', ('invalid', golden.KEY))
            fh.loc_prepare(db, 'fair_xs')
            self.assertFalse(golden.active('xs', OPEN))
            with self.assertRaises(ValueError):
                golden.activate(db, at=int(OPEN))
            db.execute('DELETE FROM mnl_meta WHERE key=?', (golden.KEY,))
            fh.loc_prepare(db, 'fair_xs')
            self.assertFalse(golden.active('xs', OPEN))

    def test_replayed_event_ticket_keeps_result_after_expiry_and_is_not_paid_twice(self):
        event = self.activate()
        token = self.player('Lan', wallet=1000)
        revision = self.store.read(token)[1]
        args = (token, 'golden-ticket-retry-01', revision, None, 'fair_xs', dict(price=10))
        self.dice(Draws([.69]))
        first = self.store.command(*args)
        self.assertGreater(first['result']['fair']['net'], 0)
        wallet = self.store.read(token)[0]['journey']['wallet']
        self.clock.t = event['ends'] + 1
        self.dice(Draws([.99]))
        replay = self.store.command(*args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['result'], first['result'])
        self.assertEqual(self.store.read(token)[0]['journey']['wallet'], wallet)
        self.dice(Draws([.69]))
        ordinary = self.cmd(token, 'fair_xs', dict(price=10))
        self.assertEqual(ordinary['result']['fair']['net'], -10)


class GoldenDraws(FairBase):
    def setUp(self):
        super().setUp()
        golden.clear()
        self.addCleanup(golden.clear)
        golden._starts.set(int(OPEN))

    def test_draw_boundary_and_long_runs_stay_at_event_rate(self):
        for game in golden.GAMES:
            j = dict(fair_balance={game: fh.STREAK})
            for n in range(100):
                p = fh.luck_p(j, None, game, OPEN + n, stake=10)
                self.assertEqual(p, golden.WIN_P)
                with mock.patch.object(fh, '_rng', Dice(draws=[.699999, .70])):
                    self.assertTrue(fh._draw_luck(j, game, p))
                    self.assertFalse(fh._draw_luck(j, game, p))
            self.assertEqual(j[fh.COOL_KEY][game]['n'], 100)

    def test_start_and_end_are_checked_at_the_actual_draw(self):
        for game in golden.GAMES:
            for t, expected in [(OPEN - .001, fh.BASES[game]), (OPEN, golden.WIN_P),
                                (OPEN + golden.DURATION - .001, golden.WIN_P),
                                (OPEN + golden.DURATION, fh.BASES[game])]:
                self.assertEqual(fh.luck_p({}, None, game, t, stake=10), expected)

    def test_forged_display_marker_never_authorizes_a_boost(self):
        golden.clear()
        j = {golden.DISPLAY_KEY: dict(id=golden.KEY, starts=int(OPEN))}
        self.assertEqual(fh.luck_p(j, None, 'xs', OPEN + 1, stake=10), fh.BASES['xs'])

    def test_absent_event_retains_ordinary_streak_decay_and_refund_prizes(self):
        golden.clear()
        j = dict(fair_balance={'xs': fh.STREAK})
        p = fh.luck_p(j, None, 'xs', OPEN, stake=10)
        self.assertEqual(p, fh.BASES['xs'])
        self.dice(Dice(draws=[fh.WIN_P_LOW]))
        self.assertFalse(fh._draw_luck(j, 'xs', p))
        for n in range(100):
            p = fh.luck_p(j, None, 'xs', OPEN + n, stake=10)
        self.assertEqual(p, fh.P_FLOOR)
        self.assertEqual(scratch.prize_mult(Dice(coins=[0])), 1)

    def test_ineligible_games_keep_normal_rules(self):
        for game in ('bc', 'dg', 'ring', 'kn', 'oaq'):
            self.assertFalse(golden.active(game, OPEN))
        for game in ('bc', 'ring'):
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=10), fh.chance_rate(game, OPEN))
        self.dice(Dice(faces=['ga'] * 3, draws=[.1]))
        _, result = self.act(story(100), 'fair_bc', bets={'cua': 10})
        self.assertLess(result['fair']['net'], 0)
        s, result = self.act(story(100), 'fair_kn_start', stake=10)
        self.assertFalse(result['fair']['run']['chance'])
        self.assertNotIn('kn', s['journey'].get('fair_chance', {}))

    def test_scratch_event_winners_have_positive_net_and_matching_visible_cells(self):
        for price in scratch.TIERS:
            for draw, won in [(.699999, True), (.70, False)]:
                self.dice(Draws([draw], seed=price))
                s, result = self.act(story(100000), 'fair_xs', price=price)
                ticket = result['fair']
                self.assertEqual(ticket['net'] > 0, won)
                self.assertEqual(scratch.read(ticket['cells']), ticket['prize'])
                self.assertEqual(s['journey']['wallet'], 100000 + ticket['net'])
                if won:
                    self.assertGreaterEqual(ticket['mult'], 2)
                engine.validate_state(s)

    def test_seeded_distribution_is_near_target_including_positive_net_scratch_prizes(self):
        count = 30000
        for game in golden.GAMES:
            self.dice(random.Random(1711))
            j, wins = {}, 0
            for i in range(count):
                p = fh.luck_p(j, None, game, OPEN + i / 100, stake=10)
                won = fh._draw_luck(j, game, p)
                if game == 'xs' and won:
                    self.assertGreater(scratch.prize_mult(fh._rng, profit_only=True), 1)
                wins += won
            self.assertAlmostEqual(wins / count, golden.WIN_P, delta=.012, msg=game)

    def test_xd_keeps_raid_rule_and_result_coins_match_paid_win(self):
        for draws, expected in [([.99, .699999], True), ([.99, .70], False)]:
            self.dice(Dice(draws=draws))
            _, result = self.act(story(100), 'fair_xd', side='chan', stake=10)
            out = result['fair']
            self.assertEqual(out['net'] > 0, expected)
            self.assertEqual(sum(out['coins']) % 2 == 0, expected)
        self.dice(Dice(draws=[0]))
        _, result = self.act(story(100), 'fair_xd', side='chan', stake=10)
        self.assertTrue(result['fair']['raid'])

    def test_loto_bought_before_expiry_keeps_winning_cards_and_claim_rules_after_expiry(self):
        self.clock.t = OPEN + golden.DURATION - 10
        self.dice(Draws([.699999], seed=83))
        s, _ = self.act(story(1000), 'fair_loto_buy')
        lt = s['journey']['fair']['loto']
        rv = fh.round_view(lt)
        self.assertLess(rv['mine'], rv['npc_done'])
        self.assertGreater(rv['prize'], rv['price'] * rv['n'])
        self.clock.t = OPEN + golden.DURATION + 1
        golden.clear()
        s = json.loads(json.dumps(s))
        self.assertEqual(fh.round_view(s['journey']['fair']['loto']), rv)
        s, result = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=marks_for(rv, 0, rv['mine']))
        self.assertTrue(result['fair']['won'])
        self.assertGreater(s['journey']['wallet'], 1000)
        engine.validate_state(s)

    def test_public_hint_has_no_probability_and_reload_hides_cold_hint_until_expiry(self):
        j = story()['journey']
        end = OPEN + golden.DURATION
        for n in range(40):
            fh.luck_p(j, None, 'xs', end - 100 + n, stake=10)
        j = json.loads(json.dumps(j))
        golden.clear()  # a public read on another worker has no command context
        self.assertIsNone(fh.cold(j, end - 1))
        self.assertEqual(fh.cold(j, end)['game'], 'xs')
        self.assertIsNone(golden.public(j, end))
        shown = golden.public(j, end - 1)
        self.assertEqual(set(shown), {'title', 'starts', 'ends', 'games'})
        self.assertEqual(shown['title'], golden.TITLE)
        self.assertNotIn('70', shown['title'])
        self.assertNotIn('%', shown['title'])
        self.assertEqual(shown['ends'] - shown['starts'], golden.DURATION)
        self.clock.t = end - 20
        s = story()
        s['journey'] = j
        public = engine.public_state(s)['fair']
        self.assertEqual(public['golden_days'], shown)
        self.assertIsNone(public['cool'])
        self.assertFalse({'luck_pct', 'win_p', 'odds', 'probability'} & set(public['rules']))
