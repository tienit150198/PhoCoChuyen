"""🏁 Đường đua Bến Mây: tune your own motorbike or car, then race it (owner 22/10, player #470 "Thêm độ xe để đua xe
đi ad ơi": "độ xe này kia làm kĩ vào nhé").

Tuning your own vehicle (story mode, a save key; every rule here, the client only draws it)
* Four lines, three stages each (MODS): ⚙️ Động cơ (power), 🔩 Khung gầm (weight and grip), 🛑 Phanh, 🛞 Lốp (grip).
  Stage n needs stage n-1. Price a stage: STAGE_PCT % of the vehicle's catalogue price, never below the class floor
  (STAGE_MIN), rounded up to 10 xu; paid to 🔧 Xưởng Tư Pít-tông (a money sink: it goes to nobody), wallet first then
  the bank account, never into debt (jr_tune_buy {id, mod}). Every part is street legal: the garage fits nothing else.
* Wear: each race wears the parts (WEAR: tyres fastest); a part's bonus is scaled by 40 % + 60 % × its wear left.
  🧰 Bảo dưỡng xe độ at the garage (jr_tune_fix {id}) brings every part back to 100 for FIX_PCT % of the worn value.
* A player 🔧 Thợ độ xe (game/tuning_service.py, Phố dịch vụ) adds what the NPC garage cannot: a hand-tuned map
  (+FX_POWER % power) or a chassis set-up (+FX_GRIP grip) for the next FX_RACES races, or a full service of the most
  worn tuned vehicle.
* Selling a vehicle loses its parts (the record of a vehicle no longer owned is dropped at the next write).

Racing (POST /api/race/<op>, server.py; deterministic: the result is a pure function of the run's inputs, so every
run is stored with them and replays exactly)
* Two tracks: 🏁 Drag 400 m (launch: êm / vừa / mạnh, then three shifts: sớm / đúng vạch / trễ) and ⛰️ Đèo Mây Bay
  (five corners, a braking point each: sớm / vừa / muộn). The notebook (NOTES) tells the rules the choices follow
  from the vehicle's numbers; a little luck (LUCK_PERMIL ‰ of the time, seeded by the run's id).
* Two classes, never mixed: 🏍️ xe máy, 🚗 ô tô (bicycles cannot race).
* ⏱️ Chạy tính giờ (`trial`): TRIAL_FEE xu a run (burned: the track's rent), TRIAL_DAY runs a Vietnam day. The best
  time of the Vietnam ISO week per track and class makes the weekly board; its top 3 hold weekly titles
  (game/lb_titles.py boards race_*).
* ⚔️ Đua tay đôi (`challenge` / `accept`, async): the challenger runs first (a fixed fee from FEES, escrowed from the
  save); anyone in the same class whose vehicle is within PI_GAP of theirs runs the same track later. Both pay the
  same fee; the faster takes the pot minus BURN_PCT % (burned); a dead heat refunds both in full. An open challenge
  expires after OPEN_HOURS with a full refund (run_housekeeping, or the challenger's next visit).

Safety (inside the transaction that moves the money)
* No betting beyond the fixed entry fee: no side stakes, no custom amounts, nothing transferable but the pot.
* Duels: both accounts at least ACCOUNT_DAYS real days old; never two players seen on one network (service_market
  same_net), never a blocked pair; the same two players at most PAIR_DAY duels a Vietnam day; a player at most
  DUEL_DAY accepted duels and OPEN_MAX open challenges; the fee counts toward a new account's day cap
  (bank_xfer.count_out). Trials: a registered account, TRIAL_DAY a day.
* 🛑 MNL_RACE_OFF=1: no new run or challenge; open challenges can still be cancelled and expire with their refund.

Tables (game/pg_schema.py SCHEMA_VERSION 84): race_runs (every time-trial run with its inputs), race_duels (every
duel, open → done | tie | cancelled | expired). Save: only the optional journey['tune'] (older builds keep it unread:
journey.validate allows extra keys), so a rollback just hides the parts until the build comes back.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import time

from . import marriage as mr

VERSION = 1
KEY = 'tune'
MODS = ('may', 'gam', 'phanh', 'lop')
STAGES = 3
CLASSES = {'bike': ('🏍️', 'Xe máy'), 'car': ('🚗', 'Ô tô')}
# base model id (game/garage.py VEHICLES; limited editions race as their base) → class, power (mã lực), weight with the
# rider (kg), grip, brakes (0–100)
BASE = {
    'xe_so': ('bike', 9, 165, 40, 35),
    'xe_ga': ('bike', 11, 185, 45, 42),
    'o_to_mini': ('car', 70, 980, 48, 50),
    'o_to_suv': ('car', 150, 1980, 46, 52),
    'mui_tran': ('car', 180, 1280, 60, 58),
    'sieu_xe': ('car', 600, 1480, 82, 85),
}
MOD_INFO = {
    'may': dict(emoji='⚙️', name='Động cơ', stages={'bike': ('Map ECU mới', 'Pô và lọc gió đạt chuẩn', 'Nồi và nhông đua'),
                                                    'car': ('Map ECU mới', 'Pô và lọc gió đạt chuẩn', 'Turbo đúng luật')}),
    'gam': dict(emoji='🔩', name='Khung gầm', stages={'bike': ('Phuộc chỉnh được', 'Khung nhẹ, bỏ đồ thừa', 'Ghế và mâm nhẹ'),
                                                      'car': ('Phuộc chỉnh được', 'Ghế nhẹ, bỏ đồ thừa', 'Cánh gió đúng luật')}),
    'phanh': dict(emoji='🛑', name='Phanh', stages={'bike': ('Má phanh hiệu năng', 'Đĩa lớn', 'Heo phanh 4 piston'),
                                                    'car': ('Má phanh hiệu năng', 'Đĩa lớn', 'Heo phanh 6 piston')}),
    'lop': dict(emoji='🛞', name='Lốp', stages={'bike': ('Lốp bám đường', 'Lốp thể thao', 'Lốp bán đua'),
                                                'car': ('Lốp bám đường', 'Lốp thể thao', 'Lốp bán đua')}),
}
POWER = (8, 16, 26)          # % power by stage of ⚙️ Động cơ
LIGHTER = (3, 6, 9)          # % weight off by stage of 🔩 Khung gầm
GAM_GRIP = (3, 6, 10)        # grip by stage of 🔩 Khung gầm
BRAKE = (10, 20, 30)         # brakes by stage of 🛑 Phanh
TYRE = (6, 12, 18)           # grip by stage of 🛞 Lốp
STAGE_PCT = (4, 9, 16)       # % of the vehicle's price a stage
STAGE_MIN = {'bike': (40, 90, 160), 'car': (120, 270, 480)}
WEAR = {'lop': 10, 'phanh': 6, 'may': 3, 'gam': 2}   # wear a race
SLIDE_WEAR = 3               # tyres again for each slide / wheelspin
FIX_PCT = 25                 # % of the worn value of the parts
FIX_MIN = 10
FX_RACES, FX_POWER, FX_GRIP = 10, 3, 4   # a player tuner's hand-tuned map / chassis set-up
CARS_MAX = 32

TRACKS = {
    'drag': dict(emoji='🏁', name='Drag 400 m', where='Trường đua Bến Mây'),
    'deo': dict(emoji='⛰️', name='Đèo Mây Bay', where='Đèo Mây Bay, ngày đóng đường'),
}
LAUNCH = ('em', 'vua', 'manh')
LAUNCH_AT = (35, 70)         # chỉ số bám đề-pa (100 × grip ÷ power per tonne): vừa from 35, mạnh from 70
SHIFT = ('som', 'dung', 'tre')
BRAKE_AT = ('som', 'vua', 'muon')
CORNERS = (('gat', 'Cua tay áo'), ('vua', 'Cua chữ S'), ('dai', 'Cua vòng cung'), ('gat', 'Cua đá lở'), ('vua', 'Cua về đích'))
CORNER_BASE = {'gat': 9.0, 'vua': 6.0, 'dai': 8.0}
WORDS = dict(launch=dict(em='Êm', vua='Vừa', manh='Mạnh'), shift=dict(som='Sớm', dung='Đúng vạch', tre='Trễ'),
             brake=dict(som='Sớm', vua='Vừa', muon='Muộn'))
LUCK_PERMIL = 4
TRIAL_FEE = {'drag': 5, 'deo': 8}
FEES = (10, 20, 50)
BURN_PCT = 20
TRIAL_DAY = 20
DUEL_DAY = 10
OPEN_MAX = 3
PAIR_DAY = 2
ACCOUNT_DAYS = 3
OPEN_HOURS = 24
PI_GAP = 20                  # % a duel's two vehicles may differ in performance index
BOARD_TOP = 20
DAY = 86400
OUT_KIND = 'life'            # a wallet row's kind (journey.HISTORY_KINDS: older builds read the save back)
NOTES = (
    'Mọi con số dưới đây là luật đường đua Bến Mây của trò chơi.',
    'Xe máy đua với xe máy, ô tô đua với ô tô. Xe đạp không vào đường đua.',
    'Drag, đề-pa: chỉ số bám đề-pa từ 70 trở lên đề-pa mạnh; từ 35 đến dưới 70 đề-pa vừa; dưới 35 đề-pa êm kẻo bốc khói bánh.',
    'Drag, sang số: số 1 sang sớm khi chỉ số bám đề-pa dưới 35, còn lại sang đúng vạch; số 2 và số 3 luôn sang đúng vạch.',
    'Đèo, điểm phanh theo độ chắc (bám và phanh chia đôi): cua gắt dưới 50 phanh sớm, từ 50 phanh vừa; '
    'cua vừa dưới 75 phanh vừa, từ 75 phanh muộn; cua vòng cung dưới 60 phanh vừa, từ 60 phanh muộn.',
    'Phanh sớm hơn cần thì mất ít thời gian; phanh muộn quá thì trượt bánh, mất nhiều hơn và mòn lốp.',
    'Mỗi lượt đua làm mòn đồ độ, lốp mòn nhanh nhất. Đồ mòn thì yếu đi: bảo dưỡng ở xưởng cho mới lại.',
    'Đua tay đôi: phí vào cửa cố định, hai bên như nhau; người nhanh hơn lấy cả hũ trừ 20% phí sân. Không cược thêm.',
)
OFF_TEXT = 'Đường đua tạm đóng, quay lại sau nhé.'


class RaceError(mr.MarriageError):
    """A refusal shown as is (the server answers a MarriageError with its status and code)."""


def need(cond, message: str, code: str = 'race_error', status: int = 400):
    if not cond:
        raise RaceError(message, code, status)


def off() -> bool:
    return os.environ.get('MNL_RACE_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def now() -> float:
    return time.time()


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def ceil10(n: float) -> int:
    return int(math.ceil(n / 10.0)) * 10


# ---------------------------------------------------------------- the vehicles and their parts (pure)
def _garage():
    from . import garage as gr
    return gr


def base_of(vid: str) -> str | None:
    """The model a vehicle races as (a limited edition: its base), or None (cannot race: bicycles, boats, planes)."""
    V = _garage().VEHICLES.get(vid)
    if not V:
        return None
    b = V.get('base') or vid
    return b if b in BASE else None


def class_of(vid: str) -> str | None:
    b = base_of(vid)
    return BASE[b][0] if b else None


def stage_price(vid: str, mod: str, stage: int) -> int:
    """The price of stage `stage` (1..3) of `mod` on vehicle `vid`."""
    cls = class_of(vid)
    price = int(_garage().VEHICLES[vid]['price'])
    return max(STAGE_MIN[cls][stage - 1], ceil10(price * STAGE_PCT[stage - 1] / 100))


def _blank_car() -> dict:
    return dict(m={k: 0 for k in MODS}, w={k: 100 for k in MODS}, fx={}, spent=0)


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s.get('journey'), dict) else None
    x = j.get(KEY) if j else None
    return x if isinstance(x, dict) and x.get('v') == VERSION and isinstance(x.get('cars'), dict) else None


def _ensure(s: dict) -> dict:
    x = get(s)
    if x is None:
        x = dict(v=VERSION, cars={}, stats=dict(bought=0, fixed=0, races=0, spent=0))
        s['journey'][KEY] = x
    return x


def car_of(s: dict, vid: str) -> dict:
    """The parts record of `vid` (a fresh blank one when none: never stored by reading)."""
    x = get(s)
    c = (x or {}).get('cars', {}).get(vid)
    return c if _car_ok(vid, c) else _blank_car()


def owned(s: dict) -> list:
    """[vehicle id] the player owns that can race, in catalogue order."""
    gr = _garage()
    g = gr.get(s)
    cars = (g or {}).get('cars') or {}
    return [vid for vid in gr.ORDER if vid in cars and base_of(vid)]


def _factor(w: int) -> float:
    return 0.4 + 0.6 * max(0, min(100, w)) / 100


def perf(s: dict, vid: str) -> dict:
    """The racing numbers of `vid` now: {cls, hp, kg, grip, brake, launch, firm, pi} (one decimal)."""
    return perf_of(vid, car_of(s, vid))


def perf_of(vid: str, car: dict) -> dict:
    cls, hp, kg, grip, brake = BASE[base_of(vid)]
    m, w, fx = car['m'], car['w'], car.get('fx') or {}
    if m['may']:
        hp *= 1 + POWER[m['may'] - 1] / 100 * _factor(w['may'])
    if fx.get('may'):
        hp *= 1 + FX_POWER / 100
    if m['gam']:
        f = _factor(w['gam'])
        kg *= 1 - LIGHTER[m['gam'] - 1] / 100 * f
        grip += GAM_GRIP[m['gam'] - 1] * f
    if fx.get('gam'):
        grip += FX_GRIP
    if m['phanh']:
        brake += BRAKE[m['phanh'] - 1] * _factor(w['phanh'])
    if m['lop']:
        grip += TYRE[m['lop'] - 1] * _factor(w['lop'])
    hp, kg, grip, brake = round(hp, 1), round(kg, 1), round(min(grip, 120), 1), round(min(brake, 120), 1)
    launch = round(100 * grip / (hp / kg * 1000), 1)
    firm = round((grip + brake) / 2, 1)
    pi = int(round(1000 * math.sqrt(hp / kg) * (grip + brake) / 200))
    return dict(cls=cls, hp=hp, kg=kg, grip=grip, brake=brake, launch=launch, firm=firm, pi=pi)


# ---------------------------------------------------------------- the race (pure, deterministic)
def _rng(seed: str, salt: str) -> float:
    """A number in [0, 1) from the run's seed (no global random state)."""
    h = hashlib.sha256(f'{seed}|{salt}'.encode()).digest()
    return int.from_bytes(h[:8], 'big') / 2**64


def ideal_launch(p: dict) -> str:
    return 'manh' if p['launch'] >= LAUNCH_AT[1] else 'vua' if p['launch'] >= LAUNCH_AT[0] else 'em'


def ideal_shift(p: dict, gear: int) -> str:
    return 'som' if gear == 0 and p['launch'] < LAUNCH_AT[0] else 'dung'


def ideal_brake(p: dict, kind: str) -> str:
    f = p['firm']
    if kind == 'gat':
        return 'vua' if f >= 50 else 'som'
    if kind == 'vua':
        return 'muon' if f >= 75 else 'vua'
    return 'muon' if f >= 60 else 'vua'


def check_choices(track: str, c) -> dict:
    """The choices of a run, checked: drag {launch, shifts: [3]}, deo {brakes: [5]}."""
    need(isinstance(c, dict), 'Chọn cách chạy trước nhé.', 'bad_choices')
    if track == 'drag':
        need(set(c) == {'launch', 'shifts'} and c['launch'] in LAUNCH and isinstance(c['shifts'], list) and len(c['shifts']) == 3
             and all(x in SHIFT for x in c['shifts']), 'Chọn đề-pa và ba lần sang số nhé.', 'bad_choices')
        return dict(launch=c['launch'], shifts=list(c['shifts']))
    need(set(c) == {'brakes'} and isinstance(c['brakes'], list) and len(c['brakes']) == len(CORNERS)
         and all(x in BRAKE_AT for x in c['brakes']), 'Chọn điểm phanh cho từng khúc cua nhé.', 'bad_choices')
    return dict(brakes=list(c['brakes']))


def run(track: str, p: dict, choices: dict, seed: str) -> dict:
    """One run: {ms, legs: [{label, ms, note, ok}], slides}. Pure: the same inputs give the same run."""
    legs, slides = [], 0
    if track == 'drag':
        lbhp = p['kg'] * 2.2046 / p['hp']
        base = 5.825 * lbhp ** (1 / 3)
        want = ideal_launch(p)
        d = LAUNCH.index(choices['launch']) - LAUNCH.index(want)
        lose = 0.0 if d == 0 else (0.45 if d == 1 else 0.9) if d > 0 else (0.25 if d == -1 else 0.55)
        if d > 0:
            slides += d
        note = 'Đề-pa đẹp' if d == 0 else 'Bốc khói bánh' if d > 0 else 'Đề-pa hụt ga'
        legs.append(dict(label='Đề-pa', ms=int(round((base * 0.28 + lose) * 1000)), note=note, ok=d == 0))
        for g, ch in enumerate(choices['shifts']):
            want = ideal_shift(p, g)
            pen = 0.0 if ch == want else 0.12 if ch == 'som' else 0.10 if ch == 'tre' else 0.08
            legs.append(dict(label=f'Lên số {g + 2}', ms=int(round((base * 0.24 + pen) * 1000)),
                             note='Đúng nhịp' if ch == want else 'Sang sớm, hụt lực' if ch == 'som' else 'Sang trễ, chạm ngưỡng' if ch == 'tre' else 'Lệch nhịp',
                             ok=ch == want))
    else:
        straight = 30 * (p['kg'] / p['hp']) ** 0.33
        factor = 120 / (p['grip'] + p['brake'] / 2 + 40)
        for i, ((kind, name), ch) in enumerate(zip(CORNERS, choices['brakes'])):
            want = ideal_brake(p, kind)
            d = BRAKE_AT.index(ch) - BRAKE_AT.index(want)
            pen = 0.0 if d == 0 else 1.1 * d if d > 0 else 0.35 * -d
            if d > 0:
                slides += d
            t = straight / len(CORNERS) + CORNER_BASE[kind] * factor + pen
            legs.append(dict(label=name, ms=int(round(t * 1000)), note='Vào cua gọn' if d == 0 else 'Trượt bánh' if d > 0 else 'Phanh sớm, chậm',
                             ok=d == 0))
    total = sum(x['ms'] for x in legs)
    luck = (_rng(seed, 'luck') * 2 - 1) * LUCK_PERMIL / 1000
    ms = max(1, int(round(total * (1 + luck))))
    return dict(ms=ms, legs=legs, slides=slides, luck=round(luck * 1000, 2))


def wear_after(car: dict, slides: int) -> dict:
    """The parts record after one race: wear on fitted parts, a hand-tune counts down. A copy."""
    c = json.loads(json.dumps(car))
    for k in MODS:
        if c['m'][k]:
            c['w'][k] = max(0, c['w'][k] - WEAR[k] - (SLIDE_WEAR * slides if k == 'lop' else 0))
    c['fx'] = {k: n - 1 for k, n in (c.get('fx') or {}).items() if n > 1}
    return c


# ---------------------------------------------------------------- the save: validation and commands
VID_RE = re.compile(r'^[a-z0-9_]{1,40}$')


def _car_ok(vid, c) -> bool:
    if not (isinstance(vid, str) and VID_RE.fullmatch(vid) and isinstance(c, dict) and set(c) == {'m', 'w', 'fx', 'spent'}):
        return False
    m, w, fx = c['m'], c['w'], c['fx']
    return (isinstance(m, dict) and set(m) == set(MODS) and all(type(v) is int and 0 <= v <= STAGES for v in m.values())
            and isinstance(w, dict) and set(w) == set(MODS) and all(type(v) is int and 0 <= v <= 100 for v in w.values())
            and isinstance(fx, dict) and set(fx) <= {'may', 'gam'} and all(type(v) is int and 1 <= v <= FX_RACES for v in fx.values())
            and type(c['spent']) is int and 0 <= c['spent'] <= 10**12)


def validate(s: dict) -> None:
    """journey['tune'] (optional). Raises GameError like validate_state."""
    from . import engine as e
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    x = j[KEY]
    bad = 'Đồ độ xe trong bản lưu không hợp lệ.'
    e.need(isinstance(x, dict) and set(x) == {'v', 'cars', 'stats'} and x['v'] == VERSION, bad, 'invalid_save')
    e.need(isinstance(x['cars'], dict) and len(x['cars']) <= CARS_MAX and all(_car_ok(k, v) for k, v in x['cars'].items()), bad, 'invalid_save')
    st = x['stats']
    e.need(isinstance(st, dict) and set(st) == {'bought', 'fixed', 'races', 'spent'}
           and all(type(v) is int and 0 <= v <= 10**12 for v in st.values()), bad, 'invalid_save')


def _store_car(s: dict, vid: str, car: dict) -> None:
    """Write `vid`'s record and drop the records of vehicles no longer owned."""
    x = _ensure(s)
    mine = set(owned(s))
    x['cars'] = {k: v for k, v in x['cars'].items() if k in mine}
    x['cars'][vid] = car


def fix_price(vid: str, car: dict) -> int:
    """🧰 What a full service costs at the garage now (0: nothing worn)."""
    worn = 0.0
    for k in MODS:
        st = car['m'][k]
        if st and car['w'][k] < 100:
            value = sum(stage_price(vid, k, n) for n in range(1, st + 1))
            worn += value * (100 - car['w'][k]) / 100
    return max(FIX_MIN, ceil10(worn * FIX_PCT / 100)) if worn else 0


def _story(s: dict) -> dict:
    from . import engine as e
    j = s.get('journey') if isinstance(s.get('journey'), dict) else None
    e.need(j and j.get('story'), 'Độ xe chỉ có trong chế độ hành trình.')
    return j


def _vid(s: dict, p: dict) -> str:
    from . import engine as e
    vid = p.get('id')
    e.need(isinstance(vid, str) and vid in owned(s), 'Chọn một chiếc xe máy hoặc ô tô của bạn nhé.')
    from . import rui
    e.need(not rui.is_broken(s, 'xe', vid), 'Xe đang hỏng. Sửa xe trước rồi hãy độ nhé.')
    return vid


def action(s: dict, name: str, p: dict) -> dict:
    """jr_tune_buy {id, mod}: the next stage of a part at 🔧 Xưởng Tư Pít-tông; jr_tune_fix {id}: a full service."""
    from . import engine as e
    gr = _garage()
    j = _story(s)
    e.need(isinstance(p, dict), 'Thao tác độ xe không hợp lệ.')
    vid = _vid(s, p)
    V = gr.VEHICLES[vid]
    car = car_of(s, vid)
    have = gr._have(s)
    e.need(j['wallet'] >= 0, f'Ví đang nợ {fmt(-j["wallet"])} xu. Trả nợ trước nhé.')
    if name == 'jr_tune_buy':
        e.need(set(p) <= {'id', 'mod', 'confirm'}, 'Thao tác độ xe không hợp lệ.')
        mod = p.get('mod')
        e.need(mod in MODS, 'Chọn món độ nhé.')
        st = car['m'][mod] + 1
        e.need(st <= STAGES, f'{MOD_INFO[mod]["name"]} đã độ tới cấp cao nhất.')
        price = stage_price(vid, mod, st)
        e.need(have['ready'] >= price, f'Còn thiếu {fmt(price - have["ready"])} xu (ví và tài khoản).')
        part = MOD_INFO[mod]['stages'][class_of(vid)][st - 1]
        where = gr._take(s, price, f'🔧 Độ {gr.lname(V["name"])}: {part[:1].lower() + part[1:]}')
        car['m'][mod] = st
        car['w'][mod] = 100
        car['spent'] += price
        _store_car(s, vid, car)
        x = get(s)
        x['stats']['bought'] += 1
        x['stats']['spent'] += price
        p2 = perf_of(vid, car)
        return dict(message=f'🔧 Xưởng Tư Pít-tông lắp {part[:1].lower() + part[1:]} (cấp {st}) cho {gr.lname(V["name"])}: {where}. '
                            f'Chỉ số đua {fmt(p2["pi"])}.')
    e.need(name == 'jr_tune_fix', 'Thao tác độ xe không hợp lệ.')
    e.need(set(p) <= {'id', 'confirm'}, 'Thao tác độ xe không hợp lệ.')
    price = fix_price(vid, car)
    e.need(price > 0, 'Đồ độ còn mới, chưa cần bảo dưỡng.')
    e.need(have['ready'] >= price, f'Còn thiếu {fmt(price - have["ready"])} xu (ví và tài khoản).')
    where = gr._take(s, price, f'🧰 Bảo dưỡng xe độ: {gr.lname(V["name"])}')
    car['w'] = {k: 100 for k in MODS}
    car['spent'] += price
    _store_car(s, vid, car)
    x = get(s)
    x['stats']['fixed'] += 1
    x['stats']['spent'] += price
    return dict(message=f'🧰 Xưởng Tư Pít-tông bảo dưỡng {gr.lname(V["name"])}: đồ độ mới lại như vừa lắp ({where}).')


def service_apply(s: dict, service: str) -> str | None:
    """🔧 A player tuner's work on the buyer's save (game/tuning_service.py): the vehicle ridden when it can race, else
    the one with the most parts (do_dong_co / do_khung_gam), or the most worn tuned one (bao_duong_do). The vehicle
    id, or None (no vehicle: nothing changes)."""
    mine = owned(s)
    if not mine:
        return None
    g = _garage().get(s) or {}
    if service == 'bao_duong_do':
        worn = [(sum(100 - car_of(s, v)['w'][k] for k in MODS if car_of(s, v)['m'][k]), v) for v in mine]
        worn.sort(key=lambda x: (-x[0], mine.index(x[1])))
        vid = worn[0][1]
        car = car_of(s, vid)
        car['w'] = {k: 100 for k in MODS}
    else:
        ride = g.get('ride')
        vid = ride if ride in mine else max(mine, key=lambda v: (sum(car_of(s, v)['m'].values()), -mine.index(v)))
        car = car_of(s, vid)
        car['fx'] = dict(car.get('fx') or {}, **{('may' if service == 'do_dong_co' else 'gam'): FX_RACES})
    _store_car(s, vid, car)
    return vid


# ---------------------------------------------------------------- views
def car_view(s: dict, vid: str) -> dict:
    gr = _garage()
    V = gr.VEHICLES[vid]
    car = car_of(s, vid)
    cls = class_of(vid)
    from . import rui
    mods = []
    for k in MODS:
        st = car['m'][k]
        nxt = st + 1 if st < STAGES else None
        mods.append(dict(id=k, emoji=MOD_INFO[k]['emoji'], name=MOD_INFO[k]['name'], stage=st, wear=car['w'][k],
                         part=MOD_INFO[k]['stages'][cls][st - 1] if st else '',
                         next=dict(stage=nxt, part=MOD_INFO[k]['stages'][cls][nxt - 1], price=stage_price(vid, k, nxt)) if nxt else None))
    return dict(id=vid, name=V['name'], emoji=V['emoji'], cls=cls, perf=perf(s, vid), mods=mods, fx=dict(car.get('fx') or {}),
                fix=fix_price(vid, car), broken=rui.is_broken(s, 'xe', vid), spent=car['spent'])


def view(s: dict) -> dict:
    """Your vehicles that can race, their parts, prices and numbers."""
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    g = _garage().get(s) or {}
    return dict(story=bool(j.get('story')), ride=g.get('ride'), cars=[car_view(s, v) for v in owned(s)],
                wallet=max(0, j.get('wallet') or 0))


def content() -> dict:
    """The static rules for the client (the track page and the notebook)."""
    return dict(tracks=TRACKS, classes={k: dict(emoji=e, name=n) for k, (e, n) in CLASSES.items()}, corners=[dict(kind=k, name=n) for k, n in CORNERS],
                words=WORDS, notes=NOTES, fees=FEES, trial_fee=TRIAL_FEE, burn_pct=BURN_PCT, trial_day=TRIAL_DAY, duel_day=DUEL_DAY,
                open_max=OPEN_MAX, pair_day=PAIR_DAY, account_days=ACCOUNT_DAYS, open_hours=OPEN_HOURS, pi_gap=PI_GAP,
                fx=dict(races=FX_RACES, power=FX_POWER, grip=FX_GRIP))


# ---------------------------------------------------------------- the database side (POST /api/race/<op>)
def vn_day(t: float) -> str:
    from .wedding_live import vn_day as d
    return d(t)


def vn_week(t: float) -> str:
    from .wedding_live import vn_week as w
    return w(t)


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) and text else default
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def pid_of(sid: str) -> str:
    from . import pet_arena
    return pet_arena.pid_of(sid)


ACCOUNT_LINE = 'Tạo tài khoản để chạy tính giờ và đua tay đôi nhé.'


def _who(store, token, guest_ok: bool = False) -> tuple:
    """The caller. A guest (no account) may look (home: tune page, boards) but not race: boards show names."""
    sid, display = mr.whoami(store, token)
    need(sid, 'Phiên chơi đã hết hạn. Tải lại trang nhé.', 'session_missing', 401)
    need(display or guest_ok, ACCOUNT_LINE, 'account_required', 403)
    return sid, display


def _state(store, sid: str) -> dict:
    with store.connect() as db:
        row = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,), text_bytes=True).fetchone()
    need(row, 'Không tìm thấy tiến trình của bạn.', 'session_missing', 404)
    return store.parse_state(row['state'], sid)


def _old(db, sid: str, t: float) -> bool:
    from . import service_market as sm
    return sm._old(db, sid, ACCOUNT_DAYS, t)


def _run_view(row: dict, sid: str | None = None) -> dict:
    return dict(id=row['id'], track=row['track'], cls=row['cls'], vid=row['vid'], ms=int(row['ms']), week=row['week'],
                mine=bool(sid and row['sid'] == sid), at=float(row['at']))


def _veh_name(vid: str) -> str:
    V = _garage().VEHICLES.get(vid) or {}
    return f'{V.get("emoji", "🚗")} {V.get("name", vid)}'


def _start(s: dict, vid: str, track: str, choices: dict, fee: int, label: str, seed: str) -> dict:
    """Inside a save mutation: the vehicle's numbers now, the run, the fee out of the save, the wear. The run."""
    need(isinstance(s.get('journey'), dict) and s['journey'].get('story'), 'Đường đua chỉ có trong chế độ hành trình.', 'not_story')
    need(vid in owned(s), 'Chọn một chiếc xe máy hoặc ô tô của bạn nhé.', 'bad_vehicle')
    from . import rui
    need(not rui.is_broken(s, 'xe', vid), 'Xe đang hỏng. Sửa xe rồi hãy ra đường đua nhé.', 'broken', 409)
    from . import service_market as sm
    if fee:
        sm.debit(s, fee, label)
    car = car_of(s, vid)
    p = perf_of(vid, car)
    r = run(track, p, choices, seed)
    _store_car(s, vid, wear_after(car, r['slides']))
    get(s)['stats']['races'] += 1
    return dict(perf=p, run=r)


def trial(store, sid: str, d: dict, ip: str = '') -> dict:
    """⏱️ One time-trial run: the fee burned, the run stored with its inputs, the week's best kept."""
    need(not off(), OFF_TEXT, 'race_off', 503)
    track, vid = d.get('track'), d.get('vid')
    need(track in TRACKS, 'Chọn đường đua nhé.', 'bad_track')
    need(isinstance(vid, str) and VID_RE.fullmatch(vid) and base_of(vid), 'Chọn một chiếc xe máy hoặc ô tô của bạn nhé.', 'bad_vehicle')
    choices = check_choices(track, d.get('choices'))
    t = now()
    rid = 'rr' + secrets.token_hex(8)
    fee = TRIAL_FEE[track]
    out = {}

    def fn(s):
        out.update(_start(s, vid, track, choices, fee, f'🏁 Phí chạy {TRACKS[track]["name"]} · Bến Mây', rid))

    def ops(db):
        from . import service_market as sm
        db.execute('SELECT pg_advisory_xact_lock(17911, hashtext(?))', ('race:' + sid,))
        n = int(db.execute('SELECT COUNT(*) FROM race_runs WHERE sid=? AND day=?', (sid, vn_day(t))).fetchone()[0])
        need(n < TRIAL_DAY, f'Hôm nay bạn đã chạy {TRIAL_DAY} lượt tính giờ rồi. Mai chạy tiếp nhé.', 'trial_day', 409)
        sm.record_net(db, sid, ip, t)
        db.execute('INSERT INTO race_runs(id,sid,pid,week,day,track,cls,vid,ms,perf,choices,at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (rid, sid, pid_of(sid), vn_week(t), vn_day(t), track, class_of(vid), vid, out['run']['ms'], _dump(out['perf']), _dump(choices), t))
        best = db.execute('SELECT MIN(ms) FROM race_runs WHERE sid=? AND week=? AND track=? AND cls=?', (sid, vn_week(t), track, class_of(vid))).fetchone()[0]
        return int(best or out['run']['ms'])
    res = mr._mutate_retry(store, {sid: fn}, ops)
    best = res['db']
    r = out['run']
    pb = r['ms'] <= best
    return dict(ok=True, changed=True, id=rid, track=track, vid=vid, perf=out['perf'], run=r, best=best, pb=pb,
                message=f'⏱️ {TRACKS[track]["name"]}: {secs(r["ms"])}' + (' · kỷ lục tuần của bạn!' if pb else f' · kỷ lục tuần {secs(best)}.'))


def secs(ms: int) -> str:
    return f'{int(ms) // 1000},{int(ms) % 1000:03d} giây'


def challenge(store, sid: str, d: dict, ip: str = '') -> dict:
    """⚔️ Open a duel: the challenger runs now, the fee is escrowed; anyone of the same class and close numbers may race it."""
    need(not off(), OFF_TEXT, 'race_off', 503)
    track, vid, fee = d.get('track'), d.get('vid'), d.get('fee')
    need(track in TRACKS, 'Chọn đường đua nhé.', 'bad_track')
    need(fee in FEES and type(fee) is int, 'Chọn phí vào cửa nhé.', 'bad_fee')
    need(isinstance(vid, str) and VID_RE.fullmatch(vid) and base_of(vid), 'Chọn một chiếc xe máy hoặc ô tô của bạn nhé.', 'bad_vehicle')
    choices = check_choices(track, d.get('choices'))
    t = now()
    did = 'rd' + secrets.token_hex(8)
    with store.connect() as db:
        need(_old(db, sid, t), f'Đua tay đôi mở cho tài khoản từ {ACCOUNT_DAYS} ngày trở lên.', 'too_new', 403)
    out = {}

    def fn(s):
        out.update(_start(s, vid, track, choices, fee, f'⚔️ Phí đua tay đôi {TRACKS[track]["name"]} (giữ tới khi có người đua)', did + ':a'))

    def ops(db):
        from . import bank_xfer
        from . import service_market as sm
        db.execute('SELECT pg_advisory_xact_lock(17911, hashtext(?))', ('race:' + sid,))
        n = int(db.execute("SELECT COUNT(*) FROM race_duels WHERE a_sid=? AND status='open'", (sid,)).fetchone()[0])
        need(n < OPEN_MAX, f'Bạn đang mở {OPEN_MAX} lời thách đấu rồi. Chờ có người đua hoặc hủy bớt nhé.', 'open_max', 409)
        bank_xfer.count_out(db, sid, fee)
        sm.record_net(db, sid, ip, t)
        db.execute('INSERT INTO race_duels(id,track,cls,fee,a_sid,a_pid,a_run,a_ms,a_pi,status,day,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (did, track, class_of(vid), fee, sid, pid_of(sid), _dump(dict(vid=vid, perf=out['perf'], choices=choices)),
                    out['run']['ms'], out['perf']['pi'], 'open', vn_day(t), t))
    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(ok=True, changed=True, id=did, run=out['run'], perf=out['perf'],
                message=f'⚔️ Đã mở lời thách đấu {TRACKS[track]["name"]}: {secs(out["run"]["ms"])}. Phí {fmt(fee)} xu đang giữ, có người đua là có kết quả.')


def _duel(db, did) -> dict | None:
    need(isinstance(did, str) and re.fullmatch(r'rd[0-9a-f]{16}', did), 'Không tìm thấy lời thách đấu.', 'gone', 404)
    r = db.execute('SELECT * FROM race_duels WHERE id=?', (did,)).fetchone()
    return dict(r) if r else None


def accept(store, sid: str, d: dict, ip: str = '') -> dict:
    """⚔️ Race an open duel: same track, same class, numbers within PI_GAP. Settles at once: the pot to the faster."""
    need(not off(), OFF_TEXT, 'race_off', 503)
    vid = d.get('vid')
    need(isinstance(vid, str) and VID_RE.fullmatch(vid) and base_of(vid), 'Chọn một chiếc xe máy hoặc ô tô của bạn nhé.', 'bad_vehicle')
    t = now()
    with store.connect() as db:
        row = _duel(db, d.get('id'))
        need(row and row['status'] == 'open', 'Lời thách đấu này đã có người đua hoặc đã đóng.', 'gone', 409)
        need(row['a_sid'] != sid, 'Không tự đua với chính mình được.', 'self', 409)
        need(class_of(vid) == row['cls'], f'Lời thách đấu này dành cho {CLASSES[row["cls"]][1].lower()}.', 'class', 409)
        need(_old(db, sid, t), f'Đua tay đôi mở cho tài khoản từ {ACCOUNT_DAYS} ngày trở lên.', 'too_new', 403)
    choices = check_choices(row['track'], d.get('choices'))
    fee, a_sid, track = int(row['fee']), row['a_sid'], row['track']
    out = {}

    def fb(s):
        p = perf(s, vid)
        lo, hi = row['a_pi'] * (100 - PI_GAP) / 100, row['a_pi'] * (100 + PI_GAP) / 100
        need(lo <= p['pi'] <= hi, f'Xe của bạn chênh quá {PI_GAP}% chỉ số đua với xe đối thủ ({fmt(row["a_pi"])}). Chọn xe khác nhé.', 'pi_gap', 409)
        res = _start(s, vid, track, choices, fee, f'⚔️ Phí đua tay đôi {TRACKS[track]["name"]}', row['id'] + ':b')
        out.update(res)
        a_ms, b_ms = int(row['a_ms']), res['run']['ms']
        out['winner'] = 'tie' if a_ms == b_ms else 'a' if a_ms < b_ms else 'b'
        pot = fee * 2
        out['burn'] = 0 if out['winner'] == 'tie' else pot * BURN_PCT // 100
        out['prize'] = pot - out['burn']
        from . import service_market as sm
        if out['winner'] == 'b':
            sm.credit(s, out['prize'], f'🏆 Thắng đua tay đôi {TRACKS[track]["name"]}', OUT_KIND)
        elif out['winner'] == 'tie':
            sm.credit(s, fee, f'🤝 Hòa đua tay đôi {TRACKS[track]["name"]}: hoàn phí', OUT_KIND)

    def fa(s):
        from . import service_market as sm
        if out['winner'] == 'a':
            sm.credit(s, out['prize'], f'🏆 Thắng đua tay đôi {TRACKS[track]["name"]}', OUT_KIND)
        elif out['winner'] == 'tie':
            sm.credit(s, fee, f'🤝 Hòa đua tay đôi {TRACKS[track]["name"]}: hoàn phí', OUT_KIND)

    def ops(db):
        from . import bank_xfer
        from . import service_market as sm
        for k in sorted((sid, a_sid)):
            db.execute('SELECT pg_advisory_xact_lock(17911, hashtext(?))', ('race:' + k,))
        need(not sm._blocked(db, sid, a_sid), 'Không đua được với người này.', 'blocked', 403)
        need(not sm.same_net(db, sid, a_sid, ip, sid, t), 'Hai tài khoản cùng một mạng không đua tay đôi với nhau được.', 'same_net', 403)
        day = vn_day(t)
        pair = int(db.execute("SELECT COUNT(*) FROM race_duels WHERE status IN ('done','tie') AND day_done=? AND "
                              "((a_sid=? AND b_sid=?) OR (a_sid=? AND b_sid=?))", (day, sid, a_sid, a_sid, sid)).fetchone()[0])
        need(pair < PAIR_DAY, f'Hôm nay hai bạn đã đua tay đôi {PAIR_DAY} lần rồi. Mai đua tiếp nhé.', 'pair_day', 409)
        mine = int(db.execute("SELECT COUNT(*) FROM race_duels WHERE b_sid=? AND day_done=?", (sid, day)).fetchone()[0])
        need(mine < DUEL_DAY, f'Hôm nay bạn đã nhận {DUEL_DAY} lời thách đấu rồi. Mai đua tiếp nhé.', 'duel_day', 409)
        bank_xfer.count_out(db, sid, fee)
        sm.record_net(db, sid, ip, t)
        status = 'tie' if out['winner'] == 'tie' else 'done'
        winner = '' if status == 'tie' else a_sid if out['winner'] == 'a' else sid
        n = db.execute("UPDATE race_duels SET status=?,b_sid=?,b_pid=?,b_run=?,b_ms=?,b_pi=?,winner=?,burn=?,prize=?,day_done=?,done_at=? "
                       "WHERE id=? AND status='open'",
                       (status, sid, pid_of(sid), _dump(dict(vid=vid, perf=out['perf'], choices=choices)), out['run']['ms'], out['perf']['pi'],
                        winner, out['burn'], out['prize'] if status == 'done' else 0, day, t, row['id'])).rowcount
        need(n == 1, 'Lời thách đấu này vừa có người đua trước bạn.', 'gone', 409)
    mr._mutate_retry(store, {sid: fb, a_sid: fa}, ops)
    with store.connect() as db:
        done = _duel(db, row['id'])
    v = duel_view(done, sid)
    w = out['winner']
    msg = (f'🤝 Hòa {secs(out["run"]["ms"])}! Hoàn phí {fmt(fee)} xu cho cả hai.' if w == 'tie' else
           f'🏆 Bạn thắng {secs(out["run"]["ms"])} so với {secs(row["a_ms"])}: nhận {fmt(out["prize"])} xu.' if w == 'b' else
           f'😤 Thua {secs(out["run"]["ms"])} so với {secs(row["a_ms"])}. Mất phí {fmt(fee)} xu, độ thêm rồi phục thù nhé.')
    return dict(ok=True, changed=True, duel=v, message=msg)


def _refund_open(store, row: dict, status: str, t: float) -> bool:
    """An open duel back to its challenger in full (cancel / expiry). False when it was no longer open."""
    fee, a_sid = int(row['fee']), row['a_sid']
    label = '⚔️ Hoàn phí lời thách đấu ' + ('đã hủy' if status == 'cancelled' else 'hết hạn')

    def fa(s):
        from . import service_market as sm
        sm.credit(s, fee, label, OUT_KIND)

    def ops(db):
        n = db.execute('UPDATE race_duels SET status=?,done_at=? WHERE id=? AND status=?', (status, t, row['id'], 'open')).rowcount
        if n != 1:
            raise _Gone()
    try:
        mr._mutate_retry(store, {a_sid: fa}, ops)
    except _Gone:
        return False
    return True


class _Gone(mr.MarriageError):
    def __init__(self):
        super().__init__('gone', 'gone', 409)


def cancel(store, sid: str, d: dict) -> dict:
    with store.connect() as db:
        row = _duel(db, d.get('id'))
    need(row and row['a_sid'] == sid, 'Không tìm thấy lời thách đấu của bạn.', 'gone', 404)
    need(row['status'] == 'open', 'Lời thách đấu này đã có người đua hoặc đã đóng.', 'gone', 409)
    need(_refund_open(store, row, 'cancelled', now()), 'Lời thách đấu này vừa có người đua.', 'gone', 409)
    return dict(ok=True, changed=True, message=f'Đã hủy lời thách đấu, hoàn {fmt(row["fee"])} xu.')


def expire(store, sid: str | None = None, limit: int = 50, t: float | None = None) -> int:
    """Open duels past OPEN_HOURS back to their challengers (all, or one player's). How many."""
    t = now() if t is None else t
    with store.connect() as db:
        q = "SELECT * FROM race_duels WHERE status='open' AND created<?" + (' AND a_sid=?' if sid else '') + ' ORDER BY created LIMIT ?'
        rows = [dict(r) for r in db.execute(q, (t - OPEN_HOURS * 3600, *((sid,) if sid else ()), limit)).fetchall()]
    n = 0
    for row in rows:
        try:
            n += _refund_open(store, row, 'expired', t)
        except Exception:  # noqa: BLE001 - one save that refuses never blocks the others (retried next pass)
            pass
    return n


def run_housekeeping(store) -> None:
    try:
        expire(store)
    except Exception:  # noqa: BLE001
        pass


def duel_view(row: dict, sid: str | None = None) -> dict:
    a, b = _j(row.get('a_run'), {}), _j(row.get('b_run'), {})
    side = 'a' if sid == row['a_sid'] else 'b' if sid and sid == row.get('b_sid') else ''
    return dict(id=row['id'], track=row['track'], cls=row['cls'], fee=int(row['fee']), status=row['status'],
                a=dict(pid=row['a_pid'], vid=a.get('vid'), pi=int(row['a_pi']), ms=int(row['a_ms']) if row['status'] != 'open' or side == 'a' else None),
                b=dict(pid=row.get('b_pid') or '', vid=b.get('vid'), pi=int(row.get('b_pi') or 0), ms=int(row.get('b_ms') or 0)) if row.get('b_sid') else None,
                me=side, won=(row.get('winner') == sid) if sid and row['status'] == 'done' else None, prize=int(row.get('prize') or 0),
                created=float(row['created']), done_at=float(row.get('done_at') or 0))


def replay(store, sid: str, d: dict) -> dict:
    """The legs of a run, recomputed from its stored inputs (a trial `rr…` or a duel `rd…`)."""
    rid = d.get('id')
    with store.connect() as db:
        if isinstance(rid, str) and re.fullmatch(r'rr[0-9a-f]{16}', rid):
            row = db.execute('SELECT * FROM race_runs WHERE id=?', (rid,)).fetchone()
            need(row, 'Không tìm thấy lượt chạy.', 'gone', 404)
            row = dict(row)
            r = run(row['track'], _j(row['perf'], {}), _j(row['choices'], {}), rid)
            return dict(ok=True, kind='trial', track=row['track'], runs=[dict(vid=row['vid'], vehicle=_veh_name(row['vid']), perf=_j(row['perf'], {}), run=r,
                                                                           mine=row['sid'] == sid)])
        row = _duel(db, rid)
    need(row and row['status'] in ('done', 'tie'), 'Trận này chưa có kết quả.', 'gone', 404)
    runs = []
    for side in ('a', 'b'):
        x = _j(row[f'{side}_run'], {})
        runs.append(dict(vid=x.get('vid'), vehicle=_veh_name(x.get('vid') or ''), perf=x.get('perf'),
                         run=run(row['track'], x.get('perf'), x.get('choices'), f'{row["id"]}:{side}'), mine=row[f'{side}_sid'] == sid, pid=row[f'{side}_pid']))
    return dict(ok=True, kind='duel', track=row['track'], runs=runs, duel=duel_view(row, sid))


def _names(db, sids) -> dict:
    """{sid: the name the boards show} (game/leaderboard.py privacy: hidden → 'Một người chơi'; the sid never leaves the
    server)."""
    from .leaderboard import _VISIBLE
    sids = sorted(set(x for x in sids if x))
    out = {}
    for i in range(0, len(sids), 100):
        part = sids[i:i + 100]
        rows = db.execute(f'SELECT a.sid AS sid, a.display AS display, ({_VISIBLE}) AS vis FROM accounts a LEFT JOIN leaderboard_players p '
                          'ON p.sid=a.sid WHERE a.sid IN (' + ','.join('?' * len(part)) + ')', tuple(part)).fetchall()
        for r in rows:
            out[r['sid']] = mr._clean_name(r['display']) if r['vis'] and r['display'] else 'Một người chơi'
    return out


def board(db, track: str, cls: str, week: str, n: int = BOARD_TOP, visible: bool = False) -> list:
    """[(sid, pid, best ms, vid)] of a week's board, each player's best run, fastest first (ties: the earlier run).
    visible: only the players the boards show by name (game/leaderboard.py privacy: who may hold a title)."""
    from .leaderboard import _VISIBLE
    where = (f' AND {_VISIBLE}' if visible else '')
    rows = db.execute('SELECT sid,pid,ms,vid,at FROM (SELECT DISTINCT ON (r.sid) r.sid,r.pid,r.ms,r.vid,r.at FROM race_runs r '
                      'LEFT JOIN accounts a ON a.sid=r.sid LEFT JOIN leaderboard_players p ON p.sid=r.sid '
                      f'WHERE r.week=? AND r.track=? AND r.cls=?{where} ORDER BY r.sid,r.ms,r.at) b ORDER BY ms,at,sid LIMIT ?',
                      (week, track, cls, n)).fetchall()
    return [(r['sid'], r['pid'], int(r['ms']), r['vid']) for r in rows]


BOARDS = {f'race_{t}_{c}': (t, c) for t in TRACKS for c in CLASSES}


def standings(db, board_id: str, t: float, n: int) -> list:
    """[(board, rank, sid, score)] of a race board (game/lb_titles.py): the week of `t`, the score the time in ms."""
    track, cls = BOARDS[board_id]
    return [(board_id, i + 1, sid, ms) for i, (sid, _pid, ms, _vid) in enumerate(board(db, track, cls, vn_week(t), n, visible=True))]


def home(store, token, sid: str, account: bool = True) -> dict:
    """Everything the track page needs: your vehicles, today's counts, your open and recent duels, the open duels of
    others, the week's boards."""
    expire(store, sid, 10)
    s = _state(store, sid)
    t = now()
    week, day = vn_week(t), vn_day(t)
    with store.connect() as db:
        mine_open = [dict(r) for r in db.execute("SELECT * FROM race_duels WHERE a_sid=? AND status='open' ORDER BY created DESC", (sid,)).fetchall()]
        recent = [dict(r) for r in db.execute("SELECT * FROM race_duels WHERE (a_sid=? OR b_sid=?) AND status IN ('done','tie') ORDER BY done_at DESC LIMIT 10",
                                             (sid, sid)).fetchall()]
        others = [dict(r) for r in db.execute("SELECT * FROM race_duels WHERE status='open' AND a_sid<>? AND created>=? ORDER BY created DESC LIMIT 30",
                                             (sid, t - OPEN_HOURS * 3600)).fetchall()]
        trials = int(db.execute('SELECT COUNT(*) FROM race_runs WHERE sid=? AND day=?', (sid, day)).fetchone()[0])
        duels = int(db.execute('SELECT COUNT(*) FROM race_duels WHERE b_sid=? AND day_done=?', (sid, day)).fetchone()[0])
        boards = {}
        sids = [sid]
        for bid, (track, cls) in BOARDS.items():
            rows = board(db, track, cls, week)
            boards[bid] = rows
            sids += [r[0] for r in rows]
        mine_best = {bid: next((dict(rank=i + 1, ms=r[2]) for i, r in enumerate(rows) if r[0] == sid), None) for bid, rows in boards.items()}
        sids += [r['a_sid'] for r in others + recent] + [r.get('b_sid') for r in recent]
        names = _names(db, sids)
        old = _old(db, sid, t)
    from . import lb_titles
    lb_titles.ensure(store)
    out_boards, weekly = {}, {}
    for bid, rows in boards.items():
        out_boards[bid] = [dict(rank=i + 1, name=names.get(x, 'Một người chơi'), ms=ms, vehicle=_veh_name(vid), me=x == sid)
                           for i, (x, _pid, ms, vid) in enumerate(rows)]
        try:
            weekly[bid] = lb_titles.board_view(store, bid, sid)   # 🏅 who holds the titles (updated once a day)
        except Exception:  # noqa: BLE001 - the page shows without its titles block
            weekly[bid] = None
    dv = lambda r: dict(duel_view(r, sid), a_name=names.get(r['a_sid'], 'Một người chơi'), b_name=names.get(r.get('b_sid') or '', ''),
                        a_vehicle=_veh_name(_j(r['a_run'], {}).get('vid', '')))
    return dict(ok=True, off=off(), garage=view(s), rules=content(), week=week, today=dict(trials=trials, duels=duels),
                account=account, old_enough=old and account, open=[dv(r) for r in mine_open], recent=[dv(r) for r in recent], others=[dv(r) for r in others],
                boards=out_boards, best=mine_best, weekly=weekly)


OPS = ('home', 'trial', 'challenge', 'accept', 'cancel', 'replay')


def post(store, token, op: str, d: dict, ip: str = '') -> dict:
    need(op in OPS, 'Thao tác không hợp lệ.', 'unknown', 404)
    need(isinstance(d, dict), 'Thông tin không hợp lệ.', 'bad')
    sid, display = _who(store, token, guest_ok=op == 'home')
    if op == 'home':
        return home(store, token, sid, bool(display))
    if op == 'trial':
        return trial(store, sid, d, ip)
    if op == 'challenge':
        return challenge(store, sid, d, ip)
    if op == 'accept':
        return accept(store, sid, d, ip)
    if op == 'cancel':
        return cancel(store, sid, d)
    return replay(store, sid, d)
