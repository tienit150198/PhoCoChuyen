"""📜 Học lịch sử Việt Nam (game/history_course.py): content, learning, exam, the one-off reward, old saves,
tampered saves and the page (tests/history_course.mjs)."""
import copy
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import history_content as C
from game import history_course as hc
from game import journey as jr
from game.engine import GameError, apply_action, new_state, validate_state

ROOT = Path(__file__).resolve().parents[1]


def story(seed=4242):
    s = new_state()
    jr.enable_story(s, seed)
    validate_state(s)
    return s


def act(s, action, **p):
    return apply_action(s, None, action, p)


def wrong(q):
    return next(o['id'] for o in q['options'] if o['id'] != q['answer'])


def learn_all(s):
    for l in C.LESSONS:
        s, _ = act(s, 'vs_open', lesson=l['id'])
        for q in l['practice']:
            if q['id'] not in s['history_course']['lessons'][l['id']]['solved']:
                s, _ = act(s, 'vs_answer', lesson=l['id'], question=q['id'], option=q['answer'])
    return s


def sit(s, right=hc.DRAW):
    s, _ = act(s, 'vs_exam_start')
    out = None
    for i, qid in enumerate(list(s['history_course']['active']['qs'])):
        q = hc.EXAM[qid]
        s, out = act(s, 'vs_exam_answer', question=qid, option=q['answer'] if i < right else wrong(q))
    return s, out


class HistoryContentTests(unittest.TestCase):
    def test_lessons_short_ordered_and_each_question_has_one_right_option(self):
        self.assertTrue(8 <= len(C.LESSONS) <= 12)
        ids = [l['id'] for l in C.LESSONS]
        self.assertEqual(len(ids), len(set(ids)))
        qids = [q['id'] for l in C.LESSONS for q in l['practice'] + l['exam']]
        self.assertEqual(len(qids), len(set(qids)))
        answers = set()
        for l in C.LESSONS:
            self.assertTrue(3 <= len(l['body']) <= 5, l['id'])
            self.assertEqual((len(l['practice']), len(l['exam'])), (2, 2), l['id'])
            for q in l['practice'] + l['exam']:
                opts = [o['id'] for o in q['options']]
                labels = [o['label'] for o in q['options']]
                self.assertEqual(len(opts), 3, q['id'])
                self.assertEqual(len(set(opts)), 3, q['id'])
                self.assertEqual(len(set(labels)), 3, q['id'])
                self.assertIn(q['answer'], opts, q['id'])
                self.assertTrue(q['why'].strip(), q['id'])
                answers.add(q['answer'])
        self.assertEqual(answers, {'a', 'b', 'c'}, 'the right answer is not always in the same place')

    def test_lessons_run_in_time_order(self):
        years = [int(m.group()) for l in C.LESSONS for m in [re.search(r'\d{3,4}', l['era'])] if m]
        self.assertGreaterEqual(len(years), 9)
        self.assertEqual(years, sorted(years))

    def test_the_hint_line_holds_the_answer(self):
        for l in C.LESSONS:
            for q in l['practice']:
                line = l['body'][hc.hint_line(l, q)].lower()
                right = next(o['label'] for o in q['options'] if o['id'] == q['answer']).lower()
                core = re.sub(r'^(ngày|năm|quân)\s+', '', right)
                words = {w for w in re.findall(r'\w+', core) if len(w) > 1}
                self.assertTrue(core in line or any(w in line for w in words), (q['id'], line))


class HistoryCourseTests(unittest.TestCase):
    def test_old_and_new_saves_load_and_viewing_stores_nothing(self):
        s = story()
        before = json.dumps(s, sort_keys=True)
        s, r = act(s, 'vs_view')
        self.assertNotIn('history_course', s)
        self.assertEqual(r['history_view']['done'], 0)
        self.assertEqual(r['history_view']['total'], len(C.LESSONS))
        self.assertFalse(r['history_view']['can_exam'])
        old = json.loads(before)
        validate_state(old)   # a save from before the course
        plain = new_state()
        plain, _ = act(plain, 'vs_view')
        self.assertNotIn('history_course', plain)

    def test_practice_needs_the_lesson_open_and_retries_freely(self):
        s = story()
        l = C.LESSONS[0]
        q = l['practice'][0]
        with self.assertRaises(GameError):
            act(s, 'vs_answer', lesson=l['id'], question=q['id'], option=q['answer'])
        s, r = act(s, 'vs_open', lesson=l['id'], view={'lesson': l['id']})
        view = r['history_view']['lesson']
        self.assertEqual(view['body'], l['body'])
        self.assertNotIn('answer', view['questions'][0])
        wallet = s['journey']['wallet']
        s, r = act(s, 'vs_answer', lesson=l['id'], question=q['id'], option=wrong(q))
        self.assertIs(r['correct'], False)
        self.assertEqual(r['hint'], hc.hint_line(l, q))
        self.assertNotIn(q['why'], r['message'])
        self.assertEqual(s['history_course']['lessons'][l['id']]['solved'], [])
        s, r = act(s, 'vs_answer', lesson=l['id'], question=q['id'], option=q['answer'])
        self.assertIs(r['correct'], True)
        self.assertFalse(r['lesson_done'])
        with self.assertRaises(GameError):
            act(s, 'vs_answer', lesson=l['id'], question=q['id'], option=q['answer'])
        with self.assertRaises(GameError):   # an exam question is not a practice question
            act(s, 'vs_answer', lesson=l['id'], question=l['exam'][0]['id'], option='a')
        s, r = act(s, 'vs_answer', lesson=l['id'], question=l['practice'][1]['id'], option=l['practice'][1]['answer'])
        self.assertTrue(r['lesson_done'])
        self.assertEqual(s['journey']['wallet'], wallet, 'learning is free')
        self.assertEqual(r['history_view']['done'], 1)

    def test_exam_waits_for_every_lesson_and_keeps_its_key(self):
        s = story()
        with self.assertRaises(GameError):
            act(s, 'vs_exam_start')
        s = learn_all(s)
        s, r = act(s, 'vs_exam_start')
        paper = s['history_course']['active']
        self.assertEqual(len(paper['qs']), hc.DRAW)
        self.assertEqual(sorted(hc.EXAM[q]['lesson'] for q in paper['qs']), sorted(l['id'] for l in C.LESSONS))
        shown = r['history_view']['active']['question']
        self.assertEqual(shown['id'], paper['qs'][0])
        self.assertNotIn('answer', shown)
        self.assertNotIn('why', shown)
        with self.assertRaises(GameError):   # not the current question
            act(s, 'vs_exam_answer', question=paper['qs'][1], option='a')
        with self.assertRaises(GameError):
            act(s, 'vs_exam_start')
        with self.assertRaises(GameError):
            act(s, 'vs_exam_cancel')
        s, _ = act(s, 'vs_exam_cancel', confirm=True)
        self.assertIsNone(s['history_course']['active'])
        s, _ = act(s, 'vs_exam_start')
        self.assertEqual(s['history_course']['attempts'], 2)

    def test_pass_gives_certificate_title_and_gift_once(self):
        s = learn_all(story())
        wallet = s['journey']['wallet']
        s, r = sit(s, right=hc.PASS_RIGHT - 1)
        self.assertFalse(r['exam']['passed'])
        self.assertIsNone(s['history_course']['cert'])
        self.assertEqual(s['journey']['wallet'], wallet)
        self.assertEqual(len(r['history_view']['review']['questions']), hc.DRAW)
        s, r = sit(s, right=hc.PASS_RIGHT)
        self.assertTrue(r['exam']['passed'] and r.get('celebrate'))
        cert = s['history_course']['cert']
        self.assertEqual(cert['gift'], hc.GIFT)
        self.assertTrue(cert['serial'].startswith('PCC-HIS-'))
        self.assertEqual(s['journey']['wallet'], wallet + hc.GIFT)
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('study', hc.GIFT))
        self.assertIn(hc.TITLE, s['journey']['titles'])
        self.assertIn(hc.TITLE, jr.TITLE_INDEX)
        self.assertTrue(jr._context(s)['history'])
        s, r = sit(s)
        self.assertTrue(r['exam']['passed'])
        self.assertEqual(s['journey']['wallet'], wallet + hc.GIFT, 'a retake pays nothing more')
        self.assertEqual(s['history_course']['cert'], cert)
        self.assertEqual(s['history_course']['best'], 100)

    def test_outside_the_story_the_certificate_has_no_gift(self):
        s = learn_all(new_state())
        wallet = s['journey']['wallet']
        s, r = sit(s)
        self.assertTrue(r['exam']['passed'])
        self.assertEqual(s['history_course']['cert']['gift'], 0)
        self.assertEqual(s['journey']['wallet'], wallet)
        self.assertNotIn(hc.TITLE, s['journey']['titles'])

    def test_tampered_saves_are_refused(self):
        s, _ = sit(learn_all(story()), right=hc.PASS_RIGHT - 2)
        s, _ = act(s, 'vs_exam_start')
        validate_state(s)
        bad = []
        x = copy.deepcopy(s); x['history_course']['extra'] = 1; bad.append(x)
        x = copy.deepcopy(s); x['history_course']['lessons']['atlantis'] = dict(read=True, solved=[], tries=0); bad.append(x)
        x = copy.deepcopy(s); x['history_course']['lessons']['hung']['solved'].append('hung_e1'); bad.append(x)
        x = copy.deepcopy(s); x['history_course']['active']['qs'].reverse(); bad.append(x)
        x = copy.deepcopy(s); x['history_course']['last']['score'] = 100; bad.append(x)
        x = copy.deepcopy(s); x['history_course']['cert'] = dict(date='2026-10-08', serial='PCC-HIS-X', score=100, gift=30); \
            x['history_course']['best'] = 100; x['history_course']['lessons'].pop('doi_moi'); x['history_course']['active'] = None; bad.append(x)
        x = copy.deepcopy(s); x['history_course']['cert'] = dict(date='2026-10-08', serial='PCC-HIS-X', score=100, gift=999); \
            x['history_course']['best'] = 100; bad.append(x)
        for i, x in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(x)

    def test_unknown_command(self):
        with self.assertRaises(GameError):
            act(story(), 'vs_nope')


class HistoryCourseUITests(unittest.TestCase):
    def test_page_renders_every_state_safely(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        s = story()
        l = C.LESSONS[2]
        s, _ = act(s, 'vs_open', lesson=l['id'])
        s, _ = act(s, 'vs_answer', lesson=l['id'], question=l['practice'][0]['id'], option=l['practice'][0]['answer'])
        lesson = hc.public(s, l['id'])
        s = learn_all(s)
        s, _ = sit(s)
        s, _ = act(s, 'vs_exam_start')
        data = dict(index=hc.public(new_state()), lesson=lesson, exam=hc.public(s), name='Học viên',
                    keys={q: hc.EXAM[q]['answer'] for q in hc.EXAM})
        out = subprocess.run([node, str(ROOT / 'tests/history_course.mjs')], input=json.dumps(data, ensure_ascii=False), text=True,
                             encoding='utf-8', cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
