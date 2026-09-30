"""Nothing a player made is lost: rows cut from the save's lists go to the archive table,
in the same transaction as the save (game/archive.py, game/storage.py)."""
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import game.engine as E
import game.operations as O
from game.storage import Store
from tests.helpers import Journey


class StoreJourney(Journey):
    """The test solvers, played through Store.command like the real client."""

    def __init__(self, store, career):
        self.store, self.career = store, career
        self.token, _, _ = store.session()
        self.rev = 0
        self.act('select_career')

    def act(self, action, **payload):
        out = self.store.command(self.token, secrets.token_hex(8), self.rev, self.career, action, payload)
        self.rev = out['revision']
        self.state, _, _ = self.store.read(self.token)
        return out['result']


def everything(store, token, career, kind, limit=7):
    """All rows of a history through the paging API, oldest first (checks the paging too)."""
    rows, before, seen = [], None, set()
    while True:
        page = store.archive_page(token, career, kind, before=before, limit=limit)
        for r in page['rows']:
            assert r['pos'] not in seen
            seen.add(r['pos'])
        rows.extend(page['rows'])
        if page['before'] is None:
            break
        before = page['before']
    assert sorted(seen) == list(range(page['total'])), (len(seen), page['total'])
    return [r['row'] for r in reversed(rows)]


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'game.db')
        # small caps so that a short session overflows every list many times
        self.caps = [mock.patch.object(E, 'JOURNAL_KEPT', 12), mock.patch.object(E, 'FEED_KEPT', 4),
                     mock.patch.object(O, 'LEDGER_HIGH', 9), mock.patch.object(O, 'LEDGER_KEEP', 5),
                     mock.patch.object(O, 'LEDGER_DAYS', 0)]
        for p in self.caps:
            p.start()
        # every row the game ever creates, in order
        self.made = dict(journal=[], ledger=[], feed=[])
        log, record_money, add_feed = E.log, O.record_money, E.add_feed

        def spy_log(s, c, *a, **k):
            lid = log(s, c, *a, **k)
            self.made['journal'].append(lid)
            return lid

        def spy_money(c, *a, **k):
            record_money(c, *a, **k)
            self.made['ledger'].append(c['ops']['finance']['ledger'][-1]['id'])

        def spy_feed(*a, **k):
            post = add_feed(*a, **k)
            self.made['feed'].append(post['id'])
            return post
        for p in (mock.patch.object(E, 'log', spy_log), mock.patch.object(O, 'record_money', spy_money),
                  mock.patch.object(E, 'add_feed', spy_feed)):
            p.start()
            self.caps.append(p)

    def tearDown(self):
        for p in self.caps:
            p.stop()
        self.tmp.cleanup()

    def play(self, career='milk_tea', days=4):
        j = StoreJourney(self.store, career)
        self.opening = j.c['ops']['finance']['opening_balance']
        j.act('start_day')
        for _ in range(days):
            for _ in range(4):
                todo = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
                if not todo:
                    break
                j.solve(todo[0]['id'])
            j.act('end_day')
            j.act('start_day')
        return j

    def test_long_session_loses_nothing(self):
        j = self.play()
        c = j.c
        self.assertEqual(len(c['journal']), 12)
        # a review of a group's first cup is taken back when the group waits: kept apart
        retracted = [r['row']['id'] for r in self.store.archive_export(j.token) if r['kind'] == 'feed.retracted']
        for kind in ('journal', 'ledger', 'feed'):
            ids = [r['id'] for r in everything(self.store, j.token, 'milk_tea', kind)]
            self.assertGreater(len(ids), 10, kind)
            made = [x for x in self.made[kind] if x not in retracted]
            self.assertEqual(ids, made, kind)  # archive + save == every row ever made, in order
        self.assertEqual(set(retracted) | set(ids), set(self.made['feed']))

    def test_money_identities_hold_with_archived_rows(self):
        j = self.play()
        c = j.c
        f = c['ops']['finance']
        self.assertEqual(f['opening_balance'] + sum(r['amount'] for r in f['ledger']), c['money'])
        rows = everything(self.store, j.token, 'milk_tea', 'ledger')
        self.assertGreater(len(rows), len(f['ledger']))
        self.assertEqual(self.opening + sum(r['amount'] for r in rows), c['money'])
        validate = E.validate_state
        validate(j.state)

    def test_export_includes_the_archive_and_import_restores_it(self):
        j = self.play(days=2)
        dump = self.store.archive_export(j.token)
        self.assertTrue(any(r['kind'] == 'journal' for r in dump))
        backup = dict(format='mot-ngay-lam-nghe/save-v4', state=j.state, archive=dump)
        other = StoreJourney(self.store, 'milk_tea')
        other.act('import_save', save=json.loads(json.dumps(backup)))
        # the backup's archive comes back first, then (its migration may move more) its own rows
        mine = [r for r in self.store.archive_export(other.token) if r['kind'] != 'replaced_save']
        strip = lambda rows: [(r['career'], r['kind'], r['seq'], r['day'], r['row']) for r in rows]
        self.assertEqual(strip([r for r in mine if (r['kind'], r['seq']) in {(x['kind'], x['seq']) for x in dump}]), strip(dump))
        for kind, path in (('journal', ('journal',)), ('ledger', ('ops', 'finance', 'ledger'))):
            node = j.state['careers']['milk_tea']
            for k in path:
                node = node[k]
            want = [r['row'] for r in dump if r['kind'] == kind] + node
            self.assertEqual(everything(self.store, other.token, 'milk_tea', kind), want, kind)
        # the save the backup replaced is kept whole
        replaced = [r for r in self.store.archive_export(other.token) if r['kind'] == 'replaced_save']
        self.assertEqual(len(replaced), 1)
        self.assertIn('careers', replaced[0]['row'])

    def test_bad_archive_in_a_backup_is_rejected(self):
        j = self.play(days=1)
        for bad in ([dict(career='nope', kind='journal', row={})], [dict(career='milk_tea', kind='', row={})], 'x',
                    [dict(career='milk_tea', kind='journal')]):
            with self.assertRaises(E.GameError):
                j.act('import_save', save=dict(format='mot-ngay-lam-nghe/save-v4', state=j.state, archive=bad))

    def test_deleting_the_save_deletes_its_archive(self):
        j = self.play(days=1)
        with self.store.connect() as db:
            self.assertTrue(db.execute('SELECT COUNT(*) FROM archive').fetchone()[0])
        self.store.delete(j.token)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM archive').fetchone()[0], 0)

    def test_paging_newest_first_with_skip_and_before(self):
        j = self.play(days=2)
        full = everything(self.store, j.token, 'milk_tea', 'journal')
        first = self.store.archive_page(j.token, 'milk_tea', 'journal', skip=5, limit=3)
        self.assertEqual([r['row'] for r in first['rows']], list(reversed(full[-8:-5])))
        nxt = self.store.archive_page(j.token, 'milk_tea', 'journal', before=first['before'], limit=3)
        self.assertEqual([r['row'] for r in nxt['rows']], list(reversed(full[-11:-8])))
        with self.assertRaises(E.GameError):
            self.store.archive_page(j.token, 'bogus', 'journal')

    def test_nothing_is_archived_when_the_save_write_loses_the_race(self):
        j = self.play(days=1)
        with self.store.connect() as db:
            n = db.execute('SELECT COUNT(*) FROM archive').fetchone()[0]
        sid = self.store.key(j.token)
        ok = self.store._store(sid, j.rev - 1, '{}', 'req-race-0001', 'x' * 64, '{}', [('milk_tea', 'journal', 1, '{}')])
        self.assertFalse(ok)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM archive').fetchone()[0], n)

    def test_reset_keeps_the_old_career_in_the_archive(self):
        j = self.play(days=1)
        money = j.c['money']
        j.act('reset_career', confirm='BAT DAU LAI')
        rows = [r for r in self.store.archive_export(j.token) if r['kind'] == 'reset']
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['career'], rows[0]['row']['money']), ('milk_tea', money))


class OlderSaveTests(unittest.TestCase):
    def test_long_journal_of_an_older_save_moves_to_the_archive_once(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 'game.db')
        token, _, _ = store.session()
        s, _, _ = store.read(token)
        c = s['careers']['grocery']
        c['journal'] = [dict(id=f'log-{i}', kind='fact', text=f'row {i}', npc=None, ref=None, day=1, turn=0) for i in range(1200)]
        E.validate_state(s)
        with store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), store.key(token)))
        store.command(token, 'req-older-0001', 0, 'milk_tea', 'select_career', {})
        saved, _, _ = store.read(token)
        self.assertEqual(len(saved['careers']['grocery']['journal']), E.JOURNAL_KEPT)
        rows = everything(store, token, 'grocery', 'journal', limit=200)
        self.assertEqual([r['text'] for r in rows], [f'row {i}' for i in range(1200)])


class ArchiveHTTPTests(unittest.TestCase):
    def test_export_and_paging_over_http(self):
        import http.client
        import os
        import threading
        from server import GameServer
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        server = GameServer(('127.0.0.1', 0), Store(Path(tmp.name) / 'state.db'))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        quiet = mock.patch.dict(os.environ, {'QUIET': '1'})
        quiet.start()
        self.addCleanup(quiet.stop)
        cookie = None

        def req(path, method='GET', body=None, csrf=None):
            h = {'Host': f'127.0.0.1:{server.server_port}'}
            if cookie:
                h['Cookie'] = cookie
            if csrf:
                h['X-Game-CSRF'] = csrf
            if body is not None:
                h['Content-Type'] = 'application/json'
                body = json.dumps(body)
            con = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            con.request(method, path, body=body, headers=h)
            res = con.getresponse()
            out = res.status, dict(res.getheaders()), res.read()
            con.close()
            return out
        self.assertEqual(req('/api/archive?career=milk_tea&kind=journal')[0], 401)  # the owner's session only
        status, headers, body = req('/api/bootstrap')
        cookie = headers['Set-Cookie'].split(';')[0]
        csrf = json.loads(body)['csrf']
        rev = 0
        with mock.patch.object(E, 'JOURNAL_KEPT', 3):
            for i, action in enumerate(['select_career'] + ['start_day', 'advance', 'end_day'] * 4):
                status, _, body = req('/api/command', 'POST', dict(request_id=f'http-arch-{i:03d}', expected_revision=rev,
                                                                   career='milk_tea', action=action, payload={}), csrf)
                self.assertEqual(status, 200, body)
                rev = json.loads(body)['revision']
        status, _, body = req('/api/archive?career=milk_tea&kind=journal&skip=3&limit=2')
        page = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(len(page['rows']), 2)
        self.assertGreater(page['total'], 5)
        self.assertEqual([r['pos'] for r in page['rows']], [page['total'] - 4, page['total'] - 5])
        status, _, body = req(f"/api/archive?career=milk_tea&kind=journal&before={page['before']}&limit=200")
        rest = json.loads(body)
        self.assertEqual(rest['before'], None)
        self.assertEqual(rest['rows'][-1]['pos'], 0)
        self.assertEqual(req('/api/archive?career=milk_tea&kind=journal&before=x')[0], 400)
        status, _, body = req('/api/save/export')
        dump = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(any(r['kind'] == 'journal' for r in dump['archive']))


if __name__ == '__main__':
    unittest.main()


class ClearedChat(unittest.TestCase):
    def test_cleared_chat_is_erased_from_the_archive_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'game.db')
            p = StoreJourney(store, 'milk_tea')
            npc = next(n['id'] for n in E.NPCS if n['career_id'] == 'milk_tea')
            for i in range(30):  # 60 messages: more than the 40 kept in the save
                p.act('talk', npc=npc, text=f'chào {i}')
            with store.connect() as db:
                kept = db.execute("SELECT COUNT(*) FROM archive WHERE kind=?", ('chat:' + npc,)).fetchone()[0]
            self.assertGreater(kept, 0)
            p.act('chat_clear', npc=npc)
            self.assertNotIn(npc, p.state['careers']['milk_tea']['chats'])
            with store.connect() as db:
                left = db.execute("SELECT COUNT(*) FROM archive WHERE kind=?", ('chat:' + npc,)).fetchone()[0]
            self.assertEqual(left, 0)


class SaveSizeTests(unittest.TestCase):
    """v0.9.5 keeps less in the save (finished jobs, their ids, board posts, journal, cash
    book, bills, day recaps) and routes every list that used to drop rows silently into
    the archive: what the save keeps plus what the archive holds is the whole history."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'game.db')

    def patch(self, *patches):
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_finished_jobs_and_their_ids(self):
        made, paid = {}, []  # every job that was ever in the save, every id marked paid
        done = E.mark_done

        def spy_done(c, tid):
            if tid not in c['completed_ids']:
                paid.append(tid)
            done(c, tid)
        self.patch(mock.patch.object(E, 'DONE_KEPT', 2), mock.patch.object(E, 'DONE_MAX', 3),
                   mock.patch.object(E, 'COMPLETED_IDS_KEPT', 4),
                   mock.patch.object(E, 'mark_done', spy_done))
        j = StoreJourney(self.store, 'milk_tea')
        act = j.act

        def watched(action, **payload):
            out = act(action, **payload)
            made.update((t['id'], None) for t in j.c['tasks'])
            return out
        j.act = watched
        j.act('start_day')
        for _ in range(4):
            for _ in range(4):
                todo = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
                if not todo:
                    break
                j.solve(todo[0]['id'])
            j.act('end_day')
            j.act('start_day')
        c = j.c
        done_ids = [t['id'] for t in c['tasks'] if t['status'] in ('completed', 'referred', 'cancelled')]
        self.assertLessEqual(len(done_ids), 3)
        archived = [r['row']['id'] for r in self.store.archive_export(j.token) if r['kind'] == 'tasks']
        self.assertGreater(len(archived), 5)
        everyone = archived + [t['id'] for t in c['tasks']]
        self.assertEqual(sorted(everyone), sorted(made))  # every job ever in the save, once
        self.assertEqual(len(set(everyone)), len(everyone))
        ids = [r['row'] for r in self.store.archive_export(j.token) if r['kind'] == 'completed_ids']
        self.assertEqual(len(c['completed_ids']), 4)
        self.assertEqual(ids + c['completed_ids'], paid)  # in order
        E.validate_state(j.state)
        # a backup carries them: imported elsewhere, the same history comes back
        dump = self.store.archive_export(j.token)
        other = StoreJourney(self.store, 'milk_tea')
        other.act('import_save', save=json.loads(json.dumps(dict(format='mot-ngay-lam-nghe/save-v4', state=j.state, archive=dump))))
        back = [r for r in self.store.archive_export(other.token) if r['kind'] in ('tasks', 'completed_ids')]
        self.assertEqual([(r['kind'], r['row']) for r in back], [(r['kind'], r['row']) for r in dump if r['kind'] in ('tasks', 'completed_ids')])
        self.assertEqual([t['id'] for t in other.state['careers']['milk_tea']['tasks']], [t['id'] for t in c['tasks']])

    def test_board_posts_move_to_the_archive_and_page_back(self):
        from game import board as bd
        from game import board_ai
        from game import journey as jr
        made = []
        new_post = bd._new_post

        def spy(*a, **k):
            p = new_post(*a, **k)
            made.append(p['id'])
            return p
        self.patch(mock.patch.object(bd, '_new_post', spy))
        # an older save: 120 posts kept by the previous build
        with mock.patch.object(bd, 'POSTS_MAX', 120):
            s = E.new_state()
            jr.enable_story(s, 99)
            s['journey'].update(gender='female', intro=True)
            s, _ = E.apply_action(s, 'milk_tea', 'select_career', {})
            s, _ = E.apply_action(s, 'milk_tea', 'talk', dict(npc='milk_tea_npc_01', text='chào'))
            for _ in range(30):
                s['journey']['life_day'] += 1
                for _ in range(35):
                    bd.after(s, 'milk_tea', 'talk', {})
            self.assertEqual(len(s['journey']['board']['posts']), 120)
            E.validate_state(s)
        lost = made[:-120]  # cut by that build before the archive existed: not this test's business
        token, _, _ = self.store.session()
        self.store.read(token)
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), self.store.key(token)))
        self.store.command(token, 'req-board-0001', 0, None, 'settings', dict(sound=False))
        saved, _, _ = self.store.read(token)
        self.assertEqual(len(saved['journey']['board']['posts']), bd.POSTS_MAX)
        # page the feed like the client: the save's posts, then the archive, read only
        older = lambda before, limit: self.store.archive_tail(token, '', 'board.posts', before, limit)
        view = board_ai.get_view(saved, {}, older)['board']
        seen, pages = list(view['posts']), 0
        while view['older']:
            q = dict(before=seen[-1]['seq'])
            if view.get('apos') is not None:
                q['apos'] = view['apos']
            view = board_ai.get_view(saved, q, older)['board']
            seen += view['posts']
            pages += 1
        self.assertGreaterEqual(pages, 3)
        self.assertEqual([p['id'] for p in reversed(seen)], [x for x in made if x not in lost])
        self.assertTrue(all(p.get('archived') for p in seen[bd.POSTS_MAX:]))
        self.assertFalse(any(p.get('archived') for p in seen[:bd.POSTS_MAX]))

    def test_silent_caps_now_archive(self):
        from game import archive as ar
        from game import closeness as qn
        from game import journey as jr
        s = E.new_state()
        jr.enable_story(s, 5)
        self.patch(mock.patch.object(qn, 'LOG_MAX', 5))
        with ar.collect() as box:
            for i in range(12):
                qn.change(s, 'ba_tam', 1, f'dòng {i}', 'work')
        rows = [r for _, kind, r in box.rows if kind == 'closeness.log'] + s['journey']['closeness']['log']
        self.assertEqual([r['text'] for r in rows], [f'dòng {i}' for i in range(12)])

    def test_older_save_moves_its_overflow_once_and_money_still_adds_up(self):
        token, _, _ = self.store.session()
        s, _, _ = self.store.read(token)
        c = s['careers']['grocery']
        c.update(day=60, started=True)
        f = c['ops']['finance']
        f['ledger'] = [dict(id=f'entry-{i}', day=1 + i // 8, turn=0, amount=1, category='revenue', reason=f'r{i}', ref=None) for i in range(400)]
        c['money'] = f['opening_balance'] + 400
        f['bills'] = [dict(id=f'utility-{i}', kind='utility', label=f'Điện nước · ngày {i}', amount=5, due=i + 1, created_day=i,
                           status='paid', source=f'day-{i}', extended=False, paid_day=i + 1) for i in range(1, 300)]
        c['completed_ids'] = [f'grocery-{d:04d}-00' for d in range(1, 251)]
        c['journal'] = [dict(id=f'log-{i}', kind='fact', text=f'row {i}', npc=None, ref=None, day=1, turn=0) for i in range(300)]
        E.validate_state(s)
        opening, money = f['opening_balance'], c['money']
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), self.store.key(token)))
        self.store.command(token, 'req-older-0002', 0, None, 'settings', dict(sound=False))
        saved, _, _ = self.store.read(token)
        c = saved['careers']['grocery']
        f = c['ops']['finance']
        dump = self.store.archive_export(token)
        rows = lambda kind: [r['row'] for r in dump if r['career'] == 'grocery' and r['kind'] == kind]
        self.assertEqual(len(c['journal']), E.JOURNAL_KEPT)
        self.assertEqual([r['text'] for r in rows('journal') + c['journal']], [f'row {i}' for i in range(300)])
        self.assertLessEqual(len(f['ledger']), O.LEDGER_KEEP)
        self.assertEqual([r['id'] for r in rows('ledger') + f['ledger']], [f'entry-{i}' for i in range(400)])
        self.assertEqual(f['opening_balance'] + sum(r['amount'] for r in f['ledger']), c['money'])
        self.assertEqual(opening + sum(r['amount'] for r in rows('ledger') + f['ledger']), money)
        self.assertEqual(c['money'], money)
        self.assertEqual(len([b for b in f['bills'] if b['status'] == 'paid']), O.BILLS_PAID)
        self.assertEqual([b['id'] for b in rows('bills') + f['bills']], [f'utility-{i}' for i in range(1, 300)])
        self.assertEqual(rows('completed_ids') + c['completed_ids'], [f'grocery-{d:04d}-00' for d in range(1, 251)])
        self.assertEqual(len(c['completed_ids']), E.COMPLETED_IDS_KEPT)
        # moved once: another command archives nothing more of these kinds
        n = len(dump)
        self.store.command(token, 'req-older-0003', 1, None, 'settings', dict(sound=True))
        self.assertEqual(len([r for r in self.store.archive_export(token) if r['kind'] in ('journal', 'ledger', 'bills', 'completed_ids')]),
                         len([r for r in dump if r['kind'] in ('journal', 'ledger', 'bills', 'completed_ids')]))
        self.assertGreaterEqual(len(self.store.archive_export(token)), n)
