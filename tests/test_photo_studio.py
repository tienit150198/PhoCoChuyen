"""📸 Chụp ảnh cho người chơi (game/photo_studio.py, owner 21/10): a photographer player shoots another player. The order
(escrow from the buyer's save, the look snapshot taken then), accept / decline / cancel / expire (the whole price back,
once), the session (shots judged from the beat, SHOTS at most), delivery (the photo stored in the album and the
portfolio, PAY_PCT % to the photographer, BURN_PCT % burned: buyer debit = pay + burn exactly), the anti-abuse rules
(price caps, no self-orders, the same network, the pair's daily cap, open caps), the album (archive past ALBUM_MAX,
never deleted), the profile photo on the profile card, the framed photo at home, and the id lists shared with the
client."""
import re
import time
from pathlib import Path
from unittest import mock

from game import live_effects as lfx
from game import marriage as mr
from game import photo_studio as P
from game import social
from game import work_visits as wv
from game.engine import validate_state
from tests.test_quay_hire import Base as QBase

ROOT = Path(__file__).resolve().parents[1]
BUYER_IP, SHOOTER_IP = '10.0.0.1', '10.0.0.2'


class Base(QBase):
    def setUp(self):
        super().setUp()
        self.n = 0
        P._SWEEP['at'] = 0.0

    def shooter(self, name='thoanh'):
        tok = self.user(name, trade='photobooth')
        self.cmd(tok, 'select_career', career='photobooth')
        self.cmd(tok, 'start_day', career='photobooth')
        sid = self.sid(tok)
        pid = P.place_id(sid)
        with self.store.connect() as db:
            row = db.execute('SELECT id FROM work_visit_places WHERE id=?', (pid,)).fetchone()
        self.assertTrue(row, 'the photobooth place is synced with the save')
        wv.post(self.store, tok, self.state(tok), 'visibility', dict(place=pid, visibility='public'))
        P.get(self.store, tok, None, 'studio', {})
        P.post(self.store, tok, None, 'studio', dict(open=True), SHOOTER_IP)   # the photographer's network tag
        return tok

    def buyer(self, name='khach', wallet=30000):
        tok = self.user(name, wallet=wallet)
        self.cmd(tok, 'select_career', career='milk_tea')
        self.cmd(tok, 'start_day', career='milk_tea')
        return tok

    def order(self, tok, shooter, pkg='chan_dung', price=None, ip=BUYER_IP, **kw):
        self.n += 1
        d = dict(rid=f'rid-photo-{self.n:05d}', place=P.place_id(self.sid(shooter)), pkg=pkg,
                 price=P.default_of(pkg) if price is None else price, wish=dict(bd='any', mood='any'))
        d.update(kw)
        return P.post(self.store, tok, None, 'order', d, ip)

    def op(self, tok, op, ip=SHOOTER_IP, **d):
        return P.post(self.store, tok, None, op, d, ip)

    def row(self, oid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM photo_orders WHERE id=?', (oid,)).fetchone())

    def refused(self, code, fn, *a, **kw):
        with self.assertRaises(P.PhotoError) as cm:
            fn(*a, **kw)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception

    def good_el(self, oid, n, pkg='chan_dung'):
        b = P.beat(oid, n, pkg)
        return b['count'] + b['lead'] + b['hold'] / 2

    def shoot_all(self, tok, oid, st=None, el=None):
        st = st or dict(bd='kem', light='mem', frame='nua', pose='v', face='cuoi_hip', prop='none')
        out = []
        for n in range(P.SHOTS):
            out.append(self.op(tok, 'shot', id=oid, n=n, set=st, el=self.good_el(oid, n) if el is None else el))
        return out


class Flow(Base):
    def test_order_escrow_session_delivery_payout_and_burn(self):
        sh, by = self.shooter(), self.buyer()
        w_by, w_sh = self.wallet(by), self.wallet(sh)
        o = self.order(by, sh)['order']
        self.assertEqual((o['status'], o['price']), ('open', 900))
        self.assertEqual(self.wallet(by), w_by - 900, 'the price is held from the buyer at once')
        r = self.row(o['id'])
        snap = P._j(r['snap'], {})
        self.assertEqual(snap['me']['lk']['hair'], self.state(by)['wardrobe']['look']['hair'] if 'wardrobe' in self.state(by) else snap['me']['lk']['hair'])
        self.assertTrue(snap['me']['n'])
        # a retry of the same rid: the same order, nothing paid twice
        again = P.post(self.store, by, None, 'order', dict(rid=f'rid-photo-{self.n:05d}', place=P.place_id(self.sid(sh)), pkg='chan_dung',
                                                          price=900, wish={}), BUYER_IP)
        self.assertTrue(again['again'])
        self.assertEqual(self.wallet(by), w_by - 900)
        # the photographer's queue shows it with the snapshot; the buyer's album lists it on its way
        q = P.get(self.store, sh, None, 'studio', {})['queue']
        self.assertEqual([x['id'] for x in q], [o['id']])
        self.assertIn('snap', q[0])
        self.assertEqual(P.get(self.store, by, None, 'album', {})['orders'][0]['status'], 'open')
        # deliver before accepting / before the shots: refused
        self.refused('gone', self.op, sh, 'deliver', id=o['id'], pick=0, rt={})
        self.op(sh, 'accept', id=o['id'])
        self.refused('not_enough_shots', self.op, sh, 'deliver', id=o['id'], pick=0, rt={})
        shots = self.shoot_all(sh, o['id'])
        self.assertEqual([s['shot']['q'] for s in shots], ['good'] * 3)
        self.assertIsNone(shots[-1]['beat'])
        self.refused('full', self.op, sh, 'shot', id=o['id'], set=shots[0]['shot']['set'], el=4.0)
        # a retried shot answers the same
        self.assertEqual(self.op(sh, 'shot', id=o['id'], n=1, set=shots[0]['shot']['set'], el=0.1)['shot'], shots[1]['shot'])
        out = self.op(sh, 'deliver', id=o['id'], pick=1, rt=dict(sang=1, am=0, min=1, vig=0))
        self.assertEqual((out['pay'], out['burn']), (855, 45))
        self.assertEqual(out['pay'] + out['burn'], 900, 'buyer debit = pay + burn')
        self.assertEqual(self.wallet(sh), w_sh + 855)
        self.assertEqual(self.wallet(by), w_by - 900)
        self.assertEqual(out['stars'], 5, out['misses'])
        r = self.row(o['id'])
        self.assertEqual((r['status'], r['pay'], r['burn'], r['photo']), ('done', 855, 45, out['photo']))
        # delivered again: nothing moves
        self.assertTrue(self.op(sh, 'deliver', id=o['id'], pick=1, rt={})['again'])
        self.assertEqual(self.wallet(sh), w_sh + 855)
        # the album shows it with its render data; the portfolio too
        alb = P.get(self.store, by, None, 'album', {})
        self.assertEqual([p['id'] for p in alb['photos']], [out['photo']])
        data = alb['photos'][0]['data']
        self.assertEqual((data['pkg'], data['q'], data['set']['bd'], data['rt']['sang']), ('chan_dung', 'good', 'kem', 1))
        self.assertEqual(data['snap']['me']['n'], snap['me']['n'])
        folio = P.get(self.store, by, None, 'folio', dict(pid=P.pid_of(self.sid(sh))))['photos']
        self.assertEqual([p['id'] for p in folio], [out['photo']])
        self.assertEqual(P.get(self.store, by, None, 'one', dict(id=out['photo']))['photo']['id'], out['photo'])
        st = P.get(self.store, sh, None, 'studio', {})
        self.assertEqual((st['stats']['done'], st['stats']['stars'], st['queue']), (1, 5.0, []))
        validate_state(self.state(by))
        validate_state(self.state(sh))

    def test_stars_follow_the_shot_wish_light_framing_and_retouch(self):
        sh, by = self.shooter(), self.buyer()
        o = self.order(by, sh, wish=dict(bd='hong', mood='tinh'))['order']
        self.op(sh, 'accept', id=o['id'])
        st = dict(bd='den', light='mem', frame='toan', pose='v', face='le_luoi', prop='hoa')
        b = P.beat(o['id'], 0, 'chan_dung')
        self.assertEqual(self.op(sh, 'shot', id=o['id'], set=st, el=b['count'] + b['lead'] / 3)['shot']['q'], 'early')
        b = P.beat(o['id'], 1, 'chan_dung')
        self.assertEqual(self.op(sh, 'shot', id=o['id'], set=st, el=b['count'] + b['lead'] + b['hold'] + .3)['shot']['q'], 'blink')
        self.assertEqual(self.op(sh, 'shot', id=o['id'], set=st, el=15.0)['shot']['q'], 'late')
        out = self.op(sh, 'deliver', id=o['id'], pick=0, rt=dict(sang=2, am=-2, min=1, vig=0))
        self.assertEqual(out['stars'], 1)
        self.assertEqual(len(out['misses']), 7)   # the shot ×2, phông, không khí, đèn, khung, chỉnh quá tay

    def test_cancel_decline_and_expire_give_the_price_back_once(self):
        sh, by = self.shooter(), self.buyer()
        w = self.wallet(by)
        a = self.order(by, sh)['order']
        self.assertEqual(self.wallet(by), w - 900)
        P.post(self.store, by, None, 'cancel', dict(id=a['id']))
        self.assertEqual(self.wallet(by), w, 'cancel: straight back into the save')
        self.assertTrue(P.post(self.store, by, None, 'cancel', dict(id=a['id']))['again'])
        self.assertEqual(self.wallet(by), w)
        # the pair's cap counts what was not cancelled; decline goes back through live_effects, paid once
        b = self.order(by, sh, pkg='chan_dung')['order']
        self.op(sh, 'decline', id=b['id'])
        self.assertEqual(self.wallet(by), w - 900)
        fx = [e for e in self.effects(self.sid(by)) if e['kind'] == 'photo']
        self.assertEqual([(e['amount'], e['status']) for e in fx], [(900, 'pending')])
        self.assertTrue(P.refund_waiting(self.store, by))
        lfx.on_load(self.store, by, self.state(by))
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w)
        self.assertFalse(P.refund_waiting(self.store, by))
        self.refused('gone', self.op, sh, 'decline', id=b['id'])
        # expired: an accepted order past SHOOT_HOURS
        with mock.patch.object(P, 'PAIR_DAY', 10):
            c = self.order(by, sh)['order']
        self.op(sh, 'accept', id=c['id'])
        self.assertEqual(P.sweep(self.store, P.now()), 0)
        self.assertEqual(P.sweep(self.store, P.now() + P.SHOOT_HOURS * 3600 + 5), 1)
        self.assertEqual(P.sweep(self.store, P.now() + P.SHOOT_HOURS * 3600 + 5), 0)
        self.assertEqual(self.row(c['id'])['status'], 'expired')
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w)
        self.refused('gone', self.op, sh, 'shot', id=c['id'], set={}, el=4.0)


    def test_the_off_switch_still_refunds_cancels_declines_and_sweeps(self):
        """Review 22/10: MNL_PHOTO_OFF refused everything, the sweep included: paid orders were stranded."""
        import os
        sh, by = self.shooter(), self.buyer()
        w = self.wallet(by)
        a = self.order(by, sh)['order']
        with mock.patch.object(P, 'PAIR_DAY', 10):
            b = self.order(by, sh)['order']
            c = self.order(by, sh)['order']
        self.op(sh, 'accept', id=c['id'])
        with mock.patch.dict(os.environ, {'MNL_PHOTO_OFF': 'true'}):
            self.refused('off', self.order, by, sh)
            self.refused('off', self.op, sh, 'accept', id=b['id'])
            self.assertTrue(P.get(self.store, by, None, 'album', {})['ok'])
            P.post(self.store, by, None, 'cancel', dict(id=a['id']))
            self.op(sh, 'decline', id=b['id'])
            P._SWEEP['at'] = 0.0
            with mock.patch.object(P, 'now', lambda: time.time() + P.SHOOT_HOURS * 3600 + 5):
                P.run_housekeeping(self.store)
        self.assertEqual([self.row(x['id'])['status'] for x in (a, b, c)], ['cancelled', 'declined', 'expired'])
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w, 'every price back')


class Rules(Base):
    def test_price_caps_self_orders_network_pair_and_open_caps(self):
        sh, by = self.shooter(), self.buyer()
        w = self.wallet(by)
        self.refused('bad_price', self.order, by, sh, price=P.floor_of('chan_dung') - 1)
        self.refused('bad_price', self.order, by, sh, price=P.cap_of('chan_dung') + 1)
        self.refused('bad_price', self.order, by, sh, price='900')
        self.refused('bad_pkg', self.order, by, sh, pkg='x', price=900)
        self.refused('self', self.order, sh, sh)
        self.refused('same_net', self.order, by, sh, ip=SHOOTER_IP)
        self.assertEqual(self.wallet(by), w, 'a refusal takes nothing')
        # an offer under the list price is allowed (between floor and cap): the photographer accepts or declines
        o = self.order(by, sh, price=P.floor_of('chan_dung'))['order']
        self.assertEqual((o['price'], o['list']), (300, 900))
        # the photographer accepting from the buyer's network: refused
        self.refused('same_net', self.op, sh, 'accept', ip=BUYER_IP, id=o['id'])
        self.order(by, sh)
        self.refused('pair_limit', self.order, by, sh)
        with mock.patch.object(P, 'PAIR_DAY', 50):
            for _ in range(P.BUYER_OPEN - 2):
                self.order(by, sh)
            self.refused('buyer_full', self.order, by, sh)
        self.assertEqual(self.wallet(by), w - 300 - 900 * (P.BUYER_OPEN - 1))
        # a reverse order counts in the pair's day too: two photographers ordering from each other
        sh2 = self.shooter('thoanh2')
        self.order(sh, sh2, ip='10.0.0.7')
        self.order(sh, sh2, ip='10.0.0.7')
        self.refused('pair_limit', self.order, sh2, sh, ip='10.0.0.8')
        # not enough money: nothing written
        poor = self.buyer('ngheo', wallet=10)
        self.refused('not_enough', self.order, poor, sh2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM photo_orders WHERE buyer=?', (self.sid(poor),)).fetchone()[0], 0)

    def test_a_new_photographer_account_and_a_closed_studio_take_no_orders(self):
        sh, by = self.shooter(), self.buyer()
        self.store.transaction(lambda db: db.execute("UPDATE accounts SET created_at='2999-01-01 00:00:00' WHERE sid=?", (self.sid(sh),)))
        self.refused('too_new', self.order, by, sh)
        self.store.transaction(lambda db: db.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (self.sid(sh),)))
        P.post(self.store, sh, None, 'studio', dict(open=False), SHOOTER_IP)
        self.refused('studio_closed', self.order, by, sh)
        P.post(self.store, sh, None, 'studio', dict(open=True, prices=dict(chan_dung=1200)), SHOOTER_IP)
        self.assertEqual(self.order(by, sh, price=1200)['order']['list'], 1200)
        self.refused('bad_price', P.post, self.store, sh, None, 'studio', dict(prices=dict(chan_dung=99999)), SHOOTER_IP)
        # a closed place: nobody can order
        wv.post(self.store, sh, self.state(sh), 'visibility', dict(place=P.place_id(self.sid(sh)), visibility='closed'))
        self.refused('closed', self.order, by, sh)

    def test_couple_and_baby_packages_need_them(self):
        sh, by = self.shooter(), self.buyer()
        self.refused('no_mate', self.order, by, sh, pkg='doi')
        self.refused('no_baby', self.order, by, sh, pkg='day_thang')
        self.refused('no_family', self.order, by, sh, pkg='gia_dinh')
        self.refused('bad_product', self.order, by, sh, pkg='san_pham')
        o = self.order(by, sh, pkg='san_pham', product='tra_sua')['order']
        snap = P._j(self.row(o['id'])['snap'], {})
        self.assertEqual(snap['shop']['p'], 'tra_sua')
        self.assertTrue(snap['shop']['n'])

    def test_group_pose_needs_two_and_the_island_needs_one(self):
        sh, by = self.shooter(), self.buyer()
        o = self.order(by, sh)['order']
        self.op(sh, 'accept', id=o['id'])
        base = dict(bd='kem', light='mem', frame='nua', pose='tim_to', face='auto', prop='none')
        self.refused('bad_set', self.op, sh, 'shot', id=o['id'], set=base, el=4.0)
        self.refused('no_island', self.op, sh, 'shot', id=o['id'], set=dict(base, pose='v', bd='dao'), el=4.0)
        self.refused('bad_set', self.op, sh, 'shot', id=o['id'], set=dict(base, pose='v', bd='<b>'), el=4.0)
        self.refused('bad_el', self.op, sh, 'shot', id=o['id'], set=dict(base, pose='v'), el=99)


class Album(Base):
    def delivered(self, sh, by, n=1):
        out = []
        with mock.patch.object(P, 'PAIR_DAY', 99), mock.patch.object(P, 'BUYER_OPEN', 99):
            for _ in range(n):
                o = self.order(by, sh)['order']
                self.op(sh, 'accept', id=o['id'])
                self.shoot_all(sh, o['id'])
                out.append(self.op(sh, 'deliver', id=o['id'], pick=0, rt={})['photo'])
        return out

    def test_profile_photo_frame_at_home_portfolio_hide_and_archive(self):
        sh, by = self.shooter(), self.buyer()
        a, = self.delivered(sh, by)
        # 🙂 profile photo: only a photo of my own album
        self.refused('gone', P.post, self.store, sh, None, 'pfp', dict(id=a))
        P.post(self.store, by, None, 'pfp', dict(id=a))
        self.assertEqual(P.get(self.store, by, None, 'album', {})['pfp'], a)
        self.store.transaction(lambda db: db.execute("UPDATE profiles SET visible=1, name='Khach' WHERE sid=?", (self.sid(by),)))
        prof = social.get(self.store, sh, self.state(sh), 'shop', dict(pid=P.pid_of(self.sid(by))))['profile']
        self.assertEqual(prof['pfp']['id'], a)
        self.assertEqual(prof['pfp']['data']['snap']['me']['n'], self.row(self._order_of(a))['buyer_name'])
        self.store.transaction(lambda db: db.execute("UPDATE profiles SET visible=1, name='Tho' WHERE sid=?", (self.sid(sh),)))
        self.assertEqual(social.get(self.store, by, self.state(by), 'shop', dict(pid=P.pid_of(self.sid(sh))))['profile']['studio'],
                         P.place_id(self.sid(sh)))
        P.post(self.store, by, None, 'pfp', dict(id=None))
        self.assertEqual(P.get(self.store, by, None, 'album', {})['pfp'], '')
        # 🖼️ a frame in the bag of furniture, its photo in journey.photo_wall; once a photo
        out = P.post(self.store, by, None, 'hang', dict(id=a))
        s = self.state(by)
        uid = out['uid']
        self.assertEqual(s['journey']['photo_wall'], {uid: a})
        self.assertIn(dict(id=uid, k='anh_chup', r=None, x=None), s['journey']['reno']['items'])
        self.assertIn('đã có', P.post(self.store, by, None, 'hang', dict(id=a))['message'])
        self.assertEqual(sum(1 for x in self.state(by)['journey']['reno']['items'] if x['k'] == 'anh_chup'), 1)
        validate_state(self.state(by))
        bad = self.state(by)
        bad['journey']['photo_wall'] = {uid: '<script>'}
        with self.assertRaises(Exception):
            validate_state(bad)
        # 👁 hidden from the photographer's portfolio
        pid = P.pid_of(self.sid(sh))
        P.post(self.store, by, None, 'folio', dict(id=a, show=False))
        self.assertEqual(P.get(self.store, by, None, 'folio', dict(pid=pid))['photos'], [])
        P.post(self.store, by, None, 'folio', dict(id=a, show=True))
        self.assertEqual(len(P.get(self.store, by, None, 'folio', dict(pid=pid))['photos']), 1)
        # 🗄️ past ALBUM_MAX the oldest go to the archive, never deleted
        with mock.patch.object(P, 'ALBUM_MAX', 2):
            more = self.delivered(sh, by, 2)
        alb = P.get(self.store, by, None, 'album', {})
        self.assertEqual([p['id'] for p in alb['photos']], list(reversed(more)))
        self.assertEqual(alb['archived'], 1)
        old = P.get(self.store, by, None, 'album', dict(old='1'))
        self.assertEqual([p['id'] for p in old['photos']], [a])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM photos WHERE buyer=?', (self.sid(by),)).fetchone()[0], 3)

    def _order_of(self, photo):
        with self.store.connect() as db:
            return db.execute('SELECT order_id FROM photos WHERE id=?', (photo,)).fetchone()[0]


class People(Base):
    def couple(self, a, b, status='married'):
        sa, sb = self.sid(a), self.sid(b)

        def run(db):
            cid = db.execute('INSERT INTO couples(a, b, status, since) VALUES(?,?,?,?) RETURNING id', (sa, sb, status, P.now())).fetchone()[0]
            for s in (sa, sb):
                db.execute('INSERT INTO marriage_bonds(sid, couple) VALUES(?,?)', (s, cid))
        self.store.transaction(run)

    def test_the_couple_photo_takes_the_spouse_from_their_own_save_and_the_baby_and_pet_ride_along(self):
        sh, by, mate = self.shooter(), self.buyer(), self.buyer('nguoithuong')
        mr._mutate(self.store, {self.sid(mate): lambda s: s.update(wardrobe=dict(v=1, owned=[], look=dict(
            hair='toc_ngan', shade='mau_den', skin='da_trung', top='ao_so_mi', bottom='quan_jean', shoes='giay_nau', acc='pk_khong', uniform=False)))})
        self.couple(by, mate)
        baby = dict(id='child', n='Bé Na', g='biet_bo', o='flower')
        with mock.patch.object(P, '_babies', return_value=[baby]):
            o = self.order(by, sh, pkg='doi')['order']
            fam = self.order(by, sh, pkg='day_thang')['order']
        snap = P._j(self.row(o['id'])['snap'], {})
        self.assertEqual(snap['mate']['lk']['top'], 'ao_so_mi', "the spouse's own look, from their save")
        self.assertEqual(snap['mate']['n'], 'Nguoithuong')
        self.assertEqual(P._j(self.row(fam['id'])['snap'], {})['baby'], dict(n='Bé Na', g='biet_bo', o='flower'))
        # the photographer's queue shows who comes along; a group pose is allowed with two
        self.op(sh, 'accept', id=o['id'])
        st = dict(bd='cuoi', light='ven', frame='toan', pose='tim_to', face='mat_tim', prop='none')
        self.assertEqual(self.op(sh, 'shot', id=o['id'], set=st, el=self.good_el(o['id'], 0, 'doi') - 0)['shot']['set']['pose'], 'tim_to')
        # the pet: only one at home
        self.refused('no_pet', self.order, by, sh, pkg='gia_dinh', pet='p999', price=2100)


class Concurrency(Base):
    def test_two_deliveries_at_once_pay_once_and_accept_races_cancel(self):
        import threading
        sh, by = self.shooter(), self.buyer()
        w_sh = self.wallet(sh)
        o = self.order(by, sh)['order']
        self.op(sh, 'accept', id=o['id'])
        self.shoot_all(sh, o['id'])
        out, errs = [], []

        def go():
            try:
                out.append(self.op(sh, 'deliver', id=o['id'], pick=0, rt={}))
            except Exception as e:   # noqa: BLE001  (a racing delivery may be refused or answer "again")
                errs.append(e)
        ts = [threading.Thread(target=go) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(self.wallet(sh), w_sh + 855, 'paid exactly once')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM photos WHERE order_id=?', (o['id'],)).fetchone()[0], 1)
        # accept against cancel: one wins, the money is where the winner says
        w = self.wallet(by)
        c = self.order(by, sh)['order']
        res = {}

        def accept():
            try:
                res['a'] = self.op(sh, 'accept', id=c['id'])
            except P.PhotoError as e:
                res['a'] = e.code

        def cancel():
            try:
                res['c'] = P.post(self.store, by, None, 'cancel', dict(id=c['id']))
            except P.PhotoError as e:
                res['c'] = e.code
        ts = [threading.Thread(target=accept), threading.Thread(target=cancel)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        status = self.row(c['id'])['status']
        self.assertIn(status, ('shoot', 'cancelled'))
        self.assertEqual(self.wallet(by), w if status == 'cancelled' else w - 900)


class Forget(Base):
    def test_a_player_who_erases_their_data(self):
        sh, by = self.shooter(), self.buyer()
        o = self.order(by, sh)['order']
        self.op(sh, 'accept', id=o['id'])
        self.shoot_all(sh, o['id'])
        photo = self.op(sh, 'deliver', id=o['id'], pick=0, rt={})['photo']
        P.post(self.store, by, None, 'pfp', dict(id=photo))
        waiting = self.order(by, sh)['order']
        # the photographer erases: the waiting order is declined, its buyer gets the price back
        w = self.wallet(by)
        P.forget(self.store, sh)
        self.assertEqual(self.row(waiting['id'])['status'], 'declined')
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w + 900)
        self.assertEqual(P.get(self.store, by, None, 'album', {})['photos'][0]['by']['name'], P.GONE)
        # the buyer erases: their photo leaves the portfolio, their profile photo goes; the rows stay
        P.forget(self.store, by)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT folio FROM photos WHERE id=?', (photo,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT photo FROM photo_pfp WHERE sid=?', (self.sid(by),)).fetchone()[0], '')


class Lists(Base):
    def test_ids_match_the_client(self):
        poses = (ROOT / 'public/js/v4/booth-poses.js').read_text(encoding='utf-8')
        rows = poses[poses.index('const ROWS=['):poses.index('export const POSES')]
        ids = dict(re.findall(r"\['([a-z_]+)','[^']+','[^']+',(\d)\]", rows))
        for p in P.SOLO_POSES:
            self.assertEqual(ids.get(p), '0', p)
        for p in P.GROUP_POSES:
            self.assertEqual(ids.get(p), '1', p)
        faces = poses[poses.index('const FACE_ROWS=['):poses.index('export const FACES')]
        self.assertLessEqual(set(P.FACES), set(re.findall(r"\['([a-z_]+)'", faces)))
        frames = (ROOT / 'public/js/v4/photo-frames.js').read_text(encoding='utf-8')
        props = frames[frames.index('export const PROPS=['):frames.index('const PROP=')]
        self.assertLessEqual(set(P.PROPS) - {'none'}, set(re.findall(r"id:'([a-z_]+)'", props)))
        art = (ROOT / 'public/js/v4/portrait-art.js').read_text(encoding='utf-8')
        for k in P.BACKDROPS:
            self.assertRegex(art, rf"\b{k}:", f'backdrop {k} is drawn')
        for k in P.LIGHTS:
            self.assertRegex(art, rf"\b{k}:", f'light {k} is drawn')
        for k in P.PRODUCTS:
            self.assertIn(k, art)

    def test_split_and_caps(self):
        for pkg in P.PKGS:
            self.assertEqual(P.default_of(pkg), P.PKGS[pkg]['base'] * 3)
            for price in (P.floor_of(pkg), P.default_of(pkg), P.cap_of(pkg), 301, 999):
                pay, burn = P.split(price)
                self.assertEqual(pay + burn, price)
                self.assertEqual(burn, price * 5 // 100)

    def test_marketplace_seam(self):
        """🛎️ Phố dịch vụ lists the packages (own flow): the real registry takes every spec (strict: a refusal raises)."""
        from game import service_market as sm
        self.assertTrue(P.install(strict=True))
        for pkg in P.PKGS:
            spec = sm.REGISTRY[(P.CAREER, pkg)]
            self.assertTrue(sm.is_own(spec))
            self.assertEqual((spec['base'], spec['floor'], spec['max_price']), (P.PKGS[pkg]['base'], P.floor_of(pkg), P.cap_of(pkg)))
            self.assertEqual(spec['open']['action'], 'photoStudio')
            self.assertIsNone(spec['deliver'], 'never the market escrow: the order, the session and the payout stay here')
        # a registry that refuses never breaks the studio at runtime (logged), and fails loudly when strict
        with mock.patch.object(sm, 'register', side_effect=ValueError('no')):
            with self.assertLogs('game.photo_studio', 'ERROR'):
                self.assertFalse(P.install())
            with self.assertRaises(ValueError):
                P.install(strict=True)
        self.assertTrue(P.install())
