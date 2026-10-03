"""Giúp việc theo giờ (plugin career giupviec): the morning cart (cloths, bottles), a client's flat room by
room (the right tool and product per surface, top to bottom, dry before wet), the client's words and
things (a desk to leave alone, a cat, a toddler, a vase, a ring), the walk-through and the pay, regulars,
cô Mai's apprenticeship, determinism, save validation, old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

GV = PLUGINS.get('giupviec')


def find(pred=None, days=range(1, 40), slots=range(1, 6)):
    for day in days:
        for slot in slots:
            t = make_task('giupviec', day, slot, 1)
            if t['kind'] == 'job' and (pred is None or pred(t)):
                return day, slot
    raise AssertionError('no job')


def has_spot(sid):
    return lambda t: any(x['id'] == sid for r in t['needs']['rooms'] for x in r['spots'])


class Base(unittest.TestCase):
    def setUp(self):
        if GV is None:
            raise unittest.SkipTest('giupviec is filtered out by MNL_CAREERS')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, learning=False):
        """A client's flat on its own, the cart already out (clean cloths, full bottles)."""
        self.j = Journey('giupviec', slot=slot, day=day)
        d = GV._data(self.j.c)
        d['intro'] = True
        d['cart'].update(day=day, out=True, cloths='clean', bottles={p: GV.BOTTLE for p in GV.gc.BOTTLES})
        d['learn']['done'] = not learning
        for x in GV.ITEMS:
            kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('gv_desk', option=kit.desk_script(GV.DESK, ev['script'])['default'])

    def hold(self, tool, product):
        self.j.act('gv_tool', tool=tool)
        self.j.act('gv_product', product=product)

    def wipe_clean(self, tid, room, sid):
        t = self.j.get(tid)
        sp = GV.SPOTS[sid]
        self.hold(sp['tools'][0], GV.right_products(t['needs'], sid)[0])
        k = GV.key_of(room, sid)
        for _ in range(GV.MAX_DIRT + 1):
            if self.j.get(tid)['dirt'][k] == 0:
                return
            self.settle_desk()
            self.j.act('gv_wipe', task=tid, spot=sid)
        self.assertEqual(self.j.get(tid)['dirt'][k], 0)

    def clean_room(self, tid, room):
        t = self.j.get(tid)
        n = t['needs']
        if t['room'] != room:
            self.j.act('gv_room', task=tid, room=room)
        for x in n['items']:
            if x['room'] == room and self.j.get(tid)['items'][x['id']] == 'on':
                self.j.act('gv_move', task=tid, item=x['id'])
        spots = next(r['spots'] for r in n['rooms'] if r['id'] == room)
        for s in sorted(spots, key=lambda s: GV.SPOTS[s['id']]['lvl']):
            if GV.key_of(room, s['id']) not in n['skip']:
                self.wipe_clean(tid, room, s['id'])
        for x in n['items']:
            if x['room'] == room and GV.ITEMS_CARE[x['id']]['kind'] == 'fragile' and self.j.get(tid)['items'][x['id']] == 'off':
                self.j.act('gv_back', task=tid, item=x['id'])

    def clean_all(self, tid):
        if not self.j.get(tid)['known']:
            self.j.act('ask', task=tid)
        for r in self.j.get(tid)['needs']['rooms']:
            self.settle_desk()
            self.clean_room(tid, r['id'])
        self.settle_desk()
        return self.j.act('gv_check', task=tid)

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}


class Spec(Base):
    def test_spec_shape(self):
        s = GV.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('giupviec', 'gv_', 'service'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('giupviec', jr.CH_UNLOCKS[2])
        for name in GV.ACTIONS:
            self.assertTrue(name.startswith('gv_'))
        for name in (*GV.NO_TICK, *GV.PHYSICAL, *GV.FREE):
            self.assertTrue(name in GV.ACTIONS or name in ('gv_intro', 'gv_desk'), name)

    def test_content_is_consistent(self):
        for sid, sp in GV.SPOTS.items():
            self.assertTrue(set(sp['tools']) <= set(GV.TOOLS), sid)
            self.assertTrue(set(sp['products']) <= set(GV.PRODUCTS), sid)
            self.assertIn(sp['lvl'], GV.gc.LEVELS)
            for k in sp['harm']:
                self.assertTrue(k in GV.TOOLS or k in GV.PRODUCTS, (sid, k))
                self.assertNotIn(k, sp['products'] + sp['tools'], f'{sid}: the right way never harms')
        for i, h in GV.HOMES.items():
            self.assertTrue(0 < i < len(GV.PEOPLE))
            for room, (always, optional) in h['rooms'].items():
                self.assertIn(room, GV.ROOMS)
                self.assertTrue(set(always) | set(optional) <= set(GV.SPOTS), room)
                self.assertEqual(len(set(always) | set(optional)), len(always) + len(optional))
            for item, room, spot in h['items']:
                self.assertIn(item, GV.ITEMS_CARE)
                self.assertIn(spot, h['rooms'][room][0] + h['rooms'][room][1], f'{item}: sits on a spot of that room')
            self.assertTrue(set(h['notes']) <= set(GV.NOTES))
        for j in GV.JOBS:
            self.assertIn(j[0], GV.HOMES)
            self.assertTrue(j[3] is None or set(j[3]) <= set(GV.HOMES[j[0]]['rooms']))
        self.assertEqual(set(GV.gc.BOTTLES), {p for p, v in GV.PRODUCTS.items() if v['item']})
        self.assertEqual({v['item'] for v in GV.PRODUCTS.values() if v['item']}, {x['id'] for x in GV.ITEMS})

    def test_tasks_are_deterministic_and_one_visit_a_day_each(self):
        kinds = set()
        for day in range(1, 30):
            seen = []
            for slot in range(0, 6):
                a, b = make_task('giupviec', day, slot, 3), make_task('giupviec', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
                if a['kind'] == 'job':
                    seen.append(a['npc'])
            self.assertEqual(len(seen[:3]), len(set(seen[:3])), day)
        self.assertEqual(kinds, set(GV.KINDS))

    def test_jobs_grow_with_the_days(self):
        rooms = lambda day: max(len(make_task('giupviec', day, s, 1)['needs']['rooms']) for s in range(1, 5))
        self.assertEqual(rooms(1), 2)
        self.assertGreaterEqual(max(rooms(d) for d in range(10, 20)), 3)

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in GV.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in GV.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_pay_stays_in_line_with_the_street_trades(self):
        self.assertLessEqual(GV.PRICES['room'] * 4 + GV.REGULAR_BONUS + GV.TET_BONUS, 60)


class Morning(Base):
    def test_wash_fill_and_set_off(self):
        self.j = Journey('giupviec')
        self.j.act('gv_intro')
        t = next(t for t in self.j.c['tasks'] if t['kind'] == 'setup')
        self.assertEqual(self.j.c['active_task'], t['id'])
        self.j.act('gv_wash')
        before = kit.stock(self.j.c, 'chai_kinh')
        r = self.j.act('gv_fill', product='kinh')
        self.assertEqual(self.d['cart']['bottles']['kinh'], GV.BOTTLE)
        self.assertEqual(kit.stock(self.j.c, 'chai_kinh'), before - 1)
        self.assertIn('Chai cũ', r['message'])
        with self.assertRaises(GameError):
            self.j.act('gv_fill', product='kinh')
        for p in GV.gc.BOTTLES:
            if self.d['cart']['bottles'][p] < GV.BOTTLE:
                self.j.act('gv_fill', product=p)
        self.j.act('gv_open', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertFalse(self.codes(t['id']))
        self.assertTrue(self.d['cart']['out'])

    def test_dirty_cloths_and_a_low_bottle_are_named(self):
        self.j = Journey('giupviec')
        self.j.act('gv_intro')
        t = next(t for t in self.j.c['tasks'] if t['kind'] == 'setup')
        self.d['cart']['bottles'] = {p: 1 for p in GV.gc.BOTTLES}
        self.j.act('gv_open', task=t['id'])
        self.assertEqual(self.codes(t['id']), {'cloths', 'bottle'})

    def test_no_work_before_the_cart_is_out(self):
        t = self.at(*find())
        self.d['cart']['out'] = False
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('gv_room', task=t['id'], room=t['needs']['rooms'][0]['id'])

    def test_the_day_ends_with_dirty_cloths(self):
        self.j = Journey('giupviec')
        self.j.act('gv_intro')
        self.d['cart']['cloths'] = 'clean'
        self.j.act('end_day', carry_event=True)
        self.assertEqual(self.d['cart']['cloths'], 'dirty')


class Cleaning(Base):
    def test_a_clean_job_end_to_end(self):
        t = self.at(*find())
        money = self.j.c['money']
        r = self.clean_all(t['id'])
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed', r)
        self.assertFalse(self.codes(t['id']), r)
        self.assertEqual(t['price'], GV.PRICES['room'] * len(t['needs']['rooms']) + (GV.TET_BONUS if t['needs']['tet'] else 0))
        self.assertGreaterEqual(self.j.c['money'], money + t['price'])
        self.assertIn('Ting ting', r['message'])
        self.assertTrue(all(x['ok'] for x in t['check']))
        self.assertTrue(self.d['regulars'][str(GV._npc_index(t))]['happy'])

    def test_wrong_tool_or_product_does_nothing_but_costs_time(self):
        t = self.at(*find(has_spot('guong')))
        tid = t['id']
        self.j.act('ask', task=tid)
        room = next(r['id'] for r in t['needs']['rooms'] if any(x['id'] == 'guong' for x in r['spots']))
        self.j.act('gv_room', task=tid, room=room)
        k = GV.key_of(room, 'guong')
        dirt, pat = self.j.get(tid)['dirt'][k], self.j.get(tid)['patience']
        self.hold('cay_lau', 'kinh')
        r = self.j.act('gv_wipe', task=tid, spot='guong')
        self.assertFalse(r['correct'])
        self.hold('khan_xanh', 'da_nang')
        self.j.act('gv_wipe', task=tid, spot='guong')
        t = self.j.get(tid)
        self.assertEqual(t['dirt'][k], dirt)
        self.assertEqual(t['waste'], 2)
        self.assertLess(t['patience'], pat)
        self.assertFalse(self.codes(tid))
        self.hold('khan_xanh', 'kinh')
        r = self.j.act('gv_wipe', task=tid, spot='guong')
        self.assertTrue(r['correct'])
        self.assertEqual(self.j.get(tid)['dirt'][k], dirt - 1)

    def test_the_red_cloth_is_for_the_toilet_only(self):
        t = self.at(*find(has_spot('lavabo')))
        tid = t['id']
        self.j.act('ask', task=tid)
        room = next(r['id'] for r in t['needs']['rooms'] if any(x['id'] == 'lavabo' for x in r['spots']))
        self.j.act('gv_room', task=tid, room=room)
        for x in t['needs']['items']:
            if x['room'] == room:
                self.j.act('gv_move', task=tid, item=x['id'])
        self.hold('khan_do', 'da_nang')
        self.j.act('gv_wipe', task=tid, spot='lavabo')
        self.assertIn('red_cloth', self.codes(tid))

    def test_a_harsh_product_damages_the_surface(self):
        t = self.at(*find(has_spot('ban_an')))
        tid = t['id']
        self.j.act('ask', task=tid)
        room = next(r['id'] for r in t['needs']['rooms'] if any(x['id'] == 'ban_an' for x in r['spots']))
        self.j.act('gv_room', task=tid, room=room)
        self.hold('khan_vang', 'dau_mo')
        r = self.j.act('gv_wipe', task=tid, spot='ban_an')
        self.assertIn('bạc', r['message'])
        self.assertIn('harm_ban_an', self.codes(tid))

    def test_top_to_bottom_dust_falls_on_what_is_done(self):
        t = self.at(*find(lambda t: any({x['id'] for x in r['spots']} >= {'quat_tran', 'san_quet'} for r in t['needs']['rooms'])))
        tid = t['id']
        self.j.act('ask', task=tid)
        room = next(r['id'] for r in t['needs']['rooms'] if {x['id'] for x in r['spots']} >= {'quat_tran', 'san_quet'})
        self.j.act('gv_room', task=tid, room=room)
        self.wipe_clean(tid, room, 'san_quet')
        self.hold('phat_tran', 'kho')
        k = GV.key_of(room, 'quat_tran')
        for _ in range(self.j.get(tid)['dirt'][k]):
            r = self.j.act('gv_wipe', task=tid, spot='quat_tran')
        self.assertIn('lau lại', r['message'])
        self.assertEqual(self.j.get(tid)['dirt'][GV.key_of(room, 'san_quet')], 1)
        self.assertGreater(self.j.get(tid)['redo'], 0)

    def test_mopping_a_dusty_floor_only_smears_it(self):
        t = self.at(*find(has_spot('san_lau')))
        tid = t['id']
        self.j.act('ask', task=tid)
        room = next(r['id'] for r in t['needs']['rooms'] if any(x['id'] == 'san_lau' for x in r['spots']))
        self.j.act('gv_room', task=tid, room=room)
        k = GV.key_of(room, 'san_lau')
        dirt = self.j.get(tid)['dirt'][k]
        self.hold('cay_lau', GV.right_products(t['needs'], 'san_lau')[0])
        r = self.j.act('gv_wipe', task=tid, spot='san_lau')
        self.assertIn('Quét trước', r['message'])
        self.assertEqual(self.j.get(tid)['dirt'][k], dirt)

    def test_a_walk_through_names_what_is_left(self):
        t = self.at(*find())
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room=t['needs']['rooms'][0]['id'])
        money = self.j.c['money']
        r = self.j.act('gv_check', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('dirty', self.codes(tid))
        self.assertIn('✗', r['message'])
        self.assertLessEqual(self.j.c['money'] - money, t['price'])
        self.assertFalse(self.d['regulars'][str(GV._npc_index(t))]['happy'])

    def test_a_happy_client_adds_to_the_next_job(self):
        t = self.at(*find())
        i = str(GV._npc_index(t))
        self.d['regulars'][i] = dict(visits=1, happy=True)
        GV.on_task(self.j.state, self.j.c, self.j.get(t['id']))
        self.assertTrue(self.j.get(t['id'])['regular'])
        self.clean_all(t['id'])
        t = self.j.get(t['id'])
        self.assertEqual(t['price'], GV.PRICES['room'] * len(t['needs']['rooms']) + GV.REGULAR_BONUS + (GV.TET_BONUS if t['needs']['tet'] else 0))
        self.assertEqual(t['story'], GV.REG_STORY[int(i)][1])


class ClientWords(Base):
    def test_the_desk_is_left_alone(self):
        t = self.at(*find(lambda t: 'desk' in t['needs']['notes']))
        tid = t['id']
        self.assertEqual(t['needs']['skip'], ['khach.ban_lam_viec'])
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room='khach')
        self.hold('khan_vang', 'kho')
        self.j.act('gv_wipe', task=tid, spot='ban_lam_viec')
        self.assertIn('skip', self.codes(tid))
        self.assertEqual(self.j.get(tid)['touched'], ['khach.ban_lam_viec'])
        self.j.act('gv_wipe', task=tid, spot='ban_lam_viec')
        self.assertEqual(sum(1 for x in self.j.get(tid)['slips'] if x['code'] == 'skip'), 1)

    def test_a_desk_left_alone_is_not_dirty_at_the_walk_through(self):
        t = self.at(*find(lambda t: 'desk' in t['needs']['notes']))
        self.clean_all(t['id'])
        self.assertFalse(self.codes(t['id']))

    def test_carry_the_cat_out_and_mop_with_clean_water(self):
        t = self.at(*find(lambda t: 'cat' in t['needs']['notes'] and any(x['id'] == 'meo' for x in t['needs']['items'])))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room='khach')
        self.hold('hut_bui', 'kho')
        r = self.j.act('gv_wipe', task=tid, spot='sofa')
        self.assertIn('pet', self.codes(tid))
        self.assertEqual(self.j.get(tid)['items']['meo'], 'off')
        self.assertEqual(GV.right_products(t['needs'], 'san_lau'), ('nuoc',))
        self.wipe_clean(tid, 'khach', 'san_quet')
        self.hold('cay_lau', 'lau_san')
        self.j.act('gv_wipe', task=tid, spot='san_lau')
        self.assertIn('gentle', self.codes(tid))

    def test_a_vase_is_lifted_off_and_put_back(self):
        t = self.at(*find(lambda t: any(x['id'] == 'binh_gom' for x in t['needs']['items'])))
        tid = t['id']
        self.clean_all(tid)
        self.assertEqual(self.j.get(tid)['items']['binh_gom'], 'back')
        self.assertFalse(self.codes(tid))

    def test_a_vase_left_on_the_cabinet(self):
        t = self.at(*find(lambda t: any(x['id'] == 'binh_gom' for x in t['needs']['items'])))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room='tho')
        money = self.j.c['money']
        self.hold('khan_xanh', 'kinh')
        r = self.j.act('gv_wipe', task=tid, spot='tu_kinh')
        codes = self.codes(tid)
        self.assertTrue(codes & {'broke', 'wobble'}, r)
        if 'broke' in codes:
            self.assertEqual(self.j.get(tid)['items']['binh_gom'], 'broken')
            self.assertEqual(self.j.c['money'], money - GV.ITEMS_CARE['binh_gom']['comp'])

    def test_a_vase_not_put_back_is_noticed(self):
        t = self.at(*find(lambda t: any(x['id'] == 'binh_gom' for x in t['needs']['items'])))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room='tho')
        self.j.act('gv_move', task=tid, item='binh_gom')
        self.j.act('gv_check', task=tid)
        self.assertIn('not_back', self.codes(tid))

    def test_a_ring_in_the_tray_is_handed_back(self):
        t = self.at(*find(lambda t: any(x['id'] == 'nhan' for x in t['needs']['items'])))
        r = self.clean_all(t['id'])
        self.assertIn('nhẫn', r['message'])
        self.assertEqual(self.d['stats']['kept'], 1)


class Apprenticeship(Base):
    def test_co_mai_stops_each_mistake_once(self):
        t = self.at(*find(lambda t: 'desk' in t['needs']['notes']), learning=True)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room='khach')
        self.hold('khan_vang', 'kho')
        r = self.j.act('gv_wipe', task=tid, spot='ban_lam_viec')
        self.assertIn('Cô Mai', r['message'])
        self.assertEqual(r['lesson'], 'skip')
        self.assertFalse(self.codes(tid))
        self.j.act('gv_wipe', task=tid, spot='ban_lam_viec')
        self.assertIn('skip', self.codes(tid))

    def test_two_jobs_and_she_lets_you_go_alone(self):
        t = self.at(*find(), learning=True)
        self.assertTrue(GV.public_data(self.j.c)['learn']['on'])
        r = None
        for n in range(GV.APPRENTICE):
            if n:
                t = make_task('giupviec', 1, n + 1, 1)
                self.j.c['tasks'].append(t)
                GV.on_task(self.j.state, self.j.c, t)
                self.j.c['active_task'] = t['id']
            r = self.clean_all(t['id'])
        self.assertIn('Học nghề xong', r['message'])
        self.assertTrue(self.d['learn']['done'])
        self.assertFalse(GV.public_data(self.j.c)['learn']['on'])


class Days(Base):
    def play_day(self):
        self.settle_desk()
        for t in [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled')]:
            self.settle_desk()
            if t['kind'] == 'setup':
                if self.d['cart']['cloths'] != 'clean':
                    self.j.act('gv_wash')
                for p in GV.gc.BOTTLES:
                    if self.d['cart']['bottles'][p] < 8:
                        self.j.act('gv_fill', product=p)
                self.j.act('gv_open', task=t['id'])
                continue
            self.clean_all(t['id'])
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r

    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('giupviec')
        self.j.act('gv_intro')
        for _ in range(10):
            for x in GV.ITEMS:
                if kit.stock(self.j.c, x['id']) < 4:
                    kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
            r = self.play_day()
            car = r['summary']['career']
            self.assertIn('lines', car)
            self.assertIn('tomorrow', car)
        self.assertGreater(self.d['stats']['jobs'], 10)
        self.assertEqual(self.d['stats']['perfect'], self.d['stats']['jobs'])
        v = public_state(self.j.state)
        json.dumps(v['careers']['giupviec'])

    def test_public_task_hides_the_job_until_asked(self):
        t = self.at(*find())
        self.assertIsNone(GV.public_task(t)['needs'])
        self.j.act('ask', task=t['id'])
        v = GV.public_task(self.j.get(t['id']))
        self.assertEqual(v['needs']['rooms'], t['needs']['rooms'])

    def test_validator_rejects_tampering(self):
        t = self.at(*find(lambda t: t['needs']['items']))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.j.act('gv_room', task=tid, room=t['needs']['rooms'][0]['id'])
        validate_state(self.j.state)
        task = lambda s: next(x for x in s['careers']['giupviec']['tasks'] if x['id'] == tid)
        data = lambda s: s['careers']['giupviec']['ext']['data']
        item = t['needs']['items'][0]['id']
        for mutate in (lambda s: task(s)['dirt'].update({k: 9 for k in task(s)['dirt']}),
                       lambda s: task(s)['dirt'].update({'khach.lo_vu_tru': 1}),
                       lambda s: task(s)['items'].update({item: 'gone'}),
                       lambda s: task(s).update(room='san_thuong'),
                       lambda s: task(s).update(regular='yes'),
                       lambda s: task(s)['needs']['rooms'][0]['spots'][0].update(dirt=0),
                       lambda s: data(s)['cart']['bottles'].update(kinh=99),
                       lambda s: data(s)['cart'].update(cloths='sparkling'),
                       lambda s: data(s)['hand'].update(tool='robot'),
                       lambda s: data(s)['regulars'].update({'9': dict(visits=1, happy=True)})):
            bad = copy.deepcopy(self.j.state)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)


class OldSaves(Base):
    def story_save(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        return s

    def test_a_save_without_the_team_gains_it_fresh_and_nothing_else_moves(self):
        s = self.story_save()
        s['careers'].pop('giupviec')
        s['journey']['chapter'] = 3
        s['journey']['unlocked'] = [cid for n in range(1, 4) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['giupviec'], sort_keys=True), json.dumps(initial_career('giupviec'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('giupviec', m['journey']['unlocked'])

    def test_data_from_an_older_build_fills_in(self):
        t = self.at(*find())
        for k in ('learn', 'regulars', 'stats', 'hand'):
            self.d.pop(k)
        self.d['cart']['bottles'].pop('kinh')
        self.j.act('ask', task=t['id'])
        validate_state(self.j.state)


if __name__ == '__main__':
    unittest.main()
