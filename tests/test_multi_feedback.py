"""Multiple-choice steps say what is actually wrong (feedback #124: the Trung thu safety step answered
"Pháo không an toàn cho trẻ nhỏ" to a player who never ticked the fireworks)."""
import copy
import unittest

from game import classroom as C
from game import procedures as P
from game.engine import validate_state
from tests.helpers import Journey

FIRE = 'Pháo không an toàn cho trẻ nhỏ.'


class TrungThuSafety(unittest.TestCase):
    def setUp(self):
        self.j = Journey('teacher')
        self.j.c['day'] = 1
        validate_state(self.j.state)
        a = C.INDEX['ev_trung_thu']
        self.assertIn(a['id'], C.offers(self.j.c))
        self.j.act('cl_start', activity=a['id'])
        steps = a['steps']
        i = next(k for k, s in enumerate(steps) if s['id'] == 'safe')
        for st in steps[:i]:
            self.assertTrue(self.j.act('cl_submit', step=st['id'], answer=copy.deepcopy(st['_key']))['correct'])
        self.st = steps[i]

    def send(self, answer):
        return self.j.act('cl_submit', step='safe', answer=answer)

    def test_the_right_ticks_pass(self):
        self.assertEqual(sorted(self.st['_key']), ['adults', 'count', 'led', 'peanut'])
        r = self.send(['count', 'adults', 'peanut', 'led'])
        self.assertTrue(r['correct'])

    def test_missing_one_never_talks_about_fireworks(self):
        for _ in range(4):   # the old hint list reached the fireworks line on the second try
            r = self.send(['led', 'adults', 'count'])
            self.assertFalse(r['correct'])
            self.assertNotIn(FIRE, r['message'])
            self.assertIn('Đúng 3/4 mục cần chọn.', r['message'])
            self.assertIn('Sức khỏe', r['message'])     # An's allergy: the note that says why
        r = self.send(['led', 'peanut', 'count'])
        self.assertNotIn(FIRE, r['message'])
        self.assertIn('ai đi cùng', r['message'])

    def test_ticking_the_fireworks_says_so(self):
        r = self.send(['led', 'peanut', 'adults', 'count', 'fire'])
        self.assertFalse(r['correct'])
        self.assertIn('Đúng 4/4 mục cần chọn, thừa 1 mục.', r['message'])
        self.assertIn(FIRE, r['message'])
        r = self.send(['led', 'fire'])            # a wrong tick is named before the missing ones
        self.assertIn(FIRE, r['message'])
        self.assertIn('thừa 1 mục', r['message'])

    def test_no_key_leaks_to_the_client(self):
        from game.engine import public_state
        import json
        pub = json.dumps(public_state(self.j.state)['careers']['teacher']['classroom'], ensure_ascii=False)
        self.assertNotIn('_why', pub)
        self.assertNotIn('Pháo không an toàn', pub)


class EveryMultiStep(unittest.TestCase):
    def test_every_classroom_multi_names_each_option(self):
        for a in C.ACTIVITIES:
            for st in a['steps']:
                if st['kind'] != 'multi':
                    continue
                ids = {o['id'] for o in st['options']}
                self.assertEqual(set(st['_why']), ids, (a['id'], st['id']))
                for x in ids:   # one wrong move at a time: the hint is that option's own word
                    ans = [k for k in st['_key'] if k != x] if x in st['_key'] else list(st['_key']) + [x]
                    if not ans:
                        continue
                    t = dict(proc=[st], proc_state=P.initial_state(), mistakes=0)
                    ok, msg = P.submit(t, st['id'], ans)
                    self.assertFalse(ok)
                    self.assertIn(st['_why'][x], msg, (a['id'], st['id'], x))

    def test_steps_without_reasons_keep_their_hints(self):
        st = P.step('m', 'multi', 'T', 'P', ['a', 'b'], options=[dict(id=x, label=x) for x in 'abc'], hints=['Gợi ý một.', 'Gợi ý hai.'])
        t = dict(proc=[st], proc_state=P.initial_state(), mistakes=0)
        ok, msg = P.submit(t, 'm', ['a'])
        self.assertFalse(ok)
        self.assertEqual(msg, 'Đúng 1/2 mục cần chọn. Gợi ý một.')
        ok, msg = P.submit(t, 'm', ['a', 'c'])
        self.assertEqual(msg, 'Đúng 1/2 mục cần chọn, thừa 1 mục. Gợi ý hai.')

    def test_match_says_how_many_rows_fit(self):
        st = P.step('g', 'match', 'T', 'P', dict(x='1', y='2'), left=[dict(id='x', label='x'), dict(id='y', label='y')],
                    right=[dict(id='1', label='1'), dict(id='2', label='2')], hints=['Xem lại.'])
        t = dict(proc=[st], proc_state=P.initial_state(), mistakes=0)
        ok, msg = P.submit(t, 'g', dict(x='1', y='1'))
        self.assertFalse(ok)
        self.assertEqual(msg, 'Ghép đúng 1/2 dòng. Xem lại.')


if __name__ == '__main__':
    unittest.main()
