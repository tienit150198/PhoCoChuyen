"""Weekly fair net loss, recorded atomically with successful save commands.

Weekly deltas, with an explicit one-time current-save baseline when requested.
Weeks use transaction recording time in Vietnam. Import/reset never award loss.
"""
from __future__ import annotations

import json
import threading
import time
from . import fair as fh
from . import leaderboard as lb
from .wedding_live import week_start, vn_day

BOARD = 'fair-loss'
META = 'fair-loss:'
CURSOR = META + 'cursor'
WEEK = 7 * 86400
GRACE = 60
TOP = 10
TITLES = ('f_loss_king', 'f_loss_club')
SEED = META + 'seed:'
_due = {}
_lock = threading.Lock()
_FROM = 'FROM fair_loss_week l JOIN sessions s ON s.sid=l.sid LEFT JOIN accounts a ON a.sid=l.sid LEFT JOIN leaderboard_players p ON p.sid=l.sid'
_ORDER = 'ORDER BY l.net ASC,l.since ASC,l.sid ASC'


def now():
    return time.time()


def clear_cache():
    with _lock:
        _due.clear()


def _activate(db, t):
    w = int(week_start(t))
    db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
               (CURSOR, json.dumps(dict(next=w, started=t))))


def record(db, sid, before, after, action):
    """Called under the save row lock, in the transaction that writes its receipt."""
    if action in ('import_save', 'reset_all'):
        return
    previous = before.get('_fair_net', fh.money_of(before.get('journey'))[0])
    delta = fh.money_of(after.get('journey'))[0] - previous
    if not delta:
        return
    t = now()
    _activate(db, t)
    t = now()
    w = int(week_start(t))
    # Shared locks let players proceed together, but settlement waits for every
    # in-flight write of that week before freezing the final numbers.
    while True:
        db.execute('SELECT pg_advisory_xact_lock_shared(1947,?)', (w // WEEK,))
        t = now()
        current_week = int(week_start(t))
        if current_week == w:
            break
        # A paused writer may acquire its lock after that week's settlement.
        # Record in the current week under its lock, never alter frozen results.
        w = current_week
    db.execute('INSERT INTO fair_loss_week(week,sid,net,since) VALUES(?,?,?,?) '
               'ON CONFLICT(week,sid) DO UPDATE SET net=fair_loss_week.net+excluded.net,since=excluded.since',
               (w, sid, delta, t))


def _standings(db, w, limit):
    return [dict(r) for r in db.execute(
        f'SELECT l.sid,l.net,l.since,a.display,p.name AS gname,a.uid IS NOT NULL AS acct {_FROM} '
        f'WHERE l.week=? AND l.net<0 AND {lb._VISIBLE} {_ORDER} LIMIT ?', (w, limit))]


def seed_current(store, week, batch=50):
    """One resumable batch: use current fair balances for the owner-requested first week.

    Save rows and progress are locked before the week lock, just like record().
    Never called automatically: later weeks always start at zero.
    """
    week = int(week)
    if not 1 <= batch <= 200:
        raise ValueError('batch must be 1..200')
    mark = SEED + vn_day(week)

    def run(db):
        t = now()
        if int(week_start(t)) != week:
            raise ValueError('Only the current week may be seeded')
        initial = dict(last='', done=False, week=week, started=t, processed=0, balances=0)
        db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
                   (mark, json.dumps(initial)))
        progress = json.loads(db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (mark,)).fetchone()[0])
        if progress['done']:
            return progress
        # Acquire ALL save locks before the advisory lock: deletion also locks
        # saves and the settlement cursor, so alternating these locks can cycle.
        # Saved JSON uses literal ASCII keys. Most visitors never opened the fair;
        # skip full JSON parsing for their much larger career save payloads.
        rows = list(db.execute("SELECT sid,CASE WHEN strpos(state,'\"fair\"')>0 "
                               "THEN state::jsonb->'journey'->'fair' ELSE NULL END AS fair FROM sessions "
                               'WHERE sid>? ORDER BY sid LIMIT ? FOR UPDATE', (progress['last'], batch)))
        _activate(db, now())
        db.execute('SELECT pg_advisory_xact_lock_shared(1947,?)', (week // WEEK,))
        t = now()
        if int(week_start(t)) != week:
            raise ValueError('Week changed while seeding')
        zero = []
        for row in rows:
            net = fh.money_of(dict(fair=row['fair']))[0]
            if net:
                db.execute('INSERT INTO fair_loss_week(week,sid,net,since) VALUES(?,?,?,?) '
                           'ON CONFLICT(week,sid) DO UPDATE SET '
                           'since=CASE WHEN fair_loss_week.net<>excluded.net THEN excluded.since ELSE fair_loss_week.since END,'
                           'net=excluded.net', (week, row['sid'], net, t))
                progress['balances'] += 1
            else:
                # A reset/import before this requested snapshot has a current
                # zero balance. Do not create empty rows for untouched saves.
                zero.append(row['sid'])
        if zero:
            marks = ','.join('?' for _ in zero)
            db.execute(f'UPDATE fair_loss_week SET net=0,since=? WHERE week=? AND sid IN ({marks}) AND net<>0',
                       (t, week, *zero))
        if rows:
            progress['last'] = rows[-1]['sid']
        progress['processed'] += len(rows)
        progress['done'] = len(rows) < batch
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(progress), mark))
        return progress

    return store.transaction(run, best_effort_ms=500)


def settle(store, t=None, best_effort_ms=None):
    t = now() if t is None else t
    key = store.path
    with _lock:
        if _due.get(key, 0) > t:
            return

    def run(db):
        _activate(db, t)
        cursor = json.loads(db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()[0])
        w = int(cursor['next'])
        from .wedding_live import grant
        for _ in range(8):
            if t < w + WEEK + GRACE:
                break
            db.execute('SELECT pg_advisory_xact_lock(1947,?)', (w // WEEK,))
            mark = META + vn_day(w)
            if db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (mark, '[]')).rowcount:
                winners = []
                for i, r in enumerate(_standings(db, w, TOP)):
                    tid = TITLES[0 if i == 0 else 1]
                    grant(db, r['sid'], 'title', 1, f'{mark}:{tid}:{r["sid"]}', dict(title=tid, src='fair'))
                    winners.append(dict(rank=i+1, sid=r['sid'], score=-r['net'], title=tid))
                db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners), mark))
            w += WEEK
        cursor['next'] = w
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(cursor), CURSOR))
        return w + WEEK + GRACE

    due = store.transaction(run, best_effort_ms)
    if due:
        with _lock:
            if len(_due) > 32:
                _due.clear()
            _due[key] = due


def view(store, limit=20, token=None):
    t = now()
    w = int(week_start(t))
    settle(store, t, best_effort_ms=250)
    sid = lb._viewer(store, token)
    from .journey import TITLE_INDEX
    from . import lb_titles
    with store.connect() as db:
        top = _standings(db, w, limit)
        total = db.execute(f'SELECT COUNT(*) {_FROM} WHERE l.week=? AND l.net<0 AND {lb._VISIBLE}', (w,)).fetchone()[0]
        rows = [dict(rank=i+1, name=r['display'] if r['acct'] else r['gname'], guest=not r['acct'],
                     score=-r['net'], xu=-r['net'], days=0, me=r['sid']==sid) for i, r in enumerate(top)]
        me = None
        if sid:
            me = lb._privacy(db, sid)
            me.pop('show', None)
            mine = db.execute('SELECT net,since FROM fair_loss_week WHERE week=? AND sid=?', (w, sid)).fetchone()
            net = mine['net'] if mine else 0
            me.update(net=net, xu=max(0,-net), rank=None)
            if net < 0:
                ahead = db.execute(f'SELECT COUNT(*) {_FROM} WHERE l.week=? AND l.net<0 AND {lb._VISIBLE} '
                                   'AND (l.net,l.since,l.sid)<(?,?,?)', (w, net, mine['since'], sid)).fetchone()[0]
                me['rank'] = ahead+1
        meta = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (CURSOR,)).fetchone()
        started = json.loads(meta[0])['started'] if meta else t
        seeded = bool(db.execute('SELECT 1 FROM leaderboard_meta WHERE k=?', (SEED+vn_day(w),)).fetchone())
        prev = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META+vn_day(w-WEEK),)).fetchone()
        winners = []
        for r in json.loads(prev[0]) if prev else []:
            person = db.execute('SELECT a.display,p.name AS gname,p.show,a.uid IS NOT NULL AS acct '
                                'FROM sessions s LEFT JOIN accounts a ON a.sid=s.sid '
                                'LEFT JOIN leaderboard_players p ON p.sid=s.sid WHERE s.sid=?', (r['sid'],)).fetchone()
            person = dict(person, sid=r['sid']) if person else None
            title = TITLE_INDEX[r['title']]
            winners.append(dict(rank=r['rank'], score=r['score'], name=lb_titles._public(person,sid) if person else 'Một người chơi',
                                title=title['name'], emoji=title['emoji'], me=r['sid']==sid))
    tiers = [dict(label='Top 1' if i==0 else 'Top 2–10', lo=1 if i==0 else 2, hi=1 if i==0 else TOP,
                  emoji=TITLE_INDEX[tid]['emoji'], name=TITLE_INDEX[tid]['name']) for i,tid in enumerate(TITLES)]
    return dict(board=BOARD, total=total, rows=rows, me=me, weekly=None,
                fair=dict(loss=True, weekly=True, next=w+WEEK, week=vn_day(w), started=started, seeded=seeded,
                          tiers=tiers, winners=winners, crowned=vn_day(w) if prev else None, settled=bool(prev)))


def forget(db, sid):
    db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()
    db.execute('DELETE FROM fair_loss_week WHERE sid=?', (sid,))
    db.execute("DELETE FROM live_effects WHERE sid=? AND id LIKE ? AND status='pending'", (sid, META+'%'))
    for row in db.execute('SELECT k,v FROM leaderboard_meta WHERE k LIKE ? AND v LIKE ? FOR UPDATE',
                          (META+'____-__-__', '%'+sid+'%')).fetchall():
        values = json.loads(row['v'])
        for r in values:
            if r.get('sid') == sid:
                r['sid'] = ''
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(values), row['k']))
    clear_cache()
