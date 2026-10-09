"""Owner and accepted friend presence uses real PostgreSQL authorization."""
import json
import time
import asyncio
from unittest.mock import patch
from game import home_guests, marriage
from tests.live_support import LiveCase


class Guests(LiveCase):
    cfg_extra = dict(home=True)

    def setup_house(self):
        self.owner, self.osid = self.account('Owner')
        self.first, self.fsid = self.account('First')
        self.second, self.ssid = self.account('Second')
        self.saved = {'journey': {'story': True, 'home': {'own': {'id': 'home1', 'kind': 'tap_the'}}}}
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(self.saved), self.osid))
        for sid in (self.osid, self.fsid, self.ssid):
            marriage.ensure_person(self.store, sid)
        self.befriend(self.osid, self.fsid)
        self.befriend(self.osid, self.ssid)
        with self.store.connect() as db:
            self.codes = {r['sid']: r['code'] for r in db.execute('SELECT sid,code FROM marriage_people').fetchall()}
        self.host = self.codes[self.osid]

    def invite(self, token, sid, kind='stay', accept=True):
        result = home_guests.post(self.store, self.owner, {}, 'invite', dict(code=self.codes[sid], kind=kind))
        ident = next(i['id'] for i in result['outgoing'] if i['code'] == self.codes[sid])
        if accept:
            home_guests.post(self.store, token, {}, 'answer', dict(id=ident, answer='accept'))
        return ident

    def sql(self, query, args=()):
        with self.store.connect() as db:
            return db.execute(query, args)

    async def enter(self, token, host=True):
        c = await self.connect(token)
        await c.send(t='home_in', r='living', x=.2, y=.8, **({'host': self.host} if host else {}))
        c.room = await c.expect('home_room')
        c.pid = c.welcome['me']['pid']
        return c

    async def event(self, c, kind):
        frame = await c.expect('home')
        self.assertEqual(frame['ev'][0]['k'], kind)
        return frame['ev'][0]

    async def test_pending_denied_then_two_accepted_guests_enter_with_owner_offline(self):
        self.setup_house()
        ident = self.invite(self.first, self.fsid, 'visit', accept=False)
        a = await self.connect(self.first)
        await a.send(t='home_in', r='living', host=self.host)
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        home_guests.post(self.store, self.first, {}, 'answer', dict(id=ident, answer='accept'))
        self.invite(self.second, self.ssid)
        a = await self.enter(self.first)
        b = await self.enter(self.second)
        self.assertEqual(a.room['room'], b.room['room'])
        self.assertEqual(b.room['people'][0]['pid'], a.pid)
        await self.event(a, 'in')
        owner = await self.enter(self.owner, host=False)
        self.assertEqual(owner.room['room'], a.room['room'])
        self.assertEqual(len(owner.room['people']), 2)
        for sid in (self.osid, self.fsid, self.ssid):
            self.assertNotIn(sid, json.dumps(owner.room))

    async def test_revocation_ejects_only_revoked_guest_before_forwarding(self):
        self.setup_house()
        ident = self.invite(self.first, self.fsid)
        self.invite(self.second, self.ssid)
        owner = await self.enter(self.owner)
        a = await self.enter(self.first)
        await self.event(owner, 'in')
        b = await self.enter(self.second)
        await self.event(owner, 'in'); await self.event(a, 'in')
        self.sql("UPDATE home_guest_invites SET status='revoked' WHERE id=?", (ident,))
        await a.send(t='home_mv', p=[[.2,.8],[.4,.8]], ms=200)
        await a.expect('home_left', why='changed')
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        self.assertEqual((await self.event(owner, 'out'))['pid'], a.pid)
        await self.event(b, 'out')
        await b.send(t='home_emote', kind='hug', to=owner.pid)
        offer = await self.event(owner, 'emote'); await self.event(b, 'emote')
        await owner.send(t='home_reply', id=offer['id'], answer='accept')
        await self.event(owner, 'reaction'); await self.event(b, 'reaction')

    async def test_expired_visit_and_unfriend_remove_guest_on_tick(self):
        self.setup_house()
        ident = self.invite(self.first, self.fsid, 'visit')
        self.invite(self.second, self.ssid)
        a = await self.enter(self.first); b = await self.enter(self.second)
        await self.event(a, 'in')
        self.sql('UPDATE home_guest_invites SET expires_at=? WHERE id=?', (time.time()-1, ident))
        await a.expect('home_left', why='changed', timeout=4)
        await self.event(b, 'out')
        self.sql('DELETE FROM friends WHERE sid=? AND friend=?', (self.osid, self.ssid))
        await b.expect('home_left', why='changed', timeout=4)

    async def test_both_block_tables_and_directions_deny_guest_to_guest_entry(self):
        self.setup_house()
        self.invite(self.first, self.fsid); self.invite(self.second, self.ssid)
        a = await self.enter(self.first)
        b = await self.connect(self.second)
        for table, key, x, y in (
            ('blocks','pid',self.pid(self.fsid),self.pid(self.ssid)),
            ('blocks','pid',self.pid(self.ssid),self.pid(self.fsid)),
            ('marriage_blocks','sid',self.fsid,self.ssid),
            ('marriage_blocks','sid',self.ssid,self.fsid),
        ):
            self.sql(f'INSERT INTO {table}({key},target,at) VALUES(?,?,?)',(x,y,time.time()))
            await b.send(t='home_in', r='living', host=self.host)
            self.assertEqual((await b.expect('error'))['code'], 'no_home')
            await a.nothing('home', wait=.01)
            self.sql(f'DELETE FROM {table} WHERE {key}=? AND target=?',(x,y))

    async def test_owner_move_ejects_all_rooms_and_old_home_cannot_rejoin(self):
        self.setup_house()
        self.invite(self.first, self.fsid); self.invite(self.second, self.ssid)
        a = await self.enter(self.first); b = await self.enter(self.second)
        await self.event(a, 'in')
        await b.send(t='home_in', r='bed', host=self.host)
        await b.expect('home_room'); await self.event(a, 'out')
        self.saved['journey']['home']['own']['id'] = 'home2'
        self.sql('UPDATE sessions SET state=? WHERE sid=?',(json.dumps(self.saved),self.osid))
        await a.send(t='home_mv', p=[[.2,.8],[.4,.8]], ms=200)
        await a.expect('home_left'); await b.expect('home_left')
        await a.expect('error', code='no_home')
        await b.send(t='home_in', r='living', host=self.host)
        await b.expect('error', code='no_home')

    async def test_owner_notify_refreshes_guest_and_chatblock_unblock_cannot_revive_invite(self):
        self.setup_house()
        ident = self.invite(self.first, self.fsid)
        a = await self.enter(self.first)
        await self.app.on_notify(json.dumps(dict(t='home_changed',sid=self.osid)))
        await a.expect('home_changed')
        owner = await self.enter(self.owner)
        await self.event(a, 'in')
        await owner.send(t='block',pid=a.pid); await owner.expect('blocked',on=True)
        await a.expect('home_left', why='changed')
        self.assertEqual((await self.event(owner,'out'))['pid'],a.pid)
        await owner.send(t='unblock',pid=a.pid); await owner.expect('blocked',on=False)
        with self.store.connect() as db:
            status = db.execute('SELECT status FROM home_guest_invites WHERE id=?',(ident,)).fetchone()['status']
        self.assertEqual(status, 'revoked')
        await a.send(t='home_in', r='living', host=self.host)
        await a.expect('error',code='no_home')

    async def test_divorce_removes_pair_but_keeps_invited_guest_without_ghost_people(self):
        self.setup_house()
        self.invite(self.first, self.fsid)
        with self.store.connect() as db:
            cid = db.execute("INSERT INTO couples(a,b,status,since) VALUES(?,?,'married',?) RETURNING id", (self.osid,self.ssid,time.time())).fetchone()[0]
            db.executemany('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', [(self.osid,cid),(self.ssid,cid)])
            db.execute('UPDATE sessions SET state=? WHERE sid=?',(json.dumps({'journey': {'story':True,'home': {'own':None, 'rent':None, 'shared': {'id':'home1','kind':'tap_the','couple':cid}}}}),self.ssid))
        a = await self.enter(self.first)
        owner = await self.enter(self.owner, host=False); await self.event(a,'in')
        spouse = await self.enter(self.second, host=False); await self.event(a,'in'); await self.event(owner,'in')
        self.assertEqual(len(spouse.room['people']),2)
        self.sql("UPDATE couples SET status='divorced' WHERE id=?",(cid,))
        await owner.send(t='home_mv',p=[[.2,.8],[.3,.8]],ms=50)
        await owner.expect('home_left'); await owner.expect('error',code='no_home'); await spouse.expect('home_left')
        departed = {(await self.event(a,'out'))['pid'],(await self.event(a,'out'))['pid']}
        self.assertEqual(departed,{owner.pid,spouse.pid})
        await a.send(t='home_mv',p=[[.2,.8],[.3,.8]],ms=50)
        await self.event(a,'mv')

    async def test_old_tab_out_does_not_cancel_new_tab_join_query(self):
        self.setup_house()
        self.invite(self.first,self.fsid)
        old = await self.enter(self.first)
        new = await self.connect(self.first)
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.app.db.fetchrow
        once = True
        async def delayed(sql,args=()):
            nonlocal once
            row = await original(sql,args)
            if once and sql == home_guests.ACCESS_SQL and args == (self.fsid,self.host):
                once = False
                entered.set()
                await release.wait()
            return row
        with patch.object(self.app.db,'fetchrow',side_effect=delayed):
            await new.send(t='home_in',r='living',host=self.host)
            await asyncio.wait_for(entered.wait(),2)
            await old.call('home_out','home_left')
            release.set()
            await new.expect('home_room')

    async def test_married_owner_living_apart_joins_own_home_without_host(self):
        self.setup_house()
        self.invite(self.first, self.fsid)
        with self.store.connect() as db:
            cid = db.execute("INSERT INTO couples(a,b,status,since) VALUES(?,?,'married',?) RETURNING id", (self.osid,self.ssid,time.time())).fetchone()[0]
            db.executemany('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', [(self.osid,cid),(self.ssid,cid)])
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps({'journey': {'story':True, 'home': {'own':None,'rent':None,'shared':None}}}),self.ssid))
        visitor = await self.enter(self.first)
        owner = await self.enter(self.owner, host=False)
        self.assertEqual(owner.room['room'], visitor.room['room'])
        self.assertEqual(owner.room['people'][0]['pid'],visitor.pid)
        await self.event(visitor,'in')
        await owner.send(t='home_mv',p=[[.2,.8],[.3,.8]],ms=50)
        await self.event(owner,'mv'); await self.event(visitor,'mv')
        spouse = await self.connect(self.second)
        await spouse.send(t='home_in',r='living')
        await spouse.expect('error',code='no_home')
        await spouse.send(t='home_in',r='living',host=self.host)
        await spouse.expect('error',code='no_home')

    async def test_revoked_while_join_waits_for_peer_checks_never_receives_room(self):
        from live.home import BLOCK_SQL
        self.setup_house()
        ident = self.invite(self.first,self.fsid)
        owner = await self.enter(self.owner)
        guest = await self.connect(self.first)
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.app.db.fetchrow
        once = True
        async def delayed(sql,args=()):
            nonlocal once
            row = await original(sql,args)
            if once and sql == BLOCK_SQL and args[0] == self.fsid:
                once = False
                entered.set()
                await release.wait()
            return row
        with patch.object(self.app.db,'fetchrow',side_effect=delayed):
            await guest.send(t='home_in',r='living',host=self.host)
            await asyncio.wait_for(entered.wait(),2)
            home_guests.post(self.store,self.owner,{},'revoke',dict(id=ident))
            release.set()
            await asyncio.sleep(.15)
            await guest.nothing('home_room',wait=.01)
            await guest.expect('error',code='no_home')
            await owner.nothing('home',wait=.01)
    async def test_unmarried_owner_can_enter_own_house(self):
        token, sid = self.account('Owner')
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps({'journey': {
                'story': True, 'home': {'own': {'id': 'own1', 'kind': 'tap_the'}}}}), sid))
        owner = await self.connect(token)
        await owner.send(t='home_in', r='living')
        room = await owner.expect('home_room')
        self.assertEqual(room['cap'], 12)
        self.assertEqual(room['people'], [])
        self.assertNotIn(sid, json.dumps(room))


    async def test_villa_guests_and_owner_meet_on_every_floor(self):
        # 🏰 F 09/10: a villa bought in Mua sắm (game/estates.py) that its owner lives in, with no house of their own.
        self.setup_house()
        self.saved = {'journey': {'story': True, 'home': {'own': None, 'shared': None, 'rent': None},
                                  'lux': {'own': {'bt_vuon_da_lat': {'d': 3, 'p': 150000}}, 'live': 'bt_vuon_da_lat'}}}
        self.sql('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(self.saved), self.osid))
        self.invite(self.first, self.fsid)
        self.invite(self.second, self.ssid, 'visit')
        with self.store.connect() as db:
            homes = {(r['home_id'], r['home_kind']) for r in db.execute('SELECT home_id,home_kind FROM home_guest_invites').fetchall()}
        self.assertEqual(homes, {('estate:bt_vuon_da_lat:3', 'bt_vuon_da_lat')})
        a = await self.enter(self.first)
        await a.send(t='home_in', r='bed', host=self.host)   # a bedroom on the second floor
        a.room = await a.expect('home_room')
        b = await self.connect(self.second)
        await b.send(t='home_in', r='bed', host=self.host)
        b.room = await b.expect('home_room')
        self.assertEqual(a.room['room'], b.room['room'])
        await self.event(a, 'in')
        owner = await self.connect(self.owner)
        await owner.send(t='home_in', r='bed')
        owner.room = await owner.expect('home_room')
        self.assertEqual(owner.room['room'], a.room['room'])
        self.assertEqual(len(owner.room['people']), 2)
        await b.send(t='home_in', r='nowhere', host=self.host)
        await b.expect('error', code='bad')
        self.saved['journey']['lux']['live'] = None   # the owner moves out of the villa
        self.sql('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(self.saved), self.osid))
        await a.send(t='home_mv', p=[[.2, .8], [.4, .8]], ms=200)
        await a.expect('home_left'); await b.expect('home_left'); await owner.expect('home_left')
        await a.send(t='home_in', r='bed', host=self.host)
        await a.expect('error', code='no_home')
