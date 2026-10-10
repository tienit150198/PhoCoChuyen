"""Weekly net-loss accounting: real commands, same save transaction, privacy and titles."""
import json
import threading
from unittest.mock import patch
from tests.pg_support import pg_only
from tests.test_fair import StoreBase, Dice
from tests.test_fair_forever import MON1
from game import fair as fh, leaderboard as lb, live_effects

@pg_only
class WeeklyLoss(StoreBase):
    def setUp(self):
        super().setUp()
        from game import fair_loss as fl
        self.fl = fl
        self.addCleanup(fl.clear_cache)
        fl.clear_cache()
        self.p = patch.object(fl, 'now', side_effect=lambda: self.clock.t)
        self.p.start(); self.addCleanup(self.p.stop)

    def lose(self, tok, amount=10, rid=None):
        self.dice(Dice(faces=['ga']*3, draws=[.99]))
        return self.cmd(tok, 'fair_bc', {'bets': {'cua': amount}}, rid=rid)

    def win(self, tok, amount=10):
        self.dice(Dice(faces=['cua','ga','tom'], draws=[.99]))
        return self.cmd(tok, 'fair_bc', {'bets': {'cua': amount}})

    def board(self, tok=None):
        return lb.view(self.store, 'fair-loss', 20, tok)

    def test_net_offsets_losses_and_new_week_starts_zero(self):
        a=self.player('Lan', wallet=10000)
        self.lose(a,100)
        self.win(a,30)
        b=self.board(a)
        self.assertEqual((b['me']['net'], b['rows'][0]['xu']),(-70,70))
        self.clock.t=MON1+120
        self.assertEqual(self.board(a)['rows'],[])
        self.assertEqual(self.board(a)['me']['net'],0)
        self.lose(a,5)
        self.assertEqual(self.board(a)['rows'][0]['xu'],5)

    def test_command_retry_and_rollback_do_not_double_count(self):
        a=self.player('Lan')
        self.lose(a,10,rid='fair-loss-retry-01')
        again=self.lose(a,10,rid='fair-loss-retry-01')
        self.assertTrue(again['replayed'])
        self.assertEqual(self.board(a)['me']['xu'],10)
        original=self.fl.record
        def broken(*args,**kwargs):
            original(*args,**kwargs)
            raise RuntimeError('rollback after loss row')
        with patch.object(self.fl,'record',side_effect=broken):
            with self.assertRaises(RuntimeError):self.lose(a,10)
        self.assertEqual(self.board(a)['me']['xu'],10)
        self.assertEqual(self.store.read(a)[0]['journey']['wallet'],490)

    def test_weekly_titles_top_ten_privacy_idempotent_no_money(self):
        players=[self.player('Player '+str(i)) for i in range(12)]
        for i,p in enumerate(players):self.lose(p,i+1)
        hidden=players[-1]
        with self.store.connect() as db:
            db.execute('UPDATE leaderboard_players SET show=0 WHERE sid=?',(self.store.key(hidden),))
        v=self.board(hidden)
        self.assertFalse(v['me']['visible'])
        self.assertEqual(v['rows'][0]['xu'],11)
        self.assertNotIn('sid',json.dumps(v))
        self.clock.t=MON1+120
        errors=[]
        def settle():
            try:self.fl.settle(self.store)
            except Exception as e:errors.append(e)
        threads=[threading.Thread(target=settle) for _ in range(3)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(errors,[])
        with self.store.connect() as db:
            rows=list(db.execute("SELECT kind,amount,data FROM live_effects WHERE id LIKE 'fair-loss:%'"))
        self.assertEqual(len(rows),10)
        self.assertTrue(all(r['kind']=='title' and r['amount']==1 for r in rows))
        winner=players[-2];before=self.store.read(winner)[0]['journey']['wallet']
        self.assertTrue(live_effects.on_load(self.store,winner,self.store.read(winner)[0]))
        state=self.store.read(winner)[0]
        self.assertEqual(state['journey']['wallet'],before)
        self.assertIn('f_loss_king',state['journey']['titles'])
        self.assertFalse(live_effects.on_load(self.store,winner,state))
        self.store.delete(winner)
        self.assertNotIn(self.store.key(winner),json.dumps(self.board()))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fair_loss_week WHERE sid=?',(self.store.key(winner),)).fetchone()[0],0)

    def test_import_reset_and_existing_totals_are_not_weekly_losses(self):
        a=self.player('Lan')
        from game.storage import _commit_before
        from game import marriage
        def old(s):
            fh._state(s['journey'],self.clock.t)['stats']['lost']=2000
        marriage._mutate(self.store,{self.store.key(a):old})
        self.lose(a,10)
        self.assertEqual(self.board(a)['me']['xu'],10)
        with self.store.connect() as db:
            state=self.store.read(a)[0]
            self.fl.record(db,self.store.key(a),dict(_fair_net=0),state,'import_save')
            self.fl.record(db,self.store.key(a),dict(_fair_net=-2010),dict(journey={}), 'reset_all')
        self.assertEqual(self.board(a)['me']['xu'],10)

    def test_locked_path_gifts_loans_and_wins_are_not_losses(self):
        a=self.player('Lan')
        from game import storage
        with patch.object(storage,'OPTIMISTIC_TRIES',0):
            self.lose(a,10)
        self.assertEqual(self.board(a)['me']['xu'],10)
        self.cmd(a,'fair_gift',{})
        self.assertEqual(self.board(a)['me']['xu'],10)
        self.win(a,30)
        self.assertEqual(self.board(a)['rows'],[])
        self.assertEqual(self.board(a)['me']['net'],20)
        self.clock.t=MON1+120
        self.fl.settle(self.store)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM live_effects WHERE id LIKE 'fair-loss:%'").fetchone()[0],0)

    def test_settlement_rolls_back_snapshot_and_titles_together(self):
        a=self.player('Lan')
        self.lose(a,10)
        self.clock.t=MON1+59
        self.fl.settle(self.store)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM live_effects WHERE id LIKE 'fair-loss:%'").fetchone()[0],0)
        self.clock.t=MON1+61
        from game import wedding_live
        original=wedding_live.grant
        def broken(*args,**kwargs):
            original(*args,**kwargs)
            raise RuntimeError('abort title settlement')
        with patch.object(wedding_live,'grant',side_effect=broken):
            with self.assertRaises(RuntimeError):self.fl.settle(self.store)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM live_effects WHERE id LIKE 'fair-loss:%'").fetchone()[0],0)
        self.fl.settle(self.store)
        self.assertEqual(len(self.board()['fair']['winners']),1)

    def test_writer_delayed_before_week_lock_cannot_change_finalized_week(self):
        from game import db as dbm
        a=self.player('Lan')
        self.lose(a,10)
        sid=self.store.key(a)
        state=self.store.read(a)[0]
        before=dict(_fair_net=fh.money_of(state['journey'])[0]+50)
        self.clock.t=MON1-1
        paused=threading.Event()
        resume=threading.Event()
        errors=[]
        execute=dbm.PgConnection.execute

        def pause_before_lock(db,sql,args=()):
            if 'pg_advisory_xact_lock_shared(1947' in sql:
                paused.set()
                if not resume.wait(10):
                    raise RuntimeError('timed out waiting to resume week writer')
            return execute(db,sql,args)

        def write():
            try:
                self.store.transaction(lambda db:self.fl.record(db,sid,before,state,'fair_bc'))
            except Exception as error:
                errors.append(error)

        with patch.object(dbm.PgConnection,'execute',pause_before_lock):
            writer=threading.Thread(target=write)
            writer.start()
            try:
                self.assertTrue(paused.wait(10),'writer did not reach the week lock')
                self.clock.t=MON1+self.fl.GRACE+1
                self.fl.settle(self.store)
            finally:
                resume.set()
                writer.join(10)
        self.assertFalse(writer.is_alive())
        self.assertEqual(errors,[])
        with self.store.connect() as db:
            weeks={r['week']:r['net'] for r in db.execute(
                'SELECT week,net FROM fair_loss_week WHERE sid=?',(sid,))}
            mark=self.fl.META+self.fl.vn_day(MON1-self.fl.WEEK)
            winners=json.loads(db.execute('SELECT v FROM leaderboard_meta WHERE k=?',(mark,)).fetchone()[0])
        self.assertEqual(weeks,{int(MON1-self.fl.WEEK):-10,int(MON1):-50})
        self.assertEqual([r['score'] for r in winners],[10])

    def test_seed_uses_existing_net_once_and_future_weeks_reset(self):
        from game import marriage
        a=self.player('Lan',wallet=10000)
        def old(s):
            stats=fh._state(s['journey'],self.clock.t)['stats']
            stats['lost']=2000;stats['won']=500
        marriage._mutate(self.store,{self.store.key(a):old})
        self.lose(a,10)
        week=int(self.fl.week_start(self.clock.t))
        while True:
            result=self.fl.seed_current(self.store,week,batch=1)
            if result['done']:break
        self.assertEqual(self.board(a)['me']['net'],-1510)
        self.assertTrue(self.board(a)['fair']['seeded'])
        self.win(a,30)
        self.fl.seed_current(self.store,week)
        self.assertEqual(self.board(a)['me']['net'],-1480)
        self.clock.t=MON1+120
        self.assertEqual(self.board(a)['me']['net'],0)
        self.assertFalse(self.board(a)['fair']['seeded'])
        with self.assertRaises(ValueError):self.fl.seed_current(self.store,week)
        self.lose(a,5)
        self.assertEqual(self.board(a)['me']['net'],-5)

    def test_seed_progress_and_ledger_rollback_together(self):
        from game import db as dbm
        a=self.player('Lan')
        self.lose(a,10)
        week=int(self.fl.week_start(self.clock.t))
        execute=dbm.PgConnection.execute
        def broken(db,sql,args=()):
            result=execute(db,sql,args)
            if sql.startswith('UPDATE leaderboard_meta SET v=') and str(args[-1]).startswith(self.fl.SEED):
                raise RuntimeError('seed progress rollback')
            return result
        with patch.object(dbm.PgConnection,'execute',broken):
            with self.assertRaises(RuntimeError):self.fl.seed_current(self.store,week)
        self.assertFalse(self.board(a)['fair']['seeded'])
        self.assertEqual(self.board(a)['me']['net'],-10)
        self.assertTrue(self.fl.seed_current(self.store,week)['done'])
