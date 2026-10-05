import concurrent.futures
import http.client
import json
import threading
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from game import business, operations as ops, workplace_business as wb
from game.storage import Store
from game.engine import validate_state
from tests.helpers import Journey


class BusinessStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'business';self.store=Store(self.path)
        self.token,_,_=self.store.session()
        j=Journey('accounting');self.start=2000000000
        with patch('game.business.time.time',return_value=self.start):
            ops.action(j.state,j.c,'accounting','ops_hire',{'candidate':'accounting-staff-1','confirm':True})
        self.at=min(p['at'] for p in j.c['ops']['business']['pending'].values())
        self.before=copy.deepcopy(j.state);validate_state(j.state)
        self.store.command(self.token,'import-business',0,None,'import_save',{'save':{'format':'mot-ngay-lam-nghe/save-v4','state':j.state}})

    def tearDown(self):self.store.close_pool();self.tmp.cleanup()

    def test_concurrent_sync_and_retry_pay_one_order(self):
        with patch('game.business.time.time',return_value=self.at):
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda i:self.store.command(self.token,'business-sync-'+str(i),None,None,business.ACTION,{},internal=True),range(4)))
            again=self.store.command(self.token,'business-sync-0',None,None,business.ACTION,{},internal=True)
        s,_,_=self.store.read(self.token);c=s['careers']['accounting'];b=c['ops']['business']
        self.assertEqual(b['served'],1);self.assertTrue(again['replayed'])
        row=b['recent'][0]
        before=self.before['careers']['accounting']
        # Private shops also receive the existing 40% positive-margin bonus.
        bonus,carry=divmod(before['ops']['business_profit']['carry']+max(0,row['net'])*40,100)
        self.assertEqual(c['ops']['business_profit']['recent'][row['id']],bonus)
        self.assertEqual(c['ops']['business_profit']['total'],before['ops']['business_profit']['total']+bonus)
        self.assertEqual(c['ops']['business_profit']['carry'],carry)
        self.assertEqual(c['money'],before['money']+row['revenue']-row['cash_expenses']+bonus)
        validate_state(s)

    def test_restart_offline_cursor_and_read_projection(self):
        self.store.close_pool();self.store=Store(self.path)
        s,_,_=self.store.read(self.token)
        with patch('game.business.time.time',return_value=self.at):
            self.assertTrue(business.on_load(self.store,self.token,s))
            s,rev,_=self.store.read(self.token)
            self.assertFalse(business.on_load(self.store,self.token,s))
        self.assertEqual(s['careers']['accounting']['ops']['business']['served'],1)
        self.assertEqual(self.store.read(self.token)[1],rev)

    def test_http_state_and_bootstrap_settle_before_returning_view(self):
        from server import GameServer
        server=GameServer(('127.0.0.1',0),self.store)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('game.business.time.time',return_value=self.at):
                for route in ('/api/state','/api/bootstrap?lite=1'):
                    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                    with patch.object(self.store,'read',wraps=self.store.read) as reads:
                        conn.request('GET',route,headers={'Cookie':'mnl_session='+self.token})
                        response=conn.getresponse();body=json.loads(response.read());conn.close()
                        if route=='/api/state':self.assertEqual(reads.call_count,1)
                    self.assertEqual(response.status,200,body)
                    self.assertEqual(body['state']['careers']['accounting']['ops']['business']['served'],1)
        finally:server.shutdown();server.server_close();thread.join()
