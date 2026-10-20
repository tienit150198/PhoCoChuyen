"""📜 Nội quy bang: a bang's two rules texts (owner 21/10 "bang thì thêm cái nội quy bang nữa nhé, thiếu nội quy bang
rồi", then "công bố bên ngoài thì có nội quy bang riêng nữa, có text và giới hạn chữ"; SCHEMA_VERSION 73).

* 📢 Nội quy công khai ('pub', at most PUB_MAX characters and PUB_LINES lines): shown outside the bang, a short preview on
  its card in Tìm bang and in full on its page for visitors and applicants. It is what an applicant agrees to: when the
  bang has one, a join, a request or an accepted invitation (POST /api/bang/join | accept) needs {agree: true, code_ver:
  the version they read}; a version changed since is refused (code_changed: read it again), a page that sends no
  agreement (2.4.66 and older) is refused with a clear "tải lại" message (code_agree), and a bang without public rules
  takes everyone as before. The version agreed to is kept (bang_code_seen.agreed).
* 📜 Nội quy nội bộ ('in', at most IN_MAX characters and IN_LINES lines): only members see it, in the bang sheet.
* Phó bang and up (CODE_FROM, like the join rules) write both (POST /api/bang/code {kind, text, ver}): the motto's
  cleaning (game/social.py clean: no link, e-mail or phone number, the banned words; then live/filters.py mask), edits
  compare-and-set on `ver` under the bang row's lock (a stale page is told someone else edited first; the same text again
  is a no-op, so a retried tap is harmless), at most one edit of a text every EDIT_GAP seconds and EDIT_DAY edits of
  both a Vietnam day for a bang. Every edit is logged in the bang ("📜 X cập nhật nội quy bang …") and kept in bang_code_hist (append-only).
* 📜 Nội quy mới: a member whose read versions (bang_code_seen) are older than a shown text sees the badge (the sheet's
  📜 tab, the home tab's notice, the menu's ⚔️ Bang count through GET /api/bang/me mine.code_new) until they open the tab
  (POST /api/bang/code_seen {pub, in}). A new member has read the public version they agreed to, not the internal one.
* The operator (POST /api/admin/bang {op: code_hide | code_show, id, kind}) hides or shows either text: the text stays
  in the database, the bang log and admin_note say who.
* 🛑 MNL_BANG_OFF (game/bang.py off): the whole Bang is refused, these texts with it.
Nothing is in a save. A player's erasure keeps the texts and anonymises who wrote them (forget)."""
from __future__ import annotations

import datetime
import re

from . import bang as B

KINDS = ('pub', 'in')
NAMES = {'pub': 'nội quy công khai', 'in': 'nội quy nội bộ'}
PUB_MAX, PUB_LINES = 300, 8
IN_MAX, IN_LINES = 1200, 20
LIMITS = {'pub': (PUB_MAX, PUB_LINES), 'in': (IN_MAX, IN_LINES)}
CODE_FROM = 4                    # Phó bang and up (game/bang_content.py RULES_FROM: the same officers as the join rules)
EDIT_GAP = 15.0                  # seconds between two edits of one of a bang's texts
EDIT_DAY = 20                    # edits of a bang's two texts together in a Vietnam day
TIPS = (                         # one tap inserts a line (the leader edits it as they like)
    'Online góp quỹ mỗi tuần',
    'Không chửi bậy trong bang',
    'Bang chiến Chủ nhật 20:00 phải có mặt',
    'Vắng 7 ngày không báo sẽ bị mời ra',
    'Điểm danh mỗi ngày nhé',
    'Tôn trọng Bang chủ và mọi thành viên',
)
AGREE_TEXT = 'Tôi đã đọc và đồng ý nội quy bang'


def clean(kind: str, value) -> str:
    """The text as stored: NFC, no control characters, one space between words, at most one blank line in a row, the
    game's public-text rules (no link, e-mail or phone number; banned words masked), then the chat's mask; within the
    kind's characters and lines. Raises BangError with the reason."""
    from . import social
    from live import filters
    limit, lines = LIMITS[kind]
    B.need(isinstance(value, str), 'Nội quy không hợp lệ.', 'bad_code')
    if len(value) > limit * 4:
        raise B.BangError(f'Nội quy tối đa {limit} ký tự.', 'code_long')
    try:
        # its own length check never fires (longer than limit × 4 was refused above): ours follows, after cleaning
        text = social.clean(value.replace('\r\n', '\n').replace('\r', '\n'), limit * 4, 0, 'Nội quy')
    except social.SocialError as x:
        raise B.BangError(x.message.replace(' trong Phố nghề', ' trong nội quy'), x.code if x.code != 'social_error' else 'bad_code') from None
    text = re.sub(r' *\n *', '\n', text).strip()
    text = filters.mask(text).strip()
    B.need(len(text) <= limit, f'Nội quy tối đa {limit} ký tự (đang {len(text)}).', 'code_long')
    n = text.count('\n') + 1 if text else 0
    B.need(n <= lines, f'Nội quy tối đa {lines} dòng (đang {n}).', 'code_long')
    return text


# ---------------------------------------------------------------- reads
def _rows(db, bids=None) -> dict:
    """{(bang, kind): row} of these bangs (all with None)."""
    if bids is None:
        rows = B._rows(db, 'SELECT * FROM bang_code')
    else:
        bids = sorted({b for b in bids if b})
        if not bids:
            return {}
        rows = B._rows(db, 'SELECT * FROM bang_code WHERE bang IN (' + ','.join('?' * len(bids)) + ')', tuple(bids))
    return {(r['bang'], r['kind']): r for r in rows}


def shown(row: dict | None) -> str:
    """What players see of a row: its text, or '' when there is none or the operator hid it."""
    return '' if not row or row['hidden'] else str(row['text'] or '')


def _ver(row: dict | None) -> int:
    return int(row['ver']) if row else 0


def public(row: dict | None) -> dict:
    """The bang card's `code`: {text, ver} of the public rules ('' and the version when there are none)."""
    return dict(text=shown(row), ver=_ver(row))


def public_map(db, bids=None) -> dict:
    """{bang: {text, ver}} of the public rules of these bangs (one query; all with None)."""
    return {b: public(r) for (b, k), r in _rows(db, bids).items() if k == 'pub'}


def public_of(db, bid: str) -> dict:
    return public(_rows(db, [bid]).get((bid, 'pub')))


def _seen(db, bid: str, sid: str) -> dict | None:
    return B._row(db, 'SELECT * FROM bang_code_seen WHERE sid=? AND bang=?', (sid, bid))


def _fresh(rows: dict, bid: str, seen: dict | None) -> list:
    """The kinds with a shown text newer than what the member read."""
    read = {'pub': int(seen['pub']) if seen else 0, 'in': int(seen['inn']) if seen else 0}
    return [k for k in KINDS if shown(rows.get((bid, k))) and _ver(rows.get((bid, k))) > read[k]]


def fresh(db, bid: str, sid: str) -> bool:
    """📜 Nội quy mới for this member (GET /api/bang/me mine.code_new)."""
    return bool(_fresh(_rows(db, [bid]), bid, _seen(db, bid, sid)))


def member_view(db, bid: str, sid: str, role: str) -> dict:
    """The member page's `code`: both texts, what this member read, the badge, the editor's limits and tips."""
    rows = _rows(db, [bid])
    seen = _seen(db, bid, sid)
    out = {}
    for k in KINDS:
        r = rows.get((bid, k))
        out[k] = dict(text=shown(r), ver=_ver(r), at=float(r['at']) if r and r['at'] else 0.0,
                      by=B._display(db, r['by_sid']) if r and r['by_sid'] and shown(r) else '', hidden=bool(r and r['hidden']))
    news = _fresh(rows, bid, seen)
    edit = B._rank(role) >= CODE_FROM
    out.update(seen=dict(pub=int(seen['pub']) if seen else 0, **{'in': int(seen['inn']) if seen else 0}), fresh=bool(news), news=news,
               edit=edit, max={k: LIMITS[k][0] for k in KINDS}, lines={k: LIMITS[k][1] for k in KINDS})
    if edit:
        out['tips'] = list(TIPS)
    return out


# ---------------------------------------------------------------- 🚪 joining (game/bang.py _op_join, _op_accept)
def need_agree(db, bang: dict, data: dict) -> int:
    """The public version the joining player agreed to (0: the bang has no public rules). The bang row is locked by
    the caller, as every edit locks it: the version compared is the one in force."""
    row = _rows(db, [bang['id']]).get((bang['id'], 'pub'))
    if not shown(row):
        return 0
    ver = _ver(row)
    agree = data.get('agree')
    if agree is not True:
        if agree is None and 'code_ver' not in data:   # a page from before 📜 (2.4.66 and older)
            raise B.BangError(f'Bang {bang["name"]} có nội quy. Tải lại game để đọc và đồng ý nội quy rồi vào bang nhé.', 'code_agree')
        raise B.BangError(f'Đánh dấu "{AGREE_TEXT}" trước khi vào nhé.', 'code_agree')
    B.need(type(data.get('code_ver')) is int and data['code_ver'] == ver,
           f'Bang {bang["name"]} vừa đổi nội quy. Đọc lại nội quy mới và đồng ý nhé.', 'code_changed', 409)
    return ver


def agreed(db, bid: str, sid: str, ver: int, t: float) -> None:
    """Keep the version agreed to (a request: the member later approved has read that one)."""
    if ver:
        db.execute('INSERT INTO bang_code_seen(sid, bang, agreed, agreed_at, at) VALUES(?,?,?,?,?) '
                   'ON CONFLICT(sid, bang) DO UPDATE SET agreed=excluded.agreed, agreed_at=excluded.agreed_at, at=excluded.at',
                   (sid, bid, ver, t, t))


def joined(db, bid: str, sid: str, t: float) -> None:
    """A new member (any way in): they have read the public version they agreed to (none: none), not the internal rules."""
    db.execute('INSERT INTO bang_code_seen(sid, bang, at) VALUES(?,?,?) '
               'ON CONFLICT(sid, bang) DO UPDATE SET pub=bang_code_seen.agreed, inn=0, at=excluded.at', (sid, bid, t))


# ---------------------------------------------------------------- ✏️ the officers' edit, a member's read
def _day_start(t: float) -> float:
    d = datetime.datetime.fromtimestamp(t, B.VN).date()
    return datetime.datetime(d.year, d.month, d.day, tzinfo=B.VN).timestamp()


def op_edit(db, sid: str, data: dict, t: float) -> dict:
    """POST /api/bang/code {kind: 'pub' | 'in', text, ver}: Phó bang and up; `ver` the version the editor started from."""
    bang, me = B._officer(db, sid, CODE_FROM)
    kind = data.get('kind')
    B.need(kind in KINDS, 'Chọn nội quy công khai hay nội bộ nhé.')
    B.need(set(data) <= {'kind', 'text', 'ver'} and 'text' in data, 'Thông tin không hợp lệ.')
    text = clean(kind, data['text'])
    bid = bang['id']
    row = _rows(db, [bid]).get((bid, kind))
    if row and not row['hidden'] and text == row['text'] or not row and not text:
        return dict(message='Không có gì thay đổi.')   # the same text again (a retried tap): nothing written
    B.need(not (row and row['hidden'] and text and text == row['text']), 'Quản trị đã ẩn nội quy này. Viết nội quy khác nhé.', 'code_hidden')
    base = data.get('ver')
    B.need(type(base) is int and base == _ver(row), 'Nội quy vừa được người khác sửa. Xem bản mới rồi sửa lại nhé.', 'code_conflict', 409)
    last = db.execute("SELECT MAX(at) AS t FROM bang_code_hist WHERE bang=? AND kind=? AND what='edit'", (bid, kind)).fetchone()['t']
    B.need(last is None or t - float(last) >= EDIT_GAP, f'Vừa sửa nội quy xong. Chờ {int(EDIT_GAP)} giây rồi sửa tiếp nhé.', 'code_slow')
    n = int(db.execute("SELECT COUNT(*) AS n FROM bang_code_hist WHERE bang=? AND what='edit' AND at>=?", (bid, _day_start(t))).fetchone()['n'])
    B.need(n < EDIT_DAY, f'Hôm nay bang đã sửa nội quy {EDIT_DAY} lần. Mai sửa tiếp nhé.', 'code_slow')
    ver = _ver(row) + 1
    db.execute("INSERT INTO bang_code(bang, kind, text, ver, by_sid, at, hidden, hidden_by, hidden_at) VALUES(?,?,?,?,?,?,0,'',NULL) "
               'ON CONFLICT(bang, kind) DO UPDATE SET text=excluded.text, ver=excluded.ver, by_sid=excluded.by_sid, at=excluded.at, '
               "hidden=0, hidden_by='', hidden_at=NULL", (bid, kind, text, ver, sid, t))
    db.execute("INSERT INTO bang_code_hist(bang, kind, ver, what, text, by_sid, at) VALUES(?,?,?,'edit',?,?,?)", (bid, kind, ver, text, sid, t))
    # the editor has read what they wrote (no badge for them)
    col = 'pub' if kind == 'pub' else 'inn'
    db.execute(f'INSERT INTO bang_code_seen(sid, bang, {col}, at) VALUES(?,?,?,?) '
               f'ON CONFLICT(sid, bang) DO UPDATE SET {col}=GREATEST(bang_code_seen.{col}, excluded.{col}), at=excluded.at', (sid, bid, ver, t))
    who = B._display(db, sid)
    B._log(db, bid, sid, 'code', f'📜 {who} {"xóa" if not text else "cập nhật"} {NAMES[kind]} của bang.', t)
    B._bump(db, bid)
    pids = [x['pid'] for x in B._rows(db, "SELECT pid FROM bang_members WHERE bang=? AND status='in' AND sid<>?", (bid, sid))]
    if pids and text:
        B._notify(db, pids=pids)   # their GET /api/bang/me again: the 📜 Nội quy mới badge
    return dict(message=f'Đã lưu {NAMES[kind]}.' if text else f'Đã xóa {NAMES[kind]}.', ver=ver)


def op_seen(db, sid: str, data: dict, t: float) -> dict:
    """POST /api/bang/code_seen {pub, in}: the versions this member has now read (never more than the current ones,
    never less than what they had read)."""
    me = B._mine(db, sid)
    B.need(me is not None, 'Bạn chưa ở bang nào.', 'not_member')
    bid = me['bang']
    rows = _rows(db, [bid])
    got = {}
    for k in KINDS:
        v = data.get(k)
        got[k] = min(v, _ver(rows.get((bid, k)))) if type(v) is int and v > 0 else 0
    db.execute('INSERT INTO bang_code_seen(sid, bang, pub, inn, at) VALUES(?,?,?,?,?) '
               'ON CONFLICT(sid, bang) DO UPDATE SET pub=GREATEST(bang_code_seen.pub, excluded.pub), '
               'inn=GREATEST(bang_code_seen.inn, excluded.inn), at=excluded.at', (sid, bid, got['pub'], got['in'], t))
    return dict(ok=True, fresh=fresh(db, bid, sid))


# ---------------------------------------------------------------- the operator
def admin_map(db, bids) -> dict:
    """{bang: {pub: {...}, in: {...}}} for the operator's list: the stored text even when hidden."""
    out = {}
    for (b, k), r in _rows(db, bids).items():
        out.setdefault(b, {})[k] = dict(text=str(r['text'] or ''), ver=int(r['ver']), at=float(r['at'] or 0), hidden=bool(r['hidden']),
                                        hidden_by=str(r['hidden_by'] or ''))
    return out


def admin_act(db, bang: dict, op: str, kind, who: str, t: float) -> None:
    """code_hide / code_show of one text (the bang row locked by the caller): the text stays; the version moves (a join
    names the version it read), the bang log and admin_note say who."""
    B.need(kind in KINDS, 'Chọn nội quy công khai hay nội bộ.')
    bid = bang['id']
    row = _rows(db, [bid]).get((bid, kind))
    B.need(row is not None and str(row['text'] or ''), 'Bang này chưa có nội quy đó.', 'none')
    hide = op == 'code_hide'
    if bool(row['hidden']) == hide:
        return
    ver = int(row['ver']) + 1
    db.execute('UPDATE bang_code SET hidden=?, hidden_by=?, hidden_at=?, ver=? WHERE bang=? AND kind=?',
               (1 if hide else 0, who if hide else '', t if hide else None, ver, bid, kind))
    db.execute('INSERT INTO bang_code_hist(bang, kind, ver, what, text, by_sid, at) VALUES(?,?,?,?,?,?,?)',
               (bid, kind, ver, 'hide' if hide else 'show', str(row['text'] or ''), 'admin:' + who, t))
    db.execute('UPDATE bangs SET admin_note=? WHERE id=?', (f'{"ẩn" if hide else "hiện lại"} {NAMES[kind]} bởi {who}'[:200], bid))
    B._log(db, bid, '', 'admin', f'📜 Quản trị {"ẩn" if hide else "hiện lại"} {NAMES[kind]} của bang.', t)


def forget(db, sid: str) -> None:
    """A player erased their data: the texts stay (the bang's), who wrote them goes."""
    for table in ('bang_code', 'bang_code_hist'):
        db.execute(f"UPDATE {table} SET by_sid='' WHERE by_sid=?", (sid,))
