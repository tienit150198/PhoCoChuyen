"""Offline staff histories keep order and rollback while avoiding per-row round trips."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from game import archive as ar
from game.storage import Store, _write_archive


class ArchiveBatch(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'batch.db')
        self.addCleanup(self.store.close_pool)
        token,_,_=self.store.session()
        self.sid=self.store.key(token)

    def read(self):
        with self.store.connect() as db:
            return [tuple(r) for r in db.execute('SELECT career,kind,seq,day,row FROM archive WHERE sid=? ORDER BY career,kind,seq',(self.sid,))]

    def test_offline_batch_keeps_every_row_with_bounded_calls(self):
        rows=[('milk_tea','ledger',i//100,json.dumps({'id':i})) for i in range(4096)]
        with self.store.connect() as db:
            with patch.object(db,'execute',wraps=db.execute) as execute:
                _write_archive(db,self.sid,rows)
                # A few calls for sequence allocation/chunks, rather than 4096 INSERT round trips.
                self.assertLess(execute.call_count,20)
        found=self.read()
        self.assertEqual([r[2] for r in found],list(range(4096)))
        self.assertEqual([json.loads(r[4])['id'] for r in found],list(range(4096)))

    def test_forget_resets_only_its_history_even_inside_batch(self):
        with self.store.connect() as db:
            _write_archive(db,self.sid,[('milk_tea','ledger',1,'"old"'),('com','ledger',1,'"other"')])
            _write_archive(db,self.sid,[('milk_tea','ledger',2,'"discard"'),('milk_tea',ar.FORGET+'ledger',None,'null'),('com','ledger',2,'"keep"'),('milk_tea','ledger',3,'"new"'),('milk_tea','ledger',4,'"next"')])
        self.assertEqual(self.read(),[('com','ledger',0,1,'"other"'),('com','ledger',1,2,'"keep"'),('milk_tea','ledger',0,3,'"new"'),('milk_tea','ledger',1,4,'"next"')])

    def test_failed_transaction_does_not_keep_partial_batch(self):
        with self.assertRaises(RuntimeError):
            with self.store.connect() as db:
                _write_archive(db,self.sid,[('com','ledger',1,'{}')]*1100)
                raise RuntimeError('simulate later save failure')
        self.assertEqual(self.read(),[])
