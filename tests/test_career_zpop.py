"""Tiệm album Mây Pop (plugin career zpop): the morning (count, the limit sign, the demo lightstick, the pre-order
deadline paid into the stock), the customer's words mapped to the right version (a member's card for sure, a CD, Bluetooth
and its batteries, the cheapest), the counter's options (Zchart, the poster tube, fansign entries, POB), the per-person
limit, the annoying customers decided by hidden traits, the cases, the apprenticeship, the till, determinism, money only
from goods sold, save validation, old saves and the rollback to 1.9.9 (MNL_OLD_TREE)."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Journey
from game import journey as jr
from game import guide_content as G
from game.careers import kit, till, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state, apply_action

ZP = PLUGINS.get('zpop')
ROOT = Path(__file__).resolve().parents[1]
if ZP:
    from game.careers.zpop_content import TW, SKU, ORDERS, CASES, PEOPLE, MEMBERS


def find(pred, days=range(1, 60), slots=range(1, 8)):
    for day in days:
        for slot in slots:
            t = make_task('zpop', day, slot, 1)
            if pred(t):
                return day, slot
    raise AssertionError('no such task')


def by_title(title):
    return lambda t: t['title'] == title


def best_answer(t):
    sid, trait = t['needs']['tw'], ZP.trait_of(t)
    for want in ('good', 'ok'):
        for a in TW[sid]['answers']:
            if ZP._by(a['q'], trait) == want:
                return a['id']
    return TW[sid]['answers'][0]['id']


class Base(unittest.TestCase):
    def setUp(self):
        if ZP is None:
            raise unittest.SkipTest('zpop is filtered out by MNL_CAREERS')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, learning=False, stock=6):
        """A customer on their own, the shop open, every shelf stocked."""
        self.j = Journey('zpop', slot=slot, day=day)
        d = ZP._data(self.j.c)
        d['intro'] = True
        d['shop'].update(day=day, open=True, counted=True, sign=ZP.limit_of(day), demo=True, battery=True)
        d['learn']['done'] = not learning
        d['pob'] = 10
        for x in ZP.ITEMS:
            kit.add_lot(self.j.c, x['id'], stock, x['cost'], 999, 'test')
        return self.j.task

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}

    def fill(self, tid, skip=()):
        """Put exactly what the customer wants in the basket (the limit applied)."""
        t = self.j.get(tid)
        n = t['needs']
        nolimit = bool((t.get('tw') or {}).get('nolimit'))
        for line in n['lines']:
            want = line['qty']
            if n.get('upto'):
                want = min(want, sum(kit.stock(self.j.c, k) for k in line['any']))
            if n['limit'] and not nolimit and any(SKU[k].get('limited') for k in line['any']):
                want = min(want, n['limit'])
            for k in line['any']:
                while want > 0 and kit.stock(self.j.c, k) > self.j.get(tid)['cart'].get(k, 0):
                    self.j.act('zp_add', task=tid, sku=k)
                    want -= 1
        for key in ('zchart', 'tube', 'raffle', 'pob'):
            if n.get(key) and key not in skip:
                self.j.act('zp_opt', task=tid, key=key, on=True)

    def settle_tw(self, tid, answer=None):
        t = self.j.get(tid)
        sid = t['needs'].get('tw')
        if not sid:
            return
        for p in TW[sid]['probes']:
            if not self.j.get(tid)['tw']['done']:
                self.j.act('zp_probe', task=tid, probe=p['id'])
        for _ in range(3):
            if self.j.get(tid)['tw']['done']:
                break
            self.j.act('zp_ans', task=tid, answer=answer or best_answer(self.j.get(tid)))

    def ring_pay(self, tid):
        r = self.j.act('zp_ring', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        return self.j.act('zp_pay', task=tid, change=till.greedy(max(0, till.due(t['cash']))))

    def serve(self, tid):
        if not self.j.get(tid)['known']:
            self.j.act('ask', task=tid)
        self.settle_tw(tid)
        if self.j.get(tid)['status'] == 'completed':
            return None
        self.fill(tid)
        return self.ring_pay(tid)


class Spec(Base):
    def test_spec_and_registries(self):
        s = ZP.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('zpop', 'zp_', 'shop'))
        self.assertTrue(5 <= len(s['people']) <= 7)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('zpop', jr.CH_UNLOCKS[3])
        self.assertIn('zpop', G.ORDER)
        for name in ZP.ACTIONS:
            self.assertTrue(name.startswith('zp_'))
        for name in (*ZP.NO_TICK, *ZP.PHYSICAL, *ZP.FREE):
            self.assertTrue(name in ZP.ACTIONS or name in ('zp_intro', 'zp_desk'), name)
        town = (ROOT / 'public' / 'js' / 'scenes' / 'town-place.js').read_text(encoding='utf-8')
        self.assertIn("'com','zpop','lm:quan'", town)
        self.assertIn("zpop:'albumshop'", (ROOT / 'public' / 'js' / 'scenes' / 'index.js').read_text(encoding='utf-8'))

    def test_the_idols_are_fiction(self):
        """No real group, member, album or company: the parody stays a parody."""
        text = json.dumps([ZP.content(), ORDERS, CASES, TW, PEOPLE, ZP.DESK, ZP.SITUATIONS, ZP.INTRO], ensure_ascii=False).lower()
        for real in ('blackpink', 'jisoo', 'jennie', 'rosé', 'rose ', 'lisa', 'yg ', 'hybe', 'hanteo', 'circle chart', 'weverse',
                     'bts', 'twice', 'born pink', 'the album', 'square up', 'blink '):
            self.assertNotIn(real, text, real)
        self.assertIn('blankpink', text)
        self.assertIn('blinky', text)
        self.assertEqual(len(MEMBERS['bp']), 4)

    def test_orders_use_known_products_and_people(self):
        for o in ORDERS:
            self.assertTrue(0 <= o['npc'] < len(PEOPLE))
            for line in o['lines']:
                self.assertTrue(line['any'] and set(line['any']) <= set(ZP.SELL), line)
                self.assertIn(line['code'], ('', 'bias', 'cd', 'battery', 'cheap', 'bt'))
            self.assertTrue(o['tw'] is None or o['tw'] in ZP.SALE_TW)
            self.assertTrue(o['mod'] is None or o['mod'] in ZP.MOD)
        for x in CASES:
            self.assertIn(x['tw'], ZP.CASE_TW)
        for sid, x in TW.items():
            ids = [a['id'] for a in x['answers']]
            self.assertEqual(len(ids), len(set(ids)), sid)
            for trait in x['traits']:
                if not x.get('probe_only'):
                    self.assertTrue(any(ZP._by(a['q'], trait) == 'good' for a in x['answers']), (sid, trait))

    def test_tasks_are_deterministic_and_varied(self):
        kinds, tws = set(), set()
        for day in range(1, 40):
            for slot in range(0, 6):
                a, b = make_task('zpop', day, slot, 3), make_task('zpop', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
                tws.add(a['needs'].get('tw'))
        self.assertEqual(kinds, set(ZP.KINDS))
        self.assertGreaterEqual(len(tws - {None}), 10)

    def test_prices_keep_a_margin_and_stay_in_line(self):
        for k, price in ZP.PRICES.items():
            x = SKU[k]
            if not x.get('opened'):
                self.assertGreater(price, x['cost'], k)
        self.assertLessEqual(max(SKU[k]['price'] for k in SKU if SKU[k]['group'] == 'album'), 20)


class Morning(Base):
    def test_a_careful_morning_has_no_slip(self):
        day = next(d for d in range(2, 40) if ZP.mod_of(d)['id'] == 'normal' and ZP.demo_weak(d))
        self.j = Journey('zpop', slot=0, day=day)
        tid = self.j.task['id']
        self.j.act('zp_count', task=tid)
        self.j.act('zp_sign', task=tid, n=ZP.limit_of(day))
        r = self.j.act('zp_demo', task=tid)
        self.assertIn('Pin AAA', r['message'])
        before = kit.stock(self.j.c, 'pin_aaa')
        self.j.act('zp_battery', task=tid)
        self.assertEqual(kit.stock(self.j.c, 'pin_aaa'), before - 1)
        self.j.act('zp_open', task=tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        self.assertEqual(self.codes(tid), set())
        self.assertTrue(self.d['shop']['open'])

    def test_a_wrong_sign_and_skipped_checks_are_slips(self):
        day = next(d for d in range(3, 60) if ZP.mod_of(d)['id'] == 'comeback')
        self.j = Journey('zpop', slot=0, day=day)
        tid = self.j.task['id']
        self.j.act('zp_sign', task=tid, n=3)          # the distributor says 2 on a comeback day
        self.j.act('zp_open', task=tid)
        self.assertTrue({'sign', 'no_count', 'no_demo'} <= self.codes(tid))

    def test_the_deadline_closes_the_book_at_cost(self):
        day = next(d for d in range(2, 60) if ZP.mod_of(d)['id'] == 'chot')
        self.j = Journey('zpop', slot=0, day=day)
        tid = self.j.task['id']
        need = ZP.book_total(day)
        money, stock = self.j.c['money'], kit.stock(self.j.c, 'ps_jewel')
        self.j.act('zp_close', task=tid, qty=need)
        self.assertEqual(self.j.c['money'], money - need * SKU['ps_jewel']['cost'])
        self.assertEqual(kit.stock(self.j.c, 'ps_jewel'), stock + need)
        with self.assertRaises(GameError):
            self.j.act('zp_close', task=tid, qty=1)
        self.assertNotIn('close_short', self.codes(tid))

    def test_closing_short_or_forgetting_is_a_slip(self):
        day = next(d for d in range(2, 60) if ZP.mod_of(d)['id'] == 'chot')
        self.j = Journey('zpop', slot=0, day=day)
        tid = self.j.task['id']
        self.j.act('zp_close', task=tid, qty=max(0, ZP.book_total(day) - 2))
        self.assertIn('close_short', self.codes(tid))
        j2 = Journey('zpop', slot=0, day=day)
        t2 = j2.task['id']
        j2.act('zp_open', task=t2)
        self.assertIn('no_close', {x['code'] for x in j2.get(t2)['slips']})

    def test_no_customer_before_opening(self):
        day, slot = find(by_title('Mít mua quà cho ba'))
        self.at(day, slot)
        self.d['shop']['open'] = False
        tid = self.j.task['id']
        self.j.act('ask', task=tid)
        with self.assertRaises(GameError):
            self.j.act('zp_add', task=tid, sku='gm_sang')
        can = public_state(self.j.state)['careers']['zpop']['data']['can']['open']
        self.assertIsInstance(can, dict)


class Versions(Base):
    def test_a_member_card_for_sure_is_that_member_s_digipack(self):
        day, slot = find(by_title('Na săn card Mận-Ji'))
        t = self.at(day, slot)
        tid = t['id']
        self.j.act('ask', task=tid)
        money, stock = self.j.c['money'], kit.stock(self.j.c, 'ps_digi_manji')
        self.fill(tid)
        r = self.ring_pay(tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed', r)
        self.assertEqual(self.codes(tid), set())
        self.assertEqual(self.j.c['money'] - money, self.j.get(tid)['price'] + self.j.get(tid).get('tip_given', 0))
        self.assertEqual(kit.stock(self.j.c, 'ps_digi_manji'), stock - 1)

    def test_a_random_version_for_a_sure_card_is_the_bias_slip(self):
        day, slot = find(by_title('Na săn card Mận-Ji'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        self.j.act('zp_add', task=tid, sku='ps_pink')
        self.j.act('zp_opt', task=tid, key='zchart', on=True)
        self.ring_pay(tid)
        self.assertIn('bias', self.codes(tid))

    def test_the_kit_version_has_no_cd(self):
        day, slot = find(by_title('Mít mua quà cho ba'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        self.j.act('zp_add', task=tid, sku='gm_kit')
        self.ring_pay(tid)
        self.assertIn('cd', self.codes(tid))

    def test_either_cd_version_will_do(self):
        day, slot = find(by_title('Mít mua quà cho ba'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        self.j.act('zp_add', task=tid, sku='gm_dem')
        self.ring_pay(tid)
        self.assertEqual(self.codes(tid), set())

    def test_the_wrong_batteries_and_an_extra_item(self):
        day, slot = find(by_title('Na đi concert tối nay'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        for k in ('bua2', 'pin_aaa', 'slogan'):
            self.j.act('zp_add', task=tid, sku=k)
        self.ring_pay(tid)
        self.assertTrue({'battery', 'extra'} <= self.codes(tid))

    def test_the_limit_caps_a_line_and_selling_over_it_is_a_slip(self):
        day, slot = find(by_title('Tuấn mua đúng luật'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        limit = self.j.get(tid)['needs']['limit']
        for _ in range(limit + 1):
            self.j.act('zp_add', task=tid, sku='ps_jewel')
        self.ring_pay(tid)
        if limit < 3:
            self.assertIn('limit', self.codes(tid))

    def test_comeback_three_jewels_sell_two(self):
        day, slot = find(by_title('Na nộp phiếu fansign'))
        tid = self.at(day, slot)['id']
        self.d['pob'] = 5
        self.j.act('ask', task=tid)
        self.assertEqual(self.j.get(tid)['needs']['limit'], 2)
        self.fill(tid)
        self.assertEqual(self.j.get(tid)['cart'], {'ps_jewel': 2})
        entries = self.d['raffle']
        self.ring_pay(tid)
        self.assertEqual(self.codes(tid), set())
        self.assertEqual(self.d['raffle'], entries + 2)
        self.assertEqual(self.d['pob'], 3)

    def test_counter_options_and_their_stock(self):
        day, slot = find(by_title('Na giữ poster'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        tubes = kit.stock(self.j.c, 'ong_poster')
        self.fill(tid)
        self.ring_pay(tid)
        self.assertEqual(kit.stock(self.j.c, 'ong_poster'), tubes - 1)
        self.assertEqual(self.codes(tid), set())

    def test_a_forgotten_poster_tube_and_zchart(self):
        day, slot = find(by_title('Na giữ poster'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        self.fill(tid, skip=('tube',))
        self.ring_pay(tid)
        self.assertIn('poster', self.codes(tid))

    def test_a_zchart_ban_greys_the_scan(self):
        day, slot = find(by_title('Na săn card Mận-Ji'))
        tid = self.at(day, slot)['id']
        self.d['zban'] = day + 1
        self.j.act('ask', task=tid)
        with self.assertRaises(GameError):
            self.j.act('zp_opt', task=tid, key='zchart', on=True)
        can = public_state(self.j.state)['careers']['zpop']['data']['can']['opt']['zchart']
        self.assertIsInstance(can, dict)

    def test_out_of_stock_is_said_honestly_and_only_then(self):
        day, slot = find(by_title('Na thiếu một bản'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        with self.assertRaises(GameError):
            self.j.act('zp_decline', task=tid)
        kit.take(self.j.c, 'kb_std', kit.stock(self.j.c, 'kb_std'))
        money = self.j.c['money']
        self.j.act('zp_decline', task=tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        self.assertEqual(self.j.c['money'], money)


class Hidden(Base):
    def test_the_order_is_hidden_before_asking_and_the_trait_always(self):
        day, slot = find(by_title('Chị Kiều gom bản giới hạn'))
        tid = self.at(day, slot)['id']
        pub = public_state(self.j.state)['careers']['zpop']
        t = next(x for x in pub['tasks'] if x['id'] == tid)
        self.assertIsNone(t['needs'])
        self.j.act('ask', task=tid)
        raw = json.dumps(public_state(self.j.state), ensure_ascii=False)
        self.assertNotIn('_tw', raw)
        self.assertNotIn('"trait"', raw)

    def test_the_parent_s_list_is_the_kid_s_note(self):
        day, slot = find(by_title('Cô Hạnh nhầm nhóm'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        t = next(x for x in public_state(self.j.state)['careers']['zpop']['tasks'] if x['id'] == tid)
        self.assertTrue(t['needs']['hidden'])
        self.assertEqual(t['needs']['lines'], [])
        self.assertIn('PINK STATIC', t['needs']['guess'])
        with self.assertRaises(GameError):
            self.j.act('zp_ring', task=tid)
        r = self.j.act('zp_probe', task=tid, probe='note')
        self.assertIn('Gió Mùa bản Đêm', r['message'])
        t = next(x for x in public_state(self.j.state)['careers']['zpop']['tasks'] if x['id'] == tid)
        self.assertEqual([l['any'] for l in t['needs']['lines']], [['gm_dem']])
        self.j.act('zp_add', task=tid, sku='ps_pink')       # what mum pointed at
        self.ring_pay(tid)
        self.assertTrue({'missing', 'extra'} <= self.codes(tid) or 'version' in self.codes(tid))


class Twists(Base):
    def tw(self, title, trait=None):
        day, slot = find(lambda t: t['title'] == title and (trait is None or ZP.trait_of(t) == trait))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        return tid

    def test_the_trader_never_opens_before_paying(self):
        tid = self.tw('Tuấn đòi khui tại quầy', 'calm')
        self.j.act('zp_add', task=tid, sku='ps_pink')
        with self.assertRaises(GameError):
            self.j.act('zp_ring', task=tid)
        self.j.act('zp_ans', task=tid, answer='corner')
        self.assertTrue(self.j.get(tid)['tw']['done'])
        self.j.act('zp_drop', task=tid, sku='ps_pink')
        self.fill(tid)
        self.ring_pay(tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        self.assertEqual(self.codes(tid), set())

    def test_a_pushy_trader_comes_back_once(self):
        tid = self.tw('Tuấn đòi khui tại quầy', 'pushy')
        r = self.j.act('zp_ans', task=tid, answer='corner')
        self.assertIn('MỘT bản', r['message'])
        self.assertFalse(self.j.get(tid)['tw']['done'])
        self.j.act('zp_ans', task=tid, answer='corner')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')

    def test_opening_first_costs_three_albums_and_the_sale(self):
        tid = self.tw('Tuấn đòi khui tại quầy', 'calm')
        stock, money = kit.stock(self.j.c, 'ps_pink'), self.j.c['money']
        self.j.act('zp_ans', task=tid, answer='open_first')
        t = self.j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(kit.stock(self.j.c, 'ps_pink'), stock - 3)
        self.assertEqual(self.j.c['money'], money)
        self.assertEqual(t['tw']['q'], 'bad')

    def test_receipts_only_locks_the_shop_out_of_zchart(self):
        tid = self.tw('Anh Dũng đẩy chart')
        self.j.act('zp_ans', task=tid, answer='receipt')
        self.assertGreater(self.d['zban'], self.j.c['day'])
        self.assertEqual(self.j.get(tid)['disc'], 30)
        self.assertTrue(any(p.get('stars') == 1 and p.get('npc') == kit.npc_id('zpop', 1) for p in self.j.c['feed']))

    def test_the_bulk_buyer_takes_what_the_shelf_has(self):
        tid = self.tw('Anh Dũng đẩy chart')
        self.settle_tw(tid)
        self.fill(tid)
        self.assertEqual(sum(self.j.get(tid)['cart'].values()), 30)     # as many as asked, the shelf has more
        self.ring_pay(tid)
        self.assertEqual(self.codes(tid), set())

    def test_selling_every_limited_copy_to_the_reseller(self):
        tid = self.tw('Chị Kiều gom bản giới hạn', 'reseller')
        r = self.j.act('zp_ans', task=tid, answer='limit')
        self.assertIn('20 xu', r['message'])         # she pushes once
        self.j.act('zp_ans', task=tid, answer='all')
        t = self.j.get(tid)
        self.assertTrue(t['tw']['nolimit'])
        self.assertEqual(t['tw']['q'], 'bad')
        self.fill(tid)
        self.assertEqual(self.j.get(tid)['cart'], {'ps_jewel': 10})
        self.ring_pay(tid)
        self.assertNotIn('limit', self.codes(tid))   # she is happy; the fans who missed out write the review
        self.assertTrue(any(p.get('stars') == 1 and p.get('npc') == kit.npc_id('zpop', 1) for p in self.j.c['feed']))

    def test_a_stranger_picking_up_a_pre_order(self):
        tid = self.tw('Chị Kiều lấy hàng đặt trước', 'stranger')
        r = self.j.act('zp_probe', task=tid, probe='phone')
        self.assertIn('7730', r['message'])
        self.j.act('zp_ans', task=tid, answer='hold')
        t = self.j.get(tid)
        self.assertEqual((t['status'], t['tw']['q']), ('completed', 'good'))

    def test_handing_a_pre_order_to_a_stranger_costs_two_jewels(self):
        tid = self.tw('Chị Kiều lấy hàng đặt trước', 'stranger')
        stock = kit.stock(self.j.c, 'ps_jewel')
        self.j.act('zp_ans', task=tid, answer='give')
        self.assertEqual(kit.stock(self.j.c, 'ps_jewel'), stock - 2)
        self.assertEqual(self.j.get(tid)['tw']['q'], 'bad')

    def test_a_friend_with_the_code_gets_the_pre_order(self):
        tid = self.tw('Mít lấy hàng đặt trước giùm', 'friend')
        r = self.j.act('zp_probe', task=tid, probe='code')
        self.assertIn('MP-117', r['message'])
        self.j.act('zp_ans', task=tid, answer='give')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')
        self.fill(tid)
        self.ring_pay(tid)
        self.assertEqual(self.codes(tid), set())

    def test_the_fansign_odds_are_told_as_shown(self):
        tid = self.tw('Na hỏi tỉ lệ fansign', 'calm')
        o = ZP.odds_text(self.j.c['day'])
        pub = next(x for x in public_state(self.j.state)['careers']['zpop']['tasks'] if x['id'] == tid)
        honest = next(a for a in pub['tw']['answers'] if a['id'] == 'honest')
        self.assertIn('30 suất', honest['label'])
        self.assertIn(o['pct'], honest['label'])
        self.j.act('zp_ans', task=tid, answer='promise')
        self.assertIn('tw_bad', self.codes(tid))

    def test_a_queue_jumper_without_a_ticket(self):
        tid = self.tw('Na xếp hàng từ sáu giờ', 'liar')
        self.d['pob'] = 5
        self.j.act('zp_probe', task=tid, probe='ticket')
        self.j.act('zp_ans', task=tid, answer='order')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')


class Cases(Base):
    def case(self, title, trait):
        day, slot = find(lambda t: t['title'] == title and ZP.trait_of(t) == trait)
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        return tid

    def test_no_refund_for_the_wrong_member(self):
        tid = self.case('Mít đòi trả album', 'wrong_member')
        money = self.j.c['money']
        r = self.j.act('zp_probe', task=tid, probe='look')
        self.assertIn('Sữa-Ah', r['message'])
        self.j.act('zp_ans', task=tid, answer='policy')
        t = self.j.get(tid)
        self.assertEqual((t['status'], t['tw']['q']), ('completed', 'good'))
        self.assertEqual(self.j.c['money'], money)

    def test_a_refund_costs_the_album_s_price(self):
        tid = self.case('Mít đòi trả album', 'wrong_member')
        money = self.j.c['money']
        self.j.act('zp_ans', task=tid, answer='refund')
        self.assertEqual(self.j.c['money'], money - SKU['ps_pink']['price'])
        self.assertEqual(self.j.get(tid)['tw']['q'], 'bad')

    def test_an_album_missing_its_card_is_exchanged(self):
        tid = self.case('Mít đòi trả album', 'empty')
        self.j.act('zp_probe', task=tid, probe='look')
        self.j.act('zp_ans', task=tid, answer='swap')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')

    def test_a_fake_lightstick_is_explained_not_warrantied(self):
        tid = self.case('Búa hồng mua trên mạng', 'fake')
        r = self.j.act('zp_probe', task=tid, probe='serial')
        self.assertIn('000000', r['message'])
        money = self.j.c['money']
        self.j.act('zp_ans', task=tid, answer='warranty')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'bad')
        self.assertLess(self.j.c['money'], money)

    def test_pairing_takes_the_right_fix_and_wrong_tries_cost_patience(self):
        tid = self.case('Búa ver.2 không ghép ghế', 'app')
        r = self.j.act('zp_ans', task=tid, answer='flip')
        self.assertFalse(self.j.get(tid)['tw']['done'])
        self.assertIs(r.get('correct'), False)
        self.j.act('zp_probe', task=tid, probe='app')
        self.j.act('zp_ans', task=tid, answer='update')
        t = self.j.get(tid)
        self.assertEqual((t['status'], t['tw']['q']), ('completed', 'ok'))   # right in the end, after a wrong try

    def test_bootlegs_are_refused(self):
        tid = self.case('Lô album gửi bán', 'bootleg')
        for p in ('tem', 'src'):
            self.j.act('zp_probe', task=tid, probe=p)
        self.j.act('zp_ans', task=tid, answer='refuse')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')

    def test_fanmade_goods_go_on_the_free_board(self):
        tid = self.case('Lô album gửi bán', 'fanmade')
        self.assertIn('fanmade', self.j.get(tid)['opening'].lower())
        self.j.act('zp_probe', task=tid, probe='tem')
        self.j.act('zp_ans', task=tid, answer='board')
        self.assertEqual(self.j.get(tid)['tw']['q'], 'good')


class Apprenticeship(Base):
    def test_chi_tho_stops_each_mistake_once(self):
        day, slot = find(by_title('Na săn card Mận-Ji'))
        tid = self.at(day, slot, learning=True)['id']
        self.j.act('ask', task=tid)
        self.j.act('zp_add', task=tid, sku='ps_pink')
        r = self.j.act('zp_ring', task=tid)
        self.assertEqual(r.get('lesson'), 'bias')
        self.assertEqual(self.j.get(tid)['stage'], 'prep')
        self.assertEqual(self.codes(tid), set())
        r = self.j.act('zp_ring', task=tid)
        self.assertEqual(r.get('lesson'), 'zchart')
        r = self.j.act('zp_ring', task=tid)
        self.assertEqual(self.j.get(tid)['stage'], 'pay', r)
        self.assertIn('bias', self.codes(tid))


class Surprises(Base):
    def test_every_surprise_option_and_situation_runs(self):
        day, slot = find(by_title('Mít mua quà cho ba'), days=range(5, 40))
        self.at(day, slot)
        j = self.j
        for x in ZP.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
            for o in x['options']:
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('zp_add', task=j.task['id'], sku='gm_sang')
                self.assertTrue(j.act('zp_desk', option=o['id'])['message'])
        for x in ZP.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(json.loads(json.dumps(j.state)))


class Saves(Base):
    def test_round_trip_and_tampering(self):
        day, slot = find(by_title('Chị Kiều gom bản giới hạn'))
        tid = self.at(day, slot)['id']
        self.j.act('ask', task=tid)
        self.j.act('zp_probe', task=tid, probe='phone')
        validate_state(json.loads(json.dumps(self.j.state)))
        for mutate in (lambda t: t['needs']['lines'][0].update(qty=1),
                       lambda t: t['_tw'].update(trait='family' if t['_tw']['trait'] == 'reseller' else 'reseller'),
                       lambda t: t['cart'].update(bogus=1),
                       lambda t: t['tw']['asked'].append('nope'),
                       lambda t: t['opt'].update(zchart='yes')):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['zpop']['tasks'] if x['id'] == tid)
            mutate(t)
            with self.assertRaises(GameError):
                validate_state(s)
        for path, value in ((('shop', 'sign'), 4), (('pob',), -1), (('learn', 'codes'), ['nope']), (('regulars',), {'9': {'visits': 1}})):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['zpop']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_data_from_an_older_build_fills_in(self):
        day, slot = find(by_title('Mít mua quà cho ba'))
        self.at(day, slot)
        for k in ('learn', 'regulars', 'stats', 'raffle'):
            self.d.pop(k)
        self.d['shop'].pop('closed')
        self.j.act('ask', task=self.j.task['id'])
        validate_state(self.j.state)

    def test_a_save_without_the_shop_gains_it_fresh_and_nothing_else_moves(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s['careers'].pop('zpop')
        s['journey']['unlocked'] = [x for x in s['journey']['unlocked'] if x != 'zpop']
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['zpop'], sort_keys=True), json.dumps(initial_career('zpop'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)


def solve(j, tid):
    """The careful player (also used for the days below)."""
    t = j.get(tid)
    if t['kind'] == 'setup':
        n = t['needs']
        j.act('zp_count', task=tid)
        j.act('zp_sign', task=tid, n=n['limit'])
        j.act('zp_demo', task=tid)
        if ZP.demo_weak(j.c['day']) and kit.stock(j.c, 'pin_aaa'):
            j.act('zp_battery', task=tid)
        if n.get('chot'):
            j.act('zp_close', task=tid, qty=ZP.book_total(j.c['day']))
        j.act('zp_open', task=tid)
        return
    if not t['known']:
        j.act('ask', task=tid)
    t = j.get(tid)
    sid = t['needs'].get('tw')
    if sid:
        for p in TW[sid]['probes']:
            if not j.get(tid)['tw']['done']:
                j.act('zp_probe', task=tid, probe=p['id'])
        for _ in range(3):
            if j.get(tid)['tw']['done']:
                break
            j.act('zp_ans', task=tid, answer=best_answer(j.get(tid)))
    t = j.get(tid)
    if t['status'] == 'completed':
        return
    n = t['needs']
    for line in n['lines']:
        want = line['qty']
        if n.get('upto'):
            want = min(want, sum(kit.stock(j.c, k) for k in line['any']))
        if n['limit'] and not t['tw'] or n['limit'] and not t['tw'].get('nolimit'):
            if any(SKU[k].get('limited') for k in line['any']):
                want = min(want, n['limit'])
        for k in line['any']:
            while want > 0 and kit.stock(j.c, k) > j.get(tid)['cart'].get(k, 0):
                j.act('zp_add', task=tid, sku=k)
                want -= 1
    for key in ('zchart', 'tube', 'raffle', 'pob'):
        if n.get(key):
            try:
                j.act('zp_opt', task=tid, key=key, on=True)
            except GameError:
                pass
    if not j.get(tid)['cart']:
        j.act('zp_decline', task=tid)
        return
    j.act('zp_ring', task=tid)
    t = j.get(tid)
    j.act('zp_pay', task=tid, change=till.greedy(max(0, till.due(t['cash']))))


class Days(Base):
    def test_twelve_days_of_play_stay_valid_and_money_comes_only_from_goods(self):
        self.j = Journey('zpop')
        self.j.act('zp_intro')
        paid = 0
        for _ in range(12):
            for x in ZP.ITEMS:
                if kit.stock(self.j.c, x['id']) < x['start']:
                    kit.add_lot(self.j.c, x['id'], x['start'], x['cost'], 999, 'test')
            for _ in range(12):
                ev = self.d['desk']['ev']
                if ev:
                    self.j.act('zp_desk', option=kit.desk_script(ZP.DESK, ev['script'])['default'])
                open_ = [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
                if not open_:
                    break
                solve(self.j, open_[0]['id'])
            done = [t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['status'] == 'completed']
            for t in done:
                if t['kind'] != 'sale':
                    continue
                # what a customer hands over is never more than the bill (cash)
                self.assertLessEqual((t.get('cash') or {}).get('price', 0), sum(ZP._price(self.j.c, k) * q for k, q in (t.get('sold') or {}).items()))
                paid += (t.get('cash') or {}).get('price', 0)
            ev = self.d['desk']['ev']
            if ev:
                self.j.act('zp_desk', option=kit.desk_script(ZP.DESK, ev['script'])['default'])
            r = self.j.act('end_day', carry_event=True)
            self.assertIn('units', r['summary']['career'])
            self.j.act('start_day')
            validate_state(self.j.state)
        self.assertGreater(paid, 0)
        self.assertGreaterEqual(self.d['stats']['customers'], 20)


# ------------------------------------------------------------ the rolling release and a rollback to 1.9.9
OLD_TREE = os.environ.get('MNL_OLD_TREE')     # a rel-1.9.9 tree (git archive rel-1.9.9 game reference i18n | tar -x -C DIR)
OLD_CHECK = r'''
import json, sys
from game.engine import migrate_state, validate_state, GameError
s = json.load(open(sys.argv[1], encoding='utf-8'))
try:
    validate_state(migrate_state(s))
    print('ok')
except GameError as e:
    print('rejected:', e)
'''


def strip_zpop(s):
    """What a rollback to a tree without the album shop needs: the career block gone and the id out of every list."""
    s = copy.deepcopy(s)
    s['careers'].pop('zpop', None)
    if s.get('current') == 'zpop':
        s['current'] = next(iter(s['careers']))

    def ours(v):
        return isinstance(v, str) and (v == 'zpop' or v.startswith('zpop_') or v.startswith('zpop-'))

    def scrub(o):
        if isinstance(o, dict):
            for k in [k for k in o if ours(k)]:
                del o[k]
            for v in o.values():
                scrub(v)
        elif isinstance(o, list):
            o[:] = [v for v in o if not ours(v) and not (isinstance(v, dict) and any(ours(x) for x in v.values()))]
            for v in o:
                scrub(v)
    for k, v in s.items():
        if k != 'careers':
            scrub(v)
    return s


@unittest.skipUnless(OLD_TREE and Path(OLD_TREE, 'game', 'engine.py').exists(), 'set MNL_OLD_TREE to a rel-1.9.9 tree')
class Release199(Base):
    """1.9.9 → here, and here → 1.9.9 (a rollback, or an old worker meeting a new save during the switch)."""

    def run_old(self, state):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, 's.json')
            p.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
            env = dict(os.environ, PYTHONPATH=OLD_TREE)
            env.pop('MNL_CAREERS', None)
            out = subprocess.run([sys.executable, '-c', OLD_CHECK, str(p)], cwd=OLD_TREE, env=env, capture_output=True, text=True, timeout=300)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            return out.stdout.strip().splitlines()[-1]

    def test_1_9_9_refuses_a_save_that_names_the_album_shop_until_it_is_stripped(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        self.assertIn('zpop', s['careers'])
        self.assertTrue(self.run_old(s).startswith('rejected'))     # "Bản lưu cần đủ các nghề."
        self.assertEqual(self.run_old(strip_zpop(s)), 'ok')
        self.j = Journey('zpop')                                     # someone who played the album shop
        self.j.act('zp_intro')
        solve(self.j, self.j.task['id'])
        self.assertEqual(self.run_old(strip_zpop(self.j.state)), 'ok')


if __name__ == '__main__':
    unittest.main()
