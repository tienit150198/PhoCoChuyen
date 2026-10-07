"""🍚 No bụng và 😴 Tỉnh táo: eating and sleeping around the work day (story mode only, like tinh thần).

Player feedback: "thêm đói bụng và buồn ngủ … đi làm về chọn mua gì ăn và giờ đi ngủ … cả ngày làm cũng nên ăn
đủ bữa". Small on purpose: two bars next to tinh thần, one lunch moment, one evening screen. Never a hard fail.

* Two numbers 0–100 in `s['journey']['needs']`: `full` (no bụng) and `wake` (tỉnh táo). They drain with the
  workplace's own clock (game/dayclock.py): FULL_PER_HOUR and WAKE_PER_HOUR per hour of shop time, counted on
  the minutes worked today (`worked`), so 20-minute steps never lose a rounding.
* Breakfast is automatic and free each morning (the first career action of a new life day, normally start_day).
  A shift that opens at LATE_START or later had its lunch at home before work, also free.
* Lunch: from LUNCH_FROM on the shop clock the calm screen offers LUNCH (one tap, never a modal). Left alone, the
  packed lunch box is eaten when the clock passes LUNCH_UNTIL. Meals do not move the shop clock: each career keeps
  its own clock and its customers' patience runs on it, so a meal is a break, not a lost turn.
* Evening (between end_day and the next morning; journey.life_day has already moved on): one dinner and one
  bedtime (`jr_needs_eve`). The home decides the free dinner (Bà Tám's attic, mì gói in the dorm, cooking in a
  rented room or at home); the street and a nicer meal cost a few xu; married players can eat with their spouse.
  Bedtimes start after the dinner is over (the day's closing time + the meal's minutes); the bedtime sets tomorrow
  morning's tỉnh táo. Not chosen by the morning: "như mọi khi" (the last choice still possible, else the free
  dinner and 23:00) is taken for you.
* Money: the daily living cost (journey.LIVING) already pays rent *and* meals, so every home dinner and the packed
  lunch are free: nothing is charged twice. Only the optional street food and treats cost xu, from the wallet,
  with the history kind 'living' (an older build accepts it), and only when the wallet holds the price: food never
  makes debt.
* Ăn thêm (jr_needs_snack {item}): any time during the work day, the player can buy a snack or a coffee, paid
  from the wallet (SNACK). No daily cap: a food is refused when no bụng is already high (FULL_CAP), the coffee
  when tỉnh táo is (WAKE_CAP). No tinh thần from snacks, and no new state: nothing to roll back.
* Tinh thần (game/life.py, journey.life.spirit) moves a little: −1 the first time a bar drops under LOW in a day
  (with a line from the character), +1 for a day fed well, +1 for sleeping on time or for a relaxed late evening,
  +1/+2 for the paid meals. No death spiral: the free routine never triggers a dip on an ordinary day.

State (absent in older saves; created on the first story action, validate() checks it strictly when present):
  v, day (the life day these numbers belong to; < journey.life_day means the evening is on), full, wake, worked,
  seen ([career, career day, minute] last read off the shop clock), lunch (today's lunch id or None),
  low (bars that dipped today), finish (today's closing minute, for the evening), eve ({meal, bed} chosen tonight
  or None), usual ({meal, bed}: "như mọi khi").
Commands (through journey.action): jr_needs_lunch {meal}, jr_needs_eve {meal, bed}, jr_needs_snack {item}. The first two are idempotent: the same
choice again changes nothing; a different one after choosing is refused with code 'already_done'.
Rollback: an older build ignores `journey.needs` (journey.validate allows extra keys) and keeps loading the save.
"""
from __future__ import annotations

from . import dayclock as dc
from . import housing as hs
from . import price_index as pi   # 💹 07/10: LUNCH, EVE and SNACK prices are the base, indexed below

VERSION = 1
START_FULL, START_WAKE = 90, 100     # a save that meets this layer: just had breakfast, slept well
FULL_PER_HOUR, WAKE_PER_HOUR = 7, 4  # per hour of shop time
STEP_CAP = 240                       # one action never counts more than this many shop minutes
LOW = 25                             # under this: a dip (−1 tinh thần) and a hint, once a day per bar
FED = 35                             # "ăn đủ bữa": lunch eaten and fullness never under LOW today
LUNCH_FROM, LUNCH_UNTIL = 11 * 60 + 30, 13 * 60 + 30
LATE_START = 13 * 60                 # a shift opening this late: lunch at home before work
NIGHT_FULL = 30                      # the night takes this much fullness
BREAKFAST = 25
HOME_LUNCH = 35
WAKE_AT = 6 * 60 + 30                # tomorrow's alarm, for the hours of sleep
BEDS = (22 * 60, 23 * 60, 24 * 60, 25 * 60)
ON_TIME = 23 * 60                    # in bed by then: "ngủ đủ giấc" +1 the next morning
OWL = 24 * 60                        # in bed this late or later: +1 tonight (a film, the phone), less tỉnh táo
BED_MIN, BED_MAX = 20 * 60, 27 * 60
KEYS = {'v', 'day', 'full', 'wake', 'worked', 'seen', 'lunch', 'low', 'finish', 'eve', 'usual'}

# Lunch: id → what it is. price in xu (0: the packed lunch, already in the daily cơm nước), full / wake added,
# spirit (tinh thần) added. 'nha' (lunch at home before a late shift) is never offered: the morning sets it.
LUNCH = {
    'hop': dict(emoji='🍱', name='Cơm hộp mang theo', short='Cơm hộp', price=0, full=35, wake=0, spirit=0, note='Cơm nhà, đã tính trong tiền cơm nước'),
    'binh_dan': dict(emoji='🍛', name='Cơm bình dân đầu hẻm', short='Cơm bình dân', price=4, full=45, wake=0, spirit=1, note='Ngồi quán, đổi gió một chút'),
    'banh_mi': dict(emoji='🥖', name='Bánh mì và cà phê sữa đá', short='Bánh mì, cà phê', price=3, full=25, wake=12, spirit=0, note='Ăn nhanh, tỉnh cả người'),
    'nhin': dict(emoji='🙅', name='Nhịn, làm tiếp', short='Nhịn', price=0, full=0, wake=0, spirit=0, note='Bụng sẽ réo vào buổi chiều'),
}
LUNCH_IDS = tuple(LUNCH) + ('nha',)
AUTO_LUNCH = 'hop'
ATE = ('hop', 'binh_dan', 'banh_mi', 'nha')

# Dinner. 'nha' is the free one at home and depends on where you live (HOME_MEAL); minutes = how long it takes.
HOME_MEAL = {
    'attic': dict(emoji='🍲', name='Cơm Bà Tám để phần', full=45, minutes=30, note='Bà Tám nấu, đã tính trong tiền cơm nước'),
    'dorm': dict(emoji='🍜', name='Mì gói ở phòng', full=30, minutes=15, note='Nấu ấm siêu tốc, ăn cùng bạn phòng'),
    'rent': dict(emoji='🍳', name='Tự nấu bữa đơn giản', full=45, minutes=40, note='Cơm, trứng chiên, canh rau'),
    'own': dict(emoji='🍳', name='Nấu cơm ở nhà', full=50, minutes=45, note='Bếp nhà mình, cơm canh nóng hổi'),
}
EVE = {
    'an_vat': dict(emoji='🥢', name='Bún riêu đầu hẻm', price=4, full=40, minutes=20, spirit=0, note='Tô bún nóng, ngồi ghế nhựa ngắm phố'),
    'bua_ngon': dict(emoji='🍖', name='Cơm tấm sườn bì chả', price=9, full=55, minutes=50, spirit=2, note='Tự thưởng sau một ngày dài'),
    'vo_chong': dict(emoji='💞', name='Ăn tối cùng {spouse}', price=0, full=50, minutes=60, spirit=2, note='Hai người, một mâm cơm'),
}
EVE_IDS = ('nha',) + tuple(EVE)

# Ăn thêm: bought whenever the player wants during the work day. Always paid (the daily cơm nước covers three meals).
SNACK = {
    'banh_bao': dict(emoji='🥟', name='Bánh bao nóng', short='Bánh bao', price=3, full=20, wake=0),
    'xoi': dict(emoji='🍙', name='Gói xôi mặn', short='Xôi mặn', price=5, full=35, wake=0),
    'pho': dict(emoji='🍜', name='Tô phở bò', short='Tô phở', price=8, full=50, wake=0),
    'ca_phe': dict(emoji='☕', name='Ly cà phê sữa đá', short='Cà phê', price=3, full=0, wake=15),
}
for _menu in (LUNCH, EVE, SNACK):   # 💹 07/10 (game/price_index.py; under 5 xu a price stays)
    pi.index(_menu, luxury=False)
FULL_CAP, WAKE_CAP = 90, 90   # at or above: "no rồi" / "tỉnh rồi", that item is refused
COOK_SKILL = 3            # Nội trợ: after this many jobs there, your own cooking is a little nicer (+1 tinh thần)

BED_TEXT = {
    22 * 60: 'Ngủ sớm',
    23 * 60: 'Tắm, nghe nhạc',
    24 * 60: 'Xem một tập phim',
    25 * 60: 'Lướt điện thoại',
}

FULL_WORDS = ((75, 'No nê'), (50, 'Vừa bụng'), (LOW, 'Hơi đói'), (0, 'Đói lả'))
WAKE_WORDS = ((75, 'Tỉnh như sáo'), (50, 'Hơi mỏi'), (LOW, 'Mệt'), (0, 'Buồn ngủ rũ rượi'))
SAY_HUNGRY = 'Bụng réo ùng ục rồi… Tay chân hơi rã rời.'
SAY_SLEEPY = 'Mắt díp lại rồi… Tay chậm hẳn đi.'


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _clamp(v) -> int:
    return max(0, min(100, int(v)))


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, day=max(1, int(day)), full=START_FULL, wake=START_WAKE, worked=0, seen=None, lunch=None,
                low=[], finish=None, eve=None, usual=dict(meal='nha', bed=ON_TIME))


def get(s: dict) -> dict | None:
    j = s.get('journey')
    n = j.get('needs') if isinstance(j, dict) else None
    return n if isinstance(n, dict) else None


def ensure(s: dict, day: int | None = None) -> dict:
    """The needs record, created on first use (story mode). `day`: the life day it starts on."""
    j = s['journey']
    n = j.get('needs')
    if not isinstance(n, dict):
        n = j['needs'] = initial(j['life_day'] if day is None else min(day, j['life_day']))
    return n


def word(value: int, words) -> str:
    return next(w for low, w in words if value >= low)


def tone(value: int) -> str:
    return 'good' if value >= 60 else 'mid' if value >= 35 else 'low'


def _spirit(s: dict, n: int) -> int:
    """Move tinh thần (journey.life.spirit) by n, clamped; the change really made."""
    L = s['journey'].get('life')
    if not n or not isinstance(L, dict) or type(L.get('spirit')) is not int:
        return 0
    before = L['spirit']
    L['spirit'] = max(0, min(100, before + n))
    return L['spirit'] - before


def _where(s: dict) -> str:
    """'attic' | 'dorm' | 'rent' | 'own' (own and a spouse's home cook the same)."""
    place, kind = hs.where(hs.get(s))
    if place in ('own', 'shared'):
        return 'own'
    if place == 'rent':
        return 'dorm' if kind == hs.DORM else 'rent'
    return 'attic'


def _spouse(s: dict) -> str | None:
    m = s.get('marriage')
    sp = m.get('spouse') if isinstance(m, dict) else None
    if isinstance(sp, dict) and sp.get('status') == 'married' and isinstance(sp.get('name'), str) and sp['name']:
        return sp['name'][:24]
    return None


def _cook(s: dict) -> bool:
    c = (s.get('careers') or {}).get('homemaker')
    return isinstance(c, dict) and int((c.get('metrics') or {}).get('served', 0) or 0) >= COOK_SKILL


def hm(minute: int) -> str:
    return dc.hm(minute)


def sleep_wake(bed: int) -> int:
    """Tomorrow morning's tỉnh táo for a bedtime (minutes after midnight of the evening's day, 25*60 = 01:00)."""
    mins = WAKE_AT + 24 * 60 - int(bed)
    return _clamp(24 + 9 * max(0, mins) // 60)


def _drain(n: dict, minutes: int) -> None:
    before, after = n['worked'], n['worked'] + minutes
    n['full'] = _clamp(n['full'] - (after * FULL_PER_HOUR // 60 - before * FULL_PER_HOUR // 60))
    n['wake'] = _clamp(n['wake'] - (after * WAKE_PER_HOUR // 60 - before * WAKE_PER_HOUR // 60))
    n['worked'] = min(after, 2 * dc.DAY_MIN)


def _eat_lunch(s: dict, n: dict, mid: str) -> int:
    x = LUNCH[mid]
    n['lunch'] = mid
    n['full'] = _clamp(n['full'] + x['full'])
    n['wake'] = _clamp(n['wake'] + x['wake'])
    return _spirit(s, x['spirit'])


def _lows(s: dict, n: dict, result: dict) -> None:
    """A bar that just went under LOW: −1 tinh thần and a line from the character, once a day per bar."""
    for key, value, say, tip in (('full', n['full'], SAY_HUNGRY, 'Nhớ ăn uống đàng hoàng nhé.'),
                                 ('wake', n['wake'], SAY_SLEEPY, 'Tối nay ngủ sớm chút nhé.')):
        if value < LOW and key not in n['low']:
            n['low'].append(key)
            got = _spirit(s, -1)
            icon = '🍚' if key == 'full' else '😴'
            result.setdefault('effects', []).append(f'{icon} {say}' + (f' Tinh thần −{-got}.' if got else '') + f' {tip}')
            result['needs_say'] = say


# ---------------------------------------------------------------- the evening's options
def ready_at(n: dict, meal_minutes: int) -> int:
    """When dinner is over: today's closing time + the meal (after midnight counts on: 01:00 = 25*60)."""
    finish = n['finish'] if isinstance(n.get('finish'), int) else 19 * 60
    return finish + int(meal_minutes)


def meals(s: dict) -> list[dict]:
    """Tonight's dinners: [{id, emoji, name, price, full, minutes, spirit, note, ok, why}] (the free one first)."""
    j = s['journey']
    home = HOME_MEAL[_where(s)]
    cook = _where(s) in ('rent', 'own') and _cook(s)
    rows = [dict(id='nha', emoji=home['emoji'], name=home['name'], price=0, full=home['full'], minutes=home['minutes'],
                 spirit=1 if cook else 0, note=home['note'] + (' · tay nghề nội trợ' if cook else ''))]
    spouse = _spouse(s)
    for mid, x in EVE.items():
        if mid == 'vo_chong':
            if not spouse:
                continue
            rows.append(dict(x, id=mid, name=x['name'].format(spouse=spouse)))
        else:
            rows.append(dict(x, id=mid))
    wallet = int(j.get('wallet', 0))
    for r in rows:
        r['ok'] = r['price'] <= 0 or wallet >= r['price']
        r['why'] = None if r['ok'] else f'Ví còn {max(0, wallet)} xu'
    return rows


def beds(n: dict, minutes: int) -> list[dict]:
    """Bedtimes possible after a dinner of `minutes`: the usual four from when dinner is over (at least one)."""
    ready = ready_at(n, minutes)
    times = [b for b in BEDS if b >= ready]
    if not times:
        times = [min(BED_MAX, -(-ready // 30) * 30)]
    return [_bed_row(b) for b in times]


def _bed_row(b: int, ok: bool = True) -> dict:
    return dict(bed=b, time=hm(b), text=BED_TEXT.get(b, 'Dọn dẹp rồi ngủ'), wake=sleep_wake(b), ok=ok,
                spirit=1 if b <= ON_TIME or b >= OWL else 0, when='morning' if b <= ON_TIME else 'tonight' if b >= OWL else '')


def bed_rows(n: dict, minutes: int) -> list[dict]:
    """For the evening sheet: the usual four bedtimes (ok=False before dinner is over), then any later fallback."""
    can = {r['bed'] for r in beds(n, minutes)}
    return [_bed_row(b, b in can) for b in BEDS] + [_bed_row(b) for b in sorted(can - set(BEDS))]


def _default(s: dict, n: dict, free: bool = False) -> tuple[str, int]:
    """"Như mọi khi": the last choice when it is still possible tonight, else the free dinner and 23:00 (or the
    first bedtime after it). `free`: taken without a tap (the morning), so never a paid meal."""
    rows = {r['id']: r for r in meals(s)}
    u = n.get('usual') or {}
    meal = u.get('meal') if u.get('meal') in rows and rows[u['meal']]['ok'] and not (free and rows[u['meal']]['price']) else 'nha'
    times = [b['bed'] for b in beds(n, rows[meal]['minutes'])]
    bed = u.get('bed') if u.get('bed') in times else next((b for b in times if b >= ON_TIME), times[-1])
    return meal, bed


def _apply_eve(s: dict, n: dict, meal: str, bed: int, auto: bool = False) -> list[str]:
    """Eat tonight's dinner and set the bedtime (the morning reads it). Money only for a chosen paid meal."""
    jr = _jr()
    j = s['journey']
    row = next(r for r in meals(s) if r['id'] == meal)
    lines = []
    if row['price'] > 0:
        jr._wallet(j, -row['price'], 'living', f'Ăn tối: {row["name"]}'[:120])
    n['full'] = _clamp(n['full'] + row['full'])
    sp = row['spirit'] + (1 if bed >= OWL else 0)
    got = _spirit(s, sp)
    n['eve'] = dict(meal=meal, bed=int(bed))
    if not auto:   # a habit is what you chose, not what was taken for you
        n['usual'] = dict(meal=meal, bed=int(bed))
    if auto:
        line = f'{row["emoji"]} Tối qua: {row["name"]}, ngủ lúc {hm(bed)}.'
    else:
        line = f'{row["emoji"]} Tối nay: {row["name"]}, ngủ lúc {hm(bed)}. Sáng mai tỉnh táo {sleep_wake(bed)}.'
    lines.append(line + (f' Tinh thần +{got}.' if got else ''))
    return lines


def _morning(s: dict, n: dict, career: str | None, result: dict) -> None:
    """A new life day's first career action: tonight's choice (or the usual), the night, breakfast, the alarm."""
    j = s['journey']
    lines = []
    if n['day'] < j['life_day']:
        if not n['eve']:
            meal, bed = _default(s, n, free=True)
            lines += _apply_eve(s, n, meal, bed, auto=True)
        bed = n['eve']['bed']
        n['full'] = _clamp(max(0, n['full'] - NIGHT_FULL) + BREAKFAST)
        n['wake'] = sleep_wake(bed)
        rested = _spirit(s, 1) if bed <= ON_TIME else 0
        n.update(day=j['life_day'], worked=0, seen=None, lunch=None, low=[], finish=None, eve=None)
        note = '☕ Ăn sáng xong' + (', ngủ đủ giấc' if bed <= ON_TIME else '') + f'. No bụng {n["full"]}, tỉnh táo {n["wake"]}.'
        if rested:
            note += f' Tinh thần +{rested}.'
        elif n['wake'] < 75:
            note += ' Hôm nay dễ mỏi, nhớ nghỉ tay chút.'
        lines.append(note)
    c = (s.get('careers') or {}).get(career) if career else None
    if c is not None and n['lunch'] is None and dc.hours(c, career)[0] >= LATE_START:
        n['lunch'] = 'nha'
        n['full'] = _clamp(n['full'] + HOME_LUNCH)
    if lines:
        result.setdefault('effects', []).extend(lines)


def _clock(s: dict, n: dict, career: str, result: dict) -> None:
    """Count the shop minutes since the last reading; the packed lunch when the lunch hour passed unchosen."""
    c = s['careers'][career]
    m = dc.minute_now(c, career)
    if m is None:
        return
    key = [career, int(c['day'])]
    seen = n['seen']
    if seen and seen[:2] == key and m > seen[2]:
        before = seen[2]
        _drain(n, min(STEP_CAP, m - before))
        if n['lunch'] is None and before < LUNCH_UNTIL <= m:
            got = _eat_lunch(s, n, AUTO_LUNCH)
            result.setdefault('effects', []).append(f'🍱 Tranh thủ ăn hộp cơm mang theo. No bụng {n["full"]}.' + (f' Tinh thần +{got}.' if got else ''))
    if not seen or seen[:2] != key or m >= seen[2]:
        n['seen'] = key + [int(m)]
    _lows(s, n, result)


def _close(s: dict, n: dict, career: str, result: dict) -> None:
    """end_day: the minutes up to closing, the lunch if it never came, the day's "ăn đủ bữa"."""
    summary = result.get('summary') if isinstance(result.get('summary'), dict) else {}
    finish = None
    try:
        hh, mm = str((summary.get('clock') or {}).get('finish') or '').split(':')
        finish = int(hh) * 60 + int(mm)
    except (ValueError, TypeError):
        finish = None
    seen = n['seen']
    c = s['careers'][career]
    if finish is not None and seen and seen[0] == career and seen[1] == int(c['day']) - 1 and finish > seen[2]:
        before = seen[2]
        _drain(n, min(STEP_CAP, finish - before))
        if n['lunch'] is None and before < LUNCH_UNTIL <= finish:
            _eat_lunch(s, n, AUTO_LUNCH)
        _lows(s, n, result)
    if finish is None:
        finish = seen[2] if seen else 19 * 60
    n['finish'] = int(finish)
    n['seen'] = None
    lunch_ok = n['lunch'] in ATE or (n['lunch'] is None and finish < LUNCH_UNTIL)
    if lunch_ok and 'full' not in n['low'] and n['full'] >= FED:
        got = _spirit(s, 1)
        if got:
            result.setdefault('effects', []).append(f'🍚 Hôm nay ăn đủ bữa. Tinh thần +{got}.')


# ---------------------------------------------------------------- engine hook
def after(s: dict, career: str | None, action: str, result: dict) -> None:
    """After every career action (engine._apply_action, after life's daily turn)."""
    if not _story(s) or career not in (s.get('careers') or {}):
        return
    j = s['journey']
    if action == 'end_day':
        n = ensure(s, j['life_day'] - 1)
        if n['day'] < j['life_day']:
            _close(s, n, career, result)
        return
    n = ensure(s)
    c = s['careers'][career]
    if n['day'] < j['life_day'] and (action == 'start_day' or c.get('open')):
        _morning(s, n, career, result)
    elif action == 'start_day':
        _morning(s, n, career, result)   # a late shift's lunch at home (the first morning of this layer)
    if c.get('open') and n['day'] == j['life_day']:
        _clock(s, n, career, result)


# ---------------------------------------------------------------- commands
COMMANDS = ('jr_needs_lunch', 'jr_needs_eve')


def _snack_why(j: dict, n: dict, x: dict) -> str:
    """Why this snack cannot be bought now ('' = it can)."""
    if x['full'] and n['full'] >= FULL_CAP:
        return 'Bụng no rồi'
    if not x['full'] and n['wake'] >= WAKE_CAP:
        return 'Đang tỉnh rồi'
    if int(j.get('wallet', 0)) < x['price']:
        return 'Chưa đủ xu'
    return ''


def _lunch_due(s: dict, n: dict, career: str | None) -> int | None:
    """The shop minute when lunch can be chosen now (None: not now)."""
    j = s['journey']
    if n['day'] != j['life_day'] or n['lunch'] is not None or career not in (s.get('careers') or {}):
        return None
    m = dc.minute_now(s['careers'][career], career)
    return m if m is not None and LUNCH_FROM <= m else None


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(_story(s), 'Ăn uống và giấc ngủ chỉ có trong hành trình.', 'locked')
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    j = s['journey']
    n = ensure(s)
    result = dict(message='', effects=[])
    if name == 'jr_needs_lunch':
        need(set(p) == {'meal'} and p['meal'] in LUNCH, 'Chọn một món cho bữa trưa nhé.')
        meal = p['meal']
        if n['day'] == j['life_day'] and n['lunch'] == meal:
            result['message'] = 'Bạn ăn trưa rồi.'
            return result
        need(n['day'] == j['life_day'] and n['lunch'] is None, 'Hôm nay ăn trưa rồi.', 'already_done')
        need(_lunch_due(s, n, s.get('current')) is not None, 'Chưa tới giờ ăn trưa. Từ 11:30 trên đồng hồ nơi làm nhé.', 'not_now')
        x = LUNCH[meal]
        if x['price']:
            need(j['wallet'] >= x['price'], f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {x["price"]} xu. Ăn cơm hộp mang theo nhé.', 'not_enough')
            _jr()._wallet(j, -x['price'], 'living', f'Ăn trưa: {x["name"]}'[:120])
        got = _eat_lunch(s, n, meal)
        if meal == 'nhin':
            result['message'] = '🙅 Bạn nhịn, làm tiếp. Chiều nay chắc bụng réo đó.'
        else:
            result['message'] = f'{x["emoji"]} Ăn trưa: {x["name"]}' + (f' ({x["price"]} xu)' if x['price'] else '') + f'. No bụng {n["full"]}' \
                + (f', tỉnh táo {n["wake"]}' if x['wake'] else '') + '.' + (f' Tinh thần +{got}.' if got else '')
    elif name == 'jr_needs_snack':
        need(set(p) == {'item'} and p['item'] in SNACK, 'Chọn một món nhé.')
        need(n['day'] == j['life_day'], 'Tối rồi, chọn bữa tối nhé.', 'not_now')
        x = SNACK[p['item']]
        why = _snack_why(j, n, x)
        need(why != 'Bụng no rồi', 'Bụng no rồi, ăn nữa là căng bụng đó.', 'too_full')
        need(why != 'Đang tỉnh rồi', 'Đang tỉnh rồi, uống nữa tối khó ngủ đó.', 'too_full')
        need(not why, f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {x["price"]} xu.', 'not_enough')
        _jr()._wallet(j, -x['price'], 'living', f'Ăn thêm: {x["name"]}'[:120])
        n['full'] = _clamp(n['full'] + x['full'])
        n['wake'] = _clamp(n['wake'] + x['wake'])
        gain = f'No bụng {n["full"]}.' if x['full'] else f'Tỉnh táo {n["wake"]}.'
        result['message'] = f'{x["emoji"]} Ăn thêm: {x["name"]} ({x["price"]} xu). {gain}'
    elif name == 'jr_needs_eve':
        need(set(p) == {'meal', 'bed'} and p['meal'] in EVE_IDS and type(p['bed']) is int, 'Chọn bữa tối và giờ đi ngủ nhé.')
        meal, bed = p['meal'], p['bed']
        need(n['day'] < j['life_day'], 'Tối nay chưa tới. Khép ca xong rồi chọn nhé.', 'not_now')
        if n['eve']:
            need(n['eve'] == dict(meal=meal, bed=bed), 'Tối nay chọn rồi. Mai lại chọn nhé.', 'already_done')
            result['message'] = f'Ngủ ngon nhé. Sáng mai tỉnh táo {sleep_wake(bed)}.'
            return result
        rows = {r['id']: r for r in meals(s)}
        need(meal in rows, 'Món này tối nay không có.')
        need(rows[meal]['ok'], f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {rows[meal]["price"]} xu. Chọn bữa ở nhà nhé.', 'not_enough')
        need(bed in [b['bed'] for b in beds(n, rows[meal]['minutes'])], 'Giờ ngủ này không được: ăn xong mới tới giờ đó.')
        lines = _apply_eve(s, n, meal, bed)
        result['message'] = lines[0]
    else:
        raise e.GameError('Thao tác không hợp lệ.', 'unknown_action')
    return result


# ---------------------------------------------------------------- view
def _bar(value: int, words) -> dict:
    return dict(value=value, label=word(value, words), tone=tone(value))


def public(s: dict, focus: str | None = None) -> dict:
    if not _story(s):
        return dict(enabled=False)
    j = s['journey']
    n = get(s) or initial(j['life_day'])
    v = dict(enabled=True, full=_bar(n['full'], FULL_WORDS), wake=_bar(n['wake'], WAKE_WORDS), low=list(n['low']),
             lunch=None, today=n['lunch'] if n['day'] == j['life_day'] else None, evening=None, snack=None)
    if n['day'] == j['life_day']:
        v['snack'] = [dict(id=k, emoji=x['emoji'], name=x['name'], short=x['short'], price=x['price'], full=x['full'],
                           wake=x['wake'], why=_snack_why(j, n, x), ok=not _snack_why(j, n, x)) for k, x in SNACK.items()]
    m = _lunch_due(s, n, focus or s.get('current'))
    if m is not None:
        wallet = int(j.get('wallet', 0))
        v['lunch'] = dict(time=hm(m), until=hm(LUNCH_UNTIL), choices=[
            dict(id=k, emoji=x['emoji'], name=x['name'], short=x['short'], price=x['price'], full=x['full'], wake=x['wake'], spirit=x['spirit'],
                 note=x['note'], ok=x['price'] <= 0 or wallet >= x['price']) for k, x in LUNCH.items()])
    if n['day'] < j['life_day']:
        rows = meals(s)
        meal, bed = _default(s, n)
        usual = next(r for r in rows if r['id'] == meal)
        v['evening'] = dict(
            finish=hm(n['finish']) if isinstance(n['finish'], int) else None, life_day=j['life_day'],
            meals=[dict(r, beds=bed_rows(n, r['minutes'])) for r in rows],
            usual=dict(meal=meal, bed=bed, time=hm(bed), name=usual['name'], emoji=usual['emoji'], price=usual['price']),
            chosen=dict(n['eve'], time=hm(n['eve']['bed']), wake=sleep_wake(n['eve']['bed']),
                        name=next((r['name'] for r in rows if r['id'] == n['eve']['meal']), ''),
                        emoji=next((r['emoji'] for r in rows if r['id'] == n['eve']['meal']), '🍽️')) if n['eve'] else None)
    return v


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'needs' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu ăn uống và giấc ngủ không hợp lệ.'
    n = j['needs']
    need(isinstance(n, dict) and set(n) == KEYS and n.get('v') == VERSION, bad, 'invalid_save')
    integer(n['day'], 1, 10**6)
    need(n['day'] <= j['life_day'], bad, 'invalid_save')
    integer(n['full'], 0, 100)
    integer(n['wake'], 0, 100)
    integer(n['worked'], 0, 2 * dc.DAY_MIN)
    seen = n['seen']
    need(seen is None or (isinstance(seen, list) and len(seen) == 3 and seen[0] in (s.get('careers') or {})
                          and type(seen[1]) is int and 1 <= seen[1] <= 10**9 and type(seen[2]) is int and 0 <= seen[2] <= 2 * dc.DAY_MIN), bad)
    need(n['lunch'] is None or n['lunch'] in LUNCH_IDS, bad)
    need(isinstance(n['low'], list) and len(n['low']) == len(set(n['low'])) and set(n['low']) <= {'full', 'wake'}, bad)
    need(n['finish'] is None or (type(n['finish']) is int and 0 <= n['finish'] <= 2 * dc.DAY_MIN), bad)
    for key in ('eve', 'usual'):
        x = n[key]
        if key == 'eve' and x is None:
            continue
        need(isinstance(x, dict) and set(x) == {'meal', 'bed'} and x['meal'] in EVE_IDS and type(x['bed']) is int
             and BED_MIN <= x['bed'] <= BED_MAX, bad)
    need(n['eve'] is None or n['day'] < j['life_day'], bad)
