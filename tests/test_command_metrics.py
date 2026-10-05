"""Bounded operator timings; no database is required for this instrumentation."""
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import command_metrics as cm
from game import admin_stats
from game.storage import Store, Conflict


class SignatureStore:
    def __init__(self, path):
        self.path = path
        self.calls = []
        self.receipt = {'result': {'message': 'private receipt'}, 'replayed': True}
        self.error = None

    def command(self, token, request_id, expected, career, action, payload, internal=False):
        self.calls.append((token, request_id, expected, career, action, payload, internal))
        if self.error is not None:
            raise self.error
        return self.receipt


class CommandMetricsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.db'
        self.store = SignatureStore(self.path)
        self.now = int(time.time() // 60) * 60 + 1.0

    def collector(self, pid=123):
        return cm.CommandMetrics(self.path, pid=pid)

    def test_positional_keyword_and_mixed_actions_preserve_returns_and_arguments(self):
        self.assertEqual(list(inspect.signature(Store.command).parameters),
                         list(inspect.signature(SignatureStore.command).parameters))
        cm.install_command_metrics(self.store)
        payload = {'body': 'private player data'}
        self.assertIs(self.store.command('secret-token', 'receipt-id', 7, 'private-career',
                                         'start_day', payload), self.store.receipt)
        self.assertIs(self.store.command(token='secret-token', request_id='receipt-id',
                                         expected=7, career=None, action='end_day',
                                         payload=payload, internal=True), self.store.receipt)
        self.store.command('secret-token', 'receipt-id', 7, None, action='settings', payload=payload)
        result = cm.read_command_metrics(self.store)
        self.assertEqual(set(result['actions']), {'start_day', 'end_day', 'settings'})
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['errors'], 0)
        self.assertIs(self.store.calls[0][5], payload)
        self.assertTrue(self.store.calls[1][-1])
        serialized = json.dumps(self.store._command_metrics.snapshot())
        for private in ('secret-token', 'receipt-id', 'private-career', 'private player data', 'private receipt'):
            self.assertNotIn(private, serialized)

    def test_original_exception_identity_is_preserved_and_counted(self):
        cm.install_command_metrics(self.store)
        error = Conflict('private failure detail', 'revision_conflict')
        self.store.error = error
        with self.assertRaises(Conflict) as raised:
            self.store.command('t', 'r', 1, None, 'start_day', {})
        self.assertIs(raised.exception, error)
        result = cm.read_command_metrics(self.store)
        self.assertEqual((result['count'], result['errors']), (1, 1))
        self.assertNotIn('private failure detail', json.dumps(result))

    def test_real_store_public_command_keeps_receipt_replay_and_validation_contract(self):
        store = object.__new__(Store)
        store.path = self.path
        first = {'result': {'message': 'private receipt'}, 'revision': 2, 'replayed': False}
        replay = {**first, 'replayed': True}
        cm.install_command_metrics(store)
        with patch.object(store, '_command', side_effect=[first, replay]) as execute, \
                patch('game.storage.kpi.econ_commit'):
            self.assertIs(store.command('token', 'request-id', None, None, 'settings', {}, internal=True), first)
            self.assertIs(store.command(token='token', request_id='request-id', expected=None,
                                        career=None, action='settings', payload={}, internal=True), replay)
            self.assertEqual(execute.call_count, 2)
        with self.assertRaises(Exception) as failure:
            store.command('token', 'bad', 1, None, 'start_day', {})
        self.assertEqual(type(failure.exception).__name__, 'GameError')
        result = cm.read_command_metrics(store)
        self.assertEqual((result['count'], result['errors']), (3, 1))
        self.assertEqual(result['actions']['settings']['count'], 2)

    def test_both_wrapper_install_orders_are_idempotent_and_keep_admin_counters(self):
        for admin_first in (False, True):
            store = SignatureStore(self.path)
            if admin_first:
                admin_stats.install_command_timer(store)
            cm.install_command_metrics(store)
            admin_stats.install_command_timer(store)
            cm.install_command_metrics(store)
            with patch.object(admin_stats, 'record_command') as old_counter, patch.object(admin_stats.kpi, 'add'):
                store.command('t', 'r', 1, None, 'settings', {})
            self.assertEqual(old_counter.call_count, 1)
            self.assertEqual(cm.read_command_metrics(store)['count'], 1)

    def test_whole_existing_command_is_timed_including_existing_wrapper(self):
        clock = [100.0]
        real = self.store.command
        def existing(*args, **kwargs):
            clock[0] += 0.200
            result = real(*args, **kwargs)
            clock[0] += 0.300
            return result
        self.store.command = existing
        cm.install_command_metrics(self.store)
        with patch.object(cm.time, 'perf_counter', side_effect=lambda: clock[0]):
            self.store.command('t', 'r', 1, None, 'start_day', {})
        self.assertAlmostEqual(cm.read_command_metrics(self.store)['actions']['start_day']['total_ms'], 500)

    def test_telemetry_failure_cannot_change_result_or_mask_command_error(self):
        cm.install_command_metrics(self.store)
        with patch.object(self.store._command_metrics, 'record', side_effect=OSError('disk unavailable')):
            self.assertIs(self.store.command('t', 'r', 1, None, 'settings', {}), self.store.receipt)
            self.store.error = RuntimeError('command failed')
            with self.assertRaises(RuntimeError) as raised:
                self.store.command('t', 'r', 1, None, 'settings', {})
            self.assertIs(raised.exception, self.store.error)

    def test_histograms_merge_and_percentiles_are_bounded_by_actual_maximum(self):
        one, two = self.collector(101), self.collector(102)
        for ms in (10, 20, 100, 1000):
            one.record('start_day', ms, False, now=self.now)
        two.record('start_day', 50000, True, now=self.now)
        one.flush(now=self.now, force=True)
        two.flush(now=self.now, force=True)
        result = cm.read_command_metrics(self.path, now=self.now)
        row = result['actions']['start_day']
        self.assertEqual((row['count'], row['errors'], row['total_ms'], row['max_ms']), (5, 1, 51130, 50000))
        self.assertEqual(sum(row['histogram']), 5)
        self.assertLessEqual(row['p50_ms'], row['p95_ms'])
        self.assertLessEqual(row['p95_ms'], row['p99_ms'])
        self.assertLessEqual(row['p99_ms'], row['max_ms'])
        self.assertEqual((result['count'], result['workers']), (5, 2))
        self.assertEqual(cm.read_command_metrics(self.path, now=self.now), result)

    def test_live_memory_replaces_own_file_without_double_count(self):
        collector = cm.install_command_metrics(self.store)
        collector.record('settings', 10, False, now=self.now)
        collector.flush(now=self.now, force=True)
        collector.record('settings', 15, False, now=self.now + 1)
        result = cm.read_command_metrics(self.store, now=self.now + 1)
        self.assertEqual((result['count'], result['workers']), (2, 1))
        self.assertEqual(cm.read_command_metrics(self.path, now=self.now + 1)['count'], 1)

    def test_action_cardinality_syntax_and_window_are_bounded(self):
        collector = self.collector()
        for i in range(cm.MAX_ACTIONS + 50):
            collector.record('action_' + str(i), 20, False, now=self.now)
        for bad in (None, {}, 'token value', 'x' * 1000, 'private@example.com', '漢字', 'WITH_UPPERCASE'):
            collector.record(bad, 20, True, now=self.now)
        snapshot = collector.snapshot(now=self.now)
        rows = next(iter(snapshot['minutes'].values()))
        self.assertEqual(len(rows), cm.MAX_ACTIONS + 1)
        self.assertIn(cm.OVERFLOW_ACTION, rows)
        self.assertNotIn('private@example.com', json.dumps(snapshot))
        later = self.now + cm.WINDOW_MINUTES * 60
        collector.record('new_action', 30, False, now=later)
        result = cm.merge_snapshots([collector.snapshot(now=later)], now=later)
        self.assertEqual(set(result['actions']), {'new_action'})
        self.assertEqual(result['count'], 1)

    def test_sidecar_remains_small_at_full_window_and_atomic_replaces_one_pid_file(self):
        collector = self.collector()
        for minute in range(cm.WINDOW_MINUTES):
            for index in range(cm.MAX_ACTIONS + 1):
                action = 'a' * 35 + '_' + str(index)
                collector.record(action, 1234.567, index % 2 == 0, now=self.now + minute * 60)
        collector.flush(now=self.now + (cm.WINDOW_MINUTES - 1) * 60, force=True)
        paths = list(Path(self.tmp.name).glob('*-command-metrics.*.json'))
        self.assertEqual(len(paths), 1)
        self.assertLess(paths[0].stat().st_size, cm.MAX_FILE_BYTES)
        self.assertEqual(list(Path(self.tmp.name).glob('*.tmp')), [])
        result = cm.read_command_metrics(self.path, now=self.now + (cm.WINDOW_MINUTES - 1) * 60)
        self.assertEqual(result['count'], (cm.MAX_ACTIONS + 1) * cm.WINDOW_MINUTES)
        self.assertEqual(len(result['actions']), cm.MAX_ACTIONS + 1)

    def test_supports_1024_actions_without_truncating_15_minute_window(self):
        self.assertEqual(cm.MAX_ACTIONS, 1024)
        self.assertEqual(cm.MAX_FILE_BYTES, 4 * 1024 * 1024)
        collector = self.collector()
        for minute in range(cm.WINDOW_MINUTES):
            for index in range(1024):
                collector.record('action_' + str(index), 120.0 + index, False, now=self.now + minute * 60)
        collector.flush(now=self.now + 14 * 60, force=True)
        result = cm.read_command_metrics(self.path, now=self.now + 14 * 60)
        self.assertEqual((result['count'], len(result['actions'])), (1024 * 15, 1024))
        self.assertLess(next(Path(self.tmp.name).glob('*-command-metrics.*.json')).stat().st_size, cm.MAX_FILE_BYTES)

    def test_worker_merge_preserves_fair_actions_after_more_than_256_other_actions(self):
        one, two = self.collector(101), self.collector(102)
        for index in range(500):
            one.record('action_' + str(index), 20, False, now=self.now)
        two.record('fair_kn_throw', 75, False, now=self.now)
        result = cm.merge_snapshots([one.snapshot(now=self.now), two.snapshot(now=self.now)], now=self.now)
        self.assertEqual((result['count'], len(result['actions'])), (501, 501))
        self.assertEqual(result['actions']['fair_kn_throw']['count'], 1)
        self.assertNotIn(cm.OVERFLOW_ACTION, result['actions'])

    def test_flush_is_throttled_and_stale_worker_files_are_pruned(self):
        collector = self.collector()
        collector.record('settings', 10, False, now=self.now)
        path = next(Path(self.tmp.name).glob('*-command-metrics.*.json'))
        original = path.read_bytes()
        collector.record('settings', 20, False, now=self.now + cm.FLUSH_SECONDS - 1)
        self.assertEqual(path.read_bytes(), original)
        stale = self.collector(222)
        stale.record('settings', 99, False, now=self.now - 7200)
        stale_path = Path(str(self.path) + '-command-metrics.222.json')
        os.utime(stale_path, (self.now - 7200, self.now - 7200))
        collector.record('settings', 30, False, now=self.now + cm.FLUSH_SECONDS)
        self.assertNotEqual(path.read_bytes(), original)
        self.assertFalse(stale_path.exists())

    def test_merger_rejects_stale_future_malformed_and_duplicate_worker_snapshots(self):
        collector = self.collector()
        collector.record('settings', 10, False, now=self.now)
        snapshot = collector.snapshot(now=self.now)
        result = cm.merge_snapshots([snapshot, snapshot, {}, {'minutes': []}], now=self.now)
        self.assertEqual(result['count'], 1)
        self.assertEqual(cm.merge_snapshots([snapshot], now=self.now + 7200)['count'], 0)
        self.assertEqual(cm.merge_snapshots([snapshot], now=self.now - 7200)['count'], 0)

    def test_reader_skips_corrupt_or_oversized_sidecars(self):
        self.collector().record('settings', 10, False, now=self.now)
        for pid, content in ((998, '{'), (999, ' ' * (cm.MAX_FILE_BYTES + 1))):
            Path(str(self.path) + f'-command-metrics.{pid}.json').write_text(content)
        self.assertEqual(cm.read_command_metrics(self.path, now=self.now)['count'], 1)

    def test_atomic_write_failure_keeps_previous_snapshot_and_removes_temporary_file(self):
        collector = self.collector()
        collector.record('settings', 10, False, now=self.now)
        path = Path(str(self.path) + '-command-metrics.123.json')
        previous = path.read_bytes()
        collector.record('settings', 20, False, now=self.now + 1)
        with patch.object(cm.os, 'replace', side_effect=OSError('unwritable')):
            collector.flush(now=self.now + 1, force=True)
        self.assertEqual(path.read_bytes(), previous)
        self.assertFalse(Path(str(path) + '.tmp').exists())

    def test_stale_temporary_files_from_stopped_workers_are_pruned(self):
        stale = Path(str(self.path) + '-command-metrics.999.json.tmp')
        stale.write_text('interrupted snapshot')
        os.utime(stale, (self.now - 7200, self.now - 7200))
        self.collector().record('settings', 10, False, now=self.now)
        self.assertFalse(stale.exists())

    def test_prefork_collector_resets_in_child_without_reusing_parent_pid_or_counts(self):
        collector = self.collector()
        collector.record('settings', 10, False, now=self.now)
        with patch.object(cm.os, 'getpid', return_value=124):
            collector._after_fork()
        collector.record('start_day', 20, False, now=self.now)
        snapshot = collector.snapshot(now=self.now)
        self.assertEqual(snapshot['pid'], 124)
        self.assertEqual(set(next(iter(snapshot['minutes'].values()))), {'start_day'})
        self.assertEqual(cm.read_command_metrics(self.path, now=self.now)['workers'], 2)

    def test_concurrent_recorders_keep_every_command(self):
        collector = self.collector()
        threads = [threading.Thread(target=lambda: [collector.record('settings', 5, False, now=self.now)
                                                     for _ in range(200)]) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        result = cm.merge_snapshots([collector.snapshot(now=self.now)], now=self.now)
        self.assertEqual((result['count'], result['total_ms']), (1600, 8000))

    def test_server_installs_after_admin_timer_and_flushes_on_close(self):
        import server
        with patch.object(server.social, 'ensure'), patch.object(server.push, 'ensure'), \
                patch.object(server.admin_stats, 'ensure', side_effect=admin_stats.install_command_timer), \
                patch.object(server.admin_stats, 'stop_jobs'), patch.object(server.retention, 'flush'), \
                patch.object(server.kpi, 'flush'), patch.object(server.kpi, 'add'):
            http_server = server.GameServer(('127.0.0.1', 0), self.store)
            try:
                self.store.command('t', 'r', 1, None, 'settings', {})
                self.store.command('t', 'r', 1, None, 'settings', {})
            finally:
                http_server.server_close()
        self.assertEqual(cm.read_command_metrics(self.path)['count'], 2)


if __name__ == '__main__':
    unittest.main()
