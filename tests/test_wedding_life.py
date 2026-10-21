"""💍 Đời sống vợ chồng (game/wedding_life.py, #442 / #444): the lễ rước dâu + lễ gia tiên both partners take part in,
the trip together (escrow until both accept, refunds once, rented or own plane / yacht, the album), the daily chores,
the wedding party's guard, blocks, a divorce in the middle, and the content's photo ids."""
import json

from game import couple as cp
from game import garage
from game import marriage as mr
from game import photo_studio as ps
from game import pg_schema
from game import price_index as pi
from game import wedding_content as W
from game import wedding_life as wl
from game import wedding_life_content as C
from tests.test_couple import CoupleBase
from tests.test_marriage import Base, PLAN


class LifeBase(CoupleBase):
    def act(self, tok, op, **d):
        if isinstance(d.get('rid'), str):
            d['rid'] = d['rid'].ljust(8, '0')   # marriage._rid: 8 to 64 characters, else a fresh random one
        return super().act(tok, op, **d)

    def life(self, tok):
        return self.view(tok)['life']

    def err(self, tok, op, code, **d):
        with self.assertRaises(mr.MarriageError) as e:
            self.act(tok, op, **d)
        self.assertEqual(e.exception.code, code, e.exception.message)
        return e.exception

    def spirit(self, tok):
        return self.state(tok)['journey']['life']['spirit']

    def happy(self):
        r = self.row('SELECT happy FROM couple_stats WHERE couple=?', self.cid)
        return r['happy'] if r else 0

    def balance(self):
        with self.store.connect() as db:
            return cp._balance(db, self.cid)


class RiteTests(LifeBase):
    def run_rite(self, lead, host):
        r = self.life(lead)['rite']
        for n, st in enumerate(C.RITE_STEPS):
            who = lead if st['side'] == 'lead' else host
            other = host if who is lead else lead
            self.err(other, 'wl_rite_step', 'not_your_turn', rite=r['id'], step=n, pick=st['options'][0]['id'])
            self.act(who, 'wl_rite_step', rite=r['id'], step=n, pick=st['options'][0]['id'])
            self.assertEqual(self.act(who, 'wl_rite_step', rite=r['id'], step=n, pick=st['options'][0]['id'])['changed'], False)  # a retried tap
        return r['id']

    def test_both_take_part_and_it_is_kept(self):
        r = self.life(self.a)['rite']
        self.assertEqual((r['state'], r['fee'], r['trays_fixed']), ('none', 0, 5))   # PLAN: gia tiên and 5 trays already paid
        wallets = self.wallet(self.a), self.wallet(self.b)
        sp, hp = (self.spirit(self.a), self.spirit(self.b)), self.happy()
        self.act(self.a, 'wl_rite_start', rid='rite-0001')
        self.assertEqual(self.act(self.a, 'wl_rite_start', rid='rite-0001')['changed'], False)
        self.assertTrue(self.life(self.b)['rite']['steps'][2]['mine'])
        rid = self.run_rite(self.a, self.b)
        r = self.life(self.b)['rite']
        self.assertEqual((r['state'], r['score']), ('done', 12))
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), wallets)
        self.assertEqual(self.happy(), min(cp.HAPPY_MAX, hp + wl.RITE_HAPPY))
        self.assertEqual((self.spirit(self.a), self.spirit(self.b)), tuple(min(100, x + wl.RITE_SPIRIT) for x in sp))
        album = self.act(self.b, 'wl_album')['photos']
        self.assertEqual(len(album), 1)
        self.assertEqual(album[0]['set']['bd'], 'cuoi')
        self.assertIn(f'rite:{rid}', {r['ref'] for r in self.rows('SELECT ref FROM news')})
        self.err(self.b, 'wl_rite_start', 'done', rid='rite-0002')

    def test_paid_ceremony_refunds_once(self):
        a, b = self.user('cuc', 1000), self.user('dung', 1000)
        self.engage(a, b)
        plan = dict(PLAN, ceremonies=dict(dam_ngo=False, an_hoi=0, gia_tien=False, le_duong=False))
        self.plan_and_confirm(a, b, plan=plan)
        r = self.view(a)['life']['rite']
        self.assertEqual(r['fee'], W.CEREMONY_INDEX['gia_tien']['price'])
        self.err(a, 'wl_rite_start', 'bad_trays', rid='r-1', trays=6)
        before = self.wallet(a)
        cost = r['fee'] + dict((n, x) for n, x, _ in W.CEREMONY_INDEX['an_hoi']['options'])[7]
        self.act(a, 'wl_rite_start', rid='r-2', trays=7)
        self.act(a, 'wl_rite_start', rid='r-2', trays=7)
        self.assertEqual(self.wallet(a), before - cost)
        self.err(a, 'wl_rite_start', 'busy', rid='r-3', trays=5)
        rite = self.view(b)['life']['rite']['id']
        self.act(b, 'wl_rite_cancel', rite=rite)          # either partner may call it off
        self.err(a, 'wl_rite_cancel', 'gone', rite=rite)
        mr.settle(self.store, self.sid(a))
        self.assertEqual(self.wallet(a), before)
        self.assertEqual(len(self.rows("SELECT id FROM marriage_effects WHERE id LIKE 'wlr:rf:%'")), 1)

    def test_not_while_the_party_is_open_and_expiry(self):
        wid = self.row("SELECT id FROM weddings WHERE couple=? AND status='done'", self.cid)['id']
        self.store.transaction(lambda db: db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) VALUES(?,?,?,?,?,'booked',?) "
                                                      'ON CONFLICT(wedding) DO UPDATE SET at=excluded.at', (wid, self.cid, self.sid(self.a), self.sid(self.b),
                                                                                                           self.clock.t + 60, self.clock.t)))
        self.err(self.a, 'wl_rite_start', 'party_live', rid='live-1')
        self.clock.t += 3600
        self.act(self.a, 'wl_rite_start', rid='live-2')
        self.clock.t += wl.RITE_DAYS * mr.DAY + 1
        self.assertEqual(self.life(self.a)['rite']['state'], 'none')   # the view's housekeeping called it off
        self.assertEqual(self.row('SELECT status FROM wl_rites WHERE couple=?', self.cid)['status'], 'expired')


class TripTests(LifeBase):
    def go(self, dest='da_lat', ride='ve', pay_by='split', rid='trip-0001', **extra):
        return self.act(self.a, 'wl_trip_propose', dest=dest, ride=ride, pay_by=pay_by, rid=rid, **extra)

    def trip(self, tok=None):
        return self.life(tok or self.a)['trip']

    def test_split_both_accept_travel_and_come_home(self):
        price = pi.price(C.DESTS[0]['base'])
        wa, wb = self.wallet(self.a), self.wallet(self.b)
        self.go()
        self.go()                                           # a retried tap: held once
        self.assertEqual(self.wallet(self.a), wa - (price + 1) // 2)
        t = self.trip(self.b)
        self.assertEqual((t['status'], t['mine']), ('proposed', False))
        self.err(self.a, 'wl_trip_answer', 'gone', trip=t['id'], answer='accept')   # not the proposer
        self.act(self.b, 'wl_trip_answer', trip=t['id'], answer='accept', rid='acc-1')
        self.act(self.b, 'wl_trip_answer', trip=t['id'], answer='accept', rid='acc-2')
        self.assertEqual(self.wallet(self.b), wb - price // 2)
        hp, sp = self.happy(), (self.spirit(self.a), self.spirit(self.b))
        for n in range(3):
            t = self.trip(self.a)
            who, other = (self.a, self.b) if n % 2 == 0 else (self.b, self.a)
            self.assertEqual(self.life(who)['trip']['my_turn'], True)
            pick = t['options'][0]['id']
            self.err(other, 'wl_trip_pick', 'not_your_turn', trip=t['id'], day=n, pick=pick)
            if n:
                self.err(who, 'wl_trip_pick', 'too_soon', trip=t['id'], day=n, pick=pick)
                self.clock.t += wl.DAY_GAP
            self.act(who, 'wl_trip_pick', trip=t['id'], day=n, pick=pick)
            self.act(who, 'wl_trip_pick', trip=t['id'], day=n, pick=pick)   # replay: nothing more
        last = self.life(self.b)['last']
        self.assertEqual((last['status'], last['day'], len(last['photos'])), ('done', 3, 3))
        self.assertEqual(self.happy(), min(cp.HAPPY_MAX, hp + wl.TRIP_HAPPY['vn']))
        self.assertEqual((self.spirit(self.a), self.spirit(self.b)), tuple(min(100, x + wl.TRIP_SPIRIT) for x in sp))
        photo = last['photos'][0]
        self.assertEqual(photo['pkg'], 'doi')
        self.assertIn('mate', photo['snap'])
        self.assertTrue(self.life(self.a)['today_done'])
        self.err(self.a, 'wl_trip_propose', 'today', dest='hoi_an', ride='ve', pay_by='me', rid='trip-0002')
        self.clock.t += mr.DAY
        self.act(self.a, 'wl_trip_propose', dest='hoi_an', ride='ve', pay_by='me', rid='trip-0003')

    def test_fund_escrow_declined_refunds_once(self):
        self.fund(self.a, 20000)
        self.act(self.a, 'fund_deposit', amount=20000, rid='dep-1')
        price = pi.price(C.RENT['thue_bay']['vn'])
        self.go(dest='phu_quoc', ride='thue_bay', pay_by='fund')
        self.assertEqual(self.balance(), 20000 - price)
        t = self.trip(self.b)
        self.act(self.b, 'wl_trip_answer', trip=t['id'], answer='decline')
        self.err(self.b, 'wl_trip_answer', 'gone', trip=t['id'], answer='decline')
        self.err(self.a, 'wl_trip_cancel', 'gone', trip=t['id'])
        self.assertEqual(self.balance(), 20000)
        self.assertEqual(len(self.rows("SELECT id FROM joint_ledger WHERE kind='refund'")), 1)

    def test_cancel_and_expiry_refund_wallets(self):
        wa = self.wallet(self.a)
        self.go(pay_by='me', rid='t-1')
        t = self.trip()
        self.err(self.a, 'wl_trip_propose', 'busy', dest='hoi_an', ride='ve', pay_by='me', rid='t-2')
        self.act(self.a, 'wl_trip_cancel', trip=t['id'])
        mr.settle(self.store, self.sid(self.a))
        self.assertEqual(self.wallet(self.a), wa)
        self.go(pay_by='me', rid='t-3')
        tid = self.trip(self.b)['id']
        self.clock.t += wl.TRIP_WAIT_H * 3600 + 1
        self.err(self.b, 'wl_trip_answer', 'expired', trip=tid, answer='accept')
        self.assertIsNone(self.trip())                       # the view's housekeeping refunded it
        mr.settle(self.store, self.sid(self.a))
        self.assertEqual(self.wallet(self.a), wa)

    def test_rides_rent_and_own_vehicles(self):
        self.err(self.a, 'wl_trip_propose', 'bad_ride', dest='da_lat', ride='thue_thuyen', pay_by='me', rid='r-1')
        self.err(self.a, 'wl_trip_propose', 'not_owned', dest='ha_long', ride='nha', vehicle='du_thuyen', pay_by='me', rid='r-2')
        self.err(self.a, 'wl_trip_propose', 'no_island', dest='dao_rieng', ride='ve', pay_by='me', rid='r-3')

        def give(s):   # 🔨 the auction's numbered superyacht (garage.grant_limited) and a helicopter
            garage.grant_limited(s, 'lx_du_thuyen_01')
            V = garage.VEHICLES['truc_thang']
            garage._ensure(s)['cars']['truc_thang'] = dict(c=V['paint'], n='', d=s['journey']['life_day'], p=V['price'])
        mr._mutate(self.store, {self.sid(self.b): give})
        got = self.act(self.a, 'wl_assets')['assets']['vehicles']
        self.assertEqual({v['id'] for v in got}, {'lx_du_thuyen_01', 'truc_thang'})
        self.assertFalse(any(v['mine'] for v in got))
        self.err(self.a, 'wl_trip_propose', 'bad_ride', dest='uc', ride='nha', vehicle='truc_thang', pay_by='me', rid='r-4')
        self.err(self.a, 'wl_trip_propose', 'bad_ride', dest='da_lat', ride='nha', vehicle='lx_du_thuyen_01', pay_by='me', rid='r-5')
        wa = self.wallet(self.a)
        self.go(dest='ha_long', ride='nha', vehicle='lx_du_thuyen_01', pay_by='me', rid='r-6')
        fuel = pi.price(C.RENT['thue_thuyen']['vn']) // C.FUEL_DIV
        self.assertEqual(self.wallet(self.a), wa - fuel)
        self.assertLess(fuel, pi.price(C.RENT['thue_thuyen']['vn']))
        self.assertIn('Ngọc Trai', self.trip()['ride']['vehicle'])

    def test_blocked_and_divorce_before_leaving(self):
        self.store.transaction(lambda db: db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?,?,?)', (self.sid(self.b), self.sid(self.a), 1.0)))
        self.err(self.a, 'wl_trip_propose', 'blocked', dest='da_lat', ride='ve', pay_by='me', rid='b-1')
        self.err(self.a, 'wl_chore_start', 'blocked', kind='viec_nha', role='rua_bat')
        self.store.transaction(lambda db: db.execute('DELETE FROM marriage_blocks'))
        self.fund(self.a, 5000)
        self.act(self.a, 'fund_deposit', amount=4000, rid='dep-2')
        wb = self.wallet(self.b)
        self.go(dest='hoi_an', pay_by='fund', rid='d-1')
        self.act(self.b, 'wl_rite_start', rid='d-rite')
        self.act(self.b, 'divorce', confirm='LY HON')
        for tok in (self.a, self.b):
            mr.settle(self.store, self.sid(tok))
        # the fund (the trip's part back in it) is split 50/50: each gets 2 000
        self.assertEqual(self.wallet(self.b), wb + 2000)
        self.assertEqual(self.row('SELECT status FROM wl_trips')['status'], 'cancelled')
        self.assertEqual(self.row('SELECT status FROM wl_rites')['status'], 'cancelled')


class ChoreTests(LifeBase):
    def test_together_once_a_day(self):
        hp, sp = self.happy(), self.spirit(self.b)
        self.act(self.a, 'wl_chore_start', kind='nau_an', role='nau')
        self.err(self.a, 'wl_chore_start', 'once_a_day', kind='nau_an', role='so_che')
        self.err(self.a, 'wl_chore_join', 'not_your_turn', kind='nau_an', role='so_che')
        self.err(self.b, 'wl_chore_join', 'bad_role', kind='nau_an', role='nau')
        out = self.act(self.b, 'wl_chore_join', kind='nau_an', role='don_mam')
        self.assertIn('đứng bếp', out['message'])
        self.err(self.b, 'wl_chore_join', 'gone', kind='nau_an', role='nem')
        self.assertEqual(self.happy(), hp + wl.CHORE_POINTS)
        self.assertEqual(self.spirit(self.b), min(100, sp + wl.CHORE_SPIRIT))
        ch = {x['kind']: x for x in self.life(self.a)['chores']}
        self.assertEqual(ch['nau_an']['state'], 'done')
        self.assertTrue(ch['cham_con']['locked'])
        self.err(self.a, 'wl_chore_start', 'no_child', kind='cham_con', role='tam')
        self.clock.t += mr.DAY
        self.act(self.a, 'wl_chore_start', kind='nau_an', role='nau')


class EngagedTests(Base):
    def test_engaged_couple_may_hold_the_rite_but_not_travel(self):
        a, b = self.user('em', 1000), self.user('anh', 1000)
        self.engage(a, b)
        self.assertIsNone(self.view(a)['life']['rite'])        # no confirmed plan yet
        self.plan_and_confirm(a, b)
        life = self.view(b)['life']
        self.assertEqual((life['rite']['state'], life['married']), ('none', False))
        with self.assertRaises(mr.MarriageError) as e:
            mr.act(self.store, a, 'wl_trip_propose', dict(dest='da_lat', ride='ve', pay_by='me', rid='x-1'))
        self.assertEqual(e.exception.code, 'not_married')
        mr.act(self.store, b, 'wl_rite_start', dict(rid='e-1'))
        self.assertEqual(self.view(a)['life']['rite']['lead']['me'], False)


class ContentTests(Base):
    def test_photo_ids_and_tables(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 83)
        for name in ('wl_rites', 'wl_trips', 'wl_photos', 'wl_chores'):
            self.assertIn(name, pg_schema.TABLE)
        self.assertEqual(set(C.ACTIVITIES), {d['id'] for d in C.DESTS})
        for dest, acts in C.ACTIVITIES.items():
            self.assertEqual(len(acts), 6, dest)
            for x in acts:
                self.assertIn(x['bd'], ps.BACKDROPS, x)
                self.assertIn(x['light'], ps.LIGHTS, x)
                self.assertIn(x['pose'], ps.GROUP_POSES, x)
                self.assertIn(x['face'], ps.FACES, x)
                self.assertIn(x['prop'], ps.PROPS, x)
        for st in C.RITE_STEPS:
            self.assertEqual(len(st['options']), 3)
            self.assertEqual(max(o['pts'] for o in st['options']), 2)
        self.assertEqual(sum(max(o['pts'] for o in s['options']) for s in C.RITE_STEPS), 12)
        for d in wl.catalog()['dests']:
            self.assertGreater(d['prices']['ve'], 0)
            self.assertGreater(d['prices']['thue_bay'], d['prices']['ve'])
            self.assertLess(d['fuel']['plane'], d['prices']['thue_bay'])
