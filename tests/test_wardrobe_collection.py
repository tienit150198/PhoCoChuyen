"""Feedback #152: bun hairstyles and full dresses survive the wardrobe lifecycle."""
import unittest
import shutil
import subprocess
from pathlib import Path

from game import wardrobe as wd
from game.engine import GameError, migrate_state, validate_state
from tests.test_wardrobe import story, act

NEW = {'toc_bui_cao': ('hair', 50), 'toc_bui_doi': ('hair', 60), 'toc_bui_thap': ('hair', 45),
       'dam_cong_chua': ('top', 160), 'dam_du_tiec': ('top', 180), 'dam_yem': ('top', 120)}


class Collection(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the shared character painters')
    def test_character_painters(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', str(root / 'tests' / 'wardrobe_collection.mjs')],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_purchase_equip_recolor_and_reload(self):
        s = story(wallet=2000)
        bottom = s['wardrobe']['look']['bottom']
        for iid, (slot, price) in NEW.items():
            with self.subTest(item=iid):
                self.assertEqual(wd.INDEX[iid]['price'], price)
                with self.assertRaises(GameError):
                    act(s, 'jr_wd_wear', look={slot: iid})
                before = s['journey']['wallet']
                s, _ = act(s, 'jr_wd_buy', item=iid, wear=False)
                self.assertEqual(before - s['journey']['wallet'], price)
                s, _ = act(s, 'jr_wd_wear', look={slot: iid})
                self.assertEqual(s['wardrobe']['look'][slot], iid)
                if slot == 'top':
                    s, _ = act(s, 'jr_wd_color', item=iid, color='mint', buy=True)
                    self.assertEqual(wd.look_of(s)['tint'][iid], 'mint')
                s = migrate_state(s)
                validate_state(s)
                self.assertEqual(s['wardrobe']['look'][slot], iid)
        self.assertEqual(s['wardrobe']['look']['bottom'], bottom)

    def test_staff_prices_and_old_save_defaults(self):
        s = story(wallet=2000)
        s['careers']['clothing']['started'] = True
        for iid, (_, price) in NEW.items():
            before = s['journey']['wallet']
            s, _ = act(s, 'jr_wd_buy', item=iid)
            self.assertEqual(before - s['journey']['wallet'], price - price * 20 // 100)
        del s['wardrobe']
        migrated = migrate_state(s)
        self.assertEqual(migrated['wardrobe']['look'], wd.default_look('female'))
        validate_state(migrated)
