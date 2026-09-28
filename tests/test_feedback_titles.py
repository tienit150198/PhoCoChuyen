"""Parents' reviews use the player's title once the gender is known."""
import unittest

from game import feedback


class TeacherTitle(unittest.TestCase):
    def test_title_follows_gender(self):
        text = 'Cảm ơn cô/thầy nhiều ạ! Cô/thầy trả lời vậy làm tôi yên tâm.'
        self.assertEqual(feedback.teacher_title({'journey': {'gender': 'male'}}, text),
                         'Cảm ơn thầy nhiều ạ! Thầy trả lời vậy làm tôi yên tâm.')
        self.assertEqual(feedback.teacher_title({'journey': {'gender': 'female'}}, text),
                         'Cảm ơn cô nhiều ạ! Cô trả lời vậy làm tôi yên tâm.')

    def test_unknown_gender_keeps_both(self):
        text = 'Cảm ơn cô/thầy nhiều ạ!'
        self.assertEqual(feedback.teacher_title({}, text), text)
        self.assertEqual(feedback.teacher_title({'journey': {'gender': None}}, text), text)

    def test_new_modes_grade_from_their_own_facts(self):
        t = dict(career='teacher', mistakes=0, patience=100,
                 room=dict(kids=[dict(id='an'), dict(id='vy')], roll={'an': 'present', 'vy': 'present'},
                           tickets={'an': {}, 'vy': {}}, marks={'an': 'praise', 'vy': 'hint'}))
        self.assertTrue(all(x['score'] == 5 for x in feedback._criteria_default({}, t)))
        trip = dict(career='tour_guide', mistakes=0, patience=100, trip=dict(clock=100, limit=120))
        self.assertTrue(all(x['score'] == 5 for x in feedback._criteria_default({}, trip)))
        trip['trip']['clock'] = 130
        self.assertEqual(min(x['score'] for x in feedback._criteria_default({}, trip)), 3)


if __name__ == '__main__':
    unittest.main()
