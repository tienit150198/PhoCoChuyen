"""Routing/CSRF integration for workplace APIs (business behavior is tested separately)."""
import json
from unittest.mock import patch
from tests.test_http import HTTPTests


class WorkVisitHTTP(HTTPTests):
    def test_visit_reads_authenticate_without_parsing_the_save(self):
        self.bootstrap()
        with patch.object(self.server.store,'read',side_effect=AssertionError('No save needed')), patch('game.work_visits.get',return_value={'incoming':[], 'outgoing':[]}):
            status,_,body=self.req('/api/work-visits/orders')
            self.assertEqual(status,200,body)

    def test_visit_get_forwards_query_with_session(self):
        self.bootstrap()
        with patch('game.work_visits.get',return_value={'places':[]}) as call:
            status,_,body=self.req('/api/work-visits/places?scope=friends&owner=PCC-ABCDEF')
            self.assertEqual(status,200,body)
            self.assertEqual(call.call_args.args[-2:],('places',{'scope':'friends','owner':'PCC-ABCDEF'}))

    def test_visit_post_is_csrf_guarded_and_calls_service(self):
        self.bootstrap()
        with patch.object(self.server.store,'read',side_effect=AssertionError('No save needed')), patch('game.work_visits.post',return_value={'ok':True}) as call:
            status,_,body=self.req('/api/work-visits/order','POST',{'place':'test','request_id':'one'})
            self.assertEqual(status,200,body)
            self.assertEqual(call.call_args.args[-2:],('order',{'place':'test','request_id':'one'}))
            self.csrf='wrong'
            self.assertEqual(self.req('/api/work-visits/order','POST',{})[0],403)
            self.assertEqual(call.call_count,1)

    def test_visit_requires_valid_session_for_both_methods(self):
        for cookie in (None,'mnl_session=invalid-session'):
            self.cookie=cookie
            self.assertEqual(self.req('/api/work-visits/orders')[0],401)
            self.assertEqual(self.req('/api/work-visits/order','POST',{})[0],401)

    def test_visit_domain_error_is_returned_without_private_state(self):
        from game.work_visits import WorkVisitError
        self.bootstrap()
        with patch('game.work_visits.get',side_effect=WorkVisitError('Chỗ làm đang đóng.','closed',403)):
            status,_,body=self.req('/api/work-visits/place?id=test')
            self.assertEqual(status,403,body)
            self.assertEqual(json.loads(body)['code'],'closed')
            self.assertNotIn('state',json.loads(body))
