import copy
import json
import unittest

from game import classroom as C
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


def solve(j, aid):
    j.act('cl_start', activity=aid)
    for st in C.INDEX[aid]['steps']:
        r = j.act('cl_submit', step=st['id'], answer=copy.deepcopy(st['_key']))
        assert r['correct'], (aid, st['id'])
    return j.act('cl_finish')


class ClassroomTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('teacher')

    def at_day(self, day):
        self.j.c['day'] = day
        validate_state(self.j.state)

    def test_every_activity_is_solvable_and_valid(self):
        for a in C.ACTIVITIES:
            j = Journey('teacher')
            day = next(d for d in range(1, C.YEAR + 1) if a['id'] in C.offers(dict(day=d, ext=dict(data={}))))
            j.c['day'] = day
            money = j.c['money']
            r = solve(j, a['id'])
            self.assertEqual(r['outcome']['grade'], 'great', a['id'])
            self.assertEqual(j.c['money'], money + a['reward'])
            validate_state(json.loads(json.dumps(j.state)))
            self.assertGreaterEqual(len(a['perspectives']), 2)

    def test_answers_hidden_in_public_state(self):
        aid = C.offers(self.j.c)[0]
        self.j.act('cl_start', activity=aid)
        pub = json.dumps(public_state(self.j.state)['careers']['teacher']['classroom'], ensure_ascii=False)
        self.assertNotIn('_key', pub)
        first = public_state(self.j.state)['careers']['teacher']['classroom']['active']['steps'][0]
        self.assertNotIn('explain', first)

    def test_wrong_answer_counts_and_lowers_grade(self):
        aid = next(a for a in C.offers(self.j.c) if C.INDEX[a]['steps'][0]['kind'] == 'choice')
        st = C.INDEX[aid]['steps'][0]
        wrong = next(o['id'] for o in st['options'] if o['id'] != st['_key'])
        self.j.act('cl_start', activity=aid)
        r = self.j.act('cl_submit', step=st['id'], answer=wrong)
        self.assertFalse(r['correct'])
        with self.assertRaises(GameError):
            self.j.act('cl_submit', step=st['id'], answer='not-an-option')
        with self.assertRaises(GameError):
            self.j.act('cl_finish')
        for s2 in C.INDEX[aid]['steps']:
            self.j.act('cl_submit', step=s2['id'], answer=copy.deepcopy(s2['_key']))
        r = self.j.act('cl_finish')
        self.assertEqual(r['outcome']['grade'], 'ok')

    def test_calendar_events_by_month(self):
        self.at_day(1)
        self.assertIn('ev_trung_thu', C.offers(self.j.c))
        self.assertNotIn('ev_tet', C.offers(self.j.c))
        with self.assertRaises(GameError):
            self.j.act('cl_start', activity='ev_tet')
        self.at_day(1 + C.DAYS_PER_MONTH * 4)
        self.assertIn('ev_tet', C.offers(self.j.c))
        solve(self.j, 'ev_tet')
        self.assertNotIn('ev_tet', C.offers(self.j.c))
        self.j.c['day'] += C.YEAR
        self.assertIn('ev_tet', C.offers(self.j.c))

    def test_one_active_at_a_time_and_quit(self):
        a, b = C.offers(self.j.c)[:2]
        self.j.act('cl_start', activity=a)
        with self.assertRaises(GameError):
            self.j.act('cl_start', activity=b)
        self.j.act('cl_quit')
        self.j.act('cl_start', activity=b)

    def test_tampered_progress_rejected(self):
        aid = C.offers(self.j.c)[0]
        self.j.act('cl_start', activity=aid)
        st = C.INDEX[aid]['steps'][0]
        self.j.act('cl_submit', step=st['id'], answer=copy.deepcopy(st['_key']))
        bad = copy.deepcopy(self.j.state)
        bad['careers']['teacher']['ext']['data']['class']['active']['state']['answers'][st['id']] = 'forged'
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(self.j.state)
        bad['careers']['teacher']['ext']['data']['class']['active']['id'] = 'nope'
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_other_careers_cannot_use_classroom(self):
        j = Journey('restaurant')
        with self.assertRaises(GameError):
            j.act('cl_start', activity='les_math_market')

    def test_needs_open_shift(self):
        self.j.c['open'] = False
        with self.assertRaises(GameError):
            self.j.act('cl_start', activity=C.offers(self.j.c)[0])


if __name__ == '__main__':
    unittest.main()
