import copy
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import farm as F
from tests.helpers import Journey


def find(pred, days=range(1, 10), slots=range(6)):
    for day in days:
        for slot in slots:
            if pred(F.make_task(day, slot, 1)):
                return day, slot
    raise AssertionError('no matching farm task')


def journey(title):
    day, slot = find(lambda t: t['title'] == title)
    return Journey('farm', slot=slot, day=day)


def data(j):
    return j.c['ext']['data']


def plot(j, pid):
    return data(j)['plots'][F.PLOT_IDS.index(pid)]


def view(j):
    return public_state(j.state)['careers']['farm']


def add_lot(j, crop, qty, grade='A', organic=True):
    return F._add_lot(j.c, data(j), crop, grade, qty, organic, False, 'P6' if crop != 'egg' else 'coop')['id']


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


def post_for(j, tid):
    return next(p for p in j.c['feed'] if p.get('source') == tid)


class FarmOrderTests(unittest.TestCase):
    def test_happy_path_market_order(self):
        j = journey('Cô Hai đi chợ sớm')
        tid = j.task['id']
        j.act('ask')
        n = j.task['needs']
        bags, trays, before = kit.stock(j.c, 'bag'), kit.stock(j.c, 'egg_tray'), j.c['money']
        for crop, q in n['items'].items():
            lot = next(l for l in data(j)['cold'] if l['crop'] == crop)
            if lot['qty'] < q:
                lot = data(j)['cold'][data(j)['cold'].index(lot)]
                lot['qty'] = q
            j.act('fa_pack', task=tid, lot=lot['id'], qty=q)
        j.act('fa_label', task=tid, label='plain')
        r = j.act('fa_deliver', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['served']['missing'], 0)
        self.assertGreaterEqual(j.c['money'] - before, t['served']['pay'])
        self.assertEqual(kit.stock(j.c, 'bag'), bags - 1)
        self.assertEqual(kit.stock(j.c, 'egg_tray'), trays - 1)
        self.assertGreaterEqual(post_for(j, tid)['stars'], 4)
        self.assertIn('Đủ', r['message'])
        roundtrip(j)

    def test_needs_and_pests_hidden(self):
        j = Journey('farm')
        v = view(j)
        self.assertTrue(all(t['needs'] is None for t in v['tasks']))
        self.assertTrue(all('pests' not in p for p in v['data']['plots']))
        plot(j, 'P2')['pests'] = 2
        j.act('fa_scout', plot='P2')
        p2 = next(p for p in view(j)['data']['plots'] if p['id'] == 'P2')
        self.assertEqual(p2['seen'], 2)
        self.assertNotIn('pests', p2)
        j.act('ask')
        self.assertIsNotNone(next(t for t in view(j)['tasks'] if t['id'] == j.c['active_task'])['needs'])

    def test_order_actions_need_ask(self):
        j = journey('Cô Hai đi chợ sớm')
        with self.assertRaises(GameError):
            j.act('fa_pack', lot='L1', qty=1)

    def test_false_organic_label_refused(self):
        j = journey('Xà lách hữu cơ cho quán chay')
        tid = j.task['id']
        j.act('ask')
        want = j.task['needs']['items']['lettuce']
        chem = add_lot(j, 'lettuce', want, organic=False)
        clean = add_lot(j, 'lettuce', want, organic=True)
        j.act('fa_pack', task=tid, lot=chem, qty=want)
        j.act('fa_label', task=tid, label='organic')
        r = j.act('fa_deliver', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('QR', r['message'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('fa_label', task=tid, label='plain')
        r = j.act('fa_deliver', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))   # the contract is for organic produce
        self.assertEqual(j.task['mistakes'], 2)
        j.act('fa_unpack', task=tid, lot=chem)
        self.assertEqual(next(l for l in data(j)['cold'] if l['id'] == chem)['qty'], want)
        j.act('fa_pack', task=tid, lot=clean, qty=want)
        j.act('fa_label', task=tid, label='organic')
        j.act('fa_deliver', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['served']['pay'], want * F.PRICES['lettuce'] * F.ORGANIC_PERCENT // 100)
        roundtrip(j)

    def test_eggs_are_never_organic_and_use_trays(self):
        j = journey('Trứng cho mẻ bánh flan')
        tid = j.task['id']
        j.act('ask')
        lot = next(l for l in data(j)['cold'] if l['crop'] == 'egg')
        j.act('fa_pack', task=tid, lot=lot['id'], qty=20)
        j.act('fa_label', task=tid, label='organic')
        r = j.act('fa_deliver', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('cám', r['message'])
        trays, cartons = kit.stock(j.c, 'egg_tray'), kit.stock(j.c, 'carton')
        j.act('fa_label', task=tid, label='plain')
        j.act('fa_deliver', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(kit.stock(j.c, 'egg_tray'), trays - 2)
        self.assertEqual(kit.stock(j.c, 'carton'), cartons - 1)

    def test_partial_delivery_paid_for_what_arrived(self):
        j = journey('Cô Hai đi chợ sớm')
        tid = j.task['id']
        j.act('ask')
        lot = next(l for l in data(j)['cold'] if l['crop'] == 'egg')
        j.act('fa_pack', task=tid, lot=lot['id'], qty=5)
        j.act('fa_label', task=tid, label='plain')
        r = j.act('fa_deliver', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['served']['pay'], 5 * F.PRICES['egg'])
        self.assertGreater(t['served']['missing'], 0)
        self.assertIn('thiếu', r['message'])
        quantity = next(x for x in post_for(j, tid)['feedback']['criteria'] if x['key'] == 'quantity')
        self.assertLess(quantity['score'], 5)

    def test_grade_b_in_contract_is_paid_less(self):
        j = journey('Cà chua cho nồi sốt')
        tid = j.task['id']
        j.act('ask')
        want = j.task['needs']['items']['tomato']
        b = add_lot(j, 'tomato', want, grade='B')
        j.act('fa_pack', task=tid, lot=b, qty=want)
        j.act('fa_label', task=tid, label='plain')
        j.act('fa_deliver', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['served']['pay'], want * (F.PRICES['tomato'] * F.B_PERCENT // 100))
        quality = next(x for x in post_for(j, tid)['feedback']['criteria'] if x['key'] == 'quality')
        self.assertLessEqual(quality['score'], 3)

    def test_packaging_must_be_in_stock(self):
        j = journey('Trứng cho mẻ bánh flan')
        tid = j.task['id']
        j.act('ask')
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == 'carton':
                lot['qty'] = 0
        lot = next(l for l in data(j)['cold'] if l['crop'] == 'egg')
        j.act('fa_pack', task=tid, lot=lot['id'], qty=20)
        j.act('fa_label', task=tid, label='plain')
        with self.assertRaises(GameError):
            j.act('fa_deliver', task=tid, confirm=True)

    def test_order_payload_validation(self):
        j = journey('Cô Hai đi chợ sớm')
        tid = j.task['id']
        j.act('ask')
        egg = next(l for l in data(j)['cold'] if l['crop'] == 'egg')
        bad = [dict(lot='L99', qty=1), dict(lot=egg['id'], qty=0), dict(lot=egg['id'], qty=99), dict(lot=egg['id'], qty='2'),
               dict(lot=egg['id'], qty=13)]
        for p in bad:
            with self.assertRaises(GameError, msg=str(p)):
                j.act('fa_pack', task=tid, **p)
        with self.assertRaises(GameError):
            j.act('fa_deliver', task=tid, confirm=True)   # empty crate
        j.act('fa_pack', task=tid, lot=egg['id'], qty=10)
        with self.assertRaises(GameError):
            j.act('fa_deliver', task=tid, confirm=True)   # no label
        for label in ('bio', None, 1):
            with self.assertRaises(GameError):
                j.act('fa_label', task=tid, label=label)
        j.act('fa_label', task=tid, label='plain')
        with self.assertRaises(GameError):
            j.act('fa_deliver', task=tid)
        with self.assertRaises(GameError):
            j.act('fa_unpack', task=tid, lot='L99')
        before = j.c['money']
        j.act('fa_deliver', task=tid, confirm=True, pay=99999, price=99999)
        self.assertLess(j.c['money'] - before, 200)

    def test_wrong_crop_and_expired_lot_refused(self):
        j = journey('Trứng cho mẻ bánh flan')
        tid = j.task['id']
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('fa_pack', task=tid, lot='L1', qty=1)   # muống is not in this order
        lot = next(l for l in data(j)['cold'] if l['crop'] == 'egg')
        lot['expires'] = j.c['day'] - 1
        with self.assertRaises(GameError):
            j.act('fa_pack', task=tid, lot=lot['id'], qty=1)


class FarmFieldTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('farm')

    def test_growth_follows_turns_and_weather(self):
        j = self.j
        g0, m0 = plot(j, 'P4')['growth'], plot(j, 'P4')['moisture']
        for _ in range(4):
            j.act('advance')
        p4 = next(p for p in view(j)['data']['plots'] if p['id'] == 'P4')
        self.assertGreaterEqual(p4['growth'], g0 + 4 * 3)
        self.assertEqual(p4['moisture'], m0 - 4 * F.WEATHER_INDEX['sun']['evap'])
        self.assertEqual(plot(j, 'P4')['growth'], g0)   # stored state catches up lazily
        j.act('fa_scout', plot='P4')
        self.assertGreater(plot(j, 'P4')['growth'], g0)
        roundtrip(j)

    def test_dry_soil_stops_growth_and_watering_helps(self):
        j = self.j
        plot(j, 'P4')['moisture'] = 10
        g0 = plot(j, 'P4')['growth']
        j.act('fa_scout', plot='P4')
        j.act('fa_scout', plot='P4')
        self.assertEqual(plot(j, 'P4')['growth'], g0)
        self.assertGreater(plot(j, 'P4')['stress'], 0)
        j.act('fa_water', plot='P4')
        self.assertGreater(plot(j, 'P4')['moisture'], F.MOIST_DRY)   # one can of water on bone-dry soil is not enough for ideal
        m = [p['moisture'] for p in data(j)['plots']]
        j.act('fa_water', plot='all')
        self.assertTrue(all(p['moisture'] >= min(100, x + F.WATER_ALL) - 4 for p, x in zip(data(j)['plots'], m)))

    def test_waterlogged_plot_needs_drain(self):
        j = self.j
        with self.assertRaises(GameError):
            j.act('fa_drain', plot='P4')
        plot(j, 'P4')['moisture'] = 100
        j.act('fa_drain', plot='P4')
        self.assertLess(plot(j, 'P4')['moisture'], 100 - F.DRAIN + 1)

    def test_plant_weed_and_field_validation(self):
        j = self.j
        seeds = kit.stock(j.c, 'seed_muong')
        j.act('fa_plant', plot='P6', crop='muong')
        self.assertEqual(plot(j, 'P6')['crop'], 'muong')
        self.assertEqual(kit.stock(j.c, 'seed_muong'), seeds - 1)
        self.assertTrue(any('gieo' in r['text'] for r in data(j)['diary']))
        bad = [('fa_plant', dict(plot='P6', crop='muong')), ('fa_plant', dict(plot='P9', crop='muong')),
               ('fa_plant', dict(plot='P6', crop='durian')), ('fa_water', dict(plot='P0')),
               ('fa_fertilize', dict(plot='P2', kind='urea')), ('fa_spray', dict(plot='P2', kind='magic')),
               ('fa_harvest', dict(plot='P5', confirm=True)), ('fa_harvest', dict(plot='P1')),
               ('fa_clear', dict(plot='P6')), ('fa_discard', dict(lot='L1')), ('fa_scout', dict(plot=3))]
        for action, p in bad:
            with self.assertRaises(GameError, msg=action):
                j.act(action, **p)
        j.act('fa_clear', plot='P6', confirm=True)
        with self.assertRaises(GameError):
            j.act('fa_plant', plot='P6', crop='cucumber')   # unlocks at level 2
        plot(j, 'P3')['weeds'] = 3
        j.act('fa_weed', plot='P3')
        self.assertEqual(plot(j, 'P3')['weeds'], 0)
        with self.assertRaises(GameError):
            j.act('fa_weed', plot='P3')
        roundtrip(j)

    def test_harvest_ripe_plot_to_cold_room(self):
        j = self.j
        n = len(data(j)['cold'])
        r = j.act('fa_harvest', plot='P1', confirm=True)
        self.assertTrue(r.get('celebrate'))
        lot = data(j)['cold'][-1]
        self.assertEqual((lot['crop'], lot['grade'], lot['organic'], lot['unsafe']), ('muong', 'A', True, False))
        self.assertEqual(len(data(j)['cold']), n + 1)
        self.assertIsNone(plot(j, 'P1')['crop'])

    def test_pests_lower_grade(self):
        j = self.j
        plot(j, 'P1')['pests'] = 2
        j.act('fa_harvest', plot='P1', confirm=True)
        grades = {l['grade'] for l in data(j)['cold'] if l['plot'] == 'P1' and l['day'] == j.c['day'] and l['id'] != 'L1'}
        self.assertEqual(grades, {'A', 'B'})

    def test_chemical_fertiliser_starts_phi_and_ends_organic(self):
        j = self.j
        j.act('fa_fertilize', plot='P1', kind='npk')
        self.assertFalse(plot(j, 'P1')['organic'])
        self.assertGreater(plot(j, 'P1')['phi'], j.c['turn'])
        r = j.act('fa_harvest', plot='P1', confirm=True)
        self.assertIn('cách ly', r['message'])
        lot = data(j)['cold'][-1]
        self.assertTrue(lot['unsafe'])
        self.assertEqual(data(j)['stats']['unsafe'], 1)
        j.act('ask')
        tid = j.task['id']
        if 'muong' in j.task['needs']['items']:
            with self.assertRaises(GameError):
                j.act('fa_pack', task=tid, lot=lot['id'], qty=1)
        j.act('fa_discard', lot=lot['id'], confirm=True)
        self.assertFalse(any(l['id'] == lot['id'] for l in data(j)['cold']))
        self.assertTrue(any('cách ly' in w['reason'] for w in j.c['life']['waste']))
        roundtrip(j)

    def test_waiting_out_phi_makes_harvest_safe(self):
        j = self.j
        j.act('fa_fertilize', plot='P4', kind='npk')
        for _ in range(60):
            p4 = next(p for p in view(j)['data']['plots'] if p['id'] == 'P4')
            if p4['safe_in'] == 0 and p4['growth'] >= F.RIPE:
                break
            if p4['moisture'] < F.MOIST_LOW:
                j.act('fa_water', plot='P4')
            elif p4['weeds'] >= 2:
                j.act('fa_weed', plot='P4')
            else:
                j.act('advance')
        j.act('fa_harvest', plot='P4', confirm=True)
        lots = [l for l in data(j)['cold'] if l['plot'] == 'P4']
        self.assertTrue(lots)
        self.assertTrue(all(not l['unsafe'] and not l['organic'] for l in lots))

    def test_sprays(self):
        j = self.j
        j.act('fa_spray', plot='P2', kind='bio')
        self.assertEqual(data(j)['stats']['wasted_spray'], 1)
        self.assertTrue(plot(j, 'P2')['organic'])
        plot(j, 'P3')['pests'] = 3
        j.act('fa_scout', plot='P3')
        j.act('fa_spray', plot='P3', kind='chem')
        self.assertEqual(plot(j, 'P3')['pests'], 0)
        self.assertFalse(plot(j, 'P3')['organic'])
        j.act('fa_fertilize', plot='P4', kind='compost')
        with self.assertRaises(GameError):
            j.act('fa_fertilize', plot='P4', kind='compost')
        self.assertTrue(plot(j, 'P4')['organic'])

    def test_hens_feed_collect_and_overnight(self):
        j = self.j
        feed = kit.stock(j.c, 'feed')
        j.act('fa_feed')
        self.assertEqual(kit.stock(j.c, 'feed'), feed - 1)
        with self.assertRaises(GameError):
            j.act('fa_feed')
        n = len(data(j)['cold'])
        j.act('fa_collect')
        self.assertEqual(data(j)['coop']['nest'], 0)
        self.assertGreater(len(data(j)['cold']), n)
        self.assertFalse(data(j)['cold'][-1]['organic'])
        with self.assertRaises(GameError):
            j.act('fa_collect')
        j.act('end_day', carry_event=True)
        self.assertEqual(data(j)['coop']['nest'], F.HENS)
        j.act('start_day')
        # Not fed today: half the eggs tomorrow, and uncollected eggs go stale.
        j.act('end_day', carry_event=True)
        self.assertEqual(data(j)['coop']['nest'], F.HENS + F.HENS // 2)
        self.assertEqual(data(j)['coop']['stale'], F.HENS)
        j.act('start_day')
        j.act('fa_collect')
        grades = [l['grade'] for l in data(j)['cold'] if l['plot'] == 'coop' and l['day'] == j.c['day']]
        self.assertIn('B', grades)
        roundtrip(j)


class FarmDayAndStateTests(unittest.TestCase):
    def test_day_cycle_growth_expiry_and_crate_return(self):
        j = journey('Cô Hai đi chợ sớm')
        tid = j.task['id']
        j.act('ask')
        j.act('fa_pack', task=tid, lot='L1', qty=2)
        g5 = plot(j, 'P5')['growth']
        summary = j.act('end_day', carry_event=True)['summary']
        self.assertIn('note', summary['career'])
        self.assertEqual(j.get(tid)['crate'], [])
        self.assertEqual(next(l for l in data(j)['cold'] if l['id'] == 'L1')['qty'], 6)
        self.assertGreaterEqual(plot(j, 'P5')['growth'], g5 + F.NIGHT_GROWTH)
        j.act('start_day')
        self.assertEqual(data(j)['turn'], j.c['turn'])
        j.act('end_day', carry_event=True)   # muống lots only last 2 days
        self.assertFalse(any(l['id'] == 'L1' for l in data(j)['cold']))
        self.assertTrue(any('kho mát' in w['reason'] for w in j.c['life']['waste']))
        j.act('start_day')
        roundtrip(j)

    def test_weather_is_deterministic(self):
        self.assertEqual(F._weather(1)['id'], 'sun')
        self.assertEqual([F._weather(d)['id'] for d in range(2, 12)], [F._weather(d)['id'] for d in range(2, 12)])
        j = Journey('farm')
        self.assertEqual(view(j)['data']['weather']['id'], 'sun')
        self.assertIn('forecast', view(j)['data'])

    def test_tampering_rejected(self):
        j = journey('Cô Hai đi chợ sớm')
        j.act('ask')
        tid = j.task['id']
        j.act('fa_pack', task=tid, lot='L1', qty=1)
        cases = [
            lambda s: s['tasks'][0]['needs']['items'].update(muong=1),
            lambda s: s['tasks'][0]['needs'].update(organic=True),
            lambda s: s['tasks'][0]['crate'][0].update(crop='herbs'),
            lambda s: s['tasks'][0].update(label='premium'),
            lambda s: s['ext']['data']['plots'][0].update(growth=999),
            lambda s: s['ext']['data']['plots'][5].update(organic=False),
            lambda s: s['ext']['data']['cold'][0].update(unsafe='no'),
            lambda s: s['ext']['data']['cold'][0].update(crop='durian'),
            lambda s: s['ext']['data']['coop'].update(hens=500),
            lambda s: s['ext']['data'].update(turn=10**6),
        ]
        for i, mutate in enumerate(cases):
            s = copy.deepcopy(j.state)
            mutate(s['careers']['farm'])
            with self.assertRaises(GameError, msg=str(i)):
                validate_state(s)
        roundtrip(j)

    def test_all_situations_playable(self):
        j = Journey('farm')
        for x in F.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_orders_distinct_per_day(self):
        for day in range(1, 8):
            titles = [F.make_task(day, slot, 1)['title'] for slot in range(3)]
            self.assertEqual(len(set(titles)), 3)


# ---------------------------------------------------------------- v0.5: seasons, market, HTX, surprises
BANNED = ('NPC', 'trong game', 'của game', 'ngày game', 'luật game', 'hư cấu', 'mô phỏng', 'giả lập', 'người chơi',
          'chị chủ', 'cô chủ', 'anh chủ')


def quiet(j):
    """No random surprise unless the test asks for one."""
    data(j)['desk'].update(day=j.c['day'], plan=[], fired=0)


def force(j, sid):
    d = data(j)
    desk = d['desk']
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script=sid, day=j.c['day'], at='between')
    F._attach(j.c, d)


def ledger(j, since=0):
    return j.c['ops']['finance']['ledger'][since:]


def mark(j):
    return len(j.c['ops']['finance']['ledger'])


def at_day(j, day):
    j.c['day'] = day
    data(j)['market'].update(day=0, sold={}, income=0)
    quiet(j)


class FarmSeasonMarketTests(unittest.TestCase):
    def test_generators_old_and_new(self):
        old = F.make_task(6, 2, kit.LEGACY_TURN + 5)
        new = F.make_task(6, 2, 5)
        self.assertNotIn('gen', old)
        self.assertEqual(new['gen'], F.GEN)
        self.assertEqual(old['title'], F._make_v1(6, 2, 5)['title'])
        titles = {F.make_task(day, slot, 1)['title'] for day in range(1, 30) for slot in range(12)}
        self.assertTrue({o[2] for o in F.ORDERS_NEW} <= titles)
        def extra(days):   # vegetables asked beyond the base order line
            rows = []
            for day in days:
                for slot in range(6):
                    t = F.make_task(day, slot, 1)
                    base = next(o[4] for o in F.ORDERS_V2 if o[2] == t['title'])
                    rows += [q - base[k] for k, q in t['needs']['items'].items() if k != 'egg' and k in base]
            return sum(rows) / len(rows)
        self.assertGreater(extra(range(12, 20)), extra(range(1, 3)) + 0.5)   # orders grow with the days

    def test_old_save_migrates(self):
        j = journey('Cô Hai đi chợ sớm')
        s = copy.deepcopy(j.state)
        c = s['careers']['farm']
        d = c['ext']['data']
        for k in ('desk', 'market', 'pledge'):
            d.pop(k)
        for k in ('sold', 'pledged'):
            d['stats'].pop(k)
        t = c['tasks'][0]
        old = F._make_v1(t['day'], int(t['id'].rsplit('-', 1)[1]), 1)
        old['quoted_price'] = t['quoted_price']
        c['tasks'][0] = old
        validate_state(s)
        c = s['careers']['farm']
        self.assertGreaterEqual(c['tasks'][0]['created_turn'], kit.LEGACY_TURN)
        self.assertEqual(c['ext']['data']['market'], dict(day=0, sold={}, income=0, start=0))
        self.assertIsNone(c['ext']['data']['pledge'])
        public_state(s)
        validate_state(json.loads(json.dumps(s)))

    def test_seasons_cycle_and_change_growth(self):
        ids = [F.season(d)['id'] for d in (1, 4, 5, 8, 9, 13, 16, 17)]
        self.assertEqual(ids, ['spring', 'spring', 'summer', 'summer', 'autumn', 'winter', 'winter', 'spring'])
        self.assertEqual(F._fit(1, 'muong'), 1)
        self.assertEqual(F._fit(13, 'tomato'), -1)
        self.assertEqual(F._fit(5, 'lettuce'), -1)

        def grow(day, crop):
            d = F.initial()
            p = d['plots'][5]
            p.update(crop=crop, growth=40, moisture=60, weeds=0)
            for turn in range(1, 6):
                p['moisture'] = 60
                F._step(d, turn, F.WEATHER_INDEX['cloud'], day)
            return p['growth']
        self.assertGreater(grow(5, 'tomato'), grow(13, 'tomato'))       # summer vs winter
        self.assertGreater(grow(13, 'lettuce'), grow(5, 'lettuce'))     # winter vs summer
        winter = [F._weather(d)['id'] for d in range(13, 17)] + [F._weather(d)['id'] for d in range(29, 33)]
        self.assertNotIn('hot', [F._weather(d)['id'] for d in range(13, 17)])
        self.assertEqual(winter, [F._weather(d)['id'] for d in list(range(13, 17)) + list(range(29, 33))])

    def test_winter_nights_are_slow(self):
        j = Journey('farm')
        j.c['day'] = 13
        quiet(j)
        p = plot(j, 'P5')
        p.update(moisture=70, growth=30)
        j.act('end_day', carry_event=True)
        self.assertTrue(30 + F.NIGHT_GROWTH // 2 <= plot(j, 'P5')['growth'] <= 30 + F.NIGHT_GROWTH // 2 + 6)

    def test_market_is_deterministic_bounded_and_rumours_mostly_right(self):
        self.assertEqual(F.market(7), F.market(7))
        right = total = 0
        cheap = dear = 0
        for day in range(1, 241):
            m = F.market(day)
            self.assertTrue(all(45 <= v <= 190 for v in m.values()))
            x = F.season(day)
            cheap += sum(m[k] for k in x['good']) / len(x['good'])
            dear += sum(m[k] for k in x['bad']) / len(x['bad']) if x['bad'] else sum(m[k] for k in x['good']) / len(x['good'])
            r = F.rumour(day)
            nxt = F.market(day + 1)[r['crop']]
            if nxt != m[r['crop']]:
                total += 1
                right += (nxt > m[r['crop']]) == r['up']
        self.assertGreater(dear, cheap)                   # off-season produce fetches more
        self.assertTrue(0.65 <= right / total <= 0.95, right / total)

    def test_sell_wholesale_pays_slips_and_caps(self):
        j = Journey('farm')
        quiet(j)
        lot = add_lot(j, 'muong', 20)
        with self.assertRaises(GameError):
            j.act('fa_sell', lot=lot, qty=4)              # needs confirmation
        m0, since = j.c['money'], mark(j)
        want = F._sale(1, 'muong', 'A', 0, 4)
        r = j.act('fa_sell', lot=lot, qty=4, confirm=True)
        self.assertEqual(j.c['money'] - m0, want)
        self.assertIn('+', r['message'])
        self.assertEqual([e['category'] for e in ledger(j, since)], ['revenue'])
        self.assertLess(F._tenths(1, 'muong', 'A', 4), F._tenths(1, 'muong', 'A', 0))   # the price slips
        self.assertEqual(view(j)['data']['market']['rows'][0]['sold'], 4)
        before = copy.deepcopy(j.state['careers']['farm']['ext']['data'])
        for bad in (dict(lot=lot, qty=F.DEPTH['muong']), dict(lot=lot, qty=0), dict(lot=lot, qty=99), dict(lot='L999', qty=1), dict(lot=lot, qty='3')):
            with self.assertRaises(GameError, msg=str(bad)):
                j.act('fa_sell', confirm=True, **bad)
        after = j.state['careers']['farm']['ext']['data']
        self.assertEqual(before['market'], after['market'])
        self.assertEqual(before['cold'], after['cold'])
        j.act('fa_sell', lot=lot, qty=F.DEPTH['muong'] - 4, confirm=True)
        with self.assertRaises(GameError):
            j.act('fa_sell', lot=lot, qty=1, confirm=True)   # the market is full for today
        b = add_lot(j, 'tomato', 4, grade='B')
        a = add_lot(j, 'tomato', 4, grade='A')
        self.assertLess(F._sale(1, 'tomato', 'B', 0, 4), F._sale(1, 'tomato', 'A', 0, 4))
        unsafe = add_lot(j, 'lettuce', 3)
        next(l for l in data(j)['cold'] if l['id'] == unsafe)['unsafe'] = True
        with self.assertRaises(GameError):
            j.act('fa_sell', lot=unsafe, qty=1, confirm=True)
        next(l for l in data(j)['cold'] if l['id'] == a)['expires'] = 0
        with self.assertRaises(GameError):
            j.act('fa_sell', lot=a, qty=1, confirm=True)
        j.act('fa_sell', lot=b, qty=4, confirm=True)
        self.assertFalse(any(l['id'] == b for l in data(j)['cold']))
        roundtrip(j)

    def test_market_resets_next_day(self):
        j = Journey('farm')
        quiet(j)
        lot = add_lot(j, 'egg', 30)
        j.act('fa_sell', lot=lot, qty=F.DEPTH['egg'], confirm=True)
        income = data(j)['market']['income']
        summary = j.act('end_day', carry_event=True)['summary']['career']
        self.assertEqual(summary['market_income'], income)
        self.assertTrue(any('chợ đầu mối' in x for x in summary['lines']))
        j.act('start_day')
        quiet(j)
        lot = add_lot(j, 'egg', 5)
        j.act('fa_sell', lot=lot, qty=5, confirm=True)
        self.assertEqual(data(j)['market']['sold'], {'egg': 5})

    def test_htx_pledge_full(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-HTX')
        off = data(j)['desk']['ev']['offer']
        ev = view(j)['data']['desk']['ev']
        self.assertIn(str(off['qty']), ev['options'][0]['label'])
        j.act('fa_decide', option='full')
        pl = data(j)['pledge']
        self.assertEqual((pl['crop'], pl['qty'], pl['done']), (off['crop'], off['qty'], 0))
        good = add_lot(j, off['crop'], off['qty'])
        other = add_lot(j, 'egg' if off['crop'] != 'egg' else 'muong', 5)
        b = add_lot(j, off['crop'], 3, grade='B')
        for bad in (dict(lot=other), dict(lot=b), dict(lot=good, qty=off['qty'] + 1)):
            with self.assertRaises(GameError, msg=str(bad)):
                j.act('fa_pledge', **bad)
        m0 = j.c['money']
        r = j.act('fa_pledge', lot=good, qty=off['qty'])
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(j.c['money'] - m0, off['qty'] * off['price'])
        with self.assertRaises(GameError):
            j.act('fa_pledge', lot=b, qty=1)
        summary = j.act('end_day', carry_event=True)['summary']['career']
        self.assertTrue(any('HTX' in x and 'đủ' in x for x in summary['lines']))
        self.assertIsNone(data(j)['pledge'])
        self.assertEqual(j.c['feed'][0]['stars'], 5)
        roundtrip(j)

    def test_htx_pledge_shortfall_is_fined(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-HTX')
        off = data(j)['desk']['ev']['offer']
        j.act('fa_decide', option='half')
        half = max(2, off['qty'] // 2)
        self.assertEqual(data(j)['pledge']['qty'], half)
        lot = add_lot(j, off['crop'], 1)
        j.act('fa_pledge', lot=lot, qty=1)
        since = mark(j)
        summary = j.act('end_day', carry_event=True)['summary']['career']
        fines = [e for e in ledger(j, since) if e['category'] == 'fine']
        self.assertEqual(sum(e['amount'] for e in fines), -(half - 1) * F.PLEDGE_FINE)
        self.assertTrue(any('phạt' in x for x in summary['lines']))

    def test_every_surprise_option_plays_and_reads_well(self):
        for x in F.EVENTS:
            for text in [x['title'], x['text']] + [o['label'] + o.get('hint', '') + o.get('outcome', '') for o in x['options']]:
                for word in BANNED:
                    self.assertNotIn(word, text, x['id'])
            for opt in x['options']:
                j = Journey('farm')
                at_day(j, 6)
                add_lot(j, 'muong', 20)
                force(j, x['id'])
                r = j.act('fa_decide', option=opt['id'])
                self.assertTrue(r['message'], (x['id'], opt['id']))
                for word in BANNED:
                    self.assertNotIn(word, r['message'])
                self.assertIsNone(data(j)['desk']['ev'])
                roundtrip(j)
        for o in F.ORDERS_NEW:
            for word in BANNED:
                self.assertNotIn(word, o[2] + o[3] + o[6])

    def test_surprise_blocks_work_until_decided_and_closes_by_default(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-GOATS')
        with self.assertRaises(GameError) as e:
            j.act('fa_water', plot='P1')
        self.assertIn('bất ngờ', str(e.exception))
        with self.assertRaises(GameError):
            j.act('fa_decide', option='nope')
        g = max(plot(j, p)['growth'] for p in ('P1', 'P3', 'P4'))
        summary = j.act('end_day', carry_event=True)['summary']['career']
        self.assertTrue(any('Dê' in x for x in summary['lines']))
        self.assertEqual(data(j)['desk']['last']['choice'], 'shoo')
        self.assertIsNone(data(j)['desk']['ev'])
        self.assertLess(max(plot(j, p)['growth'] for p in ('P1', 'P3', 'P4')), g + F.NIGHT_GROWTH)

    def test_pump_cut_blocks_the_valve_only_today(self):
        j = Journey('farm')
        at_day(j, 3)
        force(j, 'FE-PUMP')
        j.act('fa_decide', option='bucket')
        with self.assertRaises(GameError):
            j.act('fa_water', plot='all')
        self.assertTrue(view(j)['data']['nopump'])
        j.act('fa_water', plot='P1')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        quiet(j)
        data(j)['desk']['ev'] = None
        j.act('fa_water', plot='all')

    def test_truck_waters_everything(self):
        j = Journey('farm')
        at_day(j, 3)
        before = [p['moisture'] for p in data(j)['plots']]
        force(j, 'FE-PUMP')
        m0 = j.c['money']
        j.act('fa_decide', option='truck')
        self.assertEqual(j.c['money'], m0 - 12)
        self.assertTrue(all(p['moisture'] >= min(100, b + 20) - 1 for p, b in zip(data(j)['plots'], before)))

    def test_bees_punish_chemical_spray(self):
        j = Journey('farm')
        at_day(j, 4)
        g = plot(j, 'P2')['growth']
        force(j, 'FE-BEES')
        j.act('fa_decide', option='yes')
        self.assertGreaterEqual(plot(j, 'P2')['growth'], g + 10)   # tomatoes pollinated
        self.assertTrue(view(j)['data']['bees'])
        m0, since = j.c['money'], mark(j)
        r = j.act('fa_spray', plot='P1', kind='chem')
        self.assertIn('Ong', r['message'])
        self.assertEqual(sum(e['amount'] for e in ledger(j, since) if e['category'] == 'fine'), -F.BEE_FINE)
        self.assertEqual(j.c['money'], m0 - F.BEE_FINE)
        self.assertEqual(j.c['feed'][0]['stars'], 1)
        self.assertFalse(view(j)['data']['bees'])

    def test_audit_clean_and_with_violation(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-AUDIT')
        m0 = j.c['money']
        r = j.act('fa_decide', option='open')
        self.assertEqual(j.c['money'], m0 + 12)
        self.assertTrue(r.get('celebrate'))
        j2 = Journey('farm')
        at_day(j2, 4)
        bad = add_lot(j2, 'lettuce', 5)
        next(l for l in data(j2)['cold'] if l['id'] == bad)['unsafe'] = True
        force(j2, 'FE-AUDIT')
        m0 = j2.c['money']
        r = j2.act('fa_decide', option='open')
        self.assertEqual(j2.c['money'], m0 - 10)
        self.assertFalse(any(l['id'] == bad for l in data(j2)['cold']))
        self.assertFalse(r.get('celebrate'))
        self.assertIs(data(j2)['desk']['last']['good'], False)
        roundtrip(j2)

    def test_dodged_audit_comes_back(self):
        j = Journey('farm')
        at_day(j, 5)
        force(j, 'FE-AUDIT')
        j.act('fa_decide', option='gift')
        self.assertIn('audit_due', data(j)['desk']['marks'])
        pool = [x['id'] for x in F.EVENTS if not x.get('need_mark') or x['need_mark'] in data(j)['desk']['marks']]
        self.assertIn('FE-AUDIT2', pool)
        force(j, 'FE-AUDIT2')
        j.act('fa_decide', option='open')
        self.assertNotIn('audit_due', data(j)['desk']['marks'])

    def test_pest_wave_is_hidden_until_scouted(self):
        j = Journey('farm')
        at_day(j, 3)
        force(j, 'FE-PESTS')
        j.act('fa_decide', option='scout')
        self.assertTrue(all(p['pests'] >= 1 for p in data(j)['plots'] if p['crop'] and p['growth'] >= 10))
        self.assertTrue(all('pests' not in p for p in view(j)['data']['plots']))
        j.act('fa_scout', plot='P1')
        self.assertGreaterEqual(next(p for p in view(j)['data']['plots'] if p['id'] == 'P1')['seen'], 1)

    def test_preventive_chemicals_cost_the_organic_label(self):
        j = Journey('farm')
        at_day(j, 3)
        force(j, 'FE-PESTS')
        j.act('fa_decide', option='chem')
        planted = [p for p in data(j)['plots'] if p['crop']]
        self.assertTrue(all(not p['organic'] and p['phi'] > j.c['turn'] for p in planted))
        self.assertTrue(any('phòng dịch' in r['text'] for r in data(j)['diary']))

    def test_fox_takes_a_hen_and_hens_can_be_restocked(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-FOX')
        j.act('fa_decide', option='later')
        self.assertEqual(data(j)['coop']['hens'], F.HENS - 1)
        m0 = j.c['money']
        with self.assertRaises(GameError):
            j.act('fa_hen')
        j.act('fa_hen', confirm=True)
        self.assertEqual((data(j)['coop']['hens'], j.c['money']), (F.HENS, m0 - F.HEN_COST))
        with self.assertRaises(GameError):
            j.act('fa_hen', confirm=True)
        force(j, 'FE-FOX')
        j.act('fa_decide', option='fence')
        self.assertIn('fence', data(j)['desk']['marks'])
        self.assertNotIn('FE-FOX', [x['id'] for x in kit._desk_pool(F.ID, j.c, data(j)['desk'], F.EVENTS, 'between', 'sun')])

    def test_storm_and_goats_hurt_the_right_plots(self):
        j = Journey('farm')
        at_day(j, 5)
        tall = {p['id']: p['growth'] for p in data(j)['plots'] if p['crop'] in F.TALL}
        leafy = {p['id']: p['growth'] for p in data(j)['plots'] if p['crop'] in F.LEAFY}
        force(j, 'FE-STORM')
        j.act('fa_decide', option='drain')
        for pid, g in tall.items():
            self.assertEqual(plot(j, pid)['growth'], max(0, g - 12))
        for pid, g in leafy.items():
            self.assertEqual(plot(j, pid)['growth'], g)
        force(j, 'FE-GOATS')
        j.act('fa_decide', option='shoo')
        top = max(leafy, key=lambda pid: (leafy[pid], pid))
        self.assertEqual(plot(j, top)['growth'], max(0, leafy[top] - 25))

    def test_trader_buys_the_cold_room(self):
        j = Journey('farm')
        at_day(j, 4)
        add_lot(j, 'lettuce', 20)
        units = F._trader_units(j.c, data(j))
        force(j, 'FE-TRADER')
        self.assertEqual(data(j)['desk']['ev']['offer'], dict(units=units))
        self.assertIn(str(units), view(j)['data']['desk']['ev']['text'])
        m0 = j.c['money']
        j.act('fa_decide', option='all')
        self.assertGreater(j.c['money'], m0)
        self.assertEqual(F._trader_units(j.c, data(j)), 0)
        self.assertTrue(any(l['crop'] == 'egg' for l in data(j)['cold']))   # eggs and spoilt lots stay

    def test_field_work_brings_the_first_surprise(self):
        j = Journey('farm')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        desk = data(j)['desk']
        desk['ev'] = None
        desk.update(plan=[5], fired=0)
        for _ in range(20):
            if data(j)['desk']['ev']:
                break
            j.act('fa_scout', plot='P2')
        self.assertIsNotNone(data(j)['desk']['ev'])
        self.assertGreaterEqual(j.c['turn'] - data(j)['market']['start'], 12)
        roundtrip(j)

    def test_trader_only_comes_for_a_full_cold_room(self):
        j = Journey('farm')
        at_day(j, 4)
        for turn in range(40):
            j.c['turn'] = 100 + turn
            F._maybe_trader(j.state, j.c, data(j))
        self.assertIsNone(data(j)['desk']['ev'])      # 10 units of vegetables are not enough
        add_lot(j, 'muong', 20)
        for turn in range(40):
            j.c['turn'] = 200 + turn
            F._maybe_trader(j.state, j.c, data(j))
            if data(j)['desk']['ev']:
                break
        self.assertEqual(data(j)['desk']['ev']['script'], 'FE-TRADER')

    def test_public_view_shows_today_not_tomorrow(self):
        j = Journey('farm')
        v = view(j)['data']
        self.assertEqual(v['season']['id'], 'spring')
        self.assertEqual(len(v['market']['rows']), len(F.PRICES))
        text = json.dumps(v['market'])
        self.assertNotIn('tomorrow', text)
        self.assertEqual(set(v['market']['rumour']), {'crop', 'up'})
        self.assertIsNone(v['desk']['ev'])
        self.assertNotIn('marks', json.dumps(v['desk']['ev']))

    def test_v2_tampering_rejected(self):
        j = Journey('farm')
        at_day(j, 4)
        force(j, 'FE-HTX')
        j.act('fa_decide', option='full')
        lot = add_lot(j, 'egg', 10)
        j.act('fa_sell', lot=lot, qty=5, confirm=True)
        cases = [
            lambda d: d['market']['sold'].update(egg=999),
            lambda d: d['market']['sold'].update(durian=1),
            lambda d: d['market'].update(income=-5),
            lambda d: d['market'].update(start=10 ** 6),
            lambda d: d['pledge'].update(price=99),
            lambda d: d['pledge'].update(done=d['pledge']['qty'] + 1),
            lambda d: d['pledge'].update(paid=50),
            lambda d: d['stats'].update(sold=-1),
            lambda d: d['desk'].update(ev=dict(id='x', script='FE-NOPE', day=1, at='between')),
        ]
        for i, mutate in enumerate(cases):
            s = copy.deepcopy(j.state)
            mutate(s['careers']['farm']['ext']['data'])
            with self.assertRaises(GameError, msg=str(i)):
                validate_state(s)
        s = copy.deepcopy(j.state)
        force_ev = s['careers']['farm']['ext']['data']['desk']
        force_ev['ev'] = dict(id='desk-99', script='FE-HTX', day=4, at='between', offer=dict(crop='muong', qty=5, price=99))
        with self.assertRaises(GameError):
            validate_state(s)
        roundtrip(j)

    def test_three_days_with_market_and_orders(self):
        j = Journey('farm')
        for day in range(3):
            quiet(j)
            for t in [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]:
                j.act('ask', task=t['id'])
            for p in data(j)['plots']:
                if p['crop'] and F.RIPE <= p['growth'] < F.ROTTEN and j.c['turn'] >= p['phi']:
                    j.act('fa_harvest', plot=p['id'], confirm=True)
                    data(j)['desk']['ev'] = None
            if not data(j)['coop']['fed'] == j.c['day']:
                j.act('fa_feed')
            if data(j)['coop']['nest']:
                j.act('fa_collect')
            for lot in list(data(j)['cold']):
                if lot['crop'] != 'egg' and not lot['unsafe'] and lot['expires'] == j.c['day']:
                    room = F.DEPTH[lot['crop']] - F._mkt(j.c, data(j))['sold'].get(lot['crop'], 0)
                    if room:
                        j.act('fa_sell', lot=lot['id'], qty=min(room, lot['qty']), confirm=True)
            j.act('end_day', carry_event=True)
            j.act('start_day')
        roundtrip(j)
        self.assertGreater(data(j)['stats']['sold'] + data(j)['stats']['eggs'], 0)


class FarmConsequenceTests(unittest.TestCase):
    """What the buyer finds in the crate costs the farm, in proportion (game.consequences)."""

    def _order(self, title='Cà chua cho nồi sốt'):
        j = journey(title)
        tid = j.task['id']
        j.act('ask')
        quiet(j)
        return j, tid

    def _deliver(self, j, tid, crop, qty, label='plain', **lot):
        lid = F._add_lot(j.c, data(j), crop, lot.get('grade', 'A'), qty, lot.get('organic', True), lot.get('unsafe', False), 'P6')['id']
        if 'expires' in lot:
            next(l for l in data(j)['cold'] if l['id'] == lid)['expires'] = lot['expires']
        j.act('fa_pack', task=tid, lot=lid, qty=qty)
        j.act('fa_label', task=tid, label=label)
        since = mark(j)
        r = j.act('fa_deliver', task=tid, confirm=True)
        got = sum(e['amount'] for e in ledger(j, since) if e['ref'] == tid and e['category'] != 'tip')
        return j.get(tid), got, r

    def test_right_crate_full_pay_no_slips(self):
        j, tid = self._order()
        want = j.task['needs']['items']['tomato']
        t, got, _ = self._deliver(j, tid, 'tomato', want)
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(got, t['served']['pay'])
        self.assertGreaterEqual(post_for(j, tid)['stars'], 4)

    def test_short_weight_is_named_and_costs(self):
        j, tid = self._order()
        want = j.task['needs']['items']['tomato']
        t, got, _ = self._deliver(j, tid, 'tomato', want - 1)
        self.assertEqual([s['code'] for s in t['slips']], ['short'])
        self.assertIn(t['reaction']['kind'], ('accept', 'grumble', 'discount', 'refund'))
        self.assertEqual(got, t['served']['pay'] - t['reaction']['cut'])
        post = post_for(j, tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('chỉ giao', post['text'])
        roundtrip(j)

    def test_severity_scales_the_stars(self):
        j1, t1 = self._order()
        want = j1.task['needs']['items']['tomato']
        small, _, _ = self._deliver(j1, t1, 'tomato', want, expires=j1.c['day'])          # last fresh day: small
        j2, t2 = self._order()
        big, _, _ = self._deliver(j2, t2, 'tomato', want - 1, grade='B')                   # short and grade B
        self.assertEqual(cq_points(small), 1)
        self.assertGreaterEqual(cq_points(big), 3)
        self.assertGreater(post_for(j1, t1)['stars'], post_for(j2, t2)['stars'])

    def test_produce_inside_the_pesticide_interval_is_refused_and_reported(self):
        j, tid = self._order()
        want = j.task['needs']['items']['tomato']
        units = sum(l['qty'] for l in data(j)['cold'])
        t, got, r = self._deliver(j, tid, 'tomato', want, unsafe=True)
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(got, 0)
        self.assertEqual(post_for(j, tid)['stars'], 1)
        self.assertTrue(any(p.get('report') and p.get('source') == tid for p in j.c['feed']))
        self.assertTrue(any(f['src'] == tid and f['script'] == 'slip_food_inspect' for f in j.c['incidents']['follow']))
        self.assertEqual(sum(l['qty'] for l in data(j)['cold']), units)   # the unsafe lot is destroyed, not restocked
        self.assertIn('kiểm tra', r['message'])
        roundtrip(j)

    def test_reaction_is_paid_once(self):
        from game import consequences as cq
        j, tid = self._order()
        want = j.task['needs']['items']['tomato']
        t, got, _ = self._deliver(j, tid, 'tomato', want, grade='B')
        cut = t['reaction']['cut']
        self.assertEqual(got, t['served']['pay'] - cut)
        money = j.c['money']
        again = cq.react(j.state, j.c, t, t['served']['pay'], who='Chị Hạnh')
        self.assertEqual((again['cut'], j.c['money']), (cut, money))
        roundtrip(j)

    def test_old_crate_entries_without_the_unsafe_flag_still_load(self):
        j, tid = self._order()
        lid = add_lot(j, 'tomato', 2)
        j.act('fa_pack', task=tid, lot=lid, qty=2)
        j.task['crate'][0].pop('unsafe')
        roundtrip(j)
        j.task['crate'][0]['unsafe'] = 'yes'
        with self.assertRaises(GameError):
            validate_state(json.loads(json.dumps(j.state)))


class FarmCareLoopTests(unittest.TestCase):
    """Sub-project 3: multi-day growth, soil, rotation, pest spread, outlook, hen mood."""

    def setUp(self):
        self.j = Journey('farm')
        quiet(self.j)

    def night(self, sky='sun'):
        return F._night(self.j.c, data(self.j), F.WEATHER_INDEX[sky])

    def test_crops_take_several_days_with_a_daily_budget(self):
        j = self.j
        j.act('fa_clear', plot='P6', confirm=True) if plot(j, 'P6')['crop'] else None
        plot(j, 'P6')['prev'] = None
        j.act('fa_plant', plot='P6', crop='muong')
        cap = F.CROP_INDEX['muong']['cap']
        for _ in range(30):
            plot(j, 'P6').update(moisture=60, weeds=0)
            j.act('fa_scout', plot='P6')              # a farm action: the stored state catches up each beat
        p6 = plot(j, 'P6')
        self.assertEqual((p6['growth'], p6['grown']), (cap, cap))   # no more growth today
        v = next(p for p in view(j)['data']['plots'] if p['id'] == 'P6')
        self.assertEqual((v['stage'], v['eta'], v['cap']), ('young', 2, cap))
        self.assertLess(p6['growth'], F.YOUNG)                       # cannot be harvested on the day it was sown
        j.act('end_day', carry_event=True)
        self.assertEqual(plot(j, 'P6')['grown'], 0)                  # the budget starts again
        self.assertEqual(plot(j, 'P6')['growth'], cap + F.NIGHT_GROWTH)
        j.act('start_day')

    def test_ripe_produce_ages_at_half_budget(self):
        p = F._plot('P1', 'muong', F.RIPE, 60, soil=60)
        self.assertEqual(F._cap(p), F.CROP_INDEX['muong']['cap'] // 2)
        ripe, over = F._eta(p, 1)
        self.assertEqual(ripe, 0)
        self.assertGreaterEqual(over, 1)                             # a missed day is grade B, not rotten
        self.assertEqual(F._eta(F._plot('P1', 'tomato', 15, 60), 1)[0], 2)

    def test_soil_is_used_rested_and_fed(self):
        j = self.j
        s1, s6 = plot(j, 'P1')['soil'], plot(j, 'P6')['soil']
        self.night()
        self.assertEqual(plot(j, 'P1')['soil'], s1 - F.CROP_INDEX['muong']['feed'])
        self.assertEqual(plot(j, 'P6')['soil'], s6 + F.SOIL_REST)
        compost = kit.stock(j.c, 'compost')
        j.act('fa_fertilize', plot='P6', kind='compost')              # bón lót on an empty bed
        self.assertEqual(plot(j, 'P6')['soil'], s6 + F.SOIL_REST + F.SOIL_ADD['compost'])
        self.assertEqual(kit.stock(j.c, 'compost'), compost - 1)
        with self.assertRaises(GameError):
            j.act('fa_fertilize', plot='P6', kind='compost')
        with self.assertRaises(GameError):
            j.act('fa_fertilize', plot='P6', kind='npk')              # NPK still needs a crop
        j.act('fa_plant', plot='P6', crop='tomato')
        self.assertTrue(plot(j, 'P6')['compost'])                     # the base dressing counts for this crop
        self.assertTrue(plot(j, 'P6')['organic'])
        with self.assertRaises(GameError):
            j.act('fa_fertilize', plot='P6', kind='compost')

    def test_depleted_soil_slows_but_never_stops(self):
        rich, poor = F._plot('P1', 'lettuce', 40, 60, soil=60), F._plot('P1', 'lettuce', 40, 60, soil=F.SOIL_LOW - 1)
        self.assertLess(F._cap(poor), F._cap(rich))
        self.assertGreater(F._cap(poor), 0)
        self.assertEqual(F._night_growth(poor, 1), F._night_growth(rich, 1) // 2)
        self.assertGreater(F._night_growth(F._plot('P1', 'lettuce', 40, 60, soil=0), 13), 0)

    def test_rotation_and_replanting_the_same_crop(self):
        j = self.j
        self.assertEqual(plot(j, 'P6')['prev'], 'muong')
        v = next(p for p in view(j)['data']['plots'] if p['id'] == 'P6')
        self.assertEqual((v['rotation']['muong'], v['rotation']['tomato'], v['rotation']['lettuce']), ('same', 'rotate', None))
        s6 = plot(j, 'P6')['soil']
        r = j.act('fa_plant', plot='P6', crop='tomato')
        self.assertIn('Luân canh', r['message'])
        self.assertEqual(plot(j, 'P6')['soil'], s6 + F.SOIL_ROTATE)
        self.assertEqual(plot(j, 'P6')['pests'], 0)
        j.act('fa_harvest', plot='P1', confirm=True)
        self.assertEqual(plot(j, 'P1')['prev'], 'muong')
        r = j.act('fa_plant', plot='P1', crop='muong')
        self.assertIn('sâu bệnh cũ', r['message'])
        self.assertEqual(plot(j, 'P1')['pests'], 1)
        self.assertNotIn('pests', next(p for p in view(j)['data']['plots'] if p['id'] == 'P1'))   # still hidden
        roundtrip(j)

    def test_heavy_pests_spread_overnight_unless_sprayed(self):
        j = self.j
        self.assertEqual(F.NEIGHBOURS['P2'], ['P1', 'P3', 'P5'])
        self.assertEqual(F.NEIGHBOURS['P4'], ['P1', 'P5'])
        for p in data(j)['plots']:
            p['pests'] = 0
        plot(j, 'P2')['pests'] = 2
        plot(j, 'P1')['guard'] = j.c['day']                            # sprayed today
        out = self.night()
        self.assertEqual(out['spread'], 2)
        self.assertEqual([plot(j, x)['pests'] for x in ('P1', 'P2', 'P3', 'P4', 'P5')], [0, 3, 1, 0, 1])
        # One pest level does not spread.
        j2 = Journey('farm')
        for p in data(j2)['plots']:
            p['pests'] = 0
        plot(j2, 'P2')['pests'] = 1
        self.assertEqual(F._night(j2.c, data(j2), F.WEATHER_INDEX['sun'])['spread'], 0)

    def test_spray_guards_and_summary_names_no_hidden_bed(self):
        j = self.j
        for p in data(j)['plots']:
            p['pests'] = 0
        plot(j, 'P2')['pests'] = 3
        j.act('fa_spray', plot='P3', kind='bio')
        self.assertEqual(plot(j, 'P3')['guard'], j.c['day'])
        summary = j.act('end_day', carry_event=True)['summary']['career']
        line = next(x for x in summary['lines'] if '🐛' in x)
        self.assertNotIn('P1', line)
        self.assertEqual(summary['pest_spread'], 2)                  # P1 and P5; P3 was guarded
        self.assertEqual(plot(j, 'P3')['pests'], 0)

    def test_nights_follow_tomorrows_sky(self):
        for sky, loss in F.NIGHT_DRY.items():
            j = Journey('farm')
            before = [p['moisture'] for p in data(j)['plots']]
            F._night(j.c, data(j), F.WEATHER_INDEX[sky])
            self.assertEqual([p['moisture'] for p in data(j)['plots']], [max(0, min(100, m - loss)) for m in before], sky)
        self.assertGreater(F.NIGHT_DRY['hot'], F.NIGHT_DRY['cloud'])

    def test_outlook_plan_and_care_list(self):
        j = self.j
        v = view(j)['data']
        self.assertEqual([r['day'] for r in v['outlook']], [j.c['day'] + k for k in (1, 2, 3)])
        self.assertEqual(v['outlook'][0]['id'], v['forecast']['id'])
        self.assertTrue(v['plan'].startswith('Mai'))
        labels = [r['label'] for r in v['care']]
        self.assertIn('Cho gà ăn & thay nước', labels)
        self.assertTrue(any(r['label'].startswith('Thu hoạch') and 'P1' in r['label'] for r in v['care']))
        self.assertTrue(all(set(r) <= {'ok', 'icon', 'label', 'note', 'tone'} for r in v['care']))
        self.assertTrue(all(p['eta'] is not None for p in v['plots'] if p['crop']))
        j.act('fa_feed')
        j.act('fa_clean')
        care = {r['label']: r['ok'] for r in view(j)['data']['care']}
        self.assertTrue(care['Cho gà ăn & thay nước'] and care['Dọn chuồng gà'])
        for pid in ('P1', 'P2', 'P3', 'P4', 'P5'):
            j.act('fa_scout', plot=pid)
        self.assertTrue(next(r for r in view(j)['data']['care'] if r['icon'] == '🔍')['ok'])
        # A tip for a rainy tomorrow warns against watering.
        rainy = next(d for d in range(2, 60) if F._weather(d + 1)['id'] == 'rain')
        self.assertIn('đừng tưới', F._plan(dict(j.c, day=rainy), data(j), F._weather(rainy + 1)))

    def test_hen_mood_follows_care_and_recovers(self):
        j = self.j
        self.assertEqual(data(j)['coop']['mood'], F.MOOD_START)
        j.act('fa_clean')
        with self.assertRaises(GameError):
            j.act('fa_clean')
        coop = data(j)['coop']
        self.assertEqual(coop['cleaned'], j.c['day'])
        c = j.c
        # Three neglected days: the flock sulks but never dies and still lays.
        coop.update(fed=0, cleaned=0, nest=0, stale=0)
        eggs = []
        for day in range(2, 5):
            c['day'] = day
            coop['nest'] = 0
            eggs.append(F._hens_night(c, coop))
        self.assertEqual(coop['hens'], F.HENS)
        self.assertGreaterEqual(coop['mood'], F.MOOD_MIN)
        self.assertLess(F._lay_pct(coop['mood']), 100)
        self.assertEqual(eggs[-1], F.HENS // 2 * F._lay_pct(coop['mood']) // 100)
        self.assertGreater(eggs[-1], 0)
        # Three good days bring the worst flock back to full laying.
        for day in range(5, 8):
            c['day'] = day
            coop.update(fed=day, cleaned=day, nest=0)
            laid = F._hens_night(c, coop)
        self.assertEqual((F._lay_pct(coop['mood']), laid), (100, F.HENS))
        # A normal flock that misses one feeding lays half (hunger) but its mood still allows full laying.
        c['day'] = 8
        coop.update(fed=7, cleaned=8, nest=0, mood=F.MOOD_START)
        self.assertEqual(F._hens_night(c, coop), F.HENS // 2)
        self.assertGreaterEqual(coop['mood'], F.MOOD_OK)

    def test_coop_helper_cleans_and_fox_scares(self):
        j = self.j
        at_day(j, 4)
        force(j, 'FE-FOX')
        m = data(j)['coop']['mood']
        j.act('fa_decide', option='later')
        self.assertEqual(data(j)['coop']['mood'], m + F.MOOD['fox'])
        data(j)['coop']['fed'] = j.c['day']
        self.assertIn('dọn chuồng', F.assist(j.state, j.c, dict(role='fa_coop'), None))
        self.assertEqual(data(j)['coop']['cleaned'], j.c['day'])

    def test_old_save_gains_care_fields(self):
        j = self.j
        s = copy.deepcopy(j.state)
        d = s['careers']['farm']['ext']['data']
        for p in d['plots']:
            for k in ('soil', 'grown', 'prev', 'guard'):
                p.pop(k)
        for k in ('mood', 'cleaned'):
            d['coop'].pop(k)
        validate_state(s)
        d = s['careers']['farm']['ext']['data']
        self.assertTrue(all(p['soil'] == F.SOIL_START and p['grown'] == 0 and p['prev'] is None for p in d['plots']))
        self.assertEqual(d['coop']['mood'], F.MOOD_START)
        public_state(s)
        validate_state(json.loads(json.dumps(s)))

    def test_care_tampering_rejected(self):
        j = self.j
        cases = [
            lambda d: d['plots'][0].update(soil=101),
            lambda d: d['plots'][0].update(grown=-1),
            lambda d: d['plots'][0].update(prev='durian'),
            lambda d: d['plots'][0].update(guard='x'),
            lambda d: d['coop'].update(mood=5),
            lambda d: d['coop'].update(cleaned=10 ** 6),
            lambda d: d['coop'].update(happy=True),
        ]
        for i, mutate in enumerate(cases):
            s = copy.deepcopy(j.state)
            mutate(s['careers']['farm']['ext']['data'])
            with self.assertRaises(GameError, msg=str(i)):
                validate_state(s)

    def test_a_week_of_care_with_one_lazy_day(self):
        """Play seven days through commands: a caring routine, one day skipped, then back to work."""
        j = self.j
        harvested = []
        for n in range(7):
            quiet(j)
            data(j)['desk']['ev'] = None
            lazy = n == 3
            for _ in range(3 if lazy else 18):
                v = view(j)['data']
                if data(j)['desk']['ev']:
                    j.act('fa_decide', option=kit.desk_script(F.EVENTS, data(j)['desk']['ev']['script'])['default'])
                    continue
                if lazy:
                    j.act('advance')
                    continue
                p = next((p for p in v['plots'] if p['crop'] and p['stage'] in ('ripe', 'over') and not p['safe_in']), None)
                if p:
                    lots = len(data(j)['cold'])
                    try:
                        j.act('fa_harvest', plot=p['id'], confirm=True)
                    except GameError:
                        pass
                    harvested.append(len(data(j)['cold']) - lots)
                    continue
                e = next((p for p in v['plots'] if not p['crop']), None)
                if e and kit.stock(j.c, 'seed_lettuce'):
                    j.act('fa_plant', plot=e['id'], crop='lettuce' if e['rotation'].get('lettuce') != 'same' else 'muong')
                    continue
                dry = next((p for p in v['plots'] if p['crop'] and p['moisture'] < F.MOIST_LOW), None)
                if dry:
                    j.act('fa_water', plot=dry['id'])
                    continue
                if not v['fed_today'] and kit.stock(j.c, 'feed'):
                    j.act('fa_feed')
                    continue
                if not v['coop']['cleaned_today']:
                    j.act('fa_clean')
                    continue
                if v['coop']['nest']:
                    j.act('fa_collect')
                    continue
                j.act('advance')
            j.act('end_day', carry_event=True)
            j.act('start_day')
            roundtrip(j)
        self.assertTrue(harvested)
        self.assertGreaterEqual(data(j)['coop']['mood'], F.MOOD_OK)   # the flock forgave the lazy day
        self.assertFalse(any(p['crop'] and p['growth'] >= F.ROTTEN for p in data(j)['plots']))


def cq_points(t):
    from game import consequences as cq
    return cq.points(t)


if __name__ == '__main__':
    unittest.main()
