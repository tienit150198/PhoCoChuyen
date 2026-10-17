"""🏝️ Đảo riêng and rollbacks: saves with journey.island validate, migrate and play on the releases production may be
rolled back to (2.4.34 at 917f0733, the floor 2.4.27 at 04a51030). Those builds keep the block untouched (journey
allows extra keys), never bill it, and accept the wallet rows a 15M–200M purchase or sale writes (each ≤ 10M xu)."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import island as isl
from game.engine import validate_state
from tests.test_bank import act, story
from tests.test_island import buy, next_day, rich

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {'2.4.34': '917f0733', '2.4.27': '04a51030'}

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    # a career a later release added (2.4.34's hotel) is not this tree's business: the island block is
    s['careers']={k:v for k,v in s['careers'].items() if k in CAREERS};j=s['journey']
    j['unlocked']=[c for c in j['unlocked'] if c in CAREERS];j['days']=[d for d in j['days'] if d['c'] in CAREERS]
    validate_state(s);s=migrate_state(s);validate_state(s)
    before=json.dumps(s['journey'].get('island'),sort_keys=True)
    s['journey']['life_day']+=6
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,json.dumps(s['journey'].get('island'),sort_keys=True),s['journey']['wallet'],s['journey']['life_day']])
print(json.dumps(out))
'''


class OldServer(unittest.TestCase):
    """Current saves validate, migrate and take a command on the older trees; the island block survives as it was."""

    def old_tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-island-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_old(self, rev, saves):
        old = self.old_tree(rev)
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', PROG], input=json.dumps(saves), capture_output=True, text=True, cwd=old,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def saves(self):
        a = rich(240_000_000)
        a, _ = buy(a, 'dao_hoang_hon')                    # 20 wallet rows of -10M
        a, _ = buy(a, 'dao_dua')                          # and a second island
        a = next_day(a, 3)                                # fees accruing (not billed yet)
        b = rich(80_000_000)
        b, _ = buy(b, 'dao_san_ho')
        b, _ = act(b, 'jr_island_sell', id='dao_san_ho', confirm=True)   # rows of +10M back, an empty block
        c = rich(32_000_000)
        c, _ = buy(c, 'dao_dua')
        c['journey']['island']['own']['dao_sau_nay'] = dict(d=2, p=150_000_000)   # a newer build's island, kept by shape
        for s in (a, b, c):
            validate_state(s)
        return [a, b, c]

    def check(self, rev):
        saves = self.saves()
        got = self.run_old(rev, saves)
        for s, (before, after, wallet, day) in zip(saves, got):
            mine = json.dumps(s['journey']['island'], sort_keys=True)
            self.assertEqual(before, mine)            # migrate keeps it
            self.assertEqual(after, mine)             # a morning there neither bills nor drops it
            self.assertEqual(wallet, s['journey']['wallet'])
            self.assertEqual(day, s['journey']['life_day'] + 6)
        # back on this build the days the older build ran are billed once (the day counter), nothing lost
        a = saves[0]
        a['journey']['life_day'] += 6
        a, _ = act(a, 'jr_seen', ids=['x'])
        validate_state(a)
        self.assertEqual(sorted(isl.owned(a)), ['dao_dua', 'dao_hoang_hon'])
        self.assertGreater(a['journey']['island']['upk']['paid'], 0)

    def test_saves_play_on_2_4_34(self):
        self.check(RELEASES['2.4.34'])

    def test_saves_play_on_2_4_27(self):
        self.check(RELEASES['2.4.27'])


if __name__ == '__main__':
    unittest.main()
