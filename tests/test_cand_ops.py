"""👮 Công an phường Mây across players (game/cand_ops.py, live/cand.py): the patrol at Chợ đen (evidence, the small
player's exemption, the levels, fines, jail, cooldowns and caps, envelopes taken / refused / found out with a fixed
draw) and the commanders (the force, commendations and expulsions and their limits).

No PostgreSQL needed: the handlers run against an in-memory SQLite database holding the real cand_* tables of
game/pg_schema.py, and in-memory saves (cand_ops._read / _mutate replaced: every save a handler changes is validated
in full, the database part runs in one transaction with it)."""
import copy
import os
import re
import sqlite3
import unittest
from contextlib import contextmanager
from unittest import mock

from game import cand_ops as K
from game import cand_roster as CR
from game import fair as fh
from game import fair_bm as bm
from game import jail
from game import org as ORG
from game import pg_schema
from game import promotion as pm
from game.engine import validate_state
from game.social import pid_of
from tests.test_black_market import OPEN, story
from tests.test_org_police import officer

T0 = OPEN   # 2026-10-10 20:00 Vietnam time: the Chợ đen is open


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


# ------------------------------------------------------------------------------------- an in-memory store
def _ddl(name: str) -> str:
    m = re.search(rf'CREATE TABLE IF NOT EXISTS {name} \(.*?\n\);', pg_schema.TABLES_DDL, re.S)
    return m.group(0).replace(pg_schema.T, 'TEXT')


class FakeStore:
    def __init__(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        for t in ('cand_roster', 'cand_stops', 'cand_acts'):
            self.db.execute(_ddl(t))
        self.db.execute('CREATE TABLE profiles (pid TEXT PRIMARY KEY, sid TEXT)')
        self.db.execute('CREATE TABLE accounts (sid TEXT PRIMARY KEY, display TEXT)')
        self.db.execute('CREATE TABLE friends (sid TEXT, friend TEXT, since REAL)')
        self.db.execute('CREATE TABLE inbox (id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, kind TEXT, text TEXT, ref TEXT, at REAL)')
        self.states, self.events, self.writes = {}, [], 0

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
        self.db.execute('INSERT INTO profiles(pid,sid) VALUES(?,?)', (pid_of(sid), sid))
        if account:
            self.db.execute('INSERT INTO accounts(sid,display) VALUES(?,?)', (sid, name))
        validate_state(state)

    def inbox(self, sid):
        return [r['text'] for r in self.db.execute('SELECT text FROM inbox WHERE pid=? ORDER BY id', (pid_of(sid),))]


def fake_read(store, sid):
    return (copy.deepcopy(store.states[sid]), 1) if sid in store.states else None


def fake_mutate(store, fns, ops=None):
    from game import marriage as mr
    new = {}
    for sid, fn in fns.items():
        mr.need(sid in store.states, 'Không tìm thấy tiến trình của người chơi này.', 'session_missing', 404)
        s = copy.deepcopy(store.states[sid])
        fn(s)
        validate_state(s)   # every save a handler changes stays a valid save
        new[sid] = s
    out = store.transaction(lambda db: ops(db) if ops else None)
    store.states.update(new)
    store.writes += 1
    return dict(db=out)


class Base(unittest.TestCase):
    def setUp(self):
        for k, v in {'MNL_JAIL_OFF': '0'}.items():
            p = mock.patch.dict(os.environ, {k: v})
            p.start()
            self.addCleanup(p.stop)
        for k in ('MNL_FAIR_START', 'MNL_FAIR_DAYS'):
            os.environ.pop(k, None)
        self.clock = Clock(T0)
        self.store = FakeStore()
        for target, new in ((K, 'now'), (fh, 'now'), (jail, 'now')):
            p = mock.patch.object(target, new, self.clock)
            p.start()
            self.addCleanup(p.stop)
        for name, fn in (('_read', fake_read), ('_mutate', fake_mutate), ('_lock', lambda db, key: None),
                         ('_push', lambda store, sid, text: None), ('_notify', lambda db, ev: self.store.events.append(ev))):
            p = mock.patch.object(K, name, fn)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(pm, '_now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.draw = None   # the detection draw: None = the real one, True / False forced
        p = mock.patch.object(K, '_roll', lambda stop_id, prob: self.draws.append(prob) or (self.draw if self.draw is not None else False))
        p.start()
        self.addCleanup(p.stop)
        self.draws = []

    # ---- people
    def cop(self, sid='off', name='Hùng', post='to_vien', grade='trung_uy', wallet=1000):
        j = officer(post, grade)
        j.state['journey']['wallet'] = wallet
        j.state['name'] = name   # the character's name (the roster's), kept in step with the account's
        self.store.add(sid, j.state, name)
        return sid

    def player(self, sid='tgt', name='Lan', wallet=200_000, stake=60_000, ago=60, net=0, big=0, account=True):
        s = story(wallet)
        self.gambled(s, stake, ago, net, big)
        self.store.add(sid, s, name, account)
        return sid

    def gambled(self, s, stake, ago=60, net=0, big=0):
        j = s['journey']
        t = self.clock.t
        f = fh._state(j, t)
        f['net'] = net
        j[bm.EV_KEY] = dict(t=int((t - ago) * 1000), s=stake)
        if big:
            j[bm.SPAM_KEY] = dict(d=fh.vn_date(t), n=big)
        return s

    def S(self, sid):
        return self.store.states[sid]

    def org(self, sid):
        return pm.org_live(self.S(sid), self.S(sid)['careers']['police'], 'police')

    def wallet(self, sid):
        return self.S(sid)['journey']['wallet']

    def friends(self, a, b):
        for x, y in ((a, b), (b, a)):
            self.store.db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', (x, y, 0))

    # ---- calls
    def op(self, name, sid, **d):
        return K.ACTIONS[name](self.store, sid, 'Tên', d)

    def refused(self, code, name, sid, **d):
        from game import marriage as mr
        with self.assertRaises(mr.MarriageError) as e:
            self.op(name, sid, **d)
        self.assertEqual(e.exception.code, code, e.exception.message)
        return e.exception

    def stop(self, act, officer='off', target='tgt'):
        return self.op('cand_stop', officer, pid=pid_of(target), act=act)['stop']

    def later(self, s):
        self.clock.t += s


# ===================================================================================== pure rules
class Rules(Base):
    def test_levels_keep_the_owner_rules(self):
        self.assertEqual(K.level(49_999, 300_000, 0), 0)          # a small player: search only
        self.assertEqual(K.level(10_000, 0, 200), 0)             # even after many big rounds earlier, this round is small
        self.assertEqual(K.level(50_000, 0, 0), 1)               # a 50k+ round: the fine
        self.assertEqual(K.level(10_000, 300_001, 0), 3)         # today's net past 300k: the heaviest
        self.assertEqual(K.level(60_000, 0, 19), 1)
        self.assertEqual(K.level(60_000, 0, 20), 2)              # 20 big rounds: Tạm giữ
        self.assertEqual(K.level(300_000, 0, 0), 2)              # a 300k round: Tạm giữ
        self.assertEqual(K.level(60_000, 0, 50), 2)
        self.assertEqual(K.level(60_000, 0, 51), 3)              # past 50 big rounds: Bắt giữ
        self.assertEqual(K.allowed(0), ['search'])
        self.assertEqual(K.allowed(1), ['search', 'fine'])
        self.assertEqual(K.allowed(3), list(K.ACTS))

    def test_evidence_is_a_recent_paid_luck_round_written_by_the_fair(self):
        s = story(500_000)
        self.assertIsNone(K.evidence(s['journey'], self.clock.t))
        fh.action(s, 'fair_bc', {'bets': {'cua': 60_000}})
        ev = K.evidence(s['journey'], self.clock.t)
        self.assertEqual((ev['stake'], ev['lvl']), (60_000, 1))
        validate_state(s)
        self.later(K.EVIDENCE_S + 1)
        self.assertIsNone(K.evidence(s['journey'], self.clock.t))   # 15 minutes later: nothing to go on

    def test_evidence_reads_today_only(self):
        s = self.gambled(story(), 60_000, net=400_000, big=60)
        self.assertEqual(K.evidence(s['journey'], self.clock.t)['lvl'], 3)
        s['journey']['fair']['date'] = '2026-10-09'
        s['journey'][bm.SPAM_KEY]['d'] = '2026-10-09'
        ev = K.evidence(s['journey'], self.clock.t)
        self.assertEqual((ev['net'], ev['big'], ev['lvl']), (0, 0, 1))

    def test_a_bad_evidence_block_is_refused_by_the_save_check(self):
        from game.engine import GameError
        s = story()
        s['journey'][bm.EV_KEY] = dict(t=1, s=0)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_fines_are_thirty_percent_of_the_round_and_jail_by_act(self):
        self.assertEqual(K.fine_of(60_000), 18_000)
        s = story(100_000)
        pen = K.penalize(s, 'fine', 60_000, self.clock.t)
        self.assertEqual((pen, s['journey']['wallet']), (dict(fine=18_000, days=0), 82_000))
        self.assertFalse(jail.active(s['journey'], self.clock.t))
        s = story(100_000)
        self.assertEqual(K.penalize(s, 'hold', 60_000, self.clock.t), dict(fine=0, days=1))
        self.assertEqual(s['journey']['wallet'], 100_000)
        s = story(100_000)
        self.assertEqual(K.penalize(s, 'arrest', 60_000, self.clock.t), dict(fine=18_000, days=3))
        self.assertTrue(jail.active(s['journey'], self.clock.t))
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        validate_state(s)
        s = story(1_000)   # a short wallet: what is there (then the bank, savings…), never below zero
        self.assertEqual(K.penalize(s, 'fine', 60_000, self.clock.t)['fine'], 1_000)
        self.assertEqual(s['journey']['wallet'], 0)

    def test_detection_odds_grow_by_half_a_percent_to_85_and_reset_after_a_quiet_week(self):
        self.assertAlmostEqual(K.detect_p(0), .05)
        self.assertAlmostEqual(K.detect_p(10), .10)
        self.assertAlmostEqual(K.detect_p(160), .85)
        self.assertAlmostEqual(K.detect_p(10**5), .85)
        t = self.clock.t
        self.assertEqual(K.br_count({}, t), 0)
        self.assertEqual(K.br_count({bm.BR_KEY: dict(n=12, t=int(t - 86400))}, t), 12)
        self.assertEqual(K.br_count({bm.BR_KEY: dict(n=12, t=int(t - 8 * 86400))}, t), 0)

    def test_who_may_patrol(self):
        o = self.S(self.cop())
        self.assertIsNone(K.officer_block(o, self.clock.t))
        o2 = copy.deepcopy(o)
        o2['careers']['police']['open'] = False
        self.assertIn('Mở ca', K.officer_block(o2, self.clock.t))
        o3 = copy.deepcopy(o)
        pm.org_live(o3, o3['careers']['police'], 'police')[1]['susp'] = 2
        self.assertIn('đình chỉ', K.officer_block(o3, self.clock.t))
        o4 = copy.deepcopy(o)
        o4['journey']['story'] = True
        jail.arrest(o4['journey'], 'bm', 1, self.clock.t)
        self.assertIn('trại', K.officer_block(o4, self.clock.t))
        o5 = copy.deepcopy(o)
        rec, x = pm.org_live(o5, o5['careers']['police'], 'police')
        pm.mark_expel(rec, x, o5, 'bribe')
        self.assertIn('khai trừ', K.officer_block(o5, self.clock.t))
        self.assertIn('Chỉ cán bộ', K.officer_block(story(), self.clock.t))
        from game.employment import hired_record
        o6 = copy.deepcopy(o)
        o6['careers']['police']['job'] = hired_record('police', 'cap-td')   # the part-time desk: not the ladder
        self.assertIsNotNone(K.officer_block(o6, self.clock.t))

    def test_who_commands(self):
        self.assertIsNotNone(K.commander_block(self.S(self.cop('a', post='doi_truong', grade='dai_uy')), self.clock.t))
        for post, grade in (('pho_truong_ca', 'thieu_ta'), ('truong_ca', 'trung_ta'), ('gd', 'dai_ta')):
            self.assertIsNone(K.commander_block(self.S(self.cop('c' + post, post=post, grade=grade)), self.clock.t), post)

    def test_the_envelope_count_is_an_optional_journey_key_and_the_ext_is_untouched(self):
        j = officer()
        rec, x = pm.org_live(j.state, j.c, 'police')
        e = ORG.ext_of(rec, x)
        self.assertEqual(set(e), ORG.EXT_KEYS)                # the ext keeps the exact keys older builds check
        self.assertNotIn(bm.BR_KEY, j.state['journey'])
        validate_state(j.state)
        j.state['journey'][bm.BR_KEY] = dict(n=3, t=int(self.clock.t))
        validate_state(j.state)
        from game.engine import GameError
        for bad in (dict(n=-1, t=0), dict(n=1, t=0, x=1), dict(n=1.5, t=0), [1, 2]):
            j.state['journey'][bm.BR_KEY] = bad
            with self.assertRaises(GameError):
                validate_state(j.state)


# ===================================================================================== the patrol
class Patrol(Base):
    def test_search_shows_the_findings_and_tells_the_target(self):
        self.cop()
        self.player(stake=60_000, big=3)
        before = copy.deepcopy(self.S('tgt'))
        r = self.op('cand_stop', 'off', pid=pid_of('tgt'), act='search')
        self.assertEqual(r['stop']['st'], 'done')
        self.assertIn('60.000 xu', r['stop']['text'])
        self.assertEqual(r['stop']['acts'], ['search', 'fine'])
        self.assertNotIn('%', r['stop']['text'])
        self.assertEqual(self.S('tgt'), before)   # a search takes nothing
        self.assertTrue(any('lục soát' in t for t in self.store.inbox('tgt')))
        self.assertEqual(self.store.events[-1]['to'], pid_of('tgt'))

    def test_a_small_player_may_only_be_searched(self):
        self.cop()
        self.player(stake=49_000, net=300_000, big=80)
        for act in ('fine', 'hold', 'arrest'):
            self.refused('cand_small', 'cand_stop', 'off', pid=pid_of('tgt'), act=act)
        self.assertEqual(self.stop('search')['acts'], ['search'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM cand_stops').fetchone()[0], 1)

    def test_no_evidence_no_stop(self):
        self.cop()
        self.player(ago=K.EVIDENCE_S + 5)
        self.refused('cand_no_ev', 'cand_stop', 'off', pid=pid_of('tgt'), act='search')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM cand_stops').fetchone()[0], 0)

    def test_the_act_needs_its_level(self):
        self.cop()
        self.player(stake=60_000)
        self.refused('cand_level', 'cand_stop', 'off', pid=pid_of('tgt'), act='hold')
        self.refused('cand_level', 'cand_stop', 'off', pid=pid_of('tgt'), act='arrest')

    def test_only_an_officer_on_duty_and_never_oneself(self):
        self.player('a', stake=60_000)
        self.player()
        self.refused('cand_off', 'cand_stop', 'a', pid=pid_of('tgt'), act='search')
        self.cop()
        self.S('off')['careers']['police']['open'] = False
        self.refused('cand_off', 'cand_stop', 'off', pid=pid_of('tgt'), act='search')
        self.S('off')['careers']['police']['open'] = True
        self.refused('self', 'cand_stop', 'off', pid=pid_of('off'), act='search')
        self.refused('not_found', 'cand_stop', 'off', pid='0' * 16, act='search')
        self.refused('bad_act', 'cand_stop', 'off', pid=pid_of('tgt'), act='beat')

    def test_a_guest_or_a_jailed_player_is_not_stopped(self):
        self.cop()
        self.player('g', account=False)
        self.refused('cand_guest', 'cand_stop', 'off', pid=pid_of('g'), act='search')
        self.player()
        jail.arrest(self.S('tgt')['journey'], 'bm', 3, self.clock.t)
        self.refused('cand_jailed', 'cand_stop', 'off', pid=pid_of('tgt'), act='fine')

    def test_cooperation_takes_the_fine_and_nobody_gets_it(self):
        self.cop(wallet=1000)
        self.player(wallet=200_000, stake=60_000)
        st = self.stop('fine')
        self.assertEqual((st['st'], st['left']), ('ask', K.ASK_S))
        ask = self.store.events[-1]
        self.assertEqual((ask['k'], ask['to'], ask['left']), ('ask', pid_of('tgt'), K.ASK_S))
        adj = self.org('off')[1]['adj']
        r = self.op('cand_answer', 'tgt', id=st['id'], bribe=0)
        self.assertEqual(r['stop']['st'], 'done')
        self.assertEqual(self.wallet('tgt'), 200_000 - 18_000)
        self.assertEqual(self.wallet('off'), 1000)                 # no xu for a stop
        self.assertEqual(self.org('off')[1]['adj'], adj + 1)       # +0.1 ★
        self.assertFalse(jail.active(self.S('tgt')['journey'], self.clock.t))
        self.assertIn('18.000', r['message'])
        self.refused('cand_stale', 'cand_decide', 'off', id=st['id'], take=True)

    def test_no_answer_is_cooperation(self):
        self.cop()
        self.player(stake=60_000, big=25)
        st = self.stop('hold')
        self.later(K.ASK_S - 1)
        self.assertEqual(self.op('cand_poll', 'off', id=st['id'])['stop']['st'], 'ask')
        self.later(2)
        v = self.op('cand_poll', 'off', id=st['id'])['stop']
        self.assertEqual(v['st'], 'done')
        self.assertTrue(jail.active(self.S('tgt')['journey'], self.clock.t))
        self.assertEqual(self.S('tgt')['journey']['jail']['days'], 1)
        self.assertEqual(self.wallet('tgt'), 200_000)              # Tạm giữ: no fine

    def test_the_heaviest_are_arrested_three_days_and_fined(self):
        self.cop()
        self.player(stake=100_000, net=350_000)
        st = self.stop('arrest')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=0)
        self.assertEqual(self.S('tgt')['journey']['jail']['days'], 3)
        self.assertEqual(self.wallet('tgt'), 200_000 - 30_000)

    def test_a_stop_nobody_settles_lapses_without_a_penalty(self):
        self.cop()
        self.player()
        st = self.stop('fine')
        self.later(K.STALE_S + 1)
        self.assertEqual(self.op('cand_poll', 'tgt')['stop'], None)
        self.assertEqual(K._stop(self.store.db, st['id'])['status'], 'gone')
        self.assertEqual(self.wallet('tgt'), 200_000)

    def test_target_poll_finds_the_question(self):
        self.cop()
        self.player()
        st = self.stop('fine')
        v = self.op('cand_poll', 'tgt')['stop']
        self.assertEqual((v['id'], v['role'], v['name']), (st['id'], 'target', 'Hùng'))
        self.assertNotIn('stake', v)

    # ---- envelopes
    def test_envelope_taken_and_not_found_out(self):
        self.cop(wallet=1000)
        self.player(wallet=200_000)
        st = self.stop('fine')
        r = self.op('cand_answer', 'tgt', id=st['id'], bribe=5000)
        self.assertEqual(r['stop']['st'], 'offer')
        off = self.store.events[-1]
        self.assertEqual((off['k'], off['to'], off['amount']), ('offer', pid_of('off'), 5000))
        self.assertEqual(self.op('cand_poll', 'off', id=st['id'])['stop']['amount'], 5000)
        self.draw = False
        r = self.op('cand_decide', 'off', id=st['id'], take=True)
        self.assertEqual(self.wallet('tgt'), 195_000)              # the envelope, no fine
        self.assertEqual(self.wallet('off'), 6000)
        self.assertAlmostEqual(self.draws[-1], .05)                # the first envelope: 5 %
        rec, x = self.org('off')
        self.assertEqual(self.S('off')['journey'][bm.BR_KEY]['n'], 1)
        self.assertEqual(set(rec['cx']), ORG.EXT_KEYS)
        self.assertIsNone(x['mark']['b'])
        self.assertNotIn('%', r['message'])
        self.assertNotIn('p', r['stop'])

    def test_each_envelope_raises_the_odds(self):
        self.cop()
        self.S('off')['journey'][bm.BR_KEY] = dict(n=20, t=int(self.clock.t - 3600))
        self.player()
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=100)
        self.op('cand_decide', 'off', id=st['id'], take=True)
        self.assertAlmostEqual(self.draws[-1], .15)
        self.assertEqual(self.S('off')['journey'][bm.BR_KEY]['n'], 21)

    def test_envelope_found_out_demotes_marks_and_confiscates(self):
        self.cop(wallet=1000, grade='trung_uy')
        self.player(wallet=200_000)
        g = self.org('off')[1]['g']
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=3000)
        self.draw = True
        r = self.op('cand_decide', 'off', id=st['id'], take=True)
        rec, x = self.org('off')
        self.assertEqual(x['g'], g - 1)                            # one grade down
        self.assertIsNotNone(x['mark']['b'])                       # the integrity mark
        self.assertEqual(rec['cx']['sev'][-1]['c'], 'bribe')       # a grave fault a commander may expel for
        self.assertEqual(self.wallet('off'), 1000)                 # nothing kept
        self.assertEqual(self.wallet('tgt'), 197_000)              # the envelope is gone
        self.assertIn('tịch thu', r['message'])
        self.assertEqual(K._stop(self.store.db, st['id'])['outcome'], 'caught')

    def test_envelope_refused_brings_the_penalty_and_liem_chinh(self):
        self.cop(wallet=1000)
        self.player(wallet=200_000)
        liem = self.org('off')[1]['liem']
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=2000)
        r = self.op('cand_decide', 'off', id=st['id'], take=False)
        self.assertEqual(self.wallet('tgt'), 200_000 - 18_000)     # the fine, the envelope stays home
        self.assertEqual(self.wallet('off'), 1000)
        self.assertEqual(self.org('off')[1]['liem'], liem + 1)
        self.assertIn('Từ chối', r['message'])
        self.assertEqual(self.draws, [])                           # nothing to find out

    def test_the_officer_silent_on_an_envelope_means_the_penalty(self):
        self.cop()
        self.player()
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=2000)
        self.later(K.ASK_S + K.OFFER_S + 1)
        self.refused('cand_stale', 'cand_decide', 'off', id=st['id'], take=True)
        self.assertEqual(self.wallet('tgt'), 200_000 - 18_000)
        self.assertEqual(K._stop(self.store.db, st['id'])['outcome'], 'lapse')

    def test_envelope_bounds(self):
        self.cop()
        self.player(wallet=4000)
        st = self.stop('fine')
        for bad in (-1, 5001, 1.5, '100', True):
            self.refused('bad_bribe', 'cand_answer', 'tgt', id=st['id'], bribe=bad)
        self.refused('cand_short', 'cand_answer', 'tgt', id=st['id'], bribe=4001)
        self.refused('not_found', 'cand_answer', 'off', id=st['id'], bribe=0)   # only the one stopped answers
        self.refused('not_found', 'cand_decide', 'tgt', id=st['id'], take=True)

    def test_an_envelope_no_longer_in_the_wallet_is_the_biên_bản(self):
        self.cop(wallet=1000)
        self.player(wallet=100_000)
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=5000)
        self.S('tgt')['journey']['wallet'] = 1000   # spent meanwhile
        r = self.op('cand_decide', 'off', id=st['id'], take=True)
        self.assertEqual(K._stop(self.store.db, st['id'])['outcome'], 'void')
        self.assertEqual(self.wallet('off'), 1000)
        self.assertIn('Phạt hành chính', r['message'])

    # ---- limits
    def test_a_target_once_in_30_minutes_across_officers(self):
        self.cop('a')
        self.cop('b', name='Minh')
        self.player()
        st = self.stop('fine', 'a')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=0)
        self.refused('cand_recent', 'cand_stop', 'b', pid=pid_of('tgt'), act='search')
        self.later(K.TARGET_GAP_S - 2)
        self.gambled(self.S('tgt'), 60_000)
        self.refused('cand_recent', 'cand_stop', 'b', pid=pid_of('tgt'), act='fine')
        self.later(3)
        self.assertEqual(self.stop('fine', 'b')['st'], 'ask')

    def test_a_search_then_the_same_officers_follow_up(self):
        self.cop('a')
        self.cop('b', name='Minh')
        self.player()
        self.stop('search', 'a')
        self.refused('cand_recent', 'cand_stop', 'b', pid=pid_of('tgt'), act='fine')   # another officer waits
        self.assertEqual(self.stop('fine', 'a')['st'], 'ask')
        self.later(K.FOLLOW_S + 1)
        self.op('cand_poll', 'a')   # settles it (no answer: cooperation)

    def test_one_open_stop_one_penalty_per_player_a_day_ten_stops_a_day(self):
        self.cop()
        for i in range(12):
            self.player(f't{i}', name=f'P{i}')
        st = self.stop('fine', target='t0')
        self.refused('cand_busy', 'cand_stop', 'off', pid=pid_of('t1'), act='search')
        self.op('cand_answer', 't0', id=st['id'], bribe=0)
        self.later(K.TARGET_GAP_S + 1)
        self.gambled(self.S('t0'), 60_000)
        self.refused('cand_pair', 'cand_stop', 'off', pid=pid_of('t0'), act='fine')
        for i in range(1, 10):
            self.gambled(self.S(f't{i}'), 60_000)
            self.stop('search', target=f't{i}')
        self.gambled(self.S('t10'), 60_000)
        self.refused('cand_day_max', 'cand_stop', 'off', pid=pid_of('t10'), act='search')

    def test_rewards_capped_at_three_a_day_and_never_between_friends(self):
        self.cop()
        for i in range(5):
            self.player(f't{i}', name=f'P{i}')
        self.friends('off', 't4')
        adj0 = self.org('off')[1]['adj']
        for i in range(5):
            st = self.stop('fine', target=f't{i}')
            self.op('cand_answer', f't{i}', id=st['id'], bribe=0)
            self.later(1)
        self.assertEqual(self.org('off')[1]['adj'], min(10, adj0 + K.REWARD_DAY_MAX))
        self.assertEqual(self.wallet('t4'), 200_000 - 18_000)   # the friend is fined all the same

    def test_friends_get_no_liem_chinh_for_a_refused_envelope(self):
        self.cop()
        self.player()
        self.friends('off', 'tgt')
        liem = self.org('off')[1]['liem']
        st = self.stop('fine')
        self.op('cand_answer', 'tgt', id=st['id'], bribe=1)
        self.op('cand_decide', 'off', id=st['id'], take=False)
        self.assertEqual(self.org('off')[1]['liem'], liem)


# ===================================================================================== commanders
class Commanders(Base):
    def setUp(self):
        super().setUp()
        self.cop('cmd', name='Trưởng', post='truong_ca', grade='trung_ta')
        self.cop('cmd2', name='Phó', post='pho_truong_ca', grade='thieu_ta')
        self.cop('o1', name='An')
        self.cop('o2', name='Bình')
        for sid in ('cmd', 'cmd2', 'o1', 'o2'):
            CR.command_commit(self.store.db, sid, {}, self.S(sid))

    def test_the_force_list(self):
        r = self.op('cand_force', 'cmd')
        names = [x['name'] for x in r['force']]
        self.assertEqual(names[0], 'Trưởng')   # the highest post first
        self.assertEqual(set(names), {'Trưởng', 'Phó', 'An', 'Bình'})
        self.assertTrue(all(len(x['pid']) == 16 and 'sid' not in x for x in r['force']))
        me = next(x for x in r['force'] if x['me'])
        self.assertFalse(me['can_hon'] or me['can_out'])
        self.refused('cand_off', 'cand_force', 'o1')

    def test_commendation_once_a_day_each_way_never_oneself(self):
        adj = self.org('o1')[1]['adj']
        self.op('cand_hon', 'cmd', pid=pid_of('o1'))
        rec, x = self.org('o1')
        self.assertEqual(x['adj'], min(10, adj + K.HON_ADJ))
        self.assertEqual(rec['cx']['hon'][-1]['by'], 'Trung tá Tên')
        self.assertTrue(any('khen thưởng' in t for t in self.store.inbox('o1')))
        self.refused('cand_hon_day', 'cand_hon', 'cmd', pid=pid_of('o2'))       # one a day per commander
        self.refused('cand_hon_target', 'cand_hon', 'cmd2', pid=pid_of('o1'))   # one a day per officer
        self.assertEqual(len(self.org('o1')[0]['cx']['hon']), 1)                 # nothing written by a refusal
        self.op('cand_hon', 'cmd2', pid=pid_of('o2'))
        self.refused('self', 'cand_hon', 'cmd', pid=pid_of('cmd'))
        self.refused('cand_off', 'cand_hon', 'o1', pid=pid_of('o2'))
        self.later(86400)
        self.op('cand_hon', 'cmd', pid=pid_of('o1'))   # a new Vietnam day
        self.assertEqual(len(self.org('o1')[0]['cx']['hon']), 2)

    def test_a_suspended_or_jailed_commander_cannot_act(self):
        x = self.org('cmd')[1]
        x['susp'] = 1
        self.refused('cand_off', 'cand_hon', 'cmd', pid=pid_of('o1'))
        x['susp'] = 0
        j = self.S('cmd')['journey']
        j['story'] = True
        jail.arrest(j, 'bm', 1, self.clock.t)
        self.refused('cand_off', 'cand_hon', 'cmd', pid=pid_of('o1'))

    def fault(self, sid, ago_days=2, code='bribe'):
        rec, x = self.org(sid)
        ORG.add_sev(ORG.ext_of(rec, x), code, self.clock.t - ago_days * 86400)

    def test_expulsion_needs_a_recent_grave_fault(self):
        self.refused('cand_no_sev', 'cand_out', 'cmd', pid=pid_of('o1'), confirm=True)
        self.fault('o1', ago_days=8)
        self.refused('cand_no_sev', 'cand_out', 'cmd', pid=pid_of('o1'), confirm=True)
        self.fault('o1', ago_days=6)
        self.refused('confirm', 'cand_out', 'cmd', pid=pid_of('o1'))
        self.op('cand_out', 'cmd', pid=pid_of('o1'), confirm=True)
        rec = self.org('o1')[0]
        self.assertTrue(pm.expel_due(rec))
        self.assertEqual(rec['cx']['out']['c'], 'bribe')
        self.assertTrue(any('khai trừ' in t for t in self.store.inbox('o1')))
        self.refused('cand_gone', 'cand_out', 'cmd', pid=pid_of('o1'), confirm=True)
        # done at the officer's next close: the contract ended, the ban, jail
        j = self.S('o1')
        lines = pm.after_close(j, j['careers']['police'], 'police')
        self.assertTrue(lines and pm.banned(j, 'police'))

    def test_expulsion_only_below_and_never_oneself(self):
        self.fault('cmd2')
        self.fault('cmd')
        self.refused('cand_rank', 'cand_out', 'cmd2', pid=pid_of('cmd'), confirm=True)   # a Phó cannot expel the Trưởng
        self.refused('self', 'cand_out', 'cmd', pid=pid_of('cmd'), confirm=True)
        self.op('cand_out', 'cmd', pid=pid_of('cmd2'), confirm=True)

    def test_expulsions_a_day_are_capped(self):
        for i in range(K.OUT_DAY_MAX + 1):
            self.cop(f'x{i}', name=f'X{i}')
            self.fault(f'x{i}')
        for i in range(K.OUT_DAY_MAX):
            self.op('cand_out', 'cmd', pid=pid_of(f'x{i}'), confirm=True)
        self.refused('cand_out_day', 'cand_out', 'cmd', pid=pid_of(f'x{K.OUT_DAY_MAX}'), confirm=True)
        self.assertFalse(pm.expel_due(self.org(f'x{K.OUT_DAY_MAX}')[0]))


class Draw(unittest.TestCase):
    def test_the_real_draw_is_fixed_by_the_stop_and_near_its_odds(self):
        self.assertEqual(K._roll('cs0123456789abcdef', .5), K._roll('cs0123456789abcdef', .5))   # a retried write draws the same
        self.assertFalse(K._roll('cs0123456789abcdef', 0))
        self.assertTrue(K._roll('cs0123456789abcdef', 1))
        hits = sum(K._roll(f'cs{i:016x}', .05) for i in range(4000))
        self.assertTrue(120 < hits < 290, hits)


# ===================================================================================== the live push
class LiveFrame(unittest.TestCase):
    def test_frames_are_checked_and_carry_no_sid(self):
        from live.cand import frame
        pid = pid_of('tgt')
        got = frame(dict(op='cand', to=pid, k='ask', id='cs' + '0' * 16, act='fine', text='x' * 500, by='Trung úy Hùng', left=60,
                         sid='secret'))
        self.assertEqual(got[0], pid)
        self.assertEqual(set(got[1]), {'t', 'k', 'id', 'act', 'text', 'by', 'left'})
        self.assertEqual(len(got[1]['text']), 200)
        for bad in (dict(op='cand', to='x', k='ask', id='cs' + '0' * 16, act='fine'),
                    dict(op='cand', to=pid, k='boom', id='cs' + '0' * 16, act='fine'),
                    dict(op='cand', to=pid, k='ask', id='zz', act='fine'),
                    dict(op='auction', to=pid)):
            self.assertIsNone(frame(bad))


class Wiring(unittest.TestCase):
    def test_actions_reach_the_marriage_route(self):
        from game import marriage as mr
        for op in K.ACTIONS:
            self.assertIs(mr._more_actions()[op], K.ACTIONS[op])
        from live.app import FEATURES
        self.assertIn('CandFeature', [f.__name__ for f in FEATURES])


if __name__ == '__main__':
    unittest.main()
