"""Read status, or explicitly activate the one-shot 48-hour Chợ Đen event.

Run inside the deployed app with its normal DATABASE_URL/GAME_NAMESPACE:
  python scripts/activate_fair_golden_days.py
  python scripts/activate_fair_golden_days.py --activate
Repeating --activate returns the original window, even after it has expired.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import fair_golden_days as golden
from game.storage import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true', help='Start the event once; retries never extend it')
    parser.add_argument('--namespace', default=os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')))
    args = parser.parse_args()
    store = Store(args.namespace, story=True)
    try:
        with store.connect() as db:
            result = golden.activate(db) if args.activate else golden.status(db)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    finally:
        store.close_pool()


if __name__ == '__main__':
    main()
