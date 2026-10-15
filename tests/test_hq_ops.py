"""🛃 Hải quan across players (game/hq_ops.py; owner spec 14/10, I.1.1.4): an officer inspects another player's shop
(evidence read from the shop's own save: overdue tax bills, the till), proposes a measure; a higher post (or the Cục's
automatic review) approves; a measure without grounds disciplines the officer (and a player who approved it), the
third within 14 days expels; the owner is told and may appeal; limits against abuse (friends, spouses, oneself, the
daily cap, the cooldowns).

No PostgreSQL needed: the handlers run against an in-memory SQLite database holding the real hq_* tables of
game/pg_schema.py and in-memory saves (hq_ops._read / _mutate replaced: every save a handler changes is validated in
full, the database part runs in one transaction with it)."""
import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest import mock

from game import engine as eng
from game import hq_ops as H
from game import jail
from game import operations as ops
from game import org as ORG
from game import promotion as pm
from game.engine import validate_state
from game.marriage import MarriageError
from game.social import pid_of
from tests.test_black_market import story
from tests.test_cand_ops import Clock, _ddl, fake_mutate, fake_read
from tests.test_career_customs import P, officer

T0 = 1_792_000_000.0


class FakeStore:
    def __init__(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        for t in ('hq_roster', 'hq_cases'):
            self.db.execute(_ddl(t))
        self.db.execute('CREATE TABLE friends (sid TEXT NOT NULL, friend TEXT NOT NULL, since REAL NOT NULL, PRIMARY KEY (sid, friend))')
        self.db.execute('CREATE TABLE marriage_bonds (sid TEXT PRIMARY KEY, couple INTEGER NOT NULL)')
        self.db.execute('CREATE TABLE profiles (pid TEXT PRIMARY KEY, sid TEXT, name TEXT, shop TEXT, visible INTEGER, hidden INTEGER, seen REAL)')
        self.db.execute('CREATE TABLE accounts (sid TEXT PRIMARY KEY, display TEXT)')
        self.db.execute('CREATE TABLE inbox (id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, kind TEXT, text TEXT, ref TEXT, at REAL)')
        self.states, self.writes = {}, 0

    @contextmanager
    def connect(self):
        yield self.db

    def transaction(self, fn, best_effort_ms=None):
        self.db.execute('BEGIN')
        try:
            out = fn(self.db)
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        self.db.execute('COMMIT')
        return out

    def add(self, sid, state, name, account=True):
        self.states[sid] = state
        shop = json.dumps(dict(careers=[dict(id='grocery', name='Tạp hóa')]))
        self.db.execute('INSERT INTO profiles(pid,sid,name,shop,visible,hidden,seen) VALUES(?,?,?,?,1,0,?)', (pid_of(sid), sid, name, shop, T0))
        if account:
            self.db.execute('INSERT INTO accounts(sid,display) VALUES(?,?)', (sid, name))
        validate_state(state)

    def inbox(self, sid):
        return [r['text'] for r in self.db.execute('SELECT text FROM inbox WHERE pid=? ORDER BY id', (pid_of(sid),))]


def shop(late=5, debt=500, till=320):
    """A save whose grocery has one tax bill `late` days past due and `till` xu in the till."""
    s = story(5000)
    c = s['careers']['grocery']
    c['day'] = 10
    if till != c['money']:
        eng.money(s, c, till - c['money'], 'Vốn thử', None)
    ops.bill(c, 'tax-p1', 'tax', 'Thuế 5% · kỳ kết ngày 3', debt, 10 - late, 'p1')
    validate_state(s)
    return s


@unittest.skipIf(P is None, 'customs filtered out')
class Rules(unittest.TestCase):
    """The pure rules: what an inspection finds and when a measure has grounds."""

    def test_findings_read_only_overdue_tax(self):
        f = H.findings(shop())
        self.assertEqual((f['debt'], f['late'], f['items'][0]['career'], f['items'][0]['till']), (500, 5, 'grocery', 320))
        s = shop()
        s['careers']['grocery']['ops']['finance']['bills'][-1]['due'] = 10    # due today: not late yet
        self.assertEqual(H.findings(s)['items'], [])
        self.assertEqual(H.findings(story(100))['items'], [])

    def test_grounds(self):
        self.assertTrue(H.grounded(H.findings(shop(late=2)), 'collect'))
        self.assertFalse(H.grounded(H.findings(shop(late=1)), 'collect'))
        self.assertTrue(H.grounded(H.findings(shop(late=5, till=320)), 'seize'))
        self.assertFalse(H.grounded(H.findings(shop(late=5, till=900)), 'seize'))   # the till pays: nothing to sell
        self.assertFalse(H.grounded(H.findings(shop(late=4, till=0)), 'seize'))
        self.assertTrue(H.grounded(H.findings(shop(late=1)), 'remind'))
        self.assertFalse(H.grounded(H.findings(story(100)), 'remind'))

    def test_collect_never_into_debt_and_seize_sells_stock_first(self):
        s = shop(till=320)
        out = H.apply(s, 'collect', H.findings(s))
        self.assertEqual((out['paid'], out['due']), (0, 1))
        validate_state(s)
        s = shop(till=900)
        H.apply(s, 'collect', H.findings(s))
        c = s['careers']['grocery']
        self.assertEqual((c['money'], c['ops']['finance']['bills'][-1]['status']), (400, 'paid'))
        validate_state(s)
        s = shop(till=320)
        qty0 = sum(l['qty'] for l in s['careers']['grocery']['ext']['inv']['lots'])
        out = H.apply(s, 'seize', H.findings(s))
        c = s['careers']['grocery']
        self.assertEqual(out['paid'], 500)
        self.assertGreaterEqual(out['sold'], 180)
        self.assertLess(sum(l['qty'] for l in c['ext']['inv']['lots']), qty0)
        self.assertGreaterEqual(c['money'], 0)
        validate_state(s)


@unittest.skipIf(P is None, 'customs filtered out')
class Ops(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(T0)
        self.store = FakeStore()
        for target, name, fn in ((H, 'now', self.clock), (jail, 'now', self.clock), (pm, '_now', self.clock), (H, '_read', fake_read),
                                 (H, '_mutate', fake_mutate), (H, '_lock', lambda db, key: None), (H, '_push', lambda store, sid, text: None)):
            p = mock.patch.object(target, name, fn)
            p.start()
            self.addCleanup(p.stop)
        self.store.add('ktv', officer('hq_ktv', 'ktv_2').state, 'Kiểm')
        self.store.add('doi', officer('hq_doi', 'ktvc_3').state, 'Đội')
        self.store.add('tap', officer('hq_ts', 'tap_su').state, 'Tập')
        self.store.add('own', shop(), 'Chủ')

    def act(self, sid, op, **d):
        return H.ACTIONS[op](self.store, sid, self.store.db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()['display'], d)

    def err(self, sid, op, **d):
        with self.assertRaises(MarriageError) as e:
            self.act(sid, op, **d)
        return e.exception.code

    def org_of(self, sid):
        return pm.record(self.store.states[sid], 'customs')['org']

    def inspect(self, sid='ktv', target='own'):
        return self.act(sid, 'hq_inspect', pid=pid_of(target))

    # ---- who may inspect whom
    def test_a_tap_su_or_a_citizen_may_not(self):
        self.assertEqual(self.err('tap', 'hq_inspect', pid=pid_of('own')), 'hq_off')
        self.store.add('cit', story(100), 'Dân')
        self.assertEqual(self.err('cit', 'hq_shops'), 'hq_off')

    def test_not_oneself_a_friend_or_a_spouse(self):
        self.assertEqual(self.err('ktv', 'hq_inspect', pid=pid_of('ktv')), 'self')
        self.store.db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', ('ktv', 'own', T0))
        self.assertEqual(self.err('ktv', 'hq_inspect', pid=pid_of('own')), 'hq_conflict')
        self.assertNotIn(pid_of('own'), [x['pid'] for x in self.act('ktv', 'hq_shops')['shops']])
        self.store.db.execute('DELETE FROM friends')
        self.store.db.executemany('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', [('ktv', 7), ('own', 7)])
        self.assertEqual(self.err('ktv', 'hq_inspect', pid=pid_of('own')), 'hq_conflict')

    def test_the_shift_must_be_open(self):
        self.store.states['ktv']['careers']['customs']['open'] = False
        self.assertEqual(self.err('ktv', 'hq_inspect', pid=pid_of('own')), 'hq_off')

    def test_cooldowns_and_the_daily_cap(self):
        self.inspect()
        self.assertEqual(self.err('doi', 'hq_inspect', pid=pid_of('own')), 'hq_recent')   # a shop once per 24 h
        self.clock.t += 25 * 3600
        self.assertEqual(self.err('ktv', 'hq_inspect', pid=pid_of('own')), 'hq_pair')     # the same pair once per 72 h
        self.inspect('doi')
        for i in range(H.OFFICER_DAY_MAX):
            self.store.add(f'o{i}', story(100), f'C{i}')
        for i in range(H.OFFICER_DAY_MAX - 1):
            self.act('doi', 'hq_inspect', pid=pid_of(f'o{i}'))
        self.assertEqual(self.err('doi', 'hq_inspect', pid=pid_of(f'o{H.OFFICER_DAY_MAX - 1}')), 'hq_day_max')

    # ---- inspections and proposals
    def test_a_clean_shop_closes_clear(self):
        self.store.add('clean', story(100), 'Sạch')
        r = self.act('ktv', 'hq_inspect', pid=pid_of('clean'))
        self.assertEqual((r['case']['status'], r['measures']), ('clear', []))
        self.assertIn('Không phát hiện', self.store.inbox('clean')[-1])
        self.assertEqual(self.err('ktv', 'hq_propose', case=r['case']['id'], measure='remind'), 'hq_gone')

    def test_remind_is_done_at_once(self):
        cid = self.inspect()['case']['id']
        self.assertIn('Phát hiện', self.store.inbox('own')[0])
        self.act('ktv', 'hq_propose', case=cid, measure='remind')
        self.assertIn('Hải quan nhắc', self.store.inbox('own')[-1])
        self.assertEqual(self.store.db.execute('SELECT status FROM hq_cases').fetchone()['status'], 'done')

    def test_a_grounded_seize_approved_by_a_higher_post(self):
        cid = self.inspect()['case']['id']
        self.act('ktv', 'hq_propose', case=cid, measure='seize')
        self.assertEqual(self.err('ktv', 'hq_review', case=cid, ok=True), 'self')
        self.assertEqual([x['id'] for x in self.act('doi', 'hq_reviews')['reviews']], [cid])
        adj = self.org_of('ktv')['adj']
        self.act('doi', 'hq_review', case=cid, ok=True)
        row = self.store.db.execute('SELECT status,amount,wrong,rwrong FROM hq_cases').fetchone()
        self.assertEqual((row['status'], row['amount'], row['wrong'], row['rwrong']), ('done', 500, 0, 0))
        self.assertEqual(self.store.states['own']['careers']['grocery']['ops']['finance']['bills'][-1]['status'], 'paid')
        self.assertEqual(self.org_of('ktv')['adj'], adj + H.REWARD_ADJ)
        mine = self.act('own', 'hq_mine')['cases'][0]
        self.assertTrue(mine['can_appeal'])
        r = self.act('own', 'hq_appeal', case=cid)            # grounded: kept
        self.assertIn('giữ nguyên', r['message'])
        self.assertEqual(self.err('own', 'hq_appeal', case=cid), 'hq_gone')

    def test_only_a_higher_post_reviews(self):
        self.store.add('ktv2', officer('hq_ktv', 'ktv_1').state, 'Kiểm 2')
        cid = self.inspect()['case']['id']
        self.act('ktv', 'hq_propose', case=cid, measure='collect')
        self.assertEqual(self.act('ktv2', 'hq_reviews')['reviews'], [])
        self.assertEqual(self.err('ktv2', 'hq_review', case=cid, ok=True), 'hq_rank')
        self.store.db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', ('doi', 'own', T0))
        self.assertEqual(self.err('doi', 'hq_review', case=cid, ok=True), 'hq_conflict')

    def test_a_proposal_without_grounds_rejected_disciplines_the_officer(self):
        self.store.states['own'] = shop(late=5, till=900)       # the till pays: a seizure has no grounds
        cid = self.inspect()['case']['id']
        self.act('ktv', 'hq_propose', case=cid, measure='seize')
        g = self.org_of('ktv')['g']
        self.act('doi', 'hq_review', case=cid, ok=False)
        self.assertEqual(self.org_of('ktv')['g'], g - 1)         # giáng 1 bậc
        self.assertGreaterEqual(pm.record(self.store.states['ktv'], 'customs')['cx']['hold'], 15)   # giam hàm 15 ngày
        self.assertEqual(ORG.svc_count(self.store.states['ktv'], 'customs'), 1)
        self.assertTrue(any('chèn ép' in t for t in self.store.inbox('ktv')))
        self.assertEqual(self.store.states['own']['careers']['grocery']['ops']['finance']['bills'][-1]['status'], 'unpaid')

    def test_approving_without_grounds_disciplines_both_and_the_appeal_reverses(self):
        self.store.states['own'] = shop(late=5, till=900)
        cid = self.inspect()['case']['id']
        self.act('ktv', 'hq_propose', case=cid, measure='seize')
        gk, gd = self.org_of('ktv')['g'], self.org_of('doi')['g']
        self.act('doi', 'hq_review', case=cid, ok=True)
        self.assertEqual((self.org_of('ktv')['g'], self.org_of('doi')['g']), (gk - 1, gd - 1))
        till = self.store.states['own']['careers']['grocery']['money']
        r = self.act('own', 'hq_appeal', case=cid)
        self.assertIn('hoàn trả 500 xu', r['message'])
        self.assertEqual(self.store.states['own']['careers']['grocery']['money'], till + 500)
        self.assertEqual(self.org_of('ktv')['g'], gk - 1)       # not twice for the same case
        self.assertEqual(self.store.db.execute('SELECT status FROM hq_cases').fetchone()['status'], 'reversed')
        validate_state(self.store.states['own'])

    def test_the_cucs_review_approves_only_what_is_grounded(self):
        self.store.add('own2', shop(late=5, till=900), 'Chủ 2')
        a = self.inspect()['case']['id']
        b = self.act('doi', 'hq_inspect', pid=pid_of('own2'))['case']['id']
        self.act('ktv', 'hq_propose', case=a, measure='collect')    # grounded (5 days late) but the till is short
        self.act('doi', 'hq_propose', case=b, measure='seize')      # not grounded
        g = self.org_of('doi')['g']
        self.clock.t += H.REVIEW_S + 60
        self.act('own', 'hq_mine')                                   # any hq_* request runs the sweep
        rows = {r['id']: dict(r) for r in self.store.db.execute('SELECT id,status,reviewer,wrong FROM hq_cases')}
        self.assertEqual((rows[a]['status'], rows[a]['reviewer'], rows[a]['wrong']), ('done', '', 0))
        self.assertEqual((rows[b]['status'], rows[b]['wrong']), ('rejected', 1))
        self.assertEqual(self.org_of('doi')['g'], g - 1)
        self.assertIn('quỹ cửa hàng chưa đủ', self.store.inbox('own')[-1])

    def test_the_third_wrong_case_in_14_days_expels(self):
        self.store.add('kc', officer('hq_ktvc', 'ktvc_2').state, 'Chính')
        self.store.add('ccc', officer('hq_ccc', 'ktvcc_1').state, 'Chi cục')
        for i in range(H.WRONG_MAX):
            self.store.add(f's{i}', shop(late=5, till=900), f'S{i}')
            self.clock.t += 25 * 3600
            cid = self.act('kc', 'hq_inspect', pid=pid_of(f's{i}'))['case']['id']
            self.act('kc', 'hq_propose', case=cid, measure='seize')
            self.act('ccc', 'hq_review', case=cid, ok=False)
        rec = pm.record(self.store.states['kc'], 'customs')
        self.assertTrue(pm.expel_due(rec))
        self.assertEqual(self.err('kc', 'hq_shops'), 'hq_off')
        self.assertEqual(ORG.svc_count(self.store.states['kc'], 'customs'), 3)

    def test_appeal_window_and_strangers(self):
        cid = self.inspect()['case']['id']
        self.act('ktv', 'hq_propose', case=cid, measure='seize')
        self.act('doi', 'hq_review', case=cid, ok=True)
        self.assertEqual(self.err('doi', 'hq_appeal', case=cid), 'not_found')
        self.clock.t += H.APPEAL_S + 1
        self.assertEqual(self.err('own', 'hq_appeal', case=cid), 'hq_late')
        self.assertFalse(self.act('own', 'hq_mine')['cases'][0]['can_appeal'])

    def test_bad_payloads(self):
        self.assertEqual(self.err('ktv', 'hq_inspect', pid='nope'), 'not_found')
        self.assertEqual(self.err('ktv', 'hq_propose', case='hq' + '0' * 16, measure='burn'), 'bad_measure')
        self.assertEqual(self.err('ktv', 'hq_propose', case="x' OR 1=1", measure='remind'), 'not_found')
        self.assertEqual(self.err('doi', 'hq_review', case='hq' + '0' * 16, ok='yes'), 'bad_ok')


if __name__ == '__main__':
    unittest.main()
