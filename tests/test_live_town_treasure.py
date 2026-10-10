"""Authenticated WebSocket movement -> short proof -> atomic HTTP-domain claim."""
import importlib.util
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game import journey
from game.storage import Store, serialize
from tests.live_support import LiveCase, ORIGIN


class BroadcastCompatibility(unittest.TestCase):
    def test_text_frames_use_installed_broadcast_signature(self):
        from live import hub
        self.assertTrue(hasattr(hub,'_broadcast'), 'text-frame broadcast adapter required')
        sent=[]
        def installed(connections,message,raise_exceptions=False):sent.append(message)
        with patch('live.hub._ws_broadcast',installed):
            hub._broadcast([],b'{"t":"welcome"}',text=True)
        self.assertEqual(sent,['{"t":"welcome"}'])


class TreasureSockets(LiveCase):
    cfg_extra = dict(town=True)

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.store = Store(Path(cls.tmp.name) / 'treasure-live.db', story=True)
        cls.addClassCleanup(cls.store.close_pool)

    async def asyncSetUp(self):
        self.assertIsNotNone(importlib.util.find_spec('live.town_treasure'), 'live treasure feature missing')
        self.cfg_extra = dict(town=True, treasure=True)
        p = patch.dict('os.environ', LIVE_TOWN='1', LIVE_TOWN_TREASURE='1')
        p.start(); self.addCleanup(p.stop)
        from live.app import App
        from live.config import Config
        with self.store.connect() as db:
            db.execute('DELETE FROM town_treasure_waves')
            db.execute('DELETE FROM town_treasure_proofs')
            db.execute('DELETE FROM town_treasure_presence')
        self.cfg=Config(port=0,chat=False,origins=frozenset({ORIGIN}),db_url=self.store.pg.url,
                        db_schema=self.store.pg.schema,presence_grace=.1,town=True,treasure=True)
        self.app=App(self.cfg)
        await self.app.start()
        self.port=self.app.port()
        self.clients=[]
        from game import town_treasure
        self.tt = town_treasure

    async def asyncTearDown(self):
        for c in self.clients:
            if c.closed is None:
                await c.close()
        await self.app.stop()

    async def enter(self):
        token,sid = self.account()
        state=self.store.read(token)[0]
        journey.enable_story(state,42)
        self.store.transaction(lambda db:db.execute('UPDATE sessions SET state=? WHERE sid=?',(serialize(state),sid)))
        c=await self.connect(token)
        out=await c.call('town_in','town_room',map='iso-town-v1',x=70,y=44,direction='se')
        self.assertEqual((out['x'],out['y']),self.tt.START,'new client coordinates cannot teleport to treasure')
        return c,token,sid

    def next_chest(self):
        return self.tt.snapshot(self.store)['chests'][0]

    def put_chest_near_spawn(self, chest):
        self.store.transaction(lambda db:db.execute('UPDATE town_treasure_chests SET x=?,y=? WHERE id=?',(*self.tt.START,chest['id'])))

    async def test_live_proof_pays_authenticated_nearby_player_and_replays(self):
        c,token,sid=await self.enter()
        chest=self.next_chest();self.put_chest_near_spawn(chest)
        response=await c.call('town_treasure_prepare','town_treasure_ready',chest_id=chest['id'],cid='proof-a',x=999,y=999)
        self.assertEqual(response['cid'],'proof-a')
        body=dict(chest_id=chest['id'],proof=response['proof'],request_id='live-pick-001')
        result=self.tt.claim(self.store,token,body)
        self.assertEqual(result['result']['treasure']['coins'],10000)
        self.assertTrue(self.tt.claim(self.store,token,body)['replayed'])

    async def test_remote_stale_and_activity_presence_cannot_get_proof(self):
        c,token,sid=await self.enter()
        chest=self.next_chest()
        self.store.transaction(lambda db:db.execute('UPDATE town_treasure_chests SET x=60,y=44 WHERE id=?',(chest['id'],)))
        await c.send(t='town_treasure_prepare',chest_id=chest['id'],x=60,y=44,cid='remote')
        self.assertEqual((await c.expect('error',ref='remote'))['code'],'treasure_presence')
        self.put_chest_near_spawn(chest)
        room,w=self.app.by_name['town']._me(next(cn for cn in self.app.hub.conns if cn.player.sid==sid))
        w.last=time.monotonic()-13
        await c.send(t='town_treasure_prepare',chest_id=chest['id'],cid='stale')
        self.assertEqual((await c.expect('error',ref='stale'))['code'],'treasure_presence')
        w.last=time.monotonic()
        w.activity=dict(kind='homes-rent',x=0,y=0,direction='se',phase='idle',moving=False,action=None)
        await c.send(t='town_treasure_prepare',chest_id=chest['id'],cid='activity')
        self.assertEqual((await c.expect('error',ref='activity'))['code'],'treasure_presence')

    async def test_takeover_and_leave_revoke_proof(self):
        c,token,sid=await self.enter()
        chest=self.next_chest();self.put_chest_near_spawn(chest)
        response=await c.call('town_treasure_prepare','town_treasure_ready',chest_id=chest['id'])
        other=await self.connect(token)
        await other.call('town_in','town_room',map='iso-town-v1',x=70,y=44)
        body=dict(chest_id=chest['id'],proof=response['proof'],request_id='takeover-001')
        with self.assertRaises(self.tt.TreasureError):self.tt.claim(self.store,token,body)
        ready=await other.call('town_treasure_prepare','town_treasure_ready',chest_id=chest['id'])
        await other.call('town_out','town_left')
        body['proof']=ready['proof']
        with self.assertRaises(self.tt.TreasureError):self.tt.claim(self.store,token,body)

    async def test_reconnect_resumes_checkpoint_and_movement_does_not_hit_db(self):
        c,token,sid=await self.enter()
        conn=next(cn for cn in self.app.hub.conns if cn.player.sid==sid)
        room,w=self.app.by_name['town']._me(conn)
        w.last-=1
        calls=[]; original=self.app.db._run
        async def track(sql,*args,**kw):
            calls.append(sql)
            return await original(sql,*args,**kw)
        self.app.db._run=track
        await self.app.by_name['town'].town_mv(conn,dict(x=6,y=8))
        self.app.db._run=original
        self.assertEqual(calls,[])
        await self.app.by_name['treasure'].checkpoint()
        other=await self.connect(token)
        out=await other.call('town_in','town_room',map='iso-town-v1',x=70,y=44)
        self.assertEqual((out['x'],out['y']),(6,8))

    async def test_wave_notice_is_in_game_and_scheduled_with_no_players(self):
        feature=self.app.by_name['treasure']
        await feature.tick(time.time())
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM town_treasure_waves').fetchone()[0],1)
        c,_,_=await self.enter()
        await feature.refresh(broadcast=True)
        notice=await c.expect('town_treasure')
        self.assertTrue(3 <= len(notice['chests']) <= 5)
        self.assertEqual(notice['wave']['reward'],10000)
