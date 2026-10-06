"""Phase-0 command-path wins keep every save, result and view identical (WP7, split-save spec §8).

* W0a game/settle_scope.py: a moved career is validated with the pieces it did not change skipped;
* W0b work_visits.places before the row lock;
* W0d the save's text as UTF-8 bytes from the SELECT to the UPDATE;
* W0f marriage._mutate validates a stamped save like a command does.

The differential tests run the same commands, from the same save and the same frozen clock, once
with the 1.7.15 paths (full validation of moved careers, places under the lock, str texts) and
once with the new ones, and require byte-identical stored saves, results, views and side tables.
scripts/bench_command.py does the same across two trees on 225 KB / 1.4 MB / 3 MB saves.

Pieces are skipped only with orjson (fastjson.FAST, as on the production server: the vendored
wheel, scripts/vendor_orjson.sh); without it serialize validates every moved career in full, as
1.7.15 did. The tests that need the skip to happen are skipped without orjson; the byte-for-byte
comparisons run either way.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import db as dbm, engine, fastjson as fj, marriage as mr, operations as ops
from game import settle_scope, storage, work_visits, workplace_business as wb
from game.engine import GameError, NPC_INDEX, new_state, validate_career, validate_state

T0 = 2_000_000_000
BUSINESS = ('accounting', 'grocery', 'florist', 'milk_tea', 'repair')


def fixture():
    """A save with staff paid by the clock in a few careers, reviews with comments and a long cash book."""
    s = new_state()
    for cid in BUSINESS:
        c = s['careers'][cid]
        c.update(open=True, started=True)
        add = 5000 - c['money']
        c['money'] += add
        ops.record_money(c, add, 'Góp vốn chủ tiệm', None, 'other_income')
        with mock.patch.object(wb.time, 'time', return_value=T0):
            ops.action(s, c, cid, 'ops_hire', {'candidate': cid + '-staff-1', 'confirm': True})
        npc = next(k for k, v in NPC_INDEX.items() if v['career_id'] == cid)
        for i in range(6):
            post = engine.add_feed(s, c, npc, f'Khách {i} khen quán 🙂 lắm', 'review', stars=5)
            post['comments'] = [dict(author='Khách', text='Ghé lại nha', day=c['day'], npc=npc)]
    with mock.patch.object(wb.time, 'time', return_value=T0):
        wb.settle(s)
    for at in range(T0 + 600, T0 + 3600, 600):
        wb.settle(s, at)
    s['current'] = 'accounting'
    validate_state(s)
    return s


def old_paths():
    """The 1.7.15 command path: every moved career validated in full, the save's places computed
    under the row lock, the text fetched and written as str."""
    serialize_bytes = storage.serialize_bytes
    execute = dbm.PgConnection.execute

    def as_str(*a, **k):
        out = serialize_bytes(*a, **k)
        return out if type(out) is str else out.decode('utf-8')

    def as_text(self, sql, params=(), *, text_bytes=False):
        return execute(self, sql, params)
    return [mock.patch.object(storage, 'SCOPED_CAREERS', False), mock.patch.object(storage, '_places', lambda raw: None),
            mock.patch.object(storage, 'serialize_bytes', as_str), mock.patch.object(dbm.PgConnection, 'execute', as_text)]


class PiecesTests(unittest.TestCase):
    def test_pieces_put_together_are_the_career_json_byte_for_byte(self):
        s = fixture()
        s['careers']['florist']['feed'][0]['text'] = 'Emoji 🌸🌸 và chữ có dấu, "ngoặc" \\ gạch'
        for state in (new_state(), s):
            for cid, c in state['careers'].items():
                out, whole = settle_scope.pieces(c)
                self.assertEqual(whole, fj.dumps_raw(c), cid)
                self.assertEqual(out['ops'], fj.dumps_raw(c['ops']), cid)
                self.assertEqual(out['ops.finance.ledger'], fj.dumps_raw(c['ops']['finance']['ledger']), cid)

    @unittest.skipUnless(fj.FAST, 'scoped validation needs orjson (fastjson.FAST)')
    def test_record_that_cannot_be_cut_is_not_snapshotted(self):
        s = fixture()
        known = fj.loads(storage.serialize(s, None, True))['check']['careers']
        bad = s['careers']['grocery']
        bad['odd.key'] = 1
        with mock.patch.object(wb.time, 'time', return_value=T0 + 99999):
            snap = settle_scope.snapshot(s, known, 'accounting')
        self.assertNotIn('grocery', snap)
        self.assertIn('accounting', snap)

    def test_without_orjson_nothing_is_snapshotted(self):
        s = fixture()
        known = fj.loads(storage.serialize(s, None, True))['check']['careers']
        with mock.patch.object(fj, 'FAST', False), mock.patch.object(wb.time, 'time', return_value=T0 + 99999):
            self.assertEqual(settle_scope.snapshot(s, known, 'accounting'), {})

    def test_only_records_with_their_stored_digest_are_snapshotted(self):
        s = fixture()
        known = fj.loads(storage.serialize(s, None, True))['check']['careers']
        s['careers']['accounting']['xp'] += 1  # edited outside the game: not the record that passed
        with mock.patch.object(wb.time, 'time', return_value=T0 + 99999):
            snap = settle_scope.snapshot(s, known, 'accounting')
        self.assertNotIn('accounting', snap)
        self.assertTrue(set(snap) <= set(BUSINESS))

    def test_grown_cash_book_keeps_its_stored_rows_as_a_prefix(self):
        c = fixture()['careers']['grocery']
        before = settle_scope.pieces(c)[0]
        n = len(c['ops']['finance']['ledger'])
        c['money'] += 7
        ops.record_money(c, 7, 'Khách trả thêm', None, 'revenue')
        same, whole = settle_scope.same(before, c)
        self.assertEqual(whole, fj.dumps_raw(c))
        self.assertEqual(same.prefix, {'ops.finance.ledger': n})
        self.assertNotIn('ops.finance.ledger', same)
        self.assertNotIn('money', same)
        self.assertIn('feed', same)
        self.assertIn('tasks', same)


class ScopedCareerValidationTests(unittest.TestCase):
    def check_same_error(self, c, cid, same):
        with self.assertRaises(GameError) as full:
            validate_career(copy.deepcopy(c), cid)
        with self.assertRaises(GameError) as scoped:
            validate_career(c, cid, same=same)
        self.assertEqual(scoped.exception.message, full.exception.message)
        self.assertEqual(scoped.exception.code, full.exception.code)

    def test_every_record_passes_with_all_or_none_of_its_pieces_same(self):
        s = fixture()
        for cid, c in s['careers'].items():
            out, _ = settle_scope.pieces(c)
            validate_career(c, cid, same=settle_scope.Same(out))
            validate_career(c, cid, same=settle_scope.same(out, c)[0])

    def test_a_broken_changed_piece_fails_with_the_full_validation_message(self):
        s = fixture()
        cases = {
            'feed': lambda c: c['feed'][0].update(stars=9),
            'ops.finance.ledger': lambda c: c['ops']['finance']['ledger'].append(dict(c['ops']['finance']['ledger'][-1], id='x' * 200)),
            'money': lambda c: c.update(money=-5),
            'ops.business': lambda c: c['ops']['business'].update(served=-1),
            'tasks': lambda c: c['tasks'].append(dict(c['tasks'][0], id='florist-0001-99')) if c['tasks'] else c.update(active_task='nope'),
            'journal': lambda c: c['journal'].append(dict(id='j', kind='note', text='', day=1, turn=0)),
            'nan': lambda c: c['life'].update(consumed_cost=float('nan')),
        }
        for name, corrupt in cases.items():
            with self.subTest(name):
                c = copy.deepcopy(s['careers']['florist'])
                before = settle_scope.pieces(c)[0]
                corrupt(c)
                same = settle_scope.same(before, c)[0]
                self.check_same_error(c, 'florist', same)

    def test_an_untouched_open_security_case_is_still_referenced(self):
        """Staging 06/10: settlement moved a career whose security book (with an open case) did not
        move; the skipped case loop left no ids, so 'active' looked dangling ('hồ sơ an ninh sai')."""
        s = fixture()
        c = s['careers']['grocery']
        ops.spawn_case(s, c, 'grocery', 'misplaced')
        validate_career(c, 'grocery')
        self.assertIsNotNone(c['ops']['security']['active'])
        before = settle_scope.pieces(c)[0]
        c['money'] += 7  # what settlement does: money and the cash book move, security does not
        ops.record_money(c, 7, 'Khách trả thêm', None, 'revenue')
        same = settle_scope.same(before, c)[0]
        self.assertIn('ops.security', same)
        self.assertIn('stock', same)
        validate_career(c, 'grocery', same=same)
        validate_career(c, 'grocery', same=settle_scope.Same(settle_scope.pieces(c)[0]))
        # a dangling or duplicated reference is still refused, with the full validation's message
        for corrupt in (lambda sec: sec.update(active='nope'),
                        lambda sec: sec['cases'].append(copy.deepcopy(sec['cases'][-1]))):
            bad = copy.deepcopy(c)
            before = settle_scope.pieces(bad)[0]
            corrupt(bad['ops']['security'])
            self.check_same_error(bad, 'grocery', settle_scope.same(before, bad)[0])

    def test_a_new_cash_book_row_is_checked_after_the_stored_ones(self):
        c = copy.deepcopy(fixture()['careers']['grocery'])
        before = settle_scope.pieces(c)[0]
        c['ops']['finance']['ledger'].append(dict(c['ops']['finance']['ledger'][0]))  # a duplicate id
        c['money'] += c['ops']['finance']['ledger'][0]['amount']
        same = settle_scope.same(before, c)[0]
        self.assertTrue(same.prefix)
        self.check_same_error(c, 'grocery', same)


class DifferentialTests(unittest.TestCase):
    """The same commands with the old and the new paths: byte-identical everything. The scoped path is off by
    default since 06/10 (SCOPED_CAREER_VALIDATION); these tests switch it on to keep it checked."""

    def setUp(self):
        p = mock.patch.object(storage, 'SCOPED_CAREERS', True)
        p.start()
        self.addCleanup(p.stop)
    PLAN = [('settings', None, {'musicVolume': 40}), ('select_career', 'accounting', {}), ('start_day', 'accounting', {}),
            ('more_work', 'accounting', {}), ('ask', 'accounting', {}), ('advance', 'accounting', {}),
            ('settings', None, {'sound': False}), ('business_sync', None, {}), ('advance', 'accounting', {}),
            ('select_career', 'grocery', {}), ('start_day', 'grocery', {}), ('more_work', 'grocery', {}),
            ('end_day', 'accounting', {}), ('settings', None, {'musicVolume': 41})]

    def run_plan(self, start, patches):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = storage.Store(Path(tmp.name) / 'game.db')
        token = 'f' * 64
        sid = store.digest('acct:' + token)
        with store.connect() as db:
            db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', (sid, 'c' * 48, start))
            db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)', ('phase0', 'Phase 0', 'x', sid))
            db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (store.digest(token), sid, 'c' * 48))
        trail, rev, clock = [], 0, [T0 + 4000]
        with mock.patch('time.time', lambda: clock[0]), mock.patch.object(mr, '_new_code', lambda: 'PCC-TEST22'):  # a random public code
            for p in patches:
                p.start()
            try:
                for n, (action, career, payload) in enumerate(self.PLAN):
                    clock[0] += 300
                    payload = dict(payload)
                    try:
                        out = store.command(token, f'req-{n:04d}', rev, career, action, payload, internal=action == 'business_sync')
                        rev = out['revision']
                        trail.append(('ok', out['result'], fj.dumps_raw(out['state'])))
                    except GameError as e:
                        trail.append(('error', e.code, e.message))
                    with store.connect() as db:
                        trail.append(db.execute('SELECT revision,state FROM sessions WHERE sid=?', (sid,)).fetchone()[:])
                        trail.append([tuple(r) for r in db.execute('SELECT kind,target,visibility,data FROM work_visit_places WHERE owner=? ORDER BY kind,target', (sid,))])
                        trail.append([tuple(r) for r in db.execute('SELECT career,kind,seq,row FROM archive WHERE sid=? ORDER BY career,kind,seq', (sid,))])
            finally:
                for p in reversed(patches):
                    p.stop()
        store.close_pool()
        return trail

    def test_commands_store_the_same_bytes_and_answer_the_same(self):
        start = storage.serialize(fixture(), None, True)
        with mock.patch.object(storage, 'FULL_EVERY', 10**6):  # every command on the scoped path
            old = self.run_plan(start, old_paths())
            calls = []
            real = storage.validate_career
            def spy(c, cid, finite=True, same=frozenset()):
                calls.append(bool(same))
                return real(c, cid, finite, same)
            with mock.patch.object(storage, 'validate_career', spy):
                new = self.run_plan(start, [])
        if fj.FAST:
            self.assertTrue(any(calls), 'no career was validated with pieces skipped')
        else:  # without orjson every moved career is validated in full (see the module doc)
            self.assertTrue(calls and not any(calls))
        self.assertEqual(len(old), len(new))
        for a, b in zip(old, new):
            self.assertEqual(a, b)
        self.assertTrue(any(isinstance(x, list) and x and x[0][0] == 'career' for x in new), 'work-visit places were written')

    def test_open_security_cases_on_settled_careers_answer_the_same(self):
        """Settled careers (staff paid by the clock) holding an open security case: the scoped path must not
        refuse what the full validation accepts (staging 06/10, 'Tham chiếu hồ sơ an ninh sai.')."""
        s = fixture()
        for cid in BUSINESS:
            ops.spawn_case(s, s['careers'][cid], cid, 'misplaced')
        validate_state(s)
        start = storage.serialize(s, None, True)
        with mock.patch.object(storage, 'FULL_EVERY', 10**6):
            old = self.run_plan(start, old_paths())
            new = self.run_plan(start, [])
        self.assertFalse([x for x in new if isinstance(x, tuple) and x and x[0] == 'error' and 'an ninh' in x[2]])
        self.assertTrue(any(isinstance(x, tuple) and x and x[0] == 'ok' for x in new))
        self.assertEqual(old, new)

    def test_unstamped_and_periodic_commands_are_unchanged_too(self):
        s = fixture()
        start = json.dumps(s, ensure_ascii=False, separators=(',', ':'))  # no stamp: the first command validates all
        with mock.patch.object(storage, 'FULL_EVERY', 3):
            old = self.run_plan(start, old_paths())
            new = self.run_plan(start, [])
        self.assertEqual(old, new)


class BytesTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = storage.Store(Path(self.tmp.name) / 'game.db')

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def test_utf8_text_round_trips_as_text(self):
        text = json.dumps({'a': 'Phố Có Chuyện 🙂   "x"'}, ensure_ascii=False)
        with self.store.connect() as db:
            db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', ('s1', 'c', dbm.Utf8Text(text.encode())))
            self.assertEqual(db.execute('SELECT state FROM sessions WHERE sid=?', ('s1',)).fetchone()[0], text)
            got = db.execute('SELECT state,csrf FROM sessions WHERE sid=?', ('s1',), text_bytes=True).fetchone()
        self.assertEqual(got[0], text.encode())
        self.assertEqual(got[1], b'c')
        self.assertEqual(fj.loads(got[0]), json.loads(text))
        self.assertEqual(fj.loads(dbm.Utf8Text(text.encode())), json.loads(text))

    def test_serialize_bytes_is_serialize_and_a_lone_surrogate_stays_a_str(self):
        s = fixture()
        self.assertEqual(storage.serialize_bytes(copy.deepcopy(s), None, True).decode(), storage.serialize(s, None, True))
        s['name'] = 'Mây\ud800'
        out = storage.serialize_bytes(s, None, True)
        self.assertIs(type(out), str)
        self.assertEqual(out, storage.serialize(s, None, True))

    def test_fresh_marker_as_bytes_is_a_new_save(self):
        self.assertEqual(self.store.parse_state(b'', 'x')['careers'].keys(), self.store.parse_state('', 'x')['careers'].keys())


class MutateTests(unittest.TestCase):
    """marriage._mutate (bank transfers, weddings, couples, quầy hire, work visits)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = storage.Store(Path(self.tmp.name) / 'game.db')
        self.start = storage.serialize(fixture(), None, True)
        with self.store.connect() as db:
            for sid in ('a', 'b'):
                db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', (sid, 'c', self.start))

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def stored(self, sid):
        with self.store.connect() as db:
            return db.execute('SELECT revision,state FROM sessions WHERE sid=?', (sid,)).fetchone()[:]

    @staticmethod
    def change(s):
        mr._apply_effect(s, dict(id='gift:1', kind='wallet', amount=25, label='Quà cưới', data='{}'))
        c = s['careers']['grocery']
        c['money'] += 3
        ops.record_money(c, 3, 'Tiền mừng', None, 'other_income')

    def test_stamped_save_is_validated_like_a_command_and_stored_the_same(self):
        calls = []
        real = storage.validate_career
        with mock.patch.object(storage, 'validate_career', lambda *a, **k: calls.append(1) or real(*a, **k)), \
                mock.patch.object(engine, 'validate_career', lambda *a, **k: calls.append(2) or real(*a, **k)):
            mr._mutate(self.store, {'a': self.change})
        self.assertEqual(calls, [1])  # only the career fn changed, not 41
        with mock.patch.object(storage, 'FULL_EVERY', 1):  # every revision a full check: the 1.7.15 path
            mr._mutate(self.store, {'b': self.change})
        self.assertEqual(self.stored('a'), self.stored('b'))

    def test_a_broken_change_is_refused_on_both_paths(self):
        def broken(s):
            self.change(s)
            s['careers']['grocery']['money'] = -1
        for every in (10**6, 1):
            with self.subTest(every=every), mock.patch.object(storage, 'FULL_EVERY', every):
                with self.assertRaises(GameError):
                    mr._mutate(self.store, {'a': broken})
        self.assertEqual(self.stored('a'), (0, self.start))

    def test_rentals_hook_reads_the_life_day_before_the_change(self):
        seen = []
        from game import rentals
        with mock.patch.object(rentals, 'command_commit', lambda db, sid, before, after, action: seen.append(before)):
            mr._mutate(self.store, {'a': self.change})
        self.assertEqual(seen, [dict(journey=dict(life_day=json.loads(self.start)['journey']['life_day']))])


if __name__ == '__main__':
    unittest.main()
