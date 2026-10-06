"""WP2 (06/10) with PostgreSQL: paid 5★ player reviews are weighed (never deleted), the admin chat's safety queue,
mutes of N minutes, 🐢 slow mode, the list of offending names with its one-click safe rename, and the live chat's
safety notice flag, "An toàn / trẻ vị thành niên" reports and per-player slow mode."""
import tempfile
import time
import unittest
from pathlib import Path

from game import accounts, live_chat, pg_schema, push, social
from game.storage import Store
from tests.live_support import LiveCase, needs_ws
from tests.pg_support import columns, pg_only
from tests.test_social import Player

DAY = 86400


def age(store, player, days):
    with store.connect() as db:
        db.execute('UPDATE profiles SET created=? WHERE pid=?', (time.time() - days * DAY, player.pid))


@pg_only
class PaidReviews(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)
        push.ensure(self.store)
        self.owner = Player(self.store, 'Chủ Quán')
        self.fan, self.paid, self.fresh = Player(self.store, 'Khách Quen'), Player(self.store, 'Được Quà'), Player(self.store, 'Mới Toanh')
        for p in (self.owner, self.fan, self.paid):
            age(self.store, p, 30)

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def review(self, p, stars, text, at=None, day=None):
        p.get('shop', pid=self.owner.pid)            # the visit
        if at is None:
            p.post('review', pid=self.owner.pid, stars=stars, text=text)
            return
        with self.store.connect() as db:
            db.execute('INSERT INTO previews(from_pid,to_pid,career,day,stars,text,at) VALUES(?,?,?,?,?,?,?)',
                       (p.pid, self.owner.pid, 'restaurant', day, stars, text, at))

    def test_latest_per_reviewer_age_and_gifts(self):
        self.review(self.fan, 1, 'Hôm trước dở', at=time.time() - 3 * DAY, day='2026-01-01')
        self.review(self.fan, 4, 'Nay ngon hơn rồi')
        with self.store.connect() as db:            # xu from the owner a few hours before the 5★
            db.execute('INSERT INTO gifts(from_pid,to_pid,sticker,coins,note,day,at) VALUES(?,?,?,?,?,?,?)',
                       (self.owner.pid, self.paid.pid, '🌸', 20, '', social.today(), time.time() - 3600))
        self.review(self.paid, 5, 'Đỉnh nóc kịch trần')
        self.review(self.fresh, 5, 'Năm sao nha')    # a profile made today
        shop = self.fan.get('shop', pid=self.owner.pid)
        self.assertEqual(shop['rating'], 4.0)          # only the fan's newest review counts
        self.assertEqual(len(shop['reviews']), 4)      # nothing deleted
        why = {r['text']: r for r in shop['reviews']}
        self.assertFalse(why['Hôm trước dở']['counted'])
        self.assertEqual(why['Hôm trước dở']['why'], social.REVIEW_WHY['older'])   # the reviewer sees why
        self.assertNotIn('counted', why['Nay ngon hơn rồi'])
        self.assertFalse(why['Đỉnh nóc kịch trần']['counted'])
        self.assertNotIn('why', why['Đỉnh nóc kịch trần'])  # a stranger does not learn about the transfer
        own = {r['text']: r for r in self.owner.get('shop', pid=self.owner.pid)['reviews']}
        self.assertEqual(own['Đỉnh nóc kịch trần']['why'], social.REVIEW_WHY['paid'])
        self.assertEqual(own['Năm sao nha']['why'], social.REVIEW_WHY['new_account'])

    def test_bank_transfer_counts_as_paid(self):
        with self.store.connect() as db:
            db.execute("INSERT INTO bank_xfers(id,code,sender,receiver,from_name,to_name,amount,note,src,status,day,at) "
                       "VALUES('x1','C1',?,?,'a','b',300,'','bank','done',?,?)",
                       (self.store.key(self.owner.token), self.store.key(self.paid.token), social.today(), time.time() - 600))
        self.review(self.paid, 5, 'Tuyệt vời')
        self.assertIsNone(self.fan.get('shop', pid=self.owner.pid)['rating'])

    def test_profile_name_blocklist(self):
        p = Player(self.store)
        for bad in ('concac', 'Sục cháy chim', 'dcm'):
            with self.assertRaises(social.SocialError):
                p.post('profile', name=bad)


@pg_only
class AdminTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def msg(self, db, pid, text, reports=0):
        return db.execute('INSERT INTO chat_messages(channel, pid, name, av, text, at, reports) VALUES(?,?,?,?,?,?,?) RETURNING id',
                          ('town', pid, 'Ai đó', '🌸', text, time.time(), reports)).fetchone()[0]

    def test_schema(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 24)
        self.assertIn('chat_slow', pg_schema.TABLE)
        with self.store.connect() as db:
            self.assertEqual(columns(db, 'chat_slow'), {'pid', 'every', 'until', 'by_admin', 'at'})

    def test_safety_reports_come_first_and_highlighted(self):
        with self.store.connect() as db:
            safety = self.msg(db, 'a' * 16, 'em mấy tuổi, nhà ở đâu', reports=1)
            spam = [self.msg(db, 'b' * 16, f'spam {i}', reports=1) for i in range(3)]
            db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'chat', ?, 'minor', ?)", ('c' * 16, str(safety), time.time()))
            for m in spam:
                db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'chat', ?, 'spam', ?)", ('c' * 16, str(m), time.time()))
        v = live_chat.view(self.store)
        self.assertEqual(v['items'][0]['id'], safety)
        self.assertTrue(v['items'][0]['safety'])
        self.assertFalse(any(x['safety'] for x in v['items'][1:]))
        self.assertEqual(v['counts']['safety'], 1)
        with self.store.connect() as db:            # nothing was hidden or muted by itself
            self.assertEqual(db.execute('SELECT hidden FROM chat_messages WHERE id=?', (safety,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_mutes').fetchone()[0], 0)
        live_chat.act(self.store, 'adm', dict(op='keep', id=safety))
        self.assertEqual(live_chat.view(self.store)['counts']['safety'], 0)

    def test_mute_minutes_and_slow_mode(self):
        pid = 'd' * 16
        out = live_chat.act(self.store, 'adm', dict(op='mute', pid=pid, minutes=10))
        self.assertAlmostEqual(out['until'], time.time() + 600, delta=5)
        with self.assertRaises(live_chat.ChatAdminError):
            live_chat.act(self.store, 'adm', dict(op='mute', pid=pid, minutes=7))
        live_chat.act(self.store, 'adm', dict(op='mute', pid=pid, hours=24))   # the old buttons still work
        live_chat.act(self.store, 'adm', dict(op='slow', pid=pid, seconds=60, minutes=60))
        live_chat.act(self.store, 'adm', dict(op='slow', pid='town', seconds=30, minutes=60))
        v = live_chat.view(self.store)
        self.assertEqual({x['pid']: x['every'] for x in v['slows']}, {pid: 60.0, 'town': 30.0})
        with self.assertRaises(live_chat.ChatAdminError):
            live_chat.act(self.store, 'adm', dict(op='slow', pid=pid, seconds=5, minutes=60))
        live_chat.act(self.store, 'adm', dict(op='unslow', pid=pid))
        self.assertEqual([x['pid'] for x in live_chat.view(self.store)['slows']], ['town'])

    def test_offending_names_listed_then_renamed_safely(self):
        token, _, _ = self.store.session(None)
        out = accounts.register(self.store, token, dict(username='be.na', password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Bé Na'))
        sid = self.store.resolve(out['token'])[0]
        ok_token, _, _ = self.store.session(None)
        accounts.register(self.store, ok_token, dict(username='hoa.gio', password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Hoa Gió'))
        with self.store.connect() as db:            # a name from before the filter
            db.execute("UPDATE accounts SET display='con cặc lớn' WHERE sid=?", (sid,))
            uid = db.execute('SELECT uid FROM accounts WHERE sid=?', (sid,)).fetchone()[0]
        names = live_chat.view(self.store)['names']
        self.assertEqual([x['uid'] for x in names], [uid])
        self.assertNotIn('sid', names[0])
        with self.store.connect() as db:            # listing renames nobody
            self.assertEqual(db.execute('SELECT display FROM accounts WHERE uid=?', (uid,)).fetchone()[0], 'con cặc lớn')
        money = self.store.read(out['token'])[0]['careers']
        live_chat.act(self.store, 'adm', dict(op='rename', uid=uid))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT display FROM accounts WHERE uid=?', (uid,)).fetchone()[0], f'Cư dân {uid}')
        state = self.store.read(out['token'])[0]
        self.assertEqual(state['name'], f'Cư dân {uid}')
        self.assertEqual(state['careers'], money)    # nothing else in the save moves
        self.assertEqual(live_chat.view(self.store)['names'], [])
        with self.assertRaises(live_chat.ChatAdminError):   # only listed names can be renamed this way
            live_chat.act(self.store, 'adm', dict(op='rename', uid=uid))


@pg_only
@needs_ws
class LiveSafety(LiveCase):
    async def test_safety_flag_only_to_the_sender(self):
        self.cfg.town_every = 0
        a = await self.connect(self.account('Mây Hồng')[0])
        b = await self.connect(self.account('Gió')[0])
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='cuối tuần hẹn gặp ngoài đời nha, nhà bạn ở đâu', cid='s1')
        mine = await a.expect('msg', cid='s1')
        self.assertEqual(mine.get('safety'), 1)
        got = await b.expect('msg')
        self.assertNotIn('safety', got)
        await a.send(t='send', ch='town', text='chào cả phố', cid='s2')
        self.assertNotIn('safety', await a.expect('msg', cid='s2'))
        await b.send(t='report', id=mine['id'], reason='minor')
        await b.expect('reported')
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT reason FROM reports WHERE kind='chat' AND target=?", (str(mine['id']),)).fetchone()[0], 'minor')
            self.assertEqual(db.execute('SELECT hidden FROM chat_messages WHERE id=?', (mine['id'],)).fetchone()[0], 0)

    async def test_mention_of_a_known_player_stays(self):
        self.cfg.town_every = 0
        a = await self.connect(self.account('LeeSerin')[0])
        b = await self.connect(self.account('Gió')[0])
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await b.send(t='send', ch='town', text='@LeeSerin ơi, @nguoila123 là ai', cid='m')
        self.assertEqual((await b.expect('msg', cid='m'))['text'], '@LeeSerin ơi, ••• là ai')

    async def test_admin_slow_mode_for_one_player(self):
        token, sid = self.account('Nhanh Tay')
        live_chat.act(self.store, 'adm', dict(op='slow', pid=self.pid(sid), seconds=120, minutes=60))
        a = await self.connect(token)
        await a.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='một', cid='1')
        self.assertEqual((await a.expect('msg', cid='1'))['wait'], 120)
        await a.send(t='send', ch='town', text='hai', cid='2')
        e = await a.expect('error', ref='2')
        self.assertEqual(e['code'], 'slow')
        self.assertGreater(e['wait'], 100)
        b = await self.connect(self.account('Bình Thường')[0])   # everyone else: the default
        await b.call('join', 'joined', ch='town')
        await b.send(t='send', ch='town', text='ba', cid='3')
        self.assertEqual((await b.expect('msg', cid='3'))['wait'], 10)


if __name__ == '__main__':
    unittest.main()
