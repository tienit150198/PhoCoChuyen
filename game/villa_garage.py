"""🚘 Hầm để xe: where your vehicles park at home, a villa's underground garage first (story mode).

Owner 23/10: "biệt thự ok thêm hầm để xe"; F#271 "làm cho e hầm để xe của biệt thự sân vườn". The vehicles are
game/garage.py's (bought, painted, plated, ridden there); this is where they stand at home and two light things to do
with them: 🫧 rửa xe (jr_hamxe_wash) and choosing which ones take the bays (jr_hamxe_park). "Đi một vòng" and "Đi chiếc
này" are garage.py's own commands (jr_garage_trip / jr_garage_ride), sent from the garage view as they are.

* Where: the place you live in (game/deco.py place: your home, your spouse's, a villa of Mua sắm, a rented room).
  GARAGES gives each kind of place its parking: a villa's hầm (4 to 12 bays by the villa), a nhà phố's room inside or
  the yard of the Nhà có sân, an apartment block's shared basement, the lot at the head of the alley for a rented room.
* Which vehicles: everything you own that runs on a road (bikes and cars) is derived from journey.garage, nothing to
  migrate. The bays take your picks (`park`, in order) and then the vehicle you ride, then the dearest; the rest wait
  "ngoài sân / bãi gửi". Boats moor at the villa's private berth (BERTH) or the marina, planes at its helipad (PAD,
  helicopters only) or the private airport.
* 🫧 Rửa xe: each vehicle once a life day, free (a bucket and a hose). The first wash of the day adds WASH_SPIRIT
  tinh thần; the others only make it shine ("sạch bóng" until tomorrow). Never xu.

State journey['hamxe'] (absent until the first command; an older build ignores it: journey.validate allows extra keys):
{v, day (the life day of `wash`, 0: never), wash [vehicle ids washed that day], park [vehicle ids picked for the bays,
in order], n (washes in all)}. Ids are checked by shape only: a vehicle sold since, or one a newer build knows, stays
harmless (it is simply not shown).
"""
from __future__ import annotations

import random
import re

from . import garage as gr

VERSION = 1
KEYS = frozenset({'v', 'day', 'wash', 'park', 'n'})
COMMANDS = ('jr_hamxe_wash', 'jr_hamxe_park')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
WASH_SPIRIT = 1                   # the first wash of a life day
PARK_MAX = 16                     # picks kept (the biggest hầm has 12 bays)
ROAD = ('bike', 'car')            # what parks in a garage
HELI = ('truc_thang',)            # what lands on a helipad (and the limited editions built on it)

# kind of place -> (style, name, bays). style: 'ham' a villa's underground garage, 'san' a yard, 'nha' inside the house,
# 'chung' an apartment block's shared basement, 'bai' the lot down the alley.
GARAGES = {
    'attic': ('bai', 'Bãi gửi xe đầu hẻm', 1),
    'tro_moi': ('bai', 'Bãi gửi xe cạnh chợ', 1),
    'ky_tuc_xa': ('bai', 'Nhà xe ký túc xá', 1),
    'tap_the': ('chung', 'Nhà xe khu tập thể', 1),
    'can_ho_studio': ('chung', 'Hầm gửi xe tòa Nắng Mai', 2),
    'can_ho_mini': ('chung', 'Chỗ giữ xe dưới sảnh', 2),
    'can_ho_1pn': ('chung', 'Hầm gửi xe tòa Mây Xanh', 2),
    'can_ho_2pn': ('chung', 'Hầm gửi xe tòa Cánh Diều', 2),
    'penthouse': ('chung', 'Hầm VIP tòa Mây Xanh', 3),
    'nha_pho': ('nha', 'Chỗ để xe trong nhà', 1),
    'nha_san': ('san', 'Sân để xe', 2),
    'biet_thu_vuon': ('ham', 'Hầm để xe Vườn Cau', 4),
    'biet_thu_song': ('ham', 'Hầm để xe Sông Hồng', 6),
    'bt_vuon_da_lat': ('ham', 'Hầm xe dưới đồi thông', 4),
    'bt_dong_duong': ('ham', 'Hầm xe Đông Dương', 6),
    'bt_kinh': ('ham', 'Hầm xe kính Mây', 8),
    'bt_bien': ('ham', 'Hầm xe Mũi Né', 8),
    'penthouse_sky': ('ham', 'Hầm riêng tầng B3', 10),
    'dinh_thu_dao': ('ham', 'Hầm xe Hòn Mây', 12),
}
OTHER = ('bai', 'Bãi gửi xe', 1)  # a kind this build does not know
BERTH = {'biet_thu_song': 'Bến riêng ven sông', 'bt_bien': 'Bến riêng trước biển', 'dinh_thu_dao': 'Bến ca nô của đảo'}
PAD = {'penthouse_sky': 'Sân trực thăng tầng thượng', 'dinh_thu_dao': 'Sân trực thăng trên đảo'}
MARINA, AIRPORT = 'Bến du thuyền', 'Sân bay tư nhân'
WASH_LINES = (
    'Xịt nước, xoa xà phòng, lau khô từng chút. {name} sáng bóng như mới mua.',
    'Bạn bật nhạc, rửa xe dưới hầm mát rượi. {name} bóng lộn, soi gương được luôn.',
    'Xà phòng thơm mùi chanh, nước mát lạnh. Rửa xong {name}, bạn thấy nhẹ cả người.',
)


def _core():
    from . import engine
    return engine


def spec(kind: str | None) -> dict:
    """The parking of a kind of place: {style, name, slots, berth?, pad?} (also in each home_overview plan)."""
    style, name, n = GARAGES.get(kind, OTHER)
    out = dict(style=style, name=name, slots=n)
    if kind in BERTH:
        out['berth'] = BERTH[kind]
    if kind in PAD:
        out['pad'] = PAD[kind]
    return out


def _place_kind(s: dict) -> str | None:
    from . import deco
    pl = deco.place(s['journey'])
    return 'attic' if pl.get('where') == 'attic' else pl.get('kind')


def get(s: dict) -> dict | None:
    b = s['journey'].get('hamxe')
    return b if isinstance(b, dict) else None


def _today(s: dict) -> list:
    b = get(s)
    return list(b['wash']) if b and b.get('day') == s['journey']['life_day'] else []


def _base(vid: str) -> str:
    V = gr.VEHICLES[vid]
    return V.get('base') or vid


def lineup(s: dict, kind: str | None) -> dict:
    """Where each vehicle you own stands: {park: [bays in order], out: [the rest of the road ones], water: [(id, where)],
    air: [(id, where)]}."""
    g = gr.get(s)
    cars = g['cars'] if g else {}
    have = [vid for vid in gr.ORDER if vid in cars]
    road = [vid for vid in have if gr.VEHICLES[vid]['group'] in ROAD]
    b = get(s)
    picks = [vid for vid in (b['park'] if b else []) if vid in road]
    ride = g.get('ride') if g else None
    rest = sorted((vid for vid in road if vid not in picks),
                  key=lambda vid: (vid != ride, -cars[vid]['p'], gr.ORDER.index(vid)))
    order = picks + rest
    n = spec(kind)['slots']
    water = [(vid, BERTH.get(kind, MARINA)) for vid in have if gr.VEHICLES[vid]['group'] == 'boat']
    air = [(vid, PAD[kind] if kind in PAD and _base(vid) in HELI else AIRPORT) for vid in have
           if gr.VEHICLES[vid]['group'] == 'plane']
    return dict(park=order[:n], out=order[n:], water=water, air=air)


def public(s: dict) -> dict | None:
    """journey.public 'homelife.hamxe': the parking where you live and where each vehicle stands (small: ids only; the
    client has the vehicles in journey.garage and the catalogue)."""
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    kind = _place_kind(s)
    L = lineup(s, kind)
    washed = _today(s)
    # Small (it rides on every state): empty lists are left out; the place is homelife.ov.kind, the first wash's
    # tinh thần is the catalogue's (journey.content()['homelife']['wash_spirit']), paid while `wash` is empty.
    return dict(spec(kind), park=L['park'], **({'out': L['out']} if L['out'] else {}),
                **({'water': [list(x) for x in L['water']]} if L['water'] else {}),
                **({'air': [list(x) for x in L['air']]} if L['air'] else {}), **({'wash': washed} if washed else {}))


# ---------------------------------------------------------------- commands
def _ensure(s: dict) -> dict:
    j = s['journey']
    b = get(s)
    if b is None:
        b = j['hamxe'] = dict(v=VERSION, day=0, wash=[], park=[], n=0)
    if b['day'] != j['life_day']:
        b['day'], b['wash'] = j['life_day'], []
    return b


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Hầm để xe chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict), 'Thông tin không hợp lệ.')
    g = gr.get(s)
    cars = g['cars'] if g else {}
    if name == 'jr_hamxe_wash':
        need(set(p) <= {'id'} and isinstance(p.get('id'), str) and p['id'] in gr.VEHICLES, 'Chọn một chiếc xe nhé.')
        vid = p['id']
        V = gr.VEHICLES[vid]
        need(vid in cars, f'Bạn chưa có {gr.vname(V)}.', 'not_owned')
        if vid in _today(s):
            return dict(message=f'{V["emoji"]} {gr.vname(V)[:1].upper() + gr.vname(V)[1:]} vẫn còn sạch bóng. Mai rửa tiếp nhé.',
                        duplicate=True)
        first = not _today(s)
        b = _ensure(s)
        b['wash'].append(vid)
        b['n'] = min(10**6, b['n'] + 1)
        from . import needs as nd
        got = nd._spirit(s, WASH_SPIRIT) if first else 0
        nm = gr.vname(V)
        line = random.Random(f'hamxe|{j.get("seed", 0)}|{j["life_day"]}|{vid}').choice(WASH_LINES).format(name=nm[:1].upper() + nm[1:])
        return dict(message=f'🫧 {line}', effects=[f'😊 Tinh thần +{got}'] if got else [], wash=vid)
    need(set(p) <= {'ids'} and isinstance(p.get('ids'), list) and len(p['ids']) <= PARK_MAX, 'Chọn xe để đỗ nhé.')
    ids = p['ids']
    need(all(isinstance(x, str) and x in cars and x in gr.VEHICLES and gr.VEHICLES[x]['group'] in ROAD for x in ids)
         and len(set(ids)) == len(ids), 'Chỉ xe máy và ô tô của bạn mới đỗ trong hầm.', 'not_owned')
    n = spec(_place_kind(s))['slots']
    need(len(ids) <= n, f'Chỗ này chỉ có {n} chỗ đỗ.', 'limit')
    b = _ensure(s)
    if b['park'] == ids:
        return dict(message='Các xe vẫn đỗ y chỗ cũ.', duplicate=True)
    b['park'] = list(ids)
    return dict(message=f'Đã xếp {len(ids)} xe vào chỗ đỗ.' if ids else 'Để hầm tự xếp xe như cũ.')


# ---------------------------------------------------------------- saves
def _ids_ok(x, cap: int) -> bool:
    return (isinstance(x, list) and len(x) <= cap and len(set(x)) == len(x)
            and all(isinstance(v, str) and ID_RE.fullmatch(v) for v in x))


def _ok(b, life_day: int) -> bool:
    return (isinstance(b, dict) and set(b) == KEYS and b['v'] == VERSION and type(b['day']) is int
            and 0 <= b['day'] <= life_day and _ids_ok(b['wash'], 64) and _ids_ok(b['park'], PARK_MAX)
            and type(b['n']) is int and 0 <= b['n'] <= 10**6)


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'hamxe' not in j:
        return
    _core().need(_ok(j['hamxe'], j.get('life_day', 1)), 'Dữ liệu hầm để xe không hợp lệ.', 'invalid_save')


def upgrade(j: dict) -> None:
    """A block this build cannot read (hand-edited, or a newer shape) is dropped: it holds nothing that can be lost
    (the vehicles live in journey.garage; the picks fall back to the automatic order)."""
    if isinstance(j, dict) and 'hamxe' in j and not _ok(j['hamxe'], j.get('life_day', 1) if type(j.get('life_day')) is int else 0):
        j.pop('hamxe')
