"""🛎️ Phố dịch vụ routing: /api/svc/* reads with a session (no save parsed but for 'mine'), writes CSRF-guarded with the
client's network passed on, refusals answered with their code; /api/admin/svc is admin only."""
import json
from unittest.mock import patch

from tests.test_http import HTTPTests


class ServiceMarketHTTP(HTTPTests):
    def test_reads_need_a_session_and_skip_the_save(self):
        for cookie in (None, 'mnl_session=invalid-session'):
            self.cookie = cookie
            self.assertEqual(self.req('/api/svc/dir')[0], 401)
            self.assertEqual(self.req('/api/svc/order', 'POST', {})[0], 401)
        self.cookie = None
        self.bootstrap()
        with patch.object(self.server.store, 'read', side_effect=AssertionError('No save needed')), \
                patch('game.service_market.get', return_value={'items': []}) as call:
            status, _, body = self.req('/api/svc/dir?career=milk_tea&sort=price')
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('dir', {'career': 'milk_tea', 'sort': 'price'}))
            self.assertIn('ip', call.call_args.kwargs)

    def test_writes_are_csrf_guarded_and_carry_the_network(self):
        self.bootstrap()
        with patch('game.service_market.post', return_value={'ok': True}) as call:
            status, _, body = self.req('/api/svc/offer', 'POST', {'pid': 'x', 'price': 5})
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('offer', {'pid': 'x', 'price': 5}))
            self.assertTrue(call.call_args.kwargs.get('ip'))
            self.csrf = 'wrong'
            self.assertEqual(self.req('/api/svc/offer', 'POST', {})[0], 403)
            self.assertEqual(call.call_count, 1)

    def test_refusal_code_and_admin_only(self):
        from game.service_market import ServiceError
        self.bootstrap()
        with patch('game.service_market.post', side_effect=ServiceError('Hai tài khoản cùng một mạng không giao dịch với nhau được.', 'same_net', 403)):
            status, _, body = self.req('/api/svc/order', 'POST', {})
            self.assertEqual((status, json.loads(body)['code']), (403, 'same_net'))
        self.assertEqual(self.req('/api/admin/svc')[0], 403)
        self.assertEqual(self.req('/api/admin/svc', 'POST', {'op': 'close'})[0], 403)
