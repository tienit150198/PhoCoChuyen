"""🛍️ Mua sắm (game/lux.py, game/estates.py; owner 07/10 "đưa ra nhiều cái mà mọi người sẽ mua … mọi người nhiều tiền quá
rồi"): the catalogue and its price bands, money (never created: every xu leaves through the wallet history or the bank
log, selling back always loses), the visa's paperwork, trips and souvenirs, collections and wine, villas lived in (their
rooms, floors, the living cost, Sông Hồng's bigger inside), parties, courses, the bills, titles worn through spend.py,
saves (absent block, strict shape, a newer build's block) and the public sponsorships written with the save."""
import copy
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game import bank as bk
from game import deco as dc
from game import estates as es
from game import estates_content as EC
from game import journey as jr
from game import lux
from game import lux_content as C
from game import spend as sp
from game import spend_content as SC
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act, story

T0 = 1_791_300_000.0          # a Tuesday (2026-10-06, Vietnam time)


def LX(s):
    return s['journey']['lux']


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


def rich(wallet=5_000_000, bank=0):
    s = story(wallet + bank)
    if bank:
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=bank)
    return s


def next_day(s, n=1):
    for _ in range(n):
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_seen', ids=['x'])   # any command: journey.after runs every morning's catch-up
    return s


class Catalogue(unittest.TestCase):
    def test_prices_sit_where_the_money_is(self):
        # DESIGN_0610 §0.1: p90 wallets 3,300, p99 26,400, the top 1.6–3.4 M; nothing cost more than 150,000 before
        tops = [it['price'] for st in C.SETS for it in st['items']] + [a['price'] for a in C.ASSETS] + [e['price'] for e in EC.ESTATES]
        self.assertGreater(max(tops), 1_500_000)
        self.assertTrue(all(1000 <= p <= 5_000_000 for p in tops))
        self.assertEqual(sorted(e['price'] for e in EC.ESTATES), [e['price'] for e in EC.ESTATES])   # rising
        self.assertGreater(EC.ESTATES[0]['price'], 60000)                                        # above Sông Hồng
        for c in C.COUNTRIES:
            self.assertTrue(4000 <= c['trip'] <= 30000 and c['visa'] < c['trip'])
        self.assertEqual([c['mult'] for c in C.CLASSES], [1, 3, 10])
        for c in C.COURSES:
            self.assertTrue(4000 <= c['price'] <= 500000)
        self.assertTrue(50 <= C.SELL_PCT <= 65)

    def test_ids_unique_and_shaped(self):
        ids = (list(lux.PIECE) + list(lux.ASSET) + list(lux.ESTATE) + list(lux.SOUV) + list(lux.COURSE) + list(lux.GIVE)
               + list(lux.COUNTRY) + [t['id'] for t in C.PARTY_TIERS] + [k['id'] for k in C.PARTY_KINDS])
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids:
            self.assertRegex(i, lux.ID_RE.pattern)
        self.assertEqual({t for t, _, _ in C.EARN}, {x['id'] for x in SC.LUX_TITLES})
        self.assertEqual(jr.content()['lux'], lux.catalogue())

    def test_never_pay_to_win(self):
        # No command of the catalogue pays xu: only selling back, always below the price paid.
        import inspect
        src = inspect.getsource(lux)
        self.assertEqual(src.count("_wallet(s['journey'], back"), 1)
        self.assertNotIn("'salary'", src)


class Money(unittest.TestCase):
    def test_buy_and_sell_back_at_a_loss(self):
        s = rich(500_000, bank=200_000)
        before = money(s)
        s, r = act(s, 'jr_lux_buy', id='dh_tourbillon', confirm=True)
        self.assertEqual(money(s), before - 250_000)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'life')
        s, r = act(s, 'jr_lux_sell', id='dh_tourbillon', confirm=True)
        self.assertEqual(money(s), before - 250_000 + 150_000)       # 60 %
        self.assertNotIn('dh_tourbillon', LX(s)['own'])

    def test_the_wallet_then_the_bank_never_a_loan(self):
        s = rich(100_000, bank=900_000)
        s, r = act(s, 'jr_lux_buy', id='tr_son_dau', confirm=True)   # 350,000
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 650_000)
        self.assertIn('từ tài khoản', r['message'])
        refused(self, s, 'jr_lux_buy', 'not_enough', id='tr_kiet_tac', confirm=True)
        s['journey']['wallet'] = -5
        refused(self, s, 'jr_lux_buy', 'not_enough', id='tr_dong_ho', confirm=True)   # a wallet in debt buys nothing

    def test_no_money_is_ever_created(self):
        rnd = random.Random(7)
        s = rich(3_000_000, bank=1_000_000)
        s['journey']['days'] = [dict(c=c, d=1, m='normal') for c in list(jr.CAREERS)[:3]]
        paid = {}
        cmds = [('jr_lux_buy', lambda: dict(id=rnd.choice(list(lux.GOODS)), confirm=True)),
                ('jr_lux_sell', lambda: dict(id=rnd.choice(list(lux.GOODS)), confirm=True)),
                ('jr_lux_open', lambda: dict(id=rnd.choice([i for i in lux.PIECE if lux.PIECE[i]['set'] == 'ruou']), confirm=True)),
                ('jr_lux_party', lambda: dict(kind='sinh_nhat', tier=rnd.choice(list(lux.PARTY_TIER)), guests=rnd.choice((5, 50, 100)), confirm=True)),
                ('jr_lux_course', lambda: dict(id=rnd.choice(list(lux.COURSE)), confirm=True)),
                ('jr_lux_study', lambda: dict(id=rnd.choice(list(lux.COURSE)))),
                ('jr_lux_photo', lambda: {}),
                ('jr_lux_use', lambda: dict(id=rnd.choice(list(lux.ASSET)))),
                ('jr_lux_live', lambda: dict(id=rnd.choice(list(lux.ESTATE) + [None])))]
        for step in range(400):
            name, p = rnd.choice(cmds)
            p = p()
            before, owned = money(s), dict(LX(s)['own']) if s['journey'].get('lux') else {}
            try:
                s, _ = act(s, name, **p)
            except GameError:
                continue
            gain = money(s) - before
            if name == 'jr_lux_sell':
                self.assertEqual(gain, lux.sell_price(owned[p['id']]['p']))
                self.assertLess(gain, owned[p['id']]['p'])
            else:
                self.assertLessEqual(gain, 0, (name, p))
            if step % 40 == 0:
                s = next_day(s)
        validate_state(s)


class Visa(unittest.TestCase):
    def test_paperwork_refusals_keep_the_fee(self):
        s = rich(50_000)
        r = refused(self, s, 'jr_lux_trip', 'no_visa', country='trung_quoc', cls='pho_thong', confirm=True)
        self.assertIn('visa', r)
        s, r = act(s, 'jr_lux_visa', country='trung_quoc', docs=['anh', 'sao_ke'], confirm=True)
        self.assertTrue(r['refused'])
        self.assertIn('thiếu ảnh', r['message'])
        self.assertEqual(s['journey']['wallet'], 50_000 - 300)        # the fee is kept
        s, _ = act(s, 'jr_lux_photo')
        s, r = act(s, 'jr_lux_visa', country='trung_quoc', docs=['anh', 'sao_ke'], confirm=True)
        self.assertIn('tài khoản ngân hàng', r['message'])
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=4000)
        s, r = act(s, 'jr_lux_visa', country='trung_quoc', docs=['anh', 'sao_ke'], confirm=True)
        self.assertIn('sao kê chưa đủ 4.500', r['message'])
        s, _ = act(s, 'jr_bk_deposit', amount=1000)
        s, r = act(s, 'jr_lux_visa', country='trung_quoc', docs=['sao_ke'], confirm=True)
        self.assertIn('thiếu ảnh', r['message'])                     # forgot to attach it
        s, r = act(s, 'jr_lux_visa', country='trung_quoc', docs=['anh', 'sao_ke', 'lich_trinh'], confirm=True)
        self.assertNotIn('refused', r)                                  # an extra paper does no harm
        self.assertEqual(lux.visa_left(s, 'trung_quoc'), 30)
        refused(self, s, 'jr_lux_visa', 'already_done', country='trung_quoc', docs=['anh'], confirm=True)
        s = next_day(s, C.PHOTO_DAYS)
        self.assertIn('ảnh chụp quá', lux.doc_problem(s, 'trung_quoc', 'anh'))
        self.assertEqual(lux.visa_left(s, 'trung_quoc'), 0)           # 30 life days

    def test_us_interview_and_the_english_course(self):
        s = rich(500_000, bank=60_000)
        s['journey']['days'] = [dict(c=c, d=1, m='normal') for c in list(jr.CAREERS)[:3]]
        s, _ = act(s, 'jr_lux_photo')
        docs = ['anh', 'sao_ke', 'cong_viec', 'lich_trinh']
        qs = lux.asked(s, 'my')
        self.assertEqual(len(qs), 3)
        wrong = [(C.INTERVIEW[q]['ok'] + 1) % 3 for q in qs]
        s, r = act(s, 'jr_lux_visa', country='my', docs=docs, answers=wrong, confirm=True)
        self.assertIn('phỏng vấn', r['message'])
        qs = lux.asked(s, 'my')
        s, r = act(s, 'jr_lux_visa', country='my', docs=docs, answers=[C.INTERVIEW[q]['ok'] for q in qs], confirm=True)
        self.assertNotIn('refused', r)
        s, _ = act(s, 'jr_lux_course', id='tieng_anh', confirm=True)
        for _ in range(5):
            s, _ = act(s, 'jr_lux_study', id='tieng_anh')
            s = next_day(s)
        self.assertEqual(len(lux.asked(s, 'my')), 1)

    def test_europe_wants_its_insurance_once(self):
        s = rich(500_000, bank=80_000)
        s['journey']['days'] = [dict(c=c, d=1, m='normal') for c in list(jr.CAREERS)[:3]]
        s, _ = act(s, 'jr_lux_photo')
        docs = ['anh', 'sao_ke', 'cong_viec', 'lich_trinh', 'bao_hiem']
        s, r = act(s, 'jr_lux_visa', country='chau_au', docs=docs, confirm=True)
        self.assertIn('bảo hiểm', r['message'])
        s, _ = act(s, 'jr_lux_insure', country='chau_au')
        self.assertEqual(LX(s)['ins'], 'chau_au')
        s, r = act(s, 'jr_lux_visa', country='chau_au', docs=docs, confirm=True)
        self.assertNotIn('refused', r)
        self.assertEqual(LX(s)['ins'], '')


class Trips(unittest.TestCase):
    def granted(self, cid='han_quoc'):
        s = rich(3_000_000)
        b = lux._ensure(s)
        b['visa'][cid] = s['journey']['life_day'] + 10
        return s

    def test_a_trip_a_day_any_class_souvenirs_that_day(self):
        s = self.granted()
        s['journey'].setdefault('life', {})['spirit'] = 50
        before = money(s)
        s, r = act(s, 'jr_lux_trip', country='han_quoc', cls='hoang_gia', confirm=True)
        self.assertEqual(money(s), before - 65_000)
        self.assertEqual(LX(s)['trips'], {'han_quoc': 1})
        self.assertEqual(LX(s)['album'][-1], dict(k='trip', i='han_quoc', c='hoang_gia', d=s['journey']['life_day'], n=1))
        self.assertEqual(s['journey']['life']['spirit'], 53)
        self.assertTrue(r['effects'] and r['effects'][0] in C.TRIP_LINES['han_quoc'])
        refused(self, s, 'jr_lux_trip', 'already_done', country='han_quoc', cls='pho_thong', confirm=True)
        s, _ = act(s, 'jr_lux_souv', id='hong_sam')
        self.assertEqual(LX(s)['souv'], {'hong_sam': 1})
        refused(self, s, 'jr_lux_souv', 'locked', id='dao_seki')        # Japan's: not there today
        s = next_day(s)
        refused(self, s, 'jr_lux_souv', 'locked', id='hong_sam')        # back home

    def test_three_countries_earn_a_title_worn_in_chat(self):
        s = rich(3_000_000)
        b = lux._ensure(s)
        for c in ('trung_quoc', 'han_quoc', 'nhat_ban'):
            b['visa'][c] = 99
        for c in ('trung_quoc', 'han_quoc', 'nhat_ban'):
            s, r = act(s, 'jr_lux_trip', country=c, cls='pho_thong', confirm=True)
            s = next_day(s)
        self.assertIn('Dân xê dịch', r['message'])
        self.assertEqual(s['journey']['spend']['own']['t_xe_dich'], SC.PERMANENT)
        refused(self, s, 'jr_spend_style', 'limit', id='t_xe_dich', confirm=True)    # never sold, never renewed
        refused(self, s, 'jr_spend_style', 'locked', id='t_toan_cau', confirm=True)
        with patch('game.spend.now', lambda: T0):
            s, _ = act(s, 'jr_spend_wear', kind='title', id='t_xe_dich')
            self.assertEqual(sp.style_now(s, T0), {'t': 't_xe_dich'})
        from live import styles
        self.assertEqual(styles.title_text({'t': 't_xe_dich'}), '🧳 Dân xê dịch')


class Collections(unittest.TestCase):
    def test_one_of_each_wine_opens_once(self):
        s = rich(1_000_000)
        s['journey'].setdefault('life', {})['spirit'] = 50
        s, _ = act(s, 'jr_lux_buy', id='rv_1945', confirm=True)
        s, r = act(s, 'jr_lux_buy', id='rv_1945', confirm=True)
        self.assertTrue(r.get('duplicate'))
        before = money(s)
        s, r = act(s, 'jr_lux_open', id='rv_1945', confirm=True)
        self.assertEqual(money(s), before)                              # no money back
        self.assertNotIn('rv_1945', LX(s)['own'])
        self.assertEqual(s['journey']['life']['spirit'], 53)
        refused(self, s, 'jr_lux_open', None, id='dh_co_sg', confirm=True)   # only wine

    def test_titles_for_collectors(self):
        s = rich(3_000_000)
        for i in ('tr_dong_ho', 'tr_son_mai', 'tr_lua_co', 'tg_to_he'):
            s, _ = act(s, 'jr_lux_buy', id=i, confirm=True)
        self.assertNotIn('t_suu_tam', s['journey'].get('spend', {}).get('own', {}))
        s, r = act(s, 'jr_lux_buy', id='tg_ngua_tram', confirm=True)
        self.assertIn('Nhà sưu tầm', r['message'])
        s, r = act(s, 'jr_lux_buy', id='tg_ky_lan', confirm=True)
        self.assertIn('Chủ báu vật', r['message'])


class Estates(unittest.TestCase):
    def test_live_in_a_villa_its_rooms_and_floors(self):
        s = rich(5_000_000)
        s, r = act(s, 'jr_lux_buy', id='dinh_thu_dao', confirm=True)
        self.assertIn('Chủ dinh thự', r['message'])
        self.assertIn('Chúa đảo', r['message'])
        refused(self, s, 'jr_lux_live', 'not_owned', id='bt_kinh')
        s, r = act(s, 'jr_lux_live', id='dinh_thu_dao')
        pl = dc.place(s['journey'])
        self.assertEqual(pl, dict(key='estate:dinh_thu_dao:1', where='estate', kind='dinh_thu_dao'))
        rooms = dc.rooms_of(pl['key'])
        types = {r['type'] for r in rooms}
        self.assertTrue({'cinema', 'cellar', 'gym', 'closet', 'showroom', 'study', 'suite', 'terrace', 'infinity', 'pavilion'} <= types)
        self.assertEqual({r['fl'] for r in rooms}, {1, 2, 3})
        song_hong = dc.rooms_of('own:h1:biet_thu_song')                 # the inside 1.9.9 draws
        self.assertGreater(max(r['cols'] for r in rooms), max(r['cols'] for r in song_hong))
        self.assertGreater(sum(r['cols'] * r['frows'] for r in rooms), 3 * sum(r['cols'] * r['frows'] for r in song_hong))
        self.assertEqual(jr.living_cost(s['journey'])['rent'], 80)
        v = public_state(s)['journey']['deco']
        self.assertEqual(v['place']['name'], 'Dinh thự đảo Hòn Mây')
        self.assertTrue(all('fl' in r for r in v['rooms']))
        # a villa piece in its room, an older piece in a villa room
        s, r = act(s, 'jr_deco_buy', item='ghe_rap_doi', confirm=True, put=dict(r='cinema', x=40, y=20))
        s, r = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='cinema', x=120, y=40))
        self.assertEqual({q['r'] for q in s['journey']['decor']['items'].values()}, {'cinema'})
        validate_state(s)
        # the pool counts for Thư giãn
        from game import relax
        self.assertNotEqual(relax.why_not(s, 'nam'), 'Nhà này không có hồ bơi')
        s, r = act(s, 'jr_lux_sell', id='dinh_thu_dao', confirm=True)
        self.assertIsNone(LX(s)['live'])
        self.assertEqual(dc.place(s['journey'])['where'], 'attic')

    def test_the_monthly_bill_and_never_a_debt(self):
        s = rich(260_000)
        s, _ = act(s, 'jr_lux_buy', id='bt_vuon_da_lat', confirm=True)   # 150,000 × 0,4 % a tháng = 600
        s, _ = act(s, 'jr_lux_buy', id='dh_van_nien', confirm=True)      # 60,000: insured, 0,2 % = 120
        self.assertEqual(lux.monthly(s), 720)
        w = s['journey']['wallet']
        s = next_day(s, 5)                                               # life day 6: one bill at day 5
        self.assertEqual(w - s['journey']['wallet'], 720 * 4 // 5)      # days 2..5 only (bought on day 1)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'upkeep')
        s['journey']['wallet'] = 10
        s = next_day(s, 5)
        self.assertEqual(s['journey']['wallet'], 0)                      # waived, never below 0
        validate_state(s)

    def test_song_hong_owners_get_three_floors_and_keep_their_room(self):
        from tests.test_deco import owner
        s = owner('biet_thu_song', wallet=90000)
        old_key = dc._place(s['journey'])['key']
        self.assertEqual(dc.place(s['journey'])['key'], old_key + ':v2')
        s, r = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=40, y=40))
        rooms = dc.rooms_of(old_key + ':v2')
        self.assertEqual({r['fl'] for r in rooms}, {1, 2, 3})
        self.assertTrue({'living', 'bed', 'bed2', 'kitchen', 'yard', 'bath', 'pool', 'study', 'suite', 'terrace'} <= {r['id'] for r in rooms})
        # a layout from before (or by 1.9.9 since) is the same place
        t = copy.deepcopy(s)
        for k in ('deco', 'decor'):
            t['journey'][k]['at'] = old_key
        jr.upgrade(t['journey'])
        self.assertEqual(t['journey']['decor']['at'], old_key + ':v2')
        self.assertEqual(t['journey']['decor']['items'], s['journey']['decor']['items'])
        validate_state(t)


class PartiesCourses(unittest.TestCase):
    def test_a_housewarming_needs_a_home(self):
        s = rich(1_000_000)
        refused(self, s, 'jr_lux_party', 'locked', kind='tan_gia', tier='binh_dan', guests=10, confirm=True)
        refused(self, s, 'jr_lux_party', None, kind='sinh_nhat', tier='binh_dan', guests=7, confirm=True)   # steps of 5
        s, r = act(s, 'jr_lux_party', kind='sinh_nhat', tier='hoang_gia', guests=100, confirm=True)
        self.assertEqual(1_000_000 - s['journey']['wallet'], 200_000 + 4000 * 100)
        refused(self, s, 'jr_lux_party', 'already_done', kind='sinh_nhat', tier='binh_dan', guests=5, confirm=True)

    def test_a_lesson_a_day_and_a_title_at_the_end(self):
        s = rich(1_000_000)
        refused(self, s, 'jr_lux_study', 'locked', id='mba')
        s, _ = act(s, 'jr_lux_course', id='mba', confirm=True)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'study')
        for n in range(10):
            s, r = act(s, 'jr_lux_study', id='mba')
            if n < 9:
                refused(self, s, 'jr_lux_study', 'already_done', id='mba')
            s = next_day(s)
        self.assertIn('Thạc sĩ MBA', r['message'])
        refused(self, s, 'jr_lux_study', 'already_done', id='mba')


class Saves(unittest.TestCase):
    def test_absent_block_and_a_newer_builds_block(self):
        s = story(100)
        self.assertNotIn('lux', s['journey'])
        pub = public_state(s)['journey']['lux']
        self.assertEqual(set(pub), {'story', 'ask', 'month', 'next'})
        s2 = rich(3_000_000)
        s2, _ = act(s2, 'jr_lux_buy', id='bt_kinh', confirm=True)
        s2, _ = act(s2, 'jr_lux_live', id='bt_kinh')
        j = copy.deepcopy(s2['journey'])
        j['lux']['future'] = 1
        j['lux']['own']['some_new_villa'] = dict(d=1, p=9_000_000)
        lux.upgrade(j)
        self.assertNotIn('future', j['lux'])
        self.assertIn('some_new_villa', j['lux']['own'])                 # kept by shape, not shown
        t = dict(s2, journey=j)
        validate_state(t)
        self.assertNotIn('some_new_villa', public_state(t)['journey']['lux']['own'])
        bad = copy.deepcopy(s2)
        bad['journey']['lux']['live'] = 'bt_bien'                         # not owned
        with self.assertRaises(GameError):
            validate_state(bad)


class Database(unittest.TestCase):
    """The rows written in the save's own transaction (game/storage.py → lux.command_commit) and the board."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        lux._BOARD.clear()

    def player(self, wallet=2_000_000, name='Lan'):
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
        return self.store.command(token, f'lux-{n[0]:08d}', self.store.read(token)[1], None, action, p)

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def test_plaques_fireworks_board(self):
        a, b = self.player(), self.player(name='Minh')
        self.cmd(a, 'jr_lux_give', kind='ghe_da', slot=7, msg='me', confirm=True)
        with self.assertRaises(GameError) as cm:                         # the same bench: refused, nothing paid
            self.cmd(b, 'jr_lux_give', kind='ghe_da', slot=7, msg='bo', confirm=True)
        self.assertEqual(cm.exception.code, 'taken')
        self.assertEqual(self.store.read(b)[0]['journey']['wallet'], 2_000_000)
        self.cmd(b, 'jr_lux_give', kind='ghe_da', slot=8, msg='bo', anon=True, confirm=True)
        self.cmd(a, 'jr_lux_give', kind='phao_hoa', size='lon', confirm=True)
        with self.assertRaises(GameError) as cm:                         # one show at a time on the whole street
            self.cmd(b, 'jr_lux_give', kind='phao_hoa', size='nho', confirm=True)
        self.assertEqual(cm.exception.code, 'busy')
        self.assertEqual(self.store.read(b)[0]['journey']['wallet'], 2_000_000 - 30_000)
        self.cmd(b, 'jr_lux_give', kind='thu_vien', amount=250_000, confirm=True)
        self.cmd(a, 'jr_lux_give', kind='hoi_cho', confirm=True)
        news = [r['text'] for r in self.rows("SELECT text FROM news WHERE kind='lux' ORDER BY id")]
        self.assertTrue(any('pháo hoa lớn' in t and lux.GUEST_NAME in t for t in news), news)   # a guest is never named
        chat = self.rows("SELECT pid, channel, text FROM chat_messages WHERE channel='town'")
        self.assertEqual(len(chat), 1)
        self.assertEqual(chat[0]['pid'], 'admin')
        self.assertEqual(lux.board(self.store, a)['mine'], 260_000)
        with self.store.connect() as db:   # Lan signs up: the board shows her account's display name
            db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES('lan', 'Lan Mây', 'x', ?)", (self.store.key(a),))
        lux._BOARD.clear()
        board = lux.board(self.store, a)
        self.assertEqual(board['xu'], 30_000 + 30_000 + 80_000 + 250_000 + 150_000)
        self.assertEqual([(x['name'], x['xu']) for x in board['top']],
                         [('Lan Mây', 260_000), (lux.GUEST_NAME, 250_000), (lux.ANON_NAME, 30_000)])   # a guest is never named
        self.assertEqual(board['banners'], {'hoi_cho': 'Lan Mây'})
        self.assertEqual(board['library'], dict(name=lux.GUEST_NAME, xu=250_000))
        self.assertEqual({(p['k'], p['s'], p['name']) for p in board['plaques']}, {('ghe_da', 7, 'Lan Mây'), ('ghe_da', 8, lux.ANON_NAME)})
        self.assertGreater(board['fw_wait'], 0)
        self.store.delete(b)                                              # erased: what Minh gave stays, anonymous
        lux._BOARD.clear()
        self.assertEqual(lux.board(self.store, None)['library'], dict(name=lux.ANON_NAME, xu=250_000))
        self.assertEqual({r['sid'] for r in self.rows("SELECT sid FROM lux_gifts WHERE anon=1")}, {''})
