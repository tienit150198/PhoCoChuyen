import copy
import os
import unittest
from unittest.mock import patch
from game import quay, quay_business as qb
from tests.test_quay import bare, owner, act


def legacy(places):
    s, st = bare('xe', 'milk_tea')
    s['journey']['quay'] = dict(v=1, seq=len(places), stalls=[], shift=None, out=[])
    for i, place in enumerate(places, 1):
        row = copy.deepcopy(st)
        row.update(id=f'q{i}', place=place)
        s['journey']['quay']['stalls'].append(row)
    return s


def grant(s, level):
    from game import business_progression as bp
    s['journey']['certificates'] = {gid: dict(score=100, best=100, earned_day=1, attempts=1)
                                  for gid in bp.CERTS[:level]}


class Policy(unittest.TestCase):
    def test_course_public_keeps_full_tuition_and_actual_retake_fee(self):
        from game import business_progression as bp, certificates
        s=legacy([]);grant(s,1)
        course=bp.evaluate(s,now=1000)['courses'][0]
        self.assertEqual(course['fee'],certificates.tuition('business_basics'))
        self.assertEqual(course['enrol_fee'],certificates.fee(s['journey'],'business_basics','class'))
        self.assertLess(course['enrol_fee'],course['fee'])

    def test_pure_requirement_counts_paused_and_third_upgrade(self):
        from game import business_progression as bp
        s=legacy([])
        self.assertTrue(bp.open_requirement(s,'xe')['allowed'])
        self.assertFalse(bp.open_requirement(s,'sap')['allowed'])
        s=legacy(['kiot','kiot','xe'])
        grant(s,2)
        self.assertEqual(bp.open_requirement(s,'kiot',replace_id='q3')['required_level'],3)
        self.assertFalse(bp.open_requirement(s,'kiot',replace_id='q3')['allowed'])
        s=legacy(['sap']*50);grant(s,1)
        self.assertTrue(bp.open_requirement(s,'sap')['allowed'])

    def test_owner_notice_once_no_generic_notice_and_exact_deadline(self):
        from game import business_progression as bp
        s=legacy(['kiot']*12)
        before=copy.deepcopy(s)
        self.assertEqual(bp.evaluate(s,now=1000)['status'],'not_required')
        self.assertEqual(s,before)
        qb.settle(s,now=1000)
        self.assertNotIn('business_license',quay.get(s))
        for st in quay.get(s)['stalls']:st['business']['paused']=True
        bp.owner_access(s,now=1000)
        deadline=1000+72*3600
        self.assertEqual(bp.evaluate(s,now=deadline-.001)['status'],'grace')
        self.assertEqual(bp.evaluate(s,now=deadline)['blocked_ids'],[f'q{i}' for i in range(10,13)]+[f'q{i}' for i in range(2,10)])
        bp.owner_access(s,now=deadline+99)
        self.assertEqual(bp.evaluate(s,now=deadline+99)['deadline'],deadline)
        self.assertTrue(all(st['business']['paused'] for st in quay.get(s)['stalls']))

    def test_entitlements_priority_and_legacy_fallback(self):
        from game import business_progression as bp
        s=legacy(['kiot']*3+['xe','sap']);bp.owner_access(s,now=1000)
        quay.get(s)['business_license']['preferred_ids']=['q3','q2','q1']
        self.assertEqual(bp.evaluate(s,now=300000)['allowed_ids'],['q4'])
        grant(s,1)
        self.assertEqual(bp.evaluate(s,now=300000)['allowed_ids'],['q4','q5'])
        grant(s,2)
        self.assertEqual(set(bp.evaluate(s,now=300000)['allowed_ids']),{'q2','q3','q4','q5'})
        grant(s,3)
        self.assertEqual(bp.evaluate(s,now=300000)['status'],'compliant')
        s=legacy([]);bp.snapshot(s)
        quay.get(s)['stalls']=legacy(['kiot']*3)['journey']['quay']['stalls']
        bp.owner_access(s,now=1000)
        self.assertEqual(bp.evaluate(s,now=300000)['allowed_ids'],[])

    def test_open_and_upgrade_reject_before_money(self):
        s=owner(wallet=100000)
        s['journey']['certificates']={}
        before=copy.deepcopy(s)
        from game.engine import GameError
        with self.assertRaises(GameError) as cm:act(s,'jr_quay_open',trade='milk_tea',place='sap',confirm=True)
        self.assertEqual(cm.exception.code,'business_license')
        self.assertEqual(s,before)
        s,_=act(s,'jr_quay_open',trade='milk_tea',place='xe',confirm=True)
        with self.assertRaises(GameError):act(s,'jr_quay_upgrade',stall='q1',place='kiot',confirm=True)

    def test_split_catchup_matches_frequent_polls_and_resume_without_backpay(self):
        from game import business_progression as bp
        s=legacy(['xe']*3);qb.settle(s,now=1000);bp.owner_access(s,now=1000)
        for st in quay.get(s)['stalls']:
            st['business']['stock']={d:100 for d in st['business']['arrivals']}
        deadline=1000+72*3600
        # Anchor a populated live ledger just before the cut-off.
        for st in quay.get(s)['stalls']:
            b=st['business'];b['cursor']=int((deadline-10)*1000)
            b['arrivals']={d:int((deadline-2)*1000) for d in b['arrivals']}
        other=copy.deepcopy(s)
        for at in [deadline-1,deadline,deadline+1,deadline+60]:qb.settle(s,now=at)
        qb.settle(other,now=deadline+60)
        self.assertEqual(s,other)
        blocked=quay.get(s)['stalls'][1]
        self.assertGreater(blocked['business']['sold'],0)
        self.assertEqual(qb.public(blocked)['status'],'restricted')
        frozen=copy.deepcopy(blocked['business']['expenses'])
        qb.settle(s,now=deadline+600)
        self.assertEqual(blocked['business']['expenses'],frozen)
        grant(s,1);bp.reconcile(s,now=deadline+600)
        sold=blocked['business']['sold'];qb.settle(s,now=deadline+600)
        self.assertEqual(blocked['business']['sold'],sold)
        self.assertFalse(blocked['business']['certificate_block'])


class Integration(unittest.TestCase):
    def test_priority_switch_preserves_orders_accepted_after_original_deadline(self):
        from game import business_progression as bp, quay_self as qs
        from tests.test_quay_owner_queue import OwnerQueue
        s,st=OwnerQueue().shop()
        q=quay.get(s);q['stalls'] += [dict(copy.deepcopy(st),id='q2'),dict(copy.deepcopy(st),id='q3')];q['seq']=3
        s['journey']['certificates']={};q.pop(bp.KEY,None)
        bp.owner_access(s,now=2000000000-bp.GRACE_SECONDS-60)
        qb.settle(s,now=2000000000)
        self.assertIn('cust',qs.run_view(s,st))
        with patch('game.business.time.time',return_value=2000000001):
            s,_=act(s,'jr_quay_license_keep',stalls=['q2'])
            st=quay.get(s)['stalls'][0]
            self.assertTrue(st['business']['certificate_block'])
            self.assertIn('cust',qs.run_view(s,st))
            c=qs.run_view(s,st)['cust']
            s,_=act(s,'jr_quay_serve',stall='q1',items=c['items'],change=c['pay']-c['total'],smile=True)
        self.assertNotIn('cust',qs.run_view(s,quay.get(s)['stalls'][0]))

    def test_deadline_excludes_exact_arrival_and_keeps_owner_queue(self):
        from game import business_progression as bp, quay_self as qs
        s=legacy(['xe']*3);qb.settle(s,now=1000);bp.owner_access(s,now=1000)
        deadline=1000+bp.GRACE_SECONDS
        st=quay.get(s)['stalls'][1];b=st['business']
        b['cursor']=int((deadline-1)*1000)
        b['arrivals']={d:int(deadline*1000) for d in b['arrivals']}
        qb.settle(s,now=deadline)
        self.assertEqual(b['sold'],0)
        self.assertFalse(bp.can_arrive(st,int(deadline*1000)))
        self.assertTrue(bp.can_arrive(st,int(deadline*1000)-1))

    def test_inspections_off_clears_only_policy_and_no_backpay(self):
        from game import business_progression as bp
        s=legacy(['xe']*3);qb.settle(s,now=1000);bp.owner_access(s,now=1000)
        qb.settle(s,now=300000)
        st=quay.get(s)['stalls'][1];st['business']['paused']=True
        frozen=copy.deepcopy(st['business']['expenses']);sold=st['business']['sold']
        with patch.dict(os.environ,{'MNL_BUSINESS_INSPECTIONS_OFF':'1'}):
            qb.settle(s,now=900000)
            self.assertFalse(st['business']['certificate_block'])
            self.assertTrue(st['business']['paused'])
            self.assertEqual(st['business']['expenses'],frozen)
            self.assertEqual(st['business']['sold'],sold)
            self.assertGreater(min(st['business']['arrivals'].values()),900000000)
        with patch.dict(os.environ,{'MNL_BUSINESS_LICENSES_OFF':'1'}):
            self.assertTrue(bp.open_requirement(s,'kiot')['allowed'])

    def test_pure_public_at_deadline_is_consistent_without_mutation(self):
        from game import business_progression as bp, work_visits
        s=legacy(['xe']*3);qb.settle(s,now=1000);bp.owner_access(s,now=1000)
        before=copy.deepcopy(s)
        with patch('game.business.time.time',return_value=300000):
            view=quay.public(s)
        self.assertTrue(view['stalls'][1]['license_blocked'])
        self.assertEqual(view['stalls'][1]['business']['status'],'restricted')
        self.assertEqual(s,before)

    def test_new_open_snapshots_before_append_and_issues_on_third_owner_action(self):
        from game import business_progression as bp
        s=owner(wallet=100000);s['journey']['certificates']={}
        with patch.dict(os.environ,{'MNL_BUSINESS_LICENSES_OFF':'1'}), patch('game.business.time.time',return_value=2000):
            for _ in range(3):s,_=act(s,'jr_quay_open',trade='milk_tea',place='kiot',confirm=True)
        case=quay.get(s)[bp.KEY]
        self.assertEqual(case['legacy_ids'],[])
        self.assertEqual(case['issued_at'],2000000)
        self.assertEqual(bp.evaluate(s,now=300000)['allowed_ids'],[])

    def test_same_code_flags_off_roundtrip_keeps_new_certificates(self):
        import json
        from game import business_progression as bp
        from game.engine import migrate_state, validate_state
        s=owner(wallet=100000)
        with patch('game.business.time.time',return_value=2000):
            s,_=act(s,'jr_quay_open',trade='milk_tea',place='kiot',confirm=True)
        certs=copy.deepcopy(s['journey']['certificates'])
        with patch.dict(os.environ,{'MNL_BUSINESS_LICENSES_OFF':'1','MNL_BUSINESS_INSPECTIONS_OFF':'1'}):
            restored=migrate_state(json.loads(json.dumps(s)))
            validate_state(restored)
            self.assertEqual(restored['journey']['certificates'],certs)
            self.assertFalse(bp.evaluate(restored)['enabled'])

    def test_selection_validation_and_no_new_privilege(self):
        from game import business_progression as bp
        from game.engine import GameError
        s=legacy(['kiot']*3);bp.owner_access(s,now=1000)
        for rows in [['q1','q1'],['missing'],[1]]:
            with self.assertRaises(GameError):bp.choose(s,{'stalls':rows})
        bp.choose(s,{'stalls':['q3']})
        self.assertEqual(bp.evaluate(s,now=300000)['allowed_ids'],['q3'])
        self.assertEqual(bp.evaluate(s,now=300000)['deadline'],260200)
        quay.get(s)['stalls']=[st for st in quay.get(s)['stalls'] if st['id']=='q3']
        self.assertEqual(bp.evaluate(s,now=300000)['status'],'compliant')
        self.assertEqual(bp.evaluate(s,now=300000)['deadline'],260200)

    def test_idle_owner_read_not_maintenance_delivers_notice(self):
        from game import business_progression as bp, business
        from unittest.mock import Mock
        s=legacy(['kiot']*3);qb.settle(s,now=1000)
        for st in quay.get(s)['stalls']:st['business']['paused']=True
        business.settle(s,now=1500)
        self.assertNotIn(bp.KEY,quay.get(s))
        store=Mock()
        with patch('game.business.time.time',return_value=2000):
            business.on_load_result(store,'token',s)
        store.command.assert_called_once()
        self.assertTrue(bp.owner_due(s,now=2000))
        bp.owner_access(s,now=2000)
        self.assertFalse(bp.owner_due(s,now=2001))

    def test_preaccepted_visitor_completes_only_direct_wages_after_cutoff(self):
        from game import business_progression as bp, player_service_tasks as ps
        from game.engine import GameError
        s=legacy(['xe']*3);qb.settle(s,now=1000);bp.owner_access(s,now=1000)
        deadline=1000+bp.GRACE_SECONDS
        for st in quay.get(s)['stalls']:
            st['business']['cursor']=int((deadline-1)*1000)
            st['business']['arrivals']={d:int((deadline+100)*1000) for d in st['business']['arrivals']}
        st=quay.get(s)['stalls'][1];dish=next(iter(st['business']['stock']))
        order=dict(id='wo-1234567890abcdef',buyer=dict(name='Bạn',code='friend',fc=''),note='',offer_id=dish,items=[dish],price=__import__('game.quay_self',fromlist=['price']).price(st,dish))
        ps.accept_visit(s,'q2',order,now=deadline-1)
        qb.settle(s,now=deadline)
        frozen={k:st['business']['expenses'][k] for k in ('rent','power','environment','protection')}
        qb.settle(s,now=deadline+60)
        self.assertEqual(st['business']['visitor_orders'][0]['status'],'completed')
        self.assertEqual({k:st['business']['expenses'][k] for k in frozen},frozen)
        self.assertEqual(qb.public(st)['status'],'restricted')
        self.assertFalse(qb.public(st)['running_cost']['accruing'])
        self.assertIsNone(qb.public(st)['income'])
        with self.assertRaises(GameError):ps.accept_visit(s,'q2',dict(order,id='wo-abcdef1234567890'),now=deadline+60)


    def test_preaccepted_owner_and_online_orders_finish_but_replacements_stop(self):
        from game import business_progression as bp, quay_self as qs
        from tests.test_quay_owner_queue import OwnerQueue
        from game.engine import GameError, validate_state, migrate_state
        s,st=OwnerQueue().shop()
        st['online']=True
        # Start a fresh online run, then model the legacy fleet before first notice.
        with patch('game.business.time.time',return_value=2000000000):
            s,_=act(s,'jr_quay_close',stall=st['id'])
            s,_=act(s,'jr_quay_start',stall=st['id'])
        st=quay.get(s)['stalls'][0]
        q=quay.get(s);q['stalls'] += [dict(copy.deepcopy(st),id='q2'),dict(copy.deepcopy(st),id='q3')];q['seq']=3
        s['journey']['certificates']={};q.pop(bp.KEY,None)
        bp.owner_access(s,now=2000000000-bp.GRACE_SECONDS+1)
        bp.choose(s,{'stalls':['q2']})
        deadline=2000000001
        # Owner's first customer is already present; online quote is also accepted.
        for o in st['run']['order_data'].values():o['available_at']=2000000000000
        qb.settle(s,now=deadline+60)
        self.assertTrue(st['business']['certificate_block'])
        c=qs.run_view(s,st)['cust']
        with patch('game.business.time.time',return_value=deadline+60):
            s,_=act(s,'jr_quay_serve',stall='q1',items=c['items'],change=c['pay']-c['total'],smile=True)
        st=quay.get(s)['stalls'][0]
        self.assertNotIn('cust',qs.run_view(s,st))
        o=next(iter(st['run']['order_data'].values()))
        qs._check_order(st,st['run'],o,{})
        qs._next_order(s,st,st['run'],0,int((deadline+60)*1000))
        with self.assertRaises(GameError):qs._check_order(st,st['run'],st['run']['order_data']['0'],{})
        validate_state(s);validate_state(migrate_state(copy.deepcopy(s)))

from tests.test_quay_hire import Base as HireBase

class HireRestriction(HireBase):
    def test_restricted_post_never_creates_job_or_escrow(self):
        from game import business_progression as bp, marriage as mr, quay_hire as qh
        from game.engine import GameError
        tok=self.user('licensed');self.open_stall(tok)
        def legacy_owner(s):
            q=quay.get(s);st=q['stalls'][0]
            q['stalls'] += [dict(copy.deepcopy(st),id='q2'),dict(copy.deepcopy(st),id='q3')];q['seq']=3
            s['journey']['certificates']={};q.pop(bp.KEY,None)
            bp.owner_access(s,now=qh.now()-bp.GRACE_SECONDS-1)
        mr._mutate(self.store,{self.sid(tok):legacy_owner})
        before=self.state(tok)
        with self.assertRaises(qh.QuayError):self.act(tok,'post',stall='q2',wage=30)
        after=self.state(tok)
        self.assertEqual(after,before)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM quay_jobs WHERE owner=?',(self.sid(tok),)).fetchone()[0],0)

if __name__=='__main__':unittest.main()


