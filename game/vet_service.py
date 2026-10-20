"""🩺 Khám, tiêm cho thú cưng của người chơi: a 🩺 Bác sĩ thú y player examines or vaccinates another player's pets through
🛎️ Phố dịch vụ (game/service_market.py), owner 21/10 ("làm thêm nghề khác").

What it does in the buyer's save is exactly what the NPC clinic does (game/pets.py jr_pet_vet), without the clinic's
bill and with the same bond, week points and tricks (pets._care), for one pet per order (qty_max 1: the market's
check cannot see qty, so nobody pays for a pet that is not served):
* 'kham' 🩺: a pet's health back to C.VET['h'] (the pets that need it most first);
* 'tiem' 💉: health + C.VACCINE['h'] (at least its floor) and vaccinated for C.VACCINE['days'] life days (the pets
  whose vaccination ran out first).
It also counts in the pets' stats (vet). No new save key, no table, no schema change: a rollback loads every save.

Flow: the buyer orders from a vet in Phố dịch vụ (escrow there; one pet per order). The vet takes the order and works
it in the career screen (🩺 Phòng khám → Bé của người chơi: ty_svc, three server-graded steps per order,
game/careers/vet.py), then taps Giao (POST /api/svc/done). The deliver hook reads the vet's committed save and refuses
unless that order is in the career's finished list (careers.vet.ext.data.svc_ok).

Kill switch: MNL_VET_SVC_OFF=1 — no new order or delivery (paid orders run out their timers and are refunded).
"""
from __future__ import annotations

from . import marriage as mr
from . import moto_service as ms
from . import service_market as sm

CAREER = 'vet'
OFF_LINE = 'Phòng khám tạm không nhận bé của người chơi, quay lại sau nhé.'
SERVICES = {
    'kham': dict(name='Khám tổng quát cho thú cưng', icon='🩺', unit='bé', duration=30,
                 desc='Khám tai, mắt, răng, nghe tim: sức khỏe bé về lại đầy.'),
    'tiem': dict(name='Tiêm phòng cho thú cưng', icon='💉', unit='bé', duration=30,
                 desc='Tiêm phòng: bé khỏe thêm và ba mươi ngày không lo ốm vặt.'),
}


def off() -> bool:
    return sm.env_on('MNL_VET_SVC_OFF')


def need(cond, message: str, code: str = 'vet_error', status: int = 400):
    if not cond:
        raise sm.ServiceError(message, code, status)


def _base(service: str) -> int:
    from . import pets_content as C
    return (C.VET if service == 'kham' else C.VACCINE)['price']


def candidates(state: dict, service: str) -> list:
    """The buyer's pets this service would help, the neediest first."""
    from . import pets
    b = pets.get(state)
    day = int((state.get('journey') or {}).get('life_day') or 1)
    rows = [p for p in (b or {}).get('list') or () if isinstance(p, dict)]
    if service == 'kham':
        from . import pets_content as C
        rows = [p for p in rows if pets.needs_at(p, day)['h'] < C.FULL]
        return sorted(rows, key=lambda p: pets.needs_at(p, day)['h'])
    rows = [p for p in rows if int(p.get('vac') or 0) < day]
    return sorted(rows, key=lambda p: int(p.get('vac') or 0))


def apply(state: dict, service: str, qty: int) -> list:
    """The clinic's effect on up to `qty` pets of the buyer: [pet names]."""
    from . import pets
    from . import pets_content as C
    day = int(state['journey']['life_day'])
    done = []
    for p in candidates(state, service)[:max(1, int(qty or 1))]:
        pets._tick(p, day)
        if service == 'kham':
            p['h'] = C.VET['h']
        else:
            p['h'] = pets._clamp(max(p['h'] + C.VACCINE['h'], C.VACCINE['floor']))
            p['vac'] = day + C.VACCINE['days'] - 1
        try:   # the bond, the week's points and tricks, as at the NPC clinic (jr_pet_vet)
            pets._care(state, p, 'vet', [])
        except (KeyError, TypeError, ValueError):
            pass
        done.append(str(p.get('n') or ''))
    b = pets.get(state)
    if done and isinstance((b or {}).get('stats'), dict) and type(b['stats'].get('vet')) is int:
        b['stats']['vet'] += len(done)
    return done


# ---------------------------------------------------------------- the market hooks
def _check(service):
    def check(db, buyer, state):
        if off():
            return OFF_LINE
        if candidates(state, service):
            return ''
        return 'Các bé nhà bạn đang khỏe re, chưa cần khám.' if service == 'kham' else 'Các bé nhà bạn còn hạn tiêm phòng.'
    return check


def _can_provide(state) -> str:
    if off():
        return OFF_LINE
    c = (state.get('careers') or {}).get(CAREER)
    if not (isinstance(c, dict) and c.get('started')):
        return 'Bạn cần làm nghề 🩺 Bác sĩ thú y trước đã.'
    if not (isinstance(c.get('job'), dict) and c['job'].get('status') == 'hired'):
        return 'Ứng tuyển vào Phòng khám Thú y Cỏ May trước đã.'   # a vet who left the clinic cannot open a shift
    return ''


def _deliver(db, provider, buyer, order) -> dict:
    need(not off(), OFF_LINE, 'vet_off', 409)
    got = ms.finished(ms._state(db, provider), CAREER).get(order['id'])
    need(got and got.get('s') == order.get('service'), 'Khám xong ở 🩺 Phòng khám (Bé của người chơi) rồi mới giao nhé.', 'vet_bench')
    by = mr._display(db, provider)
    return dict(svc=order.get('service'), grade=int(got['q']), by=str(by or '')[:24])


def _on_buyer(state, order) -> None:
    try:
        apply(state, str(order.get('service') or ''), int(order.get('qty') or 1))
    except Exception:  # noqa: BLE001  (never block the vet's pay over a save that changed shape)
        pass


def install() -> None:
    """Register with Phố dịch vụ (idempotent; called at import and by tests after a registry reset)."""
    for sid, sp in SERVICES.items():
        sm.register(CAREER, sid, dict(name=sp['name'], icon=sp['icon'], desc=sp['desc'], base=_base(sid), unit=sp['unit'], qty_max=1,
                                      duration=sp['duration'], work_hours=72, deliver=_deliver, on_buyer=_on_buyer, confirm='auto',
                                      requires=dict(story=True), check=_check(sid), can_provide=_can_provide,
                                      note_hint='Dặn bác sĩ thêm (bé nào, sợ gì…)'))


install()
