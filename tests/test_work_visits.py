import copy
import json
from types import SimpleNamespace
from unittest.mock import patch
from tests.test_quay_hire import Base
from game import marriage as mr, social


class WorkVisits(Base):
    def setUp(self):
        super().setUp()
        from game import work_visits as w
        self.w=w
        self.bridge=SimpleNamespace(
            offers=lambda s,c:[dict(offer_id='offer-'+c,digest='digest-'+c,price=25,label='Dịch vụ '+c,career=c)],
            accept=lambda s,c,o:'task-'+o['id'],
            transitions=lambda before,after,career,action,result:result.get('service_events',[]))
        bridge_patch=patch.object(w,'_bridge',return_value=self.bridge)
        bridge_patch.start();self.addCleanup(bridge_patch.stop)

    def user(self, name, **kwargs):
        tok=super().user(name, **kwargs)
        self.cmd(tok, 'select_career', career='milk_tea')
        self.cmd(tok, 'start_day', career='milk_tea')
        return tok

    def api_get(self,tok,sub,**query):
        return self.w.get(self.store,tok,self.state(tok),sub,query)

    def api_post(self,tok,sub,**data):
        return self.w.post(self.store,tok,self.state(tok),sub,data)

    def mine(self,tok):
        return self.api_get(tok,'places',scope='mine')['places']

    def make_public(self,tok):
        place=next(p for p in self.mine(tok) if p['target']=='milk_tea' and p['kind']=='career')
        self.api_post(tok,'visibility',place=place['id'],visibility='public')
        return self.api_get(tok,'place',place=place['id'])['place']

    def test_default_friends_privacy_all_careers_and_no_sensitive_projection(self):
        owner=self.user('visit_owner');buyer=self.user('visit_buyer')
        places=self.mine(owner)
        self.assertEqual(len([p for p in places if p['kind']=='career']),1)
        self.assertTrue(all(p['visibility']=='friends' for p in places))
        self.assertEqual(self.api_get(buyer,'places',scope='public')['places'],[])
        raw=json.dumps(places,ensure_ascii=False)
        self.assertNotIn(self.sid(owner),raw)
        self.assertNotIn('wallet',raw)
        self.assertNotIn('answer',raw)

    def test_empty_order_poll_does_not_read_or_rebuild_the_players_save(self):
        owner=self.user('idle_visit_owner')
        with patch.object(mr,'_read_state',side_effect=AssertionError('Polling an empty inbox must not load a save')):
            result=self.w.get(self.store,owner,None,'orders',{})
        self.assertEqual(result,dict(incoming=[],outgoing=[]))

    def test_idle_place_visit_reads_provider_save_once_and_refreshes_snapshot(self):
        owner=self.user('visit_read_once')
        place=self.make_public(owner)
        mr._mutate(self.store,{self.sid(owner):lambda s:s['careers']['milk_tea'].update(open=False)})
        with patch.object(mr,'_read_state',wraps=mr._read_state) as read:
            result=self.w.get(self.store,owner,None,'place',{'place':place['id']})
        self.assertEqual(result['place']['activity']['status'],'resting')
        self.assertEqual(read.call_count,1)

    def test_offline_place_visit_uses_snapshot_from_committed_work(self):
        from game import operations,workplace_business as wb
        owner=self.user('visit_settle_once')
        place=self.make_public(owner)
        at=2000000000
        with patch('time.time',return_value=at):
            def hire(s):
                c=s['careers']['accounting'];c['started']=True
                operations.action(s,c,'accounting','ops_hire',{'candidate':'accounting-staff-1','confirm':True})
                wb.settle(s)
            mr._mutate(self.store,{self.sid(owner):hire})
        before=self.state(owner)['careers']['accounting']['ops']['business']['served']
        with patch('time.time',return_value=at+1000),patch.object(self.w,'sync',wraps=self.w.sync) as sync,patch.object(mr,'_read_state',wraps=mr._read_state) as read:
            result=self.w.get(self.store,owner,None,'place',{'place':place['id']})
        self.assertEqual(result['place']['id'],place['id'])
        self.assertGreater(self.state(owner)['careers']['accounting']['ops']['business']['served'],before)
        self.assertEqual(sync.call_count,1)
        self.assertEqual(read.call_count,1)

    def test_order_escrow_idempotent_cancel_refund_exactly_once(self):
        owner=self.user('seller');buyer=self.user('customer')
        place=self.make_public(owner);wallet=self.wallet(buyer)
        body=dict(place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='visit-order-0001',note='Xin cảm ơn')
        first=self.api_post(buyer,'order',**body)['order']
        again=self.api_post(buyer,'order',**body)['order']
        self.assertEqual(first['id'],again['id'])
        self.assertEqual(self.wallet(buyer),wallet-first['price'])
        self.api_post(buyer,'cancel',order=first['id'])
        self.api_post(buyer,'receive')
        self.api_post(buyer,'receive')
        self.assertEqual(self.wallet(buyer),wallet)

    def test_only_actual_completed_order_pays_and_can_review(self):
        owner=self.user('provider');buyer=self.user('purchaser')
        place=self.make_public(owner)
        order=self.api_post(buyer,'order',place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='visit-paid-0001')['order']
        self.api_post(owner,'accept',order=order['id'])
        before=self.state(owner)['careers']['milk_tea']['money']
        self.api_post(owner,'receive')
        self.assertEqual(self.state(owner)['careers']['milk_tea']['money'],before)
        with self.assertRaises(self.w.WorkVisitError):
            self.api_post(buyer,'review',order=order['id'],stars=5,tags=['friendly'],comment='Tốt')
        state=self.state(owner)
        self.store.transaction(lambda db:self.w.command_commit(db,self.sid(owner),state,state,'milk_tea','task_action',{'service_events':[{'id':order['id'],'status':'completed'}]}))
        self.api_post(owner,'receive')
        self.api_post(owner,'receive')
        self.assertEqual(self.state(owner)['careers']['milk_tea']['money'],before+order['price'])
        self.api_post(buyer,'review',order=order['id'],stars=5,tags=['friendly'],comment='Tốt')
        self.api_post(owner,'reply',order=order['id'],text='Cảm ơn bạn')
        rows=self.api_get(buyer,'place',place=place['id'])['reviews']
        self.assertEqual((len(rows),rows[0]['stars'],rows[0]['reply']),(1,5,'Cảm ơn bạn'))

    def test_either_block_direction_hides_and_prevents_new_order(self):
        owner=self.user('blocked_owner');buyer=self.user('blocked_buyer')
        place=self.make_public(owner)
        self.store.transaction(lambda db:db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)',(self.sid(owner),self.sid(buyer),1)))
        self.assertEqual(self.api_get(buyer,'places',scope='public')['places'],[])
        with self.assertRaises(self.w.WorkVisitError):
            self.api_post(buyer,'order',place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='blocked-order-1')

    def test_imported_completion_cancels_and_refunds_instead_of_paying(self):
        owner=self.user('import_owner');buyer=self.user('import_buyer')
        place=self.make_public(owner);cash=self.wallet(buyer)
        order=self.api_post(buyer,'order',place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='import-order-01')['order']
        self.api_post(owner,'accept',order=order['id'])
        state=self.state(owner)
        self.store.transaction(lambda db:self.w.command_commit(db,self.sid(owner),state,state,'milk_tea','import',{'service_events':[{'id':order['id'],'status':'completed'}]}))
        self.api_post(buyer,'receive')
        self.assertEqual(self.wallet(buyer),cash)
    def test_changed_confirmed_price_rejected_without_debit(self):
        owner=self.user('quote_owner');buyer=self.user('quote_buyer')
        place=self.make_public(owner);cash=self.wallet(buyer)
        with self.assertRaises(self.w.WorkVisitError) as error:
            self.api_post(buyer,'order',place=place['id'],offer_id=place['offers'][0]['offer_id'],expected_price=26,rid='stale-quote-001')
        self.assertEqual(error.exception.code,'quote_changed')
        self.assertEqual(self.wallet(buyer),cash)

    def test_provider_deleted_refunds_customer_and_hides_place(self):
        owner=self.user('delete_owner');buyer=self.user('delete_buyer')
        place=self.make_public(owner);cash=self.wallet(buyer)
        order=self.api_post(buyer,'order',place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='delete-order-1')['order']
        self.store.transaction(lambda db:self.w.forget(db,self.sid(owner)))
        self.api_post(buyer,'receive')
        self.assertEqual(self.wallet(buyer),cash)
        self.assertEqual(self.api_get(buyer,'places',scope='public')['places'],[])

    def test_simultaneous_same_request_only_debits_once(self):
        import concurrent.futures
        owner=self.user('race_owner');buyer=self.user('race_buyer',wallet=25)
        # Starting day 12 can trigger a seeded life incident. Fund the race after
        # that setup so both concurrent requests really compete for one purchase.
        mr._mutate(self.store,{self.sid(buyer):lambda s:s['journey'].update(wallet=25)})
        place=self.make_public(owner);cash=self.wallet(buyer)
        self.assertEqual(cash,25)
        body=dict(place=place['id'],offer_id=place['offers'][0]['offer_id'],rid='same-race-0001')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(lambda _:self.api_post(buyer,'order',**body),range(2)))
        self.assertEqual(rows[0]['order']['id'],rows[1]['order']['id'])
        self.assertEqual(self.wallet(buyer),cash-25)

    def test_real_staff_order_autotakes_offline_completes_and_pays_once(self):
        from game import player_service_tasks as pst,operations,workplace_business as wb
        owner=self.user('staff_owner');buyer=self.user('staff_buyer')
        at=2000000000
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=at):
            def hire(s):
                c=s['careers']['milk_tea']
                operations.action(s,c,'milk_tea','ops_hire',{'candidate':'milk_tea-staff-1','confirm':True})
                wb.settle(s)
            mr._mutate(self.store,{self.sid(owner):hire})
            place=self.make_public(owner)
            offer=next(o for o in place['offers'] if o.get('staffed'))
            cash=self.state(owner)['careers']['milk_tea']['money'];buyer_cash=self.wallet(buyer)
            order=self.api_post(buyer,'order',place=place['id'],offer_id=offer['offer_id'],expected_price=offer['price'],rid='real-staff-0001')['order']
            self.assertEqual(order['status'],'accepted')
            state=self.state(owner);c=state['careers']['milk_tea'];job=c['player_service_jobs'][0]
            self.assertLess(c['money'],cash)
            beforepay=c['money'];bonus=max(0,offer['price']-job['wage']-job['materials']-job['goods'])*40//100
            self.assertEqual(self.wallet(buyer),buyer_cash-offer['price'])
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=job['due_at']):
            rows=self.api_get(buyer,'orders')['outgoing']
            self.assertEqual(rows[0]['status'],'completed')
            self.assertEqual(self.state(owner)['careers']['milk_tea']['money'],beforepay+offer['price']+bonus)
            self.api_post(buyer,'receive')
            self.assertEqual(self.state(owner)['careers']['milk_tea']['money'],beforepay+offer['price']+bonus)

    def test_actual_minigame_store_commit_is_only_payment_proof(self):
        from game import player_service_tasks as pst
        from tests.helpers import Journey
        owner=self.user('manual_owner');buyer=self.user('manual_buyer')
        self.cmd(owner,'select_career',career='mother_baby',confirm=True)
        self.cmd(owner,'start_day',career='mother_baby')
        with patch.object(self.w,'_bridge',return_value=pst):
            place=next(p for p in self.mine(owner) if p['target']=='mother_baby')
            self.api_post(owner,'visibility',place=place['id'],visibility='public')
            offer=place['offers'][0]
            order=self.api_post(buyer,'order',place=place['id'],offer_id=offer['offer_id'],rid='real-manual-001')['order']
            accepted=self.api_post(owner,'accept',order=order['id'])
            before=self.state(owner)['careers']['mother_baby']['money']
            j=Journey.__new__(Journey);j.career='mother_baby';j.state=self.state(owner)
            def act(action,**payload):
                result=self.cmd(owner,action,career='mother_baby',**payload)
                j.state=self.state(owner)
                return result
            j.act=act
            j.solve(accepted['task_id'])
            self.assertEqual(j.get(accepted['task_id'])['status'],'completed')
            afterwork=j.c['money']
            self.assertLessEqual(afterwork,before)
            rows=self.api_get(buyer,'orders')['outgoing']
            self.assertEqual(rows[0]['status'],'completed')
            self.assertEqual(self.state(owner)['careers']['mother_baby']['money'],afterwork+order['price'])
    def test_actual_minigame_commit_under_locked_fallback(self):
        with patch('game.storage.OPTIMISTIC_TRIES',0):
            self.test_actual_minigame_store_commit_is_only_payment_proof()

    def test_social_block_reverse_direction_and_closed_place(self):
        owner=self.user('social_owner');buyer=self.user('social_buyer')
        place=self.make_public(owner)
        self.store.transaction(lambda db:db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)',(social.pid_of(self.sid(buyer)),social.pid_of(self.sid(owner)),1)))
        self.assertEqual(self.api_get(buyer,'places',scope='public')['places'],[])
        with self.assertRaises(self.w.WorkVisitError):
            self.api_get(buyer,'place',place=place['id'])
        self.api_post(owner,'visibility',place=place['id'],visibility='closed')
        self.assertEqual(self.api_get(owner,'place',place=place['id'])['place']['visibility'],'closed')

    def test_real_quay_staff_fulfills_reserved_stock_and_receipt(self):
        from game import player_service_tasks as pst,quay_business as qb
        from tests.test_quay_business import fixture
        owner=self.user('quayvisit_owner');buyer=self.user('quayvisit_buyer')
        at=2000000000
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=at):
            source,stall=fixture();qb.settle(source,now=at)
            mr._mutate(self.store,{self.sid(owner):lambda s:s['journey'].update(quay=copy.deepcopy(source['journey']['quay']))})
            place=next(p for p in self.mine(owner) if p['kind']=='quay')
            self.api_post(owner,'visibility',place=place['id'],visibility='public')
            offer=place['offers'][0]
            stock=self.state(owner)['journey']['quay']['stalls'][0]['business']['stock'][offer['dish']]
            order=self.api_post(buyer,'order',place=place['id'],offer_id=offer['offer_id'],expected_price=offer['price'],rid='real-quay-0001')['order']
            self.assertEqual(order['status'],'accepted')
            self.assertTrue(order['staffed'])
            st=self.state(owner)['journey']['quay']['stalls'][0]
            self.assertEqual(st['business']['stock'][offer['dish']],stock-1)
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=at+1000):
            import concurrent.futures
            self.w._advance_provider(self.store,self.sid(owner))
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda tok:self.api_post(tok,'receive'),[owner,buyer]))
            rows=self.api_get(buyer,'orders')['outgoing']
            self.assertEqual(rows[0]['status'],'completed')
            st=self.state(owner)['journey']['quay']['stalls'][0]
            self.assertTrue(next(r for r in st['business']['visitor_orders'] if r['id']==order['id'])['settled'])
            before=st['till']+st['fund'];sold=st['business']['sold']
            self.api_post(buyer,'receive')
            st=self.state(owner)['journey']['quay']['stalls'][0]
            self.assertEqual(st['till']+st['fund'],before)
            self.assertEqual(st['business']['sold'],sold)
    def test_friend_code_resolves_private_friend_workplace(self):
        owner=self.user('friend_owner');buyer=self.user('friend_buyer')
        place=self.mine(owner)[0]
        self.assertTrue(place['owner']['code'])
        self.assertEqual(self.api_get(buyer,'places',owner=place['owner']['code'])['places'],[])
        self.store.transaction(lambda db:db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)',(self.sid(buyer),self.sid(owner),1)))
        rows=self.api_get(buyer,'places',owner=place['owner']['code'])['places']
        self.assertEqual([r['id'] for r in rows],[place['id']])
    def _accepted_staff_order(self, suffix):
        from game import player_service_tasks as pst,operations,workplace_business as wb
        owner=self.user('staff_'+suffix);buyer=self.user('buyer_'+suffix)
        def hire(s):
            c=s['careers']['milk_tea']
            operations.action(s,c,'milk_tea','ops_hire',{'candidate':'milk_tea-staff-1','confirm':True})
            wb.settle(s)
        mr._mutate(self.store,{self.sid(owner):hire})
        place=self.make_public(owner);offer=next(o for o in place['offers'] if o.get('staffed'))
        order=self.api_post(buyer,'order',place=place['id'],offer_id=offer['offer_id'],rid='staff-order-'+suffix)['order']
        return owner,buyer,order,self.state(owner)['careers']['milk_tea']['player_service_jobs'][0]

    def test_repeated_import_cannot_restore_refunded_staff_binding(self):
        from game import player_service_tasks as pst
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=2000000000):
            owner,buyer,order,job=self._accepted_staff_order('restore')
            backup=copy.deepcopy(self.state(owner));cash=self.wallet(buyer)
            for _ in range(2):
                self.cmd(owner,'import_save',save={'format':'mot-ngay-lam-nghe/save-v4','state':copy.deepcopy(backup)})
                self.api_post(buyer,'receive')
                self.assertFalse(self.state(owner)['careers']['milk_tea'].get('player_service_jobs'))
            self.assertEqual(self.wallet(buyer),cash+order['price'])

    def test_deleted_customer_keeps_accepted_escrow_for_actual_staff_service(self):
        from game import player_service_tasks as pst
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=2000000000):
            owner,buyer,order,job=self._accepted_staff_order('deleted')
            self.store.delete(buyer)
            cash=self.state(owner)['careers']['milk_tea']['money']
        with patch.object(self.w,'_bridge',return_value=pst),patch('time.time',return_value=job['due_at']):
            self.api_post(owner,'receive')
            c=self.state(owner)['careers']['milk_tea']
            bonus=max(0,order['price']-job['wage']-job['materials']-job['goods'])*40//100
            self.assertEqual(c['money'],cash+order['price']+bonus)
            self.assertTrue(c['player_service_jobs'][0]['settled'])
