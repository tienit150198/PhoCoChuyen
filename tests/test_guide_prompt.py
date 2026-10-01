"""The guide card the first time at each workplace (public/js/tutorial/announce.js, store.js): once per
workplace, never again after "Bỏ qua" or "Xem hướng dẫn", carried in settings.notesSeen (one packed id the
server already accepts). Runs tests/guide_prompt.mjs with node when it is installed."""
import shutil
import subprocess
import json
import unittest
from pathlib import Path

from game.engine import apply_action, new_state, validate_state

ROOT = Path(__file__).resolve().parents[1]


class GuideCard(unittest.TestCase):
    def test_browser_rules(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        careers = list(new_state()['careers'])
        out = subprocess.run([node, str(ROOT / 'tests' / 'guide_prompt.mjs'), json.dumps(careers)], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_packed_id_is_a_valid_seen_flag(self):
        # Every workplace marked: "gd-" + 6 base-32 digits today; up to 105 workplaces fit in 24 characters.
        s = new_state()
        s, _ = apply_action(s, None, 'settings', {'notesSeen': 'onb1,h-job,gd-vvvvv7'})
        self.assertEqual(s['settings']['notesSeen'], 'onb1,h-job,gd-vvvvv7')
        validate_state(s)
        s, _ = apply_action(s, None, 'settings', {'notesSeen': 'gd-' + 'v' * 21})
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
