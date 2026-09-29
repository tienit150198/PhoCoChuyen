"""Commands on a save stamped by this build re-validate only what they change.

See Store._compute / storage.serialize and engine.apply_action(scoped=True): the
stored save carries state["check"] = {build, careers: {cid: digest}}; a career whose
serialized text still has its stored digest is byte for byte what already passed,
every other career (and everything outside the careers) is validated as before.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import game.storage as storage
from game.engine import BUILD, GameError, migrate_state, public_state, stamped
from game.storage import Store, serialize


class ScopedValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'game.db')
        self.token, _, _ = self.store.session()
        self.sid = self.store.key(self.token)
        self.rev = 0
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, action, career='mother_baby', **payload):
        self.n += 1
        out = self.store.command(self.token, f'request-{self.n:04d}', self.rev, career, action, payload)
        self.rev = out['revision']
        return out

    def stored(self):
        with self.store.connect() as db:
            return db.execute('SELECT state FROM sessions WHERE sid=?', (self.sid,)).fetchone()[0]

    def put(self, state):
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state, ensure_ascii=False), self.sid))

    def test_first_command_stamps_the_save_and_the_view_hides_the_stamp(self):
        self.assertFalse(stamped(json.loads(self.stored())))
        out = self.cmd('start_day')
        s = json.loads(self.stored())
        self.assertTrue(stamped(s))
        self.assertEqual(s['check']['build'], BUILD)
        self.assertEqual(set(s['check']['careers']), set(s['careers']))
        self.assertNotIn('check', out['state'])
        self.assertNotIn('check', public_state(s))

    def test_serialize_is_plain_json_dumps(self):
        self.cmd('start_day')
        s = json.loads(self.stored())
        self.assertEqual(self.stored(), json.dumps(s, ensure_ascii=False))
        self.assertEqual(serialize(s, None, True), json.dumps(s, ensure_ascii=False))

    def test_stamped_save_skips_migration(self):
        self.cmd('start_day')
        s = json.loads(self.stored())
        self.assertIs(migrate_state(s, owned=True), s)
        copy = migrate_state(s)
        self.assertIsNot(copy, s)
        self.assertEqual(copy, s)
        s['check']['build'] = 'older-build'
        self.assertFalse(stamped(s))

    def test_idle_career_edited_in_the_database_is_still_rejected(self):
        self.cmd('start_day')
        s = json.loads(self.stored())
        s['careers']['pharmacy']['money'] = -5  # its digest no longer matches
        self.put(s)
        with self.assertRaises(GameError):
            self.cmd('advance')
        self.assertEqual(self.store.read(self.token)[1], 1)

    def test_other_career_changed_by_the_command_is_validated(self):
        self.cmd('start_day')
        real = storage.apply_action

        def corrupt(raw, *a, **k):
            raw, result = real(raw, *a, **k)
            raw['careers']['pharmacy']['stock'] = {'bunny': -3}
            return raw, result
        with mock.patch.object(storage, 'apply_action', corrupt):
            with self.assertRaises(GameError):
                self.cmd('advance')
        self.assertEqual(self.store.read(self.token)[1], 1)

    def test_acting_career_is_validated(self):
        self.cmd('start_day')
        real = storage.apply_action

        def corrupt(raw, *a, **k):
            raw, result = real(raw, *a, **k)
            raw['careers']['mother_baby']['xp'] = -1
            return raw, result
        with mock.patch.object(storage, 'apply_action', corrupt):
            with self.assertRaises(GameError):
                self.cmd('advance')

    def test_outside_the_careers_is_validated(self):
        self.cmd('start_day')
        real = storage.apply_action

        def corrupt(raw, *a, **k):
            raw['settings']['lang'] = 'xx'  # the reducer's own (scoped) validate_state sees it
            return real(raw, *a, **k)
        with mock.patch.object(storage, 'apply_action', corrupt):
            with self.assertRaises(GameError):
                self.cmd('advance')

    def forged(self):
        """An invalid idle career whose digest was forged to match: only a full check sees it."""
        s = json.loads(self.stored())
        s['careers']['pharmacy']['money'] = -5
        piece = json.dumps(s['careers']['pharmacy'], ensure_ascii=False)
        s['check']['careers']['pharmacy'] = storage._digest(piece)
        return s

    def test_periodic_full_check_catches_what_digests_cannot(self):
        self.cmd('start_day')
        self.put(self.forged())
        with mock.patch.object(storage, 'FULL_EVERY', 1):
            with self.assertRaises(GameError):
                self.cmd('advance')

    def test_every_nth_revision_is_checked_in_full(self):
        self.cmd('start_day')
        self.put(self.forged())
        with mock.patch.object(storage, 'FULL_EVERY', 3):
            self.cmd('advance')  # revision 2: scoped, the forged career is trusted
            with self.assertRaises(GameError):
                self.cmd('advance')  # revision 3: full

    def test_new_build_validates_everything_again(self):
        self.cmd('start_day')
        s = self.forged()
        s['check']['build'] = 'older-build'
        self.put(s)
        with self.assertRaises(GameError):
            self.cmd('advance')

    def test_import_never_trusts_a_stamp(self):
        self.cmd('start_day')
        s = self.forged()
        with self.assertRaises(GameError):
            self.cmd('import_save', save={'format': 'mot-ngay-lam-nghe/save-v4', 'state': s})

    def test_scoped_and_full_commands_store_the_same_save(self):
        plays = [('start_day', 'mother_baby', {}), ('advance', 'mother_baby', {}), ('select_career', 'milk_tea', {}),
                 ('start_day', 'milk_tea', {}), ('advance', 'milk_tea', {}), ('end_day', 'milk_tea', {}),
                 ('settings', None, {'lang': 'en'}), ('advance', 'mother_baby', {})]
        saves = []
        for every in (50, 1):
            other = Store(Path(self.tmp.name) / f'g{every}.db')
            token, _, _ = other.session()
            rev = 0
            with mock.patch.object(storage, 'FULL_EVERY', every):
                for i, (action, career, payload) in enumerate(plays):
                    rev = other.command(token, f'req-{i:05d}', rev, career, action, payload)['revision']
            saves.append(other.read(token)[0])
        self.assertEqual(saves[0], saves[1])


if __name__ == '__main__':
    unittest.main()
