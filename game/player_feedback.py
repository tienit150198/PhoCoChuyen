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
import logging
import os
import re
import secrets
import time
import unicodedata

from . import accounts
from .ai import redact
from .social import BANNED
from . import feedback_images
from . import system_gift

KINDS = ('bug', 'idea', 'praise', 'hard')
STATUSES = ('new', 'seen', 'done')
TEXT_MAX, TEXT_MIN, REPLY_MAX = 10000, 3, 10000   # owner 06/10: góp ý up to 10,000 characters (was 1,000); 10/10: the reply too (was 300)
MINE_LIMIT, ADMIN_PAGE = 20, 50
LAYOUTS = ('phone', 'tablet', 'desktop')
THANKS = 'Đã ghi nhận, cảm ơn bạn!'
CREDITS = ('name', 'anon')   # F#503: an idea's thank-you line in "Có gì mới" (game/whats_new.py thanks=): the character's name, or "ẩn danh"
# 🎁 Owner 23/10 "chỉ cái nào được mình ghi nhận mới có thưởng": a note the operator acknowledges (✅ Ghi nhận) pays its
# player once, through the gift system (game/system_gift.py, id reward_id(fid)). Secret: the form never mentions it.
REWARD = {'bug': 30_000, 'idea': 30_000, 'praise': 30_000, 'hard': 30_000}
REWARD_GIFT = {   # kind -> (card title, text with the note's first words as {q}): a thank-you for that note, no rule
    'idea': ('💡 Cảm ơn ý tưởng của bạn', 'Cảm ơn bạn đã góp ý tưởng: “{q}”. Nhà làm game đã ghi nhận ý tưởng này, gửi bạn chút quà cảm ơn! 💛'),
    'bug': ('🐞 Cảm ơn bạn đã báo lỗi', 'Cảm ơn bạn đã báo lỗi: “{q}”. Nhà làm game đã ghi nhận lỗi bạn báo, gửi bạn chút quà cảm ơn! 💛'),
    'praise': ('💛 Cảm ơn lời khen của bạn', 'Cảm ơn lời khen của bạn: “{q}”. Cả nhà làm game đọc mà vui lắm, gửi bạn chút quà cảm ơn! 💛'),
    'hard': ('🧭 Cảm ơn góp ý của bạn', 'Cảm ơn bạn đã góp ý: “{q}”. Nhà làm game đã đọc kỹ và ghi nhận, gửi bạn chút quà cảm ơn! 💛'),
}
QUOTE = 60
LOG = logging.getLogger(__name__)
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


def with_credit(ctx: dict, kind: str, credit=None) -> dict:
    """F#503: an idea keeps context['credit'] ('name' only when the player ticked "ghi tên nhân vật", else 'anon');
    any other kind has none. credit: True / False from the form, None = keep what the note had (default 'anon')."""
    ctx = dict(ctx)
    if kind != 'idea':
        ctx.pop('credit', None)
    elif type(credit) is bool:
        ctx['credit'] = 'name' if credit else 'anon'
    elif ctx.get('credit') not in CREDITS:
        ctx['credit'] = 'anon'
    return ctx


def _ctx(raw) -> dict:
    try:
        ctx = json.loads(raw or '{}')
    except ValueError:
        return {}
    return ctx if isinstance(ctx, dict) else {}


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


def _row(r, admin: bool = False, images: dict | None = None, extras: dict | None = None) -> dict:
    item = dict(id=r['id'], kind=r['kind'], text=r['text'], status=r['status'], reply=r['reply'],
                created_at=r['created_at'], updated_at=r['updated_at'], replied_at=r['replied_at'],
                images=(images or {}).get(r['id'], []))
    ctx = _ctx(r['context'])
    if r['kind'] == 'idea' and ctx.get('credit') in CREDITS:
        item['credit'] = ctx['credit']   # F#503: the player's own choice shows (and is editable) in their list too
    if admin:
        item.update(context=ctx, account=r['account'], player=_tag(r['sid']), reward=None, reward_coins=REWARD.get(r['kind']))
        item.update((extras or {}).get(r['id'], {}))
    return item


def reward_id(fid: int) -> str:
    """The 🎁 thank-you gift's id for one note (system_gift.valid_id): the same note can only ever be paid once."""
    return f'fb-thanks-{int(fid)}'


def _extras(db, rows) -> dict:
    """Admin rows: the thank-you gift (system_gifts by its primary key) and, for an idea, the character's name
    (leaderboard_players by sid, its primary key) for the credit badge. Two bounded lookups, never a scan."""
    if not rows:
        return {}
    out: dict = {r['id']: {} for r in rows}
    gids = {reward_id(r['id']): r['id'] for r in rows}
    for g in db.execute(f'SELECT id,coins,status FROM system_gifts WHERE id IN ({",".join("?" for _ in gids)})', list(gids)):
        out[gids[g['id']]]['reward'] = dict(coins=int(g['coins']), status=g['status'])
    named = {r['sid'] for r in rows if r['kind'] == 'idea'}
    if named:
        names = {n['sid']: n['name'] for n in db.execute(
            f'SELECT sid,name FROM leaderboard_players WHERE sid IN ({",".join("?" for _ in named)})', list(named))}
        for r in rows:
            if r['kind'] == 'idea':
                out[r['id']]['name'] = names.get(r['sid']) or None
    return out


def _image_metadata(db, rows) -> dict:
    """One bounded metadata query; never load image bytes for inbox/list rows."""
    ids = [r['id'] for r in rows]
    if not ids:
        return {}
    out: dict = {}
    for r in db.execute('SELECT id,feedback_id,mime,width,height,byte_size FROM player_feedback_images '
                        f'WHERE feedback_id IN ({",".join("?" for _ in ids)}) ORDER BY feedback_id,position', ids):
        out.setdefault(r['feedback_id'], []).append(dict(id=r['id'], url='/api/feedback/images/' + r['id'],
            mime=r['mime'], width=r['width'], height=r['height'], size=r['byte_size']))
    return out


def read_image(store, token: str | None, image_id: str) -> tuple[bytes, str]:
    """Cookie/session route: only this feedback's owner or a current operator."""
    need(token, 'Bạn chưa có phiên chơi.', 'no_session', 401)
    need(isinstance(image_id, str) and re.fullmatch(r'[a-f0-9]{32}', image_id),
         'Không tìm thấy ảnh.', 'not_found', 404)
    sid = store.key(token)
    account = account_of(store, token)
    admin = bool(account and account in admin_users())
    with store.connect() as db:
        row = db.execute('SELECT i.data,i.mime FROM player_feedback_images i '
            'JOIN player_feedback f ON f.id=i.feedback_id WHERE i.id=? '
            'AND (? OR f.sid=? OR (f.account IS NOT NULL AND f.account=?))',
            (image_id, admin, sid, account or '')).fetchone()
    need(row, 'Không tìm thấy ảnh.', 'not_found', 404)
    return bytes(row['data']), row['mime']


# ---------------------------------------------------------------- player side
def submit(store, token: str, state: dict, data: dict, ua: str = '', version: str = '') -> dict:
    need(isinstance(data, dict), 'Dữ liệu góp ý không hợp lệ.')
    kind = data.get('kind')
    need(kind in KINDS, 'Chọn loại góp ý: lỗi, ý tưởng, lời khen hoặc khó dùng.', 'bad_kind')
    text = clean_text(data.get('text'), TEXT_MAX, TEXT_MIN, 'Góp ý')
    need(len(text.replace('•••', '').replace('[đã ẩn]', '').strip()) >= TEXT_MIN, 'Viết thêm vài chữ nữa nhé.', 'bad_length')
    try:
        images = feedback_images.decode_images(data.get('images', []))
    except feedback_images.ImageUploadError as exc:
        raise FeedbackError(str(exc), exc.code, exc.status) from None
    context = with_credit(clean_context(data.get('context'), state, ua, version), kind, data.get('credit'))
    sid = store.key(token)
    account = account_of(store, token)
    now = time.time()
    with store.connect() as db:
        sql = 'INSERT INTO player_feedback(sid,account,kind,text,context,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)'
        args = (sid, account, kind, text, json.dumps(context, ensure_ascii=False), 'new', now, now)
        fid = db.execute(sql + ' RETURNING id', args).fetchone()[0]
        for position, image in enumerate(images):
            db.execute('INSERT INTO player_feedback_images(id,feedback_id,position,mime,width,height,byte_size,data) '
                       'VALUES(?,?,?,?,?,?,?,?)', (secrets.token_hex(16), fid, position, image['mime'],
                       image['width'], image['height'], image['size'], image['data']))
    return dict(ok=True, id=fid, message=THANKS)


EDITED = 'Đã lưu góp ý.'
NOT_EDITABLE = 'Góp ý này đã có lời đáp nên không sửa được nữa. Gửi góp ý mới nhé.'


def edit(store, token: str, data: dict) -> dict:
    """F#295 "nên có nút sửa lại góp ý": the player's own note, while it has no reply yet. One UPDATE by id AND owner
    (this save or this account, as list_mine) AND reply IS NULL, so a reply written meanwhile wins. The edited note
    goes back to "new" so the operator reads it again. Kind may change too (optional), and an idea's credit (F#503)."""
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
        cur = db.execute('SELECT kind,context FROM player_feedback WHERE id=? AND (sid=? OR (account IS NOT NULL AND account=?)) '
                         'AND reply IS NULL', (fid, sid, account or '')).fetchone()
        ctx = json.dumps(with_credit(_ctx(cur['context']), kind or cur['kind'], data.get('credit')), ensure_ascii=False) if cur else None
        row = db.execute("UPDATE player_feedback SET text=?, kind=COALESCE(?, kind), context=COALESCE(?, context), status='new', "
                         'updated_at=? WHERE id=? AND (sid=? OR (account IS NOT NULL AND account=?)) AND reply IS NULL RETURNING *',
                         (text, kind, ctx, now, fid, sid, account or '')).fetchone()
        images = _image_metadata(db, [row]) if row else {}
    need(row, NOT_EDITABLE, 'not_editable', 409)
    return dict(ok=True, item=_row(row, images=images), message=EDITED)


DELETED = 'Đã xóa góp ý.'
NOT_DELETABLE = 'Góp ý này đã có lời đáp nên không xóa được nữa.'


def delete(store, token: str, data: dict) -> dict:
    """F#412 "cái nút xóa góp ý": the player's own note (and its images, ON DELETE CASCADE) while it has no reply yet.
    One DELETE by id AND owner (as edit / list_mine) AND reply IS NULL, so a reply written meanwhile wins."""
    need(isinstance(data, dict), 'Dữ liệu góp ý không hợp lệ.')
    fid = _int(data.get('id'), 'Mã góp ý')
    need(fid is not None, 'Thiếu mã góp ý.')
    sid = store.key(token)
    account = account_of(store, token)
    with store.connect() as db:
        row = db.execute('DELETE FROM player_feedback WHERE id=? AND (sid=? OR (account IS NOT NULL AND account=?)) '
                         'AND reply IS NULL RETURNING id', (fid, sid, account or '')).fetchone()
    need(row, NOT_DELETABLE, 'not_deletable', 409)
    return dict(ok=True, id=fid, message=DELETED)


def list_mine(store, token: str, limit: int = MINE_LIMIT) -> list[dict]:
    sid = store.key(token)
    account = account_of(store, token)
    with store.connect() as db:
        rows = db.execute('SELECT * FROM player_feedback WHERE sid=? OR (account IS NOT NULL AND account=?) ORDER BY id DESC LIMIT ?',
                          (sid, account or '', int(limit))).fetchall()
        images = _image_metadata(db, rows)
    return [_row(r, images=images) for r in rows]


def forget(store, token: str) -> int:
    """'Xóa dữ liệu của tôi': this save's and this account's notes go."""
    sid = store.key(token)
    account = account_of(store, token)
    with store.connect() as db:
        return db.execute('DELETE FROM player_feedback WHERE sid=? OR (account IS NOT NULL AND account=?)', (sid, account or '')).rowcount


def prune(store, days: int = 730) -> int:
    """Feedback and its images are retained until the owner explicitly requests deletion.

    Kept as a no-op for existing housekeeping callers. Status, age, deployments
    and idle-save cleanup must never remove submitted feedback or its images.
    """
    return 0


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
        images, extras = _image_metadata(db, rows[:limit]), _extras(db, rows[:limit])
    more = len(rows) > limit
    rows = rows[:limit]
    return dict(items=[_row(r, admin=True, images=images, extras=extras) for r in rows], next=rows[-1]['id'] if more and rows else None,
                counts=counts)


def update(store, fid, status=None, reply=None, acknowledge: bool = False, by: str | None = None) -> dict:
    """status: new|seen|done or None (keep). reply: text, '' (clear) or None (keep). acknowledge=True: also ✅ ghi nhận
    the note (acknowledge_note) once the status and reply are saved; a gift that fails is logged and reported in the
    item's reward_error, never undoing them. 'done' alone pays nothing (owner 23/10)."""
    fid = _int(fid, 'Mã góp ý')
    need(fid is not None, 'Thiếu mã góp ý.')
    touch_reply = reply is not None
    need(status is not None or touch_reply or acknowledge is True, 'Không có gì để cập nhật.')
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
        if len(sets) > 1:
            db.execute(f'UPDATE player_feedback SET {",".join(sets)} WHERE id=?', (*args, fid))
    error = None
    if acknowledge is True:
        try:
            acknowledge_note(store, fid, by)
        except Exception as e:   # noqa: BLE001 - the reply and status are saved already; the operator sees why
            LOG.exception('feedback #%s: the thank-you gift failed', fid)
            error = getattr(e, 'message', None) or 'Chưa gửi được quà cảm ơn.'
    with store.connect() as db:
        row = db.execute('SELECT * FROM player_feedback WHERE id=?', (fid,)).fetchone()
        images, extras = _image_metadata(db, [row]), _extras(db, [row])
    item = _row(row, admin=True, images=images, extras=extras)
    if error:
        item['reward_error'] = error
    return item


def _quote(text: str) -> str:
    line = ' '.join((text or '').split('\n')[0].split())
    return line if len(line) <= QUOTE else line[:QUOTE - 1].rstrip() + '…'


def acknowledge_note(store, fid, by: str | None = None) -> dict:
    """✅ Ghi nhận (owner 23/10): queue this note's thank-you gift, REWARD[kind] xu with a card quoting the note, paid at
    the player's next load (game/system_gift.py). Once per note whatever the clicks, retries or status changes: the gift
    id is reward_id(fid). Returns {status: created | exists, coins, gift_status}."""
    fid = _int(fid, 'Mã góp ý')
    need(fid is not None, 'Thiếu mã góp ý.')
    gid = reward_id(fid)
    with store.connect() as db:
        row = db.execute('SELECT id,sid,kind,text FROM player_feedback WHERE id=?', (fid,)).fetchone()
        need(row, 'Không tìm thấy góp ý này.', 'not_found', 404)
        have = db.execute('SELECT coins,status FROM system_gifts WHERE id=?', (gid,)).fetchone()
    if have:
        return dict(status='exists', coins=int(have['coins']), gift_status=have['status'])
    coins = REWARD.get(row['kind'])
    need(coins, 'Loại góp ý này không có quà cảm ơn.', 'no_reward')
    title, text = REWARD_GIFT[row['kind']]
    try:
        out = system_gift.grant(store, row['sid'], coins, title, text.format(q=_quote(row['text'])), gid=gid, by=by)
    except system_gift.GiftError as e:
        raise FeedbackError(f'Chưa gửi được quà cảm ơn: {e.message}', 'reward_failed', 409) from None
    return dict(status=out['status'], coins=int(out['gift']['coins']), gift_status=out['gift']['status'])
