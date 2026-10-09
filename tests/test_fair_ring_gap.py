"""B5 (backlog 6, 07/10): one session sent ~20,000 ring-toss calls. A new ring round starts at least RING_GAP_MS
after the last one started; a faster start is refused gently ("Từ từ thôi nha"), changes nothing and costs nothing.
The earnings rules stay as they were: no round cap (owner 03/10 "kiếm không giới hạn")."""
import copy
import json
import unittest

from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import Dice, FairBase, aim, story


class RingGap(FairBase):
    def start(self, s, gap_s=2.0):
        self.clock.t += gap_s - 2      # the test clock steps 2 s a call
        return self.act(s, 'fair_ring_start')

    def test_the_gap_is_two_seconds(self):
        self.assertEqual(fh.RING_GAP_MS, 2000)

    def test_a_start_too_soon_is_refused_gently_and_changes_nothing(self):
        s, r = self.start(story(0))
        before, t0 = json.dumps(s, sort_keys=True), self.clock.t
        for gap in (0.0, 1.0, 1.999):
            self.clock.t = t0
            with self.assertRaises(GameError) as e:
                self.start(copy.deepcopy(s), gap)
            self.clock.t = t0
            self.assertEqual(e.exception.code, 'fair_slow')
            self.assertIn('Từ từ thôi nha', e.exception.message)
            with self.assertRaises(GameError):
                self.start(s, gap)
            self.assertEqual(json.dumps(s, sort_keys=True), before)   # no penalty, no counter moved
        self.clock.t = t0
        s, r = self.start(s, 2.0)                                        # exactly the gap: fine
        self.assertNotEqual(json.dumps(s, sort_keys=True), before)        # a new round: started and counted
        validate_state(s)

    def test_a_finished_round_also_waits_for_the_gap(self):
        s, r = self.start(story(0))
        rd = r['fair']['round']
        taps = aim(rd)
        self.clock.t += taps[-1] / 1000 - 2 + 0.3
        self.dice(Dice(draws=[.1], coins=[4, 0, 1, 2, 3, 4]))
        s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        self.assertEqual(r['fair']['n'], 5)
        if taps[-1] < 1700:                     # the throw landed within 2 s of the start
            with self.assertRaises(GameError):
                self.start(s, 0.0)
        s, _ = self.start(s, 2.0)
        validate_state(s)

    def test_no_round_cap_at_a_human_pace(self):
        s = story(0)
        paid = 0
        for _ in range(40):                    # twice the old RING_DAY counter's half, every round pays
            s, r = self.start(s, 2.5)
            rd = r['fair']['round']
            self.dice(Dice(draws=[.1], coins=[4, 0, 1, 2, 3, 4]))
            self.clock.t += 1.2 - 2
            s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=[0, 300, 600, 900, 1200])
            full = r['fair']['n'] * fh.RING_HIT + (fh.RING_ALL if r['fair']['n'] == 5 else 0)
            # 09/10 (exploit audit): no round cap, but at most fair.RING_PAY_DAY xu a Vietnam day
            self.assertEqual(r['fair']['prize'], min(full, fh.RING_PAY_DAY - paid))
            paid += r['fair']['prize']
        self.assertGreater(paid, 0)
        self.assertLessEqual(paid, fh.RING_PAY_DAY)
        self.assertEqual(fh.money_of(s['journey'])[0], paid)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
