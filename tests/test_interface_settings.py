"""Interface choice follows the save without changing the player's progress."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from game.engine import BUILD, GameError, apply_action, migrate_state, new_state, public_state, validate_state


class InterfaceSettingsTests(unittest.TestCase):
    def test_new_player_defaults_to_new_interface_with_unseen_prompt(self):
        state = new_state()
        settings = public_state(state)['settings']
        self.assertIs(settings.get('newInterface'), True)
        self.assertIs(settings.get('interfacePromptSeen'), False)
        self.assertNotIn('newInterface', state['settings'])
        self.assertNotIn('interfacePromptSeen', state['settings'])

    def test_migration_keeps_a_deliberate_classic_choice(self):
        state = new_state()
        state['settings'].update(newInterface=False, interfacePromptSeen=True)
        for _ in range(2):
            state = migrate_state(state)
            self.assertNotIn('newInterface', state['settings'])
            self.assertNotIn('interfacePromptSeen', state['settings'])
            self.assertEqual(state['journey']['interface'], dict(newInterface=False, interfacePromptSeen=True))
            self.assertIs(public_state(state)['settings']['newInterface'], False)
            self.assertIs(public_state(state)['settings']['interfacePromptSeen'], True)

    def test_migration_also_removes_draft_keys_from_a_stamped_save(self):
        state = new_state()
        state['check'] = {'build': BUILD}
        state['settings'].update(newInterface=False, interfacePromptSeen=True)
        migrated = migrate_state(state)
        self.assertNotIn('newInterface', migrated['settings'])
        self.assertEqual(migrated['journey']['interface'], dict(newInterface=False, interfacePromptSeen=True))

    def test_migration_keeps_canonical_preference_if_draft_settings_also_exist(self):
        state = new_state()
        state['journey']['interface'] = dict(newInterface=False, interfacePromptSeen=True)
        state['settings'].update(newInterface=True, interfacePromptSeen=False)
        migrated = migrate_state(state)
        self.assertNotIn('newInterface', migrated['settings'])
        self.assertEqual(migrated['journey']['interface'], dict(newInterface=False, interfacePromptSeen=True))

    def test_older_saves_receive_defaults_without_resetting_progress(self):
        state = new_state()
        state['settings'].pop('newInterface', None)
        state['settings'].pop('interfacePromptSeen', None)
        state['careers']['mother_baby']['money'] = 1234
        migrated = migrate_state(state)
        self.assertIs(public_state(migrated)['settings'].get('newInterface'), True)
        self.assertIs(public_state(migrated)['settings'].get('interfacePromptSeen'), False)
        self.assertEqual(migrated['careers']['mother_baby']['money'], 1234)

    def test_switching_both_ways_preserves_progress_and_round_trips_the_save(self):
        state, _ = apply_action(new_state(), None, 'settings', {})
        validate_state(state)  # stock validators normalize opening lots before the stored baseline
        progress = copy.deepcopy((state['careers'], state['journey']))
        for enabled in (False, True, False):
            state, _ = apply_action(state, None, 'settings', {
                'newInterface': enabled, 'interfacePromptSeen': True,
            })
            state = migrate_state(json.loads(json.dumps(state)))
            self.assertEqual((state['careers'], {k: v for k, v in state['journey'].items() if k != 'interface'}), progress)
            self.assertIs(public_state(state)['settings']['newInterface'], enabled)
            self.assertIs(public_state(state)['settings']['interfacePromptSeen'], True)
            self.assertNotIn('newInterface', state['settings'])
            validate_state(state)

    def test_interface_flags_reject_non_booleans_on_command_and_import(self):
        for key in ('newInterface', 'interfacePromptSeen'):
            for bad in (0, 1, 'false', None):
                with self.subTest(key=key, value=bad):
                    with self.assertRaises(GameError):
                        apply_action(new_state(), None, 'settings', {key: bad})
                    state = new_state()
                    state['settings'][key] = bad
                    with self.assertRaises(GameError):
                        validate_state(state)
                    with self.assertRaises(GameError):
                        migrate_state(state)
                    state = new_state()
                    state['journey']['interface'] = {key: bad}
                    with self.assertRaises(GameError):
                        validate_state(state)

    def test_invalid_interface_namespace_is_rejected(self):
        for value in (None, [], 'false', {'unexpected': True}):
            with self.subTest(value=value):
                state = new_state()
                state['journey']['interface'] = value
                with self.assertRaises(GameError):
                    validate_state(state)

    def test_public_projection_does_not_add_keys_to_persisted_settings(self):
        state, _ = apply_action(new_state(), None, 'settings', dict(newInterface=False, interfacePromptSeen=True))
        raw = copy.deepcopy(state['settings'])
        projected = public_state(state, migrated=True)
        projected['settings']['newInterface'] = True
        self.assertEqual(state['settings'], raw)
        self.assertIs(state['journey']['interface']['newInterface'], False)

    def test_rollback_release_keeps_preference_when_validating_and_changing_settings(self):
        root = Path(__file__).resolve().parents[1]
        state, _ = apply_action(new_state(), None, 'settings', dict(newInterface=False, interfacePromptSeen=True))
        tree = subprocess.run(['git', 'archive', 'e4ea7eba', 'game', 'reference'], cwd=root,
                              capture_output=True, timeout=120, check=True).stdout
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as old:
            with tarfile.open(fileobj=io.BytesIO(tree)) as archive:
                archive.extractall(old, filter='data')
            script = ('import json,sys; from game.engine import validate_state,migrate_state,public_state,apply_action;'
                      's=json.load(sys.stdin);validate_state(s);s=migrate_state(s);validate_state(s);public_state(s);'
                      's,_=apply_action(s,None,"settings",{"sound":False});validate_state(s);print(json.dumps(s))')
            env = dict(os.environ, PYTHONPATH=old)
            result = subprocess.run([sys.executable, '-c', script], input=json.dumps(state), capture_output=True,
                                    text=True, cwd=old, env=env, encoding='utf-8', timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        restored = migrate_state(json.loads(result.stdout))
        self.assertEqual(restored['journey']['interface'], dict(newInterface=False, interfacePromptSeen=True))
        self.assertIs(restored['settings']['sound'], False)
        self.assertIs(public_state(restored)['settings']['newInterface'], False)


if __name__ == '__main__':
    unittest.main()
