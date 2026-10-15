"""🌳 Cây ước nguyện at chùa Gió Lành: a player writes their own wish, hangs it on one of the trees, everyone reads.

Owner 15/10: "tôi muốn mọi người vào 1 cái cây, rồi ghi cái ước nguyện mình muốn chứ k phải chọn chọn như này, xong
rồi treo lên thôi, và trong đó có rất nhiều cái cây ước nguyện luôn. mọi người xem cây ước nguyện được và xử lý được
tốt ấy, nhìn rõ ràng và có ý nghĩa."

Hanging: the temple's 'nguyen' act with a tree (game/chua.py jr_chua_do {act: 'nguyen', tree, text, color, anon}).
The save gains only what any 'nguyen' gives (did / n / tinh thần): the words never enter the save, so an older build
reads it unchanged. command_commit (the save's own transaction, game/storage.py) writes the row: a refused row (today's
PER_DAY used, a Vietnam day) refuses the whole command, and a replayed request (its receipt) never hangs twice (`key`).
Text: the chat's cleaner and mask (live/filters.py, like 💌 game/wed_invite.py): no control or invisible characters,
phones / links / contacts / heavy words masked; the original stays for admins only (`raw`). Emoji are fine.
Name: the character's name when it was hung, or '' (shown "Ẩn danh") when the player ticked it.
Reading (never the sid): GET /api/chua/trees (the trees, live counts and the last ribbons' colours cached COUNTS_TTL s,
my wishes left today), GET /api/chua/wishes?tree=&before=&limit= (newest first, cursor = id, a partial index per
tree: a tree of thousands stays one index range) or ?mine=1 (all my wishes, any status).
POST /api/chua/wishes {op, id}: 🙏 'pray' (cùng cầu: once per player and wish, chua_wish_prayers), 'report' (the
Phố nghề `reports` table, kind 'wish': HIDE_AFTER players hide it until an admin looks), 'down' (the author takes
their own wish down). Admins (GET/POST /api/admin/wishes): reported ones first, 'hide' / 'show'. Statuses: live,
hidden (reports), removed (admin), down (author). Nothing is deleted, except by the player's own "Xóa dữ liệu" (forget).
Kill switch: MNL_WISH_OFF=1 stops new wishes (reading stays).
Tables (game/pg_schema.py, SCHEMA_VERSION 44): new ones only, no save key: a rollback never sees them.
"""
from __future__ import annotations

import datetime
import os
import re
import secrets
import threading
import time

from .engine import need

TEXT_MIN, TEXT_MAX, TEXT_LINES = 3, 150, 3
PER_DAY = 5               # wishes a player hangs a Vietnam day (owner 15/10: "a few", against spam)
HIDE_AFTER = 3            # reports from different players that hide a wish until an admin looks
COUNTS_TTL = 10.0         # seconds the trees' counts are kept (one small dict per process)
PAGE_MAX = 40
RIBBONS = 14              # colours of the newest ribbons sent per tree (the garden's little trees)
VN = datetime.timezone(datetime.timedelta(hours=7))
# id, name, emoji, what people wish for there (owner 15/10: "rất nhiều cái cây ước nguyện")
TREES = (
    ('binh_an', 'Bình an', '🕊️', 'Bình an cho mình, cho nhà, cho phố'),
    ('gia_dao', 'Gia đạo', '🏡', 'Nhà êm ấm, cha mẹ con cái thuận hòa'),
    ('suc_khoe', 'Sức khỏe', '🌿', 'Mạnh khỏe, mau lành bệnh'),
    ('hoc_hanh', 'Học hành', '📚', 'Học giỏi, thi đâu đỗ đó'),
    ('su_nghiep', 'Sự nghiệp', '💼', 'Công việc suôn sẻ, làm ăn tấn tới'),
    ('tai_loc', 'Tài lộc', '🪙', 'Đủ đầy, may mắn, không nợ nần'),
    ('tinh_duyen', 'Tình duyên', '💞', 'Thương nhau, gặp đúng người'),
    ('uoc_mo', 'Ước mơ', '🌟', 'Điều mình mong một ngày thành thật'),
    ('tuong_nho', 'Tưởng nhớ', '🕯️', 'Gửi lời tới người đã đi xa'),
)
TREE = {t[0]: t for t in TREES}
COLORS = ('do', 'vang', 'hong', 'xanh', 'tim')   # the ribbon: đỏ, vàng, hồng, xanh lá, tím
REASONS = ('spam', 'rude', 'private', 'scam', 'other')   # the Phố nghề report reasons (game/social.py REPORT_REASONS)
STATUSES = ('live', 'hidden', 'removed', 'down')
BAD = 'Tham số cây ước nguyện không hợp lệ.'
_cache = dict(at=0.0, data=None)
_lock = threading.Lock()


def off() -> bool:
    return os.environ.get('MNL_WISH_OFF', '').strip() not in ('', '0')


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%Y-%m-%d')


def _invalidate() -> None:
    with _lock:
        _cache.update(at=0.0, data=None)


# ---------------------------------------------------------------- the reducer's half (game/chua.py, pure)
def clean(text) -> tuple[str, str | None]:
    """(what players see, the original when the mask changed it). GameError when it is not TEXT_MIN..TEXT_MAX."""
    from live import filters
    need(isinstance(text, str), 'Viết điều ước của bạn nhé.', 'bad_wish')
    out = filters.clean(text, TEXT_MAX, TEXT_LINES)
    if out is None:
        stripped = filters.clean(text, TEXT_MAX * 4, TEXT_LINES) or ''
        need(len(stripped) <= TEXT_MAX, f'Điều ước dài tối đa {TEXT_MAX} ký tự thôi nhé.', 'bad_wish')
        need(False, 'Viết điều ước của bạn nhé.', 'bad_wish')
    need(len(out) >= TEXT_MIN, f'Viết ít nhất {TEXT_MIN} ký tự nhé.', 'bad_wish')
    masked = filters.mask(out)
    return masked, (out if masked != out else None)


def parse(p: dict) -> dict:
    """The wish of a jr_chua_do {act: 'nguyen', tree, text, color?, anon?} (the result's `chua_wish`)."""
    need(not off(), 'Cây ước nguyện đang tạm nghỉ, quay lại sau nhé.', 'wish_off')
    need(set(p) <= {'act', 'tree', 'text', 'color', 'anon'}, 'Chọn một việc ở chùa nhé.')
    tree, color, anon = p.get('tree'), p.get('color', 'do'), p.get('anon', False)
    need(isinstance(tree, str) and tree in TREE, 'Chọn một cây để treo điều ước nhé.', 'bad_wish')
    need(isinstance(color, str) and color in COLORS, 'Chọn màu dải lụa nhé.', 'bad_wish')
    need(type(anon) is bool, 'Ẩn danh không hợp lệ.', 'bad_wish')
    text, raw = clean(p.get('text'))
    return dict(key=secrets.token_hex(12), tree=tree, color=color, text=text, raw=raw, anon=anon)


def tree_label(tree: str) -> str:
    return f'Cây {TREE[tree][1]}'


# ---------------------------------------------------------------- the save's transaction (game/storage.py)
def command_commit(db, sid: str, action: str, after: dict, result) -> None:
    w = (result or {}).get('chua_wish') if action == 'jr_chua_do' else None
    if not isinstance(w, dict):
        return
    t = now()
    day = vn_day(t)
    n = db.execute('SELECT count(*) FROM chua_wishes WHERE sid=? AND day=?', (sid, day)).fetchone()[0]
    need(n < PER_DAY, f'Hôm nay bạn đã treo {PER_DAY} điều ước rồi. Mai quay lại treo tiếp nhé 🌙', 'wish_limit')
    name = '' if w['anon'] else ' '.join(str(after.get('name') or '').split())[:40]
    life_day = int(((after.get('journey') or {}).get('life_day')) or 0)
    db.execute('INSERT INTO chua_wishes(key, sid, tree, color, text, raw, name, at, day, life_day) VALUES(?,?,?,?,?,?,?,?,?,?) '
               'ON CONFLICT (key) DO NOTHING', (w['key'], sid, w['tree'], w['color'], w['text'], w['raw'], name, t, day, life_day))
    _invalidate()


# ---------------------------------------------------------------- reading
def _sid(store, db, token: str) -> str:
    from .chua_board import _session
    return _session(store, db, token)[0]


def _summary(store) -> dict:
    """{tree: (live count, [the newest ribbons' colours])}, kept COUNTS_TTL seconds."""
    t = now()
    with _lock:
        if _cache['data'] is not None and t - _cache['at'] < COUNTS_TTL:
            return _cache['data']
    ids = [x[0] for x in TREES]
    with store.connect() as db:
        counts = {r['tree']: int(r['n']) for r in db.execute(
            "SELECT tree, count(*) AS n FROM chua_wishes WHERE status='live' GROUP BY tree")}
        colors = {}
        for r in db.execute("SELECT t.tree, w.color FROM unnest(?::text[]) AS t(tree) CROSS JOIN LATERAL "
                            "(SELECT id, color FROM chua_wishes WHERE tree=t.tree AND status='live' ORDER BY id DESC LIMIT ?) w "
                            'ORDER BY t.tree, w.id DESC', (ids, RIBBONS)):
            colors.setdefault(r['tree'], []).append(r['color'])
    data = {k: (counts.get(k, 0), colors.get(k, [])) for k in ids}
    with _lock:
        _cache.update(at=t, data=data)
    return data


def trees(store, token: str) -> dict:
    """GET /api/chua/trees: the garden."""
    summary = _summary(store)
    with store.connect() as db:
        sid = _sid(store, db, token)
        used = db.execute('SELECT count(*) FROM chua_wishes WHERE sid=? AND day=?', (sid, vn_day(now()))).fetchone()[0]
        mine = db.execute("SELECT count(*) FROM chua_wishes WHERE sid=? AND status<>'down'", (sid,)).fetchone()[0]
    return dict(trees=[dict(id=k, name=name, emoji=emoji, hint=hint, count=summary[k][0], ribbons=summary[k][1])
                       for k, name, emoji, hint in TREES],
                colors=list(COLORS), min=TEXT_MIN, max=TEXT_MAX, per_day=PER_DAY, left=max(0, PER_DAY - int(used)),
                mine=int(mine), total=sum(v[0] for v in summary.values()), off=off())


def parse_query(query: dict) -> dict:
    """GET /api/chua/wishes (parse_qs lists): tree + before + limit, or mine=1 + before + limit."""
    need(set(query) <= {'tree', 'before', 'limit', 'mine'} and all(len(v) == 1 for v in query.values()), BAD)
    out = {}
    for key, (value,) in query.items():
        if key == 'tree':
            need(value in TREE, BAD)
            out['tree'] = value
        elif key == 'mine':
            need(value == '1', BAD)
            out['mine'] = True
        else:
            need(len(value) <= 15 and re.fullmatch(r'[0-9]+', value), BAD)
            out[key] = int(value)
    need(('tree' in out) != bool(out.get('mine')), BAD)
    need(1 <= out.get('limit', 24) <= PAGE_MAX, BAD)
    return out


_ROW = ('SELECT w.id, w.key, w.tree, w.color, w.text, w.name, w.at, w.life_day, w.prayers, w.status, w.sid=? AS mine, '
        'EXISTS(SELECT 1 FROM chua_wish_prayers p WHERE p.wish=w.id AND p.sid=?) AS prayed FROM chua_wishes w ')


def _view(r) -> dict:
    out = dict(id=int(r['id']), tree=r['tree'], color=r['color'], text=r['text'], name=r['name'], at=int(r['at']),
               day=int(r['life_day']), prayers=int(r['prayers']), mine=bool(r['mine']), prayed=bool(r['prayed']))
    if r['mine']:
        out.update(key=r['key'], status=r['status'])
    return out


def page(store, token: str, *, tree: str | None = None, mine: bool = False, before: int | None = None, limit: int = 24) -> dict:
    """Newest first. A tree: its live wishes, without those I reported. Mine: all of mine, any status."""
    from .social import pid_of
    cursor = before if before is not None else 2**62
    with store.connect() as db:
        sid = _sid(store, db, token)
        if mine:
            rows = db.execute(_ROW + 'WHERE w.sid=? AND w.id<? ORDER BY w.id DESC LIMIT ?',
                              (sid, sid, sid, cursor, limit + 1)).fetchall()
        else:
            rows = db.execute(_ROW + "WHERE w.tree=? AND w.status='live' AND w.id<? AND NOT EXISTS (SELECT 1 FROM reports r "
                              "WHERE r.reporter=? AND r.kind='wish' AND r.target=w.id::text) ORDER BY w.id DESC LIMIT ?",
                              (sid, sid, tree, cursor, pid_of(sid), limit + 1)).fetchall()
    shown = rows[:limit]
    return dict(rows=[_view(r) for r in shown], before=int(shown[-1]['id']) if len(rows) > limit else None)


# ---------------------------------------------------------------- 🙏 cùng cầu, báo cáo, gỡ xuống
def act(store, token: str, d: dict) -> dict:
    """POST /api/chua/wishes {op: pray | report | down, id, reason?}: the wish as the reader now sees it."""
    from .social import pid_of
    need(isinstance(d, dict) and d.get('op') in ('pray', 'report', 'down'), BAD)
    op, wid = d['op'], d.get('id')
    need(type(wid) is int and 1 <= wid <= 2**62, BAD)
    need(set(d) <= {'op', 'id', 'reason'} and (op == 'report' or 'reason' not in d), BAD)
    reason = d.get('reason', 'other')
    need(reason in REASONS, 'Lý do không hợp lệ.')
    t = now()

    def run(db):
        sid = _sid(store, db, token)
        w = db.execute('SELECT sid, status FROM chua_wishes WHERE id=? FOR UPDATE', (wid,)).fetchone()
        need(w is not None and (w['status'] == 'live' or w['sid'] == sid and op == 'down'), 'Điều ước này không còn trên cây.', 'gone')
        own = w['sid'] == sid
        message = ''
        if op == 'pray':
            need(not own, 'Đây là điều ước của bạn mà 🙂')
            if db.execute('INSERT INTO chua_wish_prayers(wish, sid, at) VALUES(?,?,?) ON CONFLICT DO NOTHING', (wid, sid, t)).rowcount:
                db.execute('UPDATE chua_wishes SET prayers=prayers+1 WHERE id=?', (wid,))
            message = '🙏 Bạn đã cùng cầu cho điều ước này.'
        elif op == 'report':
            need(not own, 'Bạn không cần báo cáo điều ước của mình.')
            if db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?,'wish',?,?,?) ON CONFLICT DO NOTHING",
                          (pid_of(sid), str(wid), reason, t)).rowcount:
                db.execute("UPDATE chua_wishes SET reports=reports+1, status=CASE WHEN reports+1>=? AND status='live' "
                           "THEN 'hidden' ELSE status END WHERE id=?", (HIDE_AFTER, wid))
            message = 'Cảm ơn bạn. Điều ước này sẽ không hiện với bạn nữa và sẽ được xem xét.'
        else:
            need(own, 'Chỉ người treo mới gỡ được điều ước này.')
            db.execute("UPDATE chua_wishes SET status='down' WHERE id=? AND status IN ('live','hidden')", (wid,))
            message = 'Bạn đã gỡ điều ước xuống. Chỉ mình bạn còn thấy nó trong “Của tôi”.'
        r = db.execute(_ROW + 'WHERE w.id=?', (sid, sid, wid)).fetchone()
        return dict(message=message, wish=_view(r))
    out = store.transaction(run)
    if op != 'pray':
        _invalidate()
    return out


# ---------------------------------------------------------------- admins, privacy
def admin_view(store) -> dict:
    """GET /api/admin/wishes: reported wishes not looked at yet first, then the newest (the original when masked)."""
    with store.connect() as db:
        rows = db.execute('(SELECT w.*, a.username FROM chua_wishes w LEFT JOIN accounts a ON a.sid=w.sid '
                          'WHERE w.reports>0 AND w.reviewed_at IS NULL ORDER BY w.id DESC LIMIT 100) UNION ALL '
                          '(SELECT w.*, a.username FROM chua_wishes w LEFT JOIN accounts a ON a.sid=w.sid '
                          'WHERE NOT (w.reports>0 AND w.reviewed_at IS NULL) ORDER BY w.id DESC LIMIT 60)').fetchall()
        reasons = {}
        ids = [str(r['id']) for r in rows if r['reports']]
        if ids:
            for x in db.execute("SELECT target, reason, count(*) AS n FROM reports WHERE kind='wish' AND target=ANY(?) "
                                'GROUP BY target, reason', (ids,)):
                reasons.setdefault(x['target'], {})[x['reason']] = int(x['n'])
    return dict(off=off(), items=[dict(id=int(r['id']), tree=r['tree'], tree_name=tree_label(r['tree']) if r['tree'] in TREE else r['tree'],
                                       text=r['text'], raw=r['raw'], name=r['name'], username=r['username'] or '', at=float(r['at']),
                                       status=r['status'], reports=int(r['reports']), reasons=reasons.get(str(r['id']), {}),
                                       prayers=int(r['prayers']), reviewed=r['reviewed_at'] is not None, by=r['by_admin'] or '')
                                  for r in rows])


def admin_act(store, admin: str, d: dict) -> dict:
    """POST /api/admin/wishes {act: hide | show, id}: hide = 'removed' (never shown again); show = live again
    (a wish the author took down stays down)."""
    wid = d.get('id') if isinstance(d, dict) else None
    need(isinstance(d, dict) and d.get('act') in ('hide', 'show') and type(wid) is int and wid >= 1, 'Thao tác không hợp lệ.', 'bad_admin')
    status = 'removed' if d['act'] == 'hide' else 'live'
    n = store.transaction(lambda db: db.execute("UPDATE chua_wishes SET status=?, reviewed_at=?, by_admin=? WHERE id=? AND status<>'down'",
                                                (status, now(), str(admin)[:40], wid)).rowcount)
    _invalidate()
    return dict(ok=True, changed=bool(n), status=status)


def forget(store, token: str) -> None:
    """Account deletion ("XOA"): this player's wishes and their 🙏."""
    sid = store.key(token)

    def run(db):
        db.execute('DELETE FROM chua_wish_prayers WHERE wish IN (SELECT id FROM chua_wishes WHERE sid=?)', (sid,))
        db.execute('DELETE FROM chua_wish_prayers WHERE sid=?', (sid,))
        db.execute('DELETE FROM chua_wishes WHERE sid=?', (sid,))
    store.transaction(run)
    _invalidate()

