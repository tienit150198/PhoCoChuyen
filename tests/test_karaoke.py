"""🎤 Phòng hát (game/karaoke.py): the YouTube link parser, the oEmbed check and its cache (the network mocked),
🧩 Đoán bài's clue rules and guess matching, the queue ticket (first of the day free, then QUEUE_XU), tips (80 % to the
singer, caps, blocks, account age), the admin tools, and the saves staying valid for 1.9.4 (history rows written with
an old kind; 'karaoke' accepted from now on)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, social
from game import journey as jr
from game import karaoke as kg
from game import marriage as mr
from game.engine import validate_state
from game.storage import Store

VID = 'dQw4w9WgXcQ'


class Links(unittest.TestCase):
    def test_accepted_forms_give_the_id(self):
        for link in (VID, f'https://www.youtube.com/watch?v={VID}', f'https://youtube.com/watch?v={VID}&t=42s', f'http://m.youtube.com/watch?v={VID}',
                     f'https://music.youtube.com/watch?v={VID}&list=x', f'https://youtu.be/{VID}', f'https://youtu.be/{VID}?si=abc',
                     f'https://www.youtube.com/shorts/{VID}', f'https://www.youtube.com/embed/{VID}?start=3', f'https://www.youtube.com/live/{VID}',
                     f'https://www.youtube-nocookie.com/embed/{VID}', f'  https://www.youtube.com/watch?v={VID}  '):
            self.assertEqual(kg.parse_vid(link), VID, link)

    def test_what_a_phone_copies_gives_the_id(self):
        """B3 (07/10, 9 refused pastes): Chia sẻ › Sao chép on phones and apps, shorts and music, si= and other params."""
        for link in (f'https://youtube.com/shorts/{VID}?si=AbC-12_x', f'https://m.youtube.com/watch?v={VID}&feature=share&si=x',
                     f'https://music.youtube.com/watch?v={VID}&si=Zz9', f'https://www.youtube.com/watch?app=desktop&v={VID}&pp=ygU',
                     f'youtu.be/{VID}?si=x', f'www.youtube.com/watch?v={VID}', f'YOUTUBE.COM/shorts/{VID}', f'm.youtube.com/watch?v={VID}',
                     f'music.youtube.com/watch?v={VID}', f'​https://youtu.be/{VID}​', f'﻿{VID}',
                     f'Xem "Nơi này có anh" trên YouTube: https://youtu.be/{VID}?si=abc', f'"https://youtu.be/{VID}"',
                     f'<https://youtu.be/{VID}>', f'https://youtu.be/{VID}, hay lắm', f'https://www.youtube.com/watch?v={VID}%26si%3Dabc'):
            self.assertEqual(kg.parse_vid(link), VID, link)

    def test_anything_else_is_refused(self):
        for link in ('', None, 'dQw4w9WgXc', f'https://youtube.com.evil.io/watch?v={VID}', f'https://evil.com/watch?v={VID}',
                     f'javascript:alert(1)//{VID}', f'https://www.youtube.com/watch?v={VID}x', 'https://www.youtube.com/watch?v=short',
                     f'ftp://youtube.com/watch?v={VID}', f'https://user:pw@youtube.com/watch?v={VID}', f'https://youtube.com:8443/watch?v={VID}',
                     f'https://www.youtube.com/channel/{VID}', 'x' * 500, 12345,
                     f'youtube.com.evil.io/watch?v={VID}', f'evil.io/youtu.be/{VID}', f'xem bài {VID} nhé', f'//youtu.be/{VID}',
                     f'https://www.youtube.com/watch?v={VID}x%26si', 'https://www.youtube.com/@sontungmtp', 'nơi này có anh'):
            self.assertIsNone(kg.parse_vid(link), link)


class Guessing(unittest.TestCase):
    def test_fold_and_answers(self):
        self.assertEqual(kg.fold('  Nơi Này CÓ ANH!! '), 'noi nay co anh')
        self.assertEqual(kg.fold('Đường về'), 'duong ve')
        self.assertEqual(kg.answers('Nơi này có anh / Noi nay co anh / NNCA'), ['noi nay co anh', 'nnca'])
        self.assertEqual(kg.answers(''), [])
        self.assertEqual(kg.answers('a'), [])
        self.assertEqual(kg.answers('x' * 61), [])

    def test_match_is_accent_insensitive_and_normalised(self):
        keys = kg.answers('Nơi này có anh')
        for guess in ('noi nay co anh', 'NƠI NÀY CÓ ANH', 'nơi này có anh!!!', 'bài nơi này có anh', 'là nơi này có anh', 'noinaycoanh',
                      'chắc là nơi này có anh đó', 'noi nay co ah'):
            self.assertEqual(kg.match(guess, keys), 'yes', guess)
        self.assertEqual(kg.match('nơi này có em', keys), 'near')
        for guess in ('em của ngày hôm qua', '', 'anh', 'noi'):
            self.assertEqual(kg.match(guess, keys), 'no', guess)

    def test_short_answers_need_the_exact_words(self):
        keys = kg.answers('Em')
        self.assertEqual(kg.match('em', keys), 'yes')
        self.assertEqual(kg.match('Ém', keys), 'yes')
        self.assertNotEqual(kg.match('anh', keys), 'yes')
        self.assertNotEqual(kg.match('em ơi em à', keys), 'yes')   # a 2-letter answer is not found inside a sentence

    def test_lyric_clue_is_a_short_snippet_with_blanks(self):
        self.assertEqual(kg.check_clue('lyric', 'Em ơi ___ ___ về chưa'), 'Em ơi ___ ___ về chưa')
        self.assertEqual(kg.check_clue('lyric', 'Em ơi … về chưa'), 'Em ơi ___ về chưa')
        self.assertEqual(kg.check_clue('lyric', 'Em ơi ____ về chưa'), 'Em ơi ___ về chưa')
        with self.assertRaises(kg.KaraError) as e:
            kg.check_clue('lyric', 'một hai ba bốn năm sáu bảy tám chín mười mười một mười hai ___')
        self.assertEqual(e.exception.code, 'clue_long')
        with self.assertRaises(kg.KaraError) as e:
            kg.check_clue('lyric', 'Em ơi Hà Nội phố')
        self.assertEqual(e.exception.code, 'no_blank')
        with self.assertRaises(kg.KaraError):
            kg.check_clue('lyric', '___ ___')                       # nothing left to go by
        self.assertEqual(kg.check_clue('lyric', 'đéo ___ về đâu'), '*** ___ về đâu')   # heavy words as *

    def test_emoji_clue_is_emoji_only(self):
        self.assertEqual(kg.check_clue('emoji', '🌧️💔🏠'), '🌧️💔🏠')
        self.assertEqual(kg.check_clue('emoji', '🌧️ 💔 🏠 👨‍👩‍👧'), '🌧️ 💔 🏠 👨👩👧')
        for bad in ('🌧️ mưa', '🌧️1', '💔', '', 'abc', '🌧️' * 13):
            with self.assertRaises(kg.KaraError, msg=bad):
                kg.check_clue('emoji', bad)
        with self.assertRaises(kg.KaraError):
            kg.check_clue('video', '🌧️💔')

    def test_titles_are_filtered(self):
        self.assertEqual(kg.clean_title('Bài đéo gì vậy (Official MV)'), 'Bài *** gì vậy (Official MV)')
        self.assertEqual(kg.clean_title('Liên hệ 0912345678'), 'Liên hệ •••')
        self.assertEqual(kg.clean_title(''), 'Bài hát YouTube')
        self.assertLessEqual(len(kg.clean_title('a' * 500)), kg.TITLE_LEN)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        h = patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        h.start()
        self.addCleanup(h.stop)
        self.n = 0

    def user(self, name, old=True, wallet=100):
        token, _, _ = self.store.session()
        tok = accounts.register(self.store, token, dict(username=name + '_k', password='matkhau-dai-lam', confirm='matkhau-dai-lam',
                                                        display=name.title()))['token']
        sid = self.store.key(tok)
        if old:
            self.store.transaction(lambda db: db.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))

        def fn(s):
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {sid: fn})
        return tok

    def rid(self):
        self.n += 1
        return f'rid-test-{self.n:04d}'

    def wallet(self, tok):
        return self.store.read(tok)[0]['journey']['wallet']

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def singing(self, tok, played=True):
        e = kg.queue(self.store, tok, dict(rid=self.rid()))['e']
        if played:
            self.store.transaction(lambda db: db.execute('UPDATE kara_tickets SET used=1, played=? WHERE id=?', (time.time(), e)))
        return e

    def song_ok(self, vid=VID):
        with patch.object(kg, '_http_get', return_value=(200, json.dumps(dict(title='Nơi này có anh', author_name='Sơn Tùng M-TP')).encode())):
            return kg.check_song(self.store, f'https://youtu.be/{vid}')


class SongCheck(Base):
    def test_oembed_answers_and_the_cache(self):
        calls = []

        def net(status, body=b''):
            def get(url, timeout):
                calls.append((url, timeout))
                return status, body
            return get
        with patch.object(kg, '_http_get', net(200, json.dumps(dict(title='Đi về nhà đéo', author_name='JustaTee')).encode())):
            s = kg.check_song(self.store, f'https://www.youtube.com/watch?v={VID}&t=1')
            self.assertEqual((s['vid'], s['ok'], s['title'], s['channel']), (VID, True, 'Đi về nhà ***', 'JustaTee'))
            self.assertIn('oembed', calls[0][0])
            self.assertIn('watch%3Fv%3D' + VID, calls[0][0])
            self.assertLessEqual(calls[0][1], 5)
            kg.check_song(self.store, VID)                       # cached: no second request
            self.assertEqual(len(calls), 1)
        for status, why in ((401, 'blocked'), (403, 'blocked'), (404, 'gone'), (400, 'gone')):
            with patch.object(kg, '_http_get', net(status)):
                s = kg.check_song(self.store, f'https://youtu.be/{status:011d}')
            self.assertEqual((s['ok'], s['why']), (False, why), status)
            self.assertTrue(s['text'])
        for status in (0, 500, 429):                            # YouTube did not answer: try again, nothing cached
            with patch.object(kg, '_http_get', net(status)):
                with self.assertRaises(kg.KaraError) as e:
                    kg.check_song(self.store, 'aaaaaaaaaaa')
            self.assertEqual(e.exception.code, 'busy')
        self.assertEqual(self.rows("SELECT vid FROM kara_songs WHERE vid='aaaaaaaaaaa'"), [])
        with self.assertRaises(kg.KaraError) as e:
            kg.check_song(self.store, 'https://evil.com/x')
        self.assertEqual(e.exception.code, 'bad_link')
        with self.assertRaises(kg.KaraError) as e:               # the outbound budget is spent
            kg.check_song(self.store, 'bbbbbbbbbbb', fetch_ok=lambda: False)
        self.assertEqual(e.exception.status, 429)

    def test_old_cache_is_checked_again_and_a_ban_sticks(self):
        self.song_ok()
        self.store.transaction(lambda db: db.execute('UPDATE kara_songs SET checked_at=? WHERE vid=?', (time.time() - kg.CACHE_OK_SECS - 5, VID)))
        with patch.object(kg, '_http_get', return_value=(401, b'')) as get:
            s = kg.check_song(self.store, VID)
        self.assertEqual(get.call_count, 1)
        self.assertEqual((s['ok'], s['why']), (False, 'blocked'))
        self.assertEqual(s['title'], 'Nơi này có anh')            # the title it had is kept
        kg.admin_act(self.store, 'boss', dict(act='ban', vid=VID))
        with patch.object(kg, '_http_get') as get:
            s = kg.check_song(self.store, VID)
        get.assert_not_called()
        self.assertEqual((s['ok'], s['why']), (False, 'banned'))


class Money(Base):
    def test_first_song_of_the_day_is_free_then_two_xu_one_row(self):
        a = self.user('lan', wallet=50)
        r1 = kg.queue(self.store, a, dict(rid=self.rid()))
        self.assertEqual((r1['price'], r1.get('free')), (0, True))
        self.assertEqual(self.wallet(a), 50)
        again = kg.queue(self.store, a, dict(rid=self.rid()))      # the free ticket is not used yet: handed back
        self.assertEqual((again['e'], again['price'], again['again']), (r1['e'], 0, True))
        self.store.transaction(lambda db: db.execute('UPDATE kara_tickets SET used=1 WHERE id=?', (r1['e'],)))
        r2 = kg.queue(self.store, a, dict(rid='rid-same-0001'))
        self.assertEqual(r2['price'], kg.QUEUE_XU)
        self.assertEqual(self.wallet(a), 50 - kg.QUEUE_XU)
        self.assertEqual(kg.queue(self.store, a, dict(rid='rid-same-0001'))['e'], r2['e'])   # unused: the same ticket
        self.store.transaction(lambda db: db.execute('UPDATE kara_tickets SET used=1'))
        r3 = kg.queue(self.store, a, dict(rid='rid-same-0001'))     # a retry of a used rid: that ticket, nothing paid
        self.assertEqual((r3['e'], r3['price']), (r2['e'], 0))
        kg.queue(self.store, a, dict(rid=self.rid()))
        s = self.store.read(a)[0]
        self.assertEqual(s['journey']['wallet'], 50 - 2 * kg.QUEUE_XU)
        rows = [h for h in s['journey']['history'] if h['label'].startswith(kg.LABEL_QUEUE)]
        self.assertEqual(len(rows), 1)                               # one Sổ ví row a day, updated in place
        self.assertEqual((rows[0]['amount'], rows[0]['label'], rows[0]['kind']), (-4, '🎤 Phòng hát · 2 bài', kg.WRITE_KIND))
        validate_state(s)

    def test_refusals(self):
        poor = self.user('poor', wallet=1)
        kg.queue(self.store, poor, dict(rid=self.rid()))
        self.store.transaction(lambda db: db.execute('UPDATE kara_tickets SET used=1'))
        with self.assertRaises(kg.KaraError) as e:
            kg.queue(self.store, poor, dict(rid=self.rid()))
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(self.wallet(poor), 1)
        guest, _, _ = self.store.session()
        with self.assertRaises(kg.KaraError) as e:
            kg.queue(self.store, guest, dict(rid=self.rid()))
        self.assertEqual(e.exception.code, 'account_required')
        muted = self.user('muted')
        self.store.transaction(lambda db: db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)',
                                                     (kg.pid_of(self.store.key(muted)), time.time() + 600, 'a', '', time.time())))
        with self.assertRaises(kg.KaraError) as e:
            kg.queue(self.store, muted, dict(rid=self.rid()))
        self.assertEqual(e.exception.code, 'muted')
        with self.assertRaises(kg.KaraError):
            kg.queue(self.store, poor, dict(rid='x'))

    def test_tips_go_80_percent_to_the_singer_once(self):
        singer, fan = self.user('singer'), self.user('fan', wallet=500)
        e = self.singing(singer)
        out = kg.tip(self.store, fan, dict(e=e, xu=50, rid='tip-rid-0001'))
        self.assertEqual((out['xu'], out['got'], out['to']), (50, 40, 'Singer'))
        self.assertEqual(self.wallet(fan), 450)
        again = kg.tip(self.store, fan, dict(e=e, xu=50, rid='tip-rid-0001'))   # a retry: nothing moves
        self.assertEqual((again['xu'], again['again']), (0, True))
        self.assertEqual(self.wallet(fan), 450)
        fx = self.rows("SELECT sid, kind, amount, data, status FROM live_effects WHERE id LIKE 'ktip:%'")
        self.assertEqual(len(fx), 1)
        self.assertEqual((fx[0]['sid'], fx[0]['kind'], fx[0]['amount'], json.loads(fx[0]['data'])['src']), (self.store.key(singer), 'coins', 40, 'kara_tip'))
        s = self.store.read(fan)[0]
        self.assertEqual(s['journey']['history'][-1]['kind'], kg.WRITE_KIND)
        self.assertEqual(s['journey']['history'][-1]['amount'], -50)
        validate_state(s)
        from game import live_effects as lfx
        before = self.wallet(singer)
        lfx.on_load(self.store, singer, self.store.read(singer)[0])
        st = self.store.read(singer)[0]
        self.assertEqual(st['journey']['wallet'], before + 40)
        self.assertEqual(st['journey']['history'][-1]['label'], '🎤 Khán giả tặng xu')
        validate_state(st)

    def test_tip_caps_blocks_and_rules(self):
        singer, fan = self.user('singer2'), self.user('fan2', wallet=2000)
        e = self.singing(singer)
        for i in range(4):
            kg.tip(self.store, fan, dict(e=e, xu=50, rid=f'cap-rid-{i:04d}'))
        with self.assertRaises(kg.KaraError) as x:                   # 200 sent today
            kg.tip(self.store, fan, dict(e=e, xu=5, rid='cap-rid-0009'))
        self.assertEqual(x.exception.code, 'cap')
        self.assertEqual(self.wallet(fan), 1800)                     # the refused one took nothing
        fans = [self.user(f'f{i}', wallet=500) for i in range(3)]
        for i, f in enumerate(fans[:2]):
            for k in range(4):
                kg.tip(self.store, f, dict(e=e, xu=50, rid=f'g{i}-rid-{k:04d}'))
        got = self.rows("SELECT SUM(got) AS n FROM kara_tickets WHERE kind='tip'")[0]['n']
        self.assertEqual(got, 12 * 40)                              # 480 of the singer's 500 a day
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, fans[2], dict(e=e, xu=50, rid='g2-rid-0000'))
        self.assertEqual(x.exception.code, 'cap_got')
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, singer, dict(e=e, xu=5, rid='self-rid-01'))
        self.assertEqual(x.exception.code, 'self')
        blocker = self.user('blocker', wallet=100)
        self.store.transaction(lambda db: db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)',
                                                     (kg.pid_of(self.store.key(singer)), kg.pid_of(self.store.key(blocker)), time.time())))
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, blocker, dict(e=e, xu=5, rid='blk-rid-01'))
        self.assertEqual(x.exception.code, 'blocked')
        young = self.user('young', old=False, wallet=100)
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, young, dict(e=e, xu=5, rid='yng-rid-01'))
        self.assertEqual(x.exception.code, 'too_new')
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, fans[2], dict(e=e, xu=7, rid='bad-rid-01'))
        self.assertEqual(x.exception.code, 'bad_amount')
        stale = self.singing(self.user('stale'), played=False)        # never played: no stage to tip
        with self.assertRaises(kg.KaraError) as x:
            kg.tip(self.store, fans[2], dict(e=stale, xu=5, rid='stl-rid-01'))
        self.assertEqual(x.exception.code, 'gone')

    def test_new_kind_accepted_and_old_kind_written(self):
        self.assertIn('karaoke', jr.HISTORY_KINDS)
        self.assertEqual(kg.WRITE_KIND, 'life')                     # step 1: 1.9.4 validates every row this build writes
        self.assertIn(kg.WRITE_KIND, ('living', 'upkeep', 'draw', 'invest', 'salary', 'reopen', 'incident', 'life', 'study', 'backdoor', 'bank', 'home', 'fair'))
        a = self.user('kind', wallet=50)

        def fn(s):
            jr._wallet(s['journey'], -1, 'karaoke', '🎤 thử')
        mr._mutate(self.store, {self.store.key(a): fn})              # a save with the new kind (step 2) loads here
        validate_state(self.store.read(a)[0])


class Admin(Base):
    def test_reports_queue_and_tools(self):
        a = self.user('rep')
        self.song_ok()
        t = time.time()
        bad = 'abcdefabcdef0123'
        self.store.transaction(lambda db: [db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'kara', ?, ?, ?)", row) for row in (
            ('aaaaaaaaaaaaaaa1', 'v:' + VID, 'rude', t), ('aaaaaaaaaaaaaaa2', 'p:' + bad, 'minor', t - 5), ('aaaaaaaaaaaaaaa3', 'v:' + VID, 'spam', t))])
        v = kg.admin_view(self.store)
        self.assertEqual(v['items'][0]['target'], 'p:' + bad)        # 🛟 minor first
        self.assertTrue(v['items'][0]['safety'])
        song = v['items'][1]
        self.assertEqual((song['n'], song['title'], song['reasons']), (2, 'Nơi này có anh', {'rude': 1, 'spam': 1}))
        kg.admin_act(self.store, 'boss', dict(act='keep', target='v:' + VID))
        self.assertEqual([i['target'] for i in kg.admin_view(self.store)['items']], ['p:' + bad])
        out = kg.admin_act(self.store, 'boss', dict(act='mute', pid=bad, minutes=60))
        self.assertGreater(out['until'], t)
        self.assertEqual(kg.admin_view(self.store)['items'], [])
        kg.admin_act(self.store, 'boss', dict(act='ban', vid=VID))
        self.assertEqual([b['vid'] for b in kg.admin_view(self.store)['banned']], [VID])
        kg.admin_act(self.store, 'boss', dict(act='unban', vid=VID))
        self.assertEqual(kg.admin_view(self.store)['banned'], [])
        for act in ('skip', 'close', 'end_round'):
            self.assertEqual(kg.admin_act(self.store, 'boss', dict(act=act, room='kara:tre-2'))['room'], 'kara:tre-2')
        kg.admin_act(self.store, 'boss', dict(act='kick', pid=bad))
        for data in (dict(act='nuke'), dict(act='skip', room='town'), dict(act='kick', pid='x'), dict(act='ban', vid='x'), dict(act='keep', target='town')):
            with self.assertRaises(kg.KaraError, msg=data):
                kg.admin_act(self.store, 'boss', data)
        e = kg.queue(self.store, a, dict(rid=self.rid()))['e']
        kg.forget(self.store, a)
        self.assertEqual(self.rows('SELECT id FROM kara_tickets WHERE id=?', e), [])


OLD = Path(os.environ.get('MNL_PREV_TREE', '/nonexistent/rel-1.9.4'))


@unittest.skipUnless((OLD / 'game' / 'engine.py').exists(), 'previous release tree not found (MNL_PREV_TREE)')
class PreviousServer(Base):
    """Saves this build wrote (a paid queue ticket, a tip sent, a tip and a guess prize received) load on the previous
    release (1.9.4's validate_state: its closed list of Sổ ví kinds)."""
    PROG = r'''
import json, sys
sys.path.insert(0, '.')
from game.engine import validate_state, migrate_state
for path in sys.argv[1:]:
    s = migrate_state(json.load(open(path, encoding='utf-8')), owned=True)
    validate_state(s)
print(json.dumps(dict(ok=True)))
'''

    def test_old_server_accepts_the_saves(self):
        from game import live_effects as lfx
        singer, fan = self.user('oldsinger', wallet=60), self.user('oldfan', wallet=300)
        e = self.singing(singer)
        kg.queue(self.store, singer, dict(rid=self.rid()))           # paid (the free one is used)
        kg.tip(self.store, fan, dict(e=e, xu=20, rid='old-rid-0001'))
        self.store.transaction(lambda db: db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, 'coins', 5, ?, 'pending', ?)",
                                                     ('kguess:abc:1', self.store.key(singer), json.dumps(dict(src='kara_guess')), time.time())))
        lfx.on_load(self.store, singer, self.store.read(singer)[0])
        paths = []
        for n, tok in (('singer', singer), ('fan', fan)):
            st = self.store.read(tok)[0]
            self.assertTrue(any(h['label'].startswith('🎤') for h in st['journey']['history']), n)
            p = Path(self.tmp.name) / f'{n}.json'
            p.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
            paths.append(str(p))
        out = subprocess.run([sys.executable, '-c', self.PROG, *paths], cwd=OLD, capture_output=True, text=True, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(json.loads(out.stdout.strip().splitlines()[-1]), dict(ok=True))


class Headers(unittest.TestCase):
    """server.py's CSP lets in the YouTube IFrame player only; everything else as strict as before; the mic stays off."""

    def test_csp_allows_youtube_embed_only(self):
        import re as _re
        src = (Path(__file__).resolve().parents[1] / 'server.py').read_text(encoding='utf-8')
        start = src.index('CSP=(')
        csp = ''.join(_re.findall(r'"([^"]*)"', src[start:src.index(')', start)]))
        d = {p.split()[0]: p.split()[1:] for p in csp.split(';') if p.strip()}
        self.assertEqual(d['default-src'], ["'self'"])
        self.assertEqual(d['script-src'], ["'self'", 'https://www.youtube.com', 'https://s.ytimg.com'])
        self.assertEqual(d['frame-src'], ['https://www.youtube-nocookie.com', 'https://www.youtube.com'])
        self.assertEqual(d['img-src'], ["'self'", 'data:', 'blob:', 'https://i.ytimg.com'])
        for k, v in (('connect-src', ["'self'"]), ('object-src', ["'none'"]), ('frame-ancestors', ["'none'"]), ('base-uri', ["'self'"]),
                     ('form-action', ["'self'"]), ('style-src', ["'self'", "'unsafe-inline'"]), ('media-src', ["'self'", 'blob:'])):
            self.assertEqual(d[k], v, k)
        self.assertNotIn("'unsafe-eval'", csp)
        # phase 1 records nothing: the mic stays off unless LIVE_KARAOKE_MIC turns it on (tests/test_karaoke_mic.py)
        self.assertIn('PERMISSIONS="camera=(), microphone=(), geolocation=(), payment=()"', src)
        self.assertIn('self.send_header("Permissions-Policy",PERMISSIONS)', src)

    def test_player_sends_its_origin_to_youtube(self):
        js = (Path(__file__).resolve().parents[1] / 'public/js/v4/karaoke.js').read_text(encoding='utf-8')
        self.assertIn("f.referrerPolicy='strict-origin-when-cross-origin'", js)   # the site is no-referrer: YouTube error 153
        self.assertIn("YT_HOST='https://www.youtube-nocookie.com'", js)

    def test_drift_control_seeks_rarely(self):
        """B2 (07/10 "nhạc cứ giật giật"): a seek re-buffers, so it is the last resort (scripts/browser_live_karaoke.py)."""
        js = (Path(__file__).resolve().parents[1] / 'public/js/v4/karaoke.js').read_text(encoding='utf-8')
        self.assertIn('const SEEK_AT=2,SEEK_GAP=10000,', js)   # ≥ 2 s off, at most once per 10 s
        body = js[js.index('function sync('):js.index('function voiceMove(')]
        self.assertIn('if(s!==1)return;', body)                 # never while buffering, an ad or a pause
        self.assertEqual(body.count('seekTo('), 1)
        # 🎙️ following live voices (08/10): a seek only when a voice would come late, a few a song, 6 s apart
        voice = js[js.index('function voiceMove('):js.index('function mixNow(')]
        self.assertEqual(voice.count('seekTo('), 1)
        self.assertIn("mv==='seek'&&((K.vSeeks<VOICE_SEEKS&&gap>=VSEEK_GAP)||(Math.abs(off)>SEEK_AT&&gap>=SEEK_GAP))", voice)
        self.assertIn('VOICE_SEEKS=3,VSEEK_GAP=6000', js)
