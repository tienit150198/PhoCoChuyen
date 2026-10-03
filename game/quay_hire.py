"""💼 Quầy của bạn, B2: hire another player for one shift at your counter (game/quay.py).

Owner 03/10: "thuê người chơi khác về làm, tự set lương". The wage is the owner's own xu moved to the worker (never
minted); the worker does a real day of the trade (their own career, hands-on) and that day's work earns the counter
its sales (quay.shift_value x how the day went), like a day of an NPC hand.

Flow (one row per shift in `quay_jobs`; every money move is a save write under its revision guard in the same
transaction as a guarded row update, so each step happens once whatever the retries, tabs or processes):

* post (owner): the wage leaves the counter (till, then fund: the NPC wages' rule) into escrow, the row is 'open'
  for OPEN_HOURS. To anyone who knows the trade, or to one friend (a friendship of FRIEND_DAYS days at least).
* accept (worker): row open -> taken (`UPDATE … WHERE status='open'`: two players tapping at once, one gets it);
  the worker's save gets journey.quay.shift {career, day, base…}. One shift at a time.
* the worker plays their next day of that career; closing it (journey.after -> quay.on_shift) moves the shift to
  journey.quay.out with the tasks done that day. The client then calls flush (and every load does).
* flush (worker): row taken -> paid with the wage into the wallet ('salary', a kind the previous build knows) when the
  day had MIN_TASKS tasks or more; the owner's share of the day goes to the owner's live_effects inbox (kind 'quay',
  id quay:<job>:pay, applied once by game/live_effects.py into the till). Otherwise taken -> lapsed and the escrow
  goes back (quay:<job>:back into the fund).
* quit (worker, always free), cancel (owner, open only), decline (an invited friend), expiry (sweep): the escrow
  goes back to the counter, never to anyone else.

Fair and safe: nobody can take xu from another save (the only debit is the owner's own post); the worker's pay is
the escrow, the owner's refund is the escrow; both sides consent; caps against farming with a second account
(registered accounts ACCOUNT_DAYS old, LIFE_DAYS life days, the trade known; per worker WORKER_DAY shifts a day and
WORKER_WEEK_XU xu a week; one pair PAIR_WEEK shifts a week; an owner OWNER_DAY posts a day; a shift with too few
tasks pays nobody). Blocked players never see each other's offers.

Tables: SCHEMA below (SQLite) and game/pg_schema.py (PostgreSQL). The previous build has neither the table nor the
inbox kind: its saves keep journey.quay untouched and 'quay' inbox rows wait pending for this build.
"""
from __future__ import annotations

import json
import secrets
import time

from . import marriage as mr
from . import quay as qy

OPEN_HOURS = 24          # an offer nobody took expires (escrow back)
SHIFT_HOURS = 36         # a taken shift must be played and closed within this (escrow back after)
WAGE_MIN, WAGE_MAX = 10, 120
MIN_TASKS = 2            # tasks in the shift's day for it to count (pay + sales)
SHARE_BASE, SHARE_STEP, SHARE_MAX = 40, 20, 120   # % of shift_value the owner's counter earns: 40 + 20 x tasks, at most 120
LOW_STARS = 30           # average review under 3.0 stars (x10): the counter earns 80 % of that
WORKER_DAY = 2           # shifts a worker takes per VN day
WORKER_WEEK_XU = 400     # wages a worker earns per 7 days
PAIR_WEEK = 4            # shifts between one owner and one worker per 7 days
OWNER_DAY = 4            # offers an owner posts per VN day
ACCOUNT_DAYS = 3         # both accounts registered at least this long
LIFE_DAYS = 10           # both saves have lived this many days
FRIEND_DAYS = 2          # a friend-only offer: friends at least this long
BOARD_MAX = 20
MINE_DAYS = 2            # finished offers shown to their owner this long
SWEEP_EVERY = 30.0       # seconds between two expiry sweeps of one process
KIND = 'quay'            # live_effects kind (game/live_effects.py PAYS)
DAY = 86400
STATUSES = ('open', 'taken', 'paid', 'lapsed', 'quit', 'cancelled', 'declined', 'expired', 'gone')

SCHEMA = """
CREATE TABLE IF NOT EXISTS quay_jobs (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, owner_name TEXT NOT NULL, stall TEXT NOT NULL, stall_name TEXT NOT NULL,
  trade TEXT NOT NULL, place TEXT NOT NULL, wage INTEGER NOT NULL, value INTEGER NOT NULL, friend TEXT, worker TEXT,
  status TEXT NOT NULL, day TEXT NOT NULL, taken_day TEXT, at REAL NOT NULL, taken_at REAL, ended REAL, until REAL NOT NULL,
  tasks INTEGER NOT NULL DEFAULT 0, stars INTEGER NOT NULL DEFAULT 0, earned INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS quay_jobs_owner ON quay_jobs(owner, status);
CREATE INDEX IF NOT EXISTS quay_jobs_worker ON quay_jobs(worker, status);
CREATE INDEX IF NOT EXISTS quay_jobs_open ON quay_jobs(status, until);
"""

_swept = [0.0]


class QuayError(mr.MarriageError):
    """A refusal (shown as is). A MarriageError so the server answers it like Hôn nhân's."""


def need(cond, message: str, code: str = 'quay_error', status: int = 400):
    if not cond:
        raise QuayError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> str:
    return time.strftime('%Y-%m-%d', time.gmtime((now() if t is None else t) + 7 * 3600))


def share(value: int, tasks: int, stars: int) -> int:
    """What the counter earns from a shift of `tasks` tasks (0 under MIN_TASKS)."""
    if tasks < MIN_TASKS:
        return 0
    pct = min(SHARE_MAX, SHARE_BASE + SHARE_STEP * tasks)
    if 0 < stars < LOW_STARS:
        pct = pct * 80 // 100
    return max(1, value * pct // 100)


def wage_max(value: int) -> int:
    return max(WAGE_MIN, min(WAGE_MAX, value))


# ---------------------------------------------------------------- who
def _who(store, token: str) -> tuple:
    sid, display = mr.whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để thuê hoặc làm thêm nhé.', 'account_required', 403)
    return sid, display


def _old_enough(db, sid: str) -> bool:
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    if not r:
        return False
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now() - ACCOUNT_DAYS * DAY))
    return str(r['created_at']) <= cut


def _effect(db, eid: str, sid: str, amount: int, stall: str, what: str, label: str) -> None:
    """One credit into a save's inbox (game/live_effects.py applies it once, by this id)."""
    if amount <= 0:
        return
    data = json.dumps(dict(stall=stall, what=what, label=label[:80]), ensure_ascii=False)
    db.execute("INSERT INTO live_effects(id,sid,kind,amount,data,status,at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
               (eid, sid, KIND, int(amount), data, now()))


def _refund(db, r: dict, why: str) -> None:
    _effect(db, f'quay:{r["id"]}:back', r['owner'], r['wage'], r['stall'], 'back', f'💼 {why}: lương giữ chỗ về lại')


def _ping(store, sid: str, text: str) -> None:
    """A phone notification (game/push.py), best effort, after the write: never fails a step."""
    from . import push
    try:
        store.transaction(lambda db: push.queue(db, sid, KIND, text, '/'), 250)
    except Exception:  # noqa: BLE001 - no push tables (tests, a dev database), a busy moment
        pass


def _row(db, jid) -> dict | None:
    if not isinstance(jid, str) or not qy.JOB_RE.fullmatch(jid):
        return None
    return mr._row(db, 'SELECT * FROM quay_jobs WHERE id=?', (jid,))


def _end(db, r: dict, status: str, frm: str, extra: str = '', args: tuple = ()) -> bool:
    """Guarded status change; True when this call made it."""
    return db.execute(f'UPDATE quay_jobs SET status=?,ended=?{extra} WHERE id=? AND status=?',
                      (status, now(), *args, r['id'], frm)).rowcount == 1


# ---------------------------------------------------------------- owner: post, cancel
def post(store, sid: str, display: str, d: dict) -> dict:
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    s = loaded[0]
    j = s['journey']
    need(j.get('story'), 'Quầy riêng chỉ có trong hành trình.', 'not_story')
    st = next((x for x in (qy.get(s) or {}).get('stalls', ()) if x['id'] == d.get('stall')), None)
    need(st, 'Không thấy quầy này.', 'no_stall', 404)
    need(st['due'] == 0 and st['left'] <= qy.LEFT_DAYS, 'Quầy đang đóng. Mở lại quầy trước nhé.', 'closed')
    need(int(j['life_day']) >= LIFE_DAYS, f'Thuê người chơi mở từ ngày sống {LIFE_DAYS}.', 'too_new')
    value = qy.shift_value(st['place'], st['trade'])
    wage = d.get('wage')
    need(type(wage) is int and WAGE_MIN <= wage <= wage_max(value), f'Lương từ {WAGE_MIN} tới {wage_max(value)} xu một ca.', 'bad_wage')
    need(st['till'] + st['fund'] >= wage, f'Két và vốn quầy chưa đủ {wage} xu để giữ lương.', 'no_funds')
    friend = None
    code = d.get('to')
    t = now()
    with store.connect() as db:
        need(_old_enough(db, sid), f'Tài khoản cần {ACCOUNT_DAYS} ngày tuổi để thuê người chơi.', 'too_new')
        if code:
            p = mr._find(db, mr.clean_code(code))
            need(p and p['sid'] != sid, 'Không tìm thấy người này.', 'not_found', 404)
            friend = p['sid']
            f = db.execute('SELECT since FROM friends WHERE sid=? AND friend=?', (sid, friend)).fetchone()
            need(f and float(f['since']) <= t - FRIEND_DAYS * DAY, f'Mời riêng chỉ cho bạn bè đã kết bạn {FRIEND_DAYS} ngày.', 'not_friend')
            need(not mr._blocked(db, sid, friend), 'Không mời được người này.', 'blocked')
    jid = 'qj-' + secrets.token_hex(8)
    day = vn_day(t)
    P = qy.PLACES[st['place']]

    def fn(s2):
        st2 = qy.stall(s2, st['id'])
        need(st2['till'] + st2['fund'] >= wage, f'Két và vốn quầy chưa đủ {wage} xu để giữ lương.', 'no_funds')
        qy._from_till_fund(st2, wage)
        qy._log(st2, int(s2['journey']['life_day']), '💼 Giữ lương ca làm thêm', -wage)

    def ops(db):
        need(db.execute('SELECT COUNT(*) FROM quay_jobs WHERE owner=? AND day=?', (sid, day)).fetchone()[0] < OWNER_DAY,
             f'Mỗi ngày đăng tối đa {OWNER_DAY} ca thôi nhé.', 'rate_limited', 429)
        need(db.execute("SELECT COUNT(*) FROM quay_jobs WHERE owner=? AND stall=? AND status IN ('open','taken')",
                        (sid, st['id'])).fetchone()[0] < P['slots'], f'Quầy này chỉ đăng {P["slots"]} ca cùng lúc.', 'full')
        db.execute('INSERT INTO quay_jobs(id,owner,owner_name,stall,stall_name,trade,place,wage,value,friend,worker,status,day,at,until) '
                   "VALUES(?,?,?,?,?,?,?,?,?,?,NULL,'open',?,?,?)",
                   (jid, sid, display[:24], st['id'], st['name'], st['trade'], st['place'], wage, value, friend, day, t, t + OPEN_HOURS * 3600))
    mr._mutate_retry(store, {sid: fn}, ops)
    if friend:
        _ping(store, friend, f'💼 {display[:24]} mời bạn làm một ca ở {st["name"]}: {wage} xu.')
    return dict(message=f'💼 Đã đăng ca làm thêm, lương {wage} xu (đã giữ từ quầy).', changed=True)


def cancel(store, sid: str, display: str, d: dict) -> dict:
    with store.connect() as db:
        r = _row(db, d.get('id'))
    need(r and r['owner'] == sid and r['status'] == 'open', 'Ca này không hủy được nữa.', 'gone', 409)

    def fn(s):
        qy.credit(s, r['stall'], 'back', r['wage'], '💼 Hủy ca làm thêm')

    def ops(db):
        need(_end(db, r, 'cancelled', 'open'), 'Ca này vừa có người nhận.', 'taken', 409)
    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(message=f'Đã hủy. {r["wage"]} xu về lại vốn quầy.', changed=True)


# ---------------------------------------------------------------- worker: accept, decline, quit
def _can_work(s: dict, trade: str) -> str | None:
    j = s['journey']
    if not j.get('story'):
        return 'Làm thêm chỉ có trong hành trình.'
    if int(j['life_day']) < LIFE_DAYS:
        return f'Làm thêm mở từ ngày sống {LIFE_DAYS}.'
    if qy.served(s, trade) < qy.UNLOCK_SERVED:
        return f'Làm {qy.UNLOCK_SERVED} việc ở nghề này trước nhé.'
    return None


def accept(store, sid: str, display: str, d: dict) -> dict:
    t = now()
    with store.connect() as db:
        r = _row(db, d.get('id'))
        need(r and r['status'] == 'open' and r['until'] > t and r['friend'] in (None, sid), 'Ca này vừa có người nhận rồi.', 'gone', 409)
        need(r['owner'] != sid, 'Đây là ca của quầy bạn mà.', 'own')
        need(not mr._blocked(db, sid, r['owner']), 'Không nhận được ca này.', 'blocked')
        need(_old_enough(db, sid), f'Tài khoản cần {ACCOUNT_DAYS} ngày tuổi để làm thêm.', 'too_new')
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    why = _can_work(loaded[0], r['trade'])
    need(not why, why or '', 'cannot')
    day = vn_day(t)
    trade = qy.TRADES[r['trade']]

    def fn(s):
        need(not _can_work(s, r['trade']), 'Chưa nhận được ca này.', 'cannot')
        q = qy.ensure(s)
        need(q['shift'] is None, 'Bạn đang có một ca làm thêm rồi. Làm xong hoặc bỏ ca đó trước nhé.', 'busy_shift')
        c = s['careers'][r['trade']]
        q['shift'] = dict(id=r['id'], career=r['trade'], day=int(c['day']), base=int(c.get('day_completed') or 0) if c.get('open') else 0,
                          wage=r['wage'], value=r['value'], who=r['owner_name'][:24], name=r['stall_name'][:qy.NAME_MAX],
                          until=int(t + SHIFT_HOURS * 3600))

    def ops(db):
        week = t - 7 * DAY
        need(db.execute('SELECT COUNT(*) FROM quay_jobs WHERE worker=? AND taken_day=?', (sid, day)).fetchone()[0] < WORKER_DAY,
             f'Mỗi ngày nhận tối đa {WORKER_DAY} ca thôi nhé.', 'rate_limited', 429)
        got = db.execute("SELECT COALESCE(SUM(wage),0) FROM quay_jobs WHERE worker=? AND taken_at>? AND status IN ('taken','paid')",
                         (sid, week)).fetchone()[0]
        need(int(got) + r['wage'] <= WORKER_WEEK_XU, f'Tuần này bạn làm thêm đủ {WORKER_WEEK_XU} xu rồi. Nghỉ chút nhé.', 'rate_limited', 429)
        need(db.execute('SELECT COUNT(*) FROM quay_jobs WHERE owner=? AND worker=? AND taken_at>?', (r['owner'], sid, week)).fetchone()[0] < PAIR_WEEK,
             f'Một quầy chỉ thuê một người {PAIR_WEEK} ca mỗi tuần.', 'rate_limited', 429)
        n = db.execute("UPDATE quay_jobs SET status='taken',worker=?,taken_day=?,taken_at=?,until=? "
                       "WHERE id=? AND status='open' AND owner<>? AND (friend IS NULL OR friend=?) AND until>?",
                       (sid, day, t, t + SHIFT_HOURS * 3600, r['id'], sid, sid, t)).rowcount
        need(n == 1, 'Ca này vừa có người nhận rồi.', 'gone', 409)
    mr._mutate_retry(store, {sid: fn}, ops)
    _ping(store, r['owner'], f'💼 {display[:24]} đã nhận ca ở {r["stall_name"]}.')
    return dict(message=f'💼 Đã nhận ca! Vào làm {trade["emoji"]} {trade["name"]}, xong {MIN_TASKS} việc trở lên rồi khép ca.', changed=True)


def decline(store, sid: str, display: str, d: dict) -> dict:
    with store.connect() as db:
        r = _row(db, d.get('id'))
    need(r and r['friend'] == sid and r['status'] == 'open', 'Lời mời này không còn nữa.', 'gone', 409)

    def run(db):
        if _end(db, r, 'declined', 'open'):
            _refund(db, r, 'Bạn được mời bận')
    store.transaction(run)
    return dict(message='Đã từ chối. Không sao đâu!', changed=False)


def quit_shift(store, sid: str, display: str, d: dict) -> dict:
    """Bỏ ca: always possible, costs the worker nothing; the escrow goes back to the counter."""
    loaded = mr._read_state(store, sid)
    sh = ((qy.get(loaded[0]) or {}).get('shift') if loaded else None)
    need(sh, 'Bạn không có ca làm thêm nào.', 'gone', 409)
    with store.connect() as db:
        r = _row(db, sh['id'])

    def fn(s):
        q = qy.get(s)
        if q and q.get('shift') and q['shift']['id'] == sh['id']:
            q['shift'] = None

    def ops(db):
        if r and r['worker'] == sid and _end(db, r, 'quit', 'taken'):
            _refund(db, r, 'Người làm thêm bận')
    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(message='Đã bỏ ca. Lần sau nhé!', changed=True)


# ---------------------------------------------------------------- worker: settle finished shifts
def flush(store, sid: str) -> bool:
    """Settle this save's finished shifts (journey.quay.out) and drop a shift whose row ended. True when it wrote."""
    wrote = False
    for _ in range(qy.OUT_MAX + 2):
        loaded = mr._read_state(store, sid)
        q = qy.get(loaded[0]) if loaded else None
        if not q:
            return wrote
        sh = q.get('shift')
        out = q.get('out') or []
        if not out and not sh:
            return wrote
        with store.connect() as db:
            if out:
                o = out[0]
                r = _row(db, o['id'])
            else:
                o, r = None, _row(db, sh['id'])
                if r and r['status'] == 'taken' and r['worker'] == sid:
                    return wrote   # still on: nothing to do
        if o is None:
            def fn(s, jid=sh['id']):
                qq = qy.get(s)
                if qq.get('shift') and qq['shift']['id'] == jid:
                    qq['shift'] = None
            ops = None
        else:
            live = bool(r and r['status'] == 'taken' and r['worker'] == sid)
            pay = live and not o['late'] and o['tasks'] >= MIN_TASKS
            earned = share(r['value'], o['tasks'], o['stars']) if pay else 0

            def fn(s, o=o, r=r, pay=pay):
                qq = qy.get(s)
                qq['out'] = [x for x in qq['out'] if x['id'] != o['id']]
                if pay:
                    from . import journey as jr
                    jr._wallet(s['journey'], r['wage'], 'salary', f'💼 Làm thêm ở {r["stall_name"]}'[:120], r['trade'])

            def ops(db, o=o, r=r, live=live, pay=pay, earned=earned):
                if not live:
                    return
                if pay:
                    if not _end(db, r, 'paid', 'taken', ',tasks=?,stars=?,earned=?', (o['tasks'], o['stars'], earned)):
                        raise mr._Retry()
                    _effect(db, f'quay:{r["id"]}:pay', r['owner'], earned, r['stall'], 'shift', f'💼 Ca của {mr._display(db, sid)}')
                elif _end(db, r, 'lapsed', 'taken', ',tasks=?,stars=?', (o['tasks'], o['stars'])):
                    _refund(db, r, 'Ca chưa đủ việc')
        try:
            mr._mutate(store, {sid: fn}, ops)
            wrote = True
        except mr._Retry:
            time.sleep(.01)
    return wrote


def on_load(store, token: str, state: dict | None) -> bool:
    """Bootstrap: settle finished shifts. Cheap when the save has none."""
    q = ((state or {}).get('journey') or {}).get(qy.KEY)
    if not isinstance(q, dict) or not (q.get('out') or q.get('shift')):
        return False
    return flush(store, store.key(token))


# ---------------------------------------------------------------- expiry
def sweep(store, force: bool = False) -> int:
    """Offers nobody took and shifts never played: expired, escrow back. At most every SWEEP_EVERY seconds a process."""
    t = now()
    if not force and t - _swept[0] < SWEEP_EVERY:
        return 0
    _swept[0] = t
    with store.connect() as db:
        rows = mr._rows(db, "SELECT * FROM quay_jobs WHERE status IN ('open','taken') AND until<? LIMIT 50", (t,))
    for r in rows:
        def run(db, r=r):
            if _end(db, r, 'expired', r['status']):
                _refund(db, r, 'Ca làm thêm hết hạn')
        store.transaction(run)
    return len(rows)


def forget(store, token: str) -> None:
    """Account deletion: this player's open offers go; a shift they held goes back to its counter."""
    sid = store.key(token)

    def run(db):
        db.execute("UPDATE quay_jobs SET status='gone',ended=? WHERE owner=? AND status='open'", (now(), sid))
        for r in mr._rows(db, "SELECT * FROM quay_jobs WHERE worker=? AND status='taken'", (sid,)):
            if _end(db, r, 'quit', 'taken'):
                _refund(db, r, 'Người làm thêm rời phố')
    store.transaction(run)


# ---------------------------------------------------------------- views
def _job(r: dict, db, me: str) -> dict:
    T = qy.TRADES.get(r['trade']) or {}
    out = dict(id=r['id'], trade=r['trade'], emoji=T.get('emoji', '💼'), stall=r['stall'], name=r['stall_name'], owner=r['owner_name'],
               wage=r['wage'], status=r['status'], until=int(r['until']), invite=r['friend'] == me)
    if r['owner'] == me:
        out['mine'] = True
        if r['worker']:
            out['worker'] = mr._display(db, r['worker'])
        if r['friend']:
            out['to'] = mr._display(db, r['friend'])
        if r['status'] == 'paid':
            out['earned'], out['tasks'] = r['earned'], r['tasks']
    return out


def view(store, sid: str, state: dict) -> dict:
    sweep(store)
    t = now()
    j = state.get('journey') or {}
    q = qy.get(state) or {}
    stalls = [x['id'] for x in q.get('stalls', ())]
    with store.connect() as db:
        mine = [_job(r, db, sid) for r in mr._rows(db, "SELECT * FROM quay_jobs WHERE owner=? AND (status IN ('open','taken') OR ended>?) "
                                                         'ORDER BY at DESC LIMIT 12', (sid, t - MINE_DAYS * DAY))]
        board = []
        for r in mr._rows(db, "SELECT * FROM quay_jobs WHERE status='open' AND until>? AND owner<>? AND (friend IS NULL OR friend=?) "
                              'ORDER BY (friend IS NULL), at DESC LIMIT 60', (t, sid, sid)):
            if len(board) >= BOARD_MAX or mr._blocked(db, sid, r['owner']) or _can_work(state, r['trade']):
                continue
            board.append(_job(r, db, sid))
        friends = []
        if stalls:
            cut = t - FRIEND_DAYS * DAY
            for r in mr._rows(db, 'SELECT f.friend, p.code FROM friends f JOIN marriage_people p ON p.sid=f.friend '
                                  'WHERE f.sid=? AND f.since<=? ORDER BY f.since LIMIT 40', (sid, cut)):
                friends.append(dict(name=mr._display(db, r['friend']), code=r['code']))
        ok = _old_enough(db, sid)
    lock = None
    if not ok:
        lock = f'Tài khoản cần {ACCOUNT_DAYS} ngày tuổi.'
    elif int(j.get('life_day') or 0) < LIFE_DAYS:
        lock = f'Mở từ ngày sống {LIFE_DAYS}.'
    return dict(mine=mine, board=board, friends=friends, lock=lock,
                rules=dict(wage_min=WAGE_MIN, wage_max=WAGE_MAX, tasks=MIN_TASKS, day=WORKER_DAY, week=WORKER_WEEK_XU, pair=PAIR_WEEK,
                           hours=OPEN_HOURS, shift_hours=SHIFT_HOURS))


def get(store, token: str, state: dict) -> dict:
    """GET /api/quay: settle finished shifts first (the state comes back when it moved)."""
    sid, _ = _who(store, token)
    changed = flush(store, sid)
    if changed:
        state = mr._read_state(store, sid)[0]
    out = view(store, sid, state)
    out['changed'] = changed
    return out


ACTIONS = dict(post=post, cancel=cancel, accept=accept, decline=decline, quit=quit_shift)


def act(store, token: str, op: str, d: dict) -> dict:
    """POST /api/quay/<op>. Returns {message, changed}."""
    need(isinstance(d, dict), 'Dữ liệu không hợp lệ.')
    sid, display = _who(store, token)
    if op == 'flush':
        return dict(message='', changed=flush(store, sid))
    handler = ACTIONS.get(op)
    need(handler, 'Không có thao tác này.', 'not_found', 404)
    mr.ensure_person(store, sid)
    return handler(store, sid, display, d)
