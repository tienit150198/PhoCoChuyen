"""Player rental market: prepaid, voluntary five-tenant-life-day contracts.

Authoritative rows and both wallets commit together after sorted session locks.
Only the tenant can leave early (unused days are non-refundable) or buy an extra
period. Owners cannot evict during a paid period. Once it is over by the wall
clock (F#225: an inactive tenant's life days never run out), the owner may
reclaim the home: see reclaim_why. Reducer commit hooks inspect only the
already-locked session and rental rows; they never lock another save.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import time

from . import archive as ar
from . import estates as es
from . import housing as hs
from . import marriage as mr

PERIOD = hs.MONTH_DAYS
TERMS = ('Trả trước 5 ngày sống của người thuê. Tự gia hạn; không tự trừ tiền. Trả nhà sớm không hoàn tiền những ngày còn lại. '
         'Chủ nhà không thể lấy lại nhà giữa kỳ; chỉ lấy lại sau kỳ đã trả: quá 5 ngày thật kể từ lần trả gần nhất, '
         'hoặc người thuê vắng 3 ngày thật mà chưa trả trước kỳ sau.')
DAY_S = 86400
REAL_DAYS = PERIOD          # F#225: a paid period, by the wall clock, lasts this many real days after the payment
IDLE_DAYS = 3               # ... or ends when the tenant has not played for this long and holds no further prepaid period
VN = datetime.timezone(datetime.timedelta(hours=7))
RID = re.compile(r'[A-Za-z0-9_-]{8,64}')


class RentalError(mr.MarriageError):
    pass


def need(ok, text, code='rental_error', status=400):
    if not ok:
        raise RentalError(text, code, status)


def _who(store, token):
    sid, name = mr.whoami(store, token)
    need(sid and name, 'Tạo tài khoản để thuê hoặc cho người chơi thuê nhà nhé.', 'account_required', 403)
    return sid, name


def _pid(sid):
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def _blocked(db, a, b):
    pa, pb = _pid(a), _pid(b)
    return mr._blocked(db, a, b) or bool(db.execute(
        'SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?)',
        (pa, pb, pb, pa)).fetchone())


def _marker(row):
    return {k: row[k] for k in ('id', 'kind', 'rent', 'start_day', 'end_day')}


def paid_until(row) -> float:
    """When the paid period is over by the wall clock: REAL_DAYS after the last payment (accept / renew set `updated`)."""
    return float(row['updated']) + REAL_DAYS * DAY_S


def _date(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%d/%m')


def reclaim_why(row, tenant_day: int, idle: bool, now: float) -> str | None:
    """None when the owner may take the home back (F#225), else why not. Never during a paid period: the period is over
    REAL_DAYS after the last payment, or as soon as the tenant has been away IDLE_DAYS without a further prepaid period.
    A further period bought ahead (renew) is honoured to its own end: twice REAL_DAYS after that payment."""
    if row['status'] != 'leased':
        return 'Nhà này không còn cho thuê.'
    if row['end_day'] - tenant_day > PERIOD:
        end = float(row['updated']) + 2 * REAL_DAYS * DAY_S
        return None if now > end else f'Người thuê đã trả trước thêm một kỳ, tới ngày {_date(end)}.'
    if now > paid_until(row) or idle:
        return None
    return f'Người thuê đã trả tới ngày {_date(paid_until(row))}. Chưa thể lấy lại nhà giữa kỳ.'


def _idle(db, sid) -> bool:
    """The tenant's save has not been written for IDLE_DAYS (sessions.updated_at, as storage.prune reads it)."""
    from . import db as dbm
    r = db.execute(f'SELECT updated_at<{dbm.UTC_INTERVAL_TEXT} AS idle FROM sessions WHERE sid=?', (f'-{IDLE_DAYS} days', sid)).fetchone()
    return bool(r and r['idle'])


def _view(row, reclaim=None):
    home = hs.HOMES[row['kind']]
    reference = hs.rent_of(row['kind'])
    out = dict(id=row['id'], property=row['property'], kind=row['kind'], name=home['name'], emoji=home['emoji'],
               owner_name=row.get('current_owner', row['owner_name']), tenant_name=row.get('current_tenant', row['tenant_name']), rent=row['rent'],
               status=row['status'], start_day=row['start_day'], end_day=row['end_day'], period_days=PERIOD,
               market_rent=reference, demand_pct=hs.demand(row['rent'], reference),
               market_news=hs.pm.quote(row['kind'])['news'])
    if reclaim is not None:   # the owner's own leased row: when the paid period ends, and whether it may be reclaimed now
        out.update(paid_until=paid_until(row), reclaim=reclaim)
    return out


def get(store, token, state=None, offset=0):
    need(type(offset) is int and 0 <= offset <= 10**6, 'Trang tin thuê nhà không hợp lệ.', 'bad_offset')
    sid, display = mr.whoami(store, token)
    if not sid or not display:
        return dict(market=[], next_offset=None, mine=[], tenancy=None, locked='Tạo tài khoản để thuê và cho người chơi thuê nhà.',
                    rules=dict(period_days=PERIOD, clock='tenant_life_day', prepaid=True, refundable=False, terms=TERMS))
    # No save scan: indexed listings plus this account's own rows.
    select = "SELECT r.*, COALESCE(oa.display,r.owner_name) AS current_owner, COALESCE(ta.display,r.tenant_name) AS current_tenant FROM rentals r LEFT JOIN accounts oa ON oa.sid=r.owner LEFT JOIN accounts ta ON ta.sid=r.tenant "
    with store.connect() as db:
        rows = mr._rows(db, select + "WHERE r.status='listing' AND r.owner<>? "
                        "AND NOT EXISTS (SELECT 1 FROM marriage_blocks b WHERE (b.sid=? AND b.target=r.owner) "
                        "OR (b.sid=r.owner AND b.target=?)) "
                        "AND NOT EXISTS (SELECT 1 FROM blocks cb WHERE "
                        "(cb.pid=substring(encode(sha256(convert_to('pid:' || r.owner,'UTF8')),'hex'),1,16) AND cb.target=?) "
                        "OR (cb.target=substring(encode(sha256(convert_to('pid:' || r.owner,'UTF8')),'hex'),1,16) AND cb.pid=?)) "
                        "ORDER BY r.at DESC,r.id DESC LIMIT 101 OFFSET ?", (sid, sid, sid, _pid(sid), _pid(sid), offset))
        mine = mr._rows(db, select + "WHERE r.owner=? ORDER BY CASE WHEN r.status IN ('listing','leased') THEN 0 ELSE 1 END,r.at DESC LIMIT 40", (sid,))
        tenancy = mr._row(db, select + "WHERE r.tenant=? AND r.status='leased'", (sid,))
        t = time.time()
        # Shown, not decided: act() checks again with the tenant's save (a further period bought ahead waits longer).
        reclaim = {r['id']: t > paid_until(r) or _idle(db, r['tenant']) for r in mine if r['status'] == 'leased'}
    return dict(market=[_view(r) for r in rows[:100]], next_offset=offset + 100 if len(rows) > 100 else None,
                mine=[_view(r, reclaim.get(r['id'])) for r in mine],
                tenancy=_view(tenancy) if tenancy else None,
                rules=dict(period_days=PERIOD, clock='tenant_life_day', prepaid=True, refundable=False, terms=TERMS))


def _available(s, prop):
    h = hs.get(s)
    x = hs.find(h, prop)
    need(x and x in h['props'], 'Chọn căn nhà đang để trống, bạn không ở trong đó.', 'not_available')
    need(not x['let'], 'Căn này đang có khách NPC thuê.', 'not_available')
    need(not x['joint'], 'Nhà mua bằng quỹ chung cần giữ quyền của cả hai, chưa thể cho thuê.', 'joint_home')
    need(not s['journey'].get('rental_ads', {}).get(prop, {}).get('active'),
         'Gỡ tin cho NPC thuê căn này trước nhé.', 'npc_listing')
    return x


def _pay(tenant, owner, rent, owner_box):
    have = hs._have(tenant)
    need(have['wallet'] + have['balance'] >= rent, 'Ví và tài khoản chưa đủ tiền trả trước kỳ thuê.', 'not_enough')
    hs._take(tenant, rent, 'Trả trước tiền thuê nhà người chơi', tenant['journey']['life_day'])
    with owner_box:
        hs._receive(owner, rent, 'Tiền cho người chơi thuê nhà', owner['journey']['life_day'])


def act(store, token, action, data):
    """All mutation and replay checks execute under the actor's session row lock."""
    from .engine import migrate_state, validate_state, public_state
    from .storage import serialize, _write_archive, _archive_rows
    sid, display = _who(store, token)
    need(action in ('listing', 'accept', 'renew', 'leave', 'cancel', 'reclaim'), 'Thao tác thuê nhà không hợp lệ.', 'unknown_action')
    need(isinstance(data, dict) and isinstance(data.get('rid'), str) and RID.fullmatch(data['rid']),
         'Mã thao tác không hợp lệ. Tải lại trang nhé.', 'bad_rid')
    rid = data['rid']
    fp = hashlib.sha256(json.dumps([action, data], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    # Read immutable owner identity before locking; all statuses are checked again inside.
    other = None
    if action != 'listing':
        need(isinstance(data.get('id'), str), 'Chọn tin thuê nhà.', 'not_found')
        with store.connect() as db:
            peek = mr._row(db, 'SELECT * FROM rentals WHERE id=?', (data['id'],))
        need(peek, 'Tin thuê nhà không còn tồn tại.', 'not_found', 404)
        other = peek['owner']
        if action == 'reclaim':   # the owner acts; the tenant's save is the other one (checked again under the row lock)
            need(peek['owner'] == sid, 'Chỉ chủ nhà được lấy lại nhà.', 'forbidden', 403)
            need(peek['tenant'], 'Nhà này chưa có người thuê.', 'not_available', 409)   # status: checked under the lock (a replay sees 'ended')
            other = peek['tenant']
    identities = sorted({sid, other} - {None})
    with store.connect() as db:
        db.begin()
        store._patient(db)
        saved = {}
        for key in identities:
            r = db.execute('SELECT state,revision FROM sessions WHERE sid=? FOR UPDATE', (key,)).fetchone()
            need(r, 'Tiến trình của một người chơi không còn tồn tại.', 'session_missing', 404)
            saved[key] = r
        for key in identities:
            need(not db.execute('SELECT 1 FROM rental_closed_accounts WHERE sid=?', (key,)).fetchone(),
                 'Tài khoản này đang được xóa dữ liệu.', 'account_closed', 403)
        old = mr._row(db, 'SELECT * FROM rental_receipts WHERE sid=? AND rid=?', (sid, rid))
        if old:
            need(old['fingerprint'] == fp, 'Mã thao tác đã dùng cho nội dung khác.', 'idempotency_conflict', 409)
            result = json.loads(old['result'])
            result.update(changed=False, replayed=True)
        else:
            states = {key: migrate_state(store.parse_state(r['state'], key), owned=True) for key, r in saved.items()}
            for key, s in states.items():
                need(s['journey'].get('story') or action == 'reclaim' and key != sid, 'Thuê nhà chỉ có trong hành trình.', 'story_only')
                need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (key,)).fetchone(), 'Cả hai cần có tài khoản.', 'account_required', 403)
            cuts = {}
            owner_box = ar.collect()
            before = {k: dict(s['careers']) for k, s in states.items()}
            with ar.collect() as box:
                actor = states[sid]
                j = actor['journey']
                moved = sid   # whose home changed (deco bags furniture on a changed place)
                if action == 'listing':
                    prop, rent = data.get('property'), data.get('rent')
                    need(isinstance(prop, str), 'Chọn căn nhà.', 'bad_property')
                    need(type(rent) is int and 1 <= rent <= 10**9, 'Giá thuê phải là số xu nguyên dương.', 'bad_rent')
                    x = _available(actor, prop)
                    need(not db.execute("SELECT 1 FROM rentals WHERE owner=? AND property=? AND status IN ('listing','leased')", (sid, prop)).fetchone(),
                         'Căn này đã có tin hoặc hợp đồng thuê. Gỡ tin trước khi đổi giá.', 'already_listed', 409)
                    lid = 'rent-' + hashlib.sha256(f'{sid}|{rid}'.encode()).hexdigest()[:24]
                    db.execute("INSERT INTO rentals(id,owner,property,kind,owner_name,rent,status,at,updated) VALUES(?,?,?,?,?,?,'listing',?,?)",
                               (lid, sid, prop, x['kind'], display, rent, time.time(), time.time()))
                    result = dict(message='Đã đăng tin cho người chơi thuê nhà.', id=lid, changed=True)
                else:
                    row = mr._row(db, 'SELECT * FROM rentals WHERE id=? FOR UPDATE', (data['id'],))
                    need(row, 'Không tìm thấy tin thuê nhà.', 'not_found', 404)
                    owner = states[row['owner']]
                    if action == 'reclaim':
                        need(sid == row['owner'], 'Chỉ chủ nhà được lấy lại nhà.', 'forbidden', 403)
                        need(row['status'] == 'leased' and row['tenant'] == other, 'Nhà này không còn cho thuê.', 'not_available', 409)
                        tenant = states[other]
                        tj = tenant['journey']
                        why = reclaim_why(row, int(tj.get('life_day', 0)), _idle(db, other), time.time())
                        need(why is None, why or '', 'paid_period', 409)
                        db.execute("UPDATE rentals SET status='ended',updated=? WHERE id=? AND status='leased'", (time.time(), row['id']))
                        home = hs.HOMES[row['kind']]['name']
                        tenant_name = row.get('current_tenant') or row['tenant_name'] or 'Người thuê'
                        with owner_box:   # the tenant's rows cut here go to the tenant's archive
                            if (tj.get('rental') or {}).get('id') == row['id']:
                                tj.pop('rental', None)
                            th = hs.get(tenant)
                            if th:
                                hs._log(th, tj['life_day'], f'Hết kỳ thuê {hs.lname(home)}: chủ nhà đã lấy lại nhà. Tìm chỗ ở mới nhé.')
                        oh = hs.get(actor)
                        if oh:
                            hs._log(oh, j['life_day'], f'Lấy lại {hs.lname(home)} sau kỳ thuê của {tenant_name}.')
                        from . import social
                        social.notify(store, db, _pid(other), 'rental',
                                      f'🏠 Hết kỳ thuê {hs.lname(home)}: {display} đã lấy lại nhà. Không trừ thêm tiền; tìm chỗ ở mới nhé.')
                        moved = other
                        result = dict(message=f'Đã lấy lại {hs.lname(home)}. {tenant_name} được báo dọn đi, không mất thêm tiền.', changed=True)
                    elif action == 'cancel':
                        need(sid == row['owner'], 'Chỉ chủ nhà được gỡ tin.', 'forbidden', 403)
                        need(row['status'] in ('listing', 'cancelled'), 'Hợp đồng đã trả trước không thể bị chủ nhà hủy giữa kỳ.', 'active_lease', 409)
                        db.execute("UPDATE rentals SET status='cancelled',updated=? WHERE id=?", (time.time(), row['id']))
                        result = dict(message='Đã gỡ tin cho thuê.', changed=True)
                    elif action == 'accept':
                        need(sid != row['owner'], 'Bạn không thể thuê nhà của chính mình.', 'self_rent')
                        need(row['status'] == 'listing', 'Căn nhà đã được thuê hoặc tin đã được gỡ.', 'not_available', 409)
                        need(not _blocked(db, sid, row['owner']), 'Không thể thuê nhà của người này.', 'blocked', 403)
                        need(not db.execute("SELECT 1 FROM rentals WHERE tenant=? AND status='leased'", (sid,)).fetchone(),
                             'Bạn đang có một hợp đồng thuê. Trả nhà trước nhé.', 'active_lease', 409)
                        need(not hs.active_lease(j), 'Bạn đang thuê nhà người chơi.', 'active_lease')
                        x = _available(owner, row['property'])
                        need(x['kind'] == row['kind'], 'Căn nhà đã thay đổi.', 'not_available')
                        # Require the displayed price when supplied by clients.
                        need(data.get('rent', row['rent']) == row['rent'], 'Giá thuê đã thay đổi.', 'stale_quote', 409)
                        _pay(actor, owner, row['rent'], owner_box)
                        h = hs._ensure(actor)
                        if h['own']:
                            hs._move_out(actor, h, j['life_day'])
                        if h['rent']:
                            hs._leave_rent(actor, h, j['life_day'])
                        h['shared'] = None
                        es.move_out(j)   # 🏰 out of a villa bought in Mua sắm too (game/estates.py move_out)
                        row.update(status='leased', tenant=sid, tenant_name=display, start_day=j['life_day'], end_day=j['life_day'] + PERIOD)
                        j['rental'] = _marker(row)
                        db.execute("UPDATE rentals SET status='leased',tenant=?,tenant_name=?,start_day=?,end_day=?,updated=? WHERE id=?",
                                   (sid, display, row['start_day'], row['end_day'], time.time(), row['id']))
                        result = dict(message='Đã trả trước tiền thuê và dọn vào nhà. ' + TERMS, changed=True)
                    else:
                        need(row['tenant'] == sid, 'Chỉ người thuê được thao tác hợp đồng này.', 'forbidden', 403)
                        if action == 'leave':
                            need(row['status'] in ('leased', 'left', 'expired'), 'Hợp đồng không còn hiệu lực.', 'not_available')
                            if row['status'] == 'leased':
                                db.execute("UPDATE rentals SET status='left',updated=? WHERE id=?", (time.time(), row['id']))
                            if j.get('rental', {}).get('id') == row['id']:
                                j.pop('rental', None)
                            result = dict(message='Đã trả nhà. Tiền thuê trả trước của kỳ hiện tại không hoàn lại; đồ đạc vẫn thuộc về bạn.', changed=True)
                        else:
                            need(row['status'] == 'leased' and j['life_day'] < row['end_day'], 'Hợp đồng đã hết hạn. Chọn tin mới để thuê nhé.', 'expired', 409)
                            need(not _blocked(db, sid, row['owner']), 'Không thể gia hạn với người này.', 'blocked', 403)
                            need(j.get('rental') == _marker(row), 'Tiến trình thuê nhà đã thay đổi.', 'lease_mismatch', 409)
                            # Bound prepaid exposure to one further period per current period.
                            need(row['end_day'] - j['life_day'] <= PERIOD, 'Bạn đã trả trước kỳ tiếp theo rồi.', 'already_renewed', 409)
                            _available(owner, row['property'])
                            _pay(actor, owner, row['rent'], owner_box)
                            row['end_day'] += PERIOD
                            j['rental'] = _marker(row)
                            db.execute('UPDATE rentals SET end_day=?,updated=? WHERE id=?', (row['end_day'], time.time(), row['id']))
                            result = dict(message='Đã trả trước và gia hạn thêm 5 ngày sống của bạn.', changed=True)
                # Reducer reconciliation bags furniture on a changed place without deleting ownership.
                from . import deco
                for key, s in states.items():
                    if key == moved == sid:
                        deco.on_life_day(s)
                    elif key == moved:
                        with owner_box:   # reclaim: the tenant's rows go to the tenant's archive
                            deco.on_life_day(s)
                    validate_state(s)
                    mr.validate_save(s)
            # Owner and tenant history tails are collected separately.
            for key, s in states.items():
                cuts[key] = _archive_rows(box if key == sid else owner_box, before[key], s, '')
                db.execute('UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?',
                           (serialize(s, None, True), saved[key]['revision'] + 1, key))
                _write_archive(db, key, cuts[key])
            db.execute('INSERT INTO rental_receipts(sid,rid,fingerprint,result) VALUES(?,?,?,?)',
                       (sid, rid, fp, json.dumps(result, ensure_ascii=False)))
        db.commit()
    result['rentals'] = get(store, token)
    state, revision, _ = store.read(token)
    result.update(state=public_state(state), revision=revision)
    return result


def command_commit(db, sid, before, after, action):
    """Contract guard inside Store's existing session lock; never acquire a second session."""
    from .engine import need as check
    rows = mr._rows(db, "SELECT * FROM rentals WHERE (owner=? OR tenant=?) AND status IN ('listing','leased')", (sid, sid))
    j = after.get('journey') or {}
    before_j = before.get('journey') or {}
    # Imports/resets cannot remove or mint contractual rights or roll back the lease clock.
    if action in ('import_save', 'reset', 'reset_all', 'new_game'):
        check(not rows, 'Gỡ tin và kết thúc hợp đồng thuê trước khi khôi phục hoặc đặt lại tiến trình.', 'active_lease')
        check(not j.get('rental'), 'Bản lưu không thể khôi phục hợp đồng thuê người chơi.', 'invalid_save')
    active = next((r for r in rows if r['tenant'] == sid and r['status'] == 'leased'), None)
    if active:
        check(j.get('life_day', 0) >= before_j.get('life_day', 0), 'Không thể lùi ngày sống trong hợp đồng thuê.', 'active_lease')
        if j.get('life_day', 0) >= active['end_day']:
            check(not hs.active_lease(j), 'Hợp đồng thuê đã hết hạn.', 'lease_mismatch')
            db.execute("UPDATE rentals SET status='expired',updated=? WHERE id=? AND status='leased'", (time.time(), active['id']))
        else:
            check(j.get('rental') == _marker(active), 'Hãy dùng thao tác trả nhà để kết thúc hợp đồng thuê.', 'active_lease')
    else:
        check(not hs.active_lease(j), 'Hợp đồng thuê không tồn tại trên máy chủ.', 'lease_mismatch')
    for row in rows:
        if row['owner'] != sid:
            continue
        h = hs.get(after)
        x = hs.find(h, row['property'])
        ok = x and x in h['props'] and x['kind'] == row['kind'] and not x['let'] and not x['joint']
        ok = ok and not j.get('rental_ads', {}).get(row['property'], {}).get('active')
        if row['status'] == 'leased':
            check(ok, 'Nhà đang có hợp đồng thuê người chơi: chưa thể bán, dọn vào hay cho NPC thuê.', 'active_lease')
        elif not ok:
            db.execute("UPDATE rentals SET status='cancelled',updated=? WHERE id=? AND status='listing'", (time.time(), row['id']))


def prepare_delete(store, token):
    sid = store.key(token)
    with store.connect() as db:
        db.begin()
        db.execute('SELECT 1 FROM sessions WHERE sid=? FOR UPDATE', (sid,))
        freeze_account(db, sid)


def freeze_account(db, sid):
    from .engine import need as check
    check(not db.execute("SELECT 1 FROM rentals WHERE (owner=? OR tenant=?) AND status='leased'", (sid, sid)).fetchone(),
          'Kết thúc hợp đồng thuê người chơi trước khi xóa dữ liệu.', 'active_lease')
    db.execute('INSERT INTO rental_closed_accounts(sid) VALUES(?) ON CONFLICT DO NOTHING', (sid,))


def forget(db, sid):
    """Privacy deletion closes listings; leased assets must be returned beforehand."""
    freeze_account(db, sid)
    db.execute("UPDATE rentals SET status='cancelled',owner_name='Người chơi đã xóa' WHERE owner=? AND status='listing'", (sid,))
    db.execute("UPDATE rentals SET owner_name='Người chơi đã xóa' WHERE owner=?", (sid,))
    db.execute("UPDATE rentals SET tenant_name='Người chơi đã xóa' WHERE tenant=?", (sid,))
    db.execute('DELETE FROM rental_receipts WHERE sid=?', (sid,))


def validate(s):
    from .engine import need as check, integer
    j = s['journey']
    lease = j.get('rental')
    if lease is not None:
        check(isinstance(lease, dict) and set(lease) == {'id', 'kind', 'rent', 'start_day', 'end_day'}, 'Dữ liệu thuê nhà không hợp lệ.', 'invalid_save')
        check(isinstance(lease['id'], str) and re.fullmatch(r'rent-[a-f0-9]{24}', lease['id']) and lease['kind'] in hs.OWN,
              'Hợp đồng thuê không hợp lệ.', 'invalid_save')
        integer(lease['rent'], 1, 10**9)
        integer(lease['start_day'], 1, 10**6)
        integer(lease['end_day'], lease['start_day'] + PERIOD, 10**6 + PERIOD * 2)
    bases = j.get('property_market_basis', {})
    check(isinstance(bases, dict) and len(bases) <= hs.OWNED_MAX, 'Giá mua nhà không hợp lệ.', 'invalid_save')
    for hid, bp in bases.items():
        check(isinstance(hid, str), 'Mã nhà không hợp lệ.', 'invalid_save')
        integer(bp, 5500, 16500)
    ads = j.get('rental_ads', {})
    check(isinstance(ads, dict) and len(ads) <= hs.OWNED_MAX, 'Tin thuê nhà không hợp lệ.', 'invalid_save')
    for hid, ad in ads.items():
        check(isinstance(hid, str) and isinstance(ad, dict) and set(ad) == {'rent', 'since', 'checked', 'active'}, 'Tin thuê nhà không hợp lệ.', 'invalid_save')
        integer(ad['rent'], 1, 10**9)
        integer(ad['since'], 1, 10**6)
        integer(ad['checked'], ad['since'], 10**6)
        check(type(ad['active']) is bool, 'Tin thuê nhà không hợp lệ.', 'invalid_save')
