"""🎤 Phòng hát end to end over real authenticated sockets on a disposable PostgreSQL schema (TEST_DATABASE_URL): the
game server's own song check (oEmbed mocked) and free first ticket, then two players in one room see the same song at
the same server second, and an emoji round is won and paid once. With LIVE_KARAOKE off the frames answer 'off' and
the welcome says so."""
import json
import time
from unittest.mock import patch

from game import karaoke as kg
from tests.live_support import LiveCase

VID = 'dQw4w9WgXcQ'


class KaraokeSockets(LiveCase):
    cfg_extra = dict(kara=True)

    async def test_two_players_one_song_one_clock_and_a_round(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        a, b = await self.connect(ta), await self.connect(tb)
        self.assertTrue(a.welcome['flags']['kara'])
        ra = await a.call('kara_in', 'kara_room', theme='qt')
        rb = await b.call('kara_in', 'kara_room', id=ra['id'])
        self.assertEqual((ra['id'], rb['id'], rb['n']), ('kara:qt', 'kara:qt', 2))
        with patch.object(kg, '_http_get', return_value=(200, json.dumps(dict(title='Never Gonna Give You Up', author_name='Rick')).encode())):
            song = kg.check_song(self.store, f'https://youtu.be/{VID}')
        self.assertTrue(song['ok'])
        self.assertTrue((await a.call('kara_can', 'kara_can'))['ok'])
        ticket = kg.queue(self.store, ta, dict(rid='sock-rid-0001'))
        self.assertEqual(ticket['price'], 0)                                # the first song of the day
        await a.send(t='kara_add', vid=VID, e=ticket['e'])
        pa, pb = await a.expect('kara_play'), await b.expect('kara_play')
        self.assertEqual((pa['vid'], pa['at'], pa['e']), (pb['vid'], pb['at'], pb['e']))
        self.assertGreater(pa['at'], time.time())                          # a lead to load, then everyone starts at once
        clocks = [await c.call('kara_time', 'kara_time', c=i) for i, c in enumerate((a, b))]
        self.assertLess(abs(clocks[0]['at'] - clocks[1]['at']), 1)
        await b.send(t='kara_round', mode='emoji', clue='🎤🕺🎶', answer='Never gonna give you up')
        rd = (await a.expect('kara_round'))['round']
        self.assertEqual(rd['words'], 5)
        with patch('live.karaoke.GUESS_MIN_SECS', 0):
            await a.send(t='kara_say', text='never gonna give u up')            # a small typo still counts
            rv = await b.expect('kara_reveal')
        self.assertEqual((rv['by']['name'], rv['xu']), ('Lan', kg.GUESS_XU))
        await a.expect('kara_won')
        with self.store.connect() as db:
            rows = db.execute("SELECT sid, amount, status FROM live_effects WHERE id LIKE 'kguess:%'").fetchall()
        self.assertEqual([(r['sid'], r['amount'], r['status']) for r in rows], [(sa, kg.GUESS_XU, 'pending')])

    async def test_switched_off(self):
        self.cfg.kara = False
        c = await self.connect(self.account('Lan')[0])
        self.assertFalse(c.welcome['flags']['kara'])
        await c.send(t='kara_list')
        self.assertEqual((await c.expect('error', ref='kara_list'))['code'], 'off')
