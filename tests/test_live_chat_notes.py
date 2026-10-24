"""💭 Ghi chú trạng thái (live/notes.py, feedback #170): a one-line note over the avatar for 24 h, set and cleared from
the chat screen; friends see it in their list and live, the filter masks it, reports hide it, a player who hides
their online status shows it to friends only, and it rides on the player cards."""
import time

from live import notes
from tests.live_support import LiveCase

PHONE = '0912 345 678'


class NoteTests(LiveCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ta, self.sa = self.account('Lan Anh')
        self.tb, self.sb = self.account('Minh Tú')
        self.pa, self.pb = self.pid(self.sa), self.pid(self.sb)

    def row(self, pid):
        with self.store.connect() as db:
            r = db.execute('SELECT text, raw, hidden, reports, pub FROM chat_notes WHERE pid=?', (pid,)).fetchone()
        return tuple(r) if r else None

    async def test_set_seen_by_friends_live_and_cleared(self):
        self.befriend(self.sa, self.sb)
        a, b = await self.connect(self.ta), await self.connect(self.tb)
        self.assertIsNone(a.welcome['me']['nt'])                       # this service has notes, none yet
        f = await a.call('note', 'noted', text='  Đang ôn thi,   nhắn sau nha 📚 ')
        self.assertEqual((f['pid'], f['nt']['t']), (self.pa, 'Đang ôn thi, nhắn sau nha 📚'))
        g = await b.expect('noted', pid=self.pa)                       # my friend hears it at once
        self.assertEqual(g['nt']['t'], f['nt']['t'])
        self.assertEqual(self.row(self.pa)[:3], ('Đang ôn thi, nhắn sau nha 📚', None, 0))
        # a new connection: in my `me` and in the friend's list
        a2, b2 = await self.connect(self.ta), await self.connect(self.tb)
        self.assertEqual(a2.welcome['me']['nt']['t'], f['nt']['t'])
        friend = next(x for x in b2.welcome['friends'] if x['pid'] == self.pa)
        self.assertEqual(friend['nt']['t'], f['nt']['t'])
        await a.send(t='note', text='')
        self.assertIsNone((await a.expect('noted', pid=self.pa))['nt'])
        self.assertIsNone((await b.expect('noted', pid=self.pa))['nt'])
        self.assertIsNone((await a2.expect('noted', pid=self.pa))['nt'])   # my other tab too
        self.assertIsNone(self.row(self.pa))
        b3 = await self.connect(self.tb)
        self.assertNotIn('nt', next(x for x in b3.welcome['friends'] if x['pid'] == self.pa))

    async def test_filter_length_and_who_may_write(self):
        a = await self.connect(self.ta)
        f = await a.call('note', 'noted', text=f'gọi {PHONE} nhé')
        self.assertNotIn(PHONE, f['nt']['t'])
        text, raw = self.row(self.pa)[:2]
        self.assertNotIn(PHONE, text)
        self.assertIn(PHONE, raw)                                      # what was typed: admin only
        self.assertEqual((await a.call('note', 'noted', text='một\nhai'))['nt']['t'], 'một hai')   # always one line
        for cid, text in (('long', 'x' * (notes.LEN + 1)), ('blank', '   '), ('type', 5)):
            await a.send(t='note', text=text, cid=cid)
            self.assertEqual((await a.expect('error', ref=cid))['code'], 'text')
        g = await self.connect(self.guest('Khách')[0])
        await g.send(t='note', text='chào', cid='g')
        self.assertEqual((await g.expect('error', ref='g'))['code'], 'account')

    async def test_hidden_player_shows_it_to_friends_only_and_cards(self):
        tc, sc = self.account('Người Lạ')
        self.befriend(self.sa, self.sb)
        a = await self.connect(self.ta)
        await a.call('note', 'noted', text='Ra hồ câu cá 🎣')
        b, c = await self.connect(self.tb), await self.connect(tc)
        nm = notes.of_app(self.app)
        pb, pc = self.app.hub.players[self.pb], self.app.hub.players[self.pid(sc)]
        self.assertEqual((await nm.one(pc, self.pa))['t'], 'Ra hồ câu cá 🎣')   # online and visible: anyone who meets me
        await a.send(t='prefs', online=False)
        await a.expect('prefs')
        self.assertEqual(self.row(self.pa)[4], 0)
        self.assertIsNone(await nm.one(pc, self.pa))                   # hidden: not to a stranger
        self.assertEqual((await nm.one(pb, self.pa))['t'], 'Ra hồ câu cá 🎣')   # still to a friend
        await a.send(t='prefs', online=True)
        await a.expect('prefs')
        self.assertEqual(self.row(self.pa)[4], 1)
        # a block hides it both ways
        await c.call('block', 'blocked', pid=self.pa)
        self.assertIsNone(await nm.one(pc, self.pa))

    async def test_reports_hide_it_until_a_new_note(self):
        a = await self.connect(self.ta)
        await a.call('note', 'noted', text='bán acc giá rẻ')
        others = [await self.connect(self.account(f'Người {i}')[0]) for i in range(3)]
        for i, o in enumerate(others):
            f = await o.call('note_report', 'note_reported', pid=self.pa, reason='scam')
            self.assertEqual(f['pid'], self.pa)
        await others[0].call('note_report', 'note_reported', pid=self.pa, reason='scam')   # the same reporter twice: once
        self.assertEqual(self.row(self.pa)[2:4], (1, 3))
        self.assertIsNone((await a.expect('noted', pid=self.pa))['nt'])
        await others[2].expect('noted', pid=self.pa)                   # the one whose report hid it hears so
        viewer = self.app.hub.players[others[0].welcome['me']['pid']]
        self.assertIsNone(await notes.of_app(self.app).one(viewer, self.pa))
        await a.call('note', 'noted', text='Chào cả nhà')              # a new note starts clean
        self.assertEqual(self.row(self.pa)[2:4], (0, 0))
        await a.send(t='note_report', pid=self.pa, reason='scam', cid='me')
        self.assertEqual((await a.expect('error', ref='me'))['code'], 'bad')

    async def test_expires_after_a_day(self):
        a = await self.connect(self.ta)
        await a.call('note', 'noted', text='Hôm qua vui ghê')
        with self.store.connect() as db:
            db.execute('UPDATE chat_notes SET at=? WHERE pid=?', (time.time() - notes.TTL - 5, self.pa))
        nm = notes.of_app(self.app)
        nm.rows.pop(self.pa, None)
        self.assertIsNone(await nm.one(self.app.hub.players[self.pa], self.pa))
        nm._prune_at = 0
        self.assertEqual(await nm.prune(time.time()), 1)
        self.assertIsNone(self.row(self.pa))
        self.assertIsNone(notes.public(dict(text='x', at=time.time() - notes.TTL - 1, hidden=0)))
        self.assertEqual(notes.public(dict(text='x', at=time.time(), hidden=0))['t'], 'x')
        self.assertIsNone(notes.public(dict(text='x', at=time.time(), hidden=1)))
