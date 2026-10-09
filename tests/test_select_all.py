""""Tất cả" (feedback #290): Lắp tất cả / Thuê tất cả at a counter and Cả đội vào ca in Sổ tiệm reuse the per-item
commands one at a time (public/js/v4/select-all.js). Here the client's plan is computed by node from real states, then
sent exactly like the client does: the server takes what the money and the places allow, refuses the next step without
changing anything, and the save stays valid. No server code changed, so the saves are the same as 1.9.28's."""
import copy
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from game import quay as qy
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey
from tests.test_quay import ST, owner

ROOT = Path(__file__).resolve().parents[1]


def plan(**x):
    out = subprocess.run(['node', 'tests/select_all.mjs', '--plan'], cwd=ROOT, input=json.dumps(x), capture_output=True,
                         text=True, encoding='utf-8', check=True)
    return json.loads(out.stdout)


def render_staff(state, career):
    from game import operations
    x = dict(career=career, state=public_state(state), operations=operations.content())
    out = subprocess.run(['node', 'tests/select_all.mjs', '--render'], cwd=ROOT, input=json.dumps(x), capture_output=True,
                         text=True, encoding='utf-8', check=True)
    return out.stdout


def run_all(s, career, action, payloads):
    """select-all.js runAll: one command at a time, stop at the first refusal (which must change nothing)."""
    done = 0
    for p in payloads:
        before = copy.deepcopy(s)
        try:
            s, _ = apply_action(s, career, action, p)
        except GameError as e:
            assert s == before
            return s, done, e
        validate_state(s)
        done += 1
    return s, done, None


class QuaySelectAll(unittest.TestCase):
    def counter(self, place, wallet):
        s = owner(50000)
        s, _ = apply_action(s, None, 'jr_quay_open', dict(trade='milk_tea', place=place, name='Trà Mây', confirm=True))
        s['journey']['wallet'] = wallet
        validate_state(s)
        return s

    def test_buy_all_installs_what_the_wallet_pays_cheapest_first(self):
        s = self.counter('sap', 800)   # camera 140 + tủ vệ sinh 280 + chuông 300 fit, chống chập 400 does not
        j = public_state(s)['journey']
        st = j['quay']['stalls'][0]
        p = plan(kind='buy', catalog=qy.catalogue()['items'], owned=st['items'], place=st['place'], journey=j)
        self.assertEqual([i['id'] for i in p['todo']], ['camera', 'hygiene', 'alarm', 'surge', 'bang', 'tu', 'ket'])
        self.assertEqual(p['total'], sum(it['price']['sap'] for it in qy.ITEMS.values()))
        self.assertEqual([i['id'] for i in p['fit']], ['camera', 'hygiene', 'alarm'])
        self.assertEqual(p['fitTotal'], 720)
        s, done, err = run_all(s, None, 'jr_quay_buy', [dict(stall=st['id'], item=i['id'], confirm=True) for i in p['fit']])
        self.assertEqual((done, err), (3, None))
        self.assertEqual(ST(s)['items'], ['camera', 'hygiene', 'alarm'])
        self.assertEqual(s['journey']['wallet'], 80)
        # The rest: the next tap is the server's own refusal, nothing taken.
        s, done, err = run_all(s, None, 'jr_quay_buy', [dict(stall=st['id'], item='surge', confirm=True)])
        self.assertEqual(done, 0)
        self.assertEqual(err.code, 'no_money')

    def test_buy_all_stops_cleanly_when_the_money_moved_after_the_confirm(self):
        s = self.counter('sap', 5000)
        j = public_state(s)['journey']
        st = j['quay']['stalls'][0]
        p = plan(kind='buy', catalog=qy.catalogue()['items'], owned=st['items'], place=st['place'], journey=j)
        self.assertEqual(len(p['fit']), 7)
        s['journey']['wallet'] = 750   # 140 + 280 + 300 fit, then 400 does not   # spent elsewhere between the confirm and the run: a stale client total
        s, done, err = run_all(s, None, 'jr_quay_buy', [dict(stall=st['id'], item=i['id'], confirm=True) for i in p['fit']])
        self.assertEqual(done, 3)
        self.assertEqual(err.code, 'no_money')
        self.assertEqual(ST(s)['items'], ['camera', 'hygiene', 'alarm'])
        self.assertEqual(s['journey']['wallet'], 30)
        self.assertGreaterEqual(s['journey']['wallet'], 0)

    def test_hire_all_fills_only_the_free_places(self):
        s = self.counter('kiot', 5000)   # 3 places
        j = public_state(s)['journey']
        st = j['quay']['stalls'][0]
        p = plan(kind='hire', cands=st['cands'], staff=len(st['staff']), slots=qy.PLACES['kiot']['slots'])
        self.assertEqual(len(p), 3)
        s, done, err = run_all(s, None, 'jr_quay_hire', [dict(stall=st['id'], cand=c['id'], wage=c['wage']) for c in p])
        self.assertEqual((done, err), (3, None))
        self.assertEqual([x['id'] for x in ST(s)['staff']], [c['id'] for c in p])
        self.assertEqual([x['wage'] for x in ST(s)['staff']], [c['ask'] for c in st['cands']])
        # Full now: the plan is empty, and a stale one is refused at the first step.
        st2 = public_state(s)['journey']['quay']['stalls'][0]
        self.assertEqual(plan(kind='hire', cands=st2.get('cands', []), staff=len(st2['staff']), slots=3), [])
        s, done, err = run_all(s, None, 'jr_quay_hire', [dict(stall=st['id'], cand=p[0]['id'], wage=p[0]['wage'])])
        self.assertEqual((done, err.code), (0, 'full'))


class ShopShiftAll(unittest.TestCase):
    def setUp(self):
        for target in ('game.workplace_business.refresh', 'game.workplace_business.settle'):
            m = patch(target, return_value=False)
            m.start()
            self.addCleanup(m.stop)

    def test_whole_team_on_and_off_shift(self):
        j = Journey('homestay')
        j.state['settings']['securityEvents'] = False
        j.act('end_day', carry_event=True)
        j.act('ops_move_property', tier='sunny', confirm=True)
        j.act('start_day')
        ids = []
        for n in (1, 2):
            sid = f'homestay-staff-{n}'
            j.act('ops_hire', candidate=sid, confirm=True)
            ids.append(sid)
        staff = lambda: public_state(j.state)['careers']['homestay']['ops']['staff']
        html = render_staff(j.state, 'homestay')
        self.assertNotIn('data-on="1"', html)   # everyone already on shift
        self.assertIn('Cho cả đội nghỉ ca · 2 người', html)
        self.assertEqual(plan(kind='shift', staff=staff(), on=True), [])
        off = plan(kind='shift', staff=staff(), on=False)
        self.assertEqual(off, ids)
        j.state, done, err = run_all(j.state, 'homestay', 'ops_shift', [dict(employee=e, on=False) for e in off])
        self.assertEqual((done, err), (2, None))
        self.assertTrue(all(not e['on_shift'] for e in j.c['ops']['staff'] if e['status'] == 'hired'))
        html = render_staff(j.state, 'homestay')
        self.assertIn('Cả đội vào ca · 2 người', html)
        self.assertNotIn('data-on="0"', html)
        on = plan(kind='shift', staff=staff(), on=True)
        j.state, done, err = run_all(j.state, 'homestay', 'ops_shift', [dict(employee=e, on=True) for e in on])
        self.assertEqual((done, err), (2, None))
        self.assertTrue(all(e['on_shift'] for e in j.c['ops']['staff'] if e['status'] == 'hired'))


if __name__ == '__main__':
    unittest.main()
