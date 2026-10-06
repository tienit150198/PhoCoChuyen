"""Queue commands before loading saves, not while holding several large copies."""
import concurrent.futures
import contextvars
import os
import threading
import time
import unittest
from unittest.mock import patch

from game import storage


class CommandAdmissionTests(unittest.TestCase):
    def test_stores_share_a_bounded_process_budget(self):
        release = threading.Event()
        lock = threading.Condition()
        entered = 0
        peak = 0
        active = 0
        callers = set()
        workers = set()
        stores = [object.__new__(storage.Store) for _ in range(2)]

        def work(*args):
            nonlocal entered, peak, active
            with lock:
                entered += 1
                active += 1
                workers.add(threading.current_thread())
                peak = max(peak, active)
                lock.notify_all()
            try:
                if not release.wait(5):
                    raise TimeoutError('test did not release commands')
                return {'replayed': True}
            finally:
                with lock:
                    active -= 1

        for store in stores:
            store._command = work
        def call(i):
            with lock:
                callers.add(threading.current_thread())
            return stores[i % 2].command('token', 'request-001', 0, None, 'noop', {})
        with patch.object(storage, '_COMMAND_GATE', threading.BoundedSemaphore(2), create=True), \
             patch.object(storage.kpi, 'econ_drop'), \
             concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(call, i) for i in range(6)]
            try:
                with lock:
                    self.assertTrue(lock.wait_for(lambda: entered >= 2, timeout=3))
                # The other callers have time to reach the gate while both slots are held.
                time.sleep(.2)
                with lock:
                    self.assertEqual(entered, 2)
            finally:
                release.set()
            for future in futures:
                self.assertEqual(future.result(timeout=3), {'replayed': True})
        self.assertEqual(entered, 6)
        self.assertEqual(peak, 2)
        self.assertFalse(callers & workers, 'large save buffers must use reusable worker threads')

    def test_failed_validation_and_failed_command_release_the_slot(self):
        store = object.__new__(storage.Store)
        gate = threading.BoundedSemaphore(1)
        with patch.object(storage, '_COMMAND_GATE', gate, create=True), \
             patch.object(storage.kpi, 'econ_drop'):
            for failure in (storage.GameError('test failure'), RuntimeError('test failure'), SystemExit(1)):
                with patch.object(store, '_command', side_effect=failure):
                    with self.assertRaises(type(failure)):
                        store.command('token', 'request-001', 0, None, 'noop', {})
                self.assertTrue(gate.acquire(blocking=False))
                gate.release()
            with self.assertRaises(storage.GameError):
                store.command('token', 'bad', 0, None, 'noop', {})
            self.assertTrue(gate.acquire(blocking=False))
            gate.release()

    def test_nested_command_reuses_slot_and_preserves_context(self):
        store = object.__new__(storage.Store)
        context = contextvars.ContextVar('test_command_context', default='missing')
        token = context.set('caller context')
        def work(_h, _who, _request_id, _revision, _career, action, *_args):
            self.assertEqual(context.get(), 'caller context')
            if action == 'outer':
                return store.command('token', 'nested-001', 0, None, 'inner', {})
            return {'replayed': True}
        store._command = work
        try:
            with patch.object(storage, '_COMMAND_GATE', threading.BoundedSemaphore(1)), \
                 patch.object(storage.kpi, 'econ_drop'):
                self.assertEqual(store.command('token', 'request-001', 0, None, 'outer', {}),
                                 {'replayed': True})
        finally:
            context.reset(token)

    @unittest.skipUnless(hasattr(os, 'fork'), 'prefork production server runs on POSIX')
    def test_child_does_not_inherit_exhausted_parent_budget(self):
        import select
        import signal
        store = object.__new__(storage.Store)
        store._command = lambda *args: {'replayed': True}
        # Exercise the pool before fork: its parent threads will not exist in the child.
        with patch.object(storage.kpi, 'econ_drop'):
            store.command('token', 'request-001', 0, None, 'noop', {})
        read_fd, write_fd = os.pipe()
        with patch.object(storage, '_COMMAND_GATE', threading.BoundedSemaphore(1), create=True):
            storage._COMMAND_GATE.acquire()
            pid = os.fork()
            if pid == 0:
                os.close(read_fd)
                with patch.object(storage.kpi, 'econ_drop'):
                    result = store.command('token', 'request-002', 0, None, 'noop', {})
                os.write(write_fd, b'1' if result.get('replayed') else b'0')
                os._exit(0)
            os.close(write_fd)
            try:
                self.assertTrue(select.select([read_fd], [], [], 5)[0], 'forked command pool is blocked')
                self.assertEqual(os.read(read_fd, 1), b'1')
            finally:
                os.close(read_fd)
                # Killing an already-exited child has no effect; never leave a failed child waiting.
                try:os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid, 0)
                storage._COMMAND_GATE.release()
