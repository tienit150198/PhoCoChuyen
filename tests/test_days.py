"""Ngày N (game/days.py): one day counter and concrete words for "hôm sau"; the interview retry day."""
import unittest

from game import days
from game import employment as emp
from game import journey as jr
from game.engine import GameError, apply_action, new_state, public_state, validate_state


def story(seed=7):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey']['gender'] = 'female'
    s['journey']['intro'] = True
    return s


class Wording(unittest.TestCase):
    def test_today_is_the_life_day_in_the_story(self):
        s = story()
        s['journey']['life_day'] = 4
        s['careers']['milk_tea']['day'] = 2
        self.assertEqual(days.today(s, s['careers']['milk_tea']), 4)

    def test_today_is_the_career_day_in_the_sandbox(self):
        s = new_state()
        s['careers']['grocery']['day'] = 3
        self.assertEqual(days.today(s, s['careers']['grocery']), 3)

    def test_when_day(self):
        s = story()
        s['journey']['life_day'] = 4
        self.assertEqual(days.when_day(s, 3), 'bây giờ')
        self.assertEqual(days.when_day(s, 4), 'bây giờ')
        self.assertEqual(days.when_day(s, 5), 'từ Ngày 5 (còn 1 ngày · sau khi khép ca hôm nay)')
        self.assertEqual(days.when_day(s, 7), 'từ Ngày 7 (còn 3 ngày)')

    def test_on_day_and_info(self):
        s = story()
        s['journey']['life_day'] = 4
        self.assertEqual(days.on_day(s, 4), 'hôm nay (Ngày 4)')
        self.assertEqual(days.on_day(s, 5), 'Ngày 5 (ngày mai)')
        self.assertEqual(days.on_day(s, 9), 'Ngày 9 (còn 5 ngày)')
        self.assertEqual(days.on_day(s, 2), 'Ngày 2 (đã qua)')
        info = days.day_info(s, 6)
        self.assertEqual((info['day'], info['left'], info['open']), (6, 2, False))
        self.assertTrue(days.day_info(s, 4)['open'])


class InterviewRetry(unittest.TestCase):
    CID = 'delivery'

    def rejected(self):
        s = story()
        day = s['journey']['life_day']
        job = s['careers'][self.CID]['job']
        job.update(status='rejected', cooldown_day=day + 1)
        validate_state(s)
        return s, day

    def test_posting_shows_the_day_and_the_apply_is_refused_until_then(self):
        s, day = self.rejected()
        v = public_state(s, full=self.CID)['careers'][self.CID]['job']['retry']
        self.assertEqual((v['day'], v['left'], v['open'], v['button']), (day + 1, 1, False, 'Còn 1 ngày'))
        self.assertIn(f'từ Ngày {day + 1}', v['line'])
        post = emp.postings(self.CID)[0]['id']
        s['current'] = self.CID
        with self.assertRaises(GameError) as e:
            apply_action(s, self.CID, 'job_apply', {'posting': post})
        self.assertEqual(e.exception.code, 'retry_later')
        self.assertIn(f'Ngày {day + 1}', str(e.exception))

    def test_notice_fires_exactly_once_on_the_day(self):
        s, day = self.rejected()
        self.assertEqual(emp.retry_notices(s), [])  # not yet
        s['journey']['life_day'] = day + 1
        lines = emp.retry_notices(s)
        self.assertEqual(len(lines), 1)
        self.assertIn(f'Hôm nay (Ngày {day + 1}) bạn có thể phỏng vấn lại ở', lines[0])
        self.assertEqual(emp.retry_notices(s), [])  # once
        validate_state(s)
        v = public_state(s, full=self.CID)['careers'][self.CID]['job']
        self.assertNotIn('retry_told', v)
        self.assertEqual((v['retry']['open'], v['retry']['button']), (True, 'Phỏng vấn lại'))

    def test_notice_rides_on_the_closing_of_a_day(self):
        s, day = self.rejected()
        s, _ = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        s, _ = apply_action(s, 'milk_tea', 'start_day')
        s, r = apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})
        self.assertEqual(s['journey']['life_day'], day + 1)
        hits = [x for x in r['effects'] if 'phỏng vấn lại' in x]
        self.assertEqual(len(hits), 1)
        s, r = apply_action(s, 'milk_tea', 'start_day')
        self.assertFalse([x for x in r.get('effects', []) if 'phỏng vấn lại' in x])

    def test_old_save_without_notice_mark(self):
        s, day = self.rejected()
        s['careers'][self.CID]['job'].pop('retry_told', None)
        validate_state(s)
        s['careers'][self.CID]['job']['retry_told'] = -1
        with self.assertRaises(GameError):
            validate_state(s)


class DaySummary(unittest.TestCase):
    def test_summary_names_tomorrow(self):
        s = story()
        day = s['journey']['life_day']
        s, _ = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
        s, _ = apply_action(s, 'milk_tea', 'start_day')
        s, r = apply_action(s, 'milk_tea', 'end_day', {'carry_event': True})
        self.assertIn(f'Ngày {day + 1} (ngày mai) mở cửa', r['summary']['clock']['next_text'])


if __name__ == '__main__':
    unittest.main()
