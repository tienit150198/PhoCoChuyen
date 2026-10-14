#!/usr/bin/env python3
"""Recompute the 🏆 Bảng vàng chợ đen (Top lời) rows of this edition from the saves (game/leaderboard.py summary,
with the operator's fine refunds: game/fair_refund.py). The rows are derived data: each save's rows are synced to its
summary exactly as a command does, only where the save is still at the revision that was read (a save played
meanwhile is read again). Saves, wallets and titles are never written.

Which saves: those with a row on the board now and those with a fine refund this edition (fast, ~500 saves);
--all also walks every save that ever opened the Chợ đen (slow: run it off-peak, outside 17:30–20:00).

Dry run by default: prints how many rows would change and the five biggest moves (rank, uid, before → after; never a
session id). --apply writes them. Run from the release directory with the game's environment:

--week: 🗓️ this week's rows (fair_loss_week: Top lời and Top lỗ, game/fair_loss.py) instead. The week's rows are the
ledger itself (each command adds its change in its own transaction; a save keeps no wall-clock time of its rounds, so
they cannot be rebuilt from saves). What this adds: the Chợ đen fine refunds (system_gifts refund-cd-…, applied this
week, held by the save's journey.gifts) paid before the release that counts them, once each (marker
'fair-loss:refund:<gift id>', written with the row; a refund paid after it is counted by its own command). Saves are
locked and read only, never written; dry run by default, --apply writes.

  set -a; . /etc/mot-ngay-lam-nghe/game.env; . /etc/mot-ngay-lam-nghe/pg.env; set +a
  sudo -E -u mnl nice -n 15 python3 scripts/fair_board_recompute.py            # dry run
  sudo -E -u mnl nice -n 15 python3 scripts/fair_board_recompute.py --apply    # write
  sudo -E -u mnl nice -n 15 python3 scripts/fair_board_recompute.py --week     # this week: dry run (--apply writes)
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import fair as fh
from game import fair_loss
from game import fair_refund
from game import leaderboard as lb
from game.storage import Store


def targets(store, everyone: bool) -> list:
    board = fh.board()
    with store.connect() as db:
        sids = {r[0] for r in db.execute('SELECT sid FROM leaderboard WHERE board=?', (board,))}
    sids |= set(fair_refund.sids(store))
    if everyone:
        last = ''
        while True:
            with store.connect() as db:
                rows = db.execute("SELECT sid FROM sessions WHERE sid>? AND strpos(state,'\"fair\"')>0 ORDER BY sid LIMIT 200",
                                  (last,)).fetchall()
            if not rows:
                break
            sids |= {r[0] for r in rows}
            last = rows[-1][0]
            time.sleep(.05)
    return sorted(sids)


def plan(store, sids: list) -> tuple[list, list]:
    """([(sid, revision, rows)] to write, [(uid, before, after)] moves) for the saves whose fair row is not their summary."""
    board = fh.board()
    items, moves = [], []
    for i in range(0, len(sids), 40):
        part = sids[i:i + 40]
        marks = ','.join('?' * len(part))
        with store.connect() as db:
            saved = {r['sid']: r for r in db.execute(f'SELECT sid,revision,state FROM sessions WHERE sid IN ({marks})', part)}
            now = {r['sid']: int(r['score']) for r in db.execute(
                f'SELECT sid,score FROM leaderboard WHERE board=? AND sid IN ({marks})', (board, *part))}
            uids = {r['sid']: r['uid'] for r in db.execute(f'SELECT sid,uid FROM accounts WHERE sid IN ({marks})', part)}
        for sid in part:
            r = saved.get(sid)
            if r is None:
                continue
            try:
                rows = lb.summary(store.parse_state(r['state'], sid), fair_refund.of(store, sid))
            except (ValueError, TypeError, AttributeError, KeyError, RecursionError):
                continue   # an unreadable save: left as it is
            want = rows[board][0] if board in rows else None
            if want != now.get(sid):
                items.append((sid, r['revision'], rows))
                moves.append((uids.get(sid), now.get(sid), want))
        time.sleep(.05)
    return items, moves


def week(store, apply: bool) -> None:
    """--week: the refunds paid this week that the week's net does not hold yet (see the module doc)."""
    from game.wedding_live import vn_day, week_start
    w = int(week_start(fair_loss.now()))
    todo = fair_loss.refunds_missing(store)
    sids = sorted({r['sid'] for r in todo})
    with store.connect() as db:
        uids = {r['sid']: r['uid'] for r in db.execute(
            f'SELECT sid,uid FROM accounts WHERE sid IN ({",".join("?" * len(sids))})', sids)} if sids else {}
    before = fair_loss.week_net(store, sids)
    after = dict(before)
    for r in todo:
        after[r['sid']] += r['xu']
    print(f'week {vn_day(w)}: {len(todo)} fine refunds paid this week not in its net yet', flush=True)
    for sid in sorted(sids, key=lambda x: -(after[x] - before[x]))[:10]:
        uid = uids.get(sid)
        print(f'  uid {uid if uid is not None else "(guest)"}: {before[sid]} -> {after[sid]}', flush=True)
    if not apply or not todo:
        return
    got = {}
    for r in todo:
        res = fair_loss.fold_refund(store, r['id'], r['sid'], r['xu'])
        got[res] = got.get(res, 0) + 1
        time.sleep(.02)
    print('written: ' + ', '.join(f'{k} {v}' for k, v in sorted(got.items())), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='write the rows (default: dry run)')
    parser.add_argument('--all', action='store_true', help='also every save that opened the Chợ đen (slow)')
    parser.add_argument('--week', action='store_true', help="this week's Top lời/Top lỗ rows: add the fine refunds paid this week")
    args = parser.parse_args()
    store = Store(Path('storage/fair-board-recompute'))
    try:
        if args.week:
            week(store, args.apply)
            return
        sids = targets(store, args.all)
        items, moves = plan(store, sids)
        print(f'{fh.board()}: {len(sids)} saves read, {len(items)} rows differ from their save', flush=True)
        for uid, before, after in sorted(moves, key=lambda m: -abs((m[2] or 0) - (m[1] or 0)))[:5]:
            print(f'  uid {uid if uid is not None else "(guest)"}: {before if before is not None else "-"} -> '
                  f'{after if after is not None else "- (off the board)"}', flush=True)
        if not args.apply or not items:
            return
        left = items
        for _ in range(4):   # saves played meanwhile: read again (their command already wrote the new rows)
            moved = set(lb._sync(store, left))
            if not moved:
                break
            left, _ = plan(store, sorted(moved))
        lb.clear_cache()
        print(f'written: {len(items)} rows', flush=True)
    finally:
        store.close_pool()


if __name__ == '__main__':
    main()
