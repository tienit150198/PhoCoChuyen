"""🚗 Vehicles on the live maps (owner 16/10): a ride `r` {v, c, p?} on the strolls (live/street.py) and in the island
town (live/town.py). `p`, the words of an auction plate (gold), travels only when that player won it (live/plates.py:
auction_lots, cached per player); anything odd rides on without a plate, never an error. The town takes any garage
vehicle (a yacht / plane is shown parked by the client) and repeats `r` only when it changes; site rooms drop it."""
import json
import time
import unittest
from types import SimpleNamespace

from live import plates
from live.config import Config
from live.hub import Conn, Hub
from live.street import clean_ride as street_ride
from live.town import MAP_ID, TownFeature, clean_ride as town_ride
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')


def won(player, *texts):
    """As if live/plates.py had just read the plates this player won."""
    player.ext['uq_plates'] = (frozenset(texts), time.monotonic() + 60)


class Wire(unittest.TestCase):
    def test_plate_words_are_short_plain_text(self):
        self.assertEqual(street_ride({'v': 'xe_ga', 'c': 'hong', 'p': '30K-666.66'}), {'v': 'xe_ga', 'c': 'hong', 'p': '30K-666.66'})
        self.assertEqual(street_ride({'v': 'lx_xe_ga_01', 'c': 'ngoc_bich'}), {'v': 'lx_xe_ga_01', 'c': 'ngoc_bich'})
        for odd in (5, None, '', 'x' * 25, 'a\nb', ['a'], {'a': 1}):
            self.assertEqual(street_ride({'v': 'xe_ga', 'c': 'hong', 'p': odd}), {'v': 'xe_ga', 'c': 'hong'}, odd)
        self.assertIsNone(street_ride({'v': 'phan_luc', 'c': 'hong'}))     # the strolls: two-wheelers only
        self.assertEqual(town_ride({'v': 'phan_luc', 'c': 'bach_kim', 'p': 'VN-A888'}), {'v': 'phan_luc', 'c': 'bach_kim', 'p': 'VN-A888'})
        self.assertEqual(town_ride({'v': 'du_thuyen', 'c': 'Bad Paint!'}), {'v': 'du_thuyen', 'c': ''})
        for odd in ({'v': 'tau_ngam'}, {'v': 5}, {'c': 'do'}, 'xe_ga', None):
            self.assertIsNone(town_ride(odd), odd)

    def test_keep_only_won_plates_on_own_vehicles(self):
        import asyncio
        p = SimpleNamespace(ext={}, sid='s')
        won(p, 'VN-A888')
        keep = lambda r: asyncio.run(plates.keep(None, p, r))
        self.assertEqual(keep({'v': 'phan_luc', 'c': '', 'p': 'VN-A888'}), {'v': 'phan_luc', 'c': '', 'p': 'VN-A888'})
        self.assertEqual(keep({'v': 'phan_luc', 'c': '', 'p': 'VN-A168'}), {'v': 'phan_luc', 'c': ''})
        self.assertEqual(keep({'v': 'xe_ga', 'c': '', 'o': '0123456789abcdef', 'p': 'VN-A888'}), {'v': 'xe_ga', 'c': '', 'o': '0123456789abcdef'})
        self.assertIsNone(keep(None))
        q = SimpleNamespace(ext={}, sid='t')                               # no database: no plate, no error
        self.assertEqual(asyncio.run(plates.keep(None, q, {'v': 'xe_ga', 'c': '', 'p': 'X'})), {'v': 'xe_ga', 'c': ''})


class Town(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = Config(town=True) if 'town' in getattr(Config, '__dataclass_fields__', {}) else Config()
        self.hub = Hub(self.cfg)
        self.frames = {}
        self.hub.write = lambda sockets, raw, **kw: [self.frames[s].append(json.loads(raw)) for s in sockets]
        self.town = TownFeature(SimpleNamespace(cfg=self.cfg, hub=self.hub, db=None, chat=None))

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.town._empty(room)

    def player(self, pid):
        ident = SimpleNamespace(pid=pid, sid='private-' + pid, name='Tên ' + pid, av='🌸', account=False,
                                muted_until=0, old=True, since=0, online=True)
        ws = object()
        self.frames[ws] = []
        c = Conn(ws, self.hub.player(ident), 'test', self.cfg)
        c.ready = True
        self.hub.add(c)
        return c

    async def join(self, conn, **extra):
        return await self.town.town_in(conn, dict(map=MAP_ID, x=6, y=6, direction='se', look={}, **extra))

    def flush(self, conn):
        room = self.hub.rooms[conn.ext['town']]
        if room.data['h']:
            room.data['h'].cancel()
        self.town._flush(room)
        return room

    async def test_rides_and_plates_in_the_town(self):
        a, b, c = self.player('a'), self.player('b'), self.player('c')
        won(a.player, 'VN-A888')
        await self.join(a, r={'v': 'phan_luc', 'c': 'bach_kim', 'p': 'VN-A888'})
        await self.join(b, r={'v': 'xe_ga', 'c': 'hong', 'p': 'VN-A888'})            # not theirs: no plate
        snap = await self.join(c, r={'v': 'tau_ngam'})                                  # unknown: on foot
        people = {p['pid']: p for p in snap['people']}
        self.assertEqual(people['a']['r'], {'v': 'phan_luc', 'c': 'bach_kim', 'p': 'VN-A888'})
        self.assertEqual(people['b']['r'], {'v': 'xe_ga', 'c': 'hong'})
        room = self.flush(a)
        self.assertNotIn('r', room.data['people']['c'].public())
        walker = room.data['people']['b']
        walker.last -= 1
        await self.town.town_mv(b, dict(x=6, y=6.5, direction='se'))                  # no `r`: unchanged, not repeated
        await self.town.town_mv(b, dict(x=6, y=6.6, direction='se', r={'v': 'xe_ga', 'c': 'hong'}))   # the same
        self.assertEqual([e for _, e in room.data['ev'] if e['k'] == 'mv' and 'r' in e], [])
        await self.town.town_mv(b, dict(x=6, y=6.7, direction='se', r={'v': 'o_to_suv', 'c': 'bac'}))
        await self.town.town_mv(b, dict(x=6, y=6.8, direction='se', r=None))
        self.flush(b)
        moves = [e for f in self.frames[a.ws] if f['t'] == 'town' for e in f['ev'] if e['k'] == 'mv' and e['pid'] == 'b']
        self.assertIsNone(moves[-1]['r'])                                               # batched: the latest wins
        self.assertIsNone(walker.ride)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Strolls(LiveCase):
    """A plate won at the auction shows on the stroll (gold, the client's ride.js); a copied plate text never does."""
    cfg_extra = dict(street=True)

    async def stroll(self, token, **extra):
        c = await self.connect(token)
        c.room = await c.call('walk_in', 'walk_room', place='boho', look=LOOK, g='female', title=None, **extra)
        c.pid = c.welcome['me']['pid']
        return c

    async def test_won_plate_travels_copied_one_does_not(self):
        from game import auction as au
        (ta, sa), (tb, sb) = self.account('Minh Khang'), self.account('Lan Anh')
        lid = au.admin_add(self.store, 'op', dict(item='pl_30k66666', hours=1))['id']
        with self.store.connect() as db:
            db.execute("UPDATE auction_lots SET status='sold', winner_sid=? WHERE id=?", (sa, lid))
        ride = {'v': 'xe_ga', 'c': 'hong', 'p': '30K-666.66'}
        minh = await self.stroll(ta, r=ride)
        lan = await self.stroll(tb, r=ride)
        seen = {p['pid']: p for p in lan.room['people']}
        self.assertEqual(seen[minh.pid]['r'], ride)
        self.assertEqual(seen[lan.pid]['r'], {'v': 'xe_ga', 'c': 'hong'})


if __name__ == '__main__':
    unittest.main()
