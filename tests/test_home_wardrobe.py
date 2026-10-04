import subprocess
import shutil
import unittest
from pathlib import Path


class HomeWardrobe(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for browser-module checks')
    def test_furnished_wardrobe_uses_existing_collection(self):
        subprocess.run(['node','tests/home_wardrobe.mjs'],cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True)
