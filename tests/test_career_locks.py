"""🔒 Vì sao chưa làm được nghề này (game/career_locks.py, owner 23/10): every reason the switch or the work is refused,
in plain words, the same words select_career answers with, and the picker's chapter line (v4/career-pick.js) agreeing."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from game import career_locks as cl
from game import journey as jr
from game.engine import GameError, apply_action, new_state, public_state, validate_state

ROOT = Path(__file__).resolve().parents[1]


def story(chapter=1):
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey']['gender'] = 'female'
    j = s['journey']
    for n in range(2, chapter + 1):   # the chapters before are done and their places open, as the story does it
        j['done'].append(n - 1)
        j['chapter'] = n
        jr._unlock_chapter(j, n)
    validate_state(s)
    return s


class ChapterLocks(unittest.TestCase):
    def test_a_later_chapter_says_which_and_how_far(self):
        s = story()
        w = cl.why(s, 'pho')
        self.assertEqual(w['k'], 'chapter')
        self.assertEqual(w['t'], '🔒 Mở ở chương 3')
        self.assertIn('bạn đang ở chương 1 (đã xong 0/', w['how'])

    def test_the_next_chapter_says_finish_this_one(self):
        s = story(2)
        w = cl.why(s, 'pho')
        self.assertEqual(w['t'], '🔒 Xong chương 2 là mở')
        self.assertTrue(w['how'].startswith('Làm xong việc cần làm của chương 2 (đã xong '))
        self.assertIsNone(cl.why(s, 'salon'), 'a chapter-2 place is open in chapter 2')
        self.assertIsNone(cl.why(s, 'canteen'), 'a late place of chapter 1 is open')

    def test_select_career_refuses_with_the_place_and_the_reason(self):
        s = story()
        with self.assertRaises(GameError) as e:
            apply_action(s, 'pho', 'select_career', {})
        self.assertEqual(e.exception.code, 'locked')
        self.assertIn('Quán phở Cây Si chưa mở với bạn.', str(e.exception))
        self.assertIn('chương 3', str(e.exception))
        self.assertNotIn('hàng xóm sẽ giới thiệu', str(e.exception), 'no vague line any more')

    def test_customs_counts_the_chapters_done(self):
        s = story(2)
        w = cl.why(s, 'customs')
        self.assertEqual(w['k'], 'customs')
        self.assertEqual(w['t'], '🔒 Cần xong 3 chương truyện (1/3)')
        self.assertIn('Công an tới cấp Hạ sĩ', w['how'])

    def test_an_accounting_place_offers_the_exam_way_in(self):
        w = cl.why(story(), 'corp_accounting')
        self.assertEqual((w['k'], w['act']), ('chapter', 'accountingSchool'))
        self.assertIn('Học kế toán', w['how'])

    def test_outside_the_story_nothing_is_shut(self):
        s = new_state()
        self.assertIsNone(cl.why(s, 'pho'))
        self.assertEqual(cl.public(s), {})


class OtherLocks(unittest.TestCase):
    def test_cert(self):
        s = story(5)
        w = cl.why(s, 'corp_accounting')
        self.assertEqual(w['k'], 'cert')
        self.assertEqual(w['act'], 'accountingSchool')
        self.assertIn('Kế toán cơ bản', w['t'])
        with self.assertRaises(GameError) as e:
            apply_action(s, 'corp_accounting', 'select_career', {})
        self.assertEqual(e.exception.code, 'need_cert')
        self.assertTrue(str(e.exception).startswith('Công ty CP Mây Tre Xanh chưa nhận bạn: thi đạt chứng nhận'))

    def test_gov_ban_says_the_good_days_left_and_lets_you_look(self):
        s = story(4)
        s['journey']['gov_ban'] = dict(t=7)
        w = cl.why(s, 'police')
        self.assertEqual((w['k'], w['soft']), ('gov_ban', True))
        self.assertIn('còn 15 ngày tốt để gỡ', w['t'])
        self.assertIn('ngày làm việc tốt', w['how'])
        s['journey']['gov_redo'] = dict(v=1, n=4, r=0, b=7)
        self.assertIn('còn 11 ngày', cl.why(s, 'police')['t'])
        self.assertIsNone(cl.why(s, 'nurse'), 'only the state careers')

    def test_a_failed_interview_says_the_day(self):
        s = story(4)
        job = s['careers']['nurse']['job']
        job.update(status='rejected', cooldown_day=s['journey']['life_day'] + 3)
        w = cl.why(s, 'nurse')
        self.assertEqual((w['k'], w['soft']), ('retry', True))
        self.assertIn(f'Ngày {s["journey"]["life_day"] + 3} (còn 3 ngày)', w['t'])
        job['cooldown_day'] = s['journey']['life_day']
        self.assertIsNone(cl.why(s, 'nurse'), 'the day has come: open again')

    def test_abroad_only_its_branch_opens(self):
        s = story(4)
        with mock.patch('game.abroad.contract', return_value=dict(career='nurse', to='nhat_ban', need=10, n=4)):
            w = cl.why(s, 'milk_tea')
            self.assertEqual((w['k'], w['soft'], w['act']), ('abroad', True, 'abroad'))
            self.assertIn('còn 6 ngày', w['t'])
            self.assertIsNone(cl.why(s, 'nurse'))


class PublicView(unittest.TestCase):
    def test_locks_skip_the_plain_chapter_lines_and_recent_lists_the_last_places(self):
        s = story()
        for cid in ('milk_tea', 'grocery'):
            s, _ = apply_action(s, cid, 'select_career', {})
            s, _ = apply_action(s, cid, 'start_day', {})
            s, _ = apply_action(s, cid, 'end_day', {'carry_event': True})
        J = public_state(s)['journey']
        self.assertEqual(J['recent'], ['grocery', 'milk_tea'])
        self.assertNotIn('pho', J['locks'], 'the client says the plain chapter line itself')
        self.assertEqual(J['locks']['customs']['k'], 'customs')
        self.assertNotIn('corp_accounting', J['locks'], 'its chapter line with the exam way in: the client says it too')
        self.assertEqual(list(J['locks']), ['customs'])
        self.assertLess(len(json.dumps(J['locks'], ensure_ascii=False)), 400, 'small on every response')


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class ClientAgrees(unittest.TestCase):
    def test_the_picker_says_the_chapter_line_in_the_same_words(self):
        for chapter in (1, 2, 3):
            s = story(chapter)
            J = public_state(s)['journey']
            n_of = {cid: n for n, ids in jr.CH_UNLOCKS.items() for cid in ids} | dict(jr.LATE_UNLOCKS)
            ids = [cid for cid in s['careers'] if cid not in J['unlocked'] and cid in n_of]
            out = subprocess.run(['node', str(ROOT / 'tests' / 'career_pick_lock.mjs')], cwd=ROOT, text=True, encoding='utf-8',
                                 input=json.dumps(dict(J=dict(chapter=J['chapter'], goals=J['goals']), n={c: n_of[c] for c in ids})),
                                 capture_output=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            got = json.loads(out.stdout)
            for cid in ids:
                want = cl.why(s, cid)
                self.assertEqual(got[cid], {k: want[k] for k in ('k', 't', 'how', 'act') if k in want}, cid)
            self.assertIn('corp_accounting', ids)


if __name__ == '__main__':
    unittest.main()
