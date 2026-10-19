"""⚔️ The bang island's room in the live service (live/bang_island.py) with the stub Bang (game/bang_island.py
StubProvider): members and invited guests walk, talk, gesture and visit facilities together; strangers are refused;
the room's cap; movement never asks the contract (memory only); access is asked again periodically and at once on a
notice from the game server (kicked, view, disband); bubbles go through the chat's store; blocks hide people."""
import json
import time

from game import bang_island as BI
from tests.live_support import LiveCase

LOOK = dict(hair='toc_ngan', top='ao_thun')


class CountingStub(BI.StubProvider):
    calls = 0
    fail = False

    async def access_live(self, db, sid, bang_id):
        type(self).calls += 1
        if self.fail:
            raise RuntimeError('provider down')
        return self._access(sid, bang_id)


class BangIsland(LiveCase):
    cfg_extra = dict(bisle=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.a, self.asid = self.account('Bang Chu')
        self.b, self.bsid = self.account('De Tu')
        self.g, self.gsid = self.account('Khach Moi')
        self.x, self.xsid = self.account('Nguoi La')
        CountingStub.calls, CountingStub.fail = 0, False
        self.stub = CountingStub(views={'b1': BI.stub_view('b1')}, members={self.asid: ('b1', 'bang_chu'), self.bsid: ('b1', 'thanh_vien')},
                                 guests={self.gsid: {'b1'}})
        BI.register(self.stub)
        self.feat = self.app.by_name['bang_island']

    async def asyncTearDown(self):
        BI.register(None)
        BI._looked = False
        await super().asyncTearDown()

    async def enter(self, token, x=.85, y=.85, bang='b1'):
        c = await self.connect(token)
        await c.send(t='bisl_in', bang=bang, look=LOOK, g='female', x=x, y=y)
        c.room = await c.expect('bisl_room')
        c.pid = c.welcome['me']['pid']
        return c

    async def ev(self, c, kind, timeout=3.0):
        f = await c.expect('bisl', timeout=timeout)
        self.assertEqual(f['ev'][0]['k'], kind, f)
        return f['ev'][0]

    def sql(self, q, args=()):
        with self.store.connect() as db:
            return db.execute(q, args)

    async def test_welcome_flag(self):
        c = await self.connect(self.a)
        self.assertTrue(c.welcome['flags'].get('bisle'))

    async def test_members_and_a_guest_walk_talk_gesture_together(self):
        a = await self.enter(self.a)
        self.assertEqual((a.room['bang'], a.room['kind'], a.room['role'], a.room['cap'], a.room['people']), ('b1', 'member', 'bang_chu', BI.CAP, []))
        b = await self.enter(self.b, .5, .6)
        self.assertEqual([(p['pid'], p['kd'], p['r']) for p in b.room['people']], [(a.pid, 'member', 'bang_chu')])
        came = await self.ev(a, 'in')
        self.assertEqual((came['pid'], came['name'], came['x'], came['y'], came['kd']), (b.pid, 'De Tu', .5, .6, 'member'))
        g = await self.enter(self.g)
        self.assertEqual(g.room['kind'], 'guest')
        self.assertEqual((await self.ev(a, 'in'))['kd'], 'guest')
        await self.ev(b, 'in')
        calls = CountingStub.calls
        for i in range(4):
            await b.send(t='bisl_mv', p=[[.5, .6], [.5 + i / 100, .5]], ms=500)
        # 21/10: a room's walks go out together every MV_FLUSH seconds, each walker's latest move (one frame, not four)
        f = await a.expect('bisl')
        self.assertEqual([e['k'] for e in f['ev']], ['mv'])
        mv = f['ev'][0]
        self.assertEqual((mv['pid'], mv['p'], mv['ms']), (b.pid, [[.5, .6], [.53, .5]], 500))
        await a.nothing('bisl', wait=.4)
        own = await b.expect('bisl')                       # the walker gets the same frame (the client skips its own move)
        self.assertEqual([e['pid'] for e in own['ev']], [b.pid])
        self.assertEqual(CountingStub.calls, calls, 'walking never asks the contract')
        await a.send(t='bisl_emote', e='bow')
        self.assertEqual((await self.ev(b, 'emote'))['e'], 'bow')
        self.assertEqual((await self.ev(a, 'emote'))['e'], 'bow')
        await b.send(t='bisl_do', s='dai_sanh')
        self.assertEqual((await self.ev(a, 'do'))['s'], 'dai_sanh')
        await b.send(t='bisl_do', s='ao_sen')
        self.assertEqual((await self.ev(a, 'do'))['s'], 'ao_sen')
        await b.send(t='bisl_do', s='hang_dong')
        self.assertEqual((await b.expect('error'))['code'], 'bad')
        await a.send(t='bisl_emote', e='nope')
        self.assertEqual((await a.expect('error'))['code'], 'bad')
        await a.send(t='bisl_say', text='Họp bang lúc 8 giờ nhé!')
        said = await self.ev(b, 'said')
        self.assertEqual((said['pid'], said['text']), (a.pid, 'Họp bang lúc 8 giờ nhé!'))
        await self.ev(a, 'said')
        row = self.sql('SELECT channel FROM chat_messages WHERE id=?', (said['id'],)).fetchone()
        self.assertEqual(row['channel'], 'bisl:b1', 'kept in the chat store (filters, reports, admin hide)')
        await b.send(t='bisl_out')
        await b.expect('bisl_left', why='out')
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.pid)
        for sid in (self.asid, self.bsid, self.gsid):
            self.assertNotIn(sid, json.dumps(a.frames + b.frames + g.frames + [a.room, b.room, g.room]))

    async def test_strangers_bad_ids_and_frames_outside_the_room(self):
        c = await self.connect(self.x)
        await c.send(t='bisl_in', bang='b1', look=LOOK, g='male')
        self.assertEqual((await c.expect('error'))['code'], 'no_bang_island')
        await c.send(t='bisl_in', bang='B 1', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'bad')
        await c.send(t='bisl_mv', p=[[.1, .1], [.2, .2]], ms=10)
        self.assertEqual((await c.expect('error'))['code'], 'no_bang_island')
        b = await self.connect(self.b)
        await b.send(t='bisl_in', bang='b2', look=LOOK)
        self.assertEqual((await b.expect('error'))['code'], 'no_bang_island', 'a member of b1 is a stranger on b2')

    async def test_the_cap(self):
        old, BI.CAP = BI.CAP, 2
        try:
            await self.enter(self.a)
            await self.enter(self.b)
            c = await self.connect(self.g)
            await c.send(t='bisl_in', bang='b1', look=LOOK)
            self.assertEqual((await c.expect('error'))['code'], 'full')
        finally:
            BI.CAP = old

    async def test_access_is_asked_again_periodically(self):
        self.feat.check_every = .3
        a = await self.enter(self.a)
        b = await self.enter(self.b)
        await self.ev(a, 'in')
        self.stub.members.pop(self.bsid)       # left the bang (the Bang branch's answer changes)
        await b.expect('bisl_left', why='changed', timeout=4)
        self.assertEqual((await self.ev(a, 'out', timeout=4))['pid'], b.pid)
        await b.send(t='bisl_say', text='alo')
        self.assertEqual((await b.expect('error'))['code'], 'no_bang_island')

    async def test_a_provider_error_keeps_people_and_refuses_a_join_once(self):
        self.feat.check_every = .3
        a = await self.enter(self.a)
        self.stub.fail = True
        await a.nothing('bisl_left', wait=1.2)
        c = await self.connect(self.b)
        await c.send(t='bisl_in', bang='b1', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'busy')
        self.stub.fail = False
        await self.enter(self.b)

    async def test_notices_from_the_game_server(self):
        a = await self.enter(self.a)
        b = await self.enter(self.b)
        await self.ev(a, 'in')
        await self.app.on_notify(json.dumps(dict(op='bang_island', why='view', bang='b1')))
        await self.ev(a, 'view')
        await self.ev(b, 'view')
        self.stub.members.pop(self.bsid)
        await self.app.on_notify(json.dumps(dict(op='bang_island', why='kicked', sid=self.bsid, bang='b1')))
        await b.expect('bisl_left', why='changed', timeout=1.5)
        await self.app.on_notify(json.dumps(dict(op='bang_island', why='nonsense', bang='b1')))
        await self.app.on_notify(json.dumps(dict(op='bang_island', why='disband', bang='b1')))
        await a.expect('bisl_left', why='ended', timeout=1.5)

    async def test_a_second_window_takes_over(self):
        a1 = await self.enter(self.a)
        await self.enter(self.a)
        await a1.expect('bisl_left', why='other')

    async def test_two_members_who_blocked_each_other_never_see_each_other(self):
        a = await self.enter(self.a)
        self.sql('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (self.pid(self.bsid), self.pid(self.asid), time.time()))
        b = await self.enter(self.b)
        self.assertEqual(b.room['people'], [])
        await a.nothing('bisl', wait=.3)
        await b.send(t='bisl_say', text='alo')
        await a.nothing('bisl', wait=.3)


class IsleStub(CountingStub):
    """🏝️ The real provider's answer since 21/10: the island's level (0: not bought) and its cap."""
    isle, cap = 1, 2

    async def access_live(self, db, sid, bang_id):
        acc = await super().access_live(db, sid, bang_id)
        return dict(acc, isle=type(self).isle, cap=type(self).cap) if acc else acc


class IslandLevels(LiveCase):
    cfg_extra = dict(bisle=True)
    enter, ev = BangIsland.enter, BangIsland.ev

    async def asyncTearDown(self):
        BI.register(None)
        BI._looked = False
        await super().asyncTearDown()

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.a, self.asid = self.account('Bang Chu')
        self.b, self.bsid = self.account('De Tu')
        self.g, self.gsid = self.account('Khach Moi')
        IsleStub.isle, IsleStub.cap, IsleStub.fail = 1, 2, False
        self.stub = IsleStub(views={'b1': BI.stub_view('b1')}, members={self.asid: ('b1', 'bang_chu'), self.bsid: ('b1', 'thanh_vien')},
                             guests={self.gsid: {'b1'}})
        BI.register(self.stub)

    async def test_the_room_cap_is_the_island_level_s_and_grows(self):
        a = await self.enter(self.a)
        self.assertEqual(a.room['cap'], 2)
        await self.enter(self.b)
        c = await self.connect(self.g)
        await c.send(t='bisl_in', bang='b1', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'full')
        IsleStub.cap = 3                                     # the island grew: the next join opens the room wider
        await c.send(t='bisl_in', bang='b1', look=LOOK)
        self.assertEqual((await c.expect('bisl_room'))['cap'], 3)

    async def test_a_bang_without_its_island_has_no_room(self):
        IsleStub.isle = 0
        c = await self.connect(self.a)
        await c.send(t='bisl_in', bang='b1', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'no_bang_island')

    async def test_a_room_of_many_walkers_sends_one_frame_a_flush(self):
        IsleStub.cap = 40
        a = await self.enter(self.a)
        b = await self.enter(self.b)
        g = await self.enter(self.g)
        await self.ev(a, 'in')
        await self.ev(a, 'in')
        await self.ev(b, 'in')
        for c, x in ((b, .4), (g, .6), (b, .45)):
            await c.send(t='bisl_mv', p=[[.5, .5], [x, .5]], ms=300)
        f = await a.expect('bisl')
        self.assertEqual(sorted((e['k'], e['pid'], e['p'][1][0]) for e in f['ev']), sorted([('mv', g.pid, .6), ('mv', b.pid, .45)]), 'each walker\'s latest')
        await a.nothing('bisl', wait=.4)


class Off(LiveCase):
    async def test_frames_are_off_without_the_switch(self):
        token, _ = self.account('Ai Do')
        c = await self.connect(token)
        self.assertNotIn('bisle', c.welcome['flags'])
        await c.send(t='bisl_in', bang='b1', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'off')


class TickCap(BangIsland):
    async def test_the_check_cap_holds_across_rooms(self):
        """Review fix 19/10: at most CHECKS_PER_TICK re-checks a tick, every room together (the inner `break` alone let
        each room take its own 200)."""
        from types import SimpleNamespace
        from live import bang_island as LBI
        rooms = [SimpleNamespace(conns=[SimpleNamespace(ext={}) for _ in range(150)]) for _ in range(3)]
        done = []

        async def recheck(conn):
            done.append(conn)
            conn.ext['bisl_at'] = 10**12
        orig = self.feat.hub.rooms_with_prefix
        self.feat.hub.rooms_with_prefix = lambda prefix: rooms if prefix == LBI.PREFIX else orig(prefix)
        self.feat._recheck = recheck
        try:
            await self.feat.tick(0)
            self.assertEqual(len(done), LBI.CHECKS_PER_TICK)
            await self.feat.tick(0)
            self.assertEqual(len(done), 2 * LBI.CHECKS_PER_TICK)
            await self.feat.tick(0)
            self.assertEqual(len(done), 450)                                     # everyone, then nobody twice
        finally:
            del self.feat._recheck
            self.feat.hub.rooms_with_prefix = orig
