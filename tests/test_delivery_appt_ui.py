"""📅 Đơn hẹn giờ: render the real courier page (public/js/careers/delivery.js) with public state from the engine."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game.content import public_content
from game.engine import public_state
from tests import test_delivery_appt as T

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    out = dict(content=public_content())
    day, slot = T.find(T.plain)
    j = T.Journey('delivery', slot=slot, day=day)
    out['board_new'] = public_state(j.state)
    j, tid = T.journey()
    T.to_door(j, tid)
    a = T.appt(j, tid)
    out['door_early'] = public_state(j.state)
    T.data(j)['clock'] = a['end'] - 5
    out['door_soon'] = public_state(j.state)
    T.data(j)['clock'] = a['end'] + 7
    out['door_late'] = public_state(j.state)
    out['task'] = tid
    out['window'] = [a['start'], a['end']]
    return out


class DeliveryApptPage(unittest.TestCase):
    def test_page_shows_the_window_countdown_and_choices(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node unavailable')
        run = subprocess.run([node, 'tests/delivery_appt_ui.mjs'], input=json.dumps(fixtures()), text=True,
                             capture_output=True, cwd=ROOT, encoding='utf-8', timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
