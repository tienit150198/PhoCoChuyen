"""🛎️ Phố dịch vụ (game/service_market.py): players serve players across careers (owner 21/10).

Two (or three) real accounts on one store: prices (×3 default, ×N, floors, thương lượng with rounds and expiry), escrow
exactly once under concurrency, the 5 % burned (money conservation: buyer − provider − burn = 0), cancels / declines /
expiries refund in full, the anti-laundering rules (same network, spouses, pair caps, new accounts, self, max price),
ratings and khách quen, reports, career hooks (deliver, on_buyer, svc_done in a command), legacy workplace orders
(×3, negotiated, 95 %, real-margin staff bonus, the quầy visitor cap) and account deletion."""
import concurrent.futures
import time
from unittest.mock import patch

from game import bank as bk
from game import marriage as mr
from game import player_service_tasks as pst
from game import service_market as sm
from tests.test_quay_hire import Base

HOOKS = []


def _deliver(db, provider, buyer, order):
    HOOKS.append(('deliver', order['id'], order['price']))
    db.execute("INSERT INTO svc_net(sid,tag,at) VALUES(?,?,?) ON CONFLICT DO NOTHING", (buyer, 'hook-' + order['id'][:12], 1.0))
    return dict(photo='p-' + order['id'][-6:])


def _on_buyer(state, order):
    HOOKS.append(('buyer', order['id'], order['paid']))
    state['journey']['wallet'] += 0   # a real career puts its effect here (an album photo, a booked night…)


class _Helpers(Base):
    def setUp(self):
        super().setUp()
        HOOKS.clear()
        sm._swept[0] = 0.0
        saved = dict(sm.specs())
        self.addCleanup(lambda: (sm.REGISTRY.clear(), sm.REGISTRY.update(saved)))
        sm.register('milk_tea', 'tasting', dict(name='Thử trà tại nhà', base=1000, unit='lượt'))
        sm.register('milk_tea', 'portrait', dict(name='Chụp ảnh ly trà', base=2000, deliver=_deliver, on_buyer=_on_buyer, unit='tấm', qty_max=3))
        sm.register('milk_tea', 'room', dict(name='Phòng sinh', base=100_000, floor=500_000, max_price=60_000_000))

    # ------------------------------------------------------------ helpers
    def user(self, name, **kw):
        tok = super().user(name, **kw)
        self.cmd(tok, 'select_career', career='milk_tea')
        self.cmd(tok, 'start_day', career='milk_tea')
        return tok

    def total(self, tok):
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def fund(self, tok, wallet):
        mr._mutate(self.store, {self.sid(tok): lambda s: s['journey'].update(wallet=wallet)})

    def get(self, tok, sub, **q):
        return sm.get(self.store, tok, None, sub, q)

    def post(self, tok, sub, ip='', **d):
        return sm.post(self.store, tok, None, sub, d, ip=ip)

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def sell(self, tok, service='tasting', mode='fixed', mult=3, on=True):
        return self.post(tok, 'settings', career='milk_tea', service=service, on=on, mode=mode, mult=mult)

    def order(self, buyer, seller, service='tasting', rid=None, ip='', **kw):
        self.rid += 1
        return self.post(buyer, 'order', ip=ip, pid=self.pid(seller), career='milk_tea', service=service, rid=rid or f'ord-{self.rid:08d}', **kw)['order']

    def offer(self, buyer, seller, price, service='tasting', **kw):
        self.rid += 1
        return self.post(buyer, 'offer', pid=self.pid(seller), career='milk_tea', service=service, price=price, rid=f'off-{self.rid:08d}', **kw)['order']

    def row(self, oid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM svc_orders WHERE id=?', (oid,)).fetchone())

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def complete(self, buyer, seller, service='tasting', **kw):
        o = self.order(buyer, seller, service, **kw)
        self.post(seller, 'take', order=o['id'])
        self.post(seller, 'done', order=o['id'])
        return self.post(buyer, 'confirm', order=o['id'])['order']


class Market(_Helpers):
    # ------------------------------------------------------------ prices
    def test_default_x3_custom_multiplier_and_floor(self):
        a, b = self.user('sm_seller'), self.user('sm_buyer')
        self.sell(a)
        d = self.get(b, 'dir', career='milk_tea', service='tasting')
        self.assertEqual([(x['price'], x['mult'], x['mode']) for x in d['items']], [(3000, 3, 'fixed')])
        self.sell(a, mult=7)
        self.assertEqual(self.get(b, 'dir', career='milk_tea', service='tasting')['items'][0]['price'], 7000)
        self.refused('bad_number', self.sell, a, mult=11)
        self.refused('bad_number', self.sell, a, mult=0)
        # a floor (the childbirth room ≥ 500,000) wins over the multiplier; ×10 of the NPC price is the top
        self.sell(a, service='room', mult=1)
        room = self.get(b, 'provider', pid=self.pid(a))
        r = next(x for x in room['items'] if x['service'] == 'room')
        self.assertEqual((r['price'], r['lo'], r['hi']), (500_000, 500_000, 1_000_000))
        self.sell(a, service='room', mult=10)
        self.assertEqual(next(x for x in self.get(b, 'provider', pid=self.pid(a))['items'] if x['service'] == 'room')['price'], 1_000_000)
        # a changed price never charges the old one
        self.refused('quote_changed', self.order, b, a, expected_price=3000)
        o = self.order(b, a, expected_price=7000)
        self.assertEqual((o['status'], o['price']), ('held', 7000))

    def test_quantity_multiplies_and_is_bounded(self):
        a, b = self.user('sm_qa'), self.user('sm_qb')
        self.sell(a, service='portrait', mult=2)
        o = self.order(b, a, 'portrait', qty=3)
        self.assertEqual(o['price'], 2000 * 2 * 3)
        self.refused('bad_number', self.order, b, a, 'portrait', qty=4)

    # ------------------------------------------------------------ escrow, fee, conservation
    def test_completed_deal_pays_95_burns_5_and_money_is_conserved(self):
        a, b = self.user('sm_pa'), self.user('sm_pb')
        self.sell(a, mult=5)
        ta, tb = self.total(a), self.total(b)
        o = self.order(b, a)
        self.assertEqual(self.total(b), tb - 5000)
        self.post(a, 'take', order=o['id'])
        done = self.post(a, 'done', order=o['id'])['order']
        self.assertEqual(done['status'], 'delivered')
        self.assertEqual(self.total(a), ta, 'nothing paid before the buyer confirms')
        out = self.post(b, 'confirm', order=o['id'])['order']
        self.assertEqual(out['status'], 'done')
        fee = sm.fee_of(5000)
        self.assertEqual(fee, 250)
        self.assertEqual(self.total(a) - ta, 5000 - fee)
        self.assertEqual((tb - self.total(b)) - (self.total(a) - ta) - fee, 0, 'buyer − provider − burn = 0')
        r = self.row(o['id'])
        self.assertEqual((r['fee'], r['paid']), (fee, 5000 - fee))
        self.assertEqual(sm.admin_view(self.store)['totals']['burned'], fee)
        # again: nothing more moves
        self.post(b, 'confirm', order=o['id'])
        self.post(a, 'receive')
        self.assertEqual(self.total(a) - ta, 5000 - fee)

    def test_fee_rounds_up(self):
        self.assertEqual([sm.fee_of(x) for x in (1, 7, 20, 21, 100, 101, 3000)], [1, 1, 1, 2, 5, 6, 150])

    def test_wallet_then_bank_never_debt(self):
        a, b = self.user('sm_wa'), self.user('sm_wb')
        self.sell(a, mult=10)   # 10,000
        mr._mutate(self.store, {self.sid(b): lambda s: (s['journey'].update(wallet=4000), s['journey'].pop('bank', None))})
        self.refused('no_money', self.order, b, a)

        def bank(s):
            s['journey']['bank'] = bk.initial(1, s['journey']['life_day'])
            bk.get(s)['balance'] = 6000
        mr._mutate(self.store, {self.sid(b): bank})
        self.order(b, a)
        s = self.state(b)
        self.assertEqual((s['journey']['wallet'], bk.get(s)['balance']), (0, 0))
        self.refused('no_money', self.order, b, a)
        mr._mutate(self.store, {self.sid(b): lambda s: s['journey'].update(wallet=-5)})
        self.refused('in_debt', self.order, b, a)

    def test_concurrent_confirms_and_polls_pay_once(self):
        a, b = self.user('sm_ca'), self.user('sm_cb')
        self.sell(a)
        ta = self.total(a)
        o = self.order(b, a)
        self.post(a, 'take', order=o['id'])
        self.post(a, 'done', order=o['id'])
        calls = [lambda: self.post(b, 'confirm', order=o['id']), lambda: self.post(b, 'confirm', order=o['id']),
                 lambda: self.post(a, 'receive'), lambda: self.get(b, 'inbox'), lambda: sm.settle_for(self.store, None)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for f in [pool.submit(c) for c in calls]:
                try:
                    f.result()
                except mr.MarriageError:
                    pass
        sm.settle_for(self.store, None)
        self.assertEqual(self.row(o['id'])['status'], 'done')
        self.assertEqual(self.total(a) - ta, 3000 - sm.fee_of(3000))

    def test_concurrent_same_order_request_debits_once(self):
        a, b = self.user('sm_ra'), self.user('sm_rb')
        self.sell(a)
        tb = self.total(b)
        body = dict(pid=self.pid(a), career='milk_tea', service='tasting', rid='same-rid-0001')
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(lambda _: self.post(b, 'order', **body)['order']['id'], range(3)))
        self.assertEqual(len(set(rows)), 1)
        self.assertEqual(tb - self.total(b), 3000)

    def test_concurrent_accepts_of_one_talk_escrow_once(self):
        a, b = self.user('sm_ta'), self.user('sm_tb')
        self.sell(a, mode='nego')
        tb = self.total(b)
        t = self.offer(b, a, 2500)
        def accept():
            try:
                return self.post(a, 'answer', order=t['id'], op='accept', ask=2500)['order']['status']
            except mr.MarriageError as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            got = list(pool.map(lambda _: accept(), range(3)))
        self.assertIn('working', got)
        self.assertEqual(tb - self.total(b), 2500)
        self.assertEqual(self.row(t['id'])['price'], 2500)

    # ------------------------------------------------------------ negotiation
    def test_negotiation_rounds_bounds_and_lock_in(self):
        a, b = self.user('sm_na'), self.user('sm_nb')
        self.sell(a, mode='nego')
        self.refused('negotiate', self.order, b, a)
        self.refused('bad_price', self.offer, b, a, 999)        # below the NPC price (×1)
        self.refused('bad_price', self.offer, b, a, 10001)      # above ×10
        tb = self.total(b)
        t = self.offer(b, a, 1500)
        self.assertEqual((t['status'], t['ask'], t['ask_by'], t['rounds']), ('talk', 1500, 'buyer', 1))
        self.assertEqual(self.total(b), tb, 'a talk holds no money')
        self.refused('not_your_turn', self.post, b, 'answer', order=t['id'], op='accept')
        price = 4000
        for i in range(5):   # rounds 2…6
            who = a if i % 2 == 0 else b
            t = self.post(who, 'answer', order=t['id'], op='counter', price=price)['order']
            price -= 300
        self.assertEqual(t['rounds'], sm.MAX_ROUNDS)
        self.assertNotIn('counter', self.get(b, 'inbox')['items'][0]['actions'])
        self.refused('rounds', self.post, b, 'answer', order=t['id'], op='counter', price=2000)
        self.refused('ask_changed', self.post, b, 'answer', order=t['id'], op='accept', ask=1)
        out = self.post(b, 'answer', order=t['id'], op='accept', ask=t['ask'])['order']
        self.assertEqual((out['status'], out['price']), ('working', t['ask']))
        self.assertEqual(tb - self.total(b), t['ask'])

    def test_talk_expires_and_declines_without_money(self):
        a, b = self.user('sm_ea'), self.user('sm_eb')
        self.sell(a, mode='nego')
        tb = self.total(b)
        t = self.offer(b, a, 2000)
        with patch('time.time', return_value=time.time() + sm.TALK_HOURS * 3600 + 5):
            self.get(b, 'inbox')
        self.assertEqual(self.row(t['id'])['status'], 'expired')
        t2 = self.offer(b, a, 2000)
        self.post(a, 'decline', order=t2['id'])
        self.assertEqual(self.row(t2['id'])['status'], 'declined')
        self.assertEqual(self.total(b), tb)

    # ------------------------------------------------------------ refunds
    def test_cancel_decline_expiry_and_late_provider_refund_in_full(self):
        a, b = self.user('sm_xa'), self.user('sm_xb')
        self.sell(a)
        tb = self.total(b)
        o1 = self.order(b, a)
        self.post(b, 'cancel', order=o1['id'])
        self.assertEqual(self.total(b), tb)
        o2 = self.order(b, a)
        self.post(a, 'take', order=o2['id'])
        self.refused('already_started', self.post, b, 'cancel', order=o2['id'])   # work started: only the provider may stop it
        self.post(a, 'decline', order=o2['id'])
        self.assertEqual(self.total(b), tb)
        o3 = self.order(b, a)
        o4 = self.order(b, a)
        self.post(a, 'take', order=o4['id'])
        later = time.time() + sm.WORK_HOURS * 3600 + 60
        with patch('time.time', return_value=later):
            sm._swept[0] = 0.0
            sm.run_housekeeping(self.store)
        self.assertEqual((self.row(o3['id'])['status'], self.row(o4['id'])['status']), ('refunded', 'refunded'))
        self.assertEqual(self.total(b), tb)
        self.assertEqual(sm.admin_view(self.store)['totals']['burned'], 0)

    def test_delivered_order_auto_confirms_and_pays_with_both_away(self):
        a, b = self.user('sm_aa'), self.user('sm_ab')
        self.sell(a)
        ta = self.total(a)
        o = self.order(b, a)
        self.post(a, 'take', order=o['id'])
        self.post(a, 'done', order=o['id'])
        with patch('time.time', return_value=time.time() + sm.CONFIRM_HOURS * 3600 + 60):
            sm._swept[0] = 0.0
            sm.run_housekeeping(self.store)
        self.assertEqual(self.row(o['id'])['status'], 'done')
        self.assertEqual(self.total(a) - ta, 3000 - sm.fee_of(3000))

    # ------------------------------------------------------------ anti-laundering
    def test_self_same_network_and_spouse(self):
        a, b, c = self.user('sm_la'), self.user('sm_lb'), self.user('sm_lc')
        self.sell(a)
        self.refused('self', self.post, a, 'order', pid=self.pid(a), career='milk_tea', service='tasting', rid='self-order-01')
        self.get(a, 'mine')
        self.post(a, 'settings', ip='10.0.0.7', career='milk_tea', service='tasting', on=True, mode='fixed', mult=3)
        self.refused('same_net', self.order, b, a, ip='10.0.0.7')
        # once seen on that network (even refused), b cannot buy from a from elsewhere either (within NET_DAYS)
        with self.store.connect() as db:
            self.assertTrue(sm.same_net(db, self.sid(b), self.sid(a)))
        self.refused('same_net', self.order, b, a, ip='10.9.9.9')
        # lixi grabs on one network count too
        self.store.transaction(lambda db: db.execute("INSERT INTO lixi_grabs(packet,sid,pid,amount,day,ip,at) VALUES('pk1',?,?,5,'d',?,?)",
                                                     (self.sid(c), 'x', sm.net_tags('10.0.0.7')[0], time.time())))
        self.refused('same_net', self.order, c, a)
        # a married couple shares a home network: allowed (and counted in the caps)
        def wed(db):
            cid = db.execute("INSERT INTO couples(a,b,status,since,married_at) VALUES(?,?,'married',1,1) RETURNING id", (self.sid(a), self.sid(b))).fetchone()['id']
            for x in (a, b):
                db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (self.sid(x), cid))
        self.store.transaction(wed)
        o = self.order(b, a, ip='10.0.0.7')
        self.assertEqual(o['status'], 'held')
        with self.store.connect() as db:
            self.assertEqual(sm.pair_usage(db, self.sid(b), self.sid(a))['day'], 1)

    def test_pair_day_and_week_caps_and_max_price(self):
        a, b = self.user('sm_ka'), self.user('sm_kb')
        self.sell(a)
        for _ in range(sm.PAIR_DAY):
            self.order(b, a)
        self.refused('pair_day', self.order, b, a)
        # the week: a big service fills it
        c, d = self.user('sm_kc'), self.user('sm_kd')
        self.sell(c, mult=10)                              # 10,000 an order
        with patch.object(sm, 'PAIR_WEEK_XU', 25_000):
            self.order(d, c)
            self.order(d, c)
            self.refused('pair_week', self.order, d, c)
            with self.store.connect() as db:          # a service declaring a higher max price allows one such order a week
                self.assertEqual(sm.week_cap(sm.get_spec('milk_tea', 'room')), 60_000_000)
        with self.store.connect() as db:
            self.refused('too_much', sm.guard, db, self.sid(d), self.sid(c), 60_000_001, sm.get_spec('milk_tea', 'room'), money=False)
            self.refused('too_much', sm.guard, db, self.sid(d), self.sid(c), sm.MAX_PRICE + 1, sm.get_spec('milk_tea', 'tasting'), money=False)

    def test_new_account_shares_the_bank_transfer_day_cap(self):
        from game import bank_xfer
        a = self.user('sm_na_old')
        b = Base.user(self, 'sm_na_new', old=False)
        self.cmd(b, 'select_career', career='milk_tea')
        self.fund(b, 2_000_000)
        self.sell(a, service='room', mult=1)       # 500,000
        self.order(b, a, 'room')
        with self.store.connect() as db:
            self.assertEqual(bank_xfer._today(db, self.sid(b), bank_xfer.vn_day())['sent'], 500_000)
        self.sell(a)                                # 3,000 more today: past the 500,000 a young account may send
        self.refused('day_cap', self.order, b, a, 'tasting')

    def test_blocked_either_way(self):
        a, b = self.user('sm_ba'), self.user('sm_bb')
        self.sell(a)
        self.store.transaction(lambda db: db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (self.sid(a), self.sid(b), 1)))
        self.assertEqual(self.get(b, 'dir')['items'], [])
        self.refused('blocked', self.order, b, a)

    # ------------------------------------------------------------ hooks, reputation, reports
    def test_deliver_hook_and_buyer_effect_run_once(self):
        a, b = self.user('sm_ha'), self.user('sm_hb')
        self.sell(a, service='portrait')
        o = self.order(b, a, 'portrait')
        self.refused('not_working', self.post, a, 'done', order=o['id'])
        self.post(a, 'take', order=o['id'])
        out = self.post(a, 'done', order=o['id'], result={'pose': 'cười'})['order']
        self.assertEqual(out['status'], 'done', "a hook's proof settles at once (confirm 'auto')")
        self.assertEqual(out['result'], dict(photo='p-' + o['id'][-6:]))
        self.post(a, 'done', order=o['id'])
        sm.deliver(self.store, self.sid(a), o['id'])
        self.assertEqual([h[0] for h in HOOKS], ['deliver', 'buyer'])
        self.assertEqual(HOOKS[1][2], 6000 - sm.fee_of(6000))
        with self.store.connect() as db:
            self.assertEqual(sm.order_of(db, o['id'])['result'], out['result'])

    def test_command_svc_done_marks_ready_and_poll_pays(self):
        a, b = self.user('sm_da'), self.user('sm_db')
        self.sell(a, service='portrait')
        ta = self.total(a)
        o = self.order(b, a, 'portrait')
        self.post(a, 'take', order=o['id'])
        with self.store.connect() as db:
            self.assertEqual([x['id'] for x in sm.open_orders(db, self.sid(a), 'milk_tea')], [o['id']])
        self.store.transaction(lambda db: sm.command_commit(db, self.sid(a), {'svc_done': [{'order': o['id']}, {'order': 'sv_' + '0' * 24}]}))
        self.assertEqual(self.row(o['id'])['status'], 'ready')
        self.post(a, 'receive')
        self.assertEqual(self.total(a) - ta, 6000 - sm.fee_of(6000))

    def test_rating_reputation_regulars_and_reports(self):
        a, b = self.user('sm_ra2'), self.user('sm_rb2')
        self.sell(a)
        o1 = self.complete(b, a)
        self.assertIn('rate', o1['actions'])
        self.post(b, 'rate', order=o1['id'], stars=5, comment='Ngon')
        o2 = self.complete(b, a)
        self.post(b, 'rate', order=o2['id'], stars=1)
        card = self.get(b, 'provider', pid=self.pid(a))
        self.assertEqual((card['rep']['n'], card['rep']['avg'], card['rep']['deals']), (1, 5.0, 2), 'one counted rating a week per pair')
        self.assertEqual(card['rep']['regulars'], 1)
        self.assertEqual(self.get(a, 'provider', pid=self.pid(a))['regulars'][0]['n'], 2)
        self.refused('not_completed', self.post, b, 'rate', order=self.order(b, a)['id'], stars=5)
        # a report within 24 h goes to the admin, nothing automatic
        self.post(b, 'flag', order=o2['id'], text='Giao thiếu món')
        v = sm.admin_view(self.store)
        self.assertEqual([(f['order'], f['status']) for f in v['flags']], [(o2['id'], 'open')])
        sm.admin_act(self.store, 'admin', dict(op='close', order=o2['id'], note='Đã nhắc'))
        self.assertEqual(sm.admin_view(self.store)['flags'][0]['status'], 'closed')
        with patch('time.time', return_value=time.time() + sm.FLAG_HOURS * 3600 + 60):
            self.refused('late', self.post, b, 'flag', order=o1['id'], text='Quá giờ rồi')

    def test_directory_sorts_and_online(self):
        a, b, c = self.user('sm_sa'), self.user('sm_sb'), self.user('sm_sc')
        self.sell(a, mult=2)
        self.sell(b, mult=8)
        price = [x['price'] for x in self.get(c, 'dir', sort='price', service='tasting')['items']]
        self.assertEqual(price, sorted(price))
        self.complete(c, b)
        self.post(c, 'rate', order=self.get(c, 'inbox')['items'][0]['id'], stars=5)
        rated = self.get(c, 'dir', sort='rating', service='tasting')['items']
        self.assertEqual(rated[0]['pid'], self.pid(b))
        self.assertTrue(all('online' in x for x in rated))
        self.assertTrue(self.get(c, 'dir')['counts'])

    def test_alerts_badge(self):
        a, b = self.user('sm_ba3'), self.user('sm_bb3')
        self.sell(a, mode='nego')
        self.offer(b, a, 2000)
        with self.store.connect() as db:
            self.assertEqual((sm.alert_count(db, self.sid(a)), sm.alert_count(db, self.sid(b))), (1, 0))
        self.assertEqual(mr.alerts(self.store, self.sid(a))['svc'], 1)

    def test_provider_deleted_refunds_buyer(self):
        a, b = self.user('sm_fa'), self.user('sm_fb')
        self.sell(a)
        tb = self.total(b)
        o = self.order(b, a)
        self.post(a, 'take', order=o['id'])
        self.store.delete(a)
        self.get(b, 'inbox')
        self.assertEqual(self.row(o['id'])['status'], 'refunded')
        self.assertEqual(self.total(b), tb)

    def test_register_contract(self):
        with self.assertRaises(ValueError):
            sm.register('milk_tea', 'bad', dict(name='x', base=0))
        with self.assertRaises(ValueError):
            sm.register('milk_tea', 'bad', dict(name='x', base=1, wat=1))
        with self.assertRaises(ValueError):
            sm.register('milk_tea', 'bad', dict(name='x', base=1, confirm='auto'))
        spec = sm.register('nurse', 'birth_room', dict(name='Phòng sinh', base=200_000, floor=500_000, requires=dict(married=True)))
        self.assertEqual((spec['floor'], spec['max_price'], spec['confirm'], spec['pay_to']), (500_000, sm.MAX_PRICE, 'buyer', 'wallet'))
        self.assertEqual(sm.bounds(spec, 200_000), (500_000, 2_000_000))
        self.assertIn(('milk_tea', 'job'), sm.specs())
        self.assertIn(('quay', 'dish'), sm.specs())

    def test_requirements(self):
        a, b = self.user('sm_qa2'), self.user('sm_qb2')
        sm.register('milk_tea', 'wed', dict(name='Chụp ảnh cưới', base=1000, requires=dict(married=True, life_day=5)))
        self.sell(a, service='wed')
        self.refused('requirement', self.order, b, a, 'wed')


class Legacy(_Helpers):
    """Today's workplace orders (game/work_visits.py) through Phố dịch vụ."""

    def place(self, tok):
        from game import work_visits as wv
        return next(p for p in wv.get(self.store, tok, None, 'places', {'scope': 'mine'})['places'] if p['target'] == 'milk_tea')

    def test_listed_legacy_place_x3_fixed_order_and_95_percent(self):
        from game import work_visits as wv
        a, b = self.user('lg_a'), self.user('lg_b')
        self.sell(a, service='job')
        d = self.get(b, 'dir', career='milk_tea', service='job')['items']
        self.assertEqual(len(d), 1)
        offer = d[0]['offers'][0]
        self.assertEqual(offer['price'], offer['base'] * 3)
        # listed: a buyer who is not a friend may order there (the place stays 'friends')
        self.assertEqual(self.place(a)['visibility'], 'friends')
        o = self.post(b, 'order', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      rid='legacy-fixed-01', expected_price=offer['price'])['order']
        self.assertEqual((o['status'], o['price']), ('requested', offer['price']))
        with patch.object(wv, '_bridge', return_value=pst):
            acc = wv.post(self.store, a, None, 'accept', {'order': o['id']})
            meta = next(t for t in self.state(a)['careers']['milk_tea']['tasks'] if t['id'] == acc['task_id'])['player_order']
            self.assertEqual(meta['price'], offer['price'], 'the save keeps the price charged (≤ 1,000,000: every build validates it)')
            before = self.state(a)['careers']['milk_tea']['money']
            st = self.state(a)
            self.store.transaction(lambda db: wv.command_commit(db, self.sid(a), st, st, 'milk_tea', 'task_action', {}))
            with self.store.connect() as db:
                db.execute("UPDATE work_service_orders SET status='ready' WHERE id=?", (o['id'],))
                db.commit()
            wv.post(self.store, a, None, 'receive', {})
        self.assertEqual(self.state(a)['careers']['milk_tea']['money'] - before, offer['price'] - sm.fee_of(offer['price']))
        with self.store.connect() as db:
            r = db.execute('SELECT fee FROM work_service_orders WHERE id=?', (o['id'],)).fetchone()
        self.assertEqual(r['fee'], sm.fee_of(offer['price']))

    def test_legacy_negotiation_links_an_order_at_the_agreed_price(self):
        a, b = self.user('lg_na'), self.user('lg_nb')
        self.sell(a, service='job', mode='nego')
        offer = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers'][0]
        self.assertTrue(offer['nego'])
        from game import work_visits as wv
        with self.assertRaises(mr.MarriageError) as cm:   # a direct order at that place is refused while it negotiates
            wv.post(self.store, b, None, 'order', dict(place=offer['place'], offer_id=offer['offer_id'], rid='legacy-direct-1'))
        self.assertEqual(cm.exception.code, 'negotiate')
        tb = self.total(b)
        t = self.post(b, 'offer', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      price=offer['base'] * 2, rid='legacy-talk-01')['order']
        self.assertEqual(t['kind'], 'wo')
        from game import work_visits as wv
        with patch.object(wv, '_bridge', return_value=pst):
            out = self.post(a, 'answer', order=t['id'], op='accept', ask=offer['base'] * 2)
        self.assertEqual(out['order']['price'], offer['base'] * 2)
        self.assertEqual(tb - self.total(b), offer['base'] * 2)
        r = self.row(t['id'])
        self.assertEqual((r['status'], r['link']), ('linked', out['order']['id']))

    def test_legacy_talk_survives_the_next_customer_ticket(self):
        """#526: the provider served another customer (or closed the shift) after the buyer bargained: the ticket the
        talk names is gone. Agreeing moves the talk to the shop's current ticket, never 'Dịch vụ này hiện chưa sẵn sàng.'"""
        from game import work_visits as wv
        a, b = self.user('lg_ra'), self.user('lg_rb')
        self.sell(a, service='job', mode='nego')
        offer = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers'][0]
        price = offer['base'] * 2
        t = self.post(b, 'offer', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      price=price, rid='legacy-talk-26')['order']
        # the shop serves a customer and takes its next NPC one: the ticket the talk names is gone
        mr._mutate(self.store, {self.sid(a): lambda s: s['careers']['milk_tea']['tasks'][0].update(status='completed')})
        self.cmd(a, 'more_work', career='milk_tea')
        now = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers']
        self.assertNotIn(offer['offer_id'], [o['offer_id'] for o in now])
        with patch.object(wv, '_bridge', return_value=pst):
            out = self.post(a, 'answer', order=t['id'], op='accept', ask=price)
        self.assertEqual((out['order']['price'], out['order']['status']), (price, 'accepted'))
        self.assertEqual(self.row(t['id'])['status'], 'linked')

    def test_legacy_talk_on_a_closed_shop_says_what_to_do(self):
        a, b = self.user('lg_ca'), self.user('lg_cb')
        self.sell(a, service='job', mode='nego')
        offer = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers'][0]
        t = self.post(b, 'offer', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      price=offer['base'] * 2, rid='legacy-talk-27')['order']
        with self.store.connect() as db:   # the shift ended: no ticket at all
            db.execute("UPDATE work_visit_places SET data=jsonb_set(jsonb_set(data::jsonb,'{offers}','[]'),'{available}','false')::text "
                       'WHERE id=?', (offer['place'],))
            db.commit()
        msg = self.refused('offer_gone', self.post, a, 'answer', order=t['id'], op='accept', ask=offer['base'] * 2)
        self.assertIn('mở ca rồi bấm Đồng ý lại', msg)
        self.assertEqual(self.row(t['id'])['status'], 'talk')   # still answerable: decline works
        self.assertEqual(self.post(a, 'answer', order=t['id'], op='decline')['order']['status'], 'declined')


    def test_quay_visitor_bonus_cap_stays_at_twice_the_dish_base(self):
        from game import quay as qy, quay_self as qs, quay_business as qb
        from tests.test_quay_business import fixture
        source, st = fixture()
        qb.settle(source, now=2000000000)
        st = qy.stall(source, st['id'])
        dish = next(iter(qs.menu(st)['on']))
        base = qs.DISH[st['trade']][dish]['base']
        price = base * 10
        st['business'].setdefault('visitor_orders', []).append(dict(v=1, id='wo_' + 'a' * 24, buyer=dict(name='B', code='', fc=''), note='', price=price,
                                                                   dish=dish, status='completed', accepted_at=0, due_at=None, completed_at=1,
                                                                   quality=5, staffed=False, settled=False))
        seen = []
        real = qb.reward_margin
        with patch.object(qb, 'reward_margin', side_effect=lambda s, basis, costs: (seen.append(basis), real(s, basis, costs))[1]):
            got = pst.credit_visit(source, st['id'], 'wo_' + 'a' * 24, price, paid=price - sm.fee_of(price))
        self.assertEqual(seen, [base * pst.VISIT_BONUS_RATIO])
        self.assertLessEqual(got, price - sm.fee_of(price))

    def test_staff_bonus_counts_only_the_npc_margin(self):
        from game import workplace_business as wb
        calls = []
        with patch.object(wb, 'credit_profit_bonus', side_effect=lambda c, margin, *a, **k: calls.append(margin) or 0):
            s = dict(careers=dict(milk_tea=dict(player_service_jobs=[dict(id='o1', settled=False, status='completed', price=300, wage=5, materials=1, goods=4, label='Đơn')],
                                                ops=dict(business={}))))
            with patch.object(wb, 'prepare', return_value=None):
                pst.credit_staff_bonus(s, 'milk_tea', 'o1', 300, paid=285, base=30)
                pst.credit_staff_bonus(s, 'milk_tea', 'o1', 300)
        self.assertEqual(calls, [30 - 10, 300 - 10])


class OwnFlow(_Helpers):
    """🏥 player birth rooms (game/birth.py) and 📸 player photographers (game/photo_studio.py) are LISTED in Phố dịch vụ:
    their own booking, escrow and payout stay in their modules; the market never orders, holds or sets them up."""

    def setUp(self):
        super().setUp()
        from game import photo_studio as P
        self.P = P
        self.OWN = [('homestay', 'phong_sinh')] + [('photobooth', k) for k in P.PKGS]

    def room(self, tok, price=700_000, open_=True, career='homestay', name='Phòng Đồi Thông'):
        sid = self.sid(tok)
        self.store.transaction(lambda db: db.execute(
            'INSERT INTO birth_rooms(sid,career,name,price,open,at) VALUES(?,?,?,?,?,?) ON CONFLICT (sid) DO UPDATE SET '
            'career=EXCLUDED.career,name=EXCLUDED.name,price=EXCLUDED.price,open=EXCLUDED.open', (sid, career, name, price, open_, time.time())))
        with self.store.connect() as db:
            return int(db.execute('SELECT id FROM birth_rooms WHERE sid=?', (sid,)).fetchone()['id'])

    def shooter(self, name='sm_tho'):
        from game import work_visits as wv
        tok = Base.user(self, name)
        self.cmd(tok, 'select_career', career='photobooth')
        self.cmd(tok, 'start_day', career='photobooth')
        wv.post(self.store, tok, self.state(tok), 'visibility', dict(place=self.P.place_id(self.sid(tok)), visibility='public'))
        return tok

    def own_items(self, tok, **q):
        return [x for x in self.get(tok, 'dir', **q)['items'] if x.get('own')]

    # ------------------------------------------------------------ the registry
    def test_registry_holds_every_own_listing_after_server_start(self):
        import server  # noqa: F401  (server start: service_market.install_own())
        for key in self.OWN:
            self.assertIn(key, sm.REGISTRY, f'{key} missing: its register() call was refused')
            self.assertTrue(sm.is_own(sm.REGISTRY[key]), key)
        self.assertTrue(sm.install_own(strict=True), 'every spec is valid (strict: a refusal raises here)')
        # the market's own seed wires them too, whatever imported first
        saved = dict(sm.REGISTRY)
        try:
            sm.REGISTRY.clear()
            sm._seeded[0] = False
            for key in self.OWN:
                self.assertIn(key, sm.specs())
        finally:
            sm.REGISTRY.clear()
            sm.REGISTRY.update(saved)
            sm._seeded[0] = True
        # the old seam keys are what the registry refuses (they failed silently before)
        with self.assertRaises(ValueError):
            sm.register('homestay', 'phong_sinh_x', dict(name='Phòng sinh', emoji='🏥', base=1, max=5, hours=3))
        # an own-flow listing never takes the escrow hooks; providers / offer need open
        prov, offer = (lambda db, limit, offset: []), (lambda db, sid: None)
        link = dict(action='marriage', data=dict(tab='family'))
        for bad in (dict(deliver=_deliver), dict(on_buyer=_on_buyer), dict(confirm='buyer'), dict(pay_to='career'), dict(qty_max=2), dict(providers=None)):
            with self.assertRaises(ValueError, msg=bad):
                sm.register('milk_tea', 'own_bad', dict(dict(name='X', base=10, open=link, providers=prov, offer=offer), **bad))
        with self.assertRaises(ValueError):
            sm.register('milk_tea', 'own_bad', dict(name='X', base=10, providers=prov, offer=offer))
        with self.assertRaises(ValueError):
            sm.register('milk_tea', 'own_bad', dict(name='X', base=10, open=dict(action='bad action!'), providers=prov, offer=offer))
        self.assertNotIn(('milk_tea', 'own_bad'), sm.REGISTRY)
        self.assertTrue(all(x['own'] for x in sm.catalog()['services'] if (x['career'], x['service']) in self.OWN))

    # ------------------------------------------------------------ 🏥 birth rooms
    def test_birth_room_listed_with_its_price_and_opens_the_family_sheet(self):
        a, b = self.user('sm_nha'), self.user('sm_cap')
        rid = self.room(a, 700_000)
        items = self.own_items(b, career='homestay', service='phong_sinh')
        self.assertEqual(len(items), 1)
        x = items[0]
        self.assertEqual((x['pid'], x['price'], x['note'], x['mine'], x['available']), (self.pid(a), 700_000, 'Phòng Đồi Thông', False, True))
        self.assertEqual(x['open'], dict(action='marriage', data=dict(tab='family', section='children', room=rid), label='👶 Đặt phòng sinh'))
        self.assertIn(x['pid'], [i['pid'] for i in self.own_items(b)], 'listed with every career too')
        self.assertIn(('homestay', 'phong_sinh'), {(c['career'], c['service']) for c in self.get(b, 'dir', career='milk_tea')['counts']})
        self.assertEqual(self.own_items(b, career='hotel'), [], 'a homestay room is not a hotel one')
        # the module's rating and record
        self.store.transaction(lambda db: db.execute('UPDATE birth_rooms SET stars=9, rated=2, born=3 WHERE id=?', (rid,)))
        self.assertEqual(self.own_items(b, career='homestay')[0]['rep'], dict(n=2, avg=4.5, deals=3))
        # closed: gone from the directory
        self.room(a, 700_000, open_=False)
        self.assertEqual(self.own_items(b, career='homestay'), [])

    def test_birth_room_never_ordered_or_set_up_through_the_market(self):
        a, b = self.user('sm_nha2'), self.user('sm_cap2')
        self.room(a, 900_000)
        self.fund(b, 5_000_000)
        before = self.total(b)
        for sub, extra in (('order', dict(expected_price=900_000)), ('offer', dict(price=900_000))):
            self.rid += 1
            self.refused('own_flow', self.post, b, sub, pid=self.pid(a), career='homestay', service='phong_sinh', rid=f'own-{self.rid:08d}', **extra)
        self.refused('own_settings', self.post, a, 'settings', career='homestay', service='phong_sinh', on=True, mode='fixed', mult=1)
        with self.store.connect() as db:
            self.refused('own_flow', sm.quote, db, self.sid(a), 'homestay', 'phong_sinh')
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM svc_orders WHERE service='phong_sinh'").fetchone()['n'], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM svc_settings WHERE service='phong_sinh'").fetchone()['n'], 0)
        self.assertEqual(self.total(b), before, 'nothing held: the booking (and its escrow) is Nhà & Gia đình’s')

    # ------------------------------------------------------------ 📸 photographers
    def test_photographer_packages_listed_and_never_ordered_here(self):
        P = self.P
        sh, b = self.shooter(), self.user('sm_khach')
        items = {x['service']: x for x in self.own_items(b, career='photobooth')}
        self.assertEqual(set(items), set(P.PKGS))
        place = P.place_id(self.sid(sh))
        for pkg, x in items.items():
            self.assertEqual(x['price'], P.default_of(pkg))
            self.assertEqual(x['open'], dict(action='photoStudio', data=dict(tab='order', place=place, pkg=pkg), label='📸 Đặt chụp'))
        # the photographer's own prices (×1–×5) and open flag, set in their studio
        P.post(self.store, sh, None, 'studio', dict(prices=dict(chan_dung=1200)), '10.0.0.9')
        self.assertEqual({x['service']: x['price'] for x in self.own_items(b, career='photobooth')}['chan_dung'], 1200)
        mine = {m['service']: m for m in self.get(sh, 'mine')['services'] if m['career'] == 'photobooth' and m['own']}
        self.assertEqual(set(mine), set(P.PKGS))
        self.assertTrue(mine['chan_dung']['on'] and mine['chan_dung']['own'])
        self.assertEqual((mine['chan_dung']['price'], mine['chan_dung']['setup']['action']), (1200, 'photoStudio'))
        prov = self.get(b, 'provider', pid=self.pid(sh))
        self.assertEqual({x['service'] for x in prov['items'] if x.get('own')}, set(P.PKGS))
        self.rid += 1
        self.refused('own_flow', self.post, b, 'order', pid=self.pid(sh), career='photobooth', service='chan_dung', rid=f'own-{self.rid:08d}')
        self.refused('own_settings', self.post, sh, 'settings', career='photobooth', service='chan_dung', on=True, mode='fixed', mult=3)
        # closed studio, then a friends-only place: not listed (its order sheet would refuse), 🧰 says why
        P.post(self.store, sh, None, 'studio', dict(open=False), '10.0.0.9')
        self.assertEqual(self.own_items(b, career='photobooth'), [])
        self.assertFalse(next(m for m in self.get(sh, 'mine')['services'] if m['service'] == 'chan_dung')['on'])
        P.post(self.store, sh, None, 'studio', dict(open=True), '10.0.0.9')
        from game import work_visits as wv
        wv.post(self.store, sh, self.state(sh), 'visibility', dict(place=place, visibility='friends'))
        self.assertEqual(self.own_items(b, career='photobooth'), [])
        self.assertIn('Mọi người', next(m for m in self.get(sh, 'mine')['services'] if m['service'] == 'chan_dung')['why'])

    def test_own_rows_merge_into_the_sort_and_the_pages(self):
        a, b, c = self.user('sm_mix_a'), self.user('sm_mix_b'), self.user('sm_mix_c')
        self.sell(a, mult=3)            # 🧋 3 000 xu
        self.room(b, 600_000)           # 🏥 600 000 xu
        self.room(c, 550_000)
        viewer = self.user('sm_mix_v')
        full = self.get(viewer, 'dir', sort='price')['items']
        prices = [x['price'] for x in full]
        self.assertEqual(prices, sorted(prices))
        self.assertTrue({3000, 550_000, 600_000} <= set(prices))
        with patch.object(sm, 'PAGE', 2):
            seen, offset = [], 0
            while offset is not None:
                d = self.get(viewer, 'dir', sort='price', offset=offset)
                seen += [(x['pid'], x['career'], x['service']) for x in d['items']]
                offset = d['next']
        self.assertEqual(seen, [(x['pid'], x['career'], x['service']) for x in full], 'every card once, in order, across pages')
