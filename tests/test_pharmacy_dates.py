"""#273 (player feedback): at the pharmacy the dates ("Hết ngày 5", "HSD ngày 12") count the counter's own days,
which the town's day at the top does not show. Today's number is now in the rulebook and the morning notes, the
lot book can pull every bad box in one tap, and the shelf costs at most 2 risk points a day, with the reason said."""
import copy
import json
import unittest

from game import desk_content as dc
from game import engine as eng
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


def care(j):
    return j.c['ext']['data']['care']


def next_day(j):
    j.act('end_day', carry_event=True)
    return j.act('start_day')


def bad_shelf(j):
    """Day 4 of a fresh counter: the day-one near-dated P-02 boxes are out of date. Recall one more batch."""
    for _ in range(3):
        next_day(j)
    expired = [b for b in care(j)['batches'] if b['exp'] < j.c['day']]
    assert expired, care(j)['batches']
    other = next(b for b in care(j)['batches'] if b['lot'] == 'P-03-A')
    other['recalled'] = eng.RECALL_WHY[0]
    return expired, other


class RulebookDayTests(unittest.TestCase):
    def test_slip_rule_says_which_day_it_is(self):
        for day in (1, 2, 8, 31):
            rule = next(r for r in dc.bulletin('pharmacy', day)['rules'] if r['id'] == 'ph_date')
            self.assertTrue(rule['text'].endswith(f'Hôm nay là ngày {day} ở quầy.'), rule['text'])
            self.assertEqual(rule['short'], 'Phiếu còn hạn')

    def test_desk_view_sends_the_day_of_the_case(self):
        from tests.desk_support import desk_journey
        j = desk_journey('pharmacy', 'ph_expired')
        j.act('ask', task=j.task['id'])
        view = next(t for t in public_state(j.state)['careers']['pharmacy']['tasks'] if t['id'] == j.task['id'])
        self.assertEqual(view['day'], j.task['day'])
        slip = next(d for d in view['docs'] if d['id'] == 'slip')
        self.assertTrue(any(f['id'] == 'until' for f in slip['fields']))
        self.assertIn(f"ngày {view['day']}", next(r['text'] for r in view['rules'] if r['id'] == 'ph_date'))


class PullAllTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('pharmacy')

    def test_pull_all_takes_every_bad_box_and_nothing_else(self):
        j = self.j
        expired, recalled = bad_shelf(j)
        good = {b['id']: b['qty'] for b in care(j)['batches'] if not eng._ph_flag(b, j.c['day'])}
        stock = dict(j.c['stock'])
        money = j.c['money']
        r = j.act('ph_lot_pull', all=True)
        self.assertIn('Đã rút', r['message'])
        left = {b['id'] for b in care(j)['batches']}
        self.assertFalse(left & {b['id'] for b in expired + [recalled]})
        self.assertEqual({b['id']: b['qty'] for b in care(j)['batches']}, good)
        self.assertEqual(j.c['money'] - money, recalled['qty'] * eng.PH_UNIT)  # the recall is refunded
        self.assertEqual(care(j)['waste'], sum(b['qty'] for b in expired) * eng.PH_UNIT)
        for lot in {b['lot'] for b in expired + [recalled]}:
            gone = sum(b['qty'] for b in expired + [recalled] if b['lot'] == lot)
            self.assertEqual(j.c['stock'][lot], stock[lot] - gone)
            self.assertIsNone(eng.ph_shelf_block(j.c, lot))
        validate_state(json.loads(json.dumps(j.state)))
        # nothing left to pull: refused, nothing changes
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('ph_lot_pull', all=True)
        self.assertEqual(j.state, before)

    def test_only_true_means_all(self):
        j = self.j
        bad_shelf(j)
        for payload in (dict(all='true'), dict(all=1), dict()):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('ph_lot_pull', **payload)
            self.assertEqual(j.state, before)

    def test_boxes_in_a_tray_stay_until_put_back(self):
        j = self.j
        expired, _ = bad_shelf(j)
        lot = expired[0]['lot']
        # every box of that lot is held by a slip's tray: the shelf has none free to pull
        held = j.c['stock'][lot]
        t = next(t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled'))
        t.setdefault('basket', {})[lot] = held
        self.assertLess(eng.available(j.c, lot), sum(b['qty'] for b in expired if b['lot'] == lot))
        r = j.act('ph_lot_pull', all=True)
        self.assertIn('trong khay', r['message'])
        self.assertTrue(any(b['lot'] == lot and eng._ph_flag(b, j.c['day']) for b in care(j)['batches']))

    def test_needs_an_open_shift(self):
        j = self.j
        bad_shelf(j)
        j.act('end_day', carry_event=True)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('ph_lot_pull', all=True)
        self.assertEqual(j.state, before)


class WarningsAndRiskTests(unittest.TestCase):
    def test_morning_notes_name_the_day_and_the_boxes(self):
        j = Journey('pharmacy')
        notes = []
        for _ in range(3):
            notes += next_day(j)['effects']
        # day 3 morning: the near-dated boxes (HSD = start + 2 = day 3) have their last day today
        self.assertTrue(any(n.startswith('⏳') and 'hết hạn sau hôm nay' in n for n in notes), notes)
        # day 4 morning: they are out of date
        self.assertTrue(any(n.startswith('⚠️ Hôm nay là ngày 4 ở quầy') for n in notes), notes)

    def test_counter_alert_for_the_last_day(self):
        j = Journey('pharmacy')
        next_day(j)
        next_day(j)  # day 3
        alerts = public_state(j.state)['careers']['pharmacy']['data']['care']['alerts']
        self.assertTrue(any(a.startswith('⏳') and 'ngày 3 ở quầy' in a for a in alerts), alerts)

    def test_shelf_costs_at_most_two_points_a_day_and_says_so(self):
        j = Journey('pharmacy')
        bad_shelf(j)
        for b in care(j)['batches'][:4]:
            b['exp'] = 1  # four out-of-date batches on the shelf
        flagged = [b for b in care(j)['batches'] if eng._ph_flag(b, j.c['day'])]
        self.assertGreaterEqual(len(flagged), 3)
        d = j.c['ext']['data']['desk']
        d['risk'] = 0
        lines = eng._ph_close({}, j.c)
        shelf = next(x for x in lines if x.startswith('Còn trên kệ'))
        self.assertIn('+2 điểm rủi ro', shelf)
        self.assertLessEqual(d['risk'], 2 + 3)  # the shelf's 2, plus at most the fridge log's own points

    def test_inspection_note_names_the_shelf(self):
        j = Journey('pharmacy')
        while j.c['day'] % dc.INSPECT_EVERY['pharmacy']:
            next_day(j)
        j.c['ext']['data']['desk']['risk'] = 2
        r = j.act('end_day', carry_event=True)
        note = (r['summary'].get('career') or {}).get('note') or ''
        self.assertIn('hộp quá hạn để trên kệ', note)


if __name__ == '__main__':
    unittest.main()
