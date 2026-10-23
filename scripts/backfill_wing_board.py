#!/usr/bin/env python3
"""🪽 Fill wing_board (SCHEMA_VERSION 91, game/wing_lb.py: the 🪽 Cánh board of Bảng xếp hạng) for players who owned wings
before it existed (server-side tool, run by hand ONCE after the release that adds the table).

The release writes a player's row with their next jr_pet_* command. This script writes it now for every player who wears a
wing (wing_worn: one row per save wearing one, a small table walked in key order), skipping those who already have a row.
Each save is read BY PRIMARY KEY (sessions.sid), never by a scan of the saves table, in its own short transaction that
locks that one save row (the same lock a game command takes, held for one parse and one upsert), so a player who plays
meanwhile is never overwritten by an older copy. Saves are never changed. Safe to run again.

  python3 scripts/backfill_wing_board.py --dry-run     # what it would write
  python3 scripts/backfill_wing_board.py               # write the missing rows

DATABASE_URL is required (PostgreSQL). It refuses to run before the database is at SCHEMA_VERSION 91 (it never runs DDL).
Throttled: --batch saves (default 50) then --pause seconds (default 0.5), at least 5 ms a save.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import db as dbm  # noqa: E402
from game import pg_schema  # noqa: E402
from game import wing_lb  # noqa: E402

NEED = 91


def parse(text) -> dict | None:
    if isinstance(text, (bytes, bytearray, memoryview)):
        text = bytes(text).decode('utf-8')
    if not text:
        return None
    try:
        s = json.loads(text)
    except ValueError:
        return None
    return s if isinstance(s, dict) else None


def run(store, dry_run: bool = False, batch: int = 50, pause: float = .5, force: bool = False, log=print) -> dict:
    """Walk wing_worn by sid; for each save without a wing_board row (every one with `force`), read it by primary key and
    write its row. Returns the counts."""
    out = dict(seen=0, had=0, written=0, none=0, gone=0)
    last = ''
    while True:
        with store.connect() as db:
            sids = [r[0] for r in db.execute('SELECT sid FROM wing_worn WHERE sid>? ORDER BY sid LIMIT ?', (last, int(batch))).fetchall()]
            if not sids:
                break
            have = set() if force else {r[0] for r in db.execute('SELECT sid FROM wing_board WHERE sid = ANY(?)', (sids,)).fetchall()}
        last = sids[-1]
        out['seen'] += len(sids)
        out['had'] += len(have)
        for sid in sids:
            if sid in have:
                continue
            t0 = time.perf_counter()

            def step(db, sid=sid):
                row = db.execute('SELECT state FROM sessions WHERE sid=?' + ('' if dry_run else ' FOR UPDATE'), (sid,)).fetchone()
                if not row:
                    return 'gone'
                s = parse(row[0])
                if s is None or wing_lb.score(s) is None:
                    return 'none'
                if not dry_run:
                    wing_lb.write(db, sid, s, wing_lb.reached(s))
                return 'written'
            got = store.transaction(step)
            out[got] += 1
            time.sleep(max(.005, time.perf_counter() - t0))   # never more than about half a core
        log(f"… {out['seen']} người đeo cánh, {out['written']} dòng {'sẽ ghi' if dry_run else 'đã ghi'}")
        if pause:
            time.sleep(pause)
    if not dry_run:
        wing_lb.clear_cache()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--namespace', default=os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')), help='PostgreSQL test namespace (default: GAME_NAMESPACE)')
    ap.add_argument('--batch', type=int, default=50, help='saves per batch (default 50)')
    ap.add_argument('--pause', type=float, default=.5, help='seconds between batches (default 0.5)')
    ap.add_argument('--force', action='store_true', help='rewrite rows that are already there too')
    ap.add_argument('--dry-run', action='store_true', help='count only, write nothing')
    a = ap.parse_args()
    dbm.database_url()  # requires PostgreSQL; no file fallback
    pool = dbm.pool_for(a.namespace)
    db = pool.connect()
    try:
        v = pg_schema.installed_version(db)
    finally:
        db.close()
    if v < NEED:
        sys.exit(f'Cơ sở dữ liệu đang ở SCHEMA_VERSION {v}: cần {NEED} (triển khai bản mới trước).')
    from game.storage import Store
    store = Store(a.namespace, story=True)   # at 91 already: its startup check runs no DDL
    t0 = time.time()
    out = run(store, dry_run=a.dry_run, batch=max(1, a.batch), pause=max(0.0, a.pause), force=a.force, log=lambda m: print(m, flush=True))
    print(json.dumps(out, ensure_ascii=False))
    print(f"{'Thử (không ghi): ' if a.dry_run else 'Xong: '}{out['written']} dòng, {out['had']} đã có, {out['none']} không còn cánh, "
          f"{out['gone']} không còn save, {time.time() - t0:.1f} s.")
    store.close_pool()


if __name__ == '__main__':
    main()
