"""NPC ledger scan acceleration must preserve every original trim boundary."""
import copy
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from game import operations as ops, archive
from game.engine import new_state


def original_trim(c):
    f=c['ops']['finance'];rows=f['ledger']
    if len(rows)<=ops.LEDGER_HIGH:return
    cut=len(rows)-ops.LEDGER_KEEP;recent=c['day']-ops.LEDGER_DAYS
    while cut>0 and rows[cut-1]['day']>=recent:cut-=1
    cut=max(cut,len(rows)-ops.LEDGER_MAX)
    if cut<=0:return
    archive.record(rows[:cut],'ledger',c)
    f['opening_balance']+=sum(x['amount'] for x in rows[:cut])
    f['ledger']=rows[cut:]


def sample(days):
    c=new_state()['careers']['accounting'];c['day']=20
    c['ops']['finance']['ledger']=[dict(id=f'old-{i}',day=day,turn=0,amount=i%7-3,
        category='materials',reason='Synthetic history',ref=None) for i,day in enumerate(days)]
    return c


class LedgerBatch(unittest.TestCase):
    def compare(self,days,steps,*,cross_day=False):
        fixture=sample(days);results=[]
        for optimized in (False,True):
            c=copy.deepcopy(fixture)
            with archive.collect() as box, (ops.recent_ledger_batch() if optimized else nullcontext()), (nullcontext() if optimized else patch.object(ops,'trim_ledger',original_trim)):
                for i in range(steps):
                    if cross_day and i==steps//2:c['day']+=20
                    ops.record_money(c,i%5-2,'Synthetic entry',str(i),'materials')
            results.append((c,[(kind,row) for _,kind,row in box.rows]))
        self.assertEqual(results[0],results[1])

    def test_recent_cap_and_money_archive_are_exact(self):
        self.compare([20]*1200,4096)

    def test_old_threshold_counterexample_is_exact(self):
        self.compare([1]*199,51)

    def test_unsorted_and_mixed_days_preserve_exact_archive_order(self):
        for rows in ([20,1]*150,[1]*80+[20]*400,[20]*190+[1]*20+[20]*990):
            with self.subTest(rows=len(rows)):self.compare(rows,400)

    def test_crossing_day_invalidates_proof(self):
        self.compare([20]*1200,100,cross_day=True)

    def test_failure_discards_context_and_nonbatch_stays_original(self):
        c=sample([20]*300)
        with self.assertRaises(RuntimeError):
            with ops.recent_ledger_batch():
                ops.record_money(c,1,'First',None,'materials')
                raise RuntimeError('Aborted settlement')
        self.assertIsNone(ops._LEDGER_BATCH.get())
        c['ops']['finance']['ledger'][10]['day']=1
        expected=copy.deepcopy(c)
        with archive.collect() as got:ops.record_money(c,2,'After failure',None,'materials')
        with archive.collect() as want,patch.object(ops,'trim_ledger',original_trim):ops.record_money(expected,2,'After failure',None,'materials')
        self.assertEqual(c,expected)
        self.assertEqual([(k,r) for _,k,r in got.rows],[(k,r) for _,k,r in want.rows])

    def test_recent_batch_does_not_rescan_whole_ledger_per_entry(self):
        class Counted(dict):
            reads=0
            def __getitem__(self,key):
                if key=='day':Counted.reads+=1
                return super().__getitem__(key)
        c=sample([20]*1200);c['ops']['finance']['ledger']=[Counted(r) for r in c['ops']['finance']['ledger']]
        with ops.recent_ledger_batch():
            for i in range(100):ops.record_money(c,0,'Same day',None,'materials')
        self.assertLess(Counted.reads,2000)

    def test_replaced_ledger_invalidates_proof(self):
        c=sample([20]*300)
        with ops.recent_ledger_batch():
            ops.record_money(c,0,'First',None,'materials')
            c['ops']['finance']['ledger']=copy.deepcopy(c['ops']['finance']['ledger'])
            c['ops']['finance']['ledger'][10]['day']=1
            expected=copy.deepcopy(c)
            with archive.collect() as got:ops.record_money(c,1,'Replaced',None,'materials')
            with archive.collect() as want,patch.object(ops,'trim_ledger',original_trim):ops.record_money(expected,1,'Replaced',None,'materials')
        self.assertEqual(c,expected)
        self.assertEqual([(k,r) for _,k,r in got.rows],[(k,r) for _,k,r in want.rows])

    def test_actual_npc_batch_matches_state_and_ordered_archive(self):
        from game import workplace_business as wb
        from tests.test_workplace_business import WorkplaceBusinessTests
        fixture,c,_=WorkplaceBusinessTests().sample()
        f=c['ops']['finance'];f['ledger']=sample([1]*1200)['ops']['finance']['ledger'];f['opening_balance']=c['money']-sum(r['amount'] for r in f['ledger'])
        results=[]
        for optimized in (False,True):
            state=copy.deepcopy(fixture)
            with archive.collect() as box,(nullcontext() if optimized else patch.object(ops,'trim_ledger',original_trim)):
                wb.settle(state,2000000000+86400)
            results.append((state,[(kind,row) for _,kind,row in box.rows]))
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[0][0]['careers']['accounting']['ops']['business']['served'],1024)
        with patch.object(wb,'_finish',side_effect=RuntimeError('Failed NPC order')):
            with self.assertRaises(RuntimeError):wb.settle(copy.deepcopy(fixture),2000000000+86400)
        self.assertIsNone(ops._LEDGER_BATCH.get())
