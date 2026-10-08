"""Background music that some players hear and others do not (owner report 08/10/2026): public/js/audio.js and
public/js/v4/music.js are checked with node against a fake AudioContext/fetch/document (tests/audio_resume.mjs):
first tap, hidden/visible, phone interruptions, a stuck clock, failed downloads and decodes, career-switch races,
the iPhone silent switch (silent <audio> keeper on iOS 15–16.3, navigator.audioSession on 16.4+), ducking."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AudioResumeTest(unittest.TestCase):
    def test_scenarios(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'audio_resume.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=180)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
