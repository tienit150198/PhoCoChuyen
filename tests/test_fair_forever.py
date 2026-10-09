"""🕶️ Owner 09/10: "chợ đen mở mãi đi, k có thời hạn nhé" (game/fair.py FAIR_DAYS 0, forever(); game/fair_board.py
crown()). The edition fair20261009 stays open for good: every stall long after the old five days, no countdown on the
client (`forever`), the same edition (money, board, gift), a vay nóng that waits to be paid back, the titles crowned
every Monday from the running Bảng vàng (once a week, no row twice), and saves written here still valid on the
releases this one may be rolled back to (1.9.29 9f084739, 1.9.30 65dafa3b)."""
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import fair_board as fb
from game import fair_cash as fc
from game import leaderboard as lb
from game import live_effects as lfx
from game import needs as nd
from game.engine import apply_action, migrate_state, public_state, validate_state
from tests.test_fair import AFTER, OPEN, Dice, FairBase, StoreBase, at, story

ROOT = Path(__file__).resolve().parents[1]
OLD_RELEASES = ('9f084739', '65dafa3b')   # 1.9.29 and 1.9.30: the releases this one may be rolled back to
LATER = at(2026, 10, 20, 21)                # a week after the old five days
MUCH_LATER = at(2027, 3, 1, 9)
MON1 = at(2026, 10, 12, 0)                  # the first Monday after the opening: the first crowning
MON2 = at(2026, 10, 19, 0)


class OpenForGood(FairBase):
    def test_no_end(self):
        self.assertTrue(fh.forever())
        self.assertEqual(fh.FAIR_DAYS, 0)
        self.assertEqual(fh.window(), (int(at(2026, 10, 9, 0)), fh.NEVER))
        self.assertEqual((fh.edition(), fh.board()), ('fair20261009', 'fair20261009xu'))   # the same edition goes on
        for t in (AFTER, LATER, MUCH_LATER):
            self.assertTrue(fh.is_open(t), t)

    def test_every_stall_long_after_the_old_close(self):
        for t in (AFTER + 1, LATER, MUCH_LATER):
            self.clock.t = t
            s = story(1000)
            n = nd.ensure(s)
            n.update(full=50, wake=50)
            self.dice(Dice(faces=['ga', 'bau', 'ca'], draws=[.99] * 9))
            s, _ = self.act(s, 'fair_bc', bets={'cua': 10})
            s, _ = self.act(s, 'fair_xd', side='chan', stake=10)
            s, _ = self.act(s, 'fair_gift')
            s, _ = self.act(s, 'fair_snack', item='bap_nuong')
            s, _ = self.act(s, 'fair_photo')
            s, _ = self.act(s, 'fair_borrow', amount=100)
            v = public_state(s)['fair']
            self.assertEqual((v['show'], v['open'], v['over'], v['soon'], v['forever']), (True, True, False, False, True), t)
            self.assertEqual(v['opens'], fh.window()[0])
            validate_state(migrate_state(json.loads(json.dumps(s))))

    def test_the_money_of_the_edition_goes_on(self):
        s = story(100)
        self.dice(Dice(faces=['cua'] * 3))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        before = fh.money_of(s['journey'])
        self.assertGreater(before[0], 0)
        self.clock.t = MUCH_LATER
        self.assertEqual(fh.money_of(s['journey']), before)               # no new edition: nothing resets
        self.dice(Dice(faces=['cua'] * 3))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(fh.money_of(s['journey']), (before[0] * 2, 2))
        self.assertEqual(s['journey']['fair']['ed'], 'fair20261009')

    def test_a_loan_waits_to_be_paid_back(self):
        s = story(0)
        s, _ = self.act(s, 'fair_borrow', amount=500)
        self.clock.t = MUCH_LATER
        s, _ = apply_action(s, None, 'settings', {'name': 'Lan'})          # no close: nothing collected
        j = s['journey']
        self.assertEqual((j['wallet'], j['fair_cash']['loan'], j['fair_cash']['debt']), (500, dict(ed='fair20261009', p=500, due=600), 0))
        self.assertEqual(public_state(s)['fair']['cash']['loan'], dict(p=500, due=600))
        self.assertEqual(self.refused(s, 'fair_borrow', amount=50), 'fair_loan_open')   # still one at a time
        s['journey']['wallet'] = 650
        s, _ = self.act(s, 'fair_repay')
        self.assertEqual((s['journey']['wallet'], s['journey']['fair_cash']['loan']), (50, None))
        s, _ = self.act(s, 'fair_borrow', amount=50)                       # paid back: a new one
        validate_state(s)

    def test_a_loan_of_an_earlier_edition_is_still_collected(self):
        s = story(0)
        s, _ = self.act(s, 'fair_borrow', amount=100)
        s['journey']['fair_cash']['loan']['ed'] = 'fair20261003'
        s['journey']['wallet'] = 500
        self.clock.t = LATER
        s, _ = apply_action(s, None, 'settings', {'name': 'Lan'})
        self.assertEqual((s['journey']['wallet'], s['journey']['fair_cash']['loan']), (500 - fc.owed(100), None))

    def refused(self, s, action, **p):
        from game.engine import GameError
        with self.assertRaises(GameError) as e:
            self.act(s, action, **p)
        return e.exception.code


class WeeklyCrowning(StoreBase):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(fb, 'now', lambda: self.clock.t)
        p.start()
        self.addCleanup(p.stop)

    def score(self, tok, rounds):
        self.dice(Dice(faces=['cua'] * (3 * rounds)))
        for _ in range(rounds):
            self.cmd(tok, 'fair_bc', {'bets': {'cua': 1}})

    def title_rows(self):
        with self.store.connect() as db:
            return sorted(r[0] for r in db.execute("SELECT id FROM live_effects WHERE kind='title'").fetchall())

    def test_crowned_every_monday_from_the_running_board(self):
        a, b = self.player('Anh Ba'), self.player('Chị Tư')
        self.score(a, 5)
        self.score(b, 3)
        sa, sb = self.store.key(a), self.store.key(b)
        self.assertEqual((fb.crown(OPEN), fb.next_crown(OPEN)), (None, int(MON1)))
        view = lb.view(self.store, fh.board(), 20, a)['fair']
        self.assertEqual((view['closes'], view['weekly'], view['next'], view['crowned'], view['settled'], view['winners']),
                         (fh.NEVER, True, int(MON1), None, False, []))
        self.assertIsNone(fb.settle(self.store, OPEN))                     # no crowning before the first Monday
        self.assertIsNone(fb.settle(self.store, MON1 + fb.GRACE - 1))
        got = fb.settle(self.store, MON1 + fb.GRACE)
        self.assertEqual([(w['rank'], w['sid'], w['title']) for w in got], [(1, sa, 'f_king'), (2, sb, 'f_master')])
        self.assertIsNone(fb.settle(self.store, MON1 + 3600))              # once a week
        fb._done.clear()                                                   # another process: the mark stops it
        self.assertIsNone(fb.settle(self.store, MON1 + 7200))
        self.assertEqual(self.title_rows(), sorted([f'fair20261009:f_king:{sa}', f'fair20261009:f_master:{sb}']))
        self.clock.t = MON1 + 7200
        view = lb.view(self.store, fh.board(), 20, b)['fair']
        self.assertEqual((view['crowned'], view['next'], view['settled']), ('2026-10-12', int(MON2), True))
        self.assertEqual([(w['rank'], w['name'], w['me']) for w in view['winners']], [(1, 'Anh Ba', False), (2, 'Chị Tư', True)])
        # the week after: Chị Tư goes ahead, so she is crowned king and Anh Ba master (new rows for both)
        self.score(b, 4)
        got = fb.settle(self.store, MON2 + fb.GRACE)
        self.assertEqual([(w['rank'], w['sid'], w['title']) for w in got], [(1, sb, 'f_king'), (2, sa, 'f_master')])
        self.assertEqual(self.title_rows(), sorted([f'fair20261009:f_king:{sa}', f'fair20261009:f_master:{sb}',
                                                    f'fair20261009:f_king:{sb}', f'fair20261009:f_master:{sa}']))
        self.clock.t = MON2 + 3600
        view = lb.view(self.store, fh.board(), 20, b)['fair']
        self.assertEqual((view['crowned'], view['winners'][0]['name']), ('2026-10-19', 'Chị Tư'))
        # a third week with the same standings: nobody gets a row twice
        fb.settle(self.store, at(2026, 10, 26, 0) + fb.GRACE)
        self.assertEqual(len(self.title_rows()), 4)
        # paid into the save on the next load, once each
        self.assertTrue(lfx.on_load(self.store, b, self.store.read(b)[0]))
        self.assertFalse(lfx.on_load(self.store, b, self.store.read(b)[0]))
        tb = self.store.read(b)[0]['journey']['titles']
        self.assertTrue('f_king' in tb and 'f_master' in tb)

    def test_a_missed_monday_crowns_only_the_latest(self):
        a = self.player('Anh Ba')
        self.score(a, 2)
        got = fb.settle(self.store, at(2026, 11, 4, 12))                   # down from 11/10 to 04/11
        self.assertEqual([w['title'] for w in got], ['f_king'])
        with self.store.connect() as db:
            keys = [r[0] for r in db.execute("SELECT k FROM leaderboard_meta WHERE k LIKE 'fair:fair20261009%'").fetchall()]
        self.assertEqual(keys, ['fair:fair20261009@2026-11-02'])

    def test_after_an_end_crowned_by_an_older_server(self):
        """After a rollback to a release with the five days, that server crowned the end ('fair:<edition>'); back on
        this one, the weeks go on and nobody gets a title row twice."""
        a = self.player('Anh Ba')
        self.score(a, 2)
        with mock.patch.dict(os.environ, {'MNL_FAIR_DAYS': '5'}):
            fb.settle(self.store, AFTER + fb.GRACE)
        fb._done.clear()
        self.clock.t = AFTER + 3600
        view = lb.view(self.store, fh.board(), 20, a)['fair']
        self.assertEqual([w['name'] for w in view['winners']], ['Anh Ba'])   # the end's, or 12/10's (the same board)
        self.assertEqual(len(self.title_rows()), 1)
        fb.settle(self.store, MON2 + fb.GRACE)
        self.assertEqual(len(self.title_rows()), 1)                        # the same title again: no second row
        self.clock.t = MON2 + 3600
        self.assertEqual(lb.view(self.store, fh.board(), 20, a)['fair']['crowned'], '2026-10-19')


class OlderServers(FairBase):
    """Saves written while the Chợ đen has no end (long after the old five days: rounds, the gift, an open loan, a
    weekly title) validate on the releases this one may be rolled back to. Such a release (FAIR_DAYS 5) then sees the
    edition closed after 14/10 00:00 (no new rounds, the loan collected): accepted on a rollback."""

    def old_tree(self, rev):
        if os.environ.get('MNL_FAIR_OLD_TREE'):
            return Path(os.environ['MNL_FAIR_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix=f'mnl-{rev}-')
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev} (MNL_FAIR_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def saves(self):
        self.clock.t = LATER
        s = story(5000)
        n = nd.ensure(s)
        n.update(full=50, wake=50)
        s, _ = self.act(s, 'fair_gift')
        self.dice(Dice(faces=['cua'] * 3))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 10})
        s, _ = self.act(s, 'fair_xd', side='chan', stake=20)
        s, _ = self.act(s, 'fair_snack', item='bap_nuong')
        s, _ = self.act(s, 'fair_borrow', amount=200)
        s['journey']['titles']['f_king'] = s['journey']['life_day']    # as live_effects pays a weekly title
        validate_state(s)
        loan = json.loads(json.dumps(s))
        self.clock.t = MUCH_LATER
        s, _ = self.act(s, 'fair_repay')
        s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=1)
        return [loan, json.loads(json.dumps(s))]

    def test_saves_validate_on_the_rollback_releases(self):
        saves = self.saves()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'public_state(s);out.append([s["journey"]["fair"]["ed"],s["journey"]["fair_cash"]["loan"]])\nprint(json.dumps(out))')
        for rev in OLD_RELEASES:
            with self.subTest(rev=rev):
                old = self.old_tree(rev)
                env = {k: v for k, v in os.environ.items() if not k.startswith('MNL_FAIR_')}
                env['PYTHONPATH'] = os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x)
                out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True,
                                     text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
                self.assertEqual(out.returncode, 0, out.stderr[-3000:])
                self.assertEqual(json.loads(out.stdout), [['fair20261009', dict(ed='fair20261009', p=200, due=240)],
                                                          ['fair20261009', None]])


if __name__ == '__main__':
    unittest.main()
