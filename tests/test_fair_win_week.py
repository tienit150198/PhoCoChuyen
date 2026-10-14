"""🏆 Top lời theo tuần (owner 14/10): the Bảng vàng chợ đen ranks this week's net won (game/fair_loss.py view_win, on
the fair_loss_week rows Top lỗ uses), a Chợ đen fine refund paid this week counts in it once, the Monday crowning
(👑 Vua trò chơi, 🎪 Cao thủ chợ đen) comes from that week, once, and scripts/fair_board_recompute.py --week adds the
refunds paid before the release without touching saves."""
import io
import json
import threading
from contextlib import redirect_stdout
from unittest.mock import patch

from tests.pg_support import pg_only
from tests.test_fair import StoreBase
from tests.test_fair_board_refund import _script
from tests.test_fair_forever import MON1, MON2
from tests import test_fair_loss as _weekly   # its helpers, not its tests (a class imported here would run again)
from game import fair as fh, fair_board as fb, fair_refund, leaderboard as lb, live_effects, system_gift as sg


@pg_only
class WeeklyWin(StoreBase):
    lose, win = _weekly.WeeklyLoss.lose, _weekly.WeeklyLoss.win

    def setUp(self):
        super().setUp()
        from game import fair_loss as fl
        self.fl = fl
        fl.clear_cache()
        self.addCleanup(fl.clear_cache)
        for mod in (fl, fb):
            p = patch.object(mod, 'now', side_effect=lambda: self.clock.t)
            p.start()
            self.addCleanup(p.stop)
        fair_refund.clear_cache()
        self.addCleanup(fair_refund.clear_cache)
        self.clock.t = MON1 + 3600   # the first weekly week (12/10)

    def board(self, tok=None):
        return lb.view(self.store, fh.board(), 20, tok)

    def net(self, tok):
        return self.board(tok)['me']['net']

    def refund(self, tok, coins, gid):
        sg.grant(self.store, self.store.key(tok), coins, 'Quà từ Phố Có Chuyện', 'Hoàn phần phạt dư.', gid=gid)
        changed, _ = sg.on_load(self.store, tok, self.store.read(tok)[0])
        self.assertTrue(changed)

    def titles(self):
        with self.store.connect() as db:
            return sorted(r[0] for r in db.execute("SELECT id FROM live_effects WHERE kind='title'").fetchall())

    def test_the_board_is_this_weeks_net_won(self):
        a, b, c = self.player('Lan', wallet=10000), self.player('Minh', wallet=10000), self.player('Hoa', wallet=10000)
        self.win(a, 10)
        self.win(b, 30)
        self.lose(c, 20)
        self.win(a, 10)
        self.lose(a, 5)
        v = self.board(b)
        self.assertEqual(v['board'], fh.board())
        self.assertEqual([r['name'] for r in v['rows']], ['Minh', 'Lan'])        # biggest first, Hoa (a loss) not on it
        self.assertEqual([r['xu'] for r in v['rows']], [self.net(b), self.net(a)])
        self.assertTrue(all(r['days'] >= 1 for r in v['rows']))                  # an older client shows "N ngày chơi"
        self.assertEqual((v['me']['rank'], v['total']), (1, 2))
        self.assertEqual((v['fair']['win'], v['fair']['weekly'], v['fair']['week'], v['fair']['next']),
                         (True, True, '2026-10-12', int(MON2)))
        self.assertLess(self.net(c), 0)
        self.assertIsNone(self.board(c)['me']['rank'])
        self.assertNotIn(self.store.key(a), json.dumps(v))
        # the other board (Top lỗ) is the same rows, the other way round
        self.assertEqual([r['name'] for r in lb.view(self.store, 'fair-loss', 20, c)['rows']], ['Hoa'])
        # an older client asks by the edition: the same weekly board under the name it asked
        self.assertEqual(lb.view(self.store, fh.edition(), 20, a)['board'], fh.edition())
        # a new week starts at zero; the cumulative row (lời tích lũy) is untouched
        cum = fh.money_of(self.store.read(b)[0]['journey'])[0]
        self.clock.t = MON2 + 3600
        self.assertEqual((self.board(b)['rows'], self.net(b)), ([], 0))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT score FROM leaderboard WHERE board=? AND sid=?',
                                        (fh.board(), self.store.key(b))).fetchone()[0], cum)

    def test_hidden_names_are_not_ranked(self):
        a, b = self.player('Lan', wallet=10000), self.player('Minh', wallet=10000)
        self.win(a, 10)
        self.win(b, 30)
        with self.store.connect() as db:
            db.execute('INSERT INTO leaderboard_players(sid,name,show) VALUES(?,?,0) ON CONFLICT(sid) DO UPDATE SET show=0',
                       (self.store.key(b), 'Minh'))
        v = self.board(b)
        self.assertEqual([r['name'] for r in v['rows']], ['Lan'])
        self.assertFalse(v['me']['visible'])

    def test_a_fine_refund_paid_this_week_counts_once(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 10)
        won = self.net(a)
        self.refund(a, 7, 'g-other-gift-0001')                      # another gift: not fair money
        self.assertEqual(self.net(a), won)
        self.refund(a, 300, 'refund-cd-20261011-week0001')
        self.assertEqual(self.net(a), won + 300)
        # paid once: a second load, a replayed command, the save already holding the id
        self.assertFalse(sg.on_load(self.store, a, self.store.read(a)[0])[0])
        rev = self.store.read(a)[1]
        self.store.command(a, 'sysgift-refund-cd-20261011-week0001', rev, None, sg.ACTION,
                           dict(id='refund-cd-20261011-week0001', coins=300), internal=True)
        self.assertEqual(self.net(a), won + 300)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM leaderboard_meta WHERE k LIKE 'fair-loss:refund:%'").fetchone()[0], 1)
        # a big enough refund lifts a week's loss onto Top lời
        b = self.player('Minh', wallet=10000)
        self.lose(b, 20)
        self.assertEqual(lb.view(self.store, 'fair-loss', 20, b)['me']['rank'], 1)
        self.refund(b, 50, 'refund-cd-20261011-week0002')
        self.assertEqual(self.net(b), 30)
        self.assertEqual(self.board(b)['me']['rank'], 2)

    def test_monday_crowning_from_the_week_once_without_money(self):
        players = [self.player(f'Người {i}', wallet=10000) for i in range(12)]
        for i, p in enumerate(players):
            for _ in range(i + 1):
                self.win(p, 1)
        self.lose(players[0], 500)                                   # off Top lời, onto Top lỗ
        order = [r['name'] for r in self.board()['rows']]
        self.assertEqual(len(order), 11)
        self.clock.t = MON2 + self.fl.GRACE + 1
        errors, got = [], []

        def settle():
            try:
                got.append(fb.settle(self.store, self.clock.t))
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=settle) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        crowned = [g for g in got if g]
        self.assertEqual(len(crowned), 1)
        self.assertEqual([w['title'] for w in crowned[0]], ['f_king'] + ['f_master'] * 9)
        top = self.store.key(players[-1])
        self.assertEqual(crowned[0][0]['sid'], top)
        self.assertEqual(len([t for t in self.titles() if t.startswith('fair20261009:')]), 10)
        self.assertEqual(len([t for t in self.titles() if t.startswith('fair-loss:')]), 1)   # Top lỗ crowned with it
        before = self.store.read(players[-1])[0]['journey']['wallet']
        self.assertTrue(live_effects.on_load(self.store, players[-1], self.store.read(players[-1])[0]))
        state = self.store.read(players[-1])[0]
        self.assertEqual(state['journey']['wallet'], before)
        self.assertIn('f_king', state['journey']['titles'])
        self.clock.t = MON2 + 7200
        view = self.board(players[0])['fair']
        self.assertEqual((view['crowned'], view['winners'][0]['name'], view['winners'][0]['title']),
                         ('2026-10-19', order[0], 'Vua trò chơi'))
        # deleting an account hides its id in the stored crowning
        self.store.delete(players[-1])
        with self.store.connect() as db:
            self.assertNotIn(top, db.execute("SELECT v FROM leaderboard_meta WHERE k='fair:fair20261009@2026-10-19'").fetchone()[0])

    def test_a_week_an_older_release_crowned_is_not_crowned_again(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 5)
        with self.store.connect() as db:   # 2.4.3 got to 19/10 first: the cumulative board's crowning, same key
            db.execute("INSERT INTO leaderboard_meta(k,v) VALUES('fair:fair20261009@2026-10-19','[]')")
        self.clock.t = MON2 + self.fl.GRACE + 1
        self.assertIsNone(fb.settle(self.store, self.clock.t))
        self.assertEqual(self.titles(), [])

    def test_recompute_week_adds_refunds_paid_before_the_release(self):
        a, b = self.player('Lan', wallet=10000), self.player('Minh', wallet=10000)
        self.win(a, 10)
        self.refund(a, 250, 'refund-cd-20261011-week0003')
        self.refund(b, 90, 'refund-cd-20261011-week0004')
        won = self.net(a)
        sa, sb = self.store.key(a), self.store.key(b)
        # as 2.4.3 left them: the refunds paid, no marker, not in the week's net
        with self.store.connect() as db:
            db.execute("DELETE FROM leaderboard_meta WHERE k LIKE 'fair-loss:refund:%'")
            db.execute('UPDATE fair_loss_week SET net=net-250 WHERE sid=?', (sa,))
            db.execute('UPDATE fair_loss_week SET net=net-90 WHERE sid=?', (sb,))
        # a refund paid last week is not this week's
        with self.store.connect() as db:
            db.execute("UPDATE system_gifts SET applied_at=? WHERE id='refund-cd-20261011-week0004'", (MON1 - 60,))
        saves = (self.store.read(a), self.store.read(b))
        script = _script()

        def run(*args):
            with patch.object(script, 'Store', return_value=self.store), patch.object(self.store, 'close_pool'), \
                    patch('sys.argv', ['x', '--week', *args]), redirect_stdout(io.StringIO()) as out:
                script.main()
            return out.getvalue()
        out = run()
        self.assertIn('1 fine refunds paid this week not in its net yet', out)
        self.assertNotIn(sa, out)
        self.assertEqual(self.net(a), won - 250)                    # dry run
        out = run('--apply')
        self.assertIn('written: added 1', out)
        self.assertEqual((self.net(a), self.net(b)), (won, 0))
        self.assertIn('0 fine refunds', run('--apply'))             # once
        self.assertEqual((self.store.read(a), self.store.read(b)), saves)   # saves and revisions untouched
        # a gift the save does not hold is never counted
        self.assertEqual(self.fl.fold_refund(self.store, 'refund-cd-20261011-none0001', sa, 5), 'unpaid')

    def test_243_on_the_same_database(self):
        """After this release crowned a week and counted a refund, 2.4.3 (`git archive rel-2.4.3`) runs on the same
        database: its schema check is a no-op at 43, its Monday crowning finds the week's key and grants nothing
        again, and both boards render."""
        import os
        import subprocess
        import sys
        import tarfile
        import tempfile
        from pathlib import Path
        a, b = self.player('Lan', wallet=10000), self.player('Minh', wallet=10000)
        self.win(a, 10)
        self.lose(b, 10)
        self.refund(a, 40, 'refund-cd-20261011-roll0001')
        self.clock.t = MON2 + self.fl.GRACE + 1
        self.assertEqual([w['title'] for w in fb.settle(self.store, self.clock.t)], ['f_king'])
        titles = self.titles()
        root = Path(__file__).resolve().parents[1]
        tmp = tempfile.mkdtemp(prefix='mnl-243-')
        try:
            data = subprocess.run(['git', 'archive', 'rel-2.4.3', 'game', 'reference'], cwd=root, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest('no git tree with rel-2.4.3')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        prog = ('import json,sys,game;from game.storage import Store;from game import fair_board as fb,leaderboard as lb,fair as fh\n'
                's=Store(sys.argv[1],story=True);t=float(sys.argv[2])\n'
                'got=fb.settle(s,t);fb._done.clear();again=fb.settle(s,t+3600)\n'
                'win=lb.view(s,fh.board(),20,None);loss=lb.view(s,"fair-loss",20,None)\n'
                'print(json.dumps(dict(v=game.__version__,got=got,again=again,crowned=win["fair"].get("crowned"),'
                'winners=[w["name"] for w in win["fair"]["winners"]],loss=[r["name"] for r in loss["rows"]])))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}   # a test module's career filter
        env['PYTHONPATH'] = tmp
        out = subprocess.run([sys.executable, '-c', prog, self.store.path, str(MON2 + 7200)], capture_output=True, text=True,
                             cwd=tmp, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual((got['v'], got['got'], got['again'], got['crowned'], got['winners']),
                         ('2.4.3', None, None, '2026-10-19', ['Lan']))
        self.assertIsInstance(got['loss'], list)                         # Top lỗ renders (its week: the real clock)
        self.assertEqual(self.titles(), titles)                         # nothing granted twice
