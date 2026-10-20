"""⚔️ Bang (game/bang.py, owner design 19/10): founding (account age, a chức danh, the fee as a pure sink in ≤ 10 M rows,
the name rules and its unique key), joining freely (open / by approval / invitations, switching with no cooldown, one
bang at a time, the member cap by the Đại sảnh), the deposit-only fund (no way out, the cap, disbanding burns it, two
deposits at once), điểm cống hiến (deposits, check-in, work days, the daily cap, no farming by hopping), roles (seats,
handover, kicks, the title gone on leaving), the points-only shop (items usable only in their bang), facilities (cost,
slots, the hall gate, real-time builds), the bang's Giờ vàng (rules, membership spans, deterministic ×2 bound per
command), the weekly ranking and its title, the chat group kept in sync, the operator's hide / rename, erasure, and saves
crossing the previous release (2.4.60)."""
import copy
import inspect
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import golden_hour, promotion, staff_market
from game import marriage as mr
from game.engine import GameError, apply_action, validate_state
from tests.test_bank import story

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_792_378_800.0      # Mon 2026-10-19 10:00 VN


def act(s, name, **p):
    return apply_action(s, None, name, p)


def titled(wallet=20_000_000, bank_balance=0):
    s = story(wallet)
    promotion.record(s, 'milk_tea', True)['rank'] = 1
    if bank_balance:
        s, _ = act(s, 'jr_bk_open')
        s['journey']['wallet'] += bank_balance
        s, _ = act(s, 'jr_bk_deposit', amount=bank_balance)
    validate_state(s)
    return s


def found(s, **p):
    p = dict(dict(name='Rồng Đỏ', emoji='🐉', color='do', motto='Đoàn kết', open=True, confirm=True), **p)
    return apply_action(s, None, 'jr_bang_found', p)


def refused(test, s, action_, want=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        apply_action(s, None, action_, p)
    test.assertEqual(s, before)
    if want:
        test.assertEqual(cm.exception.code, want)
    return str(cm.exception)


class Catalogue(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(C.FOUND_FEE, 5_000_000)
        self.assertEqual(C.FOUND_ACCOUNT_DAYS, 14)
        self.assertEqual(C.HALL_CAP[1:], (10, 15, 20, 25, 30))
        self.assertEqual(C.max_level(C.HALL), 5)
        self.assertEqual({k: v[2] for k, v in C.ROLES.items()}, dict(chu=1, pho=2, lao=3, tinh=5, tv=None))
        self.assertEqual(C.XU_PER_POINT, 1000)
        self.assertTrue(all(5 <= C.max_level(f) <= 10 for f in C.FACILITIES))
        for f in C.FACILITIES:
            costs = [x for x, _ in C.FACILITIES[f]['levels']]
            self.assertEqual(costs, sorted(costs), f)
            for n in range(1, C.max_level(f) + 1):
                self.assertTrue(C.perk(f, n), (f, n))
        self.assertEqual(len(C.KHO_CAP), C.max_level('kho') + 1)
        self.assertEqual(len(C.GOLDEN), C.max_level('den_vang') + 1)
        self.assertGreaterEqual(C.KHO_CAP[-1], C.cost(C.HALL, 5)[0])   # the dearest level fits a full Kho bang
        self.assertTrue(all(c[3] in ('den', 'vang', 'bac', 'hong', 'do', 'dao', 'mint', 'navy', 'lavender', 'trang') for c in C.COLORS.values()))
        from game import garage
        self.assertTrue(all(c[4] in garage.PAINT_INDEX for c in C.COLORS.values()))
        from game import wardrobe
        self.assertTrue(all(u[1] in wardrobe.PAINTABLE for u in C.UNIFORMS.values()))

    def test_js_palette_matches(self):
        src = (ROOT / 'public/js/v4/bang-tag.js').read_text(encoding='utf-8')
        for cid, c in C.COLORS.items():
            self.assertIn(f"{cid}:['{c[1]}','{c[2]}','{c[3]}','{c[4]}']", src, cid)
        for rid, r in C.ROLES.items():
            self.assertIn(f"{rid}:'{r[0]}'", src)

    def test_no_way_out_of_the_fund(self):
        src = inspect.getsource(bang)
        self.assertEqual(bang.COMMANDS, ('jr_bang_found', 'jr_bang_give'))
        self.assertNotIn('_wallet(j, part', src.replace('_wallet(j, -part', ''))   # only debits from a wallet
        self.assertNotIn("balance'] +=", src)                                    # never into a bank account
        for op in bang.OPS:
            self.assertNotRegex(op, 'withdraw|rut|refund|transfer|pay')
        self.assertNotIn('live_effects', src)                                    # nothing paid into a save later either
        self.assertEqual(src.count('_wallet('), 1)                               # _take's debit, the only wallet row
        self.assertEqual(src.count('INSERT INTO bang_fund'), 4)                  # give, build, the island (kind build), burn: the only ledger rows
        self.assertEqual(src.count("kind, amount, balance, at) VALUES(?,?,?,'give'"), 1)


class Reducer(unittest.TestCase):
    def setUp(self):
        p = patch.object(bang, 'now', lambda: T0)
        p.start()
        self.addCleanup(p.stop)

    def test_found_pays_the_fee_wallet_then_bank(self):
        s = titled(2_000_000, bank_balance=10_000_000)
        before = s['journey']['wallet'] + s['journey']['bank']['balance']
        s2, r = found(s)
        self.assertEqual(s2['journey']['wallet'], 0)
        self.assertEqual(s2['journey']['bank']['balance'], 7_000_000)
        self.assertEqual(before - 5_000_000, s2['journey']['bank']['balance'])
        nonce = s2['journey']['bang']['last']['r']
        self.assertRegex(nonce, r'^[0-9a-f]{16}$')                                  # the ledger ids' nonce (review fix 19/10)
        self.assertEqual(r['bang'], dict(k='found', n=1, r=nonce, name='Rồng Đỏ', emoji='🐉', color='do', motto='Đoàn kết', open=True))
        self.assertEqual(s2['journey']['bang'], dict(v=1, n=1, sum=5_000_000, last=dict(n=1, k='found', a=5_000_000, at=int(T0), r=nonce)))
        rows = [h for h in s2['journey']['history'] if h['label'].startswith('⚔️')]
        self.assertEqual([(h['amount'], h['kind']) for h in rows], [(-2_000_000, 'life')])
        validate_state(s2)

    def test_wallet_rows_never_over_ten_million(self):
        s = titled(35_000_000)
        bang._take(s, 25_000_000, 'x')
        amounts = [h['amount'] for h in s['journey']['history'] if h['label'] == 'x']
        self.assertEqual(amounts, [-10_000_000, -10_000_000, -5_000_000])
        validate_state(s)

    def test_found_refusals(self):
        s = titled()
        refused(self, s, 'jr_bang_found', name='Rồng Đỏ', emoji='🐉', color='do')                     # no confirmation
        refused(self, s, 'jr_bang_found', 'bad_emoji', name='Rồng Đỏ', emoji='💩', color='do', confirm=True)
        refused(self, s, 'jr_bang_found', 'bad_color', name='Rồng Đỏ', emoji='🐉', color='xanh', confirm=True)
        refused(self, s, 'jr_bang_found', 'bad_name', name='A', confirm=True)
        refused(self, s, 'jr_bang_found', 'bad_name', name='🐉🐉🐉 Rồng', confirm=True)                # 3 emoji
        refused(self, s, 'jr_bang_found', 'bad_name', name='Bang địt', confirm=True)                   # filtered like a player name
        refused(self, s, 'jr_bang_found', 'bad_name', name='dit me bang', confirm=True)                # unaccented, offensive_name
        refused(self, s, 'jr_bang_found', name='vao zalo.com nhe', confirm=True)                       # a link
        refused(self, s, 'jr_bang_found', name='Rồng Đỏ', motto='gọi 0912345678 nhé', confirm=True)    # a phone in the motto
        refused(self, s, 'jr_bang_found', name='Rồng Đỏ', extra=1, confirm=True)
        refused(self, s, 'jr_bang_found', name='Rồng Đỏ', open='yes', confirm=True)
        # 21/10 owner: no chức danh needed to found a bang any more (14 days + 5M xu)
        poor = titled(4_999_000)
        refused(self, poor, 'jr_bang_found', 'not_enough', name='Rồng Đỏ', confirm=True)
        debt = titled(20_000_000)
        debt['journey']['wallet'] = -10
        refused(self, debt, 'jr_bang_found', 'not_enough', name='Rồng Đỏ', confirm=True)
        free = titled()
        free['journey']['story'] = False
        refused(self, free, 'jr_bang_found', 'locked', name='Rồng Đỏ', confirm=True)

    def test_motto_is_masked(self):
        s = titled()
        _, r = found(s, motto='đéo ai bằng')
        self.assertNotIn('đéo', r['bang']['motto'])

    def test_name_key(self):
        self.assertEqual(bang.name_key('Rồng Đỏ'), 'rongdo')
        self.assertEqual(bang.name_key('RONG-DO 🐉'), 'rongdo')
        self.assertEqual(bang.name_key('rồng   đỏ'), 'rongdo')

    def test_give_refusals(self):
        s = titled()
        ok = dict(bang='b0123456789', confirm=True)
        refused(self, s, 'jr_bang_give', amount=999, **ok)
        refused(self, s, 'jr_bang_give', amount=1500, **ok)
        refused(self, s, 'jr_bang_give', amount=10_000_001, **ok)                  # not a whole thousand (and more than the wallet)
        refused(self, s, 'jr_bang_give', amount=C.GIVE_MAX + 1000, **ok)            # the technical ceiling
        refused(self, s, 'jr_bang_give', amount=1000.0, **ok)
        refused(self, s, 'jr_bang_give', amount=True, **ok)
        refused(self, s, 'jr_bang_give', amount=1000, bang='nope', confirm=True)
        refused(self, s, 'jr_bang_give', amount=1000, bang='b0123456789')
        poor = titled(5_000)
        refused(self, poor, 'jr_bang_give', 'not_enough', amount=6_000, **ok)
        s2, r = act(s, 'jr_bang_give', amount=1_000_000, **ok)
        self.assertEqual(s2['journey']['wallet'], 19_000_000)
        self.assertEqual(r['bang'], dict(k='give', n=1, bang='b0123456789', a=1_000_000, r=s2['journey']['bang']['last']['r']))
        s3, r3 = act(s2, 'jr_bang_give', amount=1_000_000, **ok)
        self.assertNotEqual(r3['bang']['r'], r['bang']['r'])                        # a new nonce each time

    def test_block_validate_and_upgrade(self):
        s = titled()
        validate_state(s)
        s['journey']['bang'] = dict(v=1, n=0, sum=0, last=None)
        validate_state(s)
        for bad in (dict(v=1, n=1, sum=0, last=None, x=1), dict(v=2, n=0, sum=0, last=None),
                    dict(v=1, n=2, sum=0, last=dict(n=1, k='give', a=5, at=1))):
            s['journey']['bang'] = bad
            with self.assertRaises(GameError):
                validate_state(s)
        j = {'bang': dict(v=1, n=3, sum=7, last=dict(n=3, k='give', a=5, at=1, extra=2), more=1)}
        bang.upgrade(j)
        self.assertEqual(j['bang'], dict(v=1, n=3, sum=7, last=dict(n=3, k='give', a=5, at=1)))
        # the nonce is optional (a block written before it stays valid) and kept by upgrade; a bad one is refused
        for ok_last in (dict(n=1, k='give', a=5, at=1), dict(n=1, k='give', a=5, at=1, r='0123456789abcdef')):
            s['journey']['bang'] = dict(v=1, n=1, sum=5, last=ok_last)
            validate_state(s)
        s['journey']['bang'] = dict(v=1, n=1, sum=5, last=dict(n=1, k='give', a=5, at=1, r='nope'))
        with self.assertRaises(GameError):
            validate_state(s)
        j = {'bang': dict(v=1, n=1, sum=5, last=dict(n=1, k='give', a=5, at=1, r='0123456789abcdef', extra=2))}
        bang.upgrade(j)
        self.assertEqual(j['bang']['last'], dict(n=1, k='give', a=5, at=1, r='0123456789abcdef'))


class Base(unittest.TestCase):
    """A real database (PostgreSQL with TEST_DATABASE_URL), players with accounts."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        bang._VIEW.clear()
        bang.gh_reset()
        self.addCleanup(bang.gh_reset)
        self.addCleanup(bang._VIEW.clear)
        self.t = [T0]
        p = patch.object(bang, 'now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)
        self.n = 0
        self.sent = []
        from game import live_chat
        real = live_chat.notify
        q = patch.object(live_chat, 'notify', side_effect=lambda db, e: (self.sent.append(e), real(db, e))[1])
        q.start()
        self.addCleanup(q.stop)

    def player(self, name='Lan', wallet=50_000_000, days=30, title=True, account=True):
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
            if title:
                promotion.record(s, 'milk_tea', True)['rank'] = 1
        mr._mutate(self.store, {sid: fn})
        if not account:
            return token
        login = secrets.token_hex(32)
        born = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days * 86400))
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?, ?, ?, ?, ?)',
                       ('u' + secrets.token_hex(5), name, 'x', sid, born))
            db.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'c')", (self.store.digest(login), sid))
        return login

    def sid(self, token):
        return self.store.key(token)

    def pid(self, token):
        return bang.pid_of(self.sid(token))

    def cmd(self, token, action, **p):
        self.n += 1
        return self.store.command(token, f'bang-{self.n:08d}-{os.getpid()}', self.store.read(token)[1], None, action, p)

    def found(self, token, name='Rồng Đỏ', **p):
        r = self.cmd(token, 'jr_bang_found', **dict(dict(name=name, emoji='🐉', color='do', motto='Đoàn kết', open=True, confirm=True), **p))
        return self.mine(token)['bang']

    def give(self, token, amount, bid=None):
        return self.cmd(token, 'jr_bang_give', bang=bid or self.mine(token)['bang'], amount=amount, confirm=True)

    def op(self, token, op, **data):
        return bang.post(self.store, token, op, data)

    def mine(self, token):
        with self.store.connect() as db:
            return bang._mine(db, self.sid(token))

    def wallet(self, token):
        return self.store.read(token)[0]['journey']['wallet']

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        r = self.rows(sql, args)
        return r[0] if r else None

    def refused_op(self, token, op, want=None, **data):
        with self.assertRaises(bang.BangError) as cm:
            self.op(token, op, **data)
        if want:
            self.assertEqual(cm.exception.code, want, str(cm.exception))
        return str(cm.exception)

    def refused_cmd(self, token, action, want=None, **p):
        before = self.wallet(token)
        with self.assertRaises(GameError) as cm:
            self.cmd(token, action, **p)
        self.assertEqual(self.wallet(token), before)   # nothing paid
        if want:
            self.assertEqual(cm.exception.code, want, str(cm.exception))
        return str(cm.exception)

    def finish(self, bid, fac):
        """Time passes until the build of `fac` is done."""
        r = self.one('SELECT ready_at FROM bang_facilities WHERE bang=? AND fac=?', (bid, fac))
        self.t[0] = max(self.t[0], float(r['ready_at']) + 1)
        self.store.transaction(lambda db: bang.finish_builds(db, bid, self.t[0]))

    def set_level(self, bid, fac, level):
        def run(db):
            db.execute('INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT(bang, fac) DO UPDATE SET level=excluded.level',
                       (bid, fac, level))
        self.store.transaction(run)

    def set_points(self, token, pts):
        self.store.transaction(lambda db: db.execute("UPDATE bang_members SET points=? WHERE sid=? AND status='in'", (pts, self.sid(token))))

    def set_fund(self, bid, xu):
        self.store.transaction(lambda db: db.execute('UPDATE bangs SET fund=? WHERE id=?', (xu, bid)))

    def set_isle(self, bid, level=1):
        """🏝️ The bang holds its island at `level` (21/10: a bang founded from now on buys it)."""
        self.store.transaction(lambda db: db.execute('UPDATE bangs SET isle=?, isle_to=NULL, isle_ready=NULL WHERE id=?', (level, bid)))


class Founding(Base):
    def test_found_writes_the_bang_its_leader_and_chat(self):
        a = self.player(name='Lan')
        bid = self.found(a)
        self.assertEqual(self.wallet(a), 45_000_000)
        b = self.one('SELECT * FROM bangs WHERE id=?', (bid,))
        self.assertEqual((b['name'], b['key'], b['emoji'], b['color'], b['status'], b['fund'], b['leader']),
                         ('Rồng Đỏ', 'rongdo', '🐉', 'do', 'active', 0, self.sid(a)))
        m = self.mine(a)
        self.assertEqual((m['role'], m['points']), ('chu', 0))
        self.assertEqual(self.one('SELECT level FROM bang_facilities WHERE bang=? AND fac=?', (bid, C.HALL))['level'], 1)
        ch = self.one('SELECT * FROM chat_channels WHERE id=?', (b['channel'],))
        self.assertEqual((ch['kind'], ch['owner_pid'], ch['title']), ('group', 'bang', '🐉 Rồng Đỏ'))
        self.assertEqual([r['pid'] for r in self.rows('SELECT pid FROM chat_members WHERE channel=?', (b['channel'],))], [self.pid(a)])
        self.assertTrue(any(e.get('op') == 'bang' and self.pid(a) in e.get('add', []) for e in self.sent))
        self.assertTrue(self.rows("SELECT 1 FROM news WHERE kind='bang'"))
        validate_state(self.store.read(a)[0])

    def test_refused_in_the_commit_pays_nothing(self):
        young = self.player(days=10)
        self.assertIn('14 ngày', self.refused_cmd(young, 'jr_bang_found', 'too_new', name='Hổ Xám', confirm=True))
        guest = self.player(account=False)
        self.refused_cmd(guest, 'jr_bang_found', 'account', name='Hổ Xám', confirm=True)
        a, b = self.player(), self.player(name='Minh')
        self.found(a, 'Rồng Đỏ')
        for same in ('rồng đỏ', 'RONG DO', 'Rong-Do'):   # case, diacritics, spaces and punctuation
            self.refused_cmd(b, 'jr_bang_found', 'name_taken', name=same, confirm=True)
        self.assertEqual(self.rows("SELECT COUNT(*) AS n FROM bangs")[0]['n'], 1)

    def test_a_leader_cannot_found_another(self):
        a = self.player()
        self.found(a)
        self.refused_cmd(a, 'jr_bang_found', 'leader', name='Hổ Xám', confirm=True)

    def test_a_member_founding_leaves_the_old_bang(self):
        a, b = self.player(), self.player(name='Minh')
        first = self.found(a)
        self.op(b, 'join', bang=first)
        second = self.found(b, 'Hổ Xám')
        self.assertNotEqual(first, second)
        self.assertEqual(self.mine(b)['role'], 'chu')
        self.assertEqual(self.one('SELECT status FROM bang_members WHERE bang=? AND sid=?', (first, self.sid(b)))['status'], 'out')

    def test_two_foundings_of_one_name_at_once(self):
        a, b = self.player(), self.player(name='Minh')
        out, errs = [], []

        def go(tok):
            try:
                self.cmd(tok, 'jr_bang_found', name='Song Long', emoji='🐉', color='do', confirm=True)
                out.append(tok)
            except GameError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=(x,)) for x in (a, b)]
        [x.start() for x in th]
        [x.join() for x in th]
        self.assertEqual((len(out), errs), (1, ['name_taken']))
        loser = b if out == [a] else a
        self.assertEqual(self.wallet(loser), 50_000_000)


class Joining(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def test_open_join_leave_switch_freely(self):
        b = self.player(name='Minh')
        r = self.op(b, 'join', bang=self.bid)
        self.assertEqual(r['done']['joined'], self.bid)
        self.assertEqual(self.mine(b)['role'], 'tv')
        ch = self.one('SELECT channel FROM bangs WHERE id=?', (self.bid,))['channel']
        self.assertIn(self.pid(b), [x['pid'] for x in self.rows('SELECT pid FROM chat_members WHERE channel=?', (ch,))])
        c = self.player(name='Tú')
        other = self.found(c, 'Hổ Xám')
        self.op(b, 'join', bang=other)                      # no cooldown, no condition: straight into another
        self.assertEqual(self.mine(b)['bang'], other)
        self.assertNotIn(self.pid(b), [x['pid'] for x in self.rows('SELECT pid FROM chat_members WHERE channel=?', (ch,))])
        self.op(b, 'join', bang=self.bid)                   # and back at once
        self.assertEqual(self.mine(b)['bang'], self.bid)
        self.assertEqual(len(self.rows("SELECT 1 FROM bang_members WHERE sid=? AND status='in'", (self.sid(b),))), 1)
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_stints WHERE sid=?', (self.sid(b),))), 3)
        self.refused_op(b, 'leave', None)                   # needs confirmation
        self.op(b, 'leave', confirm=True)
        self.assertIsNone(self.mine(b))
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_members WHERE sid=?', (self.sid(b),))), 2)   # rows kept, 'out'

    def test_no_condition_to_join(self):
        young = self.player(name='Bé', days=0, title=False, wallet=0)
        self.op(young, 'join', bang=self.bid)
        self.assertEqual(self.mine(young)['bang'], self.bid)
        guest = self.player(account=False)
        self.refused_op(guest, 'join', 'login_required', bang=self.bid)

    def test_leader_must_hand_over_first(self):
        c = self.player(name='Tú')
        other = self.found(c, 'Hổ Xám')
        self.refused_op(self.a, 'join', 'leader', bang=other)
        self.refused_op(self.a, 'leave', 'leader', confirm=True)

    def test_by_approval_and_invitations(self):
        self.op(self.a, 'set', open=False)
        b, c, d = self.player(name='Minh'), self.player(name='Tú'), self.player(name='Hà')
        r = self.op(b, 'join', bang=self.bid)
        self.assertEqual(r['done'].get('asked'), self.bid)
        self.assertIsNone(self.mine(b))
        page = bang.page(self.store, self.sid(self.a))
        self.assertEqual([x['pid'] for x in page['asks']], [self.pid(b)])
        self.refused_op(c, 'approve', 'not_member', pid=self.pid(b))
        self.op(self.a, 'approve', pid=self.pid(b))
        self.assertEqual(self.mine(b)['bang'], self.bid)
        self.op(c, 'join', bang=self.bid)
        self.op(self.a, 'approve', pid=self.pid(c), ok=False)
        self.assertIsNone(self.mine(c))
        self.refused_op(b, 'invite', 'role', code='PCC-AAAAAA')            # Thành viên cannot invite
        code = mr.ensure_person(self.store, self.sid(d))['code']
        self.op(self.a, 'invite', code=code)
        self.assertTrue(any(e.get('invite') == self.pid(d) for e in self.sent))
        me = bang.me_view(self.store, d)
        self.assertEqual([x['bang'] for x in me['invites']], [self.bid])
        self.op(d, 'accept', bang=self.bid)                                # an invitation opens a closed bang
        self.assertEqual(self.mine(d)['bang'], self.bid)
        self.refused_op(d, 'accept', 'gone', bang=self.bid)

    def test_cap_by_the_hall(self):
        for i in range(9):
            self.op(self.player(name=f'P{i}'), 'join', bang=self.bid)
        late = self.player(name='Muộn')
        self.assertIn('10 người', self.refused_op(late, 'join', 'full', bang=self.bid))
        self.set_fund(self.bid, 20_000_000)
        self.op(self.a, 'build', fac=C.HALL, confirm=True)
        self.refused_op(late, 'join', 'full', bang=self.bid)                # still building
        self.finish(self.bid, C.HALL)
        self.op(late, 'join', bang=self.bid)
        self.assertEqual(bang.page(self.store, self.sid(self.a))['bang']['cap'], 15)

    def test_two_joins_for_the_last_seat(self):
        for i in range(8):
            self.op(self.player(name=f'P{i}'), 'join', bang=self.bid)
        x, y = self.player(name='X'), self.player(name='Y')
        got, errs = [], []

        def go(tok):
            try:
                self.op(tok, 'join', bang=self.bid)
                got.append(tok)
            except bang.BangError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=(t,)) for t in (x, y)]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual((len(got), errs), (1, ['full']))
        self.assertEqual(self.rows("SELECT COUNT(*) AS n FROM bang_members WHERE bang=? AND status='in'", (self.bid,))[0]['n'], 10)


class Roles(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.m = [self.player(name=f'M{i}') for i in range(8)]
        for t in self.m:
            self.op(t, 'join', bang=self.bid)

    def role(self, t):
        return self.mine(t)['role']

    def test_seats(self):
        self.op(self.a, 'role', pid=self.pid(self.m[0]), role='pho')
        self.op(self.a, 'role', pid=self.pid(self.m[1]), role='pho')
        self.refused_op(self.a, 'role', 'seats', pid=self.pid(self.m[2]), role='pho')
        for t in self.m[2:5]:
            self.op(self.a, 'role', pid=self.pid(t), role='lao')
        self.refused_op(self.a, 'role', 'seats', pid=self.pid(self.m[5]), role='lao')
        self.op(self.a, 'role', pid=self.pid(self.m[5]), role='tinh')
        self.refused_op(self.m[0], 'role', 'role', pid=self.pid(self.m[6]), role='tinh')   # only the leader appoints
        self.assertEqual(bang.tag_of(self.store, self.store.connect(), self.sid(self.m[0]))['r'], 'pho')

    def test_handover(self):
        self.refused_op(self.a, 'role', None, pid=self.pid(self.m[0]), role='chu')        # needs confirmation
        self.op(self.a, 'role', pid=self.pid(self.m[0]), role='chu', confirm=True)
        self.assertEqual((self.role(self.m[0]), self.role(self.a)), ('chu', 'pho'))
        self.assertEqual(self.one('SELECT leader FROM bangs WHERE id=?', (self.bid,))['leader'], self.sid(self.m[0]))
        self.op(self.a, 'leave', confirm=True)                                            # no longer the leader: free to go
        self.assertIsNone(self.mine(self.a))
        # both Phó seats full: the old leader becomes a Thành viên
        new = self.m[0]
        self.op(new, 'role', pid=self.pid(self.m[1]), role='pho')
        self.op(new, 'role', pid=self.pid(self.m[2]), role='pho')
        self.op(new, 'role', pid=self.pid(self.m[3]), role='chu', confirm=True)
        self.assertEqual(self.role(new), 'tv')

    def test_kicks_and_the_title_gone_on_leaving(self):
        self.op(self.a, 'role', pid=self.pid(self.m[0]), role='pho')
        self.op(self.a, 'role', pid=self.pid(self.m[1]), role='pho')
        self.op(self.a, 'role', pid=self.pid(self.m[2]), role='lao')
        self.refused_op(self.m[2], 'kick', 'role', pid=self.pid(self.m[3]), confirm=True)   # Trưởng lão cannot kick
        self.refused_op(self.m[0], 'kick', 'role', pid=self.pid(self.m[1]), confirm=True)   # a Phó never kicks a Phó
        self.refused_op(self.m[0], 'kick', 'role', pid=self.pid(self.a), confirm=True)
        self.op(self.m[0], 'kick', pid=self.pid(self.m[2]), confirm=True)
        self.assertIsNone(self.mine(self.m[2]))
        with self.store.connect() as db:
            self.assertIsNone(bang.tag_of(self.store, db, self.sid(self.m[2])))
        self.assertEqual(self.one('SELECT role FROM bang_members WHERE bang=? AND sid=?', (self.bid, self.sid(self.m[2])))['role'], 'tv')
        self.op(self.m[2], 'join', bang=self.bid)
        self.assertEqual(self.role(self.m[2]), 'tv')                                         # rejoining starts again as a member


class Fund(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def test_deposit_points_and_ledger(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.give(b, 2_500_000)
        self.assertEqual(self.wallet(b), 47_500_000)
        r = self.one('SELECT * FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['fund'], r['given']), (2_500_000, 2_500_000))
        led = self.rows('SELECT * FROM bang_fund WHERE bang=?', (self.bid,))
        nonce = self.store.read(b)[0]['journey']['bang']['last']['r']
        self.assertEqual([(x['id'], x['kind'], x['amount'], x['balance']) for x in led], [(f'g:{self.pid(b)}:{nonce}', 'give', 2_500_000, 2_500_000)])
        m = self.mine(b)
        self.assertEqual((m['points'], m['earned'], m['given']), (2500, 2500, 2_500_000))
        self.set_level(self.bid, 'kho', 5)                                        # +25 % points (+5 %/level since 21/10)
        self.give(b, 1_000_000)
        self.assertEqual(self.mine(b)['points'], 2500 + 1250)
        validate_state(self.store.read(b)[0])

    def test_refusals_pay_nothing(self):
        b = self.player(name='Minh')
        self.refused_cmd(b, 'jr_bang_give', 'not_member', bang=self.bid, amount=1000, confirm=True)
        self.give(self.a, 10_000_000)
        self.give(self.a, 10_000_000)
        self.give(self.a, 1000)                                                   # 21/10: no cap (it was 20 M without a Kho)
        self.assertEqual(self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund'], 20_001_000)

    def test_two_deposits_at_once_no_cap(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.give(self.a, 10_000_000)
        self.give(self.a, 4_000_000)                                              # the old cap (20 M) is no more
        ok, errs = [], []

        def go(tok):
            try:
                self.give(tok, 5_000_000, self.bid)
                ok.append(tok)
            except GameError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=(t,)) for t in (self.a, b)]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual((len(ok), errs), (2, []))
        self.assertEqual(self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund'], 24_000_000)
        total = sum(x['amount'] for x in self.rows("SELECT amount FROM bang_fund WHERE bang=? AND kind='give'", (self.bid,)))
        self.assertEqual(total, 24_000_000)
        self.assertEqual(self.wallet(self.a) + self.wallet(b), 45_000_000 - 19_000_000 + 50_000_000 - 5_000_000)

    def test_two_members_deposit_at_once_many_times(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)

        def go(tok):
            for _ in range(4):
                self.give(tok, 1_000_000, self.bid)
        th = [threading.Thread(target=go, args=(t,)) for t in (self.a, b)]
        [t.start() for t in th]
        [t.join() for t in th]
        r = self.one('SELECT fund, given FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['fund'], r['given']), (8_000_000, 8_000_000))
        bal = [x['balance'] for x in self.rows("SELECT balance FROM bang_fund WHERE bang=? ORDER BY balance", (self.bid,))]
        self.assertEqual(bal, [i * 1_000_000 for i in range(1, 9)])   # each row saw the one before it

    def test_disband_burns_never_pays(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.give(self.a, 3_000_000)
        before = (self.wallet(self.a), self.wallet(b))
        self.refused_op(self.a, 'disband', 'confirm', confirm=True, name='sai tên')
        self.refused_op(b, 'disband', 'role', confirm=True, name='Rồng Đỏ')
        self.op(self.a, 'disband', confirm=True, name='Rồng Đỏ')
        r = self.one('SELECT * FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['status'], r['fund'], r['burned'], r['given']), ('disbanded', 0, 3_000_000, 3_000_000))
        self.assertEqual([(x['kind'], x['amount'], x['balance']) for x in self.rows('SELECT * FROM bang_fund WHERE bang=? ORDER BY at, kind DESC', (self.bid,))],
                         [('give', 3_000_000, 3_000_000), ('burn', -3_000_000, 0)])
        self.assertEqual((self.wallet(self.a), self.wallet(b)), before)            # nobody got anything back
        self.assertIsNone(self.mine(self.a))
        self.assertIsNone(self.mine(b))
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_members WHERE bang=?', (self.bid,))), 2)   # rows kept
        self.assertEqual(self.rows('SELECT 1 FROM chat_members WHERE channel=?', (r['channel'],)), [])
        self.refused_cmd(b, 'jr_bang_give', 'closed', bang=self.bid, amount=1000, confirm=True)
        c = self.player(name='Tú')
        self.found(c, 'Rồng Đỏ')                                                  # the name is free again


class Points(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def test_checkin_and_work_days_capped(self):
        self.op(self.a, 'checkin')
        self.refused_op(self.a, 'checkin', 'done')
        for _ in range(5):
            self.store.transaction(lambda db: bang.work_commit(db, self.sid(self.a)))
        self.assertEqual(self.mine(self.a)['points'], C.ACTIVITY_DAY_MAX)
        page = bang.page(self.store, self.sid(self.a))
        self.assertEqual((page['me']['today'], page['me']['checkin']), (50, True))
        self.t[0] += 86400                                                        # the next day
        self.op(self.a, 'checkin')
        self.assertEqual(self.mine(self.a)['points'], 70)

    def test_end_day_command_earns(self):
        def day():
            for a in ('start_day', 'end_day'):
                self.n += 1
                self.store.command(self.a, f'day-{self.n:08d}', self.store.read(self.a)[1], 'milk_tea', a, {})
        day()
        self.assertEqual(self.mine(self.a)['points'], C.WORK_POINTS)
        self.assertEqual(self.rows("SELECT kind, pts FROM bang_points WHERE kind='work'"), [dict(kind='work', pts=C.WORK_POINTS)])

    def test_no_farming_by_hopping(self):
        b = self.player(name='Minh')
        other = self.found(b, 'Hổ Xám')
        c = self.player(name='Tú')
        self.op(c, 'join', bang=self.bid)
        self.op(c, 'checkin')
        self.op(c, 'join', bang=other)
        self.refused_op(c, 'checkin', 'done')                                    # once a day, whatever the bang
        self.op(c, 'join', bang=self.bid)
        self.assertEqual(self.mine(c)['points'], 20)                             # the first bang's points were kept

    def test_outsiders_earn_nothing(self):
        x = self.player(name='Ngoài')
        self.store.transaction(lambda db: bang.work_commit(db, self.sid(x)))
        self.assertEqual(self.rows('SELECT 1 FROM bang_points WHERE sid=?', (self.sid(x),)), [])
        self.refused_op(x, 'checkin', 'not_member')


class Shop(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def rid(self):
        return 'r-' + secrets.token_hex(6)

    def test_points_only_and_requirements(self):
        w = self.wallet(self.a)
        self.refused_op(self.a, 'buy', 'not_enough', item='huy', rid=self.rid())
        self.set_points(self.a, 1000)
        self.refused_op(self.a, 'buy', 'locked', item='ao', rid=self.rid())     # needs Xưởng may 1
        self.refused_op(self.a, 'buy', None, item='huy')                           # a request id is needed
        rid = self.rid()
        self.op(self.a, 'buy', item='huy', rid=rid)
        again = self.op(self.a, 'buy', item='huy', rid=rid)                        # a retried request: once
        self.assertTrue(again['done'].get('again'))
        self.assertEqual(self.mine(self.a)['points'], 850)
        self.refused_op(self.a, 'buy', 'owned', item='huy', rid=self.rid())
        self.assertEqual(self.wallet(self.a), w)                                   # never xu
        self.set_level(self.bid, 'xuong_may', 2)                                   # −10 %
        self.op(self.a, 'buy', item='ao', rid=self.rid())
        self.assertEqual(self.mine(self.a)['points'], 850 - 270)
        m = self.mine(self.a)
        self.assertEqual(m['wear'] & (C.WEAR_BITS['huy'] | C.WEAR_BITS['ao']), 3)   # worn at once
        with self.store.connect() as db:
            self.assertEqual(bang.tag_of(self.store, db, self.sid(self.a)).get('b'), 1)
        self.refused_op(self.a, 'wear', 'locked', item='ao', on=True, style='hoodie')
        self.set_level(self.bid, 'xuong_may', 3)
        self.op(self.a, 'wear', item='ao', on=True, style='hoodie')
        self.assertEqual(bang.me_view(self.store, self.a)['mine']['uniform'], 'hoodie')

    def test_items_usable_only_in_their_bang(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.set_points(b, 500)
        self.op(b, 'buy', item='huy', rid=self.rid())
        c = self.player(name='Tú')
        other = self.found(c, 'Hổ Xám')
        self.op(b, 'join', bang=other)
        me = bang.me_view(self.store, b)
        self.assertEqual([(x['bang'], x['item']) for x in me['items']], [(self.bid, 'huy')])   # still in the inventory
        self.refused_op(b, 'wear', 'not_owned', item='huy', on=True)
        with self.store.connect() as db:
            self.assertNotIn('b', bang.tag_of(self.store, db, self.sid(b)))
        self.op(b, 'join', bang=self.bid)
        with self.store.connect() as db:
            self.assertEqual(bang.tag_of(self.store, db, self.sid(b)).get('b'), 1)   # back in that bang: worn again
        self.op(b, 'leave', confirm=True)
        self.refused_op(b, 'wear', 'not_member', item='huy', on=True)

    def test_fireworks(self):
        self.set_points(self.a, 1000)
        self.refused_op(self.a, 'buy', 'locked', item='phao', rid=self.rid())
        self.set_level(self.bid, 'cong', 3)
        self.op(self.a, 'buy', item='phao', rid=self.rid())
        self.op(self.a, 'buy', item='phao', rid=self.rid())
        self.sent.clear()
        self.op(self.a, 'fire', rid=self.rid())
        shows = [e for e in self.sent if e.get('op') == 'fireworks']
        self.assertEqual(len(shows), 1)
        self.assertEqual((shows[0]['name'], shows[0]['size']), ('🐉 Rồng Đỏ', 'lon'))
        from live.fireworks import ID_RE
        self.assertRegex(shows[0]['id'], ID_RE)
        self.refused_op(self.a, 'fire', 'soon', rid=self.rid())
        self.t[0] += C.PHAO_GAP
        self.op(self.a, 'fire', rid=self.rid())
        self.refused_op(self.a, 'fire', 'none', rid=self.rid())


class Facilities(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def test_build_from_the_fund(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.refused_op(b, 'build', 'role', fac='kho', confirm=True)
        self.refused_op(self.a, 'build', 'not_enough', fac='kho', confirm=True)
        self.give(self.a, 10_000_000)
        self.refused_op(self.a, 'build', None, fac='kho')                         # needs confirmation
        self.op(self.a, 'build', fac='kho', confirm=True)
        r = self.one('SELECT fund, spent FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['fund'], r['spent']), (8_000_000, 2_000_000))
        self.refused_op(self.a, 'build', 'building', fac='kho', confirm=True)
        self.refused_op(self.a, 'build', 'slots', fac='cong', confirm=True)        # one at a time below hall 3
        self.assertEqual(bang.levels(self.store.connect(), self.bid)['kho'], 0)
        self.finish(self.bid, 'kho')
        with self.store.connect() as db:
            self.assertEqual(bang.levels(db, self.bid)['kho'], 1)
        self.assertEqual(self.one("SELECT kind, amount, balance FROM bang_fund WHERE kind='build'"), dict(kind='build', amount=-2_000_000, balance=8_000_000))
        self.set_level(self.bid, 'kho', 2)
        self.set_fund(self.bid, 100_000_000)
        self.refused_op(self.a, 'build', 'hall', fac='kho', confirm=True)          # level 3 needs the hall at 2
        self.set_level(self.bid, C.HALL, 3)
        self.op(self.a, 'build', fac='kho', confirm=True)
        self.op(self.a, 'build', fac='cong', confirm=True)                         # 2 slots from hall 3
        self.refused_op(self.a, 'build', 'slots', fac='tuong', confirm=True)
        self.set_level(self.bid, 'tuong', 10)
        self.refused_op(self.a, 'build', 'max', fac='tuong', confirm=True)

    def test_page_shows_costs(self):
        page = bang.page(self.store, self.sid(self.a))
        fac = {f['id']: f for f in page['facilities']}
        self.assertEqual((fac[C.HALL]['level'], fac[C.HALL]['next'], fac[C.HALL]['cost']), (1, 2, 20_000_000))
        self.assertEqual((fac['kho']['level'], fac['kho']['cost'], fac['kho']['secs']), (0, 2_000_000, 3600))
        self.assertEqual(page['fund_cap'], C.FUND_MAX)                           # 21/10: no cap (an older page reads the ceiling)
        self.assertEqual(page['bang']['cap'], 10)


class Golden(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def start(self, hours=2):
        return int((self.t[0] + hours * 3600) // 300 * 300)

    def test_rules(self):
        self.refused_op(self.a, 'gh_set', 'locked', start=self.start())
        self.set_level(self.bid, 'den_vang', 1)
        self.refused_op(self.a, 'gh_set', 'too_soon', start=int(self.t[0] // 300 * 300 + 600))
        self.refused_op(self.a, 'gh_set', 'too_far', start=self.start(24 * 8))
        self.refused_op(self.a, 'gh_set', None, start=self.start() + 7)            # 5-minute marks
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.refused_op(b, 'gh_set', 'role', start=self.start())
        s0 = self.start()
        self.op(self.a, 'gh_set', start=s0)
        g = self.one('SELECT * FROM bang_gh WHERE bang=?', (self.bid,))
        self.assertEqual(g['ends'] - g['start'], 30 * 60)
        self.refused_op(self.a, 'gh_set', None, start=self.start(26 + 24))         # level 1: once a week
        self.set_level(self.bid, 'den_vang', 5)
        self.refused_op(self.a, 'gh_set', 'day', start=s0 + 3 * 3600 if bang.vn_day(s0 + 3 * 3600) == bang.vn_day(s0) else s0 - 3 * 3600)
        nxt = self.start(30)
        self.op(self.a, 'gh_set', start=nxt)
        g2 = self.one('SELECT * FROM bang_gh WHERE bang=? AND start=?', (self.bid, float(nxt)))
        self.assertEqual(g2['ends'] - g2['start'], 60 * 60)
        self.t[0] = s0 + 10
        self.refused_op(self.a, 'gh_cancel', 'started', id=int(g['id']))           # never changed once started
        self.op(self.a, 'gh_cancel', id=int(g2['id']))
        self.assertEqual(self.one('SELECT status FROM bang_gh WHERE id=?', (g2['id'],))['status'], 'cancelled')

    def mult(self, token, *times):
        tok = bang.bind(self.sid(token))
        try:
            return [bang.gold_mult(x) for x in times]
        finally:
            bang.unbind(tok)

    def fresh(self, token=None):
        """A new snapshot, as another process (or the next minute) reads it."""
        bang.gh_reset()
        with self.store.connect() as db:
            bang.prepare(db, self.t[0], sid=self.sid(token) if token else None)

    def test_windows_follow_membership_and_bind_per_command(self):
        """A window counts for members who joined ≥ 24 h before it starts, and only until they leave."""
        self.set_level(self.bid, 'den_vang', 1)
        b, c = self.player(name='Minh'), self.player(name='Tú')
        self.op(b, 'join', bang=self.bid)                                          # at T0
        self.t[0] = T0 + 25 * 3600
        s0 = self.start()                                                          # T0 + 27 h
        self.op(self.a, 'gh_set', start=s0)
        self.op(c, 'join', bang=self.bid)                                          # 2 h before the start: too late
        self.t[0] = s0 + 60
        self.fresh()
        for tok, want in ((self.a, 1), (b, 1), (c, 0)):
            self.assertEqual(len(bang.windows(self.sid(tok))), want, tok)
        self.t[0] = s0 + 600
        self.op(b, 'leave', confirm=True)                                          # left during it: ×2 only until then
        for snapshot in ('this process', 'a fresh read'):
            if snapshot == 'a fresh read':
                self.fresh()
            self.assertEqual(self.mult(b, s0 - 1, s0 + 5, s0 + 599, s0 + 600, s0 + 900), [100, 200, 200, 100, 100], snapshot)
            self.assertEqual(self.mult(self.a, s0 + 5, s0 + 30 * 60 - 1, s0 + 30 * 60), [200, 200, 100], snapshot)
            self.assertEqual(self.mult(c, s0 + 5), [100], snapshot)
        tok = bang.bind(self.sid(b))
        try:
            self.assertEqual(staff_market.x('milk_tea', s0 + 5, bang.gold_mult(s0 + 5)), 200)   # the market is off in tests: ×1
            self.assertEqual(golden_hour.scale_take(0, s0 + 5, bang.gold_mult(s0 + 5)), 100)    # take ×2
        finally:
            bang.unbind(tok)
        self.assertEqual(bang.gold_mult(s0 + 5), 100)                              # unbound: nobody's
        # never both: inside the town's ×2 too, still ×2
        with patch.dict(os.environ, {'MNL_GOLDEN_OFF': '0'}), patch.object(golden_hour, '_plan', lambda d: dict(kind='hour', start=0, end=2**40, mult=200, minutes=60)):
            tok = bang.bind(self.sid(self.a))
            try:
                self.assertEqual(staff_market.x('milk_tea', s0 + 5, bang.gold_mult(s0 + 5)) * 1, staff_market.market('milk_tea', s0 + 5) * 2)
                self.assertEqual(golden_hour.scale_take(0, s0 + 5, bang.gold_mult(s0 + 5)), 100)
            finally:
                bang.unbind(tok)

    def test_hopping_between_two_bangs_windows(self):
        """Review fix 19/10: hopping into another bang right before its window earns nothing there, and leaving a bang
        stops its window; ×2 only where both rules hold. Offline catch-up (the windows read later, from the player's own
        older ones) books exactly the same."""
        e = self.player(name='Hùng')
        other = self.found(e, 'Hổ Xám')
        for bid in (self.bid, other):
            self.set_level(bid, 'den_vang', 1)
        h, g = self.player(name='Hà'), self.player(name='Giang')
        self.op(h, 'join', bang=self.bid)                                          # h in Rồng Đỏ since T0
        self.op(g, 'join', bang=other)                                             # g in Hổ Xám since T0
        self.t[0] = T0 + 25 * 3600
        wx, wy = self.start(2), self.start(3)                                      # Rồng Đỏ's window, then Hổ Xám's
        self.op(self.a, 'gh_set', start=wx)
        self.op(e, 'gh_set', start=wy)
        self.t[0] = wx + 600
        self.op(h, 'join', bang=other)                                             # hops to Hổ Xám 50 min before its window
        self.t[0] = wy + 60
        self.op(h, 'join', bang=self.bid)                                          # and back during it
        self.t[0] = wy + 120
        want_h = [200, 200, 100, 100, 100, 100]
        times_h = (wx + 5, wx + 599, wx + 600, wx + 1700, wy + 5, wy + 100)
        for snapshot in ('this process', 'a fresh read'):
            if snapshot == 'a fresh read':
                self.fresh(h)
            self.assertEqual(self.mult(h, *times_h), want_h, snapshot)
            self.assertEqual(self.mult(g, wx + 5, wy + 5, wy + 1799, wy + 1800), [100, 200, 200, 100], snapshot)
        # back much later (the windows left the shared snapshot): the player's own older windows, the same answers
        self.t[0] = wy + 6 * 3600
        bang.gh_reset()
        with self.store.connect() as db:
            for tok in (h, g):
                bang.prepare(db, self.t[0], sid=self.sid(tok))
        self.assertEqual(bang._GH['wins'], {})
        self.assertEqual(self.mult(h, *times_h), want_h)
        self.assertEqual(self.mult(g, wx + 5, wy + 5, wy + 1799, wy + 1800), [100, 200, 200, 100])
        # the snapshot is small: only windows on now (± an hour / three hours), never every member's history
        self.t[0] = wx - 1800
        self.fresh()
        self.assertEqual({k: len(v) for k, v in bang._GH['wins'].items()}, {self.bid: 1})

    def test_joins_a_day_are_capped_softly(self):
        """Joining stays free, at most C.SWITCH_DAY_MAX bangs a Vietnam day (here 3), with a clear message."""
        chiefs = [self.player(name=f'Chủ {i}') for i in range(3)]
        others = [self.found(tok, f'Bang Số {i}') for i, tok in enumerate(chiefs)]
        h = self.player(name='Hà')
        with patch.object(C, 'SWITCH_DAY_MAX', 3):
            for bid in (self.bid, others[0], others[1]):
                self.op(h, 'join', bang=bid)
            msg = self.refused_op(h, 'join', 'switch_cap', bang=others[2])
            self.assertIn('3 bang', msg)
            self.assertEqual(self.mine(h)['bang'], others[1])                      # still where they were
            self.op(h, 'join', bang=others[1])                                     # the same bang: nothing to count
            self.op(chiefs[2], 'set', open=False)                                  # asking is free; approving counts
            self.op(h, 'join', bang=others[2])
            self.assertIn('người này', self.refused_op(chiefs[2], 'approve', 'switch_cap', pid=self.pid(h)))
            self.assertIn('3 bang', self.refused_cmd(h, 'jr_bang_found', 'switch_cap', name='Bang Mới', emoji='🐉', color='do',
                                                    open=True, confirm=True))     # founding counts too: nothing paid
            self.t[0] = bang.day_start(self.t[0]) + 86400 + 60                     # the next Vietnam day
            self.op(chiefs[2], 'approve', pid=self.pid(h))
            self.assertEqual(self.mine(h)['bang'], others[2])

    def test_cancel_freezes_before_the_start(self):
        self.set_level(self.bid, 'den_vang', 1)
        s0 = self.start()
        self.op(self.a, 'gh_set', start=s0)
        g = self.one('SELECT * FROM bang_gh WHERE bang=?', (self.bid,))
        self.t[0] = s0 - 200                                                       # in the last 5 minutes
        self.refused_op(self.a, 'gh_cancel', 'started', id=int(g['id']))

    def test_the_command_binds_its_own_windows(self):
        self.set_level(self.bid, 'den_vang', 1)
        self.t[0] = T0 + 25 * 3600
        s0 = self.start()
        self.op(self.a, 'gh_set', start=s0)
        other = self.player(name='Ngoài')
        self.t[0] = s0 + 5
        seen = {}
        from game.storage import Store
        real = Store._apply

        def spy(store, raw, *a, **k):
            seen.setdefault(k.get('sid'), bang.gold_mult(s0 + 5))
            return real(store, raw, *a, **k)
        bang.gh_reset()
        with patch.object(Store, '_apply', spy):
            self.cmd(self.a, 'jr_seen', ids=['x'])
            self.cmd(other, 'jr_seen', ids=['x'])
        self.assertEqual(seen, {self.sid(self.a): 200, self.sid(other): 100})

    def test_the_locked_path_reads_the_windows_before_its_lock(self):
        """storage._command_locked: prepare runs on a connection of its own, before the save's lock (review fix 19/10)."""
        src = inspect.getsource(__import__('game.storage', fromlist=['Store']).Store._command_locked)
        self.assertLess(src.index('_bang_prepare(pdb'), src.index('db.begin()'))
        self.assertEqual(src.count('_bang_prepare('), 1)

    def test_ticker_line(self):
        self.set_level(self.bid, 'den_vang', 1)
        self.t[0] = T0 + 25 * 3600
        s0 = self.start()
        self.op(self.a, 'gh_set', start=s0)
        self.t[0] = s0 + 30
        bang.gh_reset()
        with patch.object(mr, 'now', lambda: self.t[0]):
            out = mr.news(self.store, 0, self.a)
        self.assertIn('Giờ vàng của bang Rồng Đỏ', out['golden']['text'])
        self.assertEqual(out['golden']['ends'], s0 + 1800)
        self.assertEqual(bang.me_view(self.store, self.a)['mine']['golden']['name'], 'Rồng Đỏ')


class Weekly(Base):
    def test_ranking_and_title(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        x = self.found(a, 'Rồng Đỏ')
        y = self.found(b, 'Hổ Xám')
        self.give(a, 1_000_000)
        self.give(b, 9_000_000)                  # owner 21/10: điểm cống hiến never counts in the ranking
        self.op(b, 'checkin')
        self.set_level(x, 'kho', 2)
        bang._VIEW.clear()
        board = bang.board(self.store)
        # 👑 (owner 21/10): 🐾 Pets (none yet) + 🏗️ Công trình (Kho bang 2) + ⭐ Cấp bang (Đại sảnh 1)
        lv, fac = bang.C.LEVEL_SCORE, bang.C.FAC_SCORE
        self.assertEqual([(r['id'], r['score']) for r in board['top']], [(x, lv + 2 * fac), (y, lv)])
        self.assertEqual([(r['pets'], r['build'], r['level']) for r in board['top']], [(0, 2 * fac, lv), (0, 0, lv)])
        self.assertIsNone(board['crown'])
        with self.store.connect() as db:
            self.assertNotIn('k', bang.tag_of(self.store, db, self.sid(a)))
        self.t[0] += 7 * 86400                                                    # next week: last week's winner is frozen
        bang._VIEW.clear()
        self.assertEqual(bang.crown(self.store), x)
        self.assertEqual(self.one('SELECT bang, score FROM bang_week_win'), dict(bang=x, score=lv + 2 * fac))
        c = self.player(name='Tú')
        self.op(c, 'join', bang=x)
        with self.store.connect() as db:
            self.assertEqual(bang.tag_of(self.store, db, self.sid(c)).get('k'), 1)   # members wear 👑 this week
        self.op(c, 'leave', confirm=True)
        with self.store.connect() as db:
            self.assertIsNone(bang.tag_of(self.store, db, self.sid(c)))           # leaving drops it at once
        self.assertTrue(any(e.get('op') == 'bang_crown' for e in self.sent))
        bang._VIEW.clear()
        self.assertEqual(bang.crown(self.store), x)                               # frozen once
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_week_win')), 1)

    def test_tuong_bonus_and_hidden_excluded(self):
        a = self.player(name='Lan')
        x = self.found(a)
        self.give(a, 1_000_000)
        self.set_level(x, 'tuong', 5)    # +10 %, and 5 more levels
        with self.store.connect() as db:
            self.assertEqual(bang.scores(db, bang.vn_week(self.t[0])), [(x, (bang.C.LEVEL_SCORE + 5 * bang.C.FAC_SCORE) * 110 // 100)])
        bang.admin_act(self.store, 'op', dict(op='hide', id=x))
        with self.store.connect() as db:
            self.assertEqual(bang.scores(db, bang.vn_week(self.t[0])), [])


class Admin(Base):
    def test_hide_and_rename_never_delete(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        x = self.found(a, 'Bang Xấu')
        self.assertEqual([c['id'] for c in bang.search(self.store, None)], [x])
        bang.admin_act(self.store, 'op', dict(op='hide', id=x))
        bang._VIEW.clear()
        self.assertEqual(bang.search(self.store, None), [])
        with self.store.connect() as db:
            self.assertIsNone(bang.tag_of(self.store, db, self.sid(a)))
        with self.assertRaises(bang.BangError):
            bang.page(self.store, self.sid(b), x)
        self.refused_op(b, 'join', 'not_found', bang=x)
        self.assertTrue(bang.page(self.store, self.sid(a))['member'])               # its members still see it
        with self.assertRaises(bang.BangError):
            bang.admin_act(self.store, 'op', dict(op='rename', id=x, name='đụ má'))
        bang.admin_act(self.store, 'op', dict(op='rename', id=x, name='Bang Hiền'))
        bang.admin_act(self.store, 'op', dict(op='show', id=x))
        r = self.one('SELECT name, key, hidden, status FROM bangs WHERE id=?', (x,))
        self.assertEqual(r, dict(name='Bang Hiền', key='banghien', hidden=0, status='active'))
        ch = self.one('SELECT c.title FROM chat_channels c JOIN bangs b ON b.channel=c.id WHERE b.id=?', (x,))
        self.assertEqual(ch['title'], '🐉 Bang Hiền')
        self.assertEqual([v['name'] for v in bang.admin_view(self.store)['bangs']], ['Bang Hiền'])
        self.assertTrue(any(e.get('op') == 'bang' and e.get('bang') == x for e in self.sent))
        self.assertTrue(self.rows("SELECT 1 FROM bang_log WHERE kind='admin'"))

    def test_erasure(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        x = self.found(a)
        self.op(b, 'join', bang=x)
        self.give(a, 1_000_000)
        self.store.delete(a)
        r = self.one('SELECT leader, status, fund FROM bangs WHERE id=?', (x,))
        self.assertEqual((r['leader'], r['status'], r['fund']), (self.sid(b), 'active', 1_000_000))   # handed over, fund kept
        self.assertEqual(self.mine(b)['role'], 'chu')
        self.assertEqual(self.one("SELECT sid FROM bang_fund WHERE kind='give'")['sid'], '')
        self.store.delete(b)
        self.assertEqual(self.one('SELECT status, fund, burned FROM bangs WHERE id=?', (x,)), dict(status='disbanded', fund=0, burned=1_000_000))


class Views(Base):
    def test_get_view_shapes(self):
        a = self.player(name='Lan')
        v = bang.get_view(self.store, a, {})
        self.assertNotIn('mine', v)
        self.assertEqual(v['list'], [])
        self.assertEqual(v['catalogue']['fee'], 5_000_000)
        x = self.found(a)
        v = bang.get_view(self.store, a, {})
        self.assertEqual(v['mine']['bang'], x)
        self.assertEqual(v['page']['me']['role'], 'chu')
        self.assertEqual(v['mine']['color']['hex'], C.COLORS['do'][1])
        b = self.player(name='Minh')
        self.assertEqual([c['name'] for c in bang.get_view(self.store, b, {'q': 'rong'})['list']], ['Rồng Đỏ'])
        self.assertEqual(bang.get_view(self.store, b, {'q': 'hổ'})['list'], [])
        card = bang.get_view(self.store, b, {'id': x})
        self.assertFalse(card['member'])
        self.assertNotIn('fund', card)
        self.assertEqual(bang.get_view(self.store, None, {'list': '1'})['list'][0]['id'], x)


class Compat(unittest.TestCase):
    """Saves with journey.bang validate, migrate and take a command on the release before this one (2.4.60)."""
    RELEASES = {'2.4.60': 'e05bacf5'}
    PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    before=json.dumps(s['journey'].get('bang'),sort_keys=True)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,json.dumps(s['journey'].get('bang'),sort_keys=True),s['journey']['wallet']])
print(json.dumps(out))
'''

    def old_tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-bang-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_previous_release_keeps_the_block(self):
        with patch.object(bang, 'now', lambda: T0):
            a, _ = found(titled(30_000_000))
            a, _ = act(a, 'jr_bang_give', bang='b0123456789', amount=10_000_000, confirm=True)
            b = titled(9_000_000)
            b, _ = act(b, 'jr_bang_give', bang='b0123456789', amount=1000, confirm=True)
        for s in (a, b):
            validate_state(s)
        old = self.old_tree(self.RELEASES['2.4.60'])
        env = {k: v for k, v in dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1').items() if k != 'MNL_CAREERS'}   # another test may leave a career filter behind
        from tests.helpers import as_stored
        out = subprocess.run([sys.executable, '-c', self.PROG], input=json.dumps([as_stored(a), as_stored(b)]), capture_output=True, text=True, cwd=old,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout)
        self.assertEqual([g[0] for g in got], [g[1] for g in got])               # the block untouched
        self.assertEqual(json.loads(got[0][0]), a['journey']['bang'])
        self.assertEqual(got[0][2], a['journey']['wallet'])


if __name__ == '__main__':
    unittest.main()
