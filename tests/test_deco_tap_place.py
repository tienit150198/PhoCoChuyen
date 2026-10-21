"""♿ Chạm chọn, chạm đặt (góp ý #443, a player who uses a screen reader): the room editor's cell buttons and one-cell
steps (public/js/v4/reno.js) send the same jr_deco_put a drag sends, at whole cells (x, y multiples of deco_content.U,
the back left corner of the piece). Every cell the client offers is taken exactly where it is when the server's own
check allows it and refused with a reason otherwise; nothing new is saved. The client: tests/deco_tap_place.mjs."""
import json
import unittest

from game import deco as dc
from game import deco_content as DC
from game import whats_new as wn
from tests.test_bank import act
from tests.test_deco import fp, owner

U = DC.U


def cells(s, k):
    """The cells reno.js cellsMarkup offers for kind `k` in the first room it suits: (room, [(x, y)])."""
    L = dc.layout(s)
    room = next(r for r in L['rooms'] if r['type'] in DC.ITEMS[k]['rooms'] and dc.zone(r, k))
    z = dc.zone(room, k)
    return room, [(x * U, y * U) for y in range(z[1] // U + 1) for x in range(z[0] // U + 1)]


class Cells(unittest.TestCase):
    def check_kind(self, k):
        s = owner(wallet=20000)
        s, r = act(s, 'jr_deco_buy', item=k, confirm=True)   # in the bag: chosen from its card, then a cell
        uid = r['uid']
        room, spots = cells(s, k)
        took = refused = 0
        for x, y in spots:
            L = dc.layout(s)
            others = {u: q for u, q in L['pos'].items() if u != uid}
            bad = dc.check(room, k, dict(r=room['id'], x=x, y=y, f=0), others, L['kinds'])
            with self.subTest(k=k, x=x, y=y):
                if bad:
                    with self.assertRaises(Exception):
                        act(s, 'jr_deco_put', uid=uid, r=room['id'], x=x, y=y, f=0)
                    refused += 1
                    continue
                s2, res = act(s, 'jr_deco_put', uid=uid, r=room['id'], x=x, y=y, f=0)
                self.assertEqual(fp(s2, uid)[:4], (room['id'], x, y, 0), 'a cell is taken exactly, never snapped elsewhere')
                self.assertTrue(res['message'])
                s = s2
                took += 1
        self.assertGreater(took, 0)
        self.assertEqual(took + refused, len(spots))
        return s, uid, room, refused

    def test_floor_cells(self):
        s, uid, room, _ = self.check_kind('ghe_dau')
        # ➡️ one step from a cell: the next cell, the same command
        q = fp(s, uid)
        z = dc.zone(room, 'ghe_dau')
        x = q[1] - U if q[1] + U > z[0] else q[1] + U
        s, _ = act(s, 'jr_deco_put', uid=uid, r=room['id'], x=x, y=q[2], f=0)
        self.assertEqual(fp(s, uid)[1], x)

    def test_wall_cells(self):
        refused = self.check_kind('tranh')[3]
        self.assertGreater(refused, 0, 'the window keeps some wall cells clear: refused, with a reason')

    def test_no_new_save_keys(self):
        s, uid, _, _ = self.check_kind('ghe_dau')
        piece = s['journey']['decor']['items'][uid]
        self.assertLessEqual(set(piece), {'r', 'x', 'y', 'f', 'on', 'z', 'face'})
        json.dumps(s)


class WhatsNew(unittest.TestCase):
    def test_the_note(self):
        e = next(e for e in wn.ENTRIES if e['version'] == '2.5.2')
        texts = [i['text'] for i in e['items']]
        self.assertTrue(any('chạm chọn' in t and 'trình đọc màn hình' in t for t in texts), texts)
        wn.validate()


if __name__ == '__main__':
    unittest.main()
