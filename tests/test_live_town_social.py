"""Real sockets: proximity and moderation must be enforced by the server."""
import asyncio
import time

from live.town import MAP_ID
from tests.live_support import LiveCase


class TownSocialSockets(LiveCase):
    cfg_extra = dict(town=True)

    async def enter(self, name, x=6, y=6, guest=False):
        token, _ = self.guest(name) if guest else self.account(name)
        c = await self.connect(token)
        c.room = await c.call('town_in', 'town_room', map=MAP_ID, x=x, y=y)
        c.pid = c.room['me']
        return c

    async def test_nearby_speech_reaction_and_recall(self):
        a, b, far = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Xa', y=49)
        await a.send(t='town_say', text='Chào cả nhà', cid='say-one')
        own = await a.expect('town_said')
        heard = await b.expect('town_said')
        self.assertEqual((heard['text'], heard['pid']), ('Chào cả nhà', a.pid))
        self.assertEqual(own['cid'], 'say-one')
        self.assertEqual(heard['id'], own['id'])
        await asyncio.sleep(.1)
        self.assertFalse(any(f['t'] == 'town_said' for f in far.frames))
        await far.send(t='history', ch=heard['ch'])
        self.assertEqual((await far.expect('error', ref='history'))['code'], 'no_chat')
        await b.send(t='react', id=heard['id'], e='❤️')
        self.assertEqual((await a.expect('reacts'))['r'], {'❤️': 1})
        await a.send(t='del', id=heard['id'])
        self.assertEqual((await b.expect('deleted'))['id'], heard['id'])

    async def test_emote_targets_block_distance_and_activity(self):
        a, b, far = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Xa', y=49)
        await a.send(t='town_emote', e='👋', target=b.pid, cid='wave')
        frame = await b.expect('town_emoted')
        self.assertEqual((frame['pid'], frame['target']), (a.pid, b.pid))
        await a.expect('town_emoted')
        await a.send(t='town_emote', e='❤️', target=far.pid)
        self.assertEqual((await a.expect('error', ref='town_emote'))['code'], 'gone')
        p = self.app.hub.players[b.pid]
        p.hidden.add(a.pid)
        await a.send(t='town_emote', e='❤️', target=b.pid)
        self.assertEqual((await a.expect('error', ref='town_emote'))['code'], 'gone')
        p.hidden.clear()
        room = self.app.hub.rooms[a.room['room']]
        room.data['people'][b.pid].activity = dict(kind='fishing')
        await a.send(t='town_card', pid=b.pid)
        self.assertEqual((await a.expect('error', ref='town_card'))['code'], 'gone')

    async def test_guest_mute_invalid_and_left_room_cannot_speak(self):
        guest = await self.enter('Guest', guest=True)
        await guest.send(t='town_say', text='hello')
        self.assertEqual((await guest.expect('error', ref='town_say'))['code'], 'account')
        a = await self.enter('Lan')
        self.app.hub.players[a.pid].muted_until = time.time() + 100
        await a.send(t='town_emote', e='❤️')
        self.assertEqual((await a.expect('error', ref='town_emote'))['code'], 'muted')
        self.app.hub.players[a.pid].muted_until = 0
        await a.send(t='town_emote', e=['❤️'])
        self.assertEqual((await a.expect('error', ref='town_emote'))['code'], 'bad')
        await a.call('town_out', 'town_left')
        await a.send(t='town_say', text='hello')
        self.assertEqual((await a.expect('error', ref='town_say'))['code'], 'not_in')

    async def test_emote_obeys_database_mute_without_notify(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_mutes(pid, until, reason, at) VALUES(?,?,?,?)',
                       (a.pid, time.time()+60, 'test', time.time()))
        await a.send(t='town_emote', e='❤️')
        self.assertEqual((await a.expect('error', ref='town_emote'))['code'], 'muted')
        await asyncio.sleep(.1)
        self.assertFalse(any(f['t'] == 'town_emoted' for f in b.frames))

    async def test_speech_filters_and_rate_limit_and_report(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        await a.send(t='town_say', text='Gọi số 0912345678', name='Spoof', pid=b.pid)
        heard = await b.expect('town_said')
        await a.expect('town_said')
        self.assertNotIn('0912345678', heard['text'])
        self.assertEqual((heard['pid'], heard['name']), (a.pid, 'Lan'))
        await b.send(t='report', id=heard['id'], reason='spam')
        await b.expect('reported')
        for i in range(2):
            await a.send(t='town_say', text=f'Chào {i}')
            await a.expect('town_said')
        await a.send(t='town_say', text='Thêm nữa')
        self.assertEqual((await a.expect('error', ref='town_say'))['code'], 'slow')

    async def test_blocks_and_expired_receipts_deny_old_message_access(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        await a.send(t='town_say', text='Xin chào')
        heard = await b.expect('town_said')
        await a.expect('town_said')
        await b.send(t='block', pid=a.pid)
        await b.expect('blocked')
        await b.send(t='history', ch=heard['ch'])
        self.assertEqual((await b.expect('error', ref='history'))['code'], 'no_chat')
        await a.send(t='town_say', text='Không gửi cho người đã chặn')
        await a.expect('town_said')
        await asyncio.sleep(.1)
        self.assertFalse(any(f['t'] == 'town_said' for f in b.frames))
        self.app.by_name['town'].social_receipts[heard['ch']].until = 0
        await a.send(t='history', ch=heard['ch'])
        self.assertEqual((await a.expect('error', ref='history'))['code'], 'no_chat')
