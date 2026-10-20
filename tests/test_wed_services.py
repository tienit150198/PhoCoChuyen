"""💒 Dịch vụ cưới từ người chơi (game/wed_services.py, owner 21/10 "làm hết đi"): an engaged couple hires other players
(banquet, florist, clothing, salon) through Phố dịch vụ at ×3 the NPC price, the money held once; the provider's job
(brief, craft, three oái ăm demands, the last check) graded once per step; the delivery refused until the job is done,
then paid 95 % with 5 % burned (money conserved); the team shown on the Hôn nhân card, the invite card and the wedding
day (a good service counts as its NPC extra); a couple who hires nobody gets exactly the NPC wedding; the kill switch.
Real PostgreSQL transactions (TEST_DATABASE_URL)."""
import json
import os
import time
from unittest.mock import patch

from game import marriage as mr
from game import service_market as sm
from game import wed_services as ws
from game import wed_services_content as C
from game import wedding_content as W
from tests.test_marriage import Base, PLAN

FLORIST, BANQUET = 'florist', 'banquet'


def career(*ids):
    def fn(s):
        for cid in ids:
            s['careers'][cid]['started'] = True
    return fn


class WedBase(Base):
    def setUp(self):
        super().setUp()
        self.clock.t = time.time()        # the market's clock is the real one: keep marriage's next to it
        sm._swept[0] = 0.0
        ws._cache.clear()
        self.a, self.b = self.user('an', 5000), self.user('binh', 5000)
        self.engage(self.a, self.b)
        self.wid = self.plan_and_confirm(self.a, self.b, plan=dict(PLAN, extras=['mc', 'cards']))
        self.hoa = self.user('hoa', 100)
        self.bep = self.user('bep', 100)
        mr._mutate(self.store, {self.sid(self.hoa): career(FLORIST, 'clothing', 'salon'), self.sid(self.bep): career(BANQUET)})
        self.k = 0

    # ------------------------------------------------------------ helpers
    def rid(self):
        self.k += 1
        return f'wedsvc-test-{self.k:06d}'

    def pid(self, tok):
        from game import social
        return social.pid_of(self.sid(tok))

    def wpost(self, tok, op, **d):
        return ws.post(self.store, tok, None, op, d)

    def wget(self, tok, sub):
        return ws.get(self.store, tok, None, sub, {})

    def spost(self, tok, sub, **d):
        return sm.post(self.store, tok, None, sub, d)

    def sell(self, tok, svc, on=True):
        return self.wpost(tok, 'sell', svc=svc, on=on)

    def hire(self, buyer, seller, svc='hoa', brief=None, qty=1, **kw):
        brief = brief or dict(hoa=dict(mau='hong', loai='tulip'), tiec=dict(menu='tieu_chuan', mon='ga'),
                              vay=dict(kieu='xoe', vest='den'), makeup=dict(style='trong', toc='bui'))[svc]
        return self.wpost(buyer, 'hire', svc=svc, pid=self.pid(seller), brief=brief, qty=qty, rid=self.rid(), **kw)['order']

    def job(self, oid):
        with self.store.connect() as db:
            r = db.execute('SELECT * FROM wedsvc_jobs WHERE order_id=?', (oid,)).fetchone()
            return dict(r) if r else None

    def order(self, oid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM svc_orders WHERE id=?', (oid,)).fetchone())

    def total(self, tok):
        from game import bank
        s = self.state(tok)
        b = bank.get(s)
        return s['journey']['wallet'] + (b['balance'] if b else 0)

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message

    def work(self, seller, oid, agree=True, wrong=False):
        """Answer every step: the right craft picks, the best demand ('a'), agreeing (or not) to the change."""
        while True:
            j = self.job(oid)
            plan, answers = json.loads(j['plan']), json.loads(j['answers'])
            if len(answers) == len(plan):
                return j
            st = plan[len(answers)]
            brief = json.loads(j['brief'])
            if st['k'] == 'd':
                pick = 'a' if (agree or not st.get('change')) else 'b'
            else:
                pick = ws._right(j['svc'], st, brief)
                if wrong and st['k'] in ('b1', 'b2'):
                    pick = next(o for o in st['o'] if o != pick)
            self.wpost(seller, 'step', order=oid, at=len(answers), pick=pick)

    def resolve(self):
        self.store.transaction(lambda db: db.execute('UPDATE weddings SET due_at=? WHERE id=?', (self.clock.t - 1, self.wid)))
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
        return self.row('SELECT * FROM weddings WHERE id=?', self.wid)


class Hiring(WedBase):
    def test_hire_holds_x3_npc_price_once_with_the_brief(self):
        self.sell(self.hoa, 'hoa')
        v = self.wget(self.a, 'couple')
        hoa = next(s for s in v['services'] if s['key'] == 'hoa')
        self.assertEqual(hoa['npc'], W.EXTRA_INDEX['flowers']['price'])
        self.assertEqual([(p['pid'], p['price']) for p in hoa['providers']], [(self.pid(self.hoa), hoa['npc'] * 3)])
        before = self.total(self.a)
        body = dict(svc='hoa', pid=self.pid(self.hoa), brief=dict(mau='tim', loai='ly'), rid='wedsvc-same-rid-01', expected_price=hoa['npc'] * 3)
        o = self.wpost(self.a, 'hire', **body)['order']
        again = self.wpost(self.a, 'hire', **body)['order']    # a retried request: the same order, paid once
        self.assertEqual(o['id'], again['id'])
        self.assertEqual(self.total(self.a), before - hoa['npc'] * 3)
        self.assertEqual((o['status'], o['price']), ('held', hoa['npc'] * 3))
        j = self.job(o['id'])
        self.assertEqual(json.loads(j['brief']), dict(mau='tim', loai='ly'))
        self.assertEqual(j['status'], 'work')
        self.assertIn('Tím mộng mơ', self.order(o['id'])['data'])
        self.assertEqual(len(json.loads(j['plan'])), 7)
        # both spouses see the order; the card shows it in preparation
        self.assertEqual([x['state'] for x in self.wget(self.b, 'couple')['credits']], ['prep'])
        self.refused('quote_changed', self.wpost, self.a, 'hire', svc='hoa', pid=self.pid(self.hoa), brief=dict(mau='tim', loai='ly'),
                     rid=self.rid(), expected_price=1)
        self.refused('bad_brief', self.wpost, self.a, 'hire', svc='hoa', pid=self.pid(self.hoa), brief=dict(mau='xanh_la'), rid=self.rid())

    def test_only_a_couple_with_a_wedding_to_come_may_order(self):
        self.sell(self.hoa, 'hoa')
        lone = self.user('lan', 5000)
        self.refused('requirement', self.hire, lone, self.hoa)
        self.assertIn('đính hôn', self.wget(lone, 'couple')['why'])
        self.refused('cannot_provide', self.sell, self.a, 'hoa')   # not a florist

    def test_kill_switch_stops_orders_steps_and_deliveries_not_the_npc_wedding(self):
        self.sell(self.hoa, 'hoa')
        o = self.hire(self.a, self.hoa)
        self.spost(self.hoa, 'take', order=o['id'])
        with patch.dict(os.environ, {'MNL_WEDSVC_OFF': '1'}):
            self.refused('wedsvc_off', self.hire, self.a, self.hoa)
            self.refused('wedsvc_off', self.wpost, self.hoa, 'step', order=o['id'], at=0, pick='hong')
            self.refused('wedsvc_off', self.wpost, self.hoa, 'deliver', order=o['id'])
            self.refused('wedsvc_off', self.spost, self.hoa, 'done', order=o['id'])
            self.assertTrue(self.wget(self.a, 'couple')['off'])
            w = self.resolve()
        self.assertEqual(w['status'], 'done')
        self.assertNotIn('services', json.loads(w['result']))

    def test_decline_refunds_in_full(self):
        self.sell(self.hoa, 'hoa')
        before = self.total(self.a)
        o = self.hire(self.a, self.hoa)
        self.spost(self.hoa, 'decline', order=o['id'])
        self.assertEqual(self.total(self.a), before)
        self.assertEqual(self.order(o['id'])['status'], 'refunded')
        self.assertEqual(self.wget(self.a, 'couple')['credits'], [])


class Work(WedBase):
    def test_the_job_is_graded_once_and_delivery_waits_for_it_then_pays_95(self):
        self.sell(self.hoa, 'hoa')
        price = ws.npc_price('hoa') * 3
        o = self.hire(self.a, self.hoa)
        self.refused('not_working', self.wpost, self.hoa, 'step', order=o['id'], at=0, pick='hong')   # take it first
        self.spost(self.hoa, 'take', order=o['id'])
        self.refused('wedsvc_unfinished', self.wpost, self.hoa, 'deliver', order=o['id'])
        self.refused('wedsvc_unfinished', self.spost, self.hoa, 'done', order=o['id'])   # Phố dịch vụ's own button too
        self.refused('not_found', self.wpost, self.bep, 'step', order=o['id'], at=0, pick='hong')
        j = self.job(o['id'])
        first = json.loads(j['plan'])[0]
        r = self.wpost(self.hoa, 'step', order=o['id'], at=0, pick=ws._right('hoa', first, json.loads(j['brief'])))
        self.assertEqual(r['job']['steps'][0]['pts'], 2)
        self.wpost(self.hoa, 'step', order=o['id'], at=0, pick=next(x for x in first['o'] if x != 'hong'))   # a retried tap
        self.assertEqual(len(json.loads(self.job(o['id'])['answers'])), 1, 'answered once')
        self.refused('bad_step', self.wpost, self.hoa, 'step', order=o['id'], at=1, pick='zz')
        j = self.work(self.hoa, o['id'])
        self.assertEqual((j['status'], j['score'], j['stars']), ('ready', C.MAX_SCORE, 5))
        view = self.wget(self.hoa, 'work')['orders'][0]['job']
        self.assertTrue(view['done'])
        self.assertEqual(len(view['steps']), 7)
        self.assertEqual(sum(1 for s in view['steps'] if s['k'] == 'd'), 3)
        a0, h0 = self.total(self.a), self.total(self.hoa)
        out = self.wpost(self.hoa, 'deliver', order=o['id'])
        self.assertEqual(out['order']['status'], 'done')
        fee = sm.fee_of(price)
        self.assertEqual(self.total(self.hoa), h0 + price - fee)
        self.assertEqual(self.total(self.a), a0)
        self.wpost(self.hoa, 'deliver', order=o['id'])    # again: nothing more
        self.assertEqual(self.total(self.hoa), h0 + price - fee)
        self.assertEqual(self.job(o['id'])['status'], 'delivered')
        res = self.order(o['id'])
        self.assertEqual((res['fee'], res['paid']), (fee, price - fee))
        self.assertEqual(json.loads(res['data'])['result']['stars'], 5)

    def test_the_last_minute_change_moves_the_last_check(self):
        self.sell(self.hoa, 'hoa')
        for agree in (True, False):
            o = self.hire(self.a, self.hoa)
            self.spost(self.hoa, 'take', order=o['id'])
            plan = json.loads(self.job(o['id'])['plan'])
            ch = next(s for s in plan if s.get('change'))
            j = self.work(self.hoa, o['id'], agree=agree)
            self.assertEqual(json.loads(j['brief'])['mau'], ch['new'] if agree else 'hong')
            self.assertEqual(j['stars'], C.stars_of(C.MAX_SCORE if agree else C.MAX_SCORE - 1))
            view = ws.job_view(j)
            final = view['steps'][-1]
            self.assertEqual(final['pts'], 2, 'the last check follows the brief as it is now')
            q = next(s for s in view['steps'] if s['k'] == 'd' and ('đổi ý' in s['q']))
            self.assertIn(C.opt_name('hoa', 'mau', ch['new']).lower(), q['q'])

    def test_sloppy_work_gives_fewer_stars(self):
        self.sell(self.hoa, 'vay')
        o = self.hire(self.a, self.hoa, 'vay')
        self.spost(self.hoa, 'take', order=o['id'])
        j = self.work(self.hoa, o['id'], wrong=True)
        self.assertEqual(j['score'], C.MAX_SCORE - 4)
        self.assertEqual(j['stars'], C.stars_of(C.MAX_SCORE - 4))
        self.assertLess(j['stars'], 5)

    def test_banquet_extra_tables_and_an_order_from_the_directory(self):
        self.sell(self.bep, 'tiec')
        o = self.hire(self.a, self.bep, 'tiec', qty=12)
        self.assertEqual(o['price'], ws.npc_price('tiec') * 3 * 12)
        self.spost(self.bep, 'take', order=o['id'])
        plan = json.loads(self.job(o['id'])['plan'])
        n = next(s for s in plan if s.get('change'))['n']
        j = self.work(self.bep, o['id'])
        self.assertEqual(json.loads(j['brief'])['tables'], 12 + n)
        self.assertEqual(j['stars'], 5)
        # an order placed in the generic directory (no brief): its job is made with a rolled brief on first sight
        d = self.spost(self.b, 'order', pid=self.pid(self.bep), career=BANQUET, service='tiec_cuoi', qty=5, rid=self.rid())['order']
        self.assertIsNone(self.job(d['id']))
        work = self.wget(self.bep, 'work')
        row = next(x for x in work['orders'] if x['id'] == d['id'])
        self.assertEqual(row['status'], 'held')
        b = json.loads(self.job(d['id'])['brief'])
        self.assertIn(b['menu'], [m['id'] for m in W.MENUS])
        self.assertEqual(b['tables'], 5)

    def test_a_negotiated_order_keeps_its_brief(self):
        self.wpost(self.hoa, 'sell', svc='makeup', on=True)
        self.spost(self.hoa, 'settings', career='salon', service='trang_diem_cuoi', on=True, mode='nego', mult=3)
        npc = ws.npc_price('makeup')
        o = self.wpost(self.a, 'hire', svc='makeup', pid=self.pid(self.hoa), brief=dict(style='han', toc='xoan'), price=npc * 2, rid=self.rid())['order']
        self.assertEqual(o['status'], 'talk')
        self.assertEqual(json.loads(self.job(o['id'])['brief']), dict(style='han', toc='xoan'))
        before = self.total(self.a)
        self.spost(self.hoa, 'answer', order=o['id'], op='accept')
        self.assertEqual(self.order(o['id'])['status'], 'working')
        self.assertEqual(self.total(self.a), before - npc * 2)


class Shown(WedBase):
    def deliver_all(self):
        self.sell(self.hoa, 'hoa')
        self.sell(self.bep, 'tiec')
        oh = self.hire(self.a, self.hoa)
        ot = self.hire(self.b, self.bep, 'tiec', qty=20)
        for tok, o in ((self.hoa, oh), (self.bep, ot)):
            self.spost(tok, 'take', order=o['id'])
            self.work(tok, o['id'])
            self.wpost(tok, 'deliver', order=o['id'])
        return oh, ot

    def test_the_team_on_the_cards_and_the_wedding_day(self):
        self.deliver_all()
        card = self.view(self.a)['couple']['wedsvc']
        self.assertEqual([(x['key'], x['state'], x['stars']) for x in card], [('tiec', 'done', 5), ('hoa', 'done', 5)])
        self.assertEqual(card[1]['line'], 'Hoa do Hoa cắm')
        self.assertEqual(card[0]['line'], 'Tiệc do Bep phục vụ')
        with self.store.connect() as db:
            team = ws.invite_svc(db, self.view(self.a)['couple']['id'])
        self.assertEqual([x['name'] for x in team], ['Bep', 'Hoa'])
        plan = json.loads(self.row('SELECT plan FROM weddings WHERE id=?', self.wid)['plan'])
        w = self.resolve()
        res = json.loads(w['result'])
        self.assertEqual([x['line'] for x in res['services']], ['Tiệc do Bep phục vụ', 'Hoa do Hoa cắm'])
        played = dict(plan, extras=plan['extras'] + ['flowers'], menu='sang_trong')
        self.assertEqual(res['mood'], mr.mood_of(mr.mood_points(mr.clean_plan(played))), 'the florist counts as the flowers extra')
        self.assertEqual(res['menu'], W.MENU_INDEX[plan['menu']]['name'], 'the card keeps the planned menu')
        q = json.loads(w['quote'])
        self.assertEqual(res['total'], q['total'], 'costs never change')

    def test_no_player_service_leaves_the_npc_wedding_exactly_as_before(self):
        plan = json.loads(self.row('SELECT plan FROM weddings WHERE id=?', self.wid)['plan'])
        c = self.row('SELECT * FROM couples WHERE id=(SELECT couple FROM weddings WHERE id=?)', self.wid)
        with self.store.connect() as db:
            played, cr = ws.roll_plan(db, c, plan)
        self.assertIs(played, plan)
        self.assertEqual(cr, [])
        w = self.resolve()
        res = json.loads(w['result'])
        self.assertNotIn('services', res)
        seed = f'wedding|{w["id"]}|{c["id"]}|{int(c["since"])}'
        pools = [mr.pool_of(self.state(t)) for t in (self.a, self.b)]
        names = (mr._clean_name('An'), mr._clean_name('Binh'))
        again = mr.roll(seed, plan, mr._merge_pools(*pools), names)
        self.assertEqual((again['guests'], again['gifts'], again['mood']), (res['guests'], res['gifts'], res['mood']))

    def test_credits_cache_is_bounded(self):
        self.deliver_all()
        with patch.object(ws, 'CACHE_MAX', 3):
            with self.store.connect() as db:
                for i in range(10):
                    ws.credits_cached(db, dict(id=10_000 + i, a='x', b='y', since=0))
        self.assertLessEqual(len(ws._cache), 3)

    def test_credits_from_rows_and_the_photographer(self):
        rows = [dict(career='florist', service='hoa_cuoi', provider='p', status='working', qty=1, created_at=2, pname='Mai',
                     stars=None, brief='{"mau":"do","loai":"hong"}', jst='work', jc=None),
                dict(career='florist', service='hoa_cuoi', provider='q', status='done', qty=1, created_at=1, pname='<Lan>',
                     stars=4, brief='{"mau":"tim","loai":"ly"}', jst='delivered', jc=7),
                dict(career='salon', service='trang_diem_cuoi', provider='r', status='held', qty=1, created_at=1, pname='Thu',
                     stars=None, brief=None, jst=None, jc=8)]
        out = C.credits_from_rows(rows, [dict(shooter_name='Tách', status='shoot', at=1), dict(shooter_name='Tí', status='done', at=0)], 7)
        self.assertEqual([(x['key'], x['name'], x['state'], x['stars']) for x in out], [('hoa', 'Lan', 'done', 4), ('anh', 'Tí', 'done', 0)])
        self.assertEqual(out[0]['color'], 'tim')


class Live(WedBase):
    def test_the_live_party_and_the_invite_card_import_the_credits(self):
        import importlib
        lw = importlib.import_module('live.wedding')
        self.assertTrue(hasattr(lw.WS, 'CREDITS_SQL'))
        with self.store.connect() as db:   # the query the live service runs, on this schema
            rows = db.execute(C.CREDITS_SQL, ('a', 'b', 0)).fetchall()
            photos = db.execute(C.PHOTO_SQL, ('a', 'b', 0)).fetchall()
        self.assertEqual((list(rows), list(photos)), ([], []))
