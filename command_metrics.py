"""Bounded, aggregate timings around the complete Store.command call.

One atomic <store.path>-command-metrics.<pid>.json snapshot per worker, refreshed
by command traffic at most every 30 seconds (and on orderly server close). No
database queries, request bodies, identifiers, careers or error text are stored.
The last 15 UTC minute buckets include the current partial minute; percentiles
are histogram upper-bound estimates, capped by the actual maximum. These are
whole-command timings, not HTTP response times or timings of individual phases.

Operators can call read_command_metrics(store_path) in a separate process. When
passed the live store instead, its memory replaces its own file, never adds to it.
"""
from __future__ import annotations

import bisect
from functools import wraps
import glob
import json
import math
import os
import re
import threading
import time

WINDOW_MINUTES = 15
FLUSH_SECONDS = 30.0
MAX_ACTIONS = 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_WORKER_FILES = 128
OVERFLOW_ACTION = '__other__'
EDGES_MS = (2, 5, 10, 20, 40, 75, 100, 150, 250, 400, 750, 1000, 1500, 2500, 5000, 10000)
_ACTION = re.compile(r'[a-z][a-z0-9_]{0,39}\Z', re.ASCII)


def _prefix(path) -> str:
    return str(path) + '-command-metrics.'


def _empty_row():
    # count, errors, total_ms, max_ms, histogram; compact on disk.
    return [0, 0, 0.0, 0.0, [0] * (len(EDGES_MS) + 1)]


def _action(value):
    return value if isinstance(value, str) and _ACTION.fullmatch(value) else OVERFLOW_ACTION


class CommandMetrics:
    def __init__(self, path, *, pid=None):
        self.path = str(path)
        self.pid = os.getpid() if pid is None else pid
        self._lock = threading.Lock()
        self._flush_lock = threading.Lock()
        self._minutes = {}
        self._actions = set()
        self._minute = None
        self._last_flush = None
        if pid is None and hasattr(os, 'register_at_fork'):
            os.register_at_fork(after_in_child=self._after_fork)

    def _after_fork(self):
        # GameServer installs before serve_workers forks. Locks and counters from
        # the parent belong to no child; each child needs its own file and locks.
        self.pid = os.getpid()
        self._lock = threading.Lock()
        self._flush_lock = threading.Lock()
        self._minutes = {}
        self._actions = set()
        self._minute = None
        self._last_flush = None

    def _prune(self, minute):
        if self._minute == minute:
            return
        self._minute = minute
        self._minutes = {m: rows for m, rows in self._minutes.items()
                         if minute - WINDOW_MINUTES < m <= minute}
        self._actions = {name for rows in self._minutes.values() for name in rows
                         if name != OVERFLOW_ACTION}

    def record(self, action, ms, failed=False, *, now=None):
        now = time.time() if now is None else now
        minute = int(now // 60)
        name = _action(action)
        ms = max(0.0, float(ms))
        if not math.isfinite(ms):
            return
        with self._lock:
            self._prune(minute)
            if name != OVERFLOW_ACTION and name not in self._actions:
                if len(self._actions) >= MAX_ACTIONS:
                    name = OVERFLOW_ACTION
                else:
                    self._actions.add(name)
            rows = self._minutes.setdefault(minute, {})
            row = rows.get(name)
            if row is None:
                row = rows[name] = _empty_row()
            row[0] += 1
            row[1] += bool(failed)
            row[2] += ms
            row[3] = max(row[3], ms)
            row[4][bisect.bisect_left(EDGES_MS, ms)] += 1
            due = self._last_flush is None or now - self._last_flush >= FLUSH_SECONDS
        if due:
            self.flush(now=now)

    def snapshot(self, *, now=None):
        now = time.time() if now is None else now
        with self._lock:
            self._prune(int(now // 60))
            return {'version': 1, 'pid': self.pid, 'at': round(now, 3),
                    'minutes': {str(m): {name: [row[0], row[1], round(row[2], 3),
                                               round(row[3], 3), list(row[4])]
                                         for name, row in rows.items()}
                                for m, rows in self._minutes.items()}}

    def flush(self, *, now=None, force=False):
        """Best effort, serialized writes; callers never wait for another flusher."""
        now = time.time() if now is None else now
        if not self._flush_lock.acquire(blocking=False):
            return
        temporary = None
        try:
            with self._lock:
                if not force and self._last_flush is not None and now - self._last_flush < FLUSH_SECONDS:
                    return
                # Throttle failures too: an unwritable directory must not cost a write per command.
                self._last_flush = now
            data = self.snapshot(now=now)
            encoded = json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
            # A full 1024-action window is about 1 MB. Keep a hard bound even if
            # implausibly large counters/durations arrive through a manual caller.
            while len(encoded) > MAX_FILE_BYTES and data['minutes']:
                del data['minutes'][min(data['minutes'], key=int)]
                encoded = json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
            target = _prefix(self.path) + str(self.pid) + '.json'
            temporary = target + '.tmp'
            with open(temporary, 'wb') as output:
                output.write(encoded)
            os.replace(temporary, target)
            temporary = None
            # Remove only inactive worker snapshots older than the retained window.
            # Existing worker files and this worker's file are never removed here.
            cutoff = now - (WINDOW_MINUTES + 1) * 60
            for path in glob.iglob(glob.escape(_prefix(self.path)) + '*.json*'):
                if not path.endswith(('.json', '.json.tmp')):
                    continue
                if path == target:
                    continue
                try:
                    if os.stat(path).st_mtime < cutoff:
                        os.unlink(path)
                except OSError:
                    pass
        except (OSError, ValueError, OverflowError):
            pass
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            self._flush_lock.release()


def install_command_metrics(store):
    """Wrap once, outside existing instrumentation; preserve the command contract."""
    existing = getattr(store, '_command_metrics', None)
    if isinstance(existing, CommandMetrics):
        return existing
    real = getattr(store, 'command', None)
    if not callable(real):
        return None
    collector = CommandMetrics(store.path)

    @wraps(real)
    def command(*args, **kwargs):
        # Bound Store.command(token, request_id, expected, career, action, payload,
        # internal=False): never inspect any other argument or the response body.
        action = args[4] if len(args) > 4 else kwargs.get('action')
        started = time.perf_counter()
        failed = True
        try:
            result = real(*args, **kwargs)
            failed = False
            return result
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            try:
                collector.record(action, elapsed, failed)
            except Exception:
                pass  # telemetry must neither replace a result nor mask an error

    store.command = command
    store._command_metrics = collector
    return collector


def flush_command_metrics(store):
    collector = getattr(store, '_command_metrics', None)
    if isinstance(collector, CommandMetrics):
        collector.flush(force=True)


def _valid_row(row):
    if not isinstance(row, list) or len(row) != 5:
        return False
    count, errors, total, maximum, hist = row
    return (type(count) is int and count >= 0 and type(errors) is int and 0 <= errors <= count
            and type(total) in (int, float) and math.isfinite(total) and total >= 0
            and type(maximum) in (int, float) and math.isfinite(maximum) and 0 <= maximum <= total
            and isinstance(hist, list) and len(hist) == len(EDGES_MS) + 1
            and all(type(n) is int and n >= 0 for n in hist) and sum(hist) == count)


def _percentile(row, quantile):
    if not row[0]:
        return None
    rank = math.ceil(row[0] * quantile)
    seen = 0
    for index, count in enumerate(row[4]):
        seen += count
        if seen >= rank:
            return min(row[3], EDGES_MS[index]) if index < len(EDGES_MS) else row[3]
    return row[3]


def _report(row):
    return {'count': row[0], 'errors': row[1], 'total_ms': round(row[2], 3),
            'max_ms': round(row[3], 3), 'avg_ms': round(row[2] / row[0], 3) if row[0] else None,
            'p50_ms': _percentile(row, .50), 'p95_ms': _percentile(row, .95),
            'p99_ms': _percentile(row, .99), 'histogram': list(row[4])}


def merge_snapshots(snapshots, *, now=None):
    """Merge latest snapshot per PID, with fixed minute/action cardinality limits."""
    now = time.time() if now is None else now
    minute = int(now // 60)
    latest = {}
    for snapshot in snapshots:
        if not isinstance(snapshot, dict) or snapshot.get('version') != 1:
            continue
        pid, at = snapshot.get('pid'), snapshot.get('at')
        if type(pid) is not int or type(at) not in (int, float) or not math.isfinite(at):
            continue
        if at > now + 60 or at < (minute - WINDOW_MINUTES + 1) * 60:
            continue
        if not isinstance(snapshot.get('minutes'), dict):
            continue
        if pid in latest and at <= latest[pid]['at']:
            continue
        if pid not in latest and len(latest) >= MAX_WORKER_FILES:
            continue
        latest[pid] = snapshot
    actions, total, workers = {}, _empty_row(), 0
    for snapshot in latest.values():
        used = False
        for key, rows in snapshot['minutes'].items():
            try:
                bucket = int(key)
            except (TypeError, ValueError):
                continue
            if not minute - WINDOW_MINUTES < bucket <= minute or not isinstance(rows, dict):
                continue
            for name, row in rows.items():
                if not _valid_row(row):
                    continue
                name = _action(name)
                named_count = len(actions) - (OVERFLOW_ACTION in actions)
                if name not in actions and name != OVERFLOW_ACTION and named_count >= MAX_ACTIONS:
                    name = OVERFLOW_ACTION
                action = actions.setdefault(name, _empty_row())
                for target in (action, total):
                    target[0] += row[0]
                    target[1] += row[1]
                    target[2] += row[2]
                    target[3] = max(target[3], row[3])
                    for index, count in enumerate(row[4]):
                        target[4][index] += count
                used |= row[0] > 0
        workers += used
    return {'at': now, 'window_minutes': WINDOW_MINUTES, 'workers': workers,
            'histogram_edges_ms': list(EDGES_MS), **_report(total),
            'actions': {name: _report(row) for name, row in sorted(actions.items())}}


def read_command_metrics(store_or_path, *, now=None):
    """Read worker sidecars; optionally replace this store's file with live memory."""
    now = time.time() if now is None else now
    path = getattr(store_or_path, 'path', store_or_path)
    collector = getattr(store_or_path, '_command_metrics', None)
    snapshots = []
    for index, filename in enumerate(glob.iglob(glob.escape(_prefix(path)) + '*.json')):
        if index >= MAX_WORKER_FILES:
            break
        try:
            with open(filename, 'rb') as source:
                encoded = source.read(MAX_FILE_BYTES + 1)
            if len(encoded) > MAX_FILE_BYTES:
                continue
            snapshot = json.loads(encoded)
            if isinstance(collector, CommandMetrics) and isinstance(snapshot, dict) and snapshot.get('pid') == collector.pid:
                continue
            snapshots.append(snapshot)
        except (OSError, ValueError):
            continue
    if isinstance(collector, CommandMetrics):
        snapshots.insert(0, collector.snapshot(now=now))
    return merge_snapshots(snapshots, now=now)
