"""Exported paintings must be valid XML for room-photo image decoding."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from xml.etree import ElementTree

from game.auction_content import ITEMS


@unittest.skipUnless(shutil.which('node'), 'Node.js required to render shared SVGs')
class PaintingExports(unittest.TestCase):
    def test_every_catalogue_painting_exports_valid_svg(self):
        result = subprocess.run(
            ['node', '--input-type=module', '-e',
             "import {PAINTINGS,paintingSVG} from './public/js/v4/auction-art.js';"
             "console.log(JSON.stringify(Object.fromEntries(Object.keys(PAINTINGS)"
             ".map(id=>[id,paintingSVG(id)]))));"],
            cwd=Path(__file__).resolve().parents[1], check=True,
            capture_output=True, text=True, encoding='utf-8')
        paintings = json.loads(result.stdout)
        self.assertEqual(set(paintings), {x['id'] for x in ITEMS if x['kind'] == 'art'})
        for iid, svg in paintings.items():
            with self.subTest(painting=iid):
                self.assertEqual(ElementTree.fromstring(svg).tag,
                                 '{http://www.w3.org/2000/svg}svg')
