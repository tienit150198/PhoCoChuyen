"""A task made before a release that added a display-only field (0.9.6: clothing lines "ask")
still validates, while any real change to its facts is still refused."""
import copy
import unittest

from game.engine import GameError, validate_state
from tests.helpers import Journey


class LateTaskKeys(unittest.TestCase):
    def test_old_clothing_task_without_ask_still_validates(self):
        j = Journey('clothing')
        t = next(x for x in j.c['tasks'] if any('ask' in l for l in x['needs'].get('lines', [])))
        for line in t['needs']['lines']:
            line.pop('ask', None); line.pop('told', None)   # as stored by 0.9.5
        validate_state(j.state)

    def test_changed_facts_are_still_refused(self):
        j = Journey('clothing')
        t = next(x for x in j.c['tasks'] if x['needs'].get('lines'))
        bad = copy.deepcopy(j.state)
        task = next(x for x in bad['careers']['clothing']['tasks'] if x['id'] == t['id'])
        task['needs']['lines'][0].pop('ask', None); task['needs']['lines'][0].pop('told', None)
        task['needs']['lines'][0]['colour'] = 'màu khác'
        with self.assertRaises(GameError):
            validate_state(bad)


if __name__ == '__main__':
    unittest.main()
