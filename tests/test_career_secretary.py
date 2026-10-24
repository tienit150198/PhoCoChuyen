import random
import unittest

from game.careers import office_work as ow
from game.engine import GameError
from game.careers import secretary as M
from tests.office_desk_cases import DeskCases, roundtrip


class SecretaryTests(DeskCases, unittest.TestCase):
    M = M

    def test_call_message_is_picked_from_four(self):
        """#355: who called, from where and when are chosen from four options (no typing); the change of time is one."""
        for seed in range(200):
            for tier in (0, 1, 2):
                for twist in (False, True):
                    x = M.g_calls(random.Random(seed), dict(tier=tier, twist=twist))
                    f = {k['id']: k for k in x['work']['fields']}
                    for k in ('name', 'company', 'time', 'topic'):
                        self.assertEqual(f[k]['kind'], 'pick', k)
                    self.assertEqual(f['phone']['kind'], 'digits')
                    for k in ('name', 'company', 'time'):
                        ids, labels = [o['id'] for o in f[k]['opts']], [o['label'] for o in f[k]['opts']]
                        self.assertEqual((len(set(ids)), len(set(labels))), (4, 4), (seed, k, labels))
                        self.assertIn(f[k]['_ok'], ids)
                    right = {k: next(o['label'] for o in f[k]['opts'] if o['id'] == f[k]['_ok']) for k in ('name', 'company', 'time')}
                    self.assertIn(right['name'], x['title'])
                    self.assertTrue(any(right['company'] in l['text'] for l in x['work']['script']) or right['company'].startswith('Phụ huynh'))
                    tw = x['work']['_twist']
                    if twist:
                        self.assertIn(tw['ok'], [o['id'] for o in f['time']['opts']])
                        self.assertNotEqual(tw['ok'], f['time']['_ok'])
                    else:
                        self.assertIsNone(tw)

    def test_call_wrong_pick_is_explained_and_old_typed_calls_still_grade(self):
        j = self.journey('calls', twist=False)
        tid = j.task['id']
        j.act('ask', task=tid)
        f = {k['id']: k for k in j.task['work']['fields']}
        wrong = next(o for o in f['name']['opts'] if o['id'] != f['name']['_ok'])
        want = {k: v['_ok'] for k, v in f.items()}
        r = j.act(self.P + 'file', task=tid, confirm=True, fields=dict(want, name=wrong['id']))
        t = j.get(tid)
        self.assertFalse(r['correct'])
        self.assertEqual([e['ref'] for e in t['result']['errors']], ['name'])
        self.assertIn(wrong['label'], t['result']['errors'][0]['text'])
        # a call handed out before #355 kept its typed boxes: typing is still graded the old way
        old = dict(id='name', label='Người gọi (họ tên)', kind='text', _ok='Trần Văn Nam', _alt=['anh Trần Văn Nam'])
        self.assertTrue(ow.field_ok(old, ' tran van nam '))
        self.assertTrue(ow.field_ok(dict(id='time', kind='time', _ok='14:30'), '1430'))
        self.assertFalse(ow.field_ok(old, 'Trần Văn Hùng'))
        for twist in (False, True):
            j2 = self.journey('calls', twist=twist)
            tid2 = j2.task['id']
            tasks = j2.c['tasks']
            k = next(i for i, x in enumerate(tasks) if x['id'] == tid2)
            day, slot = tasks[k]['day'], int(tid2.rsplit('-', 1)[1])
            tasks[k] = M.make_task(day, slot, tasks[k]['created_turn'], legacy=True)   # as a 2.6.5 save holds it
            self.assertTrue(M.legacy_task(tasks[k]))
            self.assertEqual(tasks[k]['work']['fields'][0]['kind'], 'text')
            roundtrip(j2)                                                            # the save still loads
            j2.act('ask', task=tid2)
            for _ in range(3):
                w = ow.truth(j2.get(tid2))
                typed = {f['id']: f['_ok'] for f in w['fields']}
                typed['time'] = typed['time'].replace(':', '')                        # typed on the number pad
                typed['name'] = 'anh ' + typed['name'].lower()
                r2 = j2.act(self.P + 'file', task=tid2, confirm=True, fields=typed)
                if not r2.get('twist'):
                    break
            self.assertTrue(r2['correct'], j2.get(tid2)['result'])
            roundtrip(j2)
        # a pick task is never taken for an old one, and a forged typed box on a new task is refused
        fresh = M.make_task(day, slot, 1)
        self.assertFalse(M.legacy_task(fresh))
        j3 = self.journey('calls', twist=False)
        f3 = j3.task['work']['fields'][0]
        f3.update(kind='text', _ok='Ai cũng được')
        f3.pop('opts')
        with self.assertRaises(GameError):
            roundtrip(j3)


if __name__ == '__main__':
    unittest.main()
