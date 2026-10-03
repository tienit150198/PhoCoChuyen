"""🔥 Nghề x3 trong tuần (game/x3_week.py)."""
import datetime
import json
import unittest
from unittest import mock

from game import journey as jr
from game import x3_week as x3
from game.content import CAREERS
from game.engine import new_state, public_state, validate_state

VN = datetime.timezone(datetime.timedelta(hours=7))


def at(y, m, d, hh=12):
    return datetime.datetime(y, m, d, hh, tzinfo=VN).timestamp()


def story():
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey'].update(gender='female', intro=True)
    validate_state(s)
    return s


class Week(unittest.TestCase):
    def test_every_career_has_one_day_each_week(self):
        orders = set()
        for w in range(10):
            mon = at(2026, 10, 5) + w * 7 * 86400
            week, days = x3.week(mon)
            self.assertEqual(week, datetime.datetime.fromtimestamp(mon, VN).date().isoformat())
            flat = [c for d in days for c in d]
            self.assertEqual(sorted(flat), sorted(CAREERS))   # each career exactly once
            self.assertLessEqual(max(map(len, days)) - min(map(len, days)), 1)
            for i in range(7):
                t = mon + i * 86400
                self.assertEqual(x3.week(t), (week, days))   # the same list all week
                self.assertEqual(x3.today(t), days[i])
            orders.add(json.dumps(days))
        self.assertGreater(len(orders), 8)                   # a new deal each week

    # 1.4.27 (6cfb54a) dealt this for the week of Monday 28/09/2026; on Saturday 03/10 players were told
    # "milk tea, farm, delivery, garbage, ice cream". Adding careers must not change a running week.
    WEEK_0928 = [['florist', 'homestay', 'homemaker', 'pilot', 'secretary'],
                 ['mother_baby', 'tra_da', 'nail', 'pagoda', 'flight_attendant'],
                 ['customer_care', 'grocery', 'repair', 'hr_admin', 'it_helpdesk'],
                 ['tour_guide', 'pet_care', 'corp_accounting', 'tax_payroll', 'fruit'],
                 ['accounting', 'restaurant', 'salon', 'clothing', 'drain'],
                 ['milk_tea', 'farm', 'delivery', 'garbage', 'ice_cream'],
                 ['pharmacy', 'teacher', 'cafe_bakery', 'group_accounting', 'pet_shop']]

    def test_the_running_week_is_the_one_players_were_told(self):
        t = at(2026, 10, 3)
        week, days = x3.week(t)
        self.assertEqual(week, '2026-09-28')
        first = [[c for c in d if c in x3.FIRST] for d in days]
        self.assertEqual(first, self.WEEK_0928)
        self.assertEqual([c for c in x3.today(t) if c in x3.FIRST], ['milk_tea', 'farm', 'delivery', 'garbage', 'ice_cream'])

    def test_the_first_careers_keep_the_old_deal_every_week(self):
        """The 1.4.27 rule (shuffle list(CAREERS) by the Monday, deal ids[i::7]) on its 35 careers, two years round."""
        import random
        self.assertEqual(len(x3.FIRST), 35)
        for w in range(-52, 52):
            mon = datetime.date(2026, 9, 28) + datetime.timedelta(weeks=w)
            ids = list(x3.FIRST)
            random.Random(f'x3-week|{mon.isoformat()}').shuffle(ids)
            old = [sorted(ids[i::7], key=x3.FIRST.index) for i in range(7)]
            week, days = x3.week(at(mon.year, mon.month, mon.day))
            self.assertEqual(week, mon.isoformat())
            self.assertEqual([[c for c in d if c in x3.FIRST] for d in days], old)

    def test_a_career_added_later_moves_none_before_it(self):
        t = at(2026, 10, 14)
        before = x3.week(t)[1]
        with mock.patch.object(x3, 'CAREERS', tuple(CAREERS) + ('zz_new',)):
            after = x3.week(t)[1]
        self.assertEqual([[c for c in d if c != 'zz_new'] for d in after], before)
        self.assertEqual(sum(d.count('zz_new') for d in after), 1)
        self.assertLessEqual(max(map(len, after)) - min(map(len, after)), 1)

    def test_this_release_s_careers_join_without_moving_anyone(self):
        """pho, com, photobooth (1.5.0), giupviec, naucom and babysitter (1.5.1) each take one day; each one added later
        moves none added before (nor the 35 of FIRST)."""
        added = ['pho', 'com', 'photobooth', 'giupviec', 'naucom', 'babysitter']
        self.assertEqual([c for c in CAREERS if c not in x3.FIRST], added)
        for w in range(52):
            t = at(2026, 9, 28) + w * 7 * 86400
            days = x3.week(t)[1]
            for cid in added:
                self.assertEqual(sum(d.count(cid) for d in days), 1, cid)
            for k in range(1, len(added)):
                later = set(added[k:])
                with mock.patch.object(x3, 'CAREERS', tuple(c for c in CAREERS if c not in later)):
                    without = x3.week(t)[1]
                self.assertEqual([[c for c in d if c not in later] for d in days], without, added[k])

    def test_the_day_turns_at_midnight_vn_time(self):
        sun, mon = at(2026, 10, 11, 23), at(2026, 10, 12, 0)
        self.assertNotEqual(x3.week(sun)[0], x3.week(mon)[0])
        self.assertEqual(x3.today(sun), x3.week(sun)[1][6])
        self.assertEqual(x3.today(mon), x3.week(mon)[1][0])

    def test_on_follows_the_day_and_the_switch(self):
        t = at(2026, 10, 3)
        cid = x3.today(t)[0]
        with mock.patch.dict('os.environ', {'MNL_X3_OFF': '0'}):
            self.assertTrue(x3.on(cid, t))
            self.assertFalse(x3.on(x3.week(t)[1][0][0], t))
        with mock.patch.dict('os.environ', {'MNL_X3_OFF': '1'}):
            self.assertFalse(x3.on(cid, t))

    def test_bonus(self):
        self.assertEqual(x3.bonus(40), 80)
        self.assertEqual(x3.bonus(0), 0)
        self.assertEqual(x3.bonus(-25), 0)
        self.assertEqual(x3.bonus(10 ** 6), x3.CAP)

    def test_public_state(self):
        t = at(2026, 10, 3)
        with mock.patch.object(x3, 'now', lambda: t):
            v = public_state(story())['x3']
        self.assertEqual(v['x'], 3)
        self.assertEqual((v['week'], v['days']), x3.week(t))
        self.assertEqual(v['day'], 5)
        self.assertEqual(v['today'], x3.today(t))
        self.assertNotIn('x3', public_state(story())['journey'])   # outside the journey's size budget


class Shift(unittest.TestCase):
    def close(self, career, net, boosted):
        s = story()
        with mock.patch.object(x3, 'on', lambda c, t=None: boosted and c == career):
            w0 = s['journey']['wallet']
            res = {'summary': {'net': net, 'job': {}}}
            jr._end_of_day(s, career, res)
        validate_state(s)
        rows = [r for r in s['journey']['history'] if r['label'].startswith('🔥')]
        return s, res, rows, s['journey']['wallet'] - w0

    def test_the_career_s_day_pays_its_net_twice_more(self):
        cid = CAREERS[0]
        s, res, rows, _ = self.close(cid, 40, True)
        self.assertEqual([(r['amount'], r['kind'], r['career']) for r in rows], [(80, 'salary', cid)])
        self.assertTrue(any('x3' in e and '80 xu' in e for e in res['effects']))

    def test_no_bonus_on_another_day_or_a_losing_day(self):
        cid = CAREERS[0]
        self.assertEqual(self.close(cid, 40, False)[2], [])
        self.assertEqual(self.close(cid, -15, True)[2], [])
        self.assertEqual(self.close(cid, 0, True)[2], [])


class ClosedDay(unittest.TestCase):
    """The bonus is paid on the whole day: owner draws don't shrink it and the day's salary is in it."""
    def day(self, cid, earn, draw=False, salary=0):
        from game import engine as E
        s = story()
        s, _ = E.apply_action(s, cid, 'select_career', {'confirm': True})
        s, _ = E.apply_action(s, cid, 'start_day')
        E.money(s, s['careers'][cid], earn, 'khách mua')
        if draw:   # take more than the morning fund home: day_start_money clamps at 0
            s, _ = E.apply_action(s, None, 'jr_withdraw', {'career': cid, 'amount': jr.withdraw_max(s['careers'][cid])})
            self.assertEqual(s['careers'][cid]['day_start_money'], 0)
        def pay(st, c, career):
            if not salary:
                return None
            E.money(st, c, salary, 'Lương ngày', category='salary')
            return dict(salary=salary, probation=False)
        with mock.patch.object(x3, 'on', lambda c, t=None: c == cid), mock.patch.object(E.emp, 'on_close', pay):
            s, r = E.apply_action(s, cid, 'end_day', {'carry_event': True})
        validate_state(s)
        return r['summary'], [h['amount'] for h in s['journey']['history'] if h['label'].startswith('🔥')]

    def test_a_draw_bigger_than_the_morning_fund_keeps_the_bonus(self):
        summary, rows = self.day('grocery', 300, draw=True)
        self.assertEqual((summary['income'], summary['net']), (300, 300))
        self.assertEqual(rows, [600])

    def test_the_salary_counts(self):
        summary, rows = self.day('grocery', 40, salary=100)
        self.assertEqual(summary['net'], 140)
        self.assertEqual(rows, [280])

    def test_the_day_summary_shows_the_bonus(self):
        # Owner 03/10: "gom rác thấy k có thưởng gì cả": the bonus was paid but the summary card never listed it.
        summary, rows = self.day('grocery', 50)
        self.assertEqual(rows, [100])
        self.assertEqual(summary['journey']['x3'], 100)
        summary, rows = self.day('grocery', 0)
        self.assertNotIn('x3', summary['journey'])


if __name__ == '__main__':
    unittest.main()
