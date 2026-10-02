"""Optional TikTok Login Kit. No provider tokens or authorization codes are stored.

The main game cookie stays Strict. A ten-minute Lax cookie binds the return to
the browser that started it, while the saved token hash must still be active.
Authorization is consumed before contacting TikTok; confirmation is another
one-use phase and cannot change saves without its own browser-bound nonce.
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import time
import unicodedata
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import accounts, db as dbm, retention as rt

FLOW_COOKIE = 'mnl_tiktok_flow'
TTL = 600
MAX_RESPONSE = 65536
TIMEOUT = 8
DISABLED_PASSWORD = 'disabled$tiktok'
SAFE_ERRORS = frozenset(('tiktok_unavailable', 'tiktok_state', 'tiktok_session', 'tiktok_denied',
                         'tiktok_provider', 'tiktok_conflict', 'tiktok_mode'))


def fail(code='tiktok_state'):
    messages = dict(tiktok_unavailable='Đăng nhập TikTok chưa được bật. Bạn vẫn có thể dùng tài khoản thường.',
                    tiktok_state='Phiên đăng nhập TikTok đã hết hạn hoặc không hợp lệ. Hãy thử lại.',
                    tiktok_session='Phiên chơi đã thay đổi. Hãy mở lại mục Tài khoản để thử lại.',
                    tiktok_denied='Bạn đã hủy cấp quyền TikTok. Tiến trình vẫn được giữ nguyên.',
                    tiktok_provider='Chưa kết nối được với TikTok. Tiến trình vẫn được giữ nguyên. Hãy thử lại.',
                    tiktok_conflict='TikTok này đã liên kết với một tài khoản khác.',
                    tiktok_mode='Hãy đăng nhập tài khoản thường trước khi liên kết TikTok.')
    raise accounts.AccountError(messages.get(code, messages['tiktok_state']), code,
                                503 if code == 'tiktok_unavailable' else 400)


def config():
    key = os.environ.get('TIKTOK_CLIENT_KEY', '').strip()
    secret = os.environ.get('TIKTOK_CLIENT_SECRET', '').strip()
    redirect = os.environ.get('TIKTOK_REDIRECT_URI', '').strip()
    mode = os.environ.get('TIKTOK_MODE', 'sandbox').strip().lower()
    try:
        uri = urlsplit(redirect)
        valid = (uri.scheme == 'https' and uri.hostname and not uri.username and not uri.password
                 and uri.path == '/auth/tiktok/callback' and not uri.query and not uri.fragment)
        uri.port  # reject malformed ports
    except ValueError:
        valid = False
    return dict(key=key, secret=secret, redirect=redirect, mode=mode if mode in ('sandbox', 'production') else 'sandbox',
                enabled=bool(key and secret and valid and mode in ('sandbox', 'production')))


def public_config():
    c = config()
    return dict(enabled=c['enabled'], mode=c['mode'])


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _provider(opener, request):
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE: fail('tiktok_provider')
        data = json.loads(raw)
        if not isinstance(data, dict): fail('tiktok_provider')
        return data
    except accounts.AccountError:
        raise
    except Exception:  # never include provider response, network URL or request data
        fail('tiktok_provider')


def exchange_identity(code):
    c = config()
    if not c['enabled']: fail('tiktok_unavailable')
    opener = build_opener(NoRedirect())
    token = _provider(opener, Request('https://open.tiktokapis.com/v2/oauth/token/',
                     data=urlencode(dict(client_key=c['key'], client_secret=c['secret'], code=code,
                                         grant_type='authorization_code', redirect_uri=c['redirect'])).encode(),
                     headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST'))
    access = token.get('access_token')
    if (not isinstance(access, str) or not 1 <= len(access) <= 4096
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in access)
            or 'user.info.basic' not in str(token.get('scope', '')).split(',')):
        fail('tiktok_provider')
    data = _provider(opener, Request('https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name',
                                    headers={'Authorization': 'Bearer ' + access}))
    user = (data.get('data') or {}).get('user') if isinstance(data.get('data'), dict) else None
    error = data.get('error')
    if isinstance(error, dict) and error.get('code') not in (None, 'ok'): fail('tiktok_provider')
    if not isinstance(user, dict): fail('tiktok_provider')
    open_id, display = user.get('open_id'), user.get('display_name')
    if not isinstance(open_id, str) or not 1 <= len(open_id) <= 256 or any(ord(ch) < 32 for ch in open_id):
        fail('tiktok_provider')
    if token.get('open_id') is not None and token['open_id'] != open_id: fail('tiktok_provider')
    if not isinstance(display, str): fail('tiktok_provider')
    # Names are cosmetic, never identity keys. Do not copy control characters or markup.
    display = ''.join(ch for ch in display if unicodedata.category(ch)[0] != 'C' and ch not in '<>')
    display = ' '.join(display.split())[:24] or 'Người chơi TikTok'
    return open_id, display


def _source(store, db, flow, *, lock_login=True):
    sid, login = store._resolve(db, flow['source_token'])
    if sid != flow['source_sid'] or bool(login) != bool(flow['source_login']): fail('tiktok_session')
    row = db.execute('SELECT * FROM sessions WHERE sid=?' + dbm.for_update(db), (sid,)).fetchone()
    if not row: fail('tiktok_session')
    # Recheck after locking the save: a concurrent registration/logout may just have committed.
    sid, login = store._resolve(db, flow['source_token'])
    if sid != flow['source_sid'] or bool(login) != bool(flow['source_login']): fail('tiktok_session')
    if flow['source_login'] and lock_login:
        active = db.execute('SELECT 1 FROM logins WHERE token=?' + dbm.for_update(db), (flow['source_token'],)).fetchone()
        if not active: fail('tiktok_session')
    row = dict(row)
    if login: row['csrf'] = login
    return row


def start(store, token, mode):
    c = config()
    if not c['enabled']: fail('tiktok_unavailable')
    if mode not in ('login', 'link'): fail('tiktok_mode')
    state, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db = store.connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        sid, login = store._resolve(db, digest(token))
        flow = dict(source_token=digest(token), source_sid=sid, source_login=int(bool(login)))
        _source(store, db, flow, lock_login=False)
        if mode == 'link' and not login: fail('tiktok_mode')
        if mode == 'login' and login: fail('tiktok_mode')  # account changes use the explicit link action
        db.execute('DELETE FROM tiktok_flows WHERE expires_at<? OR source_token=?', (time.time(), flow['source_token']))
        _source(store, db, flow)  # flow deletion precedes the login lock, as on logout
        db.execute('INSERT INTO tiktok_flows(state_hash,binding_hash,source_token,source_sid,source_login,mode,client_key,expires_at,phase) '
                   'VALUES(?,?,?,?,?,?,?,?,?)', (digest(state), digest(binding), flow['source_token'], sid, flow['source_login'],
                                                mode, c['key'], time.time() + TTL, 'pending'))
        db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
    url = 'https://www.tiktok.com/v2/auth/authorize/?' + urlencode(dict(client_key=c['key'], response_type='code',
                  scope='user.info.basic', redirect_uri=c['redirect'], state=state))
    return dict(state=state, binding=binding, authorization_url=url)


def _checked_flow(row, binding, phase):
    if (not row or row['phase'] != phase or row['expires_at'] <= time.time()
            or not secrets.compare_digest(row['binding_hash'], digest(binding))): fail()
    c = config()
    if not c['enabled'] or row['client_key'] != c['key']: fail('tiktok_unavailable')
    return row


def _flow(db, state, binding, phase, *, lock=True):
    if not isinstance(state, str) or not isinstance(binding, str) or not 20 <= len(state) <= 128 or not 20 <= len(binding) <= 128:
        fail()
    row = db.execute('SELECT * FROM tiktok_flows WHERE state_hash=?' + (dbm.for_update(db) if lock else ''), (digest(state),)).fetchone()
    return _checked_flow(row, binding, phase)


def _lock_saves(db, flow, target_sid=None):
    """Session locks precede flow/identity/account locks, including on deletion.

    Preflight lookups do not lock anything. Lock both saves in a stable order,
    then revalidate the flow and identity: a deletion or another login may have
    committed while we were waiting.
    """
    for sid in sorted({flow['source_sid'], target_sid} - {None}):
        if not db.execute('SELECT sid FROM sessions WHERE sid=?' + dbm.for_update(db), (sid,)).fetchone():
            fail('tiktok_session')


def _confirmation_flow(db, binding):
    if not isinstance(binding, str) or not 20 <= len(binding) <= 128: fail()
    preflight = db.execute('SELECT * FROM tiktok_flows WHERE binding_hash=?', (digest(binding),)).fetchone()
    _checked_flow(preflight, binding, 'confirm')
    account = db.execute('SELECT sid FROM accounts WHERE uid=?', (preflight['target_uid'],)).fetchone()
    if not account: fail('tiktok_session')
    _lock_saves(db, preflight, account['sid'])
    row = db.execute('SELECT * FROM tiktok_flows WHERE binding_hash=?' + dbm.for_update(db), (digest(binding),)).fetchone()
    _checked_flow(row, binding, 'confirm')
    if row['target_uid'] != preflight['target_uid'] or row['source_sid'] != preflight['source_sid']: fail()
    return row


def callback(store, state, binding, code=None, error=None):
    db = store.connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        preflight = _flow(db, state, binding, 'pending', lock=False)
        _lock_saves(db, preflight)
        flow = _flow(db, state, binding, 'pending')
        _source(store, db, flow)
        db.execute("UPDATE tiktok_flows SET phase='exchanging' WHERE state_hash=?", (flow['state_hash'],))
        db.commit()  # consume BEFORE exchange; failed/denied returns cannot be replayed
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
    if error: fail('tiktok_denied')
    if not isinstance(code, str) or not 1 <= len(code) <= 2048: fail('tiktok_provider')
    open_id, display = exchange_identity(code)
    return _finish(store, state, binding, open_id, display)


def _public(db, account):
    return accounts.public_account(db, account)


def _login(db, flow, account, source, *, preserve_csrf=False):
    if flow['source_login']: db.execute('DELETE FROM logins WHERE token=?', (flow['source_token'],))
    token, csrf = accounts._new_login(db, account['sid'], source['csrf'] if preserve_csrf else None)
    db.execute("UPDATE tiktok_flows SET phase='done',nonce_hash=NULL,target_uid=? WHERE state_hash=?", (account['uid'], flow['state_hash']))
    return dict(status='linked' if flow['mode'] == 'link' else 'success', token=token, csrf=csrf, account=_public(db, account))


def _nonce(flow, binding):
    # A stable CSRF nonce for the clean confirmation URL, derived from the two
    # independent random flow secrets. Only its hash is persisted.
    return digest('tiktok-confirm:' + binding + ':' + flow['state_hash'])


def _finish(store, state, binding, open_id, display):
    db = store.connect()
    adopt = False
    try:
        db.execute('BEGIN IMMEDIATE')
        preflight = _flow(db, state, binding, 'exchanging', lock=False)
        pre_identity = db.execute('SELECT * FROM tiktok_identities WHERE client_key=? AND open_id=?',
                                  (preflight['client_key'], open_id)).fetchone()
        _lock_saves(db, preflight, pre_identity['sid'] if pre_identity else None)
        flow = _flow(db, state, binding, 'exchanging')
        source = _source(store, db, flow)
        identity = db.execute('SELECT * FROM tiktok_identities WHERE client_key=? AND open_id=?' + dbm.for_update(db),
                              (flow['client_key'], open_id)).fetchone()
        # Never acquire a newly discovered target session after the identity lock.
        if bool(identity) != bool(pre_identity): fail('tiktok_conflict')
        if identity and (identity['uid'], identity['sid']) != (pre_identity['uid'], pre_identity['sid']):
            fail('tiktok_session')
        if flow['mode'] == 'link':
            account = db.execute('SELECT * FROM accounts WHERE sid=?' + dbm.for_update(db), (flow['source_sid'],)).fetchone()
            if not account: fail('tiktok_session')
            if identity and identity['uid'] != account['uid']: fail('tiktok_conflict')
            other = db.execute('SELECT open_id FROM tiktok_identities WHERE client_key=? AND uid=?', (flow['client_key'], account['uid'])).fetchone()
            if other and other['open_id'] != open_id: fail('tiktok_conflict')
        elif identity:
            account = db.execute('SELECT * FROM accounts WHERE uid=?' + dbm.for_update(db), (identity['uid'],)).fetchone()
            if not account or account['sid'] != identity['sid']: fail('tiktok_session')
            if accounts.has_progress(store.parse_state(source['state'], flow['source_sid'])):
                nonce = _nonce(flow, binding)
                db.execute("UPDATE tiktok_flows SET phase='confirm',target_uid=?,nonce_hash=? WHERE state_hash=?",
                           (account['uid'], digest(nonce), flow['state_hash']))
                db.commit()
                return dict(status='confirm', nonce=nonce, display=account['display'])
        else:
            username = 'tt_' + secrets.token_hex(10)
            db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)',
                       (username, display, DISABLED_PASSWORD, flow['source_sid']))
            account = accounts._account_for(db, flow['source_sid'])
            rt.mark(db, flow['source_sid'], 'account')
            adopt = True
        if not identity:
            db.execute('INSERT INTO tiktok_identities(client_key,open_id,uid,sid,display) VALUES(?,?,?,?,?)',
                       (flow['client_key'], open_id, account['uid'], account['sid'], display))
        out = _login(db, flow, account, source, preserve_csrf=adopt or flow['mode'] == 'link')
        db.commit()
    except dbm.IntegrityError:
        db.rollback(); fail('tiktok_conflict')
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
    if adopt: accounts._adopt_name(store, out['token'], account['sid'], display)
    return out


def confirmation(store, binding):
    """Read the one-use confirmation form after redirecting away from code/state."""
    if not isinstance(binding, str) or not 20 <= len(binding) <= 128: fail()
    db = store.connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        flow = _confirmation_flow(db, binding)
        _source(store, db, flow)
        account = db.execute('SELECT display FROM accounts WHERE uid=?', (flow['target_uid'],)).fetchone()
        if not account: fail('tiktok_session')
        nonce = _nonce(flow, binding)
        if not secrets.compare_digest(flow['nonce_hash'] or '', digest(nonce)): fail()
        db.commit()
        return dict(display=account['display'], nonce=nonce)
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def confirm(store, binding, nonce, choice):
    if not isinstance(binding, str) or not 20 <= len(binding) <= 128 or not isinstance(nonce, str) or not 20 <= len(nonce) <= 128:
        fail()
    if choice not in ('confirm', 'cancel'): fail()
    db = store.connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        flow = _confirmation_flow(db, binding)
        if not secrets.compare_digest(flow['nonce_hash'] or '', digest(nonce)): fail()
        source = _source(store, db, flow)
        if choice == 'cancel':
            db.execute("UPDATE tiktok_flows SET phase='done',nonce_hash=NULL WHERE state_hash=?", (flow['state_hash'],))
            out = dict(status='cancelled')
        else:
            account = db.execute('SELECT * FROM accounts WHERE uid=?' + dbm.for_update(db), (flow['target_uid'],)).fetchone()
            if not account: fail('tiktok_session')
            if not db.execute('SELECT 1 FROM sessions WHERE sid=?' + dbm.for_update(db), (account['sid'],)).fetchone(): fail('tiktok_session')
            out = _login(db, flow, account, source)
        db.commit()
        return out
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
