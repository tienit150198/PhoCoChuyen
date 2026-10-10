"""Shared treasure against disposable PostgreSQL namespaces only."""
import concurrent.futures
import importlib.util
import http.client
import json
import secrets
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game.storage import Store


class Treasure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.path = Path(cls.tmp.name) / 'treasure.db'
        cls.store = Store(cls.path, story=True)
        cls.addClassCleanup(cls.store.close_pool)

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('game.town_treasure'), 'shared treasure backend is missing')
        from game import town_treasure
        self.tt = town_treasure
        with self.store.connect() as db:
            db.execute('DELETE FROM town_treasure_waves')
            db.execute('DELETE FROM town_treasure_proofs')
            db.execute('DELETE FROM town_treasure_presence')
        p = patch.dict('os.environ', LIVE_TOWN_TREASURE='1', LIVE_TOWN='1')
        p.start(); self.addCleanup(p.stop)
        self.now = 1800000001.0
        p = patch('game.town_treasure.now', side_effect=lambda: self.now)
        p.start(); self.addCleanup(p.stop)

    def account(self):
        guest, _, _ = self.store.session()
        sid = self.store.key(guest)
        token = secrets.token_hex(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)', ('u'+secrets.token_hex(6), 'Lan', 'x', sid))
            db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'csrf'))
        return token, sid

    def proof(self, sid, chest, **kw):
        proof, lease = secrets.token_hex(24), secrets.token_hex(16)
        x, y, seen = kw.get('x', chest['x']), kw.get('y', chest['y']), kw.get('seen', self.now)
        with self.store.connect() as db:
            db.execute('INSERT INTO town_treasure_presence(sid,lease,map_id,x,y,seen_at,online) VALUES(?,?,?,?,?,?,1) ON CONFLICT(sid) DO UPDATE SET lease=excluded.lease,map_id=excluded.map_id,x=excluded.x,y=excluded.y,seen_at=excluded.seen_at,online=1', (sid, lease, kw.get('map_id', chest['map_id']), x, y, seen))
            db.execute('INSERT INTO town_treasure_proofs(sid,chest_id,proof_hash,lease,created_at) VALUES(?,?,?,?,?) ON CONFLICT(sid) DO UPDATE SET chest_id=excluded.chest_id,proof_hash=excluded.proof_hash,lease=excluded.lease,created_at=excluded.created_at', (sid,chest['id'],self.store.digest(proof),lease,kw.get('created', self.now)))
        return dict(chest_id=chest['id'], proof=proof, request_id='pick-'+secrets.token_hex(8))

    def test_cadence_count_geometry_and_restart(self):
        a = self.tt.snapshot(self.store)
        self.assertTrue(3 <= len(a['chests']) <= 5)
        self.assertEqual(a['wave']['reward'], 10000)
        from live.town import clean_point
        for chest in a['chests']:
            self.assertEqual(clean_point(chest['x'],chest['y']), (chest['x'],chest['y']))
            self.assertEqual(chest['map_id'], 'iso-town-v1')
        restart = Store(self.path, story=True)
        self.addCleanup(restart.close_pool)
        self.now += 598
        self.assertEqual(self.tt.snapshot(restart)['chests'], a['chests'])
        self.now += 1
        b = self.tt.snapshot(restart)
        self.assertNotEqual(b['wave']['id'], a['wave']['id'])
        self.assertFalse(set(c['id'] for c in a['chests']) & set(c['id'] for c in b['chests']))

    def test_concurrent_workers_share_one_wave(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self.tt.snapshot(self.store)['chests'], range(5)))
        self.assertTrue(all(r == results[0] for r in results))

    def test_global_single_winner_and_retry_exact_reward(self):
        chest = self.tt.snapshot(self.store)['chests'][0]
        players = [self.account(), self.account()]
        wallets = [self.store.read(p[0])[0]['journey']['wallet'] for p in players]
        bodies = [self.proof(p[1], chest) for p in players]
        def claim(i):
            try:return self.tt.claim(self.store,players[i][0],bodies[i])
            except self.tt.TreasureError as e:return e.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, range(2)))
        winners = [i for i,r in enumerate(results) if isinstance(r,dict)]
        self.assertEqual(len(winners), 1)
        win = winners[0]
        self.assertEqual(results[1-win], 'treasure_taken')
        for i,p in enumerate(players):
            self.assertEqual(self.store.read(p[0])[0]['journey']['wallet'], wallets[i] + (10000 if i == win else 0))
        self.now += 20
        retry = self.tt.claim(self.store,players[win][0],bodies[win])
        self.assertTrue(retry['replayed'])
        self.assertEqual(retry['result'], results[win]['result'])
        self.assertEqual(retry['revision'], results[win]['revision'])

    def test_guest_arbitrary_identity_and_raw_coordinates_cannot_claim(self):
        chest = self.tt.snapshot(self.store)['chests'][0]
        guest,_,_ = self.store.session()
        owner,sid = self.account()
        body = self.proof(sid,chest)
        body.update(sid=sid, x=chest['x'], y=chest['y'], coins=999999)
        with self.assertRaises(self.tt.TreasureError) as caught:self.tt.claim(self.store,guest,body)
        self.assertEqual(caught.exception.code,'treasure_account')
        other,_ = self.account()
        with self.assertRaises(self.tt.TreasureError):self.tt.claim(self.store,other,body)

    def test_remote_stale_offmap_and_expired_proofs_denied(self):
        token,sid = self.account()
        chest = self.tt.snapshot(self.store)['chests'][0]
        for kw in (dict(x=chest['x']+30),dict(seen=self.now-13),dict(map_id='private-home'),dict(created=self.now-6)):
            body=self.proof(sid,chest,**kw)
            with self.subTest(kw=kw), self.assertRaises(self.tt.TreasureError):self.tt.claim(self.store,token,body)

    def test_next_wave_expires_unclaimed_chest_and_bounds_audit(self):
        token,sid = self.account()
        chest=self.tt.snapshot(self.store)['chests'][0]
        body=self.proof(sid,chest)
        self.now += 600
        with self.assertRaises(self.tt.TreasureError) as caught:self.tt.claim(self.store,token,body)
        self.assertEqual(caught.exception.code,'treasure_expired')
        self.now += 90000
        self.tt.snapshot(self.store)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM town_treasure_chests WHERE id=?',(chest['id'],)).fetchone()[0],0)
            self.assertLessEqual(db.execute('SELECT COUNT(*) FROM town_treasure_waves').fetchone()[0],145)

    def test_time_rechecked_after_position_lock_wait(self):
        token,sid=self.account()
        chest=self.tt.snapshot(self.store)['chests'][0]
        body=self.proof(sid,chest)
        with patch('game.town_treasure.now',side_effect=[self.now,self.now+600]):
            with self.assertRaises(self.tt.TreasureError) as caught:self.tt.claim(self.store,token,body)
        self.assertEqual(caught.exception.code,'treasure_expired')

    def test_wallet_failure_rolls_back_claim_then_can_retry(self):
        token,sid = self.account()
        chest=self.tt.snapshot(self.store)['chests'][0]
        body=self.proof(sid,chest)
        before=self.store.read(token)
        with patch('game.town_treasure.serialize', side_effect=RuntimeError('disk simulation')):
            with self.assertRaises(RuntimeError):self.tt.claim(self.store,token,body)
        # Fail after both SQL UPDATEs to prove the wallet and claim roll back together.
        with patch('game.town_treasure.leaderboard.write', side_effect=RuntimeError('late failure')):
            with self.assertRaises(RuntimeError):self.tt.claim(self.store,token,body)
        self.assertEqual(self.store.read(token)[1],before[1])
        self.assertEqual(self.store.read(token)[0]['journey']['wallet'],before[0]['journey']['wallet'])
        self.assertFalse(self.tt.snapshot(self.store)['chests'][0]['claimed'])
        self.assertEqual(self.tt.claim(self.store,token,body)['result']['treasure']['coins'],10000)

    def test_disabled_does_not_spawn_or_pay(self):
        with patch.dict('os.environ', LIVE_TOWN_TREASURE='0'):
            self.assertEqual(self.tt.snapshot(self.store)['chests'],[])
            with self.assertRaises(self.tt.TreasureError):self.tt.claim(self.store,'fake',{})
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM town_treasure_waves').fetchone()[0],0)

    def test_http_csrf_rate_limit_and_state_contract(self):
        from server import GameServer
        server=GameServer(('127.0.0.1',0),self.store)
        server.game_version=lambda:'treasure-test'  # No unrelated asset tree scan in HTTP contract tests.
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        token,sid=self.account()
        client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=10)
        self.addCleanup(client.close)
        headers={'Cookie':'mnl_session='+token,'Content-Type':'application/json','X-Game-CSRF':'csrf'}
        client.request('GET','/api/town/treasure',headers=headers)
        response=client.getresponse();payload=json.loads(response.read())
        self.assertEqual(response.status,200)
        self.assertTrue(payload['enabled'])
        body=self.proof(sid,payload['chests'][0])
        client.request('POST','/api/town/treasure/claim',json.dumps(body),{k:v for k,v in headers.items() if k!='X-Game-CSRF'})
        response=client.getresponse();response.read();self.assertEqual(response.status,403)
        client.close()  # A rejected CSRF request deliberately closes its connection.
        client.request('POST','/api/town/treasure/claim',json.dumps(body),headers)
        response=client.getresponse();paid=json.loads(response.read())
        self.assertEqual(response.status,200,paid)
        self.assertIn('state',paid);self.assertIn('revision',paid)
        self.assertEqual(paid['result']['treasure']['coins'],10000)
        server.rate_limit=lambda *args:False
        client.request('GET','/api/town/treasure',headers=headers)
        response=client.getresponse();response.read();self.assertEqual(response.status,429)
        client.request('POST','/api/town/treasure/claim',json.dumps(body),headers)
        response=client.getresponse();response.read();self.assertEqual(response.status,429)


if __name__ == '__main__':unittest.main()
