"""Operational checks fail before writing to unmatched schemas and clean up children."""
import importlib
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scripts import browser_live_chat


class ToolingSafety(unittest.TestCase):
    def test_check_runner_import_in_spawn_child_does_not_run_the_suite(self):
        values = {'TEST_DATABASE_URL': 'postgresql://test/scratch', 'DATABASE_URL': 'preserve-parent-setting'}
        with patch.dict(os.environ, values), \
                patch.object(unittest.defaultTestLoader, 'discover', side_effect=AssertionError('spawn child rediscovered the entire suite')) as discovery:
            runpy.run_path(str(ROOT / 'scripts' / 'run_checks.py'), run_name='__mp_main__')
            discovery.assert_not_called()
            self.assertEqual(os.environ['DATABASE_URL'], values['DATABASE_URL'])

    def test_existing_live_url_is_refused_before_fixture_creation(self):
        # live_load is a POSIX load harness; bypass its platform-only FD helper here.
        with patch.dict(sys.modules, {'resource': SimpleNamespace()}):
            load = importlib.import_module('scripts.live_load')
        argv = ['live_load.py', '--url', 'ws://127.0.0.1:8770/live',
                '--db-url', 'postgresql://test@127.0.0.1/mnl_loadtest', '--conns', '0']
        with patch.object(sys, 'argv', argv), patch.object(load, 'raise_fd_limit'), \
                patch.object(load.tempfile, 'mkdtemp', return_value='unwritten-scratch') as scratch, \
                patch.object(load, 'make_players', side_effect=SystemExit('fixture creation reached')) as players:
            with self.assertRaises(SystemExit) as error:
                load.main()
            self.assertRegex(str(error.exception), r'--url.*isolated.*schema')
            scratch.assert_not_called()
            players.assert_not_called()

    def test_failed_game_health_stops_its_child(self):
        game = Mock()
        game.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(browser_live_chat, 'test_env', return_value={'TEST_DATABASE_URL': 'postgresql://test/scratch'}), \
                patch.object(browser_live_chat.subprocess, 'Popen', return_value=game) as popen, \
                patch.object(browser_live_chat, 'wait_http', side_effect=SystemExit('game health failed')):
            with self.assertRaisesRegex(SystemExit, 'game health failed'):
                with browser_live_chat.servers(tmp):
                    self.fail('an unhealthy game must not be yielded')
            self.assertEqual(popen.call_count, 1)
            game.terminate.assert_called_once()
            game.wait.assert_called_once()

    def test_failed_live_health_stops_both_children_and_closes_log(self):
        game, live = Mock(), Mock()
        game.poll.return_value = live.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(browser_live_chat, 'test_env', return_value={'TEST_DATABASE_URL': 'postgresql://test/scratch'}), \
                patch.object(browser_live_chat, 'schema_for', return_value='matching_scratch_schema'), \
                patch.object(browser_live_chat.subprocess, 'Popen', side_effect=[game, live]) as popen, \
                patch.object(browser_live_chat, 'wait_http', side_effect=[None, SystemExit('live health failed')]):
            try:
                with self.assertRaisesRegex(SystemExit, 'live health failed'):
                    with browser_live_chat.servers(tmp):
                        self.fail('an unhealthy live service must not be yielded')
                for child in (game, live):
                    child.terminate.assert_called_once()
                    child.wait.assert_called_once()
                self.assertTrue(popen.call_args_list[1].kwargs['stdout'].closed)
            finally:
                # Keep the failing regression from leaking its real temporary log.
                popen.call_args_list[1].kwargs['stdout'].close()

    def test_failed_startup_kills_child_if_termination_times_out(self):
        game = Mock()
        game.poll.return_value = None
        game.wait.side_effect = [browser_live_chat.subprocess.TimeoutExpired('game', 5), None]
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(browser_live_chat, 'test_env', return_value={'TEST_DATABASE_URL': 'postgresql://test/scratch'}), \
                patch.object(browser_live_chat.subprocess, 'Popen', return_value=game), \
                patch.object(browser_live_chat, 'wait_http', side_effect=SystemExit('game health failed')):
            with self.assertRaisesRegex(SystemExit, 'game health failed'):
                with browser_live_chat.servers(tmp):
                    self.fail('an unhealthy game must not be yielded')
            game.terminate.assert_called_once()
            game.kill.assert_called_once()
            self.assertEqual(game.wait.call_count, 2)
