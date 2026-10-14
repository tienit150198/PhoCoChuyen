"""Weekly fair net (Top lỗ and, from the week of 12/10/2026, Top lời), recorded atomically with save commands.

Weekly deltas, with an explicit one-time current-save baseline when requested.
Weeks use transaction recording time in Vietnam. Import/reset never award loss.

🏆 Top lời theo tuần (owner 14/10: "Top lời theo tuần như Top lỗ"): the same rows, net > 0, biggest first. A Chợ đen
fine the operator paid back (a system gift refund-cd-…, game/fair_refund.py PREFIX) counts in the week it is paid into
the save (record(), action sys_gift; a marker row per gift keeps it to once, scripts/fair_board_recompute.py --week
adds the ones paid before this release). Its titles (👑 Vua trò chơi, 🎪 Cao thủ chợ đen) are crowned with the week's
Top lỗ in settle(), under the same exclusive week lock, on the meta key the cumulative crowning used
(game/fair_board.py 'fair:<edition>@<Monday>'), so a Monday is crowned once whichever release gets there first.
"""
from __future__ import annotations

import datetime
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
REFUND = META + 'refund:'       # leaderboard_meta 'fair-loss:refund:<gift id>': that refund is in a week's net
WIN_TITLES = ('f_king', 'f_master')
# Top lời is weekly from the week of Monday 12/10/2026 (crowned on 19/10); the crownings before were cumulative.
WIN_FROM = int(datetime.datetime(2026, 10, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=7))).timestamp())
_due = {}
_lock = threading.Lock()
_FROM = 'FROM fair_loss_week l JOIN sessions s ON s.sid=l.sid LEFT JOIN accounts a ON a.sid=l.sid LEFT JOIN leaderboard_players p ON p.sid=l.sid'
_ORDER = 'ORDER BY l.net ASC,l.since ASC,l.sid ASC'
_ORDER_WIN = 'ORDER BY l.net DESC,l.since ASC,l.sid ASC'


def now():
    return time.time()


def clear_cache():
    with _lock:
        _due.clear()


def _activate(db, t):
    w = int(week_start(t))
    db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
               (CURSOR, json.dumps(dict(next=w, started=t))))


def _refund_paid(before, after, action):
    """(gift id, xu) when this command paid a Chợ đen fine refund into the save (system_gift.apply), else None."""
    if action != 'sys_gift':
        return None
    from .fair_refund import PREFIX
    jb, ja = before.get('journey'), after.get('journey')
    if type(jb) is not dict or type(ja) is not dict:
        return None
    had = jb.get('gifts') if type(jb.get('gifts')) is list else []
    new = [g for g in (ja.get('gifts') if type(ja.get('gifts')) is list else []) if g not in had]
    xu = ja.get('wallet', 0) - jb.get('wallet', 0) if type(ja.get('wallet')) is int and type(jb.get('wallet')) is int else 0
    if len(new) != 1 or type(new[0]) is not str or not new[0].startswith(PREFIX) or xu <= 0:
        return None
    return new[0], xu


def record(db, sid, before, after, action):
    """Called under the save row lock, in the transaction that writes its receipt."""
    if action in ('import_save', 'reset_all'):
        return
    previous = before.get('_fair_net', fh.money_of(before.get('journey'))[0])
    delta = fh.money_of(after.get('journey'))[0] - previous
    paid = _refund_paid(before, after, action)
    if paid and db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
                           (REFUND + paid[0], json.dumps(dict(sid=sid, xu=paid[1], at=now())))).rowcount == 1:
        delta += paid[1]   # 💸 a fine paid back: in this week's net, once (the marker rolls back with the command)
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


def refunds_missing(store, t=None) -> list:
    """[{id, sid, xu}]: Chợ đen fine refunds paid into saves this week (system_gifts applied_at) whose xu are not in
    the week's net yet (no REFUND marker: paid before this release). scripts/fair_board_recompute.py --week."""
    from .fair_refund import PREFIX
    w = int(week_start(now() if t is None else t))
    with store.connect() as db:
        rows = db.execute("SELECT g.id,g.sid,g.coins FROM system_gifts g WHERE g.id LIKE ? AND g.status IN ('applied','seen') "
                          'AND g.applied_at>=? AND g.applied_at<? AND NOT EXISTS (SELECT 1 FROM leaderboard_meta m WHERE m.k=?||g.id) '
                          'ORDER BY g.applied_at,g.id LIMIT 1000', (PREFIX + '%', w, w + WEEK, REFUND)).fetchall()
    return [dict(id=r['id'], sid=r['sid'], xu=int(r['coins'])) for r in rows if int(r['coins']) > 0]


def fold_refund(store, gid: str, sid: str, xu: int) -> str:
    """Add one refund paid this week to the week's net, once: 'added', 'done' (its marker exists), 'gone' (no save),
    'unpaid' (the save does not hold the gift: not counted) or 'late' (the week changed meanwhile: nothing written).
    The save is locked first and only read (like record()), then the marker, then the week's shared lock."""
    def run(db):
        row = db.execute('SELECT state FROM sessions WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        if not row:
            return 'gone'
        j = store.parse_state(row['state'], sid).get('journey') or {}
        if gid not in (j.get('gifts') if type(j.get('gifts')) is list else []):
            return 'unpaid'
        paid = db.execute('SELECT applied_at FROM system_gifts WHERE id=? AND sid=?', (gid, sid)).fetchone()
        t = now()
        w = int(week_start(t))
        if not paid or paid['applied_at'] is None or not w <= paid['applied_at'] < w + WEEK:
            return 'late'
        if db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
                      (REFUND + gid, json.dumps(dict(sid=sid, xu=xu, at=t, by='recompute')))).rowcount != 1:
            return 'done'
        _activate(db, t)
        db.execute('SELECT pg_advisory_xact_lock_shared(1947,?)', (w // WEEK,))
        t = now()
        if int(week_start(t)) != w:
            raise ValueError('Week changed while adding a refund')
        db.execute('INSERT INTO fair_loss_week(week,sid,net,since) VALUES(?,?,?,?) '
                   'ON CONFLICT(week,sid) DO UPDATE SET net=fair_loss_week.net+excluded.net,since=excluded.since',
                   (w, sid, xu, t))
        return 'added'
    try:
        return store.transaction(run)
    except ValueError:
        return 'late'


def week_net(store, sids, t=None) -> dict:
    """{sid: this week's net} (0 when no row)."""
    w = int(week_start(now() if t is None else t))
    out = {sid: 0 for sid in sids}
    if sids:
        marks = ','.join('?' * len(sids))
        with store.connect() as db:
            out.update({r['sid']: int(r['net']) for r in db.execute(
                f'SELECT sid,net FROM fair_loss_week WHERE week=? AND sid IN ({marks})', (w, *sids))})
    return out


def _standings(db, w, limit, win=False):
    return [dict(r) for r in db.execute(
        f'SELECT l.sid,l.net,l.since,a.display,p.name AS gname,a.uid IS NOT NULL AS acct {_FROM} '
        f'WHERE l.week=? AND l.net{">" if win else "<"}0 AND {lb._VISIBLE} {_ORDER_WIN if win else _ORDER} LIMIT ?', (w, limit))]


def weekly_win() -> bool:
    """Top lời is weekly while the Chợ đen has no end (an edition with an end is crowned at its close: fair_board)."""
    return fh.forever()


def win_key(w) -> str:
    """leaderboard_meta key of the Top lời crowning of the week starting at w (the Monday after it)."""
    from . import fair_board
    return fair_board.META + fh.edition() + '@' + vn_day(w + WEEK)


def _crown_win(db, w, grant):
    """Top lời of the week starting at w: 👑 to the first, 🎪 to the next nine, once (insert-if-absent on the key the
    cumulative crowning used, so an older release that got there first is not crowned over). The grant ids are the
    cumulative crowning's (per edition, title and player): a title already granted is not granted twice."""
    if w < WIN_FROM or not weekly_win() or w + WEEK <= fh.window()[0]:
        return None
    key = win_key(w)
    if not db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (key, '[]')).rowcount:
        return None
    ed, winners = fh.edition(), []
    for i, r in enumerate(_standings(db, w, TOP, win=True)):
        tid = WIN_TITLES[0 if i == 0 else 1]
        grant(db, r['sid'], 'title', 1, f'{ed}:{tid}:{r["sid"]}', dict(title=tid, src='fair'))
        winners.append(dict(rank=i+1, sid=r['sid'], score=r['net'], title=tid))
    db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners, separators=(',', ':')), key))
    return winners


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
    """Crown every finished week (at most 8 a call): Top lỗ, and Top lời from WIN_FROM. Returns the Top lời winners
    this call crowned (the latest week's; None when it had nobody or nothing was crowned)."""
    t = now() if t is None else t
    key = store.path
    with _lock:
        if _due.get(key, 0) > t:
            return None
    crowned = []

    def run(db):
        crowned.clear()   # a retried transaction starts again
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
            won = _crown_win(db, w, grant)
            if won is not None:
                crowned.append(won)
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
    return (crowned[-1] or None) if due and crowned else None


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


def view_win(store, asked, limit=20, token=None):
    """GET /api/leaderboard?board=<the fair's board>: 🏆 Top lời of this week (net > 0, biggest first), the player's
    week (`me.net`, signed) and the Bảng vàng's crowning block (game/fair_board.py board_view: tiers, the latest
    winners, the next Monday) plus `week`/`started`/`win`. `rows[].days`: days played this edition (an older client
    shows it). Never a session id."""
    from . import fair_board
    t = now()
    w = int(week_start(t))
    fair_board.ensure(store)   # settles this module's weeks too (Top lời and Top lỗ)
    sid = lb._viewer(store, token)
    board = fh.board()
    days = 'COALESCE((SELECT b.days FROM leaderboard b WHERE b.sid=l.sid AND b.board=?),0) AS days'
    with store.connect() as db:
        top = [dict(r) for r in db.execute(
            f'SELECT l.sid,l.net,l.since,a.display,p.name AS gname,a.uid IS NOT NULL AS acct,{days} {_FROM} '
            f'WHERE l.week=? AND l.net>0 AND {lb._VISIBLE} {_ORDER_WIN} LIMIT ?', (board, w, limit))]
        total = db.execute(f'SELECT COUNT(*) {_FROM} WHERE l.week=? AND l.net>0 AND {lb._VISIBLE}', (w,)).fetchone()[0]
        rows = [dict(rank=i+1, name=r['display'] if r['acct'] else r['gname'], guest=not r['acct'],
                     score=r['net'], xu=r['net'], days=int(r['days']), me=r['sid']==sid) for i, r in enumerate(top)]
        me = None
        if sid:
            me = lb._privacy(db, sid)
            me.pop('show', None)
            mine = db.execute('SELECT net,since FROM fair_loss_week WHERE week=? AND sid=?', (w, sid)).fetchone()
            net = mine['net'] if mine else 0
            me.update(net=net, xu=max(0, net), rank=None)
            if net > 0:
                ahead = db.execute(f'SELECT COUNT(*) {_FROM} WHERE l.week=? AND l.net>0 AND {lb._VISIBLE} '
                                   'AND (l.net>? OR (l.net=? AND (l.since,l.sid)<(?,?)))',
                                   (w, net, net, mine['since'], sid)).fetchone()[0]
                me['rank'] = ahead+1
        meta = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (CURSOR,)).fetchone()
        started = json.loads(meta[0])['started'] if meta else t
    fair = fair_board.board_view(store, sid)
    fair.update(win=True, week=vn_day(w), started=started, weekly=True, next=w+WEEK)
    return dict(board=asked, total=total, rows=rows, me=me, weekly=None, fair=fair)


def forget(db, sid):
    db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()
    db.execute('DELETE FROM fair_loss_week WHERE sid=?', (sid,))
    db.execute("DELETE FROM live_effects WHERE sid=? AND id LIKE ? AND status='pending'", (sid, META+'%'))
    from .fair_board import META as WIN_META
    for row in db.execute('SELECT k,v FROM leaderboard_meta WHERE (k LIKE ? OR k LIKE ?) AND v LIKE ? FOR UPDATE',
                          (META+'____-__-__', WIN_META+'%@____-__-__', '%'+sid+'%')).fetchall():
        values = json.loads(row['v'])
        for r in values:
            if r.get('sid') == sid:
                r['sid'] = ''
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(values), row['k']))
    clear_cache()
