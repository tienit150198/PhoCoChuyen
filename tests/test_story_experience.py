"""Story guidance and remembered choices, derived safely from existing saves."""
import copy
import unittest
from unittest.mock import patch

from game import career_stories as stories
from game.engine import new_state, validate_state


def book(cid='milk_tea', seen=0, pick=None):
    s = new_state()
    s['stories']['arcs'][cid] = dict(
        seen=[b['id'] for b in stories.ARCS[cid]['beats'][:seen]],
        picks={f'{cid}_2': pick} if pick else {}, last=3)
    return s


def card(s, cid='milk_tea'):
    return next(a for a in stories.public(s)['arcs'] if a['career'] == cid)


class StoryExperienceTest(unittest.TestCase):
    def test_custom_metric_requirement_never_displays_internal_key(self):
        s = book()
        when = dict(stories.ARCS['milk_tea']['beats'][0]['when'], metric=('custom_metric', 3))
        with patch.dict(stories.ARCS['milk_tea']['beats'][0], when=when):
            req = next(r for r in card(s)['next']['requirements'] if r['id'] == 'custom_metric')
            self.assertEqual(req['label'], 'Hoàn thành mốc nghề')
            self.assertEqual(req['remaining'], 3)

    def test_next_unlock_has_exact_progress_and_no_future_plot(self):
        s = book(seen=2, pick='b')
        s['careers']['milk_tea'].update(day=3, xp=0)
        s['careers']['milk_tea']['metrics']['served'] = 5
        a = card(s)
        self.assertIn('next', a)
        reqs = {r['id']: r for r in a['next']['requirements']}
        self.assertEqual((reqs['days']['current'], reqs['days']['target'], reqs['days']['remaining']), (2, 4, 2))
        self.assertEqual((reqs['served']['current'], reqs['served']['target'], reqs['served']['remaining']), (5, 8, 3))
        self.assertEqual((reqs['gap']['current'], reqs['gap']['target']), (0, 1))
        self.assertFalse(a['next']['ready'])
        self.assertNotIn(stories.ARCS['milk_tea']['beats'][2]['hint'], str(a))
        self.assertNotIn(stories.ARCS['milk_tea']['beats'][2]['title'], str(a))

    def test_unlock_matches_engine_including_reset_and_level(self):
        for cid in stories.ARCS:
            for n in range(5):
                for day in (1, 3, 10):
                    s = book(cid, n)
                    s['careers'][cid].update(day=day, xp=0)
                    s['careers'][cid]['metrics']['served'] = 30
                    a = card(s, cid)
                    self.assertIn('next', a)
                    self.assertEqual(a['next']['ready'], stories.due(s, cid), (cid, n, day))
        s = book('secretary', 4)
        s['careers']['secretary'].update(day=10, xp=0)
        s['careers']['secretary']['metrics']['served'] = 30
        reqs = {r['id']: r for r in card(s, 'secretary')['next']['requirements']}
        self.assertEqual(reqs['level']['remaining'], 3)

    def test_history_recaps_only_experienced_beats(self):
        s = book(seen=2, pick='b')
        a = card(s)
        self.assertEqual(len(a['beats']), 2)
        self.assertTrue(all(b.get('recap') for b in a['beats']))
        self.assertIn('nắp ly', a['beats'][1]['pick'])
        self.assertIn('hình nền', a['beats'][1]['recap'])
        self.assertEqual(a['recap'], a['beats'][-1]['recap'])

    def test_pilots_recall_both_choices_and_keep_distinct_written_memories(self):
        for cid in ('milk_tea', 'repair'):
            memories = []
            for pick in ('a', 'b'):
                s = book(cid, 2, pick)
                s['stories']['seq'] = 1
                s['stories']['queue'] = [dict(id='s1', career=cid, beat=f'{cid}_3', day=3)]
                lines = stories.public(s)['due'][0]['lines']
                other = copy.deepcopy(s)
                other['stories']['arcs'][cid]['picks'][f'{cid}_2'] = 'b' if pick == 'a' else 'a'
                self.assertNotEqual(lines, stories.public(other)['due'][0]['lines'])
                s['stories']['arcs'][cid]['seen'] = [b['id'] for b in stories.ARCS[cid]['beats'][:4]]
                s['stories']['queue'][0]['beat'] = f'{cid}_5'
                preview = stories.public(s)['due'][0]['keepsake']
                s, result = stories.action(s, None, 'st_seen', {'id': 's1'})
                final = card(s, cid)
                self.assertEqual(preview, final['keepsake'])
                self.assertEqual(result['story']['keepsake'], final['keepsake'])
                self.assertIsNone(final['next'])
                memories.append(final['keepsake']['desc'])
                validate_state(s)
            self.assertNotEqual(*memories, cid)

    def test_legacy_missing_choices_and_public_view_do_not_change_save(self):
        for cid in ('milk_tea', 'repair'):
            s = book(cid, 5)
            before = copy.deepcopy(s)
            a = card(s, cid)
            self.assertEqual(a['keepsake'], stories.ARCS[cid]['keepsake'])
            self.assertEqual(s, before)
            validate_state(s)
        self.assertEqual(len(stories.ARCS), 46)   # + library (thư viện), oil (thợ dầu khí), railway (gác chắn đường sắt), nurse (điều dưỡng), rescue (tổng đài cứu hộ)
        self.assertEqual(sum(len(a['beats']) for a in stories.ARCS.values()), 230)   # + library's, oil's, railway's, nurse's and rescue's five beats each


if __name__ == '__main__':
    unittest.main()
