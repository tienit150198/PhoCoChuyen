"""Account directory and admin password resets. Never reads or writes save JSON.
The HTTP handler requires an admin session and CSRF before calling this module.
"""
from datetime import datetime, timezone

from . import accounts, db as dbm, social

DEFAULT_LIMIT, MAX_LIMIT = 50, 100
# PostgreSQL's existing text columns use the C collation. Translate Vietnamese
# capitals explicitly to match the Unicode folding used by public profiles.
VI_UPPER = 'ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ'


def _bounded(value, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(value)))
    except (ValueError, TypeError):
        return default


def directory(store, query):
    q = str(query.get('q') or '').replace('\x00', '').strip()[:80]
    term = social._fold(q.removeprefix('@'))
    limit = _bounded(query.get('limit'), DEFAULT_LIMIT, 1, MAX_LIMIT)
    offset = _bounded(query.get('offset'), 0, 0, 2**31 - 1)
    with store.connect() as db:
        params, where = [], ''
        if term:
            display = f"LOWER(TRANSLATE(a.display, '{VI_UPPER}', '{VI_UPPER.lower()}'))"
            # An underscore/percent in a username or query is ordinary text.
            pattern = '%' + term.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
            where = f" WHERE a.username LIKE ? ESCAPE '!' OR {display} LIKE ? ESCAPE '!' OR p.name_key LIKE ? ESCAPE '!'"
            params = [pattern] * 3
        joined = ' FROM accounts a LEFT JOIN profiles p ON p.sid=a.sid'
        count_from = joined if where else ' FROM accounts a'
        total = db.execute('SELECT COUNT(*)' + count_from + where, params).fetchone()[0]
        rows = db.execute(
            'SELECT a.uid,a.username,a.display,a.created_at,p.name,p.seen,s.updated_at AS saved_at' + joined +
            ' LEFT JOIN sessions s ON s.sid=a.sid' + where + ' ORDER BY a.uid DESC LIMIT ? OFFSET ?',
            [*params, limit, offset]).fetchall()
    items = []
    for row in rows:
        seen = datetime.fromtimestamp(row['seen'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if row['seen'] else None
        active = max(filter(None, (row['saved_at'], seen)), default=None)
        items.append(dict(id=row['uid'], username=row['username'], display=row['display'],
                          name=row['name'] or row['display'], created_at=row['created_at'], last_active_at=active))
    return dict(q=q, items=items, total=total, offset=offset, limit=limit, has_more=offset + len(items) < total)


def reset_password(store, token: str, data: dict) -> dict:
    """Reset a selected account and revoke all of its devices in one transaction."""
    uid = data.get('id')
    accounts.need(type(uid) is int and uid > 0, 'Người dùng được chọn không hợp lệ.', 'bad_target')
    username = accounts.clean_username(data.get('username'))
    accounts.need(username == data['username'], 'Tên đăng nhập không hợp lệ.', 'bad_username')
    password = accounts.clean_password(data.get('password'), field='Mật khẩu mới')
    accounts.need(isinstance(data.get('confirm'), str), 'Hai lần nhập mật khẩu chưa khớp.', 'password_mismatch')
    accounts.clean_password(password, data['confirm'], 'Mật khẩu mới')
    pw = accounts.hash_password(password)
    caller_sid, _ = store.resolve(token)
    with store.connect() as db:
        db.begin()
        selected = db.execute('SELECT sid FROM accounts WHERE uid=? AND username=?', (uid, username)).fetchone()
        accounts.need(selected, 'Không còn tìm thấy tài khoản được chọn.', 'account_missing', 404)
        # TikTok completion and account deletion lock session metadata first.
        accounts.need(db.execute('SELECT sid FROM sessions WHERE sid=?' + dbm.for_update(db),
                                 (selected['sid'],)).fetchone(),
                      'Không còn tìm thấy tài khoản được chọn.', 'account_missing', 404)
        account = db.execute('SELECT uid,username,display,sid FROM accounts WHERE uid=? AND username=? AND sid=?' +
                             dbm.for_update(db), (uid, username, selected['sid'])).fetchone()
        accounts.need(account, 'Không còn tìm thấy tài khoản được chọn.', 'account_missing', 404)
        db.execute('UPDATE accounts SET pw=?,updated_at=CURRENT_TIMESTAMP WHERE uid=?', (pw, account['uid']))
        db.execute('DELETE FROM tiktok_flows WHERE source_token IN (SELECT token FROM logins WHERE sid=?)',
                   (account['sid'],))
        db.execute('DELETE FROM logins WHERE sid=?', (account['sid'],))
    return dict(ok=True, username=account['username'], display=account['display'],
                message='Đã đổi mật khẩu. Tài khoản này cần đăng nhập lại trên mọi thiết bị.',
                reauthenticate=caller_sid == account['sid'])
