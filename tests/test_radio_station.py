"""📻 Đài Sóng Mây for players (game/radio_station.py): a radio player sells airtime on the town ticker through 🛎️ Phố dịch vụ.

Real accounts on one store: both services registered at the NPC base × 3; the buyer's words moderated before any money moves
(links, phones, contact ids, heavy words, length); the DJ airs an order from the station's desk (take + deliver with the pick),
the line runs on the ticker for its window, the DJ gets 95 % and 5 % is burned (money conserved); the generic "Xong việc" is
refused (the DJ must read it at the desk); a song dedication needs a DJ past probation; the caps (lines on air at once, a
buyer's lines a day, a DJ's a day) hold under the advisory lock; a line is taken down by its buyer, its DJ or an admin and
never deleted; a retried air pays once; the kill switch MNL_RADIO_OFF stops new orders, airings and the ticker; a deleted
account's lines leave the ticker."""
import os
import time
from unittest.mock import patch

from game import marriage as mr
from game import radio_station as rs
from game import service_market as sm
from game.employment import hired_record
from tests.test_service_market import _Helpers


class Base(_Helpers):
    def setUp(self):
        super().setUp()
        rs.install()
        rs.stale()
        self.addCleanup(rs.stale)

    def dj(self, name='rd_dj', promoted=False):
        tok = self.user(name)
        mr._mutate(self.store, {self.sid(tok): lambda s: s['careers']['radio'].update(job=hired_record('radio'))})
        self.cmd(tok, 'select_career', career='radio', confirm=True)
        self.cmd(tok, 'start_day', career='radio')
        if promoted:
            def up(s):
                d = s['careers']['radio']['ext']['data']
                d['stats'].update(jobs=3, good=3, news_days=3, active_days=0)
                d['stats']['roles']['news'] = 3
                d['promoted'] = True
            mr._mutate(self.store, {self.sid(tok): up})
        return tok

    def sell(self, tok, service=rs.AD, mode='fixed', mult=3, on=True):
        return self.post(tok, 'settings', career='radio', service=service, on=on, mode=mode, mult=mult)

    def buy(self, buyer, dj, service=rs.AD, note='Trà sữa Mây giảm 20% cả tuần, ghé nha!', **kw):
        self.rid += 1
        return self.post(buyer, 'order', pid=self.pid(dj), career='radio', service=service, note=note, rid=f'rd-{self.rid:08d}', **kw)['order']

    def air(self, dj, order, pick=None, ok=True):
        pick =pick or rs.picks(order['service'])[0]['id']
        return rs.post(self.store, dj, None, 'air', dict(order=order['id'], pick=pick, ok=ok))

    def lines(self):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM radio_lines ORDER BY created_at').fetchall()]


class Services(Base):
    def test_both_services_at_npc_price_times_three(self):
        d = self.dj()
        self.sell(d)
        with self.store.connect() as db:
            q = sm.quote(db, self.sid(d), 'radio', rs.AD)
            self.assertEqual((q['base'], q['mult'], q['price']), (rs.BASE[rs.AD], 3, rs.BASE[rs.AD] * 3))
        spec = sm.get_spec('radio', rs.SONG)
        self.assertEqual(spec['base'], rs.BASE[rs.SONG])
        self.assertTrue(spec['note_hint'])
        self.assertEqual(sm.FEE_PCT, 5)

    def test_moderation_refuses_before_any_money_moves(self):
        d, b = self.dj(), self.user('rd_buyer')
        self.sell(d)
        before = self.total(b)
        for note in ('', 'chào', 'Ghé www.muaban.vn nhé bà con', 'Gọi 0903 123 456 để đặt', 'Add zalo minh1234 nha',
                     'Đồ lồn ai không mua', 'x' * (rs.TEXT_MAX + 1), 'Tiệm này bitch thật'):
            with self.subTest(note=note[:20]):
                with self.assertRaises(mr.MarriageError) as cm:
                    self.buy(b, d, note=note)
                self.assertIn(cm.exception.code, ('bad_note', 'bad_text', 'blocked_link', 'blocked_contact'))
        self.assertEqual(self.total(b), before, 'nothing was held')
        self.assertEqual(rs.moderate('Trà sữa Mây giảm 20% cả tuần, ghé nha!'), ('Trà sữa Mây giảm 20% cả tuần, ghé nha!', ''))

    def test_an_ad_airs_on_the_ticker_and_pays_95_burns_5(self):
        d, b = self.dj(), self.user('rd_shop')
        self.sell(d)
        td, tb = self.total(d), self.total(b)
        o = self.buy(b, d)
        price = rs.BASE[rs.AD] * 3
        self.assertEqual((o['status'], o['price']), ('held', price))
        self.assertEqual(self.total(b), tb - price)
        desk = rs.get(self.store, d, None, 'desk', {})
        self.assertEqual([x['id'] for x in desk['orders']], [o['id']])
        self.assertTrue(desk['orders'][0]['preview'].startswith('📢 '))
        out = self.air(d, o)
        self.assertEqual(out['order']['status'], 'done')
        fee = sm.fee_of(price)
        self.assertEqual(self.total(d), td + price - fee)
        self.assertEqual((tb - price) - self.total(b), 0)
        self.assertEqual(tb - self.total(b) - (self.total(d) - td), fee, 'money conserved: buyer − DJ = the burned 5 %')
        line = self.lines()[0]
        self.assertEqual((line['kind'], line['buyer'], line['provider'], line['hidden']), (rs.AD, self.sid(b), self.sid(d), 0))
        self.assertAlmostEqual(line['end_at'] - line['start_at'], rs.AD_MINUTES * 60, delta=1)
        tick = rs.ticker(self.store)
        self.assertEqual(len(tick), 1)
        self.assertIn('Trà sữa Mây giảm 20% cả tuần', tick[0]['text'])
        self.assertEqual(tick[0]['replay'], rs.REPLAY_S)
        news = mr.news(self.store, 0, None)
        self.assertEqual([x['id'] for x in news['radio']], [line['id']], 'the ticker poll carries it (an older page ignores the key)')
        self.assertIn('line', out['order']['result'])

    def test_the_generic_done_button_is_refused_until_read_at_the_desk(self):
        d, b = self.dj(), self.user('rd_b2')
        self.sell(d)
        o = self.buy(b, d)
        self.post(d, 'take', order=o['id'])
        self.refused('radio_desk', self.post, d, 'done', order=o['id'])
        self.assertEqual(self.row(o['id'])['status'], 'working')
        self.refused('radio_ok', rs.post, self.store, d, None, 'air', dict(order=o['id'], pick='vui', ok=False))
        self.refused('radio_pick', rs.post, self.store, d, None, 'air', dict(order=o['id'], pick='nope', ok=True))
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.air(d, o)['order']['status'], 'done')

    def test_a_song_needs_a_dj_past_probation_and_carries_the_song(self):
        d, b = self.dj('rd_newbie'), self.user('rd_lover')
        self.refused('cannot_provide', self.sell, d, rs.SONG)
        dj = self.dj('rd_star', promoted=True)
        self.sell(dj, rs.SONG)
        o = self.buy(b, dj, rs.SONG, note='Gửi Lan: chúc em ngủ ngon, mai gặp nhé')
        self.air(dj, o, pick='dem_sao')
        line = self.lines()[0]
        self.assertIn('Đêm đầy sao', line['text'])
        self.assertIn('Gửi Lan: chúc em ngủ ngon', line['text'])
        self.assertTrue(line['text'].startswith('🎵 '))
        self.assertLessEqual(len(line['text']), rs.LINE_MAX)

    def test_a_retried_air_pays_once_and_airs_once(self):
        d, b = self.dj(), self.user('rd_b3')
        self.sell(d)
        o = self.buy(b, d)
        self.air(d, o)
        td = self.total(d)
        again = self.air(d, o)
        self.assertEqual(again['order']['status'], 'done')
        self.assertEqual(self.total(d), td)
        self.assertEqual(len(self.lines()), 1)


class Caps(Base):
    def fill(self, n, buyer='x', provider='y'):
        t = time.time()
        def run(db):
            for i in range(n):
                db.execute('INSERT INTO radio_lines(id,order_id,kind,buyer,provider,text,day,start_at,end_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (f'rl_{i:020x}', f'sv_fill{i}', rs.AD, f'{buyer}{i}', provider, f'📢 dòng {i}', rs.today(t), t - 5, t + 600, t))
        self.store.transaction(run)
        rs.stale()

    def test_the_ticker_never_holds_more_than_live_max(self):
        self.fill(rs.LIVE_MAX + 3)
        self.assertEqual(len(rs.ticker(self.store)), rs.LIVE_MAX)
        self.assertLessEqual(len(rs._CACHE), rs.CACHE_STORES)

    def test_a_full_ticker_refuses_to_air_and_the_order_waits(self):
        d, b = self.dj(), self.user('rd_b4')
        self.sell(d)
        o = self.buy(b, d)
        self.fill(rs.LIVE_MAX)
        self.refused('radio_full', self.air, d, o)
        self.assertEqual(self.row(o['id'])['status'], 'working', 'taken, still open: aired when a slot frees, or refunded after its hours')

    def test_a_buyer_gets_at_most_buyer_day_lines_a_day(self):
        d, b = self.dj(), self.user('rd_b5')
        self.sell(d)
        for _ in range(rs.BUYER_DAY):
            self.buy(b, d)   # open orders count toward the day
        self.refused('requirement', self.buy, b, d)

    def test_a_dj_airs_at_most_dj_day_lines_a_day(self):
        d, b = self.dj(), self.user('rd_b6')
        self.sell(d)
        o = self.buy(b, d)
        t = time.time()
        sid = self.sid(d)

        def run(db):
            for i in range(rs.DJ_DAY):
                db.execute('INSERT INTO radio_lines(id,order_id,kind,buyer,provider,text,day,start_at,end_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (f'rl_{i + 900:020x}', f'sv_dj{i}', rs.AD, f'b{i}', sid, 'x', rs.today(t), t - 7200, t - 3600, t - 7200))
        self.store.transaction(run)
        self.refused('radio_dj_day', self.air, d, o)


class TakeDown(Base):
    def test_buyer_dj_and_admin_take_a_line_down_never_deleted_never_refunded(self):
        d, b = self.dj(), self.user('rd_b7')
        self.sell(d)
        for who in ('buyer', 'dj', 'admin'):
            with self.subTest(who=who):
                o = self.buy(b, d) if who != 'admin' else None
                if o is None:
                    with self.store.connect() as db:
                        db.execute("UPDATE radio_lines SET day='2000-01-01'")   # earlier lines: another day (the buyer's cap)
                    o = self.buy(b, d)
                self.air(d, o)
                line = [x for x in self.lines() if x['order_id'] == o['id']][0]
                tb = self.total(b)
                if who == 'dj':   # review 22/10: paid to air it, the DJ never takes it down (an admin does)
                    self.refused('dj_hide', rs.post, self.store, d, None, 'hide', dict(line=line['id']))
                    self.assertEqual([x for x in self.lines() if x['id'] == line['id']][0]['hidden'], 0)
                    mine = rs.get(self.store, d, None, 'mine', {})['mine']
                    self.assertFalse([x for x in mine if x['id'] == line['id']][0]['can_hide'])
                    self.assertTrue([x for x in rs.get(self.store, b, None, 'mine', {})['mine'] if x['id'] == line['id']][0]['can_hide'])
                    with self.store.connect() as db:
                        db.execute("UPDATE radio_lines SET day='2000-01-01', hidden=1, hidden_by='admin' WHERE id=?", (line['id'],))
                    continue
                if who == 'admin':
                    rs.admin_act(self.store, 'admin', dict(op='hide', line=line['id']))
                else:
                    rs.post(self.store, b if who == 'buyer' else d, None, 'hide', dict(line=line['id']))
                after = [x for x in self.lines() if x['id'] == line['id']][0]
                self.assertEqual((after['hidden'], after['hidden_by']), (1, who))
                self.assertNotIn(line['id'], [x['id'] for x in rs.ticker(self.store)])
                self.assertEqual(self.total(b), tb, 'aired: no refund')
                with self.store.connect() as db:
                    db.execute("UPDATE radio_lines SET day='2000-01-01' WHERE id=?", (line['id'],))
        stranger = self.user('rd_stranger')
        line = self.lines()[0]
        self.refused('not_found', rs.post, self.store, stranger, None, 'hide', dict(line=line['id']))
        rs.admin_act(self.store, 'admin', dict(op='show', line=line['id']))
        self.assertEqual(self.lines()[0]['hidden'], 0)
        view = rs.admin_view(self.store)
        self.assertEqual(view['totals']['lines'], 3)

    def test_a_deleted_account_leaves_the_ticker(self):
        d, b = self.dj(), self.user('rd_b8')
        self.sell(d)
        self.air(d, self.buy(b, d))
        rs.forget(self.store, b)
        self.assertEqual(rs.ticker(self.store), [])
        self.assertEqual((self.lines()[0]['hidden'], self.lines()[0]['hidden_by']), (1, 'gone'))


class KillSwitch(Base):
    def test_off_stops_orders_airings_and_the_ticker(self):
        d, b = self.dj(), self.user('rd_b9')
        self.sell(d)
        o = self.buy(b, d)
        self.air(d, o)
        o2 = self.buy(b, d)
        with patch.dict(os.environ, {'MNL_RADIO_OFF': '1'}):
            rs.stale()
            self.assertEqual(rs.ticker(self.store), [])
            self.assertEqual(mr.news(self.store, 0, None)['radio'], [])
            self.refused('bad_note', self.buy, b, d)
            self.refused('radio_off', self.air, d, o2)
            self.assertTrue(rs.get(self.store, d, None, 'desk', {})['off'])
        rs.stale()
        self.assertEqual(len(rs.ticker(self.store)), 1, 'back on: the line still runs (never deleted)')
        self.assertEqual(self.air(d, o2)['order']['status'], 'done')
