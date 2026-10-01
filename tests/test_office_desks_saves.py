"""The Cánh Diều desks (hr_admin, secretary, it_helpdesk) joining saves made before they existed:
they are added fresh, nothing else in the save changes, story players already in chapter 5 find
them open, and a contract is still needed before the first day."""
import json
import unittest

from game import journey as jr
from game.careers import PLUGINS
from game.content import initial_career
from game.engine import GameError, apply_action, migrate_state, new_state, validate_state

NEW = tuple(cid for cid in ('hr_admin', 'secretary', 'it_helpdesk') if cid in PLUGINS)


def dump(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def old_save(chapter):
    s = new_state()
    jr.enable_story(s, 4242)
    s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
    s, _ = apply_action(s, 'milk_tea', 'select_career', {})
    s, _ = apply_action(s, 'milk_tea', 'start_day', {})
    for cid in NEW:
        s['careers'].pop(cid)
    j = s['journey']
    j['chapter'] = chapter
    j['unlocked'] = [cid for n in range(1, min(chapter, jr.LAST) + 1) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
    j['done'] = list(range(1, chapter))
    return s


@unittest.skipUnless(NEW, 'the Cánh Diều desks are filtered out by MNL_CAREERS')
class OldSaves(unittest.TestCase):
    def test_desks_join_fresh_and_nothing_else_moves(self):
        s = old_save(5)
        before = {cid: dump(c) for cid, c in s['careers'].items()}
        wallet = s['journey']['wallet']
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        for cid in NEW:
            self.assertEqual(dump(m['careers'][cid]), dump(initial_career(cid)), cid)
        for cid, raw in before.items():
            self.assertEqual(dump(m['careers'][cid]), raw, cid)
        self.assertEqual(m['journey']['wallet'], wallet)
        self.assertEqual(dump(migrate_state(json.loads(json.dumps(m)))), dump(m))

    def test_chapter_five_players_find_them_open_but_must_be_hired(self):
        m = migrate_state(json.loads(json.dumps(old_save(5))))
        for cid in NEW:
            self.assertIn(cid, m['journey']['unlocked'])
            self.assertTrue(jr.is_unlocked(m, cid))
        m, _ = apply_action(m, 'milk_tea', 'end_day', {'carry_event': True})
        m, _ = apply_action(m, 'secretary', 'select_career', {})
        with self.assertRaises(GameError) as cm:
            apply_action(m, 'secretary', 'start_day', {})
        self.assertEqual(cm.exception.code, 'not_hired')
        validate_state(m)

    def test_early_players_meet_them_later(self):
        m = migrate_state(json.loads(json.dumps(old_save(2))))
        validate_state(m)
        for cid in NEW:
            self.assertIn(cid, m['careers'])
            self.assertNotIn(cid, m['journey']['unlocked'])
            self.assertIn(cid, jr.CH_UNLOCKS[5])


if __name__ == '__main__':
    unittest.main()
