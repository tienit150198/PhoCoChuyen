"""💤 Cold careers keep a slim record (game/slim.py): nothing is lost (archived rows + rows in the save == before),
the wallet still matches the cash book, the lãi/lỗ chart keeps its days, and only cold careers are touched."""
import base64
import json
import secrets
import tempfile
import unittest
from pathlib import Path

import game.archive as ar
import game.engine as E
import game.slim as S
from game.storage import Store, serialize
from tests.test_archive import everything

CID = 'milk_tea'
HERE = 'mother_baby'
PNG = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + bytes(range(40))).decode()


def cold_state(day=12, rows=120, photos=6, lines=90, warm=()):
    """A save whose CID career has a long cash book, six photos and a long journal, and a journey whose last
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


def run(s, career=HERE, action='settings', payload=None):
    """One command as the storage layer runs it: (new save, the archived (owner, kind, row))."""
    with ar.collect() as box:
        out, _ = E.apply_action(s, career, action, payload or {'musicVolume': 41}, owned=True)
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
        self.assertEqual(list(reversed(moved['album'])), before['album'])   # archived oldest first
        self.assertEqual(c['album'], [])
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
        self.assertEqual(c['ext']['slim'], dict(ledger=len(moved['ledger']), album=6, journal=len(moved['journal']), life=35))
        E.validate_state(s)
        # life histories nothing reads back keep their newest rows
        self.assertEqual([r for o, k, r in cut if o == CID and k == 'life.activities'] + c['life']['activity_history'],
                         before['life']['activity_history'])
        self.assertEqual(len(c['life']['activity_history']), S.LIFE_KEEP)
        # the view says what moved (the client offers "Xem cũ hơn" on the short lists)
        view = E.public_state(json.loads(json.dumps(s)), full=CID)
        self.assertEqual(view['careers'][CID]['slim'], c['ext']['slim'])
        self.assertIn('day_sums', view['careers'][CID]['ops']['finance'])

    def test_a_second_command_leaves_a_slim_career_alone(self):
        s, _ = run(cold_state())
        snap = lists(s['careers'][CID])
        s, cut = run(s)
        self.assertEqual([x for x in cut if x[0] == CID], [])
        self.assertEqual(lists(s['careers'][CID]), snap)

    def test_warm_current_acting_and_short_journeys_are_left_alone(self):
        for case in ('recent', 'current', 'acting', 'short', 'no_collector'):
            s = cold_state(warm=(CID,) if case == 'recent' else ())
            if case == 'current':
                s['current'] = CID
            if case == 'short':
                s['journey']['days'] = s['journey']['days'][:S.COLD_DAYS - 1]
            snap = lists(s['careers'][CID])
            if case == 'no_collector':   # a copy or a preview: helpers only slice, so nothing may be cut
                s, _ = E.apply_action(s, HERE, 'settings', {'musicVolume': 3}, owned=True)
                cut = []
            else:
                s, cut = run(s, career=CID if case == 'acting' else HERE)
            self.assertEqual([x for x in cut if x[0] == CID], [], case)
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
        c['journal'][-40:] = [dict(r, day=c['day']) for r in c['journal'][-40:]]
        S.journal(c, CID)
        self.assertEqual(len(c['journal']), 40)

    def test_per_command_limit(self):
        s = cold_state()
        extra = [cid for cid in s['careers'] if cid not in (CID, HERE)][:S.PER_COMMAND + 2]
        for cid in extra:
            c = s['careers'][cid]
            c['started'] = True
            c['album'] = [dict(id=f'photo-{cid}', image=PNG, day=c['day'], title='Ảnh')]
        E.validate_state(s)
        s, cut = run(s)
        self.assertEqual(len({o for o, k, r in cut if k == 'album'}), S.PER_COMMAND)
        s, cut = run(s)
        self.assertEqual(len({o for o, k, r in cut if k == 'album'}), 3)
        self.assertTrue(all(not s['careers'][cid]['album'] for cid in extra + [CID]))

    def test_validation_refuses_bad_marks(self):
        s, _ = run(cold_state())
        c = s['careers'][CID]
        for bad in ({'x': 1}, {'ledger': -1}, 'yes'):
            c2 = json.loads(json.dumps(c))
            c2['ext']['slim'] = bad
            with self.assertRaises(E.GameError):
                E.validate_career(c2, CID)
        c2 = json.loads(json.dumps(c))
        c2['ops']['finance']['day_sums'] = {'5': {'stock': [1, 2, 3]}}   # money out must be <= 0
        with self.assertRaises(E.GameError):
            E.validate_career(c2, CID)


class SlimStoreTests(unittest.TestCase):
    """Through Store.command: the cut rows land in the archive table and page back in order."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'game.db')

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def test_archive_pages_back_everything(self):
        token, _, _ = self.store.session()
        s = cold_state()
        before = json.loads(json.dumps(s['careers'][CID]))
        sid = self.store.key(token)
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (serialize(s, None, True), sid))
        out = self.store.command(token, secrets.token_hex(8), 0, HERE, 'settings', {'musicVolume': 12})
        self.assertEqual(out['revision'], 1)
        saved, _, _ = self.store.read(token)
        self.assertEqual(saved['careers'][CID]['album'], [])
        self.assertLess(len(saved['careers'][CID]['ops']['finance']['ledger']), len(before['ops']['finance']['ledger']))
        self.assertEqual(everything(self.store, token, CID, 'ledger'), before['ops']['finance']['ledger'])
        self.assertEqual(everything(self.store, token, CID, 'journal'), before['journal'])
        self.assertEqual(everything(self.store, token, CID, 'album'), list(reversed(before['album'])))
        # the album's first page, newest first, as the Kỷ niệm sheet asks for it
        page = self.store.archive_page(token, CID, 'album', skip=0, limit=6)
        self.assertEqual([r['row']['id'] for r in page['rows']], [p['id'] for p in before['album']])


if __name__ == '__main__':
    unittest.main()
