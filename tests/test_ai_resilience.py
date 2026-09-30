"""The LLM never breaks a request: a slow, rate-limited or broken provider falls back to
the scripted line, and the concurrency gate is always given back."""
import http.client
import io
import os
import threading
import unittest
import urllib.error
from unittest import mock

from game import ai, dialogue

ENV = {'LLM_BASE_URL': 'http://localhost:9/v1', 'LLM_MODEL': 'mock', 'LLM_API_KEY': 'k'}
MSGS = [dict(role='user', content='hi')]


class ProviderFailures(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, ENV)
        self.env.start()
        self.gate = ai._gate
        ai._gate = threading.BoundedSemaphore(1)

    def tearDown(self):
        ai._gate = self.gate
        self.env.stop()

    def assert_fallback(self, error):
        with mock.patch('urllib.request.urlopen', side_effect=error):
            self.assertEqual(ai.chat(MSGS), (None, 'unavailable'))
        self.assertTrue(ai._gate.acquire(blocking=False), 'gate not released')
        ai._gate.release()

    def test_rate_limited(self):
        self.assert_fallback(urllib.error.HTTPError('http://x', 429, 'Too Many Requests', {}, io.BytesIO(b'{}')))

    def test_timeout(self):
        self.assert_fallback(TimeoutError('timed out'))

    def test_connection_dropped_mid_answer(self):
        self.assert_fallback(http.client.IncompleteRead(b'{"choi'))

    def test_garbage_status_line(self):
        self.assert_fallback(http.client.BadStatusLine('HTTP/0.9 ???'))

    def test_busy_gate_answers_at_once(self):
        self.assertTrue(ai._gate.acquire(blocking=False))
        try:
            with mock.patch('urllib.request.urlopen') as call:
                self.assertEqual(ai.chat(MSGS), (None, 'busy'))
                call.assert_not_called()
        finally:
            ai._gate.release()


class RephraseFailures(unittest.TestCase):
    def test_dropped_connection_keeps_the_canonical_line(self):
        state = dict(careers={}, settings=dict(aiConsent=True))
        npc = next(iter(dialogue.NPC_INDEX))
        career = dialogue.NPC_INDEX[npc]['career_id']
        state['careers'][career] = dict(chats={npc: [dict(role='user', text='chào'), dict(role='npc', text='Chào con.')]})
        with mock.patch.dict(os.environ, ENV), \
                mock.patch('urllib.request.urlopen', side_effect=http.client.IncompleteRead(b'')):
            out = dialogue.rephrase(state, career, npc)
        self.assertEqual((out['mode'], out['text'], out['reason']), ('scripted', 'Chào con.', 'unavailable'))


if __name__ == '__main__':
    unittest.main()
