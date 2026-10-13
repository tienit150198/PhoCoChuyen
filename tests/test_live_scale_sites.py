import asyncio
import json
from tests.live_support import LiveCase
from live.town import MAP_ID


class ScaleSiteSockets(LiveCase):
    cfg_extra = dict(town=True)

    def save_site(self, sid, public=False):
        state = {'money': 987654321, 'careers': {'grocery': {'scale': {
            'tier': 1, 'sites': [{'id': 'base', 'name': 'Tiệm Lan', 'public': public}],
            'resources': [{'id': 'r1', 'site': 'base', 'crew': 'c1', 'busy': 'SECRET-CONTRACT'}],
            'crew': [{'id': 'c1', 'name': 'Hà', 'wage': 888}], 'contracts': 'SECRET-CONTRACT'}}}}
        with self.store.connect() as db:
            db.execute('INSERT INTO profiles(pid,sid,created,updated,seen,week_key) VALUES(?,?,0,0,0,?) ON CONFLICT DO NOTHING', (self.pid(sid), sid, '2026-W42'))
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state), sid))

    async def fixture(self, public=False):
        token, sid = self.account('Lan')
        owner = await self.connect(token)
        self.save_site(sid, public)
        token2, _ = self.account('Khách')
        guest = await self.connect(token2)
        args = dict(owner=self.pid(sid), career='grocery', site='base')
        return owner, guest, sid, args

    async def test_private_owner_public_guest_and_whitelist(self):
        owner, guest, sid, args = await self.fixture()
        own = await owner.call('site_in', 'town_room', **args)
        self.assertEqual(own['map'], 'scale-site-v1')
        self.assertEqual(own['site']['name'], 'Tiệm Lan')
        self.assertNotIn('SECRET-CONTRACT', json.dumps(own))
        self.assertIs(own['layout']['resources'][0]['busy'], True)
        self.assertNotIn('987654321', json.dumps(own))
        await guest.send(t='site_in', **args)
        self.assertEqual((await guest.expect('error'))['code'], 'private')
        self.save_site(sid, True)
        town = self.app.by_name['town']; town._sites_at = 0
        await town.tick(__import__('time').monotonic())
        self.assertTrue((await owner.expect('town_site'))['site']['public'])
        other = await guest.call('site_in', 'town_room', **args)
        self.assertEqual(other['room'], own['room'])
        self.assertEqual(other['people'][0]['pid'], args['owner'])

    async def test_chat_isolation_revocation_and_street_return(self):
        owner, guest, sid, args = await self.fixture(True)
        street_token, _ = self.account('Phố')
        street = await self.connect(street_token)
        await street.call('town_in', 'town_room', map=MAP_ID, x=6, y=6)
        await owner.call('site_in', 'town_room', **args)
        await guest.call('site_in', 'town_room', **args)
        said = await owner.call('town_say', 'town_said', text='Trong tiệm')
        self.assertEqual((await guest.expect('town_said'))['id'], said['id'])
        await street.nothing('town_said')
        await owner.call('town_emote', 'town_emoted', e='👋')
        await guest.expect('town_emoted')
        self.save_site(sid, False)
        await guest.send(t='town_say', text='Đã đóng')
        self.assertEqual((await guest.expect('error', ref='town_say'))['code'], 'private')
        await guest.expect('town_left', why='private')
        returned = await guest.call('town_in', 'town_room', map=MAP_ID, x=6, y=6)
        self.assertTrue(returned['room'].startswith(MAP_ID+':'))
        await guest.send(t='history', ch=said['ch'])
        self.assertEqual((await guest.expect('error', ref='history'))['code'], 'no_chat')

    async def test_idle_revocation_and_takeover_cleanup(self):
        owner, guest, sid, args = await self.fixture(True)
        await owner.call('site_in', 'town_room', **args)
        joined = await guest.call('site_in', 'town_room', **args)
        self.save_site(sid, False)
        town = self.app.by_name['town']
        town._sites_at = 0
        await town.tick(__import__('time').monotonic())
        await guest.expect('town_left', why='private')
        self.assertEqual(len(self.app.hub.rooms[joined['room']].data['people']), 1)
        await owner.close()
        await asyncio.sleep(.15)
        self.assertNotIn(joined['room'], self.app.hub.rooms)

    async def test_invalid_ids_and_collision(self):
        owner, guest, sid, args = await self.fixture(True)
        await owner.send(t='site_in', **dict(args, owner='../anything'))
        self.assertEqual((await owner.expect('error'))['code'], 'bad')
        await owner.call('site_in', 'town_room', **args)
        await owner.send(t='town_mv', x=0, y=0)
        self.assertEqual((await owner.expect('error'))['code'], 'bad')

    async def test_sites_separate_audiences_and_second_tab_takes_over(self):
        owner, guest, sid, args = await self.fixture(True)
        with self.store.connect() as db:
            state=json.loads(db.execute('SELECT state FROM sessions WHERE sid=?',(sid,)).fetchone()['state'])
            state['careers']['grocery']['scale']['sites'].append(dict(id='branch-1',name='Nhánh',public=True))
            db.execute('UPDATE sessions SET state=? WHERE sid=?',(json.dumps(state),sid))
        own=await owner.call('site_in','town_room',**args)
        await guest.call('site_in','town_room',**dict(args,site='branch-1'))
        await owner.call('town_say','town_said',text='Chỉ cơ sở gốc')
        await guest.nothing('town_said')
        # Same account reconnects in a different tab: stale socket cannot remove it.
        # Obtain a new login for the existing owner without reusing a session token.
        import secrets
        login=secrets.token_hex(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)',(self.store.digest(login),sid,'c'))
        second=await self.connect(login)
        await second.call('site_in','town_room',**args)
        await owner.expect('town_left',why='other')
        await owner.close()
        await second.call('town_emote','town_emoted',e='👋')
        self.assertIn(args['owner'],self.app.hub.rooms[own['room']].data['people'])

    async def test_site_geometry_rejects_furniture_and_activity_forgery(self):
        owner,guest,sid,args=await self.fixture(True)
        frame=await owner.call('site_in','town_room',**args)
        await owner.send(t='town_mv',x=3.5,y=3.0)
        self.assertEqual((await owner.expect('error'))['code'],'bad')
        await owner.send(t='town_mv',x=11.5,y=16.25,activity=dict(kind='fishing',phase='walk',x=1,y=1,direction='ne'))
        await asyncio.sleep(.1)
        walker=self.app.hub.rooms[frame['room']].data['people'][args['owner']]
        self.assertIsNone(walker.activity)

    async def test_added_furniture_relocates_occupied_floor_without_teleport_budget(self):
        owner,guest,sid,args=await self.fixture(True)
        frame=await owner.call('site_in','town_room',**args)
        room=self.app.hub.rooms[frame['room']]
        walker=room.data['people'][args['owner']]
        walker.x,walker.y=10.75,3.0
        with self.store.connect() as db:
            state=json.loads(db.execute('SELECT state FROM sessions WHERE sid=?',(sid,)).fetchone()['state'])
            state['careers']['grocery']['scale']['resources'].append(dict(id='r2',site='base',crew=None,busy=None))
            db.execute('UPDATE sessions SET state=? WHERE sid=?',(json.dumps(state),sid))
        town=self.app.by_name['town'];town._sites_at=0
        await town.tick(__import__('time').monotonic())
        updated=await owner.expect('town_site')
        self.assertEqual((updated.get('x'),updated.get('y')),(11.5,16.25))
        self.assertEqual((walker.x,walker.y),(11.5,16.25))
