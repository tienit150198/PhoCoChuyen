"""Tiệm nail của chị Diệp (plugin career nail): the morning (lamp test, the weak bulb, the sterilizer,
the stock shelf), looking at the nails first (fungus / an infected cuticle are declined), single-use
files and sterilized tools, taking old polish off (wipe, file + soak, prying), shape and length,
cuticles (bleeding, honesty), gel layers under the lamp (cure times, skin, thick coats, the sticky
layer, art before top), under-cure that peels the next day, regular polish, the power cut, cash
through the shared till, hints that never give the answer, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, till, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

NL = PLUGINS.get('nail')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(kind=None, title=None, days=range(1, 60), slots=range(1, 5), cond=None):
    for day in days:
        for slot in slots:
            t = make_task('nail', day, slot, 1)
            if (kind is None or t['kind'] == kind) and (title is None or t['title'] == title) \
                    and (cond is None or (t['_cond'] or {}).get('nail') == cond):
                return day, slot
    raise AssertionError(f'no {kind} {title} {cond}')


class Base(unittest.TestCase):
    def setUp(self):
        if NL is None:
            raise unittest.SkipTest('nail is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, opened=True):
        """A client on her own, the shop already set up (lamp tested and good, tools sterilized)."""
        self.j = Journey('nail', slot=slot, day=day)
        d = NL._data(self.j.c)
        d['intro'] = True
        d['shop'].update(open=opened, stocked=True)
        d['lamp'] = dict(kind='led', weak=False, tested=True)
        d['power'] = 'on'
        d['tools'] = dict(clean=True, by=None)
        for x in NL.ITEMS:
            kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('nl_desk', option=kit.desk_script(NL.DESK, ev['script'])['default'])

    def cure_for(self, layer):
        need = NL.need_of(self.d, layer)
        return next(s for s in NL.CURE_SECS if s >= need)

    def coat(self, tid, layer, kind, colour=None, cure=True, thick='mong', short=False):
        p = dict(task=tid, layer=layer, p=kind, thick=thick)
        if colour:
            p['colour'] = colour
        self.j.act('nl_coat', **p)
        if self.j.get(tid)['coats'][-1]['skin']:
            self.j.act('nl_clean', task=tid)
        if kind == 'gel' and cure:
            sec = self.cure_for(layer)
            if short:
                sec = next(s for s in NL.CURE_SECS if s * 2 >= NL.need_of(self.d, layer))
            self.j.act('nl_cure', task=tid, sec=sec)

    def prep(self, tid):
        """Ask, look, a fresh file, old polish off, the broken nail, tips, shape, a gentle cuticle push."""
        t = self.j.get(tid)
        if not t['known']:
            self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_kit', task=tid)
        t = self.j.get(tid)
        old = t['_cond']['old']
        if old == 'thuong':
            self.j.act('nl_remove', task=tid, how='wipe')
        elif old == 'gel':
            self.j.act('nl_remove', task=tid, how='file')
            self.j.act('nl_remove', task=tid, how='wrap')
            self.clock.t += NL.SOAK_S + 1
            self.j.act('nl_remove', task=tid, how='unwrap')
        if t['_cond']['nail'] == 'broken':
            self.j.act('nl_fix', task=tid)
        n = t['needs']
        if n['extend']:
            self.j.act('nl_tip', task=tid)
        self.j.act('nl_shape', task=tid, shape=n['shape'], length=n['length'])
        self.j.act('nl_cuticle', task=tid, how='day')

    def make(self, tid, short=False):
        """Exactly what was asked, every layer cured just long enough (or a little short)."""
        self.prep(tid)
        n = self.j.get(tid)['needs']
        if n['care']:
            self.j.act('nl_care', task=tid)
        if n['polish'] == 'gel':
            self.coat(tid, 'base', 'gel', short=short)
            self.coat(tid, 'color', 'gel', n['colour'], short=short)
            self.coat(tid, 'color', 'gel', n['colour'], short=short)
            if n['art']:
                self.j.act('nl_art', task=tid, art=n['art'])
                self.j.act('nl_cure', task=tid, sec=self.cure_for('da' if n['art'] == 'da' else 'art'))
            self.coat(tid, 'top', 'gel', short=short)
            self.j.act('nl_wipe', task=tid)
        elif n['polish'] == 'thuong':
            self.coat(tid, 'base', 'thuong')
            self.coat(tid, 'color', 'thuong', n['colour'])
            self.coat(tid, 'color', 'thuong', n['colour'])
            self.coat(tid, 'top', 'thuong')
            self.j.act('nl_dry', task=tid)
        self.j.act('nl_oil', task=tid)

    def done_pay(self, tid):
        r = self.j.act('nl_done', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        return self.j.act('nl_pay', task=tid, change=till.greedy(max(0, till.due(t['cash']))))

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}

    def refused(self, msg, action, **payload):
        with self.assertRaises(GameError) as cm:
            self.j.act(action, **payload)
        self.assertIn(msg, str(cm.exception))


class Spec(Base):
    def test_spec_shape(self):
        s = NL.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('nail', 'nl_', 'service'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        self.assertEqual(s['people'][0][0], 'Chị Diệp')
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('nail', jr.CH_UNLOCKS[2])
        for name in NL.ACTIONS:
            self.assertTrue(name.startswith('nl_'))
        for name in (*NL.NO_TICK, *NL.PHYSICAL, *NL.FREE):
            self.assertTrue(name in NL.ACTIONS or name in ('nl_intro', 'nl_desk'), name)

    def test_tasks_are_deterministic_and_cover_every_kind(self):
        kinds = set()
        for day in range(1, 30):
            for slot in range(0, 5):
                a, b = make_task('nail', day, slot, 3), make_task('nail', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
        self.assertEqual(kinds, set(NL.KINDS))

    def test_first_day_is_three_gentle_clients(self):
        titles = [make_task('nail', 1, s, 1)['title'] for s in (1, 2, 3)]
        self.assertEqual(titles, ['Bé My sơn thường', 'Bà Năm cắt móng', 'Chị Ngân tháo gel làm mới'])

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in NL.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in NL.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))


class Morning(Base):
    def test_a_careful_morning_opens_clean(self):
        self.j = Journey('nail', slot=0, day=2)
        NL._data(self.j.c)['lamp'] = dict(kind='led', weak=True, tested=False)
        for x in NL.ITEMS:
            kit.add_lot(self.j.c, x['id'], 3, x['cost'], 30, 'test')
        self.j.act('nl_intro')
        r = self.j.act('nl_lamp_test')
        self.assertIn('yếu', r['message'])
        self.j.act('nl_bulb')
        self.assertFalse(self.d['lamp']['weak'])
        self.j.act('nl_sterilize')
        self.j.act('nl_stock')
        tid = self.j.task['id']
        self.j.act('nl_open', task=tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        self.assertFalse(self.codes(tid))
        self.assertTrue(self.d['shop']['open'])

    def test_skipping_the_morning_is_named(self):
        self.j = Journey('nail', slot=0, day=2)
        tid = self.j.task['id']
        self.j.act('nl_open', task=tid)
        self.assertEqual(self.codes(tid), {'no_lamp_test', 'tools_dirty', 'no_stock'})

    def test_the_second_morning_has_a_weak_bulb_and_public_data_hides_it_until_tested(self):
        self.assertFalse(NL.weak_of(1))
        self.assertTrue(NL.weak_of(2))
        self.j = Journey('nail')
        self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        self.assertEqual(self.j.c['day'], 2)
        self.assertTrue(self.d['lamp']['weak'])
        v = public_state(self.j.state)['careers']['nail']['data']
        self.assertIsNone(v['lamp']['weak'])
        self.j.act('nl_lamp_test')
        v = public_state(self.j.state)['careers']['nail']['data']
        self.assertTrue(v['lamp']['weak'])

    def test_no_spare_bulb_falls_back_to_the_uv_lamp(self):
        self.j = Journey('nail', slot=0, day=2)
        self.d['lamp'] = dict(kind='led', weak=True, tested=True)
        while kit.stock(self.j.c, 'bong_led'):
            kit.take(self.j.c, 'bong_led', 1)
        self.refused('Hết bóng LED dự phòng', 'nl_bulb')
        self.j.act('nl_lamp', kind='uv')
        self.assertEqual(NL.need_of(self.d, 'base'), 120)

    def test_work_waits_for_the_shop_to_open(self):
        day, slot = find('serve', 'Bé My sơn thường')
        t = self.at(day, slot, opened=False)
        self.j.act('ask', task=t['id'])
        self.refused('Chưa mở tiệm', 'nl_inspect', task=t['id'])


class Serving(Base):
    def test_a_clean_regular_polish_pays(self):
        t = self.at(1, 1)
        money = self.j.c['money']
        self.make(t['id'])
        self.done_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(self.codes(t['id']))
        self.assertEqual(t['price'], NL.PRICES['son_thuong'])
        self.assertGreater(self.j.c['money'], money)
        validate_state(self.j.state)

    def test_a_gel_redo_with_soak_pays_both_services(self):
        t = self.at(1, 3)
        self.assertEqual(t['_cond']['old'], 'gel')
        self.make(t['id'])
        self.done_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertFalse(self.codes(t['id']), t.get('slips'))
        self.assertEqual(t['price'], NL.PRICES['thao_gel'] + NL.PRICES['son_gel'])

    def test_the_bride_set_with_tips_and_stones(self):
        day, slot = find('bride')
        t = self.at(day, slot)
        self.make(t['id'])
        self.done_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertFalse(self.codes(t['id']), t.get('slips'))
        self.assertEqual(t['price'], NL.PRICES['noi'] + NL.PRICES['son_gel'] + NL.PRICES['da'])

    def test_a_broken_nail_is_fixed_first(self):
        day, slot = find('serve', cond='broken', days=range(2, 120))
        t = self.at(day, slot)
        if t['_cond']['nail'] != 'broken':
            self.skipTest('no broken nail')
        self.make(t['id'])
        self.done_pay(t['id'])
        self.assertNotIn('broken', self.codes(t['id']))

    def test_skipping_the_broken_nail_is_named(self):
        day, slot = find('serve', cond='broken', days=range(2, 120))
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_kit', task=t['id'])
        n = t['needs']
        self.j.act('nl_shape', task=t['id'], shape=n['shape'], length=n['length'])
        self.j.act('nl_done', task=t['id'])
        self.assertIn('broken', self.codes(t['id']))

    def test_wrong_colour_and_wrong_shape(self):
        t = self.at(1, 1)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_kit', task=t['id'])
        self.j.act('nl_shape', task=t['id'], shape='vuong', length='vua')
        self.coat(t['id'], 'color', 'thuong', 'do')
        self.j.act('nl_dry', task=t['id'])
        self.j.act('nl_done', task=t['id'])
        self.assertTrue({'colour', 'shape'} <= self.codes(t['id']))


class Hygiene(Base):
    def test_reusing_a_file_is_a_safety_slip(self):
        t = self.at(1, 1)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_shape', task=t['id'], shape='tron', length='vua')
        self.j.act('nl_done', task=t['id'], confirm=True)
        self.assertIn('reuse_file', self.codes(t['id']))
        self.assertTrue(any(x['code'] == 'reuse_file' and x.get('safety') for x in self.j.get(t['id'])['slips']))

    def test_tools_used_on_the_last_client_are_dirty(self):
        t = self.at(1, 1)
        self.d['tools'] = dict(clean=False, by='nail-0001-09')
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_kit', task=t['id'])
        self.j.act('nl_cuticle', task=t['id'], how='day')
        self.assertIn('dirty_tools', self.j.get(t['id'])['flags'])
        # The same client again: the tools are hers now, nothing new.
        self.j.act('nl_shape', task=t['id'], shape='tron', length='ngan')
        self.assertEqual(self.d['tools'], dict(clean=False, by=t['id']))

    def test_the_sterilizer_cleans_the_tools_between_clients(self):
        t = self.at(1, 1)
        self.d['tools'] = dict(clean=False, by='nail-0001-09')
        self.j.act('nl_sterilize')
        self.make(t['id'])
        self.done_pay(t['id'])
        self.assertNotIn('dirty_tools', self.codes(t['id']))


class Health(Base):
    def test_fungus_is_declined_for_health_without_a_slip(self):
        day, slot = find('serve', 'Cô Lan sơn che móng')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        r = self.j.act('nl_inspect', task=t['id'])
        self.assertIn('vàng đục', r['message'])
        r = self.j.act('nl_decline', task=t['id'], why='health')
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(self.codes(t['id']))
        self.assertIn('khám', r['message'])

    def test_working_on_an_infected_nail_is_a_safety_slip(self):
        day, slot = find('serve', 'Cô Lan đau khóe móng')
        t = self.at(day, slot)
        self.make(t['id'])
        self.j.act('nl_done', task=t['id'])
        sl = {x['code']: x for x in self.j.get(t['id'])['slips']}
        self.assertEqual(sl['health']['sev'], 3)
        self.assertTrue(sl['health']['safety'])

    def test_declining_a_healthy_client_is_wrong(self):
        t = self.at(1, 1)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_decline', task=t['id'], why='health')
        self.assertIn('wrong_refuse', self.codes(t['id']))

    def test_declining_for_stock_that_is_on_the_shelf_is_wrong_but_honest_when_out(self):
        t = self.at(1, 1)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_decline', task=t['id'], why='stock')
        self.assertIn('wrong_refuse', self.codes(t['id']))
        t = self.at(1, 1)
        while kit.stock(self.j.c, 'son_nude'):
            kit.take(self.j.c, 'son_nude', 1)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_decline', task=t['id'], why='stock')
        self.assertFalse(self.codes(t['id']))

    def test_out_of_stock_is_no_excuse_when_the_set_needs_nothing_from_the_shelf(self):
        t = self.at(1, 2)
        self.assertIsNone(t['needs']['polish'])
        self.j.act('ask', task=t['id'])
        self.j.act('nl_decline', task=t['id'], why='stock')
        self.assertIn('wrong_refuse', self.codes(t['id']))

    def test_corrupt_shop_data_is_a_clean_error(self):
        t = self.at(1, 1)
        self.d['stats'] = []
        self.refused('tiệm nail', 'nl_inspect', task=t['id'])

    def test_cutting_deep_on_blood_thinners_bleeds(self):
        t = self.at(1, 2)
        self.assertTrue(t['needs']['blood'])
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_kit', task=t['id'])
        self.j.act('nl_shape', task=t['id'], shape='tron', length='ngan')
        self.j.act('nl_cuticle', task=t['id'], how='sau')
        self.refused('cầm máu', 'nl_done', task=t['id'])
        self.j.act('nl_staunch', task=t['id'])
        self.j.act('nl_tell', task=t['id'], honest=False)
        self.j.act('nl_done', task=t['id'])
        sl = {x['code']: x for x in self.j.get(t['id'])['slips']}
        self.assertEqual(sl['bleed']['sev'], 3)
        self.assertTrue(sl['bleed']['safety'])
        self.assertIn('hid', sl)

    def test_telling_the_truth_after_bleeding_drops_the_hid_slip(self):
        t = self.at(1, 2)
        self.j.act('ask', task=t['id'])
        self.j.act('nl_inspect', task=t['id'])
        self.j.act('nl_kit', task=t['id'])
        self.j.act('nl_shape', task=t['id'], shape='tron', length='ngan')
        self.j.act('nl_cuticle', task=t['id'], how='sau')
        self.j.act('nl_staunch', task=t['id'])
        self.j.act('nl_tell', task=t['id'], honest=True)
        self.j.act('nl_done', task=t['id'])
        self.assertNotIn('hid', self.codes(t['id']))


class Gel(Base):
    def gel_client(self):
        t = self.at(1, 3)
        self.prep(t['id'])
        return t['id']

    def test_a_coat_never_cured_is_wet_and_needs_confirming(self):
        tid = self.gel_client()
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'do', cure=False)
        self.refused('chưa hơ', 'nl_done', task=tid)
        self.j.act('nl_done', task=tid, confirm=True)
        self.assertIn('wet', self.codes(tid))

    def test_far_too_short_is_wet_and_coating_over_it_smears(self):
        tid = self.gel_client()
        self.d['lamp']['weak'] = True                                  # a weak bulb: the colour needs 120 s
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'do', cure=False)
        r = self.j.act('nl_cure', task=tid, sec=NL.CURE_SECS[0])     # 30 s of 120: still wet on top
        self.assertIn('còn ướt', r['message'])
        self.coat(tid, 'color', 'gel', 'do', cure=False)
        self.assertIn('smear', self.j.get(tid)['flags'])

    def test_a_weak_bulb_doubles_the_time_and_short_cures_peel_tomorrow(self):
        t = self.at(1, 3)
        self.d['lamp']['weak'] = True
        money = self.j.c['money']
        self.make(t['id'], short=True)                 # each layer cured half its need: looks fine today
        self.done_pay(t['id'])
        self.assertNotIn('wet', self.codes(t['id']))
        self.assertEqual(len(self.d['peel']), 1)
        paid = self.j.c['money']
        self.assertGreater(paid, money)
        self.settle_desk()
        self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        self.assertEqual(self.d['peel'], [])
        self.assertEqual(self.d['stats']['peeled'], 1)
        feed = [x for x in self.j.c['feed'] if x.get('source') == t['id'] and x.get('kind') == 'review']
        self.assertEqual(feed[0]['stars'], 2)
        self.assertIn('bong', feed[0]['text'])
        validate_state(self.j.state)

    def overnight(self):
        self.settle_desk()
        self.j.act('end_day', carry_event=True)
        before = self.j.c['money']
        self.j.act('start_day')
        return before - self.j.c['money']

    def test_the_peel_refund_is_half_the_bill_and_never_more_than_was_paid(self):
        t = self.at(1, 3)
        self.d['lamp']['weak'] = True
        self.make(t['id'], short=True)
        self.done_pay(t['id'])
        t = self.j.get(t['id'])
        paid = t['price'] - t['reaction']['cut']
        self.assertEqual([x['price'] for x in self.d['peel']], [paid])
        self.assertEqual(self.overnight(), min(t['price'] // 2, paid))

    def test_no_peel_refund_when_the_client_did_not_pay(self):
        t = self.at(1, 3)
        self.d['lamp']['weak'] = True
        self.d['tools'] = dict(clean=False, by='other')        # dirty tools: she refuses to pay
        self.make(t['id'], short=True)
        self.done_pay(t['id'])
        self.assertEqual(self.d['peel'], [])
        self.assertEqual(self.overnight(), 0)
        t = self.at(1, 3)                                       # handed over but never paid: no record at all
        self.d['lamp']['weak'] = True
        self.make(t['id'], short=True)
        self.j.act('nl_done', task=t['id'])
        self.assertEqual(self.d['peel'], [])
        self.assertEqual(self.overnight(), 0)

    def test_an_old_peel_record_is_bounded_by_what_was_paid(self):
        t = self.at(1, 3)
        self.d['lamp']['weak'] = True
        self.make(t['id'], short=True)
        self.j.act('nl_done', task=t['id'])                     # old saves recorded at the hand-over
        tt = self.j.get(t['id'])
        rec = dict(id=t['id'], day=1, npc=tt['npc'], title=tt['title'][:80], price=tt['price'])
        self.d['peel'] = [rec, dict(rec, id='gone-1', price=7)]
        validate_state(self.j.state)
        self.assertEqual(self.overnight(), 3)                   # unpaid: skipped; a task no longer kept: 7 // 2
        self.assertEqual(self.d['peel'], [])
        self.assertEqual(self.d['stats']['peeled'], 1)
        validate_state(self.j.state)

    def test_long_cure_on_a_good_led_burns(self):
        tid = self.gel_client()
        self.j.act('nl_coat', task=tid, layer='base', p='gel')
        r = self.j.act('nl_cure', task=tid, sec=120)
        self.assertIn('Nóng', r['message'])
        self.assertIn('heat', self.j.get(tid)['flags'])

    def test_thick_colour_wrinkles_and_one_coat_is_patchy(self):
        tid = self.gel_client()
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'do', thick='day')
        self.coat(tid, 'top', 'gel')
        self.j.act('nl_wipe', task=tid)
        self.j.act('nl_done', task=tid)
        self.assertIn('patchy', self.codes(tid))
        tid = self.gel_client()
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'do', thick='day')
        self.coat(tid, 'color', 'gel', 'do')
        self.coat(tid, 'top', 'gel')
        self.j.act('nl_wipe', task=tid)
        self.j.act('nl_done', task=tid)
        self.assertIn('thick', self.codes(tid))

    def test_sticky_layer_and_missing_top(self):
        tid = self.gel_client()
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'do')
        self.coat(tid, 'color', 'gel', 'do')
        self.coat(tid, 'top', 'gel')
        self.j.act('nl_done', task=tid)
        self.assertIn('sticky', self.codes(tid))

    def test_skin_left_uncleaned_lifts(self):
        tid = self.gel_client()
        for i in range(12):
            self.j.act('nl_coat', task=tid, layer='base', p='gel', thick='day')
            if self.j.get(tid)['coats'][-1]['skin']:
                break
        self.assertTrue(self.j.get(tid)['coats'][-1]['skin'])
        self.j.act('nl_cure', task=tid, sec=30)
        self.refused('Không có chỗ sơn lem', 'nl_clean', task=tid)
        self.j.act('nl_done', task=tid)
        self.assertIn('lift', self.codes(tid))

    def test_art_after_the_top_is_loose(self):
        day, slot = find('serve', 'Chị Kiều làm French')
        t = self.at(day, slot)
        tid = t['id']
        self.prep(tid)
        self.coat(tid, 'base', 'gel')
        self.coat(tid, 'color', 'gel', 'sua')
        self.coat(tid, 'color', 'gel', 'sua')
        self.coat(tid, 'top', 'gel')
        self.j.act('nl_art', task=tid, art='french')
        self.j.act('nl_cure', task=tid, sec=60)
        self.j.act('nl_wipe', task=tid)
        self.j.act('nl_done', task=tid)
        self.assertIn('art_loose', self.codes(tid))

    def test_regular_polish_is_not_cured(self):
        t = self.at(1, 1)
        self.prep(t['id'])
        self.coat(t['id'], 'color', 'thuong', 'nude')
        self.refused('Sơn thường thì để khô', 'nl_cure', task=t['id'], sec=60)


class Removal(Base):
    def test_unwrapping_early_keeps_the_gel_and_prying_is_named(self):
        t = self.at(1, 3)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_kit', task=tid)
        r = self.j.act('nl_remove', task=tid, how='wipe')
        self.assertIn('dũa', r['message'])
        self.j.act('nl_remove', task=tid, how='file')
        self.j.act('nl_remove', task=tid, how='wrap')
        self.clock.t += 5
        r = self.j.act('nl_remove', task=tid, how='unwrap')
        self.assertIn('Ủ thêm', r['message'])
        self.assertFalse(self.j.get(tid)['rm']['off'])
        self.j.act('nl_remove', task=tid, how='pry')
        self.j.act('nl_shape', task=tid, shape='vuong', length='ngan')
        self.j.act('nl_done', task=tid)
        self.assertIn('pry', self.codes(tid))

    def test_wrapping_without_filing_does_not_lift_the_gel(self):
        t = self.at(1, 3)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_remove', task=tid, how='wrap')
        self.clock.t += NL.SOAK_S + 5
        r = self.j.act('nl_remove', task=tid, how='unwrap')
        self.assertIn('bám chặt', r['message'])
        self.assertFalse(self.j.get(tid)['rm']['off'])

    def test_polish_over_old_gel_is_named(self):
        t = self.at(1, 3)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_kit', task=tid)
        self.j.act('nl_shape', task=tid, shape='vuong', length='ngan')
        self.coat(tid, 'base', 'gel')
        self.j.act('nl_done', task=tid)
        self.assertIn('old_left', self.codes(tid))


class Refusals(Base):
    def test_disabled_reasons_come_from_the_server(self):
        t = self.at(1, 1)
        tid = t['id']
        self.refused('Hỏi khách', 'nl_inspect', task=tid)
        self.j.act('ask', task=tid)
        self.refused('chỉ cắt ngắn bớt được', 'nl_shape', task=tid, shape='tron', length='dai')
        self.refused('không có sơn cũ', 'nl_remove', task=tid, how='wipe')
        self.refused('Sơn thường ở tiệm chỉ có', 'nl_coat', task=tid, layer='color', p='thuong', colour='mint')
        self.refused('Xem móng khách', 'nl_fix', task=tid)
        self.refused('Không có chỗ nào chảy máu', 'nl_staunch', task=tid)
        self.refused('Chưa có lớp top gel', 'nl_wipe', task=tid)
        self.refused('Chưa làm gì', 'nl_done', task=tid)
        self.refused('Chưa đến lúc thu tiền', 'nl_pay', task=tid, change=[])
        self.refused('Hẹn giờ đèn không có mức đó', 'nl_cure', task=tid, sec=45)

    def test_power_cut_takes_the_battery_lamp(self):
        t = self.at(3, 1)
        NL._desk_hook(self.j.state, self.j.c, 'power', 'off')
        self.assertEqual(self.d['lamp']['kind'], 'pin')
        self.refused('Cúp điện', 'nl_lamp', kind='led')
        self.assertEqual(NL.need_of(self.d, 'color'), 90)


class Hints(Base):
    def test_hints_never_give_the_answer(self):
        seen = set()
        for day in range(1, 12):
            for slot in range(1, 4):
                t = make_task('nail', day, slot, 1)
                c = initial_career('nail')
                seen.add(NL.hint(c, t))
        self.assertEqual(len(seen), 1)            # one generic routine, never the client's colour or cure time
        t = self.at(1, 3)
        h = NL.hint(self.j.c, t)
        for x in NL.COLOURS:
            self.assertNotIn(x['name'].lower(), h.lower())
        for s in NL.CURE_SECS:
            self.assertNotIn(f'{s} giây', h)

    def test_public_task_hides_the_hidden_condition_and_the_cure_need(self):
        t = self.at(1, 3)
        tid = t['id']
        v = public_state(self.j.state)['careers']['nail']['tasks'][0]
        self.assertNotIn('_cond', v)
        self.assertIsNone(v['cond'])
        self.assertIsNone(v['needs'])
        self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_kit', task=tid)
        self.j.act('nl_coat', task=tid, layer='base', p='gel')
        v = public_state(self.j.state)['careers']['nail']['tasks'][0]
        self.assertEqual(v['cond']['old'], 'gel')
        self.assertNotIn('need', v['coats'][0])
        self.assertNotIn('_cond', json.dumps(v))

    def test_content_has_the_lookup_card_but_no_per_client_answers(self):
        x = NL.content()
        self.assertEqual(x['cure']['led']['color'], 60)
        self.assertNotIn('orders', x)
        json.dumps(x, ensure_ascii=False)


class Days(Base):
    def play_day(self):
        self.settle_desk()
        for t in [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled')]:
            self.settle_desk()
            if t['kind'] == 'setup':
                self.j.act('nl_lamp_test')
                if self.d['lamp']['weak']:
                    self.j.act('nl_bulb')
                for a in ('nl_sterilize', 'nl_stock'):
                    self.j.act(a)
                self.j.act('nl_open', task=t['id'])
                continue
            if not t['known']:
                self.j.act('ask', task=t['id'])
            self.j.act('nl_sterilize')
            if t['_cond']['nail'] in ('fungus', 'infected'):
                self.j.act('nl_inspect', task=t['id'])
                self.j.act('nl_decline', task=t['id'], why='health')
                continue
            self.make(t['id'])
            self.settle_desk()
            self.done_pay(t['id'])
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r

    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('nail')
        self.j.act('nl_intro')
        for _ in range(10):
            for x in NL.ITEMS:
                if kit.stock(self.j.c, x['id']) < 4:
                    kit.add_lot(self.j.c, x['id'], 6, x['cost'], x['life'], 'test')
            self.d['power'] = 'on'
            if self.d['lamp']['kind'] == 'pin':
                self.d['lamp']['kind'] = 'led'
            r = self.play_day()
            self.assertIn('lines', r['summary']['career'])
        self.assertGreater(self.d['stats']['clients'], 10)
        v = public_state(self.j.state)
        raw = json.dumps(v['careers']['nail'], ensure_ascii=False)
        self.assertNotIn('_cond', raw)
        s2 = json.loads(json.dumps(self.j.state))
        validate_state(s2)

    def test_validator_rejects_tampering(self):
        t = self.at(1, 3)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('nl_inspect', task=tid)
        self.j.act('nl_kit', task=tid)
        self.j.act('nl_coat', task=tid, layer='base', p='gel')
        validate_state(self.j.state)
        for mutate in (lambda s: s['careers']['nail']['tasks'][0]['coats'][0].update(cure=99999),
                       lambda s: s['careers']['nail']['tasks'][0]['coats'][0].update(l='glitter'),
                       lambda s: s['careers']['nail']['tasks'][0].update(flags=['magic']),
                       lambda s: s['careers']['nail']['tasks'][0]['_cond'].update(nail='ok', old='none'),
                       lambda s: s['careers']['nail']['tasks'][0]['needs'].update(colour='den'),
                       lambda s: s['careers']['nail']['ext']['data']['lamp'].update(kind='laser'),
                       lambda s: s['careers']['nail']['ext']['data']['open'].update(base=dict(n=999, c=1)),
                       lambda s: s['careers']['nail']['ext']['data'].update(power='maybe')):
            bad = copy.deepcopy(self.j.state)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)

    def test_json_round_trip(self):
        t = self.at(1, 3)
        self.make(t['id'])
        self.done_pay(t['id'])
        s = json.loads(json.dumps(self.j.state, ensure_ascii=False))
        validate_state(s)
        self.assertEqual(s['careers']['nail'], json.loads(json.dumps(self.j.c)))


class OldSaves(Base):
    def test_a_save_without_the_shop_gains_it_fresh_and_nothing_else_moves(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s['careers'].pop('nail')
        s['journey']['chapter'] = 3
        s['journey']['unlocked'] = [cid for n in range(1, 4) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['nail'], sort_keys=True), json.dumps(initial_career('nail'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('nail', m['journey']['unlocked'])


if __name__ == '__main__':
    unittest.main()
