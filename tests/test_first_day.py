"""Day one for a brand-new story player: every chapter-1 workplace opens and plays."""
import unittest

from game import employment as emp
from game import journey as jr
from game.content import CAREERS
from game.engine import GameError, apply_action, new_state, validate_state

CH1 = [c for c in jr.CH_UNLOCKS[1] if c in CAREERS]


def story_state():
    s = new_state()
    jr.enable_story(s, 777)
    s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
    return s


class FirstDay(unittest.TestCase):
    def test_every_chapter_one_place_opens_day_one(self):
        for cid in CH1:
            with self.subTest(career=cid):
                s, _ = apply_action(story_state(), cid, 'select_career', {})
                s, _ = apply_action(s, cid, 'start_day', {})
                c = s['careers'][cid]
                self.assertTrue(c['open'])
                self.assertTrue(any(t['status'] not in ('completed', 'cancelled') for t in c['tasks']))
                validate_state(s)

    def test_delivery_takes_a_new_player_on_probation(self):
        if 'delivery' not in CH1:
            self.skipTest('delivery is not in chapter 1')
        s, r = apply_action(story_state(), 'delivery', 'select_career', {})
        job = s['careers']['delivery']['job']
        self.assertEqual(job['status'], 'hired')
        self.assertTrue(job['probation'])
        self.assertGreater(job['probation_left'], 0)
        self.assertEqual(job['history'][0]['event'], 'first_day')
        self.assertIn('Thử việc', r['message'])
        self.assertTrue(r['hired'])
        validate_state(s)

    def test_only_a_never_used_record_and_only_in_the_story(self):
        # Without the story (tests, dev) the hiring pipeline stays as it was.
        s = new_state()
        s, _ = apply_action(s, 'delivery', 'select_career', {})
        self.assertEqual(s['careers']['delivery']['job']['status'], 'none')
        with self.assertRaises(GameError):
            apply_action(s, 'delivery', 'start_day', {})
        # A player who quit (history kept) is not hired again for free.
        s = story_state()
        c = s['careers']['delivery']
        c['job']['history'] = [dict(day=1, event='quit', posting='dl-rider')]
        self.assertIsNone(emp.first_day_hire(s, c, 'delivery'))
        self.assertEqual(c['job']['status'], 'none')

    def test_later_chapters_keep_their_pipeline(self):
        s = story_state()
        later = [k for n in (2, 3, 4, 5, 6) for k in jr.CH_UNLOCKS.get(n, ()) if k in s['careers'] and emp.required(k)]
        for cid in later:
            self.assertIsNone(emp.first_day_hire(s, s['careers'][cid], cid))

    def test_patience_waits_while_learning_a_place(self):
        from unittest import mock
        from game import engine
        from game import experiences

        def impatient(c, action, p, before):  # every action costs every open job 10 patience
            for t in c['tasks']:
                if 'patience' in t:
                    t['patience'] = max(25, t['patience'] - 10)

        def play(served):
            s, _ = apply_action(story_state(), 'grocery', 'select_career', {})
            s['careers']['grocery']['metrics']['served'] = served
            s, _ = apply_action(s, 'grocery', 'start_day', {})
            tid = s['careers']['grocery']['tasks'][0]['id']
            with mock.patch.object(experiences, 'update_patience', impatient):
                s, _ = apply_action(s, 'grocery', 'ask', {'task': tid})
            validate_state(s)
            return [t['patience'] for t in s['careers']['grocery']['tasks']]

        self.assertTrue(all(v == 100 for v in play(0)))
        self.assertTrue(all(v == 100 for v in play(engine.LEARNING_TASKS - 1)))
        self.assertTrue(all(v < 100 for v in play(engine.LEARNING_TASKS)))


if __name__ == '__main__':
    unittest.main()
