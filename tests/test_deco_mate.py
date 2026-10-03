"""💞 The shared home's furniture (game/deco_mate.py, GET /api/deco/mate): a married couple living in one home each
see the other's pieces too, read-only; nothing when they live apart, are not married or are divorced; reading never
writes either save, and both saves keep their shape."""
import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch

from game import deco_mate as dm
from game import housing as hs
from game import marriage as mr
from game.engine import migrate_state, public_state, validate_state
from tests.test_couple import CoupleBase
from tests.test_deco import into_bag, place_new
from tests.test_housing import buy
from tests.test_bank import act


def _swap(s, new):
    s.clear()
    s.update(new)


class SharedDecor(CoupleBase):
    def setUp(self):
        super().setUp()
        self.pieces = {}

        def own(s):        # An buys a home and sets up the living room: a sofa, a tea table and a lamp on it
            j = s['journey']
            j['wallet'] = 20000
            j['stats']['max_wallet'] = max(j['stats']['max_wallet'], 20000)
            s2, _ = buy(s, 'tap_the')
            s2, r = place_new(s2, 'sofa', 'living', 0, 1)
            self.pieces['sofa'] = r['uid']
            s2, table = into_bag(s2, 'ban_tra')
            s2, _ = act(s2, 'jr_deco_put', uid=table, r='living', x=40, y=20)
            s2, r = act(s2, 'jr_deco_buy', item='den_ban', confirm=True, put=dict(r='living', x=0, y=0, on=table))
            self.pieces['table'], self.pieces['lamp'] = table, r['uid']
            _swap(s, s2)
        mr._mutate(self.store, {self.sid(self.a): own})
        self.hid = self.state(self.a)['journey']['home']['own']['id']

    def move_in(self, tok=None, hid=None, kind='tap_the'):
        """Bình moves into An's home (the 'home' effect couple.py delivers) and places a plant there."""
        def fn(s):
            j = s['journey']
            j['wallet'] = 5000
            j['stats']['max_wallet'] = max(j['stats']['max_wallet'], 5000)
            hs.apply_effect(s, dict(set='in', couple=self.cid, id=hid or self.hid, kind=kind, name='An'))
            s2, r = place_new(s, 'cay_canh', 'living', 5, 0)
            self.pieces['plant'] = r['uid']
            _swap(s, s2)
        mr._mutate(self.store, {self.sid(tok or self.b): fn})

    def mate(self, tok):
        return dm.view(self.store, tok, self.state(tok))

    def revs(self):
        return [self.store.read(t)[1] for t in (self.a, self.b)]

    def test_owner_sees_the_spouses_pieces_and_the_spouse_sees_the_owners(self):
        self.move_in()
        before = self.revs()
        va = self.mate(self.a)
        self.assertEqual(va['name'], 'Binh')
        self.assertEqual(va['at'], public_state(self.state(self.a))['journey']['deco']['place']['key'])
        self.assertEqual([(p['id'], p['k'], p['r']) for p in va['items']], [('p:' + self.pieces['plant'], 'cay_canh', 'living')])
        vb = self.mate(self.b)
        self.assertEqual(vb['name'], 'An')
        self.assertTrue(vb['at'].startswith(f'shared:{self.cid}:{self.hid}:'))
        got = {p['id']: p for p in vb['items']}
        self.assertEqual(set(got), {'p:' + self.pieces[k] for k in ('sofa', 'table', 'lamp')})
        lamp = got['p:' + self.pieces['lamp']]
        self.assertEqual(lamp['on'], 'p:' + self.pieces['table'])           # stands on An's table, prefixed the same way
        self.assertEqual(set(lamp), {'id', 'k', 'r', 'fx', 'fy', 'f', 'on', 'z'})
        # read-only: neither save moved, each still shows only its own pieces as its own
        self.assertEqual(self.revs(), before)
        own_b = {i['id'] for i in public_state(self.state(self.b))['journey']['deco']['items']}
        self.assertEqual(own_b, {self.pieces['plant']})
        for tok in (self.a, self.b):
            s = self.state(tok)
            validate_state(s)
            validate_state(migrate_state(s))
            self.assertNotIn('mate', s['journey'].get('decor') or {})

    def test_spouse_colours_travel_with_their_pieces(self):
        self.move_in()

        def tint(s):
            pal = s.setdefault('colors', dict(v=1, have=[], wear={}, deco={}))
            from game import wardrobe as wd
            cid = next(c for c in wd.COLOR_INDEX if c != wd.GOC)
            pal['have'].append(cid)
            pal['deco'][self.pieces['sofa']] = cid
            self.cid_color = cid
        mr._mutate(self.store, {self.sid(self.a): tint})
        sofa = next(p for p in self.mate(self.b)['items'] if p['id'] == 'p:' + self.pieces['sofa'])
        self.assertEqual(sofa['c'], self.cid_color)

    def test_nothing_when_living_apart(self):
        # Bình rents a room of their own: not the same home
        def rent(s):
            s['journey']['wallet'] = 5000
            s2, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
            s2, _ = place_new(s2, 'cay_canh', 'tro')
            _swap(s, s2)
        mr._mutate(self.store, {self.sid(self.b): rent})
        self.assertEqual(self.mate(self.a), {})
        self.assertEqual(self.mate(self.b), {})

    def test_nothing_for_another_home_of_the_spouse(self):
        self.move_in(hid='h99')                                               # a home An has sold since (stale id)
        self.assertEqual(self.mate(self.a), {})
        self.assertEqual(self.mate(self.b), {})

    def test_nothing_after_a_divorce(self):
        self.move_in()
        self.assertTrue(self.mate(self.a))
        self.act(self.a, 'divorce', confirm='LY HON')
        before = self.revs()
        self.assertEqual(self.mate(self.a), {})
        self.assertEqual(self.mate(self.b), {})
        self.assertEqual(self.revs(), before)

    def test_nothing_when_not_married(self):
        c = self.user('cuc')
        self.assertEqual(self.mate(c), {})
        self.assertEqual(dm.view(self.store, None, None), {})

    def test_a_broken_spouse_save_returns_nothing(self):
        self.move_in()
        with patch.object(mr, '_read_state', side_effect=ValueError('boom')):
            self.assertEqual(self.mate(self.a), {})

    def test_http_route(self):
        from server import GameServer
        self.move_in()
        with patch.dict(os.environ, {'QUIET': '1'}):
            server = GameServer(('127.0.0.1', 0), self.store)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            def get(tok):
                con = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                h = {'Host': f'127.0.0.1:{server.server_port}'}
                if tok:
                    h['Cookie'] = f'mnl_session={tok}'
                con.request('GET', '/api/deco/mate', headers=h)
                res = con.getresponse()
                data = json.loads(res.read() or b'{}')
                con.close()
                return res.status, data
            before = self.revs()
            status, d = get(self.b)
            self.assertEqual(status, 200)
            self.assertEqual(len(d['items']), 3)
            self.assertEqual(get(self.a)[1]['name'], 'Binh')
            self.assertEqual(self.revs(), before)
            self.assertNotEqual(get(None)[0], 200)
        finally:
            server.shutdown()
            server.server_close()
            t.join()


if __name__ == '__main__':
    unittest.main()
