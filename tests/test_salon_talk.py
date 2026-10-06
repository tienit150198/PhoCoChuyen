"""Salon Tóc Gió, 1.7.16 (góp ý #199): a plan over the client's budget opens a talk (put a service off, ask for
more, take some off, or say honestly it does not fit) instead of a flat refusal."""
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, validate_state
from game.careers import salon as S
from game import consequences as cq
from tests.test_career_salon import Clock, find, T_OFFICE
from tests.helpers import Journey

PLAN = ['color', 'cut', 'style']


class SalonTalkTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.flex = S._flex

    def tearDown(self):
        kit.clock = self.old
        S._flex = self.flex

    def roundtrip(self):
        validate_state(json.loads(json.dumps(self.j.state)))

    def over(self, colour_price=110):
        """Chị Thảo (budget 140) with the colour priced up: color + cut + style goes over the budget."""
        day, slot = find(T_OFFICE)
        self.j = j = Journey('salon', slot=slot, day=day)
        j.act('ask')
        for topic in ('history', 'patch', 'length', 'budget'):
            j.act('sl_consult', topic=topic)
        j.act('sl_inspect', zone='ends')
        j.c['life']['prices']['color'] = colour_price
        r = j.act('sl_plan', services=PLAN, sessions=1)
        t = j.task
        self.assertTrue(r.get('refused'))
        self.assertIn('Trao đổi', r['message'])
        self.assertEqual(t['talk']['state'], 'open')
        self.assertEqual(cq.slips(t), [])
        self.assertEqual(S.public_task(t)['talk_view']['off'], colour_price + 45 - 140)
        return j, t['id']

    def codes(self):
        return [x['code'] for x in cq.slips(self.j.task)]

    def test_swap_puts_a_service_off(self):
        j, tid = self.over(110)                    # 155: without the blow-dry it is 140
        j.act('sl_talk', task=tid, answer='swap')
        t = j.task
        self.assertEqual(t['talk']['drop'], ['style'])
        r = j.act('sl_plan', services=['color', 'cut'], sessions=1)
        self.assertFalse(r.get('refused'))
        self.assertEqual(j.task['plan']['services'], ['color', 'cut'])
        self.roundtrip()

    def test_swap_with_nothing_to_put_off(self):
        j, tid = self.over(130)                    # 175: a picky client would only put off the blow-dry (still 160)
        r = j.act('sl_talk', task=tid, answer='swap')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['talk']['state'], 'open')
        self.assertEqual(self.codes(), [])

    def test_raise_within_the_hidden_stretch(self):
        S._flex = lambda t: 15
        j, tid = self.over(110)
        j.act('sl_talk', task=tid, answer='raise')
        self.assertEqual(j.task['talk']['state'], 'raised')
        r = j.act('sl_plan', services=PLAN, sessions=1)
        self.assertFalse(r.get('refused'))
        self.assertEqual(S._talk_budget(j.task), 155)
        self.roundtrip()

    def test_raise_refused_then_nagging(self):
        S._flex = lambda t: 0
        j, tid = self.over(110)
        r = j.act('sl_talk', task=tid, answer='raise')
        self.assertTrue(r.get('refused'))
        self.assertEqual(self.codes(), [])
        r = j.act('sl_talk', task=tid, answer='raise')
        self.assertTrue(r.get('refused'))
        self.assertIn('pushy_money', self.codes())

    def test_discount_is_paid_at_checkout(self):
        j, tid = self.over(110)                    # 15 over 155: under the 20% cap
        j.act('sl_talk', task=tid, answer='discount')
        r = j.act('sl_plan', services=PLAN, sessions=1)
        self.assertFalse(r.get('refused'))
        t = j.task
        self.assertEqual(t['quote'], 155)
        self.assertEqual(S._talk_off(t), 15)
        self.roundtrip()
        rows = {r['key']: r for r in S.feedback(j.c, t)['criteria']}
        self.assertEqual(rows['budget']['score'], 5)

    def test_discount_over_the_cap_is_refused(self):
        j, tid = self.over(200)                    # 245 vs 140
        self.assertFalse(S.public_task(j.task)['talk_view']['off_ok'])
        with self.assertRaises(GameError):
            j.act('sl_talk', task=tid, answer='discount')

    def test_promise_broken_is_a_slip(self):
        j, tid = self.over(110)
        j.act('sl_talk', task=tid, answer='swap')
        r = j.act('sl_plan', services=PLAN, sessions=1)     # agreed to put the blow-dry off, quotes it anyway
        self.assertTrue(r.get('refused'))
        self.assertIn('over_budget', self.codes())

    def test_decline_closes_the_visit(self):
        j, tid = self.over(110)
        j.act('sl_talk', task=tid, answer='decline')
        t = next(x for x in j.c['tasks'] if x['id'] == tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('no_sale', [x['code'] for x in cq.slips(t)])
        self.roundtrip()

    def test_talk_needs_a_frown(self):
        day, slot = find(T_OFFICE)
        self.j = j = Journey('salon', slot=slot, day=day)
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('sl_talk', task=j.task['id'], answer='raise')

    def test_bad_talk_is_refused_by_validation(self):
        j, tid = self.over(110)
        j.task['talk']['off'] = 999
        with self.assertRaises(GameError):
            self.roundtrip()


if __name__ == '__main__':
    unittest.main()
