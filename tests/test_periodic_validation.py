"""Periodic checks stay complete without scanning every career twice."""
import copy
import unittest
from unittest.mock import patch

from game import engine, storage
from tests import test_workplace_business as fixtures


class PeriodicValidationTests(unittest.TestCase):
    def setUp(self):
        case = fixtures.WorkplaceBusinessTests()
        self.state, career, _ = case.sample()
        self.at = case.next(career)
        engine.validate_state(self.state)
        self.text = storage.serialize(self.state, full=True)
        self.store = object.__new__(storage.Store)
        self.store.story = False

    def compute(self, text=None, rev=None):
        with patch('time.time', return_value=self.at):
            return self.store._compute('periodic-fixture', text or self.text, None,
                                       'business_sync', {}, True,
                                       storage.FULL_EVERY-1 if rev is None else rev)

    def test_periodic_settlement_validates_all_careers_once_and_keeps_same_result(self):
        original = engine.apply_action
        def old(*a, **kw):
            kw['scoped'] = False
            return original(*a, **kw)
        with patch.object(storage, 'apply_action', old):
            before = self.compute()
        with patch.object(engine, 'validate_career', wraps=engine.validate_career) as validate:
            after = self.compute()
        self.assertEqual(validate.call_count, len(self.state['careers']))
        self.assertEqual(after, before)
        self.assertTrue(engine.stamped(after[0]))
        self.assertEqual(after[0]['careers']['accounting']['ops']['business']['served'], 1)

    def test_new_build_keeps_unscoped_checks(self):
        s=copy.deepcopy(self.state);s['check']['build']='old-build'
        with patch.object(storage, 'apply_action', wraps=engine.apply_action) as apply:
            out=self.compute(storage._dumps(s))
        self.assertFalse(apply.call_args.kwargs['scoped'])
        self.assertTrue(engine.stamped(out[0]))

    def test_invalid_career_created_during_periodic_action_is_rejected(self):
        original=engine.apply_action
        def corrupt(*a, **kw):
            s,r=original(*a, **kw)
            s['careers']['mother_baby']['money']=-1
            return s,r
        with patch.object(storage, 'apply_action', corrupt):
            with self.assertRaises(engine.GameError):self.compute()

    def test_unmodified_invalid_career_is_still_caught_by_periodic_check(self):
        s=copy.deepcopy(self.state);s['careers']['mother_baby']['money']=-1
        with self.assertRaises(engine.GameError):self.compute(storage._dumps(s))
