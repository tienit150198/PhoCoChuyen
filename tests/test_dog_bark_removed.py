"""🐕 Kéo co chó sủa removed (owner 15/10): no new stake, but what 2.4.15 and older already wrote still works.

* `jr_bark_join` refuses ('bark_off') and nothing leaves the wallet; no ticket row.
* A pending 'bark' payout and a pending 'bark_weekly' prize are still paid once (with the title, which validates).
* A ticket left open (no live service plays it now) goes back by housekeeping, once.
* Erasing one's data still erases one's tickets; the table and other players' rows stay.
* No route, no live feature, no welcome flag, no client file is left.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path

from game import dog_bark as G
from game import dog_bark_board as B
from game.engine import GameError, validate_state
from tests.pg_support import pg_only

ROOT = Path(__file__).resolve().parent.parent


class Gone(unittest.TestCase):
    def test_no_route_feature_flag_or_client_file(self):
        server = (ROOT / 'server.py').read_text(encoding='utf-8')
        self.assertNotIn('/api/dogbark', server)
        self.assertNotIn('dog_bark.enabled', server)
        from live.app import FEATURES
        from live.config import Config
        self.assertNotIn('bark', {f.name for f in FEATURES})
        self.assertNotIn('bark', Config().flags())
        for rel in ('live/dog_bark.py', 'public/js/v4/dog-bark.js', 'public/js/v4/dog-bark-board.js', 'public/css/dog-bark.css',
                    'public/audio/bark'):
            self.assertFalse((ROOT / rel).exists(), rel)
        for rel in ('public/js/app.js', 'public/js/isometric/town-utilities.js', 'public/js/scenes/town-place.js',
                    'public/js/scenes/venue-place.js', 'public/js/v4/town-walk.js', 'game/town_layout.json'):
            text = (ROOT / rel).read_text(encoding='utf-8')
            self.assertNotIn('liveBark', text, rel)
            self.assertNotIn('dog-bark', text, rel)

    def test_titles_stay_valid(self):
        from game import journey as jr
        from tests.test_bank import story
        for tid in B.TITLE_IDS:
            self.assertIn(tid, jr.TITLE_INDEX)
        s = story()
        s['journey']['titles']['bark_king'] = s['journey']['life_day']   # a save holding last week's prize title
        validate_state(s)

    def test_command_refuses_without_touching_the_save(self):
        from game.engine import apply_action
        from tests.test_bank import story
        s = story(wallet=5_000)
        with self.assertRaises(GameError) as e:
            apply_action(s, None, 'jr_bark_join', dict(stake=1_000))
        self.assertEqual(e.exception.code, 'bark_off')
        self.assertEqual(s['journey']['wallet'], 5_000)


@pg_only
class Database(unittest.TestCase):
    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        self.n = 0

    def player(self, wallet=10_000, name='Lan'):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {sid: fn})
        with self.store.connect() as db:
            db.execute("INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?,?,?,?,'2026-01-01 00:00:00')",
                       (f'u{sid[:10]}', name, 'x', sid))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'c' * 48))
            db.execute('INSERT INTO account_birth(sid, year, at) VALUES(?,?,?)', (sid, 2000, 1.0))
        return token

    def state(self, token):
        return self.store.read(token)[0]

    def wallet(self, token):
        return self.state(token)['journey']['wallet']

    def pay(self, token):
        from game import live_effects
        return live_effects.on_load(self.store, token, self.state(token))

    def ticket(self, token, status='wait', stake=500, age=0.0):
        """A ticket as 2.4.15 wrote it (the stake already left the wallet)."""
        self.n += 1
        tid = f'k{self.n:020x}'
        t = time.time() - age
        with self.store.connect() as db:
            db.execute('INSERT INTO bark_tickets(id, sid, stake, status, created, started) VALUES(?,?,?,?,?,?)',
                       (tid, self.store.key(token), stake, status, t, t if status != 'wait' else None))
        return tid

    def fx(self, token, kind='bark'):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT id, amount, status FROM live_effects WHERE sid=? AND kind=? ORDER BY id',
                                                (self.store.key(token), kind)).fetchall()]

    def test_join_through_the_store_refuses(self):
        a = self.player()
        with self.assertRaises(GameError) as e:
            self.store.command(a, 'bark-00000001', self.store.read(a)[1], None, 'jr_bark_join', dict(stake=1_000))
        self.assertEqual(e.exception.code, 'bark_off')
        self.assertEqual(self.wallet(a), 10_000)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM bark_tickets').fetchone())

    def test_pending_pot_is_paid_once(self):
        a = self.player()
        tid = self.ticket(a, status='done')
        with self.store.connect() as db:
            db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?)",
                       (f'bark:{tid}', self.store.key(a), 'bark', 1_000, json.dumps(dict(ticket=tid, what='win', src='bark')), time.time()))
        self.assertTrue(self.pay(a))
        self.assertFalse(self.pay(a))
        self.assertEqual(self.wallet(a), 11_000)
        self.assertEqual([x['status'] for x in self.fx(a)], ['applied'])
        with self.store.connect() as db:      # as if the row never flipped (a crash): the receipt replays, no second pay
            db.execute("UPDATE live_effects SET status='pending' WHERE kind='bark'")
        self.pay(a)
        self.assertEqual(self.wallet(a), 11_000)

    def test_pending_weekly_prize_is_paid_with_its_title(self):
        a = self.player()
        sid = self.store.key(a)
        data = dict(week='2026-10-05', rank=1, title='bark_king')
        with self.store.connect() as db:
            db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?)",
                       (f'{B.META}2026-10-05:{sid}', sid, B.FX, B.COINS[0], json.dumps(data), time.time()))
        self.assertTrue(self.pay(a))
        s = self.state(a)
        self.assertEqual(s['journey']['wallet'], 10_000 + B.COINS[0])
        self.assertIn('bark_king', s['journey']['titles'])
        validate_state(s)
        self.assertEqual([x['status'] for x in self.fx(a, B.FX)], ['applied'])

    def test_open_tickets_go_back_once(self):
        a, b = self.player(), self.player(name='Hoa')
        self.ticket(a, 'wait', 400, age=G.WAIT_MAX + 5)
        self.ticket(b, 'play', 300, age=G.STUCK_MAX + 5)
        fresh = self.ticket(b, 'wait', 200)            # young: left for the next pass
        self.assertEqual(G.housekeeping(self.store), 2)
        self.assertEqual(G.housekeeping(self.store), 0)
        self.pay(a)
        self.pay(b)
        self.assertEqual(self.wallet(a), 10_400)
        self.assertEqual(self.wallet(b), 10_300)
        self.assertEqual(G.housekeeping(self.store, time.time() + G.WAIT_MAX + 1), 1)
        self.pay(b)
        self.assertEqual(self.wallet(b), 10_500)
        with self.store.connect() as db:                # rows stay (status 'back'), never deleted
            self.assertEqual(db.execute("SELECT status FROM bark_tickets WHERE id=?", (fresh,)).fetchone()['status'], 'back')
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM bark_tickets').fetchone()['n'], 3)

    def test_forget_erases_only_ones_own_rows(self):
        a, b = self.player(), self.player(name='Hoa')
        self.ticket(a, 'done')
        keep = self.ticket(b, 'done')
        self.store.delete(a)
        with self.store.connect() as db:
            self.assertEqual([r['id'] for r in db.execute('SELECT id FROM bark_tickets').fetchall()], [keep])


if __name__ == '__main__':
    unittest.main()
