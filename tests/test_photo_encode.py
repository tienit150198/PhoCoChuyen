"""B10 (07/10): photos sent in a command stay under the 256 KB cap on iPhones too (tests/photo_encode.mjs)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PhotoEncode(unittest.TestCase):
    def test_photo_payload_under_the_command_cap(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'photo_encode.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
