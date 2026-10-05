#!/usr/bin/env python3
"""Seed the "Giữ chân" funnel (stat_milestones, game/retention.py) for saves born before the release
that records it (server-side tool, run by hand ONCE after that release, off-peak).

Steps are recorded live from the release on. For saves born earlier (by default from 30/09, the cohort
before the 0.9.16 onboarding, up to today) this writes `created` and every step their counters show
"reached by now" (no time: the admin page marks them "ước tính"), plus `account`, `engaged` and
`married` with their real times. It reads saves 100 at a time with a pause in between and writes only
stat_milestones; saves are never changed. Safe to run again (a step a save already has is kept).

  python3 scripts/milestones_backfill.py --dry-run
  python3 scripts/milestones_backfill.py                       # 2026-09-30 .. today
  python3 scripts/milestones_backfill.py --since 2026-09-29 --until 2026-10-02

DATABASE_URL is required (PostgreSQL, see docs/POSTGRES_ONLY.md). Not 17:30-20:00.
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

from game import admin_stats, retention, db as dbm  # noqa: E402
from game.storage import Store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--namespace', default=os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')), help='PostgreSQL test namespace (default: GAME_NAMESPACE)')
    ap.add_argument('--since', default='2026-09-30', help='first birth day (Vietnam), default 2026-09-30')
    ap.add_argument('--until', default=None, help='last birth day, default today')
    ap.add_argument('--dry-run', action='store_true', help='count only, write nothing')
    a = ap.parse_args()
    dbm.database_url()  # requires PostgreSQL; no file fallback
    store = Store(a.namespace, story=True)
    admin_stats.ensure(store)
    t0 = time.time()
    out = retention.backfill(store, a.since, a.until or retention.vn_day(), dry_run=a.dry_run, log=lambda m: print(m, flush=True))
    print(json.dumps(out, ensure_ascii=False))
    print(f"{'Thử (không ghi): ' if a.dry_run else 'Xong: '}{out['saves']} lượt chơi, {out['rows']} dòng, {time.time() - t0:.1f} s.")


if __name__ == '__main__':
    main()
