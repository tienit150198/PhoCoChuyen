"""Tutorial flags in the synced settings: the first-run tour and the announcements seen."""
import copy
import unittest

from game.engine import GameError, apply_action, new_state, validate_state


class TutorialSettingsTests(unittest.TestCase):
    def test_new_saves_start_unseen(self):
        s = new_state()
        self.assertIs(s['settings']['tutorialDone'], False)
        self.assertEqual(s['settings']['notesSeen'], '')

    def test_tour_done_is_a_bool(self):
        s, _ = apply_action(new_state(), None, 'settings', {'tutorialDone': True})
        self.assertIs(s['settings']['tutorialDone'], True)
        with self.assertRaises(GameError):
            apply_action(new_state(), None, 'settings', {'tutorialDone': 'yes'})

    def test_notes_seen_keeps_clean_ids(self):
        s, _ = apply_action(new_state(), None, 'settings', {'notesSeen': 'guide-v1,,summer-2'})
        self.assertEqual(s['settings']['notesSeen'], 'guide-v1,summer-2')
        for bad in ('Guide V1', '<b>', 'x' * 400, ','.join(f'n{i}' for i in range(13)), 7):
            with self.assertRaises(GameError):
                apply_action(new_state(), None, 'settings', {'notesSeen': bad})

    def test_older_saves_without_the_keys_can_set_them(self):
        s = new_state()
        del s['settings']['tutorialDone'], s['settings']['notesSeen']
        validate_state(copy.deepcopy(s))
        s, _ = apply_action(s, None, 'settings', {'tutorialDone': True, 'notesSeen': 'guide-v1'})
        self.assertEqual((s['settings']['tutorialDone'], s['settings']['notesSeen']), (True, 'guide-v1'))

    def test_import_checks_the_flags(self):
        s = new_state()
        s['settings']['notesSeen'] = 'guide-v1'
        validate_state(copy.deepcopy(s))
        s['settings']['tutorialDone'] = 'no'
        with self.assertRaises(GameError):
            validate_state(s)


if __name__ == '__main__':
    unittest.main()
