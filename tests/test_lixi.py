"""🧧 Lì xì: phát và giật lì xì (game/lixi.py, live/lixi.py; owner 16/10 "cho phép người ta phát lì xì và giật lì xì, tiền
ngẫu nhiên … check kĩ nhé, có cả map cũ và mới nhé").

The split (every envelope ≥ ENV_MIN, the sum exact), the giver's command (validation, wallet then bank, refusals that
pay nothing, the row written with the save), grabbing (first come first served, one per player, never the giver, the
caps against alt accounts, blocks, one per address, exactly once into the wallet, two grabs on the last envelope), the
24 h sweep (once), the views (who got how much, 🏆 Hên nhất), account deletion, saves an older server (2.4.27) still
loads, and the live service's broadcast (everyone, blocked players without the name, the welcome)."""
import copy
import io
import json
import os
import random
import secrets
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import lixi
from game import live_chat
from game import live_effects
from game.engine import GameError, dormant_out, validate_state
from live.app import NOTIFY_CHANNEL
from tests.live_support import HAVE_WS, LiveCase
from tests.test_bank import act, story

ROOT = Path(__file__).resolve().parent.parent
OLD_RELEASE = '04a51030'      # 2.4.27: the rollback floor (2.4.34 is 917f0733)
OLD_AGE = '2026-01-01 00:00:00'


def refused(test, s, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, 'jr_lixi_give', **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


class Split(unittest.TestCase):
    def test_every_packet_adds_up_and_no_envelope_is_too_small(self):
        rng = random.Random(7)
        for _ in range(400):
            n = rng.randint(1, 100)
            total = rng.randint(max(lixi.TOTAL_MIN, n * lixi.ENV_MIN), lixi.TOTAL_MAX)
            left, k, got = total, n, []
            while k:
                a = lixi.split(left, k, rng)
                self.assertGreaterEqual(a, lixi.ENV_MIN)
                self.assertGreaterEqual(left - a, lixi.ENV_MIN * (k - 1))   # the others still get ENV_MIN each
                got.append(a)
                left, k = left - a, k - 1
            self.assertEqual(sum(got), total)
            self.assertEqual(len(got), n)

    def test_the_tightest_packet_and_the_last_envelope(self):
        self.assertEqual(lixi.split(100 * 50, 50), 100)     # exactly ENV_MIN each: no room to draw
        self.assertEqual(lixi.split(12345, 1), 12345)       # the last takes the rest
        for _ in range(200):                                # twice the mean at most
            self.assertLessEqual(lixi.split(100_000, 10), 20_000)

    def test_draws_vary(self):
        self.assertGreater(len({lixi.split(1_000_000, 20) for _ in range(50)}), 10)


class Give(unittest.TestCase):
    """The reducer: validation, the money (wallet then bank), the result command_commit reads."""

    def test_validation_refuses_and_changes_nothing(self):
        s = story(20_000_000)
        refused(self, s, 'bad_total', total=9_999, n=1, confirm=True)
        refused(self, s, 'bad_total', total=10_000_001, n=1, confirm=True)
        refused(self, s, 'bad_total', total=10_000.0, n=1, confirm=True)
        refused(self, s, 'bad_count', total=50_000, n=0, confirm=True)
        refused(self, s, 'bad_count', total=50_000, n=101, confirm=True)
        refused(self, s, 'bad_count', total=50_000, n=True, confirm=True)
        refused(self, s, 'bad_wish', total=50_000, n=5, wish='nope', confirm=True)
        refused(self, s, 'bad_wish', total=50_000, n=5, wish=['an_khang'], confirm=True)
        refused(self, s, 'bad_text', total=50_000, n=5, text='x' * 41, confirm=True)
        refused(self, s, None, total=50_000, n=5)                                 # no confirm
        refused(self, s, None, total=50_000, n=5, confirm=True, extra=1)          # unknown key
        refused(self, story(9_000), 'not_enough', total=10_000, n=5, confirm=True)
        poor = story(50_000)
        poor['journey']['wallet'] = -10
        refused(self, poor, 'not_enough', total=10_000, n=5, confirm=True)       # never with a wallet in debt

    def test_the_smallest_packet_holds_100_envelopes(self):
        self.assertGreaterEqual(lixi.TOTAL_MIN, lixi.N_MAX * lixi.ENV_MIN)      # so bad_split guards a future change only
        s, r = act(story(1_000_000), 'jr_lixi_give', total=10_000, n=100, confirm=True)
        self.assertEqual((r['lixi']['n'], s['journey']['wallet']), (100, 990_000))

    def test_wallet_then_bank_and_the_result(self):
        s = story(30_000)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=20_000)
        cash, bal = s['journey']['wallet'], s['journey']['bank']['balance']
        total = cash + 5_000
        s2, r = act(s, 'jr_lixi_give', total=total, n=10, wish='phat_tai', text='  Lấy hên nha  ', confirm=True)
        self.assertEqual(s2['journey']['wallet'], 0)
        self.assertEqual(s2['journey']['bank']['balance'], bal - 5_000)
        self.assertEqual(r['lixi'], dict(total=total, n=10, wish='phat_tai', text='Lấy hên nha', raw=''))
        self.assertIn('tiền mặt', r['message'])
        self.assertIn('tài khoản', r['message'])
        kinds = {x['kind'] for x in s2['journey']['history']}
        self.assertIn('life', kinds)
        self.assertNotIn('lixi', s2['journey'])                                   # no key in the save
        validate_state(s2)

    def test_custom_line_is_masked_raw_kept(self):
        s = story(100_000)
        _, r = act(s, 'jr_lixi_give', total=10_000, n=5, text='gọi 0912345678 nha', confirm=True)
        self.assertNotIn('0912345678', r['lixi']['text'])
        self.assertIn('0912345678', r['lixi']['raw'])

    def test_story_only(self):
        s = story(100_000)
        s['journey']['story'] = False
        with self.assertRaises(GameError):
            act(s, 'jr_lixi_give', total=10_000, n=5, confirm=True)


class Db(unittest.TestCase):
    """The rows: the packet with the save, grabs under the lock, live_effects paid once, the sweep."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        lixi._VIEW.clear()
        lixi._swept[0] = 0.0
        self.n = 0
        self.sent = []
        real = live_chat.notify
        p = patch.object(live_chat, 'notify', side_effect=lambda db, e: (self.sent.append(e), real(db, e)))
        p.start()
        self.addCleanup(p.stop)

    def player(self, name='Lan', wallet=2_000_000, day=20, account=True, age=OLD_AGE):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
            s['journey']['life_day'] = day
        mr._mutate(self.store, {sid: fn})
        if not account:
            return token
        login = secrets.token_hex(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?, ?, ?, ?, ?)',
                       ('u' + secrets.token_hex(5), name, 'x', sid, age))
            db.execute("INSERT INTO logins(token, sid, csrf) VALUES(?, ?, 'c')", (self.store.digest(login), sid))
        return login

    def earlier(self, token):
        """The giver's packets moved GAP seconds back (the same Vietnam day's count)."""
        with self.store.connect() as db:
            db.execute('UPDATE lixi_packets SET at=at-? WHERE sid=?', (lixi.GAP + 1, self.store.key(token)))

    def wallet(self, token):
        return self.store.read(token)[0]['journey']['wallet']

    def give(self, token, total=100_000, n=10, **p):
        self.n += 1
        return self.store.command(token, f'lx-{self.n:08d}', self.store.read(token)[1], None, 'jr_lixi_give',
                                  dict(total=total, n=n, confirm=True, **p))

    def packet(self, pk=None):
        with self.store.connect() as db:
            if pk:
                return dict(db.execute('SELECT * FROM lixi_packets WHERE id=?', (pk,)).fetchone())
            return dict(db.execute('SELECT * FROM lixi_packets ORDER BY at DESC LIMIT 1').fetchone())

    def grab(self, token, pk, ip='', rng=None):
        state = self.store.read(token)[0]
        out = lixi.grab(self.store, token, {'id': pk}, state, ip, rng=rng)
        live_effects.on_load(self.store, token, self.store.read(token)[0])
        return out

    def refused(self, code, token, pk, ip=''):
        with self.assertRaises(lixi.LixiError) as cm:
            self.grab(token, pk, ip)
        self.assertEqual(cm.exception.code, code, str(cm.exception))

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    # ---- giving
    def test_give_writes_the_row_with_the_save_and_tells_the_street(self):
        a = self.player('Lan Mây', wallet=3_000_000)
        r = self.give(a, total=1_000_000, n=20, wish='an_khang')
        self.assertIn('20 bao', r['result']['message'])
        self.assertEqual(self.wallet(a), 2_000_000)
        p = self.packet()
        self.assertEqual((p['total'], p['n'], p['left_n'], p['left_xu'], p['status'], p['name']), (1_000_000, 20, 20, 1_000_000, 'open', 'Lan Mây'))
        self.assertAlmostEqual(p['expires'] - p['at'], lixi.HOURS * 3600, delta=1)
        ev = [e for e in self.sent if e.get('op') == 'lixi']
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]['id'], ev[0]['name'], ev[0]['wish'], ev[0]['n'], ev[0]['left']), (p['id'], 'Lan Mây', 'An khang thịnh vượng', 20, 20))
        self.assertNotIn(self.store.key(a), json.dumps(ev[0]))                    # never a sid
        news = self.rows("SELECT text FROM news WHERE kind='lixi'")
        self.assertEqual(len(news), 1)                                            # a big packet: the ticker
        self.assertIn('Lan Mây', news[0]['text'])
        validate_state(self.store.read(a)[0])

    def test_refusals_in_the_transaction_pay_nothing(self):
        guest = self.player('Khách', account=False)
        with self.assertRaises(GameError) as cm:
            self.give(guest)
        self.assertEqual(cm.exception.code, 'account_required')
        self.assertEqual(self.wallet(guest), 2_000_000)
        a = self.player()
        self.give(a, total=10_000, n=1)
        with self.assertRaises(GameError) as cm:                                  # GAP seconds between two packets
            self.give(a, total=10_000, n=1)
        self.assertEqual(cm.exception.code, 'busy')
        self.assertEqual(self.wallet(a), 2_000_000 - 10_000)
        with patch.object(lixi, 'DAY_MAX', 10):                                  # a cap still works when it is set
            for _ in range(10 - 1):
                self.earlier(a)
                self.give(a, total=10_000, n=1)
            self.earlier(a)
            with self.assertRaises(GameError) as cm:                              # DAY_MAX a Vietnam day
                self.give(a, total=10_000, n=1)
            self.assertEqual(cm.exception.code, 'limit')
        self.assertEqual(self.wallet(a), 2_000_000 - 10 * 10_000)

    def test_no_cap_on_giving_by_default(self):
        """Owner 17/10: "mỗi người phát không giới hạn luôn, cho mọi người phát mà"."""
        self.assertIsNone(lixi.DAY_MAX)
        self.assertIsNone(lixi.OPEN_MAX)
        a = self.player(wallet=5_000_000)
        for _ in range(15):
            self.earlier(a)
            self.give(a, total=10_000, n=1)
        self.assertEqual(self.wallet(a), 5_000_000 - 15 * 10_000)
        self.assertEqual(len(self.rows("SELECT id FROM lixi_packets WHERE status='open'")), 15)

    def test_the_street_holds_at_most_open_max(self):
        a = self.player()
        with patch.object(lixi, 'OPEN_MAX', 1):
            self.give(a, total=10_000, n=2)
            b = self.player('Minh')
            with self.assertRaises(GameError) as cm:
                self.give(b, total=10_000, n=2)
            self.assertEqual(cm.exception.code, 'busy')
            self.assertEqual(self.wallet(b), 2_000_000)

    # ---- grabbing
    def test_first_come_first_served_sums_exactly_paid_once(self):
        a = self.player('Lan')
        self.give(a, total=50_000, n=5)
        pk = self.packet()['id']
        takers = [self.player(f'P{i}', wallet=0) for i in range(6)]
        got = []
        for i, t in enumerate(takers[:5]):
            r = self.grab(t, pk, ip=f'10.0.0.{i}')
            got.append(r['amount'])
            self.assertEqual(self.wallet(t), r['amount'])                        # into the wallet at once
        self.assertEqual(sum(got), 50_000)
        self.assertTrue(all(x >= lixi.ENV_MIN for x in got))
        p = self.packet(pk)
        self.assertEqual((p['left_n'], p['left_xu'], p['status']), (0, 0, 'done'))
        self.refused('empty', takers[5], pk)
        # a second tap (another tab): the same envelope, nothing paid again
        again = self.grab(takers[0], pk)
        self.assertTrue(again['again'])
        self.assertEqual(again['amount'], got[0])
        self.assertEqual(self.wallet(takers[0]), got[0])
        # the inbox row is paid once even when the page asks again
        live_effects.on_load(self.store, takers[0], self.store.read(takers[0])[0])
        self.assertEqual(self.wallet(takers[0]), got[0])
        rows = self.rows("SELECT status FROM live_effects WHERE kind='lixi'")
        self.assertEqual({r['status'] for r in rows}, {'applied'})
        hist = self.store.read(takers[1])[0]['journey']['history'][-1]
        self.assertEqual((hist['kind'], hist['amount']), ('life', got[1]))
        self.assertIn('Lan', hist['label'])
        ups = [e for e in self.sent if e.get('op') == 'lixi_upd']
        self.assertEqual([e['left'] for e in ups], [4, 3, 2, 1, 0])
        self.assertTrue(ups[-1]['done'])

    def test_who_may_grab(self):
        a = self.player('Lan')
        self.give(a, total=100_000, n=20)
        pk = self.packet()['id']
        self.refused('own', a, pk)                                                # never the giver
        guest = self.player('Khách', account=False)
        self.refused('account_required', guest, pk)
        young = self.player('Mới', age=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 3600)))
        self.refused('too_new', young, pk)                                        # account ACCOUNT_DAYS old
        fresh = self.player('Non', day=lixi.LIFE_DAYS - 1)
        self.refused('too_new', fresh, pk)                                        # life day LIFE_DAYS
        blocked = self.player('Chặn')
        with self.store.connect() as db:                                          # chat block, either way
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (lixi.pid_of(self.store.key(a)), lixi.pid_of(self.store.key(blocked)), time.time()))
        self.refused('blocked', blocked, pk)
        wed = self.player('Hôn nhân')
        with self.store.connect() as db:                                          # Hôn nhân block
            db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?, ?, ?)', (self.store.key(wed), self.store.key(a), time.time()))
        self.refused('blocked', wed, pk)
        self.refused('bad_lixi', self.player('X'), 'lx' + 'z' * 14)
        self.refused('not_found', self.player('Y'), 'lx' + '0' * 14)
        self.assertEqual(lixi.IP_MAX, 5)
        ok = self.player('Hoa')
        self.grab(ok, pk, ip='1.2.3.4')
        for i in range(lixi.IP_MAX - 1):                                          # #426: friends on one Wi-Fi all grab
            self.grab(self.player(f'Bạn {i}'), pk, ip='1.2.3.4')
        self.refused('same_ip', self.player('Cùng mạng'), pk, ip='1.2.3.4')        # IP_MAX envelopes per address per packet
        self.grab(self.player('Khác mạng'), pk, ip='1.2.3.5')
        self.assertEqual(self.packet(pk)['left_n'], 20 - lixi.IP_MAX - 1)
        with patch.object(lixi, 'IP_MAX', 0):                                     # 0: no cap at all
            self.grab(self.player('Không giới hạn'), pk, ip='1.2.3.4')
        self.assertIn(lixi.ip_tag('1.2.3.4'), {r['ip'] for r in self.rows('SELECT ip FROM lixi_grabs')})
        self.assertNotIn('1.2.3.4', json.dumps(self.rows('SELECT * FROM lixi_grabs')))

    def test_caps_per_grabber_and_per_giver(self):
        me = self.player('Tôi', wallet=0)
        givers = [self.player(f'G{i}', wallet=10_000_000) for i in range(3)]
        # one giver's packets: PAIR_DAY a day (when set; no cap by default since 17/10)
        with patch.object(lixi, 'PAIR_DAY', 3):
            for k in range(3 + 1):
                self.earlier(givers[0])
                self.give(givers[0], total=10_000, n=2)
                pk = self.packet()['id']
                if k < 3:
                    self.grab(me, pk)
                else:
                    self.refused('limit', me, pk)
        # the xu cap: an envelope is cut to what is left of GRAB_DAY_XU; the cut part goes back to the giver
        with patch.object(lixi, 'GRAB_DAY_XU', 30_000):
            have = sum(r['amount'] for r in self.rows('SELECT amount FROM lixi_grabs WHERE sid=?', (self.store.key(me),)))
            self.give(givers[1], total=200_000, n=1)
            pk = self.packet()['id']
            r = self.grab(me, pk)
            self.assertEqual(r['amount'], 30_000 - have)
            p = self.packet(pk)
            self.assertEqual((p['status'], p['left_n'], p['back']), ('done', 0, 200_000 - r['amount']))
            before = self.wallet(givers[1])
            live_effects.on_load(self.store, givers[1], self.store.read(givers[1])[0])
            self.assertEqual(self.wallet(givers[1]), before + 200_000 - r['amount'])   # the rest is home
            self.give(givers[2], total=10_000, n=2)
            self.refused('limit', me, self.packet()['id'])                     # nothing left of today's xu
        # the count cap
        with patch.object(lixi, 'GRAB_DAY', 4):
            self.earlier(givers[2])
            self.give(givers[2], total=10_000, n=2)
            self.refused('limit', me, self.packet()['id'])
        mine = self.rows('SELECT COUNT(*) AS n, SUM(amount) AS xu FROM lixi_grabs WHERE sid=?', (self.store.key(me),))[0]
        self.assertEqual(self.wallet(me), mine['xu'])

    def test_grab_without_caps_by_default(self):
        """Owner 17/10: "giật lì xì mỗi người không giới hạn nhé, giật thoải mái"."""
        self.assertEqual((lixi.GRAB_DAY, lixi.GRAB_DAY_XU, lixi.PAIR_DAY), (None, None, None))
        me = self.player('Tôi', wallet=0)
        g = self.player('Giàu', wallet=10_000_000)
        got = 0
        for _ in range(25):                                                       # more than the old 20 a day and 3 a giver
            self.earlier(g)
            self.give(g, total=200_000, n=1)                                      # one envelope: the whole 200k, over the old 300k a day
            got += self.grab(me, self.packet()['id'])['amount']
        self.assertEqual(got, 25 * 200_000)
        self.assertEqual(self.wallet(me), got)
        v = lixi.view(self.store, me)
        self.assertEqual(v['me']['n'], 25)
        self.assertEqual(v['caps'], dict(day=None, xu=None, pair=None))

    def test_two_grabs_on_the_last_envelope(self):
        a = self.player('Lan')
        self.give(a, total=10_000, n=2)
        pk = self.packet()['id']
        self.grab(self.player('Một'), pk)
        racers = [self.player(f'R{i}', wallet=0) for i in range(4)]
        states = {t: self.store.read(t)[0] for t in racers}
        out, errs, go = {}, {}, threading.Barrier(len(racers))

        def run(t, i):
            go.wait()
            try:
                out[t] = lixi.grab(self.store, t, {'id': pk}, states[t], f'9.9.9.{i}')
            except lixi.LixiError as e:
                errs[t] = e.code
        threads = [threading.Thread(target=run, args=(t, i)) for i, t in enumerate(racers)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(30)
        self.assertEqual(len(out), 1, (out, errs))
        self.assertEqual(set(errs.values()), {'empty'})
        p = self.packet(pk)
        self.assertEqual((p['left_n'], p['left_xu'], p['status']), (0, 0, 'done'))
        self.assertEqual(sum(r['amount'] for r in self.rows('SELECT amount FROM lixi_grabs WHERE packet=?', (pk,))), 10_000)
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE kind='lixi'")), 2)

    def test_sweep_gives_the_rest_back_once(self):
        a = self.player('Lan', wallet=500_000)
        self.give(a, total=100_000, n=10)
        pk = self.packet()['id']
        g = self.grab(self.player('Hoa'), pk)
        later = time.time() + lixi.HOURS * 3600 + 5
        self.assertEqual(lixi.sweep(self.store, t=time.time(), force=True), 0)   # not yet
        self.assertEqual(lixi.sweep(self.store, t=later, force=True), 1)
        self.assertEqual(lixi.sweep(self.store, t=later, force=True), 0)          # idempotent
        self.assertIsNone(lixi.expire_one(self.store, pk, later))
        p = self.packet(pk)
        self.assertEqual((p['status'], p['back']), ('expired', 100_000 - g['amount']))
        back = self.rows("SELECT * FROM live_effects WHERE id=?", (f'lixi:{pk}:back',))
        self.assertEqual(len(back), 1)
        live_effects.on_load(self.store, a, self.store.read(a)[0])
        live_effects.on_load(self.store, a, self.store.read(a)[0])
        self.assertEqual(self.wallet(a), 500_000 - 100_000 + 100_000 - g['amount'])
        self.assertIn('trả lại', self.store.read(a)[0]['journey']['history'][-1]['label'])
        with patch.object(lixi, 'now', lambda: later):                           # an expired packet refuses grabs
            self.refused('empty', self.player('Muộn'), pk)

    def test_views_and_luckiest(self):
        a = self.player('Lan')
        self.give(a, total=30_000, n=3, wish='van_su')
        pk = self.packet()['id']
        t1, t2, t3 = self.player('Hoa'), self.player('Minh'), self.player('Tú')
        seq = iter([500, 20_000])

        class R:
            def randint(self, lo, hi):
                return next(seq)
        self.grab(t1, pk, rng=R())
        v = lixi.view(self.store, t1, pk)
        d = v['packet']
        self.assertEqual([g['amount'] for g in d['grabs']], [500])
        self.assertTrue(d['grabs'][0]['me'])
        self.assertNotIn('best', d['grabs'][0])                                   # not finished: no 🏆 yet
        self.assertEqual(v['packets'][0]['got'], 500)
        self.assertEqual(v['packets'][0]['wish'], 'Vạn sự như ý')
        self.assertNotIn('pid', v['packets'][0])
        self.assertEqual(v['me']['n'], 1)
        self.grab(t2, pk, rng=R())
        self.grab(t3, pk)
        lixi._VIEW.clear()
        d = lixi.view(self.store, a, pk)['packet']
        self.assertTrue(d['own'])
        self.assertEqual([g['amount'] for g in d['grabs']], [500, 20_000, 9_500])
        self.assertEqual([bool(g.get('best')) for g in d['grabs']], [False, True, False])   # 🏆 Hên nhất
        self.assertEqual(d['taken'], 30_000)
        # a blocked viewer sees neither the giver's name nor the wish
        x = self.player('Ghét')
        with self.store.connect() as db:
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (lixi.pid_of(self.store.key(x)), lixi.pid_of(self.store.key(a)), time.time()))
        p = lixi.view(self.store, x)['packets'][0]
        self.assertEqual((p['name'], p['wish'], p.get('no')), ('', '', True))
        adm = lixi.admin_view(self.store)
        self.assertEqual(adm['packets'][0]['id'], pk)
        self.assertEqual(adm['today']['xu'], 30_000)

    def test_forget(self):
        a = self.player('Lan')
        self.give(a, total=20_000, n=4)
        pk = self.packet()['id']
        t = self.player('Hoa')
        self.grab(t, pk)
        lixi.forget(self.store, t)
        lixi.forget(self.store, a)
        p = self.packet(pk)
        self.assertEqual((p['sid'], p['status'], p['name']), ('', 'gone', lixi.GONE))
        g = self.rows('SELECT * FROM lixi_grabs WHERE packet=?', (pk,))[0]
        self.assertEqual((g['name'], g['ip'], g['giver']), (lixi.GONE, '', ''))
        self.assertNotEqual(g['sid'], self.store.key(t))
        self.refused('empty', self.player('Muộn'), pk)
        self.assertEqual(lixi.sweep(self.store, t=time.time() + 2 * 86400, force=True), 0)   # nothing to send back to a gone save


class OldServer(unittest.TestCase):
    """2.4.27 (the rollback floor) loads every save this feature writes and leaves 'lixi' rows alone."""

    def old_tree(self):
        if os.environ.get('MNL_LIXI_OLD_TREE'):
            return Path(os.environ['MNL_LIXI_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix='mnl-2427-')
        try:
            data = subprocess.run(['git', 'archive', OLD_RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {OLD_RELEASE} (MNL_LIXI_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_saves_validate_on_2_4_27(self):
        s = story(20_000_000)
        s, _ = act(s, 'jr_bk_open')
        s['journey']['wallet'] -= 15_000_000
        s['journey']['bank']['balance'] += 15_000_000                            # a rich player's account
        gave, _ = act(s, 'jr_lixi_give', total=10_000_000, n=1, wish='lay_hen', confirm=True)   # the biggest packet
        got, _ = live_effects.apply(copy.deepcopy(story(0)), dict(id='lixi:lx00000000000000:' + '0' * 16, kind='lixi', amount=10_000_000,
                                                                data=dict(pk='lx00000000000000', what='grab', name='Lan', src='lixi')))
        back, _ = live_effects.apply(copy.deepcopy(gave), dict(id='lixi:lx00000000000000:back', kind='lixi', amount=5_000,
                                                             data=dict(pk='lx00000000000000', what='back', src='lixi')))
        for x in (gave, got, back):
            validate_state(x)
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,wake;from game import live_effects as fx;'
                'out=[]\nfor s in json.load(sys.stdin):\n wake(s);validate_state(s);s=migrate_state(s);validate_state(s);'
                'out.append([s["journey"]["wallet"],len(s["journey"].get("live_fx",[]))])\n'
                'print(json.dumps(dict(out=out,pays="lixi" in fx.PAYS)))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        r = subprocess.run([sys.executable, '-c', prog], input=json.dumps([dormant_out(x) for x in (gave, got, back)]), capture_output=True, text=True, cwd=old,
                           env=env, encoding='utf-8', timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout)
        self.assertFalse(res['pays'])                                             # an older build leaves the rows pending
        self.assertEqual([w for w, _ in res['out']], [gave['journey']['wallet'], 10_000_000, back['journey']['wallet']])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Live(LiveCase):
    """live/lixi.py: every open page, blocks, the welcome, updates, bad events."""

    def notify(self, event):
        with self.store.connect() as db:
            db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event)))

    def event(self, sid, pk='lx0123456789abcd', **kw):
        t = time.time()
        return dict(dict(op='lixi', id=pk, pid=self.pid(sid), name='Lan', n=20, left=20, total=1_000_000, wish='Vạn sự như ý',
                         at=t, exp=t + 86400), **kw)

    async def test_everyone_gets_the_packet_blocked_players_without_the_name(self):
        (ta, sa), (tb, _sb), (tc, sc) = self.account('Lan'), self.account('Minh'), self.account('Hoa')
        with self.store.connect() as db:   # Hoa blocked Lan
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (self.pid(sc), self.pid(sa), time.time()))
        a, b, c = await self.connect(ta), await self.connect(tb), await self.connect(tc)
        self.assertNotIn('lx', b.welcome)
        self.notify(self.event(sa))
        fa, fb, fc = await a.expect('lixi'), await b.expect('lixi'), await c.expect('lixi')
        self.assertEqual((fb['id'], fb['name'], fb['wish'], fb['n'], fb['left'], fb['total']), ('lx0123456789abcd', 'Lan', 'Vạn sự như ý', 20, 20, 1_000_000))
        self.assertEqual(fa['name'], 'Lan')
        self.assertEqual((fc['name'], fc['wish'], fc['no']), ('', '', True))
        for f in (fa, fb, fc):
            self.assertNotIn(self.pid(sa), json.dumps(f))
            self.assertNotIn(sa, json.dumps(f))
            self.assertLess(f['ago'], 5)
        self.notify(self.event(sa))                                              # a repeated NOTIFY is dropped
        await b.nothing('lixi', wait=.2)
        late = await self.connect(tb)                                            # the welcome carries the open packets
        self.assertEqual([p['id'] for p in late.welcome['lx']], ['lx0123456789abcd'])
        self.assertEqual((await self.connect(tc)).welcome['lx'][0]['name'], '')
        self.notify(dict(op='lixi_upd', id='lx0123456789abcd', left=19, done=False))
        u = await b.expect('lixi_upd')
        self.assertEqual((u['left'], u['done']), (19, False))
        self.assertEqual((await self.connect(tb)).welcome['lx'][0]['left'], 19)
        self.notify(dict(op='lixi_upd', id='lx0123456789abcd', left=0, done=True))
        self.assertTrue((await b.expect('lixi_upd'))['done'])
        self.assertNotIn('lx', (await self.connect(tb)).welcome)                 # finished: no longer in the welcome

    async def test_bad_events_are_dropped(self):
        (tb, _sb), (_ta, sa) = self.account('Minh'), self.account('Lan')
        b = await self.connect(tb)
        for bad in (dict(id='nope'), dict(n=0), dict(n=101), dict(total='1'), dict(at=None), dict(left=-1)):
            self.notify(self.event(sa, pk='lx' + secrets.token_hex(7), **bad))
        self.notify(dict(op='lixi_upd', id='bad', left=1))
        await b.nothing('lixi', wait=.2)
        await b.nothing('lixi_upd', wait=.1)
        self.notify(self.event(sa, pk='lx' + secrets.token_hex(7), name='x' * 80 + '‮', wish='y' * 90, pid='nope'))
        f = await b.expect('lixi')
        self.assertEqual((len(f['name']), len(f['wish'])), (24, 48))


class Client(unittest.TestCase):
    """public/js/v4/lixi.js and lixi-cards.js with a tiny fake DOM (tests/lixi_ui.mjs)."""

    def test_client(self):
        import shutil
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, '--test', str(ROOT / 'tests' / 'lixi_ui.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout[-4000:] + out.stderr[-2000:])

    def test_both_interfaces_have_an_entry(self):
        app = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
        self.assertIn("m.live.on('lixi',", app)
        self.assertIn("items.push(['lixi','gift','Lì xì'])", app)
        iso = (ROOT / 'public/js/isometric/town-utilities.js').read_text(encoding='utf-8')
        self.assertIn("['lixi','gift','🧧','Lì xì']", iso)
        chat = (ROOT / 'public/js/v4/chat.js').read_text(encoding='utf-8')
        self.assertIn("from './lixi-cards.js'", chat)
        from game import journey
        self.assertEqual(journey.content()['lixi']['wishes'][0]['id'], lixi.WISHES[0][0])


if __name__ == '__main__':
    unittest.main()
