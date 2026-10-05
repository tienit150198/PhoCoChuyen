import http.client,json,os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from server import GameServer
from game.storage import Store

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.server=GameServer(('127.0.0.1',0),Store(Path(cls.temp.name)/'state.db'))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.port=cls.server.server_port
        cls.quiet=patch.dict(os.environ,{'QUIET':'1'});cls.quiet.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup();cls.quiet.stop()
    def setUp(self):self.cookie=None;self.csrf=None
    def req(self,path='/',method='GET',body=None,headers=None):
        h={'Host':f'127.0.0.1:{self.port}'}
        if self.cookie:h['Cookie']=self.cookie
        if self.csrf:h['X-Game-CSRF']=self.csrf
        if body is not None:h['Content-Type']='application/json';body=body if isinstance(body,str) else json.dumps(body)
        h.update(headers or {});con=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10);con.request(method,path,body=body,headers=h);res=con.getresponse();data=res.read();out=(res.status,dict(res.getheaders()),data);con.close();return out
    def bootstrap(self):
        status,headers,body=self.req('/api/bootstrap');self.cookie=headers['Set-Cookie'].split(';')[0];data=json.loads(body);self.csrf=data['csrf'];return data
    def command(self,**extra):
        payload={'request_id':'http-test-001','expected_revision':0,'career':'mother_baby','action':'start_day','payload':{}};payload.update(extra);return self.req('/api/command','POST',payload)
    def test_static_index_and_modules(self):
        for path,expected in [('/','text/html'),('/js/app.js','text/javascript'),('/css/game.css','text/css'),('/favicon.svg','image/svg+xml')]:
            status,h,body=self.req(path);self.assertEqual(status,200);self.assertIn(expected,h['Content-Type']);self.assertTrue(body)
    def test_security_headers(self):
        _,h,_=self.req();self.assertEqual(h['X-Content-Type-Options'],'nosniff');self.assertIn("script-src 'self'",h['Content-Security-Policy']);self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
    def test_session_cookie_http_only(self):
        _,h,_=self.req('/api/bootstrap');self.assertIn('HttpOnly',h['Set-Cookie']);self.assertIn('SameSite=Strict',h['Set-Cookie'])
    def test_source_and_secret_paths_are_not_served(self):
        for path in ('/server.py','/.env','/storage/game.db','/../server.py','/%2e%2e/server.py','/reference/data/npcs_24.json'):
            self.assertEqual(self.req(path)[0],404)
    def test_host_validation(self):self.assertEqual(self.req(headers={'Host':'evil.example'})[0],403)
    def test_state_requires_session(self):self.assertEqual(self.req('/api/state')[0],401)
    def test_write_requires_csrf(self):
        self.bootstrap();self.csrf='wrong';self.assertEqual(self.command()[0],403)
    def test_cross_origin_rejected(self):
        self.bootstrap();self.assertEqual(self.req('/api/command','POST',{},headers={'Origin':'https://elsewhere.example'})[0],403)
    def test_same_origin_command(self):
        self.bootstrap();status,_,body=self.command();self.assertEqual(status,200);self.assertEqual(json.loads(body)['revision'],1)
    def test_stale_revision_returns_latest_state(self):
        self.bootstrap();self.command();status,_,body=self.command(request_id='http-test-002');d=json.loads(body);self.assertEqual(status,409);self.assertIn('state',d);self.assertEqual(d['revision'],1)
    def test_request_replay(self):
        self.bootstrap();self.command();status,_,body=self.command();self.assertEqual(status,200);self.assertTrue(json.loads(body)['replayed'])
    def test_json_structure_and_non_finite_numbers(self):
        self.bootstrap()
        for data in ('[1,2]','{"action":NaN}','{"action":'):
            self.assertEqual(self.req('/api/command','POST',data)[0],400)
    def test_non_json_rejected(self):
        self.bootstrap();self.assertEqual(self.req('/api/command','POST','{}',{'Content-Type':'text/plain'})[0],415)
    def test_keys_not_in_public_config(self):
        with patch.dict(os.environ,{'LLM_API_KEY':'secret-do-not-expose','LLM_BASE_URL':'https://private.example/v1','LLM_MODEL':'test'}):
            d=self.bootstrap();serialized=json.dumps(d);self.assertNotIn('secret-do-not-expose',serialized);self.assertNotIn('private.example',serialized);self.assertTrue(d['ai']['configured'])
    def test_save_export_contains_raw_envelope(self):
        self.bootstrap();self.command();status,h,body=self.req('/api/save/export');d=json.loads(body);self.assertEqual(status,200);self.assertEqual(d['format'],'mot-ngay-lam-nghe/save-v4');self.assertIsInstance(d['state']['careers']['mother_baby']['tasks'][0]['needs'],dict)
    def test_optional_ai_without_consent_falls_back(self):
        self.bootstrap();status,_,body=self.req('/api/ai/rephrase','POST',{'career':'mother_baby','npc':'mother_baby_npc_01'});self.assertEqual(status,200);self.assertEqual(json.loads(body)['mode'],'scripted')
