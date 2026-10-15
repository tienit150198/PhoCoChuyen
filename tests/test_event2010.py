"""💐 Thiệp 20/10 (game/event2010.py, owner 16/10): a page of its own where a player writes a card and shares its link.

Without a database: the words (cleaned, masked, the original kept for admins, strict payloads), the page (preview tags and
the embedded JSON escaped, the card's words never in the preview), the window and the kill switch, the ticker's line, the
client's copy of the window and the themes. With PostgreSQL: write / read / share / delete / report / hide, the reward
(once per account, registered accounts only, from life day 3, while the window is open, REWARDS_PER_IP, paid at the next
load through game/system_gift.py), today's limit, the HTTP routes (sessions, CSRF, rate limits, same-site readers, 404 /
410 pages), schema 46 additive and idempotent, account deletion.
"""
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from game import accounts, event2010 as ev, pg_schema, system_gift
from game.storage import Store
from tests.test_chua import story

ROOT = Path(__file__).resolve().parents[1]
PG = os.environ.get('TEST_DATABASE_URL') and not os.environ.get('DATABASE_URL')
OPEN_T = ev.WRITE_UNTIL - 5 * 86400 - 12 * 3600   # 16/10/2026 11:59:59 VN


def card(**more):
    return dict(dict(op='create', theme='hoa_hong', direction='nam_nu', to='Mai', text='Chúc em 20/10 thật vui và xinh nhé 💐',
                     stickers=['🌹', '💖']), **more)


class Words(unittest.TestCase):
    def test_a_card_is_cleaned_and_kept_as_text(self):
        c = ev.parse(card(to='  Mai <b>xinh</b> ', text='Dòng một\n\n\n\nDòng hai <script>alert(1)</script>​'), 'Nam')
        self.assertEqual(c['to'], 'Mai <b>xinh</b>', 'kept as text; the page escapes it')
        self.assertIn('<script>', c['text'])
        self.assertNotIn('​', c['text'])
        self.assertEqual((c['sender'], c['theme'], c['direction'], c['stickers'], c['raw']), ('Nam', 'hoa_hong', 'nam_nu', ['🌹', '💖'], None))

    def test_the_mask_hides_phones_and_links_and_keeps_the_original_for_admins(self):
        c = ev.parse(card(text='gọi anh 0912 345 678 hoặc vào www.abc.com nhé', **{'from': 'Anh'}), 'Nam')
        self.assertNotIn('0912', c['text'])
        self.assertNotIn('abc.com', c['text'])
        raw = json.loads(c['raw'])
        self.assertIn('0912', raw['text'])
        self.assertEqual((raw['to'], raw['sender']), ('Mai', 'Anh'))

    def test_the_sender_defaults_to_the_name_in_the_game(self):
        self.assertEqual(ev.parse(card(), 'Lan')['sender'], 'Lan')
        self.assertEqual(ev.parse(card(**{'from': '  '}), '')['sender'], 'Một người thương')
        self.assertEqual(ev._default_from(dict(state=dict(name='Mây'), account=dict(display='Hoa'))), 'Hoa')
        self.assertEqual(ev._default_from(dict(state=dict(name='  Lan   Anh '), account=None)), 'Lan Anh')

    def test_refusals(self):
        bad = [dict(theme='nope'), dict(theme=1), dict(direction='x'), dict(to=''), dict(to='   '), dict(to='x' * (ev.TO_MAX + 1)),
               dict(to=7), dict(text=''), dict(text='abc'), dict(text='x' * (ev.TEXT_MAX + 1)), dict(text=None),
               dict(stickers=['🍕']), dict(stickers='🌹'), dict(stickers=['🌹', '🌹']), dict(stickers=list(ev.STICKERS[:ev.STICKERS_MAX + 1])),
               {'from': 'x' * (ev.FROM_MAX + 1)}, dict(sid='x'), dict(hearts=9)]
        for extra in bad:
            with self.assertRaises(ev.EventError, msg=extra):
                ev.parse(card(**extra), 'Nam')
        self.assertEqual(len(ev.parse(card(text='a\n' * 30 + 'b'), 'Nam')['text'].split('\n')), ev.TEXT_LINES)

    def test_ids(self):
        self.assertTrue(ev.valid_id('Ab_-0123456z'))
        for bad in ('', 'short', 'Ab_-0123456z1', 'Ab_-0123456<', None, 12, '../../etc/pa'):
            self.assertFalse(ev.valid_id(bad), bad)


class Page(unittest.TestCase):
    TEMPLATE = (ROOT / 'public' / '2010.html').read_text(encoding='utf-8')

    def card_data(self, **c):
        base = dict(id='Ab_-0123456z', theme='tulip', direction='nu_nam', to='Mai', sender='Nam', text='Chúc em vui', stickers=[], hearts=0, at=0)
        return dict(mode='card', open=True, card=dict(base, **c))

    def test_every_marker_is_filled_and_nothing_is_left(self):
        out = ev.render(self.TEMPLATE, dict(mode='home', open=True), 'https://phocochuyen.io.vn')
        self.assertNotIn('<!--ev:', out)
        self.assertIn('<meta property="og:image" content="https://phocochuyen.io.vn/icons/2010/og-hoa_hong.png">', out)
        self.assertNotIn('noindex', out, 'the home page may be found')
        self.assertIn('id="ev-data"', out)

    def test_names_and_words_are_escaped_everywhere_and_the_words_stay_out_of_the_preview(self):
        evil = '</script><script>alert(1)</script>"\'&'
        out = ev.render(self.TEMPLATE, self.card_data(to=evil, sender=evil, text='bí mật ' + evil + '\nhai'), 'https://x.vn')
        self.assertNotIn('<script>alert', out)
        self.assertNotIn('</script><script>', out)
        data = re.search(r'<script type="application/json" id="ev-data">(.*?)</script>', out, re.S).group(1)
        self.assertNotIn('<', data)
        self.assertEqual(json.loads(data)['card']['to'], evil, 'the JSON reads back to the very words')
        head = out.split('</head>')[0]
        self.assertNotIn('bí mật', head, 'a surprise: the message is not in the link preview')
        self.assertIn('og-tulip.png', head)
        self.assertIn('noindex', head)
        self.assertIn('&lt;/script&gt;', out.split('<main')[1], 'the no-script card is escaped')

    def test_gone_pages(self):
        for why in ('missing', 'hidden', 'expired'):
            out = ev.render(self.TEMPLATE, dict(mode='gone', why=why, open=False), 'https://x.vn')
            self.assertIn('noindex', out)
            self.assertIn('không còn mở được', out)


class Window(unittest.TestCase):
    def test_the_window_in_vietnam_time(self):
        self.assertEqual(ev.vn_day(ev.WRITE_UNTIL), '2026-10-21')
        self.assertEqual(ev.vn_day(ev.WRITE_UNTIL + 1), '2026-10-22')
        self.assertEqual(ev.vn_day(ev.READ_UNTIL), '2026-12-20')
        self.assertTrue(ev.writing_open(ev.WRITE_UNTIL))
        self.assertFalse(ev.writing_open(ev.WRITE_UNTIL + 1))
        self.assertTrue(ev.reading_open(ev.WRITE_UNTIL + 50 * 86400))
        self.assertFalse(ev.reading_open(ev.READ_UNTIL + 1))

    def test_kill_switch_and_the_operators_stretch(self):
        with mock.patch.dict(os.environ, {'MNL_2010_OFF': '1'}):
            self.assertFalse(ev.writing_open(OPEN_T))
            self.assertIsNone(ev.news_line(OPEN_T))
        with mock.patch.dict(os.environ, {'MNL_2010_UNTIL': str(ev.WRITE_UNTIL + 86400)}):
            self.assertTrue(ev.writing_open(ev.WRITE_UNTIL + 10))

    def test_the_tickers_line_once_a_day(self):
        a, b = ev.news_line(OPEN_T), ev.news_line(OPEN_T + 3600)
        self.assertEqual(a, b)
        self.assertIn('100.000 xu', a['text'])
        self.assertIn('Tiện ích → Thiệp 20/10', a['text'])
        self.assertNotEqual(ev.news_line(OPEN_T + 86400)['key'], a['key'])
        self.assertIn('Hôm nay 20/10', ev.news_line(ev.WRITE_UNTIL - 86400)['text'])
        self.assertIn('hết hôm nay', ev.news_line(ev.WRITE_UNTIL - 60)['text'])
        self.assertIsNone(ev.news_line(ev.WRITE_UNTIL + 1))

    def test_the_game_shows_its_entries_for_the_same_window(self):
        js = (ROOT / 'public/js/isometric/town-utilities.js').read_text(encoding='utf-8')
        self.assertEqual(int(float(re.search(r'EV2010_UNTIL=([0-9e.]+)', js).group(1))), ev.WRITE_UNTIL * 1000)

    def test_every_theme_has_its_look_its_art_and_its_preview_picture(self):
        css = (ROOT / 'public/css/event2010.css').read_text(encoding='utf-8')
        js = (ROOT / 'public/js/event2010.js').read_text(encoding='utf-8')
        self.assertGreaterEqual(len(ev.THEMES), 12)
        for theme in ev.THEMES:
            self.assertRegex(css, rf'\[data-theme="?{theme}"?\]', theme)
            self.assertRegex(js, rf'\b{theme}:', theme)
            self.assertTrue((ROOT / f'public/icons/2010/og-{theme}.png').is_file(), theme)


def make_store(case):
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    store = Store(Path(tmp.name) / 'ev2010.db')
    case.addCleanup(store.close_pool)
    return store


@unittest.skipUnless(PG, 'requires isolated TEST_DATABASE_URL without DATABASE_URL')
class Cards(unittest.TestCase):
    """Lan (account, life day 5), Minh (account, life day 1), a guest (life day 9); the clock inside the window."""
    def setUp(self):
        self.store = make_store(self)
        clock = mock.patch.object(ev, 'now', lambda: self.t)
        clock.start()
        self.addCleanup(clock.stop)
        self.t = OPEN_T
        env = mock.patch.dict(os.environ, {'MNL_BROADCAST_OFF': '1'})
        env.start()
        self.addCleanup(env.stop)
        self.lan = self.player('Lan', 5, 'lan_2010')
        self.minh = self.player('Minh', 1, 'minh_2010')
        self.guest = self.player('Tú', 9)

    def player(self, name, day, username=None):
        token, _, _ = self.store.session()
        if username:
            with mock.patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
                token = accounts.register(self.store, token, dict(username=username, password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name))['token']
        self.set_day(token, day, name)
        return token

    def set_day(self, token, day, name=None):
        s = self.store.read(token)[0] if name is None else story(life_day=day)
        s['journey']['life_day'] = day
        if name:
            s['name'] = name
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), self.store.key(token)))

    def write(self, token, ip='1.1.1.1', **more):
        return ev.act(self.store, token, card(**more), ip)

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def test_write_read_share_and_nothing_leaks(self):
        out = self.write(self.lan, to='Mai <b>xinh</b>')
        c = out['card']
        self.assertTrue(ev.valid_id(c['id']))
        self.assertEqual(out['path'], '/2010/c/' + c['id'])
        self.assertEqual((c['to'], c['sender'], c['hearts'], out['left']), ('Mai <b>xinh</b>', 'Lan', 0, ev.PER_DAY - 1))
        status, data = ev.page_data(self.store, c['id'])
        self.assertEqual((status, data['mode'], data['card']['text']), (200, 'card', c['text']))
        for blob in (json.dumps(data), json.dumps(ev.card(self.store, None, c['id'])), json.dumps(ev.me(self.store, self.minh, '2.2.2.2'))):
            self.assertNotIn(self.store.key(self.lan), blob)
            self.assertNotIn('lan_2010', blob)
        self.assertTrue(ev.card(self.store, self.lan, c['id'])['mine'])
        self.assertFalse(ev.card(self.store, self.minh, c['id'])['mine'])
        self.assertFalse(ev.card(self.store, None, c['id'])['mine'])
        me = ev.me(self.store, self.lan, '1.1.1.1')
        self.assertEqual((me['signed'], me['name'], me['left'], [m['id'] for m in me['mine']]), (True, 'Lan', ev.PER_DAY - 1, [c['id']]))
        self.assertEqual(me['csrf'], self.store.csrf(self.lan))
        self.assertEqual(ev.me(self.store, None, '1.1.1.1')['signed'], False)
        self.assertEqual(ev.page_data(self.store, 'AAAAAAAAAAAA'), (404, ev.page_data(self.store, 'AAAAAAAAAAAA')[1]))
        self.assertEqual(ev.page_data(self.store, 'AAAAAAAAAAAA')[1]['why'], 'missing')
        self.assertEqual(ev.page_data(self.store, '../x')[0], 404)

    def test_a_guest_reads_but_writes_only_with_an_account(self):
        me = ev.me(self.store, self.guest, '1.1.1.1')
        self.assertEqual((me['signed'], me['guest'], me['can_write'], me['reward']['state']), (False, True, False, 'account'))
        with self.assertRaises(ev.EventError) as e:
            self.write(self.guest)
        self.assertEqual((e.exception.code, e.exception.status), ('need_account', 403))
        with self.assertRaises(ev.EventError) as e:
            self.write('x' * 64)
        self.assertEqual(e.exception.status, 401)
        self.assertEqual(self.rows('SELECT count(*) AS n FROM ev2010_cards')[0]['n'], 0)

    def test_the_reward_once_per_account_paid_at_the_next_load(self):
        first = self.write(self.lan)
        self.assertEqual((first['reward']['state'], first['reward'].get('granted')), ('paid', True))
        again = self.write(self.lan, theme='sen')
        self.assertEqual(again['reward']['state'], 'paid')
        self.assertNotIn('granted', again['reward'])
        self.assertEqual(ev.act(self.store, self.lan, dict(op='claim'), '1.1.1.1')['reward']['state'], 'paid')
        rw = self.rows('SELECT * FROM ev2010_rewards')
        self.assertEqual(len(rw), 1)
        self.assertEqual((rw[0]['coins'], rw[0]['card'], rw[0]['life_day'], rw[0]['username']), (100_000, first['card']['id'], 5, 'lan_2010'))
        self.assertNotIn('1.1.1.1', json.dumps(rw, default=str), 'the address is only a hash')
        gift = self.rows('SELECT * FROM system_gifts WHERE id=?', (rw[0]['gift'],))[0]
        self.assertEqual((gift['coins'], gift['status'], gift['granted_by'], gift['sid']), (100_000, 'pending', 'event2010', self.store.key(self.lan)))
        state = self.store.read(self.lan)[0]
        w0 = state['journey']['wallet']
        changed, shown = system_gift.on_load(self.store, self.lan, state)
        self.assertTrue(changed)
        self.assertEqual([g['coins'] for g in shown], [100_000])
        self.assertEqual(self.store.read(self.lan)[0]['journey']['wallet'], w0 + 100_000)
        self.assertEqual(system_gift.on_load(self.store, self.lan, self.store.read(self.lan)[0])[0], False, 'paid once')
        self.assertEqual(ev.me(self.store, self.lan, '1.1.1.1')['reward'], dict(coins=100_000, min_life_day=3, state='paid', pending=False))

    def test_too_young_a_character_gets_it_later_by_claiming(self):
        out = self.write(self.minh)
        self.assertEqual((out['reward']['state'], out['reward']['need']), ('days', 2))
        self.assertEqual(self.rows('SELECT count(*) AS n FROM ev2010_rewards')[0]['n'], 0)
        self.assertEqual(ev.act(self.store, self.minh, dict(op='claim'), '1.1.1.1')['reward']['state'], 'days')
        self.set_day(self.minh, 3)
        self.assertEqual(ev.me(self.store, self.minh, '1.1.1.1')['reward']['state'], 'ready')
        self.assertEqual(ev.act(self.store, self.minh, dict(op='claim'), '1.1.1.1')['reward']['state'], 'paid')
        self.assertEqual(self.rows('SELECT card FROM ev2010_rewards')[0]['card'], out['card']['id'])
        with self.assertRaises(ev.EventError) as e:
            ev.act(self.store, self.lan, dict(op='claim'), '1.1.1.1')
        self.assertEqual(e.exception.code, 'no_card')

    def test_a_network_address_gets_at_most_its_share(self):
        with mock.patch.object(ev, 'REWARDS_PER_IP', 1):
            self.assertEqual(self.write(self.lan, ip='9.9.9.9')['reward']['state'], 'paid')
            self.set_day(self.minh, 4)
            out = self.write(self.minh, ip='9.9.9.9')
            self.assertEqual(out['reward']['state'], 'ip')
            self.assertTrue(out['card']['id'], 'the card is sent all the same')
            self.assertEqual(ev.act(self.store, self.minh, dict(op='claim'), '8.8.8.8')['reward']['state'], 'paid')
        self.assertEqual(len(self.rows('SELECT 1 FROM ev2010_rewards')), 2)

    def test_after_the_window_or_with_the_kill_switch(self):
        self.write(self.lan)
        cid = self.write(self.minh)['card']['id']
        self.set_day(self.minh, 4)
        for how in ('late', 'off'):
            with mock.patch.dict(os.environ, {'MNL_2010_OFF': '1'} if how == 'off' else {}):
                if how == 'late':
                    self.t = ev.WRITE_UNTIL + 1
                for d in (card(), dict(op='claim')):
                    with self.assertRaises(ev.EventError) as e:
                        ev.act(self.store, self.minh, d, '1.1.1.1')
                    self.assertEqual((e.exception.code, e.exception.status), ('closed', 403))
                self.assertEqual(ev.me(self.store, self.minh, '1.1.1.1')['reward']['state'], 'closed')
                self.assertEqual(ev.me(self.store, self.lan, '1.1.1.1')['reward']['state'], 'paid', 'paid stays paid')
                self.assertEqual(ev.page_data(self.store, cid)[0], 200, 'reading goes on')
                self.assertEqual(ev.heart(self.store, cid, 1)['hearts'] > 0, True)
            self.t = OPEN_T
        self.t = ev.READ_UNTIL + 1
        self.assertEqual(ev.page_data(self.store, cid)[0], 410)
        with self.assertRaises(ev.EventError) as e:
            ev.card(self.store, None, cid)
        self.assertEqual(e.exception.status, 410)
        ev.act(self.store, self.minh, dict(op='delete', id=cid), '1.1.1.1')   # the sender may still take it down

    def test_todays_limit(self):
        with mock.patch.object(ev, 'PER_DAY', 2):
            self.write(self.lan)
            self.assertEqual(self.write(self.lan)['left'], 0)
            with self.assertRaises(ev.EventError) as e:
                self.write(self.lan)
            self.assertEqual((e.exception.code, e.exception.status), ('card_limit', 429))
            self.t += 86400
            self.write(self.lan)

    def test_hearts_reports_hide_and_admin(self):
        cid = self.write(self.lan)['card']['id']
        self.assertEqual(ev.heart(self.store, cid, 3)['hearts'], 3)
        for n in (0, ev.HEARTS_MAX + 1, True, '2', 1.5):
            with self.assertRaises(ev.EventError, msg=n):
                ev.heart(self.store, cid, n)
        with self.assertRaises(ev.EventError) as e:
            ev.report(self.store, self.lan, cid, 'spam', '1.1.1.1')
        self.assertEqual(e.exception.code, 'own')
        with self.assertRaises(ev.EventError):
            ev.report(self.store, None, cid, 'nope', '1.1.1.1')
        ev.report(self.store, self.minh, cid, 'rude', '1.1.1.1')
        ev.report(self.store, self.minh, cid, 'spam', '1.1.1.2')   # the same reader counts once
        ev.report(self.store, None, cid, None, '5.5.5.5')
        self.assertEqual(self.rows('SELECT status, reports FROM ev2010_cards')[0], dict(status='live', reports=2))
        ev.report(self.store, self.guest, cid, 'scam', '1.1.1.1')
        self.assertEqual(self.rows('SELECT status, reports FROM ev2010_cards')[0], dict(status='hidden', reports=3))
        self.assertEqual(ev.page_data(self.store, cid)[1]['why'], 'hidden')
        with self.assertRaises(ev.EventError):
            ev.heart(self.store, cid, 1)
        a = ev.admin_view(self.store)
        item = a['items'][0]
        self.assertEqual((item['id'], item['reports'], item['reasons'], item['username'], item['reviewed']),
                         (cid, 3, dict(rude=1, other=1, scam=1), 'lan_2010', False))
        self.assertEqual((a['totals']['cards'], a['totals']['rewards'], a['rewards'][0]['same_ip'], a['rewards'][0]['gift']), (1, 1, 1, 'pending'))
        self.assertEqual(ev.admin_act(self.store, 'boss', dict(act='show', id=cid))['status'], 'live')
        self.assertEqual(ev.page_data(self.store, cid)[0], 200)
        self.assertTrue(ev.admin_view(self.store)['items'][0]['reviewed'])
        ev.admin_act(self.store, 'boss', dict(act='hide', id=cid))
        self.assertEqual(self.rows('SELECT status, by_admin FROM ev2010_cards')[0], dict(status='removed', by_admin='boss'))
        self.assertEqual(ev.page_data(self.store, cid)[0], 404)
        for bad in (dict(act='drop', id=cid), dict(act='hide'), dict(act='hide', id='x'), dict(act='hide', id=cid, more=1)):
            with self.assertRaises(ev.EventError):
                ev.admin_act(self.store, 'boss', bad)

    def test_the_sender_deletes_and_nobody_else_can(self):
        cid = self.write(self.lan, text='Lời riêng tư của anh')['card']['id']
        ev.report(self.store, self.minh, cid, 'spam', '1.1.1.1')
        with self.assertRaises(ev.EventError) as e:
            ev.act(self.store, self.minh, dict(op='delete', id=cid), '1.1.1.1')
        self.assertEqual(e.exception.status, 404)
        self.assertIn('Đã xóa', ev.act(self.store, self.lan, dict(op='delete', id=cid), '1.1.1.1')['message'])
        row = self.rows('SELECT status, text, to_name, from_name, raw FROM ev2010_cards')[0]
        self.assertEqual(row, dict(status='down', text='', to_name='', from_name='', raw=None))
        self.assertEqual(self.rows('SELECT count(*) AS n FROM ev2010_reports')[0]['n'], 0)
        self.assertEqual(ev.page_data(self.store, cid)[1]['why'], 'missing')
        self.assertEqual(ev.me(self.store, self.lan, '1.1.1.1')['mine'], [])
        self.assertEqual(ev.admin_view(self.store)['items'], [])
        with self.assertRaises(ev.EventError):
            ev.act(self.store, self.lan, dict(op='delete', id=cid), '1.1.1.1')
        self.assertEqual(ev.me(self.store, self.lan, '1.1.1.1')['left'], ev.PER_DAY - 1, 'a deleted card still counts today')

    def test_account_deletion_forgets_the_cards_and_keeps_the_reward_log(self):
        cid = self.write(self.lan)['card']['id']
        ev.report(self.store, self.minh, cid, 'spam', '1.1.1.1')
        other = self.write(self.minh)['card']['id']
        ev.forget(self.store, self.lan)
        self.assertEqual([r['id'] for r in self.rows('SELECT id FROM ev2010_cards')], [other])
        self.assertEqual(self.rows('SELECT count(*) AS n FROM ev2010_reports')[0]['n'], 0)
        self.assertEqual(len(self.rows('SELECT 1 FROM ev2010_rewards')), 1)

    def test_schema_46_is_additive_and_idempotent(self):
        self.write(self.lan)
        with self.store.connect() as db:
            for t in ('ev2010_reports', 'ev2010_rewards', 'ev2010_cards'):
                db.execute(f'DROP TABLE {t}')
            db.execute("UPDATE mnl_meta SET value='45' WHERE key='schema_version'")
        with self.store.connect() as db:
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(pg_schema.ensure(db))
            self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
            self.assertEqual(pg_schema.SCHEMA_VERSION, 46)
        self.write(self.lan)
        self.assertEqual(len(self.rows('SELECT 1 FROM ev2010_rewards')), 1)

    def test_http_routes(self):
        from server import GameServer
        server = GameServer(('127.0.0.1', 0), self.store)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        csrf = self.store.csrf(self.lan)

        def request(path, token=None, method=None, payload=None, headers=None, body=None):
            method = method or ('POST' if payload is not None or body is not None else 'GET')
            h = {'Content-Type': 'application/json'}
            if token:
                h['Cookie'] = 'mnl_session=' + token
                h['X-Game-CSRF'] = self.store.csrf(token)
            h.update(headers or {})
            con = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            con.request(method, path, body if body is not None else json.dumps(payload) if payload is not None else None, h)
            r = con.getresponse()
            out = r.status, r.read(), dict(r.getheaders())
            con.close()
            return out
        # pages: no cookie, no save
        status, raw, hdr = request('/2010')
        self.assertEqual(status, 200)
        self.assertIn(b'id="ev-data"', raw)
        self.assertRegex(raw.decode(), r'/js/event2010\.js\?v=[0-9a-f]+', 'asset URLs hashed')
        self.assertNotIn('mnl_session', hdr.get('Set-Cookie', ''), 'the page never makes a session')
        status, raw, _ = request('/api/2010/cards', self.lan, 'POST', card(), headers={'X-Game-CSRF': 'nope'})
        self.assertEqual(status, 403, raw)
        status, raw, _ = request('/api/2010/cards', self.lan, 'POST', card())
        self.assertEqual(status, 200, raw)
        cid = json.loads(raw)['card']['id']
        status, raw, hdr = request('/2010/c/' + cid)
        self.assertEqual(status, 200)
        self.assertIn(b'og-hoa_hong.png', raw)
        self.assertIn('noindex', hdr.get('X-Robots-Tag', ''))
        self.assertEqual(request('/2010/c/AAAAAAAAAAAA')[0], 404)
        self.assertEqual(request('/2010/c/%3Cscript%3E')[0], 404)
        status, raw, _ = request('/api/2010/me', self.lan)
        self.assertEqual((status, json.loads(raw)['csrf']), (200, csrf))
        status, raw, _ = request('/api/2010/me')
        self.assertEqual((status, json.loads(raw)['signed']), (200, False))
        status, raw, _ = request('/api/2010/card?id=' + cid)
        self.assertEqual((status, json.loads(raw)['mine']), (200, False))
        self.assertEqual(request('/api/2010/card?id=x')[0], 404)
        # readers: anyone from our own pages
        status, raw, _ = request('/api/2010/heart', payload=dict(id=cid, n=4))
        self.assertEqual((status, json.loads(raw)['hearts']), (200, 4))
        self.assertEqual(request('/api/2010/heart', payload=dict(id=cid, n=4), headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(request('/api/2010/heart', payload=dict(id=cid, n=4), headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(request('/api/2010/heart', payload=dict(id=cid, n=4), headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(request('/api/2010/heart', body='{"id":"' + 'x' * 3000 + '"}')[0], 413)
        self.assertEqual(request('/api/2010/report', payload=dict(id=cid, reason='spam'))[0], 200)
        self.assertEqual(request('/api/2010/report', self.lan, payload=dict(id=cid, reason='spam'))[0], 400, 'not my own')
        with mock.patch.dict(os.environ, {'EV2010_HEARTS_PER_MINUTE': '1'}):
            request('/api/2010/heart', payload=dict(id=cid, n=1))
            self.assertEqual(request('/api/2010/heart', payload=dict(id=cid, n=1))[0], 429)
        # writing: budgets a minute
        with mock.patch.dict(os.environ, {'EV2010_CARDS_PER_MINUTE': '1'}):
            self.assertEqual(request('/api/2010/cards', self.minh, 'POST', card())[0], 200)
            self.assertEqual(request('/api/2010/cards', self.minh, 'POST', card())[0], 429)
        self.assertEqual(request('/api/2010/cards', self.guest, 'POST', card())[0], 403)
        self.assertEqual(request('/api/2010/cards', None, 'POST', card())[0] in (401, 403), True)
        # admin only
        self.assertEqual(request('/api/admin/2010', self.lan)[0], 403)
        self.assertEqual(request('/api/admin/2010', self.lan, 'POST', dict(act='hide', id=cid))[0], 403)
        with mock.patch.dict(os.environ, {'ADMIN_USERS': 'lan_2010'}):
            status, raw, _ = request('/api/admin/2010', self.lan)
            self.assertEqual(status, 200, raw)
            self.assertEqual(json.loads(raw)['totals']['rewards'], 1)
            self.assertEqual(request('/api/admin/2010', self.lan, 'POST', dict(act='hide', id=cid))[0], 200)
        self.assertEqual(request('/2010/c/' + cid)[0], 404)
        # the sender deletes over HTTP
        cid2 = json.loads(request('/api/2010/cards', self.lan, 'POST', card(theme='sen'))[1])['card']['id']
        self.assertEqual(request('/api/2010/cards', self.minh, 'POST', dict(op='delete', id=cid2))[0], 404)
        self.assertEqual(request('/api/2010/cards', self.lan, 'POST', dict(op='delete', id=cid2))[0], 200)
        # the ticker carries the season's line
        status, raw, _ = request('/api/news?since=0')
        self.assertIn('Thiệp 20/10', json.loads(raw)['event']['text'])
        self.t = ev.READ_UNTIL + 1
        self.assertEqual(request('/2010/c/' + cid2)[0], 410)


if __name__ == '__main__':
    unittest.main()
