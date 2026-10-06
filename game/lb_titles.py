"""🏅 Danh hiệu tuần của Bảng xếp hạng: the top players of a board hold its weekly titles.

The owner (01/10): "bảng xếp hạng cũng có danh hiệu nhé, mỗi tuần sẽ có danh hiệu cho các top. Được cập nhật mỗi
ngày nhé" — the boards with titles include Chứng chỉ and Danh hiệu (game/leaderboard.py `certs`, `titles`), and
from 05/10 💰 Tài phú (`wealth`, "thêm top tài phú cho toàn server").

Who holds what
* Trải nghiệm (`all`), Danh hiệu (`titles`), Chứng chỉ (`certs`), Tài phú (`wealth`): three tiers each, top 1 /
  top 2–3 / top 4–10,
  with their own names (TIERS, BOARD_TITLES).
* Every workplace board: its top 1 is "🏆 Trùm <nghề>" (CAREER_NOUN).
* Only players the board shows (game/leaderboard.py _VISIBLE: accounts unless hidden, guests who opted in), in
  the board's own order. Nothing is written into a save: holding a weekly title is a server fact (table
  `lb_weekly`), shown on the board, under the name in Phố nghề and on the name tag in Đi dạo.

When
* Once a day (Vietnam time, UTC+7): `refresh()` recomputes the holders from the boards (never while they are
  being rebuilt after a formula change: game/leaderboard.py backfill). It runs from the server's
  housekeeping loop (one process, every 30 s; the first pass after midnight does the work) and lazily from
  GET /api/leaderboard and /api/bootstrap, so a day is never skipped. Which process does it is settled in the
  database (compare-and-set of leaderboard_meta 'weekly'); every other process only reads.
* Monday 00:00 (Vietnam): the first refresh of a new week freezes the week that ended — the standings at that
  moment become that week's final holders (`final`=1, kept, never deleted) — then the new week starts from the
  same standings and moves with them, day by day.

Table `lb_weekly` (PostgreSQL in game/pg_schema.py): one row per (week, board, rank). `final`=0 rows
are the current holders (the latest daily refresh), `final`=1 rows are past weeks. `title` holds the title text so
the live service (live/street.py) can show it without importing the game.
"""
from __future__ import annotations

import threading
import time

from .wedding_live import vn_day, vn_week, week_start, VN   # the Vietnam calendar ("Khách mời của tuần" uses it too)

META = 'weekly'                 # leaderboard_meta key: '<VN day>|<ISO week>' of the last refresh
ALL, TITLES, CERTS, WEALTH = 'all', 'titles', 'certs', 'wealth'
TOP = 10                        # ranks that hold a title on the main boards
TIERS = ((1, 1), (2, 3), (4, 10))   # (first rank, last rank) of each tier
TIER_LABELS = ('Top 1', 'Top 2–3', 'Top 4–10')
BOARD_TITLES = {                # (emoji, name) per tier
    ALL: (('👑', 'Trùm cuối của phố'), ('🔥', 'Chiến thần cày cuốc'), ('⚡', 'Dân cày top 10')),
    TITLES: (('🏅', 'Vua săn danh hiệu'), ('✨', 'Nhà sưu tầm xịn sò'), ('🎖️', 'Hội săn danh hiệu')),
    CERTS: (('🎓', 'Thủ khoa của phố'), ('📜', 'Học bá chính hiệu'), ('🤓', 'Mọt sách có số má')),
    WEALTH: (('💎', 'Đại gia của phố'), ('💰', 'Đại gia mới nổi'), ('🤑', 'Hội nhà giàu')),
}
MAIN = (ALL, TITLES, CERTS, WEALTH)     # the order of honour (a name tag shows the best one: tier first, then this order)
CAREER_EMOJI = '🏆'
CAREER_NOUN = dict(
    milk_tea='trà sữa', grocery='tạp hóa', delivery='giao hàng', cafe_bakery='bánh & cà phê', florist='tiệm hoa',
    mother_baby='mẹ & bé', restaurant='mì cay', pet_care='chăm thú cưng', salon='salon tóc', repair='sửa đồ',
    farm='nông trại', homestay='homestay', clothing='shop quần áo', pet_shop='shop thú cưng', tra_da='trà đá',
    fruit='trái cây', garbage='thu gom rác', drain='thông cống', homemaker='nội trợ', ice_cream='tiệm kem', pho='quán phở', com='quán cơm', nail='tiệm nail', pagoda='việc chùa', photobooth='tiệm ảnh', library='thư viện', giupviec='giúp việc', naucom='bếp nhà khách', babysitter='trông trẻ', customer_care='chăm sóc khách', pharmacy='nhà thuốc',
    tour_guide='dẫn tour', teacher='bục giảng', accounting='sổ sách', pilot='buồng lái', flight_attendant='khoang khách', oil='giàn khoan',
    corp_accounting='kế toán doanh nghiệp', tax_payroll='thuế & lương', group_accounting='kế toán tập đoàn',
    hr_admin='nhân sự', secretary='thư ký', it_helpdesk='IT văn phòng', railway='gác chắn', nurse='khoa Nội', lighthouse='hải đăng')
# A workplace whose top 1 is not a "Trùm": nobody is the boss of a pagoda (game/pagoda_voice.py).
CAREER_TITLE = dict(pagoda=('🪷', 'Siêng việc chùa nhất tuần'))
HOLDERS_SECONDS = 60.0          # how long a process trusts its copy of the current holders



def now() -> float:
    return time.time()


# ---------------------------------------------------------------- the titles
def tier_of(board: str, rank: int) -> int | None:
    """0, 1, 2 for the tiers of a main board; 0 for the top 1 of a workplace board; None for no title."""
    if board in BOARD_TITLES:
        return next((i for i, (lo, hi) in enumerate(TIERS) if lo <= rank <= hi), None)
    return 0 if rank == 1 else None


def career_noun(board: str) -> str:
    from .content import CAREER_META
    noun = CAREER_NOUN.get(board)
    if noun:
        return noun
    short = (CAREER_META.get(board) or {}).get('short') or board
    return short[:1].lower() + short[1:]


def title_of(board: str, rank: int) -> dict | None:
    """{emoji, name, text, tier, label} of the title a rank holds on a board, or None."""
    tier = tier_of(board, rank)
    if tier is None:
        return None
    if board in BOARD_TITLES:
        emoji, name = BOARD_TITLES[board][tier]
        label = TIER_LABELS[tier]
    elif board in CAREER_TITLE:
        (emoji, name), label = CAREER_TITLE[board], 'Top 1'
    else:
        emoji, name, label = CAREER_EMOJI, f'Trùm {career_noun(board)}', 'Top 1'
    return dict(emoji=emoji, name=name, text=f'{emoji} {name}', tier=tier, label=label)


def tiers_of(board: str) -> list:
    """The tiers of a board for the view: [{tier, label, emoji, name, ranks: (lo, hi)}]."""
    if board in BOARD_TITLES:
        return [dict(tier=i, label=TIER_LABELS[i], emoji=e, name=n, lo=TIERS[i][0], hi=TIERS[i][1])
                for i, (e, n) in enumerate(BOARD_TITLES[board])]
    t = title_of(board, 1)
    return [dict(tier=0, label='Top 1', emoji=t['emoji'], name=t['name'], lo=1, hi=1)]


def honour(board: str, rank: int) -> tuple:
    """Sort key: the best title first (tier, then main boards in MAIN order, then workplaces)."""
    tier = tier_of(board, rank)
    return (tier if tier is not None else 9, MAIN.index(board) if board in MAIN else len(MAIN), board)


# ---------------------------------------------------------------- daily refresh
def _boards() -> list:
    from .leaderboard import CAREER_IDS
    return list(MAIN) + sorted(CAREER_IDS)


def standings(db) -> list:
    """[(board, rank, sid, score)] of every title holder right now, from the boards as shown."""
    from . import leaderboard as lb
    out = []
    for board in _boards():
        n = TOP if board in BOARD_TITLES else 1
        rows = db.execute(f"SELECT l.sid,l.score {lb._FROM} WHERE l.board=? AND {lb._VISIBLE} {lb._ORDER} LIMIT ?", (board, n)).fetchall()
        out.extend((board, i + 1, r['sid'], int(r['score'])) for i, r in enumerate(rows))
    return out


def _insert(db, week: str, rows: list, final: int, day: str, t: float) -> None:
    for board, rank, sid, score in rows:
        db.execute('INSERT INTO lb_weekly(week,board,rank,sid,score,title,final,day,at) VALUES(?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(week,board,rank) DO UPDATE SET sid=excluded.sid,score=excluded.score,title=excluded.title,'
                   'final=excluded.final,day=excluded.day,at=excluded.at',
                   (week, board, rank, sid, score, title_of(board, rank)['text'], final, day, t))


_done: dict = {}                # database -> the day this process saw refreshed (no database read until tomorrow)
_pending: dict = {}             # database -> when this process last saw the boards still being rebuilt (backfill)
PENDING_SECONDS = 60.0
_lock = threading.Lock()


def _key(store) -> str:
    return str(getattr(store, 'path', None) or id(store))


def refresh(store, t: float | None = None, best_effort_ms: int | None = None) -> bool:
    """Recompute the holders once per Vietnam day; on the first day of a week, freeze the week that ended first.
    True when this call did it. Cheap when it is already done (a memo in the process, else one read)."""
    t = now() if t is None else t
    day, week, key = vn_day(t), vn_week(t), _key(store)
    if _done.get(key) == day:
        return False
    with _lock:
        if _done.get(key) == day or time.monotonic() - _pending.get(key, -1e9) < PENDING_SECONDS:
            return False
        from .leaderboard import VERSION
        with store.connect() as db:
            row = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META,)).fetchone()
            built = db.execute("SELECT v FROM leaderboard_meta WHERE k='backfill'").fetchone()
        if row and row[0].split('|')[0] == day:
            _done[key] = day
            return False
        if built and built[0] != str(VERSION):   # the boards are being rebuilt (a new formula): wait for them
            _pending[key] = time.monotonic()
            return False
        prev = vn_week(week_start(t) - 3600)

        def step(db):
            cur = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META,)).fetchone()
            last = cur[0] if cur else ''
            if last.split('|')[0] == day:
                return False
            mark = f'{day}|{week}'
            # Compare-and-set: of the processes that saw yesterday's mark, one moves it and does the work.
            claimed = (db.execute('UPDATE leaderboard_meta SET v=? WHERE k=? AND v=?', (mark, META, last)).rowcount if cur else
                       db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (META, mark)).rowcount)
            if claimed != 1:
                return False
            rows = standings(db)
            last_week = last.split('|')[1] if '|' in last else None
            if last_week and last_week != week:
                if last_week == prev:   # the week that just ended: its final holders are the standings at its end
                    db.execute('DELETE FROM lb_weekly WHERE final=0 AND week=?', (last_week,))
                    _insert(db, last_week, rows, 1, day, t)
                else:                   # a week long gone (the server was off): its last daily holders stand
                    db.execute('UPDATE lb_weekly SET final=1 WHERE final=0 AND week=?', (last_week,))
            db.execute('DELETE FROM lb_weekly WHERE final=0')
            _insert(db, week, rows, 0, day, t)
            return True
        did = store.transaction(step, best_effort_ms)
        if did is None:     # busy (best effort): try again on a later request
            return False
        _done[key] = day
        clear_cache()
        return bool(did)


def run_refresh(store) -> None:
    """Housekeeping (server.py _housekeeping): never raises."""
    import sys
    try:
        if refresh(store):
            sys.stderr.write(f'[lb_titles] weekly titles refreshed for {vn_day(now())}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down
        sys.stderr.write(f'[lb_titles] refresh: {type(e).__name__}\n')


def ensure(store, t: float | None = None) -> None:
    """Request path: today's refresh if nobody did it yet (waits at most 250 ms for the write lock). Never raises."""
    try:
        refresh(store, t, best_effort_ms=250)
    except Exception:  # noqa: BLE001 - a page never fails because of the weekly titles
        pass


# ---------------------------------------------------------------- reading
_cache: dict = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def holders(store) -> dict:
    """{sid: [{board, rank, emoji, name, text, tier, label}, …best first]} of the current week (≤ 40 + one per workplace), cached
    HOLDERS_SECONDS per process."""
    t, key = time.monotonic(), _key(store)
    with _cache_lock:
        hit = _cache.get(key)
        if hit and t - hit[0] < HOLDERS_SECONDS:
            return hit[1]
    out: dict = {}
    try:
        with store.connect() as db:
            rows = db.execute('SELECT board,rank,sid FROM lb_weekly WHERE final=0').fetchall()
    except Exception:  # noqa: BLE001 - a database from before this table
        rows = []
    for r in rows:
        ti = title_of(r['board'], int(r['rank']))
        if ti:
            out.setdefault(r['sid'], []).append(dict(ti, board=r['board'], rank=int(r['rank'])))
    for v in out.values():
        v.sort(key=lambda x: honour(x["board"], x["rank"]))
    with _cache_lock:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (t, out)
    return out


def held(store, sid: str | None) -> list:
    """The weekly titles this save holds now, best first (empty for nobody)."""
    return list(holders(store).get(sid, ())) if sid else []


def best(store, sid: str | None) -> dict | None:
    """The one a name tag shows: {emoji, name}."""
    h = held(store, sid)
    return dict(emoji=h[0]['emoji'], name=h[0]['name']) if h else None


def _public(r, viewer: str | None) -> str:
    """The holder's name as the board shows it now (game/leaderboard.py privacy)."""
    from .leaderboard import GUEST_DEFAULT
    account = bool(r['acct'])
    name = r['display'] if account else r['gname']
    show = r['show']
    visible = bool(name) and bool(show if show is not None else (1 if account else GUEST_DEFAULT))
    return name if name and (visible or r['sid'] == viewer) else 'Một người chơi'


def board_view(store, board: str, viewer: str | None = None) -> dict:
    """The "Danh hiệu tuần" block of one board: this week's holders per tier, when it was last updated, and last
    week's final holders."""
    t = now()
    week, prev = vn_week(t), vn_week(week_start(t) - 3600)
    with store.connect() as db:
        rows = db.execute('SELECT w.week,w.rank,w.sid,w.score,w.final,w.at,a.display,p.name AS gname,p.show,a.uid IS NOT NULL AS acct '
                          'FROM lb_weekly w LEFT JOIN accounts a ON a.sid=w.sid LEFT JOIN leaderboard_players p ON p.sid=w.sid '
                          'WHERE w.board=? AND (w.final=0 OR w.week=?) ORDER BY w.rank', (board, prev)).fetchall()

    def tiers(rows):
        out = []
        for tr in tiers_of(board):
            got = [dict(rank=int(r['rank']), name=_public(r, viewer), me=r['sid'] == viewer)
                   for r in rows if tr['lo'] <= int(r['rank']) <= tr['hi']]
            out.append(dict(tr, holders=got))
        return out
    cur = [r for r in rows if not r['final']]
    last = [r for r in rows if r['final'] and r['week'] == prev]
    updated = max((float(r['at']) for r in cur), default=None)
    return dict(week=week, updated=updated, ends=week_start(t) + 7 * 86400, tiers=tiers(cur),
                last=dict(week=prev, tiers=tiers(last)) if last else None)


def fmt_updated(t: float | None) -> str | None:
    """'01/10 · 00:00' (Vietnam time), for logs and tests."""
    import datetime
    return datetime.datetime.fromtimestamp(t, VN).strftime('%d/%m · %H:%M') if t else None


def forget(db, marks: str, part: list) -> None:
    """Deleted saves (game/leaderboard.py forget, inside the caller's transaction): their weekly rows go with them."""
    db.execute(f"DELETE FROM lb_weekly WHERE sid IN ({marks})", part)
    clear_cache()
