"""🏗️ Xây trên đảo and 🌍 đảo mở cửa on real PostgreSQL rows: island_builds follows the save in its own transaction (build,
upgrade, phá dỡ, sale, import, reset, erase), visitors see the buildings, a leisure building's tinh thần is checked on
the island (command_commit refuses otherwise), the owner opens the island to everyone (the list, blocks either way,
story mode, the trại tạm giữ, the cap under the trip's lock, one visit at a time, closing sends visitors home), and
the weekly 🏝️ Đảo đẹp board with its titles (a title only)."""
import json
import uuid
from unittest.mock import patch

from game import island_build as ib
from game import island_content as IC
from game import island_lb as ilb
from game import island_trips as it
from game import lb_titles as lbt
from game import leaderboard as lb
from game import marriage as mr
from game import social
from game.engine import GameError
from tests import test_lb_titles as T
from tests.test_lb_titles import SUN, with_titles
from tests.test_marriage import Base

H = 3600


class Isle(Base):
    def setUp(self):
        super().setUp()
        p = patch('game.island_build.now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        ilb.clear_cache()
        self.addCleanup(ilb.clear_cache)
        self.a = self.user('chudao', 150_000_000)
        self.f = [self.user(n, 1000) for n in ('ban1', 'ban2')]
        self.x = [self.user(n, 1000) for n in ('khach1', 'khach2', 'khach3')]
        self.codes = {t: self.code(t) for t in [self.a, *self.f, *self.x]}
        for t in self.f:
            self.befriend(self.sid(self.a), self.sid(t))
        self.command(self.a, 'jr_island_buy', id='dao_dua', confirm=True)

    def command(self, token, action, **payload):
        return self.store.command(token, str(uuid.uuid4()), self.store.read(token)[1], None, action, payload)

    def post(self, token, sub, **data):
        return it.post(self.store, token, sub, data)

    def err(self, token, sub, code, **data):
        with self.assertRaises(it.IslandError) as cm:
            self.post(token, sub, **data)
        self.assertEqual(cm.exception.code, code, cm.exception.message)

    def rows(self, sid=None):
        with self.store.connect() as db:
            return {(r['island'], r['plot']): (r['kind'], r['lvl'], r['next_lvl'], r['status'])
                    for r in db.execute('SELECT * FROM island_builds WHERE owner=?', (sid or self.sid(self.a),)).fetchall()}

    def build(self, plot, kind, token=None, iid='dao_dua'):
        return self.command(token or self.a, 'jr_isle_build', island=iid, plot=plot, kind=kind, confirm=True)


class Mirror(Isle):
    def test_rows_follow_the_save(self):
        self.build(0, 'nha_san')
        self.build(5, 'ben_thuyen')
        self.assertEqual(self.rows(), {('dao_dua', 0): ('nha_san', 0, 1, 'up'), ('dao_dua', 5): ('ben_thuyen', 0, 1, 'up')})
        self.clock.t += 12 * H
        self.command(self.a, 'jr_isle_up', island='dao_dua', plot=0, confirm=True)
        self.assertEqual(self.rows()[('dao_dua', 0)], ('nha_san', 1, 2, 'up'))
        self.command(self.a, 'jr_isle_raze', island='dao_dua', plot=5, confirm=True)
        self.assertEqual(self.rows()[('dao_dua', 5)][3], 'gone')                       # kept, marked gone
        self.build(5, 'cam_trai')
        self.assertEqual(self.rows()[('dao_dua', 5)], ('cam_trai', 0, 1, 'up'))
        self.command(self.a, 'jr_island_sell', id='dao_dua', confirm=True)
        self.assertEqual({v[3] for v in self.rows().values()}, {'gone'})
        self.command(self.a, 'jr_island_buy', id='dao_dua', confirm=True)
        self.assertEqual({v[3] for v in self.rows().values()}, {'gone'})              # bought again: empty plots

    def test_a_refused_build_writes_nothing(self):
        self.fund(self.a, 1000)
        with self.assertRaises(GameError):
            self.build(0, 'nha_san')
        self.assertEqual(self.rows(), {})

    def test_reset_and_erase(self):
        self.build(1, 'ho_boi')
        self.command(self.a, 'reset_all', confirm='BAT DAU LAI')
        self.assertEqual(self.rows()[('dao_dua', 1)][3], 'gone')
        b = self.user('chudao2', 80_000_000)
        self.command(b, 'jr_island_buy', id='dao_dua', confirm=True)
        self.build(0, 'nha_san', b)
        sid = self.sid(b)
        self.store.delete(b)
        self.assertEqual(self.rows(sid), {})

    def test_visitors_see_the_buildings_without_any_sid(self):
        self.build(0, 'nha_san')
        self.clock.t += 6 * H
        self.build(1, 'ho_boi')
        trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']
        self.assertEqual([(b['p'], b['k'], b['l'], b['b']) for b in trip['builds']], [(0, 'nha_san', 1, 0), (1, 'ho_boi', 0, 1)])
        self.assertEqual(trip['score'], ib.BUILD['nha_san']['pts'] + 10)                # the pool is scaffolding: nothing yet
        self.post(self.a, 'public', trip=trip['id'], open=True)
        seen = self.post(self.x[0], 'visit', trip=trip['id'])
        self.assertTrue(seen['done']['visit'])
        v = seen['visiting'][0]
        self.assertEqual(len(v['builds']), 2)
        self.assertNotIn(self.sid(self.a), json.dumps(seen))


class UseOnTheIsland(Isle):
    def use(self, token, trip, plot):
        return self.command(token, 'jr_isle_use', trip=trip, plot=plot)

    def test_checked_on_the_island(self):
        self.build(0, 'ho_boi')
        self.build(1, 'nha_san')
        trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']['id']
        with self.assertRaises(GameError) as cm:
            self.use(self.a, trip, 0)                                                    # scaffolding
        self.assertEqual(cm.exception.code, 'not_here')
        self.clock.t += 8 * H
        before = self.state(self.a)['journey']['life']['spirit']
        self.use(self.a, trip, 0)
        self.assertEqual(self.state(self.a)['journey']['life']['spirit'], min(100, before + 1))
        with self.assertRaises(GameError):
            self.use(self.a, trip, 1)                                                    # a home: go inside, no tinh thần
        with self.assertRaises(GameError) as cm:
            self.use(self.x[0], trip, 0)                                                 # not on this island
        self.assertEqual(cm.exception.code, 'no_island')
        self.assertEqual(self.state(self.x[0])['journey'].get('islb'), None)            # refused: nothing kept
        self.post(self.a, 'public', trip=trip, open=True)
        self.post(self.x[0], 'visit', trip=trip)
        w = self.wallet(self.x[0])
        self.use(self.x[0], trip, 0)                                                     # a visitor may
        self.assertEqual(self.wallet(self.x[0]), w)


class OpenToEveryone(Isle):
    def setUp(self):
        super().setUp()
        self.trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']['id']

    def access(self, token):
        with self.store.connect() as db:
            row = db.execute(it.ACCESS_SQL, (self.sid(token), self.trip)).fetchone()
        return it.access_for(row, self.sid(token), mr.now()), it.cap_for(row)

    def listed(self, token):
        return [t['id'] for t in it.get(self.store, token, {'public': '1'})['open']]

    def test_open_visit_leave_close(self):
        self.err(self.x[0], 'visit', 'closed', trip=self.trip)
        self.err(self.f[0], 'public', 'forbidden', trip=self.trip, open=True)
        self.assertEqual(self.listed(self.x[0]), [])
        self.post(self.a, 'public', trip=self.trip, open=True)
        self.assertEqual(self.listed(self.x[0]), [self.trip])
        self.assertEqual(self.listed(self.a), [])                                        # not one's own
        self.assertEqual(self.access(self.x[0]), (None, IC.PUBLIC_CAP))
        self.post(self.x[0], 'visit', trip=self.trip)
        self.assertEqual(self.access(self.x[0]), ('visitor', IC.PUBLIC_CAP))
        mine = it.get(self.store, self.a)['trip']
        self.assertEqual((mine['public'], mine['visitors'], [p['name'] for p in mine['visitor_list']]), (True, 1, ['Khach1']))
        self.post(self.x[0], 'leave', trip=self.trip)
        self.assertEqual(self.access(self.x[0])[0], None)
        self.post(self.x[0], 'visit', trip=self.trip)
        self.post(self.x[1], 'visit', trip=self.trip)
        self.post(self.a, 'remove', trip=self.trip, code=self.codes[self.x[1]])
        self.assertIsNone(self.access(self.x[1])[0])
        self.post(self.a, 'public', trip=self.trip, open=False)                         # closing: visitors go home
        self.assertEqual(self.access(self.x[0]), (None, 1))
        self.err(self.x[0], 'visit', 'closed', trip=self.trip)
        self.assertEqual(self.listed(self.x[0]), [])

    def test_blocks_either_way_story_and_jail(self):
        self.post(self.a, 'public', trip=self.trip, open=True)
        pa, p0 = social.pid_of(self.sid(self.a)), social.pid_of(self.sid(self.x[0]))
        self.store.transaction(lambda db: db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (p0, pa, mr.now())))
        self.assertEqual(self.listed(self.x[0]), [])
        self.err(self.x[0], 'visit', 'blocked', trip=self.trip)
        self.store.transaction(lambda db: db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)',
                                                     (self.sid(self.a), self.sid(self.x[1]), mr.now())))
        self.assertEqual(self.listed(self.x[1]), [])
        self.err(self.x[1], 'visit', 'blocked', trip=self.trip)
        self.assertEqual(self.listed(self.x[2]), [self.trip])
        mr._mutate(self.store, {self.sid(self.x[2]): lambda s: s['journey'].__setitem__('story', False)})
        self.err(self.x[2], 'visit', 'locked', trip=self.trip)
        mr._mutate(self.store, {self.sid(self.x[2]): lambda s: s['journey'].__setitem__('story', True)})
        with patch('game.jail.jailed', lambda s, t=None: True):
            self.err(self.x[2], 'visit', 'jailed', trip=self.trip)
        self.post(self.x[2], 'visit', trip=self.trip)

    def test_cap_counts_owner_friends_and_visitors(self):
        self.command(self.a, 'jr_garage_buy', id='thuyen_buom', color='trang', confirm=True)
        self.post(self.a, 'end', trip=self.trip)
        self.trip = self.post(self.a, 'start', island='dao_dua', vehicle='thuyen_buom')['trip']['id']
        self.post(self.a, 'invite', trip=self.trip, codes=[self.codes[self.f[0]]])
        self.post(self.f[0], 'answer', trip=self.trip, answer='accept')
        self.post(self.a, 'public', trip=self.trip, open=True)
        with patch.object(IC, 'PUBLIC_CAP', 4):
            self.post(self.x[0], 'visit', trip=self.trip)
            self.post(self.x[1], 'visit', trip=self.trip)                                # owner + friend + 2 = 4
            self.err(self.x[2], 'visit', 'full', trip=self.trip)
            self.post(self.x[1], 'visit', trip=self.trip)                                # already in: fine
            self.post(self.x[0], 'leave', trip=self.trip)
            self.post(self.x[2], 'visit', trip=self.trip)
        self.assertEqual(self.access(self.f[0])[0], 'guest')                             # friends aboard keep their seats

    def test_one_visit_at_a_time_and_the_trip_ending(self):
        b = self.user('chudao2', 80_000_000)
        self.command(b, 'jr_island_buy', id='dao_dua', confirm=True)
        other = it.post(self.store, b, 'start', dict(island='dao_dua', vehicle=''))['trip']['id']
        it.post(self.store, b, 'public', dict(trip=other, open=True))
        self.post(self.a, 'public', trip=self.trip, open=True)
        self.post(self.x[0], 'visit', trip=self.trip)
        self.post(self.x[0], 'visit', trip=other)
        self.assertIsNone(self.access(self.x[0])[0])
        self.assertEqual([t['id'] for t in it.get(self.store, self.x[0])['visiting']], [other])
        it.post(self.store, b, 'end', dict(trip=other))
        self.assertEqual(it.get(self.store, self.x[0])['visiting'], [])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM island_public WHERE trip=?', (other,)).fetchone()['status'], 'closed')

    def test_a_trip_has_no_time_limit(self):
        self.post(self.a, 'public', trip=self.trip, open=True)
        self.post(self.x[0], 'visit', trip=self.trip)
        self.clock.t += 40 * 86400
        self.store.transaction(lambda db: it.sweep(db))
        self.assertEqual(self.access(self.x[0])[0], 'visitor')
        self.assertEqual(self.access(self.a)[0], 'owner')
        self.assertTrue(it.get(self.store, self.a)['trip']['unlimited'])


class OlderBuildReadsTheTrip(Isle):
    def test_far_future_ends_keeps_the_trip_open_for_2_4_60(self):
        """2.4.60 (and older) decide with `ends > now` and sweep `ends <= now`: a trip of this build stays open for them."""
        trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']['id']
        self.clock.t += 3 * 86400
        old_access = ("SELECT t.id, t.owner, t.status, t.ends, g.status AS seat FROM (SELECT ?::text AS sid) v "
                      'JOIN island_trips t ON t.id=? LEFT JOIN island_guests g ON g.trip=t.id AND g.guest=v.sid')
        with self.store.connect() as db:
            row = db.execute(old_access, (self.sid(self.a), trip)).fetchone()
            self.assertTrue(row['status'] == 'open' and float(row['ends']) > mr.now() + 365 * 86400)
            n = db.execute("SELECT COUNT(*) AS n FROM island_trips WHERE status='open' AND ends<=?", (mr.now(),)).fetchone()['n']
        self.assertEqual(n, 0)


class IslandBoard(T.Weekly):
    def setUp(self):
        super().setUp()
        ilb.clear_cache()
        self.addCleanup(ilb.clear_cache)

    def islander(self, name, plots, iid='dao_dua', account=True):
        s = with_titles(1)
        s['journey']['island'] = dict(v=1, own={iid: dict(d=1, p=30_000_000)}, upk=None, stats={})
        s['journey']['islb'] = dict(v=1, p={iid: {str(i): dict(k=k, l=lv, b=0, t=0, x=1_000_000) for i, (k, lv) in enumerate(plots)}},
                                    n={}, u=None)
        return self.player(s, account=name if account else None)

    def test_query_titles_order_and_privacy(self):
        self.assertEqual(lb.parse_query({'board': 'island'}), ('island', 50))
        self.assertEqual(lbt.title_of('island', 1)['text'], '🏝️ Đảo đẹp nhất phố')
        self.assertIn('island', lbt.MAIN)
        a = self.islander('An', [('nha_san', 1), ('ho_boi', 2)])                       # 10 + 28 + 20
        b = self.islander('Bình', [('cong_vien', 3)])                                  # 24 + 10
        g = self.islander(None, [('cong_vien', 3)] * 3, account=False)                 # a guest who never opted in
        v = lb.view(self.store, 'island', 50, b)
        self.assertEqual([(r['name'], r['score'], r['rank'], r['me']) for r in v['rows']], [('An', 58, 1, False), ('Bình', 34, 2, True)])
        self.assertEqual(v['rows'][0]['island']['name'], 'Đảo Dừa')
        self.assertEqual((v['me']['rank'], v['me']['score']), (2, 34))
        self.assertNotIn('sid', json.dumps(v['rows']))
        wallet = self.store.read(a)[0]['journey']['wallet']
        self.assertTrue(lbt.refresh(self.store, SUN))
        self.assertIn(('island', 1), self.holders()['An'])
        self.assertIn(('island', 2), self.holders()['Bình'])
        self.assertNotIn(self.sid(g), lbt.holders(self.store))
        ilb.clear_cache()
        v = lb.view(self.store, 'island', 50, a)
        self.assertEqual(v['rows'][0]['title'], dict(emoji='🏝️', name='Đảo đẹp nhất phố'))
        self.assertEqual(self.store.read(a)[0]['journey']['wallet'], wallet)   # a title, no xu


for _name in dir(T.Weekly):   # Weekly's own tests run in their own module
    if _name.startswith('test'):
        setattr(IslandBoard, _name, None)
