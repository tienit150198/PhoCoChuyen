"""🏨 Sổ phòng routing: /api/hotel/* reads with a session (no save parsed), writes CSRF-guarded with the client's
network passed on, refusals answered with their code."""
import json
from unittest.mock import patch

from tests.test_http import HTTPTests


class HotelHTTP(HTTPTests):
    def test_reads_need_a_session_and_skip_the_save(self):
        for cookie in (None, 'mnl_session=invalid-session'):
            self.cookie = cookie
            self.assertEqual(self.req('/api/hotel/view')[0], 401)
            self.assertEqual(self.req('/api/hotel/arrive', 'POST', {})[0], 401)
        self.cookie = None
        self.bootstrap()
        with patch.object(self.server.store, 'read', side_effect=AssertionError('No save needed')), \
                patch('game.hotel_stay.get', return_value={'host': {}}) as call:
            status, _, body = self.req('/api/hotel/view')
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('view', {}))

    def test_writes_are_csrf_guarded_and_carry_the_network(self):
        self.bootstrap()
        with patch('game.hotel_stay.post', return_value={'ok': True}) as call:
            status, _, body = self.req('/api/hotel/checkin', 'POST', {'order': 'sv_x', 'room': 'thong', 'pick': 'tra'})
            self.assertEqual(status, 200, body)
            self.assertEqual(call.call_args.args[-2:], ('checkin', {'order': 'sv_x', 'room': 'thong', 'pick': 'tra'}))
            self.assertTrue(call.call_args.kwargs.get('ip'))
            self.csrf = 'wrong'
            self.assertEqual(self.req('/api/hotel/checkin', 'POST', {})[0], 403)
            self.assertEqual(call.call_count, 1)

    def test_refusal_code(self):
        from game.service_market import ServiceError
        self.bootstrap()
        with patch('game.hotel_stay.post', side_effect=ServiceError('Phòng Đồi Thông đang có khách.', 'room_busy', 409)):
            status, _, body = self.req('/api/hotel/checkin', 'POST', {})
            self.assertEqual((status, json.loads(body)['code']), (409, 'room_busy'))
