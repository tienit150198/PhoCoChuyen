#!/usr/bin/env python3
"""Explicit owner-requested first-week baseline; resumable, no save/wallet changes.

Run with the game's DATABASE_URL and --week YYYY-MM-DD (Monday in Vietnam).
Never scheduled: subsequent weeks retain delta-only accounting.
"""
import argparse
import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import fair_loss
from game.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--week', required=True)
    parser.add_argument('--batch', type=int, default=50)
    args = parser.parse_args()
    day = datetime.date.fromisoformat(args.week)
    if day.weekday() != 0:
        parser.error('--week must be Monday')
    zone = datetime.timezone(datetime.timedelta(hours=7))
    week = int(datetime.datetime.combine(day, datetime.time(), zone).timestamp())
    store = Store(Path('storage/fair-loss-seed'))
    try:
        while True:
            result = fair_loss.seed_current(store, week, args.batch)
            if result and (result['done'] or result['processed'] % 1000 == 0):
                # Never print private session ids or save contents.
                print(json.dumps({k:result[k] for k in ('processed','balances','done')}), flush=True)
            if result and result['done']:
                break
            time.sleep(.05 if result else .5)
    finally:
        store.close_pool()


if __name__ == '__main__':
    main()
