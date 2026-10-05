"""Render every hiring stage from real employment commands, including cabin crew."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from game import employment as emp, journey
from game.content import public_content
from game.engine import new_state

ROOT = Path(__file__).resolve().parents[1]
CAREERS = ('flight_attendant', 'customer_care', 'salon', 'pharmacy')


def fixtures():
    state = new_state()
    journey.enable_story(state, seed=75)
    state['journey'].update(wallet=461, life_day=75)
    states = []

    def capture(cid):
        room = state['careers'][cid]
        job = emp.public(room, cid, state)
        app = job.get('application') or {}
        states.append(copy.deepcopy(dict(
            label=f"{cid}/{job['status']}/{app.get('stage', '')}/{len(app.get('answers', {}))}",
            state=dict(current=cid, careers={cid: dict(job=job, day=room['day'],
                                                      open=room['open'], money=room['money'])},
                       journey=state.get('journey'), settings=dict(aiConsent=True)))))

    for cid in CAREERS:
        if cid not in state['careers']:
            raise unittest.SkipTest(cid + ' is filtered out')
        room = state['careers'][cid]
        post = emp.postings(cid)[0]
        capture(cid)
        # Exercise the full pipeline even on days with a lucky direct offer.
        for day in range(1, 100):
            room['day'] = day
            room['job'] = emp.initial()
            emp.action(state, room, cid, 'job_apply', dict(posting=post['id']))
            if room['job']['status'] == 'applying':
                break
            capture(cid)
        else:
            raise AssertionError('No normal application day')
        for _ in range(80):
            capture(cid)
            job = room['job']
            if job['status'] != 'applying':
                break
            app = job['application']
            stage = app['stage']
            if stage == 'exam':
                sheet = app['exam']
                qid = next(q for q in sheet['qs'] if q not in sheet['answers'])
                question = next(q for q in emp.exam(cid)['bank'] if q['id'] == qid)
                emp.action(state, room, cid, 'job_exam', dict(question=qid, option=question['answer']))
            elif stage == 'cv':
                emp.action(state, room, cid, 'job_cv', dict(strengths=post['wants'][:2], claims=['fresh']))
            elif stage == 'letter':
                emp.action(state, room, cid, 'job_letter', dict(parts=dict(why='specific', example='story', close='available')))
            elif emp._open_ask(app):
                emp.action(state, room, cid, 'job_followup', dict(skip=True))
            else:
                qid = next(q for q in emp.stage_steps(post, stage) if q not in app['answers'])
                option = max(emp.question(cid, qid)['options'], key=lambda o: o['score'])
                emp.action(state, room, cid, 'job_answer', dict(question=qid, option=option['id']))
        else:
            raise AssertionError('Application did not finish')
        if room['job']['status'] == 'offer':
            emp.action(state, room, cid, 'job_accept', dict(confirm=True))
            capture(cid)
        if cid == 'pharmacy':
            room['job'] = emp.initial()
            emp.action(state, room, cid, 'job_apply', dict(posting=post['id']))
            for qid in list(room['job']['application']['exam']['qs']):
                q = next(q for q in emp.exam(cid)['bank'] if q['id'] == qid)
                wrong = next(o['id'] for o in q['options'] if o['id'] != q['answer'])
                emp.action(state, room, cid, 'job_exam', dict(question=qid, option=wrong))
            capture(cid)
    return dict(content=public_content(), states=states)


class JobApplicationUITests(unittest.TestCase):
    def test_all_stages_and_interview_network_states_keep_body_content(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node unavailable')
        result = subprocess.run([node, 'tests/job_application_ui.mjs'], cwd=ROOT,
                                input=json.dumps(fixtures()), text=True, encoding='utf-8',
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
