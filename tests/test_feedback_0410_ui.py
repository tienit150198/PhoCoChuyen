"""Render the actual browser modules with public state from the game engine."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from game.content import public_content
from game.engine import public_state
from tests import test_feedback_police as police_fixture
from tests import test_homestay_reservations as home_fixture

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    police = police_fixture.PoliceReportTests()
    police.setUp()
    p = police.post()
    before = public_state(police.j.state)
    police.j.act('fb_police', post=p['id'], confirm=True)
    after = public_state(police.j.state)
    home = home_fixture.ReservationTests()
    home.setUp()
    free = public_state(home.j.state)
    home.ota()
    busy = public_state(home.j.state)
    home.data['ota'] = []
    home.j.act('hs_hold', rooms=['thong'])
    held = public_state(home.j.state)
    home.ota()
    stale = public_state(home.j.state)
    return dict(content=public_content(), post=p['id'], police_before=before, police_after=after,
                home_free=free, home_busy=busy, home_held=held, home_stale=stale)


class BrowserModuleTests(unittest.TestCase):
    def test_review_and_homestay_actions_match_public_state(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node unavailable')
        run = subprocess.run([node, 'tests/feedback_0410_ui.mjs'], input=json.dumps(fixtures()),
                             cwd=ROOT, text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
