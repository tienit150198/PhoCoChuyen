"""🗄️ The archive's old rows packed (game/archive_pack.py): every page, tail and export reads the same rows
before and after, the next position is unchanged, an erased history and a deleted save lose their packed rows."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from game import archive as ar
from game import archive_pack as arp
from game.storage import Store, _write_archive


def pages(store, token, career, kind, limit=37):
    rows, before = [], None
    while True:
        page = store.archive_page(token, career, kind, before=before, limit=limit)
        rows.extend(page['rows'])
        if page['before'] is None:
            return page['total'], rows
        before = page['before']


def tails(store, token, career, kind, limit=29):
    rows, before = [], None
    while True:
        page = store.archive_tail(token, career, kind, before=before, limit=limit)
        rows.extend(page['rows'])
        if page['before'] is None:
            return rows
        before = page['before']


class ArchivePack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'pack.db')
        self.addCleanup(self.store.close_pool)
        self.token, _, _ = self.store.session()
        self.sid = self.store.key(self.token)
        for p in (mock.patch.object(arp, 'KEEP', 10), mock.patch.object(arp, 'CHUNK', 60), mock.patch.object(arp, 'MIN_CHUNK', 5)):
            p.start()
            self.addCleanup(p.stop)

    def write(self, career, kind, rows, age=0):
        with self.store.connect() as db:
            db.begin()
            _write_archive(db, self.sid, [(career, kind, i % 7, json.dumps(r)) for i, r in enumerate(rows)])
            if age:
                db.execute('UPDATE archive SET created_at=created_at-? WHERE sid=? AND career=? AND kind=?', (age, self.sid, career, kind))
            db.commit()

    def count(self, table):
        with self.store.connect() as db:
            return db.execute(f'SELECT COUNT(*) FROM {table} WHERE sid=?', (self.sid,)).fetchone()[0]

    def sweep(self):
        return arp.sweep(self.store, 60, after='', older_than=86400)

    def test_every_read_is_the_same_after_packing(self):
        self.write('milk_tea', 'ledger', [{'id': i, 'amount': i * 3} for i in range(250)], age=5 * 86400)
        self.write('', 'board.posts', [{'id': f'p{i}'} for i in range(130)], age=5 * 86400)
        self.write('', 'chua.cards', [{'id': i} for i in range(80)], age=5 * 86400)
        before = (pages(self.store, self.token, 'milk_tea', 'ledger'), tails(self.store, self.token, '', 'board.posts'),
                  self.store.archive_export(self.token))
        moved, after, done = self.sweep()
        self.assertEqual((after, done), ('', True))
        self.assertEqual(moved, 240 + 120)   # the newest 10 of each history stay; chua.cards is never packed
        self.assertEqual(self.count('archive'), 10 + 10 + 80)
        self.assertGreaterEqual(self.count('archive_packed'), 5)
        self.assertEqual((pages(self.store, self.token, 'milk_tea', 'ledger'), tails(self.store, self.token, '', 'board.posts'),
                          self.store.archive_export(self.token)), before)
        # a second sweep finds nothing more
        self.assertEqual(self.sweep()[0], 0)

    def test_the_next_row_takes_the_next_position(self):
        self.write('pho', 'ledger', [{'id': i} for i in range(100)], age=5 * 86400)
        self.sweep()
        self.write('pho', 'ledger', [{'id': 100}, {'id': 101}])
        total, rows = pages(self.store, self.token, 'pho', 'ledger')
        self.assertEqual(total, 102)
        self.assertEqual([r['pos'] for r in rows], list(range(101, -1, -1)))
        self.assertEqual([r['row']['id'] for r in rows], list(range(101, -1, -1)))

    def test_young_rows_and_short_histories_stay(self):
        self.write('pho', 'ledger', [{'id': i} for i in range(100)])            # today's
        self.write('pho', 'journal', [{'id': i} for i in range(12)], age=5 * 86400)  # 2 past the newest 10: under MIN_CHUNK
        self.assertEqual(self.sweep()[0], 0)
        self.assertEqual(self.count('archive_packed'), 0)

    def test_an_erased_history_loses_its_packed_rows_too(self):
        self.write('', 'talk', [{'id': i} for i in range(50)], age=5 * 86400)
        self.write('pho', 'ledger', [{'id': i} for i in range(50)], age=5 * 86400)
        self.sweep()
        with self.store.connect() as db:
            db.begin()
            _write_archive(db, self.sid, [('', ar.FORGET + 'talk', None, 'null'), ('', 'talk', 0, '"new"')])
            db.commit()
        total, rows = pages(self.store, self.token, '', 'talk')
        self.assertEqual((total, [r['row'] for r in rows]), (1, ['new']))
        self.assertEqual(pages(self.store, self.token, 'pho', 'ledger')[0], 50)

    def test_a_deleted_save_loses_its_packed_rows(self):
        self.write('pho', 'ledger', [{'id': i} for i in range(50)], age=5 * 86400)
        self.sweep()
        self.assertGreater(self.count('archive_packed'), 0)
        self.assertTrue(self.store.delete(self.token))
        self.assertEqual(self.count('archive_packed'), 0)

    def test_a_row_found_in_both_tables_is_read_once(self):
        """A reader that saw a row in archive before a pack committed, then the chunk: kept once."""
        self.write('pho', 'ledger', [{'id': i} for i in range(40)], age=5 * 86400)
        with self.store.connect() as db:
            db.begin()
            rows = [(r['seq'], r['day'], r['row']) for r in db.execute(
                "SELECT seq,day,row FROM archive WHERE sid=? AND kind='ledger' AND seq<20 ORDER BY seq", (self.sid,))]
            db.execute("INSERT INTO archive_packed(sid,career,kind,seq_lo,seq_hi,n,data) VALUES(?,?,?,?,?,?,?)",
                       (self.sid, 'pho', 'ledger', 0, 20, 20, arp.encode(rows)))
            db.commit()
        total, rows = pages(self.store, self.token, 'pho', 'ledger')
        self.assertEqual([r['row']['id'] for r in rows], list(range(39, -1, -1)))

    def test_housekeeping_waits_for_the_night_and_its_turn(self):
        with mock.patch.object(arp, 'sweep', return_value=(0, '', True)) as sweep:
            arp._STATE['at'] = 0.0
            with mock.patch.object(arp, 'night', return_value=False):
                arp.run(self.store)
            sweep.assert_not_called()
            with mock.patch.object(arp, 'night', return_value=True):
                arp.run(self.store)
                arp.run(self.store)   # within EVERY: skipped
            self.assertEqual(sweep.call_count, 1)
        self.assertTrue(arp.night(time.mktime((2026, 10, 22, 3, 0, 0, 0, 0, -1)) - time.timezone - 7 * 3600))


if __name__ == '__main__':
    unittest.main()
