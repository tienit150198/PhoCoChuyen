"""Web Push (RFC 8030 + VAPID RFC 8292), standard library only.

Pushes carry no payload, so no message encryption is needed: the service
worker receives an empty "tickle" and fetches `/api/push/pending` with the
player's own cookie to learn what to show. VAPID needs ES256 signatures, done
here with a small P-256 implementation (private key never leaves the server).
Endpoints are limited to known browser push services to avoid SSRF.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

# ---------------------------------------------------------------- P-256 / ES256
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
A = P - 3
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
     0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)


def _add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    (x1, y1), (x2, y2) = p1, p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        m = (3 * x1 * x1 + A) * pow(2 * y1, -1, P) % P
    else:
        m = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (m * m - x1 - x2) % P
    return x3, (m * (x1 - x3) - y1) % P


def _mul(k: int, point=G):
    result, addend = None, point
    while k:
        if k & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        k >>= 1
    return result


def on_curve(point) -> bool:
    x, y = point
    return (y * y - (x * x * x + A * x + B)) % P == 0


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def public_bytes(d: int) -> bytes:
    x, y = _mul(d)
    return b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')


def sign(d: int, message: bytes) -> bytes:
    e = int.from_bytes(hashlib.sha256(message).digest(), 'big')
    while True:
        k = secrets.randbelow(N - 1) + 1
        r = _mul(k)[0] % N
        if not r:
            continue
        s = pow(k, -1, N) * (e + r * d) % N
        if s:
            return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')


def verify(pub: bytes, message: bytes, sig: bytes) -> bool:
    if len(pub) != 65 or pub[0] != 4 or len(sig) != 64:
        return False
    q = (int.from_bytes(pub[1:33], 'big'), int.from_bytes(pub[33:], 'big'))
    if not on_curve(q):
        return False
    r, s = int.from_bytes(sig[:32], 'big'), int.from_bytes(sig[32:], 'big')
    if not (0 < r < N and 0 < s < N):
        return False
    e = int.from_bytes(hashlib.sha256(message).digest(), 'big')
    w = pow(s, -1, N)
    point = _add(_mul(e * w % N), _mul(r * w % N, q))
    return point is not None and point[0] % N == r


def vapid_header(d: int, endpoint: str, subject: str, ttl: int = 12 * 3600) -> str:
    u = urlsplit(endpoint)
    header = b64u(json.dumps(dict(typ='JWT', alg='ES256'), separators=(',', ':')).encode())
    claims = b64u(json.dumps(dict(aud=f'{u.scheme}://{u.netloc}', exp=int(time.time()) + ttl, sub=subject), separators=(',', ':')).encode())
    signing = f'{header}.{claims}'.encode()
    return f'vapid t={header}.{claims}.{b64u(sign(d, signing))}, k={b64u(public_bytes(d))}'


# ---------------------------------------------------------------- keys & config
_keys = {}
_lock = threading.Lock()
ALLOWED_PUSH_HOSTS = ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'push.services.mozilla.com',
                      'notify.windows.com', 'push.apple.com', 'web.push.apple.com')


_key_dir = {'path': Path(__file__).resolve().parents[1] / 'storage'}


def _key_file() -> Path:
    return Path(os.environ.get('VAPID_KEY_FILE') or _key_dir['path'] / 'vapid.json')


def keys() -> dict | None:
    """VAPID private key from VAPID_PRIVATE_KEY (base64url, 32 bytes) or a
    generated file next to the database. None when push is disabled."""
    if os.environ.get('PUSH_DISABLED', '').lower() in ('1', 'true', 'yes'):
        return None
    with _lock:
        if 'd' in _keys:
            return _keys
        raw = os.environ.get('VAPID_PRIVATE_KEY', '').strip()
        d = None
        if raw:
            d = int.from_bytes(unb64u(raw), 'big')
        else:
            path = _key_file()
            try:
                if path.exists():
                    d = int(json.loads(path.read_text(encoding='utf-8'))['d'], 16)
                else:
                    d = secrets.randbelow(N - 1) + 1
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(dict(d=format(d, 'x'))), encoding='utf-8')
                    try:
                        os.chmod(path, 0o600)
                    except OSError:
                        pass
            except (OSError, ValueError, KeyError):
                return None
        if not d or not 0 < d < N:
            return None
        _keys.update(d=d, public=b64u(public_bytes(d)))
        return _keys


def subject() -> str:
    return os.environ.get('VAPID_SUBJECT', 'mailto:trachanhtv.works@gmail.com')


def public_config() -> dict:
    k = keys()
    return dict(enabled=bool(k), key=k['public'] if k else None)


SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs (
  endpoint TEXT PRIMARY KEY, sid TEXT NOT NULL, created REAL NOT NULL, last_ok REAL, fails INTEGER NOT NULL DEFAULT 0,
  prefs TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS push_subs_sid ON push_subs(sid);
CREATE TABLE IF NOT EXISTS push_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, url TEXT NOT NULL,
  at REAL NOT NULL, sent INTEGER NOT NULL DEFAULT 0, shown INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS push_queue_sid ON push_queue(sid, id);
CREATE TABLE IF NOT EXISTS push_daily (sid TEXT PRIMARY KEY, day TEXT NOT NULL);
"""
TITLES = dict(visit='Có khách ghé quán 👀', review='Đánh giá mới từ Phố nghề ⭐', reply='Có người trả lời bạn 💬', gift='Bạn nhận được quà 🎁',
              sale='Hàng đã bán ở chợ 🧺', comment='Bình luận mới 💬', daily='Quán đang chờ bạn mở cửa ☀️', community='Mục tiêu cả phố 🎉', chat='Tin nhắn mới 💬',
              wedding='Sắp tới giờ cưới 💍')
DEFAULT_PREFS = dict(social=True, daily=False, hour=19, tz=420)


def ensure(store) -> None:
    _key_dir['path'] = Path(store.path).resolve().parent
    if getattr(store, 'pg', None):
        return  # PostgreSQL: created with every other table (game/pg_schema.py)
    with store.connect() as db:
        db.executescript(SCHEMA)


def _valid_endpoint(endpoint) -> bool:
    if not isinstance(endpoint, str) or len(endpoint) > 1000:
        return False
    u = urlsplit(endpoint)
    host = (u.hostname or '').lower()
    return u.scheme == 'https' and not u.username and not u.password and u.port in (None, 443) and any(host == h or host.endswith('.' + h) for h in ALLOWED_PUSH_HOSTS)


def _prefs(data) -> dict:
    p = dict(DEFAULT_PREFS)
    if isinstance(data, dict):
        for k in ('social', 'daily'):
            if type(data.get(k)) is bool:
                p[k] = data[k]
        if type(data.get('hour')) is int and 6 <= data['hour'] <= 22:
            p['hour'] = data['hour']
        if type(data.get('tz')) is int and -720 <= data['tz'] <= 840:
            p['tz'] = data['tz']
    return p


def subscribe(store, token: str, data: dict) -> dict:
    from .social import need
    need(keys(), 'Máy chủ chưa bật thông báo đẩy.', 'push_disabled')
    sub = data.get('subscription') or {}
    endpoint = sub.get('endpoint') if isinstance(sub, dict) else None
    need(_valid_endpoint(endpoint), 'Trình duyệt này dùng dịch vụ thông báo chưa được hỗ trợ.', 'push_endpoint')
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT COUNT(*) FROM push_subs WHERE sid=? AND endpoint<>?', (sid, endpoint)).fetchone()[0] < 5, 'Tối đa 5 thiết bị nhận thông báo.')
        db.execute('INSERT INTO push_subs(endpoint,sid,created,prefs) VALUES(?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET sid=excluded.sid, prefs=excluded.prefs, fails=0',
                   (endpoint, sid, time.time(), json.dumps(_prefs(data.get('prefs')))))
    return dict(message='Đã bật thông báo trên thiết bị này.', enabled=True)


def unsubscribe(store, token: str, data: dict) -> dict:
    endpoint = (data.get('subscription') or {}).get('endpoint') if isinstance(data.get('subscription'), dict) else data.get('endpoint')
    with store.connect() as db:
        if isinstance(endpoint, str):
            db.execute('DELETE FROM push_subs WHERE endpoint=? AND sid=?', (endpoint, store.key(token)))
        else:
            db.execute('DELETE FROM push_subs WHERE sid=?', (store.key(token),))
    return dict(message='Đã tắt thông báo.', enabled=False)


def forget(store, token: str) -> None:
    sid = store.key(token)
    with store.connect() as db:
        for table in ('push_subs', 'push_queue', 'push_daily'):
            db.execute(f'DELETE FROM {table} WHERE sid=?', (sid,))


def queue(db, sid: str, kind: str, body: str, url: str = '/') -> None:
    """Called inside another transaction (social notify). Only queues for
    players who have a subscription with the matching preference."""
    subs = db.execute('SELECT prefs FROM push_subs WHERE sid=?', (sid,)).fetchall()
    if not subs:
        return
    key = 'daily' if kind == 'daily' else 'social'
    if not any(json.loads(r['prefs'] or '{}').get(key, DEFAULT_PREFS[key]) for r in subs):
        return
    # Collapse bursts: at most 6 unsent notifications per player.
    if db.execute('SELECT COUNT(*) FROM push_queue WHERE sid=? AND sent=0', (sid,)).fetchone()[0] >= 6:
        return
    db.execute('INSERT INTO push_queue(sid,kind,body,url,at) VALUES(?,?,?,?,?)', (sid, kind, body[:200], url[:200], time.time()))


def pending(store, token: str) -> dict:
    sid = store.key(token)
    with store.connect() as db:
        rows = db.execute('SELECT * FROM push_queue WHERE sid=? AND shown=0 ORDER BY id DESC LIMIT 5', (sid,)).fetchall()
        db.execute('UPDATE push_queue SET shown=1 WHERE sid=?', (sid,))
    items = [dict(id=r['id'], title=TITLES.get(r['kind'], 'Phố Có Chuyện'), body=r['body'], url=r['url'], tag=r['kind']) for r in rows]
    return dict(items=items)


def _send(d: int, endpoint: str) -> int:
    req = urllib.request.Request(endpoint, data=b'', method='POST', headers={
        'TTL': '86400', 'Urgency': 'normal', 'Content-Length': '0', 'Authorization': vapid_header(d, endpoint, subject())})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def _daily(db) -> None:
    """Queue opt-in daily reminders at the player's chosen local hour."""
    t = time.time()
    for r in db.execute('SELECT sid, prefs FROM push_subs').fetchall():
        p = _prefs(json.loads(r['prefs'] or '{}'))
        if not p['daily']:
            continue
        local = time.gmtime(t + p['tz'] * 60)
        if local.tm_hour != p['hour']:
            continue
        day = time.strftime('%Y-%m-%d', local)
        done = db.execute('SELECT day FROM push_daily WHERE sid=?', (r['sid'],)).fetchone()
        if done and done['day'] == day:
            continue
        db.execute('INSERT INTO push_daily(sid,day) VALUES(?,?) ON CONFLICT(sid) DO UPDATE SET day=excluded.day', (r['sid'], day))
        queue(db, r['sid'], 'daily', 'Khách quen đang chờ. Mở ca hôm nay nhé!', '/')


def deliver_due(store) -> int:
    k = keys()
    if not k:
        return 0
    with store.connect() as db:
        _daily(db)
        db.execute('DELETE FROM push_queue WHERE at<?', (time.time() - 7 * 86400,))
        rows = db.execute('SELECT DISTINCT sid FROM push_queue WHERE sent=0 LIMIT 200').fetchall()
        targets = {r['sid']: [s['endpoint'] for s in db.execute('SELECT endpoint FROM push_subs WHERE sid=?', (r['sid'],))] for r in rows}
        db.execute('UPDATE push_queue SET sent=1 WHERE sent=0 AND sid IN (%s)' % ','.join('?' * len(targets)), tuple(targets)) if targets else None
    sent = 0
    for sid, endpoints in targets.items():
        for endpoint in endpoints:
            status = _send(k['d'], endpoint)
            with store.connect() as db:
                if status in (404, 410):
                    db.execute('DELETE FROM push_subs WHERE endpoint=?', (endpoint,))
                elif 200 <= status < 300:
                    db.execute('UPDATE push_subs SET last_ok=?, fails=0 WHERE endpoint=?', (time.time(), endpoint))
                    sent += 1
                else:
                    db.execute('UPDATE push_subs SET fails=fails+1 WHERE endpoint=?', (endpoint,))
                    db.execute('DELETE FROM push_subs WHERE endpoint=? AND fails>=20', (endpoint,))
    return sent
