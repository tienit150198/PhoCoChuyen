"""💼 Quầy của bạn, B2 (game/quay_hire.py): an owner hires another player for one shift. Two real accounts on one
store: hire -> work -> paid once (the wage is the owner's escrow, never minted; the counter's share arrives once
through the live_effects inbox), quitting is free, an offer the counter cannot cover is refused, two players racing
for one shift / a double flush pay once, a second account cannot farm (age, caps, empty shifts), and the saves
stay valid for the previous server (1.4.31)."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, social
from game import journey as jr
from game import live_effects as lfx
from game import marriage as mr
from game import quay as qy
from game import quay_hire as qh
from game.storage import Store

ROOT = Path(__file__).resolve().parents[1]
OLD = Path(os.environ.get('MNL_PREV_TREE', r'D:/projects/Mot_ngay_lam_nghe/_rel1431/mot-ngay-lam-nghe'))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        h = patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        h.start()
        self.addCleanup(h.stop)
        qh._swept[0] = 0.0
        self.rid = 0

    # ------------------------------------------------------------ people and saves
    def user(self, name, old=True, life=12, trade='milk_tea', served=12, wallet=30000):
        token, _, _ = self.store.session()
        tok = accounts.register(self.store, token, dict(username=name + '_test', password='matkhau-dai-lam', confirm='matkhau-dai-lam',
                                                        display=name.title()))['token']
        sid = self.store.key(tok)
        if old:
            self.store.transaction(lambda db: db.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))

        def fn(s):
            j = s['journey']
            j['gender'] = 'female'
            j['chapter'] = 3
            j['done'] = [1, 2]
            for n in (2, 3):
                jr._unlock_chapter(j, n)
            j['life_day'] = life
            j['wallet'] = wallet
            j['stats']['max_wallet'] = max(wallet, j['stats']['max_wallet'])
            s['careers'][trade]['metrics']['served'] = served
        mr._mutate(self.store, {sid: fn})
        return tok

    def sid(self, tok):
        return self.store.key(tok)

    def state(self, tok):
        return self.store.read(tok)[0]

    def wallet(self, tok):
        return self.state(tok)['journey']['wallet']

    def cmd(self, tok, action, career=None, **p):
        self.rid += 1
        rev = self.store.read(tok)[1]
        return self.store.command(tok, f'req-{self.rid:06d}', rev, career, action, p)

    def open_stall(self, tok, place='xe'):
        self.cmd(tok, 'jr_quay_open', trade='milk_tea', place=place, name='Trà Mây', confirm=True)
        return self.stall(tok)

    def stall(self, tok):
        return self.state(tok)['journey']['quay']['stalls'][0]

    def act(self, tok, op, **d):
        return qh.act(self.store, tok, op, d)

    def post(self, tok, wage=30, **d):
        self.act(tok, 'post', stall=self.stall(tok)['id'], wage=wage, **d)
        return self.view(tok)['mine'][0]

    def view(self, tok):
        return qh.get(self.store, tok, self.state(tok))

    def row(self, jid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM quay_jobs WHERE id=?', (jid,)).fetchone())

    def effects(self, sid=None):
        with self.store.connect() as db:
            rows = db.execute('SELECT * FROM live_effects ORDER BY id').fetchall()
        return [dict(r) for r in rows if sid is None or r['sid'] == sid]

    def work(self, tok, tasks=3, career='milk_tea'):
        """A real day of the trade: open it, do `tasks` tasks (the count end_day reads), close it."""
        self.cmd(tok, 'start_day', career)

        def fn(s):
            s['careers'][career]['day_completed'] += tasks
        mr._mutate(self.store, {self.sid(tok): fn})
        return self.cmd(tok, 'end_day', career, carry_event=True)['result']

    def owner_load(self, tok):
        return lfx.on_load(self.store, tok, self.state(tok))

    def money(self, tok):
        """Everything a save holds: wallet + its counters' till and fund."""
        s = self.state(tok)
        return s['journey']['wallet'] + sum(st['till'] + st['fund'] for st in (s['journey'].get('quay') or {}).get('stalls', ()))

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(qh.QuayError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception.message


class HireWorkPay(Base):
    def test_hire_work_paid_once_and_the_counter_gets_its_share_once(self):
        boss, ann = self.user('boss'), self.user('ann')
        st = self.open_stall(boss)
        before = st['till'] + st['fund']
        job = self.post(boss, wage=30)
        self.assertEqual(job['status'], 'open')
        st = self.stall(boss)
        self.assertEqual(st['till'] + st['fund'], before - 30)      # escrowed from the counter
        board = self.view(ann)['board']
        self.assertEqual([b['id'] for b in board], [job['id']])
        self.act(ann, 'accept', id=job['id'])
        sh = self.state(ann)['journey']['quay']['shift']
        self.assertEqual((sh['id'], sh['career'], sh['wage']), (job['id'], 'milk_tea', 30))
        self.assertNotIn(self.sid(boss), json.dumps(self.state(ann)['journey']['quay']))   # no owner id in the worker's save
        w0 = self.wallet(ann)
        r = self.work(ann, tasks=3)
        self.assertEqual(r.get('quay'), 'shift')
        self.assertEqual(len(self.state(ann)['journey']['quay']['out']), 1)
        w1 = self.wallet(ann)                       # the day's own pay/costs moved the wallet; the wage comes with flush
        self.assertTrue(self.act(ann, 'flush')['changed'])
        self.assertEqual(self.wallet(ann), w1 + 30)
        self.assertFalse(self.act(ann, 'flush')['changed'])      # twice: nothing more
        self.assertEqual(self.wallet(ann), w1 + 30)
        self.assertGreater(w1 + 30, w0 - 1000)
        hist = [h for h in self.state(ann)['journey']['history'] if h['label'].startswith('💼 Làm thêm')]
        self.assertEqual([(h['kind'], h['amount']) for h in hist], [('salary', 30)])
        row = self.row(job['id'])
        self.assertEqual((row['status'], row['tasks']), ('paid', 3))
        value = qy.shift_value('xe', 'milk_tea')
        self.assertEqual(row['earned'], value * 100 // 100)       # 3 tasks: 100 %
        till = self.stall(boss)['till']
        self.assertTrue(self.owner_load(boss))
        self.assertEqual(self.stall(boss)['till'], till + row['earned'])
        self.assertFalse(self.owner_load(boss))                  # applied once
        self.assertEqual(self.stall(boss)['till'], till + row['earned'])
        self.assertEqual([e['status'] for e in self.effects(self.sid(boss))], ['applied'])

    def test_the_wage_is_a_transfer(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        total = self.money(boss)
        job = self.post(boss, wage=40)
        self.assertEqual(self.money(boss), total - 40)
        self.act(ann, 'accept', id=job['id'])
        self.work(ann, tasks=2)
        w = self.wallet(ann)
        self.act(ann, 'flush')
        self.assertEqual(self.wallet(ann) - w, 40)               # exactly what left the owner's counter
        self.owner_load(boss)
        self.assertEqual(self.money(boss), total - 40 + qh.share(qy.shift_value('xe', 'milk_tea'), 2, 0))

    def test_empty_or_short_shift_pays_nobody_and_the_escrow_returns(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        total = self.money(boss)
        job = self.post(boss, wage=30)
        self.act(ann, 'accept', id=job['id'])
        w = None
        r = self.work(ann, tasks=1)
        self.assertIn('chưa đủ', ' '.join(r.get('effects') or []))
        w = self.wallet(ann)
        self.act(ann, 'flush')
        self.assertEqual(self.wallet(ann), w)
        self.assertEqual(self.row(job['id'])['status'], 'lapsed')
        self.owner_load(boss)
        self.assertEqual(self.money(boss), total)

    def test_tasks_done_before_accepting_do_not_count(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        job = self.post(boss, wage=30)
        self.cmd(ann, 'start_day', 'milk_tea')
        mr._mutate(self.store, {self.sid(ann): lambda s: s['careers']['milk_tea'].__setitem__('day_completed', 4)})
        self.act(ann, 'accept', id=job['id'])
        self.assertEqual(self.state(ann)['journey']['quay']['shift']['base'], 4)
        self.cmd(ann, 'end_day', 'milk_tea', carry_event=True)
        self.act(ann, 'flush')
        self.assertEqual(self.row(job['id'])['status'], 'lapsed')

    def test_bootstrap_flush(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        job = self.post(boss, wage=25)
        self.act(ann, 'accept', id=job['id'])
        self.work(ann, tasks=4)
        w = self.wallet(ann)
        self.assertTrue(qh.on_load(self.store, ann, self.state(ann)))
        self.assertEqual(self.wallet(ann), w + 25)
        self.assertEqual(self.row(job['id'])['earned'], qh.share(qy.shift_value('xe', 'milk_tea'), 4, 0))
        self.assertFalse(qh.on_load(self.store, ann, self.state(ann)))

    def test_friend_invite_only_that_friend_sees_it(self):
        boss, ann, bob = self.user('boss'), self.user('ann'), self.user('bob')
        self.open_stall(boss)
        mr.ensure_person(self.store, self.sid(ann))
        with self.store.connect() as db:
            code = db.execute('SELECT code FROM marriage_people WHERE sid=?', (self.sid(ann),)).fetchone()['code']
        self.refused('not_friend', self.post, boss, to=code)
        t = mr.now() - 3 * 86400
        self.store.transaction(lambda db: [db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', (x, y, t))
                                           for x, y in ((self.sid(boss), self.sid(ann)), (self.sid(ann), self.sid(boss)))])
        self.assertEqual([f['code'] for f in self.view(boss)['friends']], [code])
        job = self.post(boss, to=code)
        self.assertEqual(job['to'], 'Ann')
        self.assertEqual(self.view(bob)['board'], [])
        self.assertTrue(self.view(ann)['board'][0]['invite'])
        self.refused('gone', self.act, bob, 'accept', id=job['id'])
        total = self.money(boss)
        self.act(ann, 'decline', id=job['id'])
        self.owner_load(boss)
        self.assertEqual(self.money(boss), total + 30)


class Quit(Base):
    def test_quit_is_free_and_the_counter_gets_the_wage_back(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        total = self.money(boss)
        job = self.post(boss, wage=30)
        self.act(ann, 'accept', id=job['id'])
        w = self.wallet(ann)
        self.act(ann, 'quit')
        self.assertEqual(self.wallet(ann), w)
        self.assertIsNone(self.state(ann)['journey']['quay']['shift'])
        self.assertEqual(self.row(job['id'])['status'], 'quit')
        self.owner_load(boss)
        self.assertEqual(self.money(boss), total)
        self.work(ann, tasks=3)                       # the day after quitting is just a day
        self.act(ann, 'flush')
        self.assertEqual(self.row(job['id'])['status'], 'quit')
        self.refused('gone', self.act, ann, 'quit')

    def test_owner_cancels_an_open_offer(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        total = self.money(boss)
        job = self.post(boss, wage=30)
        self.refused('gone', self.act, ann, 'cancel', id=job['id'])
        self.act(boss, 'cancel', id=job['id'])
        self.assertEqual(self.money(boss), total)
        self.refused('gone', self.act, boss, 'cancel', id=job['id'])
        self.refused('gone', self.act, ann, 'accept', id=job['id'])

    def test_expired_offers_and_unplayed_shifts_come_back(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        self.cmd(boss, 'jr_quay_fund', stall=self.stall(boss)['id'], amount=200)
        total = self.money(boss)
        a = self.post(boss, wage=30)
        self.refused('full', self.act, boss, 'post', stall=self.stall(boss)['id'], wage=20)   # xe: one slot, one offer at a time
        self.assertEqual(self.money(boss), total - 30)
        self.act(ann, 'accept', id=a['id'])
        with patch.object(qh, 'now', lambda: mr.now() + 40 * 3600):
            self.assertEqual(qh.sweep(self.store, force=True), 1)
            self.assertEqual(self.row(a['id'])['status'], 'expired')
            self.view(ann)                                  # the worker's stale shift goes
        self.assertIsNone(self.state(ann)['journey']['quay']['shift'])
        self.owner_load(boss)
        self.assertEqual(self.money(boss), total)


class Funds(Base):
    def test_an_offer_the_counter_cannot_cover_is_refused_and_nothing_moves(self):
        boss = self.user('boss')
        st = self.open_stall(boss)
        sid = st['id']
        self.cmd(boss, 'jr_quay_fund', stall=sid, amount=-st['fund'])
        st = self.stall(boss)
        self.assertEqual(st['till'] + st['fund'], 0)
        rev = self.store.read(boss)[1]
        msg = self.refused('no_funds', self.act, boss, 'post', stall=sid, wage=30)
        self.assertIn('chưa đủ', msg)
        self.assertEqual(self.store.read(boss)[1], rev)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM quay_jobs').fetchone()[0], 0)

    def test_wage_bounds_and_no_debit_of_anyone_else(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        value = qy.shift_value('xe', 'milk_tea')
        self.refused('bad_wage', self.act, boss, 'post', stall=self.stall(boss)['id'], wage=qh.WAGE_MIN - 1)
        self.refused('bad_wage', self.act, boss, 'post', stall=self.stall(boss)['id'], wage=qh.wage_max(value) + 1)
        self.refused('bad_wage', self.act, boss, 'post', stall=self.stall(boss)['id'], wage='30')
        self.refused('no_stall', self.act, ann, 'post', stall=self.stall(boss)['id'], wage=30)   # someone else's counter
        w = self.wallet(ann)
        job = self.post(boss)
        self.act(ann, 'accept', id=job['id'])
        self.act(ann, 'quit')
        self.assertEqual(self.wallet(ann), w)        # the worker never pays anything


class Races(Base):
    def test_two_players_tap_the_same_shift(self):
        boss, ann, bob = self.user('boss'), self.user('ann'), self.user('bob')
        self.open_stall(boss)
        job = self.post(boss)
        out, barrier = {}, threading.Barrier(2)

        def take(tok):
            barrier.wait()
            try:
                out[tok] = self.act(tok, 'accept', id=job['id'])['message']
            except qh.QuayError as e:
                out[tok] = e.code
        ts = [threading.Thread(target=take, args=(t,)) for t in (ann, bob)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sorted(v == 'gone' for v in out.values()), [False, True])
        holders = [t for t in (ann, bob) if self.state(t)['journey'].get('quay', {}).get('shift')]
        self.assertEqual(len(holders), 1)
        self.assertEqual(self.row(job['id'])['worker'], self.sid(holders[0]))

    def test_concurrent_flushes_pay_once(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        job = self.post(boss, wage=30)
        self.act(ann, 'accept', id=job['id'])
        self.work(ann, tasks=3)
        w = self.wallet(ann)
        barrier = threading.Barrier(3)

        def go():
            barrier.wait()
            self.act(ann, 'flush')
        ts = [threading.Thread(target=go) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(self.wallet(ann), w + 30)
        self.assertEqual(len(self.effects(self.sid(boss))), 1)
        for _ in range(3):
            self.owner_load(boss)
        self.assertEqual([e['status'] for e in self.effects(self.sid(boss))], ['applied'])

    def test_quit_racing_flush(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        total = self.money(boss)
        job = self.post(boss, wage=30)
        self.act(ann, 'accept', id=job['id'])
        self.work(ann, tasks=3)
        w = self.wallet(ann)
        self.act(ann, 'flush')
        self.refused('gone', self.act, ann, 'quit')
        self.owner_load(boss)
        self.assertEqual(self.wallet(ann), w + 30)
        self.assertEqual(self.money(boss), total - 30 + self.row(job['id'])['earned'])


class AltFarming(Base):
    def test_new_account_cannot_work_or_hire(self):
        boss, alt = self.user('boss'), self.user('alt', old=False)
        self.open_stall(boss)
        job = self.post(boss)
        self.assertIn('ngày tuổi', self.view(alt)['lock'])
        self.refused('too_new', self.act, alt, 'accept', id=job['id'])
        boss2 = self.user('boss2', old=False)
        self.open_stall(boss2)
        self.refused('too_new', self.act, boss2, 'post', stall=self.stall(boss2)['id'], wage=30)

    def test_guest_young_save_and_unknown_trade(self):
        boss = self.user('boss')
        self.open_stall(boss)
        job = self.post(boss)
        guest, _, _ = self.store.session()
        self.refused('account_required', self.act, guest, 'accept', id=job['id'])
        kid = self.user('kid', life=3)
        self.refused('cannot', self.act, kid, 'accept', id=job['id'])
        novice = self.user('novice', served=2)
        self.assertEqual(self.view(novice)['board'], [])
        self.refused('cannot', self.act, novice, 'accept', id=job['id'])
        self.refused('own', self.act, boss, 'accept', id=job['id'])

    def test_caps_per_worker_pair_and_owner(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        self.cmd(boss, 'jr_quay_fund', stall=self.stall(boss)['id'], amount=1000)
        done = 0
        for i in range(qh.PAIR_WEEK + 1):
            day = patch.object(qh, 'vn_day', lambda t=None, i=i: f'2030-01-{i + 1:02d}')   # one shift a day: only the pair cap
            day.start()
            self.addCleanup(day.stop)
            job = self.post(boss, wage=30)
            try:
                self.act(ann, 'accept', id=job['id'])
            except qh.QuayError as e:
                self.assertEqual(e.code, 'rate_limited')
                self.assertEqual(i, qh.PAIR_WEEK)
                self.act(boss, 'cancel', id=job['id'])
                break
            self.act(ann, 'quit')
            day.stop()
            done += 1
        self.assertEqual(done, qh.PAIR_WEEK)

    def test_worker_day_cap_and_owner_day_cap(self):
        boss, ann, bob = self.user('boss'), self.user('ann'), self.user('bob')
        self.open_stall(boss, place='sap')
        self.cmd(boss, 'jr_quay_fund', stall=self.stall(boss)['id'], amount=1000)
        taken = 0
        for _ in range(qh.WORKER_DAY + 1):
            job = self.post(boss, wage=20)
            try:
                self.act(ann, 'accept', id=job['id'])
                taken += 1
                self.act(ann, 'quit')
            except qh.QuayError as e:
                self.assertEqual(e.code, 'rate_limited')
                self.act(bob, 'accept', id=job['id'])
                self.act(bob, 'quit')
        self.assertEqual(taken, qh.WORKER_DAY)
        self.post(boss, wage=20)
        self.refused('rate_limited', self.act, boss, 'post', stall=self.stall(boss)['id'], wage=20)   # OWNER_DAY a VN day

    def test_week_wage_cap(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss, place='kiot')
        self.cmd(boss, 'jr_quay_fund', stall=self.stall(boss)['id'], amount=2000)
        job = self.post(boss, wage=120)
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO quay_jobs(id,owner,owner_name,stall,stall_name,trade,place,wage,value,worker,status,day,taken_day,at,taken_at,until) "
            "VALUES('qj-00000000aaaa','x','X','q1','A','milk_tea','kiot',300,300,?,'paid','2000-01-01','2000-01-01',?,?,?)",
            (self.sid(ann), mr.now(), mr.now(), mr.now())))
        self.refused('rate_limited', self.act, ann, 'accept', id=job['id'])

    def test_farming_pair_gains_only_real_work(self):
        """An owner and a second account: a shift with no work moves no money at all; a real one earns the counter
        at most SHARE_MAX % of a hand's day."""
        boss, alt = self.user('boss'), self.user('alt')
        self.open_stall(boss)
        both = self.money(boss) + self.wallet(alt)
        job = self.post(boss, wage=30)
        self.act(alt, 'accept', id=job['id'])
        w_alt = self.wallet(alt)
        self.cmd(alt, 'start_day', 'milk_tea')
        self.cmd(alt, 'end_day', 'milk_tea', carry_event=True)   # no task done
        day_pay = self.wallet(alt) - w_alt                        # the alt's own day (living costs…), not the shift's
        self.act(alt, 'flush')
        self.owner_load(boss)
        self.assertEqual(self.money(boss) + self.wallet(alt), both + day_pay)
        self.assertLessEqual(qh.share(1000, 50, 0), 1000 * qh.SHARE_MAX // 100)


class Validation(Base):
    def test_saves_and_views(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        job = self.post(boss)
        self.act(ann, 'accept', id=job['id'])
        from game.engine import public_state, validate_state
        s = self.state(ann)
        validate_state(s)
        pub = public_state(s)['journey']['quay']
        self.assertEqual(set(pub['shift']), {'id', 'career', 'wage', 'who', 'name', 'until'})
        self.assertEqual(pub['shift']['who'], 'Boss')
        bad = json.loads(json.dumps(s))
        bad['journey']['quay']['shift']['wage'] = 0
        with self.assertRaises(Exception):
            validate_state(bad)

    def test_inbox_row_for_an_unknown_counter_goes_to_the_wallet(self):
        boss = self.user('boss')
        self.open_stall(boss)
        sid = self.sid(boss)
        self.store.transaction(lambda db: qh._effect(db, 'quay:qj-00000000beef:back', sid, 30, 'q99', 'back', '💼 Thử'))
        w = self.wallet(boss)
        self.owner_load(boss)
        self.assertEqual(self.wallet(boss), w + 30)
        self.assertEqual(self.state(boss)['journey']['history'][-1]['kind'], qy.KIND_OUT)


@unittest.skipUnless((OLD / 'game' / 'engine.py').exists(), 'previous release tree not found')
class PreviousServer(Base):
    """Saves written mid-shift and after a paid shift load on 1.4.31; its inbox leaves 'quay' rows pending."""

    PROG = r'''
import json, sys
sys.path.insert(0, '.')
from game.engine import validate_state, migrate_state
from game import live_effects as lfx
from game.content import CAREERS
for path in sys.argv[1:]:
    s = json.load(open(path, encoding='utf-8'))
    for k in [k for k in s['careers'] if k not in CAREERS]:
        s['careers'].pop(k)
    s['journey']['unlocked'] = [c for c in s['journey']['unlocked'] if c in CAREERS]
    s = migrate_state(s, owned=True)
    validate_state(s)
    assert 'quay' in s['journey']
print(json.dumps(dict(ok=True, pays='quay' in lfx.PAYS)))
'''

    def test_old_server_accepts_the_saves(self):
        boss, ann = self.user('boss'), self.user('ann')
        self.open_stall(boss)
        job = self.post(boss)
        self.act(ann, 'accept', id=job['id'])
        paths = []
        for n, tok in (('mid', ann), ('owner', boss)):
            p = Path(self.tmp.name) / f'{n}.json'
            p.write_text(json.dumps(self.state(tok), ensure_ascii=False), encoding='utf-8')
            paths.append(str(p))
        self.work(ann, tasks=3)
        p = Path(self.tmp.name) / 'out.json'
        p.write_text(json.dumps(self.state(ann), ensure_ascii=False), encoding='utf-8')
        paths.append(str(p))
        self.act(ann, 'flush')
        p = Path(self.tmp.name) / 'paid.json'
        p.write_text(json.dumps(self.state(ann), ensure_ascii=False), encoding='utf-8')
        paths.append(str(p))
        out = subprocess.run([sys.executable, '-c', self.PROG, *paths], cwd=OLD, capture_output=True, text=True, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        res = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(res, dict(ok=True, pays=False))     # the old inbox never selects 'quay' rows


if __name__ == '__main__':
    unittest.main()
