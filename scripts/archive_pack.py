"""🗄️ The first pass of game/archive_pack.py over the whole archive table (the server's housekeeping then keeps up
a few seconds a night). Resumable: it prints the last save done; pass it back with --after.

    nice -n 10 ionice -c2 -n7 python scripts/archive_pack.py --hours 1 [--after SID] [--pause 0.01]

Then `pg_repack -t archive` (or VACUUM, which only lets PostgreSQL reuse the space) gives the disk back.
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import archive_pack as arp  # noqa: E402
from game.storage import Store  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--hours', type=float, default=1.0)
    p.add_argument('--after', default='')
    p.add_argument('--pause', type=float, default=0.01, help='seconds between chunks (each its own transaction)')
    p.add_argument('--older-days', type=float, default=arp.OLDER_THAN / 86400)
    a = p.parse_args()
    store = Store(os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')))
    t0, total, after = time.time(), 0, a.after
    end = t0 + a.hours * 3600
    while time.time() < end:
        n, after, done = arp.sweep(store, min(60.0, end - time.time()), after, a.older_days * 86400, a.pause)
        total += n
        print(f'{time.strftime("%H:%M:%S")} moved={total} rate={total / max(1, time.time() - t0):.0f}/s after={after!r}', flush=True)
        if done:
            print('DONE', flush=True)
            return
    print(f'STOPPED after={after!r}', flush=True)


if __name__ == '__main__':
    main()
