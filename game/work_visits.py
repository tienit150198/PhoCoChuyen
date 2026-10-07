"""Private-by-default workplaces and verified, escrow-backed player services.

Only allowlisted display fields enter place snapshots. Money lives in saves and
escrow rows; accepting an order binds a real career/quay task. A committed game
transition can mark it ready, while a separate guarded transaction pays once.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
import time

from . import marriage as mr, social

VISIBILITY = ('friends', 'public', 'closed')
TAGS = ('friendly', 'careful', 'quick', 'good_value')
ACTIVE = ('requested', 'accepted')
FINAL = ('completed', 'cancelled', 'declined', 'failed')
LIMIT = 60


class WorkVisitError(mr.MarriageError):
    pass


def need(ok, message, code='work_visit_error', status=400):
    if not ok:
        raise WorkVisitError(message, code, status)


def _clean(value, limit, minimum=0):
    try:
        return social.clean(value, limit, minimum)
    except social.SocialError as exc:
        raise WorkVisitError(str(exc), getattr(exc, 'code', 'bad_text')) from exc


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _data(row):
    return json.loads(row['data']) if row and row.get('data') else {}


def _bridge():
    from . import player_service_tasks
    return player_service_tasks


def _ack(state, order_id, cancelled=False):
    acknowledge = getattr(_bridge(), 'acknowledge', None)
    if acknowledge:
        acknowledge(state, order_id, **({'outcome': 'cancelled'} if cancelled else {}))


def _row(db, sql, args=()):
    return mr._row(db, sql, args)


def _rows(db, sql, args=()):
    return mr._rows(db, sql, args)


def _person(db, sid):
    p = _row(db, 'SELECT name,avatar FROM profiles WHERE sid=?', (sid,)) or {}
    code = _row(db, 'SELECT code FROM marriage_people WHERE sid=?', (sid,)) or {}
    face = _row(db, 'SELECT code FROM chat_faces WHERE pid=?', (social.pid_of(sid),)) or {}
    return dict(pid=social.pid_of(sid), name=str(p.get('name') or mr._display(db, sid))[:40],
                code=code.get('code', ''), avatar=str(p.get('avatar') or '🙂')[:80], fc=str(face.get('code') or '')[:100])


def _blocked(db, a, b):
    return mr._blocked(db, a, b) or social._blocked(db, social.pid_of(a), social.pid_of(b))


def _accessible(db, row, me):
    if row['owner'] == me:
        return True
    if _blocked(db, me, row['owner']) or row['visibility'] == 'closed':
        return False
    return row['visibility'] == 'public' or bool(db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (me, row['owner'])).fetchone())


def _place_id(owner, kind, target):
    return 'wp_' + hashlib.sha256(f'work-visit|{owner}|{kind}|{target}'.encode()).hexdigest()[:24]


def _offer_view(offer):
    """Canonical authored offers may carry private task details: project explicitly."""
    if not isinstance(offer, dict) or not isinstance(offer.get('offer_id'), str):
        return None
    price = offer.get('price')
    if type(price) is not int or not 1 <= price <= 1000000:
        return None
    result = dict(offer_id=offer['offer_id'][:160], price=price, label=str(offer.get('label') or 'Dịch vụ')[:120])
    for key in ('career', 'digest', 'dish', 'description'):
        if isinstance(offer.get(key), str):
            result[key] = offer[key][:160]
    if offer.get('staffed') is True:
        result['staffed'] = True
    return result


def _activity(c):
    active = next((t for t in c.get('tasks', []) if t.get('id') == c.get('active_task')), None)
    tasks = [t for t in c.get('tasks', []) if t.get('day') == c.get('day')]
    label = 'Đang nghỉ' if not c.get('open') else 'Đang thực hiện yêu cầu' if active and active.get('known') else 'Đang đón và hỏi khách'
    return dict(label=label,
                status='working' if c.get('open') else 'resting',
                tasktitle=str((active or {}).get('title', ''))[:120],
                progress=dict(done=sum(t.get('status') == 'completed' for t in tasks), total=len(tasks)))


def places(state):
    """[(kind, target, snapshot without its owner)] of a save's places: the save's part of sync(),
    no database. The storage layer computes it before it takes the save's row lock (Store._store),
    so the commit holds the lock only for the database part. Snapshots are written with sorted
    keys (_json), so the owner added afterwards gives the same text."""
    from .content import CAREER_META
    from . import quay, quay_self
    out = []
    bridge = _bridge()
    for career, c in state.get('careers', {}).items():
        if career not in CAREER_META or not c.get('started'):
            continue
        meta = CAREER_META[career]
        source = bridge.offers(state, career) if state.get('current') == career else getattr(bridge, 'staff_offers', lambda s,c: [])(state, career)
        offers = [v for o in source if (v := _offer_view(o)) is not None][:8]
        out.append(('career', career, dict(name=str(meta.get('short') or meta.get('name') or career)[:100],
            activity=_activity(c), theme=str(c.get('theme', ''))[:80],
            decor=[str(k)[:80] for k in c.get('decor', {})][:24],
            staffed=any(e.get('status') == 'hired' for e in c.get('ops', {}).get('staff', [])),
            offers=offers, available=bool(offers), status='open' if offers else 'waiting',
            reason='' if offers else 'Chủ tiệm cần chuẩn bị một yêu cầu nghề nghiệp còn trống.')))
    for st in (quay.get(state) or {}).get('stalls', []):
        board = quay_self.menu(st)
        inventory = st.get('business', {}).get('stock', {})
        paused = st.get('business', {}).get('paused') or st.get('economy', {}).get('paused') or st.get('due', 0) > 0
        ready = bool(inventory) and getattr(bridge, 'can_accept_visit', lambda st: True)(st)
        offers = [dict(offer_id=d, dish=d, price=board['p'][d], staffed=bool(st.get('staff')), label=quay_self.DISH[st['trade']][d]['name'], career=st['trade'])
                  for d in board['on'] if inventory.get(d, 0) > 0] if not paused and ready else []
        out.append(('quay', st['id'], dict(name=st['name'], career=st['trade'], offers=offers,
            activity=dict(label='Nhân viên đang phục vụ' if st.get('staff') else 'Chủ quầy phục vụ', status='waiting' if paused else 'working'),
            staffed=bool(st.get('staff')), available=bool(offers), status='closed' if paused else 'open' if offers else 'waiting',
            reason='Quầy đang tạm dừng.' if paused else '' if offers else 'Nhân viên cần đủ quỹ để nhận thêm đơn.' if inventory and not ready else 'Quầy cần nhập thêm hàng.')))
    return out


def sync(db, sid, state, now=None, projected=None):
    """Update sanitized discovery snapshots inside the owner's save transaction.
    `projected`: places(state), computed by the caller before it took the save's lock."""
    if not db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone():
        return
    at = time.time() if now is None else now
    mr.ensure_person_db(db, sid)
    person = _person(db, sid)
    existing = _rows(db, 'SELECT * FROM work_visit_places WHERE owner=?', (sid,))
    previous = {(row['kind'], row['target']): row['data'] for row in existing}
    ids = set()
    changed = []
    for kind, target, data in (places(state) if projected is None else projected):
        pid = _place_id(sid, kind, target)
        ids.add(pid)
        encoded = _json(dict(data, owner=person))
        if previous.get((kind, target)) != encoded:
            changed.append((pid, sid, kind, target, encoded, at))
    if changed:
        # Keep discovery writes in the save transaction without a round trip per
        # started career. Visibility belongs to its separate owner setting.
        values = ','.join("(?,?,?,?,'friends',?,?)" for _ in changed)
        db.execute('INSERT INTO work_visit_places(id,owner,kind,target,visibility,data,updated_at) VALUES ' + values + ' '
                   'ON CONFLICT(owner,kind,target) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at '
                   'WHERE work_visit_places.data<>excluded.data', tuple(value for row in changed for value in row))
    # Removed shops become unavailable, while retained ids/reviews remain stable.
    for old in existing:
        if old['id'] not in ids:
            data = _data(old)
            data.update(offers=[], available=False, status='closed', reason='Chỗ làm này đã đóng.')
            db.execute("UPDATE work_visit_places SET visibility='closed',data=?,updated_at=? WHERE id=?", (_json(data), at, old['id']))


def command_commit(db, sid, before, after, career, action, result, now=None, projected=None):
    """DB-only hook, called in the same commit as an actual authoritative action."""
    at = time.time() if now is None else now
    action = str(action or '')
    destructive = 'import' in action or action in ('reset_all', 'reset_career', 'restore_save')
    if destructive:
        rows = _rows(db, "SELECT * FROM work_service_orders WHERE provider=? AND status IN ('requested','accepted')", (sid,))
        for order in rows:
            data = _data(order)
            if action == 'reset_career' and data.get('career') != career:
                continue
            data['end_status'] = 'cancelled'
            db.execute("UPDATE work_service_orders SET status='refund_pending',data=?,updated_at=? WHERE id=? AND status IN ('requested','accepted')",
                       (_json(data), at, order['id']))
    else:
        for event in _bridge().transitions(before, after, career, action, result or {}):
            if not isinstance(event, dict) or event.get('status') not in ('completed', 'cancelled', 'referred'):
                continue
            order = _row(db, "SELECT * FROM work_service_orders WHERE id=? AND provider=? AND status='accepted'", (event.get('id'), sid))
            if not order:
                continue
            data = _data(order)
            if event.get('price', order['price']) != order['price']:
                continue
            if event['status'] == 'completed':
                db.execute("UPDATE work_service_orders SET status='ready',updated_at=? WHERE id=? AND status='accepted'", (at, order['id']))
            else:
                data['end_status'] = 'cancelled'
                db.execute("UPDATE work_service_orders SET status='refund_pending',data=?,updated_at=? WHERE id=? AND status='accepted'", (_json(data), at, order['id']))
    sync(db, sid, after, now=at, projected=projected)


def _actor(store, token):
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(), 'Đăng nhập để ghé chỗ làm của bạn bè.', 'login_required', 401)
    return sid


def _advance_provider(store, sid, *, refresh_snapshot=False):
    """An authenticated visit may advance actual paid employee work offline."""
    from . import quay_business, workplace_business
    loaded = mr._read_state(store, sid)
    if not loaded:
        return False
    state, _ = loaded
    if not (quay_business.due(state) or workplace_business.due(state)):
        if refresh_snapshot:
            _refresh_snapshot(store, sid, loaded=loaded)
        return False
    box = {}
    def advance(s):
        box['before'] = copy.deepcopy(s)
        quay_business.settle(s)
        workplace_business.settle(s)
        box['after'] = s
    def commit(db):
        command_commit(db, sid, box['before'], box['after'], None, 'work_visits_tick', {})
    mr._mutate_retry(store, {sid: advance}, commit)
    return True


def forget(db, sid):
    """Called in account deletion: surviving customers can recover held coins."""
    at = time.time()
    for row in _rows(db, "SELECT * FROM work_service_orders WHERE provider=? AND status IN ('requested','accepted','ready')", (sid,)):
        body = _data(row);body['end_status'] = 'cancelled'
        db.execute("UPDATE work_service_orders SET status='refund_pending',data=?,updated_at=? WHERE id=?", (_json(body), at, row['id']))
    # Work already accepted keeps its escrow: a surviving provider may finish
    # the agreed service. Only requests that have not started are discarded.
    db.execute("UPDATE work_service_orders SET status='cancelled',updated_at=? WHERE customer=? AND status='requested'", (at, sid))
    for row in _rows(db, 'SELECT * FROM work_service_orders WHERE customer=? OR provider=?', (sid, sid)):
        body = _data(row)
        for key in ('customer', 'provider'):
            if row[key] == sid:
                body[key] = dict(pid='', name='Người chơi đã rời', code='', avatar='🙂', fc='')
        db.execute('UPDATE work_service_orders SET data=? WHERE id=?', (_json(body), row['id']))
    db.execute('DELETE FROM work_service_reviews WHERE customer=? OR provider=?', (sid, sid))
    db.execute('DELETE FROM work_visit_places WHERE owner=?', (sid,))


def _refresh_snapshot(store, sid, *, loaded=None):
    loaded = mr._read_state(store, sid) if loaded is None else loaded
    if not loaded:
        return
    state, rev = loaded
    def update(db):
        row = db.execute('SELECT revision FROM sessions WHERE sid=? FOR SHARE', (sid,)).fetchone()
        if row and row['revision'] == rev:
            sync(db, sid, state)
    store.transaction(update)


class _Replay(Exception):
    pass


def _settle_one(store, order):
    from . import journey, quay
    status = order['status']
    if status not in ('ready', 'refund_pending'):
        return False
    data = _data(order)
    recipient = order['provider'] if status == 'ready' else order['customer']
    new_status = 'completed' if status == 'ready' else data.get('end_status', 'cancelled')
    state_box = {}
    if status == 'refund_pending' and not mr._read_state(store, recipient):
        # The buyer deleted their account; discard its refund but release any
        # surviving provider's bounded receipt slot in the same transaction.
        def discard(db):
            if db.execute("UPDATE work_service_orders SET status='cancelled',updated_at=? WHERE id=? AND status='refund_pending'", (time.time(), order['id'])).rowcount != 1:
                raise _Replay()
        try:
            if mr._read_state(store, order['provider']):
                mr._mutate_retry(store, {order['provider']: lambda s: _ack(s, order['id'], cancelled=True)}, discard)
            else:
                store.transaction(discard)
        except _Replay:
            return False
        return True
    def change(state):
        with store.connect() as db:
            current = _row(db, 'SELECT status FROM work_service_orders WHERE id=?', (order['id'],))
        if not current or current['status'] != status:
            raise _Replay()
        from . import quay_business, workplace_business
        state_box['before'] = copy.deepcopy(state)
        quay_business.settle(state)
        workplace_business.settle(state)
        if status == 'ready' and data['kind'] == 'quay':
            exists = any(st['id'] == data['target'] for st in state['journey'].get('quay', {}).get('stalls', []))
            if exists:
                _bridge().credit_visit(state, data['target'], order['id'], order['price'])
            else:
                journey._wallet(state['journey'], order['price'], 'salary', 'Thanh toán đơn đã phục vụ tại quầy đã đóng', data.get('career'))
        elif status == 'ready':
            from . import engine
            c = state['careers'][data['career']]
            engine.money(state, c, order['price'], 'Thanh toán đơn khách thật', order['id'], 'revenue')
            credit_bonus = getattr(_bridge(), 'credit_staff_bonus', None)
            if credit_bonus: credit_bonus(state, data['career'], order['id'], order['price'])
        else:
            journey._wallet(state['journey'], order['price'], 'draw',
                            'Thanh toán đơn khách thật' if status == 'ready' else 'Hoàn tiền đơn chỗ làm', data.get('career'))
        if status == 'ready':
            _ack(state, order['id'])
        state_box['state'] = state
    def finish(db):
        if db.execute('UPDATE work_service_orders SET status=?,updated_at=? WHERE id=? AND status=?',
                      (new_status, time.time(), order['id'], status)).rowcount != 1:
            raise _Replay()
        command_commit(db, recipient, state_box['before'], state_box['state'], data.get('career'), 'work_visits_payment', {})
    try:
        callbacks = {recipient: change}
        if status == 'refund_pending' and order['provider'] != recipient and mr._read_state(store, order['provider']):
            callbacks[order['provider']] = lambda s: _ack(s, order['id'], cancelled=True)
        mr._mutate_retry(store, callbacks, finish)
    except _Replay:
        return False
    return True


def _settle_for(store, sid, order_id=None):
    with store.connect() as db:
        pending = _rows(db, "SELECT DISTINCT provider FROM work_service_orders WHERE (customer=? OR provider=?) AND status='accepted' ORDER BY provider LIMIT 21", (sid, sid))
    advanced = 0
    for row in pending:
        advanced += bool(_advance_provider(store, row['provider']))
        if advanced >= 4:
            break
    with store.connect() as db:
        sql = "SELECT * FROM work_service_orders WHERE (customer=? OR provider=?) AND status IN ('ready','refund_pending')"
        args = [sid, sid]
        if order_id is not None:
            sql += ' AND id=?';args.append(order_id)
        rows = _rows(db, sql + ' ORDER BY updated_at,id LIMIT 20', tuple(args))
    return sum(_settle_one(store, row) for row in rows)


def _weighed(db, place, owner):
    """The place's service reviews, newest first, each marked counted / why (social.weigh_reviews: paid 5★ —
    only each customer's newest review, accounts older than 3 days, none within 24 h of xu from the owner)."""
    rows = _rows(db, 'SELECT order_id, customer, stars, created_at FROM work_service_reviews WHERE place=? ORDER BY created_at DESC LIMIT 200', (place,))
    for r in rows:
        r['rsid'], r['at'] = r['customer'], r['created_at']
    return rows, social.weigh_reviews(db, owner, rows)


def _rating(db, place, owner=None):
    rows, average = _weighed(db, place, owner)
    counted = sum(1 for r in rows if r['counted'])
    return dict(count=counted, average=round(float(average or 0), 2), total=len(rows))


def _place_view(db, row, sid):
    data = _data(row)
    return dict(id=row['id'], kind=row['kind'], target=row['target'], visibility=row['visibility'],
                mine=row['owner'] == sid, rating=_rating(db, row['id'], row['owner']), **data)


def _order_view(db, row, sid):
    data = _data(row)
    reviewed = bool(db.execute('SELECT 1 FROM work_service_reviews WHERE order_id=?', (row['id'],)).fetchone())
    return dict(id=row['id'], place=row['place'], status=row['status'], price=row['price'],
        place_name=data.get('place_name', ''), kind=data.get('kind'), career=data.get('career'),
        offer_id=data.get('offer', {}).get('offer_id'), label=data.get('offer', {}).get('label', ''),
        customer=data.get('customer', {}), provider=data.get('provider', {}), note=data.get('note', ''),
        task_id=data.get('task_id'), staffed=bool(data.get('offer', {}).get('staffed')),
        served_by='staff' if data.get('offer', {}).get('staffed') else 'owner', target=data.get('target'), created_at=row['created_at'], updated_at=row['updated_at'],
        can_review=row['customer'] == sid and row['status'] == 'completed' and not reviewed)


def _resolve(db, value):
    if re.fullmatch(r'[0-9a-f]{16}', value):
        row = _row(db, 'SELECT sid FROM profiles WHERE pid=?', (value,))
        if not row:
            row = _row(db, 'SELECT sid FROM chat_members WHERE pid=? LIMIT 1', (value,))
        return row['sid'] if row else None
    try:
        row = mr._find(db, mr.clean_code(value))
    except mr.MarriageError:
        return None
    return row['sid'] if row else None


def get(store, token, state, sub, query):
    sid = _actor(store, token)
    query = query or {}
    _settle_for(store, sid)
    if sub == 'place':
        with store.connect() as db:
            target = _row(db, 'SELECT * FROM work_visit_places WHERE id=?', (query.get('place'),))
            need(target and _accessible(db, target, sid), 'Không tìm thấy chỗ làm này.', 'not_found', 404)
        # A work commit already syncs the snapshot. Otherwise reuse the save
        # read for the due check, still guarded by its revision below.
        _advance_provider(store, target['owner'], refresh_snapshot=True)
        _settle_for(store, sid)
    if sub in ('', 'places'):
        _refresh_snapshot(store, sid)
    with store.connect() as db:
        if sub in ('', 'places'):
            scope = query.get('scope', 'friends')
            need(scope in ('mine', 'friends', 'public'), 'Chọn danh sách chỗ làm.')
            owner = _resolve(db, str(query['owner'])) if query.get('owner') else None
            if query.get('owner') and owner is None:
                return dict(places=[], next=None, scope=scope)
            args = []
            clauses = []
            if scope == 'mine':
                clauses.append('owner=?');args.append(sid)
            elif owner:
                clauses.append('owner=?');args.append(owner)
            elif scope == 'public':
                clauses.append("visibility='public'")
            else:
                clauses.append('owner IN (SELECT friend FROM friends WHERE sid=?)');args.append(sid)
            if query.get('career'):
                clauses.append('(target=? OR CAST(data AS jsonb)->>\'career\'=?)');args.extend([str(query['career'])] * 2)
            try:
                offset = max(0, min(100000, int(query.get('offset', 0))))
            except (ValueError, TypeError):
                raise WorkVisitError('Trang không hợp lệ.')
            rows = _rows(db, 'SELECT * FROM work_visit_places WHERE ' + ' AND '.join(clauses) + ' ORDER BY updated_at DESC,id LIMIT 60 OFFSET ?', tuple(args + [offset]))
            return dict(places=[_place_view(db, row, sid) for row in rows if _accessible(db, row, sid)],
                        next=offset + LIMIT if len(rows) == LIMIT else None, scope=scope)
        if sub == 'place':
            row = _row(db, 'SELECT * FROM work_visit_places WHERE id=?', (query.get('place'),))
            need(row and _accessible(db, row, sid), 'Không tìm thấy chỗ làm này.', 'not_found', 404)
            reviews = []
            counted = {r['order_id']: r['counted'] for r in _weighed(db, row['id'], row['owner'])[0]}
            for review in _rows(db, 'SELECT r.*,o.data AS order_data FROM work_service_reviews r JOIN work_service_orders o ON o.id=r.order_id WHERE r.place=? ORDER BY r.created_at DESC LIMIT 30', (row['id'],)):
                if not _blocked(db, sid, review['customer']):
                    reviews.append(dict(order=review['order_id'], stars=review['stars'], tags=json.loads(review['tags']), comment=review['comment'], reply=review['reply'], served_by='staff' if json.loads(review['order_data']).get('offer', {}).get('staffed') else 'owner', buyer=_person(db, review['customer']),
                                        counted=counted.get(review['order_id'], True)))
            orders = _rows(db, 'SELECT * FROM work_service_orders WHERE place=? AND (customer=? OR provider=?) ORDER BY created_at DESC LIMIT 30', (row['id'], sid, sid))
            return dict(place=_place_view(db, row, sid), reviews=reviews, orders=[_order_view(db, o, sid) for o in orders])
        if sub == 'orders':
            rows = _rows(db, 'SELECT * FROM work_service_orders WHERE customer=? OR provider=? ORDER BY created_at DESC LIMIT 100', (sid, sid))
            return dict(incoming=[_order_view(db, o, sid) for o in rows if o['provider'] == sid],
                        outgoing=[_order_view(db, o, sid) for o in rows if o['customer'] == sid])
    raise WorkVisitError('Không có mục này.', 'not_found', 404)


def _create(store, sid, data):
    from . import journey
    need(set(data) <= {'place', 'offer_id', 'qty', 'note', 'rid', 'expected_price'}, 'Thông tin đặt dịch vụ không hợp lệ.')
    rid = data.get('rid')
    need(isinstance(rid, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,80}', rid), 'Thiếu mã thao tác đặt đơn.', 'bad_rid')
    need(type(data.get('qty', 1)) is int and data.get('qty', 1) == 1, 'Mỗi đơn gồm một dịch vụ.')
    note = _clean(data.get('note', ''), 200)
    fingerprint = hashlib.sha256(_json({k:v for k,v in data.items() if k != 'rid'}).encode()).hexdigest()
    with store.connect() as db:
        existing = _row(db, 'SELECT * FROM work_service_orders WHERE customer=? AND request_id=?', (sid, rid))
        if existing:
            need(existing['fingerprint'] == fingerprint, 'Mã thao tác đã dùng cho nội dung khác.', 'rid_conflict', 409)
            return dict(order=_order_view(db, existing, sid), changed=False)
        place = _row(db, 'SELECT * FROM work_visit_places WHERE id=?', (data.get('place'),))
        need(place and _accessible(db, place, sid), 'Không tìm thấy chỗ làm này.', 'not_found', 404)
        need(place['owner'] != sid, 'Hãy ghé chỗ làm của người khác nhé.', 'own_place')
        snapshot = _data(place)
        offer = next((o for o in snapshot.get('offers', []) if o['offer_id'] == data.get('offer_id')), None)
        need(offer and snapshot.get('available'), 'Dịch vụ này hiện chưa sẵn sàng.', 'unavailable', 409)
        if 'expected_price' in data:
            need(type(data['expected_price']) is int and data['expected_price'] == offer['price'], 'Giá đã thay đổi. Xem lại giá trước khi đặt nhé.', 'quote_changed', 409)
        customer, provider = _person(db, sid), _person(db, place['owner'])
    price, oid, at = offer['price'], 'wo_' + secrets.token_hex(12), time.time()
    body = dict(kind=place['kind'], target=place['target'], career=offer.get('career') or snapshot.get('career') or place['target'],
                place_name=snapshot['name'], offer=offer, customer=customer, provider=provider, note=note)
    def debit(s):
        with store.connect() as db:
            previous = _row(db, 'SELECT * FROM work_service_orders WHERE customer=? AND request_id=?', (sid, rid))
        if previous:
            need(previous['fingerprint'] == fingerprint, 'Mã thao tác đã dùng cho nội dung khác.', 'rid_conflict', 409)
            raise _Replay()
        need(s.get('journey', {}).get('story'), 'Dịch vụ khách thật dùng ví hành trình.', 'not_story')
        need(s['journey']['wallet'] >= price, f'Cần {price} xu trong ví để giữ tiền cho đơn.', 'no_money')
        journey._wallet(s['journey'], -price, 'invest', 'Giữ tiền đơn chỗ làm', body['career'])
        if body['career'] == 'pet_care':   # 🐾 the pets at home go to the groomer (game/pets.py); no money moves here
            from . import pets
            pets.groom_by_player(s)
    def insert(db):
        previous = _row(db, 'SELECT * FROM work_service_orders WHERE customer=? AND request_id=?', (sid, rid))
        if previous:
            need(previous['fingerprint'] == fingerprint, 'Mã thao tác đã dùng cho nội dung khác.', 'rid_conflict', 409)
            raise _Replay()
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('work-orders:' + place['owner'],))
        current = _row(db, 'SELECT * FROM work_visit_places WHERE id=? FOR UPDATE', (place['id'],))
        need(current and _accessible(db, current, sid), 'Chỗ làm hiện không nhận đơn.', 'unavailable', 409)
        updated = _data(current)
        current_offer = next((o for o in updated.get('offers', []) if o['offer_id'] == offer['offer_id']), None)
        need(updated.get('available') and current_offer == offer, 'Thông tin dịch vụ đã đổi. Xem giá mới trước nhé.', 'quote_changed', 409)
        need(db.execute("SELECT COUNT(*) FROM work_service_orders WHERE customer=? AND status IN ('requested','accepted')", (sid,)).fetchone()[0] < 20, 'Bạn đang có nhiều đơn chờ. Hoàn thành hoặc hủy bớt nhé.', 'too_many_orders')
        need(db.execute("SELECT COUNT(*) FROM work_service_orders WHERE provider=? AND status IN ('requested','accepted')", (place['owner'],)).fetchone()[0] < 50, 'Chỗ làm đang có nhiều khách chờ.', 'busy')
        db.execute('INSERT INTO work_service_orders(id,place,customer,provider,status,price,request_id,fingerprint,data,created_at,updated_at) '
                   "VALUES(?,?,?,?,'requested',?,?,?,?,?,?)", (oid, place['id'], sid, place['owner'], price, rid, fingerprint, _json(body), at, at))
    try:
        mr._mutate_retry(store, {sid: debit}, insert)
    except _Replay:
        pass
    with store.connect() as db:
        result = _row(db, 'SELECT * FROM work_service_orders WHERE customer=? AND request_id=?', (sid, rid))
    if offer.get('staffed') or (place['kind'] == 'quay' and snapshot.get('staffed')):
        from .engine import GameError
        try:
            _accept(store, place['owner'], {'order':result['id']}, automatic=True)
        except (mr.MarriageError, GameError):
            pass  # Busy/depleted employee leaves a visible, refundable request.
    with store.connect() as db:
        result = _row(db, 'SELECT * FROM work_service_orders WHERE id=?', (result['id'],))
        return dict(order=_order_view(db, result, sid), changed=True, message='Đã giữ tiền cho đơn; trạng thái phục vụ được cập nhật tại đây.')


def _accept(store, sid, data, automatic=False):
    from . import quay_business, workplace_business
    need(set(data) <= {'order'}, 'Thông tin nhận đơn không hợp lệ.')
    with store.connect() as db:
        order = _row(db, 'SELECT * FROM work_service_orders WHERE id=?', (data.get('order'),))
        need(order and order['provider'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
        if order['status'] == 'accepted':
            return dict(order=_order_view(db, order, sid), changed=False)
        need(order['status'] == 'requested', 'Đơn không còn chờ nhận.', 'gone', 409)
        need(not _blocked(db, sid, order['customer']), 'Không thể nhận đơn này.', 'blocked')
    body = _data(order)
    state_box = {}
    def bind(s):
        state_box['before'] = copy.deepcopy(s)
        quay_business.settle(s)
        workplace_business.settle(s)
        request = dict(id=order['id'], offer_id=body['offer']['offer_id'], digest=body['offer'].get('digest'),
                       price=order['price'], buyer={**{k:body['customer'].get(k,'') for k in ('name','code','fc')}, 'av':body['customer'].get('avatar','🙂')}, note=body['note'])
        if body['kind'] == 'quay':
            from . import quay
            staffed = bool(quay.stall(s, body['target'])['staff'])
            need(not automatic or staffed, 'Chủ quầy cần trực tiếp nhận đơn này.', 'staff_changed', 409)
            body['offer']['staffed'] = staffed
            request['items'] = [body['offer']['dish']]
            task_id = _bridge().accept_visit(s, body['target'], request)
        else:
            task_id = _bridge().accept(s, body['career'], request)
        body['task_id'] = task_id
        state_box['state'] = s
    def assign(db):
        current = _row(db, 'SELECT * FROM work_service_orders WHERE id=? FOR UPDATE', (order['id'],))
        need(current and current['status'] == 'requested', 'Đơn đã được xử lý.', 'gone', 409)
        place = _row(db, 'SELECT * FROM work_visit_places WHERE id=?', (order['place'],))
        need(place and _accessible(db, place, order['customer']) and place['visibility'] != 'closed', 'Chỗ làm không còn nhận khách này.', 'unavailable', 409)
        db.execute("UPDATE work_service_orders SET status='accepted',data=?,updated_at=? WHERE id=? AND status='requested'", (_json(body), time.time(), order['id']))
        command_commit(db, sid, state_box['before'], state_box['state'], body['career'], 'work_visits_accept', {})
    mr._mutate_retry(store, {sid: bind}, assign)
    with store.connect() as db:
        result = _row(db, 'SELECT * FROM work_service_orders WHERE id=?', (order['id'],))
        return dict(order=_order_view(db, result, sid), task_id=body['task_id'], changed=True,
                    message='Đã nhận khách. Vào nghề để phục vụ yêu cầu thực tế nhé.')


def _cancel(store, sid, sub, data):
    need(set(data) <= {'order'}, 'Thông tin hủy đơn không hợp lệ.')
    def mark(db):
        order = _row(db, 'SELECT * FROM work_service_orders WHERE id=? FOR UPDATE', (data.get('order'),))
        need(order and order['customer' if sub == 'cancel' else 'provider'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
        if order['status'] in ('cancelled', 'declined', 'refund_pending'):
            return
        need(order['status'] == 'requested', 'Đơn đã bắt đầu phục vụ, không thể hủy ở đây.', 'already_started', 409)
        body = _data(order);body['end_status'] = 'cancelled' if sub == 'cancel' else 'declined'
        db.execute("UPDATE work_service_orders SET status='refund_pending',data=?,updated_at=? WHERE id=? AND status='requested'", (_json(body), time.time(), order['id']))
    store.transaction(mark)
    _settle_for(store, sid, data.get('order'))
    return dict(changed=True, message='Đơn đã dừng và tiền đã hoàn về ví khách.')


def post(store, token, state, sub, data):
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Dữ liệu không hợp lệ.')
    if sub == 'order':
        return _create(store, sid, data)
    if sub == 'accept':
        return _accept(store, sid, data)
    if sub in ('decline', 'cancel'):
        return _cancel(store, sid, sub, data)
    if sub == 'receive':
        need(set(data) <= {'order'}, 'Thông tin nhận tiền không hợp lệ.')
        n = _settle_for(store, sid, data.get('order'))
        return dict(changed=bool(n), count=n, message='Đã đối soát các đơn đã phục vụ thực tế.')
    if sub == 'visibility':
        need(set(data) <= {'place', 'visibility'} and data.get('visibility') in VISIBILITY, 'Chọn ai được ghé chỗ làm.')
        def update(db):
            need(db.execute('UPDATE work_visit_places SET visibility=?,updated_at=? WHERE id=? AND owner=?',
                            (data['visibility'], time.time(), data.get('place'), sid)).rowcount == 1, 'Không tìm thấy chỗ làm của bạn.', 'not_found', 404)
        store.transaction(update)
        return dict(changed=True, message='Đã cập nhật quyền ghé chỗ làm.')
    if sub in ('review', 'reply'):
        expected = {'order','stars','tags','comment'} if sub == 'review' else {'order','text'}
        need(set(data) <= expected, 'Thông tin đánh giá không hợp lệ.')
        if sub == 'review':
            stars = data.get('stars');tags = data.get('tags', [])
            need(type(stars) is int and 1 <= stars <= 5, 'Chọn từ 1 đến 5 sao.')
            need(isinstance(tags, list) and len(tags) <= 4 and all(isinstance(t,str) and t in TAGS for t in tags) and len(set(tags)) == len(tags), 'Nhãn đánh giá không hợp lệ.')
            comment = _clean(data.get('comment',''), 300)
        else:
            comment = _clean(data.get('text',''), 300, 1)
        def write(db):
            order = _row(db, 'SELECT * FROM work_service_orders WHERE id=? FOR UPDATE', (data.get('order'),))
            need(order and order['customer' if sub == 'review' else 'provider'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
            need(order['status'] == 'completed', 'Chỉ đánh giá dịch vụ đã được phục vụ và thanh toán.', 'not_completed')
            need(not _blocked(db, order['customer'], order['provider']), 'Không thể gửi nội dung cho đơn này.', 'blocked')
            at = time.time()
            if sub == 'review':
                old = _row(db, 'SELECT * FROM work_service_reviews WHERE order_id=?', (order['id'],))
                if old:
                    need(old['stars'] == stars and json.loads(old['tags']) == tags and old['comment'] == comment, 'Mỗi đơn chỉ có một đánh giá xác thực.', 'already_reviewed', 409)
                    return
                db.execute('INSERT INTO work_service_reviews(order_id,place,customer,provider,stars,tags,comment,reply,created_at,updated_at) VALUES(?,?,?,?,?,?,?,\'\',?,?)',
                           (order['id'], order['place'], order['customer'], order['provider'], stars, _json(tags), comment, at, at))
            else:
                old = _row(db, 'SELECT * FROM work_service_reviews WHERE order_id=?', (order['id'],))
                need(old, 'Chưa có đánh giá để trả lời.', 'no_review')
                need(not old['reply'] or old['reply'] == comment, 'Bạn đã trả lời đánh giá này.', 'already_replied', 409)
                db.execute('UPDATE work_service_reviews SET reply=?,updated_at=? WHERE order_id=?', (comment, at, order['id']))
        store.transaction(write)
        return dict(changed=True, message='Đã lưu đánh giá xác thực.' if sub == 'review' else 'Đã gửi lời cảm ơn khách.')
    raise WorkVisitError('Thao tác chỗ làm không hợp lệ.', 'unknown_action')
