"""☕ Chỗ tiêu xu (game/spend.py, owner 06/10 "cho nhiều cái để tiêu tiền"): the catalogue and its price bands, đi quán
(needs bars, stamp card, tinh thần once a day), spa, Rạp Mây (one film a week), 🙏 công đức (wallet then bank, a pure
sink, the weekly board), 🎨 the weekly status items (buy, renew up to 4 weeks, unlock, wear), money (never created, every
xu accounted for in the wallet history / bank log), saves (absent block, strict shape, a newer build's block), the
chat_style / donations rows written with the save, and the live service's reading of them (live/styles.py)."""
import asyncio
import copy
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game import bank as bk
from game import journey as jr
from game import needs as nd
from game import price_index as pi
from game import social
from game import spend as sp
from game import spend_content as C
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story

T0 = 1_791_300_000.0          # a Tuesday (2026-10-06, Vietnam time)


def SP(s):
    return s['journey']['spend']


def money(s):
    """Every xu the save holds in hand: the wallet and the bank account."""
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def at(t):
    return patch('game.spend.now', lambda: t)


def _lum(h):
    def ch(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    r, g, b = ch(h[1:3]), ch(h[3:5]), ch(h[5:7])
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


class Catalogue(unittest.TestCase):
    def test_price_bands_follow_income_percentiles(self):
        # T0 3–40 (a few % of a median 262 xu day), T1 50–400 (≤ 1.5 median days), công đức from 5; 💹 07/10: +10 %
        for sh in C.SHOPS.values():
            for it in sh['items']:
                self.assertTrue(3 <= it['price'] <= pi.price(40), it)
        for it in C.SPA:
            self.assertTrue(3 <= it['price'] <= pi.price(40), it)
        self.assertTrue(3 <= C.FILM_PRICE <= pi.price(40))
        for it in C.STYLE_ITEMS.values():
            if it.get('earn'):   # 🛍️ a title earned in Mua sắm (game/lux.py): never sold
                self.assertEqual(it['price'], 0)
                continue
            self.assertTrue(50 <= it['price'] <= pi.price(400), it)
        self.assertEqual(C.GIVE_MIN, 5)
        self.assertGreaterEqual(C.GIVE_MAX, 1_000_000)   # open-ended enough for the top of the 💰 board

    def test_ids_and_texts(self):
        ids = list(sp.ITEMS) + list(sp.SPA) + [f['id'] for f in C.FILMS] + list(C.STYLE_ITEMS) + list(C.SHOPS)
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids:
            self.assertRegex(i, sp.ID_RE.pattern)
        self.assertEqual({x['kind'] for x in C.STYLE_ITEMS.values()}, set(C.KINDS))
        self.assertEqual(C.TITLE_TEXT['t_tin_do_cafe'], '☕ Tín đồ cà phê')
        self.assertEqual(jr.content()['spend'], sp.catalogue())

    def test_name_colours_read_on_both_themes(self):
        light_bg, dark_bg = '#fffdf9', '#201e28'      # public/css/app.css --surface of "kem" and "dem"
        for c in C.COLORS:
            self.assertGreaterEqual(contrast(c['light'], light_bg), 4.5, c['id'])
            self.assertGreaterEqual(contrast(c['dark'], dark_bg), 4.5, c['id'])
            for a, b in ((c.get('grad'), light_bg), (c.get('grad_dark'), dark_bg)):
                for x in a or ():
                    self.assertGreaterEqual(contrast(x, b), 4.5, c['id'])
        for f in C.FRAMES:
            self.assertRegex(f['ring'], r'^#[0-9a-f]{6}$')


class Quan(unittest.TestCase):
    def test_a_drink_costs_its_price_from_the_wallet_and_stamps_the_card(self):
        s = story(100)
        s, r = act(s, 'jr_spend_eat', shop='co_lan', item='ca_phe_muoi')
        self.assertEqual(s['journey']['wallet'], 90)                          # 💹 07/10: 9 -> 10 xu
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('life', -10))
        self.assertIn(row['kind'], jr.HISTORY_KINDS)
        self.assertEqual(SP(s)['stamps'], {'co_lan': 1})
        self.assertIn('Thẻ tích điểm 1/10', r['message'])
        self.assertTrue(r['effects'] and r['effects'][0] in C.QUAN_LINES)   # the shop being awkward, flavour only

    def test_tinh_than_once_a_life_day(self):
        s = story(500)
        s['journey'].setdefault('life', {})['spirit'] = 50
        s, r = act(s, 'jr_spend_eat', shop='lau_ba_sau', item='lau_mot_nguoi')
        self.assertEqual(s['journey']['life']['spirit'], 52)                 # a ≥ 31 xu meal (base 28): +2
        s, r = act(s, 'jr_spend_eat', shop='co_lan', item='bac_xiu')
        self.assertEqual(s['journey']['life']['spirit'], 52)                 # the second quán of the day: nothing
        self.assertNotIn('Tinh thần', r['message'])
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_spend_eat', shop='co_lan', item='bac_xiu')
        self.assertEqual(s['journey']['life']['spirit'], 53)

    def test_the_tenth_stamp_is_a_sticker(self):
        s = story(1000)
        for i in range(10):
            s, r = act(s, 'jr_spend_eat', shop='tra_sua_may', item='tra_sua_tc')
        self.assertEqual(SP(s)['stamps'], {'tra_sua_may': 0})
        self.assertEqual(SP(s)['stickers'], {'tra_sua_may': 1})
        self.assertIn('nhãn dán', r['message'])
        self.assertEqual(s['journey']['wallet'], 1000 - 130)

    def test_needs_bars_go_up_and_a_full_belly_refuses_food(self):
        s = story(500)
        n = nd.ensure(s)
        n.update(full=40, wake=40)
        s, r = act(s, 'jr_spend_eat', shop='pho_hang_may', item='pho_tai_lan')
        self.assertEqual(nd.get(s)['full'], 85)
        self.assertIn('No bụng 85', r['message'])
        nd.get(s)['full'] = nd.FULL_CAP
        refused(self, s, 'jr_spend_eat', 'too_full', shop='pho_hang_may', item='pho_tai_lan')
        s, _ = act(s, 'jr_spend_eat', shop='co_lan', item='bac_xiu')        # a drink still wakes you up
        self.assertEqual(nd.get(s)['wake'], 52)

    def test_refusals(self):
        s = story(5)
        self.assertIn('chưa đủ 10 xu', refused(self, s, 'jr_spend_eat', 'not_enough', shop='co_lan', item='ca_phe_muoi'))
        s = story(100)
        refused(self, s, 'jr_spend_eat', shop='co_lan', item='pho_tai_lan')     # not this shop's
        refused(self, s, 'jr_spend_eat', shop='co_lan', item='x')
        refused(self, s, 'jr_spend_eat', shop='co_lan', item='bac_xiu', price=1)
        refused(self, s, 'jr_spend_frobnicate')
        s['journey']['wallet'] = -3
        refused(self, s, 'jr_spend_eat', 'not_enough', shop='co_lan', item='bac_xiu')   # never into debt


class SpaFilm(unittest.TestCase):
    def test_spa_gives_tinh_than_the_first_time_a_day(self):
        s = story(200)
        s['journey'].setdefault('life', {})['spirit'] = 10
        s, r = act(s, 'jr_spend_spa', item='massage_chan')
        self.assertEqual((s['journey']['wallet'], s['journey']['life']['spirit']), (156, 12))
        s, r = act(s, 'jr_spend_spa', item='lam_mong')
        self.assertEqual((s['journey']['wallet'], s['journey']['life']['spirit']), (123, 12))
        self.assertIn('thư giãn rồi', r['message'])

    def test_one_film_a_week(self):
        s = story(200)
        with at(T0):
            s, r = act(s, 'jr_spend_film')
            self.assertEqual(s['journey']['wallet'], 200 - C.FILM_PRICE)
            refused(self, s, 'jr_spend_film', 'already_done')
            self.assertTrue(public_state(s)['journey']['spend']['seen'])
            film = sp.film_of()
        with at(T0 + 7 * 86400):
            s, _ = act(s, 'jr_spend_film')
            self.assertNotEqual(sp.film_of()['id'], film['id'])
        self.assertEqual(len(SP(s)['stubs']), 2)
        self.assertEqual(SP(s)['stats']['film'], 2)


class Give(unittest.TestCase):
    def test_wallet_then_bank_and_the_last_row(self):
        s, _ = act(story(300), 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=200)
        before = money(s)
        with at(T0):
            s, r = act(s, 'jr_spend_give', amount=250, wish='me_khoe', anon=False, confirm=True)
        self.assertEqual(money(s), before - 250)
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 50))
        self.assertIn(C.THANKS, r['message'])
        g = SP(s)['give']
        self.assertEqual(g['last'], dict(n=1, a=250, w='me_khoe', anon=False, wk=sp.week_key(T0), at=int(T0)))
        self.assertEqual((g['n'], g['sum'], g['wsum']), (1, 250, 250))
        with at(T0 + 7 * 86400):
            s, _ = act(s, 'jr_spend_give', amount=5, confirm=True)       # anonymous unless told otherwise
        g = SP(s)['give']
        self.assertEqual((g['wsum'], g['sum'], g['last']['anon']), (5, 255, True))

    def test_the_same_thanks_whatever_the_amount(self):
        s = story(10_000)
        msgs = []
        for a in (5, 5000):
            s, r = act(s, 'jr_spend_give', amount=a, confirm=True)
            msgs.append(r['message'].split('. ', 1)[1])
        self.assertEqual(msgs[0], msgs[1])

    def test_refusals(self):
        s = story(100)
        refused(self, s, 'jr_spend_give', amount=4, confirm=True)
        refused(self, s, 'jr_spend_give', amount=C.GIVE_MAX + 1, confirm=True)
        refused(self, s, 'jr_spend_give', amount=10)                                  # no confirm
        refused(self, s, 'jr_spend_give', amount=10, confirm=True, wish='free text')  # wishes come from a list
        refused(self, s, 'jr_spend_give', amount=10, confirm=True, anon='yes')
        refused(self, s, 'jr_spend_give', 'not_enough', amount=101, confirm=True)
        s['journey']['wallet'] = -1
        self.assertIn('Ví đang nợ', refused(self, s, 'jr_spend_give', 'not_enough', amount=5, confirm=True))


class Style(unittest.TestCase):
    def test_buy_wear_renew_and_expire(self):
        s = story(2000)
        with at(T0):
            s, r = act(s, 'jr_spend_style', id='c_ngoc', confirm=True)
            self.assertEqual(s['journey']['wallet'], 1835)                  # 💹 07/10: 150 -> 165 xu
            self.assertEqual(SP(s)['own']['c_ngoc'], int(T0) + C.WEEK_SECS)
            self.assertEqual(sp.style_now(s), {'c': 'c_ngoc'})
            s, _ = act(s, 'jr_spend_style', id='c_ngoc', confirm=True)          # renew: stacked
            self.assertEqual(SP(s)['own']['c_ngoc'], int(T0) + 2 * C.WEEK_SECS)
            s, _ = act(s, 'jr_spend_style', id='c_ngoc', confirm=True)
            s, _ = act(s, 'jr_spend_style', id='c_ngoc', confirm=True)
            self.assertIn('4 tuần', refused(self, s, 'jr_spend_style', 'limit', id='c_ngoc', confirm=True))
            s, _ = act(s, 'jr_spend_style', id='c_vang', confirm=True)
            self.assertEqual(sp.style_now(s), {'c': 'c_vang'})
            s, _ = act(s, 'jr_spend_wear', kind='color', id='c_ngoc')           # switch between colours owned
            self.assertEqual(sp.style_now(s), {'c': 'c_ngoc'})
            refused(self, s, 'jr_spend_wear', kind='frame', id='c_ngoc')       # wrong kind
            refused(self, s, 'jr_spend_wear', 'expired', kind='frame', id='f_tre')
            s, _ = act(s, 'jr_spend_wear', kind='color', id=None)
            self.assertEqual(sp.style_now(s), {})
            s, _ = act(s, 'jr_spend_wear', kind='color', id='c_vang')
        with at(T0 + C.WEEK_SECS + 1):
            self.assertEqual(sp.style_now(s), {})                               # c_vang ran out
            self.assertNotIn('c_vang', public_state(s)['journey']['spend']['own'])
            refused(self, s, 'jr_spend_wear', 'expired', kind='color', id='c_vang')
        self.assertEqual(s['journey']['wallet'], 2000 - 4 * 165 - 330)

    def test_some_titles_unlock_by_playing(self):
        s = story(2000)
        self.assertIn('Đi quán 10 lần', refused(self, s, 'jr_spend_style', 'locked', id='t_tin_do_cafe', confirm=True))
        for _ in range(10):
            s, _ = act(s, 'jr_spend_eat', shop='co_lan', item='bac_xiu')
        s, _ = act(s, 'jr_spend_style', id='t_tin_do_cafe', confirm=True)
        self.assertEqual(sp.style_now(s), {'t': 't_tin_do_cafe'})
        s, _ = act(s, 'jr_spend_style', id='t_dai_gia', confirm=True)       # no condition
        self.assertEqual(sp.style_now(s)['t'], 't_dai_gia')

    def test_bank_pays_the_rest_and_debt_buys_nothing(self):
        s, _ = act(story(500), 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=250)
        s, r = act(s, 'jr_spend_style', id='f_rong_may', confirm=True)
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 60))
        self.assertIn('từ tài khoản', r['message'])
        s['journey']['wallet'] = -1
        refused(self, s, 'jr_spend_style', 'not_enough', id='f_tre', confirm=True)

    def test_social_card_carries_the_style(self):
        s = story(500)
        with at(T0):
            s, _ = act(s, 'jr_spend_style', id='f_sen_vang', confirm=True)
            snap, _ = social.snapshot(s)
        self.assertEqual(snap['style'], {'f': 'f_sen_vang', 'u': int(T0) + C.WEEK_SECS})


class Money(unittest.TestCase):
    def test_no_command_creates_money_and_every_xu_is_written_down(self):
        rng = random.Random(7)
        s, _ = act(story(5000), 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=2000)

        def eat():
            i = rng.choice(list(sp.ITEMS))
            return dict(shop=sp.ITEMS[i][0], item=i)
        cmds = [('jr_spend_eat', eat),
                ('jr_spend_spa', lambda: dict(item=rng.choice(list(sp.SPA)))),
                ('jr_spend_film', lambda: {}),
                ('jr_spend_give', lambda: dict(amount=rng.choice((5, 20, 333)), confirm=True, anon=rng.random() < .5)),
                ('jr_spend_style', lambda: dict(id=rng.choice(list(C.STYLE_ITEMS)), confirm=True)),
                ('jr_spend_wear', lambda: dict(kind=rng.choice(C.KINDS), id=None))]
        spent = done = 0
        with at(T0):
            for i in range(300):
                if i % 25 == 0:
                    s['journey']['life_day'] += 1
                name, mk = rng.choice(cmds)
                m0, w0, h0 = money(s), s['journey']['wallet'], len(s['journey']['history'])
                try:
                    s, _ = act(s, name, **mk())
                except GameError:
                    continue
                done += 1
                d = m0 - money(s)
                self.assertGreaterEqual(d, 0, name)                                  # never creates money
                rows = s['journey']['history'][h0:]
                self.assertTrue(all(r['kind'] == 'life' for r in rows), rows)       # a kind every older build accepts
                self.assertEqual(sum(r['amount'] for r in rows), s['journey']['wallet'] - w0)   # the wallet's moves are all written
                spent += d
        validate_state(s)
        self.assertGreater(done, 60)
        self.assertEqual(SP(s)['stats']['xu'], spent)
        self.assertEqual(money(s), 5000 - spent)


class Saves(unittest.TestCase):
    def test_old_saves_have_no_block_and_stay_so(self):
        s = story(500)
        self.assertNotIn('spend', s['journey'])
        s2 = migrate_state(copy.deepcopy(s))
        self.assertNotIn('spend', s2['journey'])
        validate_state(s2)
        pub = public_state(s2)['journey']['spend']
        self.assertEqual(set(pub), {'story', 'film', 'seen', 'lock'})               # small: it rides on every state
        self.assertEqual(set(pub['lock']), {'t_tin_do_cafe', 't_mot_phim', 't_tam_long_vang'})
        s3, _ = act(s2, 'jr_spend_wear', kind='color', id=None)               # nothing to put away: no block made
        self.assertNotIn('spend', s3['journey'])

    def test_bad_blocks_are_refused(self):
        s, _ = act(story(500), 'jr_spend_give', amount=20, confirm=True)
        s, _ = act(s, 'jr_spend_style', id='c_tim', confirm=True)
        for bad in ({'v': 2}, {'extra': 1}, {'today': 'cafe'}, {'stamps': {'co_lan': 10}}, {'stamps': {'Co Lan': 1}},
                    {'film': '2026-41'}, {'stubs': ['x'] * 60}, {'own': {'c_tim': -1}}, {'wear': {'color': 'c_vang', 'frame': None, 'title': None}},
                    {'wear': {'color': None}}, {'stats': {'x': 1}}, {'stats': {'eat': -1}},
                    {'give': {'n': 1, 'sum': 20, 'wk': '', 'wsum': 0, 'last': {'n': 2}}},
                    {'give': {'n': 2, 'sum': 20, 'wk': '', 'wsum': 0, 'last': dict(SP(s)['give']['last'])}}):
            t = copy.deepcopy(s)
            SP(t).update(bad)
            with self.assertRaises(GameError, msg=bad):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['spend'] = []
        with self.assertRaises(GameError):
            validate_state(t)

    def test_a_newer_builds_block_is_kept_by_upgrade(self):
        s, _ = act(story(500), 'jr_spend_style', id='c_tim', confirm=True)
        t = copy.deepcopy(s)
        SP(t)['own']['c_2027'] = 2**33                     # an id this build does not know: kept, not shown
        SP(t)['wear']['color'] = 'c_2027'
        SP(t)['stamps']['quan_2027'] = 3
        SP(t)['extra'] = {'z': 1}                           # a field a newer build added: dropped by upgrade
        t.pop('check', None)
        t = migrate_state(t)
        validate_state(t)
        self.assertEqual(SP(t)['own']['c_2027'], 2**33)
        self.assertEqual(SP(t)['stamps']['quan_2027'], 3)
        self.assertNotIn('extra', SP(t))
        self.assertEqual(sp.style_now(t), {})
        self.assertNotIn('c_2027', public_state(t)['journey']['spend']['own'])


class Live(unittest.TestCase):
    def test_style_rows_are_read_by_kind_and_expiry(self):
        from live import styles
        now = 1000.0
        row = dict(color='c_ngoc', color_until=2000.0, frame='f_tre', frame_until=999.0, title='c_dao', title_until=5000.0)
        self.assertEqual(styles.public(row, now), {'c': 'c_ngoc'})        # the frame ran out, a colour is not a title
        self.assertEqual(styles.public(dict(row, title='t_mot_phim'), now), {'c': 'c_ngoc', 't': 't_mot_phim'})
        self.assertEqual(styles.public(dict(row, color='<script>'), now), {})
        self.assertEqual(styles.public(None, now), {})
        self.assertEqual(styles.title_text({'t': 't_mot_phim'}), '🎬 Mọt phim')

    def test_cache_and_a_database_without_the_table(self):
        from live import styles
        from live.db import Error as DbError

        class DB:
            calls = 0
            missing = False

            async def fetch(self, sql, args=()):
                DB.calls += 1
                if DB.missing:
                    raise DbError[0]('no table')
                return [dict(pid=p, color='c_dao', color_until=2**40, frame='', frame_until=0, title='', title_until=0) for p in args if p == 'a']

        class App:
            db = DB()

        app = App()
        got = asyncio.run(styles.of_app(app).of(['a', 'b']))
        self.assertEqual(got, {'a': {'c': 'c_dao'}, 'b': {}})
        asyncio.run(styles.of_app(app).of(['a', 'b']))
        self.assertEqual(DB.calls, 1)                       # cached
        styles.of_app(app).forget('a')                      # a NOTIFY
        asyncio.run(styles.of_app(app).of(['a']))
        self.assertEqual(DB.calls, 2)
        app2 = App()
        DB.missing = True
        self.assertEqual(asyncio.run(styles.of_app(app2).of(['a'])), {'a': {}})
        self.assertEqual(asyncio.run(styles.of_app(app2).of(['c'])), {'c': {}})
        self.assertEqual(DB.calls, 3)                       # not asked again before RETRY
        frames = asyncio.run(styles.with_styles(app, [dict(pid='a', text='x'), dict(pid='z', text='y', st={'c': 'c_dao'})]))
        self.assertEqual(frames, [dict(pid='a', text='x', st={'c': 'c_dao'}), dict(pid='z', text='y')])


class Database(unittest.TestCase):
    """The rows written in the save's own transaction (game/storage.py → spend.command_commit) and the board."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        sp._BOARD.clear()

    def player(self, wallet=5000, name='Lan'):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {self.store.key(token): fn})
        return token

    def cmd(self, token, action, n=[0], **p):
        n[0] += 1
        return self.store.command(token, f'req-{n[0]:08d}', self.store.read(token)[1], None, action, p)

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def test_donations_and_the_board(self):
        a, b = self.player(), self.player(name='Minh')
        sid_a = self.store.key(a)
        with at(T0):
            out = self.cmd(a, 'jr_spend_give', amount=200, anon=False, wish='binh_an', confirm=True)
            self.assertEqual(out['state']['journey']['wallet'], 4800)
            self.cmd(a, 'jr_spend_give', amount=50, anon=True, confirm=True)
            self.cmd(b, 'jr_spend_give', amount=1000, anon=False, confirm=True)   # a guest: never by name
            rev = self.store.read(a)[1]
            self.store.command(a, 'req-same-1', rev, None, 'jr_spend_give', dict(amount=50, anon=True, confirm=True))
            r2 = self.store.command(a, 'req-same-1', rev, None, 'jr_spend_give', dict(amount=50, anon=True, confirm=True))
            self.assertTrue(r2['replayed'])                                        # a retry pays and writes once
            self.assertEqual(self.store.read(a)[0]['journey']['wallet'], 4700)
            rows = self.rows('SELECT id, amount, anon, week FROM donations ORDER BY at, id')
            self.assertEqual(len(rows), 4)
            self.assertEqual({x['week'] for x in rows}, {sp.week_key(T0)})
            self.assertEqual(sp.board(self.store, a)['mine'], 300)
            with self.store.connect() as db:   # Lan signs up: her named gift shows her account's display name
                db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES('lan', 'Lan Mây', 'x', ?)", (sid_a,))
            sp._BOARD.clear()
            board = sp.board(self.store, b)
        self.assertEqual(board['xu'], 1300)
        self.assertEqual(board['people'], 2)
        self.assertEqual([(x['name'], x['xu'], x['me']) for x in board['top']],
                         [('Ẩn danh', 1000, True), ('Lan Mây', 200, False), ('Ẩn danh', 100, False)])
        self.assertTrue(all('sid' not in x for x in board['top'] + board['recent']))
        self.assertIn('Cầu bình an', [x['wish'] for x in board['recent']])
        self.store.delete(b)                                                       # erased: stays on the board as anonymous
        self.assertEqual({x['sid'] for x in self.rows('SELECT sid FROM donations')}, {sid_a, ''})
        with at(T0):
            self.assertEqual(sp.board(self.store, None)['xu'], 1300)

    def test_style_row_follows_what_is_worn(self):
        from game.live_chat import pid_of
        a = self.player()
        with at(T0):
            self.cmd(a, 'jr_spend_style', id='c_dao', confirm=True)
            self.cmd(a, 'jr_spend_style', id='t_hang_xom', confirm=True)
        row = self.rows('SELECT * FROM chat_style')[0]
        self.assertEqual(row['pid'], pid_of(self.store.key(a)))
        self.assertEqual((row['color'], row['frame'], row['title']), ('c_dao', '', 't_hang_xom'))
        self.assertEqual(row['color_until'], int(T0) + C.WEEK_SECS)
        from live import styles
        self.assertEqual(styles.public(row, T0), {'c': 'c_dao', 't': 't_hang_xom'})
        with at(T0):
            self.cmd(a, 'jr_spend_wear', kind='color', id=None)
            self.assertEqual(self.rows('SELECT color, title FROM chat_style'), [dict(color='', title='t_hang_xom')])
            self.cmd(a, 'jr_spend_wear', kind='title', id=None)
        self.assertEqual(self.rows('SELECT * FROM chat_style'), [])


if __name__ == '__main__':
    unittest.main()
