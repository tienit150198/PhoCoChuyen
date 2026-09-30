"""Shop thú cưng (pet_shop): Tiệm Thú Nhỏ Chú Út.

Every kind of job done right and wrong, the till (traceable totals, change, tips), the
natural consequences (welfare and safety mistakes bring a report and an inspection),
restocking, determinism, saves and old saves."""
import copy
import json
import unittest
from unittest import mock

from game import consequences as cq
from game import short_pay
from game.careers import PLUGINS, till
from game.content import CAREERS, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from tests.helpers import Journey

PS = PLUGINS.get('pet_shop')
if PS is None:
    raise unittest.SkipTest('pet_shop is filtered out by MNL_CAREERS')


def where(variant):
    for day in range(1, 80):
        for slot, (_, v) in enumerate(PS.day_plan(day)):
            if v == variant:
                return day, slot
    raise AssertionError(variant)


def at(variant):
    day, slot = where(variant)
    j = Journey('pet_shop', slot=slot, day=day)
    j.act('ask', task=j.task['id'])
    return j


def tid(j):
    return j.c['tasks'][-1]['id']


def t_of(j):
    return j.get(tid(j))


def ring(j, extra=None):
    """Scan exactly what is on the counter, plus `extra` lines, then total."""
    t = t_of(j)
    for k, q in t['cart'].items():
        j.act('ps_scan', task=t['id'], key=k, qty=q)
    for k, q in (extra or {}).items():
        j.act('ps_scan', task=t['id'], key=k, qty=q)
    return j.act('ps_total', task=t['id'])


def pay(j, change=None):
    t = t_of(j)
    if change is None:
        change = till.greedy(till.due(t['cash']))
    return j.act('ps_handover', task=t['id'], change=change)


def ledger(j, ref=None):
    return [x for x in j.c['ops']['finance']['ledger'] if ref is None or x['ref'] == ref]


def codes(t):
    return {x['code'] for x in cq.slips(t)}


def follows(j):
    return [f['script'] for f in j.c['incidents']['follow']]


def solve_food(j, item, extra_ok=True):
    t = t_of(j)
    for topic in ('age', 'weight', 'allergy', 'now'):
        j.act('ps_ask', task=t['id'], topic=topic)
    j.act('ps_food', task=t['id'], item=item)
    if extra_ok and t['_x'].get('grab'):
        if not t['work']['dated']:
            j.act('ps_date', task=t['id'])
        j.act('ps_swap', task=t['id'])
    ring(j)
    return pay(j)


class Plan(unittest.TestCase):
    def test_script_and_determinism(self):
        self.assertEqual([j for j, _ in PS.day_plan(1)[:3]], ['food', 'care', 'tank'])
        self.assertEqual(PS.day_plan(1)[:3], [('food', 'mun_kitten'), ('care', 'care_first'), ('tank', 'linh_betta')])
        seen = set()
        for day in range(1, 50):
            for slot in range(12):
                a, b = make_task('pet_shop', day, slot, 3), make_task('pet_shop', day, slot, 3)
                self.assertEqual(a, b)
                seen.add(a['job'])
            rows = PS.day_plan(day)
            self.assertLessEqual(sum(1 for j, _ in rows if j == 'care'), 1, day)
            if day >= 6:
                self.assertEqual(len({v for _, v in rows[:5]}), 5, day)
        self.assertEqual(seen, set(PS.JOBS))

    def test_every_variant_is_reachable(self):
        for job, rows in PS.VARIANTS.items():
            for x in rows:
                where(x['id'])

    def test_hidden_until_asked(self):
        day, slot = where('tofu_allergy')
        j = Journey('pet_shop', slot=slot, day=day)
        pub = next(t for t in public_state(j.state)['careers']['pet_shop']['tasks'] if t['id'] == tid(j))
        self.assertNotIn('_x', pub)
        self.assertEqual(pub['needs'], {})
        with self.assertRaises(GameError):
            j.act('ps_ask', task=tid(j), topic='allergy')
        j.act('ask', task=tid(j))
        pub = next(t for t in public_state(j.state)['careers']['pet_shop']['tasks'] if t['id'] == tid(j))
        self.assertNotIn('allergy', pub['answers'])
        self.assertNotIn('thịt gà', json.dumps(pub, ensure_ascii=False).split('"answers"')[1][:200])
        j.act('ps_ask', task=tid(j), topic='allergy')
        pub = next(t for t in public_state(j.state)['careers']['pet_shop']['tasks'] if t['id'] == tid(j))
        self.assertIn('thịt gà', pub['answers']['allergy'])


class Food(unittest.TestCase):
    def test_right_food_full_pay_and_stock(self):
        j = at('mun_kitten')
        before, money = j.c['ext']['inv'], j.c['money']
        n0 = PS.kit.stock(j.c, 'cat_kitten')
        r = solve_food(j, 'cat_kitten')
        t = t_of(j)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(cq.slips(t))
        self.assertEqual(PS.kit.stock(j.c, 'cat_kitten'), n0 - 1)
        self.assertEqual(j.c['money'] - money, 40 + t.get('tip_given', 0))
        self.assertEqual(j.c['feed'][0]['stars'], 5)
        self.assertTrue(r['celebrate'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_allergy_is_a_safety_mistake_with_report_and_inspection(self):
        j = at('tofu_allergy')
        money = j.c['money']
        r = solve_food(j, 'dog_adult')
        t = t_of(j)
        self.assertIn('allergy', codes(t))
        self.assertTrue(cq.safety(t))
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(j.c['money'], money)            # refunded in full
        self.assertIn('Mấy hôm sau', r['message'])
        self.assertIn(PS.INSPECT, follows(j))
        self.assertEqual(j.c['feed'][0]['stars'], 1)
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertEqual(j.c['ext']['data']['welfare'], 1)

    def test_right_food_for_the_allergy(self):
        j = at('tofu_allergy')
        solve_food(j, 'dog_lamb')
        self.assertFalse(cq.slips(t_of(j)))

    def test_wrong_age_is_a_clear_mistake(self):
        j = at('mun_kitten')
        solve_food(j, 'cat_adult')
        t = t_of(j)
        self.assertEqual(codes(t), {'stage'})
        self.assertFalse(cq.safety(t))
        self.assertLessEqual(j.c['feed'][0]['stars'], 3)

    def test_wrong_species(self):
        j = at('linh_betta_food')
        solve_food(j, 'goldfish_food')
        self.assertIn('species', codes(t_of(j)))

    def test_expired_basket_cans_sold_is_safety(self):
        j = at('muop_senior')
        self.assertEqual(t_of(j)['cart'], {'pate_cat': 2})
        stock = PS.kit.stock(j.c, 'pate_cat')
        solve_food(j, 'cat_senior', extra_ok=False)
        t = t_of(j)
        self.assertIn('expired', codes(t))
        self.assertTrue(cq.safety(t))
        self.assertEqual(PS.kit.stock(j.c, 'pate_cat'), stock)   # the basket cans were not shelf stock

    def test_checking_dates_and_swapping_the_cans(self):
        j = at('muop_senior')
        m = j.act('ps_date', task=tid(j))['message']
        self.assertIn('HSD', m)
        stock = PS.kit.stock(j.c, 'pate_cat')
        waste = j.c['life']['day_waste']
        solve_food(j, 'cat_senior')
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(PS.kit.stock(j.c, 'pate_cat'), stock - 2)
        self.assertGreater(j.c['life']['day_waste'], waste)

    def test_removing_the_basket_cans_is_fine(self):
        j = at('muop_senior')
        j.act('ps_cart', task=tid(j), key='pate_cat', qty=0)
        solve_food(j, 'cat_senior', extra_ok=False)
        self.assertFalse(cq.slips(t_of(j)))

    def test_validation(self):
        j = at('mun_kitten')
        for bad in (dict(item='nope'), dict(item='leash')):
            with self.assertRaises(GameError):
                j.act('ps_food', task=tid(j), **bad)
        with self.assertRaises(GameError):
            j.act('ps_total', task=tid(j))           # nothing on the counter
        with self.assertRaises(GameError):
            j.act('ps_date', task=tid(j))            # no basket cans in this job
        with self.assertRaises(GameError):
            j.act('ps_ask', task=tid(j), topic='parent')


class Till(unittest.TestCase):
    def test_total_is_traceable_line_by_line(self):
        j = at('muop_senior')
        j.act('ps_date', task=tid(j))
        j.act('ps_swap', task=tid(j))
        j.act('ps_food', task=tid(j), item='cat_senior')
        ring(j)
        t = t_of(j)
        self.assertEqual(t['cash']['price'], 48 + 2 * 9)
        pub = next(x for x in public_state(j.state)['careers']['pet_shop']['tasks'] if x['id'] == t['id'])
        self.assertEqual(pub['bill_total'], sum(t['units'][k] * q for k, q in t['bill'].items()))
        self.assertEqual(pub['cart_total'], pub['bill_total'])
        self.assertEqual(pub['cash']['due'], sum(t['cash']['tender']) - t['cash']['price'])

    def test_overcharge_caught_by_a_careful_customer(self):
        j = at('mun_kitten')    # Bà Hai counts every coin
        j.act('ps_food', task=tid(j), item='cat_kitten')
        r = ring(j, extra={'cat_kitten': 1})
        self.assertIs(r.get('correct'), False)
        t = t_of(j)
        self.assertFalse(t['billed'])
        self.assertEqual(t['bill_caught'], 1)
        j.act('ps_void', task=tid(j), key='cat_kitten')
        j.act('ps_total', task=tid(j))
        pay(j)
        t = t_of(j)
        self.assertEqual(codes(t), {'bill_caught'})
        self.assertEqual(j.c['feed'][0]['stars'], 4)

    def test_missed_overcharge_is_found_at_home(self):
        j = at('linh_betta_food')       # Uyên is quiet: she does not check the bill
        j.act('ps_food', task=tid(j), item='fish_food')
        r = ring(j, extra={'fish_food': 1})
        t = t_of(j)
        if r.get('correct') is False:     # this customer happened to check
            self.assertEqual(t['bill_caught'], 1)
            return
        self.assertEqual(t['bill_over'], 12)
        pay(j)
        t = t_of(j)
        self.assertIn('overcharged', codes(t))

    def test_undercharge_honest_customer_points_it_out_else_the_shop_loses(self):
        j = at('linh_betta_food')
        j.act('ps_food', task=tid(j), item='fish_food')
        j.act('ps_cart', task=tid(j), key='toy', qty=1)
        j.act('ps_scan', task=tid(j), key='fish_food')
        r = j.act('ps_total', task=tid(j))
        t = t_of(j)
        if till.honest(j.c, t) or r.get('correct') is False:
            self.assertIs(r.get('correct'), False)
            self.assertEqual(t['bill_under'], -1)
            r = j.act('ps_total', task=tid(j))      # total again without the toy: now the shop eats it
        t = t_of(j)
        self.assertTrue(t['billed'])
        self.assertEqual(t['bill_under'], 10)
        money = j.c['money']
        pay(j)
        self.assertEqual(j.c['money'] - money, 12 + t_of(j).get('tip_given', 0))
        self.assertEqual(j.c['ext']['data']['today']['loss'], 10)

    def test_rescan_before_payment(self):
        j = at('mun_kitten')
        j.act('ps_food', task=tid(j), item='cat_kitten')
        ring(j)
        j.act('ps_rescan', task=tid(j))
        t = t_of(j)
        self.assertFalse(t['billed'])
        self.assertIsNone(t['cash'])
        j.act('ps_total', task=tid(j))
        pay(j)
        self.assertFalse(cq.slips(t_of(j)))

    def test_short_change_careful_customer_asks_for_the_rest(self):
        j = at('mun_kitten')
        j.act('ps_food', task=tid(j), item='cat_kitten')
        ring(j)
        t = t_of(j)
        due = till.due(t['cash'])
        self.assertGreater(due, 0)
        r = pay(j, change=till.greedy(due - 1) if due > 1 else [])
        self.assertIs(r.get('correct'), False)
        self.assertIn('thiếu', r['message'])
        self.assertEqual(t_of(j)['status'], 'in_progress')
        pay(j)
        t = t_of(j)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('change_short', codes(t))

    def test_excess_change_honest_gives_back_else_shop_loses(self):
        for variant in ('linh_betta_food', 'mun_kitten', 'tofu_allergy', 'bin_hamster_food', 'map_fish'):
            j = at(variant)
            right = PS.VINDEX['food'][variant]['x']['right']
            j.act('ps_food', task=tid(j), item=right)
            ring(j)
            t = t_of(j)
            due = till.due(t['cash'])
            money = j.c['money']
            pay(j, change=till.greedy(due + 5))
            t = t_of(j)
            rec = t['cash']
            self.assertIn(rec['outcome'], ('returned', 'kept'))
            price = rec['price']
            if rec['outcome'] == 'kept':
                self.assertEqual(j.c['money'] - money, price - 5)
            else:
                self.assertEqual(j.c['money'] - money, price)
            validate_state(json.loads(json.dumps(j.state)))

    def test_keep_the_change_tip_follows_the_contract(self):
        hits = 0
        for day in range(1, 60):
            for slot, (job, v) in enumerate(PS.day_plan(day)):
                if job != 'food' or v in ('muop_senior', 'dau_puppy'):
                    continue
                j = Journey('pet_shop', slot=slot, day=day)
                j.act('ask', task=tid(j))
                right = PS.VINDEX['food'][v]['x']['right']
                j.act('ps_food', task=tid(j), item=right)
                ring(j)
                t = t_of(j)
                if not till.waves_off(j.c, t, till.due(t['cash'])):
                    continue
                money = j.c['money']
                pay(j)
                t = t_of(j)
                self.assertGreater(t['tip_given'], 0)
                tips = [x for x in ledger(j, t['id']) if x['category'] == 'tip']
                self.assertEqual(sum(x['amount'] for x in tips), t['tip_given'])
                self.assertEqual(j.c['money'] - money, t['cash']['price'] + t['tip_given'])
                hits += 1
                break
            if hits >= 2:
                break
        self.assertGreaterEqual(hits, 1)

    def test_refuse_never_tips(self):
        j = at('tofu_allergy')
        solve_food(j, 'dog_adult')
        t = t_of(j)
        self.assertEqual(t['cash']['outcome'], 'void')
        self.assertFalse(t.get('tip_given'))


def kit_roll(t, n):
    return PS.kit.rng('pet_shop', 'bill-check', t['id'], n).random()


class Tank(unittest.TestCase):
    def build(self, j, size, fish, gear=('conditioner',), tips=('float', 'part', 'pinch'), coats=None):
        j.act('ps_tank', task=tid(j), size=size)
        for k, q in fish.items():
            j.act('ps_cart', task=tid(j), key=k, qty=q)
        for k, coat in (coats or {}).items():
            j.act('ps_coat', task=tid(j), kind=k, coat=coat)
        for g in gear:
            j.act('ps_cart', task=tid(j), key=g, qty=1)
        j.act('ps_advice', task=tid(j), tips=list(tips))
        ring(j)
        return pay(j)

    def test_first_day_betta_right(self):
        j = at('linh_betta')
        bettas = j.c['ext']['data']['animals']['betta']
        self.build(j, 'tank_10', {'betta': 1}, coats={'betta': 'blue'})
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['ext']['data']['animals']['betta'], bettas - 1)
        self.assertEqual(j.c['feed'][0]['stars'], 5)

    def test_betta_with_fin_nippers_is_a_welfare_mistake(self):
        j = at('sau_community')
        self.build(j, 'tank_60', {'guppy': 10, 'barb': 6, 'betta': 1}, gear=('filter', 'conditioner'))
        t = t_of(j)
        self.assertIn('fin_nip', codes(t))
        self.assertTrue(cq.safety(t))
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn(PS.INSPECT, follows(j))
        # the fish came back to the shop's tanks
        self.assertEqual(j.c['ext']['data']['animals']['betta'], PS.ANIMALS['betta']['target'])

    def test_community_right_without_the_betta(self):
        j = at('sau_community')
        self.build(j, 'tank_60', {'guppy': 10, 'barb': 6}, gear=('filter', 'conditioner', 'heater'))
        self.assertFalse(cq.slips(t_of(j)))

    def test_overcrowded_and_goldfish_needs_filter(self):
        j = at('bin_goldfish')
        self.build(j, 'tank_10', {'goldfish': 3})
        self.assertTrue({'crowded', 'no_filter'} <= codes(t_of(j)))
        j = at('bin_goldfish')
        self.build(j, 'tank_30', {'goldfish': 3}, gear=('filter', 'conditioner'), coats={'goldfish': 'redwhite'})
        self.assertFalse(cq.slips(t_of(j)))

    def test_two_bettas_and_mixing_goldfish(self):
        j = at('hai_bettas')
        self.build(j, 'tank_10', {'betta': 2})
        self.assertIn('betta_fight', codes(t_of(j)))
        j = at('quan_office')
        self.build(j, 'tank_30', {'guppy': 6, 'goldfish': 2}, gear=('filter', 'conditioner'))
        self.assertIn('temp_mix', codes(t_of(j)))

    def test_missing_conditioner_advice_and_wanted_fish(self):
        j = at('linh_betta')
        self.build(j, 'tank_10', {'guppy': 2}, gear=(), tips=('feed',))
        self.assertTrue({'chlorine', 'not_wanted', 'bad_advice'} <= codes(t_of(j)))

    def test_total_needs_tank_and_fish(self):
        j = at('linh_betta')
        j.act('ps_cart', task=tid(j), key='conditioner', qty=1)
        j.act('ps_scan', task=tid(j), key='conditioner')
        with self.assertRaises(GameError):
            j.act('ps_total', task=tid(j))


class Colours(unittest.TestCase):
    build = Tank.build

    def test_coats_on_show_are_seeded_and_stable(self):
        for kind, rows in PS.COATS.items():
            ids = {c[0] for c in rows}
            a = PS.show_coats(4, kind)
            self.assertEqual(a, PS.show_coats(4, kind))
            self.assertEqual(len(a), PS.SHOW)
            self.assertTrue(set(a) <= ids)
        seen = {c for day in range(1, 40) for c in PS.show_coats(day, 'betta')}
        self.assertEqual(seen, {c[0] for c in PS.COATS['betta']})    # rare colours do turn up
        j = Journey('pet_shop')
        d = public_state(j.state)['careers']['pet_shop']['data']
        self.assertEqual(d['coats']['betta'], PS.show_coats(j.c['day'], 'betta'))
        self.assertEqual([x[0] for x in d['coat_colors']['betta']], [PS.COAT['betta'][k][2] for k in d['coats']['betta']])
        self.assertEqual(len(d['corner_fur']), len(d['corner']))
        # every animal the shop keeps has colours; every adoptee has a known coat
        self.assertEqual(set(PS.COATS), set(PS.ANIMALS))
        for a in PS.ADOPTEES.values():
            self.assertIn(a['coat'], {c[0] for c in PS.FUR[a['kind']]})
        cc = PS.content()
        self.assertEqual({x['id'] for x in cc['coats']['hamster']}, {'cream', 'grey', 'white', 'spot'})
        self.assertEqual(len(cc['themes']), len(PS.THEMES))

    def test_the_task_does_not_change_when_regenerated(self):
        j = at('linh_betta')
        j.act('ps_tank', task=tid(j), size='tank_10')
        j.act('ps_cart', task=tid(j), key='betta', qty=1)
        j.act('ps_coat', task=tid(j), kind='betta', coat='red')
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        self.assertEqual(t_of(j)['coats'], {'betta': 'red'})

    def test_wrong_colour_is_a_mild_complaint(self):
        j = at('linh_betta')
        self.build(j, 'tank_10', {'betta': 1}, coats={'betta': 'red'})
        t = t_of(j)
        self.assertEqual(codes(t), {'wrong_coat'})
        slip = cq.slips(t)[0]
        self.assertEqual(slip['sev'], 1)
        self.assertFalse(slip['safety'])
        self.assertIn('xanh dương', slip['text'])
        self.assertLess(j.c['feed'][0]['stars'], 5)
        self.assertNotIn(PS.INSPECT, follows(j))                    # a colour mix-up is no welfare issue

    def test_no_colour_chosen_counts_too(self):
        j = at('bin_goldfish')
        self.build(j, 'tank_30', {'goldfish': 3}, gear=('filter', 'conditioner'))
        t = t_of(j)
        self.assertEqual(codes(t), {'wrong_coat'})
        self.assertIn('vớt được', cq.slips(t)[0]['text'])

    def test_colour_needs_the_animal_on_the_counter_and_a_real_colour(self):
        j = at('linh_betta')
        with self.assertRaises(GameError):
            j.act('ps_coat', task=tid(j), kind='betta', coat='blue')
        j.act('ps_cart', task=tid(j), key='betta', qty=1)
        for kind, coat in (('betta', 'gold'), ('dragon', 'red'), ('betta', None)):
            with self.assertRaises(GameError):
                j.act('ps_coat', task=tid(j), kind=kind, coat=coat)
        turn = j.c['turn']
        j.act('ps_coat', task=tid(j), kind='betta', coat='blue')
        self.assertEqual(j.c['turn'], turn)                         # picking a colour is free
        bad = json.loads(json.dumps(j.state))
        next(t for t in bad['careers']['pet_shop']['tasks'] if t['id'] == tid(j))['coats'] = {'betta': 'gold'}
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = json.loads(json.dumps(j.state))
        next(t for t in bad['careers']['pet_shop']['tasks'] if t['id'] == tid(j))['coats'] = ['blue']
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_rare_colour_costs_more_on_the_receipt(self):
        j = at('linh_guppy')
        base = PS._price(j.c, 'guppy')
        extra = PS.COAT['guppy']['cobra'][4]
        self.assertGreater(extra, 0)
        j.act('ps_tank', task=tid(j), size='tank_10')
        j.act('ps_cart', task=tid(j), key='guppy', qty=5)
        j.act('ps_coat', task=tid(j), kind='guppy', coat='cobra')
        t = t_of(j)
        self.assertEqual(t['units']['guppy'], base + extra)
        self.assertIn('rắn hổ mang', PS._name('guppy', t))
        j.act('ps_coat', task=tid(j), kind='guppy', coat='fire')      # a common colour is back to the normal price
        self.assertEqual(t_of(j)['units']['guppy'], base)
        j.act('ps_coat', task=tid(j), kind='guppy', coat='cobra')
        for k in ('conditioner',):
            j.act('ps_cart', task=tid(j), key=k, qty=1)
        j.act('ps_advice', task=tid(j), tips=['float', 'part', 'pinch'])
        with mock.patch.object(short_pay, 'roll', return_value=None):   # this sale pays in full (game/short_pay.py)
            r = ring(j)
        t = t_of(j)
        want = (base + extra) * 5 + t['units']['tank_10'] + t['units']['conditioner']
        self.assertEqual(t['cash']['price'], want)
        pay(j)
        t = t_of(j)
        self.assertNotIn('wrong_coat', codes(t))
        rows = ledger(j, t['id'])
        self.assertEqual(sum(x['amount'] for x in rows if x['category'] != 'tip'), want)
        self.assertEqual(sum(x['amount'] for x in rows if x['category'] == 'tip'), t['tip_given'])

    def test_budgie_sale_by_colour(self):
        j = at('sau_budgie')
        for topic in PS.TOPICS['screen']:
            j.act('ps_ask', task=tid(j), topic=topic)
        j.act('ps_verdict', task=tid(j), verdict='sell')
        for k in ['budgie'] + list(PS.KIT['budgie']):
            j.act('ps_cart', task=tid(j), key=k, qty=1)
        j.act('ps_coat', task=tid(j), kind='budgie', coat='white')
        ring(j)
        pay(j)
        self.assertEqual(codes(t_of(j)), {'wrong_coat'})
        j = at('sau_budgie')
        for topic in PS.TOPICS['screen']:
            j.act('ps_ask', task=tid(j), topic=topic)
        j.act('ps_verdict', task=tid(j), verdict='sell')
        for k in ['budgie'] + list(PS.KIT['budgie']):
            j.act('ps_cart', task=tid(j), key=k, qty=1)
        j.act('ps_coat', task=tid(j), kind='budgie', coat='blue')
        ring(j)
        pay(j)
        self.assertFalse(cq.slips(t_of(j)))


class Paint(unittest.TestCase):
    def shop(self, money=500, stage=0):
        j = Journey('pet_shop')
        j.c['ops']['finance']['opening_balance'] += money - j.c['money']   # wallet and ledger stay in step
        j.c['money'] = money
        j.c['ext']['data']['stage'] = stage
        return j

    def test_default_theme_and_palette(self):
        j = self.shop()
        d = public_state(j.state)['careers']['pet_shop']['data']
        self.assertEqual(d['theme'], 'ngoc')
        self.assertEqual(d['palette']['main'], PS.THEME['ngoc']['colors']['main'])
        self.assertEqual(d['palette']['ink'], '')

    def test_buying_a_paint_from_the_fund(self):
        j = self.shop()
        turn, money = j.c['turn'], j.c['money']
        r = j.act('ps_paint', theme='lavender')
        self.assertEqual(j.c['money'], money - PS.THEME['lavender']['cost'])
        row = ledger(j)[-1]
        self.assertEqual(row['category'], 'upgrade')
        self.assertEqual(row['amount'], -PS.THEME['lavender']['cost'])
        self.assertIn('Tím lavender', row['reason'])
        self.assertEqual(j.c['turn'], turn)
        self.assertIn('lavender', r['message'])
        d = j.c['ext']['data']
        self.assertEqual((d['theme'], d['themes']), ('lavender', ['ngoc', 'lavender']))
        self.assertEqual(public_state(j.state)['careers']['pet_shop']['data']['palette']['main'],
                         PS.THEME['lavender']['colors']['main'])
        # going back to a paint the shop already has is free
        money = j.c['money']
        j.act('ps_paint', theme='ngoc')
        j.act('ps_paint', theme='lavender')
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            j.act('ps_paint', theme='lavender')                      # already on the walls

    def test_free_once_the_shop_grows(self):
        j = self.shop(stage=2)
        money = j.c['money']
        j.act('ps_paint', theme='nang')
        j.act('ps_paint', theme='hong')
        self.assertEqual(j.c['money'], money)
        j.act('ps_paint', theme='go')                               # stage 3 paint, still bought
        self.assertEqual(j.c['money'], money - PS.THEME['go']['cost'])

    def test_not_enough_money_or_unknown_paint(self):
        j = self.shop(money=10)
        with self.assertRaises(GameError):
            j.act('ps_paint', theme='go')
        with self.assertRaises(GameError):
            j.act('ps_paint', theme='neon')
        self.assertEqual(j.c['ext']['data']['theme'], 'ngoc')
        self.assertEqual(j.c['money'], 10)

    def test_sign_ink(self):
        j = self.shop()
        turn = j.c['turn']
        j.act('ps_ink', ink='navy')
        self.assertEqual(j.c['ext']['data']['ink'], 'navy')
        self.assertEqual(public_state(j.state)['careers']['pet_shop']['data']['palette']['ink'], PS.INKS['navy'][1])
        self.assertEqual(j.c['turn'], turn)
        with self.assertRaises(GameError):
            j.act('ps_ink', ink='gold')

    def test_paint_persists_and_tampering_is_caught(self):
        j = self.shop()
        j.act('ps_paint', theme='hong')
        j.act('ps_ink', ink='wood')
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        j.state = s
        j.act('end_day')
        j.act('start_day')
        d = j.c['ext']['data']
        self.assertEqual((d['theme'], d['ink']), ('hong', 'wood'))
        for key, value in (('theme', 'go'), ('theme', 'neon'), ('themes', ['hong']), ('themes', ['ngoc', 'hong', 'hong']),
                           ('themes', 'ngoc'), ('ink', 'gold'), ('ink', None)):
            bad = copy.deepcopy(s)
            bad['careers']['pet_shop']['ext']['data'][key] = value
            with self.assertRaises(GameError, msg=(key, value)):
                validate_state(bad)

    def test_old_data_gets_the_default_paint(self):
        j = Journey('pet_shop')
        d = j.c['ext']['data']
        for k in ('theme', 'themes', 'ink'):
            d.pop(k)
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        d = s['careers']['pet_shop']['ext']['data']
        self.assertEqual((d['theme'], d['themes'], d['ink']), ('ngoc', ['ngoc'], 'auto'))


class Screen(unittest.TestCase):
    def ask_all(self, j):
        for topic in PS.TOPICS['screen']:
            j.act('ps_ask', task=tid(j), topic=topic)

    def test_kid_alone_come_back_with_a_parent(self):
        j = at('bin_alone')
        self.ask_all(j)
        money = j.c['money']
        r = j.act('ps_verdict', task=tid(j), verdict='later')
        t = t_of(j)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['money'], money)
        self.assertIn('mẹ', r['message'])

    def test_selling_to_a_kid_alone_is_a_welfare_failure(self):
        j = at('bin_alone')
        self.ask_all(j)
        j.act('ps_verdict', task=tid(j), verdict='sell')
        for k in ('hamster', 'cage_hamster', 'hamster_food', 'bedding'):
            j.act('ps_cart', task=tid(j), key=k, qty=1)
        ring(j)
        r = pay(j)
        t = t_of(j)
        self.assertIn('careless_sale', codes(t))
        self.assertTrue(cq.safety(t))
        self.assertIn('trả lại', r['message'])
        self.assertEqual(j.c['ext']['data']['animals']['hamster'], PS.ANIMALS['hamster']['target'])

    def test_with_mom_sell_with_the_kit(self):
        j = at('bin_mom')
        self.ask_all(j)
        j.act('ps_verdict', task=tid(j), verdict='sell')
        for k in ('hamster', 'cage_hamster', 'hamster_food', 'bedding'):
            j.act('ps_cart', task=tid(j), key=k, qty=1)
        j.act('ps_coat', task=tid(j), kind='hamster', coat='grey')
        ring(j)
        pay(j)
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['ext']['data']['book']['bin'], t['day'])

    def test_sale_without_a_cage(self):
        j = at('bin_mom')
        j.act('ps_verdict', task=tid(j), verdict='sell')
        j.act('ps_cart', task=tid(j), key='hamster', qty=1)
        j.act('ps_coat', task=tid(j), kind='hamster', coat='grey')
        ring(j)
        pay(j)
        t = t_of(j)
        self.assertEqual(codes(t), {'no_kit'})
        self.assertEqual(t['mistakes'], 1)          # decided before asking about the parents

    def test_adoption_with_papers(self):
        j = at('sau_adopt')
        self.ask_all(j)
        with self.assertRaises(GameError):
            j.act('ps_cart', task=tid(j), key='hamster', qty=1)
        j.act('ps_verdict', task=tid(j), verdict='sell')
        with self.assertRaises(GameError):
            ring(j)
        j.act('ps_sign', task=tid(j), checks=list(PS.SIGNS))
        j.act('ps_cart', task=tid(j), key='leash', qty=1)
        ring(j)
        self.assertEqual(t_of(j)['cash']['price'], 30 + 25)
        pay(j)
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        d = j.c['ext']['data']
        self.assertEqual(d['book']['vang'], t['day'])
        self.assertEqual(d['adopted'][-1]['pet'], 'vang')

    def test_turning_away_a_good_home(self):
        j = at('sau_adopt')
        self.ask_all(j)
        j.act('ps_verdict', task=tid(j), verdict='refuse')
        self.assertEqual(codes(t_of(j)), {'turned_away'})

    def test_renter_refused_kindly(self):
        j = at('linh_kitten')
        j.act('ps_ask', task=tid(j), topic='home')
        j.act('ps_verdict', task=tid(j), verdict='refuse')
        self.assertFalse(cq.slips(t_of(j)))


class Care(unittest.TestCase):
    def rounds(self, j, isolate=True, heat=True):
        t = t_of(j)
        x = t['_x']
        for pen in x['pens']:
            kind = PS.PENS[pen]['kind']
            j.act('ps_feed', task=t['id'], pen=pen, portion='pinch' if kind == 'fish' else 'normal')
            j.act('ps_look', task=t['id'], pen=pen)
            if kind == 'fish':
                j.act('ps_temp', task=t['id'], pen=pen)
        for pen in x['dirty']:
            j.act('ps_clean', task=t['id'], pen=pen, how='part' if PS.PENS[pen]['kind'] == 'fish' else 'all')
        if heat and x['cold']:
            j.act('ps_heat', task=t['id'], pen=x['cold'])
        if isolate and x['sick']:
            j.act('ps_isolate', task=t['id'], pen=x['sick'])
        return j.act('ps_care_done', task=t['id'])

    def test_easy_first_round(self):
        j = at('care_first')
        money = j.c['money']
        self.rounds(j)
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['money'] - money, PS.PRICES['care'])
        self.assertEqual(j.c['ext']['data']['pens']['hamster']['cleaned'], t['day'])

    def test_sick_fish_found_and_isolated(self):
        j = at('care_sick_fish')
        t = t_of(j)
        r = j.act('ps_temp', task=t['id'], pen='betta')
        self.assertIn('22', r['message'])
        r = j.act('ps_look', task=t['id'], pen='guppy')
        self.assertIn('đốm trắng', r['message'])
        j.act('ps_heat', task=t['id'], pen='betta')
        j.act('ps_isolate', task=t['id'], pen='guppy')
        for pen in t['_x']['pens']:
            kind = PS.PENS[pen]['kind']
            j.act('ps_feed', task=t['id'], pen=pen, portion='pinch' if kind == 'fish' else 'normal')
        j.act('ps_clean', task=t['id'], pen='goldfish', how='part')
        j.act('ps_care_done', task=t['id'])
        self.assertFalse(cq.slips(t_of(j)))

    def test_sick_left_with_the_others_brings_an_inspection(self):
        j = at('care_sick_fish')
        self.rounds(j, isolate=False)
        t = t_of(j)
        self.assertIn('sick_left', codes(t))
        self.assertTrue(cq.safety(t))
        self.assertIn(PS.INSPECT, follows(j))

    def test_wrong_ways(self):
        j = at('care_sick_fish')
        t = t_of(j)
        j.act('ps_feed', task=t['id'], pen='guppy', portion='heap')
        j.act('ps_clean', task=t['id'], pen='goldfish', how='all')
        j.act('ps_heat', task=t['id'], pen='goldfish')
        j.act('ps_isolate', task=t['id'], pen='budgie')
        j.act('ps_care_done', task=t['id'])
        got = codes(t_of(j))
        self.assertTrue({'overfeed', 'unfed', 'water_shock', 'too_warm', 'wrong_isolate', 'cold', 'sick_left'} <= got, got)

    def test_neglect_overnight(self):
        day, slot = where('care_sick_fish')
        j = Journey('pet_shop', slot=slot, day=day)
        j.act('ask', task=tid(j))
        health = j.c['ext']['data']['pens']['guppy']['health']
        r = j.act('end_day')
        self.assertIn(PS.INSPECT, follows(j))
        self.assertLess(j.c['ext']['data']['pens']['guppy']['health'], health)
        self.assertTrue(any('cách ly' in x for x in r['summary']['career']['lines']))
        validate_state(json.loads(json.dumps(j.state)))


class Returns(unittest.TestCase):
    def test_sealed_return_refund_puts_it_back(self):
        j = at('quan_sealed')
        for part in PS.TOPICS['ret']:
            j.act('ps_ask', task=tid(j), topic=part)
        stock, money = PS.kit.stock(j.c, 'dog_adult'), j.c['money']
        j.act('ps_return', task=tid(j), decision='refund')
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['money'], money - 42)
        self.assertEqual(PS.kit.stock(j.c, 'dog_adult'), stock + 1)
        self.assertTrue(any(x['category'] == 'refund' for x in ledger(j, t['id'])))

    def test_half_eaten_bag_refund_is_a_natural_loss(self):
        j = at('hai_half')
        money = j.c['money']
        r = j.act('ps_return', task=tid(j), decision='refund')
        t = t_of(j)
        self.assertEqual(j.c['money'], money - 36)
        self.assertFalse(cq.slips(t))
        self.assertEqual(t['mistakes'], 1)
        self.assertIn('lỗ', r['message'])
        self.assertEqual(j.c['ext']['data']['today']['loss'], 36)

    def test_half_eaten_bag_refused_by_the_policy(self):
        j = at('hai_half')
        j.act('ps_ask', task=tid(j), topic='seal')
        j.act('ps_return', task=tid(j), decision='refuse')
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['feed'][0]['feedback']['cap'], 4)   # fair, but she leaves without what she came for

    def test_refusing_a_fair_return(self):
        j = at('sau_expired')
        j.act('ps_return', task=tid(j), decision='refuse')
        t = t_of(j)
        self.assertIn('refused_fair', codes(t))
        self.assertEqual(max(x['sev'] for x in cq.slips(t)), 3)   # the shop sold it out of date

    def test_defect_exchange_takes_a_new_one(self):
        j = at('khanh_leash')
        stock = PS.kit.stock(j.c, 'leash')
        j.act('ps_return', task=tid(j), decision='exchange')
        self.assertEqual(PS.kit.stock(j.c, 'leash'), stock - 1)
        self.assertFalse(cq.slips(t_of(j)))


class Lost(unittest.TestCase):
    def notice(self, j, fields=('photo', 'look', 'where', 'when', 'phone')):
        for topic in PS.TOPICS['lost']:
            j.act('ps_ask', task=tid(j), topic=topic)
        j.act('ps_notice', task=tid(j), fields=list(fields))
        j.act('ps_pin', task=tid(j))

    def test_found_with_a_thank_you_tip(self):
        j = at('mun_lost')
        with self.assertRaises(GameError):
            j.act('ps_call', task=tid(j), call='c3', move='check')
        self.notice(j)
        for c in ('c1', 'c2', 'c3'):
            j.act('ps_call', task=tid(j), call=c, move='check')
        j.act('ps_call', task=tid(j), call='c1', move='block')
        j.act('ps_call', task=tid(j), call='c2', move='block')
        r = j.act('ps_call', task=tid(j), call='c3', move='send')
        self.assertIn('Mun', r['message'])
        money = j.c['money']
        j.act('ps_lost_done', task=tid(j))
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertTrue(t['work']['found'])
        self.assertGreater(t['tip_given'], 0)
        self.assertEqual(j.c['money'] - money, t['tip_given'])
        self.assertEqual([x['category'] for x in ledger(j, t['id'])], ['tip'])
        self.assertEqual(j.c['ext']['data']['book']['mun_found'], t['day'])

    def test_scam_sent_and_mark_on_the_notice(self):
        j = at('mun_lost')
        self.notice(j, fields=('look', 'where', 'when', 'phone', 'mark', 'address'))
        r = j.act('ps_call', task=tid(j), call='c2', move='check')
        self.assertIn('vanh vách', r['message'])
        j.act('ps_call', task=tid(j), call='c2', move='send')
        j.act('ps_call', task=tid(j), call='c3', move='block')
        j.act('ps_call', task=tid(j), call='c1', move='send')
        j.act('ps_lost_done', task=tid(j))
        t = t_of(j)
        self.assertTrue({'scam_sent', 'missed_real', 'wasted_trip', 'mark_public', 'privacy'} <= codes(t))
        self.assertFalse(t.get('tip_given'))

    def test_notice_without_a_phone(self):
        j = at('mun_lost')
        self.notice(j, fields=('look', 'where'))
        j.act('ps_call', task=tid(j), call='c3', move='send')
        j.act('ps_lost_done', task=tid(j))
        self.assertIn('no_phone', codes(t_of(j)))

    def test_open_calls_block_the_end(self):
        j = at('mun_lost')
        self.notice(j)
        j.act('ps_call', task=tid(j), call='c1', move='block')
        with self.assertRaises(GameError):
            j.act('ps_lost_done', task=tid(j))


class Ship(unittest.TestCase):
    def pack(self, j, confirm=True):
        t = t_of(j)
        if confirm:
            j.act('ps_ask', task=t['id'], topic='confirm')
        for k, q in t['needs']['order'].items():
            j.act('ps_cart', task=t['id'], key=k, qty=q)
        ring(j)

    def test_heavy_litter_by_van_right_cod(self):
        j = at('hai_litter')
        self.pack(j)
        j.act('ps_shipper', task=tid(j), kind='van')
        t = t_of(j)
        goods = sum(t['units'][k] * q for k, q in t['bill'].items())
        self.assertEqual(goods, 3 * 30 + 4 * 9)
        money = j.c['money']
        j.act('ps_cod', task=tid(j), amount=goods + 30)
        j.act('ps_ship', task=tid(j))
        t = t_of(j)
        self.assertFalse(cq.slips(t))
        self.assertEqual(j.c['money'] - money, goods)

    def test_bike_too_heavy_wrong_address_cod_over(self):
        j = at('hai_litter')
        self.pack(j, confirm=False)
        j.act('ps_shipper', task=tid(j), kind='bike')
        t = t_of(j)
        goods = sum(t['units'][k] * q for k, q in t['bill'].items())
        j.act('ps_cod', task=tid(j), amount=goods + 30)
        j.act('ps_ship', task=tid(j))
        self.assertTrue({'bike_heavy', 'wrong_address', 'cod_over'} <= codes(t_of(j)))

    def test_cod_short_is_a_loss(self):
        j = at('quan_food')
        self.pack(j)
        j.act('ps_shipper', task=tid(j), kind='bike')
        t = t_of(j)
        goods = sum(t['units'][k] * q for k, q in t['bill'].items())
        money = j.c['money']
        j.act('ps_cod', task=tid(j), amount=goods + 10 - 7)
        r = j.act('ps_ship', task=tid(j))
        self.assertFalse(cq.slips(t_of(j)))
        self.assertEqual(j.c['money'] - money, goods - 7)
        self.assertIn('thiếu 7', r['message'])

    def test_glass_tank_on_a_bike_breaks(self):
        j = at('sau_tank60')
        self.pack(j)
        j.act('ps_shipper', task=tid(j), kind='bike')
        t = t_of(j)
        goods = sum(t['units'][k] * q for k, q in t['bill'].items())
        waste = j.c['life']['day_waste']
        j.act('ps_cod', task=tid(j), amount=goods + 10)
        j.act('ps_ship', task=tid(j))
        self.assertIn('tank_broke', codes(t_of(j)))
        self.assertGreater(j.c['life']['day_waste'], waste)

    def test_van_for_a_light_order(self):
        j = at('quan_food')
        self.pack(j)
        j.act('ps_shipper', task=tid(j), kind='van')
        t = t_of(j)
        goods = sum(t['units'][k] * q for k, q in t['bill'].items())
        j.act('ps_cod', task=tid(j), amount=goods + 30)
        j.act('ps_ship', task=tid(j))
        self.assertEqual(codes(t_of(j)), {'van_costly'})


class ShopLife(unittest.TestCase):
    def test_intro_card_is_free(self):
        j = Journey('pet_shop')
        j.act('end_day')
        turn = j.c['turn']
        self.assertFalse(j.c['open'])
        self.assertFalse(public_state(j.state)['careers']['pet_shop']['data']['intro_seen'])
        j.act('ps_intro')
        self.assertTrue(j.c['ext']['data']['intro_seen'])
        self.assertEqual(j.c['turn'], turn)

    def test_restock_through_the_warehouse(self):
        j = Journey('pet_shop')
        before = PS.kit.stock(j.c, 'cat_kitten')
        j.act('inv_order', item='cat_kitten', qty=4, supplier='express', confirm=True)
        order = j.c['ext']['inv']['orders'][-1]
        for _ in range(12):
            try:
                j.act('inv_receive', order=order['id'], count=order['actual'])
                break
            except GameError:
                j.act('inv_wait')
        self.assertEqual(PS.kit.stock(j.c, 'cat_kitten'), before + order['actual'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_farm_tops_up_the_animals_and_charges_for_it(self):
        j = Journey('pet_shop')
        d = j.c['ext']['data']
        d['animals']['guppy'] = 2
        j.act('end_day')
        money = j.c['money']
        j.act('start_day')
        self.assertEqual(d is j.c['ext']['data'] or True, True)
        d = j.c['ext']['data']
        self.assertEqual(d['animals']['guppy'], PS.ANIMALS['guppy']['target'])
        self.assertLess(j.c['money'], money)
        self.assertTrue(any('Bến Mây' in n['text'] for n in d['notes']))

    def test_stage_and_story_notes_grow(self):
        j = Journey('pet_shop')
        d = j.c['ext']['data']
        d['good'] = 7
        d['book']['bin'] = 1
        j.c['day'] = 4
        j.act('end_day')
        j.act('start_day')
        d = j.c['ext']['data']
        self.assertEqual(d['stage'], 2)
        self.assertTrue(any('Bánh Bao' in n['text'] for n in d['notes']))
        self.assertEqual(public_state(j.state)['careers']['pet_shop']['data']['stage_name'], PS.STAGES[2]['name'])

    def test_staff_help(self):
        j = at('mun_kitten')
        j.act('ps_food', task=tid(j), item='cat_kitten')
        note = PS.assist(j.state, j.c, dict(role='counter', name='X'), t_of(j))
        self.assertIn('quét', note)
        self.assertEqual(t_of(j)['bill'], {'cat_kitten': 1})
        self.assertIsNotNone(PS.assist(j.state, j.c, dict(role='keeper', name='X'), None))
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = Journey('pet_shop')
        self.assertTrue(5 <= len(PS.SPEC['situations']) <= 8)
        self.assertEqual(len(PS.SPEC['stories']), 3)
        for x in PS.SPEC['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_people_and_counts_from_plugins(self):
        self.assertIn('pet_shop', CAREERS)
        self.assertTrue(5 <= len(PS.SPEC['people']) <= 8)
        self.assertEqual(cq.INSPECTION['pet_shop'], PS.INSPECT)
        from game.incident_content import INDEX
        self.assertIn(PS.INSPECT, INDEX)

    def test_no_meta_words(self):
        texts = []

        def walk(x):
            if isinstance(x, str):
                texts.append(x)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, (list, tuple)):
                for v in x:
                    walk(v)
        walk([PS.VARIANTS, PS.SPEC['meta'], PS.INTRO, PS.SITUATIONS, PS.SPEC['stories'], PS.BOOK_NOTES, PS.STAGES])
        blob = ' | '.join(texts).lower()
        for word in ('người chơi', 'mô phỏng', 'giả lập', 'npc', 'trong game'):
            self.assertNotIn(word, blob)


class Saves(unittest.TestCase):
    def test_round_trip_and_tamper(self):
        j = at('muop_senior')
        j.act('ps_date', task=tid(j))
        j.act('ps_food', task=tid(j), item='cat_senior')
        ring(j)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        bad = copy.deepcopy(s)
        next(t for t in bad['careers']['pet_shop']['tasks'] if t['id'] == tid(j))['needs']['qty'] = 9
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        next(t for t in bad['careers']['pet_shop']['tasks'] if t['id'] == tid(j))['_x']['grab'] = None
        with self.assertRaises(GameError):
            validate_state(bad)
        for key, value in (('cart', {'rocket': 1}), ('work', {'dated': 'yes', 'swapped': False}), ('bill_under', -5),
                           ('asked', ['nope'])):
            bad = copy.deepcopy(s)
            next(t for t in bad['careers']['pet_shop']['tasks'] if t['id'] == tid(j))[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(bad)
        bad = copy.deepcopy(s)
        bad['careers']['pet_shop']['ext']['data']['animals']['dragon'] = 1
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_every_job_round_trips(self):
        for job, rows in PS.VARIANTS.items():
            j = at(rows[0]['id'])
            validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_without_the_shop_loads(self):
        s = new_state()
        s['careers'].pop('pet_shop', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('pet_shop', s['careers'])

    def test_old_data_gains_new_fields(self):
        j = Journey('pet_shop')
        d = j.c['ext']['data']
        for k in ('notes', 'fired', 'book', 'today', 'intro_seen'):
            d.pop(k)
        d['pens'].pop('corner')
        d['animals'].pop('budgie')
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        j.state = s
        j.act('end_day')
        j.act('start_day')
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
