import io,json,os,unittest
from unittest.mock import patch
from game.dialogue import rephrase,public_config
from tests.helpers import Journey
class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*a):self.close()

class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.j=Journey();self.npc=self.j.task['npc'];self.j.act('talk',npc=self.npc,text='Chào bạn, hôm nay thế nào?')
    def test_no_consent_never_calls_endpoint(self):
        self.j.act('settings',aiConsent=False)  # AI is on by default now; the player can switch it off
        with patch('urllib.request.urlopen') as urlopen:
            self.assertEqual(rephrase(self.j.state,'mother_baby',self.npc)['reason'],'no_consent');urlopen.assert_not_called()
    def test_no_config_falls_back(self):
        self.j.act('settings',aiConsent=True)
        with patch.dict(os.environ,{'LLM_BASE_URL':'','LLM_MODEL':''}):self.assertEqual(rephrase(self.j.state,'mother_baby',self.npc)['mode'],'scripted')
    def run_mock(self,text):
        self.j.act('settings',aiConsent=True);payload=json.dumps({'choices':[{'message':{'content':text}}]}).encode()
        with patch.dict(os.environ,{'LLM_BASE_URL':'http://localhost:8000/v1','LLM_MODEL':'mock-model','LLM_API_KEY':'test-key'}),patch('urllib.request.urlopen',return_value=Response(payload)) as mock:
            result=rephrase(self.j.state,'mother_baby',self.npc);return result,mock
    def test_compatible_mock_response(self):
        result,mock=self.run_mock('Chào bạn! Mình trò chuyện một chút nhé.');self.assertEqual(result['mode'],'ai');req=mock.call_args.args[0];self.assertTrue(req.full_url.endswith('/v1/chat/completions'));self.assertNotIn('tools',json.loads(req.data))
    def test_new_numbers_rejected(self):self.assertEqual(self.run_mock('Mình đã cộng 9999 xu!')[0]['reason'],'new_numeric_claim')
    def test_null_provider_content_falls_back(self):self.assertEqual(self.run_mock(None)[0]['mode'],'scripted')
    def test_timeout_falls_back(self):
        self.j.act('settings',aiConsent=True)
        with patch.dict(os.environ,{'LLM_BASE_URL':'http://localhost:8000/v1','LLM_MODEL':'mock'}),patch('urllib.request.urlopen',side_effect=TimeoutError):self.assertEqual(rephrase(self.j.state,'mother_baby',self.npc)['reason'],'unavailable')
    def test_model_has_no_state_write_access(self):
        before=self.j.c['money'];self.run_mock('Mình tặng thêm rất nhiều xu.');self.assertEqual(self.j.c['money'],before)
