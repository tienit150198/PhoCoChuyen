"""Shared children and home consent use real, isolated PostgreSQL transactions."""
import copy
import datetime
import threading

from game import household, housing, marriage as mr, couple as cp, journey as jr, bank as bk
from tests.test_couple import CoupleBase


class FamilyTests(CoupleBase):
    def setUp(self):
        super().setUp()
        for token in (self.a, self.b):
            mr._mutate(self.store, {self.sid(token): lambda s: s['journey'].__setitem__('life_day', 12)})
            self.fund(token, 5000)

    def family(self, token):
        return self.view(token)['family']

    def child(self, origin='adopt'):
        self.act(self.a, 'family_child_request', name='Bông', origin=origin, rid='child-invite-001')
        request = self.family(self.b)['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='child-accept-001')
        return self.family(self.a)['child']

    def buy(self, token):
        price = housing.HOMES['tap_the']['price']
        self.store.command(token, 'home-buy-family', self.store.read(token)[1], None, 'jr_home_buy', dict(kind='tap_the', down=price, confirm=True))

    def test_family_is_available_without_changing_personal_household(self):
        self.assertIn('family', self.view(self.a))
        self.assertIsNone(self.family(self.a)['child'])
        self.assertNotIn('household', self.state(self.a)['journey'])

    def test_shared_child_eligibility_explains_both_partners_days(self):
        mr._mutate(self.store,{self.sid(self.b):lambda s:s['journey'].__setitem__('life_day',3)})
        f=self.family(self.a)
        self.assertFalse(f['ready'])
        self.assertEqual(f['eligibility'],dict(self_day=12,partner_day=3,min_day=10,self_story=True,partner_story=True))
        mr._mutate(self.store,{self.sid(self.b):lambda s:s['journey'].__setitem__('life_day',10)})
        self.assertTrue(self.family(self.a)['ready'])

    def test_partner_home_ownership_is_visible_as_next_invitation_step(self):
        self.assertFalse(self.family(self.b)['partner_can_invite'])
        self.buy(self.a)
        f=self.family(self.b)
        self.assertFalse(f['can_invite'])
        self.assertTrue(f['partner_can_invite'])
        self.assertEqual(f['partner_home_name'],housing.HOMES['tap_the']['name'])

    def test_joint_withdraw_and_spend_above_1000_are_limited_by_balance(self):
        self.act(self.a, 'fund_deposit', amount=5000, rid='joint-deposit-large')
        before = self.wallet(self.a)
        for _ in range(2):
            self.act(self.a, 'fund_withdraw', amount=1800, rid='joint-withdraw-large')
        self.assertEqual(self.wallet(self.a), before + 1800)
        mr._mutate(self.store, {self.sid(self.a): lambda s: cp.joint_spend(s, 1700, 'Mua đồ', 'joint-spend-large')})
        self.assertEqual(self.home(self.b)['fund']['balance'], 1500)
        self.assertEqual(self.home(self.a)['fund']['daily_left'], 1500)
        self.assertIsNone(self.home(self.a)['limits']['withdraw_cap'])
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.b, 'fund_withdraw', amount=1501, rid='joint-over-balance')
        self.assertEqual(err.exception.code, 'fund_low')

    def test_child_requires_partner_consent_and_replays_once(self):
        self.act(self.a, 'family_child_request', name='Bông', origin='adopt', rid='child-invite-001')
        self.act(self.a, 'family_child_request', name='Bông', origin='adopt', rid='child-invite-001')
        self.assertIsNone(self.family(self.a)['child'])
        request = self.family(self.b)['requests'][0]
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'family_answer', id=request['id'], answer='accept', rid='wrong-answer-001')
        for _ in range(2):
            self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='child-accept-001')
        self.assertEqual(self.family(self.a)['child'], self.family(self.b)['child'])
        self.assertEqual(self.row('SELECT COUNT(*) AS n FROM family_children')['n'], 1)

    def test_pending_family_invitation_keeps_alert_after_notice_is_seen(self):
        self.act(self.b,'seen')
        before=mr.alerts(self.store,self.sid(self.b))['alerts']
        self.act(self.a,'family_child_request',name='Bông',rid='alert-child-invite')
        self.act(self.b,'seen')
        self.assertEqual(mr.alerts(self.store,self.sid(self.b))['alerts'],before+1)

    def test_personal_child_is_preserved_and_both_parents_can_care(self):
        self.store.command(self.a, 'personal-child-001', self.store.read(self.a)[1], None, 'jr_hh_adopt', dict(kind='child', name='Mây', confirm=True))
        personal = copy.deepcopy(self.state(self.a)['journey']['household'])
        self.child()
        before = self.wallet(self.a)
        for _ in range(2):
            self.act(self.a, 'family_child_care', child='shared', act='milk', pay='cash', rid='milk-once-001')
        self.act(self.b, 'family_child_care', child='shared', act='wash', rid='wash-once-001')
        self.assertEqual(self.wallet(self.a), before - 4)
        self.assertEqual(self.family(self.a)['child']['care_days'], 1)
        self.assertEqual(self.state(self.a)['journey']['household'], personal)
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'family_child_care', child='shared', act='milk', rid='milk-other-001')

    def test_birth_waits_one_vietnam_calendar_day_without_offline_penalties(self):
        child = self.child('birth')
        self.assertTrue(child['waiting'])
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'family_child_care', child='shared', act='milk', rid='early-care-001')
        self.clock.t += 86400
        self.assertFalse(self.family(self.b)['child']['waiting'])
        self.act(self.b, 'family_child_care', child='shared', act='read', rid='birth-read-001')
        self.clock.t += 30 * 86400
        self.assertEqual(self.family(self.a)['child']['care_days'], 1)
        self.assertEqual(self.family(self.a)['child']['needs']['food'], 65)

    def test_long_request_ids_with_common_prefix_pay_separately_and_replay_once(self):
        self.child()
        before = self.wallet(self.a)
        care_rid = 'X' * 44 + 'a' * 20
        style_rid = 'X' * 44 + 'b' * 20
        self.act(self.a, 'family_child_care', child='shared', act='milk', pay='cash', rid=care_rid)
        self.assertEqual(self.wallet(self.a), before - 4)
        self.act(self.a, 'family_child_style', child='shared', item='yem', pay='cash', rid=style_rid)
        self.assertEqual(self.wallet(self.a), before - 24)   # 💹 07/10: milk 4 + yếm 20 (was 18)
        self.assertIn('yem', self.family(self.b)['child']['owned'])
        self.act(self.a, 'family_child_care', child='shared', act='milk', pay='cash', rid=care_rid)
        self.act(self.a, 'family_child_style', child='shared', item='yem', pay='cash', rid=style_rid)
        self.assertEqual(self.wallet(self.a), before - 24)   # 💹 07/10: milk 4 + yếm 20 (was 18)

    def test_concurrent_same_slot_pays_once(self):
        self.child()
        before = self.wallet(self.a) + self.wallet(self.b)
        errors = []
        def care(token, rid):
            try:
                self.act(token, 'family_child_care', child='shared', act='milk', pay='cash', rid=rid)
            except mr.MarriageError as e:
                errors.append(e.code)
        workers = [threading.Thread(target=care, args=(t, 'race-care-' + str(i))) for i, t in enumerate((self.a, self.b))]
        for w in workers: w.start()
        for w in workers: w.join(10)
        self.assertEqual(errors, ['already_done'])
        self.assertEqual(self.wallet(self.a) + self.wallet(self.b), before - 4)
        self.assertEqual(self.family(self.a)['child']['care_days'], 1)

    def test_home_does_not_move_spouse_until_explicit_acceptance(self):
        self.buy(self.a)
        for token in (self.a, self.b): mr.on_load(self.store, token, self.state(token))
        self.assertFalse((self.state(self.b)['journey'].get('home') or {}).get('shared'))
        self.act(self.a, 'family_home_request', rid='home-invite-001')
        request = self.family(self.b)['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='home-accept-001')
        self.assertEqual(self.state(self.b)['journey']['home']['shared']['id'], self.state(self.a)['journey']['home']['own']['id'])
        self.assertTrue(self.family(self.a)['together'])
        self.act(self.b, 'family_home_leave', rid='home-leave-001')
        for token in (self.a, self.b): mr.on_load(self.store, token, self.state(token))
        self.assertIsNone(self.state(self.b)['journey']['home']['shared'])

    def test_existing_shared_home_is_preserved_on_load(self):
        self.buy(self.a)
        own=self.state(self.a)['journey']['home']['own']
        mr._mutate(self.store,{self.sid(self.b):lambda s:housing.apply_effect(s,dict(set='in',couple=self.cid,id=own['id'],kind=own['kind'],name='An'))})
        before=copy.deepcopy(self.state(self.b)['journey']['home']['shared'])
        for token in (self.a,self.b):mr.on_load(self.store,token,self.state(token))
        self.assertEqual(self.state(self.b)['journey']['home']['shared'],before)
        self.assertTrue(self.family(self.b)['together'])

    def test_declined_and_stale_home_requests_do_not_move_anyone(self):
        self.buy(self.a)
        self.act(self.a, 'family_home_request', rid='home-invite-001')
        request = self.family(self.b)['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='decline', rid='home-decline-001')
        self.assertFalse((self.state(self.b)['journey'].get('home') or {}).get('shared'))
        self.act(self.a, 'family_home_request', rid='home-invite-002')
        request = self.family(self.b)['requests'][0]
        own = self.state(self.a)['journey']['home']['own']
        self.store.command(self.a, 'sell-family-home', self.store.read(self.a)[1], None, 'jr_home_sell', dict(confirm=True, value=housing.value_of(own, 12)))
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='stale-home-001')

    def test_divorce_keeps_private_child_copies_without_overwriting_personal_child(self):
        self.child()
        self.act(self.a, 'family_child_rename', child='shared', name='Mít', rid='rename-child-001')
        self.act(self.a, 'family_child_style', child='shared', item='yem', pay='cash', rid='style-child-001')
        self.act(self.a, 'divorce', confirm='LY HON')
        for token in (self.a, self.b):
            family = self.family(token)
            self.assertIsNone(family['child'])
            self.assertEqual(family['copies'][0]['name'], 'Mít')
            self.assertEqual(family['copies'][0]['outfit'], 'yem')
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'family_child_care', child='shared', act='wash', rid='ex-shared-care')
        child_id = self.family(self.a)['copies'][0]['id']
        self.act(self.a, 'family_child_rename', child=child_id, name='Mít nhỏ', rid='copy-rename-001')
        self.assertEqual(self.family(self.b)['copies'][0]['name'], 'Mít')

    def test_account_deletion_preserves_survivor_and_removes_deleted_family_data(self):
        self.child()
        self.buy(self.a)
        self.act(self.a, 'family_home_request', rid='delete-home-invite')
        request = self.family(self.b)['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='delete-home-accept')
        deleted = self.sid(self.a)
        mr.forget(self.store, self.a)
        mr.on_load(self.store, self.b, self.state(self.b))
        family = self.family(self.b)
        self.assertIsNone(family['child'])
        self.assertEqual(family['copies'][0]['name'], 'Bông')
        self.assertIsNone(self.state(self.b)['journey']['home']['shared'])
        self.assertEqual(self.row('SELECT COUNT(*) AS n FROM family_children')['n'], 0)
        self.assertEqual(self.row('SELECT COUNT(*) AS n FROM family_custody WHERE sid=?', deleted)['n'], 0)
        self.assertEqual(self.row('SELECT COUNT(*) AS n FROM family_receipts WHERE sid=?', deleted)['n'], 0)
        self.assertEqual(self.row('SELECT COUNT(*) AS n FROM family_requests')['n'], 0)
        self.act(self.b, 'family_child_care', child=family['copies'][0]['id'], act='wash', rid='survivor-care-001')
        self.assertEqual(self.family(self.b)['copies'][0]['care_days'], 1)

    def test_acceptance_retains_personal_home_and_rent_deposit_is_returned_once(self):
        for token in (self.a, self.b): self.buy(token)
        own_b = copy.deepcopy(self.state(self.b)['journey']['home']['own'])
        self.act(self.a, 'family_home_request', rid='own-home-invite')
        request = self.family(self.b)['requests'][0]
        self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='own-home-accept')
        home = self.state(self.b)['journey']['home']
        self.assertIsNone(home['own'])
        self.assertEqual(home['props'][0]['id'], own_b['id'])
        self.assertTrue(self.family(self.b)['together'])
        self.act(self.b, 'family_home_leave', rid='rent-home-leave')
        self.store.command(self.b, 'family-rent-room', self.store.read(self.b)[1], None, 'jr_home_rent', dict(kind=housing.RENT[0],confirm=True))
        deposit = self.state(self.b)['journey']['home']['rent']['deposit']
        before = self.wallet(self.b)
        self.act(self.a, 'family_home_request', rid='rent-home-invite')
        request = self.family(self.b)['requests'][0]
        for _ in range(2): self.act(self.b, 'family_answer', id=request['id'], answer='accept', rid='rent-home-accept')
        self.assertEqual(self.wallet(self.b), before + deposit)
        self.assertIsNone(self.state(self.b)['journey']['home']['rent'])

    def test_cohabitation_does_not_require_child_unlock_day(self):
        for token in (self.a,self.b):
            mr._mutate(self.store,{self.sid(token):lambda s:s['journey'].__setitem__('life_day',1)})
        self.buy(self.a)
        self.act(self.a,'family_home_request',rid='early-home-invite')
        request=self.family(self.b)['requests'][0]
        self.act(self.b,'family_answer',id=request['id'],answer='accept',rid='early-home-accept')
        self.assertTrue(self.family(self.b)['together'])

    def test_vietnam_midnight_not_life_day_controls_shared_care(self):
        self.clock.t = datetime.datetime(2026,10,4,16,59,tzinfo=datetime.timezone.utc).timestamp()
        self.child()
        self.act(self.a,'family_child_care',act='milk',pay='cash',rid='vn-before-midnight')
        days = [self.state(token)['journey']['life_day'] for token in (self.a,self.b)]
        self.clock.t += 120
        self.act(self.b,'family_child_care',act='milk',pay='cash',rid='vn-after-midnight')
        self.assertEqual(self.family(self.a)['day'],'2026-10-05')
        self.assertEqual(self.family(self.b)['child']['care_days'],2)
        self.assertEqual([self.state(token)['journey']['life_day'] for token in (self.a,self.b)],days)

    def test_insufficient_funds_and_changed_request_payload_roll_back(self):
        self.child()
        self.fund(self.a,0)
        before = self.family(self.a)['child']
        with self.assertRaises(mr.MarriageError):
            self.act(self.a,'family_child_care',act='milk',pay='cash',rid='poor-care-request')
        self.assertEqual(self.family(self.a)['child'],before)
        self.act(self.a,'family_child_rename',name='Mít',rid='rename-conflict-001')
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.a,'family_child_rename',name='Cam',rid='rename-conflict-001')
        self.assertEqual(err.exception.code,'request_conflict')
        outsider = self.user('Chi')
        with self.assertRaises(mr.MarriageError):
            self.act(outsider,'family_child_care',act='wash',rid='outsider-care-001')
        self.assertEqual(self.family(self.b)['child']['name'],'Mít')

    def test_old_pending_automatic_home_effect_cannot_bypass_consent(self):
        self.buy(self.a)
        own = self.state(self.a)['journey']['home']['own']
        eff = mr._effect('legacy-auto-home',self.sid(self.b),'home',data=dict(set='in',couple=self.cid,id=own['id'],kind=own['kind'],name='An'))
        self.store.transaction(lambda db: mr._insert_effects(db,[eff]))
        mr.on_load(self.store,self.b,self.state(self.b))
        self.assertFalse((self.state(self.b)['journey'].get('home') or {}).get('shared'))

    def test_family_payment_archives_displaced_wallet_history(self):
        self.child()
        def history(s):
            s['journey']['history']=[dict(day=12,amount=1,kind='life',label='Lịch sử '+str(i),career=None) for i in range(120)]
        mr._mutate(self.store,{self.sid(self.a):history})
        before = self.row("SELECT COUNT(*) AS n FROM archive WHERE sid=? AND kind='wallet'",self.sid(self.a))['n']
        self.act(self.a,'family_child_care',act='milk',pay='cash',rid='archive-care-001')
        after = self.row("SELECT COUNT(*) AS n FROM archive WHERE sid=? AND kind='wallet'",self.sid(self.a))['n']
        self.assertEqual(after,before+1)
