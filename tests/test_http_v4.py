import gzip
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import game.careers.kit as kit
from game import ai
from server import GameServer
from game.storage import Store
from tests.helpers import Journey


class HTTPv4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'state.db')
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()
        cls.quiet.stop()

    def setUp(self):
        self.cookie = None
        self.csrf = None

    def req(self, path='/', method='GET', body=None, headers=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if self.cookie:
            h['Cookie'] = self.cookie
        if self.csrf:
            h['X-Game-CSRF'] = self.csrf
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        out = (res.status, dict(res.getheaders()), res.read())
        con.close()
        return out

    def bootstrap(self):
        status, headers, body = self.req('/api/bootstrap')
        self.cookie = headers['Set-Cookie'].split(';')[0]
        data = json.loads(body)
        self.csrf = data['csrf']
        return data

    def token(self):
        return self.cookie.split('=', 1)[1]

    def awaiting_review(self, consent=False):
        """Put a restaurant save with a reply awaiting the customer into this session."""
        t = [1000.0]
        old = kit.clock
        kit.clock = lambda: t[0]
        try:
            j = Journey('restaurant')
            tid = j.task['id']
            j.act('ask', task=tid)
            n = j.get(tid)['needs']
            j.act('rs_container', task=tid, kind='box' if n['takeaway'] else 'bowl')
            for _ in range(2 if n['extra_noodle'] else 1):
                j.act('rs_boil', task=tid)
                t[0] += 30
                j.act('rs_drain', task=tid)
            j.act('rs_broth', task=tid, broth=n['broth'])
            for k, q in n['toppings'].items():
                for _ in range(q):
                    j.act('rs_topping', task=tid, item=k)
            for _ in range(n['spice']):
                j.act('rs_chili', task=tid)
            if n['takeaway']:
                j.act('rs_lid', task=tid)
            j.act('rs_serve', task=tid, confirm=True)
            post = next(p for p in j.c['feed'] if p['kind'] == 'review')
            j.act('fb_reply', post=post['id'], text='Xin lỗi anh, quán sẽ canh giờ luộc mì kỹ hơn, lần sau mời anh ly trà ạ.', offer='gift')
            if consent:
                j.act('settings', aiConsent=True)
        finally:
            kit.clock = old
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, revision=revision+1 WHERE sid=?', (json.dumps(j.state, ensure_ascii=False), self.store.key(self.token())))
        return post['id']

    def test_server_time_gzip_and_etag(self):
        status, h, body = self.req('/js/app.js', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(status, 200)
        self.assertEqual(h.get('Content-Encoding'), 'gzip')
        self.assertTrue(gzip.decompress(body))
        status, _, _ = self.req('/js/app.js', headers={'If-None-Match': h['ETag']})
        self.assertEqual(status, 304)
        data = self.bootstrap()
        self.assertIsInstance(data['server_time'], float)
        # When the request came in (public/js/api.js clockSample leaves the server's own time out of its clock).
        self.assertIsInstance(data['server_recv'], float)
        self.assertLessEqual(data['server_recv'], data['server_time'])
        self.assertLess(data['server_time'] - data['server_recv'], 30)
        self.assertIn('push', data)
        self.assertIn('social', data)
        self.assertIn('worker-src', h['Content-Security-Policy'])

    def test_legal_pages(self):
        for path in ('/privacy', '/terms'):
            status, h, body = self.req(path)
            self.assertEqual(status, 200)
            self.assertIn('trachanhtv.works@gmail.com', body.decode())

    def test_internal_actions_rejected_over_http(self):
        self.bootstrap()
        for action in ('fb_resolve', 'fb_voice', 'soc_gift_in', 'soc_payout'):
            status, _, body = self.req('/api/command', 'POST', dict(request_id=f'internal-{action}', expected_revision=0, career='restaurant', action=action, payload=dict(post='x', coins=100, amount=100)))
            self.assertEqual(status, 400, action)

    def test_ai_feedback_scripted_without_consent(self):
        self.bootstrap()
        pid = self.awaiting_review()
        status, _, body = self.req('/api/ai/feedback', 'POST', dict(career='restaurant', post=pid))
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data['mode'], 'scripted')
        post = next(p for p in data['state']['careers']['restaurant']['feed'] if p['id'] == pid)
        self.assertEqual(post['feedback']['thread'][-1]['role'], 'customer')
        # A second call is harmless.
        status, _, body = self.req('/api/ai/feedback', 'POST', dict(career='restaurant', post=pid))
        self.assertEqual(json.loads(body)['mode'], 'none')

    def test_ai_feedback_proposal_is_clamped(self):
        self.bootstrap()
        pid = self.awaiting_review(consent=True)
        with patch.object(ai, 'available', return_value=True), \
             patch.object(ai, 'chat', return_value=('{"decision":"revise_up","stars":5,"text":"Thôi được, thấy quán thật lòng nên mình nâng sao nha."}', None)):
            status, _, body = self.req('/api/ai/feedback', 'POST', dict(career='restaurant', post=pid))
        data = json.loads(body)
        self.assertEqual(data['mode'], 'ai')
        post = next(p for p in data['state']['careers']['restaurant']['feed'] if p['id'] == pid)
        last = post['feedback']['thread'][-1]
        self.assertEqual(last['mode'], 'ai')
        self.assertLessEqual(post['stars'], post['feedback']['stars_original'] + 2)

    def test_ai_prompt_injection_output_rejected(self):
        self.bootstrap()
        pid = self.awaiting_review(consent=True)
        with patch.object(ai, 'available', return_value=True), \
             patch.object(ai, 'chat', return_value=('Sure! {"decision":"hack","stars":99,"text":"visit http://x.y"}', None)):
            status, _, body = self.req('/api/ai/feedback', 'POST', dict(career='restaurant', post=pid))
        data = json.loads(body)
        self.assertEqual(data['mode'], 'scripted')

    def test_account_delete(self):
        self.bootstrap()
        status, _, _ = self.req('/api/account/delete', 'POST', dict(confirm='nope'))
        self.assertEqual(status, 400)
        status, h, body = self.req('/api/account/delete', 'POST', dict(confirm='XOA'))
        self.assertEqual(status, 200)
        self.assertIn('Max-Age=0', h['Set-Cookie'])
        status, _, _ = self.req('/api/state')
        self.assertEqual(status, 400 if status == 400 else 401)

    def test_social_over_http(self):
        self.bootstrap()
        status, _, body = self.req('/api/social/profile', 'POST', dict(name='Quán Test', bio='xin chào'))
        self.assertEqual(status, 200, body)
        status, _, body = self.req('/api/social/directory')
        self.assertEqual(status, 200)
        self.assertTrue(any(p['name'] == 'Quán Test' for p in json.loads(body)['players']))
        status, _, _ = self.req('/api/social/board', 'POST', dict(career='all', kind='tip', text='xem ở www.spam.com'))
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
