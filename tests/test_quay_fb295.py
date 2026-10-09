"""F#295/#296 (homestay, 09/10) "quầy của mình": 🔁 Nhập lại như lần trước (the last order, kept on the counter),
👛 the shortfall of a restock paid from the wallet in the same command (no Góp vốn first), 🏗️ Mở rộng quầy (a bigger
place for the same counter, paying the difference), Sổ ví rows split at ±10,000,000, and saves crossing to the
releases production may roll back to (1.9.35 = 32f7ff3c, 1.9.34 = ad81209b)."""
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
from unittest import mock

from game import quay as qy, quay_business as qb, quay_self as qs
from game.engine import GameError, public_state, validate_state
from tests.test_quay import ST, act, opened, refused

ROOT = Path(__file__).resolve().parents[1]
OLD_RELEASES = {'1.9.35': '32f7ff3c', '1.9.34': 'ad81209b'}
DISH = 'hong_tra'


def broke(s):
    """The counter's till and fund are empty (the case the player met: goods cost more than the counter holds)."""
    st = ST(s)
    st['till'] = st['fund'] = 0
    return st


class LastOrder(unittest.TestCase):
    def test_a_restock_is_kept_and_shown_for_next_time(self):
        s = opened('sap', wallet=20000)
        st = ST(s)
        self.assertEqual(qy.public(s)['stalls'][0]['business']['again'], [])
        s, r = act(s, 'jr_quay_restock', stall=st['id'], items={DISH: 7, 'tra_dao': 3})
        st = ST(s)
        self.assertEqual(st['business']['again'], {DISH: 7, 'tra_dao': 3})
        self.assertEqual(public_state(s)['journey']['quay']['stalls'][0]['business']['again'],
                         [dict(id=DISH, qty=7), dict(id='tra_dao', qty=3)])
        s, _ = act(s, 'jr_quay_restock', stall=st['id'], items={'tra_dao': 2})
        self.assertEqual(ST(s)['business']['again'], {'tra_dao': 2})     # always the latest order
        validate_state(s)

    def test_a_refused_restock_keeps_the_old_last_order(self):
        s = opened('xe', wallet=20000)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 2})
        broke(s)
        refused(self, s, 'jr_quay_restock', 'no_money', stall=ST(s)['id'], items={DISH: 50})
        self.assertEqual(ST(s)['business']['again'], {DISH: 2})

    def test_bad_saved_orders_are_refused(self):
        s = opened('xe', wallet=20000)
        b = ST(s)['business']
        for bad in ({}, {'pho_bo': 1}, {DISH: 0}, {DISH: qb.STOCK_MAX + 1}, {DISH: '3'}, [DISH, 3], {DISH: True}):
            with self.subTest(bad=bad):
                b['again'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)
        b['again'] = {DISH: qb.STOCK_MAX}
        validate_state(s)


class WalletShortfall(unittest.TestCase):
    def test_without_the_flag_a_short_counter_is_refused_as_before(self):
        s = opened('xe', wallet=5000)
        broke(s)
        msg = refused(self, s, 'jr_quay_restock', 'no_money', stall=ST(s)['id'], items={DISH: 10})
        self.assertIn('két hoặc vốn quầy', msg)

    def test_the_shortfall_comes_from_the_wallet_in_the_same_command(self):
        s = opened('xe', wallet=5000)
        st = broke(s)
        st['till'] = 5
        unit = qb.unit_cost(st, DISH)
        cost = 10 * unit
        wallet = s['journey']['wallet']
        stock = st['business']['stock'].get(DISH, 0)
        s, r = act(s, 'jr_quay_restock', stall=st['id'], items={DISH: 10}, wallet=True)
        st = ST(s)
        self.assertEqual(s['journey']['wallet'], wallet - (cost - 5))
        self.assertEqual((st['till'], st['fund']), (0, 0))
        self.assertEqual(st['business']['stock'][DISH], stock + 10)
        self.assertIn(f'Lấy {cost - 5} xu từ ví', r['message'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['career']), (-(cost - 5), 'invest', 'milk_tea'))
        self.assertTrue(row['label'].startswith('Nhập hàng'))
        validate_state(s)

    def test_enough_in_the_counter_never_touches_the_wallet(self):
        s = opened('xe', wallet=5000)
        wallet, rows = s['journey']['wallet'], len(s['journey']['history'])
        s, r = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 1}, wallet=True)
        self.assertEqual((s['journey']['wallet'], len(s['journey']['history'])), (wallet, rows))
        self.assertNotIn('từ ví', r['message'])

    def test_wallet_then_bank_never_into_debt(self):
        s = opened('xe', wallet=5000)
        broke(s)
        s['journey']['wallet'] = 3
        validate_state(s)
        refused(self, s, 'jr_quay_restock', 'no_money', stall=ST(s)['id'], items={DISH: 10}, wallet=True)
        s['journey']['wallet'] = -5
        s['journey']['in_debt'] = True
        refused(self, s, 'jr_quay_restock', 'in_debt', stall=ST(s)['id'], items={DISH: 1}, wallet=True)

    def test_bad_flags_are_refused(self):
        s = opened('xe', wallet=5000)
        for bad in ('yes', 1, None, {}):
            with self.subTest(bad=bad):
                refused(self, s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 1}, wallet=bad)
        refused(self, s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 1}, wallet=True, extra=1)

    def test_big_amounts_split_into_valid_wallet_rows(self):
        s = opened('xe', wallet=5000)
        j = s['journey']
        j['wallet'] = 3 * 10**7
        j['stats']['max_wallet'] = max(j['stats']['max_wallet'], j['wallet'])
        before = len(j['history'])
        qy._take(s, 25_000_000, 'Góp vốn quầy', 'milk_tea')
        rows = j['history'][before:]
        self.assertEqual([r['amount'] for r in rows], [-10**7, -10**7, -5 * 10**6])
        self.assertEqual(j['wallet'], 5 * 10**6)
        validate_state(s)


class Upgrade(unittest.TestCase):
    def test_a_cart_grows_into_a_market_stall_keeping_everything(self):
        s = opened('xe', wallet=20000)
        s, _ = act(s, 'jr_quay_buy', stall=ST(s)['id'], item='camera', confirm=True)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 9})
        st = ST(s)
        view = qy.public(s)['stalls'][0]
        cost = 4000 - 800 + (140 - 70)
        self.assertEqual(view['grow'], [dict(place='sap', cost=cost), dict(place='kiot', cost=15000 - 800 + 250 - 70)])
        keep = {k: st[k] for k in ('id', 'name', 'trade', 'staff', 'items', 'menu', 'hist', 'opened')}
        stock, fund = dict(st['business']['stock']), st['fund']
        wallet = s['journey']['wallet']
        s, r = act(s, 'jr_quay_upgrade', stall=st['id'], place='sap', confirm=True)
        st = ST(s)
        self.assertEqual(st['place'], 'sap')
        self.assertEqual({k: st[k] for k in keep}, keep)
        self.assertEqual(st['business']['stock'], stock)
        self.assertGreaterEqual(st['fund'], 0)
        self.assertLessEqual(abs(st['fund'] - fund), fund)
        self.assertEqual(s['journey']['wallet'], wallet - cost)
        self.assertIn('Sạp chợ Phố', r['message'])
        self.assertEqual(s['journey']['history'][-1]['amount'], -cost)
        self.assertEqual(qy.public(s)['stalls'][0]['grow'], [dict(place='kiot', cost=15000 - 4000 + 250 - 140)])
        # sang nhượng now gives what a stall opened as a Sạp would: half its price, items at the Sạp's price
        self.assertEqual(qy.sell_back(st) - st['till'] - st['fund'], 4000 * qy.SELL_PCT // 100 + 140 * qy.UPGRADE_BACK // 100
                         - st['business'].get('unpaid_fines', 0) - st['due'])
        # the second place for staff is there now
        cand = qy.candidates(s, st)[0]
        s, _ = act(s, 'jr_quay_hire', stall=st['id'], cand=cand['id'], wage=cand['ask'])
        self.assertEqual(len(ST(s)['staff']), 2)
        validate_state(s)

    def test_refusals(self):
        s = opened('sap', wallet=20000)
        sid = ST(s)['id']
        refused(self, s, 'jr_quay_upgrade', 'not_bigger', stall=sid, place='xe', confirm=True)
        refused(self, s, 'jr_quay_upgrade', 'not_bigger', stall=sid, place='sap', confirm=True)
        refused(self, s, 'jr_quay_upgrade', stall=sid, place='lau', confirm=True)
        refused(self, s, 'jr_quay_upgrade', stall=sid, place='kiot')
        refused(self, s, 'jr_quay_upgrade', stall=sid, place='kiot', confirm=True, extra=1)
        s['journey']['wallet'] = 10
        validate_state(s)
        refused(self, s, 'jr_quay_upgrade', 'no_money', stall=sid, place='kiot', confirm=True)
        top = opened('kiot', wallet=30000)
        self.assertEqual(qy.public(top)['stalls'][0]['grow'], [])
        refused(self, top, 'jr_quay_upgrade', 'not_bigger', stall=ST(top)['id'], place='kiot', confirm=True)

    def test_not_while_a_choice_waits(self):
        s = opened('xe', wallet=20000)
        st = ST(s)
        st['shop_events'] = dict(v=1, seq=1, next=99, pending=dict(id=f'shop-{st["id"]}-1', kind='traffic_inspection',
                                                                    camera_at_event=False), recent=[], reputation=0, spent=0)
        validate_state(s)
        refused(self, s, 'jr_quay_upgrade', 'busy', stall=st['id'], place='sap', confirm=True)

    def test_303_waiting_choices_do_not_block_a_bigger_place(self):
        """#303 (homestay, 09/10 "ko nâng cấp dk"): a busy counter almost always has a shop choice and a staff request
        waiting; they stay waiting and the counter grows. Only the owner's own shift (and a cart-only choice) stop it,
        and the 🏗️ row says why before the tap."""
        s = opened('sap', wallet=30000)
        st = ST(s)
        st['shop_events'] = dict(v=1, seq=1, next=99, pending=dict(id=f'shop-{st["id"]}-1', kind='rain', camera_at_event=False),
                                 recent=[], reputation=0, spent=0)
        e = st['staff'][0]
        st['staff_life'] = dict(v=1, seq=1, next=99, pending=dict(id=f'staff-{st["id"]}-1', kind='wedding', employee=e['id'],
                                name=e['name'], wage=e['wage'], raise_by=max(1, (e['wage'] + 9) // 10)), recent=[], spent=0, raises={})
        validate_state(s)
        self.assertNotIn('why', qy.public(s)['stalls'][0]['grow'][0])
        s, _ = act(s, 'jr_quay_upgrade', stall=st['id'], place='kiot', confirm=True)
        st = ST(s)
        self.assertEqual(st['place'], 'kiot')
        self.assertEqual(st['shop_events']['pending']['kind'], 'rain')
        self.assertEqual(st['staff_life']['pending']['kind'], 'wedding')
        validate_state(s)

    def test_303_the_owner_shift_is_the_reason_shown(self):
        s = opened('xe', wallet=20000)
        sid = ST(s)['id']
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={DISH: 9})
        s, _ = act(s, 'jr_quay_start', stall=sid)
        why = 'Đóng ca tự đứng quầy rồi mở rộng nhé.'
        self.assertEqual([g.get('why') for g in qy.public(s)['stalls'][0]['grow']], [why, why])
        self.assertIn(why, refused(self, s, 'jr_quay_upgrade', 'busy', stall=sid, place='sap', confirm=True))
        s, _ = act(s, 'jr_quay_close', stall=sid)
        self.assertNotIn('why', qy.public(s)['stalls'][0]['grow'][0])
        s, _ = act(s, 'jr_quay_upgrade', stall=sid, place='sap', confirm=True)
        validate_state(s)

    def test_303_a_cart_only_choice_waiting_is_the_reason_shown(self):
        s = opened('xe', wallet=20000)
        st = ST(s)
        st['shop_events'] = dict(v=1, seq=1, next=99, pending=dict(id=f'shop-{st["id"]}-1', kind='traffic_inspection',
                                                                    camera_at_event=False), recent=[], reputation=0, spent=0)
        self.assertEqual([g.get('why') for g in qy.public(s)['stalls'][0]['grow']],
                         ['Xử lý tình huống đang chờ ở quầy rồi mở rộng nhé.'] * 2)

    def test_cart_only_events_stay_with_the_cart(self):
        s = opened('xe', wallet=20000)
        st = ST(s)
        from game.shop_events import CATALOGUE
        spec = CATALOGUE['traffic_inspection']
        ch = spec['choices'][0]
        row = dict(id=f'shop-{st["id"]}-1', kind='traffic_inspection', title=spec['title'], choice=ch['id'], text=ch['text'],
                   cost=0, rep=ch['rep'])
        st['shop_events'] = dict(v=1, seq=1, next=10**6, pending=None, recent=[row], reputation=0, spent=0)
        validate_state(s)
        st2 = dict(ST(s), place='sap')
        with self.assertRaises(GameError):   # kept as it is, the row would not validate on a Sạp
            from game.shop_events import validate as ev_validate
            ev_validate(st2, st2['id'], st2['trade'], 'sap')
        s, _ = act(s, 'jr_quay_upgrade', stall=st['id'], place='sap', confirm=True)
        self.assertEqual(ST(s)['shop_events']['recent'], [])
        validate_state(s)

    def test_big_upgrade_rows_stay_within_the_wallet_row_limit(self):
        s = opened('xe', wallet=20000)
        st = ST(s)
        cost = qy.upgrade_cost(st, 'kiot')
        with mock.patch.dict(qy.PLACES['kiot'], price=qy.PLACES['xe']['price'] + 2 * 10**7 + 5):
            cost = qy.upgrade_cost(st, 'kiot')
            j = s['journey']
            j['wallet'] = cost + 1
            j['stats']['max_wallet'] = max(j['stats']['max_wallet'], j['wallet'])
            before = len(j['history'])
            s, _ = act(s, 'jr_quay_upgrade', stall=st['id'], place='kiot', confirm=True)
            rows = s['journey']['history'][before:]
            self.assertEqual(sum(r['amount'] for r in rows), -cost)
            self.assertTrue(all(abs(r['amount']) <= 10**7 for r in rows))
            validate_state(s)



class OldServer(unittest.TestCase):
    """Saves of this build (a last order kept, a counter grown into a Sạp, a short restock paid from the wallet, split
    Sổ ví rows) validate and migrate on 1.9.35 and 1.9.34, which keep the extra key and can restock again."""

    def old_tree(self, release):
        if os.environ.get('MNL_QUAY_OLD_TREE'):
            return Path(os.environ['MNL_QUAY_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix=f'mnl-{release}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', release, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {release} (MNL_QUAY_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    PROG = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state\n'
            'out=[]\n'
            'for s in json.load(sys.stdin):\n'
            ' validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
            ' st=s["journey"]["quay"]["stalls"][0];st["fund"]+=1000\n'
            ' s,_=apply_action(s,None,"jr_quay_restock",{"stall":st["id"],"items":{"hong_tra":1}});validate_state(s)\n'
            ' st=s["journey"]["quay"]["stalls"][0]\n'
            ' out.append([st["place"],st["business"].get("again"),len(st["staff"])])\n'
            'print(json.dumps(out))')

    def saves(self):
        s = opened('xe', wallet=20000)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 4, 'tra_dao': 2})
        kept = json.loads(json.dumps(s))
        s, _ = act(s, 'jr_quay_upgrade', stall=ST(s)['id'], place='sap', confirm=True)
        cand = qy.candidates(s, ST(s))[0]
        s, _ = act(s, 'jr_quay_hire', stall=ST(s)['id'], cand=cand['id'], wage=cand['ask'])
        broke(s)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 5}, wallet=True)
        grown = json.loads(json.dumps(s))
        j = s['journey']
        j['wallet'] = 3 * 10**7
        j['stats']['max_wallet'] = max(j['stats']['max_wallet'], j['wallet'])
        s, _ = act(s, 'jr_quay_fund', stall=ST(s)['id'], amount=25_000_000)
        big = json.loads(json.dumps(s))
        for x in (kept, grown, big):
            validate_state(x)
        return [kept, grown, big]

    def check(self, release):
        old = self.old_tree(release)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', self.PROG], input=json.dumps(self.saves()), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout)
        # the old server keeps place and staff; its own restock leaves the key as it was (it does not know it)
        self.assertEqual(got, [['xe', {DISH: 4, 'tra_dao': 2}, 1], ['sap', {DISH: 5}, 2], ['sap', {DISH: 5}, 2]])

    def test_saves_validate_on_1_9_35(self):
        self.check(OLD_RELEASES['1.9.35'])

    def test_saves_validate_on_1_9_34(self):
        self.check(OLD_RELEASES['1.9.34'])


if __name__ == '__main__':
    unittest.main()
