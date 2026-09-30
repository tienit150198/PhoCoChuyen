"""The street trades (fruit stall, rubbish round, drain cleaning) joining saves that were made
before they existed: the new workplaces are added fresh, nothing else in the save changes, story
players past chapter 3 find them unlocked, and the public view never shares the save's containers."""
import copy
import json
import unittest

from game import journey as jr
from game.careers import PLUGINS
from game.content import initial_career
from game.engine import apply_action, migrate_state, new_state, public_state, validate_state
from tests.helpers import Journey

NEW = tuple(cid for cid in ('fruit', 'garbage', 'drain') if cid in PLUGINS)


def dump(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def old_save(chapter):
    """A story save as the live build writes it: none of the street trades, some play elsewhere."""
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


@unittest.skipUnless(NEW, 'the street trades are filtered out by MNL_CAREERS')
class OldSaves(unittest.TestCase):
    def test_new_workplaces_join_fresh_and_nothing_else_moves(self):
        s = old_save(4)
        before = {cid: dump(c) for cid, c in s['careers'].items()}
        wallet = s['journey']['wallet']
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        for cid in NEW:
            self.assertEqual(dump(m['careers'][cid]), dump(initial_career(cid)), cid)
        for cid, raw in before.items():
            self.assertEqual(dump(m['careers'][cid]), raw, cid)
        self.assertEqual(m['journey']['wallet'], wallet)

    def test_players_past_chapter_three_find_them_open(self):
        m = migrate_state(json.loads(json.dumps(old_save(4))))
        for cid in NEW:
            self.assertIn(cid, m['journey']['unlocked'])
            self.assertTrue(jr.is_unlocked(m, cid))
        m, _ = apply_action(m, 'milk_tea', 'end_day', {'carry_event': True})
        m, _ = apply_action(m, 'fruit', 'select_career', {})
        m, _ = apply_action(m, 'fruit', 'start_day', {})
        self.assertTrue(m['careers']['fruit']['open'])
        validate_state(m)

    def test_early_players_meet_them_in_chapter_three(self):
        m = migrate_state(json.loads(json.dumps(old_save(1))))
        validate_state(m)
        for cid in NEW:
            self.assertIn(cid, m['careers'])
            self.assertNotIn(cid, m['journey']['unlocked'])

    def test_a_migrated_save_migrates_to_the_same_bytes_again(self):
        m = migrate_state(json.loads(json.dumps(old_save(4))))
        self.assertEqual(dump(migrate_state(json.loads(json.dumps(m)))), dump(m))


@unittest.skipUnless(NEW, 'the street trades are filtered out by MNL_CAREERS')
class PublicView(unittest.TestCase):
    def test_the_view_never_shares_or_touches_the_save(self):
        def ids(x, out):
            if isinstance(x, (dict, list)):
                out.add(id(x))
                for v in (x.values() if isinstance(x, dict) else x):
                    ids(v, out)
            return out
        for cid in NEW:
            j = Journey(cid)
            for _ in range(3):
                j.act('advance')
            s = j.state
            before = dump(s)
            v = public_state(s)
            self.assertEqual(dump(s), before, cid)
            self.assertFalse(ids(v, set()) & ids(s, set()), cid)
            json.dumps(v['careers'][cid])
            self.assertEqual(dump(public_state(s)), dump(public_state(copy.deepcopy(s))), cid)


if __name__ == '__main__':
    unittest.main()
