"""06/10 hotfix: a brand-new player whose first job is at an office desk that never tips cash (corp_accounting,
hi 0) could not submit it: the first-job welcome became a 0-xu cash tip that validate refused ("Kết quả tip của
công việc sai."). The welcome is now a gift there."""
import copy
import unittest
from unittest import mock

from game import accounting_jobs as aj, employment as emp, tips
from game.engine import apply_action, validate_state
from tests.test_accounting_jobs import at, paper, story, with_certs


class OfficeFirstJobWelcome(unittest.TestCase):
    def test_first_corp_accounting_job_submits_with_a_gift_welcome(self):
        s = with_certs(story(1), ['basic'])
        s['careers']['corp_accounting']['job'] = emp.hired_record('corp_accounting')
        with mock.patch.object(aj, 'now', return_value=at('2026-10-06')):
            s, _ = apply_action(s, 'corp_accounting', 'select_career')
            s, _ = apply_action(s, 'corp_accounting', 'start_day', {'acct_check': paper(s, 'corp_accounting')})
            tid = s['careers']['corp_accounting']['active_task']
            t = next(x for x in s['careers']['corp_accounting']['tasks'] if x['id'] == tid)
            s, _ = apply_action(s, 'corp_accounting', 'ask', dict(task=tid))
            for d in t['docs']:
                s, _ = apply_action(s, 'corp_accounting', 'ca_open', dict(task=tid, doc=d['id']))
            t = next(x for x in s['careers']['corp_accounting']['tasks'] if x['id'] == tid)
            for case in t['cases']:
                tr = case['_truth']
                if tr['v'] != 'approve':
                    s, _ = apply_action(s, 'corp_accounting', 'ca_circle', dict(task=tid, case=case['id'], zone=tr['z'][0]))
                s, _ = apply_action(s, 'corp_accounting', 'ca_stamp', dict(task=tid, case=case['id'], verdict=tr['v']))
            self.assertEqual(tips.norm('corp_accounting')['hi'], 0)
            s, _ = apply_action(copy.deepcopy(s), 'corp_accounting', 'ca_submit', dict(task=tid, confirm=True))
        validate_state(s)
        for x in s['careers']['corp_accounting']['life'].get('tip_day', []):
            self.assertFalse(x.get('kind') == 'cash' and not x.get('amount'), x)


if __name__ == '__main__':
    unittest.main()
