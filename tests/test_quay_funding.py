import copy
import json
import threading
from unittest.mock import patch
from tests.test_quay_hire import Base
from game import quay_hire as qh, live_effects as lfx
from game import marriage as mr, couple as cp

class Funding(Base):
    def _continuous_staffed(self, tok, at, fund=1000):
        from game import quay as qy, quay_business as qb
        self.open_stall(tok)
        def prepare(s):
            st=s['journey']['quay']['stalls'][0]
            candidate=qy.candidates(s,st)[0]
            st['staff']=[dict(id=candidate['id'],name=candidate['name'],wage=candidate['ask'],ask=candidate['ask'],mo=60,d=0,g=candidate['g'])]
            st.pop('business',None)
            st['fund']=fund;st['till']=0
            qb.initialize(s,st,now=at)
            st['fund']=fund;st['till']=0
            st['business']['stock']={'ts_tran_chau':100,'hong_tra':100,'tra_dao':100}
        mr._mutate(self.store,{self.sid(tok):prepare})

    def test_stall_escrow_debit_first_settles_work_inside_authoritative_callback(self):
        from game import quay_business as qb
        at=1800000000
        with patch('game.quay_business.time.time',return_value=at):
            boss=self.user('escrow_clock');self._continuous_staffed(boss,at)
        expected=copy.deepcopy(self.state(boss))
        qb.settle(expected,now=at+600)
        target=expected['journey']['quay']['stalls'][0]
        before=target['fund']+target['till']
        with patch('game.quay_business.time.time',return_value=at+600):
            self.post(boss,wage=30)
        actual=self.stall(boss)
        self.assertEqual(actual['business'],target['business'])
        self.assertEqual(actual['fund']+actual['till'],before-30)

    def test_stall_cancel_refund_cannot_backpay_bankrupt_interval(self):
        from game import quay_business as qb
        at=1800000000
        with patch('game.quay_business.time.time',return_value=at):
            boss=self.user('refund_clock');self._continuous_staffed(boss,at)
            job=self.post(boss,wage=30)
        def empty(s):
            st=s['journey']['quay']['stalls'][0]
            st['fund']=st['till']=0
        mr._mutate(self.store,{self.sid(boss):empty})
        with patch('game.quay_business.time.time',return_value=at+3600):
            self.act(boss,'cancel',id=job['id'])
        after=self.state(boss)
        qb.settle(after,now=at+3600)
        st=after['journey']['quay']['stalls'][0]
        self.assertEqual(st['business']['sold'],0)
        self.assertEqual(st['fund']+st['till'],30)
        self.assertEqual(st['business']['cursor'],(at+3600)*1000)

    def test_paid_shift_transports_escrow_wage_and_source_once(self):
        boss,worker=self.user('boss'),self.user('worker');st=self.open_stall(boss)
        self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='paid-ledger-0001')
        job=self.view(boss)['mine'][0]
        self.act(worker,'accept',id=job['id']);self.work(worker,tasks=3);self.act(worker,'flush')
        effect=self.effects(self.sid(boss))[0];data=json.loads(effect['data'])
        self.assertEqual((data['wage'],data['source']),(30,'cash'))
        before=self.wallet(boss);self.owner_load(boss)
        receipt=self.state(boss)['journey']['quay']['receipts'][-1]
        self.assertEqual(receipt['rev'],effect['amount'])
        self.assertEqual(receipt['net'],effect['amount']-30)
        self.assertEqual((receipt['wage'],receipt['source']),(30,'cash'))
        self.assertEqual(self.wallet(boss),before)
        once=copy.deepcopy(self.state(boss));self.owner_load(boss)
        self.assertEqual(self.state(boss),once)

    def test_suspended_counter_cannot_reserve_a_wage(self):
        boss=self.user('boss');st=self.open_stall(boss)
        def suspend(s):
            s['journey']['quay']['stalls'][0]['economy']['paused']=True
        mr._mutate(self.store,{self.sid(boss):suspend})
        before=copy.deepcopy(self.state(boss))
        with self.assertRaises(qh.QuayError) as caught:
            self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='paused-hire-0001')
        self.assertEqual(caught.exception.code,'closed')
        self.assertEqual(self.state(boss),before)
        self.assertEqual(self.view(boss)['mine'],[])

    def test_account_escrow_retry_cancel_refunds_same_account(self):
        boss=self.user('boss');st=self.open_stall(boss)
        self.cmd(boss,'jr_bk_open');self.cmd(boss,'jr_bk_deposit',amount=100)
        before=self.state(boss);body=dict(stall=st['id'],wage=30,src='account',rid='account-hire-0001')
        first=self.act(boss,'post',**body);again=self.act(boss,'post',**body)
        self.assertFalse(again['changed'])
        self.assertEqual(self.state(boss)['journey']['bank']['balance'],70)
        self.assertEqual(self.stall(boss)['fund'],st['fund'])
        job=self.view(boss)['mine'][0]
        self.assertEqual(job['source'],'account')
        self.act(boss,'cancel',id=job['id']);self.owner_load(boss);self.owner_load(boss)
        self.assertEqual(self.state(boss)['journey']['bank']['balance'],100)
        self.assertEqual(self.wallet(boss),before['journey']['wallet'])

    def test_insufficient_or_credit_funding_and_changed_request_are_rejected(self):
        boss=self.user('boss');st=self.open_stall(boss)
        self.cmd(boss,'jr_bk_open')
        before=copy.deepcopy(self.state(boss))
        for src in ('account','card','typo'):
            with self.subTest(src=src),self.assertRaises(qh.QuayError):
                self.act(boss,'post',stall=st['id'],wage=30,src=src,rid='invalid-hire-0001')
            self.assertEqual(self.state(boss),before)
        self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='cash-hire-0001')
        with self.assertRaises(qh.QuayError):
            self.act(boss,'post',stall=st['id'],wage=31,src='cash',rid='cash-hire-0001')

    def test_cash_expiry_refunds_once(self):
        boss=self.user('boss');st=self.open_stall(boss);before=self.wallet(boss)
        self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='cash-expiry-0001')
        job=self.view(boss)['mine'][0]
        self.store.transaction(lambda db:db.execute('UPDATE quay_jobs SET until=0 WHERE id=?',(job['id'],)))
        qh._swept[0]=0;qh.sweep(self.store)
        self.owner_load(boss);self.owner_load(boss)
        self.assertEqual(self.wallet(boss),before)

    def test_concurrent_duplicate_cash_post_holds_once(self):
        boss=self.user('boss');st=self.open_stall(boss);before=self.wallet(boss)
        errors=[];results=[]
        def run():
            try:results.append(self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='race-post-0001'))
            except Exception as x:errors.append(x)
        threads=[threading.Thread(target=run) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(20)
        self.assertFalse(errors,errors)
        self.assertEqual(sorted(x['changed'] for x in results),[False,True])
        self.assertEqual(self.wallet(boss),before-30)

    def test_account_worker_quit_returns_account_not_counter(self):
        boss,worker=self.user('boss'),self.user('worker');st=self.open_stall(boss)
        self.cmd(boss,'jr_bk_open');self.cmd(boss,'jr_bk_deposit',amount=100)
        self.act(boss,'post',stall=st['id'],wage=30,src='account',rid='quit-post-0001')
        job=self.view(boss)['mine'][0];self.act(worker,'accept',id=job['id']);self.act(worker,'quit')
        self.owner_load(boss);self.owner_load(boss)
        self.assertEqual(self.state(boss)['journey']['bank']['balance'],100)
        self.assertEqual(self.stall(boss)['fund'],st['fund'])

    def test_invitation_decline_after_unfriend_returns_wallet(self):
        boss,worker=self.user('boss'),self.user('worker');st=self.open_stall(boss)
        mr.ensure_person(self.store,self.sid(worker))
        with self.store.connect() as db:code=db.execute('SELECT code FROM marriage_people WHERE sid=?',(self.sid(worker),)).fetchone()['code']
        self.store.transaction(lambda db:db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)',(self.sid(boss),self.sid(worker),mr.now())))
        before=self.wallet(boss)
        self.act(boss,'post',stall=st['id'],wage=30,src='cash',rid='decline-post-0001',to=code)
        job=self.view(boss)['mine'][0]
        self.store.transaction(lambda db:db.execute('DELETE FROM friends WHERE sid=?',(self.sid(boss),)))
        self.act(worker,'decline',id=job['id']);self.owner_load(boss);self.owner_load(boss)
        self.assertEqual(self.wallet(boss),before)

    def joint(self,boss,partner):
        def insert(db):
            cid=db.execute("INSERT INTO couples(a,b,status,since,married_at) VALUES(?,?,'married',?,?) RETURNING id",(self.sid(boss),self.sid(partner),mr.now(),mr.now())).fetchone()[0]
            for token in (boss,partner):db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)',(self.sid(token),cid))
            db.execute('INSERT INTO joint_funds(couple,balance,updated) VALUES(?,100,?)',(cid,mr.now()))
            return cid
        cid=self.store.transaction(insert)
        for token,side in ((boss,'a'),(partner,'b')):
            mr._mutate(self.store,{self.sid(token):lambda s,side=side:mr._apply_effect(s,mr._effect('test-joint-'+side,self.sid(token),'status',data=dict(set='married',couple=cid,side=side,name='Partner',date='2026-10-04')))})
        return cid

    def test_joint_escrow_cancel_and_closed_marriage_fallback(self):
        boss,partner=self.user('boss'),self.user('partner');st=self.open_stall(boss);cid=self.joint(boss,partner)
        before=self.wallet(boss)
        for i,closed in enumerate((False,True)):
            self.act(boss,'post',stall=st['id'],wage=30,src='joint',rid=f'joint-post-{i:04d}')
            with self.store.connect() as db:self.assertEqual(cp._balance(db,cid),70)
            job=next(x for x in self.view(boss)['mine'] if x['status']=='open')
            if closed:self.store.transaction(lambda db:db.execute("UPDATE couples SET status='divorced' WHERE id=?",(cid,)))
            self.act(boss,'cancel',id=job['id']);self.owner_load(boss);self.owner_load(boss)
            with self.store.connect() as db:self.assertEqual(cp._balance(db,cid),70 if closed else 100)
            self.assertEqual(self.wallet(boss),before+(30 if closed else 0))

    def test_joint_insufficient_rolls_back_job_and_save(self):
        boss,partner=self.user('boss'),self.user('partner');st=self.open_stall(boss);cid=self.joint(boss,partner)
        self.store.transaction(lambda db:db.execute('UPDATE joint_funds SET balance=1 WHERE couple=?',(cid,)))
        before=copy.deepcopy(self.state(boss))
        with self.assertRaises(mr.MarriageError):self.act(boss,'post',stall=st['id'],wage=30,src='joint',rid='joint-short-0001')
        self.assertEqual(self.state(boss),before)
        self.assertEqual(self.view(boss)['mine'],[])

    def test_full_joint_refund_waits_without_blocking_other_expiry(self):
        boss,partner=self.user('boss'),self.user('partner');st=self.open_stall(boss);cid=self.joint(boss,partner)
        self.act(boss,'post',stall=st['id'],wage=30,src='joint',rid='joint-full-0001')
        job=self.view(boss)['mine'][0]
        self.store.transaction(lambda db:db.execute('UPDATE joint_funds SET balance=? WHERE couple=?',(cp.FUND_MAX,cid)))
        before=self.wallet(boss)
        result=self.act(boss,'cancel',id=job['id'])
        self.assertTrue(result['changed']);self.assertEqual(self.row(job['id'])['status'],'cancelled')
        self.assertTrue(self.view(boss)['mine'][0]['refund_pending'])
        other=self.user('other');other_st=self.open_stall(other);wallet=self.wallet(other)
        self.act(other,'post',stall=other_st['id'],wage=30,src='cash',rid='cash-full-0001')
        other_job=self.view(other)['mine'][0]
        self.store.transaction(lambda db:db.execute('UPDATE quay_jobs SET until=0 WHERE id=?',(other_job['id'],)))
        qh.sweep(self.store,force=True);self.owner_load(other)
        self.assertEqual(self.wallet(other),wallet)
        self.assertEqual(self.wallet(boss),before)
        self.store.transaction(lambda db:db.execute('UPDATE joint_funds SET balance=balance-100 WHERE couple=?',(cid,)))
        qh.sweep(self.store,force=True);qh.sweep(self.store,force=True)
        with self.store.connect() as db:self.assertEqual(cp._balance(db,cid),cp.FUND_MAX-70)
        self.assertFalse(self.view(boss)['mine'][0]['refund_pending'])

    def test_pending_joint_refund_falls_back_once_when_original_marriage_closes(self):
        boss,partner=self.user('boss'),self.user('partner');st=self.open_stall(boss);cid=self.joint(boss,partner)
        self.act(boss,'post',stall=st['id'],wage=30,src='joint',rid='joint-close-0001')
        job=self.view(boss)['mine'][0];before=self.wallet(boss)
        self.store.transaction(lambda db:db.execute('UPDATE joint_funds SET balance=? WHERE couple=?',(cp.FUND_MAX,cid)))
        self.act(boss,'cancel',id=job['id'])
        self.store.transaction(lambda db:db.execute("UPDATE couples SET status='divorced' WHERE id=?",(cid,)))
        qh.sweep(self.store,force=True);qh.sweep(self.store,force=True)
        self.owner_load(boss);self.owner_load(boss)
        self.assertEqual(self.wallet(boss),before+30)

    def test_pg_schema_includes_additive_funding_metadata(self):
        from game import pg_schema
        from tests.pg_support import columns
        with self.store.connect() as db:
            self.assertEqual(columns(db,'quay_funding'),{'job','owner','rid','fingerprint','source','couple'})
        self.assertIn('quay_funding',pg_schema.TABLE)
