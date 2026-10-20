"""Cross-career contracts for the four long-play additions."""
import unittest
import copy

from game.engine import new_state, migrate_state, validate_state
from game.content import CAREERS

from game.careers import ORDER

NEW = ('art_studio', 'lawyer', 'laundry', 'post_office')


class Registration(unittest.TestCase):
    def test_new_careers_have_stable_appended_ids(self):
        self.assertEqual(ORDER[-9:], NEW + ('customs', 'hotel', 'banquet', 'reception', 'radio'))   # 🛃 customs (16/10), 🛎️ hotel, 👨‍🍳 banquet, 🔑 reception and 📻 radio appended after the four
        self.assertEqual(len(ORDER), len(set(ORDER)))

    def test_fifty_career_save_gains_four_without_resetting_old_work(self):
        self.assertEqual(len(CAREERS),58)
        state=new_state();state.pop('check',None);state=migrate_state(state);validate_state(state)
        for cid in NEW:state['careers'].pop(cid)
        old=copy.deepcopy(state['careers'])
        migrated=migrate_state(state)
        validate_state(migrated)
        self.assertEqual(len(migrated['careers']),58)
        self.assertEqual({cid:migrated['careers'][cid] for cid in old},old)
        self.assertEqual(len(state['careers']),54)
        self.assertEqual(migrate_state(migrated),migrated)


if __name__ == '__main__':
    unittest.main()
