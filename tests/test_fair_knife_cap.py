"""🗡️ Phóng dao's silent daily cap (owner 08/10 "đảm bảo nhà cái luôn thắng", "k báo ... số liệu k hiển thị ra"): a
scripted perfect thumb nets at most fair.KN_DAY_CAP xu a Vietnam day from the stall, whatever it stakes and wherever
it stops. Nothing tells the player: the stall keeps taking stakes, the prizes shown are the ladder's, no message or
public field mentions a cap; a level whose clearing would pay past it starts on the hardest board and its clearing
throw glances off. The tally rides in the legacy 'dpts' within the bound older servers check."""
import json
import random
import unittest

from game import fair as fh
from game import fair_knife as kn
from game.engine import public_state, validate_state

from tests.test_fair import FairBase, story
from tests import test_fair_knife as tk


class Cap(FairBase):
    start, board, clear, lose = tk.Knife.start, tk.Knife.board, tk.Knife.clear, tk.Knife.lose   # its helpers, not its tests

    def setUp(self):
        super().setUp()
        self.dice(random.Random(20261008))
        self.messages = []

    def act(self, s, action, **p):
        s, r = super().act(s, action, **p)
        self.messages.append(r.get('message') or '')
        return s, r

    def perfect_run(self, s, stake, stop):
        """Start at `stake`, throw every level clean up to `stop`, take the prize; returns (s, paid): 0 when a clean
        throw glanced off."""
        s, r = self.start(s, stake)
        for lv in range(1, stop + 1):
            s, r = self.clear(s)
            x = r['fair']
            if x.get('lost'):
                self.assertEqual(x['hit'], len(x['stuck']))              # the clearing throw, after the clean ones
                return s, 0
            run = x['run']
            if 'win' in run:                                             # the ladder's prize, never a capped one
                bn = s['journey']['fair_kn']['run']['bn'] + (kn.x2_bonus(stake, lv + 1) if run['nx'] else 0)
                self.assertEqual(run['win'], kn.prize(stake, lv + 1, bn))
            if lv < stop:
                s, r = self.act(s, 'fair_kn_next')
        if r['fair'].get('all'):
            return s, r['fair']['paid']
        s, r = self.act(s, 'fair_kn_stop')
        return s, r['fair']['prize']

    def day_net(self, s, rng, runs=60):
        """A perfect player stakes and stops at random all day; returns (s, net)."""
        net = 0
        for _ in range(runs):
            stake = rng.choice(kn.STAKES[:7])
            s, paid = self.perfect_run(s, stake, rng.randint(1, kn.LEVELS))
            net += paid - stake
            self.assertLessEqual(net, fh.KN_DAY_CAP)
            self.clock.t += 1
        return s, net

    def assert_silent(self, s):
        v = public_state(s)['fair']
        text = json.dumps(v, ensure_ascii=False)
        for word in ('cap_left', 'KN_DAY', 'luck_pct', 'cooled_pct', 'floor_pct', '"luck"'):
            self.assertNotIn(word, text)
        self.assertNotIn('cap', v['knife'])
        for m in self.messages:
            self.assertNotIn('thắng đủ', m)
            self.assertNotIn(str(fh.KN_DAY_CAP), m)

    def test_the_cap_is_three_hundred_xu_within_the_old_bound(self):
        self.assertEqual(fh.KN_DAY_CAP, 300)
        self.assertEqual(fh.KN_DAY_CAP, fh.KN_CAP_UNIT * fh.POINTS_DAY)   # dpts <= POINTS_DAY, as 1.9.21 checks

    def test_a_scripted_perfect_player_nets_no_more_than_the_cap_a_day(self):
        rng = random.Random(8)
        s = story(10**6)
        total = 0
        for day in range(3):
            s, net = self.day_net(s, rng)
            self.assertLessEqual(net, fh.KN_DAY_CAP)
            validate_state(s)
            total += net
            self.clock.t += 86400                                        # the next Vietnam day: a fresh cap
            self.assertEqual(fh.kn_cap_left(s['journey']['fair'], self.clock.t), fh.KN_DAY_CAP)
        self.assertLessEqual(total, 3 * fh.KN_DAY_CAP)
        self.assert_silent(s)

    def test_a_player_who_stops_just_in_time_reaches_the_cap_and_no_more(self):
        s = story(10**5)
        paid_runs = []
        for _ in range(40):                                              # +10 a run: level 1 at 100 xu
            s, paid = self.perfect_run(s, 100, 1)
            paid_runs.append(paid)
        self.assertEqual(paid_runs, [110] * 30 + [0] * 10)              # 30 wins of 10 = the cap, then glanced off
        self.assertEqual(s['journey']['fair']['dpts'], fh.POINTS_DAY)
        s, r = self.start(s, 5)                                          # the stall still takes stakes
        self.assertEqual(r['fair']['run']['stage'], 'play')
        self.assertEqual(s['journey']['fair_kn']['run']['hot'], kn.HEAT_MAX)   # on its hardest board
        self.assertEqual(r['fair']['run']['win'], kn.prize(5, 1))        # the ladder's prize (6), as always
        s, r = self.clear(s)
        self.assertTrue(r['fair']['lost'])
        self.assert_silent(s)
        validate_state(s)

    def test_the_top_stake_cannot_pass_the_cap(self):
        s = story(5000)
        s, r = self.start(s, 1000)
        self.assertLess(s['journey']['fair_kn']['run']['hot'], kn.HEAT_MAX)   # 1100: 100 over the stake
        s, r = self.clear(s)
        s['journey']['fair_kn']['run']['nx'] = 0                         # (no x2 level in this test)
        s, r = self.act(s, 'fair_kn_next')
        self.assertLess(s['journey']['fair_kn']['run']['hot'], kn.HEAT_MAX)   # 1200: 200 over
        s, r = self.clear(s)
        self.assertEqual(r['fair']['run']['prize'], kn.prize(1000, 2))
        s['journey']['fair_kn']['run']['nx'] = 0
        s, r = self.act(s, 'fair_kn_next')
        self.assertEqual(s['journey']['fair_kn']['run']['hot'], kn.HEAT_MAX)  # 1600: past the cap
        self.assertEqual(r['fair']['run']['win'], kn.prize(1000, 3))
        s, r = self.clear(s)                                             # every throw clean: the last glances off
        self.assertTrue(r['fair']['lost'])
        self.assertEqual(r['message'], 'Dao chạm dao rồi! Lượt này thua hết.')
        self.assertEqual(s['journey']['wallet'], 4000)
        self.assert_silent(s)

    def test_small_wins_count_rounded_up_and_losses_give_nothing_back(self):
        s = story(1000)
        s, paid = self.perfect_run(s, 5, 1)                             # +1 xu counts 10
        self.assertEqual((paid, s['journey']['fair']['dpts']), (kn.prize(5, 1), 1))
        self.assertEqual(fh.kn_cap_left(s['journey']['fair'], self.clock.t), fh.KN_DAY_CAP - 10)
        s, _ = self.start(s, 50)
        s, _ = self.lose(s)
        self.assertEqual(s['journey']['fair']['dpts'], 1)
        s, paid = self.perfect_run(s, 10, 1)
        self.assertEqual(s['journey']['fair']['dpts'], 1 + (kn.prize(10, 1) - 10 + 9) // 10)

    def test_a_choice_left_overnight_is_paid_under_the_next_days_cap(self):
        s = story(5000)
        s, _ = self.start(s, 100)
        for lv in range(1, 6):
            s, r = self.clear(s)
            self.assertFalse(r['fair'].get('lost'))
            if lv < 5:
                s, _ = self.act(s, 'fair_kn_next')
        shown = r['fair']['run']['prize']
        self.assertLessEqual(shown - 100, fh.KN_DAY_CAP)
        s['journey']['fair']['dpts'] = fh.POINTS_DAY                     # (as if the rest of the day was won elsewhere)
        self.clock.t += 86400                                            # left as a choice into the next day
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(r['fair']['prize'], shown)                      # the next day's fresh cap pays it in full
        self.assertEqual(s['journey']['fair']['dpts'], -(-(shown - 100) // fh.KN_CAP_UNIT))
        validate_state(s)

    def test_the_save_keeps_its_keys_and_bounds(self):
        s = story(10**5)
        for _ in range(35):
            s, _ = self.perfect_run(s, 100, 1)
        j = s['journey']
        self.assertEqual(set(j['fair']), set(fh.KEYS))
        self.assertEqual(set(j['fair_kn']), set(fh.KN_KEYS))
        self.assertEqual(set(j['fair_kn']['run']), set(fh.KN_RUN))
        self.assertEqual(set(j['fair']['earn']), set(fh.EARN_KEYS))
        self.assertEqual(j['fair']['dpts'], fh.POINTS_DAY)
        self.assertLessEqual(j['fair_kn']['run']['hot'], kn.HEAT_MAX)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
