"""Backlog #5 (06/10): the 🛵 bike froze in front of a lit junction off the leg (dl_signal refused 104×, the client held
the bike and asked again every 2 s). The client now runs the server's corridor check first, and a refusal frees the
junction. These tests keep both sides on the same rule."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import traffic
from game.careers import delivery as D
from game.engine import GameError
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


class SignalRoute(unittest.TestCase):
    def test_client_corridor_matches_server(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        lit = sorted(traffic.LIT)
        out = subprocess.run([node, str(ROOT / 'tests' / 'delivery_signal_route.mjs')], cwd=ROOT,
                             input=json.dumps(dict(nodes=D.NODES, lit=lit), ensure_ascii=False),
                             capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        client = json.loads(out.stdout)
        j = Journey('delivery')
        asked = refused = 0
        for at in D.NODES:
            for target in D.NODES:
                if target == at:
                    continue
                for i, jj in lit:
                    j.c['ext']['data']['at'] = at   # apply_action returns a fresh state each time
                    try:
                        j.act('dl_signal', target=target, i=i, j=jj, axis='x')
                        ok = True
                    except GameError:
                        ok = False
                    key = f'{at}>{target}:{i},{jj}'
                    self.assertEqual(client[key], ok, key)
                    asked += ok
                    refused += not ok
        # Both kinds exist, so the check is not vacuous.
        self.assertGreater(asked, 100)
        self.assertGreater(refused, 100)

    def test_drive_never_holds_without_limit(self):
        drive = (ROOT / 'public' / 'js' / 'careers' / 'delivery_drive.js').read_text(encoding='utf-8')
        # Off-leg junctions are never asked; a refusal or a slow answer (4 s) frees the junction.
        self.assertIn('!onLeg(o.nodes,o.at,o.target,i,j)', drive)
        self.assertIn('S.lightDenied?.add(key)', drive)
        self.assertIn('S.t-(S.lightAsked||0)<4', drive)
        self.assertNotIn('(!S.lightChallenge||S.lightPending)){S.lightHold=true', drive)


if __name__ == '__main__':
    unittest.main()
