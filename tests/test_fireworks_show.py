"""🎆 Pháo hoa cả phố as a real show (owner 08/10: "phải có bắn toàn server cho mọi người thấy chứ k phải là chỉ có chữ",
feedback #274 "bắn pháo hoa chỗ nào z?"): the purchase (game/lux.py) announces it with NOTIFY in its own transaction,
the live service (live/fireworks.py) sends it to every open page wherever the player is, without the name and the wish
to a player who blocked the giver (or was blocked), never a pid; a page that connects just after gets it in its
welcome. The optional wish is a fixed list, kept in the save as an id (an older build accepts it)."""
import copy
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import live_chat
from game import lux
from game import lux_content as C
from game.engine import GameError, validate_state
from live.app import NOTIFY_CHANNEL
from tests.live_support import HAVE_WS, LiveCase


class Purchase(unittest.TestCase):
    """game/lux.py: the wish, the NOTIFY and what a refused show does."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        lux._BOARD.clear()
        self.n = 0

    def player(self, name='Lan', wallet=2_000_000):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {self.store.key(token): fn})
        return token

    def cmd(self, token, action, **p):
        self.n += 1
        return self.store.command(token, f'fw-{self.n:08d}', self.store.read(token)[1], None, action, p)

    def test_show_is_announced_with_the_wish(self):
        a, b = self.player(), self.player(name='Minh')
        sid = self.store.key(a)
        a = secrets.token_hex(32)                                                    # Lan signs up: her account's name
        with self.store.connect() as db:
            db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES('lan', 'Lan Mây', 'x', ?)", (sid,))
            db.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'c')", (self.store.digest(a), sid))
        sent = []
        real = live_chat.notify
        with patch.object(live_chat, 'notify', side_effect=lambda db, e: (sent.append(e), real(db, e))):
            r = self.cmd(a, 'jr_lux_give', kind='phao_hoa', size='dai_tiec', msg='sinh_nhat', confirm=True)
            self.assertIn('Đại tiệc pháo hoa', r['result']['message'])
            shows = [e for e in sent if e.get('op') == 'fireworks']
            self.assertEqual(len(shows), 1)
            e = shows[0]
            self.assertEqual((e['size'], e['name'], e['wish'], e['pid']), ('dai_tiec', 'Lan Mây', 'Mừng sinh nhật', lux._pid(sid)))
            self.assertTrue(e['id'].startswith(lux._pid(sid) + ':'))
            self.assertNotIn(sid, json.dumps(e))                                       # never a sid
            # the save keeps the wish as an id (give.last.m), the ticker and Cả phố say it too
            s = self.store.read(a)[0]
            self.assertEqual(s['journey']['lux']['give']['last']['m'], 'sinh_nhat')
            validate_state(s)
            with self.store.connect() as db:
                news = [r['text'] for r in db.execute("SELECT text FROM news WHERE kind='lux'").fetchall()]
                chat = [r['text'] for r in db.execute("SELECT text FROM chat_messages WHERE channel='town'").fetchall()]
            self.assertTrue(any('Mừng sinh nhật' in t for t in news), news)
            self.assertTrue(any('Lan Mây' in t and 'đại tiệc pháo hoa' in t for t in chat), chat)
            # one show at a time on the street: refused, nothing paid, nothing shown
            sent.clear()
            with self.assertRaises(GameError) as cm:
                self.cmd(b, 'jr_lux_give', kind='phao_hoa', size='nho', confirm=True)
            self.assertEqual(cm.exception.code, 'busy')
            self.assertEqual(self.store.read(b)[0]['journey']['wallet'], 2_000_000)
            self.assertFalse([e for e in sent if e.get('op') == 'fireworks'])

    def test_wish_is_optional_and_from_the_list(self):
        a = self.player()
        with self.assertRaises(GameError):                                              # not a wish of the list
            self.cmd(a, 'jr_lux_give', kind='phao_hoa', size='nho', msg='free text here', confirm=True)
        with self.assertRaises(GameError):                                              # not even a string
            self.cmd(a, 'jr_lux_give', kind='phao_hoa', size='nho', msg=['me'], confirm=True)
        self.assertEqual(self.store.read(a)[0]['journey']['wallet'], 2_000_000)
        sent = []
        with patch.object(live_chat, 'notify', side_effect=lambda db, e: sent.append(e)):
            self.cmd(a, 'jr_lux_give', kind='phao_hoa', size='nho', anon=True, confirm=True)   # an older page: no msg
        e = next(e for e in sent if e.get('op') == 'fireworks')
        self.assertEqual((e['size'], e['wish'], e['name']), ('nho', '', lux.ANON_NAME))      # anonymous: no name
        self.assertEqual(self.store.read(a)[0]['journey']['lux']['give']['last']['m'], '')

    def test_wishes_are_ids_an_older_build_keeps(self):
        self.assertTrue(all(lux._id(k) and t for k, t in C.FW_WISHES))
        self.assertEqual(len({k for k, _ in C.FW_WISHES}), len(C.FW_WISHES))
        self.assertEqual([w['id'] for w in lux.catalogue()['fw_wishes']], [k for k, _ in C.FW_WISHES])
        # 1.9.20's check of give.last (unchanged): `m` is '' or an id
        last = dict(n=1, k='phao_hoa', z='lon', s=0, a=80000, m='nguoi_thuong', anon=False, wk='2026-W41', at=int(time.time()))
        self.assertTrue(lux._last_ok(copy.deepcopy(last)))


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class LiveShow(LiveCase):
    """live/fireworks.py: every open page, blocks, late arrivals, bad events."""

    def notify(self, event):
        with self.store.connect() as db:
            db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event)))

    def event(self, sid, n=1, **kw):
        return dict(dict(op='fireworks', id=f'{self.pid(sid)}:{n}', pid=self.pid(sid), size='lon', name='Lan',
                         wish='Mừng sinh nhật', at=time.time()), **kw)

    async def test_everyone_sees_it_blocked_players_without_the_name(self):
        (ta, sa), (tb, _sb), (tc, sc) = self.account('Lan'), self.account('Minh'), self.account('Hoa')
        with self.store.connect() as db:   # Hoa blocked Lan
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (self.pid(sc), self.pid(sa), time.time()))
        a, b, c = await self.connect(ta), await self.connect(tb), await self.connect(tc)
        self.assertNotIn('fw', b.welcome)                                    # nothing on yet
        self.notify(self.event(sa))
        fa, fb, fc = await a.expect('fireworks'), await b.expect('fireworks'), await c.expect('fireworks')
        self.assertEqual((fb['size'], fb['name'], fb['wish']), ('lon', 'Lan', 'Mừng sinh nhật'))
        self.assertEqual(fa['name'], 'Lan')                                  # the giver sees their own show
        self.assertEqual((fc['size'], fc['name'], fc['wish']), ('lon', '', ''))   # the sky, not who
        for f in (fa, fb, fc):
            self.assertEqual(f['id'], fb['id'])
            self.assertNotIn(self.pid(sa), json.dumps(f))                    # never the pid (an anonymous giver)
            self.assertNotIn(sa, json.dumps(f))
            self.assertLess(f['ago'], 5)
        # the same show again (a repeated NOTIFY) is dropped
        self.notify(self.event(sa))
        await b.nothing('fireworks', wait=.2)
        # a page that opens just after gets it in its welcome, blocks still apply
        late = await self.connect(tb)
        self.assertEqual((late.welcome['fw']['name'], late.welcome['fw']['id']), ('Lan', fb['id']))
        self.assertNotIn('t', late.welcome['fw'])
        late_c = await self.connect(tc)
        self.assertEqual(late_c.welcome['fw']['name'], '')
        # …but not long after
        self.app.by_name['fireworks'].last['seen'] -= 120
        self.assertNotIn('fw', (await self.connect(tb)).welcome)

    async def test_bad_events_are_dropped(self):
        (tb, _sb), (_ta, sa) = self.account('Minh'), self.account('Lan')
        b = await self.connect(tb)
        for bad in (dict(id='not an id'), dict(size='<b>'), dict(size=7), dict(id=None)):
            self.notify(self.event(sa, n=9, **bad))
        await b.nothing('fireworks', wait=.2)
        # long or odd names and wishes are cut and cleaned (the page escapes them too)
        self.notify(self.event(sa, n=10, name='x' * 80 + '‮', wish='y' * 90, pid='nope'))
        f = await b.expect('fireworks')
        self.assertEqual((len(f['name']), len(f['wish'])), (24, 40))
        self.assertTrue(b.welcome['flags'])


if __name__ == '__main__':
    unittest.main()
