"""👥 Bạn bè (game/friends.py) and life as a couple (game/couple.py): friends, joint fund,
transfers, help requests, IOUs, moments, anniversaries and the bank helpers."""
import json
import unittest

from game import couple as cp
from game import friends as fr
from game import marriage as mr
from game.engine import GameError, migrate_state, new_state, validate_state
from tests.pg_support import on_pg
from tests.test_marriage import Base, PLAN, DAY


class FriendTests(Base):
    auto_friends = False

    def setUp(self):
        super().setUp()
        self.a, self.b, self.c = self.user('an'), self.user('binh'), self.user('cuc')

    def search(self, tok, **d):
        return self.act(tok, 'friend_search', **d)

    def test_search_is_exact_and_leaks_nothing(self):
        found = self.search(self.a, username='  BINH_test ')['found']
        self.assertEqual((found['name'], found['state'], found['status']), ('Binh', 'none', 'single'))
        self.assertRegex(found['code'], r'^PCC-')
        text = json.dumps(found)
        for secret in (self.sid(self.b), 'binh_test', self.b):
            self.assertNotIn(secret, text)
        for partial in ('binh', 'binh_tes', 'inh_test', 'b%', '_test', 'binh_test*'):
            self.assertIsNone(self.search(self.a, username=partial)['found'], partial)
        self.assertIsNone(self.search(self.a, username='an_test')['found'])          # yourself
        self.assertEqual(self.search(self.a, code=found['code'])['found']['name'], 'Binh')   # the code still works

    def test_hidden_missing_and_blocked_look_the_same(self):
        self.act(self.c, 'friend_settings', findable=False)
        self.act(self.b, 'friend_block', code=self.code(self.a))
        answers = {json.dumps(self.search(self.a, username=u)) for u in ('khong_ai_test', 'cuc_test', 'binh_test')}
        self.assertEqual(len(answers), 1)
        self.assertEqual(self.search(self.a, code=self.code(self.c))['found']['name'], 'Cuc')   # a shared code still finds Cuc
        self.assertIsNone(self.search(self.a, code=self.code(self.b))['found'])              # a block hides both ways
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'friend_request', code=self.code(self.b))
        self.assertEqual(e.exception.code, 'not_found')
        self.act(self.c, 'friend_settings', findable=True)
        self.assertIsNotNone(self.search(self.a, username='cuc_test')['found'])

    def test_requests_by_username_count_as_searches(self):
        for _ in range(fr.SEARCH_PER_MIN):
            with self.assertRaises(mr.MarriageError):
                self.act(self.a, 'friend_request', username='khong_ai_test')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'friend_request', username='binh_test')
        self.assertEqual(e.exception.code, 'rate_limited')

    def test_search_rate_limits(self):
        for _ in range(fr.SEARCH_PER_MIN):
            self.search(self.a, username='nobody_test')
        with self.assertRaises(mr.MarriageError) as e:
            self.search(self.a, username='binh_test')
        self.assertEqual((e.exception.code, e.exception.status), ('rate_limited', 429))
        done = fr.SEARCH_PER_MIN
        while done < fr.SEARCH_PER_DAY:
            self.clock.t += 61
            for _ in range(min(fr.SEARCH_PER_MIN, fr.SEARCH_PER_DAY - done)):
                self.search(self.a, username='nobody_test')
                done += 1
        self.clock.t += 61
        with self.assertRaises(mr.MarriageError):
            self.search(self.a, username='binh_test')
        self.assertEqual(self.view(self.a)['friends']['searches_left'], 0)
        self.clock.t += DAY
        self.assertIsNotNone(self.search(self.a, username='binh_test')['found'])

    def test_request_accept_decline_cancel_unfriend(self):
        self.act(self.a, 'friend_request', username='binh_test')
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'friend_request', username='binh_test')                     # twice
        vb = self.view(self.b)['friends']
        self.assertEqual([r['name'] for r in vb['incoming']], ['An'])
        self.assertEqual(mr.alerts(self.store, self.sid(self.b))['friends'], 1)
        self.assertEqual(self.search(self.a, username='binh_test')['found']['state'], 'sent')
        self.act(self.b, 'friend_respond', id=vb['incoming'][0]['id'], answer='accept')
        for tok, other in ((self.a, 'Binh'), (self.b, 'An')):
            self.assertEqual([f['name'] for f in self.view(tok)['friends']['list']], [other])
        self.assertIn('kết bạn', self.view(self.a)['me']['notice'])
        # decline and cancel
        self.act(self.c, 'friend_request', username='an_test')
        rid = self.view(self.a)['friends']['incoming'][0]['id']
        self.act(self.a, 'friend_respond', id=rid, answer='decline')
        self.assertEqual(self.view(self.a)['friends']['incoming'], [])
        self.act(self.c, 'friend_request', username='an_test')
        rid = self.view(self.c)['friends']['outgoing'][0]['id']
        self.act(self.c, 'friend_cancel', id=rid)
        self.assertEqual(self.view(self.a)['friends']['incoming'], [])
        # asking back makes friends at once
        self.act(self.c, 'friend_request', username='an_test')
        out = self.act(self.a, 'friend_request', username='cuc_test')
        self.assertIn('bạn bè', out['message'])
        self.assertEqual(len(self.view(self.a)['friends']['list']), 2)
        self.act(self.a, 'friend_remove', code=self.code(self.c))
        self.assertEqual([f['name'] for f in self.view(self.c)['friends']['list']], [])

    def test_block_from_a_request_and_daily_limit(self):
        self.act(self.a, 'friend_request', username='binh_test')
        rid = self.view(self.b)['friends']['incoming'][0]['id']
        self.act(self.b, 'friend_respond', id=rid, answer='block')
        self.assertIsNone(self.search(self.a, username='binh_test')['found'])
        self.assertIsNone(self.search(self.b, username='an_test')['found'])
        others = [self.user(f'nguoi{i}') for i in range(fr.REQUESTS_PER_DAY + 1)]
        for i, tok in enumerate(others[:fr.REQUESTS_PER_DAY]):
            self.act(self.c, 'friend_request', username=f'nguoi{i}_test')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.c, 'friend_request', username=f'nguoi{fr.REQUESTS_PER_DAY}_test')
        self.assertEqual(e.exception.code, 'rate_limited')

    def test_friend_card_career_and_marriage_status(self):
        def board(db):
            for board, level, score in (('all', 7, 900), ('grocery', 5, 600), ('certs', 2, 50), ('milk_tea', 3, 100),
                                       ('wealth', 0, 54000), ('titles', 9, 700), ('fair20261003xu', 0, 800)):   # the last three: not workplaces
                db.execute('INSERT INTO leaderboard(sid,board,score,k1,k2,level,days,served,stars,mastered,since,updated) VALUES(?,?,?,0,0,?,1,1,1,0,0,0) '
                           'ON CONFLICT(sid,board) DO UPDATE SET score=excluded.score,level=excluded.level',   # a story save has its 💰 row
                           (self.sid(self.b), board, score, level))
        self.store.transaction(board)
        self.befriend(self.sid(self.a), self.sid(self.b))
        card = self.view(self.a)['friends']['list'][0]
        from game.content import CAREER_META
        self.assertEqual(card['career'], dict(career=CAREER_META['grocery']['short'], level=7))
        self.assertEqual(card['status'], 'single')

    def test_proposals_only_to_friends(self):
        rid = self.ring(self.a)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'propose', code=self.code(self.b), ring=rid, message='hem')
        self.assertIn('bạn bè', e.exception.message)
        self.assertFalse(self.act(self.a, 'lookup', code=self.code(self.b))['found']['can'])
        self.act(self.a, 'friend_request', username='binh_test')
        self.act(self.b, 'friend_respond', id=self.view(self.b)['friends']['incoming'][0]['id'], answer='accept')
        self.act(self.a, 'propose', code=self.code(self.b), ring=rid, message='hem')
        self.act(self.b, 'respond', id=self.view(self.b)['incoming'][0]['id'], answer='accept')
        card = self.view(self.a)['friends']['list'][0]
        self.assertEqual((card['spouse'], card['status']), (True, 'engaged'))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'friend_remove', code=self.code(self.b))
        self.assertEqual(e.exception.code, 'spouse')

    def test_pending_proposal_from_before_friends_stays_valid(self):
        rid = self.ring(self.a)
        a, b = self.sid(self.a), self.sid(self.b)
        self.store.transaction(lambda db: (db.execute("UPDATE marriage_rings SET status='proposed' WHERE id=?", (rid,)),
                                           db.execute("INSERT INTO proposals(from_sid,to_sid,ring,message,announce,status,at) VALUES(?,?,?,'hem',1,'pending',?)",
                                                      (a, b, rid, self.clock.t))))
        self.act(self.b, 'respond', id=self.view(self.b)['incoming'][0]['id'], answer='accept')
        self.assertEqual(self.view(self.a)['couple']['status'], 'engaged')

    def test_friend_without_a_code_gets_one(self):
        """A date in the live service befriends two accounts that never opened Hôn nhân: no PCC code, so
        "Hủy kết bạn" / "Chặn" sent code=null and got a 400. The friend list now gives them a code."""
        self.befriend(self.sid(self.a), self.sid(self.b))
        self.store.transaction(lambda db: db.execute('DELETE FROM marriage_people WHERE sid=?', (self.sid(self.b),)))
        card = self.view(self.a)['friends']['list'][0]
        self.assertRegex(card['code'] or '', r'^PCC-')
        self.act(self.a, 'friend_remove', code=card['code'])
        self.assertEqual(self.view(self.a)['friends']['list'], [])

    def test_account_delete_forgets_friends(self):
        self.befriend(self.sid(self.a), self.sid(self.b))
        self.act(self.c, 'friend_request', username='an_test')
        mr.forget(self.store, self.a)
        self.assertEqual(self.rows('SELECT * FROM friends WHERE sid=? OR friend=?', self.sid(self.a), self.sid(self.a)), [])
        self.assertEqual(self.rows('SELECT * FROM friend_requests WHERE from_sid=? OR to_sid=?', self.sid(self.a), self.sid(self.a)), [])


class CoupleBase(Base):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.user('an', 1500), self.user('binh', 1500)
        self.engage(self.a, self.b)
        wid = self.plan_and_confirm(self.a, self.b)
        self.store.transaction(lambda db: db.execute('UPDATE weddings SET due_at=? WHERE id=?', (self.clock.t - 1, wid)))
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
        self.clock.t += 13 * 3600
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
            self.fund(tok, 1000)
        self.cid = self.view(self.a)['couple']['id']

    def home(self, tok):
        return self.view(tok)['home']

    def label(self, tok):
        return self.state(tok)['journey']['history'][-1]


class FundTests(CoupleBase):
    def test_withdrawals_above_1000_have_no_daily_quota(self):
        self.fund(self.a, 3000)
        self.act(self.a, 'fund_deposit', amount=3000, rid='large-deposit-1')
        before = self.wallet(self.a)
        for _ in range(2):
            self.act(self.a, 'fund_withdraw', amount=1500, rid='large-withdraw-1')
        self.assertEqual(self.wallet(self.a), before + 1500)
        self.act(self.a, 'fund_withdraw', amount=1000, rid='large-withdraw-2')
        self.assertEqual(self.home(self.a)['fund']['daily_left'], 500)
        self.assertEqual(self.home(self.b)['fund']['daily_left'], 500)
        self.assertIsNone(self.home(self.a)['limits']['withdraw_cap'])
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.b, 'fund_withdraw', amount=501, rid='large-over-balance')
        self.assertEqual(err.exception.code, 'fund_low')
        self.act(self.b, 'fund_withdraw', amount=500, rid='large-withdraw-3')
        self.assertEqual(self.home(self.a)['fund']['balance'], 0)

    def test_card_spend_and_withdrawals_share_actual_balance(self):
        self.fund(self.a, 2000)
        self.act(self.a, 'fund_deposit', amount=2000, rid='large-deposit-2')
        for _ in range(2):
            mr._mutate(self.store, {self.sid(self.a): lambda s: cp.joint_spend(s, 1200, 'Học phí', 'large-card-1200')})
        self.assertEqual(cp.joint_account(self.state(self.a))['daily_left'], 800)
        self.act(self.a, 'fund_withdraw', amount=300, rid='large-withdraw-rest')
        self.assertEqual(self.home(self.a)['fund']['daily_left'], 500)
        self.assertEqual(self.home(self.b)['fund']['daily_left'], 500)
        with self.assertRaises(GameError) as err:
            cp.joint_spend(self.state(self.a), 501, 'Mua thêm', 'large-card-over')
        self.assertEqual(err.exception.code, 'fund_low')
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.a, 'fund_withdraw', amount=501, rid='large-withdraw-over')
        self.assertEqual(err.exception.code, 'fund_low')
        self.assertEqual(self.home(self.a)['fund']['balance'], 500)

    def test_deposit_cap_is_its_own_200k_and_gifts_keep_5000(self):
        """F#231: a joint-fund deposit borrowed the spouse-gift cap (5,000)."""
        self.assertEqual((cp.DEPOSIT_MAX, cp.SEND_MAX), (200000, 5000))
        limits = self.home(self.a)['limits']
        self.assertEqual((limits['deposit_max'], limits['send_max']), (200000, 5000))
        self.fund(self.a, 250000)
        self.act(self.a, 'fund_deposit', amount=200000, rid='big-deposit-01')
        self.assertEqual(self.home(self.b)['fund']['balance'], 200000)
        self.assertEqual(self.wallet(self.a), 50000)
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.a, 'fund_deposit', amount=200001, rid='big-deposit-02')
        self.assertEqual(err.exception.code, 'bad_amount')
        with self.assertRaises(mr.MarriageError) as err:
            self.act(self.a, 'send', amount=5001, rid='big-send-0001')
        self.assertEqual(err.exception.code, 'bad_amount')
        self.assertEqual((self.wallet(self.a), self.home(self.a)['fund']['balance']), (50000, 200000))

    def test_spouse_block_links_the_couple(self):
        sp = self.state(self.a)['marriage']['spouse']
        self.assertEqual((sp['couple'], sp['side'], sp['status']), (self.cid, 'a', 'married'))

    def test_deposit_withdraw_balance_and_history(self):
        self.act(self.a, 'fund_deposit', amount=500, rid='deposit-0001')
        self.act(self.a, 'fund_deposit', amount=500, rid='deposit-0001')           # a retried tap
        self.assertEqual(self.wallet(self.a), 500)
        self.assertEqual((self.label(self.a)['label'], self.label(self.a)['kind'], self.label(self.a)['amount']), ('Gửi vào quỹ chung', 'life', -500))
        self.assertEqual(self.home(self.b)['fund']['balance'], 500)
        self.assertIn('500 xu vào quỹ chung', self.view(self.b)['me']['notice'])
        self.act(self.b, 'fund_withdraw', amount=200, rid='withdraw-001')
        self.assertEqual((self.wallet(self.b), self.label(self.b)['label']), (1200, 'Rút từ quỹ chung'))
        self.assertIn('rút 200 xu', self.view(self.a)['me']['notice'])
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.b, 'fund_withdraw', amount=301, rid='withdraw-002')
        self.assertEqual(e.exception.code, 'fund_low')
        self.assertEqual(self.home(self.b)['fund']['daily_left'], 300)
        self.act(self.a, 'fund_withdraw', amount=250, rid='withdraw-003')           # both spouses share the balance
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'fund_withdraw', amount=51, rid='withdraw-004')
        self.assertEqual(e.exception.code, 'fund_low')
        self.clock.t += DAY + 1
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'fund_withdraw', amount=60, rid='withdraw-005')
        self.assertEqual(e.exception.code, 'fund_low')                              # 50 left
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'fund_deposit', amount=5000, rid='deposit-0002')
        self.assertEqual(e.exception.code, 'not_enough')
        hist = self.home(self.a)['fund']['history']
        self.assertEqual([(h['who'], h['kind'], h['amount'], h['balance']) for h in hist],
                         [('An', 'withdraw', 250, 50), ('Binh', 'withdraw', 200, 300), ('An', 'deposit', 500, 500)])
        self.assertEqual(self.home(self.a)['fund']['balance'], 50)

    def test_divorce_splits_the_fund_and_settles_debts_from_it(self):
        self.act(self.a, 'fund_deposit', amount=301, rid='deposit-0001')
        self.act(self.a, 'send', amount=100, loan=True, rid='loan-00001')          # Bình owes An 100
        self.act(self.a, 'send', amount=400, loan=True, rid='loan-00002')          # ... and 400 more (separate debt)
        wa, wb = self.wallet(self.a), self.wallet(self.b)
        self.act(self.a, 'divorce', confirm='LY HON')
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
        # 301 → 150 An, 151 Bình (did not file); Bình's 151 pays the first debt (100) then 51 of the second
        self.assertEqual(self.wallet(self.a), wa + 150 + 151)
        self.assertEqual(self.wallet(self.b), wb)
        debts = {d['amount']: d for d in self.view(self.a)['home']['debts']}
        self.assertEqual((debts[100]['status'], debts[100]['repaid']), ('settled', 100))
        self.assertEqual((debts[400]['status'], debts[400]['repaid']), ('cleared', 51))
        self.assertEqual(self.view(self.b)['home']['debts'][0]['lender'], False)       # still visible to both after the divorce
        self.assertEqual(self.row('SELECT balance FROM joint_funds WHERE couple=?', self.cid)['balance'], 0)
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'fund_deposit', amount=10, rid='deposit-0003')

    def test_account_deletion_leaves_the_fund_to_the_partner(self):
        self.act(self.a, 'fund_deposit', amount=300, rid='deposit-0001')
        wb = self.wallet(self.b)
        mr.forget(self.store, self.a)
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertEqual(self.wallet(self.b), wb + 300)


class TransferTests(CoupleBase):
    def test_send_is_applied_once(self):
        for _ in range(3):
            self.act(self.a, 'send', amount=50, note='ngon', rid='send-000001')
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (950, 1050))
        self.assertEqual(self.label(self.b)['label'], 'An gửi: Mua gì ngon đi em')
        self.assertEqual(self.row("SELECT COUNT(*) n FROM marriage_effects WHERE id LIKE 'recv:%'")['n'], 1)
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'send', amount=50, note='free text', rid='send-000002')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'send', amount=2000, rid='send-000003')
        self.assertEqual(e.exception.code, 'not_enough')

    def test_help_request_accept_decline_expire(self):
        self.act(self.b, 'help_ask', amount=80, note='an')
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'help_ask', amount=10)
        req = self.home(self.a)['requests'][0]
        self.assertEqual((req['mine'], req['amount'], req['note']), (False, 80, 'Cho xin tiền ăn trưa'))
        self.assertGreaterEqual(mr.alerts(self.store, self.sid(self.a))['alerts'], 1)
        self.act(self.a, 'help_answer', id=req['id'], answer='accept', rid='help-answer-1')
        self.act(self.a, 'help_answer', id=req['id'], answer='accept', rid='help-answer-1')   # replay
        self.act(self.a, 'help_answer', id=req['id'], answer='accept', rid='help-answer-2')   # a second tap
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'help_answer', id=req['id'], answer='decline')
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (920, 1080))
        self.act(self.b, 'help_ask', amount=30, loan=True)
        rid = self.home(self.a)['requests'][0]['id']
        self.act(self.a, 'help_answer', id=rid, answer='decline')
        self.assertEqual(self.home(self.a)['requests'], [])
        self.act(self.b, 'help_ask', amount=30)
        self.clock.t += cp.HELP_DAYS * DAY + 1
        self.assertEqual(self.home(self.a)['requests'], [])
        self.act(self.b, 'help_ask', amount=30)                                     # the old one expired

    def test_ious_claim_later_repay_forgive(self):
        self.act(self.a, 'send', amount=100, loan=True, note='von', rid='loan-00001')
        d = self.home(self.a)['debts'][0]
        self.assertEqual((d['lender'], d['who'], d['left'], d['can_claim']), (True, 'Binh', 100, True))
        self.act(self.a, 'claim', debt=d['id'], line='tien_dau')
        self.assertIn('Tiền đâu', self.view(self.b)['me']['notice'])
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'claim', debt=d['id'], line='nhe')
        self.assertEqual(e.exception.code, 'rate_limited')
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'claim', debt=d['id'], line='nhe')                     # only the lender
        self.act(self.b, 'later', debt=d['id'], line='luong')
        self.assertIn('xin khất', self.view(self.a)['me']['notice'])
        self.assertEqual(self.home(self.a)['debts'][0]['claim']['status'], 'later')
        self.act(self.b, 'repay', debt=d['id'], amount=30, rid='repay-00001')
        self.assertEqual(self.home(self.b)['debts'][0]['left'], 70)
        with self.assertRaises(mr.MarriageError):
            self.act(self.b, 'repay', debt=d['id'], amount=71, rid='repay-00002')
        for _ in range(2):
            self.act(self.b, 'repay', debt=d['id'], amount=70, rid='repay-00003')
        self.assertEqual(self.home(self.a)['debts'][0]['status'], 'paid')
        self.assertEqual((self.wallet(self.a), self.wallet(self.b)), (1000, 1000))
        self.assertEqual(self.label(self.b)['label'], 'Trả nợ An')
        self.act(self.b, 'send', amount=40, loan=True, rid='loan-00002')
        d2 = [x for x in self.home(self.b)['debts'] if x['status'] == 'open'][0]
        self.act(self.b, 'forgive', debt=d2['id'])
        self.assertEqual([x['status'] for x in self.home(self.a)['debts']], ['forgiven', 'paid'])


class MomentTests(CoupleBase):
    def test_once_a_day_happiness_and_streak(self):
        self.act(self.a, 'interact', kind='chao')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'interact', kind='chao')
        self.assertEqual(e.exception.code, 'once_a_day')
        self.act(self.b, 'interact', kind='chao')                                  # each spouse has their own
        self.assertEqual(self.home(self.a)['happy']['points'], 2)
        self.assertIn('Chào buổi sáng', self.view(self.b)['me']['notice'])
        self.assertEqual(self.home(self.b)['moments'][1]['new'], True)
        self.assertGreaterEqual(mr.alerts(self.store, self.sid(self.b))['alerts'], 1)
        self.act(self.b, 'moments_seen')
        self.assertFalse(any(m['new'] for m in self.home(self.b)['moments']))
        w = self.wallet(self.a)
        self.act(self.a, 'interact', kind='com')
        self.assertEqual((self.wallet(self.a), self.label(self.a)['label']), (w - cp.LUNCH_COST, 'Mang cơm trưa cho Binh'))
        for kind in ('nho', 'met', 'om', 'hon'):
            self.act(self.a, 'interact', kind=kind)
        self.assertEqual(self.home(self.a)['happy']['points'], cp.HAPPY_DAY_MAX)    # at most 6 a day from moments
        self.assertEqual(sorted(self.home(self.a)['done_today']), sorted(['chao', 'com', 'nho', 'met', 'om', 'hon']))
        self.clock.t += DAY
        self.act(self.a, 'interact', kind='chao')                                  # day 2: +1 and streak bonus +1
        h = self.home(self.a)['happy']
        self.assertEqual((h['points'], h['streak']), (cp.HAPPY_DAY_MAX + 2, 2))
        self.clock.t += 3 * DAY
        self.assertEqual(self.home(self.a)['happy']['streak'], 0)
        self.act(self.a, 'interact', kind='chao')
        self.assertEqual(self.home(self.a)['happy']['points'], cp.HAPPY_DAY_MAX + 3)

    def test_gift_from_the_bag(self):
        mr._mutate(self.store, {self.sid(self.a): lambda s: s['journey']['closeness']['bag'].update(xoai=1)})
        with self.assertRaises(mr.MarriageError):
            self.act(self.a, 'interact', kind='qua', item='banh_bo')
        self.act(self.a, 'interact', kind='qua', item='xoai')
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertNotIn('xoai', self.state(self.a)['journey']['closeness']['bag'])
        self.assertEqual(self.state(self.b)['journey']['closeness']['bag'].get('xoai'), 1)
        validate_state(self.state(self.b))

    def test_anniversary_gift_once(self):
        self.act(self.a, 'interact', kind='chao')
        wed = self.state(self.a)['marriage']['spouse']['wed']
        mr._mutate(self.store, {self.sid(self.a): lambda s: s['journey'].__setitem__('life_day', wed + cp.ANNIV_DAYS)})
        w = self.wallet(self.a)
        for _ in range(3):
            mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(self.wallet(self.a), w + 5)
        self.assertIn('Quà kỷ niệm 30 ngày', self.label(self.a)['label'])
        self.assertIn('kỷ niệm', self.view(self.a)['me']['notice'])


class BankHelperTests(CoupleBase):
    def test_joint_account_and_spend(self):
        self.act(self.a, 'fund_deposit', amount=400, rid='deposit-0001')
        acc = cp.joint_account(self.state(self.a))
        self.assertEqual((acc['id'], acc['balance'], acc['daily_left']), (self.cid, 400, 400))
        self.assertEqual([m['me'] for m in acc['members']], [True, False])
        self.assertIsNone(cp.joint_account(migrate_state(new_state(), owned=True)))
        # a command that lands: spent once whatever the retries
        for _ in range(2):
            mr._mutate(self.store, {self.sid(self.a): lambda s: cp.joint_spend(s, 120, 'Mua tủ lạnh', 'card-1')})
        self.assertEqual(cp.joint_account(self.state(self.a))['balance'], 280)
        self.clock.t += cp.HOLD_S + 1
        mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(self.row("SELECT status FROM joint_ledger WHERE ref LIKE '%card-1'")['status'], 'done')
        # a command that never saved: refunded on the next load
        s = self.state(self.a)
        cp.joint_spend(s, 50, 'Mua quạt', 'card-2')
        self.assertEqual(cp.joint_account(self.state(self.a))['balance'], 230)
        self.clock.t += cp.HOLD_S + 1
        mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(cp.joint_account(self.state(self.a))['balance'], 280)
        with self.assertRaises(GameError) as e:
            cp.joint_spend(s, 50, 'Mua quạt', 'card-2')
        self.assertEqual(e.exception.code, 'expired')
        # actual balance protects card spends; not married / malformed reference
        with self.assertRaises(GameError) as e:
            cp.joint_spend(self.state(self.a), 281, 'Mua xe', 'card-3')
        self.assertEqual(e.exception.code, 'fund_low')
        with self.assertRaises(GameError) as e:
            cp.joint_spend(migrate_state(new_state(), owned=True), 5, 'x', 'card-4')
        self.assertEqual(e.exception.code, 'no_joint')
        with self.assertRaises(GameError):
            cp.joint_spend(self.state(self.a), 5, 'x', 'bad ref!')

    def test_old_married_save_gets_its_couple_link(self):
        def unlink(s):
            for k in ('couple', 'side'):
                s['marriage']['spouse'].pop(k)
        mr._mutate(self.store, {self.sid(self.b): unlink})
        self.assertIsNone(cp.joint_account(self.state(self.b)))
        mr.on_load(self.store, self.b, self.state(self.b))
        self.assertEqual(self.state(self.b)['marriage']['spouse']['side'], 'b')
        self.assertIsNotNone(cp.joint_account(self.state(self.b)))


class RingColorTests(Base):
    def test_buy_with_colours_and_prices(self):
        a = self.user('an', 5000)
        from game import wedding_content as W
        self.act(a, 'ring_buy', tier='bac', metal='vang', rid='ring-color-1')              # silver ring in gold: +20
        self.act(a, 'ring_buy', tier='kim_cuong', metal='vang_hong', stone='ruby', rid='ring-color-2')   # cheaper colours never discount
        self.act(a, 'ring_buy', tier='ruby', rid='ring-color-3')                            # the tier's own colours
        rings = {r['tier']: r for r in self.view(a)['rings']}
        self.assertEqual((rings['bac']['price'], rings['bac']['metal'], rings['bac']['stone']), (W.RING_INDEX['bac']['price'] + 20, 'vang', None))
        self.assertEqual((rings['kim_cuong']['price'], rings['kim_cuong']['stone_name']), (W.RING_INDEX['kim_cuong']['price'], 'Ruby đỏ'))
        self.assertEqual((rings['ruby']['metal'], rings['ruby']['stone']), ('vang', 'ruby'))
        self.assertTrue(rings['ruby']['colors']['stone'].startswith('#'))
        self.assertEqual(self.wallet(a), 5000 - 70 - 900 - 480)
        for bad in (dict(tier='bac', stone='ruby'), dict(tier='ruby', stone='kim_cuong_xanh'), dict(tier='bac', metal='dong'), dict(tier='ruby', stone=None)):
            with self.assertRaises(mr.MarriageError) as e:
                self.act(a, 'ring_buy', **bad)
            self.assertEqual(e.exception.code, 'bad_color', bad)
        cat = self.view(a, catalog=True)['catalog']
        self.assertEqual(len(cat['metals']), 4)
        self.assertEqual(len(cat['stones']), 6)
        self.assertEqual({r['id']: r['stones'] for r in cat['rings']}['kim_cuong'], True)

    def test_recolour_at_the_jeweller(self):
        a, b = self.user('an', 2000), self.user('binh', 2000)
        rid = self.ring(a, 'ruby')
        w = self.wallet(a)
        self.act(a, 'ring_recolor', ring=rid, metal='bach_kim', stone='sapphire', rid='recolor-0001')
        self.act(a, 'ring_recolor', ring=rid, metal='bach_kim', stone='sapphire', rid='recolor-0001')   # replay
        self.assertEqual(self.wallet(a), w - (20 + 40 + 20))
        self.assertIn('Tiệm kim hoàn', self.label_of(a))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'ring_recolor', ring=rid, metal='bach_kim', stone='sapphire', rid='recolor-0002')
        self.assertEqual(e.exception.code, 'same_color')
        with self.assertRaises(mr.MarriageError):
            self.act(b, 'ring_recolor', ring=rid, metal='bac', stone='ruby')                # not Bình's ring
        self.act(a, 'propose', code=self.code(b), ring=rid, message='hem')
        incoming = self.view(b)['incoming'][0]['ring']
        self.assertEqual((incoming['metal'], incoming['stone']), ('bach_kim', 'sapphire'))
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'ring_recolor', ring=rid, metal='vang', stone='ruby')               # in a proposal
        self.act(b, 'respond', id=self.view(b)['incoming'][0]['id'], answer='accept')
        self.assertEqual(self.view(b)['couple']['ring']['stone'], 'sapphire')
        self.act(b, 'ring_recolor', ring=rid, metal='vang_hong', stone='sapphire')           # the one who wears it
        self.assertEqual(self.view(a)['couple']['ring']['metal'], 'vang_hong')
        self.assertIn('tiệm kim hoàn', self.view(a)['me']['notice'])

    def label_of(self, tok):
        return self.state(tok)['journey']['history'][-1]['label']

    def test_old_rings_get_their_tier_colours(self):
        a = self.user('an')
        rid = self.ring(a, 'vang_tay')
        self.store.transaction(lambda db: db.execute('ALTER TABLE marriage_rings DROP COLUMN stone'))
        self.store.transaction(lambda db: db.execute('ALTER TABLE marriage_rings DROP COLUMN metal'))
        mr.bind(self.store)
        r = self.view(a)['rings'][0]
        self.assertEqual((r['id'], r['metal'], r['stone'], r['metal_name']), (rid, 'vang', None, 'Vàng'))
        mr.bind(self.store)          # twice is fine


class SaveTests(unittest.TestCase):
    def test_validate_link_and_bag(self):
        s = migrate_state(new_state(), owned=True)
        mr._apply_effect(s, dict(id='eng:1:a', kind='status', amount=0, label='', data=json.dumps(dict(set='engaged', name='Binh', couple=4, side='a'))))
        mr._apply_effect(s, dict(id='wed:1:a', kind='status', amount=0, label='', data=json.dumps(dict(set='married', name='Binh', date='2026-09-29'))))
        self.assertEqual((s['marriage']['spouse']['couple'], s['marriage']['spouse']['side']), (4, 'a'))
        mr.validate_save(s)
        for bad in (dict(couple=4), dict(couple='4', side='a'), dict(couple=4, side='c')):
            sp = {k: v for k, v in s['marriage']['spouse'].items() if k not in ('couple', 'side')}
            with self.assertRaises(GameError):
                mr.validate_save(dict(s, marriage=dict(s['marriage'], spouse=dict(sp, **bad))))
        mr._apply_effect(s, dict(id='bag:1', kind='bag', amount=0, label='', data=json.dumps(dict(item='xoai'))))
        mr._apply_effect(s, dict(id='bag:2', kind='bag', amount=0, label='', data=json.dumps(dict(item='<script>'))))
        self.assertEqual(s['journey']['closeness']['bag'], dict(xoai=1))
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
