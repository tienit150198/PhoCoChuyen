#!/usr/bin/env python3
"""Rollback drain for 🛎️ Phố dịch vụ and the careers built on it: before a code rollback to a release without them
(2.4.68 = 289df99d, live), settle or refund in full every piece of money still held by this build's tables, so the
older build never meets an escrow it does not understand. Dry run by default (counts and xu only); --write does it.

Why (review 22/10): 2.4.68 settles a legacy workplace order (work_service_orders) with its own rules. An order made by
this build (data.market = 1, priced ×3…×10 of the NPC price) would then be paid in full with the 40 % staff profit bonus
on the whole price (work_visits._settle_one → player_service_tasks.credit_staff_bonus without `base`). And 2.4.68 never
reads svc_orders, photo_orders, birth_stays or hotel_stays: their escrow would stay frozen until a roll forward.

What --write does, each step with the module's own exactly-once path (row locks, status guards, the saves under their
revision guard), in this order:
  1. 🏨 hotel_stays booked / arrived / in → hotel_stay._refund_db (the stay gone, its market order → refund)
  2. svc_orders talk → cancelled; held / working → refund (why 'rollback'); delivered → ready (the work was done: the
     provider is paid, the buyer gets the result); then every ready / refund row is settled now (service_market
     settle_for: 95 % paid, 5 % burned; refunds in full, wallet then bank account)
  3. work_service_orders made by this build (data.market = 1): requested / accepted → refund_pending (cancelled), then
     every ready / refund_pending one is settled now by this build (work_visits._settle_one: 95 / 5, the real-margin
     bonus); older orders (no data.market) are 2.4.68's own and are left alone
  4. 📸 photo_orders open / shoot → declined, the price back (photo_studio.refund_row), and every pending 'photo'
     live_effects row is paid into its save now (2.4.68 leaves that kind pending)
  5. 🏥 birth_stays proposed → cancelled; booked / staying → refunded in full to the payer (birth.end's path: a pending
     marriage_effects 'wallet' row, which 2.4.68 applies on the payer's next load)
Then it counts again: everything should be 0 (a row whose save refused is listed; run again, or look at it).

Run it after MNL_SVC_OFF=1, MNL_BIRTH_OFF=1, MNL_HOTEL_OFF=1, MNL_PHOTO_DIRECT_OFF=1 (no new money in) on this build,
inside the deployed app with its DATABASE_URL / GAME_NAMESPACE:
  python scripts/svc_drain.py            # dry run: what is held, per table
  python scripts/svc_drain.py --write    # settle / refund it all, then count again
Runbook: docs/SERVICE_MARKET.md "Rollback runbook".
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

SVC_OPEN = ('talk', 'held', 'working', 'delivered', 'ready', 'refund')
WO_OPEN = ('requested', 'accepted', 'ready', 'refund_pending')


def _table(db, name: str) -> bool:
    return bool(db.execute('SELECT to_regclass(?) AS t', (name,)).fetchone()['t'])


def _count(db, sql: str, args=()) -> dict:
    r = db.execute(sql, args).fetchone()
    return dict(n=int(r['n'] or 0), xu=int(r['xu'] or 0))


def plan(store) -> dict:
    """What this build still holds, per table and status: {key: {n, xu}} (read only)."""
    out = {}
    with store.connect() as db:
        if _table(db, 'svc_orders'):
            for st in SVC_OPEN:
                out[f'svc_orders.{st}'] = _count(db, "SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN status='talk' THEN 0 ELSE price END),0) AS xu "
                                                     'FROM svc_orders WHERE status=?', (st,))
        for st in WO_OPEN:
            out[f'work_service_orders.market.{st}'] = _count(
                db, "SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu FROM work_service_orders WHERE status=? AND data LIKE '%\"market\":1%'", (st,))
        if _table(db, 'hotel_stays'):
            out['hotel_stays.live'] = _count(db, "SELECT COUNT(*) AS n, 0 AS xu FROM hotel_stays WHERE stage IN ('booked','arrived','in')")
        if _table(db, 'photo_orders'):
            out['photo_orders.open'] = _count(db, "SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu FROM photo_orders WHERE status IN ('open','shoot')")
        out['live_effects.photo'] = _count(db, "SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS xu FROM live_effects WHERE kind='photo' AND status='pending'")
        if _table(db, 'birth_stays'):
            for st in ('proposed', 'booked', 'staying'):
                out[f'birth_stays.{st}'] = _count(db, f"SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN status='proposed' THEN 0 ELSE price END),0) AS xu "
                                                      'FROM birth_stays WHERE status=?', (st,))
    return out


def _held(report: dict) -> int:
    return sum(v['n'] for v in report.values())


# ---------------------------------------------------------------- the steps
def _hotel(store, log: list) -> None:
    from game import hotel_stay as hs
    from game import service_market as sm
    with store.connect() as db:
        if not _table(db, 'hotel_stays'):
            return
        ids = [r['order_id'] for r in db.execute("SELECT order_id FROM hotel_stays WHERE stage IN ('booked','arrived','in') ORDER BY order_id").fetchall()]
    for oid in ids:
        t = sm.now()

        def run(db, oid=oid):
            r = hs._row(db, oid, lock=True)
            if not r or r['stage'] not in hs.LIVE:
                return False
            hs._refund_db(db, r, 'rollback', t)
            mr_notice(db, r['guest'], '🏨 Sổ phòng tạm đóng để bảo trì: lượt đặt phòng của bạn được hủy, tiền phòng hoàn đủ.')
            return True
        try:
            store.transaction(run)
        except Exception as e:  # noqa: BLE001
            log.append(f'hotel {oid}: {type(e).__name__} {e}')


def mr_notice(db, sid, text):
    from game import marriage as mr
    mr._notice(db, sid, text)


def _svc(store, log: list) -> None:
    from game import service_market as sm
    with store.connect() as db:
        if not _table(db, 'svc_orders'):
            return
        rows = [dict(r) for r in db.execute("SELECT id, status FROM svc_orders WHERE status IN ('talk','held','working','delivered') ORDER BY id").fetchall()]
    for row in rows:
        t = sm.now()

        def run(db, oid=row['id']):
            cur = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (oid,)).fetchone()
            if not cur:
                return False
            cur = dict(cur)
            st = cur['status']
            if st == 'talk':
                return sm._flip(db, oid, 'talk', 'cancelled', t, due_at=None)
            d = sm._data(cur)
            if st in ('held', 'working'):
                d['why'] = 'rollback'
                sm._set_data(db, oid, d)
                return sm._flip(db, oid, st, 'refund', t, due_at=t)
            if st == 'delivered':   # delivered work is earned: confirmed now, the provider paid below
                d['auto'] = True
                sm._set_data(db, oid, d)
                return sm._flip(db, oid, 'delivered', 'ready', t, due_at=t)
            return False
        try:
            store.transaction(run)
        except Exception as e:  # noqa: BLE001
            log.append(f'svc {row["id"]} {row["status"]}: {type(e).__name__} {e}')
    store.transaction(lambda db: db.execute("UPDATE svc_orders SET due_at=? WHERE status IN ('ready','refund')", (sm.now(),)))
    for _ in range(1000):   # every ready / refund row, a batch at a time, until nothing settles any more
        if not sm.settle_for(store, None, None, 200):
            break
    with store.connect() as db:
        for r in db.execute("SELECT id, status, data FROM svc_orders WHERE status IN ('ready','refund') ORDER BY id LIMIT 50").fetchall():
            log.append(f'svc {r["id"]} still {r["status"]}: {sm._data(dict(r)).get("stuck") or "?"}')


def _legacy(store, log: list) -> None:
    from game import work_visits as wv
    rows = []
    with store.connect() as db:
        for r in db.execute("SELECT * FROM work_service_orders WHERE status IN ('requested','accepted','ready','refund_pending') ORDER BY id").fetchall():
            r = dict(r)
            if wv._data(r).get('market'):
                rows.append(r)
    for r in rows:
        if r['status'] in ('requested', 'accepted'):
            def mark(db, oid=r['id']):
                cur = db.execute('SELECT * FROM work_service_orders WHERE id=? FOR UPDATE', (oid,)).fetchone()
                if not cur or cur['status'] not in ('requested', 'accepted'):
                    return False
                body = wv._data(dict(cur))
                body['end_status'] = 'cancelled'
                return db.execute("UPDATE work_service_orders SET status='refund_pending',data=?,updated_at=? WHERE id=? AND status=?",
                                  (wv._json(body), time.time(), oid, cur['status'])).rowcount == 1
            try:
                store.transaction(mark)
            except Exception as e:  # noqa: BLE001
                log.append(f'legacy {r["id"]}: {type(e).__name__} {e}')
    for oid in [r['id'] for r in rows]:
        with store.connect() as db:
            cur = db.execute('SELECT * FROM work_service_orders WHERE id=?', (oid,)).fetchone()
        if not cur or cur['status'] not in ('ready', 'refund_pending'):
            continue
        try:
            wv._settle_one(store, dict(cur))
        except Exception as e:  # noqa: BLE001
            log.append(f'legacy {oid} {cur["status"]}: {type(e).__name__} {e}')


def _photo(store, log: list) -> None:
    from game import marriage as mr
    from game import photo_studio as ps
    with store.connect() as db:
        if not _table(db, 'photo_orders'):
            return

    def decline(db):
        t = ps.now()
        rows = ps._rows(db, "SELECT * FROM photo_orders WHERE status IN ('open','shoot') ORDER BY id FOR UPDATE")
        for r in rows:
            db.execute("UPDATE photo_orders SET status='declined', answered=?, refund=1 WHERE id=? AND status IN ('open','shoot')", (t, r['id']))
            ps.refund_row(db, r, 'rollback', t)
        return len(rows)
    store.transaction(decline)
    with store.connect() as db:
        fx = [dict(r) for r in db.execute("SELECT id, sid, amount, data FROM live_effects WHERE kind='photo' AND status='pending' ORDER BY at, id").fetchall()]
    for e in fx:
        if not mr._read_state(store, e['sid']):
            continue
        data = json.loads(e['data'] or '{}')

        def pay(s, e=e, data=data):
            ps.apply_fx(s, dict(data=data), int(e['amount']))

        def done(db, e=e):
            if db.execute("UPDATE live_effects SET status='applied', applied_at=? WHERE id=? AND status='pending'", (time.time(), e['id'])).rowcount != 1:
                raise mr.MarriageError('already applied', 'replay', 409)
        try:
            mr._mutate_retry(store, {e['sid']: pay}, done)
        except mr.MarriageError as x:
            if x.code != 'replay':
                log.append(f'photo refund {e["id"]}: {x.code} {x}')
        except Exception as x:  # noqa: BLE001
            log.append(f'photo refund {e["id"]}: {type(x).__name__} {x}')


def _birth(store, log: list) -> None:
    from game import birth as bt
    from game import marriage as mr
    with store.connect() as db:
        if not _table(db, 'birth_stays'):
            return
        ids = [int(r['id']) for r in db.execute("SELECT id FROM birth_stays WHERE status IN ('proposed','booked','staying') ORDER BY id").fetchall()]
    for ident in ids:
        def run(db, ident=ident):
            t = mr.now()
            r = mr._row(db, 'SELECT * FROM birth_stays WHERE id=? FOR UPDATE', (ident,))
            if not r or r['status'] not in bt.ACTIVE:
                return False
            if r['status'] == 'proposed':
                db.execute("UPDATE birth_stays SET status='cancelled',done=? WHERE id=?", (t, ident))
                return True
            bt._effect_wallet(db, f'birth:{ident}:r', r['payer'], int(r['price']), f'Hoàn tiền phòng sinh ({r["name"]})')
            db.execute("UPDATE birth_stays SET status='refunded',done=? WHERE id=?", (t, ident))
            for who in (r['from_sid'], r['to_sid']):
                mr._notice(db, who, f'🏥 Phòng sinh tạm đóng để bảo trì: lượt đặt được hủy, {bt._fmt(r["price"])} xu hoàn đủ cho người trả.')
            return True
        try:
            store.transaction(run)
        except Exception as e:  # noqa: BLE001
            log.append(f'birth {ident}: {type(e).__name__} {e}')


def drain(store, write: bool = False) -> dict:
    """{before, after (with --write), log}: what is held, and after settling / refunding it all (module docstring)."""
    before = plan(store)
    out = dict(before=before, held=_held(before), write=bool(write), log=[])
    if not write:
        return out
    for step in (_hotel, _svc, _legacy, _photo, _birth):
        step(store, out['log'])
    after = plan(store)
    out.update(after=after, left=_held(after))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--write', action='store_true', help='settle / refund everything (default: a dry run that only counts)')
    parser.add_argument('--namespace', default=os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')))
    args = parser.parse_args()
    from game.storage import Store
    store = Store(args.namespace, story=True)
    try:
        out = drain(store, args.write)
    finally:
        store.close_pool()
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    return 1 if args.write and out.get('left') else 0


if __name__ == '__main__':
    sys.exit(main())
