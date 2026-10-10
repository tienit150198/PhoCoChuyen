"""Shared avatar presets and accessories retain one identity across both clients and storage."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from game import wardrobe as wd
from game import avatar as avt
from game.engine import public_state, validate_state
from game.storage import Store
from live import faces
from live.street import clean_look
from live import street_data
from tests.test_wardrobe_plus import player

ROOT = Path(__file__).resolve().parents[1]
ACCESSORIES = ('mu_beret', 'mu_cao_boi', 'tai_nghe', 'vuong_mien', 'bang_do_tai_meo', 'vong_hoa', 'khau_trang', 'khan_choang')


class AvatarExpansion(unittest.TestCase):
    def test_server_catalogue_exposes_eight_distinct_valid_presets_and_accessories(self):
        presets = wd.content().get('avatar_presets', [])
        self.assertGreaterEqual(len(presets), 8)
        self.assertEqual(len({p['id'] for p in presets}), len(presets))
        self.assertGreaterEqual(len({(p['face']['hair'], p['face']['head'], p['face']['age']) for p in presets}), 8)
        for preset in presets:
            self.assertTrue(preset['name'])
            self.assertEqual(avt.clean_face(preset['face']), preset['face'])
        for iid in ACCESSORIES:
            self.assertIn(iid, wd.PLUS)
            self.assertEqual(wd.INDEX[iid]['slot'], 'acc')
            self.assertIn(iid, street_data.LOOK_IDS['acc'])
            self.assertIn(iid, street_data.TINTABLE)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for both client renderers')
    def test_purchase_preset_and_tint_survive_store_reload_and_both_mode_readers(self):
        fixtures = []
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'avatars.db')
            try:
                token, _, _ = store.session()
                original = player(wallet=20000)
                with store.connect() as db:
                    db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(original), store.key(token)))
                count = 0
                def command(name, payload):
                    nonlocal count
                    count += 1
                    store.command(token, f'avatar-expansion-{count:03d}', store.read(token)[1], None, name, payload)
                command('jr_wd_buy', {'item': 'mu_bucket'})
                command('jr_wd_unlock', {'color': 'mint'})
                presets = wd.content().get('avatar_presets', [])
                self.assertGreaterEqual(len(presets), 8)
                for iid, preset in zip(ACCESSORIES, presets):
                    before = copy.deepcopy(store.read(token)[0])
                    command('jr_wd_buy', {'item': iid})
                    command('jr_wd_color', {'item': iid, 'color': 'mint'})
                    command('jr_avatar', {'kind': 'face', 'face': preset['face']})
                    store.close_pool()
                    saved, _, _ = store.read(token)
                    validate_state(saved)
                    look = wd.look_of(saved)
                    self.assertEqual(look['acc'], iid)
                    self.assertEqual(look['tint'][iid], 'mint')
                    self.assertEqual(saved['avatar']['face'], preset['face'])
                    self.assertEqual(before['journey']['wallet'] - saved['journey']['wallet'], wd.price(before, iid))
                    self.assertIn('mu_bucket', saved['wardrobe_plus']['owned'])
                    self.assertTrue(set(before['wardrobe_plus']['owned']) <= set(saved['wardrobe_plus']['owned']))
                    remote, _ = clean_look(look, 'female')
                    self.assertEqual(remote['acc'], iid)
                    self.assertEqual(remote['tint'][iid], 'mint')
                    fixtures.append({'state': public_state(saved), 'look': look, 'face': preset['face']})
            finally:
                store.close_pool()
        result = subprocess.run(['node', 'tests/avatar-expansion.mjs', '--snapshots'], cwd=ROOT,
                                input=json.dumps(fixtures), capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rendered = json.loads(result.stdout)
        self.assertEqual(len(rendered), len(ACCESSORIES))
        for fixture, codes in zip(fixtures, rendered):
            self.assertEqual(codes[0], codes[1], 'classic and 2.5D publish the same saved identity')
            self.assertEqual(faces.clean(codes[0]), codes[0], fixture['look']['acc'])


if __name__ == '__main__':
    unittest.main()
