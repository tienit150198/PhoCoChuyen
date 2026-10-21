"""🚗 Bảo dưỡng ô tô cho người chơi: a 🚗 Đại lý xe player services another player's car through 🛎️ Phố dịch vụ
(game/service_market.py). Player #472 asked for "làm chủ bán xe hơi, xe máy"; the showroom's after-sales is the one thing
it sells to players (a vehicle itself is bought in 🚗 Xe & phương tiện, game/garage.py, where its xu are a sink).

What it does in the buyer's save is what 🏍️ game/moto_service.py does for a motorbike, for one car per order: a pending
🎲 rủi ro "xe sắp hỏng" warning on that car is cleared (counted as prevented) and the car rides calmer for
moto_service.CARE_DAYS life days (journey.xe_care, read by game/rui.py care_until for any vehicle). Same optional key,
same rollback story: a build that does not know a car in it keeps it untouched.

Flow: the buyer orders 'bao_duong_oto' from a dealer (escrow there; qty_max 1). The dealer takes the order and works it
in the career screen (🚗 Đại lý xe → Xe của người chơi: dx_svc, three server-graded steps, game/careers/car_dealer.py),
then taps Giao (POST /api/svc/done). The deliver hook reads the dealer's committed save and refuses unless that order
is in the career's finished list (careers.car_dealer.ext.data.svc_ok).

Kill switch: MNL_DEALER_SVC_OFF=1. No table, no schema change.
"""
from __future__ import annotations

from . import marriage as mr
from . import moto_service as ms
from . import service_market as sm

CAREER = 'car_dealer'
SERVICE = 'bao_duong_oto'
OFF_LINE = 'Đại lý xe tạm không nhận xe của người chơi, quay lại sau nhé.'


def off() -> bool:
    return sm.env_on('MNL_DEALER_SVC_OFF')


def need(cond, message: str, code: str = 'dealer_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


def cars(state: dict) -> list:
    """The buyer's cars that can break: [vehicle id]."""
    return ms.bikes(state, 'car')


def _check(db, buyer, state) -> str:
    if off():
        return OFF_LINE
    return '' if cars(state) else 'Bạn chưa có ô tô nào để mang đi bảo dưỡng.'


def _can_provide(state) -> str:
    if off():
        return OFF_LINE
    c = (state.get('careers') or {}).get(CAREER)
    return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề 🚗 Đại lý xe trước đã.'


def _deliver(db, provider, buyer, order) -> dict:
    need(not off(), OFF_LINE, 'dealer_off', 409)
    got = ms.finished(ms._state(db, provider), CAREER).get(order['id'])
    need(got and got.get('s') == order.get('service'), 'Bảo dưỡng xong ở 🚗 Đại lý xe (Xe của người chơi) rồi mới giao nhé.', 'dealer_bench')
    by = mr._display(db, provider)
    return dict(svc=SERVICE, grade=int(got['q']), by=str(by or '')[:24], days=ms.CARE_DAYS)


def _on_buyer(state, order) -> None:
    try:
        ms.apply(state, int(order.get('qty') or 1), 'car', 'Phòng trước: đại lý bảo dưỡng ô tô')
    except Exception:  # noqa: BLE001  (never block the dealer's pay over a save that changed shape)
        pass


def install() -> None:
    """Register with Phố dịch vụ (idempotent; called at import and by tests after a registry reset)."""
    sm.register(CAREER, SERVICE, dict(name='Bảo dưỡng ô tô', icon='🚗', base=120, unit='chiếc', qty_max=1, duration=40, work_hours=72,
                                      desc=f'Thay nhớt, kiểm phanh, lốp, đèn: ô tô bớt hỏng vặt {ms.CARE_DAYS} ngày, gỡ cảnh báo “xe sắp hỏng”.',
                                      deliver=_deliver, on_buyer=_on_buyer, confirm='auto', requires=dict(story=True), check=_check,
                                      can_provide=_can_provide, note_hint='Dặn đại lý thêm (xe nào, chạy bao nhiêu km…)'))


install()
