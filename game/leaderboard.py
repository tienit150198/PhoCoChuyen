"""Bảng xếp hạng: players ranked by what they did, never by what a client says.

Boards
* ``all``  - Top trải nghiệm, overall. Score = the journey's "trưởng thành" XP: the
  XP of every workplace + 80 for each workplace where you served at least one
  customer (journey.BREADTH_XP); the level shown is journey.maturity(score).
  Ties: more workplaces mastered (level 3 there, the career titles), then more
  days worked in total, then who reached that score first, then a fixed order.
* ``<career id>`` - Top trải nghiệm at one workplace. Score = that workplace's XP
  (level = 1 + XP // 90, as in the game). Ties: more days worked there (days
  closed = day - 1), then the higher average star rating of the reviews kept in
  the save (x10, as the game shows it), then first to reach, then a fixed order.
* ``certs`` - Top chứng chỉ. Score = certificates earned. Ties: higher total of
  the best exam score of those certificates, then earned sooner (the in-game life
  day of the latest one), then first to reach, then a fixed order.
* ``titles`` - Top danh hiệu. Score = game titles earned (game/journey.py TITLES,
  secret ones included). Ties: more secret titles, then earned sooner (the life
  day of the latest one), then first to reach, then a fixed order.
* ``wealth`` - 💰 Top tài phú (owner 05/10: "thêm top tài phú cho toàn server").
  Score = net worth in xu (game/wealth.py): what the "Tiền của bạn" sheet shows
  (wallet, workplace funds, bank, homes at market value, minus every debt), plus
  the Mây savings book, Mây Coin and gold at their cost basis (giá vốn, never a
  live price), vehicles at buy-back price and Quầy riêng at their sang nhượng
  price, minus what those counters owe and the fair's Vay nóng. Not the couple's
  Quỹ chung. Story mode only;
  0 or less: no row. Ties: more total assets, then who reached that amount
  first, then a fixed order.

Weekly titles: the top of `all`, `titles`, `certs`, `wealth` and of every workplace board
hold a title for the week, recomputed daily (game/lb_titles.py).

* ``fair<YYYYMMDD>xu`` - 🏆 Bảng vàng hội chợ while a folk fair runs (game/fair.py
  board()): the xu won at the fair this edition (fair.money_of; only players
  ahead have a row), days played. Ties: who reached the score first. Not a
  weekly-title board: its titles are granted once after the fair
  (game/fair_board.py). The rows of ``fair<YYYYMMDD>`` (its points until 03/10)
  are no longer read.

Server authoritative: rows are derived from the save stored on the server (see
``summary``), written by the storage layer in the same transaction as the save
(Store._store / _command_locked), and only when a number on a board changed.
A startup ``backfill`` (background thread, small batches) fills the table from
saves written before it existed.

Who is shown: accounts under their account display name (on by default); guests
only when they turned "Hiện tên tôi trên bảng xếp hạng" on and gave their
character a name (tagged "khách"). Only that display name leaves the server:
never usernames, save ids or IPs. Everyone can hide their name again.
"""
from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict

from . import lb_titles as lbt   # 🏅 Danh hiệu tuần (the top of each board, refreshed daily)
from . import fair as fh          # 🏮 Hội chợ dân gian: its board (fh.board()) while it runs
from . import wealth as wl        # 💰 net worth: "Tiền của bạn" (public/js/v4/wealth.js) + what the save holds beyond it
from .content import CAREERS

VERSION = 4                # rebuild rows on startup (4: auction collections)
OVERALL, CERTS, TITLES, WEALTH = 'all', 'certs', 'titles', 'wealth'
COLLECTION = 'collection'
CAREER_IDS = frozenset(CAREERS)
BOARDS = CAREER_IDS | {OVERALL, CERTS, TITLES, WEALTH, COLLECTION}
NAME = '_name'              # summary key of the guest's character name (not a board)
LIMIT = 50
CACHE_SECONDS = 5.0
GUEST_DEFAULT = 0           # guests are hidden until they opt in (privacy policy: nothing public unless you turn it on)
XP_PER_LEVEL = 90
MASTER_LEVEL = 3            # the career titles are earned at level 3


# score, k1, k2, level, days, served, stars (x10), mastered
_FIELDS = ('score', 'k1', 'k2', 'level', 'days', 'served', 'stars', 'mastered')


# ---------------------------------------------------------------- scoring
def _int(v, low: int = 0) -> int:
    return v if type(v) is int and v > low else low


def certificates_of(state: dict) -> dict:
    """The certificates of a save: {group_id: {score, best, earned_day, attempts}}.
    The only place that knows where they live; missing or malformed means none."""
    j = state.get('journey')
    certs = j.get('certificates') if type(j) is dict else None
    return certs if type(certs) is dict else {}


def _certs(state: dict) -> tuple[int, int, int]:
    """(earned, total best score of the earned ones, life day of the latest one)."""
    n = best = last = 0
    for rec in certificates_of(state).values():
        if type(rec) is not dict:
            continue
        day = rec.get('earned_day')
        if type(day) is not int or day < 0:
            continue
        n += 1
        best += _int(rec.get('best'))
        last = max(last, day)
    return n, best, last


def _titles(state: dict) -> tuple[int, int, int]:
    """(titles earned, secret ones among them, life day of the latest one). Ids this build does not know are
    not counted (validate_state refuses them anyway)."""
    from .journey import TITLE_INDEX
    j = state.get('journey')
    got = j.get('titles') if type(j) is dict else None
    if type(got) is not dict:
        return 0, 0, 0
    n = secret = last = 0
    for tid, day in got.items():
        t = TITLE_INDEX.get(tid)
        if t is None:
            continue
        n += 1
        secret += bool(t['secret'])
        if type(day) is int and day > last:
            last = day
    return n, secret, last


@functools.lru_cache(maxsize=4096)
def guest_name(name) -> str | None:
    """A guest's character name, if it may be shown: set by the player (not the
    default), and passing the same checks as an account display name."""
    from . import accounts
    if not isinstance(name, str) or not name.strip() or name.strip() == accounts.DEFAULT_NAME:
        return None
    try:
        return accounts.clean_display(name)
    except accounts.AccountError:
        return None


def summary(state) -> dict:
    """Every board row this save earns: {board: (score, k1, k2, level, days, served,
    stars, mastered)} plus NAME -> the guest name (or None). Pure and cheap: a few
    dozen dict reads per workplace, no copying."""
    from .journey import BREADTH_XP, maturity
    cs = state.get('careers') if type(state) is dict else None
    if type(cs) is not dict:
        return {}
    out = {}
    tot_xp = places = mastered = all_days = all_served = star_sum = star_n = 0
    for cid, c in cs.items():
        if cid not in CAREER_IDS or type(c) is not dict:
            continue
        xp = _int(c.get('xp'))
        m = c.get('metrics')
        served = _int(m.get('served')) if type(m) is dict else 0
        day = c.get('day')
        days = day - 1 if type(day) is int and day > 1 else 0
        feed = c.get('feed')
        got = [v for p in feed if type(p) is dict and type(v := p.get('stars')) is int and 0 < v < 6] if type(feed) is list and feed else ()
        ss, sn = sum(got), len(got)
        tot_xp += xp
        places += served > 0
        all_days += days
        all_served += served
        star_sum += ss
        star_n += sn
        level = 1 + xp // XP_PER_LEVEL
        mastered += level >= MASTER_LEVEL
        if xp > 0 or served > 0:
            stars = round(ss * 10 / sn) if sn else 0
            out[cid] = (xp, days, stars, level, days, served, stars, int(level >= MASTER_LEVEL))
    score = tot_xp + BREADTH_XP * places
    if score > 0:
        stars = round(star_sum * 10 / star_n) if star_n else 0
        out[OVERALL] = (score, mastered, all_days, maturity(score)['level'], all_days, all_served, stars, mastered)
    n, best, last = _certs(state)
    if n:
        out[CERTS] = (n, best, -last, n, last, best, 0, n)
    n, secret, last = _titles(state)
    if n:
        out[TITLES] = (n, secret, -last, n, last, secret, 0, n)
    w = wl.score(state)
    if w:     # 💰 net worth, then total assets; ties go to who reached the amount first (since)
        out[WEALTH] = (w[0], w[1], 0, 0, 0, 0, 0, 0)
    from .auction import collection_score
    points, items, legendary = collection_score(state)
    if points:
        # Ties: most items, most legendary items, then earliest score (since).
        out[COLLECTION] = (points, items, legendary, 0, 0, items, 0, legendary)
    won, days = fh.money_of(state.get('journey'))
    if won > 0:   # 🏆 Bảng vàng hội chợ: xu won, players ahead only; ties go to who reached the score first (since)
        out[fh.board()] = (won, 0, 0, 0, days, 0, 0, 0)
    out[NAME] = guest_name(state.get('name'))
    return out


def heal(rows: dict) -> bool:
    """Write these rows even though no number moved, on the first command a process sees of a save (game/storage.py,
    the summary was not remembered): fair and collection rows an older server (rolling release) may have dropped.
    One upsert that changes nothing at worst."""
    return fh.board() in rows or COLLECTION in rows


def diff(old: dict, new: dict) -> dict | None:
    """The new summary when anything on a board (or the guest name) moved, else None.
    The storage layer then syncs every row of that save (self-healing)."""
    return new if old != new else None


# The summary of the save a command starts from is usually the one the previous command
# stored: remembered per (save, revision), so a command computes only one summary.
_recent: OrderedDict = OrderedDict()
_recent_lock = threading.Lock()
RECENT = 1024


def recall(sid: str, revision: int) -> dict | None:
    with _recent_lock:
        hit = _recent.get(sid)
        return hit[1] if hit and hit[0] == revision else None


def synced(sid: str, revision: int) -> dict | None:
    """The remembered summary of the save at `revision` when the table's rows are known to be exactly it (the
    storage layer wrote them, or checked them, in that commit), else None: write(old=...) may then send only the
    rows that moved; otherwise the full self-healing sync."""
    with _recent_lock:
        hit = _recent.get(sid)
        return hit[1] if hit and hit[0] == revision and hit[2] else None


def remember(sid: str, revision: int, rows: dict, synced: bool = False) -> None:
    """Only after the save at `revision` was committed (its summary is then exact). `synced`: the table's rows
    are these rows too (see synced())."""
    with _recent_lock:
        _recent[sid] = (revision, rows, synced)
        _recent.move_to_end(sid)
        while len(_recent) > RECENT:
            _recent.popitem(last=False)


# ---------------------------------------------------------------- writing
_UPSERT = ("INSERT INTO leaderboard(sid,board,score,k1,k2,level,days,served,stars,mastered,since,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) "
           "ON CONFLICT(sid,board) DO UPDATE SET "
           "since=CASE WHEN leaderboard.score<>excluded.score THEN excluded.since ELSE leaderboard.since END,"
           "score=excluded.score,k1=excluded.k1,k2=excluded.k2,level=excluded.level,days=excluded.days,served=excluded.served,"
           "stars=excluded.stars,mastered=excluded.mastered,updated=excluded.updated "
           "WHERE (leaderboard.score,leaderboard.k1,leaderboard.k2,leaderboard.level,leaderboard.days,leaderboard.served,leaderboard.stars,leaderboard.mastered)"
           " IS DISTINCT FROM (excluded.score,excluded.k1,excluded.k2,excluded.level,excluded.days,excluded.served,excluded.stars,excluded.mastered)")
_NAME = ("INSERT INTO leaderboard_players(sid,name,updated) VALUES(?,?,?) ON CONFLICT(sid) DO UPDATE SET name=excluded.name,updated=excluded.updated "
         "WHERE leaderboard_players.name IS DISTINCT FROM excluded.name")


def write(db, sid: str, rows: dict, now: float | None = None, old: dict | None = None) -> None:
    """Sync every row of one save to `rows` (a summary), inside the caller's
    transaction: upsert its boards (unchanged rows are not rewritten), drop the
    boards it no longer earns, keep its guest name.
    `old`: the summary the rows were synced to before (the storage layer's, of the
    save this command started from). With the same boards, only the rows that
    moved are sent: 💰 wealth moves with most money changes, one statement then
    instead of one per board. A board gained or lost: the full sync above."""
    if not rows:
        return
    now = time.time() if now is None else now
    boards = [b for b in rows if b != NAME]
    if old and old.keys() == rows.keys():
        for b in boards:
            if old[b] != rows[b]:
                db.execute(_UPSERT, (sid, b, *rows[b], now, now))
        if NAME in rows and old[NAME] != rows[NAME]:
            db.execute(_NAME, (sid, rows[NAME], now))
        return
    for b in boards:
        db.execute(_UPSERT, (sid, b, *rows[b], now, now))
    marks = ','.join('?' * len(boards))
    db.execute(f"DELETE FROM leaderboard WHERE sid=? AND board NOT IN ({marks})" if boards else "DELETE FROM leaderboard WHERE sid=?", (sid, *boards))
    if NAME in rows:
        db.execute(_NAME, (sid, rows[NAME], now))


def forget(db, sids) -> None:
    """Remove the rows of deleted saves (inside the caller's transaction)."""
    sids = list(sids)
    for i in range(0, len(sids), 200):
        part = sids[i:i + 200]
        marks = ','.join('?' * len(part))
        db.execute(f"DELETE FROM leaderboard WHERE sid IN ({marks})", part)
        db.execute(f"DELETE FROM leaderboard_players WHERE sid IN ({marks})", part)
        lbt.forget(db, marks, part)
    clear_cache()


# ---------------------------------------------------------------- backfill
def _meta(db, key: str):
    row = db.execute("SELECT v FROM leaderboard_meta WHERE k=?", (key,)).fetchone()
    return row[0] if row else None


def _sync(store, items: list) -> list:
    """Write summaries [(sid, revision, rows)] only where the save is still at that
    revision; returns the sids that moved meanwhile (to be read again)."""
    moved = []

    def step(db):
        now = time.time()
        for sid, revision, rows in items:
            row = db.execute("SELECT revision FROM sessions WHERE sid=?", (sid,)).fetchone()
            if not row:
                continue
            if row[0] != revision:
                moved.append(sid)
                continue
            write(db, sid, rows, now)
    store.transaction(step)
    return moved


def _parse(store, sid: str, text: str):
    try:
        return summary(store.parse_state(text, sid))
    except (ValueError, TypeError, AttributeError, KeyError, RecursionError):
        return None  # unreadable save: left out of the boards


def backfill(store, stop: threading.Event | None = None, batch: int = 40, pause: float = .05, force: bool = False) -> int:
    """Fill the boards from saves stored before them (or rebuild them after a
    VERSION bump). Runs in a background thread: small batches, each save parsed
    outside the write lock, a short transaction per batch and a pause that keeps
    it under about half a core, so it never holds up requests or the start.
    Account saves come first (they are shown by default). Idempotent; marked done
    in leaderboard_meta. Returns the number of saves synced."""
    with store.connect() as db:
        if not force and _meta(db, 'backfill') == str(VERSION):
            return 0
    done = 0
    # Walk the saves in primary-key order so each batch resumes without a table scan.
    order = 'sid'
    for accounts_first in (True, False):
        cond = "sid IN (SELECT sid FROM accounts)" if accounts_first else "sid NOT IN (SELECT sid FROM accounts)"
        last = ''
        while True:
            if stop is not None and stop.is_set():
                return done
            with store.connect() as db:
                rows = db.execute(f"SELECT {order},sid,revision,state FROM sessions WHERE {order}>? AND revision>0 AND {cond} ORDER BY {order} LIMIT ?",
                                  (last, int(batch))).fetchall()
            if not rows:
                break
            last = rows[-1][0]
            items = []
            for r in rows:
                t0 = time.perf_counter()
                s = _parse(store, r[1], r[3])
                if s is not None:
                    items.append((r[1], r[2], s))
                time.sleep(min(.05, max(.001, time.perf_counter() - t0)))  # yield the GIL to request threads
            for _ in range(3):  # saves played meanwhile: read them again
                moved = _sync(store, items) if items else []
                if not moved:
                    break
                items = []
                with store.connect() as db:
                    for sid in moved:
                        row = db.execute("SELECT revision,state FROM sessions WHERE sid=?", (sid,)).fetchone()
                        s = _parse(store, sid, row[1]) if row else None
                        if s is not None:
                            items.append((sid, row[0], s))
            done += len(rows)
            if pause:
                time.sleep(pause)
    store.transaction(lambda db: db.execute("INSERT INTO leaderboard_meta(k,v) VALUES('backfill',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(VERSION),)))
    clear_cache()
    return done


def run_backfill(store, stop: threading.Event | None = None) -> None:
    """Thread target (server maintenance): never raises."""
    import sys
    try:
        n = backfill(store, stop)
        if n:
            sys.stderr.write(f"[leaderboard] backfill: {n} saves\n")
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down
        sys.stderr.write(f"[leaderboard] backfill stopped: {type(e).__name__}\n")


# ---------------------------------------------------------------- reading
# Keep integer flags inside the CASE to match the PostgreSQL column types.
_VISIBLE = ("(CASE WHEN a.uid IS NOT NULL THEN COALESCE(p.show,1) "
            f"WHEN p.name IS NOT NULL THEN COALESCE(p.show,{int(GUEST_DEFAULT)}) ELSE 0 END)=1")
_FROM = "FROM leaderboard l LEFT JOIN accounts a ON a.sid=l.sid LEFT JOIN leaderboard_players p ON p.sid=l.sid"
_ORDER = "ORDER BY l.score DESC, l.k1 DESC, l.k2 DESC, l.since, l.sid"
# Plain ? placeholders (PostgreSQL has no ?NNN): the values go in twice, see _ahead_args.
_AHEAD = ("(l.score>? OR l.score=? AND (l.k1>? OR l.k1=? AND (l.k2>? OR l.k2=? AND "
          "(l.since<? OR l.since=? AND l.sid<?))))")


def _ahead_args(score, k1, k2, since, sid) -> tuple:
    return (score, score, k1, k1, k2, k2, since, since, sid)

_cache: dict = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def parse_query(q: dict) -> tuple[str, int]:
    """(board, limit) of GET /api/leaderboard?career=<id|all>|board=certs|titles|wealth|collection&limit=50;
    ValueError with a player-facing message otherwise."""
    board = q.get('board') or q.get('career') or OVERALL
    if board not in BOARDS and board not in (fh.board(), fh.edition(), 'fair-loss'):   # edition: an older client (rolling release)
        raise ValueError('Nghề không hợp lệ.')
    raw = q.get('limit') or str(LIMIT)
    if not (raw.isascii() and raw.isdigit() and len(raw) <= 3 and 1 <= int(raw) <= LIMIT):
        raise ValueError(f'Số dòng cần từ 1 đến {LIMIT}.')
    return board, int(raw)


def _row_out(board: str, r) -> dict:
    """The public part of a row: display name and numbers only."""
    guest = not r['acct']
    out = dict(name=r['gname'] if guest else r['display'], guest=guest, score=r['score'], level=r['level'])
    if board == CERTS:
        out.update(certs=r['mastered'], best=r['served'], day=r['days'])
    elif board == TITLES:
        out.update(titles=r['mastered'], secret=r['served'], day=r['days'])
    elif board == WEALTH:
        out['xu'] = r['score']
    elif board == COLLECTION:
        out.update(items=r['served'], legendary=r['mastered'])
    elif board.startswith('fair'):
        out.update(xu=r['score'], days=r['days'])
    else:
        out.update(days=r['days'], served=r['served'], stars=r['stars'] / 10 if r['stars'] else None)
        if board == OVERALL:
            out['mastered'] = r['mastered']
    return out


def _top(store, board: str, limit: int) -> tuple[list, int]:
    """(rows with their sid, visible total), cached a few seconds per process."""
    key = (board, limit)
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1], hit[2]
    with store.connect() as db:
        rows = db.execute(f"SELECT l.sid,l.score,l.level,l.days,l.served,l.stars,l.mastered,a.display,p.name AS gname,a.uid IS NOT NULL AS acct "
                          f"{_FROM} WHERE l.board=? AND {_VISIBLE} {_ORDER} LIMIT ?", (board, limit)).fetchall()
        total = db.execute(f"SELECT COUNT(*) {_FROM} WHERE l.board=? AND {_VISIBLE}", (board,)).fetchone()[0]
    top = [(r['sid'], _row_out(board, r)) for r in rows]
    with _cache_lock:
        if len(_cache) > 256:
            _cache.clear()
        _cache[key] = (now, top, total)
    return top, total


def _viewer(store, token: str | None) -> str | None:
    if not isinstance(token, str) or not 16 <= len(token) <= 128:
        return None
    sid, _ = store.resolve(token)
    with store.connect() as db:
        return sid if db.execute("SELECT 1 FROM sessions WHERE sid=?", (sid,)).fetchone() else None


def _privacy(db, sid: str) -> dict:
    row = db.execute("SELECT (SELECT display FROM accounts WHERE sid=?) AS display,(SELECT uid FROM accounts WHERE sid=?) AS uid,"
                     "(SELECT name FROM leaderboard_players WHERE sid=?) AS gname,(SELECT show FROM leaderboard_players WHERE sid=?) AS show",
                     (sid, sid, sid, sid)).fetchone()
    account = row['uid'] is not None
    name = row['display'] if account else row['gname']
    show = row['show']
    visible = bool(name) and bool(show if show is not None else (1 if account else GUEST_DEFAULT))
    return dict(account=account, name=name, can_show=bool(name), show=bool(show) if show is not None else None, visible=visible)


def view(store, board: str, limit: int = LIMIT, token: str | None = None) -> dict:
    """GET /api/leaderboard: the top `limit` of a board plus the viewer's own place
    ("Bạn"), even outside the top or while their name is hidden, and the board's
    weekly titles (game/lb_titles.py: who holds them, last updated, last week's)."""
    if board == 'fair-loss':
        from . import fair_loss
        return fair_loss.view(store, limit, token)
    lbt.ensure(store)
    asked = board
    if board == fh.edition():   # an older client (rolling release) asks for the fair's board by its edition
        board = fh.board()
    top, total = _top(store, board, limit)
    sid = _viewer(store, token)
    holders = lbt.holders(store)
    rows = []
    for i, (row_sid, r) in enumerate(top):
        mine = [h for h in holders.get(row_sid, ()) if h['board'] == board]
        row = dict(r, rank=i + 1, me=row_sid == sid)
        if mine:
            row['title'] = dict(emoji=mine[0]['emoji'], name=mine[0]['name'])
        rows.append(row)
    me = None
    if sid:
        with store.connect() as db:
            me = _privacy(db, sid)
            mine = db.execute(f"SELECT l.sid,l.score,l.k1,l.k2,l.since,l.level,l.days,l.served,l.stars,l.mastered,a.display,p.name AS gname,a.uid IS NOT NULL AS acct "
                              f"{_FROM} WHERE l.board=? AND l.sid=?", (board, sid)).fetchone()
            if mine:
                ahead = db.execute(f"SELECT COUNT(*) {_FROM} WHERE l.board=? AND {_VISIBLE} AND {_AHEAD}",
                                   (board, *_ahead_args(mine['score'], mine['k1'], mine['k2'], mine['since'], sid))).fetchone()[0]
                stats = _row_out(board, mine)
                stats.pop('name', None)
                stats.pop('guest', None)
                me.update(stats, rank=ahead + 1)
            else:
                me['rank'] = None
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    if board == fh.board():   # 🏆 the fair's own titles (after the end), no weekly ones
        from . import fair_board
        fair_board.ensure(store)
        return dict(board=asked, total=total, rows=rows, me=me, weekly=None, fair=fair_board.board_view(store, sid))
    try:
        weekly = lbt.board_view(store, board, sid)
    except Exception:  # noqa: BLE001 - a database from before the weekly titles: the board still shows
        weekly = None
    return dict(board=board, total=total, rows=rows, me=me, weekly=weekly)


# ---------------------------------------------------------------- privacy setting
def set_visible(store, token: str, state: dict, visible) -> dict:
    """POST /api/leaderboard/visibility {visible}: "Hiện tên tôi trên bảng xếp hạng".
    Also syncs this player's rows from the save in hand (fresh after the backfill)."""
    from .engine import GameError
    if type(visible) is not bool:
        raise GameError('Lựa chọn không hợp lệ.', 'bad_request')
    sid, _ = store.resolve(token)
    rows = summary(state)

    def step(db):
        if not db.execute("SELECT 1 FROM sessions WHERE sid=?", (sid,)).fetchone():
            raise GameError('Phiên chơi không còn tồn tại. Tải lại trang nhé.', 'session_missing')
        now = time.time()
        write(db, sid, rows, now)
        db.execute("INSERT INTO leaderboard_players(sid,name,show,updated) VALUES(?,?,?,?) ON CONFLICT(sid) DO UPDATE SET show=excluded.show,updated=excluded.updated",
                   (sid, rows.get(NAME), int(visible), now))
        return _privacy(db, sid)
    me = store.transaction(step)
    clear_cache()
    me.pop('show', None)
    if visible and not me['can_show']:
        message = 'Đặt tên cho nhân vật (khác “Mây”) để tên bạn hiện trên bảng xếp hạng nhé.'
    elif visible:
        message = 'Tên bạn đã hiện trên bảng xếp hạng.'
    else:
        message = 'Đã ẩn tên bạn khỏi bảng xếp hạng.'
    return dict(me, message=message)


def export_rows(store, sid: str) -> list:
    """Every row of one save (tests and support tools)."""
    with store.connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM leaderboard WHERE sid=? ORDER BY board", (sid,))]
