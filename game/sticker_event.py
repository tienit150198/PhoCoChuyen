"""🎨 Thi làm sticker (owner 16/10/2026): players make a sticker on /sticker (public/sticker.html, public/js/sticker/),
download it, post it in the game's Facebook group; the reactions there decide the winners. The sticker also comes
here ("Nộp bài") so the operators have the original, its author and its rank (the top 10 become chat stickers later).

Rules (owner, verbatim in docs/the report): "tạo sticker chủ đề bất kì … ai được vote nhiều hơn thì sẽ được thắng,
tham gia thì tặng 200k/1 người, top 1 3m, top 2–3 1.5m, top 10 500k … có cả username … top 10 sẽ có sticker sử dụng
trong chat".
* Only a signed-in account (not a guest) whose character lived MIN_LIFE_DAYS days submits; the page stamps the
  account's @username on the image (the client draws it; the operators see every image and can reject one without it).
* At most MAX_ENTRIES stickers per account, each a single-frame PNG or WebP of exactly SIZE x SIZE pixels, at most
  MAX_BYTES; the server checks the magic bytes, decodes it with Pillow and keeps only re-encoded pixels (no metadata)
  plus a small thumbnail for the operator list. Submissions are private: the author and the admins see them; the
  winners' images become public once the prizes are given (the results on the page).
* The first accepted sticker of an account queues JOIN_COINS through the system gift path (game/system_gift.py: paid
  at the next load, once, whatever the retries). One reward row per account and kind (sticker_rewards), with the
  life day and a short IP tag, for the operators to review (clone rings); a reward still pending can be revoked.
* Admins (ADMIN_USERS, /admin "🎨 Sticker") reject / restore entries, set ranks 1..10 by hand from the Facebook votes
  (one rank per account, a rank on one entry only) and press "Trao giải" after END: PRIZES[rank] per ranked entry,
  once (sticker_rewards), and the rank is locked from then on.

Tables (game/pg_schema.py, SCHEMA_VERSION 49): sticker_entries, sticker_rewards. New tables only, no FK, no save key:
an older release never reads them. Account deletion ("Xóa dữ liệu") removes this account's entries and reward rows.
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
END = 1793120399                    # 27/10/2026 23:59:59 (VN): last moment to submit; the owner may move it
MAX_ENTRIES = 3                     # stickers per account
SIZE = 512                          # exactly SIZE x SIZE pixels
MAX_BYTES = 400 * 1024              # one image, as uploaded and as stored
MAX_BODY = 4 * ((MAX_BYTES + 2) // 3) + 4096   # the JSON body of a submission (base64 + a little)
MIN_LIFE_DAYS = 3                   # journey.life_day of the character, to submit (anti clone-ring)
JOIN_COINS = 200_000
PRIZES = {1: 3_000_000, 2: 1_500_000, 3: 1_500_000, **{r: 500_000 for r in range(4, 11)}}
TOP = 10
FB_GROUP_URL = ''                   # the game's Facebook group (owner to provide); the page shows the button once set
HASHTAG = '#StickerMotNgayLamNghe'
THUMB = 160
MIMES = {'image/png': 'PNG', 'image/webp': 'WEBP'}
ADMIN_LIST = 500
_GATE = threading.BoundedSemaphore(1)   # one decode at a time per worker; never queue large bodies


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


# ---------------------------------------------------------------- the image
def decode(value) -> dict:
    """data:image/png|webp;base64,… → {data, thumb, mime, width, height, size, sha}, or StickerError."""
    invalid = 'Ảnh sticker không hợp lệ. Hãy làm lại rồi nộp nhé.'
    need(isinstance(value, str), 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    need(len(value) <= MAX_BODY, 'Ảnh quá lớn: tối đa 400 KB.', 'too_large', 413)
    header, sep, encoded = value.partition(',')
    mime = next((m for m in MIMES if header == f'data:{m};base64'), None)
    need(mime and sep and encoded, 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise StickerError(invalid) from None
    need(0 < len(raw) <= MAX_BYTES, 'Ảnh quá lớn: tối đa 400 KB.', 'too_large', 413)
    magic = raw.startswith(b'\x89PNG\r\n\x1a\n') if mime == 'image/png' else raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'
    need(magic, 'Chỉ nhận ảnh PNG hoặc WebP.', 'bad_type')
    from PIL import Image, UnidentifiedImageError
    need(_GATE.acquire(blocking=False), 'Máy chủ đang xử lý một sticker khác. Thử lại sau vài giây nhé.', 'busy', 503)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=[MIMES[mime]]) as im:
                need(im.format == MIMES[mime] and getattr(im, 'n_frames', 1) == 1, 'Sticker cần là ảnh tĩnh (không động).', 'bad_type')
                need(im.size == (SIZE, SIZE), f'Sticker cần đúng {SIZE}×{SIZE} điểm ảnh.', 'bad_size')
                im.verify()
            with Image.open(io.BytesIO(raw), formats=[MIMES[mime]]) as im:
                im.load()
                pic = im.convert('RGBA')
        need(pic.getchannel('A').getbbox() is not None, 'Sticker đang trống. Vẽ hay thêm gì đó nhé.', 'empty')
        out = io.BytesIO()
        if mime == 'image/png':   # pixels only: no text chunks, profiles or trailing bytes
            pic.save(out, 'PNG', optimize=True)
        else:
            pic.save(out, 'WEBP', lossless=True, method=4)
            if out.tell() > MAX_BYTES:
                out = io.BytesIO()
                pic.save(out, 'WEBP', quality=92, method=4)
        data = out.getvalue()
        need(len(data) <= MAX_BYTES, 'Ảnh sau khi xử lý vượt 400 KB. Bớt chi tiết hay ảnh chụp một chút nhé.', 'too_large', 413)
        small = pic.copy()
        small.thumbnail((THUMB, THUMB))
        tb = io.BytesIO()
        small.save(tb, 'WEBP', quality=80)
    except StickerError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise StickerError(invalid) from None
    finally:
        _GATE.release()
    return dict(data=data, thumb=tb.getvalue(), mime=mime, width=SIZE, height=SIZE, size=len(data),
                sha=hashlib.sha256(data).hexdigest())


# ---------------------------------------------------------------- the player
def _account(store, token) -> dict | None:
    if not token:
        return None
    try:
        return accounts.status(store, token)
    except Exception:
        return None


def _entry(r, admin: bool = False) -> dict:
    out = dict(id=int(r['id']), created=r['created'], status=r['status'], rank=r['rank'],
               img=f"/api/sticker/img/{int(r['id'])}", thumb=f"/api/sticker/img/{int(r['id'])}?thumb=1")
    if admin:
        out.update(username=r['username'], display=r['display'], life_day=int(r['life_day'] or 0), ip=r['ip_tag'] or '',
                   size=int(r['byte_size']), mime=r['mime'], by=r['by_admin'] or '', note=r['note'] or '',
                   reviewed_at=r['reviewed_at'], sha=r['sha'][:12])
    return out


def results(store) -> list:
    """After END and once prizes were given: the ranked stickers (rank, @username, name, image)."""
    if is_open():
        return []
    with store.connect() as db:
        rows = db.execute("SELECT e.id,e.rank,e.username,e.display FROM sticker_entries e JOIN sticker_rewards w "
                          "ON w.entry=e.id AND w.kind='prize' AND w.status<>'revoked' "
                          "WHERE e.rank IS NOT NULL AND e.status='live' ORDER BY e.rank").fetchall()
    return [dict(rank=int(r['rank']), username=r['username'], display=r['display'], coins=PRIZES.get(int(r['rank']), 0),
                 img=f"/api/sticker/img/{int(r['id'])}") for r in rows]


def rules() -> dict:
    return dict(end=END, max=MAX_ENTRIES, size=SIZE, max_bytes=MAX_BYTES, min_days=MIN_LIFE_DAYS, join=JOIN_COINS,
                prizes=[dict(ranks='1', coins=PRIZES[1]), dict(ranks='2–3', coins=PRIZES[2]), dict(ranks='4–10', coins=PRIZES[4])],
                fb=FB_GROUP_URL, hashtag=HASHTAG)


def me(store, token, state_of) -> dict:
    """GET /api/sticker/me: the rules, who is signed in (never creates a session), this account's entries and
    reward, whether it may submit (and why not), the results once given. `state_of()` reads the save (life day)."""
    t = now()
    out = dict(open=is_open(t), now=t, rules=rules(), account=None, entries=[], results=results(store))
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
        rows = db.execute('SELECT id,created,status,rank FROM sticker_entries WHERE sid=? ORDER BY id', (sid,)).fetchall()
        joined = db.execute("SELECT w.coins,w.status,g.status AS gift FROM sticker_rewards w LEFT JOIN system_gifts g ON g.id=w.gift_id "
                            "WHERE w.sid=? AND w.kind='join'", (sid,)).fetchone()
    state = state_of()
    life = int(((state or {}).get('journey') or {}).get('life_day') or 1)
    why = '' if is_open(t) else 'closed'
    if not why and len(rows) >= MAX_ENTRIES:
        why = 'full'
    if not why and life < MIN_LIFE_DAYS:
        why = 'days'
    out.update(account=dict(username=acc['username'], display=acc.get('display') or ''), csrf=csrf, life_day=life,
               entries=[_entry(r) for r in rows], can=not why, why=why,
               joined=dict(coins=int(joined['coins']), status=joined['status'], paid=joined['gift'] in ('applied', 'seen')) if joined else None)
    return out


def submit(store, token: str, state: dict, data: dict, ip: str = '') -> dict:
    """POST /api/sticker/submit {image}: one more sticker for this account (checks above), then the participation
    gift the first time. Returns {entry, joined, entries}."""
    need(isinstance(data, dict) and set(data) <= {'image', 'rid'}, 'Dữ liệu không hợp lệ.', 'bad_request')
    need(is_open(), 'Đã hết hạn nộp sticker.', 'closed', 409)
    acc = _account(store, token)
    need(acc, 'Đăng nhập tài khoản trong game rồi quay lại nộp bài nhé.', 'login', 401)
    sid = store.key(token)
    j = (state or {}).get('journey') or {}
    life = int(j.get('life_day') or 1)
    need(life >= MIN_LIFE_DAYS, f'Nhân vật cần sống ở phố ít nhất {MIN_LIFE_DAYS} ngày mới nộp được (đang ở ngày {life}).', 'days', 403)
    with store.connect() as db:
        n = db.execute('SELECT count(*) AS n FROM sticker_entries WHERE sid=?', (sid,)).fetchone()['n']
    need(n < MAX_ENTRIES, f'Mỗi tài khoản nộp tối đa {MAX_ENTRIES} sticker.', 'full', 409)
    img = decode(data.get('image'))
    ip_tag = _tag('ip:' + ip)[:10] if ip else ''

    def run(db):
        # One account at a time: the count and the insert under the same lock (two tabs, a double tap).
        db.execute('SELECT pg_advisory_xact_lock(17823, hashtext(?))', (sid,))
        if db.execute('SELECT count(*) AS n FROM sticker_entries WHERE sid=?', (sid,)).fetchone()['n'] >= MAX_ENTRIES:
            return None
        if db.execute('SELECT 1 FROM sticker_entries WHERE sid=? AND sha=?', (sid, img['sha'])).fetchone():
            return 'same'
        return db.execute('INSERT INTO sticker_entries(sid,username,display,mime,width,height,byte_size,data,thumb,sha,created,'
                          "life_day,ip_tag,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'live') RETURNING id",
                          (sid, acc['username'], (acc.get('display') or '')[:40], img['mime'], img['width'], img['height'],
                           img['size'], img['data'], img['thumb'], img['sha'], now(), life, ip_tag)).fetchone()['id']
    eid = store.transaction(run)
    need(eid is not None, f'Mỗi tài khoản nộp tối đa {MAX_ENTRIES} sticker.', 'full', 409)
    need(eid != 'same', 'Sticker này bạn đã nộp rồi.', 'duplicate', 409)
    joined = _join(store, sid, acc['username'], life, ip_tag)
    with store.connect() as db:
        rows = db.execute('SELECT id,created,status,rank FROM sticker_entries WHERE sid=? ORDER BY id', (sid,)).fetchall()
    return dict(ok=True, entry=int(eid), joined=joined, entries=[_entry(r) for r in rows])


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
                      f'Cảm ơn bạn đã gửi sticker! Phố tặng {coins_text(JOIN_COINS)} xu. Nhớ đăng sticker vào nhóm Facebook để mọi người bình chọn nhé 💛',
                      gid=gid, by='sticker')
    made = store.transaction(lambda db: db.execute(
        "INSERT INTO sticker_rewards(gift_id,sid,kind,coins,username,status,created,life_day,ip_tag) "
        "VALUES(?,?,'join',?,?,'granted',?,?,?) ON CONFLICT DO NOTHING", (gid, sid, JOIN_COINS, username, now(), life, ip_tag)).rowcount)
    return dict(coins=JOIN_COINS) if made else None


def read_image(store, token, eid: str, thumb: bool) -> tuple[bytes, str]:
    """GET /api/sticker/img/<id>[?thumb=1]: the author's own, any for an admin, a winner's once the results are out."""
    need(isinstance(eid, str) and eid.isdigit() and len(eid) <= 12, 'Không tìm thấy sticker.', 'not_found', 404)
    sid = None
    admin = False
    acc = _account(store, token)
    if token:
        try:
            sid = store.key(token)
        except Exception:
            sid = None
        admin = bool(acc and acc['username'] in admin_users())
    col = 'thumb' if thumb else 'data'
    with store.connect() as db:
        row = db.execute(f'SELECT e.{col} AS data,e.mime,e.sid,e.rank,e.status,'
                         "EXISTS(SELECT 1 FROM sticker_rewards w WHERE w.entry=e.id AND w.kind='prize' AND w.status<>'revoked') AS won "
                         'FROM sticker_entries e WHERE e.id=?', (int(eid),)).fetchone()
    ok = row and (admin or (sid and row['sid'] == sid) or (row['won'] and row['status'] == 'live' and not is_open()))
    need(ok, 'Không tìm thấy sticker.', 'not_found', 404)
    return bytes(row['data']), 'image/webp' if thumb else row['mime']


def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): this account's stickers and reward rows (the gifts go with system_gift.forget)."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM sticker_entries WHERE sid=?', (sid,))
        db.execute('DELETE FROM sticker_rewards WHERE sid=?', (sid,))
    store.transaction(run)


# ---------------------------------------------------------------- the operators (/admin "🎨 Sticker")
def admin_view(store) -> dict:
    """GET /api/admin/sticker: every entry (newest first, thumbnails by URL), the reward rows with their gift status,
    the accounts' age and how many entries share an IP tag or an image."""
    with store.connect() as db:
        rows = db.execute('SELECT e.id,e.sid,e.username,e.display,e.mime,e.byte_size,e.sha,e.created,e.life_day,e.ip_tag,e.status,'
                          'e.rank,e.reviewed_at,e.by_admin,e.note,a.created_at AS account_at FROM sticker_entries e '
                          'LEFT JOIN accounts a ON a.sid=e.sid ORDER BY e.id DESC LIMIT ?', (ADMIN_LIST,)).fetchall()
        rewards = db.execute('SELECT w.gift_id,w.sid,w.kind,w.entry,w.rank,w.coins,w.username,w.status,w.created,w.by_admin,'
                             'w.revoked_at,w.life_day,w.ip_tag,g.status AS gift FROM sticker_rewards w '
                             'LEFT JOIN system_gifts g ON g.id=w.gift_id ORDER BY w.created DESC').fetchall()
        total = db.execute('SELECT count(*) AS n, count(DISTINCT sid) AS people FROM sticker_entries').fetchone()
    ips, shas = {}, {}
    for r in rows:
        if r['ip_tag']:
            ips.setdefault(r['ip_tag'], set()).add(r['sid'])
        shas.setdefault(r['sha'], set()).add(r['sid'])
    by_sid = {}
    for w in rewards:
        by_sid.setdefault(w['sid'], {})[w['kind']] = w
    items = []
    for r in rows:
        e = _entry(r, admin=True)
        mine = by_sid.get(r['sid'], {})
        e.update(account_at=r['account_at'] or '', same_ip=len(ips.get(r['ip_tag'], ())) if r['ip_tag'] else 0,
                 same_image=len(shas.get(r['sha'], ())),
                 join=_reward(mine.get('join')), prize=_reward(mine['prize']) if 'prize' in mine and mine['prize']['entry'] == r['id'] else None)
        items.append(e)
    return dict(items=items, total=int(total['n']), people=int(total['people']), open=is_open(), now=now(), rules=rules(),
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
    reject {id, note?} / restore {id}: the entry is out of (back in) the contest; a ranked entry loses its rank
      (not once its prize is given);
    rank {id, rank: 1..10 | null}: set or clear a rank (unique; one per account; locked once its prize is given);
    award {}: after END, the prize of every ranked live entry not paid yet (idempotent);
    revoke {gift}: a sticker reward whose gift is still pending (not in the wallet yet) is withdrawn."""
    need(isinstance(d, dict), 'Thao tác không hợp lệ.', 'bad_admin')
    act, by = d.get('act'), str(admin)[:40]
    if act in ('reject', 'restore', 'rank'):
        eid = d.get('id')
        need(type(eid) is int and eid >= 1, 'Thiếu mã bài.', 'bad_admin')
    if act in ('reject', 'restore'):
        note = d.get('note') if isinstance(d.get('note'), str) else ''
        note = re.sub(r'[\x00-\x1f\x7f]', ' ', note).strip()[:200]

        def run(db):
            row = db.execute('SELECT id,status,rank FROM sticker_entries WHERE id=? FOR UPDATE', (eid,)).fetchone()
            need(row, 'Không có bài này.', 'not_found', 404)
            if act == 'reject':
                need(not _prized(db, eid), 'Bài này đã được trao giải, không loại được nữa.', 'locked', 409)
                db.execute("UPDATE sticker_entries SET status='rejected',rank=NULL,reviewed_at=?,by_admin=?,note=? WHERE id=?",
                           (now(), by, note, eid))
            else:
                db.execute("UPDATE sticker_entries SET status='live',reviewed_at=?,by_admin=?,note='' WHERE id=?", (now(), by, eid))
            return dict(ok=True, status='rejected' if act == 'reject' else 'live')
        return store.transaction(run)
    if act == 'rank':
        rank = d.get('rank')
        need(rank is None or (type(rank) is int and 1 <= rank <= TOP), f'Hạng cần từ 1 đến {TOP}.', 'bad_rank')

        def run(db):
            db.execute('SELECT pg_advisory_xact_lock(17823, 0)')   # ranks change one admin act at a time
            row = db.execute('SELECT id,sid,status,rank FROM sticker_entries WHERE id=?', (eid,)).fetchone()
            need(row, 'Không có bài này.', 'not_found', 404)
            need(not _prized(db, eid), 'Bài này đã được trao giải: hạng đã khóa.', 'locked', 409)
            if rank is not None:
                need(row['status'] == 'live', 'Bài đã bị loại, không xếp hạng được.', 'rejected', 409)
                other = db.execute('SELECT id FROM sticker_entries WHERE rank=? AND id<>?', (rank, eid)).fetchone()
                need(not other, f'Hạng {rank} đang là bài #{other["id"] if other else 0}. Bỏ hạng bài đó trước.', 'rank_taken', 409)
                same = db.execute('SELECT id,rank FROM sticker_entries WHERE sid=? AND rank IS NOT NULL AND id<>?', (row['sid'], eid)).fetchone()
                need(not same, f'Tài khoản này đã có hạng {same["rank"] if same else 0} (bài #{same["id"] if same else 0}). Mỗi người một giải.', 'one_rank', 409)
                need(not db.execute("SELECT 1 FROM sticker_rewards WHERE sid=? AND kind='prize'", (row['sid'],)).fetchone(),
                     'Tài khoản này đã nhận giải.', 'one_rank', 409)
            db.execute('UPDATE sticker_entries SET rank=?,reviewed_at=?,by_admin=? WHERE id=?', (rank, now(), by, eid))
            return dict(ok=True, rank=rank)
        return store.transaction(run)
    if act == 'award':
        need(not is_open(), 'Chưa hết hạn bình chọn: trao giải sau khi đóng cuộc thi.', 'not_yet', 409)
        with store.connect() as db:
            rows = db.execute("SELECT e.id,e.sid,e.rank,e.username,e.life_day,e.ip_tag FROM sticker_entries e WHERE e.rank IS NOT NULL "
                              "AND e.status='live' AND NOT EXISTS(SELECT 1 FROM sticker_rewards w WHERE w.sid=e.sid AND w.kind='prize') "
                              'ORDER BY e.rank').fetchall()
        given = []
        for r in rows:
            rank, gid = int(r['rank']), prize_id(r['sid'])
            coins = PRIZES[rank]
            system_gift.grant(store, r['sid'], coins, f'Giải hạng {rank} thi sticker 🏆',
                              f'Chúc mừng! Sticker của bạn đạt hạng {rank} cuộc thi làm sticker. Phố tặng {coins_text(coins)} xu, '
                              'và sticker sẽ được đưa vào chat để cả phố cùng dùng 💛', gid=gid, by=by)
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


def _prized(db, eid: int) -> bool:
    return bool(db.execute("SELECT 1 FROM sticker_rewards WHERE entry=? AND kind='prize'", (eid,)).fetchone())


# ---------------------------------------------------------------- HTTP (server.py hands these routes over)
def http_get(h, route: str, query: str) -> bool:
    """GET /api/sticker/me, /api/sticker/img/<id>, /api/admin/sticker. True when the route was ours."""
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
        if route.startswith('/api/sticker/img/'):
            if not h.server.rate_limit('stk-img:' + h.client_ip(), 240):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            thumb = (parse_qs(query).get('thumb') or [''])[0] == '1'
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
    """POST /api/sticker/submit, /api/admin/sticker (the session and its CSRF already checked). True when ours."""
    try:
        if route == '/api/sticker/submit':
            if not h.server.rate_limit('stk-sub:' + token, 6):
                h.error(429, 'Chậm lại một chút nhé.', 'rate_limited')
                return True
            h.json(200, submit(h.server.store, token, state, data, h.client_ip()))
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
