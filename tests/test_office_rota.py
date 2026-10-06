"""F#212 (backlog #11): the pilot PGĐ step needs 5 good office days, and the hidden killer was fatigue: crew who had
flown 2 days running get 🥱 (50%) and every slot they take loses 12 (15 more when 🥱). The rule is now said in the
board, on each person ("N ngày liền") and in the day summary."""
import unittest

from game import promotion as pm
from game import promotion_office as OF
from game.engine import public_state, validate_state
from tests.test_promotion_ladders import at, office, office_state, plan_well, answer_inbox_well, day


class Rota(unittest.TestCase):
    def test_rota_line_names_who_flew_days_running(self):
        off = dict(staff=[dict(n='Lan', duty=2, iss='tired'), dict(n='Minh', duty=1, iss=None), dict(n='Tú', duty=3, iss=None)])
        line = OF.rota_line('pilot', off, [0, 1, None, 0])
        self.assertIn('Lan (2 ngày liền, đang 🥱 mệt)', line)
        self.assertNotIn('Minh', line)
        self.assertNotIn('Tú', line)   # not planned
        self.assertIn('đã bay liền', line)
        self.assertEqual(OF.rota_line('pilot', off, [1, None]), '')
        self.assertIn('đã làm liền', OF.rota_line('teacher', off, [0]))

    def test_summary_says_it_and_the_board_sends_the_days(self):
        j = at('pilot', 5)
        plan_well(j)
        answer_inbox_well(j)
        # Make the first planned person someone who already flew 2 days running.
        off = office_state(j)
        who = next(w for w in off['plan'] if w is not None)
        off['staff'][who]['duty'] = OF.TIRED_AT
        v = office(j)
        self.assertEqual(v['tired_at'], OF.TIRED_AT)
        self.assertEqual(next(m for m in v['staff'] if m['i'] == who)['duty'], OF.TIRED_AT)
        r = day(j)
        lines = r['summary']['promo']['office']['lines']
        self.assertIn('📊 Điểm điều hành', lines[1])
        self.assertIn('🏢 Ngày điều hành tốt', lines[2])   # progress keeps its place
        rota = next(x for x in lines if x.startswith('🥱 Xoay ca'))
        self.assertIn(f'{off["staff"][who]["n"]} ({OF.TIRED_AT} ngày liền', rota)
        validate_state(j.state)

    def test_rotated_day_has_no_rota_line(self):
        j = at('pilot', 5)
        plan_well(j)
        answer_inbox_well(j)
        off = office_state(j)
        for st in off['staff']:
            st['duty'] = 0
        r = day(j)
        self.assertFalse(any(x.startswith('🥱') for x in r['summary']['promo']['office']['lines']))

    def test_client_says_the_rule_and_the_tag(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parents[1] / 'public' / 'js' / 'v4' / 'promo.js').read_text(encoding='utf-8')
        self.assertIn('🔁 Xoay ca: ai đã làm 2 ngày liền', js)
        self.assertIn('ngày liền · nên nghỉ', js)
        self.assertIn('Xoay ca: không ai làm ngày thứ 3 liền', js)


if __name__ == '__main__':
    unittest.main()
