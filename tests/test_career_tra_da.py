"""Trà đá gốc bàng (plugin career tra_da): setting up the stall, the thermos and the
ice box, pouring and serving, cash and change through the shared till, the tab book
and its settlement, the timed "trật tự đô thị" sweep, surprises, the stall's story,
determinism, save validation and old saves."""
import copy
import json
import unittest
from unittest import mock

from tests.helpers import Journey
from game import tips
from game.careers import kit, till, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

TD = PLUGINS.get('tra_da')


def ledger(c, ref):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ref]


class Base(unittest.TestCase):
    def setUp(self):
        if TD is None:
            raise unittest.SkipTest('tra_da is filtered out by MNL_CAREERS')
        self.j = Journey('tra_da')

    # ------------------------------------------------------------ helpers
    @property
    def d(self):
        return self.j.c['ext']['data']

    def kind(self, kind, j=None):
        j = j or self.j
        return next(t for t in j.c['tasks'] if t['kind'] == kind and t['status'] not in ('completed', 'cancelled'))

    def setup_stall(self, j=None, spot='goc_bang', stools=4, umbrella=True, leaves=2):
        j = j or self.j
        self.settle_desk(j)
        t = self.kind('setup', j)
        j.act('td_spot', spot=spot)
        j.act('td_stools', n=stools)
        j.act('td_umbrella', up=umbrella)
        j.act('td_box')
        if leaves:
            j.act('td_brew', leaves=leaves)
        j.act('td_crush')
        j.act('td_open', task=t['id'])
        return j.get(t['id'])

    def settle_desk(self, j=None):
        """Answer a pending surprise at the stall with its default choice."""
        j = j or self.j
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('td_desk', option=kit.desk_script(TD.DESK, ev['script'])['default'])

    def fill(self, t, j=None):
        """Pour and hand out exactly what the customer ordered (never cigarettes to a kid)."""
        j = j or self.j
        tid = t['id']
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        n = j.get(tid)['needs']
        for k, q in n['drinks'].items():
            for _ in range(q):
                j.act('td_pour', task=tid, drink=k)
        for k, q in n['snacks'].items():
            if n['kid'] and k == 'thuoc_la':
                continue
            for _ in range(q):
                j.act('td_snack', task=tid, item=k)
        if n['kid']:
            j.act('td_refuse', task=tid)
        return j.get(tid)

    def open_stall(self, j):
        """A journey started on a given day and slot has no setup job: put the stall out directly."""
        d = j.c['ext']['data']
        d['stall'].update(day=j.c['day'], spot='goc_bang', stools=4, umbrella=True, box=True, open=True, packed=False)
        d['thermos'].update(tea=TD.THERMOS_MAX, strength=TD.BREW[2], turn=j.c['turn'])
        d['ice'].update(portions=TD.BLOCK, turn=j.c['turn'], acc=0)

    def at(self, pick):
        """A journey on the first (day, slot) whose task passes `pick`, with the stall already out."""
        day, slot = next((d, s) for d in range(2, 40) for s in range(1, 6) if pick(TD.make_task(d, s, 1)))
        j = Journey('tra_da', slot=slot, day=day)
        self.open_stall(j)
        return j

    def serve_all(self, j=None):
        """Serve every waiting customer the right way (skipping the ones the stall cannot serve today)."""
        j = j or self.j
        for t in [x for x in j.c['tasks'] if x['kind'] in ('glass', 'kid', 'tab', 'match') and x['status'] not in ('completed', 'cancelled')]:
            desk = j.c['ext']['data']['desk']
            if desk['ev']:
                j.act('td_desk', option=kit.desk_script(TD.DESK, desk['ev']['script'])['default'])
            sw = j.c['ext']['data']['sweep']
            if sw and sw['stage'] == 'coming':
                return
            try:
                self.fill(t, j)
                j.act('td_serve', task=t['id'])
                t = j.get(t['id'])
                if t['stage'] == 'book':
                    j.act('td_book', task=t['id'], amount=t['owe'])
                elif t['stage'] == 'pay':
                    self.pay_exact(t['id'], j)
            except GameError:
                pass       # out of lemons or sấu some days: that customer waits

    def pay_exact(self, tid, j=None):
        j = j or self.j
        rec = j.get(tid)['cash']
        return j.act('td_pay', task=tid, change=till.greedy(till.due(rec)))


class Spec(Base):
    def test_spec_shape(self):
        s = TD.SPEC
        self.assertEqual(s['id'], 'tra_da')
        self.assertEqual(s['prefix'], 'td_')
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
        for k in s['no_tick'] + s['free_actions'] + tuple(TD.ACTIONS):
            self.assertTrue(k.startswith('td_'), k)

    def test_intro_card_has_three_lists(self):
        i = TD.content()['intro']
        for key in ('work', 'meet', 'stars'):
            self.assertGreaterEqual(len(i[key]), 5, key)
            for icon, text in i[key]:
                self.assertTrue(icon and text)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ')
        blob = json.dumps([TD.ORDERS, TD.DESK, TD.SITUATIONS, TD.REG_STORY, TD.ARC, TD.INTRO, TD.SPEC['meta']], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_counts_come_from_plugins(self):
        self.assertIn('tra_da', PLUGINS)
        from game.content import CAREERS
        self.assertIn('tra_da', CAREERS)

    def test_every_action_is_dispatched(self):
        for name in TD.ACTIONS:
            self.assertTrue(callable(TD.ACTIONS[name]))


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 16):
            for slot in range(0, 8):
                a, b = TD.make_task(day, slot, 1), TD.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('tra_da', day, slot, 1)['id'], f'tra_da-{day:04d}-{slot:02d}')

    def test_first_day_is_gentle(self):
        self.assertEqual(TD.mod_of(1)['id'], 'normal')
        kinds = [TD.make_task(1, s, 1)['kind'] for s in range(3)]
        self.assertEqual(kinds, ['setup', 'glass', 'tab'])
        self.assertEqual(TD.make_task(1, 1, 1)['needs']['drinks'], {'tra_da': 1})
        self.assertIsNone(TD.sweep_plan(1))
        self.assertIsNone(TD.sweep_plan(2))
        self.assertEqual(TD.sweep_plan(3), (2, TD.SWEEP_FIRST))

    def test_days_and_sweeps_repeat(self):
        for day in range(1, 30):
            self.assertEqual(TD.mod_of(day), TD.mod_of(day))
            self.assertEqual(TD.sweep_plan(day), TD.sweep_plan(day))
        self.assertTrue({TD.mod_of(d)['id'] for d in range(2, 40)} >= {'heat', 'rain'})
        self.assertTrue(any(TD.sweep_plan(d) for d in range(4, 40)))


class Setup(Base):
    def test_setup_done_right(self):
        t = self.setup_stall()
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        st = self.d['stall']
        self.assertTrue(st['open'])
        self.assertEqual((st['spot'], st['stools'], st['umbrella'], st['box']), ('goc_bang', 4, True, True))
        self.assertEqual(self.d['thermos']['tea'], TD.THERMOS_MAX)
        self.assertEqual(self.d['ice']['portions'], TD.BLOCK)
        validate_state(self.j.state)

    def test_setup_done_wrong(self):
        j = self.j
        t = self.kind('setup')
        j.act('td_spot', spot='le_duong')
        j.act('td_stools', n=4)
        j.act('td_box')
        j.act('td_brew', leaves=1)
        with self.assertRaises(GameError):
            j.act('td_open', task='nope')
        j.act('td_open', task=t['id'])
        codes = {x['code'] for x in j.get(t['id'])['slips']}
        self.assertTrue({'road', 'no_umbrella', 'weak_brew', 'no_ice'} <= codes, codes)
        self.assertEqual(j.get(t['id'])['status'], 'completed')

    def test_cannot_open_without_basics(self):
        j = self.j
        t = self.kind('setup')
        with self.assertRaises(GameError):
            j.act('td_open', task=t['id'])
        j.act('td_spot', spot='goc_bang')
        with self.assertRaises(GameError):
            j.act('td_stools', n=9)     # only 4 stools owned
        j.act('td_stools', n=1)
        with self.assertRaises(GameError):
            j.act('td_open', task=t['id'])

    def test_rain_day_wants_the_awning(self):
        day = next(d for d in range(2, 60) if TD.mod_of(d)['id'] == 'rain')
        t = TD.make_task(day, 0, 1)
        self.assertEqual(t['needs']['spot'], 'hien')
        self.assertFalse(t['needs']['umbrella'])

    def test_cannot_sell_before_opening(self):
        j = self.j
        g = self.kind('glass')
        j.act('ask', task=g['id'])
        with self.assertRaises(GameError):
            j.act('td_pour', task=g['id'], drink='tra_da')


class Glass(Base):
    def test_right_glass_pays_the_price_through_the_till(self):
        j = self.j
        self.setup_stall()
        g = self.fill(self.kind('glass'))
        money = j.c['money']
        j.act('td_serve', task=g['id'])
        t = j.get(g['id'])
        self.assertEqual(t['price'], 3)
        self.assertEqual(t['cash']['price'], 3)
        self.assertEqual(t['stage'], 'pay')
        self.pay_exact(g['id'])
        t = j.get(g['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        # Everything the till moved for this customer is in the cash book under the task.
        self.assertEqual(j.c['money'] - money, sum(r['amount'] for r in ledger(j.c, g['id'])))
        self.assertEqual(sum(r['amount'] for r in ledger(j.c, g['id']) if r.get('category') != 'tip'), 3)
        self.assertEqual(self.d['glasses']['dirty'], 1)
        validate_state(j.state)

    def test_wrong_drink(self):
        j = self.j
        self.setup_stall()
        g = self.kind('glass')
        j.act('ask', task=g['id'])
        j.act('td_pour', task=g['id'], drink='tra_nong')
        j.act('td_serve', task=g['id'])
        t = j.get(g['id'])
        self.assertIn('wrong_drink', {x['code'] for x in t['slips']})
        self.assertEqual(t['price'], 0)           # nothing they ordered: they pay nothing
        self.assertEqual(t['status'], 'completed')

    def test_extra_glass_can_be_poured_away(self):
        j = self.j
        self.setup_stall()
        g = self.fill(self.kind('glass'))
        j.act('td_pour', task=g['id'], drink='tra_chanh')
        lemons = kit.stock(j.c, 'chanh')
        j.act('td_takeback', task=g['id'], index=1)
        self.assertEqual(len(j.get(g['id'])['tray']), 1)
        self.assertEqual(kit.stock(j.c, 'chanh'), lemons)    # a poured glass is gone, the lemon too
        j.act('td_serve', task=g['id'])
        self.assertFalse(j.get(g['id']).get('slips'))

    def test_weak_and_watery_tea(self):
        j = self.j
        self.setup_stall(leaves=1)
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        self.assertIn('weak', {x['code'] for x in j.get(g['id'])['slips']})
        self.assertEqual(self.d['thermos']['strength'], TD.BREW[1])

    def test_topping_up_thins_the_tea(self):
        j = self.j
        self.setup_stall()
        self.d['thermos']['tea'] = 1
        j.act('td_topup')
        j.act('td_topup')
        self.assertEqual(self.d['thermos']['strength'], TD.BREW[2] - 2 * TD.TOPUP_DROP)
        self.assertLess(self.d['thermos']['strength'], TD.WATERY)
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        self.assertIn('watery', {x['code'] for x in j.get(g['id'])['slips']})

    def test_stale_tea(self):
        j = self.j
        self.setup_stall()
        j.c['turn'] += TD.STALE_TURNS + 2
        self.d['ice']['turn'] = j.c['turn']
        g = self.fill(self.kind('glass'))
        self.assertTrue(j.get(g['id'])['tray'][0]['stale'])
        j.act('td_serve', task=g['id'])
        self.assertIn('stale', {x['code'] for x in j.get(g['id'])['slips']})

    def test_no_ice_left(self):
        j = self.j
        self.setup_stall()
        self.d['ice']['portions'] = 0
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        self.assertIn('no_ice', {x['code'] for x in j.get(g['id'])['slips']})

    def test_murky_basin_leaves_greasy_glasses(self):
        j = self.j
        self.setup_stall()
        self.d['glasses'].update(clean=0, dirty=6, grimy=0)
        self.d['basin'] = TD.BASIN_MAX
        j.act('td_wash')
        self.assertEqual((self.d['glasses']['clean'], self.d['glasses']['grimy']), (0, 6))
        glass = self.fill(self.kind('glass'))
        j.act('td_serve', task=glass['id'])
        self.assertIn('grimy', {x['code'] for x in j.get(glass['id'])['slips']})
        j.act('td_basin')
        j.act('td_wash')
        self.assertGreater(self.d['glasses']['clean'], 0)

    def test_no_clean_glass_blocks_pouring(self):
        j = self.j
        self.setup_stall()
        self.d['glasses'].update(clean=0, dirty=8, grimy=0)
        g = self.kind('glass')
        j.act('ask', task=g['id'])
        with self.assertRaises(GameError):
            j.act('td_pour', task=g['id'], drink='tra_da')

    def test_not_enough_stools(self):
        j = self.at(lambda x: x['kind'] == 'glass' and x['needs']['seats'] >= 3 and not x['needs']['drinks'].keys() - {'tra_da', 'tra_nong'})
        j.c['ext']['data']['stall']['stools'] = 2
        t = self.fill(j.task, j)
        j.act('td_serve', task=t['id'])
        self.assertIn('no_seat', {x['code'] for x in j.get(t['id'])['slips']})


class Ice(Base):
    def test_ice_melts_with_turns_and_faster_in_the_heat(self):
        j = self.j
        self.setup_stall()
        c, d = j.c, self.d
        rate = TD.melt_rate(c, d)
        d['ice'].update(portions=16, turn=c['turn'], acc=0)
        c['turn'] += 12
        left, _, lost = TD._melt_view(c, d)
        self.assertEqual(lost, rate * 12 // 12)
        self.assertEqual(left, 16 - lost)
        heat = next(x for x in range(2, 60) if TD.mod_of(x)['id'] == 'heat')
        cool = next(x for x in range(2, 60) if TD.mod_of(x)['id'] == 'cool')
        day = c['day']
        c['day'] = heat
        hot = TD.melt_rate(c, d)
        c['day'] = cool
        mild = TD.melt_rate(c, d)
        c['day'] = day
        self.assertEqual(hot, rate * 2)
        self.assertLess(mild, rate)

    def test_road_in_the_sun_melts_faster_than_the_shade(self):
        j = self.j
        self.setup_stall()
        d = self.d
        shade = TD.melt_rate(j.c, d)
        d['stall'].update(spot='le_duong', umbrella=False)
        self.assertGreater(TD.melt_rate(j.c, d), shade)

    def test_crushing_needs_a_block_and_room(self):
        j = self.j
        self.setup_stall()
        blocks = kit.stock(j.c, 'da')
        self.d['ice']['portions'] = TD.ICE_MAX
        with self.assertRaises(GameError):
            j.act('td_crush')
        self.d['ice']['portions'] = 0
        j.act('td_crush')
        self.assertEqual(kit.stock(j.c, 'da'), blocks - 1)

    def test_ice_man_delivers_each_morning_as_stock_cost(self):
        j = self.j
        self.setup_stall()
        j.act('td_ice_plan', n=4)
        j.act('end_day')
        money = j.c['money']
        j.act('start_day')
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == f'td-ice-{j.c["day"]}']
        self.assertEqual(sum(r['amount'] for r in rows), -4 * TD.ITEM['da']['cost'])
        self.assertEqual(rows[0]['category'], 'stock')
        self.assertLessEqual(j.c['money'], money)
        validate_state(j.state)


class Kid(Base):
    def kid_task(self):
        self.j = self.at(lambda x: x['kind'] == 'kid' and not x['needs']['drinks'])
        return self.j.task

    def test_refusing_cigarettes_to_a_child(self):
        t = self.fill(self.kid_task())
        j = self.j
        j.act('td_serve', task=t['id'])
        t = j.get(t['id'])
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['price'], TD.PRICES['keo_lac'])   # only the candy is sold
        self.pay_exact(t['id'])
        self.assertEqual(self.d['stats']['refused_kid'], 1)

    def test_selling_cigarettes_to_a_child_is_a_safety_slip(self):
        t = self.kid_task()
        j = self.j
        j.act('ask', task=t['id'])
        j.act('td_snack', task=t['id'], item='thuoc_la')
        money = j.c['money']
        j.act('td_serve', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('minor_smoke', {x['code'] for x in t['slips']})
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(j.c['money'], money)                  # no money for that
        self.assertEqual(tips.decide(j.state, j.c, t)['why'], 'given' if t.get('tip_given') else 'reaction')


class Change(Base):
    def served(self):
        j = self.j
        self.setup_stall()
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        return j.get(g['id'])

    def test_exact_change(self):
        t = self.served()
        rec = t['cash']
        self.assertEqual(till.due(rec), sum(rec['tender']) - 3)
        self.pay_exact(t['id'])
        t = self.j.get(t['id'])
        self.assertIn(t['cash']['outcome'], ('exact', 'keep'))

    def test_short_change_a_careful_customer_asks(self):
        j = self.j
        t = self.served()
        with mock.patch.object(till, 'careful', return_value=True):
            r = j.act('td_pay', task=t['id'], change=[])
        self.assertIn('thiếu', r['message'])
        self.assertEqual(j.get(t['id'])['status'], 'in_progress')
        self.pay_exact(t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertIn('change_short', {x['code'] for x in t['slips']})

    def test_short_change_found_at_home(self):
        j = self.j
        t = self.served()
        with mock.patch.object(till, 'careful', return_value=False):
            j.act('td_pay', task=t['id'], change=[])
        t = j.get(t['id'])
        self.assertEqual(t['cash']['outcome'], 'missed')
        self.assertIn('change_home', {x['code'] for x in t['slips']})

    def test_extra_change_kept_is_a_real_loss(self):
        j = self.j
        t = self.served()
        need = till.due(t['cash'])
        money = j.c['money']
        with mock.patch.object(till, 'honest', return_value=False):
            j.act('td_pay', task=t['id'], change=till.greedy(need) + [5])
        t = j.get(t['id'])
        self.assertEqual(t['cash']['outcome'], 'kept')
        self.assertEqual(j.c['money'] - money, 3 - 5)          # price in, 5 xu extra gone
        self.assertEqual(j.c['money'] - money, sum(r['amount'] for r in ledger(j.c, t['id'])))

    def test_keep_the_change_tip_contract(self):
        j = self.j
        t = self.served()
        need = till.due(t['cash'])
        money = j.c['money']
        with mock.patch.object(till, 'waves_off', return_value=True):
            r = j.act('td_pay', task=t['id'], change=till.greedy(need))
        t = j.get(t['id'])
        self.assertEqual(t['tip_given'], need)
        tips_rows = [x for x in ledger(j.c, t['id']) if x.get('category') == 'tip']
        self.assertEqual([x['amount'] for x in tips_rows], [need])
        self.assertEqual(j.c['money'] - money, 3 + need)      # the price and the change they left: nothing goes out
        self.assertIn('Khỏi thối', r['message'])
        self.assertEqual(tips.decide(j.state, j.c, t)['why'], 'given')   # the random tip never pays it twice


class Tab(Base):
    def serve_tab(self, amount=None):
        j = self.j
        self.setup_stall()
        t = self.fill(self.kind('tab'))
        j.act('td_serve', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['stage'], 'book')
        j.act('td_book', task=t['id'], amount=t['owe'] if amount is None else amount)
        return j.get(t['id'])

    def test_tab_written_right(self):
        money = self.j.c['money']
        t = self.serve_tab()
        self.assertEqual(t['status'], 'completed')
        line = self.d['tab'][-1]
        self.assertEqual(line['amount'], line['due'])
        self.assertEqual(line['due'], TD.PRICES['tra_da'] + TD.PRICES['thuoc_la'])
        self.assertEqual(self.j.c['money'], money)         # nothing paid today
        self.j.act('end_day')
        lines = self.j.c['shift_summary']['career']['lines']
        self.assertTrue(any('khớp từng dòng' in x for x in lines), lines)

    def test_tab_written_wrong_is_caught_at_night(self):
        self.serve_tab(amount=9)
        self.assertEqual(self.d['stats']['overbooked'], 4)
        self.j.act('end_day')
        lines = self.j.c['shift_summary']['career']['lines']
        self.assertTrue(any('ghi lố 4 xu' in x for x in lines), lines)

    def test_book_needs_an_amount(self):
        j = self.j
        self.setup_stall()
        t = self.fill(self.kind('tab'))
        j.act('td_serve', task=t['id'])
        with self.assertRaises(GameError):
            j.act('td_book', task=t['id'], amount=0)


class Settle(Base):
    def settle_journey(self, lines):
        j = Journey('tra_da', slot=1, day=3)
        self.assertEqual(j.task['kind'], 'settle')
        d = j.c['ext']['data']
        d.update(TD.initial(), **{k: v for k, v in d.items() if k not in TD.initial()})
        d['tab'] = [dict(id=f'tab-{i + 1}', npc=1, task=f'tra_da-0002-0{i + 1}', day=2, amount=a, due=u, what='1 trà đá')
                    for i, (a, u) in enumerate(lines)]
        d['tab_seq'] = len(lines)
        TD.on_task(j.state, j.c, j.task)
        validate_state(j.state)
        return j

    def test_settlement_collects_the_book(self):
        j = self.settle_journey([(5, 5), (3, 3)])
        t = j.task
        j.task['dispute'] = None              # a calm day: no line in question
        j.act('ask', task=t['id'])
        j.act('td_bill', task=t['id'])
        t = j.task
        self.assertEqual(t['stage'], 'pay')
        self.assertEqual(t['cash']['price'], 8)
        money = j.c['money']
        rec = t['cash']
        j.act('td_pay', task=t['id'], change=till.greedy(till.due(rec)))
        self.assertEqual(j.get(t['id'])['status'], 'completed')
        self.assertEqual(j.c['ext']['data']['tab'], [])
        self.assertGreaterEqual(j.c['money'] - money, 8)
        validate_state(j.state)

    def test_overbooked_line_must_be_fixed(self):
        j = self.settle_journey([(9, 5), (3, 3)])
        t = j.task
        self.assertEqual(t['dispute']['line'], 'tab-1')
        self.assertTrue(t['dispute']['wrong'])
        j.act('ask', task=t['id'])
        j.act('td_bill', task=t['id'])
        self.assertEqual(j.task['stage'], 'dispute')
        j.act('td_dispute', task=t['id'], choice='show')
        self.assertIn('overbook', {x['code'] for x in j.task['slips']})
        self.assertEqual(j.task['stage'], 'dispute')
        j.act('td_dispute', task=t['id'], choice='fix')
        t = j.task
        self.assertEqual(t['bill']['total'], 8)
        self.assertEqual(t['cash']['price'], 8)

    def test_correct_line_cannot_be_fixed_only_shown(self):
        j = self.settle_journey([(5, 5)])
        t = j.task
        t['dispute'] = dict(line='tab-1', wrong=False, state='open')
        j.act('ask', task=t['id'])
        j.act('td_bill', task=t['id'])
        with self.assertRaises(GameError):
            j.act('td_dispute', task=t['id'], choice='fix')
        j.act('td_dispute', task=t['id'], choice='show')
        self.assertFalse(j.task.get('slips'))
        self.assertEqual(j.task['cash']['price'], 5)

    def test_dropping_the_only_line_settles_for_nothing(self):
        j = self.settle_journey([(5, 5)])
        t = j.task
        t['dispute'] = dict(line='tab-1', wrong=False, state='open')
        j.act('ask', task=t['id'])
        j.act('td_bill', task=t['id'])
        j.act('td_dispute', task=t['id'], choice='drop')
        self.assertEqual(j.task['bill']['total'], 0)
        j.act('td_settle_free', task=t['id'])
        self.assertEqual(j.get(t['id'])['status'], 'completed')
        self.assertEqual(j.c['ext']['data']['tab'], [])

    def test_arguing_over_a_wrong_line(self):
        j = self.settle_journey([(9, 5), (3, 3)])
        t = j.task
        j.act('ask', task=t['id'])
        j.act('td_bill', task=t['id'])
        j.act('td_dispute', task=t['id'], choice='argue')
        self.assertIn('argue', {x['code'] for x in j.task['slips']})
        self.assertEqual(j.task['bill']['total'], 3)

    def test_the_book_hides_what_it_should_have_said(self):
        j = self.settle_journey([(9, 5)])
        view = public_state(j.state)['careers']['tra_da']
        self.assertNotIn('due', json.dumps(view['data']['tab']))
        pt = next(x for x in view['tasks'] if x['kind'] == 'settle')
        self.assertIsNone(pt.get('dispute'))      # not before the book is read


class Sweep(Base):
    def day3(self):
        j = self.j
        self.setup_stall()
        self.serve_all()
        for _ in range(2):
            j.act('end_day')
            j.act('start_day')
            self.setup_stall()
            if j.c['day'] < 3:
                self.serve_all()
        self.assertEqual(j.c['day'], 3)
        return j

    def finish_one(self, j):
        open_ = [x for x in j.c['tasks'] if x['kind'] in ('glass', 'tab', 'kid', 'match') and x['status'] not in ('completed', 'cancelled')]
        t = next((x for x in open_ if not set(x['needs']['drinks']) & {'tra_chanh', 'sau_da'}), open_[0])
        self.fill(t)
        r = j.act('td_serve', task=t['id'])
        t = j.get(t['id'])
        if t['stage'] == 'book':
            return j.act('td_book', task=t['id'], amount=t['owe'])
        if t['stage'] == 'pay':
            return self.pay_exact(t['id'])
        return r

    def test_packing_in_time(self):
        with mock.patch.object(kit, 'now', return_value=1000.0):
            j = self.day3()
            r = self.finish_one(j)
            sw = self.d['sweep']
            self.assertEqual(sw['stage'], 'coming', r)
            self.assertEqual(sw['limit'], TD.SWEEP_FIRST)
            with self.assertRaises(GameError):
                j.act('td_wash')
            validate_state(j.state)
            money = j.c['money']
            while self.d['sweep']['stage'] == 'coming':
                sw = self.d['sweep']
                j.act('td_pack', what='umbrella' if sw['umbrella'] and not sw['folded'] else 'stools')
        self.assertEqual(self.d['sweep']['result']['fine'], 0)
        self.assertEqual(j.c['money'], money)
        self.assertTrue(self.d['stall']['packed'])
        self.settle_desk(j)
        j.act('td_unpack')
        self.assertFalse(self.d['stall']['packed'])

    def test_too_slow_means_a_fine_and_lost_stools(self):
        clock = [1000.0]
        with mock.patch.object(kit, 'now', side_effect=lambda: clock[0]):
            j = self.day3()
            self.finish_one(j)
            owned = self.d['owned']['stools']
            stools = self.d['sweep']['stools']
            money = j.c['money']
            clock[0] += TD.SWEEP_FIRST + 1
            j.act('td_sweep_end')
        res = self.d['sweep']['result']
        fine = TD.FINE_BASE + TD.FINE_STOOL * stools + TD.FINE_UMBRELLA
        self.assertEqual(res['fine'], fine)
        self.assertEqual(money - j.c['money'], fine)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == 'sweep-3']
        self.assertEqual((rows[0]['amount'], rows[0]['category']), (-fine, 'fine'))
        self.assertEqual(self.d['owned']['stools'], max(TD.STOOLS_MIN, owned - min(stools, 3)))
        validate_state(j.state)

    def test_sweep_end_waits_for_the_truck(self):
        with mock.patch.object(kit, 'now', return_value=5000.0):
            j = self.day3()
            self.finish_one(j)
            with self.assertRaises(GameError):
                j.act('td_sweep_end')

    def test_closing_during_the_sweep_is_not_fined(self):
        with mock.patch.object(kit, 'now', return_value=1000.0):
            j = self.day3()
            self.finish_one(j)
            money = j.c['money']
            j.act('end_day')
        self.assertEqual(self.d['sweep']['result']['fine'], 0)
        self.assertGreaterEqual(j.c['money'], money)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in TD.DESK:
            for o in x['options']:
                j = Journey('tra_da')
                self.setup_stall(j)
                j.c['money'] += 100
                j.c['ops']['finance']['opening_balance'] += 100
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('td_wash')
                r = j.act('td_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                self.assertIsNone(j.c['ext']['data']['desk']['ev'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_rain_moves_the_stall(self):
        j = self.j
        self.setup_stall()
        self.d['desk']['ev'] = dict(id='desk-r', script='rain_shower', day=1, at='between')
        j.act('td_desk', option='awning')
        self.assertEqual(self.d['stall']['spot'], 'hien')
        self.assertLessEqual(self.d['stall']['stools'], TD.SPOTS['hien']['cap'])

    def test_situations_are_playable(self):
        j = self.j
        for x in TD.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Story(Base):
    def test_regulars_story_goes_on(self):
        j = self.j
        self.setup_stall()
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        r = self.pay_exact(g['id'])
        self.assertIn(TD.REG_STORY[6][0], r['message'])
        self.assertEqual(self.d['regulars']['6']['visits'], 1)

    def test_arc_and_gift(self):
        j = self.j
        self.setup_stall()
        self.assertEqual(self.d['arc']['due'], 'keys')
        j.act('td_arc')
        self.d['stats']['glasses'] = 8
        stools = self.d['owned']['stools']
        self.d['glasses']['dirty'] += 1
        j.act('td_wash')
        self.assertEqual(self.d['arc']['due'], 'taste')
        self.assertEqual(self.d['owned']['stools'], stools + 2)
        j.act('td_arc')
        self.assertEqual(self.d['arc']['seen'], ['keys', 'taste'])

    def test_growth_costs_money_as_equipment(self):
        j = self.j
        money = j.c['money']
        j.act('td_buy', item='umbrella', confirm=True)
        self.assertEqual(self.d['owned']['umbrella'], 2)
        self.assertEqual(j.c['money'], money - 30)
        row = next(r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == 'td-buy-umbrella')
        self.assertEqual(row['category'], 'equipment')
        with self.assertRaises(GameError):
            j.act('td_buy', item='umbrella', confirm=True)

    def test_intro_flag(self):
        j = self.j
        self.assertFalse(public_state(j.state)['careers']['tra_da']['data']['intro'])
        j.act('td_intro')
        self.assertTrue(public_state(j.state)['careers']['tra_da']['data']['intro'])


class Close(Base):
    def test_close_cleans_up_and_reports(self):
        j = self.j
        self.setup_stall()
        g = self.fill(self.kind('glass'))
        j.act('td_serve', task=g['id'])
        self.pay_exact(g['id'])
        j.act('end_day')
        s = j.c['shift_summary']['career']
        self.assertEqual(s['glasses'], 1)
        self.assertTrue(s['lines'])
        self.assertEqual(self.d['glasses']['dirty'] + self.d['glasses']['grimy'], 0)
        self.assertEqual(self.d['thermos']['tea'], 0)
        self.assertFalse(self.d['stall']['open'])
        j.act('start_day')
        self.assertEqual(j.task['kind'], 'setup')
        validate_state(j.state)

    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            if kit.stock(j.c, 'che') < 4:
                kit.add_lot(j.c, 'che', 10, 2, 30, 'test')      # what the storeroom order brings
            self.setup_stall()
            self.serve_all()
            validate_state(json.loads(json.dumps(j.state)))
            j.act('end_day')
            j.act('start_day')


class Saves(Base):
    def test_validate_rejects_broken_data(self):
        for path, value in ((('thermos', 'tea'), 99), (('ice', 'portions'), -1), (('stall', 'spot'), 'moon'),
                            (('owned', 'stools'), 50), (('arc', 'due'), 'dragon')):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['tra_da']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        s = copy.deepcopy(self.j.state)
        t = next(x for x in s['careers']['tra_da']['tasks'] if x['kind'] == 'glass')
        t['needs']['drinks'] = {'tra_da': 9}
        with self.assertRaises(GameError):
            validate_state(s)

    def test_old_save_without_the_stall_loads(self):
        s = new_state()
        s['careers'].pop('tra_da', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('tra_da', s['careers'])

    def test_old_data_gains_new_fields(self):
        j = self.j
        d = j.c['ext']['data']
        for k in ('intro', 'arc', 'regulars', 'sweeps', 'ice_plan', 'today'):
            d.pop(k)
        d['stats'].pop('weak')
        d['owned'].pop('banner')
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        j.state = s
        self.setup_stall()
        j.act('end_day')
        j.act('start_day')
        validate_state(j.state)

    def test_public_view_is_json_and_hides_nothing_needed(self):
        self.setup_stall()
        view = public_state(self.j.state)['careers']['tra_da']
        json.dumps(view)
        data = view['data']
        for k in ('stall', 'thermos', 'ice', 'glasses', 'tab', 'mod', 'desk', 'arc', 'owned'):
            self.assertIn(k, data)


if __name__ == '__main__':
    unittest.main()
