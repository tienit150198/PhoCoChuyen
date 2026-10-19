"""🛍️ Owner 21/10 "mua bé hoặc mua linh kiện cho chọn số lượng mua nữa nhé, trang phục cũng thế": jr_pet_adopt (the shop),
jr_pet_gear_buy and jr_pet_wbuy take an optional `qty`. Absent it is 1 and the command does exactly what it did (checked
against the release before, byte for byte); N makes N things, each the one a single purchase makes, for one charge of
N × the price; a limit (the command's own cap, the room at home and in the kennel, the gear bag, the wardrobe, the
money) refuses the whole purchase and charges nothing; a bad number is refused; a replayed request id charges once; and
the saves a bulk purchase writes load and take a command on the releases before (a rollback loses nothing)."""
import copy
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

from game import journey as jr
from game import pet_tiers as px
from game import pet_wardrobe as pw
from game import pet_wardrobe_content as W
from game import pets as pt
from game import pets_content as C
from game.engine import GameError, validate_state
from tests.test_bank import act, story

ROOT = Path(__file__).resolve().parents[1]
BASE = 'fb4b2e82'                                    # 2.4.63: the branch point, the release before this change
RELEASES = {'2.4.63': BASE, '2.4.60': 'e05bacf5'}
BAD = (0, -1, -10**18, 2.5, '3', True, False, None, [2], 10**9, 2**63)
SHOP = {'from': 'shop'}


def rich(wallet=5_000_000):
    s = story()
    s['journey']['wallet'] = wallet
    s['journey']['stats']['max_wallet'] = wallet
    return s


def hist(s):
    return s['journey']['history']


def refused(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    return str(cm.exception)


def pets_all(s):
    return px.all_pets(s)


class Limits(unittest.TestCase):
    def test_caps_and_the_catalogue(self):
        self.assertEqual((C.BUY_QTY_MAX, px.GEAR_QTY_MAX, pw.BUY_QTY_MAX), (10, 20, 20))
        cat = pt.catalogue()
        self.assertEqual(cat['buy_qty'], C.BUY_QTY_MAX)
        self.assertEqual(cat['tiers']['limits']['gear_qty'], px.GEAR_QTY_MAX)
        self.assertEqual(cat['wardrobe']['qty_max'], pw.BUY_QTY_MAX)
        # The dearest bulk purchase stays far under a Sổ ví row (journey.ROW_MAX): one row, as one purchase writes.
        dear_pet = max(b['price'] for b in C.BREEDS.values() if b['shop'])
        dear_gear = px.gear_price(3 + len(px.GX_MULT) - 1, len(px.GSHOP) - 1)
        dear_wear = max(pw.price(i, 1) for i in W.ITEMS if not i.get('lux'))
        for one, n in ((dear_pet, C.BUY_QTY_MAX), (dear_gear, px.GEAR_QTY_MAX), (dear_wear, pw.BUY_QTY_MAX)):
            self.assertLess(one * n, jr.ROW_MAX)

    def test_the_client_reads_the_server_limits(self):
        js = (ROOT / 'public/js/v4/pets.js').read_text(encoding='utf-8')
        for needle in ('CAT()?.buy_qty', 't?.limits?.gear_qty', 'W?.qty_max', 'qtyBox(', '...(q>1?{qty:q}:{})'):
            self.assertIn(needle, js)
        self.assertEqual(js.count('...(q>1?{qty:q}:{})'), 3)    # qty only above 1: an older server never sees it


class Pets(unittest.TestCase):
    def test_qty_one_is_the_old_purchase(self):
        s = rich()
        with mock.patch.object(px, 'roll', lambda n: 0):
            a, ra = act(copy.deepcopy(s), 'jr_pet_adopt', **SHOP, breed='corgi', coat=1, nick='Tofu', confirm=True)
            b, rb = act(copy.deepcopy(s), 'jr_pet_adopt', **SHOP, breed='corgi', coat=1, nick='Tofu', qty=1, confirm=True)
        self.assertEqual(a['journey'], b['journey'])
        self.assertEqual(ra['message'], rb['message'])

    def test_three_corgis_one_charge(self):
        s = rich()
        w, rows, price = s['journey']['wallet'], len(hist(s)), C.BREEDS['corgi']['price']
        s, r = act(s, 'jr_pet_adopt', **SHOP, breed='corgi', coat=1, nick='Tofu', qty=5, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 5 * price)
        self.assertEqual(len(hist(s)), rows + 1)                              # one Sổ ví row
        self.assertEqual(hist(s)[-1]['amount'], -5 * price)
        self.assertIn('×5', hist(s)[-1]['label'])
        got = [p for p in pets_all(s) if p['b'] == 'corgi']
        self.assertEqual([p['n'] for p in got], ['Tofu', 'Tofu 2', 'Tofu 3', 'Tofu 4', 'Tofu 5'])
        self.assertTrue(all(p['c'] == 1 and p['p'] == price and p['s'] == 'shop' for p in got))
        self.assertEqual(len({p['id'] for p in got}), 5)
        self.assertEqual(len(pt.get(s)['list']), C.MAX_PETS)                  # home first, then the kennel
        self.assertEqual(len(px.get(s)['ken']), 5 - C.MAX_PETS)
        self.assertEqual(pt.get(s)['stats']['bought'], 5)
        self.assertEqual(pt.get(s)['stats']['xu'], 5 * price)
        self.assertEqual(r['pets'], [p['id'] for p in got])
        self.assertTrue(all(px.get(s)['t'][p['id']]['r'] in (0, 1) for p in got))   # each its own D/C roll
        self.assertIn('2 bé ở trại nuôi', r['message'])
        validate_state(s)

    def test_long_names_fit(self):
        s = rich()
        s, _ = act(s, 'jr_pet_adopt', **SHOP, breed='pug', nick='Bánh Bao Chiên X', qty=10, confirm=True)
        names = [p['n'] for p in pets_all(s)]
        self.assertEqual(names[0], 'Bánh Bao Chiên X')
        self.assertEqual(names[-1], 'Bánh Bao Chiê 10')
        self.assertTrue(all(len(n) <= C.NAME_MAX for n in names))
        validate_state(s)

    def test_limits_refuse_without_charging(self):
        s = rich()
        for bad in BAD:
            with self.subTest(qty=bad):
                refused(self, s, 'jr_pet_adopt', **SHOP, breed='corgi', nick='A', qty=bad, confirm=True)
        refused(self, s, 'jr_pet_adopt', **SHOP, breed='corgi', nick='A', qty=C.BUY_QTY_MAX + 1, confirm=True)
        # the shelter: one at a time
        refused(self, s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='A', qty=2, confirm=True)
        s2, _ = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='A', qty=1, confirm=True)
        # money for one, not for three
        poor = rich(C.BREEDS['corgi']['price'] * 2)
        self.assertIn('thiếu', refused(self, poor, 'jr_pet_adopt', **SHOP, breed='corgi', nick='A', qty=3, confirm=True))
        # room: home 3 + kennel 30; two places left → three refused whole, two fit
        s = rich(10**7)
        for _ in range(3):
            s, _ = act(s, 'jr_pet_adopt', **SHOP, breed='pug', nick='P', qty=10, confirm=True)
        s, _ = act(s, 'jr_pet_adopt', **SHOP, breed='pug', nick='Q', qty=1, confirm=True)
        self.assertEqual(pt.room_left(s), 2)
        msg = refused(self, s, 'jr_pet_adopt', **SHOP, breed='pug', nick='R', qty=3, confirm=True)
        self.assertIn('2 bé', msg)
        s, _ = act(s, 'jr_pet_adopt', **SHOP, breed='pug', nick='R', qty=2, confirm=True)
        self.assertEqual(pt.room_left(s), 0)
        refused(self, s, 'jr_pet_adopt', **SHOP, breed='pug', nick='S', confirm=True)
        validate_state(s)

    def test_a_big_charge_is_written_in_rows_of_ten_million(self):
        s = rich(25_000_000)
        how = pt._pay(s, 24_000_000, 'Thử')
        rows = hist(s)[-3:]
        self.assertEqual([r['amount'] for r in rows], [-10_000_000, -10_000_000, -4_000_000])
        self.assertEqual(how, '24.000.000 xu tiền mặt')
        s = rich(12_000_000)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=1_000_000)
        s['journey']['bank']['balance'] += 9_000_000
        how = pt._pay(s, 20_000_000, 'Thử')
        self.assertEqual([r['amount'] for r in hist(s)[-2:]], [-10_000_000, -1_000_000])
        self.assertEqual(s['journey']['bank']['balance'], 1_000_000)
        self.assertEqual(how, '11.000.000 xu tiền mặt và 9.000.000 xu từ tài khoản')


class Gear(unittest.TestCase):
    def test_qty_one_is_the_old_purchase(self):
        s = rich()
        a, ra = act(copy.deepcopy(s), 'jr_pet_gear_buy', slot='giay', model=4, rank=1, confirm=True)
        b, rb = act(copy.deepcopy(s), 'jr_pet_gear_buy', slot='giay', model=4, rank=1, qty=1, confirm=True)
        self.assertEqual(a['journey'], b['journey'])
        self.assertEqual(ra, rb)

    def test_ten_premium_shoes_one_charge(self):
        s = rich()
        w, rows, price = s['journey']['wallet'], len(hist(s)), px.gear_price(4, 1)
        s, r = act(s, 'jr_pet_gear_buy', slot='giay', model=4, rank=1, qty=10, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 10 * price)
        self.assertEqual(len(hist(s)), rows + 1)
        bag = px.get(s)['gear']
        self.assertEqual(len(bag), 10)
        self.assertTrue(all(g['s'] == 'giay' and g['m'] == 0 and g['r'] == 1 and g['lv'] == 0 for g in bag))
        self.assertEqual({s['journey']['petw']['gm'][g['id']] for g in bag}, {1})   # each the premium model
        self.assertEqual(r['gears'], [g['id'] for g in bag])
        self.assertEqual(r['gear'], bag[0]['id'])
        validate_state(s)

    def test_limits_refuse_without_charging(self):
        s = rich()
        for bad in BAD:
            with self.subTest(qty=bad):
                refused(self, s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=bad, confirm=True)
        refused(self, s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=px.GEAR_QTY_MAX + 1, confirm=True)
        poor = rich(px.GSHOP[1] * 2)
        refused(self, poor, 'jr_pet_gear_buy', slot='giay', model=0, rank=1, qty=3, confirm=True)
        for _ in range(2):
            s, _ = act(s, 'jr_pet_gear_buy', slot='bua', model=7, rank=0, qty=20, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='bua', model=7, rank=0, qty=15, confirm=True)
        self.assertIn('5 món', refused(self, s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=6, confirm=True))
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=5, confirm=True)
        self.assertEqual(len(px.get(s)['gear']), px.GEAR_MAX)
        refused(self, s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, confirm=True)
        self.assertEqual(len(s['journey']['petw']['gm']), 55)                    # ≤ 64: the save stays valid
        validate_state(s)


class Wardrobe(unittest.TestCase):
    def test_qty_one_is_the_old_purchase(self):
        s = rich()
        a, ra = act(copy.deepcopy(s), 'jr_pet_wbuy', id='canh_cong', rank=1, confirm=True)
        b, rb = act(copy.deepcopy(s), 'jr_pet_wbuy', id='canh_cong', rank=1, qty=1, confirm=True)
        self.assertEqual(a['journey'], b['journey'])
        self.assertEqual(ra, rb)

    def test_three_to_fuse_one_charge(self):
        s = rich()
        w, rows, one = s['journey']['wallet'], len(hist(s)), pw.price(W.ITEM['canh_cong'], 1)
        s, r = act(s, 'jr_pet_wbuy', id='canh_cong', rank=1, qty=3, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 3 * one)
        self.assertEqual(len(hist(s)), rows + 1)
        items = s['journey']['petw']['it']
        self.assertEqual([(i['k'], i['r']) for i in items], [('canh_cong', 1)] * 3)
        self.assertEqual(r['items'], [i['id'] for i in items])
        validate_state(s)
        with mock.patch.object(px, 'roll', lambda n: 0):                          # and the three fuse
            s, f = act(s, 'jr_pet_wfuse', k='canh_cong', r=1, confirm=True)
        self.assertTrue(f['ok'])

    def test_limits_refuse_without_charging(self):
        s = rich()
        for bad in BAD:
            with self.subTest(qty=bad):
                refused(self, s, 'jr_pet_wbuy', id='canh_cong', qty=bad, confirm=True)
        refused(self, s, 'jr_pet_wbuy', id='canh_cong', qty=pw.BUY_QTY_MAX + 1, confirm=True)
        refused(self, s, 'jr_pet_wbuy', id='canh_phuong_hoang', qty=2, confirm=True)            # luxury: never sold
        with mock.patch.object(pw, 'vn_date', lambda: '2026-11-02'):
            refused(self, s, 'jr_pet_wbuy', id='mu_phu_thuy', qty=2, confirm=True)               # out of season
        poor = rich(W.ITEM['canh_cong']['price'] * 2)
        refused(self, poor, 'jr_pet_wbuy', id='canh_cong', qty=3, confirm=True)
        for _ in range(7):
            s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=20, confirm=True)
        self.assertIn('10 món', refused(self, s, 'jr_pet_wbuy', id='no_hong', qty=11, confirm=True))
        s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=10, confirm=True)
        self.assertEqual(len(s['journey']['petw']['it']), pw.ITEM_MAX)
        validate_state(s)


class Replay(unittest.TestCase):
    """Through the store, as the browser sends it: a lost answer re-sent with its request id charges once, a second
    tap on a stale revision is refused (nothing charged), and a new tap buys again."""

    def test_request_id_and_revision(self):
        from game import marriage as mr
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(store.close_pool)
        token, _, _ = store.session()
        store.read(token)

        def fn(s):
            s['journey']['wallet'] = 1_000_000
        mr._mutate(store, {store.key(token): fn})
        rev = store.read(token)[1]
        pay = dict(slot='dau', model=0, rank=1, qty=7, confirm=True)
        one = store.command(token, 'req-qty-0001', rev, None, 'jr_pet_gear_buy', pay)
        again = store.command(token, 'req-qty-0001', rev, None, 'jr_pet_gear_buy', pay)
        self.assertEqual(one['result'], again['result'])
        s, rev2 = store.read(token)[:2]
        self.assertEqual(len(px.get(s)['gear']), 7)
        self.assertEqual(s['journey']['wallet'], 1_000_000 - 7 * px.GSHOP[1])
        with self.assertRaises(GameError):
            store.command(token, 'req-qty-0002', rev, None, 'jr_pet_gear_buy', pay)   # the stale revision
        s = store.read(token)[0]
        self.assertEqual(len(px.get(s)['gear']), 7)
        store.command(token, 'req-qty-0003', rev2, None, 'jr_pet_gear_buy', pay)
        s = store.read(token)[0]
        self.assertEqual(len(px.get(s)['gear']), 14)
        self.assertEqual(s['journey']['wallet'], 1_000_000 - 14 * px.GSHOP[1])


# ---------------------------------------------------------------- the releases before
SAME = '''import copy,json,sys
from unittest import mock
from game import pet_tiers as px, pet_wardrobe as pw
from game import journey as jr
from game.engine import apply_action,new_state,validate_state
s0=new_state();jr.enable_story(s0,4242);s0['journey'].update(gender='female',wallet=5000000)
s0['journey']['stats']['max_wallet']=5000000
validate_state(s0)
out=[]
with mock.patch.object(px,'roll',lambda n:n//3), mock.patch.object(pw,'vn_date',lambda:'2026-10-20'), \
        mock.patch('time.time',lambda:1792500000.0):
    s=copy.deepcopy(s0)
    for name,p in json.loads(sys.argv[1]):
        s,r=apply_action(s,None,name,p)
        out.append(r.get('message'))
print(json.dumps([s['journey'],out],sort_keys=True,ensure_ascii=False))
'''

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    s['careers']={k:v for k,v in s['careers'].items() if k in CAREERS};j=s['journey']
    j['unlocked']=[c for c in j['unlocked'] if c in CAREERS];j['days']=[d for d in j['days'] if d['c'] in CAREERS]
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=lambda s:json.dumps([s['journey'].get(k) for k in ('pets','petx','petw','wallet')],sort_keys=True)
    before=keep(s)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    pet=s['journey']['pets']['list'][0]['id']
    s,_=apply_action(s,None,'jr_pet_name',{'pet':pet,'nick':'Lan'})
    validate_state(s)
    out.append([before,keep(s)!=before])
print(json.dumps(out))
'''


class OldReleases(unittest.TestCase):
    def tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-qty-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_in(self, where, code, *args, stdin=''):
        env = dict(os.environ, PYTHONPATH=str(where), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', code, *args], input=stdin, capture_output=True, text=True, cwd=where,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return out.stdout.strip().splitlines()[-1]

    def test_without_qty_it_is_the_release_before(self):
        """The old client's commands (no qty) give exactly the journey and the messages 2.4.63 gave (same save, rolls, clock)."""
        cmds = [['jr_pet_adopt', dict(SHOP, breed='corgi', coat=1, nick='Tofu', confirm=True)],
                ['jr_pet_adopt', dict(SHOP, breed='xiem', nick='Mun', confirm=True)],
                ['jr_pet_gear_buy', dict(slot='giay', model=5, rank=1, confirm=True)],
                ['jr_pet_gear_buy', dict(slot='bua', model=1, rank=0, confirm=True)],
                ['jr_pet_wbuy', dict(id='canh_cong', rank=1, confirm=True)],
                ['jr_pet_wbuy', dict(id='no_hong', confirm=True)],
                ['jr_pet_buy', dict(id='bong', confirm=True)]]
        args = (json.dumps(cmds),)
        old = self.run_in(self.tree(BASE), SAME, *args)     # each tree makes its own save (its own careers)
        new = self.run_in(ROOT, SAME, *args)
        self.assertEqual(json.loads(old), json.loads(new))

    def test_bulk_saves_load_on_older_releases(self):
        s = rich()
        s, _ = act(s, 'jr_pet_adopt', **SHOP, breed='corgi', coat=1, nick='Tofu', qty=6, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=4, rank=1, qty=12, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='pk', model=0, rank=0, qty=3, confirm=True)
        s, _ = act(s, 'jr_pet_wbuy', id='canh_cong', rank=1, qty=9, confirm=True)
        s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=4, confirm=True)
        big = rich(30_000_000)
        pt._pay(big, 25_000_000, 'Thử')                                           # rows of ≤ 10 M
        big, _ = act(big, 'jr_pet_adopt', **SHOP, breed='shiba', nick='Na', qty=2, confirm=True)
        saves = [s, big]
        for x in saves:
            validate_state(x)
        for label, rev in RELEASES.items():
            with self.subTest(release=label):
                got = json.loads(self.run_in(self.tree(rev), PROG, stdin=json.dumps(saves)))
                for (before, fed), x in zip(got, saves):
                    pets_, petx, petw, _ = json.loads(before)
                    self.assertEqual([pets_, petx, petw], [x['journey'].get(k) for k in ('pets', 'petx', 'petw')])
                    self.assertTrue(fed)


if __name__ == '__main__':
    unittest.main()
