"""🔨 Đồ đấu giá mới (owner 20/10: "thêm nhiều đồ mới cho đấu giá nhé, thêm nhiều vào và ứng dụng được"): the 50 items of
20/10 and their uses. The catalogue (kinds, ids, prices, every item with a use sentence, the client's copies of the
paints and the furniture), winning each new kind (🪑 a piece in the bag that counts its Ấm cúng and stands in for its base
piece in the theme sets; 🐾 a ranked piece in Tủ đồ thú cưng that adds to the pet's work bonus within its caps, waiting
when the wardrobe is full; 🧰 a signature tool paid on its workplace's shift, never past PCT_CAP / BONUS_CAP together
with Biển đẹp; 🏎️ limited editions in their new paints; plates; titles), journey.uniq_y's checks and upgrade, the wealth
fee's valuation, a premium starting price and a lot won end to end on PostgreSQL, and saves that cross 2.4.71 (live,
the rollback target) both ways."""
import copy
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from game import auction as au
from game import auction_content as AC
from game import content
from game import deco as dc
from game import deco_content as DC
from game import engine as E
from game import garage as gr
from game import journey as jr
from game import pet_wardrobe as pw
from game import pet_wardrobe_content as W
from game import pets as pt
from game import spend_content as SC
from game import wealth_pricing
from game.engine import GameError, validate_state
from tests.pg_support import pg_only
from tests.test_bank import act, story
from tests.test_vehicle_plates import rows, shift

ROOT = Path(__file__).resolve().parents[1]
LIVE = 'fe504023'   # 2.4.71, live on 20/10: the rollback target
NEW = ('lx_cub_50', 'lx_xe_ga_88', 'lx_mini_02', 'lx_suv_09', 'lx_buom_03', 'lx_canh_quat_01', 'lx_truc_thang_01', 'lx_sieu_xe_02',
       'pl_30l99999', 'pl_51k88888', 'pl_29k68686', 'pl_79a56789', 'pl_may1975', 'pl_65a12345', 'pl_may2468',
       'rg_vna999', 'rg_vna386', 'rg_vna520', 'hn_rong_bien', 'hn_trang_ram', 'hn_bien_ngoc',
       'dh_phuong_hoang', 'dh_ngan_ha', 'dh_hoang_hon', 'dh_hai_dang', 'dh_ca_phe', 'dh_mua_sao',
       'dc_sap_kham', 'dc_bonsai_sanh', 'dc_piano_go', 'dc_dong_ho_phap', 'dc_den_chum', 'dc_binh_chu_dau', 'dc_am_tu_sa',
       'dc_mai_co_thu', 'dc_den_keo_quan',
       'pw_vong_kc_sss', 'pw_vm_kc_ss', 'pw_canh_phuong_ss', 'pw_kinh_kc_s', 'pw_ao_hoang_gia_s', 'pw_canh_rong_a',
       'tl_espresso', 'tl_may_anh', 'tl_quay_go', 'tl_noi_pho', 'tl_may_may', 'tl_keo_hoa', 'tl_do_nghe', 'tl_binh_lac')
_LOT = [0]


def win(s, item, amount=None):
    """What live_effects pays into the save when a lot is won (game/auction.py apply_fx); the save checked."""
    _LOT[0] += 1
    it = AC.ITEM[item]
    amount = amount or AC.TIERS[it['tier']]['start']
    msg = au.apply_fx(s, dict(data=dict(lot=f'20261020-{_LOT[0]}', what='win', item=item, kind=it['kind'], text=it['name'])), amount)
    validate_state(s)
    return msg


def roundtrip(s):
    """A save written and read back (JSON, migrate, validate): what a reload does."""
    t = E.migrate_state(json.loads(json.dumps(s, ensure_ascii=False)))
    validate_state(t)
    return t


class Catalogue(unittest.TestCase):
    def test_fifty_new_items_across_six_kinds(self):
        self.assertEqual(len(NEW), 50)
        self.assertTrue(set(NEW) <= set(AC.ITEM))
        kinds = Counter(AC.ITEM[i]['kind'] for i in NEW)
        self.assertEqual(kinds, Counter(vehicle=8, plate=7, reg=3, hull=3, title=6, decor=9, petgear=6, tool=8))
        ids = [it['id'] for it in AC.ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        for i in NEW:
            it = AC.ITEM[i]
            self.assertRegex(i, au.ITEM_RE)
            self.assertIn(it['kind'], au.KINDS)
            self.assertIn(it['tier'], AC.TIERS)
            self.assertLessEqual(len(it['name']), au.TEXT_MAX)
            self.assertTrue(au.use_line(it), i)                                # every item says what it does
            self.assertTrue(it.get('story'), i)
        folded = [au.fold_plate(it['name']) for it in AC.ITEMS if it['kind'] in AC.PLATE_KINDS]
        self.assertEqual(len(folded), len(set(folded)))                        # no plate copies another
        for it in AC.ITEMS:                                                    # a premium start never under its tier's
            if 'start' in it:
                self.assertGreaterEqual(it['start'], AC.TIERS[it['tier']]['start'])
                self.assertGreater(it['step'], 0)

    def test_vehicles_and_paints(self):
        for i in NEW:
            it = AC.ITEM[i]
            if it['kind'] != 'vehicle':
                continue
            V = gr.VEHICLES[i]
            self.assertTrue(V['limited'] and i not in gr.SHOP)
            self.assertLessEqual(len(i), 24)                                   # the garage's ID_RE
            self.assertTrue(gr.PAINT_INDEX[it['paint']].get('limited'))
            self.assertEqual((V['group'], V['price']), (gr.VEHICLES[it['base']]['group'], gr.VEHICLES[it['base']]['price']))
        js = (ROOT / 'public/js/v4/auction-display.js').read_text(encoding='utf-8')
        for p in gr.SPECIAL_PAINTS:                                            # the lot card paints each one
            self.assertIn(f"{p[0]}:'{p[2]}'", js)

    def test_titles_registered_for_phong_cach_and_the_frame(self):
        from live import honours
        for i in NEW:
            if AC.ITEM[i]['kind'] == 'title':
                self.assertEqual(SC.STYLE_ITEMS[i]['earn'], AC.EARN)
                self.assertIn(i, honours.UQ_TITLES)
                self.assertRegex(i, jr.HF_PICK_RE)

    def test_furniture_registered_from_its_base_piece(self):
        js = (ROOT / 'public/js/v4/deco-art.js').read_text(encoding='utf-8')
        m = re.search(r'export const UQ_DECO=\{(.*?)\};', js, re.S)
        client = {k: (b, g) for k, b, g in re.findall(r"(dc_[a-z0-9_]+):\['([a-z0-9_]+)','(#[0-9a-f]{6})'\]", m.group(1))}
        server = {it['id']: (it['base'], it['glow']) for it in AC.ITEMS if it['kind'] == 'decor'}
        self.assertEqual(client, server)                                       # the drawings follow the catalogue
        for k, it in AC.DECO_PIECE.items():
            self.assertLessEqual(len(k), 24)                                   # game/reno.py _ID
            P, B = DC.ITEMS[k], DC.ITEMS[it['base']]
            self.assertTrue(P['uq'] and P['price'] == 0)
            self.assertEqual((P['spot'], P['w'], P['h'], P['rooms'], P['tags'], P['surface']),
                             (B['spot'], B['w'], B['h'], B['rooms'], B['tags'], B['surface']))
            self.assertEqual(P['cozy'], B['cozy'] + AC.DECO_COZY[it['tier']])
            for S in DC.SETS.values():                                         # stands in wherever its base is named
                for e in S['need']:
                    if e[0] != 'tag' and set(e) & {it['base'], *it['alt']}:
                        self.assertIn(k, e)
        shop = dc.catalogue()['items']
        self.assertTrue(all(x.get('uq') for x in shop if x['id'].startswith('uq_')))

    def test_pet_pieces_and_tools(self):
        for i in NEW:
            it = AC.ITEM[i]
            if it['kind'] == 'petgear':
                self.assertIn(it['piece'], W.ITEM)
                self.assertIn(it['rank'], (3, 4, 5, 6))                        # A…SSS: never what the shop sells (D, C)
                self.assertNotEqual(W.ITEM[it['piece']]['slot'], 'bed')        # a bed adds nothing: not worth an auction
            if it['kind'] == 'tool':
                self.assertIn(it['career'], content.CAREERS)
                self.assertIs(AC.TOOLS[it['career']], it)                       # one a workplace
        self.assertTrue(all(0 < p < AC.PCT_CAP for p in AC.TOOL_PCT.values()))

    def test_catalogue_and_lot_view_carry_the_use(self):
        cat = {x['id']: x for x in au.catalogue()['items']}
        self.assertIn('Ấm cúng +6', cat['dc_sap_kham']['use'])
        self.assertEqual((cat['dc_sap_kham']['w'], cat['dc_sap_kham']['spot']), (3, 'floor'))
        self.assertIn('+6%', cat['pw_vong_kc_sss']['use'])
        self.assertIn('+4%', cat['tl_espresso']['use'])
        json.dumps(cat, ensure_ascii=False)


class Decor(unittest.TestCase):
    def test_win_puts_the_piece_in_the_bag_and_it_counts_at_home(self):
        from tests.test_deco import bag, free, owner
        s = owner()
        msg = win(s, 'dc_sap_kham')
        self.assertIn('túi đồ trang trí', msg)
        self.assertIn('uq_dc_sap_kham', bag(s))
        self.assertEqual(s['journey']['uniq_y']['own']['dc_sap_kham']['g'], 1)
        s = roundtrip(s)
        uid = next(x['id'] for x in s['journey']['reno']['items'] if x['k'] == 'uq_dc_sap_kham')
        x, y = free(s, 'uq_dc_sap_kham', 'living')
        before = dc.points(dc.layout(s))['items']
        s, r = act(s, 'jr_deco_put', uid=uid, r='living', x=x * DC.U, y=y * DC.U)
        self.assertEqual(dc.points(dc.layout(s))['items'], before + DC.ITEMS['uq_dc_sap_kham']['cozy'])
        with self.assertRaises(GameError):                                     # unique: never sold back
            act(s, 'jr_deco_sell', uid=uid, confirm=True)
        win(s, 'dc_sap_kham')                                                  # a second payment of the same win: one piece
        self.assertEqual(sum(x['k'] == 'uq_dc_sap_kham' for x in s['journey']['reno']['items']), 1)

    def test_stands_in_for_its_base_piece_in_a_set(self):
        rooms = [dict(id='r1', type='living', tags=[])]
        L = dict(rooms=rooms, pos={'a': dict(r='r1'), 'b': dict(r='r1'), 'c': dict(r='r1')},
                 kinds={'a': 'uq_dc_sap_kham', 'b': 'tranh_dong_ho', 'c': 'uq_dc_am_tu_sa'})
        xua = next(x for x in dc.sets_of(L) if x['id'] == 'xua')
        self.assertTrue(xua['done'])
        L['kinds']['a'] = 'ban_tra'
        xua = next(x for x in dc.sets_of(L) if x['id'] == 'xua')
        self.assertFalse(xua['done'])
        self.assertNotIn('khảm', ' '.join(xua['miss']))                        # a hint never names an auction piece
        L = dict(rooms=rooms, pos={'a': dict(r='r1'), 'b': dict(r='r1')}, kinds={'a': 'uq_dc_piano_go', 'b': 'loa'})
        self.assertTrue(next(x for x in dc.sets_of(L) if x['id'] == 'nhac')['done'])   # the piano plays the guitar's part


class PetPieces(unittest.TestCase):
    def test_win_wear_and_the_capped_bonus(self):
        from tests.test_pet_tiers import get
        s = story()
        s['journey']['wallet'] = 50_000_000
        s, pid = get(s, 'Mun')
        msg = win(s, 'pw_vong_kc_sss')
        self.assertIn('Tủ đồ thú cưng', msg)
        i = next(x for x in s['journey']['petw']['it'] if x['k'] == 'vong_kim_cuong')
        self.assertEqual(i['r'], 6)
        s = roundtrip(s)
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='neck', item=i['id'])
        pet = pt.get(s)['list'][0]
        self.assertEqual(pw.bonus_bp(s, pet), pw.BONUS_BP[6] + pw.LUX_BONUS)   # 6 %, like any SSS luxury piece
        for item, slot in (('pw_vm_kc_ss', 'head'), ('pw_kinh_kc_s', 'eye'), ('pw_ao_hoang_gia_s', 'body'),
                           ('pw_canh_phuong_ss', 'back')):
            win(s, item)
            piece = AC.ITEM[item]['piece']
            j = next(x for x in s['journey']['petw']['it'] if x['k'] == piece)
            s, _ = act(s, 'jr_pet_wwear', pet=pid, slot=slot, item=j['id'])
        pet = pt.get(s)['list'][0]
        self.assertIn('hoang_gia', pw.full_sets(pw.worn(s, pet)))              # the royal set, whole
        self.assertLessEqual(pw.bonus_bp(s, pet), pw.BONUS_MAX)
        validate_state(s)

    def test_full_wardrobe_waits_then_arrives(self):
        s = story()
        x = pw._ensure(s)
        for _ in range(pw.ITEM_MAX):
            pw._new(x, 'no_hong', 0)
        validate_state(s)
        msg = win(s, 'pw_kinh_kc_s')
        self.assertIn('bỏ bớt', msg)
        self.assertEqual(s['journey']['uniq_y']['own']['pw_kinh_kc_s']['g'], 0)
        s = roundtrip(s)
        s, _ = act(s, 'jr_pet_wdrop', k='no_hong', r=0, confirm=True)         # room again: the next action hands it over
        self.assertEqual(s['journey']['uniq_y']['own']['pw_kinh_kc_s']['g'], 1)
        self.assertTrue(any(i['k'] == 'kinh_kim_cuong' and i['r'] == 4 for i in s['journey']['petw']['it']))
        s, _ = act(s, 'jr_pet_wdrop', k='no_hong', r=0, confirm=True)
        self.assertEqual(sum(i['k'] == 'kinh_kim_cuong' for i in s['journey']['petw']['it']), 1)   # handed over once


class Tools(unittest.TestCase):
    def test_paid_on_its_workplace_only(self):
        s = story(2_000_000)
        msg = win(s, 'tl_quay_go')                                             # Tạp hoá, tier 2: 3 %
        self.assertIn('+3%', msg)
        s = roundtrip(s)
        s, r = shift(s, 1000, cid='grocery')
        base = r['summary']['net']
        self.assertGreater(base, 0)
        self.assertEqual(rows(s, '🧮'), [base * 3 // 100])
        self.assertEqual(r['summary']['journey']['tool_pct'], 3)
        self.assertTrue(any('+3%' in e for e in r['effects']))
        s, r = shift(s, 1000, cid='florist')                                   # another workplace: nothing
        self.assertNotIn('tool', r['summary']['journey'])

    def test_with_a_plate_never_past_the_caps(self):
        s = story(2_000_000)
        s, _ = act(s, 'jr_garage_buy', id='sieu_xe', confirm=True)
        win(s, 'pl_29a88888')                                                  # 7 % on a car
        s, _ = act(s, 'jr_garage_plate', item='pl_29a88888', id='sieu_xe')
        s, _ = act(s, 'jr_garage_ride', id='sieu_xe')
        win(s, 'tl_quay_go')                                                   # + 3 % = 10 %: the cap
        s, r = shift(s, 1000, cid='grocery')
        base = r['summary']['net']
        self.assertEqual((r['summary']['journey']['plate_pct'], r['summary']['journey']['tool_pct']), (7, 3))
        self.assertEqual(rows(s, 'Biển đẹp') + rows(s, '🧮'), [base * 7 // 100, base * 3 // 100])
        win(s, 'lx_sieu_xe_02')                                                # a limited edition: 8 % with the plate
        s, _ = act(s, 'jr_garage_plate', item='pl_29a88888', id='lx_sieu_xe_02')
        s, _ = act(s, 'jr_garage_ride', id='lx_sieu_xe_02')
        s, r = shift(s, 1000, cid='grocery')
        self.assertEqual((r['summary']['journey']['plate_pct'], r['summary']['journey']['tool_pct']), (8, 2))   # 10 % in all
        s, r = shift(s, 200_000, cid='grocery')                                # a huge shift: BONUS_CAP for both together
        paid = r['summary']['journey'].get('plate', 0) + r['summary']['journey'].get('tool', 0)
        self.assertEqual(paid, AC.BONUS_CAP)

    def test_past_the_real_time_allowance(self):
        s = story(2_000_000)
        win(s, 'tl_quay_go')
        with mock.patch.object(jr.icl, 'day_paid', lambda st: False):
            s, r = shift(s, 1000, cid='grocery')
        self.assertEqual(rows(s, '🧮'), [])


class Saves(unittest.TestCase):
    def test_validate_and_upgrade(self):
        s = story(100_000)
        for i in ('dc_am_tu_sa', 'tl_keo_hoa', 'pw_canh_rong_a'):
            win(s, i)
        y = s['journey']['uniq_y']
        self.assertEqual(set(y['own']), {'dc_am_tu_sa', 'tl_keo_hoa', 'pw_canh_rong_a'})
        self.assertNotIn('dc_am_tu_sa', s['journey']['uniq']['own'])           # never in the blocks older builds check
        self.assertNotIn('uniq_x', s['journey'])
        self.assertEqual(au.public(s)['own']['tl_keo_hoa']['k'], 'tool')       # Của tôi lists them
        self.assertEqual(au.collection_score(s), (10 * 3, 3, 0))               # and they count on the 💎 board
        for bad in (dict(v=2), dict(extra=1), dict(own={'tl_keo_hoa': dict(k='tool', t='x', d=1, p=1, lot='20261020-1')}),
                    dict(own={'tl_keo_hoa': dict(k='plate', t='x', d=1, p=1, lot='20261020-1', g=1)}),
                    dict(own={'tl_keo_hoa': dict(k='tool', t='x', d=1, p=1, lot='20261020-1', g=2)})):
            t = copy.deepcopy(s)
            t['journey']['uniq_y'].update(bad)
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['uniq_y']['own']['tl_keo_hoa']['z'] = 1
        t['journey']['uniq_y']['own']['zz_newer'] = dict(k='car', t='x', d=1, p=1, lot='20261020-1', g=1)
        au.upgrade(t['journey'])
        self.assertEqual(t['journey']['uniq_y'], s['journey']['uniq_y'])      # a newer build's extras dropped, the rest kept
        self.assertEqual(roundtrip(s)['journey']['uniq_y'], s['journey']['uniq_y'])

    def test_unknown_item_waits(self):
        s = story()
        au.apply_fx(s, dict(data=dict(lot='20261020-99', what='win', item='dc_newer_piece', kind='decor', text='Đồ mới')), 5000)
        validate_state(s)
        self.assertEqual(s['journey']['uniq_y']['own']['dc_newer_piece']['g'], 0)   # a newer catalogue's: kept, waiting
        self.assertEqual(au.y_settle(s), '')

    def test_wealth_counts_what_can_be_sold_back(self):
        s = story(3_000_000)
        before = wealth_pricing.total(s)
        for i in ('dc_sap_kham', 'pw_vong_kc_sss', 'tl_espresso', 'dh_ngan_ha'):   # the xu were burned: nothing to sell
            win(s, i)
        self.assertEqual(wealth_pricing.total(s), before)
        win(s, 'lx_suv_09')                                                    # a limited edition: its base model's buy-back
        self.assertEqual(wealth_pricing.total(s), before + gr.sell_price(gr.VEHICLES['o_to_suv']['price']))


class Messages(unittest.TestCase):
    def test_every_new_kind_says_where_it_went(self):
        s = story(100_000)
        self.assertIn('nhà xe', win(s, 'lx_mini_02'))
        self.assertIn('Nhà xe', win(s, 'rg_vna520'))
        self.assertIn('Phong cách', win(s, 'dh_ca_phe'))
        self.assertIn('túi đồ', win(s, 'dc_den_keo_quan'))
        self.assertIn('Tủ đồ thú cưng', win(s, 'pw_canh_rong_a'))
        self.assertIn(jr._place('pho'), win(s, 'tl_noi_pho'))


@pg_only
class Database(unittest.TestCase):
    """A premium starting price and a 🪑 lot won end to end through the real command path on PostgreSQL."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        au._VIEW.clear()
        au._planned.clear()
        self.t = [1_792_000_000.0]
        p = mock.patch('game.auction.now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)

    def player(self, wallet=3_000_000):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = 'Lan'
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {sid: fn})
        created = (datetime.datetime.fromtimestamp(self.t[0], datetime.timezone.utc) - datetime.timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?,?,?,?,?)',
                       (f'u{sid[:10]}', 'Lan', 'x', sid, created))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'c' * 48))
        return token

    def row(self, lid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM auction_lots WHERE id=?', (lid,)).fetchone())

    def bid(self, token, lid, amount):
        return self.store.command(token, f'auc-{threading.get_ident() % 100000}-{amount}', self.store.read(token)[1], None,
                                  'jr_auc_bid', dict(lot=lid, amount=amount))

    def test_premium_start_and_a_piece_won_into_the_bag(self):
        lid = au.admin_add(self.store, 'op', dict(item='lx_sieu_xe_02'))['id']
        self.assertEqual((self.row(lid)['start'], self.row(lid)['step']), (1_000_000, 50_000))
        self.t[0] += 10
        lid2 = au.admin_add(self.store, 'op', dict(item='tl_espresso', tier=2))['id']   # moved to another tier: its prices
        self.assertEqual(self.row(lid2)['start'], AC.TIERS[2]['start'])
        self.t[0] += 10
        lid = au.admin_add(self.store, 'op', dict(item='dc_bonsai_sanh'))['id']
        view = next(x for x in au.view(self.store, None)['lots'] if x['id'] == lid)
        self.assertIn('Ấm cúng', view['data']['use'])
        self.assertEqual(view['data']['spot'], 'floor')
        a = self.player()
        self.t[0] += 1
        self.bid(a, lid, self.row(lid)['start'])
        self.t[0] = self.row(lid)['ends_at'] + 1
        self.assertEqual(au.settle_one(self.store, lid), 'sold')
        from game import live_effects
        live_effects.on_load(self.store, a, self.store.read(a)[0])
        s = self.store.read(a)[0]
        self.assertEqual(s['journey']['uniq_y']['own']['dc_bonsai_sanh']['g'], 1)
        self.assertTrue(any(x['k'] == 'uq_dc_bonsai_sanh' for x in s['journey']['reno']['items']))
        validate_state(s)


class OldServer(unittest.TestCase):
    """2.4.71 (live, the rollback target) loads, plays and writes back a save holding every new kind; this build reads
    it back with nothing lost."""

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE')
        if old and (Path(old) / 'game' / 'engine.py').is_file():
            return old
        tmp = tempfile.mkdtemp(prefix='mnl-auc-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', LIVE, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {LIVE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def test_saves_cross_the_live_build_both_ways(self):
        from tests.test_deco import owner
        from tests.test_pet_tiers import get
        s = owner()
        s['journey']['wallet'] = 50_000_000
        s, pid = get(s, 'Mun')
        for i in ('dc_sap_kham', 'pw_vong_kc_sss', 'tl_quay_go', 'lx_suv_09', 'pl_79a56789', 'dh_ngan_ha'):
            win(s, i)
        uid = next(x['id'] for x in s['journey']['reno']['items'] if x['k'] == 'uq_dc_sap_kham')
        from tests.test_deco import free
        x, y = free(s, 'uq_dc_sap_kham', 'living')
        s, _ = act(s, 'jr_deco_put', uid=uid, r='living', x=x * DC.U, y=y * DC.U)
        i = next(q for q in s['journey']['petw']['it'] if q['k'] == 'vong_kim_cuong')
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='neck', item=i['id'])
        s, _ = act(s, 'jr_garage_plate', item='pl_79a56789', id='lx_suv_09')
        s, _ = act(s, 'jr_garage_ride', id='lx_suv_09')
        s, _ = act(s, 'jr_garage_paint', id='lx_suv_09', color='hong_ngoc')
        validate_state(s)
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError,CAREERS;'
                'from game import auction as au;s=json.load(sys.stdin);'
                's["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's["journey"]["unlocked"]=[c for c in s["journey"]["unlocked"] if c in CAREERS];'
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,"grocery","select_career",{"confirm":True});'
                's,_=apply_action(s,"grocery","start_day",{});'
                's,_=apply_action(s,"grocery","end_day",{"carry_event":True});validate_state(s);'
                'code="";\n'
                'try:\n au.apply_fx(s,dict(data=dict(lot="20261020-90",what="win",item="tl_espresso",kind="tool",text="X")),1)\n'
                'except GameError as e:\n code=e.code or "refused"\n'
                'validate_state(s)\n'
                'print(json.dumps(dict(s=s,code=code)))')
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(got['code'])                                           # 2.4.71 leaves a new kind's win pending
        back = got['s']
        self.assertEqual(back['journey']['uniq_y'], s['journey']['uniq_y'])   # kept untouched
        self.assertTrue(any(x['k'] == 'uq_dc_sap_kham' for x in back['journey']['reno']['items']))
        self.assertEqual(back['journey']['garage']['cars']['lx_suv_09']['c'], 'hong_ngoc')
        self.assertFalse(any('🧮' in h['label'] for h in back['journey']['history']))   # no tool bonus there
        back = E.migrate_state(back)
        validate_state(back)
        self.assertEqual(au.tool_pct(back, 'grocery')[0], 3)
        self.assertEqual(gr.bonus_now(back)['pct'], 6)                         # 79A-567.89 (tier 2 car 5 %) + limited 1
        pet = pt.get(back)['list'][0]
        self.assertEqual(pw.bonus_bp(back, pet), pw.BONUS_BP[6] + pw.LUX_BONUS)
        E.public_state(back)


if __name__ == '__main__':
    unittest.main()
