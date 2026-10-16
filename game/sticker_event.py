"""🎨 Thi làm sticker (owner 16/10/2026): players make a sticker PACK (one character, many expressions, like the owner's
sample of 16 cats) in any app they like (Canva, Picsart, drawn by hand, AI with a note…), send it on /sticker
(public/sticker.html, public/js/sticker/main.js) and post it in the game's Facebook group; the reactions there decide
the winners. The pack also comes here so the operators have the original, its author and its rank (the top 10 packs
become chat stickers later).

Rules (owner): "tạo sticker chủ đề bất kì … ai được vote nhiều hơn thì sẽ được thắng, tham gia thì tặng 200k/1 người,
top 1 3m, top 2–3 1.5m, top 10 500k … có cả username … top 10 sẽ có sticker sử dụng trong chat"; then (16/10 afternoon,
with the sample): "phải làm như này" — a whole set; "hoặc là từng cái, hoặc là 1 nhóm"; at least 12 stickers; AI
allowed when said ("Cho, nhưng phải ghi rõ"); one pack per account, replaceable.
* Only a signed-in account (not a guest) whose character lived MIN_LIFE_DAYS days sends a pack.
* One pack per account (sticker_packs.sid UNIQUE), replaced in place until END. kind 'sheet': ONE picture of the whole
  set (PNG or WebP, at most SHEET_MAX_BYTES, sides SHEET_MIN_SIDE..SHEET_MAX_SIDE) and the number of stickers on it as
  the author says (MIN_PACK..MAX_SHEET_COUNT; the operators check); kind 'set': MIN_PACK..MAX_SET images of exactly
  SIZE x SIZE (the page fits each picture into the square), each at most SET_ITEM_BYTES. `ai` (required): the author
  says whether AI helped; the page writes it into the Facebook caption and the operators see it.
  The server checks the magic bytes, decodes every image with Pillow and keeps only re-encoded pixels (no metadata) plus
  a thumbnail. Packs are private: the author and the admins see them; the winners' packs become public once the prizes
  are given (the results on the page).
* The first pack of an account queues JOIN_COINS through the system gift path (game/system_gift.py: paid at the next
  load, once). One reward row per account and kind (sticker_rewards), with the life day and a short IP tag, for the
  operators to review (clone rings); a reward still pending can be revoked. The accounts paid for a single sticker under
  the first rules (2.4.29, sticker_entries) keep it: their reward row already exists, so a pack pays nothing more.
* Admins (ADMIN_USERS, /admin "🎨 Thi sticker") reject / restore packs, set ranks 1..10 by hand from the Facebook votes
  and press "Trao giải" after END: PRIZES[rank] per ranked pack, once (sticker_rewards), and the rank is locked.

Tables (game/pg_schema.py): sticker_packs, sticker_pack_images (SCHEMA_VERSION 50); sticker_rewards; sticker_entries
(SCHEMA_VERSION 49: the single stickers of the first rules, read only now). New tables only, no FK, no save key.
Account deletion ("Xóa dữ liệu") removes this account's pack, single stickers and reward rows.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import threading
import time
import warnings

from . import accounts, system_gift
from .player_feedback import admin_users

EVENT = 'sticker2610'
END = 1793120399                    # 27/10/2026 23:59:59 (VN): last moment to send; the owner may move it
MIN_PACK = 12                       # stickers in a pack, at least (owner)
MAX_SET = 24                        # images in a 'set' pack
MAX_SHEET_COUNT = 100               # the number a 'sheet' author may declare
SIZE = 512                          # a 'set' image: exactly SIZE x SIZE pixels
SET_ITEM_BYTES = 250 * 1024         # one 'set' image, as sent and as stored
SHEET_MAX_BYTES = 3 * 1024 * 1024   # the one 'sheet' picture, as sent and as stored
SHEET_MIN_SIDE, SHEET_MAX_SIDE = 300, 4096
MAX_BODY = 4 * ((max(SHEET_MAX_BYTES, MAX_SET * SET_ITEM_BYTES) + 2) // 3) + 64 * 1024   # the JSON body of a pack
MIN_LIFE_DAYS = 3                   # journey.life_day of the character, to send (anti clone-ring)
JOIN_COINS = 200_000
PRIZES = {1: 3_000_000, 2: 1_500_000, 3: 1_500_000, **{r: 500_000 for r in range(4, 11)}}
TOP = 10
FB_GROUP_URL = 'https://www.facebook.com/groups/1985137015484964'   # the game's Facebook group (owner 16/10)
HASHTAG = '#PhoCoChuyen'                   # owner 16/10
THUMB, SHEET_THUMB = 160, 480
MIMES = {'image/png': 'PNG', 'image/webp': 'WEBP'}
ADMIN_LIST = 500
_GATE = threading.BoundedSemaphore(1)   # one pack decoding at a time per worker; never queue large bodies


class StickerError(ValueError):
    def __init__(self, message: str, code: str = 'bad_sticker', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(ok, message: str, code: str = 'bad_sticker', status: int = 400) -> None:
    if not ok:
        raise StickerError(message, code, status)


def now() -> float:
    return time.time()


def is_open(t: float | None = None) -> bool:
    return (now() if t is None else t) <= END


def coins_text(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def hint() -> dict | None:
    """/api/bootstrap `ui.sticker` (server.ui_config): the in-game entry shows while submissions are open."""
    return dict(until=END) if is_open() else None


def _tag(text: str) -> str:
    return hashlib.sha256(('stk:' + text).encode()).hexdigest()


# ---------------------------------------------------------------- the images
def _too_big(label: str, max_bytes: int) -> str:
    return f'{label} quá lớn: tối đa {max_bytes // 1024} KB.' if max_bytes < 1024 * 1024 else f'{label} quá lớn: tối đa {max_bytes // (1024 * 1024)} MB.'


def _raw(value, max_bytes: int, label: str) -> tuple[bytes, str]:
    """data:image/png|webp;base64,… → (bytes, mime), or StickerError (`label` names the picture in the messages)."""
    need(isinstance(value, str), 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    need(len(value) <= 4 * ((max_bytes + 2) // 3) + 64, _too_big(label, max_bytes), 'too_large', 413)
    header, sep, encoded = value.partition(',')
    mime = next((m for m in MIMES if header == f'data:{m};base64'), None)
    need(mime and sep and encoded, 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise StickerError(f'{label} không hợp lệ. Chọn lại ảnh rồi gửi nhé.') from None
    need(0 < len(raw) <= max_bytes, _too_big(label, max_bytes), 'too_large', 413)
    magic = raw.startswith(b'\x89PNG\r\n\x1a\n') if mime == 'image/png' else raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'
    need(magic, 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    return raw, mime


def _decode(raw: bytes, mime: str, *, square: bool, max_bytes: int, thumb: int, label: str) -> dict:
    """Bytes checked by _raw → {data, thumb, mime, width, height, size, sha}: decoded, size-checked, re-encoded
    (pixels only: no text chunks, profiles or trailing bytes). The caller holds _GATE."""
    from PIL import Image, UnidentifiedImageError
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=[MIMES[mime]]) as im:
                need(im.format == MIMES[mime] and getattr(im, 'n_frames', 1) == 1, f'{label} cần là ảnh tĩnh (không động).', 'bad_type')
                w, h = im.size
                if square:
                    need((w, h) == (SIZE, SIZE), f'{label} cần đúng {SIZE}×{SIZE} điểm ảnh.', 'bad_size')
                else:
                    need(min(w, h) >= SHEET_MIN_SIDE and max(w, h) <= SHEET_MAX_SIDE,
                         f'{label} cần cạnh từ {SHEET_MIN_SIDE} đến {SHEET_MAX_SIDE} điểm ảnh.', 'bad_size')
                im.verify()
            with Image.open(io.BytesIO(raw), formats=[MIMES[mime]]) as im:
                im.load()
                pic = im.convert('RGBA')
        need(pic.getchannel('A').getbbox() is not None, f'{label} đang trống.', 'empty')
        out = io.BytesIO()
        if mime == 'image/png':
            pic.save(out, 'PNG', compress_level=6)
        else:
            pic.save(out, 'WEBP', lossless=True, method=4)
        if out.tell() > max_bytes:   # re-encoding may grow a tight file: a high-quality WebP instead
            out, mime = io.BytesIO(), 'image/webp'
            pic.save(out, 'WEBP', quality=92, method=4)
        data = out.getvalue()
        need(len(data) <= max_bytes, f'{label} sau khi xử lý vẫn quá lớn. Thu nhỏ ảnh một chút nhé.', 'too_large', 413)
        small = pic.copy()
        small.thumbnail((thumb, thumb))
        tb = io.BytesIO()
        small.save(tb, 'WEBP', quality=82)
    except StickerError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise StickerError(f'{label} không hợp lệ. Chọn lại ảnh rồi gửi nhé.') from None
    return dict(data=data, thumb=tb.getvalue(), mime=mime, width=pic.width, height=pic.height, size=len(data),
                sha=hashlib.sha256(data).hexdigest())


def decode_pack(data: dict) -> dict:
    """The body of POST /api/sticker/pack → {kind, count, ai, images: [decoded…], bytes, sha}, or StickerError."""
    need(isinstance(data, dict) and set(data) <= {'kind', 'count', 'ai', 'images', 'rid'}, 'Dữ liệu không hợp lệ.', 'bad_request')
    kind, images, ai = data.get('kind'), data.get('images'), data.get('ai')
    need(kind in ('sheet', 'set'), 'Chọn cách nộp: một ảnh cả bộ hoặc từng sticker.', 'bad_kind')
    need(type(ai) is bool, 'Cho biết bộ sticker có dùng AI hay không nhé.', 'bad_ai')
    need(isinstance(images, list) and images, 'Chưa có ảnh nào.', 'empty')
    if kind == 'sheet':
        count = data.get('count')
        need(len(images) == 1, 'Nộp kiểu một ảnh cả bộ thì gửi đúng một ảnh.', 'bad_count')
        need(type(count) is int and MIN_PACK <= count <= MAX_SHEET_COUNT,
             f'Bộ sticker cần ít nhất {MIN_PACK} sticker (ghi số sticker có trong ảnh).', 'too_few')
        raws = [_raw(images[0], SHEET_MAX_BYTES, 'Ảnh bộ sticker')]
    else:
        need(MIN_PACK <= len(images) <= MAX_SET, f'Bộ sticker cần từ {MIN_PACK} đến {MAX_SET} sticker.', 'too_few')
        count = len(images)
        raws = [_raw(v, SET_ITEM_BYTES, f'Sticker {i + 1}') for i, v in enumerate(images)]
    need(_GATE.acquire(blocking=False), 'Máy chủ đang xử lý một bộ sticker khác. Thử lại sau vài giây nhé.', 'busy', 503)
    try:
        if kind == 'sheet':
            out = [_decode(*raws[0], square=False, max_bytes=SHEET_MAX_BYTES, thumb=SHEET_THUMB, label='Ảnh bộ sticker')]
        else:
            out = [_decode(raw, mime, square=True, max_bytes=SET_ITEM_BYTES, thumb=THUMB, label=f'Sticker {i + 1}')
                   for i, (raw, mime) in enumerate(raws)]
    finally:
        _GATE.release()
    if kind == 'set':
        need(len({i['sha'] for i in out}) == len(out), 'Có sticker bị trùng nhau trong bộ. Mỗi sticker một hình khác nhé.', 'duplicate')
    return dict(kind=kind, count=count, ai=ai, images=out, bytes=sum(i['size'] for i in out),
                sha=hashlib.sha256(''.join(i['sha'] for i in out).encode()).hexdigest())


# ---------------------------------------------------------------- the player
def _account(store, token) -> dict | None:
    if not token:
        return None
    try:
        return accounts.status(store, token)
    except Exception:
        return None


PACK_COLS = ('p.id,p.sid,p.username,p.display,p.kind,p.count,p.ai,p.bytes,p.sha,p.created,p.updated,p.version,p.life_day,'
             'p.ip_tag,p.status,p.rank,p.reviewed_at,p.by_admin,p.note,'
             '(SELECT count(*) FROM sticker_pack_images i WHERE i.pack=p.id) AS n')


def _pack(r, admin: bool = False) -> dict:
    """A sticker_packs row (PACK_COLS) as the page and the admin site read it."""
    pid, v = int(r['id']), int(r['version'])
    url = lambda i, t='': f'/api/sticker/pack/{pid}/{i}?v={v}{t}'
    out = dict(id=pid, kind=r['kind'], count=int(r['count']), ai=bool(r['ai']), created=r['created'], updated=r['updated'],
               status=r['status'], rank=r['rank'], note=r['note'] if r['status'] == 'rejected' else '',
               images=[dict(img=url(i), thumb=url(i, '&thumb=1')) for i in range(int(r['n']))])
    if admin:
        out.update(username=r['username'], display=r['display'], life_day=int(r['life_day'] or 0), ip=r['ip_tag'] or '',
                   size=int(r['bytes']), by=r['by_admin'] or '', note=r['note'] or '', reviewed_at=r['reviewed_at'],
                   sha=r['sha'][:12], version=v)
    return out


def _my_pack(db, sid: str) -> dict | None:
    r = db.execute(f'SELECT {PACK_COLS} FROM sticker_packs p WHERE p.sid=?', (sid,)).fetchone()
    return _pack(r) if r else None


def results(store) -> list:
    """After END and once prizes were given: the ranked packs (rank, @username, name, images)."""
    if is_open():
        return []
    with store.connect() as db:
        rows = db.execute(f"SELECT {PACK_COLS} FROM sticker_packs p JOIN sticker_rewards w ON w.entry=p.id AND w.kind='prize' "
                          "AND w.status<>'revoked' WHERE p.rank IS NOT NULL AND p.status='live' ORDER BY p.rank").fetchall()
    return [dict(_pack(r), username=r['username'], display=r['display'], coins=PRIZES.get(int(r['rank']), 0)) for r in rows]


def rules() -> dict:
    return dict(end=END, min=MIN_PACK, max_set=MAX_SET, max_sheet=MAX_SHEET_COUNT, size=SIZE, item_bytes=SET_ITEM_BYTES,
                sheet_bytes=SHEET_MAX_BYTES, sheet_side=[SHEET_MIN_SIDE, SHEET_MAX_SIDE], min_days=MIN_LIFE_DAYS,
                join=JOIN_COINS, prizes=[dict(ranks='1', coins=PRIZES[1]), dict(ranks='2–3', coins=PRIZES[2]),
                                         dict(ranks='4–10', coins=PRIZES[4])], fb=FB_GROUP_URL, hashtag=HASHTAG)


def me(store, token, state_of) -> dict:
    """GET /api/sticker/me: the rules, who is signed in (never creates a session), this account's pack, how many single
    stickers it sent under the first rules, its reward, whether it may send (and why not), the results once given.
    `state_of()` reads the save (life day)."""
    t = now()
    out = dict(open=is_open(t), now=t, rules=rules(), account=None, pack=None, legacy=0, results=results(store))
    acc = _account(store, token)
    if not acc:
        out.update(can=False, why='login')
        return out
    sid = store.key(token)
    try:
        csrf = store.csrf(token)
    except Exception:
        csrf = ''
    with store.connect() as db:
        pack = _my_pack(db, sid)
        legacy = db.execute('SELECT count(*) AS n FROM sticker_entries WHERE sid=?', (sid,)).fetchone()['n']
        joined = db.execute("SELECT w.coins,w.status,g.status AS gift FROM sticker_rewards w LEFT JOIN system_gifts g ON g.id=w.gift_id "
                            "WHERE w.sid=? AND w.kind='join'", (sid,)).fetchone()
    state = state_of()
    life = int(((state or {}).get('journey') or {}).get('life_day') or 1)
    why = '' if is_open(t) else 'closed'
    if not why and life < MIN_LIFE_DAYS:
        why = 'days'
    out.update(account=dict(username=acc['username'], display=acc.get('display') or ''), csrf=csrf, life_day=life,
               pack=pack, legacy=int(legacy), can=not why, why=why,
               joined=dict(coins=int(joined['coins']), status=joined['status'], paid=joined['gift'] in ('applied', 'seen')) if joined else None)
    return out


def submit_pack(store, token: str, state: dict, data: dict, ip: str = '') -> dict:
    """POST /api/sticker/pack {kind, ai, images, count?}: this account's pack, new or replacing the one it sent before
    (until END; a rejected pack may be replaced too and is reviewed again), then the participation gift the first
    time. Returns {ok, pack, joined, replaced}."""
    need(is_open(), 'Đã hết hạn nộp bộ sticker.', 'closed', 409)
    acc = _account(store, token)
    need(acc, 'Đăng nhập tài khoản trong game rồi quay lại nộp bài nhé.', 'login', 401)
    sid = store.key(token)
    life = int(((state or {}).get('journey') or {}).get('life_day') or 1)
    need(life >= MIN_LIFE_DAYS, f'Nhân vật cần sống ở phố ít nhất {MIN_LIFE_DAYS} ngày mới nộp được (đang ở ngày {life}).', 'days', 403)
    pack = decode_pack(data)
    ip_tag = _tag('ip:' + ip)[:10] if ip else ''
    name, display = acc['username'], (acc.get('display') or '')[:40]

    def run(db):
        # One account at a time: the read and the write under the same lock (two tabs, a double tap).
        db.execute('SELECT pg_advisory_xact_lock(17823, hashtext(?))', (sid,))
        old = db.execute('SELECT id,sha,rank FROM sticker_packs WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        if old and old['sha'] == pack['sha']:
            return 'same', False
        t = now()
        if old:
            need(old['rank'] is None, 'Bộ sticker đã được xếp hạng, không thay được nữa.', 'locked', 409)
            pid = int(old['id'])
            db.execute("UPDATE sticker_packs SET username=?,display=?,kind=?,count=?,ai=?,bytes=?,sha=?,updated=?,version=version+1,"
                       "life_day=?,ip_tag=?,status='live',reviewed_at=NULL,by_admin=NULL,note='' WHERE id=?",
                       (name, display, pack['kind'], pack['count'], pack['ai'], pack['bytes'], pack['sha'], t, life, ip_tag, pid))
            db.execute('DELETE FROM sticker_pack_images WHERE pack=?', (pid,))
        else:
            pid = int(db.execute("INSERT INTO sticker_packs(sid,username,display,kind,count,ai,bytes,sha,created,updated,life_day,"
                                 "ip_tag,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'live') RETURNING id",
                                 (sid, name, display, pack['kind'], pack['count'], pack['ai'], pack['bytes'], pack['sha'], t, t,
                                  life, ip_tag)).fetchone()['id'])
        for i, img in enumerate(pack['images']):
            db.execute('INSERT INTO sticker_pack_images(pack,idx,mime,width,height,byte_size,data,thumb,sha) VALUES(?,?,?,?,?,?,?,?,?)',
                       (pid, i, img['mime'], img['width'], img['height'], img['size'], img['data'], img['thumb'], img['sha']))
        return 'ok', bool(old)
    done, replaced = store.transaction(run)
    need(done != 'same', 'Bộ sticker này bạn đã nộp rồi.', 'duplicate', 409)
    joined = _join(store, sid, name, life, ip_tag)
    with store.connect() as db:
        mine = _my_pack(db, sid)
    return dict(ok=True, pack=mine, joined=joined, replaced=replaced)


def join_id(sid: str) -> str:
    return f'stk-join-{_tag(sid)[:24]}'


def prize_id(sid: str) -> str:
    return f'stk-prize-{_tag(sid)[:24]}'


def _join(store, sid: str, username: str, life: int, ip_tag: str) -> dict | None:
    """The participation gift, once per account: the gift first (idempotent by its id), then the reward row
    (ON CONFLICT: a second tab finds it). A revoked reward is never given again."""
    with store.connect() as db:
        if db.execute("SELECT 1 FROM sticker_rewards WHERE sid=? AND kind='join'", (sid,)).fetchone():
            return None
    gid = join_id(sid)
    system_gift.grant(store, sid, JOIN_COINS, 'Quà tham gia thi sticker 🎨',
                      f'Cảm ơn bạn đã gửi bộ sticker! Phố tặng {coins_text(JOIN_COINS)} xu. Nhớ đăng bộ sticker vào nhóm Facebook để mọi người bình chọn nhé 💛',
                      gid=gid, by='sticker')
    made = store.transaction(lambda db: db.execute(
        "INSERT INTO sticker_rewards(gift_id,sid,kind,coins,username,status,created,life_day,ip_tag) "
        "VALUES(?,?,'join',?,?,'granted',?,?,?) ON CONFLICT DO NOTHING", (gid, sid, JOIN_COINS, username, now(), life, ip_tag)).rowcount)
    return dict(coins=JOIN_COINS) if made else None


def _viewer(store, token) -> tuple[str | None, bool]:
    sid, admin = None, False
    if token:
        try:
            sid = store.key(token)
        except Exception:
            sid = None
        acc = _account(store, token)
        admin = bool(acc and acc['username'] in admin_users())
    return sid, admin


def read_pack_image(store, token, pid: str, idx: str, thumb: bool) -> tuple[bytes, str]:
    """GET /api/sticker/pack/<pack>/<idx>[?thumb=1]: the author's own, any for an admin, a winner's once the results are out."""
    gone = 'Không tìm thấy sticker.'
    need(all(isinstance(x, str) and x.isdigit() and len(x) <= 12 for x in (pid, idx)), gone, 'not_found', 404)
    sid, admin = _viewer(store, token)
    col = 'thumb' if thumb else 'data'
    with store.connect() as db:
        row = db.execute(f'SELECT i.{col} AS data,i.mime,p.sid,p.status,'
                         "EXISTS(SELECT 1 FROM sticker_rewards w WHERE w.entry=p.id AND w.kind='prize' AND w.status<>'revoked') AS won "
                         'FROM sticker_pack_images i JOIN sticker_packs p ON p.id=i.pack WHERE i.pack=? AND i.idx=?',
                         (int(pid), int(idx))).fetchone()
    ok = row and (admin or (sid and row['sid'] == sid) or (row['won'] and row['status'] == 'live' and not is_open()))
    need(ok, gone, 'not_found', 404)
    return bytes(row['data']), 'image/webp' if thumb else row['mime']


def read_image(store, token, eid: str, thumb: bool) -> tuple[bytes, str]:
    """GET /api/sticker/img/<id>[?thumb=1]: a single sticker of the first rules (sticker_entries), its author or an admin."""
    need(isinstance(eid, str) and eid.isdigit() and len(eid) <= 12, 'Không tìm thấy sticker.', 'not_found', 404)
    sid, admin = _viewer(store, token)
    col = 'thumb' if thumb else 'data'
    with store.connect() as db:
        row = db.execute(f'SELECT {col} AS data,mime,sid FROM sticker_entries WHERE id=?', (int(eid),)).fetchone()
    need(row and (admin or (sid and row['sid'] == sid)), 'Không tìm thấy sticker.', 'not_found', 404)
    return bytes(row['data']), 'image/webp' if thumb else row['mime']


def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): this account's pack, single stickers and reward rows (the gifts go with
    system_gift.forget)."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM sticker_pack_images WHERE pack IN (SELECT id FROM sticker_packs WHERE sid=?)', (sid,))
        db.execute('DELETE FROM sticker_packs WHERE sid=?', (sid,))
        db.execute('DELETE FROM sticker_entries WHERE sid=?', (sid,))
        db.execute('DELETE FROM sticker_rewards WHERE sid=?', (sid,))
    store.transaction(run)


# ---------------------------------------------------------------- the operators (/admin "🎨 Thi sticker")
def admin_view(store) -> dict:
    """GET /api/admin/sticker: every pack (last sent first, images by URL), the single stickers of the first rules,
    the reward rows with their gift status, the accounts' age and the packs sharing an IP tag or an image."""
    with store.connect() as db:
        rows = db.execute(f'SELECT {PACK_COLS},a.created_at AS account_at FROM sticker_packs p LEFT JOIN accounts a ON a.sid=p.sid '
                          'ORDER BY p.updated DESC LIMIT ?', (ADMIN_LIST,)).fetchall()
        shared = {int(r['pack']) for r in db.execute(
            'SELECT DISTINCT i.pack FROM sticker_pack_images i WHERE i.sha IN (SELECT i2.sha FROM sticker_pack_images i2 '
            'JOIN sticker_packs p2 ON p2.id=i2.pack GROUP BY i2.sha HAVING count(DISTINCT p2.sid)>1)').fetchall()}
        legacy = db.execute('SELECT id,username,created FROM sticker_entries ORDER BY id DESC LIMIT ?', (ADMIN_LIST,)).fetchall()
        rewards = db.execute('SELECT w.gift_id,w.sid,w.kind,w.entry,w.rank,w.coins,w.username,w.status,w.created,w.by_admin,'
                             'w.revoked_at,w.life_day,w.ip_tag,g.status AS gift FROM sticker_rewards w '
                             'LEFT JOIN system_gifts g ON g.id=w.gift_id ORDER BY w.created DESC').fetchall()
    ips, by_sid = {}, {}
    for r in rows:
        if r['ip_tag']:
            ips.setdefault(r['ip_tag'], set()).add(r['sid'])
    for w in rewards:
        by_sid.setdefault(w['sid'], {})[w['kind']] = w
    items = []
    for r in rows:
        p = _pack(r, admin=True)
        mine = by_sid.get(r['sid'], {})
        p.update(account_at=r['account_at'] or '', same_ip=len(ips.get(r['ip_tag'], ())) if r['ip_tag'] else 0,
                 same_image=int(r['id']) in shared, join=_reward(mine.get('join')),
                 prize=_reward(mine['prize']) if 'prize' in mine and mine['prize']['entry'] == r['id'] else None)
        items.append(p)
    return dict(items=items, total=len(items), open=is_open(), now=now(), rules=rules(),
                legacy=[dict(id=int(e['id']), username=e['username'], created=e['created'], img=f"/api/sticker/img/{int(e['id'])}",
                             thumb=f"/api/sticker/img/{int(e['id'])}?thumb=1") for e in legacy],
                rewards=[dict(_reward(w), username=w['username'], kind=w['kind'], rank=w['rank'], life_day=w['life_day'], ip=w['ip_tag'] or '')
                         for w in rewards],
                awarded=any(w['kind'] == 'prize' for w in rewards), by_rank=PRIZES)


def _reward(w) -> dict | None:
    if not w:
        return None
    return dict(id=w['gift_id'], coins=int(w['coins']), status=w['status'], gift=w['gift'] or '', created=w['created'],
                by=w['by_admin'] or '', revoked_at=w['revoked_at'])


def admin_act(store, admin: str, d: dict) -> dict:
    """POST /api/admin/sticker {act, ...}:
    reject {id, note?} / restore {id}: the pack is out of (back in) the contest; a ranked pack loses its rank (not once
      its prize is given); the author may still replace a rejected pack before the deadline;
    rank {id, rank: 1..10 | null}: set or clear a pack's rank (unique; locked once its prize is given);
    award {}: after END, the prize of every ranked live pack not paid yet (idempotent);
    revoke {gift}: a sticker reward whose gift is still pending (not in the wallet yet) is withdrawn."""
    need(isinstance(d, dict), 'Thao tác không hợp lệ.', 'bad_admin')
    act, by = d.get('act'), str(admin)[:40]
    if act in ('reject', 'restore', 'rank'):
        pid = d.get('id')
        need(type(pid) is int and pid >= 1, 'Thiếu mã bộ.', 'bad_admin')
    if act in ('reject', 'restore'):
        note = d.get('note') if isinstance(d.get('note'), str) else ''
        note = re.sub(r'[\x00-\x1f\x7f]', ' ', note).strip()[:200]

        def run(db):
            row = db.execute('SELECT id,status,rank FROM sticker_packs WHERE id=? FOR UPDATE', (pid,)).fetchone()
            need(row, 'Không có bộ này.', 'not_found', 404)
            if act == 'reject':
                need(not _prized(db, pid), 'Bộ này đã được trao giải, không loại được nữa.', 'locked', 409)
                db.execute("UPDATE sticker_packs SET status='rejected',rank=NULL,reviewed_at=?,by_admin=?,note=? WHERE id=?",
                           (now(), by, note, pid))
            else:
                db.execute("UPDATE sticker_packs SET status='live',reviewed_at=?,by_admin=?,note='' WHERE id=?", (now(), by, pid))
            return dict(ok=True, status='rejected' if act == 'reject' else 'live')
        return store.transaction(run)
    if act == 'rank':
        rank = d.get('rank')
        need(rank is None or (type(rank) is int and 1 <= rank <= TOP), f'Hạng cần từ 1 đến {TOP}.', 'bad_rank')

        def run(db):
            db.execute('SELECT pg_advisory_xact_lock(17823, 0)')   # ranks change one admin act at a time
            row = db.execute('SELECT id,sid,status,rank FROM sticker_packs WHERE id=? FOR UPDATE', (pid,)).fetchone()
            need(row, 'Không có bộ này.', 'not_found', 404)
            need(not _prized(db, pid), 'Bộ này đã được trao giải: hạng đã khóa.', 'locked', 409)
            if rank is not None:
                need(row['status'] == 'live', 'Bộ đã bị loại, không xếp hạng được.', 'rejected', 409)
                other = db.execute('SELECT id FROM sticker_packs WHERE rank=? AND id<>?', (rank, pid)).fetchone()
                need(not other, f'Hạng {rank} đang là bộ #{other["id"] if other else 0}. Bỏ hạng bộ đó trước.', 'rank_taken', 409)
                need(not db.execute("SELECT 1 FROM sticker_rewards WHERE sid=? AND kind='prize'", (row['sid'],)).fetchone(),
                     'Tài khoản này đã nhận giải.', 'one_rank', 409)
            db.execute('UPDATE sticker_packs SET rank=?,reviewed_at=?,by_admin=? WHERE id=?', (rank, now(), by, pid))
            return dict(ok=True, rank=rank)
        return store.transaction(run)
    if act == 'award':
        need(not is_open(), 'Chưa hết hạn bình chọn: trao giải sau khi đóng cuộc thi.', 'not_yet', 409)
        with store.connect() as db:
            rows = db.execute("SELECT p.id,p.sid,p.rank,p.username,p.life_day,p.ip_tag FROM sticker_packs p WHERE p.rank IS NOT NULL "
                              "AND p.status='live' AND NOT EXISTS(SELECT 1 FROM sticker_rewards w WHERE w.sid=p.sid AND w.kind='prize') "
                              'ORDER BY p.rank').fetchall()
        given = []
        for r in rows:
            rank, gid = int(r['rank']), prize_id(r['sid'])
            coins = PRIZES[rank]
            system_gift.grant(store, r['sid'], coins, f'Giải hạng {rank} thi sticker 🏆',
                              f'Chúc mừng! Bộ sticker của bạn đạt hạng {rank} cuộc thi làm sticker. Phố tặng {coins_text(coins)} xu, '
                              'và bộ sticker sẽ được đưa vào chat để cả phố cùng dùng 💛', gid=gid, by=by)
            made = store.transaction(lambda db, r=r, gid=gid, coins=coins, rank=rank: db.execute(
                "INSERT INTO sticker_rewards(gift_id,sid,kind,entry,rank,coins,username,status,created,by_admin,life_day,ip_tag) "
                "VALUES(?,?,'prize',?,?,?,?,'granted',?,?,?,?) ON CONFLICT DO NOTHING",
                (gid, r['sid'], int(r['id']), rank, coins, r['username'], now(), by, r['life_day'], r['ip_tag'])).rowcount)
            if made:
                given.append(dict(id=int(r['id']), rank=rank, coins=coins, username=r['username']))
        return dict(ok=True, given=given)
    if act == 'revoke':
        gid = d.get('gift')
        need(isinstance(gid, str) and system_gift.valid_id(gid) and gid.startswith('stk-'), 'Mã quà không hợp lệ.', 'bad_admin')

        def run(db):
            w = db.execute('SELECT status FROM sticker_rewards WHERE gift_id=? FOR UPDATE', (gid,)).fetchone()
            need(w, 'Không có phần thưởng này.', 'not_found', 404)
            need(w['status'] != 'revoked', 'Phần thưởng này đã thu hồi rồi.', 'revoked', 409)
            # a load paying this very gift at this moment may still pay it (system_gift.on_load reads 'pending' first): rare,
            # and the row then stays 'revoked' for the record
            n = db.execute("UPDATE system_gifts SET status='revoked' WHERE id=? AND status='pending'", (gid,)).rowcount
            need(n == 1, 'Quà đã vào ví người chơi, không thu hồi được nữa.', 'paid', 409)
            db.execute("UPDATE sticker_rewards SET status='revoked',revoked_at=?,by_admin=? WHERE gift_id=?", (now(), by, gid))
            return dict(ok=True, status='revoked')
        return store.transaction(run)
    raise StickerError('Thao tác không hợp lệ.', 'bad_admin')


def _prized(db, pid: int) -> bool:
    return bool(db.execute("SELECT 1 FROM sticker_rewards WHERE entry=? AND kind='prize'", (pid,)).fetchone())


# ---------------------------------------------------------------- HTTP (server.py hands these routes over)
PACK_IMG = re.compile(r'^/api/sticker/pack/(\d{1,12})/(\d{1,3})$')


def http_get(h, route: str, query: str) -> bool:
    """GET /api/sticker/me, /api/sticker/pack/<id>/<idx>, /api/sticker/img/<id>, /api/admin/sticker. True when ours."""
    from urllib.parse import parse_qs
    try:
        if route == '/api/sticker/me':
            if not h.server.rate_limit('stk-me:' + h.client_ip(), 60):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            token = h.token()

            def state_of():
                try:
                    return h.server.store.read(token)[0]
                except Exception:
                    return None
            h.json(200, me(h.server.store, token, state_of))
            return True
        m = PACK_IMG.match(route)
        if m or route.startswith('/api/sticker/img/'):
            if not h.server.rate_limit('stk-img:' + h.client_ip(), 600):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            thumb = (parse_qs(query).get('thumb') or [''])[0] == '1'
            if m:
                data, mime = read_pack_image(h.server.store, h.token(), m.group(1), m.group(2), thumb)
            else:
                data, mime = read_image(h.server.store, h.token(), route[len('/api/sticker/img/'):], thumb)
            h.respond(200, data, mime, extra={'Cross-Origin-Resource-Policy': 'same-origin'}, cache='private, no-store')
            return True
        if route == '/api/admin/sticker':
            try:
                token, _, _, _ = h.guarded(light=True)
            except PermissionError as e:
                h.error(403, str(e), 'forbidden')
                return True
            h.require_admin(token)
            h.json(200, admin_view(h.server.store))
            return True
    except StickerError as e:
        h.error(e.status, e.message, e.code)
        return True
    return False


def http_post(h, route: str, token: str, state: dict, data: dict) -> bool:
    """POST /api/sticker/pack, /api/admin/sticker (the session and its CSRF already checked). True when ours.
    /api/sticker/submit (one sticker, the first rules) answers 410: an open tab of the old page says to reload."""
    try:
        if route == '/api/sticker/submit':
            h.error(410, 'Cuộc thi đã đổi sang nộp cả bộ sticker (từ 12 sticker). Tải lại trang nhé.', 'pack_now')
            return True
        if route == '/api/sticker/pack':
            if not h.server.rate_limit('stk-pack:' + token, 6):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            h.json(200, submit_pack(h.server.store, token, state, data, h.client_ip()))
            return True
        if route == '/api/admin/sticker':
            if not h.server.rate_limit('stk-admin:' + token, 60):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            h.require_admin(token)
            who = (accounts.status(h.server.store, token) or {}).get('username') or 'admin'
            h.json(200, admin_act(h.server.store, who, data))
            return True
    except StickerError as e:
        h.error(e.status, e.message, e.code)
        return True
    except system_gift.GiftError as e:
        h.error(e.status, e.message, e.code)
        return True
    return False
