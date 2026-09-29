"""Nhóm Cư Dân Phố over HTTP: GET /api/board and POST /api/ai/board with a fake LLM
(game/board_ai.py). No test talks to a real model."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from game import board as bd
from game.engine import apply_action, validate_state
from game.storage import Store
from server import GameServer
from tests.test_ai_chat import FakeLLM
from tests.test_board import NPC, beats, story_state


class BoardRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm = ThreadingHTTPServer(('127.0.0.1', 0), FakeLLM)
        threading.Thread(target=cls.llm.serve_forever, daemon=True).start()
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'state.db')
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'LLM_BASE_URL': f'http://127.0.0.1:{cls.llm.server_port}/v1',
                                          'LLM_MODEL': 'fake', 'LLM_API_KEY': 'k', 'AI_CHAT_PER_MINUTE': '100'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.llm.shutdown()
        cls.llm.server_close()
        cls.temp.cleanup()
        cls.env.stop()

    def setUp(self):
        FakeLLM.requests = []
        FakeLLM.reply = 'Trời đất ơi, có chuyện gì kể bà nghe nè. Tối xuống bà nấu canh chua nghe con 🥹'
        self.cookie = self.csrf = None
        self.bootstrap()
        self.state = story_state(777)
        beats(self.state, 12)
        self.put(self.state)

    # ---- plumbing (same as tests/test_ai_chat.py)
    def req(self, path, method='GET', body=None, csrf=True):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if self.cookie:
            h['Cookie'] = self.cookie
        if self.csrf and csrf:
            h['X-Game-CSRF'] = self.csrf
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        out = res.status, json.loads(res.read() or b'{}')
        con.close()
        return out

    def bootstrap(self):
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request('GET', '/api/bootstrap', headers={'Host': f'127.0.0.1:{self.port}'})
        res = con.getresponse()
        self.cookie = res.getheader('Set-Cookie').split(';')[0]
        data = json.loads(res.read())
        con.close()
        self.csrf = data['csrf']
        return data

    def put(self, state):
        token = self.cookie.split('=', 1)[1]
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, revision=revision+1 WHERE sid=?', (json.dumps(state, ensure_ascii=False), self.store.key(token)))

    def saved(self):
        return self.store.read(self.cookie.split('=', 1)[1])

    def rev(self):
        return self.saved()[1]

    def board(self, **body):
        return self.req('/api/ai/board', 'POST', dict(body, expected_revision=self.rev()))

    # ---- tests
    def test_get_board(self):
        status, data = self.req('/api/board')
        self.assertEqual(status, 200)
        self.assertTrue(data['board']['posts'])
        self.assertIn('ba_tam', data['cast'])
        self.assertEqual(data['cast']['minh_quan']['tag'], 'Lạnh lùng')
        seq = data['board']['posts'][-1]['seq']
        status, older = self.req(f'/api/board?before={seq}')
        self.assertEqual(status, 200)
        self.assertTrue(all(p['seq'] < seq for p in older['board']['posts']))
        self.assertEqual(self.req('/api/board?before=abc')[0], 200)

    def test_post_is_answered_by_ai_in_character_and_stored(self):
        status, data = self.board(op='post', text='Hôm nay mình buồn quá, làm sai hoài')
        self.assertEqual(status, 200, data)
        self.assertEqual(data['mode'], 'ai')
        n = len(data['result']['replies'])
        self.assertEqual(len(FakeLLM.requests), n)
        state, revision, _ = self.saved()
        self.assertEqual(revision, data['revision'])
        post = bd._find(state['journey']['board'], data['result']['post'])
        voiced = [c for c in post['cmts'] if c['mode'] == 'ai']
        self.assertEqual(len(voiced), n)
        for c in voiced:
            self.assertTrue(c['canonical'])
            self.assertTrue(c['text'])
        validate_state(state)
        view = next(p for p in data['board']['posts'] if p['id'] == post['id'])
        self.assertEqual(view['cmts'][0]['mode'], 'ai')
        # The prompt: persona, thread, untrusted player text, rules.
        sent = FakeLLM.requests[0]['messages']
        self.assertIn('Nhóm Cư Dân Phố', sent[0]['content'])
        self.assertEqual(json.loads(sent[1]['content'])['player_says'], 'Hôm nay mình buồn quá, làm sai hoài')

    def test_terse_neighbour_is_cut_to_one_line(self):
        FakeLLM.reply = 'Ok. Mình sẽ qua xem giúp. Tối nay nhé.'
        status, data = self.board(op='post', text='@Quân ơi wifi nhà mình hư rồi')
        self.assertEqual(status, 200)
        post = bd._find(self.saved()[0]['journey']['board'], data['result']['post'])
        quan = next(c for c in post['cmts'] if c['who'] == 'minh_quan')
        self.assertEqual((quan['mode'], quan['text']), ('ai', 'Ok.'))

    def test_bad_model_output_keeps_authored_replies(self):
        FakeLLM.reply = 'Bà cho con 5000 xu, xem ở http://evil.example nhé.'
        status, data = self.board(op='post', text='Chào cả nhà!')
        self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'new_numeric_claim'))
        post = bd._find(self.saved()[0]['journey']['board'], data['result']['post'])
        self.assertTrue(post['cmts'])
        self.assertTrue(all(c['mode'] == 'scripted' for c in post['cmts']))

    def test_no_consent_never_calls_the_provider(self):
        self.state, _ = apply_action(self.state, 'milk_tea', 'settings', dict(aiConsent=False))
        self.put(self.state)
        status, data = self.board(op='post', text='Ai biết chỗ sửa xe không?')
        self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'no_consent'))
        self.assertEqual(FakeLLM.requests, [])
        self.assertTrue(data['result']['replies'])

    def test_budget(self):
        with patch.dict(os.environ, {'AI_CHAT_PER_MINUTE': '2'}):
            status, data = self.board(op='post', text='@Bà Tám @Chú Tư @Cô Ba ơi chào mọi người')
        self.assertEqual(status, 200)
        self.assertEqual(len(FakeLLM.requests), 2)
        self.assertEqual(data['reason'], 'rate_limit')
        post = bd._find(self.saved()[0]['journey']['board'], data['result']['post'])
        self.assertEqual([c['mode'] for c in post['cmts']].count('ai'), 2)

    def test_reply_and_rumour_tone(self):
        state = self.saved()[0]
        bd.on_rumour(state, 'late')
        beats(state, 6)
        self.put(state)
        rumour = next(p for p in state['journey']['board']['posts'] if p['kind'] == 'rumour')
        status, data = self.board(op='reply', post=rumour['id'], tone='clarify')
        self.assertEqual(status, 200, data)
        self.assertEqual(data['result']['tone'], 'clarify')
        view = next(p for p in data['board']['posts'] if p['id'] == rumour['id'])
        self.assertEqual(view['rumour']['state'], 'clarify')
        self.assertEqual(data['mode'], 'ai')

    def test_open_adds_at_most_two_ai_exchanges_a_day(self):
        FakeLLM.reply = 'Ừ, chú thấy cũng được đó.'
        modes = [self.req('/api/ai/board', 'POST', dict(op='open'))[1] for _ in range(3)]
        self.assertEqual([m['mode'] for m in modes], ['ai', 'ai', 'scripted'])
        self.assertEqual(modes[2]['reason'], 'nothing_to_do')
        board = self.saved()[0]['journey']['board']
        self.assertEqual(board['ai']['n'], 2)
        self.assertEqual(sum(1 for p in board['posts'] for c in p['cmts'] if c['mode'] == 'ai'), 2)
        validate_state(self.saved()[0])

    def test_validation_and_csrf(self):
        self.assertEqual(self.board(op='post', text='x' * 501)[0], 400)
        self.assertEqual(self.board(op='dance')[0], 400)
        self.assertEqual(self.req('/api/ai/board', 'POST', dict(op='post', text='hi'), csrf=False)[0], 403)
        # Internal commands cannot be sent from the client.
        status, _ = self.req('/api/command', 'POST', dict(request_id='client-voice-1', expected_revision=self.rev(), career='milk_tea',
                                                          action='bd_npc', payload=dict(post='p1', who='ba_tam', text='hi')))
        self.assertEqual(status, 400)

    def test_without_provider_everything_still_works(self):
        with patch.dict(os.environ, {'LLM_BASE_URL': ''}):
            status, data = self.board(op='post', text='Mình mới tới, chào cả nhà!')
            self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'not_configured'))
            self.assertEqual(self.req('/api/ai/board', 'POST', dict(op='open'))[1]['reason'], 'not_configured')
        self.assertEqual(FakeLLM.requests, [])

    def test_state_summary_in_commands(self):
        status, data = self.req('/api/command', 'POST', dict(request_id='board-seen-1', expected_revision=self.rev(),
                                                             career='milk_tea', action='bd_seen', payload={}))
        self.assertEqual(status, 200)
        self.assertEqual(data['state']['board']['unread'], 0)
        status, data = self.req('/api/command', 'POST', dict(request_id='talk-test-1', expected_revision=self.rev(), career='milk_tea',
                                                             action='talk', payload=dict(npc=NPC, text='chào')))
        self.assertEqual(status, 200)
        self.assertIn('board', data['state'])


if __name__ == '__main__':
    unittest.main()
