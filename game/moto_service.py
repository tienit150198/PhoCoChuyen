"""🏍️ Bảo dưỡng xe máy cho người chơi: a 🏍️ Thợ sửa xe player services another player's motorbikes through 🛎️ Phố dịch vụ
(game/service_market.py), owner 21/10 ("làm thêm nghề khác").

What it does in the buyer's save (nothing new can break because of this module):
* a pending 🎲 rủi ro warning "xe sắp hỏng" (journey.rui.warn, kind 'xe') on one of the buyer's motorbikes is cleared,
  counted as prevented, like the warning's own "Ghé tiệm kiểm tra" (jr_rui_prevent) without its fee;
* each serviced motorbike rides calmer for CARE_DAYS life days: game/rui.py halves its weight in the daily breakdown draw while
  journey['xe_care'] = {v: 1, cars: {vid: last life day of the care}} says so (care_until). The key is optional: a build
  that does not know it keeps it untouched (journey.validate only asks for its own keys), and a rollback just loses the
  calmer days.

Flow: the buyer orders 'bao_duong' from a mechanic in Phố dịch vụ (escrow there; one motorbike per order, qty_max 1:
the market's check cannot see qty, so nobody pays for a bike that is not serviced). The mechanic takes the order and works it in the career screen (🏍️ Tiệm sửa xe → Xe của người
chơi: xm_svc, three server-graded steps per order, game/careers/moto.py), then taps Giao (POST /api/svc/done). The
market's deliver hook below reads the mechanic's committed save and refuses unless that order is in the career's
finished list (careers.moto.ext.data.svc_ok), so a delivery cannot be claimed without the work.

Kill switch: MNL_MOTO_SVC_OFF=1 — no new order or delivery (paid orders run out their timers and are refunded).
No table, no schema change.
"""
from __future__ import annotations

from . import fastjson
from . import marriage as mr
from . import service_market as sm

CAREER = 'moto'
SERVICE = 'bao_duong'
KEY = 'xe_care'
VERSION = 1
CARE_DAYS = 10
CARS_MAX = 32
OFF_LINE = 'Tiệm sửa xe tạm không nhận xe của người chơi, quay lại sau nhé.'


def off() -> bool:
    return sm.env_on('MNL_MOTO_SVC_OFF')


def need(cond, message: str, code: str = 'moto_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


def bikes(state: dict, group: str | None = 'bike') -> list:
    """The buyer's motorbikes that can break (rui._motor, group 'bike'): [vehicle id]. 🚗 game/dealer_service.py asks for
    group 'car'; None: every vehicle that can break."""
    from . import rui
    try:
        return [vid for vid, _car, V in rui._motor(state) if group is None or V.get('group') == group]
    except Exception:  # noqa: BLE001  (a save without a garage)
        return []


def care_until(state: dict, vid: str) -> int:
    """The last life day of `vid`'s calmer days (0: none): game/rui.py reads it."""
    from . import rui
    return rui.care_until(state, vid)


def apply(state: dict, qty: int, group: str = 'bike', line: str = 'Phòng trước: thợ sửa xe bảo dưỡng') -> list:
    """Service up to `qty` motorbikes of the buyer: [vehicle ids]. The ones with a pending 🎲 warning first, then the
    ones whose calmer days end soonest. The market runs it once per order (ready → done). 🚗 game/dealer_service.py
    services cars the same way (group 'car'); the calmer days of the other group are kept."""
    j = state.get('journey')
    if not isinstance(j, dict):
        return []
    x = j.get(KEY)
    if not isinstance(x, dict) or x.get('v') != VERSION or not isinstance(x.get('cars'), dict):
        x = dict(v=VERSION, cars={})
    from . import rui
    day = int(j.get('life_day') or 1)
    r = rui.get(state)
    warn = r.get('warn') if r else None
    warned = warn.get('ref') if isinstance(warn, dict) and warn.get('kind') == 'xe' else None
    own = bikes(state, group)
    own.sort(key=lambda v: (v != warned, care_until(state, v)))
    done = own[:max(1, min(int(qty or 1), len(own)))] if own else []
    for vid in done:
        x['cars'][vid] = day + CARE_DAYS   # today's draw already ran: CARE_DAYS draws to come
    motor = set(bikes(state, None))
    cars = {k: v for k, v in x['cars'].items() if k in motor and type(v) is int}
    j[KEY] = dict(v=VERSION, cars=dict(sorted(cars.items(), key=lambda kv: -kv[1])[:CARS_MAX]))
    if warned and warned in done:
        r['warn'] = None
        rui._stat(r, 'prevented')
        rui._log(r, day, line)
    return done


# ---------------------------------------------------------------- the market hooks
def _check(db, buyer, state) -> str:
    if off():
        return OFF_LINE
    return '' if bikes(state) else 'Bạn chưa có xe máy nào để mang đi bảo dưỡng.'


def _can_provide(state) -> str:
    if off():
        return OFF_LINE
    c = (state.get('careers') or {}).get(CAREER)
    return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề 🏍️ Thợ sửa xe trước đã.'


def finished(state: dict, career: str = CAREER) -> dict:
    """{order id: {q: ⭐, s: service}} of the provider's finished player jobs in their save (stepkit.svc_work wrote them;
    🩺 game/vet_service.py reads its own career's the same way)."""
    c = (state.get('careers') or {}).get(career)
    rows = (((c or {}).get('ext') or {}).get('data') or {}).get('svc_ok') if isinstance(c, dict) else None
    out = {}
    for x in rows if isinstance(rows, list) else ():
        if isinstance(x, dict) and isinstance(x.get('o'), str) and x.get('q') in (1, 2, 3):
            out[x['o']] = dict(q=x['q'], s=x.get('s'))
    return out


def _state(db, sid: str) -> dict:
    row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    raw = row['state'] if row else None
    if not raw:
        return {}
    try:
        v = fastjson.loads(raw)
    except Exception:  # noqa: BLE001
        return {}
    return v if isinstance(v, dict) else {}


def _deliver(db, provider, buyer, order) -> dict:
    need(not off(), OFF_LINE, 'moto_off', 409)
    got = finished(_state(db, provider)).get(order['id'])
    need(got and got.get('s') == order.get('service'), 'Bảo dưỡng xong ở 🏍️ Tiệm sửa xe (Xe của người chơi) rồi mới giao nhé.', 'moto_bench')
    by = mr._display(db, provider)
    return dict(svc=SERVICE, grade=int(got['q']), by=str(by or '')[:24], days=CARE_DAYS)


def _on_buyer(state, order) -> None:
    try:
        apply(state, int(order.get('qty') or 1))
    except Exception:  # noqa: BLE001  (never block the mechanic's pay over a save that changed shape)
        pass


def install() -> None:
    """Register with Phố dịch vụ (idempotent; called at import and by tests after a registry reset)."""
    sm.register(CAREER, SERVICE, dict(name='Bảo dưỡng xe máy', icon='🔧', base=50, unit='chiếc', qty_max=1, duration=40, work_hours=72,
                                      desc=f'Bơm lốp, thay nhớt, kiểm an toàn: xe bớt hỏng vặt {CARE_DAYS} ngày, gỡ cảnh báo “xe sắp hỏng”.',
                                      deliver=_deliver, on_buyer=_on_buyer, confirm='auto', requires=dict(story=True), check=_check,
                                      can_provide=_can_provide, note_hint='Dặn thợ thêm (xe nào, chạy bao nhiêu km…)'))


install()
