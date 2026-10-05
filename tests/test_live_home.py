"""Shared-home live presence: real PostgreSQL and WebSocket authorization boundaries."""
import asyncio
import json
import time
import unittest
from unittest.mock import patch

from live.config import Config, from_env
from tests.live_support import LiveCase


class HomeCase(LiveCase):
    cfg_extra = dict(home=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ta, self.sa = self.account('An')
        self.tb, self.sb = self.account('Binh')
        with self.store.connect() as db:
            self.cid = db.execute("INSERT INTO couples(a,b,status,since) VALUES(?,?,'married',?) RETURNING id",
                                  (self.sa, self.sb, time.time())).fetchone()[0]
            db.executemany('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', [(self.sa, self.cid), (self.sb, self.cid)])
        self.states = {
            self.sa: {'journey': {'story': True, 'home': {'own': {'id': 'h1', 'kind': 'tap_the'}, 'shared': None, 'rent': None}}},
            self.sb: {'journey': {'story': True, 'home': {'own': None, 'shared': {'id': 'h1', 'kind': 'tap_the', 'couple': self.cid}, 'rent': None}}},
        }
        self.save()

    def save(self):
        with self.store.connect() as db:
            for sid, state in self.states.items():
                db.execute('UPDATE sessions SET state=?,revision=revision+1 WHERE sid=?', (json.dumps(state), sid))

    def sql(self, query, args=()):
        with self.store.connect() as db:
            db.execute(query, args)

    async def join(self, token=None, r='living'):
        c = await self.connect(token or self.ta)
        await c.send(t='home_in', r=r, x=.2, y=.8, g='female')
        c.room = await c.expect('home_room')
        c.pid = c.welcome['me']['pid']
        return c

    async def event(self, c, kind):
        f = await c.expect('home')
        self.assertEqual(len(f['ev']), 1)
        self.assertEqual(f['ev'][0]['k'], kind)
        return f['ev'][0]

    def clear(self, *clients):
        for c in clients:
            c.frames.clear()


class Rooms(HomeCase):
    async def test_alone_then_spouse_share_canonical_room_without_private_ids(self):
        a = await self.join()
        self.assertEqual(a.room['people'], [])
        b = await self.join(self.tb)
        self.assertEqual(a.room['room'], b.room['room'])
        self.assertEqual((b.room['r'], b.room['cap']), ('living', 12))
        self.assertEqual(b.room['people'][0]['pid'], a.pid)
        self.assertEqual((await self.event(a, 'in'))['pid'], b.pid)
        for sid in (self.sa, self.sb):
            self.assertNotIn(sid, json.dumps([a.room, b.room]))

    async def test_move_and_all_affection_types_only_reach_shared_room(self):
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        await a.send(t='home_mv', p=[[.2, .8], [2, -1]], ms=9999)
        move = await self.event(b, 'mv')
        self.assertEqual(move, dict(k='mv', pid=a.pid, p=[[.2, .8], [1.0, 0.0]], ms=3000))
        await self.event(a, 'mv')
        await a.send(t='home_mv',p=[[1.,0.],[.21,.8]],ms=0)
        await self.event(a,'mv');await self.event(b,'mv')
        for kind in ('hug', 'kiss', 'heart'):
            await a.send(t='home_emote', kind=kind, to=b.pid)
            event = await self.event(b, 'emote')
            self.assertEqual({k:event[k] for k in ('k','pid','to','kind')}, dict(k='emote', pid=a.pid, to=b.pid, kind=kind))
            await self.event(a, 'emote')
            await b.send(t='home_reply',id=event['id'],answer='decline')
            await self.event(a,'ended');await self.event(b,'ended')

    async def test_physical_rooms_are_isolated(self):
        a = await self.join()
        b = await self.join(self.tb, 'bed')
        self.assertNotEqual(a.room['room'], b.room['room'])
        self.assertEqual(b.room['people'], [])
        await a.send(t='home_emote', kind='hug', to=b.pid)
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        await b.nothing('home')

    async def test_stranger_cannot_pick_another_home(self):
        a = await self.join()
        token, _ = self.account('Stranger')
        c = await self.connect(token)
        await c.send(t='home_in', r='living', room=a.room['room'], sid=self.sa, couple=self.cid)
        self.assertEqual((await c.expect('error'))['code'], 'no_home')
        await a.nothing('home')

    async def test_invalid_room_and_nonfinite_point_are_rejected(self):
        a = await self.connect(self.ta)
        await a.send(t='home_in', r='not_a_room')
        self.assertEqual((await a.expect('error'))['code'], 'bad')
        for pt in ([True, 0], [0, '1'], [0], [None, 0]):
            await a.send(t='home_in', r='living', x=pt[0], y=pt[1] if len(pt) > 1 else None)
            self.assertEqual((await a.expect('error'))['code'], 'bad')

    async def test_takeover_old_tab_out_and_close_do_not_remove_new_tab(self):
        old = await self.join()
        b = await self.join(self.tb)
        await self.event(old, 'in')
        new = await self.join()
        self.assertEqual((await old.expect('home_left'))['why'], 'other')
        await self.event(b, 'out')
        await self.event(b, 'in')
        await old.call('home_out', 'home_left')
        await old.close()
        await b.nothing('home')
        await new.send(t='home_emote', kind='heart', to=b.pid)
        self.assertEqual((await self.event(b, 'emote'))['pid'], new.pid)

    async def test_leave_and_disconnect_drop_empty_rooms(self):
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        await b.call('home_out', 'home_left')
        self.assertEqual((await self.event(a, 'out'))['pid'], b.pid)
        await a.close()
        await asyncio.sleep(.05)
        self.assertFalse([k for k in self.app.hub.rooms if k.startswith('home:')])

    async def test_divorce_rejects_next_move_and_revokes_idle_partner(self):
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        self.sql("UPDATE couples SET status='divorced' WHERE id=?", (self.cid,))
        await a.send(t='home_mv', p=[[.2, .8], [.5, .5]], ms=500)
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        self.assertEqual((await a.expect('home_left'))['why'], 'changed')
        self.assertEqual((await b.expect('home_left', timeout=4))['why'], 'changed')
        await b.nothing('home', wait=.05)

    async def test_idle_move_apart_revokes(self):
        a = await self.join()
        self.states[self.sb]['journey']['home']['shared'] = None
        self.save()
        self.assertEqual((await a.expect('home_left', timeout=4))['why'], 'changed')

    async def test_missing_second_bond_and_mismatched_shared_home_deny(self):
        # The spouse needs valid shared access. The homeowner's own property
        # remains independently available for a fresh owner-mode entry.
        a = await self.connect(self.tb)
        self.states[self.sb]['journey']['home']['shared']['id'] = 'h2'
        self.save()
        await a.send(t='home_in', r='living')
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        self.states[self.sb]['journey']['home']['shared']['id'] = 'h1'
        self.save()
        self.sql('DELETE FROM marriage_bonds WHERE sid=?', (self.sb,))
        await a.send(t='home_in', r='living')
        self.assertEqual((await a.expect('error'))['code'], 'no_home')

    async def test_each_block_table_and_direction_prevents_entry(self):
        a = await self.connect(self.tb)
        for table, left, right, x, y in (
            ('blocks', 'pid', 'target', self.pid(self.sa), self.pid(self.sb)),
            ('blocks', 'pid', 'target', self.pid(self.sb), self.pid(self.sa)),
            ('marriage_blocks', 'sid', 'target', self.sa, self.sb),
            ('marriage_blocks', 'sid', 'target', self.sb, self.sa),
        ):
            self.sql(f'INSERT INTO {table}({left},{right},at) VALUES(?,?,?)', (x, y, time.time()))
            await a.send(t='home_in', r='living')
            self.assertEqual((await a.expect('error'))['code'], 'no_home')
            self.sql(f'DELETE FROM {table} WHERE {left}=? AND {right}=?', (x, y))

    async def test_live_block_prevents_emote_before_periodic_refresh(self):
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        self.sql('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (self.sb, self.sa, time.time()))
        await a.send(t='home_emote', kind='kiss', to=b.pid)
        self.assertEqual((await a.expect('error'))['code'], 'no_home')
        await b.nothing('home', wait=.05)

    async def test_emote_validation_and_player_rate_limit(self):
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        for to, kind in ((a.pid, 'hug'), (b.pid, '<script>')):
            await a.send(t='home_emote', kind=kind, to=to)
            self.assertIn((await a.expect('error'))['code'], ('bad', 'no_home'))
        for _ in range(4):
            await a.send(t='home_emote', kind='heart', to=b.pid)
            e=await self.event(a, 'emote')
            await self.event(b, 'emote')
            await b.send(t='home_reply',id=e['id'],answer='decline')
            await self.event(a,'ended');await self.event(b,'ended')
        await a.send(t='home_emote', kind='heart', to=b.pid)
        self.assertEqual((await a.expect('error'))['code'], 'slow')

    async def test_notify_only_authenticated_actor_and_current_shared_spouse(self):
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        token, _ = self.account('Stranger')
        c = await self.connect(token)
        await self.app.on_notify(json.dumps(dict(t='home_changed', sid=self.sa)))
        self.assertEqual(await a.expect('home_changed'), dict(t='home_changed'))
        self.assertEqual(await b.expect('home_changed'), dict(t='home_changed'))
        await c.nothing('home_changed', wait=.05)
        self.sql("UPDATE couples SET status='divorced' WHERE id=?", (self.cid,))
        await self.app.on_notify(json.dumps(dict(t='home_changed', sid=self.sa)))
        await a.expect('home_changed')
        await b.nothing('home_changed', wait=.05)

    async def test_pg_notify_reaches_spouse_when_actor_is_offline(self):
        b = await self.connect(self.tb)
        self.sql("SELECT pg_notify('mnl_live',?)", (json.dumps(dict(t='home_changed', sid=self.sa)),))
        self.assertEqual(await b.expect('home_changed'), dict(t='home_changed'))

    async def test_database_failure_revokes_instead_of_forwarding(self):
        from live.db import Error
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        with patch.object(self.app.db, 'fetchrow', side_effect=Error[0]('temporary unavailable')):
            await a.send(t='home_emote', kind='hug', to=b.pid)
            self.assertEqual((await a.expect('error'))['code'], 'busy')
        await a.expect('home_left', why='changed')
        await b.expect('home_left', why='changed')
        await b.nothing('home', wait=.05)

    async def test_move_query_finishing_after_takeover_cannot_mutate_new_presence(self):
        from live.home import PAIR_SQL
        a = await self.join()
        b = await self.join(self.tb)
        await self.event(a, 'in')
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.app.db.fetchrow
        once = True

        async def delayed(sql, args=()):
            nonlocal once
            row = await original(sql, args)
            if once and sql == PAIR_SQL and args == (self.sa,):
                once = False
                entered.set()
                await release.wait()
            return row

        with patch.object(self.app.db, 'fetchrow', side_effect=delayed):
            await a.send(t='home_mv', p=[[.2, .8], [.9, .9]], ms=500)
            await asyncio.wait_for(entered.wait(), 2)
            new = await self.join()
            await a.expect('home_left', why='other')
            await self.event(b, 'out')
            await self.event(b, 'in')
            release.set()
            self.assertEqual((await a.expect('error'))['code'], 'no_home')
        await b.nothing('home', wait=.05)
        room = self.app.hub.rooms[new.room['room']]
        self.assertEqual(room.data['people'][new.pid]['x'], .2)

    async def test_switch_off_refuses_frames_without_creating_rooms(self):
        self.cfg.home = False
        a = await self.connect(self.ta)
        self.assertFalse(a.welcome['flags']['home'])
        await a.send(t='home_in', r='living')
        self.assertEqual((await a.expect('error'))['code'], 'off')
        self.assertFalse([k for k in self.app.hub.rooms if k.startswith('home:')])


class Reactions(HomeCase):
    async def pair(self):
        a=await self.join();b=await self.join(self.tb)
        await self.event(a,'in')
        return a,b

    async def offer(self,a,b,kind='kiss'):
        await a.send(t='home_emote',kind=kind,to=b.pid)
        received=await b.expect('home')
        self.assertEqual(received['room'],b.room['room'])
        e=received['ev'][0]
        self.assertEqual(e['k'],'emote');self.assertEqual(e['ttl'],15)
        self.assertTrue(e['id'])
        self.assertEqual((await self.event(a,'emote'))['id'],e['id'])
        return e

    async def test_only_recipient_responds_once_and_both_see_same_reaction(self):
        a,b=await self.pair();e=await self.offer(a,b)
        await a.send(t='home_reply',id=e['id'],answer='accept')
        self.assertEqual((await a.expect('error'))['code'],'not_yours')
        await b.send(t='home_reply',id=e['id'],answer='accept')
        x=await self.event(a,'reaction');self.assertEqual(x,await self.event(b,'reaction'))
        self.assertEqual(x,dict(k='reaction',id=e['id'],pid=b.pid,to=a.pid,kind='kiss',answer='accept'))
        await b.send(t='home_reply',id=e['id'],answer='accept')
        self.assertEqual((await b.expect('error'))['code'],'stale')
        await a.nothing('home',wait=.05)

    async def test_shy_sulk_and_decline_are_explicit_recipient_choices(self):
        a,b=await self.pair()
        for answer in ('shy','sulk','decline'):
            e=await self.offer(a,b,'hug')
            await b.send(t='home_reply',id=e['id'],answer=answer)
            k='ended' if answer=='decline' else 'reaction'
            x=await self.event(a,k);self.assertEqual(x,await self.event(b,k))
            self.assertEqual(x.get('answer',x.get('why')),answer if answer!='decline' else 'declined')

    async def test_offer_expires_and_never_auto_reciprocates(self):
        a,b=await self.pair();e=await self.offer(a,b)
        room=self.app.hub.rooms[a.room['room']];room.data['offer']['until']=time.time()-1
        await next(f for f in self.app.features if f.name=='home').tick(time.time())
        await b.send(t='home_reply',id=e['id'],answer='accept')
        self.assertEqual((await b.expect('error'))['code'],'stale')
        self.assertEqual((await self.event(a,'ended'))['why'],'expired')
        self.assertEqual((await self.event(b,'ended'))['why'],'expired')

    async def test_walk_cancels_offer_and_far_apart_cannot_start(self):
        a,b=await self.pair();e=await self.offer(a,b)
        await b.send(t='home_mv',p=[[.2,.8],[.9,.1]],ms=500)
        self.assertEqual((await self.event(a,'ended'))['why'],'moved')
        await self.event(a,'mv');await self.event(b,'ended');await self.event(b,'mv')
        await a.send(t='home_emote',kind='hug',to=b.pid)
        self.assertEqual((await a.expect('error'))['code'],'too_far')
        await b.send(t='home_reply',id=e['id'],answer='sulk')
        self.assertEqual((await b.expect('error'))['code'],'stale')

    async def test_pending_offer_is_not_replaced_and_sender_can_cancel(self):
        a,b=await self.pair();e=await self.offer(a,b)
        await b.send(t='home_emote',kind='heart',to=a.pid)
        self.assertEqual((await b.expect('error'))['code'],'busy')
        await b.send(t='home_reply',id=e['id'],answer='cancel')
        self.assertEqual((await b.expect('error'))['code'],'not_yours')
        await a.send(t='home_reply',id=e['id'],answer='cancel')
        self.assertEqual((await self.event(a,'ended'))['why'],'cancelled')
        await self.event(b,'ended')

    async def test_reply_after_divorce_revokes_both_and_never_plays_reaction(self):
        a,b=await self.pair();e=await self.offer(a,b)
        self.sql("UPDATE couples SET status='divorced' WHERE id=?",(self.cid,))
        await b.send(t='home_reply',id=e['id'],answer='accept')
        self.assertEqual((await b.expect('error'))['code'],'no_home')
        await a.expect('home_left');await b.expect('home_left')
        await a.nothing('home',wait=.05)

    async def test_changing_room_cancels_offer_and_old_id_is_not_reusable(self):
        a,b=await self.pair();e=await self.offer(a,b)
        await b.send(t='home_in',r='bed',x=.2,y=.8)
        await b.expect('home_room')
        self.assertEqual((await self.event(a,'ended'))['why'],'left')
        await self.event(a,'out')
        await b.send(t='home_reply',id=e['id'],answer='accept')
        self.assertEqual((await b.expect('error'))['code'],'stale')


class Switch(unittest.TestCase):
    def test_home_is_advertised_and_can_run_alone(self):
        self.assertTrue(Config(home=True).any_on())
        self.assertTrue(Config(home=True).flags()['home'])
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://config@127.0.0.1/fixture', 'LIVE_STREET': '1'}, clear=True):
            self.assertTrue(from_env([]).home)
            with patch.dict('os.environ', {'LIVE_HOME': '0'}):
                self.assertFalse(from_env([]).home)
