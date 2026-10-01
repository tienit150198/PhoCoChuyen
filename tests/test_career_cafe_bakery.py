import copy
import json
import unittest

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import cafe_bakery as CB
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def find_slot(pred, days=range(1, 15), style='classic'):
    for day in days:
        for slot in range(12):
            t = CB.make_task(day, slot, 1)
            if t['needs'].get('style') == style and pred(t['needs']):
                return day, slot
    raise AssertionError('no matching order in the order book')


class CafeBakeryTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('cafe_bakery')

    def tearDown(self):
        kit.clock = self.old

    # --- helpers --------------------------------------------------------------
    def journey(self, pred, days=range(1, 15), style='classic'):
        day, slot = find_slot(pred, days, style)
        j = Journey('cafe_bakery', slot=slot, day=day)
        self.stock_up(j)
        self.j = j
        return j

    def stock_up(self, j, qty=12):
        for it in CB.ITEMS:
            room = 40 - kit.stock(j.c, it['id'])
            if room > 0:
                inventory.add_lot(j.c, it['id'], min(qty, room), 1, 5, 'partner')

    def fresh_lot(self, j, item):
        return next(l for l in j.c['ext']['data']['case'] if l['item'] == item and CB.lot_state(j.c, item, l['day']) == 'fresh' and l['qty'] > 0)

    def ensure_case(self, j, item, qty=6):
        d = j.c['ext']['data']
        d['case'].append(dict(id=f'test-{item}-{len(d["case"])}', item=item, qty=qty, day=j.c['day'], q='golden', sale=False, cost=1))

    def drink(self, tid=None, pull=27, steam=13, art=True, milk=None, lid=True):
        j = self.j
        t = j.get(tid) if tid else j.task
        tid = t['id']
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        kind = 'paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug'
        j.act('cb_cup', task=tid, kind=kind, size=n['size'])
        if n['iced']:
            j.act('cb_ice', task=tid)
        for _ in range(n['shots']):
            j.act('cb_dose', task=tid, beans=n['beans'], grind='fine', grams=18)
            j.act('cb_pull', task=tid)
            self.clock.t += pull
            j.act('cb_stop', task=tid)
        if CB.DRINKS[n['drink']]['water']:
            j.act('cb_water', task=tid)
        if n['milk']:
            m = milk or n['milk']
            if n['iced']:
                j.act('cb_milk', task=tid, milk=m, mode='cold')
            else:
                j.act('cb_milk', task=tid, milk=m, mode='steam', foam=n['foam'])
                self.clock.t += steam
                j.act('cb_milk_stop', task=tid)
        if n['art'] and art:
            j.act('cb_art', task=tid, pattern=n['art'])
        for item, q in n['pastry'].items():
            for _ in range(q):
                if not any(l['item'] == item and l['qty'] > 0 and CB.lot_state(j.c, item, l['day']) == 'fresh' for l in j.c['ext']['data']['case']):
                    self.ensure_case(j, item)
                j.act('cb_pick', task=tid, lot=self.fresh_lot(j, item)['id'])
        if n['pastry'] and n['takeaway']:
            j.act('cb_bag', task=tid)
        if kind == 'paper' and lid:
            j.act('cb_lid', task=tid)
        return tid

    def ledger(self):
        return self.j.c['ops']['finance']['ledger']

    def review(self, tid):
        return next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    # --- tests ----------------------------------------------------------------
    def test_happy_drink_review_and_money(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] == 'milk' and not n['iced'] and n['art'], days=[1])
        money, n0 = j.c['money'], len(self.ledger())
        tid = self.drink()
        price = j.get(tid)['quoted_price']
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertTrue(r.get('celebrate'))
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        rows = self.ledger()[n0:]
        self.assertEqual(sum(e['amount'] for e in rows if e['ref'] == tid and e['category'] == 'revenue'), price)
        self.assertEqual(j.c['money'] - money, sum(e['amount'] for e in rows))
        post = self.review(tid)
        self.assertEqual(post['stars'], 5)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'taste', 'accuracy', 'presentation', 'speed'})
        validate_state(json.loads(json.dumps(j.state)))

    def test_needs_hidden_until_ask(self):
        for view in public_state(self.j.state)['careers']['cafe_bakery']['tasks']:
            self.assertIsNone(view['needs'])
        raw = json.dumps(public_state(self.j.state)['careers']['cafe_bakery']['tasks'], ensure_ascii=False)
        for t in self.j.c['tasks']:
            self.assertNotIn(t['needs']['note'], raw)
        with self.assertRaises(GameError):
            self.j.act('cb_cup', kind='mug', size='S')

    def test_extraction_window_by_real_seconds(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['drink'] == 'espresso' and n['shots'] == 1, days=[1])
        j.act('ask')
        j.act('cb_cup', kind='mug', size='S')
        results = []
        for grind, sec in (('fine', 12), ('fine', 27), ('fine', 40), ('coarse', 27)):
            j.act('cb_dose', beans='house', grind=grind, grams=18)
            j.act('cb_pull')
            self.clock.t += sec
            j.act('cb_stop')
            results.append(j.task['drink']['shots'][-1]['x'])
            if len(j.task['drink']['shots']) == 3:
                j.act('cb_dump', part='drink', confirm=True)
                j.act('cb_cup', kind='mug', size='S')
        self.assertEqual(results, ['sour', 'balanced', 'bitter', 'sour'])
        self.assertGreaterEqual(j.task['mistakes'], 3)

    def test_light_dose_runs_fast(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['drink'] == 'espresso', days=[1])
        j.act('ask')
        j.act('cb_cup', kind='mug', size='S')
        j.act('cb_dose', beans='house', grind='fine', grams=14)
        j.act('cb_pull')
        self.clock.t += 27
        j.act('cb_stop')
        shot = j.task['drink']['shots'][-1]
        self.assertGreater(shot['sec'], 30)
        self.assertIn(shot['x'], ('strong', 'bitter'))

    def test_steamed_milk_temperature(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1, 2])
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='paper' if n['takeaway'] else 'mug', size=n['size'])
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        self.clock.t += 20
        j.act('cb_milk_stop')
        self.assertEqual(j.task['drink']['milk']['tex'], 'scalded')
        self.assertEqual(j.task['mistakes'], 1)
        # A scalded pitcher cannot hold latte art.
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 27
        j.act('cb_stop')
        j.act('cb_art', pattern='heart')
        self.assertEqual(j.task['drink']['art'], 'blob')

    def test_first_day_timer_does_the_timing(self):
        """Onboarding: on day 1 a pull or a steam with auto=true ends at once in the good window."""
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1])
        self.assertEqual(j.c['day'], 1)
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='paper' if n['takeaway'] else 'mug', size=n['size'])
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull', auto=True)
        self.assertIsNone(j.task['drink']['pulling'])
        self.assertEqual(j.task['drink']['shots'][-1]['x'], 'balanced')
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'], auto=True)
        self.assertIsNone(j.task['drink']['steaming'])
        self.assertEqual(j.task['drink']['milk']['tex'], 'silky')
        self.assertEqual(j.task['mistakes'], 0)
        # The timer only times: a coarse grind still runs sour.
        j.act('cb_dose', beans=n['beans'], grind='coarse', grams=18)
        j.act('cb_pull', auto=True)
        self.assertEqual(j.task['drink']['shots'][-1]['x'], 'sour')
        # From day 2 there is no timer: the same request starts a hand-timed pull.
        j.c['day'] = 2
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull', auto=True)
        self.assertIsNotNone(j.task['drink']['pulling'])

    def three_drinks(self):
        """A journey whose queue holds three drink orders (tasks may come from different days)."""
        slots = [(d, s) for d in range(1, 6) for s in range(3)
                 if CB.make_task(d, s, 1)['needs']['kind'] == 'drink' and CB.make_task(d, s, 1)['needs']['milk'] in ('milk', 'oat')
                 and CB.make_task(d, s, 1)['needs']['style'] == 'classic'][:3]
        j = Journey('cafe_bakery', slot=slots[0][1], day=slots[0][0])
        j.c['tasks'] = [CB.make_task(d, s, 1) for d, s in slots]
        j.c['active_task'] = j.c['tasks'][0]['id']
        self.stock_up(j)
        validate_state(j.state)
        self.j = j
        for t in j.c['tasks']:
            j.act('ask', task=t['id'])
            j.act('cb_cup', task=t['id'], kind='mug', size='S')
        return j, [t['id'] for t in j.c['tasks']]

    def test_two_group_heads(self):
        j, ids = self.three_drinks()
        for tid in ids:
            j.act('cb_dose', task=tid, beans='house', grind='fine', grams=18)
        j.act('cb_pull', task=ids[0])
        j.act('cb_pull', task=ids[1])
        with self.assertRaises(GameError):
            j.act('cb_pull', task=ids[2])
        view = public_state(j.state)['careers']['cafe_bakery']['data']
        self.assertEqual(len(view['groups']), 2)
        j.act('cb_stop', task=ids[0])
        j.act('cb_pull', task=ids[2])

    def test_one_steam_wand(self):
        j, ids = self.three_drinks()
        for tid in ids[:2]:
            n = j.get(tid)['needs']
            if tid == ids[0]:
                j.act('cb_milk', task=tid, milk=n['milk'], mode='steam', foam='thin')
            else:
                with self.assertRaises(GameError):
                    j.act('cb_milk', task=tid, milk=n['milk'], mode='steam', foam='thin')

    def test_lactose_intolerance_is_a_safety_mistake(self):
        # Behaviour change: cow's milk reaching a lactose-intolerant guest is no longer a free redo.
        j = self.journey(lambda n: n['kind'] == 'drink' and n['lactose'], days=[1])
        n0 = len(self.ledger())
        tid = self.drink(milk='milk')
        r = j.act('cb_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn('sữa bò', r['message'])
        self.assertEqual(sum(e['amount'] for e in self.ledger()[n0:] if e['ref'] == tid), 0)
        self.assertEqual(self.review(tid)['stars'], 1)
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_wrong_drink_refused_then_redone(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1])
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        kind = 'paper' if n['takeaway'] else 'mug'
        j.act('cb_cup', task=tid, kind=kind, size=n['size'])
        j.act('cb_dose', task=tid, beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull', task=tid)
        self.clock.t += 27
        j.act('cb_stop', task=tid)
        if kind == 'paper':
            j.act('cb_lid', task=tid)
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        waste = len(j.c['life']['waste'])
        j.act('cb_dump', task=tid, part='drink', confirm=True)
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        kind = 'paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug'
        j.act('cb_cup', task=tid, kind=kind, size=n['size'])
        j.act('cb_dose', task=tid, beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull', task=tid)
        self.clock.t += 27
        j.act('cb_stop', task=tid)
        j.act('cb_milk', task=tid, milk=n['milk'], mode='steam', foam=n['foam'])
        self.clock.t += 13
        j.act('cb_milk_stop', task=tid)
        if n['art']:
            j.act('cb_art', task=tid, pattern=n['art'])
        if kind == 'paper':
            j.act('cb_lid', task=tid)
        for item, q in n['pastry'].items():
            for _ in range(q):
                self.ensure_case(j, item)
                j.act('cb_pick', task=tid, lot=self.fresh_lot(j, item)['id'])
        if n['pastry'] and n['takeaway']:
            j.act('cb_bag', task=tid)
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertIn('care', crit)
        self.assertEqual([x['code'] for x in j.get(tid)['slips']], ['returned'])
        self.assertLessEqual(self.review(tid)['stars'], 4)
        validate_state(j.state)

    def test_decaf_order_refuses_caffeine(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['decaf'])
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='mug', size=n['size'])
        # The decaf bean is unlocked for this order even at level 1.
        j.act('cb_dose', beans='house', grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 27
        j.act('cb_stop')
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        self.clock.t += 13
        j.act('cb_milk_stop')
        tid = j.task['id']
        r = j.act('cb_serve', confirm=True)
        # Behaviour change: caffeine for a heart patient is a safety mistake (1 star, no pay).
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn('caffeine', r['message'])
        self.assertEqual(self.review(tid)['stars'], 1)

    def test_takeaway_needs_lid_and_iced_needs_ice(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['takeaway'] and n['iced'], days=[1])
        tid = self.drink(lid=False)
        with self.assertRaises(GameError):
            j.act('cb_serve', task=tid, confirm=True)
        j.act('cb_lid', task=tid)
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_wrong_drink_identity_refused(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['drink'] == 'americano', days=[1])
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='paper', size=n['size'])
        j.act('cb_ice')
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 27
        j.act('cb_stop')
        j.act('cb_lid')
        r = j.act('cb_serve', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('americano', r['message'])

    def test_pastry_order_and_nut_allergy(self):
        j = self.journey(lambda n: n['kind'] == 'pastry' and n['allergy'] == 'nuts', days=[2, 3, 4, 5, 6])
        for item in ('croissant', 'banhmi', 'cookie'):
            self.ensure_case(j, item)
        j.act('ask')
        n = j.task['needs']
        j.act('cb_pick', lot=self.fresh_lot(j, 'cookie')['id'])
        for item, q in n['items'].items():
            for _ in range(q):
                j.act('cb_pick', lot=self.fresh_lot(j, item)['id'])
        j.act('cb_bag')
        # Open the bag, put the cookie back, fold the same bag again (no second bag used).
        bags = kit.stock(j.c, 'bag')
        j.act('cb_return', index=0)
        self.assertFalse(j.task['bag']['bagged'])
        self.assertFalse(any(x['item'] == 'cookie' for x in j.task['bag']['items']))
        j.act('cb_bag')
        self.assertEqual(kit.stock(j.c, 'bag'), bags)
        tid = j.task['id']
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertFalse(j.get(tid).get('slips'))

    def test_nut_allergen_reaching_the_guest_is_a_safety_mistake(self):
        # Behaviour change: the cookie is no longer silently refused; it reaches the guest.
        j = self.journey(lambda n: n['kind'] == 'pastry' and n['allergy'] == 'nuts', days=[2, 3, 4, 5, 6])
        for item in ('croissant', 'banhmi', 'cookie'):
            self.ensure_case(j, item)
        tid = j.task['id']
        j.act('ask')
        n0 = len(self.ledger())
        j.act('cb_pick', lot=self.fresh_lot(j, 'cookie')['id'])
        for item, q in j.task['needs']['items'].items():
            for _ in range(q):
                j.act('cb_pick', lot=self.fresh_lot(j, item)['id'])
        j.act('cb_bag')
        r = j.act('cb_serve', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn('dị ứng hạt', r['message'])
        self.assertEqual(sum(e['amount'] for e in self.ledger()[n0:] if e['ref'] == tid), 0)
        self.assertEqual(self.review(tid)['stars'], 1)
        self.assertTrue(j.c['incidents']['follow'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_proof_then_bake_real_time(self):
        j = self.j
        d = j.c['ext']['data']
        flour, butter = kit.stock(j.c, 'flour'), kit.stock(j.c, 'butter')
        j.act('cb_shape', item='croissant')
        self.assertEqual(kit.stock(j.c, 'flour'), flour - 1)
        self.assertEqual(kit.stock(j.c, 'butter'), butter - 2)
        with self.assertRaises(GameError):
            j.act('cb_bake', item='croissant')
        j.act('advance')
        j.act('advance')
        before = CB._case_count(d if False else j.c['ext']['data'], 'croissant')
        j.act('cb_bake', item='croissant')
        rack = j.c['ext']['data']['oven'][0]
        self.clock.t += 17
        j.act('cb_unload', rack=rack['id'])
        d = j.c['ext']['data']
        self.assertEqual(CB._case_count(d, 'croissant'), before + 6)
        self.assertTrue(any(l['item'] == 'croissant' and l['day'] == j.c['day'] and l['q'] == 'golden' for l in d['case']))
        self.assertEqual(d['proof'], [])
        validate_state(j.state)

    def test_burnt_tray_is_waste(self):
        j = self.j
        waste = len(j.c['life']['waste'])
        j.act('cb_bake', item='cookie')
        self.clock.t += 30
        j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'cookie')

    def test_oven_has_two_racks(self):
        j = self.j
        j.act('cb_bake', item='cookie')
        j.act('cb_bake', item='cookie')
        with self.assertRaises(GameError):
            j.act('cb_bake', item='cookie')

    def test_cake_flow_name_must_match(self):
        j = self.journey(lambda n: n['kind'] == 'cake')
        j.act('ask')
        n = j.task['needs']
        j.act('cb_bake', item='sponge')
        self.clock.t += 20
        rack = j.c['ext']['data']['oven'][0]['id']
        j.act('cb_unload', rack=rack)
        self.assertEqual(j.task['cake']['sponge'], 'golden')
        j.act('advance')
        j.act('cb_frost', cream=n['cream'], color=n['color'])
        self.assertFalse(j.task['cake']['melted'])
        wrong = CB._letters(n['text']).replace('ọ', 'o').replace('ư', 'u').replace('ở', 'o').replace('ệ', 'e')
        if wrong == CB._letters(n['text']):
            wrong = n['text'] + ' x'
        j.act('cb_write', text=wrong)
        j.act('cb_box')
        r = j.act('cb_serve', confirm=True)
        self.assertTrue(r.get('refused'))
        with self.assertRaises(GameError):
            j.act('cb_scrape', confirm=True)  # boxed: open it first
        j.task['cake']['boxed'] = False
        j.act('cb_scrape', confirm=True)
        j.act('cb_write', text='  ' + n['text'].upper() + '!  ')
        j.act('cb_box')
        tid = j.task['id']
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['presentation']['score'], 4)
        validate_state(json.loads(json.dumps(j.state)))

    def test_cake_steps_need_the_recipe_the_screen_counts(self):
        """cafe_bakery.js lacks(): the sponge and the cream take the recipes the client reads (content() bakes/creams),
        each item at least its count. One fewer of any is refused untouched (the screen offers "📦 Nhập …"
        instead of the button), exactly the recipe goes through."""
        def set_stock(c, item, n):
            first = True
            for lot in c['ext']['inv']['lots']:
                if lot['item'] == item and lot['expires'] >= c['day']:
                    lot['qty'], first = (n if first else 0), False
            self.assertFalse(first, item)
        j = self.journey(lambda n: n['kind'] == 'cake')
        j.act('ask')
        n = j.task['needs']
        content = CB.content()
        sponge = next(b for b in content['bakes'] if b['id'] == 'sponge')['recipe']
        cream = next(c for c in content['creams'] if c['id'] == n['cream'])['recipe']
        for recipe, act in ((sponge, lambda: j.act('cb_bake', item='sponge')), (cream, lambda: j.act('cb_frost', cream=n['cream'], color=n['color']))):
            for short in recipe:
                for k, q in recipe.items():
                    set_stock(j.c, k, q - (k == short))
                before = copy.deepcopy(j.state)
                with self.assertRaises(GameError):
                    act()
                self.assertEqual(j.state, before, short)
            for k, q in recipe.items():
                set_stock(j.c, k, q)
            act()
            self.assertEqual({k: kit.stock(j.c, k) for k in recipe}, {k: 0 for k in recipe})
            if recipe is sponge:
                self.clock.t += 20
                j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
                j.act('advance')

    def test_frosting_a_warm_sponge_melts(self):
        j = self.journey(lambda n: n['kind'] == 'cake')
        j.act('ask')
        n = j.task['needs']
        j.act('cb_bake', item='sponge')
        self.clock.t += 20
        j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
        j.act('cb_frost', cream=n['cream'], color=n['color'])
        self.assertTrue(j.task['cake']['melted'])

    def test_pale_sponge_refused(self):
        j = self.journey(lambda n: n['kind'] == 'cake')
        j.act('ask')
        n = j.task['needs']
        j.act('cb_bake', item='sponge')
        self.clock.t += 5
        j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
        self.assertEqual(j.task['cake']['sponge'], 'pale')
        with self.assertRaises(GameError):
            j.act('cb_frost', cream=n['cream'], color=n['color'])
        j.act('cb_dump', part='cake', confirm=True)
        self.assertIsNone(j.task['cake']['sponge'])

    def test_day_old_rules_markdown_donate_discard(self):
        j = self.j
        self.ensure_case(j, 'bonglan', 4)
        j.act('end_day', carry_event=True)
        d = j.c['ext']['data']
        # Sauce cake never stays overnight; dry bakes become "day old".
        self.assertFalse(any(l['item'] == 'bonglan' for l in d['case']))
        cro = next(l for l in d['case'] if l['item'] == 'croissant')
        self.assertEqual(CB.lot_state(j.c, 'croissant', cro['day']), 'day_old')
        j.act('start_day')
        j.act('cb_markdown', lot=cro['id'])
        with self.assertRaises(GameError):
            j.act('cb_donate', lot=next(l for l in j.c['ext']['data']['case'] if l['item'] == 'banhmi')['id'])
        bm = next(l for l in j.c['ext']['data']['case'] if l['item'] == 'banhmi')
        j.act('cb_donate', lot=bm['id'], confirm=True)
        self.assertEqual(j.c['ext']['data']['donated'], bm['qty'])
        before = j.c['money']
        summary = j.act('end_day', carry_event=True)['summary']
        self.assertGreater(summary['career']['markdown_sold'], 0)
        self.assertGreater(j.c['money'], before)
        # Everything baked on day 1 except cookies is gone after its day-old day.
        self.assertFalse(any(l['item'] in ('croissant', 'banhmi') for l in j.c['ext']['data']['case']))
        validate_state(j.state)

    def test_day_old_pick_is_a_mistake_unless_asked(self):
        j = self.journey(lambda n: n['kind'] == 'pastry' and n['day_old_ok'], days=[2, 3, 4])
        d = j.c['ext']['data']
        d['case'] = [dict(id='old-cro', item='croissant', qty=4, day=j.c['day'] - 1, q='golden', sale=True, cost=1)]
        j.act('ask')
        j.act('cb_pick', lot='old-cro')
        j.act('cb_pick', lot='old-cro')
        self.assertEqual(j.task['mistakes'], 0)
        j.act('cb_bag')
        tid = j.task['id']
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['fresh']['score'], 5)

    def test_expired_lot_cannot_be_sold_or_donated(self):
        j = self.journey(lambda n: n['kind'] == 'pastry', days=[3, 4, 5])
        lot = next(l for l in j.c['ext']['data']['case'] if l['item'] == 'croissant')
        self.assertEqual(CB.lot_state(j.c, 'croissant', lot['day']), 'expired')
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('cb_pick', task=tid, lot=lot['id'])
        with self.assertRaises(GameError):
            j.act('cb_donate', lot=lot['id'], confirm=True)
        j.act('cb_discard', lot=lot['id'], confirm=True)
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'croissant')

    def test_validation_errors(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1])
        j.act('ask')
        bad = [('cb_cup', dict(kind='bucket', size='S')), ('cb_cup', dict(kind=['mug'], size='S')), ('cb_cup', dict(kind='mug', size={'L': 1})), ('cb_cup', dict(kind='mug', size='XL')),
               ('cb_dose', dict(beans='house', grind='fine', grams=18)),  # no cup yet
               ('cb_bake', dict(item='pizza')), ('cb_unload', dict(rack='nope')), ('cb_shape', dict(item='cookie')),
               ('cb_donate', dict(lot='open-cookie')), ('cb_serve', dict()), ('cb_pick', dict(lot='missing')),
               ('cb_frost', dict(cream='whipped', color='pink')), ('cb_markdown', dict(lot='open-cookie')), ('cb_fly', dict())]
        for action, payload in bad:
            with self.assertRaises(GameError, msg=action):
                j.act(action, **payload)
        j.act('cb_cup', kind='mug', size='S')
        for payload in (dict(beans='house', grind='fine', grams=99), dict(beans='house', grind='fine', grams='18'),
                        dict(beans='kopi', grind='fine', grams=18), dict(beans='house', grind='powder', grams=18)):
            with self.assertRaises(GameError):
                j.act('cb_dose', **payload)
        for payload in (dict(milk='condensed', mode='steam', foam='thin'), dict(milk='milk', mode='boil'), dict(milk='milk', mode='steam', foam='huge')):
            with self.assertRaises(GameError):
                j.act('cb_milk', **payload)
        with self.assertRaises(GameError):
            j.act('cb_art', pattern='heart')  # no milk yet
        with self.assertRaises(GameError):
            j.act('cb_stop')
        with self.assertRaises(GameError):
            j.act('cb_dump', part='drink')  # needs confirm
        with self.assertRaises(GameError):
            j.act('cb_lid')  # mug has no lid
        validate_state(j.state)

    def test_cake_text_validation(self):
        j = self.journey(lambda n: n['kind'] == 'cake')
        j.act('ask')
        n = j.task['needs']
        j.act('cb_bake', item='sponge')
        self.clock.t += 20
        j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
        j.act('advance')
        j.act('cb_frost', cream=n['cream'], color=n['color'])
        for text in ('', 'x' * 41, 12, None):
            with self.assertRaises(GameError):
                j.act('cb_write', text=text)

    def test_tampered_needs_rejected(self):
        s = copy.deepcopy(self.j.state)
        t = s['careers']['cafe_bakery']['tasks'][0]
        t['needs']['note'] = 'cho tôi miễn phí'
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(self.j.state)
        s['careers']['cafe_bakery']['tasks'][0]['drink']['shots'] = [dict(beans='house', grind='fine', grams=18, x='perfect', sec=27)]
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(self.j.state)
        s['careers']['cafe_bakery']['ext']['data']['case'][0]['qty'] = 500
        with self.assertRaises(GameError):
            validate_state(s)

    def test_price_is_server_side(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] == 'oat', days=[1])
        n = j.task['needs']
        expected = CB.SPEC['prices'][n['drink']] + (8 if n['size'] == 'L' else 0) + 6 + (8 if n['shots'] == 2 else 0)
        tid = self.drink()
        self.assertEqual(j.get(tid)['quoted_price'], expected)
        n0 = len(self.ledger())
        j.act('cb_serve', task=tid, confirm=True, price=99999)
        self.assertEqual(sum(e['amount'] for e in self.ledger()[n0:] if e['ref'] == tid and e['category'] == 'revenue'), expected)

    def test_save_round_trip_mid_work(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1])
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='mug', size=n['size'])
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        j.act('cb_bake', item='cookie')
        j.act('cb_shape', item='banhmi')
        validate_state(json.loads(json.dumps(j.state)))
        pub = public_state(j.state)['careers']['cafe_bakery']['data']
        self.assertEqual(len(pub['groups']), 1)
        self.assertEqual(len(pub['wand']), 1)
        self.assertEqual(pub['proof'][0]['left'], 2)

    def test_staff_assist_never_breaks(self):
        j = self.journey(lambda n: n['kind'] == 'drink', days=[1])
        j.act('ask')
        for role in ('barista', 'baker', 'cashier', 'patrol'):
            note = CB.assist(j.state, j.c, dict(role=role, name='X'), j.task)
            self.assertTrue(note is None or isinstance(note, str))
        self.assertIsNotNone(j.task['drink']['container'])
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = self.j
        for x in CB.SPEC['situations']:
            self.assertGreaterEqual(len(x['options']), 2)
            for opt in x['options']:
                self.assertGreaterEqual(len(opt['perspectives']), 2, opt['id'])
                self.assertLessEqual(opt.get('cost', 0), 80)
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_content_and_spec_shape(self):
        spec = CB.SPEC
        self.assertEqual(spec['id'], 'cafe_bakery')
        self.assertTrue(5 <= len(spec['people']) <= 7)
        self.assertEqual(len(spec['staff']), 4)
        self.assertTrue(5 <= len(spec['situations']) <= 8)
        self.assertEqual(len(spec['stories']), 3)
        ids = {x['id'] for x in spec['inventory']['items']}
        self.assertTrue({'beans_house', 'milk', 'oat', 'flour', 'butter', 'egg', 'sugar', 'cup', 'bag', 'cake_box'} <= ids)
        json.dumps(CB.content())
        self.assertGreaterEqual(len(CB.EVENTS), 8)
        self.assertGreaterEqual(len(CB.MODS), 6)
        for e in CB.EVENTS:
            self.assertGreaterEqual(len(e['choices']), 2, e['id'])

    # --- the shop day: moods, trays, buyers, surprises ------------------------
    def cup(self, tid, sp, milk=None):
        """Make the active cup of an order exactly as `sp` says (optionally with another milk)."""
        j = self.j
        kind = 'paper' if sp['takeaway'] else 'glass' if sp['iced'] else 'mug'
        j.act('cb_cup', task=tid, kind=kind, size=sp['size'])
        if sp['iced']:
            j.act('cb_ice', task=tid)
        for _ in range(sp['shots']):
            j.act('cb_dose', task=tid, beans=sp['beans'], grind='fine', grams=18)
            j.act('cb_pull', task=tid)
            self.clock.t += 27
            j.act('cb_stop', task=tid)
        if CB.DRINKS[sp['drink']]['water']:
            j.act('cb_water', task=tid)
        if sp['milk']:
            m = milk or sp['milk']
            if sp['iced']:
                j.act('cb_milk', task=tid, milk=m, mode='cold')
            else:
                j.act('cb_milk', task=tid, milk=m, mode='steam', foam=sp['foam'])
                self.clock.t += 13
                j.act('cb_milk_stop', task=tid)
        if sp['art']:
            j.act('cb_art', task=tid, pattern=sp['art'])
        if kind == 'paper':
            j.act('cb_lid', task=tid)

    def view(self, tid):
        return next(v for v in public_state(self.j.state)['careers']['cafe_bakery']['tasks'] if v['id'] == tid)

    def open_event(self, eid):
        pl = CB._plan(self.j.c)
        pl['events'] = [dict(id=eid, at=0, status='open', choice=None, good=None, note=None)]
        return pl

    def test_order_styles_grow_with_the_days(self):
        self.assertEqual({CB.make_task(1, s, 1)['needs']['style'] for s in range(12)}, {'classic'})
        later = {CB.make_task(d, s, 1)['needs']['style'] for d in range(3, 9) for s in range(12)}
        self.assertEqual(later, {'classic', 'mood', 'tray'})
        for d in range(1, 12):
            for s in range(12):
                t = CB.make_task(d, s, 1)
                self.assertEqual(t, CB.make_task(d, s, 1))
                self.assertEqual(len(t['cups']), len(t['needs'].get('party') or [1]))
                self.assertEqual(t['guest']['kind'], CB.NPC_GUEST[int(t['npc'].rsplit('_', 1)[1]) - 1])

    def test_luck_of_the_day_bends_orders(self):
        base = dict(kind='drink', drink='latte', beans='house', size='S', iced=False, takeaway=False, milk='milk', foam='thin', art=None,
                    shots=1, lactose=False, decaf=False, pastry={}, note='')
        hot, title = CB._twist(base, 'Latte nóng', 'heat')
        self.assertTrue(hot['iced'])
        self.assertIsNone(hot['foam'])
        self.assertEqual(title, 'Latte đá')
        warm, _ = CB._twist(dict(base, iced=True, foam=None), 'Latte đá', 'rain')
        self.assertFalse(warm['iced'])
        self.assertEqual(warm['foam'], 'thin')
        esp, _ = CB._twist(dict(base, drink='espresso', milk=None, foam=None), 'Espresso', 'exam')
        self.assertEqual(esp['shots'], 2)
        away, _ = CB._twist(base, 'Latte', 'office')
        self.assertTrue(away['takeaway'])
        heat = next(d for d in range(2, 40) if CB.FS.pick_mod(CB.ID, d, CB.MODS)['id'] == 'heat')
        for slot in range(12):
            n = CB.make_task(heat, slot, 1)['needs']
            if n['style'] == 'classic' and n['kind'] == 'drink' and not CB.DRINKS[n['drink']]['hot_only']:
                self.assertTrue(n['iced'])

    def test_mood_order_hidden_until_guessed(self):
        j = self.journey(lambda n: n['kind'] == 'drink', style='mood')
        tid = j.task['id']
        n = j.task['needs']
        j.act('ask', task=tid)
        v = self.view(tid)
        self.assertEqual(set(v['needs']), {'kind', 'style', 'mood', 'takeaway', 'pastry'})
        self.assertEqual(set(v['needs']['mood']), {'text', 'options'})
        self.assertIsNone(v['quoted_price'])
        raw = json.dumps(public_state(j.state), ensure_ascii=False)
        self.assertNotIn(n['note'], raw)
        self.assertNotIn(n['mood']['clue'], raw)
        with self.assertRaises(GameError):
            j.act('cb_cup', task=tid, kind='mug', size='S')
        with self.assertRaises(GameError):
            j.act('cb_guess', task=tid, drink='tea')
        wrong = next(x for x in n['mood']['options'] if x != n['drink'])
        before, money = j.get(tid)['patience'], j.c['money']
        r = j.act('cb_guess', task=tid, drink=wrong)
        self.assertIn(n['mood']['clue'], r['message'])
        self.assertLessEqual(j.get(tid)['patience'], before - 12)
        self.assertEqual(self.view(tid)['needs']['mood']['clue'], n['mood']['clue'])
        with self.assertRaises(GameError):
            j.act('cb_guess', task=tid, drink=wrong)
        j.act('cb_guess', task=tid, drink=n['drink'])
        self.assertTrue(j.get(tid)['guessed'])
        self.assertEqual(j.c['money'], money)   # no tip on the second try
        v = self.view(tid)
        self.assertEqual(v['needs']['drink'], n['drink'])
        self.assertIsNotNone(v['quoted_price'])
        self.cup(tid, n)
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['mood']['score'], 4)
        validate_state(json.loads(json.dumps(j.state)))

    def test_mood_first_pick_earns_a_tip(self):
        j = self.journey(lambda n: n['kind'] == 'drink', style='mood')
        tid, n = j.task['id'], j.task['needs']
        j.act('ask', task=tid)
        n0 = len(self.ledger())
        j.act('cb_guess', task=tid, drink=n['drink'])
        self.assertIn(CB.MOOD_TIP, [e['amount'] for e in self.ledger()[n0:] if e['category'] == 'tip'])
        with self.assertRaises(GameError):
            j.act('cb_guess', task=tid, drink=n['drink'])

    def test_mood_two_misses_and_the_guest_says_it(self):
        j = self.journey(lambda n: n['kind'] == 'drink', style='mood')
        tid, n = j.task['id'], j.task['needs']
        j.act('ask', task=tid)
        wrongs = [x for x in n['mood']['options'] if x != n['drink']]
        j.act('cb_guess', task=tid, drink=wrongs[0])
        r = j.act('cb_guess', task=tid, drink=wrongs[1])
        t = j.get(tid)
        self.assertTrue(t['guessed'])
        self.assertEqual(t['mistakes'], 1)
        self.assertIn(CB.DRINKS[n['drink']]['name'], r['message'])
        self.cup(tid, n)
        j.act('cb_serve', task=tid, confirm=True)
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['mood']['score'], 3)

    def test_tray_cup_by_cup_then_one_serve(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and len(n['party']) == 2 and not any(x['lactose'] or x['decaf'] for x in n['party']), style='tray')
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        self.assertEqual(self.view(tid)['cups_total'], 2)
        self.assertIn('ly 2 là', CB.known_request(j.c, t))
        self.cup(tid, CB._spec(t, 0))
        with self.assertRaises(GameError):
            j.act('cb_serve', task=tid, confirm=True)       # cup 2 is not made yet
        with self.assertRaises(GameError):
            j.act('cb_tab', task=tid, index=1)               # cup 1 is still on the bar
        j.act('cb_done', task=tid)
        t = j.get(tid)
        self.assertEqual(t['cur'], 1)
        self.assertIsNotNone(t['cups'][0])
        self.assertIsNone(t['drink']['container'])
        with self.assertRaises(GameError):
            j.act('cb_done', task=tid)                        # nothing in cup 2 yet
        j.act('cb_tab', task=tid, index=0)                    # take cup 1 back off the tray…
        t = j.get(tid)
        self.assertEqual((t['cur'], t['cups'][0]), (0, None))
        self.assertTrue(t['drink']['container'])
        with self.assertRaises(GameError):
            j.act('cb_tab', task=tid, index=0)
        j.act('cb_done', task=tid)                            # …and put it back
        self.cup(tid, CB._spec(j.get(tid), 1))
        j.act('cb_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(len(t['served']['cups']), 2)
        self.assertEqual(t['quoted_price'], CB.quote(j.c, t['needs']))
        self.assertGreater(t['quoted_price'], CB._drink_price(j.c, t['needs']['party'][0]))
        self.assertEqual(self.review(tid)['feedback'].get('fair', self.review(tid)['stars']), 5)
        validate_state(json.loads(json.dumps(j.state)))

    def test_tray_refused_cup_comes_back(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['party'][0]['lactose'], style='tray')
        tid = j.task['id']
        j.act('ask', task=tid)
        self.cup(tid, dict(CB._spec(j.get(tid), 0), milk=None, art=None))    # a latte without milk: not the drink ordered
        j.act('cb_done', task=tid)
        self.assertEqual(j.get(tid)['cur'], 1)
        self.cup(tid, CB._spec(j.get(tid), 1))
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('ly 1', r['message'])
        t = j.get(tid)
        self.assertEqual(t['cur'], 0)
        self.assertIsNone(t['cups'][0])
        self.assertIsNotNone(t['cups'][1])
        self.assertIsNone(t['drink']['milk'])
        j.act('cb_dump', task=tid, part='drink', confirm=True)
        self.cup(tid, CB._spec(j.get(tid), 0))
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))

    def test_walk_in_buyers_shop_from_the_case(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['lactose'], days=[1])
        case = lambda: sum(l['qty'] for l in j.c['ext']['data']['case'])
        before, n0 = case(), len(self.ledger())
        tid = self.drink()
        j.act('cb_serve', task=tid, confirm=True)
        pl = j.c['ext']['data']['plan']
        self.assertEqual(pl['sales'] + pl['missed'] > 0, True)
        self.assertEqual(case(), before - pl['sales'])
        sold = sum(e['amount'] for e in self.ledger()[n0:] if e['reason'].startswith('Khách mua lẻ'))
        self.assertEqual(sold > 0, pl['sales'] > 0)
        # An empty case turns buyers away.
        j = self.journey(lambda n: n['kind'] == 'drink' and n['lactose'], days=[1])
        tid = self.drink()
        j.c['ext']['data']['case'] = []
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.c['ext']['data']['plan']['missed'], 1)
        self.assertIn('tủ hết bánh mới', r['message'])

    def test_open_surprise_blocks_serving_until_decided(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['lactose'], days=[1])
        tid = self.drink()
        self.open_event('lost_kid')
        with self.assertRaises(GameError):
            j.act('cb_serve', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('cb_event', event='lost_kid', choice='nope')
        r = j.act('cb_event', event='lost_kid', choice='inside')
        self.assertTrue(r['good'])
        j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        pub = public_state(j.state)['careers']['cafe_bakery']['data']['day']
        self.assertIsNone(pub['open_event'])

    def test_every_surprise_choice_resolves(self):
        for spec in CB.EVENTS:
            for choice in spec['choices']:
                j = self.journey(lambda n: n['kind'] == 'drink', days=[3])
                self.open_event(spec['id'])
                pub = public_state(j.state)['careers']['cafe_bakery']['data']['day']['open_event']
                self.assertEqual(pub['id'], spec['id'])
                r = j.act('cb_event', event=spec['id'], choice=choice['id'])
                self.assertTrue(r['message'], (spec['id'], choice['id']))
                self.assertIn(r['good'], (True, False, None))
                validate_state(json.loads(json.dumps(j.state)))

    def test_waiting_surprises_stay_secret(self):
        j = self.journey(lambda n: n['kind'] == 'drink', days=[3])
        pl = CB._plan(j.c)
        pl['events'] = [dict(id='grinder', at=3, status='waiting', choice=None, good=None, note=None)]
        raw = json.dumps(public_state(j.state)['careers']['cafe_bakery']['data'], ensure_ascii=False)
        self.assertNotIn('grinder', raw)
        self.assertNotIn(CB.EVENT_INDEX['grinder']['title'], raw)

    def test_box_order_needs_fresh_croissants(self):
        j = self.journey(lambda n: n['kind'] == 'drink', days=[3])
        self.open_event('box_order')
        j.act('cb_event', event='box_order', choice='half')
        box = CB._plan(j.c)['rules']['box']
        self.assertEqual((box['goal'], box['status']), (3, 'open'))
        j.c['ext']['data']['case'] = [l for l in j.c['ext']['data']['case'] if l['item'] != 'croissant']
        with self.assertRaises(GameError):
            j.act('cb_box_send')
        self.ensure_case(j, 'croissant', 4)
        n0 = len(self.ledger())
        self.assertEqual(j.act('cb_box_send').get('bank'), [3 * box['pay']])   # paid by transfer: bank speaker
        self.assertEqual(sum(e['amount'] for e in self.ledger()[n0:]), 3 * box['pay'])
        self.assertEqual(CB._case_count(j.c['ext']['data'], 'croissant'), 1)
        pl = CB._plan(j.c)
        self.assertEqual(pl['rules']['box']['status'], 'sent')
        self.assertTrue(pl['events'][0]['good'])
        with self.assertRaises(GameError):
            j.act('cb_box_send')
        # Too late: the office cancels.
        pl['rules']['box'] = dict(item='croissant', goal=3, pay=22, due=0, status='open')
        pl['served'] = 1
        CB._after_rules(j.state, j.c, pl, j.task)
        self.assertEqual(pl['rules']['box']['status'], 'failed')

    def test_hot_oven_bakes_sooner(self):
        j = self.j
        CB._plan(j.c)['rules']['hot_oven'] = True
        j.act('cb_bake', item='cookie')
        rack = j.c['ext']['data']['oven'][0]
        self.assertEqual(rack['shift'], CB.HOT_OVEN)
        self.assertEqual(public_state(j.state)['careers']['cafe_bakery']['data']['oven_shift'], CB.HOT_OVEN)
        self.clock.t += 10          # golden on a normal day, but this oven runs hot
        j.act('cb_unload', rack=rack['id'])
        self.assertTrue(any(l['item'] == 'cookie' and l['q'] == 'dark' for l in j.c['ext']['data']['case']))

    def test_sour_milk_kept_spoils_reviews(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] == 'milk' and not n['iced'] and n['art'], days=[1])
        CB._plan(j.c)['rules']['sour_milk'] = True
        tid = self.drink()
        j.act('cb_serve', task=tid, confirm=True)
        post = self.review(tid)
        self.assertLessEqual(post['stars'], 2)
        self.assertIn('chua', {x['key']: x for x in post['feedback']['criteria']}['taste']['note'])

    def test_day_close_grades_and_keeps_bakery_totals(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['lactose'], days=[1])
        tid = self.drink()
        j.act('cb_serve', task=tid, confirm=True)
        summary = j.act('end_day', carry_event=True)['summary']['career']
        self.assertIn(summary['grade']['letter'], ('S', 'A', 'B', 'C', 'D'))
        self.assertEqual(summary['served'], 1)
        for k in ('markdown_sold', 'discarded', 'tomorrow', 'lines'):
            self.assertIn(k, summary)
        validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_upgrades(self):
        # A mood slot saved by the old generator: fixed facts are regenerated once.
        day, slot = find_slot(lambda n: n['kind'] == 'drink', style='mood')
        j = Journey('cafe_bakery', slot=slot, day=day)
        s = copy.deepcopy(j.state)
        c = s['careers']['cafe_bakery']
        t = c['tasks'][0]
        for k in ('gen', 'guest', 'cups', 'cur', 'guessed', 'guesses'):
            t.pop(k)
        t['needs'] = {k: v for k, v in CB.make_task(1, 0, 1)['needs'].items() if k != 'style'}
        t['known'] = True
        for k in ('regulars', 'grades', 'ev_hist', 'counter_sold'):
            c['ext']['data'].pop(k, None)
        validate_state(s)
        t = s['careers']['cafe_bakery']['tasks'][0]
        self.assertEqual(t['gen'], CB.GEN)
        self.assertEqual(t['needs']['style'], 'mood')
        self.assertFalse(t['guessed'])
        self.assertIsNone(public_state(s)['careers']['cafe_bakery']['tasks'][0]['needs'].get('drink'))
        # A plain day-1 ticket keeps the work already done on it.
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=[1])
        j.act('ask')
        j.act('cb_cup', kind='mug', size=j.task['needs']['size'])
        s = copy.deepcopy(j.state)
        t = s['careers']['cafe_bakery']['tasks'][0]
        for k in ('gen', 'guest', 'cups', 'cur', 'guessed', 'guesses'):
            t.pop(k)
        t['needs'].pop('style')
        validate_state(s)
        self.assertEqual(s['careers']['cafe_bakery']['tasks'][0]['drink']['container'], 'mug')

    def test_tampered_tray_and_guesses_rejected(self):
        j = self.journey(lambda n: n['kind'] == 'drink', style='tray')
        for bad in (lambda t: t.update(cups=[None]), lambda t: t.update(cur=5), lambda t: t.update(guesses=['latte']),
                    lambda t: t.update(guessed='yes'), lambda t: t['cups'].__setitem__(0, dict(CB._empty_drink(), container='mug', pulling=5.0))):
            s = copy.deepcopy(j.state)
            bad(s['careers']['cafe_bakery']['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(s)


class CafeConsequenceTests(unittest.TestCase):
    """Làm sai thì phải chịu: slips at the hand-off, the guest's reaction, stars."""
    setUp, tearDown = CafeBakeryTests.setUp, CafeBakeryTests.tearDown
    journey, stock_up, fresh_lot, ensure_case = CafeBakeryTests.journey, CafeBakeryTests.stock_up, CafeBakeryTests.fresh_lot, CafeBakeryTests.ensure_case
    drink, cup, ledger, review = CafeBakeryTests.drink, CafeBakeryTests.cup, CafeBakeryTests.ledger, CafeBakeryTests.review

    def serve_through(self, tid):
        r = self.j.act('cb_serve', task=tid, confirm=True)
        if self.j.get(tid)['status'] != 'completed':
            r = self.j.act('cb_serve', task=tid, confirm=True)
        return r

    def plain(self, extra):
        return lambda n: (n['kind'] == 'drink' and not n['lactose'] and not n['decaf'] and not n['pastry'] and extra(n))

    def made_as(self, pred, change, days=range(1, 8)):
        j = self.journey(self.plain(pred), days)
        tid = j.task['id']
        j.act('ask', task=tid)
        n0 = len(self.ledger())
        self.cup(tid, change(dict(j.get(tid)['needs'])))
        r = self.serve_through(tid)
        t = j.get(tid)
        paid = sum(e['amount'] for e in self.ledger()[n0:] if e['ref'] == tid)
        return j, t, self.review(tid), paid, r

    def test_right_drink_no_slips_full_pay(self):
        j, t, post, paid, _ = self.made_as(lambda n: True, lambda sp: sp, days=[1])
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertGreaterEqual(post['stars'], 4)
        self.assertGreaterEqual(paid, t['quoted_price'])

    def test_small_cup_for_a_large_order_costs(self):
        j, t, post, paid, r = self.made_as(lambda n: n['size'] == 'L', lambda sp: dict(sp, size='S'))
        self.assertEqual(t['status'], 'completed')
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('ly lớn', post['text'])
        self.assertIn(t['reaction']['kind'], ('grumble', 'discount', 'refund', 'walkout'))
        self.assertEqual(paid, t['quoted_price'] - t['reaction']['cut'])
        # Replaying the reaction or the hand-off never moves money again.
        money = j.c['money']
        from game import consequences as cq
        cq.react(j.state, j.c, t, t['quoted_price'])
        with self.assertRaises(GameError):
            j.act('cb_serve', task=t['id'], confirm=True)
        self.assertEqual(j.c['money'], money)
        validate_state(json.loads(json.dumps(j.state)))

    def test_foam_slip_is_smaller_than_a_wrong_size(self):
        flip = lambda f: 'thin' if f == 'thick' else 'thick'
        _, t1, p1, _, _ = self.made_as(lambda n: n['foam'] and n['size'] == 'L' and not n['iced'], lambda sp: dict(sp, foam=flip(sp['foam'])))
        _, t2, p2, _, _ = self.made_as(lambda n: n['foam'] and n['size'] == 'L' and not n['iced'], lambda sp: dict(sp, size='S'))
        self.assertGreater(p1['stars'], p2['stars'])
        self.assertIn('Dặn bọt', p1['text'])

    def test_hot_cup_for_an_iced_order_is_a_mistake_not_a_block(self):
        pred = lambda n: n['iced'] and n['milk'] == 'milk' and not CB.DRINKS[n['drink']]['iced_only']
        j, t, post, paid, r = self.made_as(pred, lambda sp: dict(sp, iced=False, foam='thin'))
        self.assertEqual(t['status'], 'completed')
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('Gọi đồ đá', post['text'])

    def test_cake_in_the_wrong_colour_is_named(self):
        j = self.journey(lambda n: n['kind'] == 'cake')
        tid = j.task['id']
        j.act('ask')
        n = j.task['needs']
        j.act('cb_bake', item='sponge')
        self.clock.t += 20
        j.act('cb_unload', rack=j.c['ext']['data']['oven'][0]['id'])
        j.act('advance')
        j.act('cb_frost', cream=n['cream'], color='mint' if n['color'] != 'mint' else 'blue')
        j.act('cb_write', text=n['text'])
        j.act('cb_box')
        j.act('cb_serve', task=tid, confirm=True)
        post = self.review(tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('Đặt kem màu', post['text'])
        self.assertNotEqual(j.get(tid)['reaction']['kind'], 'remake')
        validate_state(json.loads(json.dumps(j.state)))

    def test_sour_milk_is_a_safety_mistake(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] == 'milk' and not n['iced'] and not n['lactose'] and not n['decaf'], days=[1])
        CB._plan(j.c)['rules']['sour_milk'] = True
        tid = self.drink()
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['reaction']['kind'], 'refuse')
        self.assertEqual(self.review(tid)['stars'], 1)
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        self.assertIn('mùi chua', r['message'])




class CafeCareTests(unittest.TestCase):
    """Care from one day to the next: Bé Men, overnight dough, the morning case, the notes card."""
    setUp, tearDown = CafeBakeryTests.setUp, CafeBakeryTests.tearDown
    journey, stock_up, fresh_lot, ensure_case = CafeBakeryTests.journey, CafeBakeryTests.stock_up, CafeBakeryTests.fresh_lot, CafeBakeryTests.ensure_case
    drink, ledger, review = CafeBakeryTests.drink, CafeBakeryTests.ledger, CafeBakeryTests.review

    def data(self):
        return self.j.c['ext']['data']

    def pub(self):
        return public_state(self.j.state)['careers']['cafe_bakery']['data']

    def next_day(self, feed=False):
        j = self.j
        if feed:
            j.act('cb_feed')
        out = j.act('end_day', carry_event=True)['summary']['career']
        validate_state(json.loads(json.dumps(j.state)))
        j.act('start_day')
        self.stock_up(j)
        return out

    def test_starter_is_fed_once_a_day_and_changes_overnight(self):
        j = self.j
        self.stock_up(j)
        st = self.data()['starter']
        self.assertEqual((st['strength'], st['fed']), (CB.STARTER_START, 0))
        flour = kit.stock(j.c, 'flour')
        r = j.act('cb_feed')
        self.assertIn('70% → 90%', r['message'])
        self.assertEqual(kit.stock(j.c, 'flour'), flour - 1)
        with self.assertRaises(GameError):
            j.act('cb_feed')
        out = self.next_day()
        self.assertEqual(self.data()['starter']['strength'], 85)
        self.assertIn('85%', ' '.join(out['care']['lines']))
        for want in (60, 35, 10, 10):            # unfed nights: −25 each, never below 10
            self.next_day()
            self.assertEqual(self.data()['starter']['strength'], want)
        j.act('cb_feed')                          # a hungry starter eats more: back to "ổn" the same day
        self.assertEqual(self.data()['starter']['strength'], 40)
        self.assertEqual(self.pub()['starter']['band'], 'ok')

    def test_starter_strength_sets_bread_proofing_and_density(self):
        j = self.j
        self.stock_up(j)
        d = self.data()
        d['starter']['strength'] = 90
        j.act('cb_shape', item='banhmi')
        tray = self.data()['proof'][-1]
        self.assertEqual(tray['ready'] - tray['since'], 2)
        self.assertFalse(tray['dense'])
        self.data()['starter']['strength'] = 20
        j.act('cb_shape', item='croissant')          # croissants use yeast, not Bé Men
        self.assertEqual(self.data()['proof'][-1]['ready'] - self.data()['proof'][-1]['since'], CB.PROOF_TURNS)
        j.act('cb_bake', item='banhmi')
        self.clock.t += 14
        j.act('cb_unload', rack=self.data()['oven'][0]['id'])
        j.act('advance')
        j.act('cb_bake', item='croissant')
        self.clock.t += 17
        j.act('cb_unload', rack=self.data()['oven'][0]['id'])
        self.data()['proof'] = []
        r = j.act('cb_shape', item='banhmi')
        self.assertIn('Bé Men đói (20%)', r['message'])
        tray = self.data()['proof'][-1]
        self.assertTrue(tray['dense'])
        self.assertEqual(tray['ready'] - tray['since'], 5)
        for _ in range(4):
            j.act('advance')
        j.act('cb_bake', item='banhmi')
        self.clock.t += 14
        r = j.act('cb_unload', rack=self.data()['oven'][0]['id'])
        self.assertIn('đặc ruột', r['message'])
        self.assertTrue(any(l['item'] == 'banhmi' and l['q'] == 'dense' for l in self.data()['case']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_dense_bread_is_named_in_the_review(self):
        j = self.journey(lambda n: n['kind'] == 'pastry' and 'banhmi' in n['items'] and not n['day_old_ok'] and not n['allergy'], days=[1])
        d = j.c['ext']['data']
        d['case'] = [dict(id='dense-1', item='banhmi', qty=6, day=j.c['day'], q='dense', sale=False, cost=1)]
        tid = j.task['id']
        j.act('ask')
        for item, q in j.task['needs']['items'].items():
            if item != 'banhmi':
                self.ensure_case(j, item)
            for _ in range(q):
                j.act('cb_pick', lot=self.fresh_lot(j, item)['id'])
        j.act('cb_bag')
        j.act('cb_serve', confirm=True)
        if j.get(tid)['status'] != 'completed':      # the guest may hand it back once
            j.act('cb_bag')
            j.act('cb_serve', confirm=True)
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['fresh']['score'], 3)
        self.assertIn('đặc ruột', crit['fresh']['note'])

    def test_dough_chilled_overnight_bakes_next_morning_and_warm_dough_spoils(self):
        j = self.j
        self.stock_up(j)
        j.act('cb_shape', item='banhmi')
        j.act('cb_shape', item='croissant')
        chilled = self.data()['proof'][0]['id']
        j.act('cb_chill', tray=chilled)
        self.assertEqual([x['id'] for x in self.data()['cold']], [chilled])
        with self.assertRaises(GameError):          # it needs the night
            j.act('cb_bake', item='banhmi', tray=chilled)
        with self.assertRaisesRegex(GameError, 'qua một đêm'):
            j.act('cb_bake', item='banhmi')
        with self.assertRaises(GameError):
            j.act('cb_chill', tray='nope')
        rows = {r['icon']: r for r in self.pub()['care']}
        self.assertEqual(rows['🌡️']['tone'], 'warn')        # warm croissant dough left
        waste = len(j.c['life']['waste'])
        out = self.next_day()
        self.assertEqual(self.data()['proof'], [])         # the warm tray spoiled overnight
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertTrue(any('ủ ấm' in l for l in out['care']['lines']))
        self.assertTrue(any('ủ ấm' in l for l in self.pub()['night']))
        cold = self.pub()['cold'][0]
        self.assertTrue(cold['bakeable'])
        before = CB._case_count(self.data(), 'banhmi')
        r = j.act('cb_bake', item='banhmi')                 # straight in, no proofing wait
        self.assertIn('ủ lạnh', r['message'])
        self.assertEqual(self.data()['cold'], [])
        self.clock.t += 14
        j.act('cb_unload', rack=self.data()['oven'][0]['id'])
        self.assertEqual(CB._case_count(self.data(), 'banhmi'), before + 6)
        self.assertTrue(any(l['item'] == 'banhmi' and l['q'] == 'golden' and l['day'] == j.c['day'] for l in self.data()['case']))

    def test_fridge_has_two_shelves_and_old_cold_dough_spoils(self):
        j = self.j
        self.stock_up(j)
        for item in ('banhmi', 'croissant'):
            j.act('cb_shape', item=item)
            j.act('cb_chill', tray=self.data()['proof'][0]['id'])
        j.act('cb_shape', item='banhmi')
        with self.assertRaises(GameError):
            j.act('cb_chill', tray=self.data()['proof'][0]['id'])
        self.next_day()
        self.assertEqual(len(self.data()['cold']), 2)
        self.assertFalse(any(x['last'] for x in self.pub()['cold']))
        self.next_day()
        self.assertEqual(len(self.data()['cold']), 2)
        self.assertTrue(all(x['last'] and x['nights'] == 2 for x in self.pub()['cold']))
        self.assertTrue(any(r['icon'] == '❄️' and r['tone'] == 'warn' for r in self.pub()['care']))
        out = self.next_day()
        self.assertEqual(self.data()['cold'], [])
        self.assertTrue(any('2 đêm' in l for l in out['care']['lines']))

    def test_morning_care_list_names_yesterdays_pastries_and_tomorrow(self):
        j = self.j
        self.stock_up(j)
        self.next_day(feed=True)
        rows = self.pub()['care']
        self.assertTrue(any(r['icon'] == '🧺' and r['ok'] is None for r in rows))   # the 5 a.m. bake is day-old now
        fed = next(r for r in rows if r['icon'] == '🫙')
        self.assertIsNone(fed['ok'])
        j.act('cb_feed')
        self.assertTrue(next(r for r in self.pub()['care'] if r['icon'] == '🫙')['ok'])
        for lot in [l for l in self.data()['case'] if CB.lot_state(j.c, l['item'], l['day']) == 'day_old']:
            j.act('cb_markdown', lot=lot['id'])
        self.assertTrue(next(r for r in self.pub()['care'] if r['icon'] == '🧺')['ok'])
        # Tomorrow's luck is fixed: a busy day asks for dough chilled tonight.
        busy = next(day for day in range(2, 40) if CB.FS.pick_mod(CB.ID, day + 1, CB.MODS).get('buyers', 1) >= 2)
        j.c['day'] = busy
        self.data()['starter']['fed'] = 0
        rows = self.pub()['care']
        self.assertTrue(self.pub()['tomorrow']['busy'])
        self.assertTrue(any('ủ lạnh sẵn' in r['label'] and r['ok'] is None for r in rows))

    def test_notes_card_learns_visit_by_visit_and_greeting_helps(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and not n['iced'] and n['milk'] == 'milk', days=[1])
        npc = j.task['npc']
        i = CB._npc_index(npc)
        raw = json.dumps(public_state(j.state), ensure_ascii=False)
        self.assertNotIn(CB.NOTES[i][0]['text'], raw)                 # unlearned notes never leave the server
        with self.assertRaises(GameError):
            j.act('cb_greet')
        tid = self.drink()
        r = j.act('cb_serve', task=tid, confirm=True)
        self.assertIn('Sổ khách quen', r['message'])
        self.assertEqual(self.data()['book'][npc], dict(visits=1, notes=[CB.NOTES[i][0]['id']]))
        book = self.pub()['book']
        self.assertEqual(book[0]['next'], 2)
        self.assertNotIn(CB.NOTES[i][1]['text'], json.dumps(public_state(j.state), ensure_ascii=False))
        self.data()['book'][npc]['visits'] = 3
        with self.assertRaises(GameError):                             # notes must match the visits
            validate_state(json.loads(json.dumps(j.state)))
        self.data()['book'][npc]['notes'] = CB._learned(i, 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_greeting_a_regular_adds_patience_and_a_review_row(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and not n['iced'] and n['milk'] == 'milk', days=[1])
        t = j.task
        i = CB._npc_index(t['npc'])
        self.data()['book'][t['npc']] = dict(visits=1, notes=CB._learned(i, 1))
        t.pop('regular')
        CB.on_task(j.state, j.c, t)
        self.assertEqual(t['regular'], 1)
        t['patience'] = 80
        r = j.act('cb_greet')
        self.assertIn(CB.NOTES[i][0]['text'], r['message'])
        self.assertEqual(j.task['patience'], 88)
        with self.assertRaises(GameError):
            j.act('cb_greet')
        tid = self.drink()
        j.act('cb_serve', task=tid, confirm=True)
        crit = {x['key']: x for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['regular']['score'], 5)
        self.assertEqual(self.data()['book'][t['npc']]['visits'], 2)

    def test_baker_feeds_the_starter_first(self):
        j = self.j
        self.stock_up(j)
        note = CB.assist(j.state, j.c, dict(role='baker', name='Hậu'), None)
        self.assertIn('Bé Men', note)
        self.assertEqual(self.data()['starter']['fed'], j.c['day'])
        note = CB.assist(j.state, j.c, dict(role='baker', name='Hậu'), None)
        self.assertNotIn('Bé Men', note)

    def test_old_save_without_care_data_loads(self):
        s = copy.deepcopy(self.j.state)
        c = s['careers']['cafe_bakery']
        for k in ('starter', 'cold', 'book', 'night'):
            c['ext']['data'].pop(k)
        for t in c['tasks']:
            t.pop('regular', None)
            t.pop('greeted', None)
        c['ext']['data']['proof'] = [dict(id='pf-old', item='banhmi', qty=6, since=1, ready=4, cost=2)]
        public_state(s)                              # the projection copes before migration
        validate_state(s)
        d = s['careers']['cafe_bakery']['ext']['data']
        self.assertEqual(d['starter']['strength'], CB.STARTER_START)
        self.assertEqual((d['cold'], d['book']), ([], {}))
        self.assertFalse(d['proof'][0]['dense'])

    def test_tampered_care_data_is_rejected(self):
        self.j.act('cb_shape', item='banhmi')
        self.j.act('cb_chill', tray=self.data()['proof'][0]['id'])
        npc = CB.kit.npc_id(CB.ID, 0)
        mutations = (
            lambda d, t: d['starter'].__setitem__('strength', 150),
            lambda d, t: d['starter'].__setitem__('strength', 3),
            lambda d, t: d['starter'].__setitem__('fed', 99),
            lambda d, t: d['starter'].__setitem__('extra', 1),
            lambda d, t: d['cold'].append(dict(d['cold'][0], id='x2')) or d['cold'].append(dict(d['cold'][0], id='x3')),
            lambda d, t: d['cold'][0].__setitem__('item', 'cookie'),
            lambda d, t: d['cold'][0].__setitem__('day', 99),
            lambda d, t: d['cold'][0].__setitem__('dense', 'yes'),
            lambda d, t: d['book'].__setitem__('stranger', dict(visits=1, notes=[])),
            lambda d, t: d['book'].__setitem__(npc, dict(visits=0, notes=['lam_shot'])),
            lambda d, t: d['book'].__setitem__(npc, dict(visits=5, notes=['thao_oat'])),
            lambda d, t: d.__setitem__('night', dict(day=1, lines=['x'] * 9)),
            lambda d, t: t.__setitem__('greeted', True),
            lambda d, t: t.__setitem__('regular', 7),
        )
        for mutate in mutations:
            state = json.loads(json.dumps(self.j.state))
            c = state['careers']['cafe_bakery']
            mutate(c['ext']['data'], c['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(state)

    def test_several_days_of_care(self):
        """Feed, shape, chill, close and bake again over four shifts: all of it carries over and stays valid."""
        j = self.j
        self.stock_up(j)
        for day in range(4):
            if day:
                self.assertEqual(len(self.data()['cold']), 1)
                j.act('cb_bake', item='banhmi')
                self.clock.t += 14
                j.act('cb_unload', rack=self.data()['oven'][0]['id'])
            j.act('cb_feed')
            j.act('cb_shape', item='banhmi')
            self.assertEqual(self.data()['proof'][0]['ready'] - self.data()['proof'][0]['since'], 2)   # fed: 💪 sung sức
            j.act('cb_chill', tray=self.data()['proof'][0]['id'])
            out = self.next_day()
            self.assertGreaterEqual(self.data()['starter']['strength'], 85)
            self.assertEqual(out['care']['dough_lost'], 0)
        self.assertEqual(self.data()['starter']['feeds'], 4)

if __name__ == '__main__':
    unittest.main()
