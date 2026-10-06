"""Người gác hải đăng: keeper of đèn biển Hòn Gió for Xí nghiệp Bảo đảm hàng hải Vịnh Ngọc (plugin career).

A salaried job (employment); a job done by the book adds a small bonus. A day on the island:

* ``dawn`` (slot 0): turn the light off on time (the almanac and the station's rule), test six pieces of equipment one by
  one, clean the lens with the rotation locked off, read the fuel tank into the fuel log, fix what the keeper can and
  report a fault through the right channel (the logbook, a repair slip to the company, or the coastal station when it
  touches the light's signal), then sign the logbook;
* ``weather`` (slot 1): read the anemometer, the sea, the far marks and the barometer, report the four values to Đài
  Duyên hải Vịnh Ngọc, and decide whether boats must be warned (from cấp 6 or a fast-falling barometer);
* ``sea``: something on the water: a red flare in a storm, a boat adrift, someone in the water at the jetty, kids
  swimming out for a dare, a boat heading for the reef, a boat leaving harbour into a storm, blast fishing. The keeper
  looks, calls, throws a buoy, relays to the station with the right priority and the right position, and keeps the
  target in sight; never goes out alone in the station's dinghy, never swims out. The captains on the radio decide by
  their own hidden traits;
* ``visitor``: someone lands on the island and wants something: a tour with papers, a school group, a selfie crowd,
  a couple who want to propose on the gallery at midnight, an influencer, a ghost channel that wants the light off,
  a writer who wants to stay a week, wet kayakers at dusk… The keeper checks the papers and answers in their own way
  (escort, the yard only, refuse, shelter, report); each visitor takes it by their hidden traits; anyone in danger is
  always sheltered, and nobody goes up to the lamp room against the rules;
* ``supply`` (on supply-boat days): dip the tank before and after, check the goods, note what is short or spoiled,
  sign the delivery note with the litres measured (the captain wants the full 200 signed), and haggle the captain's
  private basket of fresh things with your own coins;
* ``dusk`` (the day's last planned job): light up on time, time the flashes against the list of lights, start the fog
  horn in fog, radio the station when the light or the horn is wrong, and write the evening log truthfully.

Around the work: surprises (kit desk), situations (sit_), the chuyện oái oăm of the people around the light
(game/careers/air_odd.py with this career's scripts), and life on the rock: loneliness, the fresh food that runs out
between boats, Mun the cat, the vegetable boxes, the calls home. Safety is always the right choice. Mistakes go
through consequences.slip; money only through the engine's money(). Everything random is rolled from (day, slot) or
the task id: the same moves always end the same way.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from .. import archive as ar
from . import lighthouse_content as LC
from .lighthouse_content import (PEOPLE, MODS, EQUIP, EQUIP_IDS, FORMS, FAULTS, HANDOVER, BEAUFORT, SEA_STATES, VIS, BARO, INSTRUMENTS,
                                 WARN_WIND, REMARKS, CHAR_OPTIONS, SEA, SEA_ACTS, RELAY, WORDS, BOATS, TALK, WORD_SCORE, ANSWERS,
                                 VISITORS, VISITOR, GOODS, GOODS_IDS, GOODS_STATE, BASKET, INTRO, REG_STORY, BAY, YEN, SAU, LUC, THAM)
from .lighthouse_odd import DESK, ODD, SITUATIONS

ID = 'lighthouse'
GEN = 1
HOURS = (5 * 60, 22 * 60)      # up before sunrise to put the light out; the evening log is written by ten
KINDS = ('dawn', 'weather', 'sea', 'visitor', 'supply', 'dusk')
BONUS = dict(dawn=8, weather=8, sea=14, visitor=8, supply=6, dusk=10)
LOG_MAX = 12
MAX_ROUNDS = 2
MOD = {m['id']: m for m in MODS}

# The words of the encounters (air_odd): who to bring in, the office, the rank lost on a demotion.
CFG = dict(crew='Báo chú Bảy', company='Báo xí nghiệp', union='Nhờ công đoàn xí nghiệp', office='Phòng tổ chức xí nghiệp', demoted='người gác đèn tập sự',
           title='người gác đèn chính', harass_note='🛡️ Báo là đúng: xí nghiệp có quy trình bảo vệ người đang trực đèn.',
           ground_line='⚖️ Xí nghiệp: tạm đình chỉ trực hết hôm nay, chú Bảy trực thay. Mai lên trình bày qua bộ đàm.',
           demote_line='⚖️ Hội đồng kỷ luật xí nghiệp: hạ xuống {demoted}, tạm đình chỉ trực hôm nay, thưởng ca về 0 tới khi hồ sơ sạch lại.',
           rest_ok=' Chú Bảy trực thay ca của bạn; bạn ngủ một giấc dài nghe sóng vỗ.', levels={'ground': 'Tạm đình chỉ trực'},
           tired_line=LC.DAY_LINES['tired'])


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _clock(m: int) -> str:
    m %= 24 * 60
    return f'{m // 60:02d}:{m % 60:02d}'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def almanac(day: int) -> dict:
    """Sunrise and sunset on the island (minutes), a little different every day."""
    return dict(rise=5 * 60 + 25 + (day * 7) % 20, set=17 * 60 + 30 + (day * 11) % 25)


def _times(r, base: int, right: int, late: int, early: int) -> tuple:
    """Three times to pick from: the right one, one too late, one too early (shuffled; the index of the right one)."""
    opts = [_clock(base + right), _clock(base + late), _clock(base + early)]
    order = [0, 1, 2]
    r.shuffle(order)
    return [opts[i] for i in order], order.index(0), order.index(1), order.index(2)


def supply_day(day: int) -> bool:
    return day >= LC.SUPPLY_FIRST and (day - LC.SUPPLY_FIRST) % LC.SUPPLY_EVERY == 0


def next_supply(day: int) -> int:
    """Days until the supply boat (0 = today)."""
    if day < LC.SUPPLY_FIRST:
        return LC.SUPPLY_FIRST - day
    return (LC.SUPPLY_EVERY - (day - LC.SUPPLY_FIRST) % LC.SUPPLY_EVERY) % LC.SUPPLY_EVERY


def sky(day: int) -> dict:
    """The day's real weather (pure): what the instruments will show and whether boats must be warned."""
    mod = mod_of(day)['id']
    r = kit.rng(ID, 'sky', day)
    wind = 3 if day == 1 else {'calm': r.choice((2, 3, 3)), 'tourist': r.choice((2, 3)), 'breeze': r.choice((5, 5, 6)),
                               'fog': r.choice((1, 2)), 'storm': r.choice((7, 7, 8))}[mod]
    lo, hi = BEAUFORT[wind][1], BEAUFORT[wind][2]
    ms = round(lo + (hi - lo) * (0.25 + 0.5 * r.random()), 1)
    sea = 'lang' if wind <= 2 else 'nho' if wind <= 4 else 'vua' if wind <= 6 else 'lon'
    vis = {'fog': 'mu', 'storm': 'kem', 'breeze': 'kha'}.get(mod, 'xa')
    baro = {'storm': 'fast', 'breeze': 'down'}.get(mod) or ('steady' if day == 1 else r.choice(('steady', 'up', 'steady')))
    now = 1012 - {'fast': 6, 'down': 3}.get(baro, 0) + r.randint(-2, 2)
    drop = {'fast': r.randint(3, 5), 'down': r.randint(1, 2), 'steady': 0, 'up': -r.randint(1, 2)}[baro]
    return dict(wind=wind, ms=ms, sea=sea, vis=vis, baro=baro, hpa=now, hpa3=now + drop, warn=wind >= WARN_WIND or baro == 'fast')


def _pick(day: int, slot: int, mod: str, avoid: str | None = None) -> str:
    r = kit.rng(ID, 'pick', day, slot)
    p_sea = {'storm': 0.75, 'tourist': 0.3, 'fog': 0.6}.get(mod, 0.5)
    k = 'sea' if r.random() < p_sea else 'visitor'
    if avoid == k and r.random() < 0.6:
        k = 'visitor' if k == 'sea' else 'sea'
    return k


def plan_of(day: int) -> list:
    """The day's planned jobs in slot order: the morning round, the weather, one or two jobs, the evening light."""
    if day == 1:
        return ['dawn', 'weather', 'visitor', 'dusk']
    if day == 2:
        return ['dawn', 'weather', 'sea', 'dusk']
    mod = mod_of(day)['id']
    a = 'supply' if supply_day(day) else _pick(day, 2, mod)
    b = _pick(day, 3, mod, avoid=a)
    return ['dawn', 'weather', a, b, 'dusk']


def daily_task_count(day: int) -> int:
    return len(plan_of(day))


def kind_at(day: int, slot: int) -> str:
    plan = plan_of(day)
    if slot < len(plan):
        return plan[slot]
    return 'sea' if (day + slot) % 2 else 'visitor'     # more work after dark: the night watch


def dawn_fault(day: int) -> str | None:
    """The fault the morning round finds today (pure: the evening light knows it too)."""
    if day == 1:
        return None
    r = kit.rng(ID, 'fault', day)
    return list(FAULTS)[r.randrange(len(FAULTS))] if r.random() < 0.7 else None


def _weighted(r, rows: list) -> dict:
    total = sum(x.get('weight', 1) for x in rows)
    pick = r.random() * total
    for x in rows:
        pick -= x.get('weight', 1)
        if pick < 0:
            return x
    return rows[-1]


# ================================================================ tasks
def _dawn(day, slot, serial):
    r = kit.rng(ID, 'dawn', day)
    al = almanac(day)
    times, right, late, early = _times(r, al['rise'], LC.OFFSET, 120, -30)
    needs = dict(dawn=True, handover=HANDOVER[r.randrange(len(HANDOVER))], rise=_clock(al['rise']), times=times, rule=LC.LIGHT_RULE,
                 note='Tắt đèn đúng giờ, thử lần lượt từng thứ, lau kính, ghi sổ dầu; hỏng thì xử lý và báo đúng nơi rồi mới ký sổ trực.')
    return kit.base_task(ID, day, slot, serial, BAY, 'Ca sáng: tắt đèn, kiểm máy',
                         'Chú Bảy đưa cuốn sổ trực: “Tắt đèn đúng giờ, thử từng thứ một, lau kính cho sạch. Chưa thử thì đừng ký, con.”',
                         kind='dawn', needs=needs, _fault=dawn_fault(day), _fuel=300 + r.randint(0, 40) * 5, _off=[right, late, early], gen=GEN,
                         off=None, checked=[], found=None, fixed=False, forms=[], cleaned=None, fuel_log=None, story=None)


def _dusk(day, slot, serial):
    r = kit.rng(ID, 'dusk', day)
    al = almanac(day)
    times, right, late, early = _times(r, al['set'], -LC.OFFSET, 30, -120)
    fault = dawn_fault(day)
    mod = mod_of(day)['id']
    needs = dict(dusk=True, set=_clock(al['set']), times=times, rule=LC.LIGHT_RULE, chart=LC.CHARACTER, code=LC.CHAR_CODE, fog=mod == 'fog',
                 note='Thắp đèn đúng giờ, bấm giờ đếm chớp so với danh mục đèn; sai thì báo đài. Sương mù thì chạy còi. Ghi sổ đúng sự thật.')
    return kit.base_task(ID, day, slot, serial, BAY, 'Chạng vạng: thắp đèn',
                         'Mặt trời đỏ ối sát mặt biển. Chú Bảy gõ vào cửa phòng đèn: “Tới giờ rồi đó. Thắp xong nhớ đếm chớp.”',
                         kind='dusk', needs=needs, _light=[right, late, early], _slow=fault == 'motor', _horn_bad=fault == 'horn', gen=GEN,
                         lit=None, counted=False, horn=False, radioed=[], awake=False, remarks=None, story=None)


def _weather(day, slot, serial):
    needs = dict(weather=True, hour='07:00', note='Đọc đủ bốn thứ rồi mới báo đài. Gió từ cấp 6 hoặc áp kế giảm nhanh thì phát cảnh báo cho tàu thuyền.')
    return kit.base_task(ID, day, slot, serial, YEN, 'Quan trắc 07:00, báo đài',
                         '📻 Chị Hải Yến: “Trạm Hòn Gió, tới giờ quan trắc bảy giờ. Đài chờ số liệu của trạm.”',
                         kind='weather', needs=needs, _sky=sky(day), gen=GEN, read=[], report=None, warned=False, story=None)


def _sea_case(day: int, slot: int, mod: str) -> dict:
    if day == 2 and slot == 2:
        return SEA[LC.SEA_GENTLE]
    r = kit.rng(ID, 'sea-case', day, slot)
    pool = [x for x in SEA.values() if x['min_day'] <= day and (not x['mods'] or mod in x['mods'])]
    return _weighted(r, pool or [SEA[LC.SEA_GENTLE]])


def _sea(day, slot, serial):
    mod = mod_of(day)['id']
    x = _sea_case(day, slot, mod)
    r = kit.rng(ID, 'sea', day, slot)
    bearing = r.randrange(20, 340, 5)
    dist = {'mob': 0.1, 'kids': r.choice((0.5, 0.6, 0.8))}.get(x['id']) or r.choice((1.5, 2.0, 2.5, 3.0, 4.0))
    persons = {'mob': 1, 'kids': r.randint(3, 5)}.get(x['id']) or r.randint(2, 6)
    opts = [bearing, (bearing + 45) % 360, (bearing + 180) % 360]
    r.shuffle(opts)
    popts = sorted({persons, persons + 2, max(1, persons - 1) if persons > 1 else persons + 1})
    needs = dict(sea=True, case=x['id'], emoji=x['emoji'], bearings=[f'{b:03d}' for b in opts], persons=popts if x['persons'] else None,
                 talk=x['talk'], note='Nhìn kỹ trước. Báo đài đúng mức khẩn cấp, đúng phương vị. Không ai tự ra khơi, không ai nhảy xuống bơi.')
    answers = r.random() < 0.55
    title = f'{x["title"]}'
    return kit.base_task(ID, day, slot, serial, x['npc'], title, f'{x["emoji"]} {x["opening"]}', kind='sea', needs=needs, _case=x['id'],
                         _bearing=f'{bearing:03d}', _dist=dist, _persons=persons, _boat=BOATS[r.randrange(len(BOATS))], _answers=answers, gen=GEN,
                         looked=False, did=[], talk=[], talk_out=None, relay=None, story=None)


def _visitor(day, slot, serial):
    mod = mod_of(day)['id']
    if day == 1:
        v = VISITOR[LC.VISITOR_GENTLE]
    else:
        r = kit.rng(ID, 'visitor', day, slot)
        pool = [x for x in VISITORS if x['min_day'] <= day and (not x['mods'] or mod in x['mods'])]
        v = _weighted(r, pool or [VISITOR[LC.VISITOR_GENTLE]])
    needs = dict(visitor=True, vid=v['id'], emoji=v['emoji'], who=v['who'], wants=v['wants'], night=v['night'], soft=v['soft'],
                 note='Xem giấy tờ trước. Nội quy trạm: ban ngày, có giấy của xí nghiệp, có người đi kèm, không vào phòng đèn, không ở lại qua đêm. Người gặp nạn thì luôn cho trú.')
    npc = v['npc'] if v['npc'] is not None else BAY
    title = f'Khách ra đảo: {v["who"].split(" · ")[0]}'
    return kit.base_task(ID, day, slot, serial, npc, title, f'{v["emoji"]} {v["line"]}', kind='visitor', needs=needs, _v=v['id'], gen=GEN,
                         papers=False, answers=[], round=0, out=None, sneak=False, stopped=False, story=None)


def _supply(day, slot, serial):
    r = kit.rng(ID, 'supply', day)
    before = 380 + r.randint(0, 30) * 2
    delivered = LC.FUEL_CLAIM - r.choice((0, 0, 20, 30, 40))
    states = {g: 'ok' for g in GOODS_IDS}
    for g in r.sample(['veg', 'fish', 'rice', 'water', 'parts'], r.choice((1, 1, 2))):
        states[g] = 'spoiled' if g in ('veg', 'fish') and r.random() < 0.6 else 'short'
    ask = BASKET['fair'] * r.choice((16, 18, 20)) // 10
    needs = dict(supply=True, claim=LC.FUEL_CLAIM, goods=[dict(g) for g in GOODS], basket=dict(name=BASKET['name'], items=BASKET['items'], ask=ask),
                 note='Đo bồn trước và sau khi bơm, kiểm từng món, ghi rõ món thiếu, món hỏng. Ký đúng số lít đo được.')
    return kit.base_task(ID, day, slot, serial, LUC, 'Tàu tiếp tế cập đảo',
                         f'⛴️ Còi tàu Hòn Gió 02 vang ở bến. {LC.SUPPLY_LINES["claim"]}', kind='supply', needs=needs, _before=before,
                         _after=before + delivered, _states=states, gen=GEN, dipped=[], seen=[], noted=[], signed=None, offers=[], counter=None,
                         buy=None, story=None)


MAKERS = dict(dawn=_dawn, dusk=_dusk, weather=_weather, sea=_sea, visitor=_visitor, supply=_supply)


def make_task(day: int, slot: int, serial: int) -> dict:
    return MAKERS[kind_at(day, slot)](day, slot, serial)


FIXED = ('needs', '_fault', '_fuel', '_off', '_light', '_slow', '_horn_bad', '_sky', '_case', '_bearing', '_dist', '_persons', '_boat',
         '_answers', '_v', '_before', '_after', '_states')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] in ('dawn', 'dusk', 'weather'):
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, lit=0, safe=0, warned=0, relays=0, visitors=0, sheltered=0, refused=0, earned=0)


def initial() -> dict:
    return dict(v=1, intro=False, on_duty=False, lonely=2, fresh=LC.FRESH_DAYS, pet_day=0, garden_day=0, call_day=0, garden=0,
                log=[], regulars={}, today=_fresh_today(0),
                stats=dict(lit=0, safe=0, faults=0, reports=0, warned=0, relays=0, rescues=0, visitors=0, sheltered=0, refused=0, supplies=0, honest=0),
                desk=kit.desk_initial(), odd=ao.initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


def _pressure(c: dict, d: dict) -> int:
    """How hard the company leans on its keepers today: the storm season, and a keeper who snapped at the office."""
    marks = d['odd']['marks']
    return {'storm': 2, 'breeze': 1, 'tourist': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('hd_intro', 'hd_rest', 'hd_pet', 'hd_garden', 'hd_call')
NO_TICK = ('hd_intro', 'hd_rest', 'hd_pet', 'hd_garden', 'hd_call', 'hd_desk', 'hd_odd', 'hd_off', 'hd_form', 'hd_fuel', 'hd_read', 'hd_report',
           'hd_count', 'hd_radio', 'hd_log', 'hd_papers', 'hd_note', 'hd_goods', 'hd_wake')
PHYSICAL = ('hd_check', 'hd_act', 'hd_dip', 'hd_stop')
GROUNDED = ('hd_look', 'hd_papers', 'hd_dip')     # a keeper stood down takes no new job; the light itself is always kept
SAFE = ('hd_act', 'hd_relay', 'hd_vhf', 'hd_stop', 'hd_horn', 'hd_light', 'hd_look')   # never held up by someone talking


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'hd_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chú Bảy đang chờ ở chân tháp.')
    odd = d['odd']
    if name == 'hd_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    if name in LIFE:
        return LIFE[name](s, c, d, p)
    desk = d['desk']
    if name == 'hd_desk':
        result = kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'hd_odd':
        result = ao.reply(s, c, ID, odd, ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở trạm đèn.')
    if name not in SAFE:
        kit.desk_block(desk, 'Có chuyện trên đảo, quyết xong rồi làm tiếp nhé.')
        ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm đình chỉ trực hết hôm nay. Chú Bảy trực thay, mai lên trình bày.', 'grounded')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _busy(c: dict) -> bool:
    """Nobody turns up while someone is in the water or a stranger is on the tower stairs."""
    for t in c['tasks']:
        if t.get('career') != ID or t['status'] in ('completed', 'cancelled', 'referred'):
            continue
        if t.get('kind') == 'sea' and t.get('looked'):
            return True
        if t.get('kind') == 'visitor' and t.get('sneak') and not t.get('stopped'):
            return True
    return False


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    if _busy(c):
        return
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    x = ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kind: str | None = None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc trạm đèn.')
    if kind:
        kit.need(t['kind'] == kind, 'Thao tác này không dành cho việc đang làm.')
    return t


def _slip(t: dict, code: str, sev: int, text: str, note: str, safety: bool = False) -> None:
    if not any(x['code'] == code for x in cq.slips(t)):
        t['mistakes'] += 1
    cq.slip(t, code, sev, text, note, safety=safety)


def _need_duty(d: dict) -> None:
    kit.need(d['on_duty'], 'Làm ca sáng, ký sổ trực trước đã nhé.')


def _finish(s: dict, c: dict, d: dict, t: dict, narrative: str, extra: int = 0) -> tuple:
    """Pay the bonus (none when a safety rule was broken, less for each slip), write the regular's line, close the task."""
    safe = not cq.safety(t)
    full = 0 if not safe else max(0, BONUS[t['kind']] + extra - 3 * cq.points(t))
    reward = ao.bonus(d['odd'], full)
    d['today']['earned'] += reward
    i = _npc_index(t)
    story = ''
    if i in REG_STORY:
        rg = d['regulars'].setdefault(str(i), dict(visits=0))
        rg['visits'] = min(999, rg['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(rg['visits'], len(lines)) - 1]
        t['story'] = story
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    head = f'Thưởng ca {reward} xu.' if reward else ''
    if full and reward < full:
        head += ' (Đang bị hạ bậc: không có thưởng.)' if not reward else ' (Mệt quá: nửa thưởng.)'
    if not safe:
        head += ' 🛡️ Xí nghiệp sẽ đọc lại việc này cùng bạn.'
    tail = f'💬 {story}' if story else ''
    return reward, ' '.join(x for x in (head.strip(), note, tail) if x)


# ---------------------------------------------------------------- dawn: the morning round
def _off(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.need(t['off'] is None, 'Đã tắt đèn rồi.')
    pick = kit.integer(p.get('option'), 0, 2)
    kit.start_work(t)
    t['off'] = pick
    right, late, early = t['_off']
    at = t['needs']['times'][pick]
    if pick == early:
        _slip(t, 'off_early', 2, f'Tắt đèn lúc {at}, trời còn tối, tàu ngoài khơi mất mốc.', 'tắt đèn sớm khi trời chưa sáng', safety=True)
        return dict(message=f'💡 Bạn tắt đèn lúc {at}. Ngoài khơi vẫn còn tối mịt, mấy đốm đèn tàu cá còn lấp lóa.', correct=False)
    if pick == late:
        _slip(t, 'off_late', 1, f'Đèn sáng tới {at} giữa ban ngày, hao ắc quy.', 'tắt đèn muộn')
        return dict(message=f'💡 Bạn tắt đèn lúc {at}. Nắng đã lên cao, ắc quy tụt một khúc.', correct=False)
    return dict(message=f'💡 Tắt đèn lúc {at}, mặt trời đã lên khỏi mặt biển. Ghi giờ vào sổ trực.')


def _check(s, c, d, p):
    t = _task(c, p, 'dawn')
    item = kit.one_of(p.get('item'), EQUIP_IDS, 'Thiết bị không có trên trạm.')
    kit.need(item not in t['checked'], 'Đã kiểm tra thứ này rồi.')
    kit.start_work(t)
    t['checked'].append(item)
    x = next(e for e in EQUIP if e['id'] == item)
    f = t['_fault']
    extra = f' Thước đo bồn dầu: {t["_fuel"]} lít.' if item == 'gen' else ''
    if f and FAULTS[f]['item'] == item:
        t['found'] = f
        return dict(message=f'{x["emoji"]} {x["test"]}: ⚠️ {FAULTS[f]["text"]}{extra}', correct=True)
    return dict(message=f'{x["emoji"]} {x["test"]}: {x["ok"]}{extra}')


def _clean(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.need('lens' in t['checked'], 'Soi kính đèn trước đã.')
    kit.need(t['cleaned'] is None, 'Đã lau kính rồi.')
    how = kit.one_of(p.get('how'), ('lock', 'quick'), 'Chọn cách lau.')
    t['cleaned'] = how
    if how == 'quick':
        _slip(t, 'no_lockout', 2, 'Lau kính khi bệ đèn còn đang quay, suýt bị kẹp tay.', 'không tắt mô-tơ khi lau', safety=True)
        return dict(message='🧽 Bạn lau vội khi bệ đèn còn xoay. Vạt áo bị cuốn vào khe, bạn giật ra kịp. Tim đập thình thịch.', correct=False)
    return dict(message='🔒 Tắt mô-tơ, treo biển “Đang lau kính, cấm bật”. 🧽 Lau từng ô kính bằng giẻ da, muối với bụi sạch bong. Bật lại, đèn quay êm.')


def _fix(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.need(t['found'], 'Chưa thấy gì hỏng để xử lý.')
    f = FAULTS[t['found']]
    kit.need(f['fix'], 'Cái này mình không tự sửa được: báo đúng nơi để thợ ra đảo.')
    kit.need(not t['fixed'], 'Đã xử lý rồi.')
    t['fixed'] = True
    return dict(message=f'🔧 {f["fix"]}. {f["why"]}')


def _form(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.need(t['found'], 'Chưa thấy gì hỏng để báo.')
    form = kit.one_of(p.get('form'), FORMS, 'Không có loại phiếu này.')
    if form in t['forms']:
        t['forms'].remove(form)
        return dict(message=f'Bỏ {_lower(FORMS[form]["name"])}.')
    t['forms'].append(form)
    line = {'so': '📒 Ghi vào sổ trực, ký tên, ghi giờ.', 'phieu': '🧾 Điền phiếu báo hỏng, gửi xí nghiệp theo bộ đàm và chuyến tàu tới.',
            'dai': '📻 Gọi đài: chị Hải Yến ghi nhận, sẽ phát thông báo hàng hải cho tàu thuyền quanh Hòn Gió.'}[form]
    return dict(message=line)


def _fuel(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.need('gen' in t['checked'], 'Đo bồn dầu ở máy phát trước đã.')
    litres = kit.integer(p.get('litres'), 0, 5000)
    t['fuel_log'] = litres
    return dict(message=f'⛽ Ghi sổ dầu: {litres} lít.')


def _sign(s, c, d, p):
    t = _task(c, p, 'dawn')
    kit.start_work(t)
    missing = [e for e in EQUIP if e['id'] not in t['checked']]
    f = t['_fault']
    if t['off'] is None:
        _slip(t, 'no_off', 1, 'Quên tắt đèn, đèn sáng cả buổi sáng.', 'chưa tắt đèn')
    if missing:
        _slip(t, 'unchecked', 2, f'Ký sổ trực mà chưa thử {", ".join(_lower(e["name"]) for e in missing)}.', 'ký sổ khi chưa thử hết')
        if f and not t['found'] and FAULTS[f]['danger']:
            _slip(t, 'hidden_fault', 3, f'{FAULTS[f]["text"]} Không ai biết cho tới khi trời tối.', 'bỏ sót thiết bị hỏng', safety=True)
    if t['cleaned'] is None:
        _slip(t, 'dirty_lens', 1, 'Kính đèn không lau, đêm nay tia sáng mờ đi một quãng.', 'chưa lau kính')
    if t['fuel_log'] is None:
        _slip(t, 'no_fuel_log', 1, 'Sổ dầu bỏ trống hôm nay.', 'chưa ghi sổ dầu')
    elif t['fuel_log'] != t['_fuel']:
        _slip(t, 'fuel_log', 2 if abs(t['fuel_log'] - t['_fuel']) > 20 else 1, f'Sổ dầu ghi {t["fuel_log"]} lít, bồn thật có {t["_fuel"]} lít.', 'sổ dầu không khớp bồn')
    if t['found']:
        x = FAULTS[t['found']]
        d['stats']['faults'] += 1
        if x['fix'] and not t['fixed']:
            _slip(t, 'unfixed', 2 if x['danger'] else 1, f'Thấy hỏng mà chưa xử lý: {_lower(x["text"])}', 'chưa xử lý chỗ hỏng')
        if x['danger'] and 'dai' not in t['forms']:
            _slip(t, 'no_station', 3, 'Đèn, còi có vấn đề mà không báo đài, tàu thuyền không được thông báo.', 'không báo đài', safety=True)
        miss = [k for k in x['forms'] if k != 'dai' and k not in t['forms']]
        if miss:
            _slip(t, 'no_form', 1, f'Chưa {_lower(FORMS[miss[0]]["name"])}: xí nghiệp và ca sau không ai biết.', 'báo chưa đúng nơi')
        d['stats']['reports'] += bool(t['forms'])
    d['on_duty'] = True
    ok = not cq.slips(t)
    reward, tail = _finish(s, c, d, t, 'Ca sáng: tắt đèn, kiểm máy, ký sổ trực.')
    extra = ''
    if t['found'] and 'dai' in t['forms'] and not FAULTS[t['found']]['danger']:
        extra = ' Chị Hải Yến: “Cái này ghi sổ là được rồi em, mà báo thế chị cũng yên tâm.”'
    head = '✍️ Ký sổ trực. Chú Bảy gật gù: “Thử kỹ vậy mới yên.”' if ok else '✍️ Ký sổ trực. Chú Bảy nhíu mày: “Ký là nhận trách nhiệm đó con.”'
    return dict(message=f'{head}{extra} {tail}'.strip(), celebrate=ok)


# ---------------------------------------------------------------- weather: the observation and the report
def reading(t: dict, inst: str) -> str:
    sk = t['_sky']
    if inst == 'wind':
        return f'Máy đo gió: {sk["ms"]} m/s, kim nhích lên xuống đều.'
    if inst == 'sea':
        return SEA_STATES[sk['sea']]['seen']
    if inst == 'vis':
        return VIS[sk['vis']]['seen']
    return f'Áp kế: {sk["hpa"]} hPa. Sổ áp ghi lúc 04:00: {sk["hpa3"]} hPa.'


def _read(s, c, d, p):
    t = _task(c, p, 'weather')
    inst = kit.one_of(p.get('what'), INSTRUMENTS, 'Không có máy này.')
    kit.need(inst not in t['read'], 'Đã đọc rồi.')
    kit.start_work(t)
    t['read'].append(inst)
    return dict(message=f'{INSTRUMENTS[inst]["emoji"]} {reading(t, inst)}')


def _report(s, c, d, p):
    t = _task(c, p, 'weather')
    kit.need(t['report'] is None, 'Đã báo đài rồi.')
    wind = kit.integer(p.get('wind'), 0, 9)
    sea = kit.one_of(p.get('sea'), SEA_STATES, 'Chọn trạng thái biển.')
    vis = kit.one_of(p.get('vis'), VIS, 'Chọn tầm nhìn.')
    baro = kit.one_of(p.get('baro'), BARO, 'Chọn xu hướng áp suất.')
    kit.start_work(t)
    t['report'] = dict(wind=wind, sea=sea, vis=vis, baro=baro)
    sk = t['_sky']
    unread = [k for k in INSTRUMENTS if k not in t['read']]
    if unread:
        _slip(t, 'guess', 2, f'Báo đài mà chưa đọc {", ".join(_lower(INSTRUMENTS[k]["short"]) for k in unread)}: số liệu đoán mò.', 'báo cáo khi chưa quan trắc đủ')
    if wind != sk['wind']:
        _slip(t, 'obs_wind', 2 if abs(wind - sk['wind']) > 1 else 1, f'Báo gió cấp {wind}, thật ra cấp {sk["wind"]}.', 'báo sai cấp gió')
    if sea != sk['sea']:
        _slip(t, 'obs_sea', 1, 'Mô tả mặt biển không khớp những gì nhìn thấy.', 'báo sai trạng thái biển')
    if vis != sk['vis']:
        _slip(t, 'obs_vis', 1, 'Báo tầm nhìn không khớp các mốc nhìn thấy.', 'báo sai tầm nhìn')
    if baro != sk['baro']:
        _slip(t, 'obs_baro', 2 if sk['baro'] == 'fast' else 1, 'Xu hướng áp suất báo sai.', 'báo sai xu hướng áp suất')
    line = (f'📻 Bạn: “Trạm Hòn Gió, bảy giờ: gió cấp {wind}, {_lower(SEA_STATES[sea]["label"])}, tầm nhìn {_lower(VIS[vis]["label"])}, '
            f'áp suất {_lower(BARO[baro]["label"])}.” · Chị Hải Yến: “Đài nhận đủ. Cảm ơn trạm.”')
    return dict(message=line)


def _warn(s, c, d, p):
    t = _task(c, p, 'weather')
    kit.need(not t['warned'], 'Đã phát cảnh báo rồi.')
    kit.start_work(t)
    t['warned'] = True
    if t['_sky']['warn']:
        return dict(message='📢 Bạn phát cảnh báo gió mạnh trên kênh 16, kéo cờ tín hiệu lên cột. Mấy tàu cá gần đảo gọi lại: “Rõ, quay về.”', celebrate=True)
    return dict(message='📢 Bạn phát cảnh báo trên kênh 16. Biển vẫn êm; ông Sáu Ghe gọi lại cằn nhằn: “Gió đâu mà báo?” Cẩn thận thì không thừa, nhưng lần sau xem kỹ số liệu.')


def _wdone(s, c, d, p):
    t = _task(c, p, 'weather')
    kit.need(t['report'] is not None, 'Báo đài số liệu quan trắc trước đã.')
    sk = t['_sky']
    if sk['warn'] and not t['warned']:
        _slip(t, 'no_warn', 3, f'Gió cấp {sk["wind"]}, áp kế {_lower(BARO[sk["baro"]]["label"])} mà trạm không phát cảnh báo.', 'không cảnh báo tàu thuyền', safety=True)
    d['stats']['warned'] += t['warned']
    d['today']['warned'] += t['warned']
    reward, tail = _finish(s, c, d, t, f'Quan trắc bảy giờ: gió cấp {sk["wind"]}.')
    return dict(message=f'📒 Ghi sổ quan trắc. {tail}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- dusk: the light
def _wake(s, c, d, p):
    t = _task(c, p)
    kit.need(t['kind'] in ('dusk', 'sea'), 'Bạn đang tỉnh như sáo rồi.')
    kit.need(not t.get('awake'), 'Bạn đang tỉnh như sáo rồi.')
    t['awake'] = True
    return dict(message='🚰 Bạn vốc nước mưa lạnh lên mặt, đi hai vòng quanh chân tháp, pha ấm trà đặc. Tỉnh hẳn.')


def _light(s, c, d, p):
    t = _task(c, p, 'dusk')
    _need_duty(d)
    kit.need(t['lit'] is None, 'Đèn đã thắp rồi.')
    if d['odd']['fatigue'] >= ao.TIRED and not t['awake']:
        kit.need(False, 'Mắt díp lại rồi: rửa mặt, pha trà cho tỉnh rồi hãy lên phòng đèn.', 'tired')
    pick = kit.integer(p.get('option'), 0, 2)
    kit.start_work(t)
    t['lit'] = pick
    right, late, early = t['_light']
    at = t['needs']['times'][pick]
    if pick == late:
        _slip(t, 'light_late', 2, f'Thắp đèn lúc {at}, trời đã tối, tàu ngoài khơi tìm mốc không thấy.', 'thắp đèn muộn', safety=True)
        return dict(message=f'💡 Bạn thắp đèn lúc {at}. Trời đã tối hẳn, bộ đàm có tàu hỏi “đèn Hòn Gió đâu?”.', correct=False)
    if pick == early:
        _slip(t, 'light_early', 1, f'Thắp đèn lúc {at}, nắng còn chang chang, hao ắc quy.', 'thắp đèn sớm')
        return dict(message=f'💡 Bạn thắp đèn lúc {at}. Nắng còn gắt, đèn sáng mà chẳng ai thấy.', correct=False)
    return dict(message=f'💡 Thắp đèn lúc {at}. Tia sáng đầu tiên quét qua mặt biển còn ửng hồng.')


def count_text(t: dict) -> str:
    return '3 chớp trắng, chu kỳ 19 giây.' if t['_slow'] else '3 chớp trắng, chu kỳ 15 giây.'


def _count(s, c, d, p):
    t = _task(c, p, 'dusk')
    kit.need(t['lit'] is not None, 'Thắp đèn trước đã.')
    kit.need(not t['counted'], 'Đã đếm chớp rồi.')
    t['counted'] = True
    return dict(message=f'⏱️ Bạn bấm đồng hồ nhìn đèn quét: {count_text(t)} Danh mục đèn ghi: {LC.CHARACTER}.', correct=True)


def _horn(s, c, d, p):
    t = _task(c, p, 'dusk')
    kit.need(not t['horn'], 'Còi đã chạy rồi.')
    t['horn'] = True
    if t['_horn_bad']:
        return dict(message='📯 Bạn bật còi sương mù: một tiếng khàn đặc rồi im bặt. Còi không chạy.', correct=False)
    if not t['needs']['fog']:
        return dict(message='📯 Còi rền lên giữa trời trong. Làng chài bên kia chắc đang thắc mắc. (Không có sương thì không cần còi.)')
    return dict(message='📯 Còi sương mù rền hai hồi mỗi ba mươi giây, vang xa trong màn sương trắng.')


def _radio(s, c, d, p):
    t = _task(c, p, 'dusk')
    what = kit.one_of(p.get('what'), ('char', 'horn'), 'Báo đài chuyện gì?')
    kit.need(what not in t['radioed'], 'Đã báo đài chuyện này rồi.')
    if what == 'char':
        kit.need(t['counted'], 'Đếm chớp trước đã.')
        kit.need(t['_slow'], 'Đèn đúng đặc tính mà.')
        line = '📻 Bạn: “Đèn Hòn Gió đêm nay chớp nhóm 3, chu kỳ 19 giây, sai đặc tính.” Chị Hải Yến: “Rõ! Đài phát thông báo hàng hải ngay.”'
    else:
        kit.need(t['horn'] and t['_horn_bad'], 'Còi vẫn chạy mà.')
        line = '📻 Bạn: “Còi sương mù Hòn Gió hỏng, đêm nay không có còi.” Chị Hải Yến: “Rõ! Đài báo tàu thuyền đi chậm, canh hòn Mõ.”'
    t['radioed'].append(what)
    return dict(message=line, celebrate=True)


def truth_dusk(t: dict, day: int) -> set:
    out = set()
    right = t['_light'][0]
    if t['lit'] == right:
        out.add('ontime')
    out.add('char_bad' if t['_slow'] else 'char_ok')
    if t['needs']['fog']:
        out.add('horn_out' if t['_horn_bad'] else 'fog')
    if sky(day)['warn']:
        out.add('wind')
    return out


def _log(s, c, d, p):
    t = _task(c, p, 'dusk')
    kit.need(t['lit'] is not None, 'Thắp đèn trước đã.')
    picks = kit.id_list(p.get('remarks'), REMARKS, max_items=len(REMARKS), message='Chọn dòng ghi sổ.')
    kit.need(picks, 'Chọn ít nhất một dòng ghi sổ.')
    if not t['counted']:
        _slip(t, 'no_count', 1, 'Thắp đèn mà không đếm chớp xem đúng đặc tính chưa.', 'không kiểm đặc tính đèn')
    if t['_slow'] and 'char' not in t['radioed']:
        _slip(t, 'char_unreported', 3, 'Đèn quay sai đặc tính cả đêm mà đài không được báo, tàu có thể nhận nhầm đèn.', 'không báo đèn sai đặc tính', safety=True)
    if t['needs']['fog']:
        if not t['horn']:
            _slip(t, 'no_horn', 3, 'Sương mù dày mà trạm không chạy còi.', 'không chạy còi sương mù', safety=True)
        elif t['_horn_bad'] and 'horn' not in t['radioed']:
            _slip(t, 'horn_unreported', 3, 'Còi hỏng giữa đêm sương mà không báo đài.', 'không báo còi hỏng', safety=True)
    truth = truth_dusk(t, t['day'])
    if set(picks) != truth:
        _slip(t, 'log', 1, 'Sổ trực ghi không khớp với những gì đã xảy ra.', 'ghi sổ chưa đúng')
    t['remarks'] = list(picks)
    safe = not cq.safety(t)
    d['stats']['lit'] += 1
    d['today']['lit'] += 1
    d['stats']['safe'] += safe
    d['today']['safe'] += safe
    d['stats']['honest'] += set(picks) == truth
    if mod_of(c['day'])['id'] == 'storm':
        d['odd']['fatigue'] = min(ao.FATIGUE_MAX, d['odd']['fatigue'] + 1)
    d['log'] = ar.last(d['log'] + [dict(day=c['day'], at=t['needs']['times'][t['lit']], slow=t['_slow'], ok=not cq.slips(t), safe=safe)],
                       LOG_MAX, 'lighthouse.log', c)
    reward, tail = _finish(s, c, d, t, f'Đèn Hòn Gió sáng lúc {t["needs"]["times"][t["lit"]]}.')
    return dict(message=f'📒 Ghi sổ trực buổi tối, ký tên. {tail}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the sea
def look_text(t: dict) -> str:
    x = SEA[t['_case']]
    return x['look'].format(boat=t['_boat'], bearing=t['_bearing'], dist=t['_dist'], persons=t['_persons'])


def _look(s, c, d, p):
    t = _task(c, p, 'sea')
    _need_duty(d)
    kit.need(t['known'], 'Nhìn ra biển trước đã.')
    kit.need(not t['looked'], 'Đã nhìn kỹ rồi.')
    if d['odd']['fatigue'] >= ao.TIRED and not t.get('awake'):
        t['awake'] = True      # a cry from the sea wakes anyone
    kit.start_work(t)
    t['looked'] = True
    return dict(message=f'🔭 {look_text(t)}', correct=True)


ACT_LINES = {
    'horn': dict(kids='📯 Còi rền ba hồi. Mấy cái đầu nhỏ quay lại nhìn đảo, hai đứa bơi chậm lại chờ nhau.',
                 reef='📯 Còi rền hồi dài. Đèn hành trình vẫn lừ lừ tiến tới.', mob='📯 Còi rền lên. Người trên bến quay ra nhìn.',
                 default='📯 Còi rền lên giữa biển.'),
    'lamp': dict(reef='🔦 Bạn chiếu đèn tín hiệu chữ U liên tục về phía tàu: “Bạn đang đi vào nguy hiểm.”',
                 default='🔦 Bạn chiếu đèn tín hiệu về phía đó.'),
    'buoy': dict(mob='🛟 Bạn ném phao có dây, phao rơi sát người đang chới với. Họ bám được, bạn giữ dây kéo dần vào bến.',
                 kids='🛟 Bạn ném phao có dây từ mỏm đá, đứa nhỏ bơi chậm bám được phao, thở hổn hển. Bạn giữ chặt dây.',
                 default='🛟 Xa quá, phao rơi cách bến vài mét. Ném phao chỉ dùng cho người ở gần.'),
    'track': dict(default='🧭 Bạn đứng nguyên một chỗ, mắt không rời mục tiêu, ghi phương vị và giờ vào sổ mỗi năm phút, rọi đèn pha về hướng đó.'),
    'boat': dict(default='🚣 Bạn tháo dây xuồng định ra cứu. Sóng đánh xuồng đập vào bến đá, chú Bảy chạy ra kéo bạn lại: “Mình mà ra là thêm một người phải cứu!”'),
    'swim': dict(default='🏊 Bạn định nhảy xuống. Chú Bảy túm áo bạn lại: “Ném phao! Không ai nhảy xuống cả!”'),
}


def _act(s, c, d, p):
    t = _task(c, p, 'sea')
    what = kit.one_of(p.get('what'), [k for k in SEA_ACTS if k != 'vhf'], 'Thao tác không có.')
    kit.need(t['looked'], 'Nhìn kỹ qua ống nhòm trước đã.')
    kit.need(what not in t['did'], 'Đã làm việc này rồi.')
    t['did'].append(what)
    lines = ACT_LINES[what]
    msg = lines.get(t['_case']) or lines['default']
    if what in ('boat', 'swim'):
        _slip(t, 'went_out', 3, 'Một mình lao ra cứu giữa sóng, suýt thành người thứ hai cần cứu.', 'tự ra khơi, tự bơi ra cứu', safety=True)
        return dict(message=msg, correct=False)
    return dict(message=msg)


def _captain(t: dict) -> dict:
    x = SEA[t['_case']]
    return folk.traits(f'{t["id"]}|cap', PEOPLE[x['npc']][3])


def talk_outcome(t: dict) -> str:
    """How the people out there take the words said so far (pure: their traits and the words)."""
    x = SEA[t['_case']]
    if x['talk'] == 'reef':
        return 'ok' if t['_answers'] else 'silent'
    tr = _captain(t)
    stubborn = tr['proud'] // 34 + tr['stingy'] // 50
    need = 2 + stubborn if x['talk'] == 'storm' else 99         # blast fishermen never come clean on the radio
    score = 0
    for i, words in enumerate(t['talk']):
        score += sum(WORD_SCORE[x['talk']][w] for w in words)
        if score >= need:
            return 'back'
        if i == MAX_ROUNDS - 1:
            return 'refuse'
    return 'again'


def _vhf(s, c, d, p):
    t = _task(c, p, 'sea')
    x = SEA[t['_case']]
    kit.need(t['looked'], 'Nhìn kỹ qua ống nhòm trước đã.')
    kit.need(x['talk'], 'Không có tàu nào để gọi trên kênh 16. Báo đài thì dùng nút báo đài.')
    kit.need(t['talk_out'] in (None, 'again'), 'Đã gọi xong rồi.')
    if x['talk'] == 'reef':
        t['talk'].append(['call'])
    else:
        words = p.get('say')
        kit.need(isinstance(words, list) and 1 <= len(words) <= 2 and len(set(words)) == len(words), 'Chọn một hoặc hai ý để nói.')
        for w in words:
            kit.one_of(w, WORDS, 'Ý này không có.')
        t['talk'].append(list(words))
    out = talk_outcome(t)
    t['talk_out'] = out
    line = TALK[x['talk']][out].format(boat=t['_boat'])
    if x['talk'] == 'storm' and out in ('again', 'refuse') and any('threat' in w for w in t['talk']):
        line += ' (Dọa nạt chỉ làm ông ấy cứng đầu hơn.)'
    return dict(message=line, celebrate=out in ('ok', 'back'))


def needs_relay(t: dict) -> str | None:
    """The priority this case needs on the radio now (None: nobody needs relaying any more)."""
    x = SEA[t['_case']]
    if x['talk'] == 'reef':
        return None if t['talk_out'] == 'ok' else x['relay']
    if x['talk'] == 'storm':
        return None if t['talk_out'] == 'back' else x['relay']
    return x['relay']


RANK = dict(securite=1, pan=2, mayday=3)


def _relay(s, c, d, p):
    t = _task(c, p, 'sea')
    kit.need(t['looked'], 'Nhìn kỹ qua ống nhòm trước đã: phải biết phương vị, khoảng cách, số người.')
    kit.need(t['relay'] is None, 'Đã báo đài rồi. Giờ canh giữ mục tiêu.')
    kind = kit.one_of(p.get('kind'), RELAY, 'Chọn mức báo.')
    bearing = kit.one_of(p.get('bearing'), t['needs']['bearings'], 'Chọn phương vị.')
    persons = None
    if t['needs']['persons'] and kind != 'border':
        persons = kit.integer(p.get('persons'), 0, 99)
        kit.need(persons in t['needs']['persons'], 'Chọn số người.')
    kit.start_work(t)
    t['relay'] = dict(kind=kind, bearing=bearing, persons=persons)
    d['stats']['relays'] += 1
    d['today']['relays'] += 1
    x = SEA[t['_case']]
    if kind == 'border':
        line = f'📻 Bạn: “Trạm Hòn Gió báo: tàu {t["_boat"]}, phương vị {bearing}, nhờ đài chuyển đồn biên phòng.” Chị Hải Yến: “Rõ, đã chuyển. Biên phòng cho tàu ra ngay.”'
    else:
        head = {'mayday': 'MAYDAY RELAY, MAYDAY RELAY, MAYDAY RELAY', 'pan': 'PAN-PAN, PAN-PAN, PAN-PAN', 'securite': 'SÉCURITÉ, SÉCURITÉ, SÉCURITÉ'}[kind]
        who = f', {persons} người' if persons is not None else ''
        line = (f'📻 Bạn: “{head}. Trạm Hòn Gió: {_lower(x["title"])}, phương vị {bearing} từ đèn Hòn Gió, cách {t["_dist"]} hải lý{who}.” '
                f'Chị Hải Yến: “Đài nhận. Điều tàu cứu nạn. Trạm canh giữ mục tiêu, báo đài mỗi mười lăm phút.”')
    return dict(message=line, celebrate=True)


def _sdone(s, c, d, p):
    t = _task(c, p, 'sea')
    x = SEA[t['_case']]
    kit.start_work(t)
    if not t['looked']:
        _slip(t, 'no_look', 2, 'Báo cáo mà chưa nhìn kỹ qua ống nhòm.', 'không quan sát')
    for a in x['need']:
        if a in ('look', 'relay', 'vhf'):
            continue
        if a not in t['did']:
            nm = SEA_ACTS[a]['name']
            safe_need = a in ('buoy', 'track') and x['relay'] == 'mayday'
            _slip(t, 'miss_' + a, 3 if safe_need else 1, f'Chưa {_lower(nm)}.', _lower(nm), safety=safe_need)
    if x['talk'] in ('reef', 'storm') and not t['talk']:
        _slip(t, 'no_call', 2, 'Không gọi tàu trên kênh 16.', 'không gọi tàu', safety=x['talk'] == 'reef')
    if x['talk'] == 'reef' and t['talk_out'] == 'silent' and not ({'lamp', 'horn'} & set(t['did'])):
        _slip(t, 'no_signal', 3, 'Tàu không trả lời mà trạm không chiếu đèn, không kéo còi cảnh báo.', 'không phát tín hiệu cảnh báo', safety=True)
    want = needs_relay(t)
    rel = t['relay']
    if want and not rel:
        if want == 'border':
            _slip(t, 'no_report', 2, f'Thấy {_lower(x["title"])} mà không báo đồn biên phòng.', 'không báo biên phòng', safety=x['talk'] == 'storm')
        else:
            _slip(t, 'no_relay', 3, 'Có người gặp nạn mà trạm không báo đài.', 'không báo đài', safety=True)
    elif rel:
        if want and want != 'border' and rel['kind'] in RANK and RANK[rel['kind']] < RANK[want]:
            _slip(t, 'under_call', 3, 'Báo đài thấp hơn mức nguy hiểm thật, cứu nạn đi chậm.', 'báo thấp mức khẩn cấp', safety=True)
        elif want and want != 'border' and rel['kind'] in RANK and RANK[rel['kind']] > RANK[want]:
            _slip(t, 'over_call', 1, 'Báo đài cao hơn mức cần, đài huy động lực lượng quá mức.', 'báo cao mức khẩn cấp')
        elif want and (rel['kind'] == 'border') != (want == 'border'):
            _slip(t, 'wrong_channel', 3 if want == 'mayday' else 2, 'Báo nhầm kênh: việc cứu nạn thì báo đài, vi phạm thì báo biên phòng.', 'báo nhầm kênh',
                  safety=want == 'mayday')
        if rel['bearing'] != t['_bearing']:
            _slip(t, 'bad_bearing', 2 if want == 'mayday' else 1, f'Báo phương vị {rel["bearing"]}, thật ra {t["_bearing"]}: tàu cứu nạn tìm sai hướng.', 'sai phương vị')
        if rel['persons'] is not None and rel['persons'] != t['_persons']:
            _slip(t, 'bad_persons', 1, f'Báo {rel["persons"]} người, thật ra {t["_persons"]}.', 'sai số người')
    rescued = x['relay'] == 'mayday' and not cq.safety(t)
    d['stats']['rescues'] += rescued
    outcome = {
        'flare': f'Tàu cứu nạn theo phương vị {t["_bearing"]} vớt được {t["_persons"]} ngư dân.',
        'drift': f'Tàu kéo của đồn biên phòng kéo tàu {t["_boat"]} về âu Cửa Lở.',
        'mob': 'Người dưới nước được kéo lên bến, quấn chăn, đài nối máy tư vấn y tế.',
        'kids': 'Ghe làng chài ra đón tụi nhỏ về. Ba mẹ tụi nhỏ đứng chờ ở bến, mặt tái mét.',
        'reef': f'Tàu {t["_boat"]} tránh được bãi đá ngầm hòn Mõ.',
        'storm_out': 'Tàu ông Sáu Ghe quay về âu tránh trú. Đêm đó gió giật mạnh.',
        'blast': 'Biên phòng ra kiểm tra bãi đá, lập biên bản tàu đánh cá bằng chất nổ.',
    }[x['id']]
    if cq.safety(t):
        outcome = 'Đài phải hỏi lại nhiều lần, mọi việc chậm mất mấy chục phút quý.'
    reward, tail = _finish(s, c, d, t, f'{x["title"]}: {outcome}', extra=4 if x['relay'] == 'mayday' else 0)
    return dict(message=f'📒 Ghi sổ trực: {outcome} {tail}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- visitors
def _visitor_of(t: dict) -> dict:
    return VISITOR[t['_v']]


def _papers(s, c, d, p):
    t = _task(c, p, 'visitor')
    _need_duty(d)
    kit.need(t['known'], 'Ra bến đón khách trước đã.')
    kit.need(not t['papers'], 'Đã xem giấy tờ rồi.')
    kit.start_work(t)
    t['papers'] = True
    return dict(message=f'🪪 {_visitor_of(t)["papers"]}', correct=True)


def visit_react(t: dict, v: dict, answer: str, rnd: int) -> str:
    """How a visitor takes the answer (pure: traits rolled from the job and the person)."""
    if v['emergency']:
        return 'ok' if answer == 'shelter' else 'sulk'
    score = 2 if answer in v['best'] else 1 if answer in v['ok'] else -1 if answer in v['bad'] else 0
    tr = folk.traits(f'{t["id"]}|v', PEOPLE[v['npc']][3] if v['npc'] is not None else None)
    heat = tr['rude'] // 25 + tr['proud'] // 40 + (1 if tr['mood'] < 35 else 0)
    calm = tr['honest'] // 40 + tr['savvy'] // 50
    val = 2 * score + calm - heat + rnd
    if answer == 'report' and tr['proud'] >= 75 and not v['soft']:
        return 'blowup'
    if answer not in ('refuse', 'yard', 'report'):
        return 'ok' if val >= 1 else 'sulk'          # let in: glad, or grumbling that it is not more
    if rnd == 0:
        return 'ok' if val >= 4 else 'again'          # told no: most push once more
    if val >= 2:
        return 'ok'
    return 'sulk' if val >= 1 or not v['sneaky'] else 'sneak'


def _answer(s, c, d, p):
    t = _task(c, p, 'visitor')
    kit.need(t['out'] in (None, 'again'), 'Đã trả lời khách rồi.')
    answer = kit.one_of(p.get('answer'), ANSWERS, 'Chọn cách trả lời.')
    v = _visitor_of(t)
    who = v['who'].split(' · ')[0]
    kit.start_work(t)
    t['answers'].append(answer)
    if not t['papers'] and not v['emergency']:
        _slip(t, 'no_papers', 1, 'Quyết định mà chưa xem giấy tờ của khách.', 'chưa xem giấy tờ')
    if answer == 'give':
        t['out'] = 'gave'
        _slip(t, 'gave_in', 2 if v['emergency'] else 3, v['give'], 'chiều khách trái nội quy', safety=not v['emergency'])
        note = ao.penalize(c, d['odd'], 2 if v['offer'] else 1, CFG)
        return dict(message=f'⚠️ {v["give"]} {note}'.strip(), correct=False)
    if v['emergency'] and answer != 'shelter':
        t['out'] = 'bad'
        _slip(t, 'refused_emergency', 3, V_BAD_TEXT['refuse_emergency'], 'không cho người gặp nạn trú', safety=True)
        return dict(message=f'⚠️ {V_BAD_TEXT["refuse_emergency"]}', correct=False)
    if answer == 'escort' and not v['permit']:
        _slip(t, 'escort_nopermit', 2, V_BAD_TEXT['escort_nopermit'], 'cho người không có giấy vào tháp')
    if answer in ('refuse', 'yard') and v['permit'] and answer not in v['best'] and v['id'] != 'writer':
        _slip(t, 'refuse_permit', 1, V_BAD_TEXT['refuse_permit'], 'từ chối người có giấy')
    if answer == 'report' and v['soft']:
        _slip(t, 'cruel', 1, 'Báo biên phòng một người hiền lành, đúng là nặng tay.', 'nặng tay với người hiền')
    if answer == 'shelter' and not v['emergency'] and answer not in v['best'] + v['ok']:
        _slip(t, 'shelter_needless', 1, 'Cho người không gặp nạn vào nhà trạm, trái nội quy.', 'cho người ngoài vào nhà trạm')
    how = visit_react(t, v, answer, t['round'])
    if how == 'again':
        t['round'] = 1
        t['out'] = 'again'
        return dict(message=f'{v["emoji"]} {who}: {v["again"]}')
    t['out'] = how
    if how == 'sneak':
        t['sneak'] = True
        return dict(message=f'🏃 {V_TEXT["sneak"].format(who=who)} Xuống đưa người đó ra ngay!', correct=False)
    if how == 'blowup':
        if v['npc'] is not None:
            kit.review(s, c, kit.npc_id(ID, v['npc']), 2, 'Báo biên phòng như bắt tội phạm. Làm căng quá.', t['id'])
        return dict(message=f'{v["emoji"]} {V_TEXT["blowup"].format(who=who)}', correct=False)
    if how == 'ok':
        c['xp'] += 2
        return dict(message=f'{v["emoji"]} {LC.V_OK[answer].format(who=who)}')
    return dict(message=f'{v["emoji"]} {V_TEXT["sulk"].format(who=who)}')


V_TEXT = dict(sneak=LC.V_SNEAK, blowup=LC.V_BLOWUP, sulk=LC.V_SULK)
V_BAD_TEXT = LC.V_BAD


def _stop(s, c, d, p):
    t = _task(c, p, 'visitor')
    kit.need(t['sneak'] and not t['stopped'], 'Không có ai trên cầu thang tháp.')
    t['stopped'] = True
    v = _visitor_of(t)
    return dict(message=f'🧗 Bạn chạy lên chặn ở chiếu nghỉ, mời {v["who"].split(" · ")[0]} xuống, khóa cửa tháp. “Phòng đèn không phải chỗ tham quan.”', celebrate=True)


def _vdone(s, c, d, p):
    t = _task(c, p, 'visitor')
    kit.need(t['out'] not in (None, 'again'), 'Trả lời khách trước đã.')
    v = _visitor_of(t)
    if t['sneak'] and not t['stopped']:
        _slip(t, 'intruder', 3, 'Người lạ lên tới phòng đèn mà trạm không ngăn.', 'để người lạ vào phòng đèn', safety=True)
    last = t['answers'][-1]
    d['stats']['visitors'] += 1
    d['today']['visitors'] += 1
    if last == 'shelter' and v['emergency']:
        d['stats']['sheltered'] += 1
        d['today']['sheltered'] += 1
    if last in ('refuse', 'report'):
        d['stats']['refused'] += 1
        d['today']['refused'] += 1
    reward, tail = _finish(s, c, d, t, f'Khách ra đảo: {v["who"].split(" · ")[0]}.')
    return dict(message=f'📒 Ghi sổ khách. {tail}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the supply boat
def _dip(s, c, d, p):
    t = _task(c, p, 'supply')
    _need_duty(d)
    kit.need(t['known'], 'Ra bến đón tàu trước đã.')
    when = kit.one_of(p.get('when'), ('before', 'after'), 'Đo lúc nào?')
    kit.need(when not in t['dipped'], 'Đã đo rồi.')
    kit.need(when == 'before' or 'before' in t['dipped'], 'Đo bồn trước khi bơm đã, không thì không biết vào bao nhiêu.')
    kit.start_work(t)
    t['dipped'].append(when)
    if when == 'before':
        return dict(message=f'📏 Thước đo bồn trước khi bơm: {t["_before"]} lít. Chú Tư Lực nổ máy bơm.')
    return dict(message=f'📏 Thước đo bồn sau khi bơm: {t["_after"]} lít.', correct=True)


def _goods(s, c, d, p):
    t = _task(c, p, 'supply')
    g = kit.one_of(p.get('item'), GOODS_IDS, 'Không có món này trên phiếu.')
    kit.need(g not in t['seen'], 'Đã kiểm món này rồi.')
    kit.start_work(t)
    t['seen'].append(g)
    x = next(y for y in GOODS if y['id'] == g)
    st = t['_states'][g]
    return dict(message=f'{x["emoji"]} {x["name"]}: {"✅ " if st == "ok" else "⚠️ "}{GOODS_STATE[st]}', correct=True)


def _note(s, c, d, p):
    t = _task(c, p, 'supply')
    g = kit.one_of(p.get('item'), GOODS_IDS, 'Không có món này trên phiếu.')
    kit.need(g in t['seen'], 'Kiểm món đó trước đã.')
    x = next(y for y in GOODS if y['id'] == g)
    if g in t['noted']:
        t['noted'].remove(g)
        return dict(message=f'Bỏ ghi chú {_lower(x["name"])}.')
    t['noted'].append(g)
    return dict(message=f'✍️ Ghi vào phiếu giao hàng: {_lower(x["name"])} thiếu hoặc hỏng.')


def basket_floor(t: dict) -> int:
    """The least chú Tư Lực lets his basket go for (pure: his traits)."""
    tr = folk.traits(f'{t["id"]}|luc', PEOPLE[LUC][3])
    return BASKET['fair'] + BASKET['fair'] * (tr['stingy'] + tr['proud']) // 400


def _offer(s, c, d, p):
    t = _task(c, p, 'supply')
    kit.need(t['buy'] is None, 'Chuyện giỏ hàng riêng xong rồi.')
    ask = t['needs']['basket']['ask']
    price = kit.integer(p.get('price'), 1, ask)
    kit.need(c['money'] >= price, f'Ví chỉ còn {c["money"]} xu.')
    kit.start_work(t)
    t['offers'].append(price)
    floor = basket_floor(t)
    tries = len(t['offers'])
    if price >= floor or (t['counter'] is not None and price >= t['counter']):
        kit.money(s, c, -price, 'Giỏ đồ tươi của chú Tư Lực', t['id'], 'event_cost')
        t['buy'] = 'bought'
        d['fresh'] = min(LC.FRESH_DAYS + 3, d['fresh'] + 3)
        d['lonely'] = max(0, d['lonely'] - 1)
        cheap = ' Chú Tư Lực tặc lưỡi: “Thôi, bán lấy hên.”' if price < ask else ''
        return dict(message=f'🧺 Mua giỏ đồ tươi {price} xu: xoài chín, cà phê, cá khô, hạt cho Mun.{cheap} Mun dụi đầu vào giỏ.', celebrate=price < ask)
    if tries >= 3 or price * 10 < BASKET['fair'] * 6:
        t['buy'] = 'walked'
        return dict(message='🧺 Chú Tư Lực xách giỏ về tàu: “Trả vậy thì chú mang về bán ở bến cho rồi.”', correct=False)
    t['counter'] = max(floor, (ask + price) // 2 - tries)
    return dict(message=f'🧺 Chú Tư Lực lắc đầu: “Giá xăng lên, chở ra tận đây đó con. {t["counter"]} xu, không bớt nữa.”')


def _skipbuy(s, c, d, p):
    t = _task(c, p, 'supply')
    kit.need(t['buy'] is None, 'Chuyện giỏ hàng riêng xong rồi.')
    t['buy'] = 'skipped'
    return dict(message='🧺 Bạn lắc đầu cười: “Thôi chú, con ăn rau vườn với cá Mun bắt.”')


def _ssign(s, c, d, p):
    t = _task(c, p, 'supply')
    litres = kit.integer(p.get('litres'), 0, 1000)
    kit.start_work(t)
    measured = t['_after'] - t['_before']
    if len(t['dipped']) < 2:
        _slip(t, 'no_dip', 2, 'Ký nhận dầu mà không đo bồn trước và sau khi bơm.', 'ký nhận dầu không đo')
    if litres > measured:
        _slip(t, 'signed_more', 3, f'Ký nhận {litres} lít, bồn chỉ vào {measured} lít.', 'ký khống số dầu')
        note = ao.penalize(c, d['odd'], 2, CFG)
    else:
        note = ''
        if litres < measured:
            _slip(t, 'signed_less', 1, f'Ký nhận {litres} lít, bồn vào {measured} lít.', 'ký thiếu số dầu')
    unseen = [g for g in GOODS_IDS if g not in t['seen']]
    if unseen:
        _slip(t, 'goods_unchecked', 1, 'Ký nhận hàng mà chưa kiểm hết từng món.', 'chưa kiểm hết hàng')
    bad = {g for g, st in t['_states'].items() if st != 'ok'}
    if bad - set(t['noted']):
        _slip(t, 'note_missing', 1, 'Hàng thiếu, hàng hỏng mà phiếu không ghi.', 'phiếu giao hàng thiếu ghi chú')
    if set(t['noted']) - bad:
        _slip(t, 'false_note', 1, 'Ghi thiếu, hỏng cho món còn tốt.', 'ghi chú sai')
    t['signed'] = litres
    if t['buy'] is None:
        t['buy'] = 'skipped'
    lost = sum(1 for g in ('veg', 'fish') if t['_states'][g] != 'ok')
    d['fresh'] = max(d['fresh'], LC.FRESH_DAYS - 2 * lost)
    d['lonely'] = max(0, d['lonely'] - 2)
    d['stats']['supplies'] += 1
    d['stats']['honest'] += litres == measured
    reward, tail = _finish(s, c, d, t, f'Tàu tiếp tế: nhận {litres} lít dầu.')
    head = '✍️ Ký phiếu giao hàng.' + (' Chú Tư Lực lầm bầm nhưng cùng ký dòng “giao thiếu”.' if litres == measured < LC.FUEL_CLAIM else '')
    return dict(message=f'{head} {note} {tail}'.strip(), celebrate=not cq.slips(t))


ACTIONS = {
    'hd_off': _off, 'hd_check': _check, 'hd_clean': _clean, 'hd_fix': _fix, 'hd_form': _form, 'hd_fuel': _fuel, 'hd_sign': _sign,
    'hd_read': _read, 'hd_report': _report, 'hd_warn': _warn, 'hd_wdone': _wdone,
    'hd_wake': _wake, 'hd_light': _light, 'hd_count': _count, 'hd_horn': _horn, 'hd_radio': _radio, 'hd_log': _log,
    'hd_look': _look, 'hd_act': _act, 'hd_vhf': _vhf, 'hd_relay': _relay, 'hd_sdone': _sdone,
    'hd_papers': _papers, 'hd_answer': _answer, 'hd_stop': _stop, 'hd_vdone': _vdone,
    'hd_dip': _dip, 'hd_goods': _goods, 'hd_note': _note, 'hd_offer': _offer, 'hd_skipbuy': _skipbuy, 'hd_ssign': _ssign,
}


# ---------------------------------------------------------------- life on the rock (free, once a day each)
def _pet(s, c, d, p):
    kit.need(d['pet_day'] != c['day'], 'Hôm nay Mun được cưng đủ rồi, giờ Mun đang ngủ.')
    d['pet_day'] = c['day']
    d['lonely'] = max(0, d['lonely'] - 1)
    return dict(message=f'🐈‍⬛ {LC.PET_LINES[c["day"] % len(LC.PET_LINES)]}')


def _garden(s, c, d, p):
    kit.need(d['garden_day'] != c['day'], 'Vườn rau hôm nay tưới rồi.')
    d['garden_day'] = c['day']
    d['lonely'] = max(0, d['lonely'] - 1)
    if mod_of(c['day'])['id'] == 'storm':
        return dict(message='🌧️ Gió lớn: bạn kéo mấy thùng rau vào chân tường, phủ lưới, chằng dây. Lá dập vài cọng nhưng gốc còn.')
    d['garden'] = min(LC.GARDEN_RIPE, d['garden'] + 1)
    if d['garden'] >= LC.GARDEN_RIPE:
        d['garden'] = 0
        d['fresh'] = min(LC.FRESH_DAYS + 3, d['fresh'] + 2)
        return dict(message=f'🥬 {LC.GARDEN_HARVEST}', celebrate=True)
    return dict(message=f'🪴 {LC.GARDEN_LINES[c["day"] % len(LC.GARDEN_LINES)]} ({d["garden"]}/{LC.GARDEN_RIPE} tới mùa cắt)')


def _call(s, c, d, p):
    kit.need(d['call_day'] != c['day'], 'Hôm nay gọi về nhà rồi. Sóng điện thoại trên đảo cũng có hạn.')
    d['call_day'] = c['day']
    d['lonely'] = max(0, d['lonely'] - 2)
    return dict(message=f'📞 {LC.CALLS[kit.rng(ID, "call", c["day"]).randrange(len(LC.CALLS))]}')


LIFE = {'hd_pet': _pet, 'hd_garden': _garden, 'hd_call': _call}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d.update(on_duty=False)
    d['today'] = _fresh_today(day)
    # Yesterday's jobs are over: what is left of them is closed, and today's roster is topped up.
    for t in c['tasks']:
        if t.get('career') == ID and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    mine = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == day]
    if mine:
        slot = max(int(t['id'].split('-')[-1]) for t in mine) + 1
        for _ in range(max(0, daily_task_count(day) - len(mine))):
            t = make_task(day, slot, c['turn'])
            c['tasks'].append(t)
            on_task(s, c, t)
            slot += 1
    first = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'dawn' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if first is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        first = make_task(day, 0, c['turn'])
        c['tasks'].append(first)
        on_task(s, c, first)
    if first:
        c['active_task'] = first['id']
        first['deferred'] = False
    else:
        d['on_duty'] = True   # the morning round already signed today (a day reopened): carry on
    ao.start(c, ID, d['odd'])
    # Life on the rock: the fresh food runs down between boats and loneliness creeps up; a lonely keeper sleeps badly.
    d['fresh'] = max(0, d['fresh'] - 1)
    d['lonely'] = min(LC.LONELY_MAX, d['lonely'] + 1 + (d['fresh'] == 0))
    if d['lonely'] >= LC.LONELY_TIRED:
        d['odd']['fatigue'] = min(ao.FATIGUE_MAX, d['odd']['fatigue'] + 1)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    odd_note = ao.close(s, c, d['odd'], ODD)
    today = d['today']
    lines = []
    if today['lit']:
        lines.append(f'💡 Đèn Hòn Gió sáng đêm nay' + (' đúng giờ, đúng đặc tính.' if today['safe'] else ', nhưng có chuyện cần xem lại.'))
    if today['warned']:
        lines.append('📢 Đã phát cảnh báo gió mạnh cho tàu thuyền.')
    if today['relays']:
        lines.append(f'📻 Báo đài {today["relays"]} lần về tàu thuyền, người gặp nạn.')
    if today['visitors']:
        lines.append(f'🚤 Đón {today["visitors"]} lượt khách ra đảo' + (f', cho {today["sheltered"]} người gặp nạn trú tạm.' if today['sheltered'] else '.'))
    if today['earned']:
        lines.append(f'💵 Thưởng ca hôm nay {today["earned"]} xu (lương trả theo hợp đồng).')
    odd = d['odd']
    seen = [h for h in odd['log'] if h['day'] == c['day'] and h['how'] != 'lapse']
    if seen:
        lines.append(LC.DAY_LINES['odd'].format(n=len(seen), ok=sum(h['good'] is True for h in seen)))
    lv = ao.level(odd['conduct']['points'])
    if lv[1] != 'ok':
        lines.append(LC.DAY_LINES['record'].format(label=CFG['levels'].get(lv[1], lv[2]).lower()))
    if odd['fatigue'] >= ao.TIRED:
        lines.append(LC.DAY_LINES['tired'])
    if d['lonely'] >= LC.LONELY_TIRED:
        lines.append(LC.DAY_LINES['lonely'])
    for n in (desk_note, odd_note):
        if n:
            lines.append(n)
    d.update(on_duty=False)
    nxt = next_supply(c['day'] + 1)
    note = 'Sáng mai: tắt đèn đúng giờ, thử từng thiết bị, lau kính rồi mới ký sổ.' + (' Mai có tàu tiếp tế.' if nxt == 0 else f' Còn {nxt} ngày nữa tới tàu tiếp tế.')
    return dict(lines=lines, note=note, lit=today['lit'], safe=today['safe'], warned=today['warned'], relays=today['relays'],
                visitors=today['visitors'], sheltered=today['sheltered'], earned=today['earned'])


# ================================================================ reviews
def _score(codes: set, bad: set, worse: set = frozenset(), worst: set = frozenset()) -> int:
    if codes & worst:
        return 1
    if codes & worse:
        return 2
    if codes & bad:
        return 3
    return 5


def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    k = t['kind']
    if k == 'dawn':
        return dict(criteria=[dict(key='check', label='Thử đủ thiết bị', score=_score(codes, {'no_off', 'dirty_lens'}, {'unchecked'}, {'hidden_fault', 'off_early', 'no_lockout'}),
                                   note='thử từng thứ, lau kính an toàn' if not codes & {'unchecked', 'hidden_fault', 'no_lockout'} else 'thiếu bước'),
                              dict(key='log', label='Sổ trực, sổ dầu', score=_score(codes, {'no_fuel_log', 'no_form', 'off_late'}, {'fuel_log', 'unfixed'}, {'no_station'}),
                                   note='ghi đúng, báo đúng nơi' if not codes & {'fuel_log', 'no_fuel_log', 'no_form', 'no_station', 'unfixed'} else 'ghi, báo chưa đúng')])
    if k == 'dusk':
        return dict(criteria=[dict(key='light', label='Thắp đèn đúng giờ', score=_score(codes, {'light_early'}, set(), {'light_late'}),
                                   note='đúng giờ' if not codes & {'light_early', 'light_late'} else 'lệch giờ'),
                              dict(key='signal', label='Đặc tính đèn, còi', score=_score(codes, {'no_count'}, set(), {'char_unreported', 'no_horn', 'horn_unreported'}),
                                   note='đếm chớp, báo đài khi sai' if not codes & {'no_count', 'char_unreported', 'no_horn', 'horn_unreported'} else 'bỏ sót'),
                              dict(key='log', label='Sổ trực buổi tối', score=3 if 'log' in codes else 5, note='ghi đúng sự thật' if 'log' not in codes else 'ghi chưa khớp')])
    if k == 'weather':
        obs = {'obs_wind', 'obs_sea', 'obs_vis', 'obs_baro'}
        return dict(criteria=[dict(key='obs', label='Quan trắc đủ, đúng', score=_score(codes, obs, {'guess'}), note='đọc đủ, báo đúng' if not codes & (obs | {'guess'}) else 'sai số liệu'),
                              dict(key='warn', label='Cảnh báo tàu thuyền', score=1 if 'no_warn' in codes else 5, note='kịp thời' if 'no_warn' not in codes else 'không cảnh báo')])
    if k == 'sea':
        return dict(criteria=[dict(key='look', label='Quan sát, canh giữ', score=_score(codes, {'no_look', 'miss_horn', 'miss_track'}, set(), {'miss_buoy', 'went_out', 'no_signal'}),
                                   note='mắt không rời mục tiêu' if not codes & {'no_look', 'miss_track', 'miss_buoy', 'went_out', 'no_signal', 'miss_horn'} else 'chưa đủ'),
                              dict(key='relay', label='Báo đài đúng mức', score=_score(codes, {'over_call', 'bad_persons', 'no_call'}, {'bad_bearing', 'wrong_channel', 'no_report'},
                                                                                       {'no_relay', 'under_call'}),
                                   note='đúng mức, đúng vị trí' if not codes & {'over_call', 'bad_persons', 'bad_bearing', 'wrong_channel', 'no_relay', 'under_call', 'no_report', 'no_call'} else 'báo chưa đúng'),
                              dict(key='safe', label='Không liều mạng', score=1 if 'went_out' in codes else 5, note='cứu bằng phao, bằng bộ đàm' if 'went_out' not in codes else 'tự ra khơi')])
    if k == 'visitor':
        return dict(criteria=[dict(key='rules', label='Giữ nội quy trạm', score=_score(codes, {'no_papers', 'shelter_needless'}, {'escort_nopermit'}, {'gave_in', 'intruder'}),
                                   note='xem giấy, đúng nội quy' if not codes & {'no_papers', 'escort_nopermit', 'gave_in', 'intruder', 'shelter_needless'} else 'lỏng tay'),
                              dict(key='kind', label='Tử tế với khách', score=_score(codes, {'cruel', 'refuse_permit'}, set(), {'refused_emergency'}),
                                   note='cứng mà mềm' if not codes & {'cruel', 'refuse_permit', 'refused_emergency'} else 'chưa khéo')])
    return dict(criteria=[dict(key='fuel', label='Ký đúng số dầu', score=_score(codes, {'signed_less'}, {'no_dip'}, {'signed_more'}),
                               note='đo trước, đo sau, ký đúng' if not codes & {'signed_less', 'no_dip', 'signed_more'} else 'chưa đúng'),
                          dict(key='goods', label='Kiểm hàng', score=_score(codes, {'goods_unchecked', 'note_missing', 'false_note'}),
                               note='từng món' if not codes & {'goods_unchecked', 'note_missing', 'false_note'} else 'sót món')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    k = t['kind']
    if k == 'dawn':
        return f'Mặt trời mọc {n["rise"]}. {n["rule"]} {n["handover"]} {n["note"]}'
    if k == 'dusk':
        return f'Mặt trời lặn {n["set"]}. {n["rule"]} Danh mục đèn: {n["chart"]}. {n["note"]}'
    if k == 'weather':
        return f'Quan trắc {n["hour"]}: gió, biển, tầm nhìn, áp suất. {n["note"]}'
    if k == 'sea':
        return f'{t["opening"]} {n["note"]}'
    if k == 'visitor':
        return f'{n["who"]}: {n["wants"]}. {n["note"]}'
    return f'Tàu tiếp tế: dầu {n["claim"]} lít theo phiếu, {len(n["goods"])} món hàng. {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
        return v
    k = t['kind']
    if k == 'dawn':
        f = FAULTS[t['found']] if t['found'] else None
        v['found_text'] = f['text'] if f else None
        v['found_fix'] = f['fix'] if f else None
        v['found_item'] = f['item'] if f else None
        v['fuel_seen'] = t['_fuel'] if 'gen' in t['checked'] else None
        return v
    if k == 'dusk':
        v['count_text'] = count_text(t) if t['counted'] else None
        v['horn_dead'] = bool(t['horn'] and t['_horn_bad'])
        return v
    if k == 'weather':
        v['seen'] = {i: reading(t, i) for i in t['read']}
        return v
    if k == 'sea':
        v['seen'] = look_text(t) if t['looked'] else None
        v['talk_line'] = TALK[SEA[t['_case']]['talk']][t['talk_out']].format(boat=t['_boat']) if t['talk_out'] else None
        return v
    if k == 'visitor':
        x = _visitor_of(t)
        v['line'] = x['line'] if t['round'] == 0 else x['again']
        v['papers_text'] = x['papers'] if t['papers'] else None
        v['offer'] = x['offer'] or None
        return v
    v['dips'] = {w: t['_before'] if w == 'before' else t['_after'] for w in t['dipped']}
    v['states'] = {g: t['_states'][g] for g in t['seen']}
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    al = almanac(c['day'])
    odd = d.get('odd') or ao.initial()
    return dict(intro=d['intro'], on_duty=d['on_duty'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()}, log=d['log'][-6:],
                rise=_clock(al['rise']), set=_clock(al['set']), supply_in=next_supply(c['day']),
                life=dict(lonely=d['lonely'], fresh=d['fresh'], garden=d['garden'], ripe=LC.GARDEN_RIPE, pet=d['pet_day'] == c['day'],
                          watered=d['garden_day'] == c['day'], called=d['call_day'] == c['day'], max=LC.LONELY_MAX, tired=LC.LONELY_TIRED),
                desk=kit.desk_public(d['desk'], DESK, ID), odd=ao.public(c, odd, ODD, ID, CFG))


def content() -> dict:
    return dict(equip=EQUIP, forms=FORMS, instruments=INSTRUMENTS, beaufort=[list(b) for b in BEAUFORT],
                sea_states={k: v['label'] for k, v in SEA_STATES.items()}, vis={k: v['label'] for k, v in VIS.items()},
                baro={k: v['label'] for k, v in BARO.items()}, warn_wind=WARN_WIND, remarks=REMARKS, sea_acts=SEA_ACTS, relay=RELAY,
                words=WORDS, answers=ANSWERS, goods=GOODS, goods_state=GOODS_STATE, intro=INTRO, rule=LC.LIGHT_RULE, chart=LC.CHARACTER,
                code=LC.CHAR_CODE, light=LC.LIGHT, island=LC.ISLAND, company=LC.COMPANY, station=LC.STATION,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    return {
        'dawn': 'Tắt đèn đúng giờ → thử từng thiết bị → tắt mô-tơ rồi lau kính → ghi sổ dầu → hỏng thì xử lý và báo đúng nơi → ký sổ trực.',
        'dusk': 'Thắp đèn trước giờ lặn 15 phút → đếm chớp so với danh mục → sai thì báo đài → sương mù chạy còi → ghi sổ đúng sự thật.',
        'weather': 'Đọc máy đo gió, mặt biển, các mốc tầm xa, áp kế → báo đài bốn số liệu → gió từ cấp 6 hoặc áp giảm nhanh thì phát cảnh báo.',
        'sea': 'Nhìn kỹ qua ống nhòm → gọi tàu, ném phao, kéo còi tùy chuyện → báo đài đúng mức, đúng phương vị → canh giữ mục tiêu. Không tự ra khơi.',
        'visitor': 'Xem giấy tờ → trả lời theo nội quy (đi kèm, chỉ ở sân, từ chối, cho trú, báo biên phòng) → ai lẻn lên tháp thì đưa xuống → ghi sổ khách.',
        'supply': 'Đo bồn trước và sau → kiểm từng món, ghi món thiếu, hỏng → ký đúng số lít đo được → giỏ hàng riêng thì trả giá hoặc thôi.',
    }.get(k, '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'watch':
        if t and t.get('career') == ID and t.get('kind') == 'sea' and t['status'] not in ('completed', 'cancelled') and t.get('looked') and 'track' not in t['did']:
            t['did'].append('track')
            return 'Đã đứng canh mục tiêu, ghi phương vị mỗi năm phút.'
        return 'Đã lau kính đèn, quét bậc thang tháp.'
    if e.get('role') == 'tech':
        return 'Đã kiểm máy phát, siết lại khớp ống, châm nhớt.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu trạm đèn sai.')


def _vlist(v, allowed, n: int, msg: str = 'Dữ liệu việc trạm đèn sai.') -> None:
    kit.need(isinstance(v, list) and len(v) <= n and len(v) == len(set(v)) and all(isinstance(x, str) and x in allowed for x in v), msg)


def _vpick(v, n: int = 2) -> None:
    kit.need(v is None or (type(v) is int and 0 <= v <= n), 'Lựa chọn sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS, 'Việc trạm đèn không hợp lệ.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người quen sai.')
    k = t['kind']
    if k == 'dawn':
        _vpick(t.get('off'))
        _vlist(t.get('checked'), EQUIP_IDS, len(EQUIP_IDS))
        kit.need(t.get('found') in (None, t['_fault']) and (t['found'] is None or t['_fault'] is not None), 'Thiết bị hỏng sai.')
        _vbool(t.get('fixed'))
        _vlist(t.get('forms'), FORMS, len(FORMS))
        kit.need(t.get('cleaned') in (None, 'lock', 'quick'), 'Lau kính sai.')
        kit.need(t.get('fuel_log') is None or (type(t['fuel_log']) is int and 0 <= t['fuel_log'] <= 5000), 'Sổ dầu sai.')
        return
    if k == 'dusk':
        _vpick(t.get('lit'))
        for key in ('counted', 'horn', 'awake'):
            _vbool(t.get(key))
        _vlist(t.get('radioed'), ('char', 'horn'), 2)
        if t.get('remarks') is not None:
            _vlist(t['remarks'], REMARKS, len(REMARKS))
        return
    if k == 'weather':
        _vlist(t.get('read'), INSTRUMENTS, len(INSTRUMENTS))
        _vbool(t.get('warned'))
        r = t.get('report')
        kit.need(r is None or (isinstance(r, dict) and set(r) == {'wind', 'sea', 'vis', 'baro'} and type(r['wind']) is int and 0 <= r['wind'] <= 9
                               and r['sea'] in SEA_STATES and r['vis'] in VIS and r['baro'] in BARO), 'Báo cáo quan trắc sai.')
        return
    if k == 'sea':
        _vbool(t.get('looked'))
        _vbool(t.get('awake', False))
        _vlist(t.get('did'), [a for a in SEA_ACTS if a != 'vhf'], len(SEA_ACTS))
        tk = t.get('talk')
        kit.need(isinstance(tk, list) and len(tk) <= MAX_ROUNDS and all(isinstance(w, list) and 1 <= len(w) <= 2 and len(set(w)) == len(w)
                                                                       and all(x in WORDS or x == 'call' for x in w) for w in tk), 'Lời gọi tàu sai.')
        kit.need(t.get('talk_out') in (None, 'ok', 'silent', 'back', 'again', 'refuse'), 'Lời gọi tàu sai.')
        kit.need(bool(tk) == (t['talk_out'] is not None), 'Lời gọi tàu sai.')
        if tk:
            kit.need(t['talk_out'] == talk_outcome(t), 'Lời gọi tàu sai.')
        rel = t.get('relay')
        n = t['needs']
        kit.need(rel is None or (isinstance(rel, dict) and set(rel) == {'kind', 'bearing', 'persons'} and rel['kind'] in RELAY and rel['bearing'] in n['bearings']
                                 and (rel['persons'] is None or (n['persons'] and rel['persons'] in n['persons']))), 'Tin báo đài sai.')
        return
    if k == 'visitor':
        for key in ('papers', 'sneak', 'stopped'):
            _vbool(t.get(key))
        _vlist_dup(t.get('answers'), ANSWERS, MAX_ROUNDS)
        kit.need(t.get('round') in (0, 1) and t.get('out') in (None, 'ok', 'sulk', 'again', 'sneak', 'blowup', 'gave', 'bad'), 'Trả lời khách sai.')
        kit.need(not t['stopped'] or t['sneak'], 'Trả lời khách sai.')
        return
    _vlist(t.get('dipped'), ('before', 'after'), 2)
    _vlist(t.get('seen'), GOODS_IDS, len(GOODS_IDS))
    _vlist(t.get('noted'), GOODS_IDS, len(GOODS_IDS))
    kit.need(set(t['noted']) <= set(t['seen']), 'Phiếu giao hàng sai.')
    o = t.get('offers')
    kit.need(isinstance(o, list) and len(o) <= 3 and all(type(x) is int and 1 <= x <= t['needs']['basket']['ask'] for x in o), 'Trả giá sai.')
    kit.need(t.get('counter') is None or (type(t['counter']) is int and 1 <= t['counter'] <= 10 ** 4), 'Trả giá sai.')
    kit.need(t.get('buy') in (None, 'bought', 'skipped', 'walked'), 'Giỏ hàng riêng sai.')
    kit.need(t.get('signed') is None or (type(t['signed']) is int and 0 <= t['signed'] <= 1000), 'Phiếu giao hàng sai.')


def _vlist_dup(v, allowed, n: int) -> None:
    kit.need(isinstance(v, list) and len(v) <= n and all(isinstance(x, str) and x in allowed for x in v), 'Trả lời khách sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    for k in ('intro', 'on_duty'):
        _vbool(d[k])
    kit.integer(d['lonely'], 0, LC.LONELY_MAX)
    kit.integer(d['fresh'], 0, LC.FRESH_DAYS + 3)
    kit.integer(d['garden'], 0, LC.GARDEN_RIPE)
    for k in ('pet_day', 'garden_day', 'call_day'):
        kit.integer(d[k], 0, 10 ** 7)
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu trạm đèn sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(d['log'], list) and len(d['log']) <= LOG_MAX, 'Sổ đèn sai.')
    for x in d['log']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'at', 'slow', 'ok', 'safe'}, 'Sổ đèn sai.')
        kit.integer(x['day'], 1, 10 ** 7)
        kit.text(x['at'], 5)
        for k in ('slow', 'ok', 'safe'):
            _vbool(x[k])
    kit.desk_validate(d['desk'], DESK)
    ao.validate(d['odd'], ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='hd_', category='outdoor',
    meta=dict(short='Gác hải đăng', place='Đèn biển Hòn Gió', tagline='Đèn sáng đúng giờ, không ai bị bỏ lại ngoài khơi.', icon='sun',
              color='#2f6f8f', light='#e6f1f6', weather='Gió biển mằn mặn, trời trong', work='Việc trên đảo', station='Nhà trạm',
              greeting='Tắt đèn, thử máy, lau kính. Quan trắc, báo đài. Ai gặp nạn thì báo đài đúng mức và canh giữ; khách ra đảo thì xem giấy, không ai vào phòng đèn.',
              caption='Đêm nào đèn cũng phải sáng', map_label='29 · ĐÈN BIỂN HÒN GIÓ'),
    people=PEOPLE,
    staff=[('Lâm', 'watch', 'Ít nói, ngồi canh biển cả buổi không chớp mắt.', 74, 92),
           ('Tấn', 'tech', 'Nghe tiếng máy nổ là biết bệnh, tay lúc nào cũng dính dầu.', 80, 88),
           ('Hạnh', 'watch', 'Giọng bộ đàm rõ ràng, đọc phương vị không sai một độ.', 82, 86),
           ('Quý', 'tech', 'Leo cột thu lôi nhanh như sóc, sợ nhất là… mèo.', 86, 80)],
    roles={'watch': 'Người trực phụ', 'tech': 'Thợ máy'},
    tip=0,
    open_line='Chú Bảy gõ cửa lúc trời còn tối: “Dậy tắt đèn thôi con.”',
    more_line='Đêm xuống, ngoài biển lại có chuyện.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🗼', 'Trạm đèn Hòn Gió', [('Tắt, thắp đèn', 'Theo giờ mặt trời'), ('Đếm chớp', 'So với danh mục đèn'),
                                       ('MAYDAY RELAY', 'Khi có người gặp nạn'), ('Phòng đèn', 'Không cho người ngoài vào')],
              ['Kiểm máy, lau kính, ghi sổ dầu', 'Quan trắc và báo đài', 'Canh biển, báo đài đúng mức', 'Thắp đèn, đếm chớp, ghi sổ']),
    stories=[('Cái giẻ da của chú Bảy', ('Chú Bảy lau kính đèn bằng một miếng giẻ da cũ mềm như lụa.',
                                         'Chú kể năm bão lớn, chú quay tay mô-tơ suốt đêm cho đèn khỏi đứng.',
                                         'Ngày bạn giữ đèn trọn một tuần không sơ suất, chú đưa bạn miếng giẻ da.')),
             ('Ông Sáu Ghe và cái lưới', ('Ông Sáu Ghe đêm nào cũng gọi xin “quay đèn về phía lưới”.',
                                          'Bạn đọc bản tin gió cho ông nghe, chỉ ông dùng đèn câu trên tàu.',
                                          'Mùa bão năm ấy ông Sáu gọi lên trạm hỏi bản tin trước mỗi chuyến ra khơi.')),
             ('Mèo Mun trên đảo', ('Mun là con mèo đen theo tàu tiếp tế ra đảo từ hồi còn bé xíu.',
                                   'Đêm bão, Mun nằm khoanh tròn dưới chân bàn trực, kêu rừ rừ như cái mô-tơ đèn.',
                                   'Chú Bảy bảo: “Ở đảo mà có con mèo là có người nhà.”'))],
    review_asides=['Đèn sáng đúng giờ, quét đều như nhịp thở.', 'Báo đài rành rọt, phương vị không lệch một độ.', 'Nội quy cứng mà người thì mềm.',
                   'Sổ trực ghi thật từng dòng.'],
    situations=SITUATIONS,
    guide='Sáng: tắt đèn đúng giờ, thử từng thiết bị, tắt mô-tơ rồi lau kính, ghi sổ dầu, báo đúng nơi. Quan trắc: đọc đủ rồi báo đài; gió từ cấp 6 thì cảnh báo. '
          'Biển: nhìn kỹ, báo đài đúng mức, đúng phương vị, canh giữ; không tự ra khơi. Khách: xem giấy, không ai vào phòng đèn, người gặp nạn luôn được trú. '
          'Chiều: thắp đèn đúng giờ, đếm chớp, sai thì báo đài, ghi sổ đúng sự thật.',
    employment=dict(
        postings=[
            dict(id='hd-gac', org=f'{LC.COMPANY} · {LC.LIGHT}', kind='company', title='Nhân viên gác đèn biển',
                 salary=(66, 84), probation_days=3, wants=['careful', 'calm', 'patience'],
                 perks=['Chú Bảy kèm cặp những ca đầu', 'Có phụ cấp đảo xa', 'Có mèo Mun làm bạn'],
                 culture='Trạm đèn hai người trên một hòn đảo đá. Đèn nói trước, người nói sau; ai gặp nạn trên biển là việc của mình.',
                 questions=['hd_flare', 'hd_visit', 'hd_log', 'mistake'], reference=True),
            dict(id='hd-phu', org=f'{LC.COMPANY} · Tổ đèn luồng Cửa Lở', kind='branch', title='Nhân viên trực phụ trạm đèn',
                 salary=(56, 70), probation_days=2, wants=['careful', 'learning'],
                 perks=['Nhận việc nhanh', 'Học quan trắc từ đầu', 'Lương thấp hơn gác đèn chính'],
                 culture='Tổ đèn luồng ba người, thay ca cho các trạm đèn đảo khi thiếu người.',
                 questions=['hd_wx'], reference=False),
        ],
        questions={
            'hd_flare': dict(text='Đêm bão, bạn thấy một pháo hiệu đỏ phía đông nam. Xuồng của trạm nằm dưới bến. Bạn làm gì?', options=[
                dict(id='relay', label='Báo đài MAYDAY RELAY: phương vị, khoảng cách, số người; rồi canh giữ mục tiêu', score=3, note='Chú Bảy gật đầu: đúng việc của người gác đèn.'),
                dict(id='boat', label='Lấy xuồng ra cứu cho kịp', score=0, note='Một mình ra khơi giữa bão là thêm một người phải cứu.'),
                dict(id='wait', label='Chờ pháo hiệu thứ hai cho chắc', score=1, note='Một pháo hiệu là đủ để báo.')]),
            'hd_visit': dict(text='Nhóm khách cano thuê không có giấy, đòi lên đỉnh tháp chụp ảnh hoàng hôn.', options=[
                dict(id='yard', label='Từ chối lên tháp, mời chụp ở sân trạm, giải thích nội quy', score=3, note='Cứng mà vẫn tử tế.'),
                dict(id='up', label='Cho lên năm phút, mình đi kèm', score=0, note='Không có giấy thì không vào tháp.'),
                dict(id='shoo', label='Đuổi về, không nói gì', score=1, note='Đúng nội quy, nhưng nói một câu giải thích cũng được mà.')]),
            'hd_log': dict(text='Đêm qua đèn tắt hai mươi phút vì mất điện. Sếp bảo ghi “bình thường” cho đỡ rắc rối.', options=[
                dict(id='true', label='Ghi đúng giờ tắt, nguyên nhân và cách đã xử lý', score=3, note='Sổ trực là văn bản: ghi đúng mới có người tin.'),
                dict(id='fake', label='Ghi “bình thường” theo lời sếp', score=0, note='Sổ vênh với phản ánh của tàu thì ai chịu?'),
                dict(id='skip', label='Không ghi gì cả', score=1, note='Bỏ trống cũng là giấu.')]),
            'hd_wx': dict(text='Áp kế tụt bốn hPa trong ba giờ, gió mới cấp 4. Bạn báo đài thế nào?', options=[
                dict(id='warn', label='Báo đủ số liệu, nhấn mạnh áp giảm nhanh, phát cảnh báo cho tàu thuyền', score=3, note='Áp tụt nhanh là dấu hiệu áp thấp tới.'),
                dict(id='wind', label='Gió mới cấp 4, chưa cần báo gì thêm', score=0, note='Gió chưa lên nhưng áp đã báo trước.'),
                dict(id='later', label='Chờ giờ quan trắc sau xem sao', score=1, note='Cảnh báo sớm thì tàu kịp về.')]),
        }),
)
