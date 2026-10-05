import psycopg
"""0.9.5 reliability: restarts and database trouble never turn into lost clicks (PG_E2E F10-F13).

- the client re-sends reads and commands through a restart (tests/api_retry.mjs, run with node);
- a command during a database outage answers 503 db_unavailable, not 500 (F12);
- a POST refused before its body was read leaves a clean keep-alive stream (F13);
- housekeeping runs in one server at a time (rolling deploys run two for a while).
"""
import http.client
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from game import storage
from game.storage import Store
from server import GameServer

ROOT = Path(__file__).resolve().parents[1]


class ClientRetry(unittest.TestCase):
    def test_api_retry_logic(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'api_retry.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)




class HttpResilience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'LLM_BASE_URL': ''})
        cls.env.start()
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'game.db')
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        cls.temp.cleanup()
        cls.env.stop()

    def boot(self):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        c.request('GET', '/api/bootstrap?lite=1', headers={'Host': f'127.0.0.1:{self.port}'})
        r = c.getresponse()
        data = json.loads(r.read())
        cookie = r.getheader('Set-Cookie').split(';')[0]
        c.close()
        return cookie, data['csrf'], data['revision']

    def command(self, cookie, csrf, rid, revision, volume):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        body = json.dumps(dict(request_id=rid, expected_revision=revision, career=None, action='settings', payload=dict(musicVolume=volume)))
        c.request('POST', '/api/command', body=body, headers={'Host': f'127.0.0.1:{self.port}', 'Cookie': cookie, 'X-Game-CSRF': csrf,
                                                               'Content-Type': 'application/json'})
        r = c.getresponse()
        out = r.status, json.loads(r.read())
        c.close()
        return out

    def test_command_during_db_outage_is_503(self):  # F12
        cookie, csrf, revision = self.boot()
        for exc in (psycopg.OperationalError('connection lost'), psycopg.OperationalError('database unavailable')):
            with patch.object(self.store, 'command', side_effect=exc):
                status, data = self.command(cookie, csrf, 'resil-f12-a', revision, 20)
            self.assertEqual((status, data['code']), (503, 'db_unavailable'))
        # the same request id then lands once the database is back (the client re-sends it as is)
        status, data = self.command(cookie, csrf, 'resil-f12-a', revision, 20)
        self.assertEqual(status, 200)
        self.assertEqual(data['revision'], revision + 1)
        status, again = self.command(cookie, csrf, 'resil-f12-a', revision, 20)
        self.assertEqual((status, again['revision'], again.get('replayed')), (200, revision + 1, True))

    def test_a_real_bug_is_still_500(self):
        cookie, csrf, revision = self.boot()
        with patch.object(self.store, 'command', side_effect=psycopg.ProgrammingError('bug')):
            status, data = self.command(cookie, csrf, 'resil-bug-a', revision, 20)
        self.assertEqual((status, data['code']), (500, 'internal_error'))

    def raw_pair(self, first: bytes) -> list:
        """Send `first` then a GET /api/health on ONE keep-alive connection; the status lines seen."""
        s = socket.create_connection(('127.0.0.1', self.port), timeout=10)
        try:
            host = f'127.0.0.1:{self.port}'.encode()
            s.sendall(first + b'GET /api/health HTTP/1.1\r\nHost: ' + host + b'\r\nConnection: close\r\n\r\n')
            data, statuses = b'', []
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:  # until the server closes (Connection: close on the GET)
                try:
                    chunk = s.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data += chunk
            for part in data.split(b'HTTP/1.1 ')[1:]:
                statuses.append(int(part[:3]))
            return statuses, data
        finally:
            s.close()

    def test_refused_post_leaves_a_clean_keepalive_stream(self):  # F13
        host = f'127.0.0.1:{self.port}'.encode()
        body = b'{"request_id":"resil-f13-aaaa","expected_revision":0,"action":"settings","payload":{}}'
        first = (b'POST /api/command HTTP/1.1\r\nHost: ' + host + b'\r\nContent-Type: application/json\r\nX-Game-CSRF: x\r\n'
                 b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
        statuses, data = self.raw_pair(first)  # no cookie: 401 before the body is read
        self.assertEqual(statuses, [401, 200], data[:600])
        self.assertIn(b'"status":"ok"', data)  # compact JSON (game/fastjson.py)
        # a database outage in the session check (503) as well
        cookie, csrf, _ = self.boot()
        first = (b'POST /api/social/profile HTTP/1.1\r\nHost: ' + host + b'\r\nCookie: ' + cookie.encode() + b'\r\nX-Game-CSRF: ' + csrf.encode()
                 + b'\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
        with patch.object(self.store, 'read', side_effect=psycopg.OperationalError('database is locked')):
            statuses, data = self.raw_pair(first)
        self.assertEqual(statuses, [503, 200], data[:600])


@unittest.skipIf(getattr(server, 'fcntl', None) is None, 'flock() only on POSIX (Windows runs one server process)')
class HousekeepingLock(unittest.TestCase):
    def test_one_server_at_a_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / 'game.db')
            first = server.maintenance_lock(db)
            self.assertIsInstance(first, int)
            self.assertIsNone(server.maintenance_lock(db), 'a second server must wait')
            os.close(first)
            again = server.maintenance_lock(db)
            self.assertIsInstance(again, int, 'taken over once the first one stops')
            os.close(again)

    def test_waiting_maintenance_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'game.db')
            held = server.maintenance_lock(store.path)
            stop = threading.Event()
            t = threading.Thread(target=server.maintenance, args=(store, stop), daemon=True)
            with patch.object(server.leaderboard, 'run_backfill') as backfill:
                t.start()
                time.sleep(.3)
                self.assertFalse(backfill.called, 'no housekeeping while another server holds the lock')
                stop.set()
                t.join(15)
            self.assertFalse(t.is_alive())
            os.close(held)
            store.close_pool()


if __name__ == '__main__':
    unittest.main()
