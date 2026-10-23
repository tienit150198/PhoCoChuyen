"""23/10 lag: GET /api/state and /api/bootstrap answer server.fresh_view(state) of the save Store.read just parsed.
A save this build stamped skips public_state's defensive whole-save copy (~0.5 s for a 10 MB save) and the view is
the same byte for byte; anything else still goes through migrate_state."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import orjson

import server
from game import engine
from game.storage import Store


class FreshView(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'game.db')
        self.token, _, _ = self.store.session()
        self.store.command(self.token, 'request-001', 0, 'mother_baby', 'start_day', {})

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def bytes_of(self, view):
        return orjson.dumps(view, option=orjson.OPT_NON_STR_KEYS)

    def test_a_stamped_save_is_not_copied_and_the_view_is_the_same(self):
        state, _, _ = self.store.read(self.token)
        self.assertTrue(engine.stamped(state) and not engine.needs_migration(state))
        expected = self.bytes_of(engine.public_state(copy.deepcopy(state)))
        before = self.bytes_of(state)
        with patch('game.engine.migrate_state', side_effect=AssertionError('no migrate_state copy of the whole save')):
            view = server.fresh_view(state)
        self.assertEqual(self.bytes_of(view), expected)
        self.assertEqual(self.bytes_of(state), before, 'the save itself is left as it was')

    def test_an_unstamped_save_still_goes_through_migrate_state(self):
        state, _, _ = self.store.read(self.token)
        state['check'] = dict(state['check'], build='older-build')
        with patch('game.engine.migrate_state', wraps=engine.migrate_state) as migrate:
            server.fresh_view(state)
        self.assertEqual(migrate.call_count, 1)


if __name__ == '__main__':
    unittest.main()
