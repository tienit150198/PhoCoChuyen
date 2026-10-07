"""Hôn nhân (game/marriage.py): rings, proposals, the planner, the wedding day, news and divorce."""
import http.client, json, os, random, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, social
from game import marriage as mr
from game import wedding_content as W
from game.engine import new_state, validate_state, migrate_state, GameError
from game.storage import Store

DAY = 86400
PLAN = dict(venue='restaurant', tables=20, menu='tieu_chuan', ceremonies=dict(dam_ngo=True, an_hoi=5, gia_tien=True, le_duong=False),
            extras=['dress', 'makeup', 'mc', 'cards'], days=3)


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        self.clock = Clock()
        p = patch('game.marriage.now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        # scrypt is slow on purpose; not what these tests are about
        h = patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        h.start()
        self.addCleanup(h.stop)
        self.n = 0

    def user(self, name, wallet=2000):
        token, _, _ = self.store.session()
        out = accounts.register(self.store, token, dict(username=name + '_test', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name.title()))
        tok = out['token']
        self.fund(tok, wallet)
        return tok

    def sid(self, tok):
        return self.store.key(tok)

    def fund(self, tok, wallet):
        mr._mutate(self.store, {self.sid(tok): lambda s: s['journey'].__setitem__('wallet', wallet)})

    def state(self, tok):
        return self.store.read(tok)[0]

    def wallet(self, tok):
        return self.state(tok)['journey']['wallet']

    auto_friends = True   # proposals need a friendship: the older tests befriend quietly (tests/test_couple.py tests the real flow)

    def befriend(self, a_sid, b_sid):
        def run(db):
            for x, y in ((a_sid, b_sid), (b_sid, a_sid)):
                db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?) ON CONFLICT DO NOTHING', (x, y, mr.now()))
        self.store.transaction(run)

    def act(self, tok, op, **d):
        if op == 'propose' and self.auto_friends and isinstance(d.get('code'), str):
            with self.store.connect() as db:
                t = db.execute('SELECT sid FROM marriage_people WHERE code=?', (d['code'],)).fetchone()
            if t:
                self.befriend(self.sid(tok), t['sid'])
        return mr.act(self.store, tok, op, d)

    def view(self, tok, catalog=False):
        return mr.view(self.store, tok, self.state(tok), catalog)

    def code(self, tok):
        return self.view(tok)['me']['code']

    def ring(self, tok, tier='bac'):
        self.act(tok, 'ring_buy', tier=tier)
        return [r for r in self.view(tok)['rings'] if r['status'] == 'owned'][-1]['id']

    def engage(self, a, b, announce=True):
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem', announce=announce)
        pid = self.view(b)['incoming'][0]['id']
        self.act(b, 'respond', id=pid, answer='accept', announce=announce)
        return rid

    def plan_and_confirm(self, a, b, plan=PLAN, mine=50, announce_a=True, announce_b=True):
        self.act(a, 'plan', plan=plan, mine=mine, announce=announce_a)
        w = self.view(b)['wedding']
        self.act(b, 'confirm', id=w['id'], version=w['version'], announce=announce_b)
        return w['id']

    def row(self, sql, *args):
        with self.store.connect() as db:
            r = db.execute(sql, args).fetchone()
            return dict(r) if r else None

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]


class RingAndProposalTests(Base):
    def test_ring_purchase_charges_wallet_once(self):
        a = self.user('an', wallet=200)
        self.act(a, 'ring_buy', tier='vang_tay', rid='ring-request-01')
        self.act(a, 'ring_buy', tier='vang_tay', rid='ring-request-01')   # a retried request
        self.assertEqual(self.wallet(a), 35)                               # 💹 07/10: 150 -> 165 xu
        rings = self.view(a)['rings']
        self.assertEqual([(r['tier'], r['status']) for r in rings], [('vang_tay', 'owned')])
        hist = self.state(a)['journey']['history'][-1]
        self.assertEqual((hist['kind'], hist['amount']), ('life', -165))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'ring_buy', tier='kim_cuong')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(self.wallet(a), 35)                               # 💹 07/10: 150 -> 165 xu
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'ring_buy', tier='nhua')

    def test_guest_cannot_marry(self):
        guest, _, _ = self.store.session()
        b = self.user('binh')
        v = mr.view(self.store, guest, self.store.read(guest)[0])
        self.assertTrue(v['guest'])
        self.assertNotIn('me', v)
        for op, d in (('ring_buy', dict(tier='bac')), ('propose', dict(code=self.code(b), ring='x', message='hem'))):
            with self.assertRaises(mr.MarriageError) as e:
                mr.act(self.store, guest, op, d)
            self.assertEqual(e.exception.code, 'account_required')

    def test_codes_are_unique_and_hide_accounts(self):
        a, b = self.user('an'), self.user('binh')
        ca, cb = self.code(a), self.code(b)
        self.assertRegex(ca, r'^PCC-[2-9A-HJKMNP-Z]{6}$')
        self.assertNotEqual(ca, cb)
        self.assertEqual(mr.clean_code(' pcc ' + cb[4:].lower()), cb)
        found = self.act(a, 'lookup', code=cb)['found']
        self.assertEqual((found['name'], found['can']), ('Binh', False))   # not friends yet
        self.befriend(self.sid(a), self.sid(b))
        found = self.act(a, 'lookup', code=cb)['found']
        self.assertEqual((found['name'], found['can']), ('Binh', True))
        text = json.dumps(self.view(b)) + json.dumps(found)
        for secret in (self.sid(a), self.sid(b), 'binh"', a, b):
            self.assertNotIn(secret, text)

    def test_propose_accept(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='tra')
        vb = self.view(b)
        self.assertEqual(len(vb['incoming']), 1)
        self.assertEqual(vb['incoming'][0]['name'], 'An')
        self.assertIn('ly trà', vb['incoming'][0]['message'])
        self.assertIn('cầu hôn', vb['me']['notice'])
        self.assertEqual(mr.alerts(self.store, self.sid(b))['alerts'], 2)  # proposal + notice
        self.act(b, 'respond', id=vb['incoming'][0]['id'], answer='accept')
        for tok, other in ((a, 'Binh'), (b, 'An')):
            m = self.state(tok)['marriage']
            self.assertEqual((m['spouse']['name'], m['spouse']['status']), (other, 'engaged'))
            self.assertEqual(self.view(tok)['couple']['status'], 'engaged')
            validate_state(self.state(tok)); mr.validate_save(self.state(tok))
        self.assertEqual(self.row('SELECT status FROM marriage_rings WHERE id=?', rid)['status'], 'given')
        self.assertEqual(self.row("SELECT COUNT(*) n FROM news WHERE kind='engaged'")['n'], 1)

    def test_decline_keeps_ring_and_cools_down(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.act(b, 'respond', id=self.view(b)['incoming'][0]['id'], answer='decline')
        self.assertEqual(self.view(a)['rings'][0]['status'], 'owned')       # no refund, the ring is still his
        self.assertEqual(self.wallet(a), 2000 - 55)
        self.assertIsNone(self.view(a)['couple'])
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.assertIn('từ chối', e.exception.message)
        self.clock.t += W.DECLINE_HOURS * 3600 + 60
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.assertEqual(len(self.view(b)['incoming']), 1)

    def test_cancel_returns_ring(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.assertEqual(self.view(a)['rings'][0]['status'], 'proposed')
        with self.assertRaises(mr.MarriageError):       # one ring, one proposal at a time
            self.act(a, 'propose', code=self.code(self.user('cuc')), ring=rid, message='hem')
        pid = self.view(a)['outgoing'][0]['id']
        with self.assertRaises(mr.MarriageError):       # only the proposer cancels
            self.act(b, 'cancel', id=pid)
        self.act(a, 'cancel', id=pid)
        self.assertEqual(self.view(a)['rings'][0]['status'], 'owned')
        self.assertEqual(self.view(b)['incoming'], [])
        with self.assertRaises(mr.MarriageError):
            self.act(b, 'respond', id=pid, answer='accept')

    def test_block_and_unblock(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.act(b, 'block', id=self.view(b)['incoming'][0]['id'])
        self.assertEqual(self.view(b)['incoming'], [])
        self.assertEqual(self.view(a)['rings'][0]['status'], 'owned')
        found = self.act(a, 'lookup', code=self.code(b))['found']
        self.assertFalse(found['can'])
        self.assertIsNone(found['name'])
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.assertEqual(self.view(b)['blocks'][0]['name'], 'An')
        self.act(b, 'unblock', code=self.code(a))
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')

    def test_settings_stop_proposals(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(b, 'settings', accept=False)
        self.assertFalse(self.view(b)['me']['accept'])
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.assertIn('tắt', e.exception.message)
        self.act(b, 'settings', accept=True)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')

    def test_rate_limit_three_a_day(self):
        a = self.user('an')
        others = [self.user(n) for n in ('binh', 'cuc', 'dung', 'em')]
        rings = [self.ring(a) for _ in range(4)]
        for tok, rid in zip(others[:3], rings):
            self.act(a, 'propose', code=self.code(tok), ring=rid, message='hem')
        self.assertEqual(self.view(a)['me']['proposals_left'], 0)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'propose', code=self.code(others[3]), ring=rings[3], message='hem')
        self.assertIn('Mỗi ngày', e.exception.message)
        self.clock.t += DAY + 1
        self.act(a, 'propose', code=self.code(others[3]), ring=rings[3], message='hem')

    def test_preset_messages_only(self):
        a, b = self.user('an'), self.user('binh')
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'propose', code=self.code(b), ring=self.ring(a), message='<b>free text</b>')

    def test_one_spouse_only(self):
        a, b, c = self.user('an'), self.user('binh'), self.user('cuc')
        r1, r2 = self.ring(a), self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=r1, message='hem')
        self.act(a, 'propose', code=self.code(c), ring=r2, message='hem')
        self.act(b, 'respond', id=self.view(b)['incoming'][0]['id'], answer='accept')
        # the other pending proposal ends and its ring goes back to the box
        self.assertEqual(self.view(c)['incoming'], [])
        self.assertEqual(self.row('SELECT status FROM marriage_rings WHERE id=?', r2)['status'], 'owned')
        for who, target in ((c, a), (c, b), (a, c)):
            rid = self.ring(who)
            with self.assertRaises(mr.MarriageError):
                self.act(who, 'propose', code=self.code(target), ring=rid, message='hem')

    def test_two_acceptances_at_once(self):
        """B and C both accept A's proposals "at the same moment": the bond PK lets one win."""
        a, b, c = self.user('an'), self.user('binh'), self.user('cuc')
        r1, r2 = self.ring(a), self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=r1, message='hem')
        self.act(a, 'propose', code=self.code(c), ring=r2, message='hem')
        pc = self.view(c)['incoming'][0]['id']
        self.act(b, 'respond', id=self.view(b)['incoming'][0]['id'], answer='accept')
        # C's accept raced past the cancellation: put the proposal back to pending to force the PK path
        self.store.transaction(lambda db: db.execute("UPDATE proposals SET status='pending' WHERE id=?", (pc,)))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(c, 'respond', id=pc, answer='accept')
        self.assertEqual(e.exception.code, 'taken')
        self.assertIsNone(self.view(c)['couple'])
        self.assertEqual(self.row("SELECT COUNT(*) n FROM couples")['n'], 1)

    def test_proposal_expires_after_a_week(self):
        a, b = self.user('an'), self.user('binh')
        rid = self.ring(a)
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        self.clock.t += W.PROPOSAL_DAYS * DAY + 1
        self.assertEqual(self.view(b)['incoming'], [])
        self.assertEqual(self.view(a)['rings'][0]['status'], 'owned')


class PlannerMathTests(unittest.TestCase):
    def test_costs_deposit_and_balance(self):
        q = mr.costs(mr.clean_plan(PLAN))
        sub = {s['id']: s['subtotal'] for s in q['sections']}
        self.assertEqual(sub, dict(venue=220, reception=20 * 44, ceremony=22 + 66 + 33, extras=66 + 28 + 33 + 0))   # 💹 07/10: +10 %   # thiệp cưới miễn phí (01/10)
        self.assertEqual(q['total'], 1348)
        self.assertEqual(q['deposit'], 405)                 # 30 % rounded up
        self.assertEqual(q['balance'], 1348 - 405)
        self.assertEqual(q['seats'], 200)

    def test_menu_price_depends_on_venue(self):
        self.assertEqual(mr.table_price('home', 'tieu_chuan'), 37)
        self.assertEqual(mr.table_price('restaurant', 'tieu_chuan'), 44)
        self.assertEqual(mr.table_price('center', 'sang_trong'), 101)

    def test_plan_is_validated(self):
        for bad in (dict(PLAN, venue='castle'), dict(PLAN, tables=4), dict(PLAN, venue='home', tables=31), dict(PLAN, tables=20.5),
                    dict(PLAN, menu='buffet'), dict(PLAN, ceremonies=dict(an_hoi=6)), dict(PLAN, ceremonies=dict(gia_tien=1)),
                    dict(PLAN, extras=['mc', 'mc']), dict(PLAN, extras=['fireworks']), dict(PLAN, days=1), dict(PLAN, days=11), 'x'):
            with self.assertRaises(mr.MarriageError):
                mr.clean_plan(bad)
        self.assertEqual(mr.clean_plan(dict(venue='home', tables=5, menu='binh_dan'))['ceremonies'],
                         dict(dam_ngo=False, an_hoi=0, gia_tien=False, le_duong=False))

    def test_split(self):
        for amount in (0, 1, 99, 101, 1285):
            for pct in (0, 30, 50, 67, 100):
                a, b = mr._split(amount, pct)
                self.assertEqual(a + b, amount)
                self.assertGreaterEqual(min(a, b), 0)
        self.assertEqual(mr._split(101, 50), (51, 50))
        self.assertEqual(mr._split(1000, 70), (700, 300))
        q = mr.quote(PLAN, None, 70)
        self.assertEqual(q['shares']['a']['deposit'] + q['shares']['b']['deposit'], q['deposit'])
        self.assertEqual(q['shares']['a']['balance'] + q['shares']['b']['balance'], q['balance'])

    def test_forecast_band_is_sane(self):
        q = mr.quote(PLAN)
        lo, hi = q['forecast']['gifts']
        self.assertLess(lo, hi)
        self.assertLessEqual(q['forecast']['guests'][1], 200)
        self.assertEqual(q['profit'], [lo - q['total'], hi - q['total']])


class GiftRollTests(unittest.TestCase):
    def pool(self):
        s = migrate_state(new_state(), owned=True)
        return mr.pool_of(s)

    def test_roll_is_seeded(self):
        pool = self.pool()
        a = mr.roll('wedding|1|1|5', PLAN, pool, ('An', 'Binh'))
        self.assertEqual(a, mr.roll('wedding|1|1|5', PLAN, pool, ('An', 'Binh')))
        self.assertNotEqual(a, mr.roll('wedding|2|1|5', PLAN, pool, ('An', 'Binh')))

    def test_distribution_ranges(self):
        pool = self.pool()
        seen, gifts = set(), []
        for i in range(300):
            r = mr.roll(f'seed{i}', PLAN, pool, ('An', 'Binh'))
            self.assertLessEqual(r['guests'], r['seats'])
            self.assertEqual(r['guests'] + r['empty'], r['seats'])
            self.assertGreater(r['guests'], 60)
            per = (r['gifts']) / max(1, r['guests'])
            self.assertTrue(2 <= per <= 20, per)            # 200k–2tr per guest at a restaurant
            for h in r['highlights']:
                seen.add(h['kind'])
                self.assertTrue(0 <= h['amount'] <= 120)
            self.assertEqual(r['late_total'], sum(x['amount'] for x in r['late']))
            for c in r['close']:
                self.assertGreaterEqual(c['tier'], mr.CARD_TIER)

            gifts.append(r['gifts'] + r['late_total'])
        self.assertTrue({'rich', 'joke', 'forgot'} <= seen)
        rich = sum(1 for i in range(300) if any(h['kind'] == 'rich' for h in mr.roll(f'seed{i}', PLAN, pool)['highlights']))
        self.assertTrue(30 <= rich <= 100, rich)              # "a rare rich uncle": about one in five
        mean = sum(gifts) / len(gifts)
        exp = mr.forecast(mr.clean_plan(PLAN), pool)['expected_gifts']
        self.assertLess(abs(mean - exp) / exp, .2, (mean, exp))

    def test_close_neighbours_come_more_and_give_more(self):
        s = migrate_state(new_state(), owned=True)
        s['journey']['life']['bonds']['ba_tam'] = 95
        s['journey']['life']['bonds']['chu_tu'] = 5
        pool = mr.pool_of(s)
        came = dict(ba_tam=0, chu_tu=0)
        amount = dict(ba_tam=[], chu_tu=[])
        for i in range(200):
            r = mr.roll(f'c{i}', PLAN, pool)
            names = {c['name'] for c in r['close']}
            if 'Bà Tám' in names:
                came['ba_tam'] += 1
        g = {x['id']: x for x in pool['named']}
        self.assertEqual(g['ba_tam']['tier'], 5)
        self.assertEqual(g['chu_tu']['tier'], 1)
        self.assertGreater(came['ba_tam'], 170)              # Như người nhà almost always comes
        o = mr._odds(mr.clean_plan(PLAN), pool)
        self.assertGreater(o['p_named'](g['ba_tam']), o['p_named'](g['chu_tu']) + 40)
        self.assertGreater(mr._shift_mean(W.TIER_GIFTS[5], 0), 3 * mr._shift_mean(W.TIER_GIFTS[1], 0))

    def test_forgetful_guest_is_not_a_named_guest_who_came(self):
        pool = dict(named=[dict(id=w, name=w, emoji='🙂', tier=5, close=95) for w in ('anh_khoa', 'chu_tu', 'co_hai_loa')], circle=200, street=50)
        with patch('game.marriage._p_named', lambda g, bonus: 100.0):
            for i in range(60):
                r = mr.roll(f'f{i}', PLAN, pool)
                self.assertEqual(r['late'], [])
                self.assertEqual(len(r['close']), 3)

    def test_closeness_helper_falls_back(self):
        s = migrate_state(new_state(), owned=True)
        s['journey']['life']['bonds']['co_ba'] = 72
        with patch('game.marriage._cl', lambda: None):
            self.assertEqual(mr.neighbour(s, 'co_ba'), dict(close=72, tier=4, attend=None))
            self.assertEqual(mr.neighbour(s, 'nobody'), dict(close=0, tier=1, attend=None))
        self.assertEqual(mr.closeness_of(s, 'co_ba'), 72)

    def test_merge_pools_takes_the_higher_closeness(self):
        pa = dict(named=[dict(id='ba_tam', close=40, tier=3)], circle=100, street=60)
        pb = dict(named=[dict(id='ba_tam', close=90, tier=5), dict(id='be_ti', close=30, tier=2)], circle=80, street=40)
        m = mr._merge_pools(pa, pb)
        self.assertEqual([(g['id'], g['close']) for g in m['named']], [('ba_tam', 90), ('be_ti', 30)])
        self.assertEqual((m['circle'], m['street']), (180, 50))


class WeddingTests(Base):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.user('an', 1500), self.user('binh', 1500)
        self.engage(self.a, self.b)

    def due(self, wid):
        self.store.transaction(lambda db: db.execute('UPDATE weddings SET due_at=? WHERE id=?', (self.clock.t - 1, wid)))

    def test_plan_needs_both_to_confirm(self):
        wa, wb = self.wallet(self.a), self.wallet(self.b)
        self.act(self.a, 'plan', plan=PLAN, mine=60)
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (wa, wb))   # nothing taken yet
        w = self.view(self.b)['wedding']
        self.assertEqual((w['status'], w['mine'], w['split_mine']), ('proposed', False, 40))
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'confirm', id=w['id'], version=w['version'])       # the planner cannot confirm alone
        self.act(self.a, 'plan', plan=dict(PLAN, tables=25), mine=60)           # edited meanwhile
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.b, 'confirm', id=w['id'], version=w['version'])
        self.assertEqual(e.exception.code, 'plan_changed')
        w = self.view(self.b)['wedding']
        self.act(self.b, 'confirm', id=w['id'], version=w['version'])
        dep = w['quote']['deposit']
        a_dep, b_dep = mr._split(dep, 60)
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (wa - a_dep, wb - b_dep))
        self.assertEqual(self.view(self.a)['wedding']['status'], 'confirmed')
        self.assertEqual(self.view(self.a)['wedding']['left'], 3)
        with self.assertRaises(mr.MarriageError):                               # locked after confirmation
            self.act(self.a, 'plan', plan=PLAN)

    def test_reject_and_withdraw(self):
        self.act(self.a, 'plan', plan=PLAN)
        w = self.view(self.b)['wedding']
        self.act(self.b, 'reject', id=w['id'])
        self.assertEqual(self.view(self.a)['wedding']['status'], 'rejected')
        self.act(self.b, 'plan', plan=dict(PLAN, tables=10))                    # the other spouse proposes a new version
        w = self.view(self.a)['wedding']
        self.assertEqual((w['status'], w['mine'], w['plan']['tables']), ('proposed', False, 10))
        self.act(self.b, 'withdraw')
        self.assertIsNone(self.view(self.a)['wedding'])

    def test_confirm_needs_both_deposits(self):
        self.fund(self.b, 10)
        self.act(self.a, 'plan', plan=PLAN)
        w = self.view(self.b)['wedding']
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.b, 'confirm', id=w['id'], version=w['version'])
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (1500 - 55, 10))
        self.assertEqual(self.view(self.a)['wedding']['status'], 'proposed')

    def test_resolution_idempotent_from_either_save(self):
        wid = self.plan_and_confirm(self.a, self.b, mine=50)
        before = (self.wallet(self.a), self.wallet(self.b))
        self.assertFalse(mr.on_load(self.store, self.a, self.state(self.a)))     # not yet
        self.due(wid)
        self.assertTrue(mr.on_load(self.store, self.b, self.state(self.b)))      # B's save triggers it
        for _ in range(3):
            mr.on_load(self.store, self.a, self.state(self.a))
            mr.on_load(self.store, self.b, self.state(self.b))
        self.assertFalse(mr.resolve(self.store, self.view(self.a)['couple']['id'], wid))
        w = self.row('SELECT * FROM weddings WHERE id=?', wid)
        res = json.loads(w['result'])
        sa, sb = res['shares']['a'], res['shares']['b']
        # the late envelope arrives half a day later
        self.assertEqual(self.wallet(self.a), before[0] + sa['gift'] - sa['balance'])
        self.assertEqual(self.wallet(self.b), before[1] + sb['gift'] - sb['balance'])
        self.clock.t += 13 * 3600
        for tok in (self.a, self.b, self.a):
            mr.on_load(self.store, tok, self.state(tok))
        self.assertEqual(self.wallet(self.a), before[0] + sa['gift'] - sa['balance'] + sa['late'])
        self.assertEqual(self.wallet(self.b), before[1] + sb['gift'] - sb['balance'] + sb['late'])
        self.assertEqual(sa['gift'] + sb['gift'], res['gifts'])
        self.assertEqual(sa['balance'] + sb['balance'], res['balance'])
        self.assertEqual(self.row("SELECT COUNT(*) n FROM marriage_effects WHERE status='pending'")['n'], 0)
        for tok, other in ((self.a, 'Binh'), (self.b, 'An')):
            s = self.state(tok)
            validate_state(s); mr.validate_save(s)
            self.assertEqual((s['marriage']['spouse']['status'], s['marriage']['spouse']['name']), ('married', other))
            self.assertTrue(s['marriage']['sticker'])
            self.assertEqual(s['marriage']['weddings'], 1)
            self.assertEqual(self.view(tok)['couple']['status'], 'married')

    def test_resolution_on_life_day(self):
        wid = self.plan_and_confirm(self.a, self.b)
        target = self.row('SELECT target_a FROM weddings WHERE id=?', wid)['target_a']
        mr._mutate(self.store, {self.sid(self.a): lambda s: s['journey'].__setitem__('life_day', target)})
        self.assertTrue(mr.on_load(self.store, self.a, self.state(self.a)))
        self.assertEqual(self.row('SELECT status FROM weddings WHERE id=?', wid)['status'], 'done')
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertEqual(self.state(self.b)['marriage']['spouse']['status'], 'married')

    def test_profit_and_result_card(self):
        wid = self.plan_and_confirm(self.a, self.b)
        self.due(wid)
        mr.on_load(self.store, self.a, self.state(self.a))
        v = self.view(self.a)['wedding']
        r = v['result']
        self.assertEqual(r['profit'], r['gifts'] + r['late_total'] - r['total'])
        self.assertEqual(r['total'], 1348)
        self.assertEqual(r['names'], dict(a='An', b='Binh'))
        self.assertTrue(r['speeches'] and r['speeches'][0].startswith('MC'))      # an MC was hired
        self.assertIn('close', r)
        self.assertEqual(r['guests'] + r['empty'], 200)
        sa, sb = r['shares']['a'], r['shares']['b']
        self.assertEqual(sa['net'] + sb['net'], r['profit'])
        self.assertFalse(v['seen'])
        self.act(self.a, 'seen', wedding=v['id'])
        self.assertTrue(self.view(self.a)['wedding']['seen'])

    def test_low_wallet_on_the_day_goes_into_debt(self):
        wid = self.plan_and_confirm(self.a, self.b, plan=dict(PLAN, venue='center', tables=40, menu='sang_trong'))
        self.fund(self.a, 0)
        self.due(wid)
        mr.on_load(self.store, self.a, self.state(self.a))
        res = json.loads(self.row('SELECT result FROM weddings WHERE id=?', wid)['result'])
        expected = res['shares']['a']['gift'] - res['shares']['a']['balance']
        self.assertEqual(self.wallet(self.a), expected)
        if expected < 0:
            self.assertTrue(self.state(self.a)['journey']['in_debt'])

    def test_news_once_escaped_and_opt_out(self):
        wid = self.plan_and_confirm(self.a, self.b)
        self.due(wid)
        mr.on_load(self.store, self.a, self.state(self.a))
        mr.on_load(self.store, self.b, self.state(self.b))
        mr.resolve(self.store, self.view(self.a)['couple']['id'], wid)
        rows = self.rows("SELECT * FROM news WHERE kind='wedding'")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['text'], '💍 An & Binh vừa tổ chức đám cưới 20 bàn tại Nhà hàng Hoa Sen!')
        out = mr.news(self.store, 0)
        self.assertNotIn('a', out['items'][0])
        self.assertNotIn(self.sid(self.a), json.dumps(out))
        self.assertEqual(mr._clean_name('<img src=x onerror=1>&"`'), 'img src=x onerror=1')

    def test_news_respects_opt_out(self):
        wid = self.plan_and_confirm(self.a, self.b, announce_b=False)
        self.due(wid)
        mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(self.row('SELECT status FROM weddings WHERE id=?', wid)['status'], 'done')
        self.assertEqual(self.rows("SELECT * FROM news WHERE kind='wedding'"), [])

    def test_divorce_cancels_pending_wedding_and_cools_down(self):
        wid = self.plan_and_confirm(self.a, self.b)
        wallet = self.wallet(self.a)
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'divorce', confirm='ok')
        self.act(self.a, 'divorce', confirm='huy')             # engaged: "hủy hôn ước"
        self.due(wid)
        self.assertFalse(mr.on_load(self.store, self.b, self.state(self.b)))
        self.assertEqual(self.row('SELECT status FROM weddings WHERE id=?', wid)['status'], 'cancelled')
        self.assertEqual(self.wallet(self.a), wallet)        # the deposit is not refunded
        for tok in (self.a, self.b):
            self.assertIsNone(self.state(tok)['marriage']['spouse'])
            self.assertIsNone(self.view(tok)['couple'])
        rid = self.ring(self.b)
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'propose', code=self.code(self.a), ring=rid, message='hem')
        self.clock.t += W.REMARRY_HOURS * 3600 + 1
        self.act(self.b, 'propose', code=self.code(self.a), ring=rid, message='hem')

    def test_divorce_after_wedding(self):
        wid = self.plan_and_confirm(self.a, self.b)
        self.due(wid)
        mr.on_load(self.store, self.a, self.state(self.a))
        mr.on_load(self.store, self.b, self.state(self.b))
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'divorce', confirm='HUY')
        self.act(self.b, 'divorce', confirm='ly hon')
        for tok in (self.a, self.b):
            m = self.state(tok)['marriage']
            self.assertEqual((m['spouse'], m['sticker'], m['weddings']), (None, False, 1))
            self.assertGreater(self.view(tok)['me']['cooldown'], 0)
        self.assertIn('ly hôn', self.view(self.a)['me']['notice'])
        self.assertEqual(self.view(self.a)['last']['status'], 'divorced')

    def test_account_delete_frees_the_partner(self):
        mr.forget(self.store, self.a)
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertIsNone(self.state(self.b)['marriage']['spouse'])
        self.assertIsNone(self.view(self.b)['couple'])
        self.assertEqual(self.rows('SELECT * FROM news WHERE a=? OR b=?', self.sid(self.a), self.sid(self.a)), [])


class NewsTests(Base):
    def test_since_paging(self):
        a, b, c, d = (self.user(n) for n in ('an', 'binh', 'cuc', 'dung'))
        self.assertEqual(mr.news(self.store, 0)['items'], [])
        self.engage(a, b)
        first = mr.news(self.store, 0)
        self.assertEqual(len(first['items']), 1)
        last = first['last']
        self.assertEqual(mr.news(self.store, last)['items'], [])
        self.engage(c, d)
        nxt = mr.news(self.store, last)
        self.assertEqual([i['text'] for i in nxt['items']], ['💞 Cuc & Dung vừa đính hôn. Cả phố chờ ăn cưới!'])
        self.assertEqual(mr.news(self.store, 'junk')['last'], nxt['last'])
        self.assertEqual(len(mr.news(self.store, 10 ** 9)['items']), 2)          # a database that started over
        self.clock.t += 3 * DAY
        self.assertEqual(mr.news(self.store, 0)['items'], [])                     # old news is not replayed

    def test_alerts_for_signed_in_players(self):
        a, b = self.user('an'), self.user('binh')
        self.act(a, 'propose', code=self.code(b), ring=self.ring(a), message='hem')
        out = mr.news(self.store, 0, b)
        self.assertGreaterEqual(out['me']['alerts'], 1)
        guest, _, _ = self.store.session()
        self.assertIsNone(mr.news(self.store, 0, guest)['me'])


class SaveTests(unittest.TestCase):
    def test_old_saves_load_and_validate(self):
        s = migrate_state(new_state(), owned=True)
        self.assertNotIn('marriage', s)
        validate_state(s); mr.validate_save(s)

    def test_validate_new_fields(self):
        s = migrate_state(new_state(), owned=True)
        s['marriage'] = mr.blank()
        mr.validate_save(s)
        mr._apply_effect(s, dict(id='eng:1:a', kind='status', amount=0, label='', data=json.dumps(dict(set='engaged', name='Binh'))))
        mr._apply_effect(s, dict(id='wed:1:a', kind='status', amount=0, label='', data=json.dumps(dict(set='married', name='Binh', date='2026-09-29'))))
        self.assertFalse(mr._apply_effect(s, dict(id='wed:1:a', kind='status', amount=0, label='', data='{}')))
        mr.validate_save(s); validate_state(s)
        self.assertEqual(s['marriage']['weddings'], 1)
        for bad in (dict(s['marriage'], extra=1), dict(s['marriage'], sticker='yes'), dict(s['marriage'], applied=['x' * 99]),
                    dict(s['marriage'], spouse=dict(s['marriage']['spouse'], status='single')),
                    dict(s['marriage'], spouse=dict(s['marriage']['spouse'], date='hôm qua'))):
            with self.assertRaises(GameError):
                mr.validate_save(dict(s, marriage=bad))
        broken = dict(s, marriage='?')
        self.assertEqual(mr._box(broken), mr.blank())       # a hand-edited backup is repaired, not fatal

    def test_applied_ids_are_capped(self):
        s = migrate_state(new_state(), owned=True)
        for i in range(mr.APPLIED_KEPT + 20):
            mr._apply_effect(s, dict(id=f'gift:{i}:a', kind='wallet', amount=1, label='x', data='{}'))
        self.assertEqual(len(s['marriage']['applied']), mr.APPLIED_KEPT)
        validate_state(s); mr.validate_save(s)


class MarriageHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server import GameServer
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db', story=True))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup(); cls.quiet.stop()

    def req(self, dev, path, method='GET', body=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        if body is not None: h['Content-Type'] = 'application/json'; body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = json.loads(res.read() or b'{}'); hdrs = dict(res.getheaders()); con.close()
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return res.status, data

    def test_routes(self):
        self.server.limits.clear()
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap')[0], 200)
        status, data = self.req(dev, '/api/news?since=0')
        self.assertEqual((status, data['items'], data['me']), (200, [], None))
        status, data = self.req(dev, '/api/marriage?catalog=1')
        self.assertEqual(status, 200)
        self.assertTrue(data['guest'])
        self.assertEqual(len(data['catalog']['rings']), 5)
        status, data = self.req(dev, '/api/marriage/ring_buy', 'POST', dict(tier='bac'))
        self.assertEqual((status, data['code']), (403, 'account_required'))
        with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
            status, data = self.req(dev, '/api/account/register', 'POST', dict(username='http_an', password='matkhau-dai-lam', confirm='matkhau-dai-lam', display='An'))
        self.assertEqual(status, 200, data)
        status, data = self.req(dev, '/api/marriage/ring_buy', 'POST', dict(tier='bac'))
        self.assertEqual(status, 200, data)
        self.assertEqual(data['state']['journey']['wallet'], 5)
        self.assertEqual(data['view']['rings'][0]['tier'], 'bac')
        self.assertIn('marriage', data['state'])
        status, data = self.req(dev, '/api/marriage/ring_buy', 'POST', dict(tier='bac'))
        self.assertEqual((status, data['code']), (400, 'not_enough'))
        status, data = self.req(dev, '/api/marriage/nope', 'POST', {})
        self.assertEqual(status, 404)
        status, data = self.req(dev, '/api/marriage/quote', 'POST', dict(plan=PLAN, mine=50))
        self.assertEqual((status, data['quote']['total']), (200, 1348))
        status, data = self.req(dev, '/api/news?since=0')
        self.assertEqual(data['me']['alerts'], 0)


if __name__ == '__main__':
    unittest.main()
