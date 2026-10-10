"""Weekly microphone tug-of-war competition against real PostgreSQL."""
import datetime
import json
import threading
import unittest
from unittest.mock import patch
from game import dog_bark as G, live_effects
from tests.pg_support import pg_only
from tests import test_dog_bark as bark_tests

class LobbyAvailability(unittest.TestCase):
    def test_competition_failure_does_not_close_the_lobby(self):
        with patch('game.dog_bark_board.view', side_effect=RuntimeError('temporary')):
            with patch.object(G, 'housekeeping'), patch.object(G, 'king', return_value=None):
                result = G.view(object(), None)
        self.assertIsNone(result['competition'])
        self.assertEqual(result['min'], G.MIN_STAKE)

@pg_only
class Weekly(unittest.TestCase):
    setUp = bark_tests.Database.setUp
    player = bark_tests.Database.player
    state = bark_tests.Database.state
    wallet = bark_tests.Database.wallet
    pay = bark_tests.Database.pay

    def board(self):
        from game import dog_bark_board as B
        return B

    def init_week(self):
        B = self.board()
        B.clear_cache()
        self.w = G.week_start(datetime.datetime(2026, 10, 10, tzinfo=G.VN).timestamp())
        B.settle(self.store, self.w + 1)
        self.serial = 0
        return B

    def matches(self, token, wins, losses=0, draws=0, at=None, status='done', opp='dog'):
        at = self.w + 100 if at is None else at
        with self.store.connect() as db:
            for result, count in [('win', wins), ('lose', losses), ('draw', draws)]:
                for i in range(count):
                    self.serial += 1
                    db.execute('INSERT INTO bark_tickets(id,sid,stake,status,created,started,ended,opp,result,pay,competitive) VALUES(?,?,100,?,?,?,?,?,?,0,true)',
                               (f'k{self.serial:020x}', self.store.key(token), status, at-2, at-1, at, opp, result))

    def test_ranking_denominator_minimum_and_privacy(self):
        B = self.init_week()
        a,b,c,h,g = [self.player(name=n, account=n!='Guest') for n in ['Lan','Minh','Hoa','Hidden','Guest']]
        self.matches(a,20,5,5,opp='pvp')
        self.matches(b,30,15)
        self.matches(c,29)
        self.matches(h,30)
        self.matches(g,30)
        self.matches(a,90,status='back')
        with self.store.connect() as db:
            db.execute('INSERT INTO leaderboard_players(sid,name,show,updated) VALUES(?,?,0,0) ON CONFLICT(sid) DO UPDATE SET show=0', (self.store.key(h),'Hidden'))
        v = B.view(self.store,self.store.key(c),self.w+1000)
        self.assertEqual([r['name'] for r in v['rows']], ['Minh','Lan'])
        self.assertEqual(v['rows'][1]['played'],30)
        self.assertAlmostEqual(v['rows'][1]['rate'],200/3, places=2)
        self.assertEqual(v['me']['remaining'],1)
        self.assertFalse(v['me']['eligible'])
        self.assertNotIn('sid',json.dumps(v))
        self.assertFalse(B.view(self.store,self.store.key(h),self.w+1000)['me']['eligible'])

    def test_29_matches_cannot_win_and_30th_match_qualifies(self):
        B = self.init_week()
        a, b = self.player(name='Below threshold'), self.player(name='Thirty matches')
        self.matches(a, 29)
        self.matches(b, 29)
        before = B.view(self.store, self.store.key(b), self.w+1000)
        self.assertEqual(before['rows'], [])
        self.assertFalse(before['me']['eligible'])
        self.assertEqual(before['me']['remaining'], 1)
        self.matches(b, 0, losses=1)
        B.clear_cache()
        after = B.view(self.store, self.store.key(b), self.w+1000)
        self.assertEqual([r['name'] for r in after['rows']], ['Thirty matches'])
        self.assertTrue(after['me']['eligible'])
        self.assertEqual(after['me']['remaining'], 0)
        B.settle(self.store, self.w+B.WEEK+B.GRACE+1)
        self.assertFalse(self.pay(a))
        self.assertTrue(self.pay(b))
        self.assertEqual(self.wallet(a), 10_000)
        self.assertEqual(self.wallet(b), 2_010_000)

    def test_settlement_concurrent_exactly_once_and_title(self):
        B = self.init_week()
        a = self.player()
        self.matches(a,30)
        t = self.w+B.WEEK+B.GRACE+1
        errors=[]
        def settle():
            try: B.settle(self.store,t)
            except Exception as e: errors.append(e)
        threads=[threading.Thread(target=settle) for _ in range(4)]
        for th in threads: th.start()
        for th in threads: th.join()
        self.assertEqual(errors,[])
        with self.store.connect() as db:
            rows=list(db.execute("SELECT * FROM live_effects WHERE kind='bark_weekly'"))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['amount'],2_000_000)
        with patch.object(live_effects,'PAYS',tuple(k for k in live_effects.PAYS if k!='bark_weekly')):
            self.assertFalse(self.pay(a))
        self.assertTrue(self.pay(a))
        self.assertFalse(self.pay(a))
        self.assertEqual(self.wallet(a),2_010_000)
        self.assertIn(B.TITLE_IDS[0],self.state(a)['journey']['titles'])
        self.matches(a,1,at=self.w+500)
        B.settle(self.store,t)
        previous=B.view(self.store,self.store.key(a),t)['previous']
        self.assertEqual(previous['rows'][0]['played'],30)

    def test_activation_boundary_grace_and_account_lifetime(self):
        B = self.init_week()
        a = self.player()
        self.matches(a,30,at=self.w-100)
        self.matches(a,29,at=self.w+100)
        self.matches(a,1,at=self.w+B.WEEK)
        B.settle(self.store,self.w+B.WEEK+B.GRACE-1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM live_effects WHERE kind='bark_weekly'").fetchone()[0],0)
        B.settle(self.store,self.w+B.WEEK+B.GRACE+1)
        self.assertEqual(B.view(self.store,None,self.w+B.WEEK+B.GRACE+1)['previous']['rows'],[])
        self.assertEqual(B.view(self.store,self.store.key(a),self.w+B.WEEK+1000)['me']['played'],1)
        with self.store.connect() as db:
            db.execute("UPDATE accounts SET created_at='2026-10-13 00:00:00' WHERE sid=?", (self.store.key(a),))
        B.clear_cache()
        self.assertEqual(B.view(self.store,self.store.key(a),self.w+B.WEEK+1000)['me']['played'],0)

    def test_exact_tie_earlier_finish_and_catchup(self):
        B = self.init_week()
        a,b=self.player(name='Later'),self.player(name='Earlier')
        self.matches(a,30,at=self.w+300)
        self.matches(b,30,at=self.w+200)
        self.assertEqual(B.view(self.store,None,self.w+1000)['rows'][0]['name'],'Earlier')
        B.settle(self.store,self.w+3*B.WEEK+B.GRACE+1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM live_effects WHERE kind='bark_weekly'").fetchone()[0],2)
        B.settle(self.store,self.w+3*B.WEEK+B.GRACE+1)
        self.pay(b)
        self.assertEqual(self.wallet(b),2_010_000)

    def test_snapshot_reward_transaction_rolls_back_and_recovers(self):
        B = self.init_week()
        a = self.player()
        self.matches(a,30)
        t = self.w+B.WEEK+B.GRACE+1
        original = B._standings
        def broken(db,w):
            original(db,w)
            raise RuntimeError('test abort before grant')
        with patch.object(B,'_standings',broken):
            with self.assertRaises(RuntimeError): B.settle(self.store,t)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM leaderboard_meta WHERE k=?',(B.META+B.week_label(self.w),)).fetchone())
        B.settle(self.store,t)
        self.pay(a)
        self.assertEqual(self.wallet(a),2_010_000)

    def test_payment_requires_pending_row_and_does_not_broaden_coins(self):
        from game.engine import GameError
        B = self.init_week()
        a = self.player()
        payload=dict(id='bark-weekly:fake',kind=B.FX,amount=B.COINS[0],
                     data=dict(rank=1,week=B.week_label(self.w),title=B.TITLE_IDS[0]))
        with self.assertRaises(GameError):
            self.store.command(a,'bark-fake-0001',None,None,'live_fx',payload,internal=True)
        self.assertEqual(self.wallet(a),10_000)
        with self.assertRaises(GameError):
            self.store.command(a,'bark-fake-0002',None,None,'live_fx',dict(id='coin:fake',kind='coins',amount=2_000_000),internal=True)
        self.assertEqual(self.wallet(a),10_000)

    def test_deletion_erases_historical_identity_and_privacy_is_fresh(self):
        B = self.init_week()
        a = self.player(name='Lan')
        self.matches(a,30)
        B.view(self.store,None,self.w+1000)
        with self.store.connect() as db:
            db.execute('INSERT INTO leaderboard_players(sid,name,show,updated) VALUES(?,?,0,0) ON CONFLICT(sid) DO UPDATE SET show=0',(self.store.key(a),'Lan'))
        self.assertEqual(B.view(self.store,None,self.w+1000)['rows'],[])
        with self.store.connect() as db:
            db.execute('UPDATE leaderboard_players SET show=1 WHERE sid=?',(self.store.key(a),))
        t=self.w+B.WEEK+B.GRACE+1
        B.settle(self.store,t)
        sid=self.store.key(a)
        self.store.delete(a)
        with self.store.connect() as db:
            snapshot=db.execute('SELECT v FROM leaderboard_meta WHERE k=?',(B.META+B.week_label(self.w),)).fetchone()['v']
            self.assertNotIn(sid,snapshot)
            self.assertIsNone(db.execute("SELECT 1 FROM live_effects WHERE kind='bark_weekly' AND sid=?",(sid,)).fetchone())
        self.assertEqual(B.view(self.store,None,t)['previous']['rows'][0]['name'],'Một người chơi')

    def test_legacy_rows_cannot_qualify_and_schema_default_is_safe(self):
        B = self.init_week()
        a = self.player()
        self.matches(a,30)
        with self.store.connect() as db:
            from tests.pg_support import columns
            self.assertIn('competitive', columns(db, 'bark_tickets'))
            db.execute('UPDATE bark_tickets SET competitive=false')
        B.clear_cache()
        self.assertEqual(B.view(self.store,self.store.key(a),self.w+1000)['me']['played'],0)

    def test_schema34_upgrade_preserves_rows_with_default_false(self):
        from game import pg_schema
        B = self.init_week()
        a = self.player()
        self.matches(a,1)
        with self.store.connect() as db:
            db.execute('ALTER TABLE bark_tickets DROP COLUMN competitive')
            db.execute("UPDATE mnl_meta SET value='34' WHERE key='schema_version'")
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(db.execute('SELECT competitive FROM bark_tickets').fetchone()[0])
            self.assertFalse(pg_schema.ensure(db))
