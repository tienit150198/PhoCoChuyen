import copy
import json
import unittest

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import restaurant as R
from game.careers import food_service as FS
from tests.helpers import Journey
from game import consequences as cq


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def unlocked(c, item):
    return R.ITEM_INDEX[item].get('unlock', 1) <= kit.level(c)


class Kitchen:
    """Plays the kitchen like a careful cook (used by several tests)."""

    def __init__(self, test, j):
        self.test, self.j = test, j

    @property
    def clock(self):
        return self.test.clock

    def stock_up(self, item, qty):
        c = self.j.c
        if kit.stock(c, item) < qty:
            inventory.add_lot(c, item, qty + 2, 1, 3, 'partner')

    def plan_bowl(self, t, i=0):
        c, n = self.j.c, t['needs']
        if n['style'] != 'open':
            n = R._spec(t, i)
            tops = {}
            for k, q in n['toppings'].items():
                k = t['subs'].get(k, k)
                tops[k] = tops.get(k, 0) + q
            return n['broth'], tops, n['spice'], 2 if n['extra_noodle'] else 1
        o = n['open']
        bad = lambda k: (k in o['avoid'] or (o['veg'] and k in R.MEAT)
                         or (n['allergy'] and R.ITEM_INDEX[k].get('allergen') == n['allergy']) or not unlocked(c, k))
        broths = [b for b in (o['broths'] or ['kimchi', 'blackbean', 'tomyum']) if R.BROTH_INDEX[b]['unlock'] <= kit.level(c)
                  and not (R.BROTH_INDEX[b].get('allergen') and (o['veg'] or n['allergy']))]
        tops = {k: 1 for k in o['must'] if not bad(k)}
        pool = sorted((k for k in R.TOPPINGS if not bad(k) and k not in tops), key=lambda k: R.ITEM_INDEX[k]['price'])
        while sum(tops.values()) < o['min_tops'] and pool:
            tops[pool.pop(0)] = 1
        return broths[0], tops, o['spice'][0], 1

    def cook(self, tid=None, boil=10, broth=None, skip_lid=False, serve=False):
        j = self.j
        t = j.get(tid) if tid else j.task
        tid = t['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        if t['needs']['style'] == 'usual' and not t['recalled']:
            j.act('rs_recall' if t['npc'] in j.c['ext']['data']['notebook'] else 'rs_reask', task=tid)
            t = j.get(tid)
        n = t['needs']
        if n['style'] != 'open':
            for sp in R._specs(n):
                for k, q in sp['toppings'].items():
                    if not unlocked(j.c, k) and k not in t['subs']:
                        sub = next(x for x in ('egg', 'mushroom', 'kimchi_side') if x != k)
                        self.stock_up(sub, 4)
                        j.act('rs_sub', task=tid, item=k, substitute=sub)
                        t = j.get(tid)
            t = j.get(tid)
        total = len(R._specs(n))
        for i in range(total):
            want_broth, tops, spice, noodles = self.plan_bowl(t, i)
            for k, q in tops.items():
                self.stock_up(k, q)
            for k in ('noodle', 'box', 'chili'):
                self.stock_up(k, 6)
            pl = R._plan(j.c)
            b = broth or want_broth
            self.ready_pot(b, R._portions(pl))
            if pl['rules'].get('dirty', 0) >= R.DIRTY_MAX:
                j.act('rs_wash')
            j.act('rs_container', task=tid, kind='box' if n['takeaway'] else 'bowl')
            shift = R.WEAK_FIRE if pl['rules'].get('weak_fire') else 0
            for _ in range(noodles):
                j.act('rs_boil', task=tid)
                self.clock.t += boil + shift
                j.act('rs_drain', task=tid)
            j.act('rs_broth', task=tid, broth=b)
            for k, q in tops.items():
                for _ in range(q):
                    j.act('rs_topping', task=tid, item=k)
            for _ in range(spice):
                j.act('rs_chili', task=tid)
            if n['takeaway'] and not skip_lid:
                j.act('rs_lid', task=tid)
            if i < total - 1:
                j.act('rs_plate', task=tid)
        if serve:
            return j.act('rs_serve', task=tid, confirm=True)
        return tid

    def ready_pot(self, b, portions=1):
        """A careful cook: pour out an expired pot, reheat a cold one, top up an empty one."""
        j = self.j
        if R._pot_state(j.c['ext']['data'], b) == 'stale':
            j.act('rs_toss', broth=b, confirm=True)
        d = j.c['ext']['data']
        if d['pots'][b] < portions:
            d['pots'][b] = R.POT_MAX
            d['pot_lots'][b] = [[R.POT_MAX, 0]]
            d['pot_warm'][b] = True
        if R._pot_state(d, b) == 'cold':
            j.act('rs_reheat')

    def resolve_open_event(self, pick=0):
        pl = R._plan(self.j.c)
        e = FS.open_event(pl)
        if not e:
            return None
        spec = R.EVENT_INDEX[e['id']]
        choices = [x for x in spec['choices'] if FS.choice_ok(None, self.j.c, pl, spec, x) is None]
        return self.j.act('rs_event', event=e['id'], choice=choices[min(pick, len(choices) - 1)]['id'])

    def play_day(self, max_orders=8):
        j = self.j
        if not j.c['open']:
            j.act('start_day')
        served = 0
        while served < max_orders:
            self.resolve_open_event()
            b = R._plan(j.c)['rules'].get('batch')
            while isinstance(b, dict) and b['status'] == 'open':
                for k in ('noodle', 'box', 'chili'):
                    self.stock_up(k, 6)
                self.ready_pot(b['broth'], R.POT_MAX)
                j.act('rs_batch')
                b = R._plan(j.c)['rules']['batch']
            todo = [t for t in j.c['tasks'] if t['status'] not in FS.DONE]
            if not todo:
                break
            self.cook(todo[0]['id'], serve=True)
            served += 1
        self.resolve_open_event()
        return j.act('end_day')


class RestaurantTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('restaurant')
        self.k = Kitchen(self, self.j)

    def tearDown(self):
        kit.clock = self.old

    def cook(self, tid=None, boil=10, broth=None, skip_lid=False):
        return self.k.cook(tid, boil, broth, skip_lid)

    def force_event(self, eid, j=None):
        j = j or self.j
        pl = R._plan(j.c)
        pl['events'] = [dict(id=eid, at=0, status='waiting', choice=None, good=None, note=None)]
        FS.trigger(j.state, j.c, pl, R.EVENT_INDEX)
        self.assertEqual(FS.open_event(pl)['id'], eid)
        return pl

    def at_day(self, day, style=None, pred=None):
        for d in range(day, day + 30):
            for slot in range(1, 12):
                t = R.make_task(d, slot, 1)
                if (style is None or t['needs']['style'] == style) and (pred is None or pred(t)):
                    j = Journey('restaurant', slot=slot, day=d)
                    self.j, self.k.j = j, j
                    return j
        self.fail('no such order')

    # ---------------------------------------------------------------- basics
    def test_happy_path_review_and_money(self):
        j = self.j
        money = j.c['money']
        tid = self.cook()
        price = j.get(tid)['quoted_price']
        j.act('rs_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(j.c['money'], money + price + (4 if t['guest']['kind'] == 'generous' else 0)
                         + (3 if t['guest']['kind'] == 'rush' else 0))
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual(post['stars'], 5)
        self.assertIn('feedback', post)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'taste', 'accuracy', 'speed', 'presentation'})
        validate_state(json.loads(json.dumps(j.state)))

    def test_needs_hidden_until_ask(self):
        view = public_state(self.j.state)['careers']['restaurant']['tasks'][0]
        self.assertIsNone(view['needs'])
        with self.assertRaises(GameError):
            self.j.act('rs_container', kind='bowl')

    def test_day_one_is_classic_and_gentle(self):
        for slot in range(12):
            self.assertEqual(R.make_task(1, slot, 1)['needs']['style'], 'classic')
        self.assertEqual(FS.pick_mod('restaurant', 1, R.MODS)['id'], 'normal')
        pl = R._plan(self.j.c)
        self.assertLessEqual(len(pl['events']), 1)
        self.assertTrue(all(R.EVENT_INDEX[e['id']].get('gentle') for e in pl['events']))

    def test_noodle_doneness_by_real_seconds(self):
        j = self.j
        j.act('ask')
        j.act('rs_container', kind='box' if j.task['needs']['takeaway'] else 'bowl')
        j.act('rs_boil')
        self.clock.t += 3
        j.act('rs_drain')
        self.assertEqual(j.task['bowl']['noodles'], ['raw'])
        self.assertEqual(j.task['mistakes'], 1)

    def test_mushy_noodles_lower_taste(self):
        tid = self.cook(boil=30)
        self.serve_through(tid)
        post = next(p for p in self.j.c['feed'] if p['kind'] == 'review')
        taste = next(x for x in post['feedback']['criteria'] if x['key'] == 'taste')
        self.assertEqual(taste['score'], 2)
        self.assertLess(post['stars'], 5)

    def test_wrong_broth_refused_then_dump(self):
        j = self.j
        j.act('ask')
        other = next(b for b in ('kimchi', 'tomyum', 'blackbean') if b != j.task['needs']['broth'] and not (j.task['needs']['allergy'] and b == 'tomyum'))
        tid = self.cook(broth=other)
        r = j.act('rs_serve', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(R._plan(j.c)['refused'], 1)
        waste = len(j.c['life']['waste'])
        j.act('rs_dump', task=tid, confirm=True)
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertIsNone(j.get(tid)['bowl']['container'])
        validate_state(j.state)

    def serve_through(self, tid):
        """Serve; if the guest sends the bowl back (a slip), hand it over again as is."""
        r = self.j.act('rs_serve', task=tid, confirm=True)
        if self.j.get(tid)['status'] != 'completed':
            r = self.j.act('rs_serve', task=tid, confirm=True)
        return r

    def test_allergy_reaches_guest_is_safety_mistake(self):
        j = self.at_day(1, 'classic', lambda t: t['needs']['allergy'])
        for item in ('noodle', 'fishball', 'box', 'chili'):
            inventory.add_lot(j.c, item, 5, 1, 3, 'partner')
        j.act('ask')
        n = j.task['needs']
        j.act('rs_container', kind='box' if n['takeaway'] else 'bowl')
        j.act('rs_boil')
        self.clock.t += 10
        j.act('rs_drain')
        j.act('rs_broth', broth=n['broth'])
        j.act('rs_topping', item='fishball')
        if n['takeaway']:
            j.act('rs_lid')
        money = j.c['money']
        tid = j.task['id']
        r = j.act('rs_serve', confirm=True)
        # Behaviour change: the allergen reaches the guest -> safety slip, 1 star, no pay, report, inspection.
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn('dị ứng', r['message'])
        self.assertEqual(j.c['money'], money)
        post = next(p for p in j.c['feed'] if p.get('source') == tid and p['kind'] == 'review')
        self.assertEqual(post['stars'], 1)
        self.assertIn('dị ứng hải sản', post['text'])
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_stock_decrements_and_runs_out(self):
        j = self.j
        before = kit.stock(j.c, 'noodle')
        j.act('ask')
        j.act('rs_container', kind='bowl')
        j.act('rs_boil')
        self.assertEqual(kit.stock(j.c, 'noodle'), before - 1)
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == 'egg':
                lot['qty'] = 0
        with self.assertRaises(GameError):
            j.act('rs_topping', item='egg')

    def test_two_baskets_limit(self):
        j = self.j
        ids = [t['id'] for t in j.c['tasks']][:3]
        for tid in ids[:2]:
            j.act('ask', task=tid)
            j.act('rs_container', task=tid, kind='box')
            j.act('rs_boil', task=tid)
        j.act('ask', task=ids[2])
        j.act('rs_container', task=ids[2], kind='box')
        with self.assertRaises(GameError):
            j.act('rs_boil', task=ids[2])

    def test_takeaway_needs_lid(self):
        j = self.at_day(1, 'classic', lambda t: t['needs']['takeaway'])
        tid = self.cook(skip_lid=True)
        with self.assertRaises(GameError):
            j.act('rs_serve', task=tid, confirm=True)

    def test_pot_runs_out_and_refills_from_pack(self):
        j = self.j
        j.c['ext']['data']['pots']['kimchi'] = 0
        j.act('ask')
        j.act('rs_container', kind='bowl')
        with self.assertRaises(GameError):
            j.act('rs_broth', broth='kimchi')
        packs = kit.stock(j.c, 'pack_kimchi')
        j.act('rs_pot', broth='kimchi')
        self.assertEqual(j.c['ext']['data']['pots']['kimchi'], R.POT_BATCH)
        self.assertEqual(kit.stock(j.c, 'pack_kimchi'), packs - 1)

    def test_tampered_needs_rejected(self):
        s = copy.deepcopy(self.j.state)
        t = s['careers']['restaurant']['tasks'][0]
        t['needs']['spice'] = 0 if t['needs']['spice'] else 3
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(self.j.state)
        s['careers']['restaurant']['tasks'][0]['guest']['kind'] = 'generous'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_substitute_when_out_of_stock(self):
        j = self.j
        j.act('ask')
        n = j.task['needs']
        item = next(iter(n['toppings']))
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == item:
                lot['qty'] = 0
        sub = next(x for x in ('mushroom', 'egg', 'sausage') if x != item)
        j.act('rs_sub', item=item, substitute=sub)
        self.assertEqual(j.task['subs'][item], sub)
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = self.j
        for x in R.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_reply_thread_scripted_resolution(self):
        j = self.j
        tid = self.cook(boil=30)
        self.serve_through(tid)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        j.act('fb_reply', post=post['id'], text='Xin lỗi anh, lần sau quán sẽ canh giờ luộc mì kỹ hơn ạ.', offer='gift')
        with self.assertRaises(GameError):
            j.act('fb_resolve', post=post['id'])
        j.act('advance')
        j.act('advance')
        post = next(p for p in j.c['feed'] if p['id'] == post['id'])
        self.assertEqual(post['feedback']['thread'][-1]['role'], 'customer')
        self.assertGreaterEqual(post['stars'], post['feedback']['stars_original'])
        validate_state(j.state)

    # ------------------------------------------------------ luck of the day
    def test_modifier_is_deterministic_and_stored(self):
        for day in range(1, 40):
            a = FS.pick_mod('restaurant', day, R.MODS)['id']
            self.assertEqual(a, FS.pick_mod('restaurant', day, R.MODS)['id'])
            self.assertTrue(all(m['id'] != a or m.get('min_day', 1) <= day for m in R.MODS))
        seen = {FS.pick_mod('restaurant', d, R.MODS)['id'] for d in range(2, 60)}
        self.assertGreaterEqual(len(seen), 6)
        repeats = sum(FS.pick_mod('restaurant', d, R.MODS)['id'] == FS.pick_mod('restaurant', d + 1, R.MODS)['id'] for d in range(3, 60))
        self.assertLess(repeats, 8)
        pl = copy.deepcopy(R._plan(self.j.c))
        self.j.act('rs_clean')
        self.assertEqual(R._plan(self.j.c)['events'], pl['events'])
        self.assertEqual(R.FS.new_plan('restaurant', 5, R.MODS, R.EVENTS), R.FS.new_plan('restaurant', 5, R.MODS, R.EVENTS))

    def test_order_styles_vary_with_days(self):
        styles = {R.make_task(d, s, 1)['needs']['style'] for d in range(2, 16) for s in range(1, 6)}
        self.assertEqual(styles, {'classic', 'usual', 'open', 'picture', 'group'})
        kinds = {R.make_task(d, s, 1)['guest']['kind'] for d in range(1, 16) for s in range(0, 6)}
        self.assertGreaterEqual(len(kinds), 6)
        for d in range(1, 30):
            for s in range(12):
                t = R.make_task(d, s, 1)
                self.assertEqual(t, R.make_task(d, s, 1))
                if t['needs']['style'] == 'open':
                    self.assertLessEqual(t['needs']['open']['must'] and max(R.ITEM_INDEX[k].get('unlock', 1) for k in t['needs']['open']['must']) or 1, R._level_hint(d))

    def test_cold_day_takes_two_portions(self):
        day = next(d for d in range(3, 80) if FS.pick_mod('restaurant', d, R.MODS)['id'] == 'cold')
        j = self.at_day(day, 'classic')
        self.assertEqual(j.c['day'], j.task['day'])
        if FS.pick_mod('restaurant', j.c['day'], R.MODS)['id'] != 'cold':
            j = Journey('restaurant', slot=0, day=day)
            self.j = self.k.j = j
        before = dict(j.c['ext']['data']['pots'])
        self.cook()
        b = j.task['bowl']['broth']
        self.assertEqual(j.c['ext']['data']['pots'][b], before[b] - 2)

    def test_festival_raises_prices(self):
        day = next(d for d in range(5, 80) if FS.pick_mod('restaurant', d, R.MODS)['id'] == 'festival')
        j = Journey('restaurant', slot=0, day=day)
        t = j.task
        normal = R.SPEC['prices'][t['needs']['broth']] + sum(R.ITEM_INDEX[k]['price'] * q for k, q in t['needs']['toppings'].items()) \
            + (10 if t['needs']['extra_noodle'] else 0) + (3 if t['needs']['takeaway'] else 0)
        self.assertEqual(t['quoted_price'], round(normal * 1.1))

    # ------------------------------------------------------ order styles
    def test_usual_order_is_masked_until_recalled(self):
        j = self.at_day(2, 'usual')
        tid = j.task['id']
        j.act('ask')
        view = next(v for v in public_state(j.state)['careers']['restaurant']['tasks'] if v['id'] == tid)
        self.assertEqual(set(view['needs']), {'style', 'masked', 'takeaway'})
        self.assertNotIn('sausage', json.dumps(j.c['journal'][-3:], ensure_ascii=False) if j.task['needs']['toppings'].get('sausage') else '')
        with self.assertRaises(GameError):
            j.act('rs_recall')
        before = j.task['patience']
        j.act('rs_reask')
        self.assertTrue(j.task['recalled'] and j.task['reasked'])
        self.assertEqual(j.task['patience'], before - 15)
        self.assertIn(j.task['npc'], j.c['ext']['data']['notebook'])
        view = next(v for v in public_state(j.state)['careers']['restaurant']['tasks'] if v['id'] == tid)
        self.assertIn('broth', view['needs'])
        self.cook(tid)
        j.act('rs_serve', task=tid, confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertIn('care', {x['key'] for x in post['feedback']['criteria']})
        # Next time the notebook answers for free.
        npc = j.get(tid)['npc']
        for d in range(j.c['day'] + 1, j.c['day'] + 40):
            other = next((R.make_task(d, s, 1) for s in range(1, 12) if R.make_task(d, s, 1)['needs']['style'] == 'usual' and R.make_task(d, s, 1)['npc'] == npc), None)
            if other:
                break
        c = j.c
        c['tasks'].append(other)
        R.on_task(j.state, c, other)
        j.act('ask', task=other['id'])
        before = j.get(other['id'])['patience']
        j.act('rs_recall', task=other['id'])
        self.assertTrue(j.get(other['id'])['recalled'])
        self.assertEqual(j.get(other['id'])['patience'], before)

    def test_regular_story_moves_on(self):
        j = self.at_day(2, 'usual')
        t = j.task
        self.assertEqual(t['story'], R.REGULAR_STORY[R._npc_index(t)][0])
        self.cook(t['id'])
        j.act('rs_serve', task=t['id'], confirm=True)
        self.assertEqual(j.c['ext']['data']['regulars'][t['npc']], 1)
        nxt = R.make_task(t['day'], 11, 1)
        nxt.update(npc=t['npc'], guest=FS.guest('regular'))
        R.on_task(j.state, j.c, nxt)
        self.assertEqual(nxt['story'], R.REGULAR_STORY[R._npc_index(t)][1])

    def test_open_order_pays_what_is_in_the_bowl(self):
        j = self.at_day(3, 'open', lambda t: not t['needs']['open']['veg'] and t['guest']['kind'] != 'kid')
        tid = j.task['id']
        money = j.c['money']
        self.cook(tid)
        t = j.get(tid)
        price = R.bowl_price(j.c, t['bowl'])
        self.assertLessEqual(price, t['needs']['open']['budget'])
        j.act('rs_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['quoted_price'], price)
        self.assertFalse(t['over_budget'])
        self.assertGreaterEqual(j.c['money'], money + price)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        value = next(x for x in post['feedback']['criteria'] if x['key'] == 'value')
        self.assertEqual(value['score'], 5)

    def test_open_order_over_budget_pays_only_budget(self):
        j = self.at_day(3, 'open', lambda t: not t['needs']['open']['veg'] and not t['needs']['open']['avoid'] and t['guest']['kind'] != 'kid')
        tid = j.task['id']
        j.act('ask')
        broth, tops, spice, _ = self.k.plan_bowl(j.task)
        tops = dict(tops)
        tops['beef'] = 3
        for k, q in list(tops.items()) + [('noodle', 2), ('box', 2), ('chili', 8)]:
            self.k.stock_up(k, q)
        j.act('rs_container', kind='box' if j.task['needs']['takeaway'] else 'bowl')
        j.act('rs_boil')
        self.clock.t += 10
        j.act('rs_drain')
        j.act('rs_broth', broth=broth)
        for k, q in tops.items():
            for _ in range(q):
                j.act('rs_topping', item=k)
        for _ in range(spice):
            j.act('rs_chili')
        if j.task['needs']['takeaway']:
            j.act('rs_lid')
        budget = j.task['needs']['open']['budget']
        self.assertGreater(R.bowl_price(j.c, j.task['bowl']), budget)
        j.act('rs_serve', confirm=True, task=tid)
        t = j.get(tid)
        self.assertTrue(t['over_budget'])
        self.assertEqual(t['quoted_price'], budget)

    def test_vegetarian_bowl_with_meat_is_refused(self):
        j = self.at_day(3, 'open', lambda t: t['needs']['open']['veg'])
        j.act('ask')
        for k in ('sausage', 'noodle', 'chili'):
            self.k.stock_up(k, 2)
        j.act('rs_container', kind='bowl')
        j.act('rs_boil')
        self.clock.t += 10
        j.act('rs_drain')
        j.act('rs_broth', broth='blackbean')
        j.act('rs_topping', item='sausage')
        self.assertEqual(j.task['mistakes'], 1)
        r = j.act('rs_serve', confirm=True)
        self.assertTrue(r['refused'])
        self.assertIn('chay', r['message'])

    def test_kid_refuses_spicy_bowl(self):
        j = self.at_day(1, 'classic', lambda t: t['guest']['kind'] == 'kid')
        n = j.task['needs']
        self.cook()
        j.act('rs_chili', task=j.task['id'])
        r = j.act('rs_serve', task=j.task['id'], confirm=True)
        self.assertTrue(r['refused'])
        self.assertIn('cay', r['message'])
        self.assertGreater(j.task['bowl']['chili'], n['spice'])

    def test_picture_order_ticket_has_no_words(self):
        j = self.at_day(4, 'picture')
        r = j.act('ask')
        self.assertTrue(r['message'].startswith('👉'))
        self.assertNotIn('topping', r['message'])
        self.assertEqual(j.task['guest']['kind'], 'tourist')

    # ------------------------------------------------------ tables & app orders
    def test_group_table_bowl_by_bowl_then_one_serve(self):
        j = self.at_day(4, 'group', lambda t: len(t['needs']['party']) == 3)
        t = j.task
        tid = t['id']
        self.assertEqual(len(t['plates']), 3)
        self.assertEqual(t['quoted_price'] if t['quoted_price'] else 0, t['quoted_price'])
        r = j.act('ask', task=tid)
        self.assertIn('tô 2 là', r['message'])
        view = public_state(j.state)['careers']['restaurant']
        self.assertEqual(next(x for x in view['tasks'] if x['id'] == tid)['bowls_total'], 3)
        # Serving before every bowl is ready is refused and changes nothing.
        with self.assertRaises(GameError):
            j.act('rs_serve', task=tid, confirm=True)
        # Cannot switch away from a half-made bowl.
        for k in ('noodle', 'chili', 'box'):
            self.k.stock_up(k, 6)
        j.act('rs_container', task=tid, kind='bowl')
        with self.assertRaises(GameError):
            j.act('rs_tab', task=tid, index=1)
        j.act('rs_dump', task=tid, confirm=True)
        j.act('rs_tab', task=tid, index=2)
        self.assertEqual(j.get(tid)['cur'], 2)
        j.act('rs_tab', task=tid, index=0)
        money = j.c['money']
        self.cook(tid)
        t = j.get(tid)
        self.assertEqual(t['plates'][0] is not None and t['plates'][1] is not None, True)
        self.assertEqual(t['cur'], 2)
        price = t['quoted_price']
        r = j.act('rs_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(len(t['served']['bowls']), 3)
        self.assertGreaterEqual(j.c['money'], money + price)
        self.assertGreater(price, R.quote(j.c, dict(t['needs'], party=[])))
        validate_state(j.state)

    def test_group_bowl_mistake_is_named_and_brought_back(self):
        j = self.at_day(4, 'group', lambda t: t['guest']['kind'] == 'kid')
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        # Bowl 1 for the child gets far too much chili: the table sends that bowl back.
        low = R._spec(t, 0)['spice']
        self.cook(tid)
        t = j.get(tid)
        t['plates'][0]['chili'] = min(10, low + 4)
        r = j.act('rs_serve', task=tid, confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('tô 1', r['message'])
        t = j.get(tid)
        self.assertEqual(t['cur'], 0)
        self.assertIsNone(t['plates'][0])
        self.assertTrue(all(x is not None for x in t['plates'][1:]))
        validate_state(j.state)

    def test_app_orders_have_codes_and_wait_less(self):
        seen = [R.make_task(d, s, 1) for d in range(2, 12) for s in range(12)]
        apps = [t for t in seen if t['app']]
        self.assertTrue(apps)
        self.assertTrue(all(t['needs']['takeaway'] and t['app'].startswith('#') for t in apps))
        self.assertFalse(any(t['app'] for t in seen if not t['needs']['takeaway']))
        j = self.at_day(2, None, lambda t: bool(t['app']))
        app_id = j.task['id']
        j.act('more_work')
        other = next(t for t in j.c['tasks'] if t['id'] != app_id and t['status'] not in FS.DONE)
        j.act('task_select', task=other['id'])
        before = j.get(app_id)['patience']
        self.k.stock_up('noodle', 4)
        j.act('ask', task=other['id'])
        j.act('rs_container', task=other['id'], kind='box' if j.get(other['id'])['needs']['takeaway'] else 'bowl')
        j.act('rs_boil', task=other['id'])
        self.assertLess(j.get(app_id)['patience'], before - 1)

    # ------------------------------------------------------ surprises
    def test_event_opens_after_served_orders_and_blocks_serving(self):
        j = self.j
        pl = R._plan(j.c)
        pl['events'] = [dict(id='wallet', at=1, status='waiting', choice=None, good=None, note=None)]
        tid = self.cook()
        r = j.act('rs_serve', task=tid, confirm=True)
        self.assertIn('Ví ai bỏ quên', r['message'])
        view = public_state(j.state)['careers']['restaurant']['data']['day']
        self.assertEqual(view['open_event']['id'], 'wallet')
        self.assertEqual(len(view['open_event']['choices']), 3)
        tid = self.cook(j.c['active_task'])
        with self.assertRaises(GameError):
            j.act('rs_serve', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('rs_event', event='wallet', choice='nope')
        j.act('rs_event', event='wallet', choice='keep')
        money = j.c['money']
        j.act('rs_serve', task=tid, confirm=True)
        self.assertGreaterEqual(j.c['money'], money + 10)
        self.assertEqual(R._plan(j.c)['rules']['wallet'], 'returned')
        validate_state(j.state)

    def test_waiting_surprises_stay_secret(self):
        pl = R._plan(self.j.c)
        pl['events'] = [dict(id='inspection', at=3, status='waiting', choice=None, good=None, note=None)]
        view = public_state(self.j.state)['careers']['restaurant']['data']['day']
        self.assertEqual(view['events'], [])
        self.assertIsNone(view['open_event'])
        self.assertNotIn('inspection', json.dumps(public_state(self.j.state)['careers']['restaurant']['data']))

    def test_every_event_choice_is_playable(self):
        for eid, spec in R.EVENT_INDEX.items():
            for choice in spec['choices']:
                self.clock.t = 1000.0
                j = Journey('restaurant')
                delta = 200 - j.c['money']
                j.c['money'] += delta
                j.c['ops']['finance']['opening_balance'] += delta
                self.k.j = j
                self.j = j
                self.k.cook()
                j.act('rs_serve', task=j.task['id'], confirm=True)
                pl = self.force_event(eid, j)
                money = j.c['money']
                r = j.act('rs_event', event=eid, choice=choice['id'])
                self.assertTrue(r['message'], (eid, choice['id']))
                e = next(x for x in R._plan(j.c)['events'] if x['id'] == eid)
                self.assertEqual((e['status'], e['choice']), ('done', choice['id']))
                if choice.get('cost'):
                    self.assertEqual(j.c['money'], money - choice['cost'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_inspection_rewards_a_clean_log(self):
        j = self.j
        j.act('rs_clean')
        self.force_event('inspection')
        money = j.c['money']
        r = j.act('rs_event', choice='show')
        self.assertEqual(j.c['money'], money)
        self.assertTrue(r['good'])
        j2 = Journey('restaurant')
        self.force_event('inspection', j2)
        money = j2.c['money']
        r = j2.act('rs_event', choice='show')
        self.assertFalse(r['good'])
        self.assertEqual(j2.c['money'], money - min(30, money))
        self.assertTrue(any(x['category'] == 'fine' for x in j2.c['ops']['finance']['ledger']))

    def test_bad_beef_choices_change_the_kitchen(self):
        j = self.j
        n = kit.stock(j.c, 'beef')
        self.force_event('bad_beef')
        j.act('rs_event', choice='toss')
        self.assertEqual(kit.stock(j.c, 'beef'), 0)
        self.assertTrue(any(w['item'] == 'beef' and w['qty'] == n for w in j.c['life']['waste']))
        j2 = Journey('restaurant')
        self.force_event('bad_beef', j2)
        j2.act('rs_event', choice='keep')
        self.assertTrue(R._plan(j2.c)['rules']['bad_beef'])
        rows = R.feedback(j2.c, dict(j2.task, served=dict(bowl=dict(R._empty_bowl(), noodles=['perfect'], broth='kimchi', toppings={'beef': 1}), price=50)))
        self.assertEqual(rows['cap'], 2)

    def test_catering_batch_pays_when_complete(self):
        j = self.j
        self.force_event('catering')
        j.act('rs_event', choice='half')
        b = R._plan(j.c)['rules']['batch']
        self.assertEqual((b['goal'], b['done'], b['status']), (2, 0, 'open'))
        money = j.c['money']
        j.act('rs_batch')
        self.assertEqual(R._plan(j.c)['rules']['batch']['done'], 1)
        self.assertEqual(j.act('rs_batch').get('bank'), [2 * 36])   # the office pays by transfer: bank speaker
        self.assertEqual(R._plan(j.c)['rules']['batch']['status'], 'sent')
        self.assertEqual(j.c['money'], money + 2 * 36)
        with self.assertRaises(GameError):
            j.act('rs_batch')
        e = next(x for x in R._plan(j.c)['events'] if x['id'] == 'catering')
        self.assertTrue(e['good'])

    def test_catering_fails_if_left_at_close(self):
        j = self.j
        self.force_event('catering')
        j.act('rs_event', choice='all')
        r = j.act('end_day')
        e = next(x for x in r['summary']['career']['events'] if x['id'] == 'catering')
        self.assertFalse(e['good'])

    def test_critic_five_stars_pays_bonus(self):
        j = self.j
        self.force_event('critic')
        j.act('rs_event', choice='normal')
        target = next(t for t in j.c['tasks'] if t.get('vip') == 'critic')
        money = j.c['money']
        self.cook(target['id'])
        r = j.act('rs_serve', task=target['id'], confirm=True)
        stars = next(p for p in j.c['feed'] if p.get('source') == target['id'])['stars']
        self.assertIn('📝', r['message'])
        if stars >= 5:
            self.assertGreaterEqual(j.c['money'], money + j.get(target['id'])['quoted_price'] + 20)

    def test_noshow_dirty_bowls_need_washing(self):
        j = self.j
        self.force_event('noshow')
        j.act('rs_event', choice='self')
        R._plan(j.c)['rules']['dirty'] = R.DIRTY_MAX
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('rs_container', kind='bowl')
        j.act('rs_wash')
        j.act('rs_container', kind='bowl')
        with self.assertRaises(GameError):
            j.act('rs_wash')

    def test_gas_low_moves_the_green_window(self):
        j = self.j
        self.force_event('gas_low')
        j.act('rs_event', choice='weak')
        j.act('ask')
        j.act('rs_container', kind='box')
        j.act('rs_boil')
        self.clock.t += 5 + R.WEAK_FIRE
        j.act('rs_drain')
        self.assertEqual(j.task['bowl']['noodles'], ['raw'])
        j.act('rs_boil')
        self.clock.t += 10 + R.WEAK_FIRE
        j.act('rs_drain')
        self.assertEqual(j.task['bowl']['noodles'][-1], 'perfect')
        self.assertEqual(public_state(j.state)['careers']['restaurant']['data']['boil_shift'], R.WEAK_FIRE)

    def test_complaint_truth_is_hidden_and_decides_outcome(self):
        j = self.j
        tid = self.cook()
        j.act('rs_serve', task=tid, confirm=True)
        self.force_event('complaint')
        self.assertTrue(R._plan(j.c)['rules']['_complaint'])
        self.assertNotIn('_complaint', public_state(j.state)['careers']['restaurant']['data']['rules'])
        r = j.act('rs_event', choice='argue')
        self.assertIsNone(r['good'])
        # A wrong bowl before the complaint: arguing backfires.
        self.clock.t = 1000.0
        j2 = Journey('restaurant')
        self.k.j = j2
        tid = self.k.cook(boil=30)
        j2.act('rs_serve', task=tid, confirm=True)
        self.force_event('complaint', j2)
        posts = len(j2.c['feed'])
        r = j2.act('rs_event', choice='argue')
        self.assertFalse(r['good'])
        self.assertEqual(len(j2.c['feed']), posts + 1)

    def test_power_cut_wait_spoils_half_the_fresh_stock(self):
        j = self.j
        beef = kit.stock(j.c, 'beef')
        self.force_event('power_cut')
        j.act('rs_event', choice='wait')
        self.assertEqual(kit.stock(j.c, 'beef'), beef - beef // 2)

    def test_student_group_brings_walkins_within_limits(self):
        j = self.j
        self.force_event('student_group')
        before = len([t for t in j.c['tasks'] if t['status'] not in FS.DONE])
        j.act('rs_event', choice='share')
        after = len([t for t in j.c['tasks'] if t['status'] not in FS.DONE])
        self.assertEqual(after, min(4, before + 2))
        for _ in range(3):
            FS.spawn_walkin(j.state, j.c, 'restaurant', 1.0, 'x')
        self.assertLessEqual(len([t for t in j.c['tasks'] if t['status'] not in FS.DONE]), 4)
        validate_state(j.state)

    # ------------------------------------------------------ rhythm
    def test_patience_depends_on_personality(self):
        j = self.j
        c = j.c
        for t, kind in zip(c['tasks'][1:3], ('rush', 'chatty')):
            t['guest'] = FS.guest(kind)
        FS.patience_tick(c, 'restaurant', c['tasks'][0]['id'])
        self.assertEqual(c['tasks'][1]['patience'], 98)
        self.assertEqual(c['tasks'][2]['patience'], 100)

    def test_streak_bonus_and_grade_on_close(self):
        j = self.j
        pl = R._plan(j.c)
        pl['events'] = []
        j.c['life']['streak'] = 4
        tid = self.cook()
        money = j.c['money']
        j.act('rs_serve', task=tid, confirm=True)
        self.assertTrue(R._plan(j.c)['streak_paid'])
        self.assertTrue(any(x['category'] == 'skill_reward' and x['amount'] == FS.STREAK_BONUS for x in j.c['ops']['finance']['ledger']))
        tid = self.cook(j.c['active_task'])
        j.act('rs_serve', task=tid, confirm=True)
        r = j.act('end_day')
        g = r['summary']['career']['grade']
        self.assertIn(g['letter'], ('S', 'A'))
        self.assertEqual(j.c['ext']['data']['grades'][-1]['letter'], g['letter'])
        self.assertIn('tomorrow', r['summary']['career'])
        self.assertGreater(j.c['money'], money)

    def test_autoplay_ten_days(self):
        j = self.j
        styles, events = set(), set()
        for _ in range(10):
            r = self.k.play_day()
            s = r['summary']['career']
            validate_state(json.loads(json.dumps(j.state)))
            events |= {e['id'] for e in s['events']}
            styles |= {t['needs']['style'] for t in j.c['tasks']}
        self.assertEqual(j.c['day'], 11)
        self.assertGreaterEqual(len(events), 5)
        self.assertGreaterEqual(len(styles), 3)
        self.assertEqual(len(j.c['ext']['data']['grades']), 10)

    def test_old_save_upgrades(self):
        j = self.j
        tid = self.cook()
        j.act('rs_serve', task=tid, confirm=True)
        s = copy.deepcopy(j.state)
        c = s['careers']['restaurant']
        for t in c['tasks']:
            for k in ('guest', 'recalled', 'reasked', 'vip', 'story', 'over_budget', 'gen', 'app', 'cur', 'plates'):
                t.pop(k, None)
            t['needs'] = {k: v for k, v in t['needs'].items() if k not in ('style', 'open', 'party')}
        for k in ('plan', 'notebook', 'regulars', 'grades', 'ev_hist'):
            c['ext']['data'].pop(k, None)
        view = public_state(s)['careers']['restaurant']
        self.assertTrue(all('guest' in t for t in view['tasks']))
        validate_state(s)
        self.assertTrue(all('guest' in t for t in s['careers']['restaurant']['tasks']))
        from game.engine import apply_action
        s, _ = apply_action(s, 'restaurant', 'rs_clean', {})
        validate_state(s)


class Sloppy(Kitchen):
    """A cook that changes the recipe on purpose: mut(i, broth, tops, spice, noodles)."""

    def __init__(self, test, j, mut):
        super().__init__(test, j)
        self.mut = mut

    def plan_bowl(self, t, i=0):
        b, tops, spice, noodles = super().plan_bowl(t, i)
        return self.mut(i, b, dict(tops), spice, noodles)


class RestaurantConsequenceTests(unittest.TestCase):
    """Làm sai thì phải chịu: slips at the hand-off, the guest's reaction, stars."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def journey(self, pred, day=1, style='classic', slot_from=1):
        for d in range(day, day + 30):
            for slot in range(slot_from, 12):
                t = R.make_task(d, slot, 1)
                if t['needs']['style'] == style and pred(t):
                    return Journey('restaurant', slot=slot, day=d)
        self.fail('no such order')

    def play(self, mut, pred=lambda t: True, again=True, setup=None, **kw):
        j = self.journey(lambda t: not t['needs']['allergy'] and t['guest']['kind'] != 'kid' and pred(t), **kw)
        if setup:
            setup(j)
        tid = j.task['id']
        money = j.c['money']
        Sloppy(self, j, mut).cook(tid)
        r = j.act('rs_serve', task=tid, confirm=True)
        if again and j.get(tid)['status'] != 'completed':
            r = j.act('rs_serve', task=tid, confirm=True)
        t = j.get(tid)
        post = next((p for p in j.c['feed'] if p.get('source') == tid and p['kind'] == 'review'), None)
        return j, t, post, j.c['money'] - money, r

    def test_right_order_full_pay_no_slips(self):
        j, t, post, paid, _ = self.play(lambda i, b, tops, s, n: (b, tops, s, n))
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertGreaterEqual(post['stars'], 4)
        self.assertGreaterEqual(paid, t['quoted_price'])

    def test_spice_off_is_named_and_scales(self):
        pred = lambda t: t['needs']['spice'] <= 4
        _, t1, p1, _, _ = self.play(lambda i, b, tops, s, n: (b, tops, s + 1, n), pred)
        _, t3, p3, _, _ = self.play(lambda i, b, tops, s, n: (b, tops, s + 3, n), pred)
        self.assertEqual(t1['slips'][0]['sev'], 1)
        self.assertEqual(t3['slips'][0]['sev'], 2)
        self.assertLessEqual(p3['stars'], 3)
        self.assertGreater(p1['stars'], p3['stars'])
        self.assertIn('Dặn cay cấp', p3['text'])

    def test_missing_topping_costs_and_never_pays_twice(self):
        def drop(i, b, tops, s, n):
            tops.pop(next(iter(tops)))
            return b, tops, s, n
        j, t, post, paid, r = self.play(drop, lambda t: len(t['needs']['toppings']) >= 2)
        self.assertEqual(t['status'], 'completed')
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('không có miếng nào', post['text'])
        self.assertIn(t['reaction']['kind'], ('grumble', 'discount', 'refund', 'walkout'))
        self.assertEqual(paid, t['quoted_price'] - t['reaction']['cut'])
        money = j.c['money']
        again = cq.react(j.state, j.c, t, t['quoted_price'])
        self.assertEqual(j.c['money'], money)
        self.assertEqual(again['cut'], t['reaction']['cut'])
        with self.assertRaises(GameError):
            j.act('rs_serve', task=t['id'], confirm=True)
        self.assertEqual(j.c['money'], money)
        validate_state(json.loads(json.dumps(j.state)))

    def test_missing_topping_sent_back_then_fixed_is_small(self):
        def drop(i, b, tops, s, n):
            tops.pop(next(iter(tops)))
            return b, tops, s, n
        for slot in range(1, 12):
            j, t, post, paid, r = self.play(drop, lambda t: len(t['needs']['toppings']) >= 2, again=False, slot_from=slot)
            if t['status'] != 'completed':
                break
        else:
            self.skipTest('no send-back in range')
        self.assertTrue(r.get('refused'))
        self.assertEqual(t['reaction']['kind'], 'remake')
        want = dict(t['needs']['toppings'])
        for k, q in want.items():
            inventory.add_lot(j.c, k, q + 2, 1, 3, 'partner')
            while j.get(t['id'])['bowl']['toppings'].get(k, 0) < q:
                j.act('rs_topping', task=t['id'], item=k)
        j.act('rs_serve', task=t['id'], confirm=True)
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['returned'])
        post = next(p for p in j.c['feed'] if p.get('source') == t['id'] and p['kind'] == 'review')
        self.assertLessEqual(post['stars'], 4)
        self.assertIn('Phải làm lại', post['text'])

    def test_spoiled_beef_is_a_safety_mistake(self):
        def keep(j):
            R._plan(j.c)['rules']['bad_beef'] = True
        j, t, post, paid, r = self.play(lambda i, b, tops, s, n: (b, tops, s, n), lambda t: 'beef' in t['needs']['toppings'], setup=keep)
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(post['stars'], 1)
        self.assertEqual(paid, 0)
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        self.assertIn('mùi chua', r['message'])
        validate_state(json.loads(json.dumps(j.state)))


class RestaurantCareTests(unittest.TestCase):
    """Care across days: broth overnight, tonight's prep, the regulars' habits, the hygiene book."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('restaurant')
        self.k = Kitchen(self, self.j)

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def next_day(self):
        """Close today without serving anyone, then open tomorrow."""
        j = self.j
        self.k.resolve_open_event()
        j.act('end_day')
        j.act('start_day')

    def care(self):
        return public_state(self.j.state)['careers']['restaurant']['data']['care']

    def serve_active(self, touches=()):
        j = self.j
        tid = self.k.cook(j.task['id'])
        for k in touches:
            j.act('rs_touch', task=tid, touch=k)
        j.act('rs_serve', task=tid, confirm=True)
        return j.get(tid)

    # ---------------------------------------------------------------- broth overnight
    def test_pots_cool_overnight_and_reheat_in_one_turn(self):
        j = self.j
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'hot')
        self.next_day()
        self.assertEqual({R._pot_state(self.d, b) for b in ('kimchi', 'tomyum', 'blackbean')}, {'cold'})
        self.assertEqual(R._pot_age(self.d, 'kimchi'), 1)
        rows = {r['id']: r for r in self.care()['pots']}
        self.assertEqual((rows['kimchi']['state'], rows['kimchi']['age']), ('cold', 1))
        j.act('ask')
        n = j.task['needs']
        j.act('rs_container', kind='box' if n['takeaway'] else 'bowl')
        with self.assertRaises(GameError) as e:
            j.act('rs_broth', broth=n['broth'])
        self.assertIn('Đun sôi lại', str(e.exception))
        turn = j.c['turn']
        r = j.act('rs_reheat')
        self.assertEqual(j.c['turn'], turn + 1)
        self.assertIn('Kim chi', r['message'])
        self.assertEqual({R._pot_state(self.d, b) for b in ('kimchi', 'tomyum', 'blackbean')}, {'hot'})
        with self.assertRaises(GameError):
            j.act('rs_reheat')
        before = self.d['pots'][n['broth']]
        j.act('rs_broth', broth=n['broth'])
        self.assertEqual(self.d['pots'][n['broth']], before - R._portions(R._plan(j.c)))
        validate_state(json.loads(json.dumps(j.state)))

    def test_broth_expires_after_two_nights_and_is_poured_out(self):
        j = self.j
        for _ in range(3):
            self.next_day()
        self.assertEqual(R._pot_age(self.d, 'kimchi'), 3)
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'stale')
        self.assertEqual({r['id']: r['state'] for r in self.care()['pots']}['kimchi'], 'stale')
        # Nothing to reheat (a stale pot is not reheated); topping it up or ladling from it is refused.
        with self.assertRaises(GameError):
            j.act('rs_reheat')
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'stale')
        self.k.stock_up('pack_kimchi', 2)
        with self.assertRaises(GameError):
            j.act('rs_pot', broth='kimchi')
        j.act('ask')
        j.act('rs_container', kind='bowl')
        with self.assertRaises(GameError) as e:
            j.act('rs_broth', broth='kimchi')
        self.assertIn('Đổ phần cũ', str(e.exception))
        with self.assertRaises(GameError):
            j.act('rs_toss', broth='kimchi')
        q = self.d['pots']['kimchi']
        j.act('rs_toss', broth='kimchi', confirm=True)
        self.assertEqual((self.d['pots']['kimchi'], self.d['pot_lots']['kimchi']), (0, []))
        w = j.c['life']['waste'][-1]
        self.assertEqual((w['item'], w['value']), ('pack_kimchi', round(q * 9 / R.POT_BATCH)))
        j.act('rs_pot', broth='kimchi')
        self.assertEqual((self.d['pots']['kimchi'], R._pot_state(self.d, 'kimchi')), (R.POT_BATCH, 'hot'))
        validate_state(json.loads(json.dumps(j.state)))

    def test_topping_up_old_broth_keeps_the_older_date(self):
        j = self.j
        self.next_day()
        self.d['pots']['kimchi'] = 2
        self.k.stock_up('pack_kimchi', 2)
        r = j.act('rs_pot', broth='kimchi')
        self.assertIn('phần cũ được chan trước', r['message'])
        self.assertEqual(self.d['pot_lots']['kimchi'], [[2, 1], [R.POT_BATCH, 0]])
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'hot')
        # The old portions go into the next bowls first.
        self.assertEqual(R._use_pot(self.d, 'kimchi', 3), 1)
        self.assertEqual(self.d['pot_lots']['kimchi'], [[R.POT_BATCH - 1, 0]])

    def test_a_pot_used_and_topped_up_every_day_never_spoils(self):
        j = self.j
        for _ in range(6):
            self.next_day()
            self.assertNotEqual(R._pot_state(self.d, 'kimchi'), 'stale')
            j.act('rs_reheat')
            R._use_pot(self.d, 'kimchi', min(self.d['pots']['kimchi'], 6))
            R._cook(self.d, 'kimchi', R.POT_BATCH)
            validate_state(json.loads(json.dumps(j.state)))
        self.assertLessEqual(R._pot_age(self.d, 'kimchi'), 1)

    def test_only_expired_portions_are_poured_out(self):
        j = self.j
        self.d['pot_lots']['kimchi'] = [[2, 3], [4, 0]]
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'stale')
        with self.assertRaises(GameError):
            j.act('rs_toss', broth='tomyum', confirm=True)       # nothing expired there
        r = j.act('rs_toss', broth='kimchi', confirm=True)
        self.assertIn('Còn 4 phần', r['message'])
        self.assertEqual((self.d['pots']['kimchi'], self.d['pot_lots']['kimchi']), (4, [[4, 0]]))

    def test_two_night_broth_is_noted_in_the_review(self):
        j = self.j
        self.next_day()
        self.next_day()
        tid = self.k.cook(j.task['id'])
        self.assertEqual(j.get(tid)['broth_age'], 2)
        j.act('rs_serve', task=tid, confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)
        row = next(x for x in post['feedback']['criteria'] if x['key'] == 'broth')
        self.assertEqual(row['score'], 4)

    def test_kitchen_helper_reheats_first(self):
        self.next_day()
        msg = R.assist(self.j.state, self.j.c, dict(role='prep'), None)
        self.assertIn('đun sôi lại', msg)
        self.assertEqual(R._pot_state(self.d, 'kimchi'), 'hot')

    # ---------------------------------------------------------------- tonight's prep
    def test_simmer_tonight_opens_full_and_fresh(self):
        j = self.j
        self.k.stock_up('pack_tomyum', 4)
        packs = kit.stock(j.c, 'pack_tomyum')
        with self.assertRaises(GameError):
            j.act('rs_prep', broth='tomyum')
        j.act('rs_prep', broth='tomyum', confirm=True)
        self.assertEqual(kit.stock(j.c, 'pack_tomyum'), packs - R.PREP_PACKS)
        with self.assertRaises(GameError):
            j.act('rs_prep', broth='tomyum', confirm=True)
        with self.assertRaises(GameError):
            j.act('rs_prep', broth='cheese', confirm=True)     # locked at level 1
        self.k.stock_up('pack_kimchi', 4)
        j.act('rs_prep', broth='kimchi', confirm=True)
        self.k.stock_up('pack_blackbean', 4)
        with self.assertRaises(GameError):
            j.act('rs_prep', broth='blackbean', confirm=True)  # only two slow burners
        self.assertEqual({r['id']: r['state'] for r in self.care()['pots']}['kimchi'], 'hot')
        left = self.d['pots']['tomyum']
        self.k.resolve_open_event()
        r = j.act('end_day')
        care = r['summary']['career']['care']
        self.assertEqual({p['id']: p['state'] for p in care['pots']}['tomyum'], 'prep')
        j.act('start_day')
        for b in ('tomyum', 'kimchi'):
            self.assertEqual((self.d['pots'][b], self.d['pot_lots'][b], R._pot_state(self.d, b)), (R.POT_MAX, [[R.POT_MAX, 0]], 'hot'))
        self.assertEqual(R._pot_state(self.d, 'blackbean'), 'cold')
        self.assertEqual(self.d['prep'], [])
        if left:
            self.assertTrue(any('bữa cơm nhân viên' in x.get('message', x.get('text', '')) for x in j.c['journal'][-10:]))
        validate_state(json.loads(json.dumps(j.state)))

    def test_outlook_warns_about_pots_and_tomorrow(self):
        j = self.j
        self.next_day()
        self.next_day()
        o = self.care()['outlook']
        self.assertEqual(o['day'], j.c['day'] + 1)
        self.assertEqual(o['label'], FS.pick_mod('restaurant', j.c['day'] + 1, R.MODS)['label'])
        self.assertTrue(any('quá 2 đêm' in a for a in o['advice']))
        self.assertTrue(any('Sổ vệ sinh' in a for a in o['advice']))

    # ---------------------------------------------------------------- hygiene book
    def test_hygiene_book_builds_over_days(self):
        j = self.j
        self.assertEqual(R.hygiene(self.d), 50)
        for i in range(5):
            j.act('rs_clean')
            for b in R.BROTH_INDEX:
                if R._pot_state(self.d, b) == 'stale':
                    j.act('rs_toss', broth=b, confirm=True)
            self.k.resolve_open_event()
            r = j.act('end_day')
            j.act('start_day')
        self.assertEqual(len(self.d['hlog']), 5)
        self.assertEqual(R.hygiene(self.d), round(100 * (5 * 4 + 2 * 2) / 28))
        self.assertEqual(r['summary']['career']['care']['hygiene']['grade'], 'A')
        # A missed day costs a little; the A kitchen stays A.
        self.k.resolve_open_event()
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(self.d['hlog'][-1]['clean'], False)
        self.assertEqual(R.hygiene_grade(R.hygiene(self.d)), 'A')
        # The surprise inspection reads the book: no fine for a missing line today.
        pl = R._plan(j.c)
        pl['events'] = [dict(id='inspection', at=0, status='waiting', choice=None, good=None, note=None)]
        FS.trigger(j.state, j.c, pl, R.EVENT_INDEX)
        money = j.c['money']
        r = j.act('rs_event', choice='show')
        self.assertIsNone(r['good'])
        self.assertEqual(j.c['money'], money)
        pub = self.care()['hygiene']
        self.assertEqual(len(pub['days']), 6)
        self.assertEqual(pub['grade'], 'A')

    def test_hygiene_minded_guest_notices_the_book(self):
        j = self.j
        t = dict(j.task, npc=kit.npc_id('restaurant', 5),
                 served=dict(bowl=dict(R._empty_bowl(), noodles=['perfect'], broth='kimchi', toppings={}), price=40))
        self.d['hlog'] = [dict(day=i, clean=True, dishes=True, pots=True) for i in range(1, 8)]
        rows = {x['key']: x for x in R.feedback(j.c, t)['criteria']}
        self.assertEqual(rows['hygiene']['score'], 5)
        self.d['hlog'] = [dict(day=i, clean=False, dishes=True, pots=False) for i in range(1, 8)]
        rows = {x['key']: x for x in R.feedback(j.c, t)['criteria']}
        self.assertEqual(rows['hygiene']['score'], 3)
        self.d['hlog'] = self.d['hlog'][:2]
        self.assertNotIn('hygiene', {x['key'] for x in R.feedback(j.c, t)['criteria']})

    # ---------------------------------------------------------------- regulars' habits
    def test_regular_habits_are_learned_and_honoured(self):
        j = self.j
        t = j.task
        i = R._npc_index(t)
        self.assertIn(i, R.HABITS)
        self.assertIsNone(t['regular'])
        with self.assertRaises(GameError):
            j.act('rs_touch', task=t['id'], touch=R.HABITS[i][0][0])
        self.serve_active()
        g = self.d['guests'][t['npc']]
        self.assertEqual(g['visits'], 1)
        book = {b['npc']: b for b in self.care()['book']}
        self.assertEqual([n['touch'] for n in book[t['npc']]['notes']], [R.HABITS[i][0][0]])
        self.assertEqual(book[t['npc']]['locked'], 1)
        # Unlearned habits never leave the server.
        self.assertNotIn(R.HABITS[i][1][1], json.dumps(public_state(j.state), ensure_ascii=False))
        # The same guest comes back: the ticket snapshots what the shop knows.
        other = next(x for x in j.c['tasks'] if x['status'] not in FS.DONE)
        j.c['active_task'] = other['id']
        other['regular'] = None
        self.d['guests'][other['npc']] = dict(visits=1, bond=0) if R._npc_index(other) in R.HABITS else None
        if self.d['guests'][other['npc']] is None:
            self.skipTest('next guest has no card')
        R.on_task(j.state, j.c, other)
        habit = R.HABITS[R._npc_index(other)][0][0]
        self.assertEqual(other['regular'], dict(bond=0, notes=[habit]))
        if habit == 'soup':
            self.k.cook(other['id'])
        j.act('ask', task=other['id'])
        turn = j.c['turn']
        j.act('rs_touch', task=other['id'], touch=habit)
        self.assertEqual(j.c['turn'], turn)
        with self.assertRaises(GameError):
            j.act('rs_touch', task=other['id'], touch=habit)
        wrong = next(k for k in R.TOUCHES if k not in R.HABITS[R._npc_index(other)][0])
        with self.assertRaises(GameError):
            j.act('rs_touch', task=other['id'], touch=wrong)
        tid = self.k.cook(other['id'])
        j.act('rs_serve', task=tid, confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)
        row = next(x for x in post['feedback']['criteria'] if x['key'] == 'remember')
        self.assertEqual(row['score'], 5)
        validate_state(json.loads(json.dumps(j.state)))

    def guest_at(self, npc_index, visits=1, bond=0):
        """A day-1 order from this regular, who has been here `visits` times."""
        slot = next(x for x in range(12) if R._npc_index(R.make_task(1, x, 1)) == npc_index)
        j = Journey('restaurant', slot=slot, day=1)
        self.j, self.k.j = j, j
        self.d['guests'][j.task['npc']] = dict(visits=visits, bond=bond)
        j.task['regular'] = None
        R.on_task(j.state, j.c, j.task)
        return j.task

    def test_touch_costs_no_turn_and_soup_uses_the_pot(self):
        t = self.guest_at(3)                      # Cô Tư likes an extra bowl of broth
        j = self.j
        self.assertEqual(t['regular']['notes'], ['soup'])
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('rs_touch', task=t['id'], touch='soup')   # no broth in the bowl yet
        j.act('rs_container', kind='bowl')
        broth = t['needs']['broth']
        j.act('rs_broth', broth=broth)
        before, turn = self.d['pots'][broth], j.c['turn']
        j.act('rs_touch', task=t['id'], touch='soup')
        self.assertEqual(j.c['turn'], turn)
        self.assertEqual(self.d['pots'][broth], before - 1)
        self.assertEqual(j.task['touches'], ['soup'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_forgotten_habit_and_bond(self):
        t = self.guest_at(0, visits=3, bond=2)    # Anh Sơn: iced tea, chili on the side
        j = self.j
        self.assertEqual(t['regular']['notes'], ['tea', 'side'])
        money = j.c['money']
        done = self.serve_active(touches=['tea'])
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p.get('source') == done['id'])
        row = next(x for x in post['feedback']['criteria'] if x['key'] == 'remember')
        self.assertEqual(row['score'], 4)
        self.assertEqual(self.d['guests'][t['npc']], dict(visits=4, bond=2))   # forgot one: no bond, no thank-you
        self.assertFalse(any(x['reason'] == 'Khách quen gửi thêm tiền trà' for x in j.c['ops']['finance']['ledger']))
        self.assertGreater(j.c['money'], money)

    def test_bond_thank_you_and_book(self):
        t = self.guest_at(5, visits=1, bond=2)    # Bà Hoa: scalded chopsticks
        j = self.j
        self.assertEqual(t['regular'], dict(bond=2, notes=['scald']))
        self.serve_active(touches=['scald'])
        self.assertEqual(self.d['guests'][t['npc']], dict(visits=2, bond=3))
        self.assertTrue(any(x['reason'] == 'Khách quen gửi thêm tiền trà' and x['amount'] == R.BOND_TIP
                            for x in j.c['ops']['finance']['ledger']))
        b = next(x for x in self.care()['book'] if x['npc'] == t['npc'])
        self.assertEqual((b['bond'], b['tip'], b['next_in']), (3, R.BOND_TIP, 1))

    # ---------------------------------------------------------------- saves
    def test_old_save_gets_care_keys(self):
        j = self.j
        s = copy.deepcopy(j.state)
        c = s['careers']['restaurant']
        for k in ('pot_lots', 'pot_warm', 'prep', 'guests', 'hlog'):
            c['ext']['data'].pop(k)
        for t in c['tasks']:
            for k in ('regular', 'touches', 'broth_age'):
                t.pop(k)
        view = public_state(s)['careers']['restaurant']['data']['care']
        self.assertEqual({r['state'] for r in view['pots'] if r['portions']}, {'hot'})
        validate_state(s)
        d = c['ext']['data']
        self.assertEqual((d['prep'], d['guests'], d['hlog']), ([], {}, []))
        self.assertTrue(all(d['pot_warm'].values()))
        self.assertTrue(all(t['touches'] == [] for t in c['tasks']))

    def test_tampered_care_data_is_rejected(self):
        bad = [
            lambda d, t: d['pot_lots'].update(kimchi=[[3, 0], [3, 1]]),
            lambda d, t: d['pot_lots'].update(kimchi=[['6', 0]]),
            lambda d, t: d['pot_lots'].update(pho=[]),
            lambda d, t: d['pot_warm'].update(kimchi=1),
            lambda d, t: d.update(prep=['kimchi', 'kimchi']),
            lambda d, t: d.update(prep=['pho']),
            lambda d, t: d['guests'].update({'restaurant_npc_09': dict(visits=1, bond=0)}),
            lambda d, t: d['guests'].update({'restaurant_npc_01': dict(visits=1, bond=9)}),
            lambda d, t: d.update(hlog=[dict(day=1, clean='yes', dishes=True, pots=True)]),
            lambda d, t: d.update(hlog=[dict(day=1, clean=True, dishes=True, pots=True)] * 8),
            lambda d, t: t.update(touches=['tea']),
            lambda d, t: t.update(regular=dict(bond=0, notes=['wipe', 'tea'])),
            lambda d, t: t.update(broth_age=5),
        ]
        for f in bad:
            s = copy.deepcopy(self.j.state)
            c = s['careers']['restaurant']
            t = next(x for x in c['tasks'] if x['status'] not in FS.DONE)
            f(c['ext']['data'], t)
            with self.assertRaises(GameError):
                validate_state(s)


if __name__ == '__main__':
    unittest.main()
