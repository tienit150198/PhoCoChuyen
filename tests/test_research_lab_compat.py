"""🔬 Viện nghiên cứu, Đơn nghiên cứu and rollbacks. The release live before them (2.4.66 at a808cb79):
* loads, validates, migrates and plays a buyer's save holding journey.lab (a running seed batch and recipe, two gadgets)
  and keeps the block untouched (journey allows extra keys); back on this build the effects are there and still work;
* loads a save whose Viện nghiên cứu was never worked: the dormant record is left out of the stored text
  (engine.DORMANT), exactly like hotel/banquet. A save that worked the institute is refused there (2.4.66 requires its
  own career list): never roll back below the build that added the career (the same rule as every career since customs);
* starts on a database at SCHEMA_VERSION 71 holding a settled research order and its research_jobs row: no DDL (the
  version is never lowered), every row kept, the buyer's save read and validated."""
import json

from game import pg_schema
from game import research_lab as rl
from game.careers import farm_plus as fp, kit
from game.engine import initial_career, new_state, validate_state, wake
from tests.helpers import NEWER_THAN_LIVE, unknown_out   # 🔑 careers newer than 2.4.66 as the stored text leaves them out
from tests.test_photo_studio_compat import run
from tests.test_research_lab import LabBase

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
out=[]
for s in json.load(sys.stdin):
    s=migrate_state(s);validate_state(s)   # the read path: its own dormant careers (customs, hotel, banquet) put back
    before=json.dumps(s['journey'].get('lab'),sort_keys=True)
    s['journey']['life_day']+=3
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,json.dumps(s['journey'].get('lab'),sort_keys=True),s])
print(json.dumps(out))
'''

DB_PROG = '''import json,sys
from game.storage import Store
from game.engine import validate_state
store=Store(sys.argv[1],story=True)
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[3].split(',')}
st=store.read(sys.argv[2])[0]
validate_state(st)
out['lab']=st['journey'].get('lab')
store.close_pool()
print(json.dumps(out))
'''


def buyer_save():
    s = new_state()
    s['journey']['story'] = True
    t = int(kit.now())
    lab = rl.initial()
    lab['seed'] = dict(o='sv_' + '1' * 24, n=2, add=1, until=t + 5 * 86400, by='Minh Thư', name='Mây chịu hạn')
    lab['recipe'] = dict(o='sv_' + '2' * 24, n=7, pct=10, per=3, left=21, until=t + 3 * 86400, by='Minh Thư', name='SM-40')
    lab['gadgets'] = [dict(o='sv_' + '3' * 24, kind='fan', name='Quạt Mây Mini', by='Minh Thư', at=t, q=100),
                      dict(o='sv_' + '4' * 24, kind='lamp', name='Đèn học', by='Gia Bảo', at=t, q=80)]
    lab['last'] = dict(giong=t, mon=t, may=t)
    lab['orders'] = ['sv_' + '1' * 24, 'sv_' + '2' * 24, 'sv_' + '3' * 24, 'sv_' + '4' * 24]
    lab['stats'] = dict(seed_units=1, recipe_xu=9, gadgets=2)
    s['journey']['lab'] = lab
    farm = s['careers']['farm']
    farm['started'] = True
    farm['ext'][fp.KEY] = fp.initial(t)
    validate_state(s)
    return s


class Saves(LabBase):
    def test_a_buyer_save_with_the_lab_block_plays_on_2_4_66_and_comes_back(self):
        s = buyer_save()
        self.assertEqual(s['careers']['research'], initial_career('research'))
        self.assertIn('research', NEWER_THAN_LIVE)
        stored = unknown_out(s)   # what the stored text holds for 2.4.66: an untouched institute is left out
        self.assertNotIn('research', stored['careers'])
        got = run(self, PROG, stdin=json.dumps([stored], ensure_ascii=False))
        before, after, back = got[0]
        mine = json.dumps(s['journey']['lab'], sort_keys=True)
        self.assertEqual(before, mine)
        self.assertEqual(after, mine, '2.4.66 keeps journey.lab untouched')
        self.assertTrue(wake(back))
        validate_state(back)
        self.assertEqual(back['journey']['lab'], s['journey']['lab'])
        self.assertEqual(rl.seed_bonus(back, 5, 'ot')[0], 1)   # and it still works here
        validate_state(back)


class Database(LabBase):
    def test_2_4_66_starts_on_schema_71_with_a_settled_research_order(self):
        a, b = self.researcher('rlc_prov'), self.farmer('rlc_buyer')
        self.sell(a, 'may')
        o = self.order(b, a, 'may')
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        self.research(a, o['id'], 'may')
        tables = ('research_jobs', 'svc_orders', 'svc_settings')
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) AS n FROM {t}').fetchone()['n'] for t in tables}
        self.assertTrue(all(before.values()), before)
        got = run(self, DB_PROG, (self.store.path, b, ','.join(tables)))
        self.assertEqual(got['v'], str(pg_schema.SCHEMA_VERSION), 'the old release never lowers the version (no DDL)')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 71)   # research_jobs came at 71 (later steps of other branches stack on it)
        self.assertEqual(got['n'], before, 'every row kept')
        self.assertEqual(got['lab'], self.lab(b), 'the buyer save, with its gadget, reads on 2.4.66')
