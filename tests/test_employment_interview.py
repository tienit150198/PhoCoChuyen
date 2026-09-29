"""The interviewer talks back (v0.6): follow-up questions, typed replies scored by
transparent word rules, owners reacting in trials, and the /api/ai/interview route.

A fake OpenAI-compatible endpoint stands in for the provider; no test talks to a real
model. Spec: docs/superpowers/specs/2026-09-29-ai-interviewer-design.md
"""
import copy
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from game import employment as emp
from game.content import CAREERS
from game.engine import GameError, apply_action, new_state, validate_state
from game.storage import Store
from server import GameServer

LETTER = dict(why='specific', example='story', close='available')
ENV = {'LLM_BASE_URL': 'http://localhost:9/v1', 'LLM_MODEL': 'mock', 'LLM_API_KEY': 'k'}


def here(cid):
    if cid not in CAREERS:
        raise unittest.SkipTest(cid + ' is filtered out by MNL_CAREERS')
    return cid


def act(s, cid, action, **p):
    return apply_action(s, cid, action, p)


def post_of(cid, pid):
    return next(p for p in emp.postings(cid) if p['id'] == pid)


def best(cid, qid):
    return max(emp.question(cid, qid)['options'], key=lambda o: o['score'])['id']


def app_of(s, cid):
    return s['careers'][cid]['job']['application']


def at_stage(cid, pid, stage, claims=('fresh',), s=None):
    """A save with an open application for `pid`, walked up to `stage` (no lucky offer)."""
    for d in range(1, 400):
        t = copy.deepcopy(s) if s else new_state()
        t['careers'][cid]['day'] = d
        t, r = act(t, cid, 'job_apply', posting=pid)
        if not r.get('direct_offer'):
            break
    post = post_of(cid, pid)
    for _ in range(12):
        a = app_of(t, cid)
        if a['stage'] == stage:
            return t
        if a['stage'] == 'exam':
            for q in a['exam']['qs']:
                right = next(x['answer'] for x in emp.exam(cid)['bank'] if x['id'] == q)
                t, _ = act(t, cid, 'job_exam', question=q, option=right)
        elif a['stage'] == 'cv':
            t, _ = act(t, cid, 'job_cv', strengths=post['wants'][:2], claims=list(claims))
        elif a['stage'] == 'letter':
            t, _ = act(t, cid, 'job_letter', parts=LETTER)
        else:
            raise AssertionError(a['stage'])
    raise AssertionError('never reached ' + stage)


def finish(s, cid, reply=None, pick=best):
    """Answer the rest of the application; reply to each follow-up with `reply` (None = skip)."""
    r = None
    for _ in range(40):
        job = s['careers'][cid]['job']
        if job['status'] != 'applying':
            return s, r
        a = job['application']
        if emp._open_ask(a):
            s, r = act(s, cid, 'job_followup', **(dict(text=reply) if reply else dict(skip=True)))
            continue
        post = post_of(cid, a['posting'])
        q = next(x for x in emp.stage_steps(post, a['stage']) if x not in a['answers'])
        s, r = act(s, cid, 'job_answer', question=q, option=pick(cid, q))
    raise AssertionError('did not finish')


class ReplyRules(unittest.TestCase):
    def rule(self, text, s=None):
        s = s or new_state()
        return emp.score_reply(s, s['careers']['pharmacy'], 'pharmacy', text)

    def test_each_rule(self):
        self.assertEqual(self.rule('Có lần hôm qua con đọc lại đủ mã rồi mới giao.'), (2, ['example']))
        self.assertEqual(self.rule('Con hỏi lại khách để chắc là đúng hộp.'), (1, ['reason']))
        self.assertEqual(self.rule('Có lần con đếm lại vì hai hộp giống màu.'), (3, ['example', 'reason']))
        self.assertEqual(self.rule('dạ vâng'), (0, ['short']))
        self.assertEqual(self.rule('Con có nhiều năm kinh nghiệm quầy thuốc rồi.')[1], ['overclaim'])
        self.assertEqual(self.rule('Hôm đó sai là lỗi của đồng nghiệp chứ không phải con.'), (-1, ['blame']))
        self.assertEqual(self.rule('Hỏi làm gì, liên quan gì tới cô.'), (-3, ['rude']))

    def test_negative_rules_cancel_positive_ones_and_are_bounded(self):
        bonus, rules = self.rule('Hỏi làm gì, tôi có nhiều năm kinh nghiệm, lần trước là lỗi của khách vì họ ngu.')
        self.assertEqual(rules, ['rude', 'overclaim', 'blame'])
        self.assertEqual(bonus, emp.STEP_BONUS[0])
        for text in ('a', 'Có lần 3 khách vì vậy nên để ví dụ', 'x ' * 100):
            b, _ = self.rule(text)
            self.assertTrue(emp.STEP_BONUS[0] <= b <= emp.STEP_BONUS[1])

    def test_overclaim_needs_the_record_to_expose_it(self):
        s = new_state()
        s['careers']['grocery']['metrics']['served'] = 20
        self.assertNotIn('overclaim', self.rule('Tôi có nhiều năm kinh nghiệm bán hàng.', s)[1])

    def test_shelf_is_not_rude(self):
        self.assertNotIn('rude', self.rule('Con xếp kệ thuốc theo mã cho dễ tìm.')[1])

    def test_reply_is_redacted_and_bounded(self):
        out = emp.clean_reply_text('Gọi con 0912 345 678\n\nhoặc a@b.vn ' + 'x' * 300)
        self.assertNotIn('0912', out)
        self.assertNotIn('a@b.vn', out)
        self.assertLessEqual(len(out), emp.REPLY_MAX)


class FollowUps(unittest.TestCase):
    def setUp(self):
        here('pharmacy')
        self.s = at_stage('pharmacy', 'ph-day', 'interview', claims=('fresh', 'served5'))

    def test_one_follow_up_per_answer_never_after_the_last_and_at_most_two(self):
        s, r = act(self.s, 'pharmacy', 'job_answer', question='ph_rush', option='steady')
        a = app_of(s, 'pharmacy')
        self.assertEqual(r['talk'], 0)
        ask = a['talk'][0]
        self.assertEqual((ask['kind'], ask['status'], ask['who'], ask['mode']), ('ask', 'open', 'Cô Thu', 'scripted'))
        self.assertTrue(ask['text'].endswith('?'))
        self.assertIn('con', ask['text'])        # cô Thu calls the applicant "con"
        s, _ = act(s, 'pharmacy', 'job_followup', skip=True)
        s, _ = act(s, 'pharmacy', 'job_answer', question='ph_advice', option='wait')
        second = app_of(s, 'pharmacy')['talk'][1]
        self.assertIn('Đã hoàn thành ít nhất 5 công việc', second['text'])  # asks about the CV claim
        s, r = act(s, 'pharmacy', 'job_answer', question='ph_why', option='care')   # auto-skips the open one
        a = app_of(s, 'pharmacy')
        self.assertEqual([x['status'] for x in a['talk']], ['skipped', 'skipped'])
        self.assertNotIn('talk', r)
        self.assertLessEqual(sum(1 for x in a['talk'] if x['kind'] == 'ask'), emp.MAX_ASKS)
        validate_state(s)

    def test_reply_scores_and_reacts_in_character(self):
        s, _ = act(self.s, 'pharmacy', 'job_answer', question='ph_rush', option='steady')
        s, r = act(s, 'pharmacy', 'job_followup', text='Có lần con đọc lại mã vì hai hộp giống màu.')
        ask = app_of(s, 'pharmacy')['talk'][0]
        self.assertEqual((ask['status'], ask['bonus'], ask['rules']), ('answered', 3, ['example', 'reason']))
        self.assertTrue(ask['react'].startswith('Cô Thu'))
        self.assertEqual((r['bonus'], r['followup'], r['talk']), (3, 'answered', 0))
        with self.assertRaises(GameError):
            act(s, 'pharmacy', 'job_followup', text='again')       # only one reply per follow-up
        validate_state(s)

    def test_reply_validation(self):
        s, _ = act(self.s, 'pharmacy', 'job_answer', question='ph_rush', option='steady')
        for bad in ('', '   ', 'x' * 201, 5, None):
            with self.assertRaises(GameError):
                act(s, 'pharmacy', 'job_followup', text=bad)
        with self.assertRaises(GameError):
            act(self.s, 'pharmacy', 'job_followup', skip=True)     # nothing open yet

    def score_with(self, reply, s=None):
        s, r = finish(copy.deepcopy(s or self.s), 'pharmacy', reply)
        return app_of(s, 'pharmacy')['score'], app_of(s, 'pharmacy')

    def test_bounded_effect_on_the_score(self):
        honest = at_stage('pharmacy', 'ph-day', 'interview')
        mid = lambda cid, q: sorted(emp.question(cid, q)['options'], key=lambda o: o['score'])[1]['id']
        base, _ = finish(copy.deepcopy(honest), 'pharmacy', None, pick=mid)
        up, _ = finish(copy.deepcopy(honest), 'pharmacy', 'Có lần con làm vậy vì khách giục, kết quả là không giao nhầm.', pick=mid)
        down, _ = finish(copy.deepcopy(honest), 'pharmacy', 'Hỏi làm gì, liên quan gì tới cô.', pick=mid)
        base, up, down = (app_of(x, 'pharmacy')['score'] for x in (base, up, down))
        self.assertTrue(10 <= base <= 90, base)
        self.assertEqual(up - base, emp.TOTAL_BONUS[1])       # two replies of +3, capped at +5
        self.assertEqual(base - down, -emp.TOTAL_BONUS[0])    # two replies of −3, capped at −5
        _, a = self.score_with('Có lần con làm vậy vì khách giục, kết quả là không giao nhầm.', honest)
        self.assertTrue(any('Trả lời thêm với Cô Thu' in x for x in a['feedback']))

    def test_bonus_never_rescues_the_reference_cap(self):
        # served5 is not backed by the save: the reference check still caps the score at 40.
        score, a = self.score_with('Có lần con làm vậy vì khách giục, kết quả là không giao nhầm.')
        self.assertLessEqual(score, 40)
        self.assertFalse(a['honest'])


class TrialsAndOtherPipelines(unittest.TestCase):
    def test_owner_reacts_to_each_trial_step(self):
        here('repair')
        s = at_stage('repair', 'rp-apprentice', 'trial')
        s, r = act(s, 'repair', 'job_answer', question='rp_fan', option='measure')
        row = app_of(s, 'repair')['talk'][0]
        self.assertEqual((row['kind'], row['who'], row['stage'], r['talk']), ('react', 'Chú Tư', 'trial', 0))
        self.assertEqual(row['text'], emp.question('repair', 'rp_fan')['options'][0]['note'])
        s, _ = finish(s, 'repair')
        self.assertEqual(len(app_of(s, 'repair')['talk']), 3)
        self.assertFalse(any(x['kind'] == 'ask' for x in app_of(s, 'repair')['talk']))
        validate_state(s)

    def test_customer_care_interview_then_test(self):
        here('customer_care')
        s = at_stage('customer_care', 'cc-station', 'interview')
        s, _ = finish(s, 'customer_care', 'Có lần khách gọi ba lần, em đọc lịch sử trước để khách khỏi kể lại.')
        a = app_of(s, 'customer_care')
        kinds = [(x['stage'], x['kind']) for x in a['talk']]
        self.assertEqual(kinds, [('interview', 'ask'), ('interview', 'ask'), ('test', 'react'), ('test', 'react'), ('test', 'react')])
        self.assertEqual(emp.talk_bonus(a), emp.TOTAL_BONUS[1])
        validate_state(s)

    def test_teacher_and_office_careers_have_interviewers(self):
        rows = [('teacher', 'tch-public', 'Cô Ngọc'), ('teacher', 'tch-center', 'Chị Thùy')]
        for cid in ('corp_accounting', 'tax_payroll', 'group_accounting'):   # office plugins: their own postings
            if cid in CAREERS:
                p = next((x for x in emp.postings(cid) if len(x.get('questions') or []) >= 2), None)
                if p:
                    rows.append((cid, p['id'], emp.EC.INTERVIEWERS[cid]['name']))
        self.assertGreater(len(rows), 2)
        for cid, pid, name in rows:
            if cid not in CAREERS:
                continue
            post = post_of(cid, pid)
            s = at_stage(cid, pid, 'interview')
            q = post['questions'][0]
            s, r = act(s, cid, 'job_answer', question=q, option=best(cid, q))
            self.assertEqual(app_of(s, cid)['talk'][0]['who'], name, pid)
            s, _ = finish(s, cid, 'Ví dụ tuần trước em làm đúng quy trình vì cần đúng số.')
            validate_state(s)
        self.assertEqual(emp.content(['teacher'])['postings']['teacher'][0]['interviewer']['name'], 'Cô Ngọc')

    def test_one_question_interview_has_no_follow_up(self):
        s = at_stage('teacher', 'tch-trial', 'interview')
        s, r = act(s, 'teacher', 'job_answer', question='t_diverse', option='diff')
        self.assertEqual(app_of(s, 'teacher').get('talk'), [])
        self.assertIn(s['careers']['teacher']['job']['status'], ('offer', 'rejected'))


class Validation(unittest.TestCase):
    def setUp(self):
        here('pharmacy')
        s = at_stage('pharmacy', 'ph-day', 'interview')
        s, _ = act(s, 'pharmacy', 'job_answer', question='ph_rush', option='steady')
        self.s, _ = act(s, 'pharmacy', 'job_followup', text='Có lần con đọc lại mã vì hai hộp giống màu.')

    def broken(self, fn):
        s = copy.deepcopy(self.s)
        fn(app_of(s, 'pharmacy'))
        with self.assertRaises(GameError):
            validate_state(s)

    def test_tampered_talk_is_rejected(self):
        validate_state(self.s)
        self.broken(lambda a: a['talk'][0].update(bonus=9))
        self.broken(lambda a: a['talk'][0].update(rules=['genius']))
        self.broken(lambda a: a['talk'][0].update(reply='x' * 201))
        self.broken(lambda a: a['talk'][0].update(extra=1))
        self.broken(lambda a: a['talk'][0].update(q='ph_why'))          # not answered yet
        self.broken(lambda a: a['talk'][0].update(mode='gpt'))
        self.broken(lambda a: a['talk'].extend([dict(a['talk'][0], status='open', reply=None, react=None, react_mode=None,
                                                     react_canonical=None, bonus=0, rules=[])] * 20))
        self.broken(lambda a: a.update(talk='hi'))

    def test_open_ask_must_be_last(self):
        s = copy.deepcopy(self.s)
        a = app_of(s, 'pharmacy')
        a['talk'].insert(0, dict(a['talk'][0], status='open', reply=None, react=None, react_mode=None, react_canonical=None,
                                 bonus=0, rules=[]))
        with self.assertRaises(GameError):
            validate_state(s)

    def test_apply_voice_only_rewords_the_same_scripted_line(self):
        s = copy.deepcopy(self.s)
        row = app_of(s, 'pharmacy')['talk'][0]
        self.assertFalse(emp.apply_voice(s, 'pharmacy', 0, 'react', 'other canonical', 'Hay.'))
        self.assertFalse(emp.apply_voice(s, 'pharmacy', 0, 'text', row['canonical'], 'Hay?'))   # the ask is answered already
        self.assertFalse(emp.apply_voice(s, 'pharmacy', 5, 'react', row['react_canonical'], 'Hay.'))
        self.assertTrue(emp.apply_voice(s, 'pharmacy', 0, 'react', row['react_canonical'], 'Được đó con.'))
        self.assertEqual((row['react'], row['react_mode']), ('Được đó con.', 'ai'))
        self.assertFalse(emp.apply_voice(s, 'pharmacy', 0, 'react', row['react_canonical'], 'Lần hai.'))
        validate_state(s)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def completion(text):
    return Response(json.dumps({'choices': [{'message': {'content': text}}]}).encode())


class Voice(unittest.TestCase):
    def pend(self, cid='pharmacy', pid='ph-day'):
        s = at_stage(cid, pid, 'interview' if cid != 'repair' else 'trial')
        q = emp.stage_steps(post_of(cid, pid), app_of(s, cid)['stage'])[0]
        s, r = act(s, cid, 'job_answer', question=q, option=best(cid, q))
        return s, emp.pending_voice(s, cid, r['talk'])

    def call(self, s, cid, pend, reply):
        with patch.dict(os.environ, ENV), patch('urllib.request.urlopen', return_value=completion(reply)) as mock:
            return emp.voice(s, cid, pend), mock

    def test_town_npc_goes_through_persona_reply(self):
        s, pend = self.pend()
        self.assertEqual(pend['who']['npc'], 'pharmacy_npc_01')
        with patch('game.ai.persona_reply', return_value=dict(mode='ai', text='Ừ, con kể cô nghe một lần đi?', reason=None)) as pr:
            with patch.dict(os.environ, ENV):
                out = emp.voice(s, 'pharmacy', pend)
        self.assertEqual(out['mode'], 'ai')
        self.assertEqual(pr.call_args.kwargs['purpose'], 'interview')
        self.assertEqual(pr.call_args.args[2], 'pharmacy_npc_01')

    def test_request_shape_and_facts(self):
        s, pend = self.pend()
        out, mock = self.call(s, 'pharmacy', pend, 'Ừ, chậm mà chắc. Con từng gặp khách giục như vậy chưa?')
        self.assertEqual(out['mode'], 'ai')
        body = json.loads(mock.call_args.args[0].data)
        self.assertIn('phỏng vấn', body['messages'][0]['content'])
        data = json.loads(body['messages'][1]['content'])
        self.assertIn('40–55 xu/ngày', data['task']['interview']['wage'])
        self.assertEqual(data['canonical'], pend['canonical'])

    def test_owner_who_is_not_an_npc_gets_a_local_card(self):
        s, pend = self.pend('repair', 'rp-apprentice')
        self.assertIsNone(pend['who']['npc'])
        out, mock = self.call(s, 'repair', pend, 'Được, đo trước rồi mới thay, vậy là có nghề đó con.')
        self.assertEqual(out['mode'], 'ai')
        system = json.loads(mock.call_args.args[0].data)['messages'][0]['content']
        self.assertIn('"chú"', system)
        data = json.loads(json.loads(mock.call_args.args[0].data)['messages'][1]['content'])
        self.assertEqual(data['persona']['name'], 'Chú Tư')

    def test_guardrails_fall_back_to_the_scripted_line(self):
        s, pend = self.pend()
        cases = {'Cô nhận con luôn, mai đi làm nha?': 'promise',
                 'Lương con sẽ là 99 xu, được không?': 'new_numeric_claim',
                 'Chậm một nhịp là đúng rồi.': 'not_a_question',
                 'Là một mô hình ngôn ngữ, tôi hỏi: con khỏe không?': 'breaks_character'}
        for reply, why in cases.items():
            out, _ = self.call(s, 'pharmacy', pend, reply)
            self.assertEqual((out['mode'], out['text'], out['reason']), ('scripted', pend['canonical'], why), reply)

    def test_no_consent_and_timeouts(self):
        s, pend = self.pend('repair', 'rp-apprentice')
        s['settings']['aiConsent'] = False
        out, mock = self.call(s, 'repair', pend, 'Ừ.')
        self.assertEqual(out['reason'], 'no_consent')
        mock.assert_not_called()
        s['settings']['aiConsent'] = True
        with patch.dict(os.environ, ENV), patch('urllib.request.urlopen', side_effect=TimeoutError):
            self.assertEqual(emp.voice(s, 'repair', pend)['mode'], 'scripted')


class FakeLLM(BaseHTTPRequestHandler):
    reply = 'Ừ, chậm mà chắc. Con từng gặp khách giục như vậy chưa?'
    requests: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        FakeLLM.requests.append(body)
        data = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': FakeLLM.reply}}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class InterviewRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        here('pharmacy')
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
        cls.start = at_stage('pharmacy', 'ph-day', 'interview')

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
        FakeLLM.reply = 'Ừ, chậm mà chắc. Con từng gặp khách giục như vậy chưa?'
        self.cookie = self.csrf = None
        self.bootstrap()
        self.put(copy.deepcopy(self.start))

    def req(self, path, body=None, csrf=True):
        h = {'Host': f'127.0.0.1:{self.port}', 'Cookie': self.cookie, 'Content-Type': 'application/json'}
        if csrf:
            h['X-Game-CSRF'] = self.csrf
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        con.request('POST', path, body=json.dumps(body), headers=h)
        res = con.getresponse()
        out = res.status, json.loads(res.read() or b'{}')
        con.close()
        return out

    def bootstrap(self):
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request('GET', '/api/bootstrap', headers={'Host': f'127.0.0.1:{self.port}'})
        res = con.getresponse()
        self.cookie = res.getheader('Set-Cookie').split(';')[0]
        self.csrf = json.loads(res.read())['csrf']
        con.close()

    def put(self, state):
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, revision=revision+1 WHERE sid=?',
                       (json.dumps(state, ensure_ascii=False), self.store.key(self.cookie.split('=', 1)[1])))

    def saved(self):
        return self.store.read(self.cookie.split('=', 1)[1])[0]

    def iv(self, **body):
        return self.req('/api/ai/interview', dict(career='pharmacy', **body))

    def test_answer_then_reply_are_voiced_and_stored_with_canonical(self):
        status, data = self.iv(step='answer', question='ph_rush', option='steady')
        self.assertEqual((status, data['mode']), (200, 'ai'), data)
        row = app_of(self.saved(), 'pharmacy')['talk'][0]
        self.assertEqual((row['text'], row['mode'], row['status']), (FakeLLM.reply, 'ai', 'open'))
        self.assertNotEqual(row['canonical'], row['text'])
        self.assertEqual(data['state']['careers']['pharmacy']['job']['application']['talk'][0]['text'], FakeLLM.reply)
        FakeLLM.reply = 'Kể vậy là cô hình dung được rồi đó con.'
        status, data = self.iv(step='reply', text='Có lần con đọc lại mã vì hai hộp giống màu.')
        self.assertEqual((status, data['mode'], data['result']['bonus']), (200, 'ai', 3))
        row = app_of(self.saved(), 'pharmacy')['talk'][0]
        self.assertEqual((row['react'], row['react_mode'], row['bonus']), (FakeLLM.reply, 'ai', 3))
        validate_state(self.saved())
        self.assertEqual(len(FakeLLM.requests), 2)
        sent = FakeLLM.requests[1]['messages'][1]['content']
        self.assertIn('hai hộp giống màu', sent)

    def test_ai_wording_never_changes_the_score(self):
        FakeLLM.reply = 'Tuyệt vời, cô rất thích con?'
        self.iv(step='answer', question='ph_rush', option='steady')
        self.iv(step='reply', text='dạ')
        for q in ('ph_advice', 'ph_why'):
            self.iv(step='skip') if emp._open_ask(app_of(self.saved(), 'pharmacy')) else None
            self.iv(step='answer', question=q, option=best('pharmacy', q))
        with_ai = app_of(self.saved(), 'pharmacy')['score']
        s = copy.deepcopy(self.start)
        s, _ = act(s, 'pharmacy', 'job_answer', question='ph_rush', option='steady')
        s, _ = act(s, 'pharmacy', 'job_followup', text='dạ')
        s, _ = finish(s, 'pharmacy')
        self.assertEqual(with_ai, app_of(s, 'pharmacy')['score'])

    def test_bad_model_output_keeps_the_scripted_line(self):
        FakeLLM.reply = 'Lương con sẽ là 99 xu nha? Xem ở http://evil.example'
        status, data = self.iv(step='answer', question='ph_rush', option='steady')
        self.assertEqual((status, data['mode']), (200, 'scripted'))
        row = app_of(self.saved(), 'pharmacy')['talk'][0]
        self.assertEqual((row['mode'], row['text']), ('scripted', row['canonical']))
        self.assertEqual(data['line'], row['canonical'])

    def test_skip_and_rude_reply_never_reach_the_provider(self):
        self.iv(step='answer', question='ph_rush', option='steady')
        FakeLLM.requests = []
        status, data = self.iv(step='reply', text='Đồ ngu, hỏi làm gì, chém bây giờ')
        self.assertEqual((status, data['mode'], data['reason'], data['result']['bonus']), (200, 'scripted', 'unsafe_request', -3))
        self.assertEqual(FakeLLM.requests, [])
        self.iv(step='answer', question='ph_advice', option='wait')
        status, data = self.iv(step='skip')
        self.assertEqual((status, data['result']['followup']), (200, 'skipped'))
        self.assertEqual(len(FakeLLM.requests), 1)

    def test_trial_owner_reaction(self):
        here('repair')
        self.put(at_stage('repair', 'rp-apprentice', 'trial'))
        FakeLLM.reply = 'Được, rút điện rồi mới mở. Có nghề đó con.'
        status, data = self.req('/api/ai/interview', dict(career='repair', step='answer', question='rp_fan', option='measure'))
        self.assertEqual((status, data['mode']), (200, 'ai'))
        row = app_of(self.saved(), 'repair')['talk'][0]
        self.assertEqual((row['kind'], row['text'], row['mode']), ('react', FakeLLM.reply, 'ai'))

    def test_no_consent_skips_provider(self):
        s = copy.deepcopy(self.start)
        s['settings']['aiConsent'] = False
        self.put(s)
        status, data = self.iv(step='answer', question='ph_rush', option='steady')
        self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'no_consent'))
        self.assertEqual(FakeLLM.requests, [])
        self.assertEqual(app_of(self.saved(), 'pharmacy')['talk'][0]['status'], 'open')

    def test_budget(self):
        with patch.dict(os.environ, {'AI_CHAT_PER_MINUTE': '0'}):
            status, data = self.iv(step='answer', question='ph_rush', option='steady')
        self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'rate_limit'))
        self.assertEqual(FakeLLM.requests, [])

    def test_validation_and_csrf(self):
        self.iv(step='answer', question='ph_rush', option='steady')
        self.assertEqual(self.iv(step='reply', text='x' * 201)[0], 400)
        self.assertEqual(self.iv(step='reply', text='   ')[0], 400)
        self.assertEqual(self.iv(step='dance')[0], 400)
        self.assertEqual(self.iv(step='answer', question='ph_rush' * 20, option='steady')[0], 400)
        self.assertEqual(self.req('/api/ai/interview', dict(career='nope', step='skip'))[0], 400)
        self.assertEqual(self.req('/api/ai/interview', dict(career='pharmacy', step='skip'), csrf=False)[0], 403)
        self.assertEqual(self.iv(step='answer', question='ph_why', option='nope')[0], 400)
        validate_state(self.saved())

    def test_revision_conflict_returns_state(self):
        status, data = self.iv(step='answer', question='ph_rush', option='steady', expected_revision=0, request_id='conflict-iv-1')
        self.assertEqual(status, 409)
        self.assertIn('state', data)


if __name__ == '__main__':
    unittest.main()
