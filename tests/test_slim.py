"""💤 Cold careers keep a slim record (game/slim.py), only through the night job's internal command (player commands
never compact): nothing is lost (archived rows + rows in the save == before), the wallet still matches the cash book,
the lãi/lỗ chart keeps its days, every list's first screen shows the same rows, and only cold careers are touched.
scripts/slim_saves.py walks the big saves and compacts them through Store.save_command."""
import base64
import importlib.util
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path

import game.archive as ar
import game.engine as E
import game.slim as S
from game.storage import Conflict, Store, serialize
from tests.test_archive import everything

CID = 'milk_tea'
HERE = 'mother_baby'
PNG = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + bytes(range(40))).decode()
ROOT = Path(__file__).resolve().parents[1]


def cold_state(day=12, rows=120, photos=6, lines=100, warm=()):
    """A save whose CID career has a long cash book, six photos and a full journal, and a journey whose last
    COLD_DAYS days were spent at HERE (and `warm`)."""
    s = E.new_state()
    s['current'] = HERE
    c = s['careers'][CID]
    c.update(started=True, day=day, open=False)
    f = c['ops']['finance']
    ledger = []
    for i in range(rows):
        d = 1 + i * day // rows      # oldest first, every day 1..day
        c['ops']['seq'] += 1
        ledger.append(dict(id=f"entry-{c['ops']['seq']}", day=d, turn=i % 30, amount=(i % 7 - 3) * 11 or 5,
                           category=('stock', 'revenue', 'wage', 'tip')[i % 4], reason=f'Dòng {i}', ref=None))
    f['ledger'] = ledger
    f['opening_balance'] = c['money'] - sum(r['amount'] for r in ledger)
    c['album'] = [dict(id=f'photo-{n}', image=PNG, day=day, title=f'Ảnh {n}') for n in range(photos, 0, -1)]  # newest first
    c['journal'] = [dict(id=f'log-{n}', kind='money', text=f'Dòng sổ {n}', npc=None, ref=None, day=1 + n * day // lines, turn=n % 20)
                    for n in range(lines)]
    c['life']['activity_history'] = [dict(id=f'act-{n}', spec='x', day=1, score=n, practice=False, reward=0) for n in range(45)]
    tail = [HERE, *warm]
    s['journey']['days'] = [dict(d=n + 1, c=tail[n % len(tail)], m='normal') for n in range(S.COLD_DAYS)]
    E.validate_state(s)
    return s


def lists(c):
    """What compaction may change (a command's settlement may touch the rest of a record)."""
    return json.dumps([c['ops']['finance'], c['album'], c['journal'], c['life'], c['ext'].get('slim')], sort_keys=True)


def run(s, payload=None):
    """The night command as the storage layer runs it: (new save, the archived (owner, kind, row))."""
    with ar.collect() as box:
        out, _ = E.apply_action(s, None, S.ACTION, payload or {}, internal=True, owned=True)
    return out, box.rows


def player(s, career=HERE):
    """A player's command, as the storage layer runs it (inside a collector)."""
    with ar.collect() as box:
        out, _ = E.apply_action(s, career, 'settings', {'musicVolume': 41}, owned=True)
    return out, box.rows


class SlimUnitTests(unittest.TestCase):
    def test_cold_career_is_compacted_and_nothing_is_lost(self):
        s = cold_state()
        before = json.loads(json.dumps(s['careers'][CID]))
        s, cut = run(s)
        c = s['careers'][CID]
        moved = {k: [r for o, kk, r in cut if o == CID and kk == k] for k in ('ledger', 'album', 'journal')}
        # every row is either still in the save or in the archive, in the same order
        self.assertEqual(moved['ledger'] + c['ops']['finance']['ledger'], before['ops']['finance']['ledger'])
        self.assertEqual(moved['journal'] + c['journal'], before['journal'])
        self.assertEqual(len(moved['journal']), 20)
        # the photos stay (the Kỷ niệm sheet shows all six on open)
        self.assertEqual(moved['album'], [])
        self.assertEqual(c['album'], before['album'])
        # the cash book still adds up to the wallet; the cut rows went into the opening balance
        f = c['ops']['finance']
        self.assertEqual(f['opening_balance'] + sum(r['amount'] for r in f['ledger']), c['money'])
        self.assertEqual(f['opening_balance'], before['ops']['finance']['opening_balance'] + sum(r['amount'] for r in moved['ledger']))
        self.assertGreaterEqual(len(f['ledger']), S.LEDGER_KEEP)
        self.assertTrue(all(r['day'] < c['day'] - 1 for r in moved['ledger']))
        # the chart's days keep their sums, per category and sign
        want = {}
        for r in moved['ledger']:
            if r['day'] >= c['day'] - S.CHART_DAYS:
                x = want.setdefault(str(r['day']), {}).setdefault(r['category'], [0, 0, 0])
                x[0 if r['amount'] >= 0 else 1] += r['amount']
                x[2] += 1
        self.assertEqual(f['day_sums'], want)
        self.assertEqual(c['ext']['slim'], dict(ledger=len(moved['ledger']), journal=20, life=35))
        E.validate_state(s)
        # life histories nothing shows keep their newest rows
        self.assertEqual([r for o, k, r in cut if o == CID and k == 'life.activities'] + c['life']['activity_history'],
                         before['life']['activity_history'])
        self.assertEqual(len(c['life']['activity_history']), S.LIFE_KEEP)
        # the view says what moved (the client keeps "Xem cũ hơn" on the shortened lists)
        view = E.public_state(json.loads(json.dumps(s)), full=CID)
        self.assertEqual(view['careers'][CID]['slim'], c['ext']['slim'])
        self.assertIn('day_sums', view['careers'][CID]['ops']['finance'])

    def test_first_screens_show_the_same_rows(self):
        """Sổ dòng tiền: the newest 24 rows and its header count (rows in the save + moved ones); Sổ tay: the newest
        80; Kỷ niệm: the six photos."""
        s = cold_state(rows=150)
        old = json.loads(json.dumps(s['careers'][CID]))
        s, _ = run(s)
        view = E.public_state(json.loads(json.dumps(s)), full=CID)['careers'][CID]
        f, was = view['ops']['finance'], old['ops']['finance']
        self.assertEqual(f['ledger'][-24:], was['ledger'][-24:])
        self.assertEqual(len(f['ledger']) + view['slim']['ledger'], len(was['ledger']))
        self.assertEqual(view['journal'][-80:], old['journal'][-80:])
        self.assertEqual(len(view['journal']), 80)
        self.assertEqual(view['album'], old['album'])

    def test_player_commands_never_compact(self):
        for career in (HERE, CID):
            s = cold_state()
            snap = lists(s['careers'][CID])
            s, cut = player(s, career)
            self.assertEqual([x for x in cut if x[0] == CID], [], career)
            self.assertEqual(lists(s['careers'][CID]), snap, career)

    def test_only_the_server_sends_it(self):
        with self.assertRaises(E.GameError) as e:
            E.apply_action(cold_state(), None, S.ACTION, {}, owned=True)
        self.assertEqual(e.exception.code, 'forbidden')

    def test_a_second_night_finds_nothing(self):
        s, _ = run(cold_state())
        snap = lists(s['careers'][CID])
        with self.assertRaises(E.GameError) as e:
            run(s)
        self.assertEqual(e.exception.code, 'slim_nothing')
        self.assertEqual(lists(s['careers'][CID]), snap)

    def test_it_settles_nothing(self):
        """Staff work, fees and the rest wait for the player's next command: only the lists move."""
        s = E.migrate_state(cold_state(), owned=True)   # (a stored save is migrated already)
        here = json.dumps(s['careers'][HERE], sort_keys=True)
        rest = {k: json.dumps(v, sort_keys=True) for k, v in s.items() if k != 'careers'}
        s, _ = run(s)
        self.assertEqual(json.dumps(s['careers'][HERE], sort_keys=True), here)
        self.assertEqual({k: json.dumps(v, sort_keys=True) for k, v in s.items() if k != 'careers'}, rest)

    def test_warm_current_and_short_journeys_are_left_alone(self):
        for case in ('recent', 'current', 'short', 'no_collector'):
            s = cold_state(warm=(CID,) if case == 'recent' else ())
            if case == 'current':
                s['current'] = CID
            if case == 'short':
                s['journey']['days'] = s['journey']['days'][:S.COLD_DAYS - 1]
            snap = lists(s['careers'][CID])
            if case == 'no_collector':   # a copy or a preview: helpers only slice, so nothing may be cut
                with self.assertRaises(E.GameError):
                    E.apply_action(s, None, S.ACTION, {}, internal=True, owned=True)
            else:
                with self.assertRaises(E.GameError):
                    run(s)
            self.assertEqual(lists(s['careers'][CID]), snap, case)

    def test_open_shift_and_desk_jobs_keep_their_rows(self):
        s = cold_state()
        c = s['careers'][CID]
        c['open'] = True
        # a row of an old day that belongs to a job still on the desk stops the cut there
        c['ops']['finance']['ledger'][10]['ref'] = 'milk_tea-0001-03'
        c['tasks'] = [dict(id='milk_tea-0001-03')]
        rows = list(c['ops']['finance']['ledger'])
        self.assertEqual(S.ledger(c, CID), 10)
        self.assertEqual(c['ops']['finance']['ledger'], rows[10:])
        # open: today's journal rows stay
        c['journal'][-90:] = [dict(r, day=c['day']) for r in c['journal'][-90:]]
        S.journal(c, CID)
        self.assertEqual(len(c['journal']), 90)

    def test_per_command_limit(self):
        s = cold_state()
        extra = [cid for cid in s['careers'] if cid not in (CID, HERE)][:5]
        for cid in extra:
            c = s['careers'][cid]
            c['started'] = True
            c['life']['activity_history'] = [dict(id=f'act-{n}', spec='x', day=1, score=n, practice=False, reward=0) for n in range(45)]
        E.validate_state(s)
        self.assertEqual(len(S.plan(s)), 6)
        with ar.collect():
            _, out = E.apply_action(s, None, S.ACTION, {'careers': 4}, internal=True, owned=True)
        self.assertEqual((len(out['slim']['careers']), out['slim']['left']), (4, 2))
        with ar.collect():
            _, out = E.apply_action(s, None, S.ACTION, {'careers': 4}, internal=True, owned=True)
        self.assertEqual((len(out['slim']['careers']), out['slim']['left']), (2, 0))
        self.assertEqual(S.plan(s), [])

    def test_validation_refuses_bad_marks(self):
        s, _ = run(cold_state())
        c = s['careers'][CID]
        for bad in ({'x': 1}, {'ledger': -1}, {'album': 2}, 'yes'):
            c2 = json.loads(json.dumps(c))
            c2['ext']['slim'] = bad
            with self.assertRaises(E.GameError):
                E.validate_career(c2, CID)
        c2 = json.loads(json.dumps(c))
        c2['ops']['finance']['day_sums'] = {'5': {'stock': [1, 2, 3]}}   # money out must be <= 0
        with self.assertRaises(E.GameError):
            E.validate_career(c2, CID)


def _script():
    spec = importlib.util.spec_from_file_location('slim_saves', ROOT / 'scripts' / 'slim_saves.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SlimStoreTests(unittest.TestCase):
    """Through Store.save_command and scripts/slim_saves.py on the test database."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = Store(Path(self.tmp.name) / 'game.db')

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def save(self, s=None, ago=3600.0):
        """A new session holding `s` (default cold_state()), last updated `ago` seconds ago: (token, sid)."""
        token, _, _ = self.store.session()
        sid = self.store.key(token)
        at = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - ago))
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, updated_at=? WHERE sid=?', (serialize(s or cold_state(), None, True), at, sid))
        return token, sid

    def row(self, sid):
        with self.store.connect() as db:
            r = db.execute('SELECT revision, updated_at, pg_column_size(state) AS size FROM sessions WHERE sid=?', (sid,)).fetchone()
            n = db.execute('SELECT COUNT(*) FROM receipts WHERE sid=?', (sid,)).fetchone()[0]
        return r['revision'], r['updated_at'], int(r['size']), n

    def test_archive_pages_back_everything(self):
        token, sid = self.save()
        before = cold_state()['careers'][CID]
        rev, seen, _, _ = self.row(sid)
        out = self.store.save_command(sid, secrets.token_hex(8), rev, S.ACTION, {})
        self.assertEqual(out['revision'], rev + 1)
        # not the player playing: last seen and the play statistics (receipts) stay
        self.assertEqual(self.row(sid)[1], seen)
        self.assertEqual(self.row(sid)[3], 0)
        saved, _, _ = self.store.read(token)
        self.assertEqual(saved['careers'][CID]['album'], before['album'])
        self.assertLess(len(saved['careers'][CID]['ops']['finance']['ledger']), len(before['ops']['finance']['ledger']))
        self.assertEqual(everything(self.store, token, CID, 'ledger'), before['ops']['finance']['ledger'])
        self.assertEqual(everything(self.store, token, CID, 'journal'), before['journal'])
        # "Xem cũ hơn" under the Sổ dòng tiền (24 shown): the same rows as before, newest first
        page = self.store.archive_page(token, CID, 'ledger', skip=24, limit=50)
        self.assertEqual([r['row'] for r in page['rows']], before['ops']['finance']['ledger'][-74:-24][::-1])
        # the player's next command starts from it as usual
        out = self.store.command(token, secrets.token_hex(8), rev + 1, HERE, 'settings', {'musicVolume': 12})
        self.assertEqual(out['revision'], rev + 2)

    def test_a_save_that_moved_is_skipped(self):
        token, sid = self.save()
        rev = self.row(sid)[0]
        self.store.command(token, secrets.token_hex(8), rev, HERE, 'settings', {'musicVolume': 12})
        with self.assertRaises(Conflict):
            self.store.save_command(sid, secrets.token_hex(8), rev, S.ACTION, {})
        saved, _, _ = self.store.read(token)
        self.assertEqual(len(saved['careers'][CID]['journal']), 100)

    def test_night_job(self):
        mod = _script()
        big = [self.save(ago=3600 * (1 + i))[1] for i in range(3)]
        recent = self.save(ago=60)[1]                    # the player may be at the keyboard
        old = self.save(ago=40 * 86400)[1]               # outside the window
        small_state = cold_state()
        small_state['journey']['days'] = []
        small = self.save(small_state, ago=7200)[1]      # nothing cold
        sizes = {sid: self.row(sid)[2] for sid in big + [recent, old, small]}
        logs = []
        # dry run: reads only
        out = mod.run(self.store, min_kb=0, page=2, pause=0, dry_run=True, log=logs.append)
        self.assertEqual((out['big'], out['compacted'], out['commands']), (4, 3, 0))
        self.assertTrue(all(self.row(sid)[0] == 0 for sid in sizes))
        # the night: three saves compacted, one command each; the recent, the old and the small one untouched
        out = mod.run(self.store, min_kb=0, page=2, pause=0, log=logs.append)
        self.assertEqual((out['compacted'], out['careers'], out['nothing'], out['conflicts'], out['errors']), (3, 3, 1, 0, 0))
        self.assertEqual(out['commands'], 4)
        self.assertGreaterEqual(out['pages'], 2)
        for sid in big:
            self.assertEqual(self.row(sid)[0], 1)
        for sid in (recent, old, small):
            self.assertEqual(self.row(sid)[0], 0)
        # again: nothing left to do, nothing written
        out = mod.run(self.store, min_kb=0, pause=0, log=logs.append)
        self.assertEqual((out['compacted'], out['nothing']), (0, 4))
        self.assertTrue(all(self.row(sid)[0] == 1 for sid in big))
        # the size threshold reads the stored size (no detoasting)
        out = mod.run(self.store, min_kb=max(sizes.values()) // 1024 + 1, pause=0, log=logs.append)
        self.assertEqual(out['big'], 0)

    def test_night_job_throttle_and_deadline(self):
        mod = _script()
        for i in range(4):
            self.save(ago=3600 * (1 + i))
        now = [time.time()]
        slept = []

        def sleep(x):
            slept.append(x)
            now[0] += x
        out = mod.run(self.store, min_kb=0, pause=1, per_minute=2, clock=lambda: now[0], sleep=sleep, log=lambda line: None)
        self.assertEqual(out['compacted'], 4)
        self.assertTrue(any(x > 1 for x in slept))   # waited for the minute's budget
        for i in range(3):
            self.save(ago=3600 * (1 + i))
        start = now[0]
        out = mod.run(self.store, min_kb=0, pause=10, clock=lambda: now[0], sleep=sleep, end=start + 15, log=lambda line: None)
        self.assertEqual((out['stopped'], out['commands']), ('deadline', 2))   # 10 s after each: the second one ends past the deadline
        four = mod.datetime.datetime(2026, 10, 24, 4, 0, tzinfo=mod.VN).timestamp()
        self.assertEqual(mod.deadline('05:00', 55, four) - four, 55 * 60)
        self.assertEqual(mod.deadline('04:30', 55, four) - four, 30 * 60)
        six = four + 2 * 3600
        self.assertLessEqual(mod.deadline('05:00', 55, six), six)


if __name__ == '__main__':
    unittest.main()
