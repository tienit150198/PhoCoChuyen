import unittest
import copy
from unittest.mock import patch, Mock
from game import business
from game.engine import new_state, apply_action, GameError


class BusinessSyncTests(unittest.TestCase):
    def test_reconcile_resumes_new_funds_without_paying_blocked_time(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        s,c,_=WorkplaceBusinessTests().sample()
        c['money']=0
        at=min(p['at'] for p in c['ops']['business']['pending'].values())
        wb.settle(s,now=at)
        self.assertEqual(c['ops']['business']['reason'],'fund')
        c['money']=100
        with patch('game.business.time.time',return_value=at+10000):
            self.assertTrue(business.reconcile(s))
        self.assertEqual(c['ops']['business']['served'],0)
        self.assertGreater(min(p['at'] for p in c['ops']['business']['pending'].values()),at+10000)

    def test_successful_early_return_reconciles_businesses(self):
        with patch('game.business.reconcile',return_value=False) as reconcile:
            out,_=apply_action(new_state(),None,'settings',{'name':'Tên mới'})
        reconcile.assert_called_once_with(out)

    def test_internal_only_and_input_unchanged(self):
        s=new_state();before=copy.deepcopy(s)
        with self.assertRaises(GameError):apply_action(s,None,business.ACTION,{})
        out,_=apply_action(s,None,business.ACTION,{},internal=True)
        self.assertEqual(s,before)
        self.assertEqual(s['careers'],out['careers'])

    def test_both_settle_before_any_mutation_with_same_clock(self):
        seen=[]
        def first(s,now=None):seen.append(('quay',s['name'],now));return False
        def second(s,now=None):seen.append(('workplace',s['name'],now));return False
        s=new_state()
        with patch('game.business.time.time',return_value=12345), patch('game.quay_business.settle',side_effect=first), patch('game.workplace_business.settle',side_effect=second):
            out,_=apply_action(s,None,'settings',{'name':'Tên mới'})
        self.assertEqual(seen,[('quay',s['name'],12345),('workplace',s['name'],12345)])
        self.assertEqual(out['name'],'Tên mới')

    def test_read_without_due_work_does_not_write(self):
        store=Mock()
        with patch('game.quay_business.due',return_value=False), patch('game.workplace_business.due',return_value=False):
            self.assertFalse(business.on_load(store,'token',new_state()))
        store.command.assert_not_called()

    def test_due_read_uses_internal_atomic_command(self):
        store=Mock()
        with patch('game.quay_business.due',return_value=False), patch('game.workplace_business.due',return_value=True):
            self.assertTrue(business.on_load(store,'token',new_state()))
        args,kwargs=store.command.call_args
        self.assertEqual(args[2:],(None,None,business.ACTION,{}))
        self.assertEqual(kwargs,{'internal':True})
