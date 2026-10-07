"""🪴 After 1.7.15 (góp ý #192 "thêm nội thất", chat 06/10): 55 more pieces for every room (small things too), three
theme sets, the 🍳 Bếp & ăn uống shelf, ↻ turning many more pieces round, rooms that hold 1.5 × as many pieces with a
message that says the real number and how to get more, and the rolling release: a 1.7.15 server must accept every save
this build writes (its room cap, its two facing pieces), show the rest of the room, and lose nothing."""
import contextlib
import copy
import json
import re
import unittest
from pathlib import Path

from game import deco as dc
from game import deco_content as DC
from game import estates_content as EC
from game import price_index as pi
from game import housing as hs
from game import reno as rn
from game.engine import GameError, migrate_state, validate_state
from tests.test_bank import act
from tests.test_deco import D, bag, owner, renter, tick
from tests.test_home_rooms import put_new

ROOT = Path(__file__).resolve().parents[1]
NEW = tuple(DC.ITEMS)[len(DC.KNOWN_1715):len(DC.KNOWN_199)]
VILLA = tuple(DC.ITEMS)[len(DC.KNOWN_199):]           # 🏰 after 1.9.9 (game/estates_content.py)
NEW_SETS = ('choi', 'bep_nha', 'sao')


@contextlib.contextmanager
def build_1715():
    """What the live 1.7.15 server checks: its room cap, its facing pieces, its catalogue. It never reads
    journey.decor_more / journey.decor_turn (extra journey keys), so the save it sees is this one without them."""
    saved = (dc.room_cap, dc.FACING_ITEMS)
    items = {k: DC.ITEMS.pop(k) for k in NEW + VILLA}
    sets = {k: DC.SETS.pop(k) for k in NEW_SETS + tuple(EC.SETS)}
    dc.room_cap, dc.FACING_ITEMS = dc.old_cap, dc.FACES_OLD
    try:
        yield
    finally:
        dc.room_cap, dc.FACING_ITEMS = saved
        DC.ITEMS.update(items)
        DC.SETS.update(sets)


def as_1715(s):
    """The save as a 1.7.15 build reads it (validate + layout), with its catalogue and rules."""
    t = copy.deepcopy(s)
    j = t['journey']
    j.pop('decor_more', None)
    j.pop('decor_turn', None)
    with build_1715():
        # a 1.7.15 validate_state: the default room_cap of 1.7.15 is what its settle_free uses
        settle, check = dc.settle_free, dc.check
        dc.settle_free = lambda rooms, kinds, pos, order, cap=dc.old_cap: settle(rooms, kinds, pos, order, cap)
        try:
            validate_state(t)
            L = dc.layout(t)
        finally:
            dc.settle_free, dc.check = settle, check
    return t, L


def full_bunk(n):
    b = renter('ky_tuc_xa', wallet=20000)
    for i in range(n):
        b, _ = act(b, 'jr_deco_buy', item='lich', confirm=True, put=dict(r='bunk', x=i * 2 % 80, y=i % 3))
    return b


class Catalogue(unittest.TestCase):
    def test_the_new_pieces(self):
        self.assertEqual(len(NEW), 55)
        self.assertEqual(DC.KNOWN_1715[-1], 'mam_ngu_qua')
        self.assertEqual(len(DC.KNOWN_1715), 116)
        self.assertIn('bep', {c[0] for c in DC.CATS})
        rows = {'loft': 1}
        for k in NEW:
            it = DC.ITEMS[k]
            with self.subTest(k=k):
                self.assertTrue(10 <= it['price'] <= pi.price(450) and 1 <= it['cozy'] <= 3)   # 💹 07/10: base 10–450
                if it['spot'] == 'wall':
                    self.assertTrue(all(it['h'] <= rows.get(t, 2) for t in it['rooms']))   # fits every wall it is sold for
                if it['spot'] == 'top':
                    self.assertEqual((it['w'], it['h']), (1, 1))
        for t in ('living', 'bed', 'kitchen', 'bath', 'balcony', 'yard'):
            self.assertGreaterEqual(sum(1 for k in NEW if t in DC.ITEMS[k]['rooms']), 4, t)   # something new for every room
        small = [k for k in NEW if DC.ITEMS[k]['spot'] == 'top']
        self.assertGreaterEqual(len(small), 15)                                           # small things too
        self.assertEqual(len({it['name'] for it in DC.ITEMS.values()}), len(DC.ITEMS))
        cheap = [k for k in NEW if DC.ITEMS[k]['price'] <= 40]
        self.assertGreaterEqual(len(cheap), 12)                                           # sensible prices: many cheap

    def test_drawn_turnable_and_named_in_english(self):
        js = (ROOT / 'public' / 'js' / 'v4' / 'deco-art.js').read_text(encoding='utf-8')
        art = js[js.index('export const ART={'):js.index('/* ---------------------------------------------------------------- the room')]
        self.assertEqual(set(re.findall(r'^\s+([a-z_0-9]+):\{h:', art, re.M)), {k for k, v in DC.ITEMS.items() if not v.get('uq')})
        uq = art[art.index('const UQ_ART={'):]                               # 🔨 the paintings won at auction: one loop draws them
        self.assertEqual({'uq_' + x for x in re.findall(r'([a-z_0-9]+):\[', uq[:uq.index('};')])}, {k for k, v in DC.ITEMS.items() if v.get('uq')})
        backs = set(re.findall(r'^\s+([a-z_0-9]+):\(', art[art.index('const BACKS={'):], re.M))
        body = {m.group(1): e for e in re.split(r'\n(?=  [a-z_0-9]+:\{h:)', art[:art.index('const BACKS={')])
                if (m := re.match(r'\s*([a-z_0-9]+):\{h:', e))}
        for k in dc.FACING_ITEMS:
            with self.subTest(k=k):
                self.assertTrue(k in backs or 'back:' in body[k], 'a piece that turns has a back to show')
        self.assertTrue(len(dc.FACING_ITEMS) >= 25)
        en = json.loads((ROOT / 'i18n' / 'overrides.json').read_text(encoding='utf-8'))['strings']
        for k in NEW:
            self.assertIn(DC.ITEMS[k]['name'], en, k)
        for sid in NEW_SETS:
            self.assertIn(DC.SETS[sid]['name'], en, sid)
        self.assertIn('Bếp & ăn uống', en)


class Turning(unittest.TestCase):
    def test_a_bed_turns_round_and_a_1715_build_still_reads_the_save(self):
        s = owner('nha_pho', wallet=20000)
        s, uid = put_new(s, 'giuong', 'bed', 0, 20)
        q = dc.layout(s)['pos'][uid]
        s, r = act(s, 'jr_deco_put', uid=uid, **q, face='back')
        self.assertIn('mặt sau', r['message'])
        self.assertEqual(s['journey']['decor_turn'], dict(v=1, items={uid: 'back'}))
        self.assertNotIn('decor_faces', s['journey'])                # 1.7.15 checks that one against tv and sofa only
        self.assertEqual(next(i for i in D(s)['items'] if i['id'] == uid)['face'], 'back')
        s = migrate_state(json.loads(json.dumps(s)))
        validate_state(s)
        self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
        _old, L = as_1715(s)                                          # the old server shows the bed, facing front
        self.assertIn(uid, L['pos'])
        self.assertNotIn('face', L['pos'][uid])
        s, _ = act(s, 'jr_deco_pick', uid=uid)                        # facing travels with the piece in the bag
        self.assertEqual(D(s)['bag'][0]['face'], 'back')
        s, _ = act(s, 'jr_deco_sell', uid=uid, confirm=True, n='sell-bed')
        self.assertNotIn('decor_turn', s['journey'])
        validate_state(s)

    def test_tv_and_sofa_keep_their_old_block_and_others_are_strict(self):
        s = owner('nha_pho', wallet=20000)
        s, tv = put_new(s, 'tv', 'living', 0, 40)
        s, desk = put_new(s, 'ban_hoc', 'bed', 0, 20)
        for uid in (tv, desk):
            s, _ = act(s, 'jr_deco_put', uid=uid, **dc.layout(s)['pos'][uid], face='back')
        self.assertEqual(s['journey']['decor_faces']['items'], {tv: 'back'})
        self.assertEqual(s['journey']['decor_turn']['items'], {desk: 'back'})
        validate_state(s)
        for bad in (dict(v=1, items={tv: 'back'}), dict(v=1, items={desk: 'side'}), dict(v=2, items={desk: 'back'}), dict(v=1, items={})):
            t = copy.deepcopy(s)
            t['journey']['decor_turn'] = bad
            with self.assertRaises(GameError):
                validate_state(t)
        s, lamp = put_new(s, 'lich', 'living', 0, 0)
        with self.assertRaises(GameError):                            # a calendar has no back to show
            act(s, 'jr_deco_put', uid=lamp, **dc.layout(s)['pos'][lamp], face='back')


class RoomCap(unittest.TestCase):
    def test_half_again_as_many_and_the_message_says_how_many(self):
        b = renter('ky_tuc_xa', wallet=20000)
        rm = next(r for r in dc.layout(b)['rooms'] if r['id'] == 'bunk')
        old, cap = dc.old_cap(rm), dc.room_cap(rm)
        self.assertEqual(cap, old * 3 // 2)
        self.assertEqual(D(b)['rooms'][0]['cap'], cap)
        b = full_bunk(cap)
        with self.assertRaises(GameError) as e:
            act(b, 'jr_deco_buy', item='lich', confirm=True, put=dict(r='bunk', x=79, y=5))
        msg = str(e.exception)
        self.assertIn(f'{cap} món', msg)
        self.assertIn('cất bớt', msg)
        self.assertIn('nhà rộng hơn', msg)

    def test_a_1715_server_accepts_the_save_and_shows_the_rest_in_its_bag(self):
        b = full_bunk(30)
        rm = next(r for r in dc.layout(b)['rooms'] if r['id'] == 'bunk')
        old = dc.old_cap(rm)
        j = b['journey']
        self.assertEqual(len(j['decor']['items']), old)
        self.assertEqual(len(j['decor_more']['items']), 30 - old)
        self.assertEqual(len(dc.layout(b)['pos']), 30)
        old_save, L = as_1715(b)                                      # accepted, the first `old` stand, the rest wait
        self.assertEqual(len(L['pos']), old)
        self.assertEqual(len(rn.get(old_save)['items']), 30)        # nothing lost
        # the old server puts one away and sets out one that waited in its bag
        out = next(iter(j['decor']['items']))
        back = next(iter(j['decor_more']['items']))
        t = copy.deepcopy(b)
        t['journey']['decor']['items'][back] = t['journey']['decor']['items'].pop(out)
        t = migrate_state(t)
        validate_state(t)
        self.assertNotIn(back, t['journey']['decor_more']['items'])   # placed by the older build since: its spot wins
        pos = dc.layout(t)['pos']
        self.assertIn(back, pos)
        self.assertEqual(len(pos), 29)                                 # `out` stands nowhere twice; it is in the bag
        self.assertIn('lich', bag(t))

    def test_overflow_is_strict_and_follows_the_player(self):
        b = full_bunk(28)
        validate_state(b)
        for bad in (dict(v=2), dict(at=''), dict(items={}), dict(items={'zz': dict(r='bunk', x=0, y=0, f=0)})):
            t = copy.deepcopy(b)
            t['journey']['decor_more'].update(bad)
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(b)                                          # the same piece in both blocks
        uid = next(iter(t['journey']['decor']['items']))
        t['journey']['decor_more']['items'][uid] = t['journey']['decor']['items'][uid]
        with self.assertRaises(GameError):
            validate_state(t)
        t, _ = act(b, 'jr_deco_pick', uid='all')                      # Cất hết: every piece, the overflow too
        self.assertNotIn('decor_more', t['journey'])
        self.assertEqual(len(bag(t)), 28)
        t, _ = act(b, 'jr_home_leave', confirm=True)                  # moving out: everything into the bag
        tick(t)
        self.assertNotIn('decor_more', t['journey'])
        self.assertEqual(len(bag(t)), 28)
        self.assertEqual(hs.where(t['journey']['home'])[0], 'attic')

    def test_small_things_on_a_surface_never_stay_behind_their_table(self):
        s = owner('tap_the', wallet=50000)
        rm = next(r for r in dc.layout(s)['rooms'] if r['id'] == 'living')
        s, table = put_new(s, 'ban_tra', 'living', 0, 40)
        n = 1
        while n < dc.old_cap(rm) - 1:                                 # fill the wall up to just below the old cap
            s, _ = put_new(s, 'lich', 'living', 50 + n % 41, 0)   # between the window and the door
            n += 1
        for i in range(4):                                            # four small things on the table: past the old cap
            s, _ = put_new(s, 'rubik' if i % 2 else 'xep_hinh', 'living', 0, 0, on=table)
        j = s['journey']
        riders = {u for u, v in dc.layout(s)['pos'].items() if v.get('on') == table}
        self.assertTrue(riders & set(j['decor_more']['items']))
        self.assertIn(table, j['decor']['items'])
        _old, L = as_1715(s)
        self.assertIn(table, L['pos'])


class Sets(unittest.TestCase):
    def test_play_corner_kitchen_and_starry_night(self):
        s = owner('biet_thu_vuon', wallet=90000)
        s, _ = put_new(s, 'leu_choi', 'living', 0, 40)
        s, _ = put_new(s, 'ngua_go', 'living', 80, 40)
        s, r = act(s, 'jr_deco_buy', item='tho_bong', confirm=True, put=dict(r='living', x=120, y=40))
        self.assertIn('Góc vui chơi', r['message'])
        s, _ = put_new(s, 'bep_ga', 'kitchen', 0, 0, on='#counter')
        s, _ = put_new(s, 'thot_dao', 'kitchen', 20, 0, on='#counter')
        s, r = act(s, 'jr_deco_buy', item='hu_dua', confirm=True, put=dict(r='kitchen', x=40, y=0, on='#counter'))
        self.assertIn('Bếp nhà nấu', r['message'])
        s, bed = put_new(s, 'giuong_don', 'bed', 0, 20)
        s, _ = put_new(s, 'den_trang', 'bed', 0, 0, on=bed)
        s, r = act(s, 'jr_deco_buy', item='may_chieu', confirm=True, put=dict(r='bed', x=20, y=0, on=bed))
        self.assertIn('Đêm đầy sao', r['message'])
        done = {x['id'] for x in D(s)['sets'] if x['done']}
        self.assertTrue({'choi', 'bep_nha', 'sao'} <= done)
        validate_state(s)
        _old, L = as_1715(s)                                          # the old server: the new pieces wait in its bag
        self.assertFalse(any(L['kinds'][u] in NEW for u in L['pos']))


if __name__ == '__main__':
    unittest.main()
