#!/usr/bin/env python3
"""💍 Settle "Khách mời của tuần" by hand (the live service does it by itself after each Monday 00:00, Vietnam time).

Idempotent: every prize has a fixed key (paid once through game/live_effects.py on the winner's next load) and the
week is recorded once in `wedding_race`. Use it to check a week or to settle one while the live service was down.

  python3 scripts/wedding_week.py                      # last week, on the game database (DATABASE_URL)
  python3 scripts/wedding_week.py --week 2026-W40 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main_async(args) -> int:
    from game import wedding_live as WL
    from live.config import Config
    from live.db import open_db
    from live.wedding import settle_week
    import os
    from game import db as dbm
    url = dbm.database_url()
    schema = args.schema
    if not schema and dbm.test_mode():
        schema = dbm.pool_for(args.namespace).schema
    db = await open_db(Config(db_url=url, db_schema=schema))
    try:
        week = args.week or WL.vn_week(WL.week_start(time.time()) - 3600)
        done = await db.fetchrow('SELECT settled, top FROM wedding_race WHERE week=?', (week,))
        rows = await db.fetch('SELECT sid, COUNT(*) AS n, MAX(counted_at) AS last FROM wedding_guests WHERE week=? AND ok=1 '
                              'GROUP BY sid ORDER BY n DESC, last ASC, sid LIMIT 3', (week,))
        print(f'week {week}: ' + (f'settled at {time.strftime("%Y-%m-%d %H:%M", time.localtime(done["settled"]))}' if done else 'not settled yet'))
        for i, r in enumerate(rows):
            print(f'  #{i + 1} {r["sid"][:12]}… {r["n"]} weddings')
        if args.dry_run:
            return 0
        top = await settle_week(db, week)
        print(json.dumps(dict(week=week, paid=[dict(rank=t['rank'], n=t['n'], title=t['title']) for t in top]), ensure_ascii=False))
        return 0
    finally:
        await db.close()


def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--week', help="ISO week of the Vietnam calendar, e.g. 2026-W40 (default: last week)")
    ap.add_argument('--namespace', default='storage/game', help='PostgreSQL test namespace')
    ap.add_argument('--schema', help='PostgreSQL search_path')
    ap.add_argument('--dry-run', action='store_true')
    sys.exit(asyncio.run(main_async(ap.parse_args())))


if __name__ == '__main__':
    main()
