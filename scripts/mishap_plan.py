#!/usr/bin/env python3
"""🔐 Schedule, inspect or cancel mishaps (game/mishap.py) for accounts whose money came from a bug (owner 09/10).

Each plan spreads a target over DAYS real days as uneven incidents at random hours (some days none, some days
several), written as `live_effects` rows of kind 'mishap' that the game pays once their time has come. Run it on
the server from the live release directory with the game service's environment:

    python3 scripts/mishap_plan.py plan --uid 2205 --target 39500000 --tag x0910          # dry run: the schedule
    python3 scripts/mishap_plan.py plan --uid 2205 --target 39500000 --tag x0910 --write
    python3 scripts/mishap_plan.py status [--uid 2205]      # planned, taken so far, pending, short
    python3 scripts/mishap_plan.py topup --uid 2205 --tag x0910 [--write]   # reschedule what was not there to take
    python3 scripts/mishap_plan.py cancel --uid 2205 [--write]              # pending rows -> 'void'

Row ids: mishap-<uid>-<tag>-<n> (a plan written twice is a no-op). What a row took is in its receipt
(live_fx result `live.taken`); a row that found less than its amount leaves the rest to `topup`.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

DAYS = 10
VN = 7 * 3600
SUB_WEIGHTS = (('hack', 4), ('scam', 3), ('phish', 2), ('atm', 2), ('tip', 1))


def _count(target: int, rng: random.Random) -> int:
    return max(2, min(rng.randint(10, 17), target // 150_000 or 2))


def split(target: int, rng: random.Random, t0: float, days: int = DAYS, first_within: int = 3 * 3600, mix=SUB_WEIGHTS) -> list:
    """[(at, amount, sub)]: `target` in uneven, distinct, non-round amounts at random waking hours (VN 08-23) over
    `days` days from t0; the first one within `first_within` seconds of t0."""
    n = _count(target, rng)
    w = [rng.uniform(.25, 1.9) for _ in range(n)]
    amounts = [max(1, int(target * x / sum(w))) for x in w]
    seen = set()
    for i, a in enumerate(amounts):
        a = a - a % 1000 + rng.randint(101, 989) if a > 2000 else a
        while a in seen or (a > 2000 and a % 1000 == 0):
            a += rng.randint(1, 97)
        seen.add(a)
        amounts[i] = a
    diff = target - sum(amounts)
    amounts[-1] += diff
    if amounts[-1] <= 0 or amounts[-1] in amounts[:-1] or (amounts[-1] > 2000 and amounts[-1] % 1000 == 0):
        return split(target, random.Random(rng.random()), t0, days, first_within, mix)
    day0 = int((t0 + VN) // 86400)
    ats = [t0 + rng.randint(300, first_within)]
    picks = [rng.randrange(days) for _ in range(n - 1)]
    for d in picks:
        base = (day0 + d) * 86400 - VN
        at = base + rng.randint(8 * 3600, 23 * 3600)
        ats.append(at if at > t0 else t0 + rng.randint(600, 6 * 3600))
    ats.sort()
    subs = [rng.choices([s for s, _ in mix], [k for _, k in mix])[0] for _ in range(n)]
    rng.shuffle(amounts)
    return list(zip(ats, amounts, subs))


def _fmt(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def _when(t: float) -> str:
    return time.strftime('%d/%m %H:%M', time.gmtime(t + VN))


def _store():
    from game import db as dbm
    from game.storage import Store
    dbm.database_url()
    return Store(os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')), story=True)


def _sid(db, uid: int) -> str:
    r = db.execute('SELECT sid FROM accounts WHERE uid=?', (uid,)).fetchone()
    if not r:
        sys.exit(f'uid {uid}: no such account')
    return r['sid']


def _rows(db, sid: str) -> list:
    from game import live_effects as lfx
    out = []
    for r in db.execute("SELECT id,amount,data,status,at FROM live_effects WHERE sid=? AND kind='mishap' ORDER BY at,id", (sid,)).fetchall():
        r = dict(r)
        taken = None
        if r['status'] == 'applied':
            rc = db.execute('SELECT result FROM receipts WHERE sid=? AND request_id=?', (sid, lfx.RID + lfx.short(r['id']))).fetchone()
            try:
                taken = int(json.loads(rc['result'])['live'].get('taken', 0)) if rc else None
            except (ValueError, KeyError, TypeError):
                taken = None
        r['taken'] = taken
        out.append(r)
    return out


def _insert(db, sid: str, uid: int, tag: str, sched: list, start: int) -> int:
    n = 0
    for k, (at, amount, sub) in enumerate(sched, start):
        n += db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) "
                        'ON CONFLICT(id) DO NOTHING',
                        (f'mishap-{uid}-{tag}-{k}', sid, 'mishap', int(amount), json.dumps(dict(sub=sub)), float(at))).rowcount
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('cmd', choices=('plan', 'status', 'topup', 'cancel'))
    ap.add_argument('--uid', type=int)
    ap.add_argument('--target', type=int)
    ap.add_argument('--tag', default='')
    ap.add_argument('--days', type=int, default=DAYS)
    ap.add_argument('--mix', default='', help='kinds and weights, e.g. police:3,hack:2,scam:1 (default: hack/scam/phish/atm/tip; police/thug also reach workplace funds)')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if a.cmd in ('plan', 'topup', 'cancel') and not a.uid:
        ap.error('--uid is required')
    if a.cmd in ('plan', 'topup') and not (a.tag and a.tag.isalnum() and len(a.tag) <= 12):
        ap.error('--tag: 1-12 letters/digits')
    store = _store()
    now = time.time()
    with store.connect() as db:
        if a.cmd == 'status':
            uids = [a.uid] if a.uid else [int(r['uid']) for r in db.execute(
                "SELECT DISTINCT a.uid FROM live_effects e JOIN accounts a ON a.sid=e.sid WHERE e.kind='mishap' ORDER BY a.uid").fetchall()]
            for uid in uids:
                rows = _rows(db, _sid(db, uid))
                planned = sum(r['amount'] for r in rows if r['status'] != 'void')
                taken = sum(r['taken'] or 0 for r in rows if r['status'] == 'applied')
                pend = [r for r in rows if r['status'] == 'pending']
                done = [r for r in rows if r['status'] == 'applied']
                short = sum(r['amount'] - (r['taken'] or 0) for r in done)
                nxt = _when(pend[0]['at']) if pend else '-'
                print(f'uid {uid}: planned {_fmt(planned)} · taken {_fmt(taken)} in {len(done)} · pending {len(pend)} '
                      f'({_fmt(sum(r["amount"] for r in pend))}, next {nxt}) · short {_fmt(short)}')
            return 0
        sid = _sid(db, a.uid)
        rows = _rows(db, sid)
    if a.cmd == 'cancel':
        pend = [r for r in rows if r['status'] == 'pending']
        print(f'uid {a.uid}: {len(pend)} pending row(s), {_fmt(sum(r["amount"] for r in pend))} xu' + ('' if a.write else ' (dry run)'))
        if a.write:
            store.transaction(lambda db: db.execute("UPDATE live_effects SET status='void', applied_at=? WHERE sid=? AND kind='mishap' AND status='pending'",
                                                    (now, sid)))
        return 0
    if a.cmd == 'plan':
        if not a.target or a.target < 1000:
            ap.error('--target (xu, at least 1000) is required')
        if any(r['id'].startswith(f'mishap-{a.uid}-{a.tag}-') for r in rows):
            sys.exit(f'uid {a.uid}: plan {a.tag} exists already (status / topup / cancel)')
        target, start = a.target, 1
    else:
        mine = [r for r in rows if r['id'].startswith(f'mishap-{a.uid}-{a.tag}-')]
        if any(r['status'] == 'pending' and r['at'] <= now for r in mine):
            sys.exit('rows due but not paid yet (the player has not come back): top up later')
        target = sum(r['amount'] - (r['taken'] or 0) for r in mine if r['status'] == 'applied' and r['taken'] is not None)
        start = len(mine) + 1
        if target < 1000:
            print(f'uid {a.uid}: nothing to top up ({_fmt(target)} xu short)')
            return 0
    rng = random.Random(f'{a.uid}|{a.tag}|{start}|{target}|{os.urandom(8).hex()}')
    mix = SUB_WEIGHTS
    if a.mix:
        from game.mishap import SUBS
        mix = tuple((k, int(w)) for k, w in (x.split(':') for x in a.mix.split(',')))
        if not all(k in SUBS and w > 0 for k, w in mix):
            ap.error(f'--mix: kinds from {SUBS}, positive weights')
    sched = split(target, rng, now, a.days, mix=mix)
    print(f'uid {a.uid} plan {a.tag}: {_fmt(target)} xu in {len(sched)} incident(s)' + ('' if a.write else ' (dry run)'))
    for at, amount, sub in sched:
        print(f'  {_when(at)}  {sub:5}  {_fmt(amount)}')
    if a.write:
        n = store.transaction(lambda db: _insert(db, sid, a.uid, a.tag, sched, start))
        print(f'written: {n} row(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
