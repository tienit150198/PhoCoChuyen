#!/usr/bin/env python3
"""Seed "Thời gian chơi" (the admin's play time) for the last days from the receipts the database
still holds (server-side tool, run by hand ONCE after the release that adds the stat_play trigger).

The trigger counts every game command from the moment the release is live. The commands sent
before that are only in `receipts` (kept 2 days, at most RECEIPTS_PER_SAVE = 200 per save), so
the days this seeds are marked as estimates (table stat_play_est; the admin page says "ước tính"
and how many busy saves were at the 200 cap). Safe to run again: it adds only commands older than
what a row already counts. It reads receipts and writes only the derived stat_play /
stat_play_est tables, a hundred saves per short transaction; saves and receipts are never changed.

  python3 scripts/playtime_backfill.py --dry-run     # what it would seed
  python3 scripts/playtime_backfill.py               # seed yesterday and today

With DATABASE_URL set (PostgreSQL, see docs/POSTGRES.md) --db is ignored. Run it off-peak
(not 17:30-20:00): it reads ~2 days of receipts by primary key.
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

from game import admin_stats, db as dbm  # noqa: E402
from game.storage import Store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', default=os.environ.get('GAME_DB', str(ROOT / 'storage' / 'game.sqlite3')))
    ap.add_argument('--days', type=int, default=2, help='Vietnam days to seed, today included (default 2: yesterday and today)')
    ap.add_argument('--dry-run', action='store_true', help='count only, write nothing')
    a = ap.parse_args()
    if not dbm.database_url() and not Path(a.db).exists():
        sys.exit(f'Không thấy cơ sở dữ liệu: {a.db}')
    store = Store(a.db, story=True)
    admin_stats.ensure(store)   # the stat_play table and trigger (SQLite; on PostgreSQL the Store made them)
    t0 = time.time()
    out = admin_stats.backfill_play(store, days=a.days, dry_run=a.dry_run, log=lambda m: print(m, flush=True))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{'Thử (không ghi): ' if a.dry_run else 'Xong: '}{out['inserted']} dòng mới, {out['merged']} dòng nối thêm, "
          f"{out['capped']} lượt chơi chạm giới hạn biên nhận, {time.time() - t0:.1f} s.")


if __name__ == '__main__':
    main()
