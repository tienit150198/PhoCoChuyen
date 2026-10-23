"""💤 The night compaction of big saves (game/slim.py): cold careers' old cash-book / journal rows go to the archive.

Player commands never compact; this job does it off-peak, one save at a time, through the normal command path
(Store.save_command: lock-free compute, then the revision compare-and-set that writes the save and its archive rows
in one transaction). A save that moved since it was listed is skipped (Conflict); a player who taps meanwhile gets
the usual quiet resync. The command settles nothing and leaves no trace in the play statistics (no updated_at, no
receipt).

Which saves: those updated in the last --days days but not in the last --idle-minutes (a player at the keyboard
is left alone), newest first, read page by page from the index stat_sessions_seen (updated_at, revision, sid)
with a keyset (no table scan), and only those whose stored state is at least --min-kb (pg_column_size: the stored,
compressed bytes, no detoasting; ~1/4 of the JSON text).

Throttled: --pause seconds after each command, at most --per-minute commands a minute, stops at --until (Vietnam
time, HH:MM; already past: nothing runs) or after --minutes, whichever comes first. --dry-run only reads: what
would move, per save. One line per save, then a summary line (also as JSON).

    nice -n 10 python scripts/slim_saves.py --until 05:00 [--dry-run] [--min-kb 512] [--per-minute 30]

systemd (04:00 Vietnam time = 21:00 UTC; the server's clock may be either):
    # /etc/systemd/system/mnl-slim.service
    [Service]
    Type=oneshot
    User=<the game's user>
    WorkingDirectory=<the checkout>
    EnvironmentFile=<the game's .env>          # DATABASE_URL, GAME_NAMESPACE as for the server
    ExecStart=/usr/bin/nice -n 10 <venv>/bin/python scripts/slim_saves.py --until 05:00
    # /etc/systemd/system/mnl-slim.timer
    [Timer]
    OnCalendar=*-*-* 04:00:00 Asia/Ho_Chi_Minh
    Persistent=false
    [Install]
    WantedBy=timers.target
"""
import argparse
import datetime
import json
import os
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import archive as ar  # noqa: E402
from game import fastjson as fj  # noqa: E402
from game import slim  # noqa: E402
from game.engine import GameError  # noqa: E402
from game.storage import Conflict, Store  # noqa: E402

VN = datetime.timezone(datetime.timedelta(hours=7))
_FIRST = ('SELECT sid, revision, updated_at, pg_column_size(state) AS size FROM sessions '
          'WHERE updated_at >= ? AND updated_at < ? ORDER BY updated_at DESC, revision DESC, sid DESC LIMIT ?')
_NEXT = ('SELECT sid, revision, updated_at, pg_column_size(state) AS size FROM sessions '
         'WHERE updated_at >= ? AND (updated_at, revision, sid) < (?, ?, ?) '
         'ORDER BY updated_at DESC, revision DESC, sid DESC LIMIT ?')


def _text(t: float) -> str:
    """updated_at's TEXT form (UTC): compared as text, the range is read from the index (a cast would scan)."""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


def pages(store, since: str, before: str, page: int):
    """Pages of (sid, revision, updated_at, stored size), newest first: updated in [since, before)."""
    key = None
    while True:
        with store.connect() as db:
            if key is None:
                rows = db.execute(_FIRST, (since, before, page)).fetchall()
            else:
                rows = db.execute(_NEXT, (since, *key, page)).fetchall()
        if not rows:
            return
        rows = [(r['sid'], r['revision'], r['updated_at'], int(r['size'] or 0)) for r in rows]
        yield rows
        if len(rows) < page:
            return
        key = (rows[-1][2], rows[-1][1], rows[-1][0])


def deadline(until: str | None, minutes: float, now: float) -> float:
    end = now + minutes * 60
    if until:
        h, m = (int(x) for x in until.split(':'))
        local = datetime.datetime.fromtimestamp(now, VN)
        end = min(end, local.replace(hour=h, minute=m, second=0, microsecond=0).timestamp())
    return end


def preview(store, sid: str) -> dict:
    """--dry-run: what the night command would move (on a private parse; nothing is written)."""
    with store.connect() as db:
        row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    if not row:
        return dict(careers=0, rows=0)
    s = store.parse_state(row['state'], sid)
    before = len(fj.dumps(s))
    with ar.collect() as box:
        done = slim.compact(s, slim.MAX_PER_COMMAND)
    return dict(careers=len(done), rows=len(box.rows), kb_before=before // 1024, kb_after=len(fj.dumps(s)) // 1024)


def run(store, *, days: float = 30, idle_minutes: float = 15, min_kb: int = 512, page: int = 200, careers: int = slim.PER_COMMAND,
        rounds: int = 4, pause: float = 0.5, per_minute: int = 30, end: float | None = None, max_saves: int = 0,
        dry_run: bool = False, log=print, clock=time.time, sleep=time.sleep) -> dict:
    now = clock()
    end = now + 3600 if end is None else end
    out = dict(pages=0, listed=0, big=0, compacted=0, commands=0, careers=0, nothing=0, conflicts=0, errors=0,
               kb_before=0, kb_after=0, stopped='done', dry_run=dry_run)
    window = []   # times of the commands of the last minute
    for rows in pages(store, _text(now - days * 86400), _text(now - idle_minutes * 60), page):
        out['pages'] += 1
        out['listed'] += len(rows)
        for sid, revision, _, size in rows:
            if size < min_kb * 1024:
                continue
            if clock() >= end:
                out['stopped'] = 'deadline'
                return out
            if max_saves and out['big'] >= max_saves:
                out['stopped'] = 'max_saves'
                return out
            out['big'] += 1
            if dry_run:
                try:
                    p = preview(store, sid)
                except Exception as e:   # noqa: BLE001 (one bad save never stops the night)
                    out['errors'] += 1
                    log(f'{sid[:12]} error {type(e).__name__}: {e}')
                    continue
                out['careers'] += p['careers']
                if p['careers']:
                    out['compacted'] += 1
                    out['kb_before'] += p['kb_before']
                    out['kb_after'] += p['kb_after']
                log(f'{sid[:12]} stored={size // 1024}KB would move careers={p["careers"]} rows={p["rows"]}'
                    + (f' json {p["kb_before"]}KB -> {p["kb_after"]}KB' if p['careers'] else ''))
                continue
            moved, state = 0, 'nothing'
            for _ in range(rounds):
                while True:   # at most per_minute commands in any minute
                    window = [t for t in window if clock() - t < 60]
                    if len(window) < per_minute:
                        break
                    sleep(max(0.05, 60 - (clock() - window[0])))
                if clock() >= end:
                    break
                window.append(clock())
                out['commands'] += 1
                try:
                    res = store.save_command(sid, 'slim-' + secrets.token_hex(12), revision, slim.ACTION, dict(careers=careers))
                except Conflict:
                    state = 'moved'
                    out['conflicts'] += 1
                    break
                except GameError as e:
                    if getattr(e, 'code', None) != 'slim_nothing':
                        state = 'refused'
                        out['errors'] += 1
                        log(f'{sid[:12]} refused: {e}')
                    break
                except Exception as e:   # noqa: BLE001
                    state = 'error'
                    out['errors'] += 1
                    log(f'{sid[:12]} error {type(e).__name__}: {e}')
                    break
                finally:
                    sleep(pause)
                revision = res['revision']
                info = res['result'].get('slim') or {}
                moved += len(info.get('careers') or ())
                state = 'done'
                if not info.get('left'):
                    break
            if moved:
                out['compacted'] += 1
                out['careers'] += moved
                with store.connect() as db:
                    after = int(db.execute('SELECT pg_column_size(state) FROM sessions WHERE sid=?', (sid,)).fetchone()[0] or 0)
                out['kb_before'] += size // 1024
                out['kb_after'] += after // 1024
                log(f'{sid[:12]} {state} careers={moved} stored {size // 1024}KB -> {after // 1024}KB')
            elif state == 'nothing':
                out['nothing'] += 1
            elif state == 'moved':
                log(f'{sid[:12]} skipped: the save moved')
            if clock() >= end:
                out['stopped'] = 'deadline'
                return out
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--days', type=float, default=30, help='saves updated in the last N days')
    p.add_argument('--idle-minutes', type=float, default=15, help='skip saves updated in the last N minutes')
    p.add_argument('--min-kb', type=int, default=512, help='stored (compressed) size of the state, at least')
    p.add_argument('--page', type=int, default=200, help='index rows a statement')
    p.add_argument('--careers', type=int, default=slim.PER_COMMAND, help='cold careers a command at most')
    p.add_argument('--rounds', type=int, default=4, help='commands a save at most')
    p.add_argument('--pause', type=float, default=0.5, help='seconds after each command')
    p.add_argument('--per-minute', type=int, default=30, help='commands a minute at most')
    p.add_argument('--minutes', type=float, default=55, help='stop after N minutes')
    p.add_argument('--until', default=None, help='stop at HH:MM Vietnam time (already past: nothing runs)')
    p.add_argument('--max-saves', type=int, default=0, help='big saves to look at, at most (0: all)')
    p.add_argument('--dry-run', action='store_true', help='read only: what would move')
    a = p.parse_args()
    store = Store(os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game')))
    t0 = time.time()
    end = deadline(a.until, a.minutes, t0)
    stamp = lambda line: print(f'{time.strftime("%H:%M:%S")} {line}', flush=True)
    if end <= t0:
        stamp(f'deadline {a.until} already passed: nothing to do')
        return
    try:
        out = run(store, days=a.days, idle_minutes=a.idle_minutes, min_kb=a.min_kb, page=a.page, careers=a.careers,
                  rounds=a.rounds, pause=a.pause, per_minute=a.per_minute, end=end, max_saves=a.max_saves,
                  dry_run=a.dry_run, log=stamp)
    finally:
        store.close_pool()
    out['seconds'] = round(time.time() - t0, 1)
    stamp(('DRY RUN ' if a.dry_run else '') + f'{out["stopped"]}: listed={out["listed"]} big={out["big"]} '
          f'compacted={out["compacted"]} careers={out["careers"]} commands={out["commands"]} nothing={out["nothing"]} '
          f'conflicts={out["conflicts"]} errors={out["errors"]} {"json" if a.dry_run else "stored"} {out["kb_before"]}KB -> {out["kb_after"]}KB '
          f'in {out["seconds"]}s')
    print(json.dumps(dict(slim_saves=out), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
