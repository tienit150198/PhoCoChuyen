"""Shared systems classify four new careers consistently with their work contracts."""
import unittest
from game import journey, operations, career_voice, incident_content, life_content
from game import promotion_content, review_aspects_content, work_gear

NEW = ('art_studio', 'lawyer', 'laundry', 'post_office')


class CreativeCivicBackend(unittest.TestCase):
    def test_unlock_chapters(self):
        chapters = {cid: n for n, ids in journey.CH_UNLOCKS.items() for cid in ids}
        self.assertEqual({cid: chapters.get(cid) for cid in NEW},
                         dict(art_studio=3, lawyer=4, laundry=2, post_office=3))

    def test_employed_careers_are_salaried_and_commercial_ones_are_not(self):
        self.assertEqual(operations.SALARIED, career_voice._SALARIED)
        for cid in NEW:
            employed = cid in ('lawyer', 'post_office')
            self.assertEqual(operations.salaried(cid), employed)
            self.assertEqual(cid in incident_content.EMPLOYEE, employed)
            self.assertEqual(cid in life_content.EMPLOYED, employed)
            self.assertEqual(cid in incident_content.OWNER, not employed)
            self.assertEqual(cid in life_content.OWNERS, not employed)

    def test_shared_words_do_not_call_payroll_a_shop(self):
        for cid in ('lawyer', 'post_office'):
            row = career_voice.terms(cid)
            self.assertFalse(row['commerce'])
            for key in ('books', 'confirm', 'daily', 'end_text'):
                self.assertEqual(career_voice.shop_words(cid, row[key]), [], (cid, key))
            self.assertNotIn('tiền thuê', row['end_text'])
            # Owner 16/10 (F#393): the post office makes it up with a postage refund; the lawyer pays nothing.
            self.assertEqual(career_voice.offer_ok(cid, 'refund'), cid == 'post_office')
        for cid in ('art_studio', 'laundry'):
            self.assertTrue(career_voice.commerce(cid))

    def test_work_colleagues_promotions_gear_and_reviews_exist(self):
        for cid in NEW:
            self.assertIn(cid, incident_content.ALL)
            self.assertIn(cid, life_content.WORK)
            self.assertIn(cid, life_content.FACING)
            self.assertIn(cid, work_gear.NAMES)
            self.assertIn(cid, review_aspects_content.FAMILY)
            titles = promotion_content.EMP_TITLES if cid in ('lawyer', 'post_office') else promotion_content.OWN_TITLES
            self.assertEqual(len(titles[cid]), 7)
            self.assertEqual(len([item for item in work_gear.catalogue() if cid in item['careers']]), 3)

    def test_reviews_have_own_grounded_aspects(self):
        for cid in NEW:
            aspects = [a for a in review_aspects_content.ASPECTS.values() if cid in a['only']]
            self.assertTrue(aspects, cid)
            self.assertTrue(any(a['sig_neg'] and a['sig_pos'] and not a['subjective'] for a in aspects), cid)
            self.assertIn(cid, review_aspects_content.NV_CAREER)

    def test_existing_story_upgrade_adds_only_reached_workplaces(self):
        for chapter in range(1, 5):
            j = journey.initial(True)
            j['chapter'] = chapter
            j['unlocked'] = [c for c in j['unlocked'] if c not in NEW]
            journey.upgrade(j)
            expected = {cid for cid, unlock in [('laundry',2),('art_studio',3),('post_office',3),('lawyer',4)] if unlock <= chapter}
            self.assertEqual(set(j['unlocked']) & set(NEW), expected)


if __name__ == '__main__':
    unittest.main()
