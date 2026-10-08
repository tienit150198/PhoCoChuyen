"""🗡️ Phóng dao's daily cap (owner 08/10 "đảm bảo nhà cái luôn thắng"): a scripted perfect thumb nets at most
fair.KN_DAY_CAP xu a Vietnam day from the stall, whatever it stakes and wherever it stops; the stall then takes no
stake until the next day; the prizes it shows are the ones it pays; the tally rides in the legacy 'dpts' within the
bound older servers check, so the save stays valid both ways."""
import random
import unittest

from game import fair as fh
from game import fair_knife as kn
from game.engine import GameError, public_state, validate_state

from tests.test_fair import FairBase, story
from tests import test_fair_knife as tk


class Cap(FairBase):
    start, board, clear, lose = tk.Knife.start, tk.Knife.board, tk.Knife.clear, tk.Knife.lose   # its helpers, not its tests

    def setUp(self):
        super().setUp()
        self.dice(random.Random(20261008))

    def perfect_run(self, s, stake, stop):
        """Start at `stake`, clear `stop` levels with every throw clean, take the prize; returns (s, paid)."""
        s, r = self.start(s, stake)
        for lv in range(1, stop + 1):
            s, r = self.clear(s)
            run = r['fair']['run']
            left = fh.kn_cap_left(s['journey']['fair'], self.clock.t)
            self.assertLessEqual(run['prize'], stake + left)                # what it shows is what it may pay
            if 'win' in run:
                self.assertLessEqual(run['win'], stake + left)
            if lv < stop:
                s, r = self.act(s, 'fair_kn_next')
        if r['fair'].get('all'):
            return s, r['fair']['paid']
        s, r = self.act(s, 'fair_kn_stop')
        return s, r['fair']['prize']

    def day_net(self, s, rng, budget=60):
        """A perfect player stakes and stops at random until the stall says enough; returns (s, net, runs)."""
        net = runs = 0
        while runs < budget:
            stake = rng.choice(kn.STAKES[:7])
            try:
                s, paid = self.perfect_run(s, stake, rng.randint(1, kn.LEVELS))
            except GameError as e:
                self.assertEqual(e.code, 'fair_kn_cap')
                self.assertEqual(str(e), fh.KN_CAP_MSG)
                break
            net += paid - stake
            runs += 1
            self.assertLessEqual(net, fh.KN_DAY_CAP)
            self.clock.t += 1
        return s, net, runs

    def test_the_cap_is_three_hundred_xu_within_the_old_bound(self):
        self.assertEqual(fh.KN_DAY_CAP, 300)
        self.assertEqual(fh.KN_DAY_CAP, fh.KN_CAP_UNIT * fh.POINTS_DAY)   # dpts <= POINTS_DAY, as 1.9.21 checks

    def test_all_ten_levels_at_the_top_stake_pay_the_stake_and_the_cap(self):
        s = story(5000)
        s, paid = self.perfect_run(s, 1000, kn.LEVELS)
        self.assertEqual(paid, 1000 + fh.KN_DAY_CAP)                    # not kn.prize(1000, 10) = 10000
        self.assertEqual(s['journey']['fair_kn']['run']['pz'], 1300)
        self.assertEqual(s['journey']['fair']['dpts'], fh.POINTS_DAY)
        self.assertEqual(public_state(s)['fair']['knife']['cap_left'], 0)
        validate_state(s)
        with self.assertRaises(GameError) as e:                          # no more paid runs today
            self.start(s, 2)
        self.assertEqual((e.exception.code, str(e.exception)), ('fair_kn_cap', fh.KN_CAP_MSG))
        self.assertEqual(s['journey']['fair_kn']['run']['sg'], 'done')

    def test_the_message_says_so_when_the_cap_is_reached(self):
        s = story(5000)
        s, _ = self.start(s, 500)
        s, _ = self.clear(s)                                            # 550 shown: 50 over the stake
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual((r['fair']['prize'], r['message']), (550, 'Nhận thưởng 550 xu!'))
        s, _ = self.start(s, 500)
        for lv in range(1, 4):
            s, r = self.clear(s)
            if lv < 3:
                s, _ = self.act(s, 'fair_kn_next')
        self.assertEqual(r['fair']['run']['prize'], 750)                  # kn.prize(500, 3) = 800 or more, capped
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual((r['fair']['prize'], r['message']), (750, f'Nhận thưởng 750 xu! {fh.KN_CAP_MSG}'))

    def test_a_scripted_perfect_player_nets_no_more_than_the_cap_a_day(self):
        rng = random.Random(8)
        s = story(10**6)
        total = 0
        for day in range(3):
            s, net, runs = self.day_net(s, rng)
            self.assertLess(runs, 60)                                    # the stall said enough
            self.assertLessEqual(net, fh.KN_DAY_CAP)
            self.assertGreater(net, 0)
            self.assertEqual(s['journey']['fair']['dpts'], fh.POINTS_DAY)
            validate_state(s)
            total += net
            self.clock.t += 86400                                        # the next Vietnam day: a fresh cap
            self.assertEqual(public_state(s)['fair']['knife']['cap_left'], fh.KN_DAY_CAP)
        self.assertLessEqual(total, 3 * fh.KN_DAY_CAP)

    def test_small_wins_count_rounded_up_and_losses_give_nothing_back(self):
        s = story(1000)
        s, paid = self.perfect_run(s, 5, 1)                             # +1 xu counts 10
        self.assertEqual((paid, s['journey']['fair']['dpts']), (kn.prize(5, 1), 1))
        self.assertEqual(fh.kn_cap_left(s['journey']['fair'], self.clock.t), fh.KN_DAY_CAP - 10)
        s, _ = self.start(s, 50)
        s, _ = self.lose(s)
        self.assertEqual(s['journey']['fair']['dpts'], 1)
        s, paid = self.perfect_run(s, 10, 1)                            # a paid-back stake is no win
        self.assertEqual(s['journey']['fair']['dpts'], 1 + (kn.prize(10, 1) - 10 + 9) // 10)

    def test_a_choice_left_overnight_is_paid_under_the_next_days_cap(self):
        s = story(5000)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair'].update(date=fh.vn_date(self.clock.t), ed=fh.edition(), dpts=fh.POINTS_DAY)
        validate_state(s)
        with self.assertRaises(GameError) as e:                          # today's cap already used up
            self.start(s, 100)
        self.assertEqual(e.exception.code, 'fair_kn_cap')
        self.assertEqual(s['journey']['wallet'], 5000)
        self.clock.t += 86400
        s, _ = self.start(s, 1000)
        for lv in range(1, 6):
            s, _ = self.clear(s)
            if lv < 5:
                s, _ = self.act(s, 'fair_kn_next')
        self.clock.t += 86400                                            # left as a choice into the day after
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(r['fair']['prize'], 1300)                        # kn.prize(1000, 5) = 2800, capped
        self.assertEqual(s['journey']['fair']['dpts'], fh.POINTS_DAY)
        validate_state(s)

    def test_the_save_keeps_its_keys_and_bounds(self):
        s = story(5000)
        s, _ = self.perfect_run(s, 1000, kn.LEVELS)
        j = s['journey']
        self.assertEqual(set(j['fair']), set(fh.KEYS))
        self.assertEqual(set(j['fair_kn']), set(fh.KN_KEYS))
        self.assertEqual(set(j['fair']['earn']), set(fh.EARN_KEYS))
        self.assertLessEqual(j['fair']['dpts'], fh.POINTS_DAY)
        validate_state(s)
        v = public_state(s)['fair']['knife']
        self.assertEqual((v['cap'], v['cap_left']), (300, 0))

if __name__ == '__main__':
    unittest.main()
