"""🧰 Phục chế đồ của người chơi: a 🧰 Thợ phục chế player restores another player's broken or worn things through
🛎️ Phố dịch vụ (game/service_market.py), owner 21/10 ("làm hết đi").

What can be restored is only what the game already damages (nothing new breaks because of this module):
* 🛵 / 🚗 / ⛵ a vehicle left broken by a 🎲 rủi ro card (journey.rui.broken.xe[vid], game/rui.py): the entry goes,
  the vehicle rides again — like jr_rui_fix, without the insurance bill;
* 🏚️ a worn part of the home you live in and own (journey.reno.parts[part].c < 100, game/reno.py): back to 100, and a
  rủi ro "broken home" entry for that part goes too — like jr_reno_fix / jr_rui_fix;
* 🪑 purely cosmetic: a piece of furniture (journey.reno.items) made "cổ điển" (an aged patina drawn by
  public/js/v4/reno.js), with nothing about how it works changing.
Every restored thing carries a visible mark "đã phục chế bởi <thợ> ⭐…" in the optional save key
journey['restored'] = {v: 1, items: {"<kind>:<ref>": {by, d, s, g, o}}} (at most MARK_MAX, oldest dropped). 2.4.66
keeps an unknown journey key untouched (journey.validate only asks for its own keys), so a rollback loads the save
(tests/test_restore_compat.py).

Flow: the buyer picks a thing in 🧰 Phục chế đồ and opens a ticket (restore_tickets: open), then orders the matching
service from a restorer in Phố dịch vụ (escrow there: ×3 the NPC price by default, 95 % to the restorer, 5 % burned).
The restorer takes the order, works it at 🧰 Bàn thợ (three server-graded steps; the first binds the buyer's oldest
open ticket of that service to the order: bound) and taps Giao. The market's deliver hook (in the transaction that
marks the work done) checks the bench is finished and closes the ticket (done) with the result; the market's on_buyer
(in the settlement transaction that pays the restorer, right after for these 'auto' services) restores the thing in
the buyer's save, once: the market flips the order ready → done exactly once, and the mark carries the order id.
A ticket bound to an order that ended without delivery (refunded, cancelled…) opens again by itself.

Kill switch: MNL_RESTORE_OFF=1 — no new ticket, order, provider or delivery (orders already paid run out their
timers and are refunded in full by the market); a delivery already settling still lands in the buyer's save.
Table: restore_tickets (game/pg_schema.py SCHEMA_VERSION 72).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time

from . import marriage as mr
from . import service_market as sm

CAREER = 'restore'
KEY = 'restored'               # the optional save key
VERSION = 1
MARK_MAX = 80                  # marks a save keeps (oldest dropped)
OPEN_MAX = 6                   # open / bound tickets of a buyer
STYLES = {'giu': 'Giữ dấu thời gian', 'moi': 'Làm mới'}
DECOR_CATS = ('table', 'bed', 'light', 'le')
TICKET_RX = re.compile(r'rt_[0-9a-f]{20}')
REF_RX = re.compile(r'[A-Za-z0-9_:.-]{1,40}')
MARK_KEYS = frozenset({'by', 'd', 's', 'g', 'o'})

# service id: name, icon, NPC base price (xu, one unit), unit, one line, kind, vehicle groups
SERVICES = {
    'xe': dict(name='Phục hồi xe máy, xe đạp hỏng', icon='🛵', base=40, unit='chiếc', kind='xe', groups=('bike',),
               desc='Xe hỏng sau rủi ro chạy lại được, kèm dấu “đã phục chế”.'),
    'oto': dict(name='Phục hồi ô tô hỏng', icon='🚗', base=500, unit='chiếc', kind='xe', groups=('car',),
                desc='Ô tô hỏng sau rủi ro chạy lại được, kèm dấu “đã phục chế”.'),
    'tau': dict(name='Đại tu thuyền, máy bay hỏng', icon='⛵', base=2500, unit='chiếc', kind='xe', groups=('boat', 'plane'),
                desc='Thuyền, máy bay hỏng sau rủi ro dùng lại được, kèm dấu “đã phục chế”.'),
    'nha': dict(name='Phục hồi một phần nhà xuống cấp', icon='🏚️', base=120, unit='hạng mục', kind='nha', groups=(),
                desc='Một phần nhà đang ở (tường, mái, sàn, điện nước, bếp) về lại 100%.'),
    'co_dien': dict(name='Làm đồ gỗ thành cổ điển', icon='🪑', base=60, unit='món', kind='decor', groups=(),
                    desc='Chỉ đổi vẻ ngoài: món đồ mang nước sáp trầm, kèm dấu “đã phục chế”.'),
}
# The bench (three steps a kind): (title, options [(id, words)], the right option; '' = by the ticket's style).
BENCH = {
    'xe': [('Khám xe', [('check', 'Kiểm bugi, xích, phanh và lốp trước'), ('all_new', 'Thay hết đồ mới cho chắc'),
                        ('ride', 'Chạy thử luôn, khỏi khám')], 'check'),
           ('Sửa chỗ hỏng', [('part', 'Thay đúng phụ tùng hỏng, siết lại ốc'), ('tape', 'Quấn băng keo chỗ hở'),
                             ('oil', 'Đổ thêm nhớt là được')], 'part'),
           ('Hoàn thiện', [('giu', 'Giữ nước sơn cũ, đánh bóng nhẹ'), ('moi', 'Sơn dặm lại cho như mới'),
                           ('decal', 'Dán decal phủ kín cho nhanh')], '')],
    'nha': [('Khảo sát', [('survey', 'Đo độ ẩm, gõ thử, chụp ảnh hiện trạng'), ('smash', 'Đập ra làm lại hết'),
                          ('cover', 'Sơn đè cho nhanh')], 'survey'),
            ('Phục hồi', [('root', 'Xử lý gốc hư rồi mới hoàn thiện mặt'), ('putty', 'Trét bột che vết'),
                          ('later', 'Để chủ nhà tự lo')], 'root'),
            ('Hoàn thiện', [('giu', 'Giữ gạch, gỗ cũ còn tốt, chỉ thay chỗ hỏng'), ('moi', 'Làm mới cả hạng mục theo ý chủ nhà'),
                            ('half', 'Bỏ dở, hẹn tuần sau')], '')],
    'decor': [('Khám đồ gỗ', [('grain', 'Xem thớ gỗ, mộng và lớp sơn cũ'), ('sand', 'Chà nhám ngay'),
                              ('soak', 'Ngâm nước cho mềm')], 'grain'),
              ('Làm cổ điển', [('wax', 'Lau sạch, phủ sáp ong, đánh màu trầm'), ('gold', 'Sơn nhũ vàng chóe'),
                               ('sticker', 'Dán giấy giả gỗ')], 'wax'),
              ('Hoàn thiện', [('giu', 'Chừa vết xước kỷ niệm, phủ sáp mỏng'), ('moi', 'Đánh bóng đều cả món'),
                              ('carve', 'Khắc tên tiệm lên mặt gỗ')], '')],
}


def off() -> bool:
    return os.environ.get('MNL_RESTORE_OFF', '') not in ('', '0')


OFF_LINE = 'Xưởng phục chế đang tạm nghỉ, quay lại sau nhé.'


def _now() -> float:
    return time.time()


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _load(text) -> dict:
    try:
        v = json.loads(text) if text else {}
    except (TypeError, ValueError):
        v = {}
    return v if isinstance(v, dict) else {}


def need(cond, message: str, code: str = 'restore_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


# ---------------------------------------------------------------- what a save can bring
def _journey(state: dict) -> dict:
    j = state.get('journey') if isinstance(state, dict) else None
    return j if isinstance(j, dict) else {}


def _vehicles(state: dict, groups) -> list:
    from . import garage as gr
    from . import rui
    r = rui.get(state)
    g = gr.get(state)
    if not r or not g or not isinstance(g.get('cars'), dict):
        return []
    out = []
    for vid in r['broken'].get('xe', {}):
        v = gr.VEHICLES.get(vid)
        if v and vid in g['cars'] and v['group'] in groups:
            out.append(dict(ref=vid, label=f'{v["emoji"]} {v["name"]}', detail='Đang hỏng sau rủi ro'))
    return out


def _home_parts(state: dict) -> list:
    from . import reno as rn
    from . import rui
    r = rn.get(state)
    if not r or r.get('hid') is None or not isinstance(r.get('parts'), dict) or not rui._lived(state, r['hid']):
        return []
    out = []
    for part, x in r['parts'].items():
        if part in rn.PARTS and isinstance(x, dict) and type(x.get('c')) is int and x['c'] < 100:
            p = rn.PARTS[part]
            out.append(dict(ref=f'{r["hid"]}:{part}', label=f'{p["emoji"]} {p["name"]}', detail=f'Còn {x["c"]}% · {p["flaw"]}'))
    return out


def _decor(state: dict) -> list:
    from . import deco_content as D
    from . import reno as rn
    r = rn.get(state)
    marks = _marks(state)
    out = []
    for it in (r or {}).get('items') or []:
        k = it.get('k') if isinstance(it, dict) else None
        x = D.ITEMS.get(k)
        if x and x.get('cat') in DECOR_CATS and not x.get('uq') and isinstance(it.get('id'), str) and f'decor:{it["id"]}' not in marks:
            out.append(dict(ref=it['id'], label=f'{x["emoji"]} {x["name"]}', detail='Đổi vẻ ngoài thành đồ cổ điển'))
        if len(out) >= 40:
            break
    return out


def items(state: dict, service: str) -> list:
    """What this save can bring for `service`: [{ref, label, detail}]."""
    sp = SERVICES.get(service)
    if not sp:
        return []
    if sp['kind'] == 'xe':
        return _vehicles(state, sp['groups'])
    if sp['kind'] == 'nha':
        return _home_parts(state)
    return _decor(state)


def _item(state: dict, service: str, ref) -> dict | None:
    return next((x for x in items(state, service) if x['ref'] == ref), None) if isinstance(ref, str) else None


# ---------------------------------------------------------------- the save key journey['restored'] (optional)
def _marks(state: dict) -> dict:
    blk = _journey(state).get(KEY)
    return blk['items'] if isinstance(blk, dict) and isinstance(blk.get('items'), dict) else {}


def validate(s: dict) -> None:
    j = _journey(s)
    if KEY not in j:
        return
    from .engine import need as eneed
    b = j[KEY]
    ok = isinstance(b, dict) and set(b) == {'v', 'items'} and b['v'] == VERSION and isinstance(b['items'], dict) and len(b['items']) <= MARK_MAX
    for k, m in (b['items'].items() if ok else ()):
        ok = ok and isinstance(k, str) and len(k) <= 48 and k.split(':', 1)[0] in ('xe', 'nha', 'decor') and isinstance(m, dict) \
            and set(m) == MARK_KEYS and isinstance(m['by'], str) and len(m['by']) <= 24 and type(m['d']) is int and 0 <= m['d'] <= 10**6 \
            and m['s'] in SERVICES and type(m['g']) is int and 1 <= m['g'] <= 3 and isinstance(m['o'], str) and len(m['o']) <= 40
    eneed(ok, 'Dấu phục chế trong bản lưu không hợp lệ.', 'invalid_save')


def public(s: dict) -> dict | None:
    m = _marks(s)
    return {k: dict(by=v['by'], s=v['s'], g=v['g'], d=v['d']) for k, v in m.items()} if m else None


def _mark(s: dict, key: str, by: str, service: str, grade: int, oid: str) -> None:
    j = s['journey']
    blk = j.get(KEY)
    if not (isinstance(blk, dict) and isinstance(blk.get('items'), dict)):
        blk = j[KEY] = dict(v=VERSION, items={})
    its = blk['items']
    its.pop(key, None)   # a thing restored again: its newest mark, at the end
    its[key] = dict(by=str(by or 'Thợ phục chế')[:24], d=int(j.get('life_day') or 0), s=service, g=max(1, min(3, int(grade))), o=str(oid)[:40])
    while len(its) > MARK_MAX:
        its.pop(next(iter(its)))


def apply(s: dict, result: dict, oid: str) -> bool:
    """The restoration onto the buyer's save (False: nothing to do — already applied, or the thing is gone)."""
    if not isinstance(result, dict) or result.get('svc') not in SERVICES or not isinstance(result.get('ref'), str):
        return False
    service, ref = result['svc'], result['ref']
    kind = SERVICES[service]['kind']
    key = f'{kind}:{ref}'
    if _marks(s).get(key, {}).get('o') == oid:
        return False
    from . import reno as rn
    from . import rui
    from . import garage as gr
    if kind == 'xe':
        g = gr.get(s)
        if not g or ref not in (g.get('cars') or {}):
            return False
        r = rui.get(s)
        if r and ref in r['broken'].get('xe', {}):
            r['broken']['xe'].pop(ref)
            rui._log(r, int(s['journey'].get('life_day') or 1), f'Thợ phục chế {str(result.get("by") or "")[:24]} sửa xe'[:120], 0)
    elif kind == 'nha':
        hid, _, part = ref.rpartition(':')
        r = rn.get(s)
        if not r or str(r.get('hid')) != hid or part not in rn.PARTS or not isinstance((r.get('parts') or {}).get(part), dict):
            return False
        r['parts'][part]['c'] = 100
        b = rui.get(s)
        hk = r['hid']
        if b and hk in b['broken'].get('nha', {}) and b['broken']['nha'][hk].get('p') == part:
            b['broken']['nha'].pop(hk)
    else:
        r = rn.get(s)
        if not r or not any(isinstance(it, dict) and it.get('id') == ref for it in r.get('items') or []):
            return False
    _mark(s, key, str(result.get('by') or ''), service, int(result.get('grade') or 1), oid)
    return True


# ---------------------------------------------------------------- the market hooks
def _check(service):
    def check(db, buyer, state):
        if off():
            return OFF_LINE
        rows = db.execute("SELECT ref FROM restore_tickets WHERE buyer=? AND service=? AND status='open' ORDER BY at,id LIMIT 6",
                          (buyer, service)).fetchall()
        if not any(_item(state, service, r['ref']) for r in rows):
            return 'Mở 🧰 Phục chế đồ, chọn món cần mang tới thợ trước đã.'
        return ''
    return check


def _can_provide(state) -> str:
    if off():
        return OFF_LINE
    c = (state.get('careers') or {}).get(CAREER)
    return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề 🧰 Thợ phục chế trước đã.'


def _deliver(db, provider, buyer, order) -> dict:
    need(not off(), OFF_LINE, 'restore_off', 409)
    t = db.execute("SELECT * FROM restore_tickets WHERE order_id=? AND status='bound' FOR UPDATE", (order['id'],)).fetchone()
    need(t, 'Làm ở 🧰 Bàn thợ trước rồi mới giao được.', 'restore_bench')
    t = dict(t)
    steps = _load(t['steps'])
    kind = SERVICES[t['service']]['kind']
    need(int(steps.get('at') or 0) >= len(BENCH[kind]), 'Làm xong ba bước ở 🧰 Bàn thợ rồi mới giao nhé.', 'restore_bench')
    grade = max(1, 3 - int(steps.get('wrong') or 0))
    by = mr._display(db, provider)
    tm = _now()
    db.execute("UPDATE restore_tickets SET status='done',grade=?,done_at=?,updated_at=? WHERE id=? AND status='bound'", (grade, tm, tm, t['id']))
    return dict(svc=t['service'], ref=t['ref'], label=t['label'][:60], by=str(by or '')[:24], grade=grade, style=t['style'], t=t['id'])


def _on_buyer(state, order) -> None:
    try:
        apply(state, order.get('result') or {}, str(order.get('id') or ''))
    except Exception:  # noqa: BLE001  (never block the restorer's pay: a thing that changed shape stays as it is)
        pass


def install() -> None:
    """Register the services with Phố dịch vụ (idempotent; called at import and by tests after a registry reset)."""
    for sid, sp in SERVICES.items():
        sm.register(CAREER, sid, dict(name=sp['name'], icon=sp['icon'], desc=sp['desc'], base=sp['base'], unit=sp['unit'],
                                      duration=60, work_hours=72, deliver=_deliver, on_buyer=_on_buyer, confirm='auto',
                                      requires=dict(story=True), check=_check(sid), can_provide=_can_provide,
                                      note_hint='Dặn thợ thêm (giữ vết nào, màu gì…)'))


install()


# ---------------------------------------------------------------- tickets
def _release(db, sid: str) -> None:
    """Bound tickets whose order ended without a delivery open again (a refund, a decline…)."""
    rows = db.execute("SELECT t.id FROM restore_tickets t JOIN svc_orders o ON o.id=t.order_id WHERE (t.buyer=? OR t.provider=?) "
                      "AND t.status='bound' AND o.status IN ('refund','refunded','declined','cancelled','expired')", (sid, sid)).fetchall()
    tm = _now()
    for r in rows:
        db.execute("UPDATE restore_tickets SET status='open',order_id=NULL,provider=NULL,steps='{}',updated_at=? WHERE id=? AND status='bound'",
                   (tm, r['id']))


def _ticket_view(r: dict, orders: dict) -> dict:
    o = orders.get(r['order_id']) if r.get('order_id') else None
    return dict(id=r['id'], service=r['service'], ref=r['ref'], label=r['label'], style=r['style'], status=r['status'],
                order=r.get('order_id') or '', order_status=(o or {}).get('status') or '', grade=int(r.get('grade') or 0), at=r['at'])


def mine(store, sid: str, state: dict) -> dict:
    """The buyer's side: what can be brought (per service), the open tickets, the marks of restored things."""
    with store.connect() as db:
        _release(db, sid)
        rows = [dict(r) for r in db.execute("SELECT * FROM restore_tickets WHERE buyer=? AND status IN ('open','bound','done') "
                                            "ORDER BY at DESC,id LIMIT 30", (sid,)).fetchall()]
        ids = [r['order_id'] for r in rows if r.get('order_id')]
        orders = {}
        if ids:
            marks = ','.join('?' * len(ids))
            orders = {o['id']: dict(o) for o in db.execute(f'SELECT id,status FROM svc_orders WHERE id IN ({marks})', tuple(ids)).fetchall()}
    tickets = [_ticket_view(r, orders) for r in rows]
    taken = {(t['service'], t['ref']) for t in tickets if t['status'] in ('open', 'bound')}
    services = []
    for sid_, sp in SERVICES.items():
        its = [dict(x, ticket=(sid_, x['ref']) in taken) for x in items(state, sid_)]
        services.append(dict(id=sid_, name=sp['name'], icon=sp['icon'], desc=sp['desc'], unit=sp['unit'], base=sp['base'], items=its))
    marks = [dict(key=k, kind=k.split(':', 1)[0], by=v['by'], s=v['s'], g=v['g'], d=v['d'], name=_mark_name(state, k)) for k, v in reversed(list(_marks(state).items()))]
    return dict(off=off(), services=services, tickets=[t for t in tickets if t['status'] != 'done' or t['order_status'] != 'done'][:20],
                marks=marks[:40], styles=STYLES, open_max=OPEN_MAX)


def _mark_name(state: dict, key: str) -> str:
    kind, _, ref = key.partition(':')
    try:
        if kind == 'xe':
            from . import garage as gr
            v = gr.VEHICLES.get(ref)
            return f'{v["emoji"]} {v["name"]}' if v else 'Xe'
        if kind == 'nha':
            from . import reno as rn
            p = rn.PARTS.get(ref.rpartition(':')[2])
            return f'{p["emoji"]} {p["name"]}' if p else 'Nhà'
        from . import deco_content as D
        from . import reno as rn
        k = next((it.get('k') for it in (rn.get(state) or {}).get('items') or [] if isinstance(it, dict) and it.get('id') == ref), None)
        x = D.ITEMS.get(k)
        return f'{x["emoji"]} {x["name"]}' if x else '🪑 Đồ gỗ'
    except Exception:  # noqa: BLE001
        return key


def open_ticket(store, sid: str, state: dict, data: dict) -> dict:
    need(not off(), OFF_LINE, 'restore_off', 409)
    need(isinstance(data, dict) and set(data) <= {'service', 'ref', 'style'}, 'Thông tin không hợp lệ.')
    service, ref, style = data.get('service'), data.get('ref'), data.get('style') or 'giu'
    need(service in SERVICES, 'Chọn dịch vụ phục chế.')
    need(style in STYLES, 'Chọn giữ dấu thời gian hay làm mới.')
    need(isinstance(ref, str) and REF_RX.fullmatch(ref), 'Chọn món cần phục chế.')
    it = _item(state, service, ref)
    need(it, 'Món này không cần phục chế nữa (hoặc không còn của bạn).', 'not_eligible')
    tm = _now()

    def run(db):
        n = db.execute("SELECT COUNT(*) AS n FROM restore_tickets WHERE buyer=? AND status IN ('open','bound')", (sid,)).fetchone()['n']
        dup = db.execute("SELECT id FROM restore_tickets WHERE buyer=? AND service=? AND ref=? AND status IN ('open','bound')", (sid, service, ref)).fetchone()
        if dup:
            return dup['id']
        need(n < OPEN_MAX, f'Bạn đang gửi {OPEN_MAX} món rồi. Chờ thợ làm xong đã nhé.', 'too_many')
        tid = 'rt_' + secrets.token_hex(10)
        db.execute('INSERT INTO restore_tickets(id,buyer,service,ref,label,style,status,steps,grade,at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (tid, sid, service, ref, it['label'][:60], style, 'open', '{}', 0, tm, tm))
        return tid
    tid = store.transaction(run)
    return dict(ticket=tid, message='Đã ghi phiếu. Giờ chọn thợ ở 🛎️ Phố dịch vụ nhé.', changed=False)


def drop_ticket(store, sid: str, data: dict) -> dict:
    need(isinstance(data, dict) and isinstance(data.get('ticket'), str) and TICKET_RX.fullmatch(data['ticket']), 'Phiếu không hợp lệ.')
    tm = _now()
    n = store.transaction(lambda db: db.execute("UPDATE restore_tickets SET status='dropped',updated_at=? WHERE id=? AND buyer=? AND status='open'",
                                                (tm, data['ticket'], sid)).rowcount)
    need(n == 1, 'Phiếu này thợ đang làm, không rút được. Hủy đơn ở Phố dịch vụ trước nhé.', 'busy', 409)
    return dict(message='Đã rút phiếu.')


# ---------------------------------------------------------------- 🧰 Bàn thợ (the restorer's side)
def _order_pick(oid: str, kind: str, i: int) -> list:
    """The options of step i in an order-stable order (the right one is not always first)."""
    title, rows, _ = BENCH[kind][i]
    n = int(hashlib.sha256(f'{oid}:{i}'.encode()).hexdigest()[:6], 16) % len(rows)
    return rows[n:] + rows[:n]


def _bench_row(r: dict, kind: str, t: dict | None, people: dict) -> dict:
    steps = _load(t['steps']) if t else {}
    at = int(steps.get('at') or 0)
    view = dict(order=r['id'], status=r['status'], service=r['service'], name=SERVICES[r['service']]['name'], icon=SERVICES[r['service']]['icon'],
                buyer=people.get(r['buyer'], ''), price=int(r['price']), note=(_load(r.get('data')).get('note') or '')[:200],
                ticket=dict(label=t['label'], style=t['style'], style_name=STYLES.get(t['style'], ''), bound=t['status'] == 'bound') if t else None,
                at=at, wrong=int(steps.get('wrong') or 0), steps=len(BENCH[kind]))
    if t and at < len(BENCH[kind]):
        view['step'] = dict(i=at, title=BENCH[kind][at][0], options=[dict(id=a, label=b) for a, b in _order_pick(r['id'], kind, at)])
    view['ready'] = bool(t) and at >= len(BENCH[kind])
    return view


def _candidate(db, buyer: str, service: str):
    return db.execute("SELECT * FROM restore_tickets WHERE buyer=? AND service=? AND status='open' ORDER BY at,id LIMIT 1", (buyer, service)).fetchone()


def bench(store, sid: str) -> dict:
    with store.connect() as db:
        _release(db, sid)
        rows = [dict(r) for r in db.execute("SELECT * FROM svc_orders WHERE provider=? AND career=? AND status IN ('held','working') "
                                            "ORDER BY created_at LIMIT 30", (sid, CAREER)).fetchall()]
        people = {r['buyer']: mr._display(db, r['buyer']) for r in rows}
        out = []
        for r in rows:
            if r['service'] not in SERVICES:
                continue
            t = db.execute("SELECT * FROM restore_tickets WHERE order_id=? AND status='bound'", (r['id'],)).fetchone() or _candidate(db, r['buyer'], r['service'])
            out.append(_bench_row(r, SERVICES[r['service']]['kind'], dict(t) if t else None, people))
        done = db.execute("SELECT COUNT(*) AS n FROM restore_tickets WHERE provider=? AND status='done'", (sid,)).fetchone()['n']
    return dict(off=off(), orders=out, done=int(done))


def work(store, sid: str, data: dict) -> dict:
    """One step at the bench: {order, pick}. The first step binds the buyer's oldest open ticket of that service."""
    need(not off(), OFF_LINE, 'restore_off', 409)
    need(isinstance(data, dict) and set(data) <= {'order', 'pick'} and isinstance(data.get('order'), str) and sm.ID_RX.fullmatch(data['order'])
         and isinstance(data.get('pick'), str) and len(data['pick']) <= 20, 'Thao tác không hợp lệ.')
    oid, pick = data['order'], data['pick']
    tm = _now()

    def run(db):
        o = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (oid,)).fetchone()
        need(o and o['provider'] == sid and o['career'] == CAREER and o['service'] in SERVICES, 'Không tìm thấy đơn.', 'not_found', 404)
        need(o['status'] == 'working', 'Bấm Nhận đơn ở Phố dịch vụ trước đã.' if o['status'] == 'held' else 'Đơn không còn chờ làm.', 'not_working', 409)
        kind = SERVICES[o['service']]['kind']
        t = db.execute("SELECT * FROM restore_tickets WHERE order_id=? AND status='bound' FOR UPDATE", (oid,)).fetchone()
        if not t:
            c = _candidate(db, o['buyer'], o['service'])
            need(c, 'Khách chưa gửi món nào cho dịch vụ này. Nhắn khách mở 🧰 Phục chế đồ, hoặc từ chối đơn để khách được hoàn tiền.', 'no_ticket', 409)
            if db.execute("UPDATE restore_tickets SET status='bound',order_id=?,provider=?,updated_at=? WHERE id=? AND status='open'",
                          (oid, sid, tm, c['id'])).rowcount != 1:
                raise sm.ServiceError('Phiếu vừa đổi, thử lại nhé.', 'busy', 409)
            t = db.execute('SELECT * FROM restore_tickets WHERE id=?', (c['id'],)).fetchone()
        t = dict(t)
        steps = _load(t['steps'])
        at, wrong = int(steps.get('at') or 0), int(steps.get('wrong') or 0)
        need(at < len(BENCH[kind]), 'Xong cả ba bước rồi, bấm Giao đồ thôi.', 'bench_done', 409)
        title, rows, right = BENCH[kind][at]
        need(pick in {a for a, _ in rows}, 'Chọn một cách làm.')
        right = right or t['style']
        if pick != right:
            steps.update(at=at, wrong=min(9, wrong + 1))
            db.execute('UPDATE restore_tickets SET steps=?,updated_at=? WHERE id=?', (_json(steps), tm, t['id']))
            hint = ('Khách dặn: ' + STYLES[t['style']].lower() + '.') if not BENCH[kind][at][2] else 'Làm vậy hỏng hồn món đồ.'
            return dict(ok=False, message=f'{title}: chưa đúng. {hint} Chọn lại nhé.')
        steps.update(at=at + 1, wrong=wrong)
        db.execute('UPDATE restore_tickets SET steps=?,updated_at=? WHERE id=?', (_json(steps), tm, t['id']))
        return dict(ok=True, message=f'{title}: đúng rồi.' + (' Xong, bấm Giao đồ.' if at + 1 >= len(BENCH[kind]) else ''))
    return store.transaction(run)


# ---------------------------------------------------------------- HTTP (server.py: /api/restore/…)
def get(store, token, state, sub: str, query: dict) -> dict:
    sid = store.key(token)
    if sub == 'mine':
        need(isinstance(state, dict), 'Chưa đọc được tiến trình.')
        return mine(store, sid, state)
    if sub == 'bench':
        return bench(store, sid)
    raise sm.ServiceError('Không tìm thấy.', 'not_found', 404)


def post(store, token, state, sub: str, data: dict) -> dict:
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(), 'Đăng nhập để dùng 🧰 Phục chế đồ.', 'login_required', 401)
    if sub == 'ticket':
        need(isinstance(state, dict), 'Chưa đọc được tiến trình.')
        return open_ticket(store, sid, state, data)
    if sub == 'drop':
        return drop_ticket(store, sid, data)
    if sub == 'work':
        return work(store, sid, data)
    raise sm.ServiceError('Không tìm thấy.', 'not_found', 404)
