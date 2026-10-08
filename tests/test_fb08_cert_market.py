"""F#267 (08/10): "thi chứng chỉ bấm ở đâu" — the hire message says where the exam is.
F#263/#264 (08/10): "5 tiệm quần áo, không độn giá mà suy thoái cả 5" — the counters' market is one town-wide calendar
(not the price, not the number of counters); the counter view now carries that calendar and the price effect."""
import copy
import unittest

from game import certificates as ct
from game import quay_business as qb
from game import quay_market as market
from game import quay_self as qs
from tests.test_certificates import CID, act, here, interview, story
from tests.test_quay_business import fixture


class HireNudge(unittest.TestCase):
    def test_says_where_the_exam_is_until_earned(self):
        s = story()
        tip = ct.hire_nudge(s, 'lifeguard')
        self.assertIn('Chứng chỉ Cứu hộ hồ bơi', tip)
        self.assertIn('🎓 Thi chứng chỉ', tip)
        s['journey']['certificates']['pool_rescue'] = dict(score=100, best=100, earned_day=1, attempts=1)
        self.assertEqual(ct.hire_nudge(s, 'lifeguard'), '')

    def test_quiet_while_studying_it_and_outside_the_story(self):
        s = story()
        s['journey']['study'] = dict(cert='work_safety')
        self.assertEqual(ct.hire_nudge(s, 'delivery'), '')
        s['journey']['story'] = False
        self.assertEqual(ct.hire_nudge(s, 'lifeguard'), '')

    def test_craft_certificate_counts_too(self):
        self.assertIn('Chứng chỉ làm kem', ct.hire_nudge(story(), 'ice_cream'))

    def test_a_hire_carries_the_nudge(self):
        here(CID)
        s, _ = interview(story(wallet=500))
        self.assertEqual(s['careers'][CID]['job']['status'], 'rejected')
        s, r = act(s, CID, 'job_backdoor', confirm=True)
        self.assertEqual(s['careers'][CID]['job']['status'], 'hired')
        self.assertIn('Chứng chỉ An toàn lao động', r['message'])
        self.assertIn('Bạn được nhận', r['message'])   # the hire line itself is kept, the tip comes after it


class TownMarket(unittest.TestCase):
    def test_outlook_runs_are_contiguous_and_match_the_calendar(self):
        for at in (0, 7 * market.EPOCH_MS + 123, 5 * 86400000 + 1):
            runs = market.outlook(at, 6)
            self.assertEqual(len(runs), 6)
            self.assertLessEqual(runs[0]['starts_at'] * 1000, at)
            self.assertGreater(runs[0]['ends_at'] * 1000, at)
            for a, b in zip(runs, runs[1:]):
                self.assertEqual(a['ends_at'], b['starts_at'])
                self.assertNotEqual((a['state'], a['demand_factor']), (b['state'], b['demand_factor']))
            for r in runs:
                mid = (r['starts_at'] + r['ends_at']) / 2 * 1000
                snap = market.snapshot(mid)
                self.assertEqual((snap['state'], snap['label'], snap['demand_factor']), (r['state'], r['label'], r['demand_factor']))

    def test_day_numbers_said_on_screen(self):
        self.assertEqual(market.DAY_PERCENT, round(market._CYCLE_WORK / market._CYCLE_MS))
        self.assertGreaterEqual(market.DAY_PERCENT, 100)
        downs = sum(1 for p in market._PHASES if p[0] == 'downturn')
        self.assertEqual(market.DOWN_MINUTES, downs * market.EPOCH_MS // 60000)
        self.assertLessEqual(market.DOWN_MINUTES, 6 * 60)

    def test_every_counter_shares_one_phase_and_owning_more_splits_nothing(self):
        s, st = fixture(trade='clothing')
        qb.settle(s, now=1000)
        alone = qb._intervals(st)
        # Five clothing counters in one save: each keeps its own walk-ins (no shared pool, no saturation).
        s5 = copy.deepcopy(s)
        stalls = s5['journey']['quay']['stalls']
        for n in range(4):
            twin = copy.deepcopy(stalls[0])
            twin['id'] = f'q{n + 9}'
            stalls.append(twin)
        qb.settle(s5, now=1000)
        for other in stalls:
            self.assertEqual(qb._intervals(other), alone)
        # Another trade, another save, same moment: the same market phase.
        o, ost = fixture(trade='milk_tea')
        qb.settle(o, now=1000)
        for at in range(1001, 1001 + 86400, 1800):
            qb.settle(s5, now=at)
            qb.settle(o, now=at)
            labels = {qb.public(x)['market']['label'] for x in stalls} | {qb.public(ost)['market']['label']}
            self.assertEqual(len(labels), 1)

    def test_public_carries_the_calendar_and_the_price_effect(self):
        s, st = fixture(trade='clothing')
        qb.settle(s, now=1000)
        m = qb.public(st)['market']
        self.assertTrue(m['town'])
        self.assertEqual(m['day_percent'], market.DAY_PERCENT)
        self.assertEqual(m['down_minutes'], market.DOWN_MINUTES)
        self.assertEqual(m['runs'][0]['label'], m['label'])
        self.assertEqual(qb.public(st)['price_effect'], 100)    # a new counter sells at the reference prices

    def test_price_effect_follows_the_menu(self):
        s, st = fixture(trade='clothing')
        board = qs.menu(st)
        rows = qs.DISH['clothing']
        st['menu'] = dict(on=board['on'], p={d: rows[d]['base'] * 2 for d in rows})
        self.assertLess(qb.price_effect(st), 20)
        st['menu'] = dict(on=board['on'], p={d: max(1, rows[d]['base'] // 2) for d in rows})
        self.assertEqual(qb.price_effect(st), 160)


if __name__ == '__main__':
    unittest.main()
