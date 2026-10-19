"""🏝️ The island room of the live service (live/island.py) on real PostgreSQL rows (game/island_trips.py): who gets
in, walking and talking together, the invitation card, leaving, the owner ending the trip, the hour, blocks."""
import json
import time

from game import island_trips as it
from game import marriage
from tests.live_support import LiveCase

LOOK = dict(hair='toc_ngan', top='ao_thun')


class Island(LiveCase):
    cfg_extra = dict(home=True)

    def setup_trip(self, vehicle='thuyen_buom', guests=2):
        self.owner, self.osid = self.account('Chu Dao')
        self.people = [self.account(n) for n in ('Ban Mot', 'Ban Hai', 'Ban Ba')]
        self.stranger, self.xsid = self.account('Nguoi La')
        save = {'journey': {'story': True, 'life_day': 3,
                            'island': {'v': 1, 'own': {'dao_dua': {'d': 1, 'p': 15_000_000}}, 'upk': None, 'stats': {}},
                            'garage': {'cars': {vehicle: {'c': 'trang', 'n': '', 'd': 1, 'p': 15000}}}}}
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(save), self.osid))
        for _, sid in [(self.owner, self.osid), (self.stranger, self.xsid), *self.people]:
            marriage.ensure_person(self.store, sid)
        for _, sid in self.people:
            self.befriend(self.osid, sid)
        with self.store.connect() as db:
            self.codes = {r['sid']: r['code'] for r in db.execute('SELECT sid, code FROM marriage_people').fetchall()}
        self.trip = it.post(self.store, self.owner, 'start', dict(island='dao_dua', vehicle=vehicle))['trip']['id']
        if guests:
            it.post(self.store, self.owner, 'invite', dict(trip=self.trip, codes=[self.codes[s] for _, s in self.people[:guests]]))

    def accept(self, i):
        it.post(self.store, self.people[i][0], 'answer', dict(trip=self.trip, answer='accept'))

    async def enter(self, token, x=.5, y=.8):
        c = await self.connect(token)
        await c.send(t='isl_in', trip=self.trip, look=LOOK, g='female', x=x, y=y)
        c.room = await c.expect('isl_room')
        c.pid = c.welcome['me']['pid']
        return c

    async def ev(self, c, kind, timeout=3.0):
        f = await c.expect('isl', timeout=timeout)
        self.assertEqual(f['ev'][0]['k'], kind, f)
        return f['ev'][0]

    def sql(self, q, args=()):
        with self.store.connect() as db:
            return db.execute(q, args)

    async def test_owner_and_guest_walk_talk_and_wave_together(self):
        self.setup_trip()
        self.accept(0)
        owner = await self.enter(self.owner)
        self.assertEqual((owner.room['island'], owner.room['kind'], owner.room['seats'], owner.room['people']), ('dao_dua', 'boat', 4, []))
        self.assertEqual(owner.room['owner'], owner.pid)
        guest = await self.enter(self.people[0][0], .3, .9)
        self.assertEqual([p['pid'] for p in guest.room['people']], [owner.pid])
        self.assertTrue(guest.room['people'][0]['o'])
        came = await self.ev(owner, 'in')
        self.assertEqual((came['pid'], came['name'], came['x'], came['y'], came['o']), (guest.pid, 'Ban Mot', .3, .9, False))
        await guest.send(t='isl_mv', p=[[.3, .9], [.6, .5]], ms=900)
        mv = await self.ev(owner, 'mv')
        self.assertEqual((mv['pid'], mv['p'], mv['ms']), (guest.pid, [[.3, .9], [.6, .5]], 900))
        await owner.send(t='isl_emote', e='wave')
        self.assertEqual((await self.ev(guest, 'emote'))['e'], 'wave')
        self.assertEqual((await self.ev(owner, 'emote'))['e'], 'wave')
        await guest.send(t='isl_do', s='vong')
        self.assertEqual((await self.ev(owner, 'do'))['s'], 'vong')
        await owner.send(t='isl_say', text='Chào mừng ra đảo!')
        said = await self.ev(guest, 'said')
        self.assertEqual((said['pid'], said['text']), (owner.pid, 'Chào mừng ra đảo!'))
        self.assertEqual((await self.ev(owner, 'said'))['text'], 'Chào mừng ra đảo!')   # the speaker sees the bubble too
        await owner.send(t='isl_emote', e='nope')
        self.assertEqual((await owner.expect('error'))['code'], 'bad')
        await guest.send(t='isl_out')
        await guest.expect('isl_left', why='out')
        self.assertEqual((await self.ev(owner, 'out'))['pid'], guest.pid)
        for sid in (self.osid, self.people[0][1]):
            self.assertNotIn(sid, json.dumps(owner.frames + guest.frames + [owner.room, guest.room]))

    async def test_only_the_owner_and_the_friends_aboard_get_in(self):
        self.setup_trip()
        for token in (self.people[0][0], self.people[2][0], self.stranger):   # invited only, not invited, a stranger
            c = await self.connect(token)
            await c.send(t='isl_in', trip=self.trip, look=LOOK, g='male')
            self.assertEqual((await c.expect('error'))['code'], 'no_island')
        c = await self.connect(self.owner)
        await c.send(t='isl_in', trip='zz', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'bad')

    async def test_invitation_card_and_welcome_count(self):
        self.setup_trip(guests=0)
        c = await self.connect(self.people[0][0])
        self.assertNotIn('isl_inv', c.welcome)
        it.post(self.store, self.owner, 'invite', dict(trip=self.trip, codes=[self.codes[self.people[0][1]]]))
        ping = await c.expect('island_ping')
        self.assertEqual((ping['why'], ping['trip']), ('invite', self.trip))
        again = await self.connect(self.people[0][0])
        self.assertEqual(again.welcome.get('isl_inv'), 1)

    async def test_leaving_and_being_taken_off(self):
        self.setup_trip()
        self.accept(0)
        self.accept(1)
        owner = await self.enter(self.owner)
        a = await self.enter(self.people[0][0])
        await self.ev(owner, 'in')
        b = await self.enter(self.people[1][0])
        await self.ev(owner, 'in')
        await self.ev(a, 'in')
        it.post(self.store, self.people[0][0], 'leave', dict(trip=self.trip))
        await a.expect('isl_left', why='changed')
        self.assertEqual((await self.ev(owner, 'out'))['pid'], a.pid)
        it.post(self.store, self.owner, 'remove', dict(trip=self.trip, code=self.codes[self.people[1][1]]))
        await b.expect('isl_left', why='changed')

    async def test_owner_ends_the_trip_and_everyone_goes_home(self):
        self.setup_trip()
        self.accept(0)
        owner = await self.enter(self.owner)
        guest = await self.enter(self.people[0][0])
        it.post(self.store, self.owner, 'end', dict(trip=self.trip))
        await guest.expect('isl_left', why='ended')
        await owner.expect('isl_left', why='ended')
        await guest.send(t='isl_mv', p=[[.1, .1], [.2, .2]], ms=10)
        self.assertEqual((await guest.expect('error'))['code'], 'no_island')

    async def test_the_hour_runs_out(self):
        self.setup_trip()
        self.accept(0)
        owner = await self.enter(self.owner)
        guest = await self.enter(self.people[0][0])
        self.sql('UPDATE island_trips SET ends=? WHERE id=?', (time.time() + 1.2, self.trip))
        await owner.send(t='isl_emote', e='heart')        # the next check reads the new hour
        await owner.expect('isl_left', why='time', timeout=8)
        await guest.expect('isl_left', why='time', timeout=8)

    async def test_two_guests_who_blocked_each_other_never_see_each_other(self):
        self.setup_trip()
        self.accept(0)
        self.accept(1)
        a = await self.enter(self.people[0][0])
        # b blocked a before coming online (a new player reads its blocks on hello)
        self.sql('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (self.pid(self.people[1][1]), self.pid(self.people[0][1]), time.time()))
        b = await self.enter(self.people[1][0])
        self.assertEqual(b.room['people'], [])
        await a.nothing('isl', wait=.3)
        await b.send(t='isl_say', text='alo')
        await a.nothing('isl', wait=.3)

    async def test_a_public_visitor_walks_in_and_goes_home_when_it_closes(self):
        """🌍 Đảo mở cửa: a visitor who is not the owner's friend walks in while the island is open to everyone, the
        room's cap grows past the boat's seats, closing the island sends the visitor home (friends aboard stay)."""
        self.setup_trip(guests=1)                       # ⛵ 4 seats
        self.accept(0)
        marriage._mutate(self.store, {self.xsid: lambda s: s.setdefault('journey', {}).update(story=True)})
        owner = await self.enter(self.owner)
        c = await self.connect(self.stranger)
        await c.send(t='isl_in', trip=self.trip, look=LOOK, g='male')
        self.assertEqual((await c.expect('error'))['code'], 'no_island')        # not open yet
        it.post(self.store, self.owner, 'public', dict(trip=self.trip, open=True))
        it.post(self.store, self.stranger, 'visit', dict(trip=self.trip))
        visitor = await self.enter(self.stranger)
        self.assertEqual([p['pid'] for p in visitor.room['people']], [owner.pid])
        came = await self.ev(owner, 'in')
        self.assertEqual((came['pid'], came['o']), (visitor.pid, False))
        friend = await self.enter(self.people[0][0])
        await self.ev(owner, 'in')
        await self.ev(visitor, 'in')
        await visitor.send(t='isl_do', s='b_a')                                  # a building's spot (game/island_build.py)
        self.assertEqual((await self.ev(owner, 'do'))['s'], 'b_a')
        await self.ev(friend, 'do')
        it.post(self.store, self.owner, 'public', dict(trip=self.trip, open=False))
        await visitor.expect('isl_left', why='changed')
        self.assertEqual((await self.ev(owner, 'out'))['pid'], visitor.pid)
        await friend.send(t='isl_emote', e='wave')                               # the friend aboard is still there
        self.assertEqual((await self.ev(owner, 'emote'))['e'], 'wave')

    async def test_deploy_order_without_the_public_tables(self):
        """Review fix 19/10: a database without island_public / island_visitors (the live service is newer than the game
        server's migration): the owner and the friends aboard still get in (2.4.60's friends-only check)."""
        self.setup_trip()
        self.accept(0)
        self.sql('ALTER TABLE island_public RENAME TO island_public_later')
        self.sql('ALTER TABLE island_visitors RENAME TO island_visitors_later')
        try:
            owner = await self.enter(self.owner)
            guest = await self.enter(self.people[0][0])
            self.assertEqual((await self.ev(owner, 'in'))['pid'], guest.pid)
            c = await self.connect(self.stranger)
            await c.send(t='isl_in', trip=self.trip, look=LOOK, g='male')
            self.assertEqual((await c.expect('error'))['code'], 'no_island')
        finally:
            self.sql('ALTER TABLE island_public_later RENAME TO island_public')
            self.sql('ALTER TABLE island_visitors_later RENAME TO island_visitors')
