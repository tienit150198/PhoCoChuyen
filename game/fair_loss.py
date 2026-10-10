"""Weekly fair net loss, recorded atomically with successful save commands.

No historical approximation: old cumulative totals are only the delta baseline.
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
                fair=dict(loss=True, weekly=True, next=w+WEEK, week=vn_day(w), started=started,
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
