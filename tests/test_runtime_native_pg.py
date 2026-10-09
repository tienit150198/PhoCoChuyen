"""PostgreSQL conflict handling in player metadata and aggregate statistics."""
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from unittest.mock import patch

from game import couple, marriage, retention, social
from game.storage import Store
from tests.pg_support import pg_only


@pg_only
class NativeConflictTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'runtime.namespace')

    def tearDown(self):
        self.store.close_pool()
        self.temp.cleanup()

    def taken_code(self):
        with self.store.connect() as db:
            db.execute('INSERT INTO marriage_people(sid,code,created,updated) VALUES(?,?,?,?)',
                       ('existing-player', 'PCC-AAAAAA', 1, 1))

    def test_player_code_collision_retries_without_replacing_the_owner(self):
        self.taken_code()
        with patch.object(marriage, '_new_code', side_effect=['PCC-AAAAAA', 'PCC-BBBBBB']):
            player = marriage.ensure_person(self.store, 'new-player')
        self.assertEqual(player['code'], 'PCC-BBBBBB')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT sid FROM marriage_people WHERE code=?',
                                        ('PCC-AAAAAA',)).fetchone()[0], 'existing-player')

    def test_code_collision_does_not_abort_the_callers_transaction(self):
        self.taken_code()
        with self.store.connect() as db:
            db.execute('BEGIN')
            with patch.object(marriage, '_new_code', side_effect=['PCC-AAAAAA', 'PCC-BBBBBB']):
                marriage.ensure_person_db(db, 'new-player')
            self.assertEqual(db.execute('SELECT code FROM marriage_people WHERE sid=?',
                                        ('new-player',)).fetchone()[0], 'PCC-BBBBBB')
            self.assertEqual(db.execute('SELECT 42').fetchone()[0], 42)

    def test_repeated_milestones_keep_the_first_time_and_details(self):
        with patch.object(retention, 'ENABLED', True), self.store.connect() as db:
            retention.write_marks(db, 'player', [('picked', 'delivery', 'first')], day=1, at=100)
            retention.write_marks(db, 'player', [('picked', 'milk_tea', 'second')], day=2, at=200)
            row = db.execute('SELECT at,day,career,detail FROM stat_milestones WHERE sid=? AND key=?',
                             ('player', 'picked')).fetchone()
        self.assertEqual(tuple(row), (100, 1, 'delivery', 'first'))

    def test_duplicate_news_returns_false_and_keeps_the_first_text(self):
        with self.store.connect() as db:
            self.assertTrue(marriage._post_news(db, 'married', 'event:1', 'First', 'a', 'b'))
            self.assertFalse(marriage._post_news(db, 'married', 'event:1', 'Second', 'a', 'b'))
            rows = db.execute('SELECT text FROM news WHERE ref=?', ('event:1',)).fetchall()
        self.assertEqual([row[0] for row in rows], ['First'])

    def test_concurrent_profile_creation_returns_one_shared_profile(self):
        barrier = threading.Barrier(4)

        def create():
            with self.store.connect() as db:
                barrier.wait(timeout=10)
                return social._touch(db, 'shared-player', None)

        with ThreadPoolExecutor(max_workers=4) as pool:
            profiles = list(pool.map(lambda _: create(), range(4)))
        self.assertEqual({row['pid'] for row in profiles}, {social.pid_of('shared-player')})
        self.assertEqual({row['sid'] for row in profiles}, {'shared-player'})
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM profiles WHERE sid=?',
                                        ('shared-player',)).fetchone()[0], 1)

    def race_fund_moves(self, balance, kind, amount):
        """Release two fund operations together after both wait on the same real row lock."""
        with self.store.connect() as db:
            # a fund move checks the couple is still married (couple._lock_fund)
            db.execute("INSERT INTO couples(id,a,b,status,since) VALUES(?,?,?,'married',?)", (7, 'member', 'partner', 1))
            db.execute('INSERT INTO joint_funds(couple,balance,updated) VALUES(?,?,?)', (7, balance, 1))
        pids = Queue()

        def move(ref):
            try:
                with self.store.connect() as db:
                    pids.put(db.raw.info.backend_pid)
                    couple._fund_move(db, 7, 'member', kind, amount, 'Payment', ref)
                return 'ok'
            except marriage.MarriageError as error:
                return error.code

        with self.store.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:
            blocker.execute('BEGIN')
            blocker.execute('SELECT balance FROM joint_funds WHERE couple=? FOR UPDATE', (7,))
            futures = [pool.submit(move, f'native-fund-{n}') for n in range(2)]
            try:
                targets = [pids.get(timeout=10), pids.get(timeout=10)]
                deadline = time.monotonic() + 10
                with self.store.connect() as observer:
                    while time.monotonic() < deadline:
                        waiting = observer.pg("SELECT COUNT(*) FROM pg_stat_activity WHERE pid=ANY(%s) "
                                              "AND wait_event_type='Lock'", (targets,)).fetchone()[0]
                        if waiting == 2:
                            break
                        time.sleep(0.01)
                    else:
                        self.fail('Both PostgreSQL fund operations must reach the held row lock')
            finally:
                blocker.commit()
            return sorted(future.result(timeout=10) for future in futures)

    def test_concurrent_card_spends_obey_the_shared_daily_cap(self):
        outcomes = self.race_fund_moves(2000, 'spend', 700)
        self.assertEqual(outcomes, ['fund_cap', 'ok'])
        with self.store.connect() as db:
            self.assertEqual(couple._balance(db, 7), 1300)
            self.assertEqual(couple._used(db, 7, 'member'), 700)

    def test_concurrent_deposits_do_not_exceed_the_fund_limit(self):
        outcomes = self.race_fund_moves(couple.FUND_MAX - 100, 'deposit', 100)
        self.assertEqual(outcomes, ['fund_full', 'ok'])
        with self.store.connect() as db:
            self.assertEqual(couple._balance(db, 7), couple.FUND_MAX)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM joint_ledger WHERE couple=?', (7,)).fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
