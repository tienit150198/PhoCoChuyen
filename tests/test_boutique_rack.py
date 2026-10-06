"""F#218 (backlog #10): the clothes-shop scene drew a fixed rail whatever the stock. It now draws the counted-in
rack (data.grid), and the 👚 Giá treo card says when bought goods wait at the door, uncounted."""
import shutil
import subprocess
import unittest
from pathlib import Path

from game.careers import clothing as CL
from game.engine import public_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


class BoutiqueRack(unittest.TestCase):
    def test_scene_rail_follows_stock(self):
        if not shutil.which('node'):
            self.skipTest('node not installed')
        out = subprocess.run(['node', str(ROOT / 'tests' / 'boutique_rack.mjs')], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr[-2000:])

    def test_public_grid_is_what_the_scene_reads(self):
        j = Journey('clothing')
        grid = public_state(j.state)['careers']['clothing']['data']['grid']
        shelf = {'hat', 'belt', 'socks', 'sneaker', 'sandal', 'bag', 'earrings', 'scarf'}
        ids = {it['id'] for it in CL.ITEMS}
        self.assertTrue(shelf <= ids, 'shelf ids in boutique.js must be real clothing items')
        self.assertTrue(set(grid) <= ids)
        self.assertTrue(all(isinstance(n, int) for row in grid.values() for n in row.values()))

    def test_rack_card_nudges_arrived_crates(self):
        js = (ROOT / 'public' / 'js' / 'careers' / 'clothing.js').read_text(encoding='utf-8')
        self.assertIn('ao-crates', js)
        self.assertIn('crates(inv).ready', js)


if __name__ == '__main__':
    unittest.main()
