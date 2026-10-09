"""F#295/#296 + F#294 on the client: the plans of public/js/v4/quay-manage.js (🔁 Nhập lại như lần trước, 👛 thiếu thì
lấy từ ví, 📋 Quản lý chung) computed by node from real public states and sent exactly like quay.js does (one command
per counter, stop at the first refusal); plus the node checks (✏️ Sửa góp ý, 🏆 Xếp hạng nghề) and the 390 px browser
run of the quay dialog."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import quay_business as qb
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_quay import ST, owner

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
PLAYWRIGHT = Path('C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs')


def plan(**x):
    out = subprocess.run([NODE, 'tests/quay_manage.mjs', '--plan'], cwd=ROOT, input=json.dumps(x), capture_output=True,
                         text=True, encoding='utf-8', check=True)
    return json.loads(out.stdout)


def run_all(s, action, payloads):
    done = 0
    for p in payloads:
        before = copy.deepcopy(s)
        try:
            s, _ = apply_action(s, None, action, p)
        except GameError as e:
            assert s == before
            return s, done, e
        validate_state(s)
        done += 1
    return s, done, None


@unittest.skipUnless(NODE, 'node is required')
class Plans(unittest.TestCase):
    def counters(self):
        s = owner(50000)
        s['careers']['grocery']['metrics']['served'] = 12
        for trade, name in (('milk_tea', 'Trà Một'), ('grocery', 'Tạp Hóa'), ('milk_tea', 'Trà Hai')):
            s, _ = apply_action(s, None, 'jr_quay_open', dict(trade=trade, place='xe', name=name, confirm=True))
        q = s['journey']['quay']['stalls']
        s, _ = apply_action(s, None, 'jr_quay_restock', dict(stall=q[0]['id'], items={'hong_tra': 6, 'tra_dao': 2}))
        s, _ = apply_action(s, None, 'jr_quay_restock', dict(stall=q[2]['id'], items={'hong_tra': 3}))
        validate_state(s)
        return s

    def test_again_for_a_group_pays_each_shortfall_from_the_wallet(self):
        s = self.counters()
        for st in s['journey']['quay']['stalls']:
            st['till'] = st['fund'] = 0
        s['journey']['wallet'] = 1000
        validate_state(s)
        j = public_state(s)['journey']
        groups = plan(kind='groups', journey=j)
        ids = [st['id'] for st in s['journey']['quay']['stalls']]
        self.assertEqual(groups, [['milk_tea', [ids[0], ids[2]]], ['grocery', [ids[1]]]])
        p = plan(kind='againAll', trade='milk_tea', journey=j)
        st0, st2 = ST(s, 0), ST(s, 2)
        cost0 = 6 * qb.unit_cost(st0, 'hong_tra') + 2 * qb.unit_cost(st0, 'tra_dao')
        cost2 = 3 * qb.unit_cost(st2, 'hong_tra')
        self.assertEqual(p['steps'], [dict(stall=ids[0], items={'hong_tra': 6, 'tra_dao': 2}, wallet=True),
                                      dict(stall=ids[2], items={'hong_tra': 3}, wallet=True)])
        self.assertEqual((p['total'], p['short'], p['skip']), (cost0 + cost2, cost0 + cost2, []))
        stock = [dict(ST(s, i)['business']['stock']) for i in (0, 2)]
        s, done, err = run_all(s, 'jr_quay_restock', p['steps'])
        self.assertEqual((done, err), (2, None))
        self.assertEqual(s['journey']['wallet'], 1000 - cost0 - cost2)
        self.assertEqual(ST(s, 0)['business']['stock']['hong_tra'], stock[0]['hong_tra'] + 6)
        self.assertEqual(ST(s, 2)['business']['stock']['hong_tra'], stock[1]['hong_tra'] + 3)

    def test_a_stale_plan_stops_at_the_servers_refusal(self):
        s = self.counters()
        for st in s['journey']['quay']['stalls']:
            st['till'] = st['fund'] = 0
        s['journey']['wallet'] = 1000
        validate_state(s)
        p = plan(kind='againAll', trade='', journey=public_state(s)['journey'])
        self.assertEqual(len(p['steps']), 2)
        s['journey']['wallet'] = qb.unit_cost(ST(s, 0), 'hong_tra') * 6 + qb.unit_cost(ST(s, 0), 'tra_dao') * 2
        validate_state(s)   # spent elsewhere between the confirm and the run: only the first counter is paid
        s, done, err = run_all(s, 'jr_quay_restock', p['steps'])
        self.assertEqual((done, err.code), (1, 'no_money'))
        self.assertEqual(s['journey']['wallet'], 0)

    def test_till_and_open_plans(self):
        s = self.counters()
        ST(s, 0)['till'], ST(s, 1)['till'] = 40, 0
        ST(s, 2)['till'] = 7
        ST(s, 1)['business']['paused'] = True
        validate_state(s)
        j = public_state(s)['journey']
        t = plan(kind='till', journey=j)
        ids = [st['id'] for st in s['journey']['quay']['stalls']]
        self.assertEqual(t, dict(steps=[dict(stall=ids[0]), dict(stall=ids[2])], total=47))
        wallet = s['journey']['wallet']
        s, done, err = run_all(s, 'jr_quay_till', t['steps'])
        self.assertEqual((done, err, s['journey']['wallet']), (2, None, wallet + 47))
        o = plan(kind='open', journey=public_state(s)['journey'])
        self.assertEqual(o['steps'], [dict(stall=ids[1], on=False)])
        s, done, err = run_all(s, 'jr_quay_pause', o['steps'])
        self.assertEqual((done, err, ST(s, 1)['business']['paused']), (1, None, False))
        lines = plan(kind='lines', journey=public_state(s)['journey'])
        self.assertEqual(len(lines), 3)
        self.assertTrue(all({'status', 'low', 'cash', 'stock', 'staff'} <= set(x) for x in lines))


@unittest.skipUnless(NODE, 'node is required')
class NodeChecks(unittest.TestCase):
    def test_plans_feedback_edit_and_rank_shortcut(self):
        r = subprocess.run([NODE, 'tests/quay_manage.mjs'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(PLAYWRIGHT.is_file(), 'playwright is required')
    def test_quay_dialog_at_390px(self):
        r = subprocess.run([NODE, 'tests/quay_manage_browser.mjs'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                           timeout=240)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-4000:])


if __name__ == '__main__':
    unittest.main()
