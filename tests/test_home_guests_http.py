"""HTTP boundary for home invitation list/view and mutations."""
from unittest.mock import patch
from tests.test_http import HTTPTests


class HomeGuestsHTTP(HTTPTests):
    def test_home_list_and_view_require_session_and_forward_query(self):
        self.bootstrap()
        with patch('game.home_guests.get', return_value={'homes': []}) as call:
            status, _, body = self.req('/api/home-guests')
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('', {}))
            status, _, body = self.req('/api/home-guests/view?code=PCC-ABCDEF')
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('view', {'code': 'PCC-ABCDEF'}))

    def test_home_invite_post_keeps_csrf_guard(self):
        self.bootstrap()
        with patch('game.home_guests.post', return_value={'ok': True}) as call:
            status, _, body = self.req('/api/home-guests/invite', 'POST', {'code': 'PCC-ABCDEF', 'kind': 'stay'})
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('invite', {'code': 'PCC-ABCDEF', 'kind': 'stay'}))
            self.csrf = 'wrong'
            self.assertEqual(self.req('/api/home-guests/invite', 'POST', {})[0], 403)
            self.assertEqual(call.call_count, 1)
