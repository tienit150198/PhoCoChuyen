"""🏝️ Ra đảo cùng bạn bè (game/island_trips.py): who may start a trip and in what, invitations to mutual friends only
(blocks either way), the seats of each vehicle counted under the trip's lock (two friends racing for the last seat),
leaving and coming back, the hour, the owner ending it, a sale / an erased account ending it, and the live check."""
import concurrent.futures
import json
import threading
import uuid
from unittest.mock import patch

from game import island_content as C
from game import island_trips as it
from game import marriage as mr
from game import social
from tests.test_marriage import Base


class Trips(Base):
    def setUp(self):
        super().setUp()
        self.a = self.user('chudao', 80_000_000)
        self.f = [self.user(n, 1000) for n in ('ban1', 'ban2', 'ban3', 'ban4', 'ban5')]
        self.x = self.user('nguoila', 1000)
        self.codes = {t: self.code(t) for t in [self.a, self.x, *self.f]}
        for t in self.f:
            self.befriend(self.sid(self.a), self.sid(t))
        self.command(self.a, 'jr_island_buy', id='dao_dua', confirm=True)
        self.command(self.a, 'jr_garage_buy', id='thuyen_buom', color='trang', confirm=True)   # ⛵ 4 seats

    def command(self, token, action, **payload):
        return self.store.command(token, str(uuid.uuid4()), self.store.read(token)[1], None, action, payload)

    def post(self, token, sub, **data):
        return it.post(self.store, token, sub, data)

    def get(self, token, friends=False):
        return it.get(self.store, token, {'friends': '1'} if friends else {})

    def err(self, token, sub, code, **data):
        with self.assertRaises(it.IslandError) as cm:
            self.post(token, sub, **data)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def start(self, vehicle='thuyen_buom'):
        return self.post(self.a, 'start', island='dao_dua', vehicle=vehicle)['trip']['id']

    def invite(self, trip, *tokens):
        return self.post(self.a, 'invite', trip=trip, codes=[self.codes[t] for t in tokens])

    def seat(self, trip, token):
        with self.store.connect() as db:
            r = db.execute('SELECT status FROM island_guests WHERE trip=? AND guest=?', (trip, self.sid(token))).fetchone()
        return r['status'] if r else None

    def access(self, trip, token):
        with self.store.connect() as db:
            row = db.execute(it.ACCESS_SQL, (self.sid(token), trip)).fetchone()
        return it.access_for(row, self.sid(token), mr.now())

    # ---- starting ---------------------------------------------------------------------------------------------
    def test_start_needs_the_island_and_a_vehicle_that_carries_people(self):
        self.err(self.f[0], 'start', 'not_owned', island='dao_dua', vehicle='')
        self.err(self.a, 'start', 'not_owned', island='dao_san_ho', vehicle='')
        self.err(self.a, 'start', 'not_owned', island='dao_dua', vehicle='du_thuyen')      # not theirs
        self.err(self.a, 'start', 'island_error', island='dao_khong', vehicle='')
        out = self.post(self.a, 'start', island='dao_dua', vehicle='thuyen_buom')
        t = out['trip']
        self.assertEqual((t['seats'], t['kind'], t['aboard'], t['island']['id']), (4, 'boat', 1, 'dao_dua'))
        self.assertAlmostEqual(t['ends'] - mr.now(), C.SESSION_MIN * 60)
        self.err(self.a, 'start', 'busy', island='dao_dua', vehicle='')                    # one open trip at a time
        self.assertEqual(self.access(t['id'], self.a), 'owner')

    def test_alone_any_time_but_nobody_else(self):
        trip = self.start('')
        self.assertEqual(self.get(self.a)['trip']['seats'], 1)
        self.err(self.a, 'invite', 'solo', trip=trip, codes=[self.codes[self.f[0]]])

    # ---- invitations ------------------------------------------------------------------------------------------
    def test_only_mutual_friends_nobody_blocked(self):
        trip = self.start()
        self.err(self.a, 'invite', 'not_friends', trip=trip, codes=[self.codes[self.x]])   # a stranger
        self.store.transaction(lambda db: db.execute('DELETE FROM friends WHERE sid=? AND friend=?', (self.sid(self.f[1]), self.sid(self.a))))
        self.err(self.a, 'invite', 'not_friends', trip=trip, codes=[self.codes[self.f[1]]])   # one-way friendship
        pa, pb = social.pid_of(self.sid(self.a)), social.pid_of(self.sid(self.f[2]))
        self.store.transaction(lambda db: db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (pb, pa, mr.now())))
        self.err(self.a, 'invite', 'not_friends', trip=trip, codes=[self.codes[self.f[2]]])   # blocked (by the guest)
        self.store.transaction(lambda db: db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)',
                                                     (self.sid(self.a), self.sid(self.f[3]), mr.now())))
        self.err(self.a, 'invite', 'not_friends', trip=trip, codes=[self.codes[self.f[3]]])   # blocked (by the owner)
        out = self.invite(trip, self.f[0], self.x)
        self.assertEqual(out['done'], dict(sent=1, skipped=1))
        self.assertEqual(self.seat(trip, self.f[0]), 'invited')
        self.assertIsNone(self.seat(trip, self.x))
        self.err(self.f[0], 'invite', 'forbidden', trip=trip, codes=[self.codes[self.f[4]]])   # only the owner invites
        inv = self.get(self.f[0])['invites']
        self.assertEqual([(i['id'], i['owner']['name'], i['seats'], i['aboard']) for i in inv], [(trip, 'Chudao', 4, 1)])
        self.assertEqual(self.access(trip, self.f[0]), None)                                  # invited is not aboard
        dump = json.dumps([self.get(t, friends=True) for t in (self.a, self.f[0])])
        for t in (self.a, *self.f):
            self.assertNotIn(self.sid(t), dump)                                                # no sid ever leaves

    def test_friend_picker_lists_mutual_friends_only(self):
        names = sorted(f['name'] for f in self.get(self.a, friends=True)['friends'])
        self.assertEqual(names, ['Ban1', 'Ban2', 'Ban3', 'Ban4', 'Ban5'])

    # ---- seats ------------------------------------------------------------------------------------------------
    def test_seats_fill_and_free_again(self):
        trip = self.start()
        self.invite(trip, *self.f)
        for t in self.f[:3]:
            self.assertTrue(self.post(t, 'answer', trip=trip, answer='accept')['done']['aboard'])
        msg = self.err(self.f[3], 'answer', 'full', trip=trip, answer='accept')
        self.assertIn('4 người', msg)
        self.assertEqual(self.seat(trip, self.f[3]), 'invited')                              # still invited: may try later
        self.post(self.f[0], 'leave', trip=trip)
        self.assertEqual(self.access(trip, self.f[0]), None)
        self.assertTrue(self.post(self.f[3], 'answer', trip=trip, answer='accept')['done']['aboard'])
        self.err(self.f[0], 'answer', 'full', trip=trip, answer='accept')                   # back again: full now
        self.post(self.f[4], 'answer', trip=trip, answer='decline')
        self.assertEqual(self.seat(trip, self.f[4]), 'declined')
        self.err(self.f[4], 'answer', 'not_pending', trip=trip, answer='accept')
        mine = self.get(self.a)['trip']
        self.assertEqual(mine['aboard'], 4)
        self.assertEqual(sorted(g['status'] for g in mine['guests']), ['aboard', 'aboard', 'aboard'])
        self.post(self.a, 'remove', trip=trip, code=self.codes[self.f[1]])
        self.assertEqual(self.seat(trip, self.f[1]), 'removed')
        self.assertEqual(self.get(self.a)['trip']['aboard'], 3)

    def test_two_friends_racing_for_the_last_seat(self):
        self.command(self.a, 'jr_garage_buy', id='may_bay_nho', color='vang', confirm=True)   # 🛩️ two seats: one guest
        for round_ in range(3):
            with self.subTest(round=round_):
                trip = self.post(self.a, 'start', island='dao_dua', vehicle='may_bay_nho')['trip']['id']
                self.invite(trip, self.f[0], self.f[1])
                gate = threading.Barrier(2)
                original = it._trip_for_update

                def slow(db, trip_id):
                    if threading.current_thread().name.startswith('seat-race'):
                        gate.wait(5)
                    return original(db, trip_id)

                def take(token):
                    try:
                        self.post(token, 'answer', trip=trip, answer='accept')
                        return 'aboard'
                    except it.IslandError as e:
                        return e.code
                with patch.object(it, '_trip_for_update', slow), \
                        concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='seat-race') as pool:
                    got = sorted(pool.map(take, self.f[:2]))
                self.assertEqual(got, ['aboard', 'full'])
                with self.store.connect() as db:
                    n = db.execute("SELECT COUNT(*) AS n FROM island_guests WHERE trip=? AND status='aboard'", (trip,)).fetchone()['n']
                self.assertEqual(n, 1)
                self.post(self.a, 'end', trip=trip)

    def test_aboard_one_trip_at_a_time(self):
        trip = self.start()
        self.invite(trip, self.f[0])
        self.post(self.f[0], 'answer', trip=trip, answer='accept')
        b = self.user('chudao2', 80_000_000)
        self.befriend(self.sid(b), self.sid(self.f[0]))
        self.command(b, 'jr_island_buy', id='dao_dua', confirm=True)
        self.command(b, 'jr_garage_buy', id='thuyen_buom', color='trang', confirm=True)
        other = it.post(self.store, b, 'start', dict(island='dao_dua', vehicle='thuyen_buom'))['trip']['id']
        it.post(self.store, b, 'invite', dict(trip=other, codes=[self.codes[self.f[0]]]))
        self.post(self.f[0], 'answer', trip=other, answer='accept')
        self.assertEqual((self.seat(trip, self.f[0]), self.seat(other, self.f[0])), ('left', 'aboard'))

    # ---- the hour, the end, a sale ------------------------------------------------------------------------------
    def test_the_hour_ends_it(self):
        trip = self.start()
        self.invite(trip, self.f[0])
        self.post(self.f[0], 'answer', trip=trip, answer='accept')
        self.assertEqual(self.access(trip, self.f[0]), 'guest')
        self.clock.t += C.SESSION_MIN * 60 + 1
        self.assertIsNone(self.access(trip, self.f[0]))
        self.assertIsNone(self.access(trip, self.a))
        self.assertIsNone(self.get(self.a)['trip'])
        self.assertEqual(self.get(self.f[0])['aboard'], [])
        with self.store.connect() as db:
            r = db.execute('SELECT status, why FROM island_trips WHERE id=?', (trip,)).fetchone()
        self.assertEqual((r['status'], r['why']), ('ended', 'time'))
        self.start()                                                                          # a new hour

    def test_owner_ends_and_unfriend_takes_the_seat(self):
        trip = self.start()
        self.invite(trip, self.f[0], self.f[1])
        for t in self.f[:2]:
            self.post(t, 'answer', trip=trip, answer='accept')
        self.store.transaction(lambda db: db.execute('DELETE FROM friends WHERE sid=? AND friend=?', (self.sid(self.a), self.sid(self.f[1]))))
        self.assertIsNone(self.access(trip, self.f[1]))
        self.assertEqual(self.access(trip, self.f[0]), 'guest')
        self.err(self.f[0], 'end', 'forbidden', trip=trip)
        self.post(self.a, 'end', trip=trip)
        self.assertIsNone(self.access(trip, self.f[0]))
        self.err(self.a, 'end', 'ended', trip=trip)

    def test_selling_the_island_ends_its_trip_in_both_store_paths(self):
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                trip = self.start()
                self.command(self.a, 'jr_island_sell', id='dao_dua', confirm=True)
                with self.store.connect() as db:
                    r = db.execute('SELECT status, why FROM island_trips WHERE id=?', (trip,)).fetchone()
                self.assertEqual((r['status'], r['why']), ('ended', 'sold'))
                self.command(self.a, 'jr_island_buy', id='dao_dua', confirm=True)

    def test_erased_account_ends_its_trip_and_seats(self):
        trip = self.start()
        self.invite(trip, self.f[0])
        self.post(self.f[0], 'answer', trip=trip, answer='accept')
        self.store.transaction(lambda db: it.forget(db, self.sid(self.f[0])))
        self.assertEqual(self.seat(trip, self.f[0]), 'removed')
        self.store.transaction(lambda db: it.forget(db, self.sid(self.a)))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM island_trips WHERE id=?', (trip,)).fetchone()['status'], 'ended')

    def test_guests_need_an_account(self):
        token, _, _ = self.store.session()
        with self.assertRaises(it.IslandError) as cm:
            it.get(self.store, token, {})
        self.assertEqual(cm.exception.status, 401)
