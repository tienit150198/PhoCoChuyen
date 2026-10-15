"""game/validate_memo.py: a moved career's tasks, posts, journal, memories and chats whose JSON already passed
engine.validate_career in this worker are not checked again, only inside storage.serialize_bytes."""
import copy
import math
import unittest
from unittest.mock import patch

from game import engine, storage, validate_memo as vm
from game.engine import GameError, validate_career, validate_state
from tests.helpers import Journey


def _post(n):
    return dict(id=f'memo-post-{n}', npc='player', author='Khách', source='review', kind='post', text=f'Quán dễ thương {n}',
                stars=None, liked=False, day=1, comments=[])


@unittest.skipUnless(vm.ON, 'needs orjson')
class ValidateMemoTests(unittest.TestCase):
    def setUp(self):
        vm.clear()
        j = Journey('accounting')
        self.state = j.state
        self.c = j.c
        self.c['feed'][:0] = [_post(i) for i in range(3)]
        validate_state(self.state)

    def tearDown(self):
        vm.clear()

    def checks(self, fn, *names):
        """How often each of the given engine/feedback checks ran during fn()."""
        from game import feedback
        calls = dict.fromkeys(names, 0)
        patches = []
        for name in names:
            mod, attr = (feedback, 'validate_post') if name == 'validate_post' else (engine, name)
            real = getattr(mod, attr)

            def wrap(*a, _real=real, _name=name, **k):
                calls[_name] += 1
                return _real(*a, **k)
            patches.append(patch.object(mod, attr, wrap))
        for p in patches:
            p.start()
        try:
            fn()
        finally:
            for p in patches:
                p.stop()
        return calls

    def memo_validate(self):
        with vm.active():
            validate_career(self.c, 'accounting')

    def test_values_that_passed_are_not_checked_again_only_inside_active(self):
        first = self.checks(self.memo_validate, 'make_task', 'validate_post')
        self.assertEqual(first['make_task'], len(self.c['tasks']))
        self.assertEqual(first['validate_post'], len(self.c['feed']))
        again = self.checks(self.memo_validate, 'make_task', 'validate_post')
        self.assertEqual(again, dict(make_task=0, validate_post=0))
        # outside active() (validate_state, imports, the periodic full check) every check runs
        full = self.checks(lambda: validate_state(self.state), 'make_task', 'validate_post')
        self.assertEqual(full['make_task'], len(self.c['tasks']))
        self.assertEqual(full['validate_post'], len(self.c['feed']))
        plain = self.checks(lambda: validate_career(self.c, 'accounting'), 'make_task', 'validate_post')
        self.assertEqual(plain['validate_post'], len(self.c['feed']))

    def test_a_changed_value_is_checked_and_refused_as_before(self):
        self.memo_validate()
        self.c['feed'][1]['text'] = ''  # an invalid post: its JSON is new
        with self.assertRaises(GameError) as plain:
            validate_career(copy.deepcopy(self.c), 'accounting')
        with self.assertRaises(GameError) as memo:
            self.memo_validate()
        self.assertEqual(str(memo.exception), str(plain.exception))
        self.c['feed'][1]['text'] = 'Quán dễ thương 1'
        self.c['feed'].insert(0, _post(9))  # a new post next to remembered ones: only it is checked
        n = self.checks(self.memo_validate, 'validate_post')
        self.assertEqual(n['validate_post'], 1)

    def test_nan_hidden_behind_the_json_of_a_remembered_value_is_refused_with_the_same_message(self):
        self.memo_validate()
        self.c['feed'][0]['stars'] = math.nan  # orjson writes it as null: the same JSON as the remembered post
        with self.assertRaises(GameError) as plain:
            validate_career(copy.deepcopy(self.c), 'accounting')
        self.assertIn('sao', str(plain.exception))
        with self.assertRaises(GameError):
            self.memo_validate()  # still refused (the career's finite check)
        with self.assertRaises(GameError) as moved:
            storage._validate_moved(self.c, 'accounting', frozenset())
        self.assertEqual(str(moved.exception), str(plain.exception))  # storage reruns the full check: the same message

    def test_a_value_changed_by_its_checks_is_not_remembered(self):
        from game import feedback
        real = feedback.validate_post

        def changes(post):
            post['_seen'] = post.get('_seen', 0) + 1
            return real(post)
        with patch.object(feedback, 'validate_post', changes):
            self.memo_validate()
        self.assertFalse(any(k[1] == 'post' for k in vm._new))

    def test_whole_lists_and_tasks_are_remembered_per_career(self):
        self.memo_validate()
        kinds = {k for k in vm._new}
        self.assertIn(('accounting', 'task'), kinds)
        self.assertIn(('accounting', 'journal'), kinds)
        self.assertIn(('accounting', 'memories'), kinds)
        self.assertIn(('accounting', 'chats'), kinds)
        # another career with the same JSON is not covered by these entries
        self.assertFalse(vm.known('pharmacy', 'journal', vm.digest(self.c['journal'])))

    def test_bounded(self):
        with patch.object(vm, 'LIMIT', 4):
            vm.remember('accounting', 'post', [(vm.digest(i), i) for i in range(2)])
            vm.remember('accounting', 'post', [(vm.digest(i), i) for i in range(2, 5)])  # over half: a new generation
            self.assertTrue(vm.known('accounting', 'post', vm.digest(0)))  # the older generation is still read
            vm.remember('accounting', 'post', [(vm.digest(i), i) for i in range(5, 8)])
            self.assertFalse(vm.known('accounting', 'post', vm.digest(0)))  # dropped with its generation
            self.assertTrue(vm.known('accounting', 'post', vm.digest(7)))


if __name__ == '__main__':
    unittest.main()
