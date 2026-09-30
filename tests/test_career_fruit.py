"""Sạp trái cây Dì Tư (plugin career fruit): the morning set-up (cover, scale test, bruised fruit),
ripeness by the day, picking, the basket on the scale, weighing, bargaining, cash through the
shared till, a customer bringing fruit back, the evening sell-off, surprises, determinism, save
validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, till, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

FR = PLUGINS.get('fruit')


def ledger(c, ref):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ref]


class Base(unittest.TestCase):
    def setUp(self):
        if FR is None:
            raise unittest.SkipTest('fruit is filtered out by MNL_CAREERS')
        self.j = Journey('fruit')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def kind(self, kind, j=None):
        j = j or self.j
        return next(t for t in j.c['tasks'] if t['kind'] == kind and t['status'] not in ('completed', 'cancelled'))

    def settle_desk(self, j=None):
        j = j or self.j
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('tc_desk', option=kit.desk_script(FR.DESK, ev['script'])['default'])
        tb = j.c['ext']['data'].get('trouble')
        if tb and tb['ev']:
            j.act('tc_trouble', choice='ignore')

    def setup_stall(self, j=None, cover=None, test=True, fix=True, sort=True):
        j = j or self.j
        self.settle_desk(j)
        t = self.kind('setup', j)
        j.act('tc_cover', cover=cover or t['needs']['cover'])
        if test:
            j.act('tc_scale_test')
            if fix and j.c['ext']['data']['scale']['off']:
                j.act('tc_scale_fix')
        if sort:
            for item in list(j.c['ext']['data']['bruise']):
                j.act('tc_sort', item=item)
        j.act('tc_open', task=t['id'])
        return j.get(t['id'])

    def fill(self, tid, j=None, tare=True):
        """Pick exactly what the customer asked for, from the right ripeness baskets."""
        j = j or self.j
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        if tare:
            j.act('tc_tare', task=tid)
        t = j.get(tid)
        n = t['needs']
        if t['kind'] == 'bulk':
            for item in n['bulk']:
                while len(j.get(tid)['bag']) < n['min'] and FR.baskets(j.c)[item].get('ky'):
                    j.act('tc_pick', task=tid, item=item, stage='ky')
            return j.get(tid)
        for ln in n['lines']:
            while True:
                t = j.get(tid)
                mine = [b for b in t['bag'] if b['i'] == ln['i']]
                if ln['n'] and len(mine) >= ln['n']:
                    break
                if ln['kg'] and sum(b['g'] for b in mine) >= ln['kg'] * 0.95:
                    break
                stage = next(s for s in ln['want'] if FR.baskets(j.c)[ln['i']].get(s))
                j.act('tc_pick', task=tid, item=ln['i'], stage=stage)
        return j.get(tid)

    def pay_exact(self, tid, j=None):
        j = j or self.j
        rec = j.get(tid)['cash']
        return j.act('tc_pay', task=tid, change=till.greedy(till.due(rec)))

    def sell(self, tid, j=None, deal=None):
        j = j or self.j
        self.fill(tid, j)
        j.act('tc_weigh', task=tid)
        t = j.get(tid)
        if t['stage'] == 'haggle':
            j.act('tc_deal', task=tid, deal=deal or FR._haggle_of(t)['wants'])
            t = j.get(tid)
        if t['stage'] == 'credit':      # a customer who wants it on tab / walks off with the bag
            r = j.act('tc_credit', task=tid, choice='tab' if t['twist']['kind'] == 'tab' else 'hold')
            if j.get(tid)['stage'] != 'pay':
                return r
        return self.pay_exact(tid, j)

    def stock_up(self, j=None):
        """What the storeroom orders would bring: fruit at every ripeness."""
        j = j or self.j
        for f in FR.FRUITS:
            life = len(f['stages'])
            for left in range(1, life + 1):
                if kit.stock(j.c, f['id']) <= 30:
                    kit.add_lot(j.c, f['id'], 2, f['cost'], left, 'test')


class Spec(Base):
    def test_spec_shape(self):
        s = FR.SPEC
        self.assertEqual((s['id'], s['prefix']), ('fruit', 'tc_'))
        self.assertTrue(6 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertEqual(len(s['review_asides']), 4)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for x in s['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
                self.assertLessEqual(opt.get('cost', 0), 80)
                self.assertLessEqual(opt.get('reward', 0), 60)
        for k in s['no_tick'] + s['free_actions'] + tuple(FR.ACTIONS):
            self.assertTrue(k.startswith('tc_'), k)
        for i in FR.content()['intro'], FR.INTRO:
            for key in ('work', 'meet', 'stars'):
                self.assertGreaterEqual(len(i[key]), 5, key)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([FR.ORDERS, FR.RETURNS, FR.DESK, FR.SITUATIONS, FR.REG_STORY, FR.INTRO, FR.SPEC['meta']], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_registered_everywhere_it_needs_to_be(self):
        from game.content import CAREERS
        from game import journey as jr, inventory
        self.assertIn('fruit', CAREERS)
        self.assertIn('fruit', jr.CH_UNLOCKS[3])
        self.assertEqual(inventory.hours('fruit'), (6 * 60, 18 * 60))


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 20):
            for slot in range(0, 8):
                a, b = FR.make_task(day, slot, 1), FR.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('fruit', day, slot, 1)['id'], f'fruit-{day:04d}-{slot:02d}')

    def test_first_day_is_gentle(self):
        self.assertEqual(FR.mod_of(1)['id'], 'normal')
        self.assertEqual([FR.make_task(1, s, 1)['kind'] for s in range(3)], ['setup', 'buy', 'buy'])
        self.assertEqual(FR.drift_of(1), 40)
        kinds = {FR.make_task(d, s, 1)['kind'] for d in range(2, 40) for s in range(1, 5)}
        self.assertTrue({'buy', 'altar', 'bulk', 'return'} <= kinds, kinds)

    def test_ripeness_follows_the_days_left(self):
        lot = dict(expires=5)
        self.assertEqual([FR.stage_of('xoai', dict(lot, expires=d + 4), d) for d in range(1, 2)], ['xanh'])
        self.assertEqual([FR.stage_of('xoai', dict(expires=5), day) for day in (1, 2, 3, 4, 5)], ['xanh', 'xanh', 'chin', 'chin', 'ky'])
        self.assertEqual(FR.stage_of('cam', dict(expires=8), 8), 'heo')
        self.assertEqual(FR.kg_text(500), '5 lạng')
        self.assertEqual(FR.kg_text(1250), '1,25 ký')


class Setup(Base):
    def test_setup_done_right(self):
        t = self.setup_stall()
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertTrue(self.d['stall']['open'])
        self.assertEqual(self.d['scale']['off'], 0)
        self.assertEqual(self.d['bruise'], {})
        validate_state(self.j.state)

    def test_setup_done_wrong(self):
        t = self.setup_stall(cover='bat', test=False, sort=False)
        codes = {x['code'] for x in self.j.get(t['id'])['slips']}
        self.assertTrue({'cover', 'untested', 'bruised_left'} <= codes, codes)

    def test_a_tested_drift_must_be_fixed(self):
        t = self.setup_stall(fix=False)
        self.assertIn('drift', {x['code'] for x in self.j.get(t['id'])['slips']})
        self.assertEqual(self.d['scale']['off'], 40)

    def test_first_morning_leaves_ripe_fruit(self):
        b = FR.baskets(self.j.c)
        self.assertGreater(b['xoai'].get('chin', 0), 0)
        self.assertGreater(b['chuoi'].get('chin', 0), 0)
        self.assertGreater(b['xoai'].get('xanh', 0), 0)
        self.assertTrue(self.d['seeded'])

    def test_cannot_sell_before_opening(self):
        t = self.kind('buy')
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('tc_pick', task=t['id'], item='cam', stage='tuoi')


class Buying(Base):
    def test_right_fruit_right_weight_pays_through_the_till(self):
        j = self.j
        self.setup_stall()
        t = self.kind('buy')
        money = j.c['money']
        r = self.sell(t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertGreater(t['price'], 0)
        self.assertEqual(sum(r['amount'] for r in ledger(j.c, t['id']) if r.get('category') != 'tip'), t['price'])
        self.assertEqual(j.c['money'] - money, sum(r['amount'] for r in ledger(j.c, t['id'])))
        self.assertTrue(any(p['source'] == t['id'] and p['kind'] == 'review' for p in j.c['feed']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_price_is_weight_times_price_per_kilo(self):
        j = self.j
        self.setup_stall()
        t = self.fill(self.kind('buy')['id'])
        grams = sum(b['g'] for b in t['bag'])
        j.act('tc_weigh', task=t['id'])
        self.assertEqual(j.get(t['id'])['price'], round(grams * FR.PRICES['cam'] / 1000))

    def test_an_unzeroed_basket_overcharges_and_a_careful_customer_catches_it(self):
        day, slot = next((d, s) for d in range(2, 60) for s in range(1, 6)
                         if FR.make_task(d, s, 1)['kind'] == 'buy' and FR.make_task(d, s, 1)['needs']['check'])
        j = Journey('fruit', slot=slot, day=day)
        j.c['ext']['data']['stall'].update(open=True, cover='du', tested=True)
        self.stock_up(j)
        t = self.fill(j.task['id'], j, tare=False)
        j.act('tc_weigh', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('cheat_scale', {x['code'] for x in t['slips']})
        self.assertEqual(t['weighed'], sum(b['g'] for b in t['bag']) + FR.BASKET)

    def test_an_unzeroed_basket_is_counted_at_night(self):
        j = self.j
        self.setup_stall()
        t = self.fill(self.kind('buy')['id'], tare=False)
        j.act('tc_weigh', task=t['id'])
        self.assertNotIn('cheat_scale', {x['code'] for x in j.get(t['id']).get('slips', [])})   # Chị Thảo does not weigh again
        self.pay_exact(t['id'])
        self.assertGreater(self.d['today']['over_xu'], 0)
        lines = j.act('end_day')['summary']['career']['lines']
        self.assertTrue(any('cân thiếu' in x for x in lines), lines)

    def test_one_fruit_too_many_is_handed_back(self):
        j = self.j
        self.setup_stall()
        t = self.fill(self.kind('buy')['id'])
        for _ in range(2):
            j.act('tc_pick', task=t['id'], item='cam', stage='tuoi')
        r = j.act('tc_weigh', task=t['id'])
        self.assertFalse(r.get('correct', True))
        self.assertEqual(j.get(t['id'])['stage'], 'prep')
        j.act('tc_unpick', task=t['id'], index=len(j.get(t['id'])['bag']) - 1)

    def test_wrong_ripeness_is_a_slip(self):
        j = self.j
        self.setup_stall()
        t = next(x for x in j.c['tasks'] if x['title'] == 'Cô Năm mua xoài')
        j.act('ask', task=t['id'])
        j.act('tc_tare', task=t['id'])
        for _ in range(2):
            j.act('tc_pick', task=t['id'], item='xoai', stage='xanh')
        j.act('tc_weigh', task=t['id'])
        self.assertIn('ripe_xoai', {x['code'] for x in j.get(t['id'])['slips']})

    def test_unpicking_puts_the_fruit_back(self):
        j = self.j
        self.setup_stall()
        t = self.kind('buy')
        j.act('ask', task=t['id'])
        before = kit.stock(j.c, 'cam')
        j.act('tc_pick', task=t['id'], item='cam', stage='tuoi')
        self.assertEqual(kit.stock(j.c, 'cam'), before - 1)
        j.act('tc_unpick', task=t['id'], index=0)
        self.assertEqual(kit.stock(j.c, 'cam'), before)
        self.assertEqual(j.get(t['id'])['cost'], 0)

    def test_a_bruised_fruit_left_in_the_basket_reaches_the_customer(self):
        j = self.j
        self.setup_stall(sort=False)
        t = self.fill(self.kind('buy')['id'])
        self.assertTrue(any(b['b'] for b in t['bag']))
        j.act('tc_weigh', task=t['id'])
        self.assertIn('bruised', {x['code'] for x in j.get(t['id'])['slips']})

    def test_honest_decline_when_nothing_fits(self):
        j = self.j
        self.setup_stall()
        t = self.kind('buy')
        j.act('ask', task=t['id'])
        j.act('tc_pick', task=t['id'], item='cam', stage='tuoi')
        before = kit.stock(j.c, 'cam')
        j.act('tc_decline', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(kit.stock(j.c, 'cam'), before + 1)
        self.assertFalse(ledger(j.c, t['id']))


class Haggle(Base):
    def at_haggle(self, wants):
        day, slot = next((d, s) for d in range(2, 80) for s in range(1, 6)
                         if FR.make_task(d, s, 1).get('_haggle', {}).get('wants') == wants and FR.make_task(d, s, 1)['kind'] == 'buy')
        j = Journey('fruit', slot=slot, day=day)
        j.c['ext']['data']['stall'].update(open=True, cover='du', tested=True)
        self.stock_up(j)
        t = self.fill(j.task['id'], j)
        j.act('tc_weigh', task=t['id'])
        return j, j.get(t['id'])

    def test_every_deal(self):
        for wants in ('meet', 'extra', 'hold'):
            for deal in FR.DEALS:
                j, t = self.at_haggle(wants)
                self.assertEqual(t['stage'], 'haggle')
                full, offer = t['price'], t['offer']
                self.assertLess(offer, full)
                j.act('tc_deal', task=t['id'], deal=deal)
                t = j.get(t['id'])
                self.assertEqual(t['stage'], 'pay')
                self.assertEqual(t['price'], {'hold': full, 'meet': (full + offer + 1) // 2, 'extra': full, 'give': offer}[deal])
                stiff = 'stiff' in {x['code'] for x in t.get('slips', [])}
                self.assertEqual(stiff, deal == 'hold' and wants != 'hold', (wants, deal))
                self.pay_exact(t['id'], j)
                self.assertEqual(j.get(t['id'])['status'], 'completed')
                validate_state(json.loads(json.dumps(j.state)))


class Kinds(Base):
    def test_altar_tray(self):
        day, slot = next((d, s) for d in range(3, 120) for s in range(1, 4) if FR.make_task(d, s, 1)['kind'] == 'altar')
        j = Journey('fruit', slot=slot, day=day)
        j.c['ext']['data']['stall'].update(open=True, cover='du', tested=True)
        self.stock_up(j)
        tid = j.task['id']
        r = self.sell(tid, j)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'), r)
        self.assertEqual(len({b['i'] for b in t['bag']}), len(t['needs']['lines']))

    def test_bulk_buyer_takes_over_ripe_fruit_only(self):
        day, slot = next((d, s) for d in range(2, 80) for s in range(1, 6) if FR.make_task(d, s, 1)['kind'] == 'bulk')
        j = Journey('fruit', slot=slot, day=day)
        j.c['ext']['data']['stall'].update(open=True, cover='du', tested=True)
        self.stock_up(j)
        tid = j.task['id']
        self.sell(tid, j)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(all(b['s'] == 'ky' for b in t['bag']))

    def test_a_customer_brings_fruit_back(self):
        for fault in ('shop', 'buyer'):
            for choice in ('swap', 'refund', 'explain', 'argue'):
                day, slot = next((d, s) for d in range(2, 200) for s in range(1, 6)
                                 if FR.make_task(d, s, 1)['kind'] == 'return' and FR.make_task(d, s, 1)['_fault'] == fault)
                j = Journey('fruit', slot=slot, day=day)
                self.stock_up(j)
                tid = j.task['id']
                j.act('ask', task=tid)
                r = j.act('tc_look', task=tid)
                self.assertIn(j.get(tid)['_look'], r['message'])
                j.act('tc_return', task=tid, choice=choice)
                t = j.get(tid)
                codes = {x['code'] for x in t.get('slips', [])}
                self.assertEqual(t['status'], 'completed')
                self.assertEqual('excuse' in codes, fault == 'shop' and choice == 'explain')
                self.assertEqual('argue' in codes, choice == 'argue')
                if choice == 'refund':
                    self.assertTrue(any(x['category'] == 'refund' for x in ledger(j.c, tid)))
                validate_state(json.loads(json.dumps(j.state)))


class Evening(Base):
    def test_selling_off_the_ripe_fruit(self):
        j = self.j
        self.setup_stall()
        money = j.c['money']
        r = j.act('tc_xa')
        self.assertTrue(self.d['stall']['xa'])
        self.assertGreater(self.d['today']['xa_sold'], 0)
        self.assertEqual(j.c['money'] - money, self.d['today']['xa_money'])
        self.assertIn('Bán được', r['message'])
        with self.assertRaises(GameError):
            j.act('tc_xa')

    def test_unsorted_bruises_spoil_more_at_night(self):
        j = self.j
        self.setup_stall(sort=False)
        before = kit.stock(j.c, 'cam')
        s = j.act('end_day')['summary']['career']
        self.assertEqual(s['rotted'], 2)
        self.assertEqual(kit.stock(j.c, 'cam'), before - 2)

    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            self.stock_up()
            self.setup_stall()
            for t in [x for x in j.c['tasks'] if x['kind'] != 'setup' and x['status'] not in ('completed', 'cancelled')]:
                self.settle_desk()
                if t['kind'] == 'return':
                    j.act('ask', task=t['id'])
                    j.act('tc_look', task=t['id'])
                    j.act('tc_return', task=t['id'], choice='refund')
                else:
                    self.sell(t['id'])
            validate_state(json.loads(json.dumps(j.state)))
            self.settle_desk()
            j.act('end_day')
            j.act('start_day')
            self.assertEqual(j.task['kind'], 'setup')
        self.assertGreater(self.d['stats']['customers'], 10)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in FR.DESK:
            for o in x['options']:
                j = Journey('fruit')
                self.setup_stall(j)
                j.c['money'] += 100
                j.c['ops']['finance']['opening_balance'] += 100
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('tc_xa')
                r = j.act('tc_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        for x in FR.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_validate_rejects_broken_data(self):
        for path, value in ((('scale', 'off'), 9000), (('stall', 'cover'), 'tent'), (('bruise',), {'durian': 1}), (('seeded',), 'yes')):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['fruit']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        for key, value in (('needs', {'lines': []}), ('_haggle', dict(pct=1, wants='give')), ('stage', 'free')):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['fruit']['tasks'] if x['kind'] == 'buy' and x.get('_haggle'))
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_hidden_facts_stay_hidden(self):
        self.setup_stall()
        view = public_state(self.j.state)['careers']['fruit']
        raw = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_haggle', raw)
        self.assertNotIn('_fault', raw)
        buy = next(t for t in view['tasks'] if t['kind'] == 'buy')
        self.assertIsNone(buy['needs'])
        for k in ('stall', 'scale', 'baskets', 'bruise', 'mod', 'desk'):
            self.assertIn(k, view['data'])

    def test_old_save_without_the_stall_loads(self):
        s = new_state()
        s['careers'].pop('fruit', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('fruit', s['careers'])

    def test_old_data_gains_new_fields(self):
        j = self.j
        d = j.c['ext']['data']
        for k in ('regulars', 'today', 'bruise'):
            d.pop(k)
        d['stats'].pop('fair')
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        j.state = s
        self.setup_stall()
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
