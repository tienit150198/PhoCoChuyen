"""Release notice is opt-in, requires a live event, and never duplicates on retry."""
import importlib.util
import concurrent.futures
import tempfile
import unittest
import threading
from unittest.mock import patch
from pathlib import Path

from game.storage import Store
from tests.pg_support import pg_only


@pg_only
class ReleaseNotice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.tmp.name) / 'notice', story=True)
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.addClassCleanup(cls.store.close_pool)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.publish_major_release'), 'release publisher missing')
        from scripts import publish_major_release
        return publish_major_release

    def setUp(self):
        with self.store.connect() as db:
            db.execute("DELETE FROM mnl_meta WHERE key='release_notice_2_0_0'")
            db.execute('DELETE FROM chat_pins')
            db.execute('DELETE FROM chat_messages')
            db.execute("DELETE FROM mnl_meta WHERE key='fair_golden_days_20261011'")

    def activate(self):
        from game import fair_golden_days as golden
        with self.store.connect() as db:
            golden.activate(db)

    def test_concurrent_publishers_create_one_message(self):
        m = self.module()
        self.activate()
        def attempt(_):
            with self.store.connect() as db:
                return m.publish(db, health_version='2.0.0')
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(attempt, range(5)))
        self.assertEqual(len({row['id'] for row in results}), 1)
        self.assertEqual(sum(not row['already_published'] for row in results), 1)

    def test_publish_checks_event_and_version_before_writing(self):
        m = self.module()
        with self.store.connect() as db:
            for health in ['1.9.48', '2.0.0']:
                with self.assertRaises(ValueError):
                    m.publish(db, health_version=health)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0], 0)

    def test_retry_keeps_one_message_and_does_not_repin_over_later_notice(self):
        m = self.module()
        self.activate()
        with self.store.connect() as db:
            first = m.publish(db, health_version='2.0.0')
        with self.store.connect() as db:
            db.execute("UPDATE chat_pins SET msg=99999 WHERE channel='town'")
            second = m.publish(db, health_version='2.0.0')
            self.assertEqual(first['id'], second['id'])
            self.assertTrue(second['already_published'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT msg FROM chat_pins WHERE channel='town'").fetchone()[0], 99999)
            row = db.execute('SELECT * FROM chat_messages WHERE id=?', (first['id'],)).fetchone()
            self.assertEqual((row['pid'], row['adm'], row['channel']), ('admin', 1, 'town'))
            self.assertIn('Cài đặt', row['text'])
            self.assertIn('Giao diện mới', row['text'])
            self.assertIn('3 ảnh', row['text'])
            self.assertIn('2 ngày vàng', row['text'])
            self.assertNotIn('70', row['text'])

    def test_expiry_while_waiting_for_lock_is_rechecked(self):
        m = self.module()
        self.activate()
        entered = threading.Event()
        with self.store.connect() as holder:
            holder.begin()
            holder.execute('SELECT pg_advisory_xact_lock(?)', (20001011,))
            def attempt():
                with self.store.connect() as db:
                    original = db.execute
                    def execute(sql, params=()):
                        if 'pg_advisory_xact_lock' in sql:
                            entered.set()
                        return original(sql, params)
                    with patch.object(db, 'execute', side_effect=execute):
                        return m.publish(db, health_version='2.0.0')
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(attempt)
                self.assertTrue(entered.wait(5))
                holder.execute("UPDATE mnl_meta SET value='1700000000' WHERE key='fair_golden_days_20261011'")
                holder.commit()
                with self.assertRaises(ValueError):
                    pending.result(timeout=5)
            self.assertEqual(holder.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0], 0)

    def test_message_explicitly_names_eligible_games(self):
        text = self.module().message(1800172800)
        for label in ('Chiếu trong', 'lô tô', 'vé cào'):
            self.assertIn(label, text)
        self.assertLess(len(text), 1200)


if __name__ == '__main__':
    unittest.main()
