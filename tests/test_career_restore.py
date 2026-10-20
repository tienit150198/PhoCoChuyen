"""🧰 Xưởng phục chế Hồn Xưa (game/careers/restore.py): every ticket of every chapter plays to the end with one material
cost and an honest margin; the awkward customer demands (restore_content.DEMANDS) are many, fit the piece and change the
right finish or part; a wrong step stays open and costs quality; hidden answers never reach the browser; a played save
validates and the career stays dormant (out of the stored save) until it is worked."""
import copy
import json
import unittest
from collections import Counter

from game import engine
from game.careers import PLUGINS, kit
from game.careers import restore_content as C
from game.engine import GameError, validate_state
from tests.helpers import Journey

CHECKS = ['stable', 'photo', 'note', 'care']


def move(j, tid):
    t = j.get(tid)
    if not t['known']:
        return j.act('ask', task=tid)
    st, k = t['stage'], t['_key']
    p = ({'choice': k[st]} if st in ('clean', 'finish') else {'checks': CHECKS} if st == 'check' else
         {'tag': t['needs']['tag']} if st == 'deliver' else {'choices': k[st]})
    return j.act('phc_' + st, task=tid, **p)


def solve(j, tid):
    for _ in range(14):
        if j.get(tid)['status'] == 'completed':
            return j.get(tid)
        move(j, tid)
    raise AssertionError('restore ticket did not finish')


class RestoreCareer(unittest.TestCase):
    def setUp(self):
        self.assertIn('restore', PLUGINS)
        self.mod = PLUGINS['restore']

    def test_every_piece_plays_through_with_one_cost_and_a_fair_margin(self):
        seen = set()
        for day in (1, 4, 10, 20, 40):
            for slot in range(12):
                t = self.mod.make_task(day, slot, 1)
                if t['kind'] in seen and slot > 2:
                    continue
                seen.add(t['kind'])
                j = Journey('restore', day=day, slot=slot)
                tid = j.task['id']
                kit.money(j.state, j.c, -j.c['money'], 'Test empty wallet')
                done = solve(j, tid)
                self.assertEqual(done['quality'], 100)
                rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
                self.assertEqual(len([r for r in rows if r['amount'] < 0]), 1, 'materials settled once')
                self.assertGreaterEqual(sum(r['amount'] for r in rows), 17)
                self.assertLessEqual(sum(r['amount'] for r in rows), 40)
                state = copy.deepcopy(j.state)
                with self.assertRaises(GameError):
                    j.act('phc_deliver', task=tid, tag=done['needs']['tag'])
                self.assertEqual(state, j.state)
                validate_state(json.loads(json.dumps(j.state)))
        self.assertEqual(seen, {x[0] for x in C.ITEMS})

    def test_many_awkward_demands_fit_the_piece_and_change_the_answer(self):
        self.assertGreaterEqual(len(C.DEMANDS), 12)
        used = Counter()
        for day in range(1, 61):
            for slot in range(12):
                t = self.mod.make_task(day, slot, 1)
                n, k = t['needs'], t['_key']
                self.assertTrue(n['demands'], 'every ticket has at least one awkward demand')
                self.assertLessEqual(len(n['demands']), 2)
                for d in n['demands']:
                    used[d['id']] += 1
                    fx = C.DEMANDS[d['id']][4]
                    self.assertIn(n['material'], fx.get('only', (n['material'],)))
                    self.assertEqual(sorted(o['id'] for o in d['options']), sorted(a for a, _ in C.DEMANDS[d['id']][2]))
                    if fx.get('finish'):
                        self.assertEqual(k['finish'], fx['finish'])
                ids = [d['id'] for d in n['demands']]
                self.assertEqual('missing' in ids, any(p['missing'] for p in n['parts']))
                self.assertEqual([v for v in k['parts'].values()].count('make'), int('missing' in ids))
                self.assertLessEqual(sum(bool(C.DEMANDS[d][4].get('finish')) for d in ids), 1)
        self.assertEqual(set(used), set(C.DEMANDS), 'every demand shows up')
        # the right answer is not always in the same place
        firsts = Counter()
        for day in range(1, 30):
            t = self.mod.make_task(day, 0, 1)
            for d in t['needs']['demands']:
                firsts[[o['id'] for o in d['options']].index(C.DEMANDS[d['id']][3])] += 1
        self.assertEqual(len(firsts), 3)

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = Journey('restore', day=10, slot=0)
        tid = j.task['id']
        move(j, tid)
        move(j, tid)   # inspect
        t = j.get(tid)
        self.assertEqual(t['stage'], 'talk')
        wrong = {d: next(o['id'] for o in x['options'] if o['id'] != C.DEMANDS[d][3]) for d, x in ((x['id'], x) for x in t['needs']['demands'])}
        out = j.act('phc_talk', task=tid, choices=wrong)
        self.assertFalse(out.get('correct', True) if isinstance(out, dict) else False)
        t = j.get(tid)
        self.assertEqual((t['stage'], t['quality'], t['mistakes']), ('talk', 88, 1))
        self.assertIn('Nói thật', t['last_issue'])
        while j.get(tid)['stage'] != 'finish':
            move(j, tid)
        j.act('phc_finish', task=tid, choice='renew' if j.get(tid)['_key']['finish'] != 'renew' else 'wax')
        self.assertEqual(j.get(tid)['stage'], 'finish')
        done = solve(j, tid)
        self.assertEqual(done['quality'], 76)
        d = j.c['ext']['data']
        self.assertEqual((d['stats']['jobs'], d['stats']['good']), (1, 0))

    def test_payloads_order_and_hidden_answers(self):
        j = Journey('restore', day=4, slot=1)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('phc_inspect', task=tid, choices={})
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('phc_fix', task=tid, choices={})
        with self.assertRaises(GameError):
            j.act('phc_inspect', task=tid, choices={'s1': 'nope'})
        pub = self.mod.public_task(j.get(tid))
        self.assertNotIn('_key', pub)
        self.assertEqual(pub['stage'], 'inspect')
        self.assertTrue(pub['options'])
        text = json.dumps(pub, ensure_ascii=False)
        self.assertNotIn('glue_clamp"', text.replace('"id": "glue_clamp"', ''))
        # a tampered ticket is refused
        s = copy.deepcopy(j.state)
        next(t for t in s['careers']['restore']['tasks'] if t['id'] == tid)['_key']['clean'] = 'bleach'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_dormant_until_worked_and_on_the_map_of_the_story(self):
        self.assertIn('restore', engine.DORMANT)
        from game import journey as jr
        self.assertEqual(jr.LATE_UNLOCKS['restore'], 2)
        from game.guide_content import CAREERS as GUIDE
        self.assertIn('restore', GUIDE)
        from game.coach import own
        self.assertTrue(own('restore'))


if __name__ == '__main__':
    unittest.main()
