"""🔧 Độ xe cho người chơi: a 🔧 Thợ độ xe player tunes another player's own motorbike or car through 🛎️ Phố dịch vụ
(game/service_market.py), owner 22/10 (player #470 "Thêm độ xe để đua xe": "độ xe này kia làm kĩ vào nhé").

What a player tuner adds that the NPC garage (🔧 Xưởng Tư Pít-tông, game/racing.py jr_tune_buy) does not sell, so
nobody buys a stage cheaper from a player than from the shop:
* 💻 do_dong_co, a hand-tuned map: +racing.FX_POWER % power for the next racing.FX_RACES races of the vehicle;
* 🔩 do_khung_gam, a chassis set-up: +racing.FX_GRIP grip for the next racing.FX_RACES races;
* 🧰 bao_duong_do, a full service of the most worn tuned vehicle: every fitted part back to 100.
The vehicle: the one being ridden when it can race, else the one with the most parts (racing.service_apply).
Every job is street legal (game/careers/tuning.py: the illegal fits are refused at the bench).

Flow: the buyer orders from a tuner in Phố dịch vụ (escrow there; one vehicle per order, qty_max 1). The tuner works the
order in the career screen (🔧 Xưởng độ xe → Xe của người chơi: dx_svc, three server-graded steps per order,
game/careers/tuning.py), then taps Giao (POST /api/svc/done). The market's deliver hook below reads the tuner's
committed save and refuses unless that order is in the career's finished list (careers.tuning.ext.data.svc_ok).

Kill switch: MNL_TUNING_SVC_OFF=1: no new order or delivery (paid orders run out their timers and are refunded).
No table, no schema change; the buyer's save gains only the optional journey['tune'] (game/racing.py).
"""
from __future__ import annotations

from . import fastjson
from . import marriage as mr
from . import service_market as sm

CAREER = 'tuning'
SERVICES = ('do_dong_co', 'do_khung_gam', 'bao_duong_do')
OFF_LINE = 'Xưởng độ xe tạm không nhận xe của người chơi, quay lại sau nhé.'


def off() -> bool:
    return sm.env_on('MNL_TUNING_SVC_OFF')


def need(cond, message: str, code: str = 'tuning_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


def _owned(state: dict) -> list:
    from . import racing
    try:
        return racing.owned(state)
    except Exception:  # noqa: BLE001  (a save without a garage)
        return []


def _worn(state: dict) -> list:
    """The buyer's tuned vehicles with a worn part."""
    from . import racing
    out = []
    for vid in _owned(state):
        car = racing.car_of(state, vid)
        if any(car['m'][k] and car['w'][k] < 100 for k in racing.MODS):
            out.append(vid)
    return out


# ---------------------------------------------------------------- the market hooks
def _check_for(service: str):
    def check(db, buyer, state) -> str:
        if off():
            return OFF_LINE
        if not _owned(state):
            return 'Bạn chưa có xe máy hay ô tô nào để mang đi độ.'
        if service == 'bao_duong_do' and not _worn(state):
            return 'Xe của bạn chưa lắp đồ độ nào bị mòn, chưa cần bảo dưỡng.'
        return ''
    return check


def _can_provide(state) -> str:
    if off():
        return OFF_LINE
    c = (state.get('careers') or {}).get(CAREER)
    return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề 🔧 Thợ độ xe trước đã.'


def finished(state: dict) -> dict:
    """{order id: {q: ⭐, s: service}} of the tuner's finished player jobs (stepkit.svc_work wrote them)."""
    from . import moto_service
    return moto_service.finished(state, CAREER)


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
    need(not off(), OFF_LINE, 'tuning_off', 409)
    got = finished(_state(db, provider)).get(order['id'])
    need(got and got.get('s') == order.get('service'), 'Làm xong ở 🔧 Xưởng độ xe (Xe của người chơi) rồi mới giao nhé.', 'tuning_bench')
    by = mr._display(db, provider)
    return dict(svc=order.get('service'), grade=int(got['q']), by=str(by or '')[:24])


def _on_buyer(state, order) -> None:
    from . import racing
    try:
        racing.service_apply(state, order.get('service'))
    except Exception:  # noqa: BLE001  (never block the tuner's pay over a save that changed shape)
        pass


def install() -> None:
    """Register with Phố dịch vụ (idempotent; called at import and by tests after a registry reset)."""
    from . import racing
    common = dict(unit='chiếc', qty_max=1, duration=40, work_hours=72, deliver=_deliver, on_buyer=_on_buyer, confirm='auto',
                  requires=dict(story=True), can_provide=_can_provide)
    sm.register(CAREER, 'do_dong_co', dict(common, name='Độ map động cơ', icon='💻', base=120, check=_check_for('do_dong_co'),
                                           desc=f'Thợ chỉnh map tận tay trên băng dyno: xe mạnh thêm {racing.FX_POWER}% trong {racing.FX_RACES} lượt đua.',
                                           note_hint='Dặn thợ thêm (xe nào, chạy drag hay đèo…)'))
    sm.register(CAREER, 'do_khung_gam', dict(common, name='Chỉnh khung gầm', icon='🔩', base=120, check=_check_for('do_khung_gam'),
                                             desc=f'Cân lại phuộc, góc lái, áp suất lốp: bám đường thêm {racing.FX_GRIP} điểm trong {racing.FX_RACES} lượt đua.',
                                             note_hint='Dặn thợ thêm (xe nào, chạy drag hay đèo…)'))
    sm.register(CAREER, 'bao_duong_do', dict(common, name='Bảo dưỡng xe độ', icon='🧰', base=80, check=_check_for('bao_duong_do'),
                                             desc='Thay lốp mòn, má phanh, kiểm lại đồ độ: mọi món đã lắp mới lại như vừa ra xưởng.',
                                             note_hint='Dặn thợ thêm (xe nào, chỗ nào kêu…)'))


install()
