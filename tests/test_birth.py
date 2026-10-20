"""🏥 Phòng sinh & nhận nuôi (game/birth.py, owner 21/10 "sinh con … phải mất tiền ra, đặt tiền tối thiểu và không được
ít hơn mức đó"): a new shared child is booked and paid, both spouses agree first, a refund before check-in, exactly one
birth when both tap, the floors, the adoption fee, the nurse, the provider's escrow, and the old children untouched.
Real PostgreSQL transactions (TEST_DATABASE_URL)."""
import json
import shutil
import subprocess
import threading
import unittest
from pathlib import Path

from game import birth as bt
from game import career_scale as scale
from game import career_scale_resources as resources
from game import employment
from game import family
from game import marriage as mr
from game.engine import validate_state
from tests.test_couple import CoupleBase

H = 3600


def homestay_owner(s):
    c = s['careers']['homestay']
    c.update(started=True, open=True)
    r = scale.ensure(c, 'homestay')
    r['tier'] = 1
    r['today']['requires_contract'] = True
    resources.ensure(c, 'homestay')


def nurse(s):
    c = s['careers']['nurse']
    c['started'] = True
    if employment.required('nurse'):
        c['job'] = employment.hired_record('nurse')


class BirthBase(CoupleBase):
    def setUp(self):
        super().setUp()
        for token in (self.a, self.b):
            mr._mutate(self.store, {self.sid(token): lambda s: s['journey'].__setitem__('life_day', 12)})
            self.fund(token, 1_000_000)
        self.n = 0

    def rid(self):
        self.n += 1
        return f'birth-test-{self.n:04d}'

    def do(self, tok, op, **d):
        d.setdefault('rid', self.rid())
        return self.act(tok, op, **d)

    def fam(self, tok):
        return self.view(tok)['family']

    def bt(self, tok):
        return self.fam(tok)['birth']

    def stay(self, tok):
        return self.bt(tok)['stay']

    def account(self, tok, balance):
        def fn(s):
            from game import bank
            from game.engine import apply_action
            if not bank.get(s):
                s2, _ = apply_action(s, None, 'jr_bk_open', {})
                s.clear()
                s.update(s2)
            bank.get(s)['balance'] = balance
        mr._mutate(self.store, {self.sid(tok): fn})

    def balance(self, tok):
        from game import bank
        b = bank.get(self.state(tok))
        return b['balance'] if b else 0

    def book(self, tok=None, kind='birth', where='npc', price=None, payer='me', name='Bông', nurse_ok=True):
        tok = tok or self.a
        if price is None:
            price = bt.ADOPT_FEE if kind == 'adopt' else bt.NPC_PRICE
        d = dict(kind=kind, name=name, price=price, payer=payer, nurse=nurse_ok)
        d['where'] = 'agency' if kind == 'adopt' else where
        return self.do(tok, 'family_birth_book', **d)

    def accept(self, tok=None):
        tok = tok or self.b
        return self.do(tok, 'family_birth_answer', id=self.stay(tok)['id'], answer='accept')

    def effects(self, sid, prefix='birth:'):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,amount,status FROM marriage_effects WHERE sid=? AND id LIKE ? ORDER BY id',
                                                (sid, prefix + '%')).fetchall()]

    def children(self):
        with self.store.connect() as db:
            return [json.loads(r['state']) for r in db.execute('SELECT state FROM family_children WHERE couple=?', (self.cid,)).fetchall()]


class Booking(BirthBase):
    def test_npc_birth_pays_once_after_both_agree_and_is_born_after_the_stay(self):
        before_a, before_b = self.wallet(self.a), self.wallet(self.b)
        self.book()
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (before_a, before_b), 'nothing charged on a proposal')
        s = self.stay(self.b)
        self.assertEqual((s['status'], s['can_answer'], s['payer'], s['price']), ('proposed', True, 'partner', bt.NPC_PRICE))
        with self.assertRaises(mr.MarriageError) as e:   # the proposer cannot agree in the other's place
            self.do(self.a, 'family_birth_answer', id=s['id'], answer='accept')
        self.assertEqual(e.exception.code, 'forbidden')
        self.accept()
        self.assertEqual(self.wallet(self.a), before_a - bt.NPC_PRICE, 'the payer the proposer chose pays, once')
        self.assertEqual(self.wallet(self.b), before_b)
        self.assertEqual(self.stay(self.a)['status'], 'booked')
        self.do(self.b, 'family_birth_checkin', id=s['id'])
        s = self.stay(self.a)
        self.assertEqual((s['status'], s['left'], s['due'], s['can_cancel']), ('staying', bt.STAY_HOURS * H, False, False))
        with self.assertRaises(mr.MarriageError) as e:
            self.do(self.a, 'family_birth_done', id=s['id'])
        self.assertEqual(e.exception.code, 'waiting')
        with self.assertRaises(mr.MarriageError):
            self.do(self.a, 'family_birth_cancel', id=s['id'])
        self.assertIsNone(self.fam(self.a)['child'])
        self.clock.t += bt.STAY_HOURS * H
        out = self.do(self.a, 'family_birth_done', id=s['id'])
        self.assertIn('chào đời', out['message'])
        child = self.fam(self.b)['child']
        self.assertEqual((child['name'], child['origin'], child['waiting'], child['needs']['food'], child['bond']), ('Bông', 'birth', False, 65, 0))
        self.assertEqual(child['birth']['where'], bt.NPC['name'])
        self.assertIsNone(self.stay(self.a))
        self.assertEqual(self.wallet(self.a), before_a - bt.NPC_PRICE, 'the NPC hospital is a pure sink: no refund, no credit')
        self.assertEqual(self.effects(self.sid(self.a)) + self.effects(self.sid(self.b)), [])
        self.do(self.b, 'family_child_care', child='shared', act='wash')   # the new child is an ordinary shared child
        self.assertEqual(self.fam(self.a)['child']['care_days'], 1)
        for tok in (self.a, self.b):
            validate_state(self.state(tok))

    def test_wallet_then_account_never_card_never_debt(self):
        self.fund(self.a, 300_000)
        self.account(self.a, 600_000)
        self.book()
        self.accept()
        self.assertEqual((self.wallet(self.a), self.balance(self.a)), (0, 100_000))
        hist = self.state(self.a)['journey']['history']
        self.assertEqual(hist[-1]['amount'], -300_000)
        self.assertTrue(all(abs(r['amount']) <= bt.ROW_MAX for r in hist))
        sid = self.stay(self.a)['id']
        self.do(self.a, 'family_birth_cancel', id=sid)   # refunded to where it came from
        self.assertEqual((self.wallet(self.a), self.balance(self.a)), (300_000, 600_000))
        validate_state(self.state(self.a))

    def test_payer_short_of_money_cannot_accept_and_nothing_moves(self):
        self.fund(self.b, 10)
        self.book(payer='partner')
        before = (self.wallet(self.a), self.wallet(self.b))
        with self.assertRaises(mr.MarriageError) as e:
            self.accept()
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), before)
        self.assertEqual(self.stay(self.a)['status'], 'proposed', 'the proposal waits; the proposer may cancel')
        self.do(self.a, 'family_birth_cancel', id=self.stay(self.a)['id'])
        self.assertIsNone(self.stay(self.a))
        self.fund(self.a, -5)
        with self.assertRaises(mr.MarriageError) as e:   # a wallet in debt never pays from the account to dig deeper
            self.book()
        self.assertEqual(e.exception.code, 'not_enough')

    def test_decline_and_cancel_before_the_stay_refund_everything(self):
        self.book()
        self.do(self.b, 'family_birth_answer', id=self.stay(self.b)['id'], answer='decline')
        self.assertIsNone(self.stay(self.a))
        before = self.wallet(self.b)
        self.book(self.b)
        self.accept(self.a)
        self.assertEqual(self.wallet(self.b), before - bt.NPC_PRICE)
        sid = self.stay(self.a)['id']
        for _ in range(2):   # either spouse may cancel a booking; a retry replays the receipt (refund once)
            self.act(self.a, 'family_birth_cancel', id=sid, rid='cancel-once-001')
        self.assertEqual(self.wallet(self.b), before)
        with self.assertRaises(mr.MarriageError):
            self.do(self.b, 'family_birth_cancel', id=sid)
        self.assertEqual(self.wallet(self.b), before)

    def test_floors_and_the_seen_price(self):
        for price in (bt.NPC_PRICE - 1, 1, 0, bt.FLOOR, '800000', 799_999.5):
            with self.subTest(price=price), self.assertRaises(mr.MarriageError) as e:
                self.book(price=price)
            self.assertIn(e.exception.code, ('price_changed',))
        with self.assertRaises(mr.MarriageError):
            self.book(kind='adopt', price=bt.ADOPT_FEE - 1)
        self.assertIsNone(self.stay(self.a))
        cuc = self.user('cuc', 1000)
        with self.assertRaises(mr.MarriageError) as e:   # not a homestay owner
            self.do(cuc, 'family_room_set', name='Phòng Mây', price=bt.FLOOR)
        self.assertEqual(e.exception.code, 'not_provider')
        mr._mutate(self.store, {self.sid(cuc): homestay_owner})
        for price, code in ((bt.FLOOR - 1, 'below_floor'), (0, 'below_floor'), (-5, 'below_floor'), (499_999.9, 'below_floor'),
                            ('600000', 'below_floor'), (True, 'below_floor'), (bt.ROOM_MAX + 1, 'above_max')):
            with self.subTest(price=price), self.assertRaises(mr.MarriageError) as e:
                self.do(cuc, 'family_room_set', name='Phòng Mây', price=price)
            self.assertEqual(e.exception.code, code)
        self.do(cuc, 'family_room_set', name='Phòng Mây', price=bt.FLOOR)
        room = self.bt(self.a)['rooms'][0]
        self.assertEqual((room['price'], room['name'], room['owner']), (bt.FLOOR, 'Phòng Mây', 'Cuc'))
        with self.assertRaises(mr.MarriageError) as e:   # paying less than the room's price
            self.book(where=room['id'], price=bt.FLOOR - 100_000)
        self.assertEqual(e.exception.code, 'price_changed')
        with self.store.connect() as db:   # a row below the floor (a bug, a manual edit) is never bookable
            db.execute('UPDATE birth_rooms SET price=? WHERE id=?', (100, room['id']))
        with self.assertRaises(mr.MarriageError):
            self.book(where=room['id'], price=100)
        self.assertIsNone(self.stay(self.a))

    def test_one_open_booking_and_no_second_child(self):
        self.book()
        with self.assertRaises(mr.MarriageError) as e:
            self.book(self.b)
        self.assertEqual(e.exception.code, 'pending')
        self.accept()
        self.do(self.a, 'family_birth_checkin', id=self.stay(self.a)['id'])
        self.clock.t += bt.STAY_HOURS * H + 1
        self.fam(self.a)                      # the sheet's poll finishes it (settle_due)
        self.assertEqual(len(self.children()), 1)
        with self.assertRaises(mr.MarriageError) as e:
            self.book(kind='adopt')
        self.assertEqual(e.exception.code, 'already_owned')

    def test_single_player_cannot_book(self):
        solo = self.user('chi', 2_000_000)
        mr._mutate(self.store, {self.sid(solo): lambda s: s['journey'].__setitem__('life_day', 12)})
        with self.assertRaises(mr.MarriageError) as e:
            self.do(solo, 'family_birth_book', kind='adopt', where='agency', name='Na', price=bt.ADOPT_FEE, payer='me')
        self.assertEqual(e.exception.code, 'not_married')

    def test_both_need_life_day_ten(self):
        mr._mutate(self.store, {self.sid(self.b): lambda s: s['journey'].__setitem__('life_day', 4)})
        with self.assertRaises(mr.MarriageError) as e:
            self.book()
        self.assertEqual(e.exception.code, 'locked')


class Adoption(BirthBase):
    def test_adoption_fee_then_the_baby_comes_home_at_once(self):
        before = self.wallet(self.b)
        self.book(kind='adopt', payer='partner', name='Na')
        self.assertIsNone(self.fam(self.a)['child'])
        self.accept()
        self.assertEqual(self.wallet(self.b), before - bt.ADOPT_FEE)
        child = self.fam(self.a)['child']
        self.assertEqual((child['name'], child['origin'], child['waiting']), ('Na', 'adopt', False))
        self.assertEqual(child['birth']['where'], bt.AGENCY['name'])
        self.assertIsNone(self.stay(self.a))
        validate_state(self.state(self.b))

    def test_personal_child_pays_the_fee_and_an_old_client_is_told_the_price(self):
        from game.engine import apply_action, GameError
        from tests.test_bank import story
        s = story(bt.ADOPT_FEE - 1)
        s['journey']['life_day'] = 12
        with self.assertRaises(GameError) as e:   # 2.4.66's client sends no fee: refused, nothing charged
            apply_action(s, None, 'jr_hh_adopt', dict(kind='child', name='Bông', confirm=True))
        self.assertEqual(e.exception.code, 'fee_changed')
        self.assertIn('300.000', e.exception.message)
        with self.assertRaises(GameError) as e:
            apply_action(s, None, 'jr_hh_adopt', dict(kind='child', name='Bông', confirm=True, fee=bt.ADOPT_FEE, pay='card'))
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertNotIn('household', s['journey'])
        s['journey']['wallet'] += 1
        s2, out = apply_action(s, None, 'jr_hh_adopt', dict(kind='child', name='Bông', confirm=True, fee=bt.ADOPT_FEE))
        self.assertEqual(s2['journey']['wallet'], 0)
        self.assertIn('household', s2['journey'])
        validate_state(s2)
        from game import household as hh
        self.assertEqual(next(x for x in hh.public(s)['adopt'] if x['id'] == 'child')['cost'], bt.ADOPT_FEE)


class Concurrency(BirthBase):
    def test_both_spouses_and_the_poll_tapping_together_give_one_baby_one_credit(self):
        cuc = self.user('cuc', 1000)
        mr._mutate(self.store, {self.sid(cuc): homestay_owner})
        self.do(cuc, 'family_room_set', name='Phòng Hoa Sữa', price=1_000_000)
        room = self.bt(self.a)['rooms'][0]
        self.fund(self.a, 2_000_000)
        self.book(where=room['id'], price=1_000_000)
        self.accept()
        sid = self.stay(self.a)['id']
        self.do(self.a, 'family_birth_checkin', id=sid)
        self.clock.t += bt.STAY_HOURS * H
        errors, outs = [], []
        barrier = threading.Barrier(4)

        def tap(tok, n):
            try:
                barrier.wait(5)
                if n == 3:
                    outs.append(bt.settle_due(self.store, self.sid(tok)))
                else:
                    outs.append(family.act(self.store, self.sid(tok), 'family_birth_done', dict(id=sid, rid=f'race-done-{n:03d}'))['message'])
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))
        workers = [threading.Thread(target=tap, args=(t, i)) for i, t in enumerate((self.a, self.b, self.a, self.b))]
        for w in workers: w.start()
        for w in workers: w.join(20)
        self.assertEqual(errors, [])
        self.assertEqual(len(self.children()), 1)
        credit = self.effects(self.sid(cuc))
        self.assertEqual([e['amount'] for e in credit], [950_000], 'price − 5 % burned, once')
        with self.store.connect() as db:
            r = db.execute('SELECT status,burn FROM birth_stays WHERE id=?', (sid,)).fetchone()
        self.assertEqual((r['status'], r['burn']), ('born', 50_000))
        before = self.wallet(cuc)
        mr.on_load(self.store, cuc, self.state(cuc))
        mr.on_load(self.store, cuc, self.state(cuc))
        self.assertEqual(self.wallet(cuc), before + 950_000)
        validate_state(self.state(cuc))
        self.assertEqual(self.bt(cuc)['my_room']['room']['born'], 1)

    def test_two_answers_at_once_charge_once(self):
        self.book()
        sid = self.stay(self.b)['id']
        before = self.wallet(self.a)
        errors = []

        def answer(n):
            try:
                family.act(self.store, self.sid(self.b), 'family_birth_answer', dict(id=sid, answer='accept', rid=f'race-ans-{n:03d}'))
            except mr.MarriageError as e:
                errors.append(e.code)
        workers = [threading.Thread(target=answer, args=(i,)) for i in range(3)]
        for w in workers: w.start()
        for w in workers: w.join(20)
        self.assertEqual(sorted(errors), ['stale', 'stale'])
        self.assertEqual(self.wallet(self.a), before - bt.NPC_PRICE)


class Providers(BirthBase):
    def setUp(self):
        super().setUp()
        self.cuc = self.user('cuc', 1000)
        mr._mutate(self.store, {self.sid(self.cuc): homestay_owner})
        self.do(self.cuc, 'family_room_set', name='Phòng Đồi Thông', price=600_000)
        self.room = self.bt(self.a)['rooms'][0]

    def test_player_room_escrow_rating_and_capacity(self):
        self.book(where=self.room['id'], price=600_000)
        self.accept()
        self.assertEqual(self.effects(self.sid(self.cuc)), [], 'escrow: the provider is paid only when the baby is born')
        sid = self.stay(self.a)['id']
        self.do(self.a, 'family_birth_checkin', id=sid)
        self.assertEqual(self.bt(self.cuc)['my_room']['staying'], 1)
        self.clock.t += bt.STAY_HOURS * H
        self.fam(self.b)
        self.assertEqual([e['amount'] for e in self.effects(self.sid(self.cuc))], [570_000])
        rate = self.bt(self.a)['rate']
        self.assertEqual(rate['id'], sid)
        self.do(self.a, 'family_birth_rate', id=sid, stars=5)
        with self.assertRaises(mr.MarriageError):
            self.do(self.b, 'family_birth_rate', id=sid, stars=1)
        self.assertIsNone(self.bt(self.a)['rate'])
        self.assertEqual(self.bt(self.a)['rooms'], [], 'with a child, no room list is read')
        mine = self.bt(self.cuc)['my_room']['room']
        self.assertEqual((mine['stars'], mine['rated'], mine['born']), (5.0, 1, 1))

    def test_price_change_or_closing_before_the_answer_cancels_without_charge(self):
        self.book(where=self.room['id'], price=600_000)
        self.do(self.cuc, 'family_room_set', name='Phòng Đồi Thông', price=700_000)
        before = self.wallet(self.a)
        out = self.accept()
        self.assertIn('đổi giá', out['message'])
        self.assertEqual(self.wallet(self.a), before)
        self.assertIsNone(self.stay(self.a))
        self.do(self.cuc, 'family_room_set', name='Phòng Đồi Thông', price=700_000, open=False)
        self.assertEqual(self.bt(self.a)['rooms'], [])
        with self.assertRaises(mr.MarriageError) as e:
            self.book(where=self.room['id'], price=700_000)
        self.assertEqual(e.exception.code, 'stale_room')

    def test_own_room_is_not_listed_or_bookable(self):
        mr._mutate(self.store, {self.sid(self.a): homestay_owner})
        self.do(self.a, 'family_room_set', name='Phòng nhà mình', price=bt.FLOOR)
        mine = self.bt(self.a)
        self.assertEqual([r['name'] for r in mine['rooms']], ['Phòng Đồi Thông'])
        self.assertTrue(mine['my_room']['can'])
        with self.store.connect() as db:
            own = db.execute('SELECT id FROM birth_rooms WHERE sid=?', (self.sid(self.a),)).fetchone()['id']
        with self.assertRaises(mr.MarriageError) as e:
            self.book(self.b, where=int(own), price=bt.FLOOR)
        self.assertEqual(e.exception.code, 'own_room')

    def test_nurse_assist_gives_a_healthier_baby_never_xu(self):
        dao = self.user('dao', 777)
        self.assertIsNone(self.bt(dao)['nurse'])
        mr._mutate(self.store, {self.sid(dao): nurse})
        self.book(where=self.room['id'], price=600_000)
        self.assertEqual(self.bt(dao)['nurse']['calls'], [], 'a proposal is not a call yet')
        self.accept()
        calls = self.bt(dao)['nurse']['calls']
        self.assertEqual([c['name'] for c in calls], ['Bông'])
        with self.assertRaises(mr.MarriageError) as e:   # a spouse cannot be the nurse of their own birth
            mr._mutate(self.store, {self.sid(self.a): nurse})
            self.do(self.a, 'family_birth_nurse', id=calls[0]['id'])
        self.assertEqual(e.exception.code, 'own_stay')
        self.do(dao, 'family_birth_nurse', id=calls[0]['id'])
        eva = self.user('eva', 1)
        mr._mutate(self.store, {self.sid(eva): nurse})
        with self.assertRaises(mr.MarriageError) as e:
            self.do(eva, 'family_birth_nurse', id=calls[0]['id'])
        self.assertEqual(e.exception.code, 'taken', 'first nurse wins')
        self.assertEqual(self.stay(self.a)['nurse'], 'Dao')
        self.do(self.b, 'family_birth_checkin', id=calls[0]['id'])
        self.clock.t += bt.STAY_HOURS * H
        self.do(self.b, 'family_birth_done', id=calls[0]['id'])
        child = self.fam(self.a)['child']
        self.assertEqual((child['needs'], child['bond'], child['birth']['nurse']), (dict(food=85, clean=85, joy=85), 10, 'Dao'))
        self.assertEqual(self.wallet(dao), 777, 'the nurse perk prints no xu')
        self.assertEqual(self.effects(self.sid(dao)), [])
        self.assertEqual(self.bt(dao)['nurse']['done'], 1)

    def test_provider_account_gone_before_check_in_refunds(self):
        self.book(where=self.room['id'], price=600_000)
        before = self.wallet(self.a)
        self.accept()
        mr.forget(self.store, self.cuc)
        with self.store.connect() as db:
            db.execute('DELETE FROM birth_rooms WHERE sid=?', (self.sid(self.cuc),))
        out = self.do(self.a, 'family_birth_checkin', id=self.stay(self.a)['id'])
        self.assertIn('hoàn', out['message'].lower())
        self.assertEqual(self.wallet(self.a), before)


class OldChildren(BirthBase):
    def legacy(self, origin='birth'):
        a, b = self.sid(self.a), self.sid(self.b)
        self.store.transaction(lambda db: db.execute('INSERT INTO family_requests(couple,from_sid,to_sid,kind,data,at) VALUES(?,?,?,?,?,?)',
                                                     (self.cid, a, b, 'child', json.dumps(dict(name='Cũ', origin=origin)), mr.now())))

    def test_an_old_pending_free_request_finishes_as_before_and_blocks_a_booking(self):
        self.legacy('birth')
        with self.assertRaises(mr.MarriageError) as e:
            self.book()
        self.assertEqual(e.exception.code, 'pending')
        before = (self.wallet(self.a), self.wallet(self.b))
        req = self.fam(self.b)['requests'][0]
        self.do(self.b, 'family_answer', id=req['id'], answer='accept')
        child = self.fam(self.a)['child']
        self.assertEqual((child['name'], child['origin'], child['waiting']), ('Cũ', 'birth', True), 'the 2.4.66 rule: born the next VN day')
        self.assertIsNone(child['birth'])
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), before, 'free, as it was promised')

    def test_existing_child_and_copies_are_never_touched(self):
        self.legacy('adopt')
        req = self.fam(self.b)['requests'][0]
        self.do(self.b, 'family_answer', id=req['id'], answer='accept')
        with self.store.connect() as db:
            raw = db.execute('SELECT state,revision FROM family_children WHERE couple=?', (self.cid,)).fetchone()
            raw = (raw['state'], raw['revision'])
        for kind in ('birth', 'adopt'):
            with self.assertRaises(mr.MarriageError) as e:
                self.book(kind=kind)
            self.assertEqual(e.exception.code, 'already_owned')
        self.fam(self.a); self.fam(self.b)
        with self.store.connect() as db:
            now = db.execute('SELECT state,revision FROM family_children WHERE couple=?', (self.cid,)).fetchone()
        self.assertEqual((now['state'], now['revision']), raw)

    def test_a_child_that_came_another_way_during_the_stay_refunds_the_room(self):
        self.book()
        self.accept()
        sid = self.stay(self.a)['id']
        self.do(self.a, 'family_birth_checkin', id=sid)
        # a 2.4.66 process during a rollback lets them accept an old free request meanwhile
        child = family._child('Khác', 'adopt')
        self.store.transaction(lambda db: db.execute('INSERT INTO family_children(couple,state) VALUES(?,?)', (self.cid, family._json(child))))
        self.clock.t += bt.STAY_HOURS * H
        out = self.do(self.b, 'family_birth_done', id=sid)
        self.assertIn('hoàn', out['message'])
        self.assertEqual(self.children()[0]['name'], 'Khác')
        self.assertEqual([e['amount'] for e in self.effects(self.sid(self.a))], [bt.NPC_PRICE])

    def test_divorce_with_a_paid_booking_refunds_the_payer(self):
        self.book()
        self.accept()
        before = self.wallet(self.a)
        self.act(self.b, 'divorce', confirm='LY HON')
        mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(self.wallet(self.a), before + bt.NPC_PRICE)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM birth_stays").fetchone()['status'], 'refunded')

    def test_alert_dot_for_a_waiting_answer(self):
        self.act(self.b, 'seen')
        before = mr.alerts(self.store, self.sid(self.b))['alerts']
        self.book()
        self.act(self.b, 'seen')
        self.assertEqual(mr.alerts(self.store, self.sid(self.b))['alerts'], before + 1)


class BrowserUnits(unittest.TestCase):
    def test_birth_and_family_ui_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        root = Path(__file__).resolve().parents[1]
        for script in ('tests/birth_ui.mjs', 'tests/family.mjs', 'tests/family_ux.mjs'):
            out = subprocess.run([node, str(root / script)], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, script + '\n' + out.stderr + out.stdout)
