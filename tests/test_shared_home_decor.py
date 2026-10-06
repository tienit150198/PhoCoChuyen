"""Shared finishes are one room choice, with personal purchases and atomic save receipts."""
import concurrent.futures
import contextvars
import threading
import uuid
from unittest.mock import patch

from game import deco as dc, family, housing as hs, marriage as mr
from game.engine import GameError
from game.storage import serialize
from tests import test_deco_mate as shared
from tests.test_bank import act


class SharedHomeFinishes(shared.SharedDecor):
    def command(self, tok, skin, part='wall', room='living', request=None, **payload):
        revision = self.store.read(tok)[1]
        return self.store.command(tok, request or str(uuid.uuid4()), revision, None, 'jr_deco_skin',
                                  dict(r=room, part=part, skin=skin, **payload))

    def test_finishes_are_visible_without_spouse_furniture(self):
        self.move_in()
        def pack(s):
            d, D, L = dc._ensure(s)
            dc._store(d, D, L, {})
        mr._mutate(self.store, {self.sid(self.b): pack})
        self.command(self.a, 'bac_ha')
        a, b = self.mate(self.a), self.mate(self.b)
        self.assertEqual(a['items'], [])
        self.assertEqual(a['skins'], b['skins'])
        self.assertEqual(a['skins']['living'], {'w': 'bac_ha'})
        self.assertTrue(a['owner'])
        self.assertFalse(b['owner'])
        self.assertEqual(a['parts'], b['parts'])

    def test_resident_changes_owner_finish_then_owner_can_restore_and_clear(self):
        self.move_in()
        self.command(self.a, 'bac_ha')
        self.command(self.b, 'kem')
        self.assertEqual(self.mate(self.a)['skins']['living']['w'], 'kem')
        self.command(self.a, 'bac_ha')
        self.assertEqual(self.mate(self.b)['skins']['living']['w'], 'bac_ha')
        self.command(self.b, 'auto')
        self.assertNotIn('w', self.mate(self.a)['skins'].get('living', {}))

    def test_paid_skin_and_receipt_keep_ownership_and_charge_once(self):
        self.move_in()
        before = self.wallet(self.b)
        req = str(uuid.uuid4())
        self.command(self.b, 'hoa_nhi', request=req, confirm=True, n='shared-paid')
        again = self.command(self.b, 'hoa_nhi', request=req, confirm=True, n='shared-paid')
        self.assertTrue(again['replayed'])
        self.assertEqual(self.wallet(self.b), before - dc.SKINS['hoa_nhi']['price'])
        self.assertIn('hoa_nhi', dc.get_free(self.state(self.b))['owned'])
        self.assertNotIn('hoa_nhi', dc.get_free(self.state(self.a))['owned'])
        self.assertEqual(self.mate(self.a)['skins']['living']['w'], 'hoa_nhi')

    def test_concurrent_different_parts_survive(self):
        self.move_in()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.command, self.a, 'bac_ha')
            b = pool.submit(self.command, self.b, 'go_sang', 'floor')
            # A resident write bumps the owner's revision; an older owner command must retry explicitly.
            for future, tok, skin, part in ((a, self.a, 'bac_ha', 'wall'), (b, self.b, 'go_sang', 'floor')):
                try:
                    future.result()
                except GameError as exc:
                    self.assertEqual(exc.code, 'revision_conflict')
                    self.command(tok, skin, part)
        self.assertEqual(self.mate(self.a)['skins']['living'], {'w': 'bac_ha', 'f': 'go_sang'})
        self.assertEqual(self.mate(self.a)['skins'], self.mate(self.b)['skins'])

    def test_transaction_failure_rolls_back_payment_and_both_finishes(self):
        self.move_in()
        before = [self.store.read(t)[:2] for t in (self.a, self.b)]
        with patch('game.home_decor.notify', side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):
                self.command(self.b, 'hoa_nhi', confirm=True)
        self.assertEqual([self.store.read(t)[:2] for t in (self.a, self.b)], before)

    def test_stale_residency_cannot_paint_after_stored_divorce(self):
        self.move_in()
        with self.store.connect() as db:
            db.execute("UPDATE couples SET status='divorced' WHERE id=?", (self.cid,))
        before = self.wallet(self.b)
        with self.assertRaises(GameError):
            self.command(self.b, 'hoa_nhi', confirm=True)
        self.assertEqual(self.wallet(self.b), before)
        self.assertEqual(self.mate(self.b), {})

    def test_reducer_cannot_mirror_finishes_after_clearing_stale_residency(self):
        self.move_in()
        self.command(self.a, 'bac_ha')
        mr._mutate(self.store, {self.sid(self.b): lambda s: s['marriage'].__setitem__('spouse', None)})
        before = [self.store.read(t)[:2] for t in (self.a, self.b)]
        with self.assertRaises(GameError):
            self.command(self.b, 'hoa_nhi', confirm=True)
        self.assertEqual([self.store.read(t)[:2] for t in (self.a, self.b)], before)

    def test_divorce_in_progress_rejects_waiting_paint_without_deadlock(self):
        self.move_in()
        ending, release, starting = threading.Event(), threading.Event(), threading.Event()
        end = family.end
        bond, resident = mr._bond, self.sid(self.b)

        def observed_bond(db, sid):
            result = bond(db, sid)
            if sid == resident and result and result['status'] == 'married':
                starting.set()
            return result

        def held_end(*args, **kwargs):
            ending.set()  # divorce holds its couple lock, before its commit
            if not release.wait(5):
                raise AssertionError('test did not release divorce')
            return end(*args, **kwargs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool, patch.object(family, 'end', held_end), patch.object(mr, '_bond', observed_bond):
            divorced = pool.submit(self.act, self.a, 'divorce', confirm='LY HON')
            self.assertTrue(ending.wait(5))
            painting = pool.submit(self.command, self.b, 'hoa_nhi', confirm=True)
            self.assertTrue(starting.wait(5))
            release.set()
            divorced.result(timeout=10)
            try:
                painting.result(timeout=10)
            except GameError as exc:
                self.assertIn(exc.code, ('not_same_home', 'revision_conflict', 'invalid_action'))
            else:
                # If divorce fully settled before the request began, this must be an ordinary attic
                # command and reject the old living-room id, never update the owner's home.
                self.fail('a living-room paint after divorce must fail')
        self.assertNotIn('hoa_nhi', dc.get_free(self.state(self.a))['owned'])
        self.assertEqual(dc.layout(self.state(self.a))['skins'], {})

    def test_owner_sells_while_resident_paint_waits_then_residency_is_rechecked(self):
        self.move_in()
        a = self.state(self.a)
        home = a['journey']['home']['own']
        moved, _ = act(a, 'jr_home_sell', id=home['id'], confirm=True,
                       value=hs.value_of(home, a['journey']['life_day']))
        found = threading.Event()
        bond = mr._bond
        # Store.command runs on its own worker pool (game/storage.py), not on the caller's
        # thread: mark the painting command by a context variable, which it carries over.
        painter = contextvars.ContextVar('painter', default=False)

        def observed_bond(*args, **kwargs):
            result = bond(*args, **kwargs)
            if painter.get():
                found.set()
            return result

        def paint():
            painter.set(True)
            return self.command(self.b, 'hoa_nhi', confirm=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='paint') as pool:
            with self.store.connect() as db, patch.object(mr, '_bond', observed_bond):
                db.begin()
                db.execute('SELECT revision FROM sessions WHERE sid=? FOR UPDATE', (self.sid(self.a),))
                painting = pool.submit(paint)
                self.assertTrue(found.wait(5))  # looked up couple before the seller committed
                db.execute('UPDATE sessions SET state=?,revision=revision+1 WHERE sid=?',
                           (serialize(moved, None, True), self.sid(self.a)))
                db.commit()
                with self.assertRaises(GameError) as failed:
                    painting.result(timeout=10)
            self.assertEqual(failed.exception.code, 'not_same_home')
        self.assertEqual(self.mate(self.b), {})
        self.assertNotIn('hoa_nhi', dc.get_free(self.state(self.b))['owned'])

    def test_notifications_are_in_optimistic_and_locked_commits_only_once(self):
        self.move_in()
        from game import home_decor
        emit = home_decor.notify
        original_store = self.store._store
        for fallback in (False, True):
            with patch('game.storage.OPTIMISTIC_TRIES', 1), patch.object(self.store, '_store', side_effect=lambda *a, **kw: False if fallback else original_store(*a, **kw)), patch.object(home_decor, 'notify', wraps=emit) as notices:
                request = str(uuid.uuid4())
                revision = self.store.read(self.a)[1]
                payload = dict(item='cay_canh', confirm=True, n=str(uuid.uuid4()))
                self.store.command(self.a, request, revision, None, 'jr_deco_buy', payload)
                self.store.command(self.a, request, revision, None, 'jr_deco_buy', payload)
                self.assertEqual(notices.call_count, 1)
                self.assertEqual(notices.call_args.args[1:], (self.sid(self.a), 'jr_deco_buy'))
