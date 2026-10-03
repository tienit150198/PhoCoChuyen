"""The three hired-help careers of 1.5.1 pay a normal day and say so (chat 03/10: "Nghề trông trẻ không có tiền hả :((("):
the paying step leads with the pay (a toast shows its first note only), the day summary has the pay line and an
`earned` figure, and the money is really in the workplace fund."""
import unittest

from game.careers import kit
from tests.helpers import Journey
import tests.test_career_babysitter as TB
import tests.test_career_giupviec as TG
import tests.test_career_naucom as TN

PAY_ICONS = ('💵', '💸', '💰')


def record(j):
    """Keep every message a command returned, by action name."""
    seen = []
    act = j.act

    def wrapped(action, **payload):
        r = act(action, **payload)
        if isinstance(r, dict) and isinstance(r.get('message'), str):
            seen.append((action, r['message']))
        return r
    j.act = wrapped
    return seen


class Checks:
    def check_day(self, summary, money_before):
        car = summary['career']
        self.assertGreater(car['earned'], 0)
        self.assertGreater(summary['income'], 0)
        self.assertGreater(self.j.c['money'], money_before)
        line = next(x for x in car['lines'] if x.startswith('💵'))
        self.assertIn(f'{car["earned"]} xu tiền công', line)

    def check_paid_first(self, seen, action):
        rows = [m for a, m in seen if a == action]
        self.assertTrue(rows, action)
        for m in rows:
            self.assertTrue(m.startswith(PAY_ICONS), m)
            first = m.split('.')[0]
            self.assertRegex(first, r'\d+ xu', m)


class Babysitter(TB.Base, Checks):
    def test_a_normal_day_pays_and_says_so(self):
        self.j = Journey('babysitter')
        self.j.act('bm_intro')
        seen = record(self.j)
        money = self.j.c['money']
        for _ in range(20):
            t = next((t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] not in ('completed', 'cancelled')), None)
            if t is None:
                break
            self.block(t)
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.check_day(r['summary'], money)
        self.check_paid_first(seen, 'bm_hand')
        arrive = next(m for a, m in seen if a == 'bm_take')
        self.assertIn('💵 Công hôm nay', arrive)
        self.assertEqual(r['summary']['career']['earned'], r['summary']['income'])

    def test_closing_early_still_shows_the_half_day(self):
        self.j = Journey('babysitter')
        self.block(self.j.task)
        r = self.j.act('end_day', carry_event=True)
        car = r['summary']['career']
        self.assertGreaterEqual(car['earned'], car['half'])
        self.assertTrue(car['lines'][0].startswith('💵'))


class Giupviec(TG.Base, Checks):
    def test_a_normal_day_pays_and_says_so(self):
        self.j = Journey('giupviec')
        seen = record(self.j)
        money = self.j.c['money']
        r = TG.Days.play_day(self)
        self.check_day(r['summary'], money)
        self.check_paid_first(seen, 'gv_check')


class Naucom(TN.Base, Checks):
    def test_a_normal_day_pays_and_says_so(self):
        self.j = Journey('naucom')
        seen = record(self.j)
        money = self.j.c['money']
        TN.Days.full_day(self)
        r = self.j.act('end_day', carry_event=True)
        self.check_day(r['summary'], money)
        self.check_paid_first(seen, 'nc_done')
        self.assertTrue(r['summary']['career']['lines'][0].startswith('🍲'))


class Wording(unittest.TestCase):
    def test_the_journey_says_where_the_pay_sits(self):
        self.assertEqual(kit.earned_line({}, 42), '💵 Hôm nay nhận 42 xu tiền công.')
        line = kit.earned_line(dict(journey=dict(story=True)), 42)
        self.assertIn('quỹ nghề', line)
        self.assertIn('rút về ví', line)


if __name__ == '__main__':
    unittest.main()
