"""Giờ trong ngày (game/dayclock.py): the clock view, closing warnings, closing time and the day summary."""
import copy
import unittest

from game import abandon as ab
from game import dayclock as dc
from game import journey as jr
from game.careers import PLUGINS
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.helpers import Journey


def run_to_close(j, limit=60):
    """Advance until the clock stops moving; the closing warnings in the order they fired."""
    warns = []
    for _ in range(limit):
        r = j.act('advance')
        if r.get('clock'):
            warns.append(r['clock']['level'])
    return warns


def view(j):
    return public_state(j.state)['careers'][j.career]['day_clock']


class PartOfDay(unittest.TestCase):
    def test_parts(self):
        cases = {0: 'Đêm', 4 * 60 + 59: 'Đêm', 5 * 60: 'Sáng', 10 * 60 + 59: 'Sáng', 11 * 60: 'Trưa',
                 12 * 60 + 59: 'Trưa', 13 * 60: 'Chiều', 17 * 60 + 59: 'Chiều', 18 * 60: 'Tối', 21 * 60 + 59: 'Tối',
                 22 * 60: 'Đêm', 23 * 60 + 59: 'Đêm', 24 * 60 + 7 * 60: 'Sáng'}
        for minute, label in cases.items():
            self.assertEqual(dc.part(minute)['label'], label, minute)
        self.assertEqual(dc.part(12 * 60)['icon'], '☀️')
        self.assertEqual(dc.part(19 * 60)['icon'], '🌙')

    def test_left_text(self):
        self.assertEqual(dc.left_text(20), '20 phút')
        self.assertEqual(dc.left_text(60), '60 phút')
        self.assertEqual(dc.left_text(80), '1 giờ 20 phút')
        self.assertEqual(dc.left_text(120), '2 giờ')
        self.assertEqual(dc.left_text(130), '2 giờ 10 phút')


class ClockView(unittest.TestCase):
    def test_open_shift_starts_at_opening_time(self):
        j = Journey('grocery')
        v = view(j)
        self.assertTrue(v['is_open'])
        self.assertEqual((v['time'], v['open_time'], v['close_time']), ('06:30', '06:30', '21:30'))
        self.assertEqual(v['hours'], 'Mở 06:30 – Đóng 21:30')
        self.assertEqual(v['part']['label'], 'Sáng')
        self.assertEqual(v['progress'], 0)
        self.assertEqual(v['step'], 20)
        self.assertEqual(v['level'], '')
        j.act('advance')
        self.assertEqual(view(j)['time'], '06:50')

    def test_closed_shows_morning_prep_and_next_opening(self):
        j = Journey('restaurant')
        j.act('end_day')
        v = view(j)
        self.assertFalse(v['is_open'])
        self.assertEqual(v['level'], 'prep')
        self.assertEqual(v['time'], '09:30')  # 30 minutes of prep before the 10:00 opening
        self.assertIn('10:00', v['label'])
        j.act('start_day')
        self.assertEqual(view(j)['time'], '10:00')

    def test_every_career_shows_its_own_hours(self):
        s = new_state()
        seen = {}
        for cid in s['careers']:
            v = dc.view(s['careers'][cid], cid)
            self.assertRegex(v['hours'], r'^Mở \d\d:\d\d – Đóng \d\d:\d\d$', cid)
            self.assertLess(v['open'], v['close'], cid)
            seen[cid] = v['hours']
        self.assertEqual(seen['restaurant'], 'Mở 10:00 – Đóng 22:00')
        self.assertEqual(seen['delivery'], 'Mở 17:00 – Đóng 23:00')
        self.assertEqual(seen['farm'], 'Mở 05:30 – Đóng 17:30')
        self.assertEqual(seen['corp_accounting'], 'Mở 08:00 – Đóng 17:30')
        self.assertTrue(dc.view(s['careers']['homestay'], 'homestay')['note'])
        self.assertTrue(dc.view(s['careers']['delivery'], 'delivery')['note'])

    def test_football_night_keeps_the_tea_stall_open_late(self):
        if 'tra_da' not in PLUGINS:
            self.skipTest('tra_da filtered out')
        mod = PLUGINS['tra_da']
        day = next(d for d in range(3, 200) if mod.mod_of(d)['id'] == 'football')
        plain = next(d for d in range(3, 200) if mod.mod_of(d)['id'] != 'football')
        c = new_state()['careers']['tra_da']
        self.assertEqual(dc.view(dict(c, day=plain), 'tra_da')['close_time'], '19:30')
        late = dc.view(dict(c, day=day), 'tra_da')
        self.assertEqual(late['close_time'], '22:00')
        self.assertIn('22:00', late['note'])


class ClosingWarnings(unittest.TestCase):
    def test_each_warning_fires_once_in_order(self):
        j = Journey('cafe_bakery')
        warns = run_to_close(j)
        self.assertEqual(warns, ['soon60', 'soon30', 'closing'])
        v = view(j)
        self.assertEqual((v['time'], v['level'], v['label']), ('19:00', 'closing', 'Đến giờ đóng cửa'))
        self.assertEqual(run_to_close(j, 5), [])  # the clock rests at closing: nothing fires again

    def test_warning_text_says_the_time_really_left(self):
        j = Journey('grocery')
        texts = {}
        for _ in range(60):
            r = j.act('advance')
            if r.get('clock'):
                texts[r['clock']['level']] = r['clock']['text']
        self.assertIn('60 phút', texts['soon60'])
        self.assertIn('Sắp đóng cửa', texts['soon30'])
        self.assertIn('Đến giờ đóng cửa', texts['closing'])

    def test_hud_level_follows_the_time_left(self):
        self.assertEqual(dc._level(90), '')
        self.assertEqual(dc._level(60), 'soon60')
        self.assertEqual(dc._level(30), 'soon30')
        self.assertEqual(dc._level(0), 'closing')

    def test_deterministic(self):
        a, b = Journey('florist'), Journey('florist')
        self.assertEqual(run_to_close(a), run_to_close(b))
        self.assertEqual(view(a), view(b))


class ClosingTime(unittest.TestCase):
    def test_no_new_customer_after_closing_but_work_in_hand_goes_on(self):
        j = Journey('mother_baby')
        run_to_close(j)
        with self.assertRaises(GameError) as e:
            j.act('more_work')
        self.assertEqual(e.exception.code, 'closing_time')
        before = [t['id'] for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
        self.assertTrue(before)
        j.solve(before[0])  # the customer already inside is served to the end
        self.assertEqual(j.get(before[0])['status'], 'completed')

    def test_view_gate_predicts_the_press(self):
        """room.more_gate (what the dock offers) says None exactly when `more_work` would take a customer: the
        press ticks the clock first, so one step before closing the gate already reads 'closing'."""
        for career in ('grocery', 'mother_baby', 'pet_care', 'customer_care', 'milk_tea'):
            if career in ('grocery', 'pet_care') and career not in PLUGINS:
                continue
            j = Journey(career)
            for _ in range(60):
                gate = public_state(j.state)['careers'][career]['more_gate']
                try:
                    apply_action(copy.deepcopy(j.state), career, 'more_work', {})
                    took = True
                except GameError as e:
                    took = False
                    self.assertIsNotNone(gate, (career, str(e)))
                self.assertEqual(gate is None, took, (career, gate, view(j)['time']))
                self.assertNotIn('error', gate or {})
                j.act('advance')

    def test_gate_reasons(self):
        j = Journey('grocery' if 'grocery' in PLUGINS else 'mother_baby')
        g = lambda: public_state(j.state)['careers'][j.career]['more_gate']
        self.assertIsNone(g())
        while sum(t['status'] not in ('completed', 'referred', 'cancelled') for t in j.c['tasks']) < 4:
            j.act('more_work')
        self.assertEqual(g()['why'], 'full')
        self.assertEqual(g()['active'], 4)
        for t in j.c['tasks']:
            t['status'] = 'completed'
        while len([t for t in j.c['tasks'] if t['day'] == j.c['day']]) < 12 and g() is None:
            j.act('more_work')
            for t in j.c['tasks']:
                t['status'] = 'completed'
        self.assertIn(g()['why'], ('cap', 'closing'))
        run_to_close(j)
        self.assertEqual(g()['why'], 'closing')
        j.act('end_day')
        self.assertIsNone(g())  # closed: the dock offers "Chuẩn bị ngày mới", not a gate

    def test_walk_ins_stop_at_closing(self):
        if 'restaurant' not in PLUGINS:
            self.skipTest('restaurant filtered out')
        from game.careers import food_service
        j = Journey('restaurant')
        run_to_close(j)
        j.c['tasks'] = [t for t in j.c['tasks'] if t['status'] in ('completed', 'referred', 'cancelled')]
        self.assertIsNone(food_service.spawn_walkin(j.state, j.c, 'restaurant', 1.0, 'test'))

    def test_proper_close_is_never_an_abandonment(self):
        s = new_state()
        jr.enable_story(s, 7)
        s['journey']['gender'] = 'female'
        s['journey']['intro'] = True
        s, _ = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        s, _ = apply_action(s, 'milk_tea', 'start_day')
        for _ in range(40):
            s, _ = apply_action(s, 'milk_tea', 'advance')
        s, r = apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})
        self.assertNotIn('abandon', r['summary'])
        self.assertIsNone(ab.assess(s, 'milk_tea'))
        validate_state(s)

    def test_summary_says_when_the_day_ended(self):
        j = Journey('grocery')
        for _ in range(6):
            j.act('advance')
        r = j.act('end_day')
        k = r['summary']['clock']  # six steps and closing up: 06:30 + 7 × 20 minutes
        self.assertEqual((k['finish'], k['close'], k['next_open']), ('08:50', '21:30', '06:30'))
        self.assertEqual(k['early'], 12 * 60 + 40)
        self.assertIn('Khép ca lúc 08:50', k['text'])
        self.assertIn('06:30', k['next_text'])
        public_state(j.state)  # the summary rides in the save and the public view
        validate_state(j.state)

    def test_on_time_close(self):
        j = Journey('cafe_bakery')
        run_to_close(j)
        k = j.act('end_day')['summary']['clock']
        self.assertEqual((k['finish'], k['early'], k['over']), ('19:00', 0, 0))
        self.assertIn('đúng giờ', k['text'])


class OldSaves(unittest.TestCase):
    def test_career_without_clock_anchor_still_has_a_clock(self):
        j = Journey('grocery')
        for _ in range(3):
            j.act('advance')
        old = copy.deepcopy(j.state)
        c = old['careers']['grocery']
        (c['ext'].get('inv') or {}).pop('opened', None)
        c['journal'] = [row for row in c['journal'] if not str(row.get('text', '')).startswith('Mở ca')]
        v = public_state(old)['careers']['grocery']['day_clock']
        self.assertTrue(v['is_open'])
        self.assertRegex(v['time'], r'^\d\d:\d\d$')
        validate_state(old)

    def test_old_shift_summary_without_clock(self):
        j = Journey('grocery')
        j.act('end_day')
        j.c['shift_summary'].pop('clock')
        validate_state(j.state)
        j.act('start_day')


if __name__ == '__main__':
    unittest.main()
