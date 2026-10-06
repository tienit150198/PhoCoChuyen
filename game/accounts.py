"""Optional accounts: keep one save across devices and browser resets.

Play starts anonymously (one cookie token = one save). Registering attaches the
current save to a username/password; every signed-in device then holds its own
random token and CSRF in `logins`, mapped to the account's save, so several
devices share one save and the existing revision guard settles races.

No e-mail, no recovery. Passwords are hashed with scrypt and a per-user salt;
tokens and passwords are never logged or stored in clear (only sha256 of the
token, as for anonymous sessions).
"""
from __future__ import annotations
import hashlib
import hmac
import re
import secrets

from . import db as dbm
from . import social
from . import retention as rt

USERNAME = re.compile(r'[a-z0-9_.]{3,24}')
PASSWORD_MIN, PASSWORD_MAX = 8, 128
DEFAULT_NAME = 'Mây'
WRONG = 'Sai tên đăng nhập hoặc mật khẩu.'
SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


class AccountError(Exception):
    def __init__(self, message: str, code: str = 'account_error', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'account_error', status: int = 400):
    if not cond:
        raise AccountError(message, code, status)


# ---------------------------------------------------------------- passwords
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, maxmem=64 * 1024 * 1024, **SCRYPT)
    return f'scrypt${SCRYPT["n"]}${SCRYPT["r"]}${SCRYPT["p"]}${salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split('$')
        if algo != 'scrypt':
            return False
        got = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                             maxmem=64 * 1024 * 1024, dklen=len(digest) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got.hex(), digest)


# Spend the same work for unknown usernames so timing does not reveal who exists.
_DUMMY = hash_password(secrets.token_hex(12))


# ---------------------------------------------------------------- validation
def clean_username(value) -> str:
    need(isinstance(value, str), 'Tên đăng nhập không hợp lệ.', 'bad_username')
    name = value.strip().lower()
    need(USERNAME.fullmatch(name), 'Tên đăng nhập cần 3–24 ký tự: chữ thường không dấu, số, dấu chấm hoặc gạch dưới.', 'bad_username')
    return name


def clean_password(value, confirm=None, field: str = 'Mật khẩu') -> str:
    need(isinstance(value, str) and PASSWORD_MIN <= len(value) <= PASSWORD_MAX, f'{field} cần ít nhất {PASSWORD_MIN} ký tự.', 'weak_password')
    if confirm is not None:
        need(isinstance(confirm, str) and hmac.compare_digest(value.encode(), confirm.encode()), 'Hai lần nhập mật khẩu chưa khớp.', 'password_mismatch')
    return value


# Names shown in chat, Phố nghề and the leaderboards (moderation C#4513, C#23842: "concac", "con cặc lớn", "Sục cháy
# chim"). social.BANNED only masks whole words WITH their tone marks, so unaccented and run-together spellings passed.
# Three lists, all checked on a folded copy (lower case; "c.ặ.c" → "cặc"):
#  * NAME_MARKED: whole words as typed with tone marks (sục ≠ súc, cặc ≠ các);
#  * NAME_PLAIN: whole words typed with no tone mark at all (a plain "cac", "dcm"; "Các" with its mark is fine);
#  * NAME_JOINED: run-together spellings, matched inside the name with marks and spaces removed ("concac", "dcmm").
NAME_MARKED = ('cặc', 'cặk', 'kặc', 'lồn', 'buồi', 'địt', 'đjt', 'đụ', 'đéo', 'đĩ', 'sục', 'đcm', 'đm', 'đmm', 'đkm', 'chịch', 'nứng')
NAME_PLAIN = ('cac', 'cak', 'kac', 'kak', 'buoi', 'dit', 'djt', 'deo', 'dcm', 'dcmm', 'dkm', 'dm', 'dmm', 'dmmm', 'cmm', 'clm',
              'vcl', 'vkl', 'clgt', 'loz', 'lozz', 'suc', 'chich')
NAME_JOINED = ('concac', 'concak', 'conkac', 'conkak', 'cacto', 'caclon', 'lonto', 'lonme', 'lonmay', 'dcmm', 'ditme', 'ditcon',
               'dume', 'dumay', 'occho', 'succac', 'succhim', 'sucbuoi', 'succhay', 'buoito', 'chichnhau',
               'fuck', 'pussy', 'dick', 'bitch', 'porn', 'nigga', 'nigger', 'cunt')
_LEET = str.maketrans({'4': 'a', '@': 'a', '0': 'o', '1': 'i', '3': 'e', '$': 's'})


def _unmark(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize('NFD', text.lower()).replace('đ', 'd')
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')


def offensive_name(name) -> bool:
    """True for a display name with a vulgar word, accented, unaccented or run together (never renames anything)."""
    import unicodedata
    if not isinstance(name, str):
        return False
    marked = unicodedata.normalize('NFC', name.lower())
    words = [re.sub(r'[^\w]', '', w) for w in re.split(r'\s+', marked)]
    words = [w for w in words if w]
    for w in words:
        plain = _unmark(w)
        if w in NAME_MARKED or (w == plain and plain.translate(_LEET) in NAME_PLAIN):
            return True
    joined = _unmark(''.join(words)).replace('_', '')
    for variant in {joined, joined.translate(_LEET), re.sub(r'(.)\1+', r'\1', joined)}:
        if any(x in variant for x in NAME_JOINED):
            return True
    return False


def clean_display(value) -> str:
    try:
        name = social.clean(value, 24, 1, 'Tên hiển thị')
    except social.SocialError as e:
        raise AccountError(e.message, 'bad_display') from None
    need(name and re.fullmatch(r"[\w .'\-]+", name) and not name.isdigit(), 'Tên hiển thị chỉ gồm chữ, số và khoảng trắng.', 'bad_display')
    need('•' not in name and not offensive_name(name), 'Chọn một cái tên thân thiện hơn nhé.', 'bad_display')
    return name


def character_name(value, current: str | None = None) -> str:
    """Every rename of the character (Cài đặt, Hành trình) goes through the account display-name rules: the name
    becomes accounts.display, the chat name (moderation #13). An unchanged name is kept as it is, so an older name
    never blocks saving the other settings."""
    from .engine import GameError
    if isinstance(value, str) and current is not None and value.strip() == current:
        return current
    try:
        return clean_display(value)
    except AccountError as e:
        raise GameError(e.message, 'bad_display') from None


def has_progress(state: dict) -> bool:
    """Would signing in here throw away something the player made?"""
    j = state.get('journey') or {}
    if int(j.get('life_day', 1) or 1) > 1 or j.get('days') or j.get('done'):
        return True
    return any(c.get('started') or int(c.get('day', 1) or 1) > 1 for c in (state.get('careers') or {}).values())


# ---------------------------------------------------------------- queries
def _account_for(db, sid: str):
    return db.execute('SELECT * FROM accounts WHERE sid=?', (sid,)).fetchone()


def public_account(db, account) -> dict:
    out = dict(username=account['username'], display=account['display'])
    if db.execute('SELECT 1 FROM tiktok_identities WHERE uid=?', (account['uid'],)).fetchone():
        out.update(has_password=account['pw'].startswith('scrypt$'), tiktok_linked=True)
    return out


def status(store, token: str | None) -> dict | None:
    """Public account info for this device (None when playing anonymously)."""
    if not token:
        return None
    sid, login_csrf = store.resolve(token)
    if not login_csrf:
        return None
    with store.connect() as db:
        a = _account_for(db, sid)
        return public_account(db, a) if a else None


def sync_character_name(db, sid: str, before: dict, after: dict) -> None:
    """Commit a settings rename with its save; login identity/profile nicknames stay separate.

    The Store already owns the session row lock. The reducer has validated and
    cleaned this character name, so account-registration naming restrictions do
    not add a second, conflicting validation policy to settings.
    """
    name = after.get('name')
    if before.get('name') == name:
        return
    changed = db.execute('UPDATE accounts SET display=?,updated_at=CURRENT_TIMESTAMP '
                         'WHERE sid=? AND display IS DISTINCT FROM ?', (name, sid, name)).rowcount
    if changed:
        from .live_chat import notify
        notify(db, dict(op='name', sid=sid))


def _new_login(db, sid: str, csrf: str | None = None) -> tuple[str, str]:
    token, csrf = secrets.token_hex(32), csrf or secrets.token_hex(24)
    db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (store_digest(token), sid, csrf))
    return token, csrf


def store_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _adopt_name(store, token: str, sid: str, display: str) -> None:
    """The display name becomes the character's and the public profile's name
    when the player has not picked one yet. Never fails the registration."""
    try:
        state = store.read(token)[0]
        if state.get('name') in (None, '', DEFAULT_NAME):
            store.command(token, 'acct-name-' + secrets.token_hex(8), None, None, 'settings', dict(name=display), internal=True)
    except Exception:  # noqa: BLE001 - cosmetic, the account itself is saved
        pass
    try:
        if len(display) < 2:
            return
        with store.connect() as db:
            p = social._touch(db, sid, None)
            taken = db.execute('SELECT 1 FROM profiles WHERE name_key=? AND pid<>?', (social._fold(display), p['pid'])).fetchone()
            if not p['name'] and not taken:
                db.execute('UPDATE profiles SET name=?,name_key=? WHERE pid=? AND name IS NULL', (display, social._fold(display), p['pid']))
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- actions
def register(store, token: str, d: dict) -> dict:
    username = clean_username(d.get('username'))
    password = clean_password(d.get('password'), d.get('confirm'))
    display = clean_display(d.get('display'))
    pw = hash_password(password)
    sid, login_csrf = store.resolve(token)
    need(not login_csrf, 'Bạn đang đăng nhập rồi.', 'already_signed_in')
    db = store.connect()
    try:
        db.execute('BEGIN')
        row = db.execute('SELECT csrf FROM sessions WHERE sid=?' + dbm.for_update(db), (sid,)).fetchone()
        need(row, 'Phiên chơi không còn tồn tại. Tải lại trang nhé.', 'session_missing', 401)
        need(not _account_for(db, sid), 'Bạn đang đăng nhập rồi.', 'already_signed_in')
        need(not db.execute('SELECT 1 FROM accounts WHERE username=?', (username,)).fetchone(), 'Tên đăng nhập này đã có người dùng.', 'username_taken', 409)
        db.execute('DELETE FROM tiktok_flows WHERE source_token=?', (store_digest(token),))
        try:
            db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)', (username, display, pw, sid))
        except dbm.IntegrityError:  # PostgreSQL: the same name was taken by a concurrent registration
            raise AccountError('Tên đăng nhập này đã có người dùng.', 'username_taken', 409) from None
        # Rotate this device onto a login token; keep its CSRF so open tabs keep working.
        new_token, csrf = _new_login(db, sid, row['csrf'])
        rt.mark(db, sid, 'account')   # Giữ chân (game/retention.py): first time this save got an account
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    _adopt_name(store, new_token, sid, display)
    return dict(token=new_token, csrf=csrf, account=dict(username=username, display=display),
                message='Đã tạo tài khoản. Tiến trình của bạn được giữ trong tài khoản này.')


def check_replace(store, token: str | None, d: dict) -> None:
    """Before checking a password: warn when this device's own progress would be replaced."""
    if d.get('replace') is True or not token:
        return
    sid, login_csrf = store.resolve(token)
    if login_csrf:
        return  # already on an account: that progress stays in its account
    try:
        state = store.read(token)[0]
    except Exception:  # noqa: BLE001
        return
    need(not has_progress(state), 'Tiến trình đang chơi trên máy này sẽ được thay bằng tiến trình của tài khoản.', 'confirm_replace', 409)


def login(store, token: str | None, d: dict) -> dict:
    """Returns the new device token. The caller forgets the old anonymous save."""
    username = d.get('username')
    password = d.get('password')
    need(isinstance(username, str) and isinstance(password, str) and 0 < len(password) <= PASSWORD_MAX and len(username) <= 64, WRONG, 'bad_login', 401)
    with store.connect() as db:
        a = db.execute('SELECT * FROM accounts WHERE username=?', (username.strip().lower(),)).fetchone()
        public = public_account(db, a) if a else None
    ok = verify_password(password, a['pw'] if a else _DUMMY)
    need(a and ok, WRONG, 'bad_login', 401)
    old_sid, old_login = store.resolve(token) if token else (None, None)
    db = store.connect()
    try:
        db.execute('BEGIN')
        # Match TikTok's stable session-first ordering when switching accounts.
        # Only session identity is needed; never load a save for these locks.
        for locked_sid in sorted({a['sid'], old_sid} - {None}):
            row = db.execute('SELECT sid FROM sessions WHERE sid=?' + dbm.for_update(db), (locked_sid,)).fetchone()
            if locked_sid == a['sid']:
                need(row, WRONG, 'bad_login', 401)
        # A reset may finish after verification. Recheck the verified hash under
        # the account lock, so reset either revokes this login or rejects it here.
        need(db.execute('SELECT 1 FROM accounts WHERE uid=? AND sid=? AND pw=?' + dbm.for_update(db),
                        (a['uid'], a['sid'], a['pw'])).fetchone(), WRONG, 'bad_login', 401)
        if token:
            db.execute('DELETE FROM tiktok_flows WHERE source_token=?', (store_digest(token),))
        if old_login:
            db.execute('DELETE FROM logins WHERE token=?', (store_digest(token),))
        new_token, csrf = _new_login(db, a['sid'])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    # An anonymous save on this device is replaced (the player confirmed); drop it.
    drop = bool(token) and not old_login and old_sid != a['sid'] and not str(old_sid).startswith('revoked:')
    return dict(token=new_token, csrf=csrf, drop_anonymous=drop, account=public,
                message=f'Chào {a["display"]}! Tiến trình của tài khoản đã về máy này.')


def logout(store, token: str | None) -> None:
    need(token and store.resolve(token)[1], 'Bạn chưa đăng nhập.', 'not_signed_in')
    with store.connect() as db:
        db.execute('DELETE FROM tiktok_flows WHERE source_token=?', (store_digest(token),))
        db.execute('DELETE FROM logins WHERE token=?', (store_digest(token),))


def change_password(store, token: str, d: dict) -> dict:
    sid, login_csrf = store.resolve(token)
    need(login_csrf, 'Bạn chưa đăng nhập.', 'not_signed_in')
    current = d.get('current')
    need(isinstance(current, str) and 0 < len(current) <= PASSWORD_MAX, 'Mật khẩu hiện tại chưa đúng.', 'bad_login', 401)
    new = clean_password(d.get('password'), d.get('confirm'), 'Mật khẩu mới')
    with store.connect() as db:
        a = _account_for(db, sid)
    need(a, 'Bạn chưa đăng nhập.', 'not_signed_in')
    need(verify_password(current, a['pw']), 'Mật khẩu hiện tại chưa đúng.', 'bad_login', 401)
    pw = hash_password(new)
    with store.connect() as db:
        db.begin()
        need(db.execute('SELECT sid FROM sessions WHERE sid=?' + dbm.for_update(db),
                        (sid,)).fetchone(), 'Bạn chưa đăng nhập.', 'not_signed_in')
        # Share the reset/login lock order and reject a stale verification or
        # a device revoked while its password change was being prepared.
        need(db.execute('SELECT 1 FROM accounts WHERE uid=? AND sid=? AND pw=?' + dbm.for_update(db),
                        (a['uid'], sid, a['pw'])).fetchone(), 'Mật khẩu hiện tại chưa đúng.', 'bad_login', 401)
        need(db.execute('SELECT 1 FROM logins WHERE token=? AND sid=?' + dbm.for_update(db),
                        (store_digest(token), sid)).fetchone(), 'Bạn chưa đăng nhập.', 'not_signed_in')
        db.execute('UPDATE accounts SET pw=?,updated_at=CURRENT_TIMESTAMP WHERE uid=?', (pw, a['uid']))
        # Other devices must sign in again with the new password.
        db.execute('DELETE FROM tiktok_flows WHERE source_token IN (SELECT token FROM logins WHERE sid=? AND token<>?)', (sid, store_digest(token)))
        db.execute('DELETE FROM logins WHERE sid=? AND token<>?', (sid, store_digest(token)))
    return dict(message='Đã đổi mật khẩu. Các máy khác sẽ cần đăng nhập lại.')


# ---------------------------------------------------------------- moderation #13: names already in use
NAMES_LISTED = 200


def safe_name(uid: int) -> str:
    return f'Cư dân {int(uid)}'


def offending_names(db, limit: int = NAMES_LISTED) -> list[dict]:
    """Accounts whose chat name (accounts.display), Phố nghề name or character name (leaderboard_players, kept from
    the save by every command) fails offensive_name: listed for the admin, never renamed by themselves."""
    rows = db.execute('SELECT a.uid, a.username, a.display, a.sid, p.name AS pname, lp.name AS gname FROM accounts a '
                      'LEFT JOIN profiles p ON p.sid=a.sid LEFT JOIN leaderboard_players lp ON lp.sid=a.sid ORDER BY a.uid DESC').fetchall()
    out = []
    for r in rows:
        bad = [k for k in ('display', 'pname', 'gname') if r[k] and offensive_name(r[k])]
        if bad:
            out.append(dict(uid=int(r['uid']), username=r['username'], display=r['display'], profile=r['pname'], character=r['gname'],
                            pid=social.pid_of(r['sid']), bad=bad, safe=safe_name(r['uid'])))
            if len(out) >= limit:
                break
    return out


def rename_safe(store, uid, admin: str = '') -> dict:
    """One click in the admin: every offending name of this account becomes "Cư dân <uid>" (the save's character
    name through an internal `settings` command, so the save, accounts.display, the leaderboard and the chat follow;
    the Phố nghề name when it offends too). Nothing is deleted; names that do not offend are left as they are."""
    import hashlib as _h
    import json as _json
    need(type(uid) is int and uid > 0, 'Tài khoản không hợp lệ.', 'bad_uid')
    with store.connect() as db:
        r = db.execute('SELECT a.uid, a.sid, a.display, p.pid, p.name AS pname, lp.name AS gname FROM accounts a LEFT JOIN profiles p ON p.sid=a.sid '
                       'LEFT JOIN leaderboard_players lp ON lp.sid=a.sid WHERE a.uid=?', (uid,)).fetchone()
    need(r, 'Không thấy tài khoản này.', 'not_found', 404)
    need(any(r[k] and offensive_name(r[k]) for k in ('display', 'pname', 'gname')), 'Tên này không nằm trong danh sách cần đổi.', 'not_offensive')
    new, sid = safe_name(uid), r['sid']
    payload = dict(name=new)
    rid = 'admin-rename-' + secrets.token_hex(8)
    fingerprint = _h.sha256(_json.dumps([None, 'settings', payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    try:
        store._command_locked(sid, rid, None, None, 'settings', payload, True, fingerprint)
    except Exception as e:   # noqa: BLE001 - a save that cannot load: the account and profile names still change below
        if getattr(e, 'code', '') != 'session_missing':
            raise
    with store.connect() as db:
        db.execute('UPDATE accounts SET display=?,updated_at=CURRENT_TIMESTAMP WHERE uid=? AND display IS DISTINCT FROM ?', (new, uid, new))
        db.execute('UPDATE leaderboard_players SET name=? WHERE sid=? AND name IS DISTINCT FROM ?', (new, sid, new))
        if r['pname'] and offensive_name(r['pname']):
            taken = db.execute('SELECT 1 FROM profiles WHERE name_key=? AND sid<>?', (social._fold(new), sid)).fetchone()
            db.execute('UPDATE profiles SET name=?,name_key=? WHERE sid=?', (None, None, sid) if taken else (new, social._fold(new), sid))
        from .live_chat import notify
        notify(db, dict(op='name', sid=sid))
    return dict(ok=True, uid=uid, name=new, by=admin[:40])
