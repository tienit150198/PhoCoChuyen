"""Player feedback ("Góp ý"): short private notes from players to the operator.

A player writes a bug report, an idea, praise or "hard to use"; the operator
(an account listed in ADMIN_USERS) reads them in an in-game inbox, marks them
seen/done and may write one short reply the player sees next to the note.
Nothing here touches the save. See docs/superpowers/specs/2026-09-29-player-feedback-design.md.

Text is cleaned like the street's, but contact details and links are redacted
(`ai.redact`) instead of rejected, and rude words are masked (`social.BANNED`).
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import time
import unicodedata

from . import accounts
from .ai import redact
from .social import BANNED

KINDS = ('bug', 'idea', 'praise', 'hard')
STATUSES = ('new', 'seen', 'done')
TEXT_MAX, TEXT_MIN, REPLY_MAX = 10000, 3, 10000   # owner 06/10: góp ý up to 10,000 characters (was 1,000); 10/10: the reply too (was 300)
MINE_LIMIT, ADMIN_PAGE = 20, 50
LAYOUTS = ('phone', 'tablet', 'desktop')
THANKS = 'Đã ghi nhận, cảm ơn bạn!'
_VIEW = re.compile(r'[A-Za-z0-9_-]{1,40}')
_SCREEN = re.compile(r'\d{2,5}x\d{2,5}')


class FeedbackError(Exception):
    def __init__(self, message: str, code: str = 'feedback_error', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'feedback_error', status: int = 400):
    if not cond:
        raise FeedbackError(message, code, status)


# ---------------------------------------------------------------- cleaning
def mask_banned(text: str) -> str:
    for word in BANNED:
        text = re.sub(r'(?<!\w)' + re.escape(word) + r'(?!\w)', '•••', text, flags=re.I)
    return text


def clean_text(text, limit: int, minimum: int = 0, field: str = 'Nội dung') -> str:
    """NFC, no control characters, squeezed spaces; links, e-mails and phone-like
    numbers become [đã ẩn]; rude words become •••."""
    need(isinstance(text, str), f'{field} không hợp lệ.')
    text = unicodedata.normalize('NFC', text)
    text = ''.join(ch for ch in text if ch == '\n' or unicodedata.category(ch)[0] != 'C')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    need(minimum <= len(text) <= limit, f'{field} cần từ {minimum} đến {limit} ký tự.', 'bad_length')
    return mask_banned(redact(text))


def clean_context(client, state: dict, ua: str = '', version: str = '') -> dict:
    """Server facts (career, day, life day, language, version, user agent) plus a
    few whitelisted client hints (view, layout, screen). Bad hints are dropped."""
    out: dict = {}
    current = state.get('current')
    careers = state.get('careers') or {}
    if isinstance(current, str) and current in careers:
        out['career'] = current
        day = careers[current].get('day')
        if type(day) is int:
            out['day'] = day
    life = (state.get('journey') or {}).get('life_day')
    if type(life) is int:
        out['life_day'] = life
    lang = (state.get('settings') or {}).get('lang')
    if lang in ('vi', 'en'):
        out['lang'] = lang
    if version:
        out['version'] = str(version)[:20]
    if isinstance(ua, str) and ua.strip():
        out['ua'] = ''.join(ch for ch in ua if ch.isprintable())[:200]
    client = client if isinstance(client, dict) else {}
    view, layout, screen = client.get('view'), client.get('layout'), client.get('screen')
    if isinstance(view, str) and _VIEW.fullmatch(view):
        out['view'] = view
    if layout in LAYOUTS:
        out['layout'] = layout
    if isinstance(screen, str) and _SCREEN.fullmatch(screen):
        out['screen'] = screen
    return out


# ---------------------------------------------------------------- who is who
def admin_users() -> set[str]:
    return {u.strip().lower() for u in os.environ.get('ADMIN_USERS', '').split(',') if u.strip()}


def account_of(store, token: str | None) -> str | None:
    info = accounts.status(store, token)
    return info['username'] if info else None


def is_admin(store, token: str | None) -> bool:
    """Only a signed-in account whose username is listed in ADMIN_USERS."""
    admins = admin_users()
    if not admins or not token:
        return False
    return (account_of(store, token) or '') in admins


def _tag(sid: str) -> str:
    return hashlib.sha256(('fb:' + sid).encode()).hexdigest()[:8]


def _row(r, admin: bool = False) -> dict:
    item = dict(id=r['id'], kind=r['kind'], text=r['text'], status=r['status'], reply=r['reply'],
                created_at=r['created_at'], updated_at=r['updated_at'], replied_at=r['replied_at'])
    if admin:
        try:
            ctx = json.loads(r['context'] or '{}')
        except ValueError:
            ctx = {}
        item.update(context=ctx if isinstance(ctx, dict) else {}, account=r['account'], player=_tag(r['sid']))
    return item


# ---------------------------------------------------------------- player side
def submit(store, token: str, state: dict, data: dict, ua: str = '', version: str = '') -> dict:
    need(isinstance(data, dict), 'Dữ liệu góp ý không hợp lệ.')
    kind = data.get('kind')
    need(kind in KINDS, 'Chọn loại góp ý: lỗi, ý tưởng, lời khen hoặc khó dùng.', 'bad_kind')
    text = clean_text(data.get('text'), TEXT_MAX, TEXT_MIN, 'Góp ý')
    need(len(text.replace('•••', '').replace('[đã ẩn]', '').strip()) >= TEXT_MIN, 'Viết thêm vài chữ nữa nhé.', 'bad_length')
    context = clean_context(data.get('context'), state, ua, version)
    sid = store.key(token)
    account = account_of(store, token)
    now = time.time()
    with store.connect() as db:
        sql = 'INSERT INTO player_feedback(sid,account,kind,text,context,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)'
        args = (sid, account, kind, text, json.dumps(context, ensure_ascii=False), 'new', now, now)
        fid = db.execute(sql + ' RETURNING id', args).fetchone()[0]
    return dict(ok=True, id=fid, message=THANKS)


EDITED = 'Đã lưu góp ý.'
NOT_EDITABLE = 'Góp ý này đã có lời đáp nên không sửa được nữa. Gửi góp ý mới nhé.'


def edit(store, token: str, data: dict) -> dict:
    """F#295 "nên có nút sửa lại góp ý": the player's own note, while it has no reply yet. One UPDATE by id AND owner
    (this save or this account, as list_mine) AND reply IS NULL, so a reply written meanwhile wins. The edited note
    goes back to "new" so the operator reads it again. Kind may change too (optional)."""
    need(isinstance(data, dict), 'Dữ liệu góp ý không hợp lệ.')
    fid = _int(data.get('id'), 'Mã góp ý')
    need(fid is not None, 'Thiếu mã góp ý.')
    kind = data.get('kind')
    need(kind is None or kind in KINDS, 'Chọn loại góp ý: lỗi, ý tưởng, lời khen hoặc khó dùng.', 'bad_kind')
    text = clean_text(data.get('text'), TEXT_MAX, TEXT_MIN, 'Góp ý')
    need(len(text.replace('•••', '').replace('[đã ẩn]', '').strip()) >= TEXT_MIN, 'Viết thêm vài chữ nữa nhé.', 'bad_length')
    sid = store.key(token)
    account = account_of(store, token)
    now = time.time()
    with store.connect() as db:
        row = db.execute("UPDATE player_feedback SET text=?, kind=COALESCE(?, kind), status='new', updated_at=? "
                         'WHERE id=? AND (sid=? OR (account IS NOT NULL AND account=?)) AND reply IS NULL RETURNING *',
                         (text, kind, now, fid, sid, account or '')).fetchone()
    need(row, NOT_EDITABLE, 'not_editable', 409)
    return dict(ok=True, item=_row(row), message=EDITED)


def list_mine(store, token: str, limit: int = MINE_LIMIT) -> list[dict]:
    sid = store.key(token)
    account = account_of(store, token)
    with store.connect() as db:
        rows = db.execute('SELECT * FROM player_feedback WHERE sid=? OR (account IS NOT NULL AND account=?) ORDER BY id DESC LIMIT ?',
                          (sid, account or '', int(limit))).fetchall()
    return [_row(r) for r in rows]


def forget(store, token: str) -> int:
    """'Xóa dữ liệu của tôi': this save's and this account's notes go."""
    sid = store.key(token)
    account = account_of(store, token)
    with store.connect() as db:
        return db.execute('DELETE FROM player_feedback WHERE sid=? OR (account IS NOT NULL AND account=?)', (sid, account or '')).rowcount


def prune(store, days: int = 730) -> int:
    with store.connect() as db:
        return db.execute('DELETE FROM player_feedback WHERE created_at<?', (time.time() - int(days) * 86400,)).rowcount


# ---------------------------------------------------------------- operator side
def _int(value, field: str) -> int | None:
    if value in (None, ''):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise FeedbackError(f'{field} không hợp lệ.') from None
    need(0 < n < 2 ** 62, f'{field} không hợp lệ.')
    return n


def list_admin(store, status=None, kind=None, before=None, limit: int = ADMIN_PAGE) -> dict:
    status = status or None
    kind = kind or None
    need(status is None or status in STATUSES, 'Trạng thái không hợp lệ.')
    need(kind is None or kind in KINDS, 'Loại góp ý không hợp lệ.')
    before = _int(before, 'Mốc trang')
    where, args = [], []
    if status:
        where.append('status=?'); args.append(status)
    if kind:
        where.append('kind=?'); args.append(kind)
    if before:
        where.append('id<?'); args.append(before)
    sql = 'SELECT * FROM player_feedback' + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY id DESC LIMIT ?'
    with store.connect() as db:
        rows = db.execute(sql, (*args, int(limit) + 1)).fetchall()
        counts = {s: 0 for s in STATUSES}
        for r in db.execute('SELECT status, COUNT(*) AS n FROM player_feedback GROUP BY status'):
            counts[r['status']] = r['n']
    more = len(rows) > limit
    rows = rows[:limit]
    return dict(items=[_row(r, admin=True) for r in rows], next=rows[-1]['id'] if more and rows else None, counts=counts)


def update(store, fid, status=None, reply=None) -> dict:
    """status: new|seen|done or None (keep). reply: text, '' (clear) or None (keep)."""
    fid = _int(fid, 'Mã góp ý')
    need(fid is not None, 'Thiếu mã góp ý.')
    touch_reply = reply is not None
    need(status is not None or touch_reply, 'Không có gì để cập nhật.')
    need(status is None or status in STATUSES, 'Trạng thái không hợp lệ.')
    if touch_reply:
        reply = clean_text(reply, REPLY_MAX, 0, 'Lời đáp') or None
    now = time.time()
    with store.connect() as db:
        row = db.execute('SELECT id FROM player_feedback WHERE id=?', (fid,)).fetchone()
        need(row, 'Không tìm thấy góp ý này.', 'not_found', 404)
        sets, args = ['updated_at=?'], [now]
        if status is not None:
            sets.append('status=?'); args.append(status)
        if touch_reply:
            sets += ['reply=?', 'replied_at=?']; args += [reply, now if reply else None]
        db.execute(f'UPDATE player_feedback SET {",".join(sets)} WHERE id=?', (*args, fid))
        row = db.execute('SELECT * FROM player_feedback WHERE id=?', (fid,)).fetchone()
    return _row(row, admin=True)
