#!/usr/bin/env python3
"""🔐 Apply mishaps whose time has come to saves that are not loaded (owner 09/10: "thu trong lúc offline").

game/live_effects.py pays a due 'mishap' row when the player loads the game; this sweeper pays it at its time even
when they are away, so they find the bank SMS (unread) and the history rows when they come back. Run it from the
live release directory with the game service's environment, every few minutes (a systemd timer):

    python3 scripts/mishap_sweep.py            # dry run: the due rows
    python3 scripts/mishap_sweep.py --write

Per row, ONE transaction: the save row locked (SELECT ... FOR UPDATE), the effect row still pending (locked too),
the game's own reducer (live_effects.apply: paid once per row id, the save keeps its hash), validate, serialize,
UPDATE sessions ... WHERE revision=? (compare-and-set), the receipt under the request id on_load would use
(live-<hash>, so `mishap_plan.py status` reads what it took), the row flipped pending -> applied. A save that moved
meanwhile is left for the next run; a row the reducer refuses stays pending and is reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

BATCH = 50


def sweep(store, write: bool) -> int:
    """Apply (or list) the due rows; returns how many were applied."""
    from game import db as dbm
    from game import live_effects as lfx
    from game.engine import migrate_state
    from game.storage import serialize
    now = time.time()
    with store.connect() as db:
        due = [dict(r) for r in db.execute(
            "SELECT e.id,e.sid,e.amount,e.data,a.uid FROM live_effects e LEFT JOIN accounts a ON a.sid=e.sid "
            f"WHERE e.kind='mishap' AND e.status='pending' AND e.at<=? ORDER BY e.at LIMIT {BATCH}", (now,)).fetchall()]
    done = 0
    for r in due:
        data = json.loads(r['data'] or '{}')
        payload = dict(id=r['id'], kind='mishap', amount=int(r['amount']), src=None, sub=data.get('sub'))
        who = f"uid {r['uid']} {r['id']}"
        if not write:
            print(f'{who}: due {r["amount"]:,} ({data.get("sub")})')
            continue
        db = store.connect()
        try:
            db.begin()
            row = db.execute('SELECT revision,state FROM sessions WHERE sid=?' + dbm.for_update(db), (r['sid'],)).fetchone()
            eff = db.execute("SELECT status FROM live_effects WHERE id=? AND sid=?" + dbm.for_update(db), (r['id'], r['sid'])).fetchone()
            if not row or not eff or eff['status'] != 'pending':
                db.rollback()
                continue
            s = migrate_state(store.parse_state(row['state'], r['sid']), owned=True)
            if not (s.get('journey') or {}).get('story'):
                db.rollback()
                print(f'{who}: not a story save, left pending')
                continue
            s, result = lfx.apply(s, dict(payload))
            n = db.execute('UPDATE sessions SET state=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE sid=? AND revision=?',
                           (serialize(s, None, True), r['sid'], row['revision'])).rowcount
            if n != 1:
                db.rollback()
                print(f'{who}: save moved meanwhile, next run')
                continue
            rid = lfx.RID + lfx.short(r['id'])
            fp = hashlib.sha256(json.dumps([None, lfx.ACTION, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            db.execute('INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?) ON CONFLICT DO NOTHING',
                       (r['sid'], rid, fp, json.dumps(result, ensure_ascii=False)))
            db.execute("UPDATE live_effects SET status='applied',applied_at=? WHERE id=? AND sid=? AND status='pending'", (time.time(), r['id'], r['sid']))
            db.commit()
            done += 1
            print(f"{who}: took {result.get('live', {}).get('taken', 0):,} of {r['amount']:,}")
        except Exception as e:  # noqa: BLE001 - one row's trouble never stops the others
            db.rollback()
            print(f'{who}: error {e!r}, left pending')
        finally:
            db.close()
    if write:
        print(f'applied {done} of {len(due)} due row(s)')
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    from game import db as dbm
    from game.storage import Store
    dbm.database_url()
    sweep(Store(os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')), story=True), a.write)
    return 0


if __name__ == '__main__':
    sys.exit(main())
