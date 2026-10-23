"""🗺️ Tổng quan nhà (game/home_overview.py), 🚘 Hầm để xe (game/villa_garage.py), 🧹 Việc nhà (game/home_chores.py) and
🏖️ Chơi trên đảo (game/island_fun.py), owner 23/10 "biệt thự ok thêm hầm để xe, với nhìn được tổng quan cái nhà nữa…
tăng tương tác hơn" and F#271 (hầm để xe của biệt thự sân vườn).

Plans for every place a player can live in, matching the rooms the interior opens; the garage derived from the vehicles
owned (no migration), its bays by the villa, picks and washes; the chores' rules and caps; the beach acts and the chest,
checked on the island at commit; the saves (absent blocks, broken blocks, older builds)."""
import copy
import unittest
from unittest.mock import patch

from game import deco as dc
from game import estates_content as EC
from game import garage as gr
from game import home_chores as hc
from game import home_overview as ho
from game import housing as hs
from game import island_fun as fun
from game import journey as jr
from game import villa_garage as vg
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story
from tests.test_deco import owner, place_new, renter

TRIP = 'ab' * 8


def in_villa(eid='bt_vuon_da_lat', wallet=400_000):
    from tests.test_estate_moves import in_villa as go
    return go(eid, wallet=wallet)


def buy_cars(s, *ids):
    s['journey']['wallet'] = max(s['journey']['wallet'], 2_000_000)
    for vid in ids:
        s, _ = act(s, 'jr_garage_buy', id=vid, confirm=True)
    return s


def HL(s):
    return public_state(s)['journey']['homelife']


def adopt(s, kind, who):
    """jr_hh_adopt (its payload has a 'name': not through act()'s keyword)."""
    from game.engine import apply_action
    return apply_action(s, None, 'jr_hh_adopt', dict(kind=kind, name=who, confirm=True))


def refused(test, s, name, code, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(cm.exception.code, code, cm.exception.message)
    test.assertEqual(s, before)


def spirit(s):
    return s['journey']['life']['spirit']


def next_day(s, n=1):
    for _ in range(n):
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_seen', ids=['x'])
    return s


class Plans(unittest.TestCase):
    def test_every_place_has_a_plan_with_the_interiors_rooms(self):
        kinds = ho.kinds()
        self.assertEqual(set(kinds), {'attic', 'tro_moi', 'ky_tuc_xa'} | set(hs.OWN) | {e['id'] for e in EC.ESTATES})
        cat = ho.catalogue()
        self.assertEqual(set(cat), set(kinds))
        for k, p in cat.items():
            with self.subTest(k):
                rooms = [r for f in p['floors'] for r in f['rooms']]
                self.assertTrue(rooms)
                self.assertEqual(len({r['id'] for r in rooms}), len(rooms))
                self.assertEqual([f['fl'] for f in p['floors']], sorted({f['fl'] for f in p['floors']}))
                self.assertTrue(all(r['zone'] in ('in', 'garden', 'deck') for r in rooms))
                self.assertGreaterEqual(p['garage']['slots'], 1)
                self.assertIn(p['garage']['style'], ('ham', 'san', 'nha', 'chung', 'bai'))

    def test_the_plan_is_the_place_the_interior_draws(self):
        """A tap on a room of the plan opens that room: same ids as deco.public's rooms + kits, for each way of living."""
        for s in (story(), renter('tro_moi'), renter('ky_tuc_xa'), owner('tap_the'), owner('nha_san', 20000),
                  owner('biet_thu_vuon', 90000), owner('biet_thu_song', 120000), in_villa('bt_kinh', 900_000)):
            d = public_state(s)['journey']['deco']
            kind = ho.place_kind(d)
            with self.subTest(kind):
                self.assertIsNotNone(kind)
                want = {r['id'] for r in d['rooms']} | {dc.DC.KITS[m['t']]['id'] for m in d['more']}
                self.assertEqual(set(ho.room_ids(kind)), want)
                self.assertEqual(HL(s)['ov']['kind'], kind)

    def test_villas_have_floors_a_garden_a_pool_and_a_basement_garage(self):
        vuon = ho.plan_of('biet_thu_vuon')
        self.assertEqual([f['fl'] for f in vuon['floors']], [1, 2])
        ground = {r['id']: r['zone'] for r in vuon['floors'][0]['rooms']}
        self.assertEqual((ground['yard'], ground['pool'], ground['living']), ('garden', 'garden', 'in'))
        self.assertIn('bed', [r['id'] for r in vuon['floors'][1]['rooms']])
        self.assertEqual((vuon['garage']['style'], vuon['garage']['slots']), ('ham', 4))
        self.assertTrue(vuon['has']['garden'] and vuon['has']['pool'] and vuon['has']['garage'])
        song = ho.plan_of('biet_thu_song')
        self.assertEqual(len(song['floors']), 3)   # 🏰 its three-floor inside (game/estates_content.py SONG_HONG_V2)
        self.assertEqual(song['garage']['berth'], 'Bến riêng ven sông')
        dao = ho.plan_of('dinh_thu_dao')
        self.assertEqual((dao['garage']['slots'], dao['has']['floors']), (12, 3))
        self.assertEqual(ho.plan_of('can_ho_2pn')['floors'][0]['name'], 'Căn hộ')
        self.assertEqual(ho.plan_of('can_ho_2pn')['garage']['style'], 'chung')
        self.assertEqual([f['name'] for f in ho.plan_of('nha_pho')['floors']], ['Tầng trệt', 'Lầu 1'])
        self.assertIsNone(ho.plan_of('khong_co'))
        slots = [ho.plan_of(k)['garage']['slots'] for k in ('bt_vuon_da_lat', 'bt_dong_duong', 'bt_kinh', 'penthouse_sky', 'dinh_thu_dao')]
        self.assertEqual(slots, sorted(slots))   # dearer villas, more bays

    def test_catalogue_in_the_content(self):
        c = jr.content()['homelife']
        self.assertEqual(set(c['plans']), set(ho.kinds()))
        self.assertEqual([a['id'] for a in c['chores']['acts']], list(hc.ACTS))
        self.assertEqual([a['id'] for a in c['beach']['acts']], list(fun.ACTS))


class Overview(unittest.TestCase):
    def test_rooms_count_pieces_and_cozy(self):
        s = owner('biet_thu_vuon', 90000)
        s, _ = place_new(s, 'sofa', 'living')
        s, _ = place_new(s, 'ban_tra', 'living')
        s, _ = place_new(s, 'giuong', 'bed')
        ov = HL(s)['ov']
        D = dc.DC.ITEMS
        self.assertEqual(ov['rooms']['living'], [2, D['sofa']['cozy'] + D['ban_tra']['cozy']])
        self.assertEqual(ov['rooms']['bed'], [1, D['giuong']['cozy']])
        self.assertNotIn('kitchen', ov['rooms'])
        self.assertEqual(ov['where'], 'own')
        self.assertEqual(ho.room_stats(None), {})
        # a set done in a room adds its bonus there
        dpub = dict(items=[dict(r='bed', k='giuong')], sets=[dict(id='ngu', done=True, room='bed'), dict(id='hoc', done=False, room='bed')])
        self.assertEqual(ho.room_stats(dpub)['bed'], [1, D['giuong']['cozy'] + dc.DC.SETS['ngu']['bonus']])

    def test_who_is_home_and_the_other_homes(self):
        s = owner('nha_san', 20000)
        s['journey']['life_day'] = 10
        s, _ = adopt(s, 'cat', 'Miu')
        ov = HL(s)['ov']
        self.assertEqual(ov['who'][0]['k'], 'me')
        self.assertIn(dict(k='pet', n='Miu', e='🐱'), ov['who'])
        self.assertNotIn('homes', ov)   # one home: no list (state size)
        s['journey']['wallet'] = 200_000
        s, _ = act(s, 'jr_home_buy', kind='biet_thu_vuon', down=hs.HOMES['biet_thu_vuon']['price'], confirm=True, move_in=False)
        homes = HL(s)['ov']['homes']
        self.assertEqual(homes, [dict(kind='nha_san', live=True), dict(kind='biet_thu_vuon', live=False)])

    def test_attic_and_outside_story(self):
        s = story()
        self.assertEqual(HL(s)['ov']['kind'], 'attic')
        from game.engine import new_state
        self.assertNotIn('homelife', public_state(new_state())['journey'])


class Garage(unittest.TestCase):
    def test_derived_from_the_vehicles_owned(self):
        s = owner('biet_thu_vuon', 90000)
        h = HL(s)['hamxe']
        self.assertEqual((h['style'], h['name'], h['slots'], h['park'], h.get('out')), ('ham', 'Hầm để xe Vườn Cau', 4, [], None))
        s = buy_cars(s, 'xe_dap', 'o_to_mini', 'mui_tran', 'xe_ga', 'o_to_suv', 'thuyen_buom', 'truc_thang')
        self.assertNotIn('hamxe', s['journey'])   # nothing stored: derived
        h = HL(s)['hamxe']
        # the vehicle ridden first (the first bought), then the dearest; the fifth road vehicle waits outside
        self.assertEqual(h['park'], ['xe_dap', 'mui_tran', 'o_to_suv', 'o_to_mini'])
        self.assertEqual(h['out'], ['xe_ga'])
        self.assertEqual(h['water'], [['thuyen_buom', vg.MARINA]])
        self.assertEqual(h['air'], [['truc_thang', vg.AIRPORT]])

    def test_bays_follow_where_you_live(self):
        s = buy_cars(owner('can_ho_mini', 9000), 'xe_ga', 'o_to_mini', 'o_to_suv')
        h = HL(s)['hamxe']
        self.assertEqual((h['style'], h['slots'], len(h['park']), len(h['out'])), ('chung', 2, 2, 1))
        s = buy_cars(in_villa('dinh_thu_dao', 3_000_000), 'du_thuyen', 'truc_thang', 'phan_luc')
        h = HL(s)['hamxe']
        self.assertEqual(h['slots'], 12)
        self.assertEqual(h['water'], [['du_thuyen', 'Bến ca nô của đảo']])
        self.assertEqual(dict(h['air']), {'truc_thang': 'Sân trực thăng trên đảo', 'phan_luc': vg.AIRPORT})   # a jet needs the airport
        self.assertEqual(HL(story())['hamxe']['style'], 'bai')

    def test_park_picks(self):
        s = buy_cars(owner('biet_thu_vuon', 90000), 'xe_dap', 'o_to_mini', 'mui_tran', 'xe_ga', 'o_to_suv', 'thuyen_buom')
        s, r = act(s, 'jr_hamxe_park', ids=['xe_ga', 'o_to_mini'])
        h = HL(s)['hamxe']
        self.assertEqual(h['park'][:2], ['xe_ga', 'o_to_mini'])
        self.assertEqual(len(h['park']), 4)
        self.assertEqual(set(h['park'] + h['out']), {'xe_dap', 'o_to_mini', 'mui_tran', 'xe_ga', 'o_to_suv'})
        _, r = act(s, 'jr_hamxe_park', ids=['xe_ga', 'o_to_mini'])
        self.assertTrue(r.get('duplicate'))
        refused(self, s, 'jr_hamxe_park', 'not_owned', ids=['thuyen_buom'])          # a boat never parks in the hầm
        refused(self, s, 'jr_hamxe_park', 'not_owned', ids=['sieu_xe'])              # not yours
        refused(self, s, 'jr_hamxe_park', 'not_owned', ids=['xe_ga', 'xe_ga'])
        refused(self, s, 'jr_hamxe_park', 'limit', ids=['xe_dap', 'o_to_mini', 'mui_tran', 'xe_ga', 'o_to_suv'])
        with self.assertRaises(GameError):
            act(s, 'jr_hamxe_park', ids='xe_ga')
        # a car sold: its pick is simply skipped; back to automatic with []
        s, _ = act(s, 'jr_garage_sell', id='xe_ga', confirm=True)
        self.assertEqual(HL(s)['hamxe']['park'][0], 'o_to_mini')
        s, _ = act(s, 'jr_hamxe_park', ids=[])
        self.assertEqual(s['journey']['hamxe']['park'], [])

    def test_wash_once_a_day_spirit_only_on_the_first(self):
        s = buy_cars(owner('biet_thu_vuon', 90000), 'xe_ga', 'o_to_mini')
        s['journey']['life']['spirit'] = 50
        s, r = act(s, 'jr_hamxe_wash', id='xe_ga')
        self.assertEqual(spirit(s), 50 + vg.WASH_SPIRIT)
        self.assertTrue(r['message'].startswith('🫧'))
        _, r = act(s, 'jr_hamxe_wash', id='xe_ga')
        self.assertTrue(r.get('duplicate'))
        s, r = act(s, 'jr_hamxe_wash', id='o_to_mini')
        self.assertEqual(spirit(s), 50 + vg.WASH_SPIRIT)   # the second wash of the day: shine only
        self.assertEqual(HL(s)['hamxe']['wash'], ['xe_ga', 'o_to_mini'])
        refused(self, s, 'jr_hamxe_wash', 'not_owned', id='sieu_xe')
        with self.assertRaises(GameError):
            act(s, 'jr_hamxe_wash', id='nope')
        s = next_day(s)
        self.assertNotIn('wash', HL(s)['hamxe'])
        sp = spirit(s)
        s, _ = act(s, 'jr_hamxe_wash', id='o_to_mini')
        self.assertEqual(spirit(s), min(100, sp + vg.WASH_SPIRIT))
        self.assertEqual(s['journey']['hamxe']['n'], 3)

    def test_save_shapes(self):
        s = buy_cars(owner('biet_thu_vuon', 90000), 'xe_ga')
        s, _ = act(s, 'jr_hamxe_wash', id='xe_ga')
        validate_state(s)
        bad = copy.deepcopy(s)
        bad['journey']['hamxe']['wash'] = 'xe_ga'
        with self.assertRaises(GameError):
            validate_state(bad)
        fixed = migrate_state(copy.deepcopy(bad))   # an unreadable block is dropped on load: the vehicles stay
        self.assertNotIn('hamxe', fixed['journey'])
        self.assertIn('xe_ga', fixed['journey']['garage']['cars'])
        future = copy.deepcopy(s)
        future['journey']['hamxe']['park'] = ['xe_moi_2027']   # a vehicle a newer build knows: kept by shape, not shown
        validate_state(future)
        self.assertEqual(HL(future)['hamxe']['park'], ['xe_ga'])


class Chores(unittest.TestCase):
    def test_what_each_place_offers(self):
        # Bà Tám's attic: no garden, no plant, no kitchen, no pet, nobody; the codes' texts are in the catalogue
        self.assertEqual(HL(story())['chores'], dict(done=[], no=dict(tuoi_cay='green', nau_com='kitchen', choi_pet='pet', ca_nha='family')))
        self.assertEqual(jr.content()['homelife']['chores']['why'], hc.WHY)
        s = owner('biet_thu_vuon', 90000)
        self.assertEqual(HL(s)['chores']['no'], dict(choi_pet='pet', ca_nha='family'))
        refused(self, story(), 'jr_chore_do', 'not_here', act='nau_com')
        refused(self, s, 'jr_chore_do', 'not_here', act='choi_pet')
        with self.assertRaises(GameError):
            act(s, 'jr_chore_do', act='ngu')

    def test_a_plant_makes_the_attic_green_and_a_pet_or_child_opens_theirs(self):
        s = story(wallet=5000)
        plants = [k for k, it in dc.DC.ITEMS.items() if 'plant' in it['tags'] and 'studio' in it['rooms'] and it['price'] and not it.get('uq')]
        s, _ = place_new(s, plants[0], 'attic')
        self.assertNotIn('tuoi_cay', HL(s)['chores']['no'])
        s['journey']['life_day'] = 10
        s, _ = adopt(s, 'dog', 'Vàng')
        s, r = act(s, 'jr_chore_do', act='choi_pet')
        self.assertIn('Vàng', r['message'])
        self.assertEqual(HL(s)['chores']['no'], dict(nau_com='kitchen', ca_nha='family'))

    def test_rewards_and_caps(self):
        s = owner('biet_thu_vuon', 90000)
        s['journey']['life']['spirit'] = 50
        w0 = s['journey']['wallet']
        s, r1 = act(s, 'jr_chore_do', act='don_nha')
        s, r2 = act(s, 'jr_chore_do', act='tuoi_cay')
        self.assertEqual(spirit(s), 52)
        self.assertEqual(s['journey']['wallet'], w0)
        s, r3 = act(s, 'jr_chore_do', act='nau_com')
        self.assertEqual(spirit(s), 52)                                  # SPIRIT_MAX a day
        self.assertEqual(s['journey']['wallet'], w0 + hc.BONUS_XU)       # the third: "nhà gọn gàng"
        self.assertEqual(r3['chore']['xu'], hc.BONUS_XU)
        self.assertEqual(s['journey']['history'][-1]['kind'], hc.KIND)
        refused(self, s, 'jr_chore_do', 'already_done', act='don_nha')
        c = HL(s)['chores']
        self.assertEqual(c, dict(done=['don_nha', 'tuoi_cay', 'nau_com'], no=dict(choi_pet='pet', ca_nha='family'), paid=True, streak=1))
        # days in a row: the streak; every STREAK_EVERY-th day pays STREAK_XU more; never more than both a day
        paid = []
        for _ in range(hc.STREAK_EVERY - 1):
            s = next_day(s)
            w = s['journey']['wallet']
            for a in ('don_nha', 'tuoi_cay', 'nau_com'):
                s, _ = act(s, 'jr_chore_do', act=a)
            paid.append(s['journey']['wallet'] - w)
        self.assertEqual(paid, [hc.BONUS_XU] * (hc.STREAK_EVERY - 2) + [hc.BONUS_XU + hc.STREAK_XU])
        self.assertEqual(s['journey']['chores']['streak'], hc.STREAK_EVERY)
        self.assertLessEqual(hc.BONUS_XU + hc.STREAK_XU, 30)
        # a day skipped: the streak starts again
        s = next_day(s, 2)
        self.assertNotIn('streak', HL(s)['chores'])
        for a in ('don_nha', 'tuoi_cay', 'nau_com'):
            s, _ = act(s, 'jr_chore_do', act=a)
        self.assertEqual(s['journey']['chores']['streak'], 1)

    def test_save_shapes(self):
        s = owner('tap_the')
        s, _ = act(s, 'jr_chore_do', act='don_nha')
        validate_state(s)
        bad = copy.deepcopy(s)
        bad['journey']['chores']['paid'] = 2
        with self.assertRaises(GameError):
            validate_state(bad)
        self.assertNotIn('chores', migrate_state(bad)['journey'])
        future = copy.deepcopy(s)
        future['journey']['chores']['did'].append('lau_kinh')   # a chore a newer build knows
        validate_state(future)


class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def __call__(self):
        return self.t


class Beach(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        p = patch('game.island_fun.now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def test_acts_once_a_day_spirit_capped(self):
        s = owner('tap_the')
        s['journey']['life']['spirit'] = 40
        got = []
        for a in fun.ACTS:
            s, r = act(s, 'jr_beach_do', trip=TRIP, act=a)
            got.append(r['beach']['spirit'])
            self.assertTrue(r['message'].startswith(fun.ACTS[a]['emoji']))
        self.assertEqual(got, [1] * fun.SPIRIT_MAX + [0] * (len(fun.ACTS) - fun.SPIRIT_MAX))
        self.assertEqual(spirit(s), 40 + fun.SPIRIT_MAX)
        _, r = act(s, 'jr_beach_do', trip=TRIP, act='boi')
        self.assertTrue(r.get('duplicate'))
        self.assertEqual(HL(s)['beach']['did'], list(fun.ACTS))
        self.clock.t += 86400
        self.assertNotIn('beach', HL(s))   # a new day: nothing done yet
        s, r = act(s, 'jr_beach_do', trip=TRIP, act='boi')
        self.assertEqual(r['beach']['spirit'], 1)

    def test_chest_once_a_day_a_few_xu(self):
        s = story()
        w = s['journey']['wallet']
        s, r = act(s, 'jr_beach_chest', trip=TRIP)
        xu = r['beach']['xu']
        self.assertTrue(fun.CHEST_XU[0] <= xu <= fun.CHEST_XU[1])
        self.assertEqual(s['journey']['wallet'], w + xu)
        _, r = act(s, 'jr_beach_chest', trip=TRIP)
        self.assertTrue(r.get('duplicate'))
        self.assertTrue(HL(s)['beach']['chest'])
        self.clock.t += 86400
        s, r = act(s, 'jr_beach_chest', trip=TRIP)
        self.assertIn('xu', r['beach'])

    def test_payload(self):
        s = story()
        for p in (dict(act='boi'), dict(trip='nope', act='boi'), dict(trip=TRIP, act='ngu'), dict(trip=TRIP, act='boi', x=1)):
            with self.assertRaises(GameError):
                act(s, 'jr_beach_do', **p)
        with self.assertRaises(GameError):
            act(s, 'jr_beach_chest', trip=TRIP, act='boi')

    def test_checked_on_the_island_at_commit(self):
        s, r = act(story(), 'jr_beach_do', trip=TRIP, act='boi')

        class Row(dict):
            pass

        class DB:
            def __init__(self, row):
                self.row, self.args = row, None

            def execute(self, sql, args):
                self.args = args
                return self

            def fetchone(self):
                return self.row

        on = Row(status='open', ends=self.clock.t + 3600, owner='sid1', seat=None, friends_ok=False, blocked=False, pub='', visit='')
        db = DB(on)
        fun.command_commit(db, 'sid1', 'jr_beach_do', s, r)
        self.assertEqual(db.args, ('sid1', TRIP))
        with self.assertRaises(GameError) as cm:
            fun.command_commit(DB(None), 'sid1', 'jr_beach_do', s, r)             # no such trip / not aboard
        self.assertEqual(cm.exception.code, 'no_island')
        with self.assertRaises(GameError):
            fun.command_commit(DB(Row(on, ends=self.clock.t - 1)), 'sid1', 'jr_beach_do', s, r)   # the trip is over
        fun.command_commit(DB(None), 'sid1', 'jr_beach_do', s, dict(duplicate=True))           # a tap on something done
        fun.command_commit(DB(None), 'sid1', 'jr_garage_trip', s, {})                            # not ours

    def test_save_shapes(self):
        s, _ = act(story(), 'jr_beach_do', trip=TRIP, act='boi')
        validate_state(s)
        bad = copy.deepcopy(s)
        bad['journey']['beach']['trip'] = 'x'
        with self.assertRaises(GameError):
            validate_state(bad)
        self.assertNotIn('beach', migrate_state(bad)['journey'])


from tests.pg_support import pg_only   # noqa: E402
from tests import test_island_build_db as _isle_db   # noqa: E402


@pg_only
class BeachOnTheIsland(_isle_db.Isle):
    """On real rows: the beach act and the chest count only on the trip they name (command_commit, game/storage.py)."""
    def setUp(self):
        super().setUp()
        p = patch('game.island_fun.now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def test_only_on_the_trip(self):
        trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']['id']
        w = self.state(self.a)['journey']['wallet']
        out = self.command(self.a, 'jr_beach_chest', trip=trip)
        self.assertGreater(self.state(self.a)['journey']['wallet'], w)
        self.assertTrue(out['result']['beach']['chest'])
        self.command(self.a, 'jr_beach_do', trip=trip, act='boi')
        self.assertEqual(self.state(self.a)['journey']['beach']['did'], ['boi'])
        stranger = self.x[0]
        before = self.state(stranger)
        with self.assertRaises(GameError) as cm:
            self.command(stranger, 'jr_beach_chest', trip=trip)            # not aboard: nothing given
        self.assertEqual(cm.exception.code, 'no_island')
        self.assertEqual(self.state(stranger)['journey'], before['journey'])
        self.post(self.a, 'end', trip=trip)
        with self.assertRaises(GameError):
            self.command(self.a, 'jr_beach_do', trip=trip, act='bbq')     # the trip is over


@unittest.skipUnless(__import__('shutil').which('node'), 'needs node')
class Client(unittest.TestCase):
    def test_overview_and_garage_render_from_a_real_save(self):
        import json
        import subprocess
        import tempfile
        from pathlib import Path
        s = buy_cars(owner('biet_thu_vuon', 90000), 'xe_ga', 'o_to_suv', 'du_thuyen')
        s, _ = place_new(s, 'sofa', 'living')
        pub = public_state(s)
        fx = dict(plans=ho.catalogue(), state=dict(journey=pub['journey']),
                  content=dict(journey=dict(homelife=jr.content()['homelife'], garage=gr.catalogue())))
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'fx.json'
            f.write_text(json.dumps(fx, ensure_ascii=False), encoding='utf-8')
            out = subprocess.run(['node', 'tests/home_overview.mjs', str(f)], cwd=root, capture_output=True, text=True,
                                 encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


class OlderSaves(unittest.TestCase):
    def test_a_save_without_the_blocks_loads_and_shows_everything(self):
        s = buy_cars(owner('biet_thu_vuon', 90000), 'xe_ga')
        for k in ('hamxe', 'chores', 'beach'):
            self.assertNotIn(k, s['journey'])
        validate_state(migrate_state(copy.deepcopy(s)))
        h = HL(s)
        self.assertEqual(h['hamxe']['park'], ['xe_ga'])
        self.assertNotIn('beach', h)


if __name__ == '__main__':
    unittest.main()
