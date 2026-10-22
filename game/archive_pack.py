"""🗄️ Old archive rows packed: the same history in a fraction of the disk (owner 22/10: "archive nặng quá, coi có
cách nào gọn gọn mấy cái cũ mà k ảnh hưởng").

The `archive` table (game/archive.py) takes one row per line cut from a save, about 4 M a day, nine in ten of
them career cash-book lines (kind 'ledger'): ~560 bytes of disk each with its index. Here rows older than
OLDER_THAN, past the newest KEEP of their (career, kind) history, move in chunks of up to CHUNK consecutive
positions to `archive_packed` (SCHEMA_VERSION 89): one row per chunk, its rows as zlib-compressed JSON
[[seq, day, row text], ...], ~10 bytes a line. Nothing is dropped and no position changes: Store.archive_page,
archive_tail and archive_export read both tables (rows_between, every_row), the archived row first.

The newest KEEP rows of a history always stay in `archive`, so MAX(seq)+1 there is still the next position
(storage._write_archive is unchanged) and a build that does not know `archive_packed` (a rollback) still
appends in the right place; it only shows the older pages shorter. A history the player erased
(archive.FORGET) and a deleted save lose their packed rows too (forget). 'chua.cards' stays unpacked
(game/chua_board.py reads it by position).

    run(store, budget)        # server housekeeping: a few seconds at a time, at night only
    scripts/archive_pack.py   # the first pass over the whole table (niced, resumable)
"""
from __future__ import annotations

import datetime
import json
import sys
import time
import zlib

OLDER_THAN = 3 * 86400      # rows younger than this stay as they are
KEEP = 100                  # newest rows of each history never packed (the next position is read from them)
CHUNK = 2000                # positions per packed row
MIN_CHUNK = 200             # fewer old rows than this in a history: not worth a chunk yet
SKIP = ('chua.cards',)      # read by position elsewhere
NIGHT = (1, 7)              # Vietnam hours the housekeeping packs in
EVERY = 600                 # seconds between housekeeping turns
BUDGET = 20.0               # seconds of work a housekeeping turn


def encode(rows: list) -> bytes:
    """[(seq, day, row text)] → the packed blob."""
    return zlib.compress(json.dumps([[s, d, r] for s, d, r in rows], ensure_ascii=False, separators=(',', ':')).encode(), 6)


def decode(blob) -> list:
    return [(s, d, r) for s, d, r in json.loads(zlib.decompress(bytes(blob)))]


def rows_between(db, sid: str, career: str, kind: str, start: int, end: int) -> list:
    """Rows of one history with start <= seq < end, oldest first: [(seq, day, row text)].
    `archive` is read first: a row packed meanwhile is then found in both, and kept once."""
    if end <= start:
        return []
    out = {r['seq']: (r['seq'], r['day'], r['row']) for r in db.execute(
        'SELECT seq,day,row FROM archive WHERE sid=? AND career=? AND kind=? AND seq>=? AND seq<?', (sid, career, kind, start, end))}
    for p in db.execute('SELECT data FROM archive_packed WHERE sid=? AND career=? AND kind=? AND seq_lo<? AND seq_hi>?',
                        (sid, career, kind, end, start)):
        for s, d, r in decode(p['data']):
            if start <= s < end:
                out.setdefault(s, (s, d, r))
    return [out[s] for s in sorted(out)]


def every_row(db, sid: str) -> list:
    """Every archived row of a save, packed or not: [(career, kind, seq, day, row text)] by career, kind, seq."""
    out = {(r['career'], r['kind'], r['seq']): (r['career'], r['kind'], r['seq'], r['day'], r['row'])
           for r in db.execute('SELECT career,kind,seq,day,row FROM archive WHERE sid=?', (sid,))}
    for p in db.execute('SELECT career,kind,data FROM archive_packed WHERE sid=?', (sid,)):
        for s, d, r in decode(p['data']):
            out.setdefault((p['career'], p['kind'], s), (p['career'], p['kind'], s, d, r))
    return [out[k] for k in sorted(out)]


def forget(db, sids: list, career: str | None = None, kind: str | None = None) -> None:
    """The packed rows of erased histories (one (career, kind), or whole saves), in the caller's transaction,
    after their `archive` rows (a chunk packed meanwhile is committed by then and goes too)."""
    if career is not None:
        db.execute('DELETE FROM archive_packed WHERE sid=? AND career=? AND kind=?', (sids[0], career, kind))
    elif sids:
        db.execute('DELETE FROM archive_packed WHERE sid = ANY(?)', (list(sids),))


def pack_one(db, sid: str, career: str, kind: str, cutoff: float) -> int:
    """One chunk of one history, in the caller's transaction: the oldest old rows past the newest KEEP
    removed from `archive` and written packed. Returns the rows moved (0: nothing worth packing)."""
    keep, chunk = KEEP, CHUNK
    top = db.execute('SELECT MAX(seq) FROM archive WHERE sid=? AND career=? AND kind=?', (sid, career, kind)).fetchone()[0]
    if top is None:
        return 0
    seqs = [r[0] for r in db.execute('SELECT seq FROM archive WHERE sid=? AND career=? AND kind=? AND seq<=? AND created_at<? '
                                     'ORDER BY seq LIMIT ?', (sid, career, kind, top - keep, cutoff, chunk))]
    if len(seqs) < min(MIN_CHUNK, chunk):
        return 0
    # DELETE ... RETURNING: what a concurrent erase took first is not brought back.
    rows = sorted((r['seq'], r['day'], r['row']) for r in db.execute(
        'DELETE FROM archive WHERE sid=? AND career=? AND kind=? AND seq>=? AND seq<=? AND created_at<? RETURNING seq,day,row',
        (sid, career, kind, seqs[0], seqs[-1], cutoff)))
    if not rows:
        return 0
    db.execute('INSERT INTO archive_packed(sid,career,kind,seq_lo,seq_hi,n,data) VALUES(?,?,?,?,?,?,?)',
               (sid, career, kind, rows[0][0], rows[-1][0] + 1, len(rows), encode(rows)))
    return len(rows)


def histories(db, sid: str) -> list:
    """(career, kind) histories of a save with enough rows past the newest KEEP to pack (index-only on archive_rows)."""
    return [(r['career'], r['kind']) for r in db.execute(
        'SELECT career,kind FROM archive WHERE sid=? GROUP BY career,kind HAVING COUNT(*)>=?', (sid, KEEP + MIN_CHUNK))
        if r['kind'] not in SKIP]


def pack_save(store, sid: str, cutoff: float, deadline: float, pause: float = 0.0) -> tuple:
    """Pack the old rows of one save, a chunk per transaction. Returns (rows moved, finished before the deadline)."""
    with store.connect() as db:
        todo = histories(db, sid)
    moved = 0
    for career, kind in todo:
        while True:
            if time.time() >= deadline:
                return moved, False
            n = store.transaction(lambda db: pack_one(db, sid, career, kind, cutoff))
            moved += n or 0
            if not n:
                break
            if pause:
                time.sleep(pause)
    return moved, True


def sweep(store, budget: float, after: str = '', older_than: float = OLDER_THAN, pause: float = 0.0, log=None) -> tuple:
    """Saves in sid order from `after`, until `budget` seconds are spent. Returns (rows moved, sid to resume
    from, True when the sweep reached the last save: the next one starts over from '')."""
    deadline = time.time() + budget
    cutoff = time.time() - older_than
    moved = 0
    while time.time() < deadline:
        with store.connect() as db:
            sids = [r[0] for r in db.execute('SELECT sid FROM sessions WHERE sid>? ORDER BY sid LIMIT 200', (after,))]
        if not sids:
            return moved, '', True
        for sid in sids:
            n, done = pack_save(store, sid, cutoff, deadline, pause)
            moved += n
            if log and n:
                log(sid, n)
            if not done:
                return moved, after, False   # this save again next turn
            after = sid
    return moved, after, False


_STATE = {'at': 0.0, 'after': ''}


def night(t: float) -> bool:
    h = datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=7))).hour
    return NIGHT[0] <= h < NIGHT[1]


def run(store) -> None:
    """server.py housekeeping: BUDGET seconds every EVERY seconds, Vietnam night hours only. Never raises."""
    t = time.time()
    if t - _STATE['at'] < EVERY or not night(t):
        return
    _STATE['at'] = t
    try:
        n, _STATE['after'], _ = sweep(store, BUDGET, _STATE['after'], pause=0.02)
        if n:
            sys.stderr.write(f'[archive] packed {n} rows\n')
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down (an older schema: no archive_packed)
        sys.stderr.write(f'[archive] pack: {type(e).__name__}\n')
