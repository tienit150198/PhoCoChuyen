"""career_summary (the other careers in every response) without the full views it used to build."""
import unittest

from game import employment as emp, inventory as inv
from game.engine import career_summary, public_state
from tests.helpers import Journey


class CareerSummaryTests(unittest.TestCase):
    def test_other_career_advertises_active_staff_without_full_payload(self):
        j=Journey('accounting')
        j.act('ops_hire',candidate='accounting-staff-1',confirm=True)
        summary=career_summary(j.c,'accounting')
        self.assertTrue(summary['business_running'])
        self.assertNotIn('ops',summary)

    def test_summary_matches_the_full_views(self):
        j = Journey('milk_tea')
        j.act('advance')
        for cid, c in j.state['careers'].items():
            full = emp.public(c, cid)
            s = career_summary(c, cid)
            self.assertEqual(s['job'], dict(required=full['required'], status=full['status']), cid)
            self.assertEqual(s['inventory'], bool(inv.public(c, cid)), cid)

    def test_pay_per_day_for_the_career_list(self):
        """#406: the career list shows ~xu/ngày from what the game already knows: the last closed shift there
        (career_summary last_net), else a contract job's posted salary range (catalogue pay). A shop has none."""
        from game.content import public_content
        j = Journey('milk_tea')
        self.assertNotIn('last_net', career_summary(j.c, 'milk_tea'))
        j.act('end_day', carry_event=True)
        net = j.c['shift_summary']['net']
        self.assertEqual(career_summary(j.c, 'milk_tea')['last_net'], net)
        cat = {c['id']: c for c in public_content()['catalogue']}
        for cid, c in cat.items():
            posts = [p['salary'] for p in emp.postings(cid)]
            if posts:
                self.assertEqual(c['pay'], [min(p[0] for p in posts), max(p[1] for p in posts)], cid)
            else:
                self.assertNotIn('pay', c, cid)
        if 'hotel' in cat:
            self.assertEqual(cat['hotel']['pay'], [52, 66])

    def test_view_has_summaries_and_one_full_career(self):
        v = public_state(Journey('grocery').state)
        self.assertEqual(v['focus'], 'grocery')
        self.assertNotIn('summary', v['careers']['grocery'])
        self.assertTrue(all(c.get('summary') for cid, c in v['careers'].items() if cid != 'grocery'))


if __name__ == '__main__':
    unittest.main()
