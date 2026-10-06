"""Idle HTTP/1.1 connections must not occupy every bounded handler slot."""
import http.client
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from game.storage import Store
from server import GameServer, Handler


class ConnectionAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'state.db')
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.server.max_threads = 4
        cls.server.keepalive_timeout = 0.2
        cls.server.game_version()  # warm static version metadata before timing admission
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.store.close_pool()
        cls.temp.cleanup()
        cls.quiet.stop()

    def connection(self):
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=1)
        # Close clients before shutdown, including on failure: the accept loop may
        # still be waiting for an occupied connection slot in the old implementation.
        self.addCleanup(con.close)
        return con

    def health(self, con):
        con.request('GET', '/api/health')
        response = con.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.read())['status'], 'ok')

    def bootstrap(self):
        con = self.connection()
        con.request('GET', '/api/bootstrap?lite=1')
        response = con.getresponse()
        self.assertEqual(response.status, 200)
        cookie = response.getheader('Set-Cookie').split(';')[0]
        data = json.loads(response.read())
        con.close()
        return cookie, data['csrf'], data['revision']

    def command(self, con, *, cookie=None, csrf=None, revision=0, path='/api/command'):
        headers = {'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = cookie
        if csrf:
            headers['X-Game-CSRF'] = csrf
        body = json.dumps({'request_id': f'admission-{id(self)}-{revision}', 'expected_revision': revision,
                           'career': None, 'action': 'settings', 'payload': {'reduceMotion': bool(revision % 2)}})
        con.request('POST', path, body, headers)
        response = con.getresponse()
        return response.status, dict(response.getheaders()), json.loads(response.read()), response.will_close

    def test_idle_keepalive_connections_release_slots_for_new_clients(self):
        held = [self.connection() for _ in range(self.server.max_threads)]
        for con in held:
            self.health(con)
        started = time.monotonic()
        try:
            self.health(self.connection())
        except TimeoutError:
            self.fail('all handler slots remained occupied by idle keep-alive connections')
        self.assertLess(time.monotonic() - started, 1)

    def test_command_responses_advertise_close_including_errors_and_query_strings(self):
        cookie, csrf, revision = self.bootstrap()
        con = self.connection()
        cases = [(200, cookie, csrf), (403, cookie, 'wrong'), (401, None, None)]
        for expected, supplied_cookie, supplied_csrf in cases:
            with self.subTest(status=expected):
                status, headers, data, will_close = self.command(con, cookie=supplied_cookie,
                                                                csrf=supplied_csrf, revision=revision,
                                                                path='/api/command?client=admission')
                self.assertEqual(status, expected, data)
                self.assertEqual(headers.get('Connection'), 'close')
                self.assertTrue(will_close)
                self.assertIsNone(con.sock)

    def test_commands_release_slots_without_waiting_for_idle_timeout(self):
        cookie, csrf, revision = self.bootstrap()
        with patch.object(self.server, 'keepalive_timeout', 30):
            held = [self.connection() for _ in range(self.server.max_threads)]
            for con in held:
                status, _, data, _ = self.command(con, cookie=cookie, csrf=csrf, revision=revision)
                self.assertEqual(status, 200, data)
                revision = data['revision']
            started = time.monotonic()
            try:
                self.health(self.connection())
            except TimeoutError:
                self.fail('completed commands retained their handler slots until the idle timeout')
            self.assertLess(time.monotonic() - started, 1)

    def test_get_and_static_responses_keep_the_connection_reusable(self):
        con = self.connection()
        original_socket = None
        for path in ('/api/health', '/favicon.svg', '/api/health'):
            con.request('GET', path)
            response = con.getresponse()
            self.assertEqual(response.status, 200)
            self.assertFalse(response.will_close)
            self.assertTrue(response.read())
            if original_socket is None:
                original_socket = con.sock
            self.assertIs(con.sock, original_socket)


class EchoHandler(Handler):
    """Exercise Handler's actual HTTP parsing without game routes or a database."""
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.reply(b'ok')

    def do_POST(self):
        self.reply(self.rfile.read(int(self.headers['Content-Length'])))

    def reply(self, body):
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class RequestBudgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), EchoHandler)
        cls.server.keepalive_timeout = 0.1
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def connection(self):
        sock = socket.create_connection(self.server.server_address, timeout=1)
        self.addCleanup(sock.close)
        return sock

    def response(self, sock, expected):
        response = http.client.HTTPResponse(sock)
        response.begin()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), expected)
        response.close()

    def test_first_request_keeps_original_read_budget(self):
        sock = self.connection()
        time.sleep(0.3)
        sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        self.response(sock, b'ok')

    def test_reused_connection_keeps_active_headers_and_body_read_budget(self):
        sock = self.connection()
        sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
        self.response(sock, b'ok')
        sock.sendall(b'POST / HTTP/1.1\r\n')
        time.sleep(0.3)
        sock.sendall(b'Host: localhost\r\nContent-Length: 6\r\nConnection: close\r\n\r\nabc')
        time.sleep(0.3)
        sock.sendall(b'def')
        self.response(sock, b'abcdef')

    def test_pipelined_requests_are_both_answered(self):
        sock = self.connection()
        sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n'
                     b'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 6\r\n'
                     b'Connection: close\r\n\r\nabcdef')
        with sock.makefile('rb') as stream:
            responses = stream.read()
        self.assertEqual(responses.count(b'HTTP/1.1 200 OK\r\n'), 2)
        self.assertTrue(responses.endswith(b'\r\n\r\nabcdef'))


if __name__ == '__main__':
    unittest.main()
