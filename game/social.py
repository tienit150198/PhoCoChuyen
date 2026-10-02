"""Multiplayer "Phố nghề": players meet each other asynchronously.

* Profiles are opt-in (a public name + `visible`). Everyone is identified by a
  public id derived from the hashed session; the session token never leaves the
  server and profiles expose no personal data.
* Visits, player reviews (with one owner reply), gifts, a material market with
  escrow, a community board with reactions/comments, a weekly community goal,
  follows, blocks and reports (3 reports hide content automatically).
* Game state only changes through internal `soc_*` actions applied by
  Store.command on the acting player's own session, so money and stock obey the
  same reducer, validation and idempotency receipts as everything else.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import re
import time
import unicodedata

from .careers import PLUGINS
from . import db as dbm


class SocialError(Exception):
    def __init__(self, message: str, code: str = 'social_error', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def fail(message: str, code: str = 'social_error', status: int = 400):
    raise SocialError(message, code, status)


def need(cond, message: str, code: str = 'social_error', status: int = 400):
    if not cond:
        fail(message, code, status)


STICKERS = ('🌸', '☕', '🍜', '🎉', '💪', '🌈', '🍀', '⭐', '🧁', '🎁')
REACTIONS = ('❤️', '😂', '👏', '💡')
BOARD_KINDS = {'tip': 'Mẹo nghề', 'story': 'Chuyện nghề', 'ask': 'Hỏi nhanh', 'trade': 'Cần mua/bán'}
REPORT_REASONS = ('spam', 'rude', 'private', 'scam', 'other')
REPORT_KINDS = ('profile', 'review', 'board', 'comment', 'listing')
HIDE_AFTER = 3
WEEK_GOAL = 1500
GIFT_COINS = (0, 10, 20)
LISTING_DAYS = 3
BANNED = ('địt', 'đjt', 'đụ', 'lồn', 'cặc', 'buồi', 'đéo', 'vcl', 'vkl', 'đĩ', 'fuck', 'shit', 'bitch', 'cunt', 'dick', 'đm', 'dmm', 'clgt', 'óc chó', 'ngu như')

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  pid TEXT PRIMARY KEY, sid TEXT UNIQUE NOT NULL, name TEXT, name_key TEXT UNIQUE, bio TEXT NOT NULL DEFAULT '',
  avatar TEXT NOT NULL DEFAULT '🌸', visible INTEGER NOT NULL DEFAULT 0, shop TEXT NOT NULL DEFAULT '{}',
  served INTEGER NOT NULL DEFAULT 0, week_key TEXT NOT NULL DEFAULT '', week_base INTEGER NOT NULL DEFAULT 0,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL, updated REAL NOT NULL, seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (from_pid TEXT, to_pid TEXT, day TEXT, at REAL, PRIMARY KEY(from_pid,to_pid,day));
CREATE TABLE IF NOT EXISTS previews (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_pid TEXT NOT NULL, to_pid TEXT NOT NULL, career TEXT NOT NULL, day TEXT NOT NULL,
  stars INTEGER NOT NULL, text TEXT NOT NULL, reply TEXT, reply_at REAL, at REAL NOT NULL, reports INTEGER NOT NULL DEFAULT 0,
  hidden INTEGER NOT NULL DEFAULT 0, UNIQUE(from_pid,to_pid,day)
);
CREATE TABLE IF NOT EXISTS gifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_pid TEXT NOT NULL, to_pid TEXT NOT NULL, sticker TEXT NOT NULL, coins INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '', day TEXT NOT NULL, at REAL NOT NULL, claimed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS market (
  id INTEGER PRIMARY KEY AUTOINCREMENT, seller TEXT NOT NULL, career TEXT NOT NULL, item TEXT NOT NULL, qty INTEGER NOT NULL,
  price INTEGER NOT NULL, life_left INTEGER NOT NULL, unit_cost INTEGER NOT NULL, listed_day INTEGER NOT NULL,
  status TEXT NOT NULL, buyer TEXT, at REAL NOT NULL, sold_at REAL, settled INTEGER NOT NULL DEFAULT 0,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS board (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT NOT NULL, career TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
  at REAL NOT NULL, reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, post INTEGER NOT NULL, pid TEXT NOT NULL, text TEXT NOT NULL, at REAL NOT NULL,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reactions (post INTEGER NOT NULL, pid TEXT NOT NULL, emoji TEXT NOT NULL, PRIMARY KEY(post,pid,emoji));
CREATE TABLE IF NOT EXISTS follows (pid TEXT NOT NULL, target TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(pid,target));
CREATE TABLE IF NOT EXISTS blocks (pid TEXT NOT NULL, target TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(pid,target));
CREATE TABLE IF NOT EXISTS reports (reporter TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL, reason TEXT NOT NULL, at REAL NOT NULL,
  PRIMARY KEY(reporter,kind,target));
CREATE TABLE IF NOT EXISTS inbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL, ref TEXT, at REAL NOT NULL,
  read INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS inbox_pid ON inbox(pid, id);
CREATE INDEX IF NOT EXISTS board_career ON board(career, id);
CREATE INDEX IF NOT EXISTS market_status ON market(status, career);
CREATE INDEX IF NOT EXISTS preview_to ON previews(to_pid, id);
CREATE INDEX IF NOT EXISTS gifts_to ON gifts(to_pid, claimed);
"""


def ensure(store) -> None:
    if getattr(store, 'pg', None):
        return  # PostgreSQL: created with every other table (game/pg_schema.py)
    with store.connect() as db:
        db.executescript(SCHEMA)


# ---------------------------------------------------------------- helpers
def now() -> float:
    return time.time()


def today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')


def week() -> str:
    y, w, _ = datetime.datetime.now(datetime.timezone.utc).isocalendar()
    return f'{y}-W{w:02d}'


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def _fold(text: str) -> str:
    text = unicodedata.normalize('NFC', text.lower())
    return re.sub(r'\s+', ' ', text)


def clean(text, limit: int, minimum: int = 0, field: str = 'Nội dung') -> str:
    need(isinstance(text, str), f'{field} không hợp lệ.')
    text = unicodedata.normalize('NFC', text)
    text = ''.join(ch for ch in text if ch in '\n' or unicodedata.category(ch)[0] != 'C')
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    need(minimum <= len(text) <= limit, f'{field} cần từ {minimum} đến {limit} ký tự.')
    folded = _fold(text)
    # Protect players (many are young): no links, e-mails or phone numbers in public text.
    need(not re.search(r'https?://|www\.|\b[\w.-]+\.(com|net|vn|org|io|me|xyz|link)\b', folded), 'Không đăng đường link trong Phố nghề nhé.', 'blocked_link')
    need(not re.search(r'[\w.+-]+@[\w-]+\.', folded), 'Không đăng e-mail công khai nhé.', 'blocked_contact')
    need(not re.search(r'(\d[\s.-]?){9,}', folded), 'Không đăng số điện thoại hay số tài khoản công khai nhé.', 'blocked_contact')
    for word in BANNED:
        pattern = r'(?<!\w)' + re.escape(word) + r'(?!\w)'
        text = re.sub(pattern, '•••', text, flags=re.I)
    return text


def ival(value, low: int, high: int, field: str = 'Số') -> int:
    need(type(value) is int and low <= value <= high, f'{field} không hợp lệ.')
    return value


def _rows(db, sql: str, args=()) -> list[dict]:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def _profile(db, pid: str) -> dict | None:
    r = db.execute('SELECT * FROM profiles WHERE pid=?', (pid,)).fetchone()
    return dict(r) if r else None


def _public_profile(p: dict, me: str | None = None, db=None, ranks: dict | None = None) -> dict:
    shop = json.loads(p['shop'] or '{}')
    out = dict(pid=p['pid'], name=p['name'], bio=p['bio'], avatar=p['avatar'], shop=shop, served=p['served'],
               me=p['pid'] == me, seen=int(p['seen']))
    held = (ranks or {}).get(p.get('sid'))
    if held:   # 🏅 the best weekly leaderboard title this player holds now (game/lb_titles.py)
        out['rank'] = dict(emoji=held[0]['emoji'], name=held[0]['name'])
    if db is not None and me:
        out['following'] = bool(db.execute('SELECT 1 FROM follows WHERE pid=? AND target=?', (me, p['pid'])).fetchone())
        out['blocked'] = bool(db.execute('SELECT 1 FROM blocks WHERE pid=? AND target=?', (me, p['pid'])).fetchone())
    return out


def _blocked(db, a: str, b: str) -> bool:
    return bool(db.execute('SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?)', (a, b, b, a)).fetchone())


def _name_of(db, pid: str) -> str:
    r = db.execute('SELECT name FROM profiles WHERE pid=?', (pid,)).fetchone()
    return (r['name'] if r and r['name'] else 'Một người chơi')


def notify(store, db, pid: str, kind: str, text: str, ref: str | None = None) -> None:
    db.execute('INSERT INTO inbox(pid,kind,text,ref,at) VALUES(?,?,?,?,?)', (pid, kind, text[:300], ref, now()))
    r = db.execute('SELECT sid FROM profiles WHERE pid=?', (pid,)).fetchone()
    if r:
        from . import push
        push.queue(db, r['sid'], kind, text[:160], '/?social=inbox')


def snapshot(state: dict) -> dict:
    """Public, non-personal summary of a player's shops."""
    from .content import CAREER_META
    careers = []
    served = 0
    for cid, c in state['careers'].items():
        served += int(c.get('metrics', {}).get('served', 0))
        if not c.get('started'):
            continue
        stars = [p['stars'] for p in c.get('feed', []) if p.get('stars')][-30:]
        m = CAREER_META.get(cid, {})
        careers.append(dict(id=cid, place=m.get('place', cid), short=m.get('short', cid), level=1 + c.get('xp', 0) // 90, day=c.get('day', 1),
                            rating=round(sum(stars) / len(stars), 1) if stars else None, reviews=len(stars),
                            served=int(c.get('metrics', {}).get('served', 0))))
    careers.sort(key=lambda x: (-x['served'], x['id']))
    from .journey import TITLE_INDEX, worn_view
    j = state.get('journey') or {}
    eq = TITLE_INDEX.get(j.get('equipped'))
    title = dict(emoji=eq['emoji'], name=eq['name']) if eq else None
    worn = [dict(emoji=w['emoji'], name=w['name']) for w in worn_view(j)] if isinstance(j, dict) else []
    out = dict(current=state.get('current'), careers=careers[:14], title=title, titles=worn)
    from .garage import ride_view
    ride = ride_view(state) if isinstance(j, dict) else None
    if ride:   # 🚗 the vehicle the player rides (game/garage.py), shown on the player's card
        out['ride'] = dict(emoji=ride['emoji'], name=ride['name'], color=ride['color'])
    return out, served


SEEN_EVERY = 120   # seconds between "last seen" refreshes of a profile
SHOP_EVERY = 180   # seconds between shop snapshot refreshes (directory + weekly goal)
QUICK_MS = 250     # a busy database skips these refreshes instead of queueing for the lock


def touch(store, sid: str, state: dict | None, must: bool = False) -> dict:
    """My profile row, created/refreshed in its own short transaction (committed
    before the caller's reads, so reads never run under the write lock).
    Refreshing `seen` and the shop snapshot is best-effort and throttled: when the
    database is busy it is skipped, never a failed request. Creating the row waits
    normally only when `must` (write routes need the row to exist)."""
    pid = pid_of(sid)
    with store.connect() as db:
        p = _profile(db, pid)
    t = now()
    shop = state is not None and (not p or t - p['updated'] > SHOP_EVERY)
    if p and not shop and t - p['seen'] <= SEEN_EVERY:
        return p
    snap = snapshot(state) if shop else None  # CPU work stays outside the lock

    def write(db):
        cur = _profile(db, pid)
        if not cur:
            db.execute('INSERT OR IGNORE INTO profiles(pid,sid,created,updated,seen,week_key) VALUES(?,?,?,?,?,?)', (pid, sid, t, 0, t, week()))
            cur = _profile(db, pid)
        if snap:
            wk = week()
            base = cur['week_base'] if cur['week_key'] == wk else cur['served']
            db.execute('UPDATE profiles SET shop=?,served=?,week_key=?,week_base=?,updated=?,seen=? WHERE pid=?',
                       (json.dumps(snap[0], ensure_ascii=False), snap[1], wk, min(base, snap[1]), t, t, pid))
        else:
            db.execute('UPDATE profiles SET seen=? WHERE pid=?', (t, pid))
        return _profile(db, pid)
    out = store.transaction(write, None if (must and not p) else QUICK_MS)
    if out:
        return out
    if p:
        return p
    # Busy and no row yet: an anonymous stand-in; the row is created on a later visit.
    return dict(pid=pid, sid=sid, name=None, name_key=None, bio='', avatar='🌸', visible=0, shop='{}', served=0, week_key='',
                week_base=0, reports=0, hidden=0, created=t, updated=0, seen=t)


def _touch(db, sid: str, state: dict | None) -> dict:
    """Create/refresh my profile row (hidden until I choose a name), inside the
    caller's transaction (accounts._adopt_name). Requests use touch()."""
    pid = pid_of(sid)
    p = _profile(db, pid)
    t = now()
    if not p:
        db.execute('INSERT OR IGNORE INTO profiles(pid,sid,created,updated,seen,week_key) VALUES(?,?,?,?,?,?)', (pid, sid, t, 0, t, week()))
        p = _profile(db, pid)
    if state is not None and t - p['updated'] > 120:
        shop, served = snapshot(state)
        wk = week()
        base = p['week_base'] if p['week_key'] == wk else p['served']
        db.execute('UPDATE profiles SET shop=?,served=?,week_key=?,week_base=?,updated=?,seen=? WHERE pid=?',
                   (json.dumps(shop, ensure_ascii=False), served, wk, min(base, served), t, t, pid))
        p = _profile(db, pid)
    elif t - p['seen'] > 60:
        db.execute('UPDATE profiles SET seen=? WHERE pid=?', (t, pid))
    return p


def _require_named(p: dict) -> None:
    need(p.get('name'), 'Đặt tên hiển thị trong Phố nghề trước nhé.', 'profile_required')


def _target(db, pid) -> dict:
    need(isinstance(pid, str) and re.fullmatch(r'[0-9a-f]{16}', pid or ''), 'Người chơi không hợp lệ.')
    t = _profile(db, pid)
    need(t and t['name'] and t['visible'] and not t['hidden'], 'Không tìm thấy quán này.', 'not_found', 404)
    return t


def _count(db, sql: str, args) -> int:
    return db.execute(sql, args).fetchone()[0]


# ---------------------------------------------------------------- game-state side (internal actions)
def apply_internal(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    """Reducer part of social features. Only reachable with internal=True."""
    from . import engine as e
    from . import inventory as inv
    who = e.clean_text(p.get('who') or 'người chơi', 40)
    if name == 'soc_gift_in':
        coins = e.integer(p.get('coins'), 0, 100)
        if coins:
            e.money(s, c, coins, f'Quà từ {who} (Phố nghề)', category='gift')
        e.log(s, c, 'social', f'{who} gửi tặng bạn {p.get("sticker", "🎁")}' + (f' kèm {coins} xu' if coins else ''))
        return dict(message=f'Nhận quà từ {who}.')
    if name == 'soc_gift_out':
        coins = e.integer(p.get('coins'), 0, 100)
        if coins:
            e.money(s, c, -coins, f'Tặng quà cho {who} (Phố nghề)', category='gift')
        return dict(message='Đã gửi quà.')
    if name == 'soc_list':
        item = p.get('item')
        inv.item(career, item)
        qty = e.integer(p.get('qty'), 1, 50)
        e.need(inv.count(c, item) >= qty, 'Kho không đủ số lượng để đăng bán.')
        lots = sorted((l for l in c['ext']['inv']['lots'] if l['item'] == item and l['expires'] >= c['day'] and l['qty'] > 0),
                      key=lambda l: (l['expires'], l['received']))
        left, soonest = qty, 999
        for lot in lots:
            soonest = min(soonest, lot['expires'] - c['day'] + 1)
            left -= min(left, lot['qty'])
            if not left:
                break
        cost = inv.take(c, item, qty)
        e.log(s, c, 'social', f'Đăng bán {qty} {inv.item(career, item)["name"]} ở chợ Phố nghề.')
        return dict(message='Đã đưa hàng lên chợ.', life_left=max(1, soonest), unit_cost=cost // qty, day=c['day'])
    if name == 'soc_unlist':
        item = p.get('item')
        inv.item(career, item)
        qty = e.integer(p.get('qty'), 1, 50)
        life_left = e.integer(p.get('life_left'), 1, 999) - max(0, c['day'] - e.integer(p.get('listed_day'), 1, 10 ** 9))
        if life_left >= 1:
            name = inv.item(career, item)['name']
            fit = min(qty, max(0, inv.capacity(career) - inv.count(c, item)))
            if fit:
                inv.add_lot(c, item, fit, min(10000, e.integer(p.get('unit_cost'), 0, 100000)), life_left, 'market-return')
            if fit < qty:
                # The shelf filled up meanwhile: what doesn't fit goes to the neighbours, never lost silently.
                e.log(s, c, 'social', f'Kệ đã đầy nên {qty - fit} {name} được tặng lại cho hàng xóm.')
                return dict(message=f'{fit} {name} quay về kho, {qty - fit} phần kệ không còn chỗ nên đã tặng hàng xóm.')
            return dict(message=f'{qty} {name} quay về kho.')
        e.log(s, c, 'social', f'{qty} {inv.item(career, item)["name"]} hết hạn khi còn trên chợ.')
        return dict(message='Hàng đã hết hạn trên chợ.')
    if name == 'soc_buy':
        item = p.get('item')
        spec = inv.item(career, item)
        qty = e.integer(p.get('qty'), 1, 50)
        total = e.integer(p.get('total'), 0, 10 ** 6)
        e.need(inv.count(c, item) + inv._in_transit(c['ext']['inv'], item) + qty <= inv.capacity(career),
               f'Kệ chỉ chứa {inv.capacity(career)} phần mỗi loại (tính cả hàng đang giao).')
        e.money(s, c, -total, f'Mua ở chợ Phố nghề: {qty} {spec["name"]} của {who}', category='stock')
        inv.add_lot(c, item, qty, min(10000, total // qty), e.integer(p.get('life_left'), 1, 999), 'market')
        return dict(message=f'Đã mua {qty} {spec["name"]}. Hàng đã vào kho.')
    if name == 'soc_payout':
        amount = e.integer(p.get('amount'), 0, 10 ** 6)
        e.money(s, c, amount, f'Bán ở chợ Phố nghề cho {who}', category='revenue')
        return dict(message=f'+{amount} xu từ chợ Phố nghề.')
    raise e.GameError('Thao tác Phố nghề không hợp lệ.')


def _cmd(store, token: str, rid: str, career: str, action: str, payload: dict) -> dict:
    from .engine import GameError
    try:
        return store.command(token, rid[:100], None, career, action, payload, internal=True)['result']
    except GameError as e:
        fail(e.message, e.code)


# ---------------------------------------------------------------- settle deliveries to me
def settle(store, token: str, state: dict) -> list[str]:
    """Deliver gifts and market payouts; return expired listings. Idempotent."""
    sid = store.key(token)
    pid = pid_of(sid)
    notes = []
    with store.connect() as db:
        if not _profile(db, pid):
            return notes
        gifts = _rows(db, 'SELECT * FROM gifts WHERE to_pid=? AND claimed=0 LIMIT 20', (pid,))
        payouts = _rows(db, "SELECT * FROM market WHERE seller=? AND status='sold' AND settled=0 LIMIT 20", (pid,))
        expired = _rows(db, "SELECT * FROM market WHERE seller=? AND status='active' AND at<? LIMIT 20", (pid, now() - LISTING_DAYS * 86400))
        names = {r['from_pid']: _name_of(db, r['from_pid']) for r in gifts}
        names.update({r['buyer']: _name_of(db, r['buyer']) for r in payouts})
    career = state.get('current')
    for g in gifts:
        if not career or career not in state['careers']:
            break
        r = _cmd(store, token, f'soc-gift-{g["id"]}', career, 'soc_gift_in', dict(coins=g['coins'], sticker=g['sticker'], who=names[g['from_pid']]))
        with store.connect() as db:
            db.execute('UPDATE gifts SET claimed=1 WHERE id=?', (g['id'],))
        notes.append(r.get('message', ''))
    for m in payouts:
        r = _cmd(store, token, f'soc-pay-{m["id"]}', m['career'], 'soc_payout', dict(amount=m['price'] * m['qty'], who=names[m['buyer']]))
        with store.connect() as db:
            db.execute('UPDATE market SET settled=1 WHERE id=?', (m['id'],))
        notes.append(r.get('message', ''))
    for m in expired:
        with store.connect() as db:
            if db.execute("UPDATE market SET status='expired' WHERE id=? AND status='active'", (m['id'],)).rowcount != 1:
                continue
        _cmd(store, token, f'soc-back-{m["id"]}', m['career'], 'soc_unlist',
             dict(item=m['item'], qty=m['qty'], life_left=m['life_left'], listed_day=m['listed_day'], unit_cost=m['unit_cost']))
        with store.connect() as db:
            db.execute('UPDATE market SET settled=1 WHERE id=?', (m['id'],))
    return [n for n in notes if n]


# ---------------------------------------------------------------- read API
def community(db) -> dict:
    wk = week()
    progress = _count(db, 'SELECT COALESCE(SUM(CASE WHEN served>week_base THEN served-week_base ELSE 0 END),0) FROM profiles WHERE week_key=?', (wk,))
    players = _count(db, 'SELECT COUNT(*) FROM profiles WHERE week_key=? AND served>week_base', (wk,))
    return dict(week=wk, goal=WEEK_GOAL, progress=int(progress), players=players,
                done=progress >= WEEK_GOAL, label='Cả phố cùng phục vụ khách trong tuần')


def bootstrap(store, token: str, state: dict) -> dict:
    sid = store.key(token)
    with store.connect() as db:
        p = _profile(db, pid_of(sid))
        unread = _count(db, 'SELECT COUNT(*) FROM inbox WHERE pid=? AND read=0', (p['pid'],)) if p else 0
        return dict(me=_public_profile(p) | dict(visible=bool(p['visible'])) if p and p['name'] else None, unread=unread,
                    community=community(db), stickers=STICKERS, reactions=REACTIONS, board_kinds=BOARD_KINDS, report_reasons=REPORT_REASONS)


def get(store, token: str, state: dict, route: str, q: dict) -> dict:
    sid = store.key(token)
    if route in ('inbox', 'market'):
        notes = settle(store, token, state)
    else:
        notes = []
    me = touch(store, sid, state)
    mine = me['pid']
    from . import lb_titles
    ranks = lb_titles.holders(store) if route in ('directory', 'shop', 'community') else None
    with store.connect() as db:
        if route == 'me':
            unread = _count(db, 'SELECT COUNT(*) FROM inbox WHERE pid=? AND read=0', (mine,))
            return dict(me=_public_profile(me) | dict(visible=bool(me['visible'])) if me['name'] else None, unread=unread, community=community(db))
        if route == 'directory':
            career = q.get('career') or ''
            query = _fold(q.get('q', ''))[:30]
            rows = _rows(db, '''SELECT * FROM profiles WHERE visible=1 AND hidden=0 AND name IS NOT NULL AND seen>?
                                AND pid NOT IN (SELECT target FROM blocks WHERE pid=?) ORDER BY seen DESC, pid LIMIT 200''',
                         (now() - 60 * 86400, mine))
            if q.get('filter') == 'following':
                follow = {r['target'] for r in _rows(db, 'SELECT target FROM follows WHERE pid=?', (mine,))}
                rows = [r for r in rows if r['pid'] in follow]
            out = []
            for r in rows:
                pp = _public_profile(r, mine, ranks=ranks)
                if career and not any(x['id'] == career for x in pp['shop'].get('careers', [])):
                    continue
                if query and query not in _fold(r['name'] or ''):
                    continue
                out.append(pp)
            return dict(players=out[:60], community=community(db))
        if route == 'shop':
            t = _target(db, q.get('pid'))
            need(not _blocked(db, mine, t['pid']), 'Không thể xem quán này.', 'blocked', 403)
            if t['pid'] != mine and me['name']:
                fresh = db.execute('INSERT OR IGNORE INTO visits(from_pid,to_pid,day,at) VALUES(?,?,?,?)', (mine, t['pid'], today(), now())).rowcount
                if fresh:
                    notify(store, db, t['pid'], 'visit', f'{me["name"]} vừa ghé thăm quán của bạn 👀', mine)
                db.commit()  # the reads below must not run under the write lock
            reviews = _rows(db, '''SELECT r.*, p.name AS author, p.avatar AS avatar FROM previews r JOIN profiles p ON p.pid=r.from_pid
                                   WHERE r.to_pid=? AND r.hidden=0 ORDER BY r.id DESC LIMIT 30''', (t['pid'],))
            listings = _rows(db, "SELECT * FROM market WHERE seller=? AND status='active' AND hidden=0 ORDER BY id DESC LIMIT 10", (t['pid'],))
            visits = _count(db, 'SELECT COUNT(*) FROM visits WHERE to_pid=?', (t['pid'],))
            stars = [r['stars'] for r in reviews]
            reviewed = bool(db.execute('SELECT 1 FROM previews WHERE from_pid=? AND to_pid=? AND day=?', (mine, t['pid'], today())).fetchone())
            return dict(profile=_public_profile(t, mine, db, ranks), visits=visits, rating=round(sum(stars) / len(stars), 1) if stars else None,
                        reviews=[_review(r, mine) for r in reviews], listings=[_listing(db, m, mine) for m in listings],
                        can_review=t['pid'] != mine and bool(me['name']) and not reviewed,
                        can_gift=t['pid'] != mine and bool(me['name']))
        if route == 'board':
            career = q.get('career') or 'all'
            args = [mine]
            sql = '''SELECT b.*, p.name AS author, p.avatar AS avatar FROM board b JOIN profiles p ON p.pid=b.pid
                     WHERE b.hidden=0 AND b.pid NOT IN (SELECT target FROM blocks WHERE pid=?)'''
            if career != 'all':
                sql += " AND b.career IN (?, 'all')"
                args.append(career)
            if q.get('kind') in BOARD_KINDS:
                sql += ' AND b.kind=?'
                args.append(q['kind'])
            sql += ' ORDER BY b.id DESC LIMIT 40'
            posts = _rows(db, sql, args)
            return dict(posts=[_board(db, b, mine) for b in posts])
        if route == 'market':
            args = [mine]
            sql = """SELECT * FROM market WHERE status='active' AND hidden=0 AND seller NOT IN (SELECT target FROM blocks WHERE pid=?)"""
            if q.get('career') in PLUGINS:
                sql += ' AND career=?'
                args.append(q['career'])
            sql += ' ORDER BY id DESC LIMIT 60'
            rows = _rows(db, sql, args)
            mine_rows = _rows(db, "SELECT * FROM market WHERE seller=? AND status IN ('active','sold') ORDER BY id DESC LIMIT 20", (mine,))
            return dict(listings=[_listing(db, m, mine) for m in rows], mine=[_listing(db, m, mine) for m in mine_rows], notes=notes,
                        rules=dict(days=LISTING_DAYS, max_active=5, price_band=[0.5, 3.0]))
        if route == 'inbox':
            rows = _rows(db, 'SELECT * FROM inbox WHERE pid=? ORDER BY id DESC LIMIT 60', (mine,))
            gifts = _rows(db, '''SELECT g.*, p.name AS author, p.avatar AS avatar FROM gifts g JOIN profiles p ON p.pid=g.from_pid
                                 WHERE g.to_pid=? ORDER BY g.id DESC LIMIT 20''', (mine,))
            return dict(items=rows, unread=sum(1 for r in rows if not r['read']), notes=notes,
                        gifts=[dict(id=g['id'], author=g['author'], avatar=g['avatar'], sticker=g['sticker'], coins=g['coins'], note=g['note'], at=int(g['at'])) for g in gifts])
        if route == 'community':
            top = _rows(db, '''SELECT * FROM profiles WHERE visible=1 AND hidden=0 AND name IS NOT NULL AND week_key=? AND served>week_base
                               ORDER BY served-week_base DESC, seen DESC, pid LIMIT 10''', (week(),))
            return dict(community=community(db), top=[dict(_public_profile(p, mine, ranks=ranks), week=p['served'] - p['week_base']) for p in top])
    fail('Không có mục này.', 'not_found', 404)


def _review(r: dict, me: str) -> dict:
    return dict(id=r['id'], author=r['author'], avatar=r['avatar'], from_pid=r['from_pid'], career=r['career'], stars=r['stars'],
                text=r['text'], reply=r['reply'], at=int(r['at']), mine=r['from_pid'] == me, owner=r['to_pid'] == me)


def _listing(db, m: dict, me: str) -> dict:
    spec = next((x for x in (PLUGINS[m['career']].SPEC.get('inventory') or {}).get('items', []) if x['id'] == m['item']), {}) if m['career'] in PLUGINS else {}
    return dict(id=m['id'], career=m['career'], item=m['item'], name=spec.get('name', m['item']), emoji=spec.get('emoji', '📦'),
                qty=m['qty'], price=m['price'], total=m['price'] * m['qty'], life_left=m['life_left'], status=m['status'],
                seller=_name_of(db, m['seller']), seller_pid=m['seller'], mine=m['seller'] == me, at=int(m['at']))


def _board(db, b: dict, me: str) -> dict:
    reacts = _rows(db, 'SELECT emoji, COUNT(*) AS n, SUM(CASE WHEN pid=? THEN 1 ELSE 0 END) AS mine FROM reactions WHERE post=? GROUP BY emoji', (me, b['id']))
    comments = _rows(db, '''SELECT c.*, p.name AS author, p.avatar AS avatar FROM comments c JOIN profiles p ON p.pid=c.pid
                            WHERE c.post=? AND c.hidden=0 ORDER BY c.id LIMIT 30''', (b['id'],))
    return dict(id=b['id'], author=b['author'], avatar=b['avatar'], pid=b['pid'], career=b['career'], kind=b['kind'], text=b['text'],
                at=int(b['at']), mine=b['pid'] == me, reactions={r['emoji']: dict(n=r['n'], mine=bool(r['mine'])) for r in reacts},
                comments=[dict(id=c['id'], author=c['author'], avatar=c['avatar'], text=c['text'], at=int(c['at']), mine=c['pid'] == me) for c in comments])


# ---------------------------------------------------------------- write API
def post(store, token: str, state: dict, route: str, d: dict) -> dict:
    sid = store.key(token)
    me = touch(store, sid, state, must=True)
    mine = me['pid']
    if route == 'profile':
        name = clean(d.get('name'), 24, 2, 'Tên hiển thị')
        need(re.fullmatch(r"[\w .'\-]+", name) and not name.isdigit(), 'Tên chỉ gồm chữ, số và khoảng trắng.')
        need('•' not in name, 'Chọn một cái tên thân thiện hơn nhé.')
        bio = clean(d.get('bio', ''), 140, 0, 'Giới thiệu')
        avatar = d.get('avatar', '🌸')
        need(avatar in STICKERS + ('🧑‍🍳', '👩‍🏫', '🧑‍💼', '🧑‍🌾', '🐱', '🐶'), 'Ảnh đại diện không hợp lệ.')
        visible = d.get('visible', True)
        need(type(visible) is bool, 'Chế độ hiển thị không hợp lệ.')
        with store.connect() as db:
            other = db.execute('SELECT pid FROM profiles WHERE name_key=? AND pid<>?', (_fold(name), mine)).fetchone()
            need(not other, 'Tên này đã có người dùng. Thử thêm một chữ khác nhé.', 'name_taken')
            shop, served = snapshot(state)
            db.execute('UPDATE profiles SET name=?,name_key=?,bio=?,avatar=?,visible=?,shop=?,served=?,updated=? WHERE pid=?',
                       (name, _fold(name), bio, avatar, int(visible), json.dumps(shop, ensure_ascii=False), served, now(), mine))
            return dict(message='Đã lưu hồ sơ Phố nghề.', me=_public_profile(_profile(db, mine)) | dict(visible=visible))
    _require_named(me)
    need(not me['hidden'], 'Hồ sơ của bạn đang bị tạm ẩn do bị báo cáo nhiều lần.', 'profile_hidden', 403)
    if route == 'review':
        stars = ival(d.get('stars'), 1, 5, 'Số sao')
        text = clean(d.get('text', ''), 280, 4, 'Nhận xét')
        with store.connect() as db:
            t = _target(db, d.get('pid'))
            need(t['pid'] != mine, 'Không tự đánh giá quán mình được.')
            need(not _blocked(db, mine, t['pid']), 'Không thể đánh giá quán này.', 'blocked', 403)
            need(db.execute('SELECT 1 FROM visits WHERE from_pid=? AND to_pid=? AND at>?', (mine, t['pid'], now() - 86400)).fetchone(),
                 'Ghé thăm quán trước khi đánh giá nhé.')
            career = (json.loads(t['shop']).get('current') or 'restaurant')
            try:
                db.execute('INSERT INTO previews(from_pid,to_pid,career,day,stars,text,at) VALUES(?,?,?,?,?,?,?)', (mine, t['pid'], career, today(), stars, text, now()))
            except dbm.IntegrityError:
                fail('Hôm nay bạn đã đánh giá quán này rồi.', 'already_reviewed')
            notify(store, db, t['pid'], 'review', f'{me["name"]} chấm quán bạn {stars}★: “{text[:80]}”', mine)
        return dict(message='Đã gửi đánh giá. Cảm ơn bạn đã ghé!')
    if route == 'reply':
        text = clean(d.get('text'), 280, 2, 'Trả lời')
        with store.connect() as db:
            r = db.execute('SELECT * FROM previews WHERE id=?', (ival(d.get('id'), 1, 10 ** 12, 'Mã đánh giá'),)).fetchone()
            need(r and r['to_pid'] == mine, 'Không thấy đánh giá này.', 'not_found', 404)
            need(not r['reply'], 'Mỗi đánh giá chỉ trả lời một lần.')
            db.execute('UPDATE previews SET reply=?,reply_at=? WHERE id=?', (text, now(), r['id']))
            notify(store, db, r['from_pid'], 'reply', f'{me["name"]} đã trả lời đánh giá của bạn: “{text[:80]}”', mine)
        return dict(message='Đã trả lời.')
    if route == 'gift':
        sticker = d.get('sticker')
        need(sticker in STICKERS, 'Quà không hợp lệ.')
        coins = d.get('coins', 0)
        need(coins in GIFT_COINS, 'Số xu tặng không hợp lệ.')
        note = clean(d.get('note', ''), 80, 0, 'Lời nhắn')
        with store.connect() as db:
            t = _target(db, d.get('pid'))
            need(t['pid'] != mine, 'Tự tặng mình thì… để dành mua trà sữa nhé.')
            need(not _blocked(db, mine, t['pid']), 'Không thể tặng quà cho người này.', 'blocked', 403)
            need(_count(db, 'SELECT COUNT(*) FROM gifts WHERE from_pid=? AND day=?', (mine, today())) < 5, 'Hôm nay bạn đã tặng 5 món rồi.')
            need(not _count(db, 'SELECT COUNT(*) FROM gifts WHERE from_pid=? AND to_pid=? AND day=?', (mine, t['pid'], today())), 'Hôm nay bạn đã tặng người này rồi.')
            got = _count(db, 'SELECT COALESCE(SUM(coins),0) FROM gifts WHERE to_pid=? AND day=?', (t['pid'], today()))
            need(got + coins <= 100, 'Người này đã nhận đủ xu quà hôm nay. Tặng sticker thôi nhé.')
        career = state.get('current')
        if coins:
            need(career in state['careers'], 'Chọn một nghề để có ví xu trước nhé.')
            _cmd(store, token, f'soc-giftout-{mine}-{t["pid"]}-{today()}', career, 'soc_gift_out', dict(coins=coins, who=t['name']))
        with store.connect() as db:
            db.execute('INSERT INTO gifts(from_pid,to_pid,sticker,coins,note,day,at) VALUES(?,?,?,?,?,?,?)', (mine, t['pid'], sticker, coins, note, today(), now()))
            notify(store, db, t['pid'], 'gift', f'{me["name"]} tặng bạn {sticker}' + (f' + {coins} xu' if coins else '') + (f': “{note}”' if note else ''), mine)
        return dict(message=f'Đã gửi {sticker} tới {t["name"]}!')
    if route == 'list':
        career = d.get('career')
        need(career in PLUGINS and (PLUGINS[career].SPEC.get('inventory') or {}).get('items'), 'Nghề này không có kho để bán.')
        item = d.get('item')
        spec = next((x for x in PLUGINS[career].SPEC['inventory']['items'] if x['id'] == item), None)
        need(spec, 'Mặt hàng không hợp lệ.')
        qty = ival(d.get('qty'), 1, 50, 'Số lượng')
        base = max(1, int(spec.get('cost', 1)))
        price = ival(d.get('price'), max(1, base // 2), base * 3, f'Giá (từ {max(1, base // 2)} đến {base * 3} xu/đơn vị)')
        with store.connect() as db:
            need(_count(db, "SELECT COUNT(*) FROM market WHERE seller=? AND status='active'", (mine,)) < 5, 'Bạn đã có 5 món đang bán.')
            need(_count(db, 'SELECT COUNT(*) FROM market WHERE seller=? AND at>?', (mine, now() - 86400)) < 12, 'Hôm nay đăng bán đủ rồi.')
            nonce = _count(db, 'SELECT COALESCE(MAX(id),0) FROM market', ()) + 1
        r = _cmd(store, token, f'soc-list-{mine}-{nonce}-{int(now())}', career, 'soc_list', dict(item=item, qty=qty))
        with store.connect() as db:
            db.execute('INSERT INTO market(seller,career,item,qty,price,life_left,unit_cost,listed_day,status,at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (mine, career, item, qty, price, r['life_left'], r['unit_cost'], r['day'], 'active', now()))
        return dict(message=f'Đã đăng bán {qty} {spec["name"]} giá {price} xu/đơn vị.')
    if route == 'unlist':
        with store.connect() as db:
            m = db.execute('SELECT * FROM market WHERE id=?', (ival(d.get('id'), 1, 10 ** 12, 'Mã hàng'),)).fetchone()
            need(m and m['seller'] == mine, 'Không thấy món hàng này.', 'not_found', 404)
            need(db.execute("UPDATE market SET status='withdrawn' WHERE id=? AND status='active'", (m['id'],)).rowcount == 1, 'Món này đã bán hoặc đã gỡ.')
        r = _cmd(store, token, f'soc-back-{m["id"]}', m['career'], 'soc_unlist',
                 dict(item=m['item'], qty=m['qty'], life_left=m['life_left'], listed_day=m['listed_day'], unit_cost=m['unit_cost']))
        with store.connect() as db:
            db.execute('UPDATE market SET settled=1 WHERE id=?', (m['id'],))
        return dict(message=r.get('message', 'Đã gỡ hàng.'))
    if route == 'buy':
        with store.connect() as db:
            m = db.execute('SELECT * FROM market WHERE id=?', (ival(d.get('id'), 1, 10 ** 12, 'Mã hàng'),)).fetchone()
            need(m and not m['hidden'], 'Không thấy món hàng này.', 'not_found', 404)
            need(m['seller'] != mine, 'Đây là hàng của bạn.')
            need(not _blocked(db, mine, m['seller']), 'Không thể mua của người này.', 'blocked', 403)
            need(db.execute("UPDATE market SET status='pending',buyer=? WHERE id=? AND status='active'", (mine, m['id'])).rowcount == 1, 'Món này vừa có người mua mất rồi.', 'sold')
            seller = _name_of(db, m['seller'])
        try:
            r = _cmd(store, token, f'soc-buy-{m["id"]}', m['career'], 'soc_buy',
                     dict(item=m['item'], qty=m['qty'], total=m['price'] * m['qty'], life_left=m['life_left'], who=seller))
        except SocialError:
            with store.connect() as db:
                db.execute("UPDATE market SET status='active',buyer=NULL WHERE id=? AND status='pending'", (m['id'],))
            raise
        with store.connect() as db:
            db.execute("UPDATE market SET status='sold',sold_at=? WHERE id=?", (now(), m['id']))
            notify(store, db, m['seller'], 'sale', f'{me["name"]} đã mua {m["qty"]} món của bạn · +{m["price"] * m["qty"]} xu', str(m['id']))
        return dict(message=r.get('message', 'Đã mua.'))
    if route == 'board':
        career = d.get('career', 'all')
        need(career == 'all' or career in state['careers'], 'Chuyên mục không hợp lệ.')
        kind = d.get('kind')
        need(kind in BOARD_KINDS, 'Loại bài không hợp lệ.')
        text = clean(d.get('text'), 400, 4, 'Bài viết')
        with store.connect() as db:
            need(_count(db, 'SELECT COUNT(*) FROM board WHERE pid=? AND at>?', (mine, now() - 86400)) < 10, 'Hôm nay bạn đã đăng đủ 10 bài.')
            db.execute('INSERT INTO board(pid,career,kind,text,at) VALUES(?,?,?,?,?)', (mine, career, kind, text, now()))
        return dict(message='Đã đăng lên bảng tin.')
    if route == 'comment':
        text = clean(d.get('text'), 200, 2, 'Bình luận')
        with store.connect() as db:
            b = db.execute('SELECT * FROM board WHERE id=? AND hidden=0', (ival(d.get('post'), 1, 10 ** 12, 'Bài'),)).fetchone()
            need(b, 'Không thấy bài này.', 'not_found', 404)
            need(not _blocked(db, mine, b['pid']), 'Không thể bình luận bài này.', 'blocked', 403)
            need(_count(db, 'SELECT COUNT(*) FROM comments WHERE post=?', (b['id'],)) < 30, 'Bài này đã đủ bình luận.')
            need(_count(db, 'SELECT COUNT(*) FROM comments WHERE pid=? AND at>?', (mine, now() - 3600)) < 30, 'Chậm lại một chút nhé.')
            db.execute('INSERT INTO comments(post,pid,text,at) VALUES(?,?,?,?)', (b['id'], mine, text, now()))
            if b['pid'] != mine:
                notify(store, db, b['pid'], 'comment', f'{me["name"]} bình luận bài của bạn: “{text[:80]}”', str(b['id']))
        return dict(message='Đã bình luận.')
    if route == 'react':
        emoji = d.get('emoji')
        need(emoji in REACTIONS, 'Biểu cảm không hợp lệ.')
        with store.connect() as db:
            b = db.execute('SELECT id FROM board WHERE id=? AND hidden=0', (ival(d.get('post'), 1, 10 ** 12, 'Bài'),)).fetchone()
            need(b, 'Không thấy bài này.', 'not_found', 404)
            if db.execute('DELETE FROM reactions WHERE post=? AND pid=? AND emoji=?', (b['id'], mine, emoji)).rowcount == 0:
                db.execute('INSERT OR IGNORE INTO reactions(post,pid,emoji) VALUES(?,?,?)', (b['id'], mine, emoji))
        return dict(message='')
    if route == 'delete_post':
        with store.connect() as db:
            n = db.execute('DELETE FROM board WHERE id=? AND pid=?', (ival(d.get('post'), 1, 10 ** 12, 'Bài'), mine)).rowcount
            need(n, 'Không thấy bài của bạn.', 'not_found', 404)
            db.execute('DELETE FROM comments WHERE post=?', (d['post'],))
            db.execute('DELETE FROM reactions WHERE post=?', (d['post'],))
        return dict(message='Đã xóa bài.')
    if route in ('follow', 'unfollow', 'block', 'unblock'):
        with store.connect() as db:
            tp = d.get('pid')
            need(isinstance(tp, str) and re.fullmatch(r'[0-9a-f]{16}', tp) and tp != mine and _profile(db, tp), 'Người chơi không hợp lệ.')
            table = 'follows' if route.endswith('follow') else 'blocks'
            if route in ('follow', 'block'):
                db.execute(f'INSERT OR IGNORE INTO {table}(pid,target,at) VALUES(?,?,?)', (mine, tp, now()))
                if route == 'block':
                    db.execute('DELETE FROM follows WHERE (pid=? AND target=?) OR (pid=? AND target=?)', (mine, tp, tp, mine))
            else:
                db.execute(f'DELETE FROM {table} WHERE pid=? AND target=?', (mine, tp))
        return dict(message={'follow': 'Đã theo dõi quán này.', 'unfollow': 'Đã bỏ theo dõi.', 'block': 'Đã chặn. Bạn sẽ không thấy nhau trong Phố nghề.', 'unblock': 'Đã bỏ chặn.'}[route])
    if route == 'report':
        kind = d.get('kind')
        need(kind in REPORT_KINDS, 'Loại báo cáo không hợp lệ.')
        reason = d.get('reason')
        need(reason in REPORT_REASONS, 'Lý do không hợp lệ.')
        target = str(d.get('id', ''))[:32]
        table, key = dict(profile=('profiles', 'pid'), review=('previews', 'id'), board=('board', 'id'), comment=('comments', 'id'), listing=('market', 'id'))[kind]
        # Numeric ids are compared as numbers (SQLite converted '12' itself; PostgreSQL would reject 'abc').
        need(key == 'pid' or (target.isascii() and target.isdigit()), 'Không thấy nội dung này.', 'not_found', 404)
        ref = target if key == 'pid' else int(target)
        with store.connect() as db:
            need(db.execute(f'SELECT 1 FROM {table} WHERE {key}=?', (ref,)).fetchone(), 'Không thấy nội dung này.', 'not_found', 404)
            if db.execute('INSERT OR IGNORE INTO reports(reporter,kind,target,reason,at) VALUES(?,?,?,?,?)', (mine, kind, target, reason, now())).rowcount:
                db.execute(f'UPDATE {table} SET reports=reports+1, hidden=CASE WHEN reports+1>=? THEN 1 ELSE hidden END WHERE {key}=?', (HIDE_AFTER, ref))
        return dict(message='Cảm ơn bạn đã báo cáo. Nội dung bị nhiều người báo cáo sẽ tự ẩn và được xem xét.')
    if route == 'inbox_read':
        with store.connect() as db:
            db.execute('UPDATE inbox SET read=1 WHERE pid=?', (mine,))
        return dict(message='')
    fail('Không có thao tác này.', 'not_found', 404)


# ---------------------------------------------------------------- privacy & housekeeping
def forget(store, token: str) -> None:
    """Remove everything a player wrote or owns in Phố nghề."""
    _forget_pid(store, pid_of(store.key(token)))


def _forget_pid(store, pid: str) -> None:
    with store.connect() as db:
        posts = [r['id'] for r in db.execute('SELECT id FROM board WHERE pid=?', (pid,))]
        for post_id in posts:
            db.execute('DELETE FROM comments WHERE post=?', (post_id,))
            db.execute('DELETE FROM reactions WHERE post=?', (post_id,))
        for sql in ('DELETE FROM board WHERE pid=?', 'DELETE FROM comments WHERE pid=?', 'DELETE FROM reactions WHERE pid=?',
                    'DELETE FROM inbox WHERE pid=?', 'DELETE FROM follows WHERE pid=? OR target=?', 'DELETE FROM blocks WHERE pid=? OR target=?',
                    'DELETE FROM reports WHERE reporter=?', 'DELETE FROM visits WHERE from_pid=? OR to_pid=?', 'DELETE FROM previews WHERE from_pid=? OR to_pid=?',
                    'DELETE FROM gifts WHERE from_pid=? OR to_pid=?', "DELETE FROM market WHERE seller=? AND status IN ('active','withdrawn','expired')",
                    'DELETE FROM profiles WHERE pid=?'):
            db.execute(sql, (pid,) * sql.count('?'))
        # Sold items keep the buyer's history but lose the seller's identity.
        db.execute("UPDATE market SET seller='deleted' WHERE seller=?", (pid,))


def prune(store) -> None:
    t = now()
    with store.connect() as db:
        # Saves removed by Store.prune take their street presence with them.
        orphans = [r['pid'] for r in db.execute('SELECT pid FROM profiles WHERE sid NOT IN (SELECT sid FROM sessions)')]
    for pid in orphans:
        _forget_pid(store, pid)
    with store.connect() as db:
        db.execute('DELETE FROM inbox WHERE at<?', (t - 60 * 86400,))
        db.execute('DELETE FROM visits WHERE at<?', (t - 30 * 86400,))
        db.execute("DELETE FROM market WHERE status IN ('withdrawn','expired','sold') AND settled=1 AND at<?", (t - 30 * 86400,))
        old = [r['id'] for r in db.execute('SELECT id FROM board WHERE at<?', (t - 180 * 86400,))]
        for post_id in old:
            db.execute('DELETE FROM comments WHERE post=?', (post_id,))
            db.execute('DELETE FROM reactions WHERE post=?', (post_id,))
            db.execute('DELETE FROM board WHERE id=?', (post_id,))
