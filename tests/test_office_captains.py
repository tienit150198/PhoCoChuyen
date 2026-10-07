"""F#223: the pilot's 🏢 Phòng điều hành at Phó Giám đốc Khối khai thác bay (step 5) needs 5 good office days, and a base
left with one captain could never make them: two legs a day needed a captain, a captain who quit came back as a step-0
first officer, step 5 had no ⬆️ Thăng chức, and a captain must rest after 3 days running. So the hard legs were cancelled
every day and the score never reached 60.

Now: a captain who quits is replaced by a captain; the base never opens a day with fewer than CAPTAINS_MIN captains
(day_roll tops it up, which also repairs offices saved by older builds); a leg needs a captain only while one is free
(min(2, captains free today)); step 5 may promote. The police office (OFFICE['cand']) keeps its rules."""
import unittest

from game import promotion as pm
from game import promotion_office as OF
from game.engine import public_state, validate_state
from tests.test_promotion_ladders import at, office, office_state, answer_inbox_well, day


def captains(off):
    return [st for st in off['staff'] if st['r'] == 'pl' and st['lv'] >= 2]


def lose_captains(off, keep=1):
    """What older builds left behind: every captain but `keep` quit and came back as a step-0 newcomer."""
    for st in captains(off)[keep:]:
        st.update(n='Bạn Mới', lv=0, sk=50)


def plan_rota(j):
    """A careful player: hard legs first, each to the freshest allowed person (fewest days in a row), skill second."""
    v = office(j)
    for sl in sorted(v['slots'], key=lambda x: (x['need'] is None, x['i'])):
        v = office(j)
        if v['slots'][sl['i']]['who'] is not None:
            continue
        taken = {x['who'] for x in v['slots'] if x['who'] is not None}
        for st in sorted(v['staff'], key=lambda m: (m['duty'], -m['sk'])):
            if st['i'] in taken or st['off'] or st['rest'] or st['r'] != sl['role'] or str(st['i']) in sl['bar']:
                continue
            j.act('pm_of_plan', slot=sl['i'], mate=st['i'])
            break


class Captains(unittest.TestCase):
    def test_a_captain_who_quits_is_replaced_by_a_captain(self):
        off = OF.new_office('pilot', 7, 1)
        i = next(k for k, st in enumerate(off['staff']) if st['lv'] == 3)
        name = OF._quit('pilot', off, i, 7)
        new = off['staff'][i]
        self.assertEqual((new['r'], new['lv']), ('pl', 3))
        self.assertIn(new['n'], OF.OFFICE['pilot']['cap_hires'])
        self.assertIn('điều từ căn cứ khác', name)
        rookie = next(k for k, st in enumerate(off['staff']) if st['lv'] == 0)
        OF._quit('pilot', off, rookie, 7)
        self.assertEqual(off['staff'][rookie]['lv'], 0)   # a first officer is still replaced by a newcomer
        self.assertIn(off['staff'][rookie]['n'], OF.OFFICE['pilot']['hires'])

    def test_the_police_office_keeps_its_rules(self):
        off = OF.new_office('cand', 7, 1, 5)
        i = next(k for k, st in enumerate(off['staff']) if st['lv'] >= 2)
        OF._quit('cand', off, i, 7)
        self.assertEqual(off['staff'][i]['lv'], 0)
        self.assertIsNone(OF.OFFICE['cand'].get('keep_lv'))
        before = [dict(st) for st in off['staff']]
        for st in off['staff']:
            st['lv'] = 0
        OF.day_roll('cand', off, 7, 2, 5)
        self.assertTrue(all(st['lv'] == 0 for st in off['staff'][:len(before)]))   # no top-up outside the airline

    def test_older_offices_are_topped_up_on_their_next_day(self):
        j = at('pilot', 5, open_day=False)
        j.act('start_day')
        off = office_state(j)
        lose_captains(off)
        budget = off['budget']
        validate_state(j.state)
        day(j)
        j.act('start_day')
        off = office_state(j)
        self.assertEqual(len(captains(off)), OF.CAPTAINS_MIN)
        self.assertGreater(off['budget'], budget)   # the airline pays the new captain's step
        self.assertTrue(any('lên Cơ trưởng' in line for line in off['log']))
        validate_state(j.state)
        # A full office is never touched.
        staff = [dict(st) for st in off['staff']]
        OF._top_up('pilot', off)
        self.assertEqual(staff, off['staff'])

    def test_hard_legs_follow_the_captains_free_today(self):
        j = at('pilot', 5)
        off = office_state(j)
        self.assertEqual(sum(1 for s in office(j)['slots'] if s['need']), 2)
        caps = captains(off)
        self.assertEqual(len(caps), 3)
        caps[0]['duty'] = caps[1]['duty'] = OF.DUTY_MAX   # resting by law
        self.assertEqual(sum(1 for s in office(j)['slots'] if s['need']), 1)
        for st in caps:
            st['duty'] = OF.DUTY_MAX
        v = office(j)
        self.assertEqual(sum(1 for s in v['slots'] if s['need']), 0)
        rookie = next(m for m in v['staff'] if m['t'] == 'Cơ phó cấp thấp')
        j.act('pm_of_plan', slot=0, mate=rookie['i'])   # every leg can be flown, none cancelled

    def test_a_promotion_settles_the_board(self):
        j = at('pilot', 5)
        off = office_state(j)
        lose_captains(off)
        rookie = next(i for i, st in enumerate(off['staff']) if st['r'] == 'pl' and st['lv'] == 0)
        hard = OF._rng('of-hard', pm._seed(j.state), off['day']).sample(range(4), 2)
        # One captain free: only the first hard leg needs one; a step-0 first officer takes the second.
        self.assertEqual([s['i'] for s in office(j)['slots'] if s['need']], [hard[0]])
        j.act('pm_of_plan', slot=hard[1], mate=rookie)
        # ⬆️ Thăng chức at step 5 (F#223): a second captain makes the second leg hard again; the pick that no longer
        # fits is taken off the board.
        tin = next(i for i, st in enumerate(off['staff']) if st['r'] == 'pl' and st['lv'] == 1)
        off['staff'][tin]['sk'] = 75
        j.act('pm_of_hr', mate=tin, act='promote')
        self.assertEqual(office_state(j)['staff'][tin]['lv'], 2)
        self.assertEqual(sorted(s['i'] for s in office(j)['slots'] if s['need']), sorted(hard))
        self.assertIsNone(office_state(j)['plan'][hard[1]])
        validate_state(j.state)

    def test_one_captain_left_can_still_earn_the_step(self):
        """The F#223 office: one captain left. A careful player (rota, inbox answered) now makes 5 good days."""
        j = at('pilot', 5, open_day=False)
        j.act('start_day')
        lose_captains(office_state(j))
        good = 0
        for _ in range(12):
            if not j.c['open']:
                j.act('start_day')
            plan_rota(j)
            answer_inbox_well(j)
            r = day(j)
            o = r['summary']['promo']['office']
            good += bool(o['good'])
            self.assertFalse(any(line.startswith('❌') for line in o['lines']), o['lines'])   # nothing cancelled
        self.assertGreaterEqual(good, 5)
        self.assertGreaterEqual(office_state(j)['kpi']['good'], 5)
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
