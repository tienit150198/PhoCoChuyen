"""👥 Bạn bè: a friends list between registered players (the way to find someone to marry).

* Find someone by their exact username ("tên đăng nhập"), or by their public code "mã người chơi"
  (PCC-XXXXXX) as a second way. Exact match only: no partial search, no lists to browse. Every
  search counts against 20 a minute and 100 a day (in the database, so restarts and workers share
  it). "Not found", "this player turned search off" and "one of you blocked the other" give the
  same answer, so a search tells nothing about who exists.
* The answer carries the display name and the player's code (a public, per-account random code:
  never an account id, a username or an IP).
* A request needs an answer: Chấp nhận / Từ chối / Chặn. At most 10 requests a day and 20
  waiting at once. Asking someone who already asked you makes you friends at once.
* "Chặn" is the same block as in Hôn nhân (table marriage_blocks): no request, no proposal,
  and an existing friendship ends.
* "Cho phép tìm tôi bằng tên đăng nhập" (default on) only hides the username search; a code you
  shared still works.

Tables (created with game/marriage.SCHEMA): friend_prefs, friend_requests, friends (one row per
direction), friend_searches.
"""
from __future__ import annotations

import re

from . import marriage as mr

SEARCH_PER_MIN, SEARCH_PER_DAY = 20, 100
REQUESTS_PER_DAY, PENDING_MAX = 10, 20
FRIENDS_MAX = 200
NOT_FOUND = 'Không tìm thấy người chơi này. Kiểm tra lại tên đăng nhập (viết đúng từng ký tự) nhé.'
USERNAME = re.compile(r'[a-z0-9_.]{3,24}')
DAY = mr.DAY


def _row(db, sql, args=()):
    return mr._row(db, sql, args)


def _rows(db, sql, args=()):
    return mr._rows(db, sql, args)


def are_friends(db, a: str, b: str) -> bool:
    return bool(db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (a, b)).fetchone())


def findable(db, sid: str) -> bool:
    r = db.execute('SELECT findable FROM friend_prefs WHERE sid=?', (sid,)).fetchone()
    return True if r is None else bool(r['findable'])


def _status_of(db, sid: str) -> str:
    """Marriage status shown on a friend card."""
    r = db.execute('SELECT c.status FROM marriage_bonds b JOIN couples c ON c.id=b.couple WHERE b.sid=?', (sid,)).fetchone()
    return {'engaged': 'engaged', 'married': 'married'}.get(r['status'] if r else '', 'single')


def _career(db, sid: str) -> dict | None:
    """Main workplace and level, read from the leaderboard rows (game/leaderboard.py) when present."""
    try:
        rows = db.execute("SELECT board,level,score FROM leaderboard WHERE sid=? AND board NOT IN ('all','certs') ORDER BY score DESC LIMIT 1",
                          (sid,)).fetchall()
        overall = db.execute("SELECT level FROM leaderboard WHERE sid=? AND board='all'", (sid,)).fetchone()
    except Exception:  # noqa: BLE001 - no leaderboard table in this build
        return None
    if not rows:
        return None
    from .content import CAREER_META
    cid = rows[0]['board']
    meta = CAREER_META.get(cid) or {}
    return dict(career=str(meta.get('short') or cid)[:40], level=int(overall['level'] if overall else rows[0]['level']))


def _card(db, me: str, other: str) -> dict:
    p = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (other,))
    status = _status_of(db, other)
    mine = db.execute('SELECT c.a,c.b FROM marriage_bonds b JOIN couples c ON c.id=b.couple WHERE b.sid=?', (me,)).fetchone()
    spouse = bool(mine and other in (mine['a'], mine['b']))
    from .live_dating import bonded   # 💕 "Đang tìm hiểu": both tapped ❤️ after an in-game date (live/dating.py)
    return dict(name=mr._display(db, other), code=(p or {}).get('code'), status=status, spouse=spouse, career=_career(db, other),
                dating=not spouse and bonded(db, me, other))


def _count_search(db, sid: str) -> None:
    t = mr.now()
    minute = db.execute('SELECT COUNT(*) FROM friend_searches WHERE sid=? AND at>?', (sid, t - 60)).fetchone()[0]
    day = db.execute('SELECT COUNT(*) FROM friend_searches WHERE sid=? AND at>?', (sid, t - DAY)).fetchone()[0]
    mr.need(minute < SEARCH_PER_MIN, 'Bạn tìm hơi nhanh. Chờ một phút rồi tìm tiếp nhé.', 'rate_limited', 429)
    mr.need(day < SEARCH_PER_DAY, f'Hôm nay bạn đã tìm {SEARCH_PER_DAY} lần. Mai tìm tiếp nhé.', 'rate_limited', 429)
    db.execute('INSERT INTO friend_searches(sid,at) VALUES(?,?)', (sid, t))
    if db.execute('SELECT COUNT(*) FROM friend_searches WHERE sid=?', (sid,)).fetchone()[0] > SEARCH_PER_DAY + 20:
        db.execute('DELETE FROM friend_searches WHERE sid=? AND at<?', (sid, t - DAY))


def _target(db, sid: str, d: dict) -> str | None:
    """The account behind an exact username or a code, or None (all misses look the same)."""
    if isinstance(d.get('code'), str) and d['code'].strip():
        p = mr._find(db, mr.clean_code(d['code']))
        other = p['sid'] if p else None
    else:
        name = d.get('username')
        mr.need(isinstance(name, str) and len(name) <= 64, 'Nhập tên đăng nhập của bạn ấy nhé.', 'bad_username')
        name = name.strip().lower().lstrip('@')
        if not USERNAME.fullmatch(name):
            return None
        a = db.execute('SELECT sid FROM accounts WHERE username=?', (name,)).fetchone()
        other = a['sid'] if a and findable(db, a['sid']) else None
    if not other or other == sid or mr._blocked(db, sid, other):
        return None
    return other


def search(store, sid: str, d: dict) -> dict:
    def run(db):
        _count_search(db, sid)
        other = _target(db, sid, d)
        if not other:
            me = db.execute('SELECT username FROM accounts WHERE sid=?', (sid,)).fetchone()
            own = isinstance(d.get('username'), str) and me and d['username'].strip().lower().lstrip('@') == me['username']
            return dict(found=None, why='Đây là tên đăng nhập của chính bạn.' if own else NOT_FOUND)
        mr.ensure_person_db(db, other)
        card = _card(db, sid, other)
        state = ('friend' if are_friends(db, sid, other)
                 else 'sent' if db.execute("SELECT 1 FROM friend_requests WHERE from_sid=? AND to_sid=? AND status='pending'", (sid, other)).fetchone()
                 else 'received' if db.execute("SELECT 1 FROM friend_requests WHERE from_sid=? AND to_sid=? AND status='pending'", (other, sid)).fetchone()
                 else 'none')
        return dict(found=dict(card, state=state), why=None)
    out = store.transaction(run)
    return dict(message='', **out)


def request(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        if not (isinstance(d.get('code'), str) and d['code'].strip()):
            _count_search(db, sid)   # a request by username is a search too: no way around the search limits
        other = _target(db, sid, d)
        if not other:
            return 'missing', None    # outside: the search just counted must stay counted
        mr.need(not are_friends(db, sid, other), 'Hai bạn đã là bạn bè rồi.', 'already', 409)
        back = _row(db, "SELECT id FROM friend_requests WHERE from_sid=? AND to_sid=? AND status='pending'", (other, sid))
        if back:  # they asked first: accept
            _befriend(db, sid, other, back['id'])
            return 'accepted', mr._display(db, other)
        mr.need(not db.execute("SELECT 1 FROM friend_requests WHERE from_sid=? AND to_sid=? AND status='pending'", (sid, other)).fetchone(),
                'Bạn đã gửi lời mời rồi, chờ bạn ấy trả lời nhé.', 'already', 409)
        t = mr.now()
        mr.need(db.execute('SELECT COUNT(*) FROM friend_requests WHERE from_sid=? AND at>?', (sid, t - DAY)).fetchone()[0] < REQUESTS_PER_DAY,
                f'Mỗi ngày gửi được {REQUESTS_PER_DAY} lời mời kết bạn. Mai gửi tiếp nhé.', 'rate_limited', 429)
        mr.need(db.execute("SELECT COUNT(*) FROM friend_requests WHERE from_sid=? AND status='pending'", (sid,)).fetchone()[0] < PENDING_MAX,
                f'Bạn đang có {PENDING_MAX} lời mời chờ trả lời. Đợi bớt rồi gửi thêm nhé.', 'rate_limited', 429)
        mr.need(db.execute('SELECT COUNT(*) FROM friends WHERE sid=?', (sid,)).fetchone()[0] < FRIENDS_MAX, 'Danh sách bạn bè đã đầy.', 'full', 409)
        db.execute("INSERT INTO friend_requests(from_sid,to_sid,status,at) VALUES(?,?,'pending',?)", (sid, other, t))
        mr.ensure_person_db(db, other)
        mr._notice(db, other, f'👋 {display} muốn kết bạn với bạn. Mở mục Bạn bè để trả lời nhé.')
        return 'sent', mr._display(db, other)
    what, name = store.transaction(run)
    mr.need(what != 'missing', NOT_FOUND, 'not_found', 404)
    return dict(message=f'Hai bạn đã là bạn bè: {name} cũng vừa mời bạn!' if what == 'accepted' else f'Đã gửi lời mời kết bạn tới {name}.', changed=False)


def _befriend(db, a: str, b: str, rid: int | None) -> None:
    t = mr.now()
    if rid:
        db.execute("UPDATE friend_requests SET status='accepted',decided=? WHERE id=?", (t, rid))
    db.execute('INSERT OR IGNORE INTO friends(sid,friend,since) VALUES(?,?,?)', (a, b, t))
    db.execute('INSERT OR IGNORE INTO friends(sid,friend,since) VALUES(?,?,?)', (b, a, t))
    db.execute("UPDATE friend_requests SET status='cancelled',decided=? WHERE status='pending' AND ((from_sid=? AND to_sid=?) OR (from_sid=? AND to_sid=?))",
               (t, a, b, b, a))


def respond(store, sid: str, display: str, d: dict) -> dict:
    rid, answer = d.get('id'), d.get('answer')
    mr.need(type(rid) is int and answer in ('accept', 'decline', 'block'), 'Trả lời không hợp lệ.')

    def run(db):
        r = _row(db, "SELECT * FROM friend_requests WHERE id=? AND to_sid=? AND status='pending'", (rid, sid))
        mr.need(r, 'Lời mời này không còn chờ trả lời.', 'gone', 409)
        other = r['from_sid']
        if answer == 'accept':
            mr.need(not mr._blocked(db, sid, other), 'Không kết bạn được với người này.', 'blocked', 409)
            _befriend(db, sid, other, rid)
            mr._notice(db, other, f'🤝 {display} đã nhận lời kết bạn. Giờ hai bạn là bạn bè!')
        elif answer == 'decline':
            db.execute("UPDATE friend_requests SET status='declined',decided=? WHERE id=?", (mr.now(), rid))
        else:
            _block_db(db, sid, other)
        return mr._display(db, other)
    name = store.transaction(run)
    return dict(message={'accept': f'Bạn và {name} đã là bạn bè.', 'decline': 'Đã từ chối lời mời.',
                         'block': 'Đã chặn. Người này không gửi lời mời hay lời cầu hôn cho bạn được nữa.'}[answer], changed=False)


def cancel(store, sid: str, display: str, d: dict) -> dict:
    rid = d.get('id')
    mr.need(type(rid) is int, 'Lời mời không hợp lệ.')
    store.transaction(lambda db: mr.need(db.execute("UPDATE friend_requests SET status='cancelled',decided=? WHERE id=? AND from_sid=? AND status='pending'",
                                                    (mr.now(), rid, sid)).rowcount == 1, 'Lời mời này không còn chờ trả lời.', 'gone', 409))
    return dict(message='Đã rút lại lời mời kết bạn.', changed=False)


def _by_code(db, sid: str, d: dict) -> str:
    p = mr._find(db, mr.clean_code(d.get('code')))
    mr.need(p and p['sid'] != sid, 'Không tìm thấy người này.', 'not_found', 404)
    return p['sid']


def unfriend(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        other = _by_code(db, sid, d)
        c = mr._bond(db, sid)
        mr.need(not (c and other in (c['a'], c['b'])), 'Hai bạn đang là một đôi. Muốn dừng lại thì dùng mục Hôn nhân nhé.', 'spouse', 409)
        db.execute('DELETE FROM friends WHERE (sid=? AND friend=?) OR (sid=? AND friend=?)', (sid, other, other, sid))
        return mr._display(db, other)
    name = store.transaction(run)
    return dict(message=f'Đã hủy kết bạn với {name}.', changed=False)


def _block_db(db, sid: str, other: str) -> None:
    t = mr.now()
    db.execute('INSERT OR IGNORE INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (sid, other, t))
    db.execute('DELETE FROM friends WHERE (sid=? AND friend=?) OR (sid=? AND friend=?)', (sid, other, other, sid))
    db.execute("UPDATE friend_requests SET status='declined',decided=? WHERE status='pending' AND ((from_sid=? AND to_sid=?) OR (from_sid=? AND to_sid=?))",
               (t, sid, other, other, sid))
    for q in _rows(db, "SELECT id,ring FROM proposals WHERE status='pending' AND ((from_sid=? AND to_sid=?) OR (from_sid=? AND to_sid=?))", (sid, other, other, sid)):
        db.execute("UPDATE proposals SET status='cancelled',decided=? WHERE id=?", (t, q['id']))
        db.execute("UPDATE marriage_rings SET status='owned' WHERE id=? AND status='proposed'", (q['ring'],))


def block(store, sid: str, display: str, d: dict) -> dict:
    def run(db):
        other = _by_code(db, sid, d)
        c = mr._bond(db, sid)
        mr.need(not (c and other in (c['a'], c['b'])), 'Hai bạn đang là một đôi. Muốn dừng lại thì dùng mục Hôn nhân nhé.', 'spouse', 409)
        _block_db(db, sid, other)
    store.transaction(run)
    return dict(message='Đã chặn. Người này không gửi lời mời hay lời cầu hôn cho bạn được nữa.', changed=False)


def settings(store, sid: str, display: str, d: dict) -> dict:
    on = d.get('findable')
    mr.need(type(on) is bool, 'Thiết lập không hợp lệ.')
    store.transaction(lambda db: db.execute('INSERT INTO friend_prefs(sid,findable) VALUES(?,?) ON CONFLICT(sid) DO UPDATE SET findable=excluded.findable',
                                            (sid, int(on))))
    return dict(message='Người khác tìm được bạn bằng tên đăng nhập.' if on else 'Đã ẩn: không ai tìm được bạn bằng tên đăng nhập nữa.', changed=False)


def view(db, sid: str) -> dict:
    t = mr.now()
    friends = [dict(_card(db, sid, r['friend']), since=int(r['since']))
               for r in _rows(db, 'SELECT friend,since FROM friends WHERE sid=? ORDER BY since DESC LIMIT ?', (sid, FRIENDS_MAX))]
    friends.sort(key=lambda f: (not f['spouse'], f['name'].lower()))
    incoming = [dict(id=r['id'], name=mr._display(db, r['from_sid']), at=int(r['at']))
                for r in _rows(db, "SELECT * FROM friend_requests WHERE to_sid=? AND status='pending' ORDER BY id DESC LIMIT 30", (sid,))]
    outgoing = [dict(id=r['id'], name=mr._display(db, r['to_sid']), at=int(r['at']))
                for r in _rows(db, "SELECT * FROM friend_requests WHERE from_sid=? AND status='pending' ORDER BY id DESC LIMIT 30", (sid,))]
    left = max(0, SEARCH_PER_DAY - db.execute('SELECT COUNT(*) FROM friend_searches WHERE sid=? AND at>?', (sid, t - DAY)).fetchone()[0])
    return dict(list=friends, incoming=incoming, outgoing=outgoing, findable=findable(db, sid), searches_left=left,
                requests_left=max(0, REQUESTS_PER_DAY - db.execute('SELECT COUNT(*) FROM friend_requests WHERE from_sid=? AND at>?', (sid, t - DAY)).fetchone()[0]))


def forget(db, sid: str) -> None:
    for sql in ('DELETE FROM friends WHERE sid=? OR friend=?', 'DELETE FROM friend_requests WHERE from_sid=? OR to_sid=?'):
        db.execute(sql, (sid, sid))
    db.execute('DELETE FROM friend_prefs WHERE sid=?', (sid,))
    db.execute('DELETE FROM friend_searches WHERE sid=?', (sid,))


ACTIONS = dict(friend_search=lambda store, sid, display, d: search(store, sid, d), friend_request=request, friend_respond=respond,
               friend_cancel=cancel, friend_remove=unfriend, friend_block=block, friend_settings=settings)
