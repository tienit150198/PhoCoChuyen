"""Real PostgreSQL/WebSocket visit permissions, presence and block revocation."""
import asyncio
import json
import time

from tests.live_support import LiveCase


class WorkplaceVisits(LiveCase):
    cfg_extra = dict(visits=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ta, self.sa = self.account('Chủ tiệm')
        self.tb, self.sb = self.account('Bạn ghé')
        self.tc, self.sc = self.account('Người lạ')
        self.place = 'visit-test-place'
        self.befriend(self.sa, self.sb)
        self.sql("INSERT INTO work_visit_places(id,owner,kind,target,visibility,data,updated_at) VALUES(?,?,'career','milk_tea','friends',?,?)",
                 (self.place, self.sa, json.dumps({'name': 'Trà sữa', 'activity': {'label': 'Đang pha'}}), time.time()))

    def sql(self, sql, args=()):
        with self.store.connect() as db:
            db.execute(sql, args)

    async def join(self, token):
        c = await self.connect(token)
        await c.send(t='visit_in', place=self.place)
        c.room = await c.expect('visit_state')
        return c

    async def test_friend_enters_and_stranger_is_refused(self):
        a = await self.join(self.ta)
        b = await self.join(self.tb)
        self.assertEqual(len(b.room['people']), 2)
        self.assertNotIn(self.sa, json.dumps(b.room))
        self.assertNotIn(self.sb, json.dumps(b.room))
        c = await self.connect(self.tc)
        await c.send(t='visit_in', place=self.place)
        self.assertEqual((await c.expect('error'))['code'], 'no_visit')
        await b.send(t='visit_chat', text='Chào bạn!')
        self.assertEqual((await a.expect('visit_chat'))['text'], 'Chào bạn!')
        await b.send(t='visit_mv', p=[[.5,.8],[2,-1]], ms=9000)
        move = await a.expect('visit_mv')
        self.assertEqual(move['p'][-1], [1.,0.])
        self.assertEqual(move['ms'], 3000)

    async def test_closing_revokes_before_owner_can_broadcast(self):
        a = await self.join(self.ta)
        b = await self.join(self.tb)
        self.sql("UPDATE work_visit_places SET visibility='closed' WHERE id=?", (self.place,))
        await a.send(t='visit_emote', kind='heart')
        self.assertEqual((await b.expect('visit_left'))['why'], 'changed')
        await b.nothing('visit_emote', wait=.05)

    async def test_public_visitors_blocked_from_one_another_leave_before_message(self):
        self.sql("UPDATE work_visit_places SET visibility='public' WHERE id=?", (self.place,))
        b = await self.join(self.tb)
        c = await self.join(self.tc)
        self.sql('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (self.sb,self.sc,time.time()))
        await c.send(t='visit_chat', text='must not arrive')
        self.assertEqual((await c.expect('visit_left'))['why'], 'changed')
        await b.nothing('visit_chat', wait=.05)

    async def test_idle_revoke_takeover_and_room_cleanup(self):
        old = await self.join(self.tb)
        newer = await self.join(self.tb)
        self.assertEqual((await old.expect('visit_left'))['why'], 'other')
        await old.call('visit_out', 'visit_left')
        await newer.send(t='visit_emote', kind='wave')
        await newer.expect('visit_emote')
        self.sql("UPDATE work_visit_places SET visibility='closed' WHERE id=?", (self.place,))
        await newer.expect('visit_left', timeout=4)
        self.assertFalse(self.app.hub.rooms_with_prefix('visit:'))

    async def test_sanitized_activity_changes_and_invalid_movement(self):
        b = await self.join(self.tb)
        self.sql('UPDATE work_visit_places SET data=?,updated_at=? WHERE id=?',
                 (json.dumps({'name':'Trà sữa','activity':{'label':'Xong rồi'},'state':{'secret':1}}),time.time()+1,self.place))
        f = await b.expect('visit_activity',timeout=4)
        self.assertNotIn('state', f['activity'])
        await b.send(t='visit_mv',p=[[0,0],[True,0]],ms=30)
        self.assertEqual((await b.expect('error'))['code'],'bad')
        await b.close()
        await asyncio.sleep(.05)
        self.assertFalse(self.app.hub.rooms_with_prefix('visit:'))

    async def test_blocked_simultaneous_admission_has_only_one_member(self):
        self.sql("UPDATE work_visit_places SET visibility='public' WHERE id=?", (self.place,))
        self.sql('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (self.sb,self.sc,time.time()))
        b=await self.connect(self.tb);c=await self.connect(self.tc)
        await asyncio.gather(b.send(t='visit_in',place=self.place),c.send(t='visit_in',place=self.place))
        await asyncio.sleep(.2)
        rooms=self.app.hub.rooms_with_prefix('visit:')
        self.assertEqual(len(rooms),1)
        self.assertEqual(len(rooms[0].conns),1)
        self.assertFalse(self.app.by_name['visits'].join_locks)
