"""Hiring: work starts only after the interview, except for a lucky boss offer."""
import copy
import os
import unittest

from game import employment as emp
from game.engine import GameError, apply_action, new_state, validate_state


def office():
    return next(c for c in sorted(new_state()['careers']) if emp.required(c))


def state_at(career, day):
    s = new_state()
    c = s['careers'][career]
    c['day'] = day
    return s


def apply_until(career, direct):
    """Find a day on which applying does (or doesn't) bring a direct offer."""
    post = emp.postings(career)[0]
    for day in range(1, 500):
        s = state_at(career, day)
        r = emp.action(s, s['careers'][career], career, 'job_apply', {'posting': post['id']})
        if bool(r.get('direct_offer')) == direct:
            return s, r
    raise AssertionError('no matching day')


class HiringLuck(unittest.TestCase):
    def setUp(self):
        self.career = office()
        self.old = os.environ.pop('MNL_DEV', None)

    def tearDown(self):
        if self.old is not None:
            os.environ['MNL_DEV'] = self.old

    def test_quick_hire_needs_dev_flag(self):
        s = new_state()
        post = emp.postings(self.career)[0]
        with self.assertRaises(GameError):
            emp.action(s, s['careers'][self.career], self.career, 'job_quick', {'posting': post['id'], 'confirm': True})
        self.assertEqual(s['careers'][self.career]['job']['status'], 'none')

    def test_cannot_work_while_applying(self):
        s, r = apply_until(self.career, direct=False)
        self.assertEqual(s['careers'][self.career]['job']['status'], 'applying')
        s, _ = apply_action(s, self.career, 'select_career', {})
        with self.assertRaises(GameError):
            apply_action(s, self.career, 'start_day', {})

    def test_direct_offer_then_accept_then_work(self):
        s, r = apply_until(self.career, direct=True)
        job = s['careers'][self.career]['job']
        self.assertEqual(job['status'], 'offer')
        self.assertTrue(job['offer']['direct'])
        self.assertIn(r['message'], job['application']['feedback'])
        validate_state(s)
        # Still has to sign before working.
        s, _ = apply_action(s, self.career, 'select_career', {})
        with self.assertRaises(GameError):
            apply_action(s, self.career, 'start_day', {})
        s, _ = apply_action(s, self.career, 'job_negotiate', {})
        s, _ = apply_action(s, self.career, 'job_accept', {'confirm': True})
        self.assertEqual(s['careers'][self.career]['job']['status'], 'hired')
        s, _ = apply_action(s, self.career, 'start_day', {})
        self.assertTrue(s['careers'][self.career]['open'])

    def test_direct_offer_rate_is_rare(self):
        post = emp.postings(self.career)[0]
        hits = 0
        for day in range(1, 401):
            s = state_at(self.career, day)
            hits += bool(emp.action(s, s['careers'][self.career], self.career, 'job_apply', {'posting': post['id']}).get('direct_offer'))
        self.assertTrue(10 <= hits <= 80, hits)

    def test_reapply_same_day_does_not_reroll(self):
        s, r = apply_until(self.career, direct=False)
        c = s['careers'][self.career]
        emp.action(s, c, self.career, 'job_withdraw', {})
        r2 = emp.action(s, c, self.career, 'job_apply', {'posting': emp.postings(self.career)[0]['id']})
        self.assertFalse(r2.get('direct_offer'))

    def test_meet_boss_is_deterministic_and_valid(self):
        found = None
        for day in range(1, 2000):
            s = new_state()
            s['seq'] = day
            before = copy.deepcopy(s)
            got = emp.meet_boss(s, 'grocery' if 'grocery' in s['careers'] else 'mother_baby', 1)
            if got:
                found = (before, got, s)
                break
        self.assertIsNotNone(found)
        before, got, after = found
        again = copy.deepcopy(before)
        self.assertEqual(emp.meet_boss(again, 'grocery' if 'grocery' in again['careers'] else 'mother_baby', 1), got)
        job = after['careers'][got['career']]['job']
        self.assertEqual(job['status'], 'offer')
        self.assertTrue(emp.required(got['career']))
        validate_state(after)

    def test_meet_boss_skips_jobs_you_have(self):
        s = new_state()
        for k in s['careers']:
            if emp.required(k):
                s['careers'][k]['job'] = emp.hired_record(k)
        for seq in range(0, 3000):
            s['seq'] = seq
            self.assertIsNone(emp.meet_boss(s, 'mother_baby', 1))


if __name__ == '__main__':
    unittest.main()
