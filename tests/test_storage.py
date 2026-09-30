import copy,concurrent.futures,tempfile,unittest
from pathlib import Path
from game.engine import GameError,new_state
from game.storage import Store,Conflict
from tests.helpers import Journey

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'game.db';self.store=Store(self.path);self.token,self.csrf,_=self.store.session()
    def tearDown(self):self.tmp.cleanup()
    def call(self,key='request-001',rev=0,career='mother_baby',action='start_day',payload=None):return self.store.command(self.token,key,rev,career,action,payload or {})
    def test_reload_persists(self):
        self.call();again=Store(self.path);s,rev,csrf=again.read(self.token);self.assertTrue(s['careers']['mother_baby']['open']);self.assertEqual(rev,1);self.assertEqual(csrf,self.csrf)
    def test_idempotency_same_id_same_action(self):
        a=self.call();b=self.call();self.assertEqual(a['revision'],b['revision']);self.assertTrue(b['replayed']);self.assertEqual(a['state'],b['state'])
    def test_idempotency_same_id_other_action_conflicts(self):
        self.call()
        with self.assertRaises(Conflict):self.call(rev=1,action='advance')
    def test_revision_conflict_and_no_lost_update(self):
        self.call()
        with self.assertRaises(Conflict):self.call(key='request-002')
        self.assertEqual(self.store.read(self.token)[1],1)
    def test_new_session_isolated(self):
        self.call();token,_,_=self.store.session();self.assertNotEqual(token,self.token);self.assertFalse(self.store.read(token)[0]['careers']['mother_baby']['open'])
    def test_invalid_command_rolls_back_revision(self):
        with self.assertRaises(GameError):self.call(action='buy_upgrade',payload={'item':'unknown'})
        self.assertEqual(self.store.read(self.token)[1],0)
    def test_export_import_roundtrip(self):
        j=Journey();j.solve();r=self.call(action='import_save',payload={'save':{'format':'mot-ngay-lam-nghe/save-v1','state':j.state}});self.assertEqual(r['state']['careers']['mother_baby']['money'],400)
    def test_invalid_save_no_partial_replacement(self):
        self.call();old=self.store.read(self.token);bad=new_state();bad['careers']['mother_baby']['stock']['bunny']=-3
        with self.assertRaises(GameError):self.call('import-0001',1,action='import_save',payload={'save':{'format':'mot-ngay-lam-nghe/save-v1','state':bad}})
        self.assertEqual(self.store.read(self.token),old)
    def test_incomplete_task_or_edited_truth_rejected(self):
        for edit in ('missing','edited','group'):
            j=Journey('accounting');bad=j.state
            if edit=='missing':del bad['careers']['accounting']['tasks'][0]['source_ready']
            elif edit=='edited':bad['careers']['accounting']['tasks'][0]['docs'][0]['original']=999
            else:bad['careers']['accounting']['tasks'][0]['groups']=[{'docs':['FAKE'],'transactions':['GD-01'],'total':3}]
            with self.assertRaises(GameError):self.call(action='import_save',payload={'save':{'format':'mot-ngay-lam-nghe/save-v1','state':bad}})
    def test_malformed_collections_are_clean_errors(self):
        for bad_value in (None,[],{'oops':True}):
            bad=new_state();bad['careers']['mother_baby']['tasks']=[bad_value]
            with self.assertRaises(GameError):self.call(action='import_save',payload={'save':{'format':'mot-ngay-lam-nghe/save-v1','state':bad}})
    def test_two_concurrent_tabs_one_revision_wins(self):
        def run(i):
            try:return self.call(key=f'parallel-{i:03d}')['revision']
            except Conflict:return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
        self.assertCountEqual(results,[1,'conflict']);self.assertEqual(self.store.read(self.token)[1],1)
    def test_concurrent_duplicate_replayed_not_repeated(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:self.call(),range(4)))
        self.assertEqual(sum(not r['replayed'] for r in results),1);self.assertEqual(self.store.read(self.token)[1],1)
