"""Nấu cơm gia đình (plugin career naucom): the family's request, the menu (one canh, one mặn, one xào, one rau,
checked against the child, the elder or the diet and kept inside the market money), the market (looking, asking
for another piece, buying enough portions, haggling once, the receipt), the kitchen (the rice cooker's water line,
bowls, the bowl of nước mắm, every dish washed, cut, seasoned, on the right flame and stopped in time, two
burners, food going cold), the market book and the pay (more for a bigger family, more each time a family asks
for you again), the extra dish later in the day, surprises, determinism, save validation and old saves."""
import copy
import itertools
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game import x3_week as x3
from game.careers import kit, PLUGINS
from game.content import CAREERS
from game.content import initial_career, make_task
from game.engine import GameError, migrate_state, public_state, validate_state

NC = PLUGINS.get('naucom')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def best_menu(n):
    """The cheapest menu that suits the family (what a careful cook plans)."""
    groups = [[k for k in NC.MENU_DISHES if NC.DISHES[k]['group'] == g] for g in NC.GROUP_ORDER]
    menus = [dict(zip(NC.GROUP_ORDER, c)) for c in itertools.product(*groups)]
    ok = [m for m in menus if NC._fits(m, n['con'], n['taste'])]
    return min(ok, key=lambda m: (NC.menu_cost(m, n['n'], n['mod']), sorted(m.values())))


def day_of(fam=None, mod=None, days=range(1, 60)):
    for day in days:
        n = make_task('naucom', day, 0, 1)['needs']
        if (fam is None or n['fam'] == fam) and (mod is None or n['mod'] == mod):
            return day
    raise AssertionError(f'no day for {fam} {mod}')


class Base(unittest.TestCase):
    def setUp(self):
        if NC is None:
            raise unittest.SkipTest('naucom is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot=0):
        self.j = Journey('naucom', slot=slot, day=day)
        NC._data(self.j.c)['intro'] = True
        return self.j.task

    def act(self, name, **p):
        r = self.j.act(name, **p)
        self.settle_desk()
        return r

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('nc_desk', option=NC.kit.desk_script(NC.DESK, ev['script'])['default'])

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}

    # ---------------------------------------------------------------- the careful way, step by step
    def plan(self, tid, menu=None):
        self.act('ask', task=tid)
        n = self.j.get(tid)['needs']
        menu = menu or best_menu(n)
        for g, k in menu.items():
            self.act('nc_pick', task=tid, group=g, dish=k)
        return self.act('nc_plan', task=tid)

    def shop(self, tid, look=True, receipts=True, n=None):
        t = self.j.get(tid)
        for ing in list(t['cart']):
            if look:
                self.act('nc_look', task=tid, ing=ing)
                if self.j.get(tid)['_key']['lots'][ing] == 'uon':
                    self.act('nc_swap', task=tid, ing=ing)
            self.act('nc_buy', task=tid, ing=ing, n=n or NC.portions(t['needs']['n']))
        if receipts:
            for st in self.j.get(tid)['bills']:
                self.act('nc_receipt', task=tid, stall=st)
        return self.act('nc_home', task=tid)

    def cook(self, tid, dish, cut=None, nem=None, heat=None, secs=None, wash=True):
        t = self.j.get(tid)
        D = NC.DISHES[dish]
        if wash:
            self.act('nc_wash', task=tid, dish=dish)
        self.act('nc_cut', task=tid, dish=dish, cut=cut or NC.want_cut(t['needs'], dish) or 'vua')
        if D['method'] == 'song':
            return None
        self.act('nc_nem', task=tid, dish=dish, nem=nem or NC.want_nem(t['needs'], dish))
        self.act('nc_fire', task=tid, dish=dish, heat=heat or D['heat'])
        lo, hi = NC.METHODS[D['method']]['ok']
        self.clock.t += (lo + hi) / 2 if secs is None else secs
        return self.act('nc_off', task=tid, dish=dish)

    def kitchen(self, tid, water=None, bowls=None, fix=True):
        t = self.j.get(tid)
        n = t['needs']
        self.act('nc_rice', task=tid, water=water or NC.CONS[n['con']]['water'])
        self.act('nc_bowls', task=tid, n=bowls or n['n'])
        self.act('nc_taste', task=tid)
        q = self.j.get(tid)['table']['mam']
        if fix and q != 'ok':
            self.act('nc_fix', task=tid, add={'man': 'nuoc', 'lat': 'mam', 'ngot': 'chanh', 'chua': 'duong'}[q])
        for k in sorted(t['dishes'], key=lambda k: -NC.METHODS[NC.DISHES[k]['method']]['ok'][1]):
            self.cook(tid, k)
        self.clock.t += NC.RICE_S

    def settle(self, tid):
        for st in self.j.get(tid)['bills']:
            self.act('nc_file', task=tid, stall=st)
        return self.act('nc_done', task=tid)

    def meal(self, tid):
        self.plan(tid)
        self.shop(tid)
        self.kitchen(tid)
        r = self.act('nc_serve', task=tid)
        self.assertEqual(self.j.get(tid)['stage'], 'settle', r)
        return self.settle(tid)


class Spec(Base):
    def test_spec_shape(self):
        s = NC.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('naucom', 'nc_', 'food'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('naucom', jr.CH_UNLOCKS[2])
        self.assertIn('naucom', CAREERS)
        for name in NC.ACTIONS:
            self.assertTrue(name.startswith('nc_'))
        for name in (*NC.NO_TICK, *NC.TICKING, *NC.FREE):
            self.assertTrue(name in NC.ACTIONS or name in ('nc_intro', 'nc_desk'), name)
        self.assertEqual(NC.PHYSICAL, ())          # nobody queues at a family's kitchen

    def test_tasks_are_deterministic_and_cover_every_family(self):
        fams, mods, kinds = set(), set(), set()
        for day in range(1, 40):
            for slot in range(0, 4):
                a, b = make_task('naucom', day, slot, 3), make_task('naucom', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
            n = make_task('naucom', day, 0, 1)['needs']
            fams.add(n['fam'])
            mods.add(n['mod'])
            self.assertGreater(n['budget'], NC.cheapest(n['n'], n['con'], n['taste'], n['mod']))
        self.assertEqual(fams, set(NC.FAM))
        self.assertEqual(mods, set(NC.MOD))
        self.assertEqual(kinds, set(NC.KINDS))

    def test_the_first_day_is_chi_mai_and_a_stale_fish(self):
        t = make_task('naucom', 1, 0, 1)
        self.assertEqual(t['needs']['fam'], 'mai')
        self.assertEqual(t['needs']['mod'], 'normal')
        self.assertEqual(t['_key']['lots']['ca_loc'], 'uon')
        self.assertNotEqual(t['_key']['mam'], 'ok')

    def test_the_same_family_never_comes_two_days_running(self):
        fams = [make_task('naucom', d, 0, 1)['needs']['fam'] for d in range(1, 60)]
        self.assertFalse(any(a == b for a, b in zip(fams, fams[1:])))

    def test_every_family_can_eat_well_inside_its_money(self):
        for f in NC.FAMILIES:
            for mod in NC.MOD:
                n = dict(n=f['n'] + 2, con=f['con'], taste=f['taste'], mod=mod)
                low = NC.cheapest(n['n'], n['con'], n['taste'], mod)
                self.assertIsNotNone(low, (f['id'], mod))
                self.assertLess(low, NC.budget_for(n['n'], n['con'], n['taste'], mod))

    def test_scripts_are_well_formed(self):
        for x in NC.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in NC.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for s in NC.SITUATIONS:
            facts = {f['id'] for f in s['facts']}
            for o in s['options']:
                self.assertTrue(set(o.get('requires', [])) <= facts, (s['id'], o['id']))
        for e in NC.EXTRAS:
            self.assertIn(e[0], NC.FAM)
            self.assertIn(e[1], NC.DISHES)

    def test_new_career_joins_x3_on_its_own_day(self):
        self.assertNotIn('naucom', x3.FIRST)
        for w in range(10):
            days = x3.week(x3.now() + w * 7 * 86400)[1]
            self.assertEqual(sum(d.count('naucom') for d in days), 1)

    def test_content_is_plain_json(self):
        json.dumps(NC.content())


class Plan(Base):
    def test_a_menu_needs_all_four_groups_and_fits_the_money(self):
        t = self.at(1)
        self.act('ask', task=t['id'])
        self.act('nc_pick', task=t['id'], group='canh', dish='canh_chua')
        with self.assertRaises(GameError):
            self.act('nc_plan', task=t['id'])
        for g, k in (('man', 'thit_kho'), ('xao', 'bo_xao'), ('rau', 'rau_muong_luoc')):
            self.act('nc_pick', task=t['id'], group=g, dish=k)
        self.act('nc_pick', task=t['id'], group='man', dish='trung_hap')
        with self.assertRaises(GameError):           # a dish from another group
            self.act('nc_pick', task=t['id'], group='xao', dish='tom_rim')
        self.act('nc_pick', task=t['id'], group='man', dish='tom_rim')
        n = self.j.get(t['id'])['needs']
        self.assertGreater(NC.menu_cost(self.j.get(t['id'])['menu'], n['n'], n['mod']), n['budget'])
        with self.assertRaises(GameError):
            self.act('nc_plan', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['stage'], 'plan')

    def test_tapping_a_chosen_dish_takes_it_off(self):
        t = self.at(1)
        self.act('ask', task=t['id'])
        self.act('nc_pick', task=t['id'], group='canh', dish='canh_bi')
        self.act('nc_pick', task=t['id'], group='canh', dish='canh_bi')
        self.assertEqual(self.j.get(t['id'])['menu'], {})

    def test_a_spicy_dish_for_be_bin_and_no_sour_soup_are_named(self):
        t = self.at(1)
        self.plan(t['id'], dict(canh='canh_bi', man='trung_hap', xao='ga_xao_sa', rau='cai_luoc'))
        self.assertEqual(self.codes(t['id']), {'clash', 'taste'})
        self.assertEqual(self.j.get(t['id'])['stage'], 'market')

    def test_salty_and_chewy_for_ong_toan(self):
        t = self.at(day_of('toan'))
        self.plan(t['id'], dict(canh='canh_bi', man='thit_kho', xao='bi_xao', rau='cai_luoc'))
        self.assertIn('clash', self.codes(t['id']))
        t2 = self.at(day_of('khoa'))
        self.plan(t2['id'], dict(canh='canh_bi', man='ga_chien', xao='ga_xao_sa', rau='cai_luoc'))
        self.assertEqual(self.codes(t2['id']), {'clash'})

    def test_the_plan_needs_the_request_first(self):
        t = self.at(1)
        with self.assertRaises(GameError):
            self.j.act('nc_pick', task=t['id'], group='canh', dish='canh_chua')


class Market(Base):
    def test_the_cart_holds_one_portion_for_every_two_people(self):
        t = self.at(1)
        self.plan(t['id'])
        t = self.j.get(t['id'])
        need = NC.needs_of(t['menu'], t['needs']['n'])
        self.assertEqual(set(t['cart']), set(need))
        self.assertEqual(NC.portions(3), 2)
        self.assertEqual(NC.portions(6), 3)
        self.assertEqual(t['purse'], t['needs']['budget'])

    def test_looking_shows_freshness_only_after_a_look(self):
        t = self.at(1)
        self.plan(t['id'], dict(canh='canh_chua', man='trung_hap', xao='su_su_xao', rau='rau_muong_luoc'))
        view = public_state(self.j.state)['careers']['naucom']['tasks']
        row = next(x for x in view if x['id'] == t['id'])['cart']['ca_loc']
        self.assertNotIn('look', row)
        r = self.act('nc_look', task=t['id'], ing='ca_loc')
        self.assertIn('Mắt đục', r['message'])
        view = public_state(self.j.state)['careers']['naucom']['tasks']
        self.assertEqual(next(x for x in view if x['id'] == t['id'])['cart']['ca_loc']['look'], 'uon')
        self.act('nc_swap', task=t['id'], ing='ca_loc')
        view = public_state(self.j.state)['careers']['naucom']['tasks']
        self.assertEqual(next(x for x in view if x['id'] == t['id'])['cart']['ca_loc']['look'], 'tuoi')
        self.assertNotIn('_key', next(x for x in view if x['id'] == t['id']))

    def test_buying_spends_the_family_money_not_the_wallet(self):
        t = self.at(1)
        self.plan(t['id'])
        money = self.j.c['money']
        t = self.j.get(t['id'])
        ing = next(iter(t['cart']))
        self.act('nc_buy', task=t['id'], ing=ing, n=2)
        t = self.j.get(t['id'])
        self.assertEqual(t['purse'], t['needs']['budget'] - 2 * NC.unit_price(ing, t['needs']['mod']))
        self.assertEqual(self.j.c['money'], money)
        with self.assertRaises(GameError):
            self.act('nc_buy', task=t['id'], ing=ing, n=1)
        self.act('nc_return', task=t['id'], ing=ing)
        self.assertEqual(self.j.get(t['id'])['purse'], t['needs']['budget'])
        with self.assertRaises(GameError):
            self.act('nc_buy', task=t['id'], ing=ing, n=99)

    def test_haggling_once_and_the_receipt(self):
        day = next(d for d in range(2, 60) if make_task('naucom', d, 0, 1)['_key']['haggle']['thit'])
        t = self.at(day)
        self.plan(t['id'])
        tid = t['id']
        t = self.j.get(tid)
        for ing in t['cart']:
            self.act('nc_buy', task=tid, ing=ing, n=NC.portions(t['needs']['n']))
        before = self.j.get(tid)['purse']
        self.act('nc_receipt', task=tid, stall='thit')
        r = self.act('nc_haggle', task=tid, stall='thit')
        t = self.j.get(tid)
        self.assertGreater(t['purse'], before, r)
        self.assertFalse(t['bills']['thit']['receipt'])       # the price changed: ask for the receipt again
        with self.assertRaises(GameError):
            self.act('nc_haggle', task=tid, stall='thit')
        with self.assertRaises(GameError):                   # after a discount, nothing goes back
            self.act('nc_return', task=tid, ing=next(i for i in t['cart'] if NC.INGS[i]['stall'] == 'thit'))
        self.act('nc_receipt', task=tid, stall='thit')
        validate_state(self.j.state)

    def test_home_needs_everything_bought(self):
        t = self.at(1)
        self.plan(t['id'])
        with self.assertRaises(GameError):
            self.act('nc_home', task=t['id'])


class Kitchen(Base):
    def ready(self, day=1):
        t = self.at(day)
        self.plan(t['id'])
        self.shop(t['id'])
        return t['id']

    def test_a_clean_meal_for_chi_mai(self):
        t = self.at(1)
        money = self.j.c['money']
        r = self.meal(t['id'])
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed', r)
        self.assertEqual(self.codes(t['id']), set())
        self.assertEqual(self.j.c['money'] - money >= NC.WAGE_BASE + NC.WAGE_PER * 3, True)
        self.assertEqual(self.d['families']['mai']['visits'], 1)
        self.assertEqual(self.d['stats']['clean'], 1)
        self.assertIn('Gửi lại', r['message'])

    def test_the_stale_fish_reaches_the_table(self):
        t = self.at(1)
        tid = t['id']
        self.plan(tid, dict(canh='canh_chua', man='trung_hap', xao='su_su_xao', rau='rau_muong_luoc'))
        self.shop(tid, look=False)
        self.kitchen(tid)
        self.act('nc_serve', task=tid)
        self.assertIn('stale', self.codes(tid))
        self.assertTrue(any(x['safety'] for x in self.j.get(tid)['slips']))

    def test_the_stove_gauge_decides_the_dish(self):
        tid = self.ready()
        t = self.j.get(tid)
        k = t['menu']['canh']
        r = self.cook(tid, k, secs=2)
        self.assertEqual(self.j.get(tid)['dishes'][k]['q'], 'song', r)
        k = t['menu']['xao']
        self.cook(tid, k, secs=40)
        self.assertEqual(self.j.get(tid)['dishes'][k]['q'], 'chay')
        self.assertEqual(NC.judge('kho', 20), 'ok')
        self.assertEqual(NC.judge('kho', 30), 'qua')

    def test_a_stop_tap_counts_when_the_finger_came_down(self):
        tid = self.ready()
        k = self.j.get(tid)['menu']['xao']
        self.act('nc_wash', task=tid, dish=k)
        self.act('nc_cut', task=tid, dish=k, cut='nho')
        self.act('nc_fire', task=tid, dish=k, heat='lon')
        start = self.clock.t
        self.clock.t += 30
        self.act('nc_off', task=tid, dish=k, tap_at=start + 9)
        self.assertEqual(self.j.get(tid)['dishes'][k]['q'], 'ok')

    def test_two_burners_only(self):
        tid = self.ready()
        t = self.j.get(tid)
        ks = [k for k in t['dishes'] if NC.DISHES[k]['method'] != 'song']
        for k in ks[:2]:
            self.act('nc_wash', task=tid, dish=k)
            self.act('nc_cut', task=tid, dish=k, cut='nho')
            self.act('nc_fire', task=tid, dish=k, heat='vua')
        k = ks[2]
        self.act('nc_wash', task=tid, dish=k)
        self.act('nc_cut', task=tid, dish=k, cut='nho')
        with self.assertRaises(GameError):
            self.act('nc_fire', task=tid, dish=k, heat='vua')

    def test_serving_waits_for_the_rice_and_every_dish(self):
        tid = self.ready()
        with self.assertRaises(GameError):
            self.act('nc_serve', task=tid)
        self.act('nc_rice', task=tid, water='mot')
        self.act('nc_bowls', task=tid, n=3)
        with self.assertRaises(GameError):
            self.act('nc_serve', task=tid)

    def test_a_dish_left_too_long_goes_cold_and_can_be_warmed(self):
        tid = self.ready()
        t = self.j.get(tid)
        self.act('nc_rice', task=tid, water='mot')
        self.act('nc_bowls', task=tid, n=3)
        self.act('nc_taste', task=tid)
        first = t['menu']['man']
        self.cook(tid, first)
        self.clock.t += NC.WARM_S + 5
        for k in t['dishes']:
            if k != first:
                self.cook(tid, k)
        self.act('nc_reheat', task=tid, dish=first)
        self.clock.t += 5
        self.act('nc_serve', task=tid)
        self.assertNotIn('cold', self.codes(tid))

    def test_cold_salty_wrong_rice_and_bowls_are_named(self):
        t = self.at(day_of('toan'))
        tid = t['id']
        self.plan(tid)
        self.shop(tid)
        self.act('nc_rice', task=tid, water='lung')
        self.act('nc_bowls', task=tid, n=2)
        for k in self.j.get(tid)['dishes']:
            self.cook(tid, k, nem='dam', cut='vua')
        self.clock.t += NC.WARM_S + NC.RICE_S
        self.act('nc_serve', task=tid)
        self.assertTrue({'salt', 'rice', 'bowls', 'cold', 'cut', 'mam'} <= self.codes(tid), self.codes(tid))
        salt = next(x for x in self.j.get(tid)['slips'] if x['code'] == 'salt')
        self.assertEqual(salt['sev'], 2)

    def test_raw_meat_is_a_safety_mistake_and_the_family_pays_less(self):
        t = self.at(1)
        tid = t['id']
        self.plan(tid)
        self.shop(tid)
        n = self.j.get(tid)['needs']
        self.act('nc_rice', task=tid, water='mot')
        self.act('nc_bowls', task=tid, n=n['n'])
        self.act('nc_taste', task=tid)
        self.act('nc_fix', task=tid, add='nuoc')
        for k in self.j.get(tid)['dishes']:
            self.cook(tid, k, secs=1 if NC.DISHES[k]['group'] == 'man' else None)
        self.clock.t += NC.RICE_S
        self.act('nc_serve', task=tid)
        self.assertIn('raw', self.codes(tid))
        money = self.j.c['money']
        self.settle(tid)
        t = self.j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertLess(self.j.c['money'] - money, NC.wage(t, 0) + 20)
        self.assertGreater(t['reaction']['cut'], 0)

    def test_no_receipt_is_written_from_memory(self):
        t = self.at(1)
        tid = t['id']
        self.plan(tid)
        self.shop(tid, receipts=False)
        self.kitchen(tid)
        self.act('nc_serve', task=tid)
        r = self.settle(tid)
        self.assertIn('receipt', self.codes(tid))
        self.assertEqual(self.j.get(tid)['status'], 'completed', r)

    def test_short_portions_are_named(self):
        t = self.at(day_of('le'))
        tid = t['id']
        self.plan(tid)
        self.shop(tid, n=1)
        self.kitchen(tid)
        self.act('nc_serve', task=tid)
        self.assertIn('short', self.codes(tid))

    def test_regulars_pay_a_little_more(self):
        t = dict(needs=dict(n=3))
        self.assertEqual(NC.wage(t, 0), NC.WAGE_BASE + 3 * NC.WAGE_PER)
        self.assertEqual(NC.wage(t, 2), NC.WAGE_BASE + 3 * NC.WAGE_PER + 2 * NC.LOYAL_STEP)
        self.assertEqual(NC.wage(t, 50), NC.WAGE_BASE + 3 * NC.WAGE_PER + NC.LOYAL_MAX)


class Extra(Base):
    def test_the_extra_dish_waits_for_the_meal_then_pays(self):
        t = self.at(1)
        ex = make_task('naucom', 1, 1, 1)
        self.j.c['tasks'].append(ex)
        self.act('ask', task=ex['id'])
        k = ex['needs']['x']
        with self.assertRaises(GameError):
            self.act('nc_wash', task=ex['id'], dish=k)
        self.meal(t['id'])
        money = self.j.c['money']
        self.cook(ex['id'], k)
        r = self.act('nc_bring', task=ex['id'])
        self.assertEqual(self.j.get(ex['id'])['status'], 'completed', r)
        self.assertEqual(self.j.c['money'] - money >= NC.EXTRA_PAY, True)
        self.assertEqual(self.codes(ex['id']), set())
        validate_state(self.j.state)


class Days(Base):
    def full_day(self):
        self.settle_desk()
        self.j.act('nc_intro')
        day = self.j.c['day']
        meal = next(t for t in self.j.c['tasks'] if t['day'] == day and t['kind'] == 'meal')
        if meal['status'] != 'completed':
            self.meal(meal['id'])
        done = 1
        for t in [t for t in self.j.c['tasks'] if t['day'] == day and t['kind'] == 'extra' and t['status'] not in ('completed', 'referred', 'cancelled')]:
            self.act('ask', task=t['id'])
            self.cook(t['id'], t['needs']['x'])
            self.act('nc_bring', task=t['id'])
            done += 1
        self.settle_desk()
        return done

    def test_ten_days_stay_valid(self):
        self.j = Journey('naucom')
        for day in range(1, 11):
            self.assertGreaterEqual(self.full_day(), 1, day)
            validate_state(self.j.state)
            json.dumps(public_state(self.j.state))
            r = self.j.act('end_day', carry_event=True)
            car = r['summary']['career']
            self.assertTrue(car['lines'][0].startswith('🍲'))
            self.assertIn('tomorrow', car)
            self.j.act('start_day')
            validate_state(self.j.state)
        self.assertEqual(self.d['stats']['meals'], 10)
        self.assertGreater(sum(v['visits'] for v in self.d['families'].values()), 9)

    def test_an_unfinished_meal_is_dropped_next_day(self):
        self.j = Journey('naucom')
        self.j.act('nc_intro')
        meal = next(t for t in self.j.c['tasks'] if t['kind'] == 'meal')
        self.plan(meal['id'])
        self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        self.assertEqual(self.j.get(meal['id'])['status'], 'cancelled')
        today = [t for t in self.j.c['tasks'] if t['day'] == self.j.c['day'] and t['kind'] == 'meal']
        self.assertEqual(len(today), 1)
        validate_state(self.j.state)

    def test_validator_rejects_tampering(self):
        self.j = Journey('naucom')
        self.full_day()
        validate_state(self.j.state)
        for bad in (lambda d: d['families'].update(mai=dict(visits=-1)), lambda d: d['families'].update(nobody=dict(visits=1)),
                    lambda d: d['stats'].update(meals='x'), lambda d: d.update(intro='yes')):
            s = copy.deepcopy(self.j.state)
            bad(s['careers']['naucom']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_task_tampering_is_refused(self):
        t = self.at(1)
        self.plan(t['id'])
        for bad in (lambda tt: tt.update(purse=999), lambda tt: tt['_key']['lots'].update(ca_loc='tuoi'),
                    lambda tt: tt['needs'].update(budget=999), lambda tt: tt['menu'].update(canh='tom_rim'),
                    lambda tt: tt['bills']['thit'].update(off=2)):
            s = copy.deepcopy(self.j.state)
            tt = next(x for x in s['careers']['naucom']['tasks'] if x['id'] == t['id'])
            bad(tt)
            with self.assertRaises(GameError):
                validate_state(s)


class OldSaves(Base):
    def test_old_save_without_naucom_gains_it_fresh(self):
        self.j = Journey('ice_cream')
        s = copy.deepcopy(self.j.state)
        s['careers'].pop('naucom')
        s = migrate_state(s)
        self.assertIn('naucom', s['careers'])
        validate_state(s)
        self.assertEqual(s['careers']['naucom'], json.loads(json.dumps(s['careers']['naucom'])))

    def test_a_block_missing_new_keys_is_upgraded(self):
        self.j = Journey('naucom')
        d = self.d
        for k in ('families', 'desk', 'stats'):
            d.pop(k)
        NC._data(self.j.c)
        validate_state(self.j.state)

    def test_initial_block_is_plain_json(self):
        c = initial_career('naucom')
        json.dumps(c)


if __name__ == '__main__':
    unittest.main()
