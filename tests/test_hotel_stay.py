"""🏨 Phòng cho người chơi (game/hotel_stay.py): a homestay / hotel player rents rooms to other players through Phố dịch
vụ. Real accounts on one PostgreSQL store (TEST_DATABASE_URL): prices ×3, the whole flow (confirm → arrive → check-in →
the night's situations and the guest's requests → check-out) paying the host 95 % and burning 5 % with money conserved,
the host's burned costs, the guest's rest once a Vietnam day, couples resting together once, refunds on cancel /
decline / no-show, the system check-out, the generic "Xong việc" refused, exactly once under concurrency, the badge and
the kill switch."""
import concurrent.futures
import os
from unittest.mock import patch

from game import bank as bk
from game import hotel_stay as hs
from game import hotel_stay_content as hc
from game import marriage as mr
from game import needs as nd
from game import service_market as sm
from tests.test_quay_hire import Base

H, M = 3600, 60


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class HotelBase(Base):
    def setUp(self):
        super().setUp()
        sm._swept[0] = 0.0
        hs._swept[0] = 0.0
        self.clock = Clock(1_790_000_000.0)
        p = patch('game.service_market.now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.n = 0

    # ------------------------------------------------------------ people
    def host(self, name, career='homestay', wallet=5000):
        tok = self.user(name, wallet=wallet)

        def fn(s):
            s['careers'][career]['started'] = True
        mr._mutate(self.store, {self.sid(tok): fn})
        return tok

    def guest(self, name, wallet=5000):
        return self.user(name, wallet=wallet)

    def couple(self, a, b, status='engaged'):
        sa, sb = self.sid(a), self.sid(b)

        def run(db):
            cid = db.execute("INSERT INTO couples(a,b,status,since) VALUES(?,?,?,?) RETURNING id", (sa, sb, status, 1.0)).fetchone()['id']
            for s in (sa, sb):
                db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (s, cid))
        self.store.transaction(run)

    def total(self, tok):
        s = self.state(tok)
        b = bk.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def sell(self, tok, career='homestay', service='stay_night', mult=3, on=True, mode='fixed'):
        return sm.post(self.store, tok, None, 'settings', dict(career=career, service=service, on=on, mode=mode, mult=mult))

    def order(self, buyer, host, career='homestay', service='stay_night', qty=1):
        self.n += 1
        return sm.post(self.store, buyer, None, 'order', dict(pid=self.pid(host), career=career, service=service, qty=qty,
                                                              rid=f'hotel-{self.n:06d}', note='Phòng yên tĩnh nha'))['order']

    def do(self, tok, op, **d):
        return hs.post(self.store, tok, None, op, d)

    def view(self, tok):
        return hs.view(self.store, self.sid(tok))

    def stay(self, tok, oid):
        v = self.view(tok)
        return next((x for x in v['host']['stays'] + v['guest']['stays'] if x['id'] == oid), None)

    def row(self, oid):
        with self.store.connect() as db:
            return hs._row(db, oid)

    def svc(self, oid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM svc_orders WHERE id=?', (oid,)).fetchone())

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def needs(self, tok):
        return nd.get(self.state(tok)) or {}

    def spirit(self, tok):
        return self.state(tok)['journey']['life']['spirit']

    def to_in(self, host, guest, career='homestay', service='stay_night', qty=1, room=None):
        """Book, confirm, arrive, check in (the first option of the arrival quirk)."""
        o = self.order(guest, host, career, service, qty)
        self.do(host, 'confirm', order=o['id'])
        self.do(guest, 'arrive', order=o['id'])
        st = self.stay(host, o['id'])
        room = room or next(r['id'] for r in st['rooms'] if not r['busy'] and not r['cost'])
        self.do(host, 'checkin', order=o['id'], room=room, pick=st['quirk']['opts'][0]['id'])
        return o


class Prices(HotelBase):
    def test_x3_default_multiplier_bounds_and_both_careers(self):
        a, h, g = self.host('ht_a'), self.host('ht_h', 'hotel'), self.guest('ht_g')
        self.sell(a)
        self.sell(h, 'hotel', 'stay_couple', mult=5)
        d = sm.get(self.store, g, None, 'dir', dict(career='homestay', service='stay_night'))
        self.assertEqual([(x['price'], x['mult'], x['unit']) for x in d['items']], [(90, 3, 'đêm')])
        d = sm.get(self.store, g, None, 'dir', dict(career='hotel', service='stay_couple'))
        self.assertEqual(d['items'][0]['price'], 56 * 5)
        self.assertEqual((d['items'][0]['lo'], d['items'][0]['hi']), (56, 560))
        # a non-host cannot sell rooms; three nights are three times the price
        self.refused('cannot_provide', self.sell, g)
        o = self.order(g, a, qty=3)
        self.assertEqual((o['status'], o['price']), ('held', 270))


class Flow(HotelBase):
    def test_full_stay_pays_95_burns_5_and_the_guest_rests(self):
        h, g = self.host('fl_h'), self.guest('fl_g')
        self.sell(h)
        th, tg = self.total(h), self.total(g)
        wake0, sp0 = self.needs(g).get('wake', nd.START_WAKE), self.spirit(g)
        o = self.order(g, h)
        self.assertEqual(self.total(g), tg - 90, 'escrow at the order')
        # the booking waits in the host's inbox (the market's badge) and in the Sổ phòng
        v = self.view(h)
        self.assertEqual([p['id'] for p in v['host']['pending']], [o['id']])
        with self.store.connect() as db:
            self.assertEqual(sm.alert_count(db, self.sid(h)), 1)
        self.do(h, 'confirm', order=o['id'])
        self.assertEqual(self.svc(o['id'])['status'], 'working')
        self.assertEqual(self.stay(g, o['id'])['actions'], ['arrive', 'cancel'])
        self.do(g, 'arrive', order=o['id'])
        st = self.stay(h, o['id'])
        self.assertEqual(st['stage'], 'arrived')
        self.assertIn('checkin', st['actions'])
        self.assertTrue(st['quirk']['text'] and len(st['quirk']['opts']) >= 3)
        with self.store.connect() as db:
            self.assertEqual(hs.alerts(db, self.sid(h)), 1)
        good = next(x for x in st['quirk']['opts'] if x['cost'] == 0 and x['tone'] == 'good')
        self.do(h, 'checkin', order=o['id'], room='thong', pick=good['id'])
        st = self.stay(h, o['id'])
        self.assertEqual((st['stage'], st['room']['id']), ('in', 'thong'))
        self.assertEqual(st['left'], 180 * M)
        # the night's situations come with time; one paid answer costs the host (burned)
        self.clock.t += 170 * M
        st = self.stay(h, o['id'])
        opened = [e for e in st['events'] if e['k'] == 'sys' and e['st'] == 'open']
        plan = 2 + hc.TEMPERS[self.row(o['id'])['temper']]['extra']   # one night: 2 situations, a chatty guest one more
        self.assertEqual(len(opened), plan, st['events'])
        paid = next((x for e in opened for x in e['opts'] if x['cost'] > 0), None)
        ev = next(e for e in opened if paid in e['opts']) if paid else opened[0]
        pick = paid or ev['opts'][0]
        before = self.total(h)
        self.do(h, 'handle', order=o['id'], ev=ev['key'], pick=pick['id'])
        self.assertEqual(self.total(h), before - pick['cost'])
        self.refused('stale', self.do, h, 'handle', order=o['id'], ev=ev['key'], pick=pick['id'])
        # the guest sees the host's reply, not the host's numbers
        gv = self.stay(g, o['id'])
        self.assertTrue(any(e['reply'] for e in gv['events'] if e['k'] == 'sys'))
        self.assertNotIn('temper', gv)
        # check-out (time is up): the other situation was missed
        self.clock.t += 15 * M
        st = self.stay(h, o['id'])
        self.assertIn('checkout', st['actions'])
        costs = pick['cost']
        out = self.do(h, 'checkout', order=o['id'], pick=st['out_quirk']['opts'][0]['id'])
        self.assertIn('hài lòng', out['message'])
        costs += next(x['cost'] for x in st['out_quirk']['opts'] if x['id'] == st['out_quirk']['opts'][0]['id'])
        r = self.svc(o['id'])
        self.assertEqual(r['status'], 'done')
        fee = sm.fee_of(90)
        self.assertEqual((r['fee'], r['paid']), (fee, 90 - fee))
        self.assertEqual(self.total(h), th + 90 - fee - costs)
        self.assertEqual(self.total(g), tg - 90)
        self.assertEqual((th + tg) - (self.total(h) + self.total(g)), fee + costs, 'only the fee and the host costs leave the town')
        res = self.row(o['id'])
        result = __import__('json').loads(res['result'])
        self.assertEqual(result['stay']['missed'], plan - 1)
        rest = result['rest']['guest']
        self.assertIsNotNone(rest)
        n = self.needs(g)
        self.assertEqual(n['wake'], min(100, wake0 + rest['wake']) if wake0 + rest['wake'] <= 100 else 100)
        self.assertEqual(self.spirit(g), min(100, sp0 + rest['spirit']))
        gv = self.stay(g, o['id'])
        self.assertEqual(gv['actions'], ['rate'])
        sm.post(self.store, g, None, 'rate', dict(order=o['id'], stars=gv['result']['stay']['stars']))
        self.assertEqual(self.stay(g, o['id'])['actions'], [])
        self.assertEqual(self.view(h)['card']['stays'], 1)

    def test_the_generic_done_is_refused_and_one_room_one_guest(self):
        h, g, g2 = self.host('gd_h'), self.guest('gd_g'), self.guest('gd_g2')
        self.sell(h)
        o = self.order(g, h)
        sm.post(self.store, h, None, 'take', dict(order=o['id']))
        self.refused('use_hotel_book', sm.post, self.store, h, None, 'done', dict(order=o['id']))
        self.assertEqual(self.svc(o['id'])['status'], 'working')
        # the row exists although the host took it in the market's inbox
        self.assertEqual(self.stay(g, o['id'])['stage'], 'booked')
        self.do(g, 'arrive', order=o['id'])
        q = self.stay(h, o['id'])['quirk']['opts'][0]['id']
        self.do(h, 'checkin', order=o['id'], room='suong', pick=q)
        o2 = self.order(g2, h)
        self.do(h, 'confirm', order=o2['id'])
        self.do(g2, 'arrive', order=o2['id'])
        st = self.stay(h, o2['id'])
        self.assertTrue(next(r for r in st['rooms'] if r['id'] == 'suong')['busy'])
        self.refused('room_busy', self.do, h, 'checkin', order=o2['id'], room='suong', pick=st['quirk']['opts'][0]['id'])
        # a guest holds one booking at a time
        self.refused('requirement', self.order, g, h)

    def test_guest_requests_late_checkout_and_limits(self):
        h, g = self.host('rq_h'), self.guest('rq_g')
        self.sell(h, service='stay_hours')
        o = self.to_in(h, g, service='stay_hours')
        self.refused('too_soon', self.do, g, 'leave', order=o['id'])
        st = self.stay(g, o['id'])
        self.assertIn('ask', st['actions'])
        self.do(g, 'ask', order=o['id'], ask='late')
        self.refused('already_done', self.do, g, 'ask', order=o['id'], ask='late')
        self.do(g, 'ask', order=o['id'], ask='pet')
        self.refused('ask_max', self.do, g, 'ask', order=o['id'], ask='mi')
        with self.store.connect() as db:
            self.assertEqual(hs.alerts(db, self.sid(h)), 1)
        due = self.stay(h, o['id'])['due']
        self.do(h, 'handle', order=o['id'], ev='ask:late', pick='ok')
        self.assertEqual(self.stay(h, o['id'])['due'], due + hs.LATE_MIN * M)
        self.clock.t += 61 * M
        self.assertNotIn('checkout', self.stay(h, o['id'])['actions'], 'the late hour granted')
        self.refused('too_soon', self.do, h, 'checkout', order=o['id'], pick=hc.CHECKOUT[hs._pick(o['id'], 'out', hc.CHECKOUT)]['opts'][0][0])
        # the guest leaves early: the host may check out now
        self.do(g, 'leave', order=o['id'])
        st = self.stay(h, o['id'])
        self.assertIn('checkout', st['actions'])
        self.do(h, 'checkout', order=o['id'], pick=st['out_quirk']['opts'][0]['id'])
        self.assertEqual(self.svc(o['id'])['status'], 'done')


class Refunds(HotelBase):
    def test_cancel_decline_and_no_show_refund_in_full(self):
        h, g = self.host('rf_h'), self.guest('rf_g')
        self.sell(h)
        tg, th = self.total(g), self.total(h)
        # held: the guest cancels through the market
        o = self.order(g, h)
        self.do(g, 'cancel', order=o['id'])
        self.assertEqual(self.total(g), tg)
        # booked: the guest cancels
        o = self.order(g, h)
        self.do(h, 'confirm', order=o['id'])
        self.refused('forbidden', self.do, h, 'cancel', order=o['id'])
        self.do(g, 'cancel', order=o['id'])
        self.assertEqual((self.svc(o['id'])['status'], self.total(g)), ('refunded', tg))
        # arrived: the host declines
        o = self.order(g, h)
        self.do(h, 'confirm', order=o['id'])
        self.do(g, 'arrive', order=o['id'])
        self.do(h, 'decline', order=o['id'])
        self.assertEqual((self.svc(o['id'])['status'], self.total(g)), ('refunded', tg))
        # no-show: refunded by the housekeeping after ARRIVE_HOURS
        o = self.order(g, h)
        self.do(h, 'confirm', order=o['id'])
        self.clock.t += hs.ARRIVE_HOURS * H + 1
        hs._swept[0] = 0
        hs.run_housekeeping(self.store)
        self.assertEqual((self.svc(o['id'])['status'], self.row(o['id'])['stage']), ('refunded', 'gone'))
        self.assertEqual((self.total(g), self.total(h)), (tg, th), 'nothing kept, nothing burned')
        # once in, nobody can cancel any more
        o = self.to_in(h, g)
        self.refused('stale', self.do, g, 'cancel', order=o['id'])
        self.refused('stale', self.do, h, 'decline', order=o['id'])


class System(HotelBase):
    def test_overdue_stay_is_checked_out_and_paid_while_both_are_away(self):
        h, g = self.host('sy_h'), self.guest('sy_g')
        self.sell(h, service='stay_hours')
        th = self.total(h)
        o = self.to_in(h, g, service='stay_hours')
        cost0 = th - self.total(h)
        self.clock.t += 60 * M + hs.GRACE_MIN * M + 1
        hs._swept[0] = 0
        self.assertGreaterEqual(hs.run_housekeeping(self.store), 1)
        r = self.svc(o['id'])
        self.assertEqual(r['status'], 'done')
        self.assertEqual(self.total(h), th - cost0 + 36 - sm.fee_of(36))
        res = __import__('json').loads(self.row(o['id'])['result'])
        self.assertTrue(res['stay']['auto'])
        self.assertLessEqual(res['stay']['mood'], hs.MOOD_START + 20)

    def test_checkout_exactly_once_under_concurrency(self):
        h, g = self.host('cc_h'), self.guest('cc_g')
        self.sell(h, service='stay_hours')
        o = self.to_in(h, g, service='stay_hours')
        self.clock.t += 61 * M
        st = self.stay(h, o['id'])
        pick = next(x['id'] for x in st['out_quirk']['opts'] if not x['cost'])
        th, sp = self.total(h), self.spirit(g)

        def one(i):
            try:
                if i % 2:
                    self.do(h, 'checkout', order=o['id'], pick=pick)
                else:
                    hs.sync(self.store, self.sid(g))
                    sm.settle_for(self.store, self.sid(h))
                return 'ok'
            except mr.MarriageError as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            got = list(ex.map(one, range(6)))
        self.assertIn('ok', got)
        sm.settle_for(self.store, self.sid(h))
        self.assertEqual(self.total(h), th + 36 - sm.fee_of(36))
        rest = __import__('json').loads(self.row(o['id'])['result'])['rest']['guest']
        self.assertEqual(self.spirit(g), min(100, sp + rest['spirit']))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM hotel_hosts WHERE sid=? AND stays=1', (self.sid(h),)).fetchone()['n'], 1)

    def test_rest_once_a_day_and_couples_rest_together_once(self):
        h, a, b = self.host('cp_h', 'hotel'), self.guest('cp_a'), self.guest('cp_b')
        self.sell(h, 'hotel', 'stay_couple')
        self.sell(h, 'hotel', 'stay_hours')
        self.refused('requirement', self.order, a, h, 'hotel', 'stay_couple')
        self.couple(a, b)
        sa, sb = self.spirit(a), self.spirit(b)
        o = self.to_in(h, a, 'hotel', 'stay_couple', room='p101')
        st = self.stay(b, o['id'])
        self.assertEqual(st['partner']['pid'], self.pid(b))
        self.assertIn('ask', st['actions'], 'the partner may ask too')
        self.assertNotIn('cancel', st['actions'])
        self.do(b, 'ask', order=o['id'], ask='goi')
        self.assertEqual(next(e for e in self.stay(h, o['id'])['events'] if e['k'] == 'ask')['by'], 'partner')
        stranger = self.guest('cp_x')
        self.refused('not_found', self.do, stranger, 'ask', order=o['id'], ask='mi')
        self.clock.t += 180 * M
        st = self.stay(h, o['id'])
        self.do(h, 'checkout', order=o['id'], pick=st['out_quirk']['opts'][0]['id'])
        res = __import__('json').loads(self.row(o['id'])['result'])
        self.assertIsNotNone(res['rest']['partner'])
        for _ in range(3):
            hs.settle_partner(self.store)
        self.assertEqual(self.row(o['id'])['partner_rest'], 2)
        self.assertEqual(self.spirit(a), min(100, sa + res['rest']['guest']['spirit']))
        self.assertEqual(self.spirit(b), min(100, sb + res['rest']['partner']['spirit']))
        # the same Vietnam day: a second stay completes and pays, without a second rest
        o2 = self.to_in(h, a, 'hotel', 'stay_hours', room='p205')
        self.clock.t += 61 * M
        st = self.stay(h, o2['id'])
        self.do(h, 'checkout', order=o2['id'], pick=st['out_quirk']['opts'][0]['id'])
        self.assertEqual(self.svc(o2['id'])['status'], 'done')
        res2 = __import__('json').loads(self.row(o2['id'])['result'])
        self.assertIsNone(res2['rest']['guest'])


class Switch(HotelBase):
    def test_kill_switch_stops_new_bookings_not_the_way_out(self):
        h, g, g2 = self.host('ks_h'), self.guest('ks_g'), self.guest('ks_g2')
        self.sell(h, service='stay_hours')
        o = self.to_in(h, g, service='stay_hours')
        with patch.dict(os.environ, {'MNL_HOTEL_OFF': '1'}):
            self.assertTrue(self.view(g)['off'])
            self.refused('unavailable', self.order, g2, h, service='stay_hours')   # the host's side says no first
            self.refused('cannot_provide', self.sell, h, service='stay_night')
            self.clock.t += 61 * M
            st = self.stay(h, o['id'])
            self.do(h, 'checkout', order=o['id'], pick=st['out_quirk']['opts'][0]['id'])
        self.assertEqual(self.svc(o['id'])['status'], 'done')

    def test_catalogue_is_sound(self):
        for cat in (hc.CHECKIN, hc.EVENTS, hc.ASKS, hc.CHECKOUT):
            for key, item in cat.items():
                self.assertTrue(item['text'] and item['icon'], key)
                self.assertGreaterEqual(len(item['opts']), 3, key)
                ids = [o[0] for o in item['opts']]
                self.assertEqual(len(ids), len(set(ids)), key)
                for oid, label, mood, cost, effect, reply in item['opts']:
                    self.assertTrue(label and reply, (key, oid))
                    self.assertTrue(0 <= cost <= hc.COST_MAX, (key, oid))
                    self.assertIn(effect, ('', 'late', 'upgrade'))
                self.assertTrue(any(o[2] > 0 for o in item['opts']) and any(o[2] < 0 for o in item['opts']), key)
        for career in hs.CAREERS:
            for svc in hs.SERVICES:
                self.assertIsNotNone(sm.get_spec(career, svc))
