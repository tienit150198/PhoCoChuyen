"""🎪 Hội chợ việc làm (game/town_fair.py): the weekly town fair where every career opens a booth player to player. Real
accounts on one PostgreSQL store (TEST_DATABASE_URL): the calendar (Saturday 14:00–17:00 Vietnam time, the admin's
switches, the kill switch), the booth's discount on the provider's own Phố dịch vụ prices (never below the floor / NPC
base, no discount on a negotiation, gone when the booth closes or the fair ends) with the money still the market's
(escrow, 95 % / 5 % burned, conserved), the shows and their 🎟️ stamps, the oái oăm moments and the booth's mood, the
stamps of completed orders, the cosmetic rewards claimed exactly once (under concurrency too), the board frozen and its
titles granted once by the housekeeping, the archive kept."""
import concurrent.futures
import os
from unittest.mock import patch

from game import bank as bk
from game import live_effects as lfx
from game import marriage as mr
from game import service_market as sm
from game import spend as sp
from game import spend_content as SC
from game import town_fair as tf
from game import town_fair_content as C
from tests.test_quay_hire import Base

H, M = 3600, 60


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


SERVICES = ('milk_tea', 'florist', 'salon', 'pho')


class FairBase(Base):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'MNL_FAIR_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        tf.clear_cache()
        self.addCleanup(tf.clear_cache)
        sm._swept[0] = 0.0
        tf._swept[0] = 0.0
        self.ev = tf.weekly_event(1_790_000_000.0)
        self.clock = Clock(self.ev['starts'] + 10 * M)
        for target in ('game.service_market.now', 'game.town_fair.now'):
            p = patch(target, self.clock)
            p.start()
            self.addCleanup(p.stop)
        for career in SERVICES:   # one plain service per career (no deliver hook: the buyer confirms)
            sm.register(career, 'fair_test', dict(name=f'Dịch vụ thử {career}', icon='🧪', base=1000, unit='lượt', qty_max=3))
            self.addCleanup(sm.REGISTRY.pop, (career, 'fair_test'), None)
        self.n = 0

    def provider(self, name, career='milk_tea', mult=3, mode='fixed', wallet=5000):
        tok = self.user(name, wallet=wallet)

        def fn(s):
            s['careers'][career]['started'] = True
        mr._mutate(self.store, {self.sid(tok): fn})
        sm.post(self.store, tok, None, 'settings', dict(career=career, service='fair_test', on=True, mode=mode, mult=mult))
        return tok

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def total(self, tok):
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def fpost(self, tok, op, **d):
        return tf.post(self.store, tok, None, op, d)

    def fview(self, tok, **q):
        return tf.view(self.store, self.sid(tok), q)

    def quote(self, tok, career='milk_tea'):
        with self.store.connect() as db:
            return sm.quote(db, self.sid(tok), career, 'fair_test', 1)

    def order(self, buyer, prov, career='milk_tea', **extra):
        self.n += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=self.pid(prov), career=career, service='fair_test', qty=1,
                                                              rid=f'fair-{self.n:06d}', **extra))['order']

    def complete(self, buyer, prov, career='milk_tea'):
        o = self.order(buyer, prov, career)
        sm.post(self.store, prov, None, 'take', dict(order=o['id']))
        sm.post(self.store, prov, None, 'done', dict(order=o['id']))
        sm.post(self.store, buyer, None, 'confirm', dict(order=o['id']))
        return o

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def booth(self, tok):
        with self.store.connect() as db:
            return tf._booth(db, self.ev['id'], self.sid(tok))

    def own(self, tok):
        b = sp.get(self.state(tok))
        return {k: v for k, v in (b or {}).get('own', {}).items() if k in C.ITEM_IDS}

    def load(self, tok):
        lfx.on_load(self.store, tok, self.state(tok))


class Calendar(FairBase):
    def test_saturday_afternoon_vietnam_time(self):
        import datetime
        d0 = datetime.datetime.fromtimestamp(self.ev['starts'], tf.VN)
        d1 = datetime.datetime.fromtimestamp(self.ev['ends'], tf.VN)
        self.assertEqual((d0.weekday(), d0.hour, d0.minute, d1.hour, d1.minute), (5, 14, 0, 17, 0))
        self.assertEqual(self.ev['id'], 'w' + d0.strftime('%Y%m%d'))
        # just before: soon; during: open; just after: the next Saturday
        with self.store.connect() as db:
            self.assertEqual(tf.status(db, self.ev['starts'] - 3 * H)['state'], 'soon')
            self.assertEqual(tf.status(db, self.ev['starts'] - 3 * 86400)['state'], 'closed')
            self.assertEqual(tf.current(db, self.ev['starts'] + 1)['id'], self.ev['id'])
            self.assertIsNone(tf.current(db, self.ev['ends']))
        nxt = tf.weekly_event(self.ev['ends'])
        self.assertEqual(nxt['starts'] - self.ev['starts'], 7 * 86400)
        # the peak (17:30–20:00) and Sunday 20:00 are outside every window
        self.assertLessEqual(d1.hour * 60 + d1.minute, 17 * 60 + 30)

    def test_admin_switches_and_kill_switch(self):
        with self.store.connect() as db:
            self.assertIsNotNone(tf.current(db))
        v = tf.admin_act(self.store, 'admin', dict(op='weekly', on=False))
        self.assertFalse(v['weekly'])
        self.assertEqual(v['fair']['state'], 'closed')
        v = tf.admin_act(self.store, 'admin', dict(op='open_now', hours=2))
        self.assertEqual((v['fair']['state'], v['fair']['kind']), ('open', 'special'))
        self.refused('fair_open', tf.admin_act, self.store, 'admin', dict(op='open_now', hours=1))
        self.refused('bad_number', tf.admin_act, self.store, 'admin', dict(op='open_now', hours=tf.SPECIAL_MAX_HOURS + 1))
        v = tf.admin_act(self.store, 'admin', dict(op='close_special'))
        self.assertEqual(v['fair']['state'], 'closed')
        tf.admin_act(self.store, 'admin', dict(op='weekly', on=True))
        with patch.dict(os.environ, {'MNL_FAIR_OFF': '1'}):
            with self.store.connect() as db:
                self.assertIsNone(tf.current(db))
            self.assertIsNone(tf.news_line(self.store))
            self.assertIsNone(tf.hint())
        line = tf.news_line(self.store)
        self.assertEqual((line['state'], line['key']), ('open', 'tfair:' + self.ev['id']))


class Discount(FairBase):
    def test_booth_lowers_only_the_providers_own_price_and_money_stays_the_markets(self):
        p, b = self.provider('dc_p'), self.user('dc_b')
        mr._mutate(self.store, {self.sid(p): lambda s: s['careers']['florist'].update(started=True)})
        self.assertEqual(self.quote(p)['price'], 3000)
        self.refused('bad_number', self.fpost, p, 'open', career='milk_tea', pct=35)
        self.refused('not_started', self.fpost, p, 'open', career='nurse', pct=20)
        r = self.fpost(p, 'open', career='milk_tea', pct=20)
        self.assertIn('giảm 20%', r['message'])
        q = self.quote(p)
        self.assertEqual((q['price'], q['usual'], q['fair']), (2400, 3000, 20))
        self.refused('one_booth', self.fpost, p, 'open', career='florist', pct=10)
        before = self.total(b) + self.total(p)
        bt, pt = self.total(b), self.total(p)
        o = self.complete(b, p)
        with self.store.connect() as db:
            row = sm.order_of(db, o['id'])
        self.assertEqual((row['price'], row['fee'], row['paid']), (2400, 120, 2280))
        self.assertEqual((self.total(b), self.total(p)), (bt - 2400, pt + 2280))
        self.assertEqual(self.total(b) + self.total(p), before - 120, 'only the 5 % is burned')
        # the directory shows it too, with the usual price
        d = sm.directory(self.store, self.sid(b), dict(career='milk_tea', service='fair_test'))
        item = next(x for x in d['items'] if x['pid'] == self.pid(p))
        self.assertEqual((item['price'], item['usual'], item['fair']), (2400, 3000, 20))
        # closed booth: the usual price again; reopened: the discount again
        self.fpost(p, 'close')
        self.assertEqual((self.quote(p)['price'], self.quote(p)['fair']), (3000, 0))
        self.fpost(p, 'open', career='milk_tea', pct=10)
        self.assertEqual(self.quote(p)['price'], 2700)
        # after the fair: gone
        self.clock.t = self.ev['ends'] + 1
        self.assertEqual((self.quote(p)['price'], self.quote(p)['fair']), (3000, 0))

    def test_never_below_the_floor_and_no_discount_on_a_negotiation(self):
        low, nego = self.provider('fl_low', mult=1), self.provider('fl_nego', mode='nego')
        for tok in (low, nego):
            self.fpost(tok, 'open', career='milk_tea', pct=30)
        q = self.quote(low)
        self.assertEqual((q['price'], q['fair']), (1000, 0), 'the NPC base is the floor')
        q = self.quote(nego)
        self.assertEqual((q['price'], q['fair']), (None, 0))
        mid = self.provider('fl_mid', mult=2)
        self.fpost(mid, 'open', career='milk_tea', pct=30)
        self.assertEqual(self.quote(mid)['price'], 1400)
        # a stale expected price is refused (the buyer sees the new price first)
        b = self.user('fl_b')
        self.refused('quote_changed', self.order, b, mid, expected_price=2000)

    def test_legacy_workplace_quote_follows_the_booth(self):
        p = self.provider('lg_p')
        with self.store.connect() as db:
            q0 = sm.legacy_quote(db, self.sid(p), 'career', 'milk_tea', 100)
        self.fpost(p, 'open', career='milk_tea', pct=25)
        with self.store.connect() as db:
            q1 = sm.legacy_quote(db, self.sid(p), 'career', 'milk_tea', 100)
            qq = sm.legacy_quote(db, self.sid(p), 'quay', 'quay', 100)
        self.assertEqual((q0['price'], q1['price'], q1['usual'], q1['fair']), (300, 225, 300, 25))
        self.assertEqual(qq['fair'], 0, 'a quầy is not a career booth')

    def test_kill_switch_stops_discounts_and_new_booths(self):
        p = self.provider('ks_p')
        self.fpost(p, 'open', career='milk_tea', pct=20)
        with patch.dict(os.environ, {'MNL_FAIR_OFF': '1'}):
            self.assertEqual(self.quote(p)['price'], 3000)
            q = self.provider('ks_q', 'florist')
            self.refused('fair_off', self.fpost, q, 'open', career='florist', pct=20)
        self.assertEqual(self.quote(p)['price'], 2400)


class Booth(FairBase):
    def test_shows_give_stamps_to_watchers_once(self):
        p, v = self.provider('sh_p', 'florist'), self.user('sh_v')
        self.fpost(p, 'open', career='florist', pct=15)
        self.refused('show_over', self.fpost, v, 'watch', pid=self.pid(p))
        menu = self.fview(p)['mine']['menu']
        self.assertEqual(menu[0]['id'], C.CAREER_SHOWS['florist'][0], 'the signature act first')
        r = self.fpost(p, 'show', show=menu[0]['id'])
        self.assertIn('🎟️', r['message'])
        self.refused('show_wait', self.fpost, p, 'show', show=menu[1]['id'])
        self.refused('own_booth', self.fpost, p, 'watch', pid=self.pid(p))
        r = self.fpost(v, 'watch', pid=self.pid(p))
        self.assertIn('+1 tem', r['message'])
        r = self.fpost(v, 'watch', pid=self.pid(p))
        self.assertNotIn('+1 tem', r['message'])
        b = self.booth(p)
        self.assertEqual((b['shows'], b['watchers'], b['mood']), (1, 1, tf.MOOD_START + tf.SHOW_MOOD + 1))
        self.assertEqual(self.fview(v)['stamps']['n'], 1)
        booth = next(x for x in self.fview(v)['booths'] if x['pid'] == self.pid(p))
        self.assertTrue(booth['stamped'] and booth['watched'] and booth['show'])
        self.clock.t += tf.SHOW_SECONDS + 1
        self.refused('show_over', self.fpost, v, 'watch', pid=self.pid(p))

    def test_oai_oam_moments_move_the_mood(self):
        p = self.provider('mo_p')
        self.fpost(p, 'open', career='milk_tea', pct=15)
        self.assertIsNone(self.fview(p)['mine']['moment'])
        self.clock.t += tf.MOMENT_FIRST
        m = self.fview(p)['mine']['moment']
        self.assertTrue(m and len(m['opts']) == 3)
        best = max(C.MOMENT_INDEX[m['key']][3], key=lambda o: o[2])
        self.refused('bad_pick', self.fpost, p, 'moment', key=m['key'], pick='nope')
        r = self.fpost(p, 'moment', key=m['key'], pick=best[0])
        self.assertEqual(r['view']['mine']['mood'], tf.MOOD_START + best[2])
        self.refused('moment_gone', self.fpost, p, 'moment', key=m['key'], pick=best[0])
        # the next one comes after MOMENT_EVERY; left unanswered it is missed
        self.clock.t += tf.MOMENT_EVERY
        m2 = self.fview(p)['mine']['moment']
        self.assertTrue(m2 and m2['key'] != m['key'])
        self.clock.t += tf.MOMENT_ANSWER + 1
        mine = self.fview(p)['mine']
        self.assertEqual((mine['missed'], mine['handled'], mine['mood']), (1, 1, tf.MOOD_START + best[2] + tf.MISS_MOOD))
        self.assertEqual(mine['log'][0]['d'], tf.MISS_MOOD)

    def test_visitors_see_booths_by_group_with_fair_prices(self):
        a, f, v = self.provider('vw_a'), self.provider('vw_f', 'florist'), self.user('vw_v')
        self.fpost(a, 'open', career='milk_tea', pct=20)
        self.fpost(f, 'open', career='florist', pct=10)
        tf._stale()
        got = self.fview(v)
        self.assertEqual(got['fair']['state'], 'open')
        self.assertEqual({x['career'] for x in got['booths']}, {'milk_tea', 'florist'})
        tea = next(x for x in got['booths'] if x['career'] == 'milk_tea')
        self.assertEqual((tea['items'][0]['price'], tea['items'][0]['usual'], tea['items'][0]['fair']), (2400, 3000, 20))
        self.assertEqual({x['career'] for x in self.fview(v, group='shop')['booths']}, {'florist'})
        self.assertEqual(got['counts']['food'], 1)
        self.assertIn('milk_tea', {c['career'] for c in self.fview(a)['can_open']} | {'milk_tea'})
        self.assertIsNone(self.fview(v)['mine'])


class Stamps(FairBase):
    def three(self):
        ps = [self.provider(f'st_{c}', c) for c in ('milk_tea', 'florist', 'salon')]
        for tok, c in zip(ps, ('milk_tea', 'florist', 'salon')):
            self.fpost(tok, 'open', career=c, pct=20)
        return ps

    def test_completed_orders_become_stamps_and_unlock_a_cosmetic_once(self):
        ps, v = self.three(), self.user('st_v', wallet=50000)
        self.complete(v, ps[0], 'milk_tea')
        self.complete(v, ps[1], 'florist')
        o = self.order(v, ps[2], 'salon')   # paid, not completed yet: no stamp
        card = self.fview(v)['stamps']
        self.assertEqual(card['n'], 2)
        self.refused('not_enough', self.fpost, v, 'claim', event=self.ev['id'], tier=1)
        sm.post(self.store, ps[2], None, 'take', dict(order=o['id']))
        sm.post(self.store, ps[2], None, 'done', dict(order=o['id']))
        sm.post(self.store, v, None, 'confirm', dict(order=o['id']))
        card = self.fview(v)['stamps']
        self.assertEqual((card['n'], card['tiers'][0]['ready']), (3, True))
        r = self.fpost(v, 'claim', event=self.ev['id'], tier=1)
        self.assertIn(SC.STYLE_ITEMS['t_hc_khach']['name'], r['message'])
        self.assertEqual(self.own(v), {'t_hc_khach': SC.PERMANENT})
        again = self.fpost(v, 'claim', event=self.ev['id'], tier=1)
        self.assertIn('rồi', again['message'])
        self.load(v)
        self.assertEqual(self.own(v), {'t_hc_khach': SC.PERMANENT})
        with self.store.connect() as db:
            n = db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE sid=? AND kind='tfair'", (self.sid(v),)).fetchone()['n']
            st = db.execute("SELECT status FROM live_effects WHERE sid=? AND kind='tfair'", (self.sid(v),)).fetchone()['status']
        self.assertEqual((n, st), (1, 'applied'))
        self.refused('not_enough', self.fpost, v, 'claim', event=self.ev['id'], tier=2)
        # the title is worn like any earned title, never sold
        self.cmd(v, 'jr_spend_wear', kind='title', id='t_hc_khach')
        self.assertEqual(sp.style_now(self.state(v))['t'], 't_hc_khach')
        self.assertIn('để mở', sp.style_why(self.state(self.user('st_w')), 'f_hc_den_long'))

    def test_claims_race_exactly_once(self):
        ps, v = self.three(), self.user('rc_v', wallet=50000)
        for tok, c in zip(ps, ('milk_tea', 'florist', 'salon')):
            self.fpost(tok, 'show', show=tf.shows_for(c)[0]['id'])
            self.fpost(v, 'watch', pid=self.pid(tok))
        with concurrent.futures.ThreadPoolExecutor(4) as ex:
            list(ex.map(lambda _: self.fpost(v, 'claim', event=self.ev['id'], tier=1), range(4)))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM fair_rewards WHERE sid=?', (self.sid(v),)).fetchone()['n'], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE sid=? AND kind='tfair'", (self.sid(v),)).fetchone()['n'], 1)
        self.assertEqual(self.own(v), {'t_hc_khach': SC.PERMANENT})


class Board(FairBase):
    def test_board_settles_once_and_grants_booth_titles(self):
        a, f, v, w = self.provider('bd_a'), self.provider('bd_f', 'florist'), self.user('bd_v', wallet=50000), self.user('bd_w', wallet=50000)
        self.fpost(a, 'open', career='milk_tea', pct=20)
        self.fpost(f, 'open', career='florist', pct=20)
        for buyer in (v, w, v):
            self.complete(buyer, a)
        o = self.complete(w, f, 'florist')
        sm.post(self.store, w, None, 'rate', dict(order=o['id'], stars=5))
        tf._stale()   # the live board is cached a few seconds
        live = tf.board(self.store)
        self.assertEqual([r['who']['name'] for r in live['served']], ['Bd_A', 'Bd_F'])
        self.assertEqual(live['served'][0]['served'], 3)
        self.assertFalse(live['event']['final'])
        # not before the settle time
        self.clock.t = self.ev['ends'] + 1
        self.assertEqual(tf.run_housekeeping(self.store), 0)
        self.clock.t = self.ev['ends'] + tf.SETTLE_HOURS * H + 1
        tf._swept[0] = 0
        self.assertEqual(tf.run_housekeeping(self.store), 1)
        tf._swept[0] = 0
        self.assertEqual(tf.run_housekeeping(self.store), 0)
        snap = tf.board(self.store, self.ev['id'])
        self.assertTrue(snap['event']['final'])
        self.assertEqual((snap['served'][0]['served'], snap['booths'], snap['orders']), (3, 2, 4))
        self.assertEqual(snap['rated'][0]['who']['name'], 'Bd_F', '5 stars lift the florist above')
        self.load(a)
        self.load(f)
        self.assertEqual(set(self.own(a)), {C.HOST_ITEM, C.SERVED_ITEM, C.RATED_ITEM})
        self.assertEqual(set(self.own(f)), {C.SERVED_ITEM, C.RATED_ITEM})
        with self.store.connect() as db:
            n = db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE kind='tfair'").fetchone()['n']
            news = [r['text'] for r in db.execute("SELECT text FROM news WHERE kind='tfair'").fetchall()]
        self.assertEqual(n, 2)
        self.assertTrue(any('khép lại' in x for x in news))
        self.assertEqual(snap['past'][0]['id'], self.ev['id'])
        # archived, never deleted: the rows stay
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM fair_booths').fetchone()['n'], 2)

    def test_opening_news_once(self):
        tf.run_housekeeping(self.store)
        tf._swept[0] = 0
        tf.run_housekeeping(self.store)
        with self.store.connect() as db:
            rows = db.execute("SELECT ref FROM news WHERE kind='tfair'").fetchall()
        self.assertEqual([r['ref'] for r in rows], ['tfair:open:' + self.ev['id']])
