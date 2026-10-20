"""🏗️ Xây trên đảo and rollbacks: saves with journey.islb (and the wallet rows building, upgrading, razing and a sale
wrote) validate, migrate and play on the releases production may be rolled back to (2.4.60 at e05bacf5, the release
before this one; 2.4.34 at 917f0733, the first with islands). Those builds keep the block untouched (journey allows extra
keys), never charge or pay it, and coming back to this build the buildings are still there. 🏡 20/10: a house style in
another colour ('<style>__<n>') is kept by shape there too (never shown, never counted)."""
import copy
import json
import unittest
from unittest.mock import patch

from game import island_build as ib
from game.engine import validate_state
from tests.test_bank import act
from tests.test_island import buy, rich
from tests import test_island_compat as old_compat

RELEASES = {'2.4.60': 'e05bacf5', '2.4.34': '917f0733'}
T0 = 1_800_000_000.0

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    s['careers']={k:v for k,v in s['careers'].items() if k in CAREERS};j=s['journey']
    j['unlocked']=[c for c in j['unlocked'] if c in CAREERS];j['days']=[d for d in j['days'] if d['c'] in CAREERS]
    validate_state(s);s=migrate_state(s);validate_state(s)
    before=json.dumps(s['journey'].get('islb'),sort_keys=True)
    s['journey']['life_day']+=6
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,json.dumps(s['journey'].get('islb'),sort_keys=True),s['journey']['wallet'],s['journey']['life_day']])
print(json.dumps(out))
'''


class Rollback(old_compat.OldServer):   # (the module: its own OldServer tests run there, not here)
    def run_old(self, rev, saves):
        import os
        import subprocess
        import sys
        old = self.old_tree(rev)
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', PROG], input=json.dumps(saves), capture_output=True, text=True, cwd=old,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def saves(self):
        clock = [T0]
        with patch('game.island_build.now', lambda: clock[0]):
            a = rich(330_000_000)
            a, _ = buy(a, 'dao_hoang_hon')
            a, _ = act(a, 'jr_isle_build', island='dao_hoang_hon', plot=0, kind='lau_dai', confirm=True)   # 25M: rows of ≤ 10M
            a, _ = act(a, 'jr_isle_build', island='dao_hoang_hon', plot=23, kind='ben_thuyen', confirm=True)
            clock[0] += 48 * 3600
            a, _ = act(a, 'jr_isle_up', island='dao_hoang_hon', plot=0, confirm=True)                       # 40M upgrade building
            a, _ = act(a, 'jr_isle_raze', island='dao_hoang_hon', plot=23, confirm=True)                    # salvage back
            a, _ = act(a, 'jr_isle_build', island='dao_hoang_hon', plot=2, kind='pho_hoi_an', look=2, confirm=True)   # 🏡 20/10: a style
            a, _ = act(a, 'jr_isle_paint', island='dao_hoang_hon', plot=2, look=1, confirm=True)            # in its colour 'pho_hoi_an__1'
            a, _ = act(a, 'jr_isle_use', trip='ab' * 8, plot=1)
            b = rich(80_000_000)
            b, _ = buy(b, 'dao_san_ho')
            b, _ = act(b, 'jr_isle_build', island='dao_san_ho', plot=9, kind='ben_thuyen', confirm=True)
            b, _ = act(b, 'jr_island_sell', id='dao_san_ho', confirm=True)                                  # sold with it
        for s in (a, b):
            validate_state(s)
        return [a, b]

    def check(self, rev):
        saves = self.saves()
        got = self.run_old(rev, saves)
        for s, (before, after, wallet, day) in zip(saves, got):
            mine = json.dumps(s['journey']['islb'], sort_keys=True)
            self.assertEqual(before, mine)
            self.assertEqual(after, mine)
            # the wallet moves exactly as on this build (2.4.60 bills the island's own monthly fee; the buildings: nothing)
            here = copy.deepcopy(s)
            here['journey']['life_day'] += 6
            here, _ = act(here, 'jr_seen', ids=['x'])
            self.assertEqual(wallet, here['journey']['wallet'] if rev == RELEASES['2.4.60'] else s['journey']['wallet'])
            self.assertEqual(day, s['journey']['life_day'] + 6)
        a = saves[0]
        a['journey']['life_day'] += 6
        a, _ = act(a, 'jr_seen', ids=['x'])
        validate_state(a)
        self.assertEqual(a['journey']['islb']['p']['dao_hoang_hon']['0']['k'], 'lau_dai')
        self.assertEqual(a['journey']['islb']['p']['dao_hoang_hon']['2']['k'], 'pho_hoi_an__1')   # an older build kept it as it was
        self.assertGreater(ib.worth(a['journey']), 0)

    def test_saves_play_on_2_4_60(self):
        self.check(RELEASES['2.4.60'])

    def test_saves_play_on_2_4_34(self):
        self.check(RELEASES['2.4.34'])


for _name in ('test_saves_play_on_2_4_34', 'test_saves_play_on_2_4_27'):   # OldServer's own tests run in their module
    if _name not in Rollback.__dict__:
        setattr(Rollback, _name, None)


if __name__ == '__main__':
    unittest.main()
