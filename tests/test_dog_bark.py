"""🐕 Kéo co chó sủa (game/dog_bark.py): the loudness clamps, the rope, the house dog's long-run odds, the pair limit,
and on real PostgreSQL the escrow (the command and its ticket, refused as a whole), the payout paid exactly once, a
draw's and a cancel's refund, the daily caps, the win-streak cool-down, the stale-ticket housekeeping and no save key."""
import random
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import dog_bark as G
from game.engine import GameError, validate_state
from tests.pg_support import pg_only
from tests.test_bank import act, story


class Voice(unittest.TestCase):
    def test_clamps_and_rejects_non_numbers(self):
        v = G.Voice()
        self.assertEqual(v.add([-5, 150, 'x', None, float('nan'), 50], 10.0), 3)
        self.assertEqual(v.add([float('inf'), True, [1], {'v': 9}], 10.0), 0)   # bool is no number
        self.assertEqual([x for _, x in v.s], [0.0, 100.0, 50.0])
        self.assertAlmostEqual(v.level(10.2), 50.0)
        self.assertEqual(v.level(11.0), 0.0)                 # older than WINDOW: silence
        self.assertEqual(v.add('loud', 12.0), 0)             # not a list

    def test_rate_and_batch_caps(self):
        v = G.Voice()
        self.assertEqual(v.add([60] * 20, 1.0), G.BATCH_MAX)  # one frame: BATCH_MAX at most
        for i in range(10):
            v.add([61, 62, 63, 64, 65, 66], 1.0 + i * 0.01)
        self.assertEqual(len([1 for t, _ in v.s if t < 2.0]), G.RATE_MAX)   # one second: RATE_MAX at most
        self.assertGreater(v.add([70], 2.5), 0)              # the next second takes again

    def test_flat_run_is_not_a_voice(self):
        v = G.Voice()
        t = 0.0
        for i in range(G.FLAT_RUN + 5):
            t += 0.07
            v.add([100], t)
        self.assertEqual(v.s[-1][1], 0.0)
        self.assertEqual(v.s[0][1], 100.0)


class RopeAndDog(unittest.TestCase):
    def test_rope_ends_time_and_draw(self):
        r = G.Rope(5)
        out = None
        while out is None:
            out = r.step(100, 0)
        self.assertEqual((out, r.x), ('a', G.END))
        self.assertLess(r.t, 2.5)                            # a full lead crosses in 2 s
        r = G.Rope(1)
        while (out := r.step(40, 40)) is None:
            pass
        self.assertEqual(out, 'draw')                        # dead centre at the limit
        r = G.Rope(1)
        while (out := r.step(30, 40)) is None:
            pass
        self.assertEqual(out, 'b')                           # on b's half at the limit

    def test_house_dog_long_run_odds_about_half(self):
        profiles = {'steady': lambda t, r: 60, 'noisy': lambda t, r: r.uniform(30, 90),
                    'barks': lambda t, r: (85 if (t % 0.6) < 0.35 else 25) + r.uniform(-8, 8), 'max': lambda t, r: 100}
        for name, f in profiles.items():
            rng = random.Random(20261010)
            n = 3000
            res = [G.simulate(rng, f) for _ in range(n)]
            won = res.count('a') / n
            self.assertTrue(0.45 <= won <= 0.55, (name, won))
            self.assertLess(res.count('draw') / n, 0.03)

    def test_a_quiet_player_loses(self):
        rng = random.Random(1)
        self.assertEqual({G.simulate(rng, lambda t, r: 0) for _ in range(200)}, {'b'})
        lazy = [G.simulate(rng, lambda t, r: 18) for _ in range(500)]
        self.assertLess(lazy.count('a') / 500, 0.3)          # a lazy whisper mostly loses

    def test_house_dog_varies_and_is_labelled(self):
        rng = random.Random(3)
        dogs = [G.HouseDog(rng) for _ in range(300)]
        self.assertGreater(len({d.name for d in dogs}), 40)
        self.assertGreater(len({d.breed[0] for d in dogs}), 8)
        self.assertGreater(len({round(d.base, 2) for d in dogs}), 20)
        v = dogs[0].view()
        self.assertTrue(v['house'])
        self.assertEqual(v['tag'], 'Chó nhà Mây')
        self.assertNotIn('pid', v)
        for _ in range(100):                                 # never the same name twice in a row
            self.assertNotEqual(G.HouseDog(rng, avoid=('Mực',)).name, 'Mực')
        d = G.HouseDog(random.Random(5))
        seen = {d.state for _ in range(450) if d.pull(60) >= 0}
        self.assertTrue({'burst', 'pause'} <= seen)          # a rhythm, not a line

    def test_dog_pull_can_pass_a_maxed_player(self):
        d = G.HouseDog(random.Random(9))
        self.assertGreater(max(d.pull(100) for _ in range(450)), 100)


class Pairs(unittest.TestCase):
    def test_three_in_a_row_then_someone_else(self):
        p = G.PairBook()
        for i in range(3):
            self.assertTrue(p.ok('a', 'b', 100 + i))
            p.played('a', 'b', 100 + i)
        self.assertFalse(p.ok('b', 'a', 110))
        p.played('a', None, 111)                             # the house dog resets nothing
        self.assertFalse(p.ok('a', 'b', 112))
        p.played('a', 'c', 113)                              # a played someone else, b not yet
        self.assertFalse(p.ok('a', 'b', 114))
        p.played('b', 'd', 115)                              # both have: the pair starts over
        self.assertTrue(p.ok('a', 'b', 116))
        self.assertEqual(p.count('a', 'b', 116), 0)

    def test_cool_down_and_bound(self):
        p = G.PairBook(cap=5)
        for i in range(3):
            p.played('a', 'b', 0)
        self.assertFalse(p.ok('a', 'b', G.PAIR_COOL - 1))
        self.assertTrue(p.ok('a', 'b', G.PAIR_COOL))
        for i in range(20):
            p.played(f'x{i}', f'y{i}', 1)
        self.assertLessEqual(len(p.d), 5)

    def test_ip_hash_salted(self):
        self.assertNotEqual(G.ip_hash(b'1', '1.2.3.4'), G.ip_hash(b'2', '1.2.3.4'))
        self.assertEqual(G.ip_hash(b'1', '1.2.3.4'), G.ip_hash(b'1', '1.2.3.4'))
        self.assertNotIn('1.2.3.4', G.ip_hash(b'1', '1.2.3.4'))


class Rules(unittest.TestCase):
    def test_pot_and_caps(self):
        self.assertEqual(G.pot(100), 200)                    # FEE_PCT 0: the system pays both stakes
        self.assertEqual(G.dog_room(dict(dog_n=0, dog_net=0)), G.DOG_WIN_DAY)
        self.assertEqual(G.dog_room(dict(dog_n=0, dog_net=4_000)), 1_000)
        self.assertEqual(G.dog_room(dict(dog_n=0, dog_net=-9_000)), G.DOG_WIN_DAY)
        self.assertEqual(G.dog_room(dict(dog_n=G.DOG_DAY, dog_net=0)), 0)
        rows = [dict(result='win', ended=1000.0)] * 4
        self.assertEqual(G.cool_left(rows, 1000.0), G.COOL_S)
        self.assertEqual(G.cool_left(rows, 1000.0 + G.COOL_S), 0)
        self.assertEqual(G.cool_left([dict(result='lose', ended=1000.0)] + rows[:3], 1000.0), 0)

    def test_command_takes_the_stake_from_the_wallet_only(self):
        s = story(1000)
        s2, r = act(s, 'jr_bark_join', stake=300)
        self.assertEqual(s2['journey']['wallet'], 700)
        self.assertRegex(r['bark']['ticket'], G.TICKET_RE)
        self.assertNotIn('bark', s2['journey'])              # no save key
        validate_state(s2)
        for bad, code in ((99, 'bark_stake'), (1001, 'not_enough'), (G.STAKE_MAX + 1, 'bark_stake'), ('100', 'bark_stake')):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_bark_join', stake=bad)
            self.assertEqual(e.exception.code, code, bad)
        with self.assertRaises(GameError):
            act(s, 'jr_bark_join', stake=200, extra=1)
        with patch.dict('os.environ', LIVE_DOG_BARK='0'):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_bark_join', stake=200)
            self.assertEqual(e.exception.code, 'bark_off')


@pg_only
class Database(unittest.TestCase):
    """The ticket, the payout and the refunds through the real command path (game/storage.py) on PostgreSQL."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        self.n = 0
        G._KING.clear()

    def player(self, wallet=10_000, name='Lan', year=2000, account=True):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {sid: fn})
        with self.store.connect() as db:
            if account:
                db.execute("INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?,?,?,?,'2026-01-01 00:00:00')",
                           (f'u{sid[:10]}', name, 'x', sid))
                db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'c' * 48))
            if year:
                db.execute('INSERT INTO account_birth(sid, year, at) VALUES(?,?,?)', (sid, year, 1.0))
        return token

    def state(self, token):
        return self.store.read(token)[0]

    def wallet(self, token):
        return self.state(token)['journey']['wallet']

    def join(self, token, stake):
        self.n += 1
        return self.store.command(token, f'bark-{self.n:08d}', self.store.read(token)[1], None, 'jr_bark_join', dict(stake=stake))

    def tickets(self, token):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM bark_tickets WHERE sid=? ORDER BY created', (self.store.key(token),)).fetchall()]

    def fx(self, token):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT id, amount, status FROM live_effects WHERE sid=? AND kind='bark' ORDER BY id",
                                                (self.store.key(token),)).fetchall()]

    def pay(self, token):
        from game import live_effects
        return live_effects.on_load(self.store, token, self.state(token))

    def settle(self, token, result, pay, prev='play'):
        """What live/dog_bark.py _settle writes for one side (the guarded UPDATE and its one payout row)."""
        import json
        t = time.time()
        r = self.tickets(token)[-1]

        def run(db):
            n = db.execute("UPDATE bark_tickets SET status='done', result=?, pay=?, ended=? WHERE id=? AND status=?",
                           (result, pay, t, r['id'], prev)).rowcount
            if n == 1 and pay:
                db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
                           (f'bark:{r["id"]}', r['sid'], 'bark', pay,
                            json.dumps(dict(ticket=r['id'], what='win' if result == 'win' else 'draw', src='bark')), t))
            return n
        return self.store.transaction(run)

    def start(self, token, opp='pvp'):
        with self.store.connect() as db:
            db.execute("UPDATE bark_tickets SET status=?, opp=?, started=? WHERE sid=? AND status='wait'",
                       ('dog' if opp == 'dog' else 'play', opp, time.time(), self.store.key(token)))

    # ------------------------------------------------------------------ escrow and settlement
    def test_join_escrow_win_paid_exactly_once(self):
        a = self.player()
        r = self.join(a, 1_000)
        self.assertEqual(self.wallet(a), 9_000)
        t = self.tickets(a)
        self.assertEqual([(x['status'], x['stake'], x['id']) for x in t], [('wait', 1_000, r['result']['bark']['ticket'])])
        with self.assertRaises(GameError) as e:              # one open ticket at a time: the second stake never leaves
            self.join(a, 500)
        self.assertEqual(e.exception.code, 'bark_open')
        self.assertEqual(self.wallet(a), 9_000)
        self.start(a)
        self.assertEqual(self.settle(a, 'win', 2_000), 1)
        self.assertEqual(self.settle(a, 'win', 2_000), 0)    # a second settlement finds nothing to do
        self.assertTrue(self.pay(a))
        self.assertFalse(self.pay(a))                        # paid once, whatever the retries
        self.assertEqual(self.wallet(a), 11_000)
        self.assertEqual([x['status'] for x in self.fx(a)], ['applied'])
        with self.store.connect() as db:                     # as if the row never flipped (a crash): the receipt replays
            db.execute("UPDATE live_effects SET status='pending' WHERE kind='bark'")
        self.pay(a)
        self.assertEqual(self.wallet(a), 11_000)
        h = [x for x in self.state(a)['journey']['history'] if 'Kéo co' in str(x.get('label'))]
        self.assertEqual([x['amount'] for x in h], [-1_000, 2_000])

    def test_loss_and_draw(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        self.join(a, 500)
        self.join(b, 500)
        self.start(a)
        self.start(b)
        self.settle(a, 'lose', 0)
        self.settle(b, 'win', 1_000)
        self.pay(a)
        self.pay(b)
        self.assertEqual((self.wallet(a), self.wallet(b)), (9_500, 10_500))   # the money only moved between them
        self.join(a, 700)
        self.start(a, 'dog')
        self.settle(a, 'draw', 700, prev='dog')
        self.assertTrue(self.pay(a))
        self.assertEqual(self.wallet(a), 9_500)              # a draw gives the stake back

    def test_who_may_play(self):
        for kw, code in ((dict(account=False, year=None), 'bark_account'), (dict(year=None), 'bark_birth'), (dict(year=2015), 'bark_young')):
            p = self.player(**kw)
            with self.assertRaises(GameError) as e:
                self.join(p, 200)
            self.assertEqual(e.exception.code, code)
            self.assertEqual(self.wallet(p), 10_000)         # refused as a whole: nothing taken
            self.assertEqual(self.tickets(p), [])

    def test_cancel_and_housekeeping_refund_once(self):
        a, b = self.player(), self.player()
        r = self.join(a, 400)
        tid = r['result']['bark']['ticket']
        self.assertTrue(G.cancel(self.store, a, dict(ticket=tid))['back'])
        self.assertFalse(G.cancel(self.store, a, dict(ticket=tid))['back'])
        self.assertFalse(G.cancel(self.store, b, dict(ticket=tid))['back'])   # not theirs
        self.assertTrue(self.pay(a))
        self.assertEqual(self.wallet(a), 10_000)
        self.join(b, 300)
        self.start(b)
        t = time.time() + G.STUCK_MAX + 1                     # the live service stopped mid-match
        self.assertEqual(G.housekeeping(self.store, t), 1)
        self.assertEqual(G.housekeeping(self.store, t), 0)
        self.assertEqual(self.settle(b, 'win', 600), 0)       # a late settlement finds it refunded
        self.pay(b)
        self.assertEqual(self.wallet(b), 10_000)
        self.assertEqual(len(self.fx(b)), 1)
        self.join(a, 200)
        self.assertEqual(G.housekeeping(self.store, time.time() + G.WAIT_MAX + 1), 1)
        self.pay(a)
        self.assertEqual(self.wallet(a), 10_000)

    def test_daily_caps_and_streak_cool_down(self):
        a = self.player()
        sid = self.store.key(a)
        now = time.time()
        with self.store.connect() as db:
            for i in range(G.STREAK):
                db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created, started, ended, opp, result, pay) "
                           "VALUES(?,?,100,'done',?,?,?,'pvp','win',200)", (f'k{i:020x}', sid, now - 60 + i, now - 60 + i, now - 50 + i))
        with self.assertRaises(GameError) as e:
            self.join(a, 100)
        self.assertEqual(e.exception.code, 'bark_cool')
        with patch('game.dog_bark.now', lambda: now + G.COOL_S + 5):
            self.join(a, 100)                                  # after the cool-down
        with self.store.connect() as db:
            db.execute("UPDATE bark_tickets SET status='back' WHERE sid=? AND status='wait'", (sid,))
            for i in range(G.MATCH_DAY):
                db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created, ended, opp, result, pay) "
                           "VALUES(?,?,100,'done',?,?,'dog','lose',0)", (f'k{1000 + i:020x}', sid, now - 30, now - 3000))
        with patch('game.dog_bark.now', lambda: now + G.COOL_S + 5):
            with self.assertRaises(GameError) as e:
                self.join(a, 100)
        self.assertEqual(e.exception.code, 'bark_day')
        v = G.view(self.store, a)['me']
        self.assertEqual((v['played'], v['dog_n'], v['dog_room']), (G.MATCH_DAY + G.STREAK, G.MATCH_DAY, 0))
        self.assertEqual(self.wallet(a), 10_000 - 100)        # only the one stake (refunded by hand above, not paid here)

    def test_dog_net_room_and_view(self):
        a = self.player()
        sid = self.store.key(a)
        now = time.time()
        with self.store.connect() as db:
            db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created, ended, opp, result, pay) "
                       "VALUES(?,?,1500,'done',?,?,'dog','win',3000)", ('k' + '1' * 20, sid, now - 10, now - 5))
        v = G.view(self.store, a)
        self.assertEqual(v['me']['dog_room'], G.DOG_WIN_DAY - 1_500)
        self.assertEqual(v['me']['code'], '')
        self.assertEqual(v['king']['title'], '🐕 Vua sủa')
        self.assertEqual((v['king']['name'], v['king']['xu']), ('Lan', 1_500))

    def test_concurrent_settlement_pays_once(self):
        a = self.player()
        self.join(a, 1_000)
        self.start(a)
        out = []
        ths = [threading.Thread(target=lambda: out.append(self.settle(a, 'win', 2_000))) for _ in range(4)]
        for x in ths:
            x.start()
        for x in ths:
            x.join()
        self.assertEqual(sorted(out), [0, 0, 0, 1])
        self.pay(a)
        self.assertEqual(self.wallet(a), 11_000)

    def test_forget(self):
        a = self.player()
        self.join(a, 100)
        self.store.delete(a)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM bark_tickets').fetchone())
