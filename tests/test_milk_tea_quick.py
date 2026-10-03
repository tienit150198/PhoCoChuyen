"""Milk tea picks shown at once (public/js/careers/milk_tea.js "picks at once", feedback #116 "pha trà chọn đồ
nhanh ko bị lag"): a pick the page shows before the server answers must be one the server takes, and the cup and
order ticket it draws must be the ones the server sends back. Every pick on a run of cups (right and wrong ones)
goes through node (tests/milk_tea_quick.mjs) and through the engine, and the two must agree."""
import json
import random
import shutil
import subprocess
import unittest
from pathlib import Path

from game import boba
from game import extra_content
from game.engine import GameError, apply_action, public_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]
CUP_KEYS = ('placed', 'size', 'items', 'ice', 'sugar', 'checked', 'sealed')


def picks(tid):
    yield 'tea_cup', dict(task=tid, size='M')
    yield 'tea_cup', dict(task=tid, size='L')
    for i in extra_content.INGREDIENTS:
        yield 'tea_add', dict(task=tid, item=i['id'])
    for lv in boba.ICES:
        yield 'tea_ice', dict(task=tid, level=lv)
    for lv in boba.SUGARS:
        yield 'tea_sugar', dict(task=tid, level=lv)


def room_of(state):
    return json.loads(json.dumps(public_state(state)['careers']['milk_tea']))


def view_task(room, tid):
    return next(t for t in room['tasks'] if t['id'] == tid)


def cases(seed):
    """Cups made with random picks (the right one most of the time), every possible pick tried at each step."""
    rnd = random.Random(seed)
    out = []
    for day, slot in ((1, 0), (4, 2), (9, 1)):
        j = Journey('milk_tea', slot=slot, day=day)
        tid = j.task['id']
        out.append(dict(room=room_of(j.state), task=view_task(room_of(j.state), tid), op='tea_add', payload=dict(task=tid, item='black'),
                        pending=[], server=None))  # not known yet: never shown ahead
        j.act('ask', task=tid)
        right = [(a, p) for a, p in boba.solution(j.get(tid)) if a not in ('tea_seal', 'tea_serve')]
        prev = None   # the last pick that landed, with the room before it (laid as still on its way)
        for _ in range(8):
            room = room_of(j.state)
            took = []
            for op, payload in picks(tid):
                try:
                    after, _ = apply_action(j.state, 'milk_tea', op, payload)   # a copy: j.state stays as it is
                    server = json.loads(json.dumps(boba.public_task(next(t for t in after['careers']['milk_tea']['tasks'] if t['id'] == tid))))
                    took.append((op, payload, after))
                except GameError:
                    server = None
                out.append(dict(room=room, task=view_task(room, tid), op=op, payload=payload, pending=[], server=server))
                # The same pick drawn while the previous pick is still on its way (the room from before it).
                if prev:
                    out.append(dict(room=prev[0], task=view_task(prev[0], tid), op=op, payload=payload, pending=[prev[1]], server=server))
            if not took:
                break
            todo = [x for x in right if any(x[0] == t[0] and x[1] == t[1] for t in took)]
            op, payload, after = (next(t for t in took if (t[0], t[1]) == todo[0]) if todo and rnd.random() < .75 else rnd.choice(took))
            prev = (room, dict(op=op, payload=payload))
            j.state = after
    return out


class MilkTeaQuickParity(unittest.TestCase):
    def test_a_pick_shown_at_once_is_what_the_server_does(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        all_cases = cases(116)
        spec = json.dumps(dict(ingredients=extra_content.INGREDIENTS, cases=[{k: v for k, v in c.items() if k != 'server'} for c in all_cases]),
                          ensure_ascii=False)
        out = subprocess.run([node, str(ROOT / 'tests' / 'milk_tea_quick.mjs')], input=spec, cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        js = json.loads(out.stdout)
        self.assertEqual(len(js), len(all_cases))
        shown = taken = 0
        for c, r in zip(all_cases, js):
            where = f"{c['op']} {c['payload']} pending={c['pending']}"
            server = c['server']
            if r['quick']:
                shown += 1
                self.assertIsNotNone(server, 'shown at once but the server refuses it: ' + where)
                for k in CUP_KEYS:
                    self.assertEqual(r['cup'].get(k), server['cup'].get(k), f'{k}: {where}')
                self.assertEqual(r['ticket'], server['ticket'], where)
            same_cup = c['op'] == 'tea_cup' and c['task']['cup'].get('placed') and c['task']['cup'].get('size') == c['payload']['size']
            if server is not None and not c['pending'] and not same_cup:   # "Ly M đã nằm sẵn trên quầy": nothing to show
                taken += 1
                # A pick the server takes on a cup the page shows as it is: shown at once.
                self.assertTrue(r['quick'], 'the server takes it but the page waits: ' + where)
        self.assertGreater(shown, 120)
        self.assertGreater(taken, 60)


if __name__ == '__main__':
    unittest.main()
