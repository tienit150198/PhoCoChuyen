"""Khách sạn Sông Mây: a salaried shift that rotates through the hotel's posts.

Lễ tân (check-in), Buồng phòng (a checked-out room), Giặt là (sheets and towels from several rooms), Bữa sáng
(the breakfast list), Bảo trì (a room report) and Trang trí (seasonal or year-round decoration). Every task is a
few concrete steps graded on the server; a wrong step stays open to fix in place and lowers the quality (and so
the small bonus). Pay is the employment contract's salary at closing, as at the post office.

Seasons follow the real Vietnam date (UTC+7, season_of): Valentine, Tết, Noel. A task taken in season carries
`season`: a decoration task then becomes the season's lobby brief (decor_brief, a pure function of day, slot and
season, so a save still validates on any later date), its bonus is x1.5 and the day opens with one more guest.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json

from . import kit
from . import hotel_content as hc
from .. import consequences as cq

ID = 'hotel'
GEN = 1
PEOPLE = hc.PEOPLE
KINDS = hc.KINDS
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('ht_step',)
FREE = ('ht_intro',)
NO_TICK = ('ht_intro', 'ht_desk')
SEASON_IDS = ('none',) + tuple(hc.SEASONS)
VN = timezone(timedelta(hours=7))
TYPES = ('choice', 'number', 'order', 'multi', 'counts')


# ---------------------------------------------------------------- seasons (pure, real Vietnam date)
def season_of(d: date) -> str | None:
    """The hotel's season on the Vietnam calendar date `d`: 'valentine', 'tet', 'noel' or None."""
    tet = any(t and t - hc.TET_BEFORE <= d <= t + hc.TET_AFTER for t in (hc.TET.get(d.year), hc.TET.get(d.year + 1)))
    valentine = d.month == 2 and 1 <= d.day <= 14
    if valentine and (not tet or d.day == 14):
        return 'valentine'
    if tet:
        return 'tet'
    if d.month == 12 and d.day <= 25:
        return 'noel'
    return None


def today_vn() -> date:
    return datetime.fromtimestamp(kit.now(), VN).date()


def season_now() -> str:
    return season_of(today_vn()) or 'none'


def season_view(sid: str | None = None) -> dict | None:
    sid = season_now() if sid is None else sid
    if sid not in hc.SEASONS:
        return None
    label, emoji, note = hc.SEASONS[sid]
    return dict(id=sid, label=label, emoji=emoji, note=note, bonus=hc.SEASON_BONUS)


# ---------------------------------------------------------------- task building
def _opts(r, rows, shuffle=True):
    out = [dict(id=k, label=v) for k, v in rows]
    if shuffle:
        r.shuffle(out)
    return out


def _step(kind, name, typ, title, evidence, options=None, fields=None, unit=''):
    st = dict(id=f'{kind}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if fields is not None:
        st['fields'] = fields
    if unit:
        st['unit'] = unit
    return st


def _swap_code(code: str, i: int) -> str:
    d = list(code)
    d[i], d[i + 1] = d[i + 1], d[i]
    return ''.join(d)


def _checkin(r, day, slot):
    req_id, req_text, test = hc.REQUESTS[r.randrange(len(hc.REQUESTS))]
    match = [room for room in hc.ROOMS if test(room)]
    target = r.choice(match)
    board = []
    for room in hc.ROOMS:
        if room is target:
            status = 'clean'
        elif room in match:
            status = r.choice(('dirty', 'occupied', 'maintenance'))
        else:
            status = r.choice(('clean', 'clean', 'occupied', 'occupied', 'dirty'))
        board.append(dict(no=room[0], floor=int(room[0][0]), bed=room[1], view=room[2], spot=room[3], access=room[4], status=status))
    names = hc.NAMES[r.randrange(len(hc.NAMES))]
    digits = r.sample('123456789', 4)
    code = ''.join(digits)
    other = _swap_code(code, 1)
    third = _swap_code(code, 2)
    guests = 4 if req_id in ('family', 'river_family') else 2 if req_id in ('access', 'lift_double') else r.choice((1, 2))
    nights = r.randint(1, 3)
    breakfast = r.random() < 0.75
    rows = [(names[0], code, guests, True), (names[1], code, r.choice((1, 2, 3)), False),
            (names[0], other, r.choice((1, 2, 4)), False), (names[2], third, r.choice((1, 2)), False)]
    r.shuffle(rows)
    bookings, answer = [], None
    for i, (name, c, g, real) in enumerate(rows):
        bid = f'b{i + 1}'
        bookings.append(dict(id=bid, name=name, code=f'SM-{c}', guests=g, nights=nights if real else r.randint(1, 3)))
        if real:
            answer = bid
    paper = r.choice(('match', 'match', 'update', 'confirm'))
    present = guests + 1 if paper == 'update' else guests
    id_name = r.choice(hc.BOOKERS) if paper == 'confirm' else names[0]
    cards = 1 if present == 1 else 2
    no = target[0]
    alt = no[::-1] if no[0] != no[2] else no[0] + '0' + str(5 - int(no[2]))   # 203 -> 302, 303 -> 302: a look-alike key
    tomorrow = hc.WEEKDAYS[day % 7]
    bf = 'none' if not breakfast else 'we' if day % 7 in (5, 6) else 'wk'
    said = f'{names[0]}, mã đặt SM-{code}'
    who = {'confirm': f'Người ra quầy nhận phòng hộ, giấy tờ ghi: {id_name}.', 'update': f'Giấy tờ: {id_name}. Đi cùng thêm một người chưa có trên phiếu.',
           'match': f'Giấy tờ: {id_name}.'}[paper]
    steps = [
        _step('checkin', 'booking', 'choice', 'Tìm đúng phiếu đặt phòng', f'Khách nói: “{said}.” Tìm phiếu khớp cả họ tên lẫn mã đặt.',
              [dict(id=b['id'], label=f'{b["name"]} · {b["code"]} · {b["guests"]} khách · {b["nights"]} đêm') for b in bookings]),
        _step('checkin', 'papers', 'choice', 'Đối chiếu giấy tờ với phiếu', f'{who} Số người tại quầy: {present}. Phiếu: {names[0]}, {guests} khách.',
              _opts(r, [('match', 'Khớp tên và số khách: nhận phòng'), ('update', 'Cập nhật số khách lên phiếu, báo phụ thu giường phụ'),
                        ('confirm', 'Gọi người đặt xác nhận người nhận phòng hộ'), ('refuse', 'Từ chối nhận phòng')])),
        _step('checkin', 'room', 'choice', 'Chọn phòng trên bảng phòng', f'Yêu cầu: {req_text} Chỉ giao phòng “{hc.STATUS["clean"]}”.',
              [dict(id=b['no'], label=f'Phòng {b["no"]}') for b in board]),
        _step('checkin', 'key', 'choice', 'Giao thẻ phòng', f'Khách nhận phòng: {present} người. 1 khách 1 thẻ, từ 2 khách giao 2 thẻ.',
              _opts(r, [(f'{target[0]}-1', f'Thẻ phòng {target[0]} · 1 thẻ'), (f'{target[0]}-2', f'Thẻ phòng {target[0]} · 2 thẻ'),
                        (f'{alt}-{cards}', f'Thẻ phòng {alt} · {cards} thẻ')])),
        _step('checkin', 'breakfast', 'choice', 'Dặn giờ ăn sáng', f'Sáng mai là {tomorrow}. {"Phiếu có kèm bữa sáng." if breakfast else "Phiếu không kèm bữa sáng."}',
              _opts(r, hc.BREAKFAST)),
    ]
    key = {'checkin.booking': answer, 'checkin.papers': paper, 'checkin.room': target[0], 'checkin.key': f'{target[0]}-{cards}', 'checkin.breakfast': bf}
    needs = dict(request=req_text, said=said, board=board, bookings=bookings, id_name=id_name, present=present,
                 breakfast=breakfast, tomorrow=tomorrow, steps=steps)
    npc = (3, 4, 5, 6)[(day + slot) % 4]
    return needs, key, 'Khách tới quầy nhận phòng', f'{said}. Mình đặt phòng rồi, nhờ bạn làm thủ tục giúp.', npc


def _housekeeping(r, day, slot):
    room = r.choice(hc.ROOMS)
    no, bed = room[0], room[1]
    cap = hc.CAPACITY[bed]
    start = dict(water=2, soda=2, beer0=2, snack=2, noodle=1)
    left = {k: r.randint(0, n) for k, n in start.items()}
    bill = sum((start[k] - left[k]) * price for k, _, price in hc.MINIBAR)
    lost = r.choice(hc.LOST[:1] * 3 + hc.LOST[1:])
    issue = r.choice(hc.ISSUES)
    order = [k for k, _ in hc.HK_ORDER]
    mini = '; '.join(f'{label}{" (miễn phí)" if price == 0 else f" {price} xu"}: {start[k]} → còn {left[k]}' for k, label, price in hc.MINIBAR)
    steps = [
        _step('housekeeping', 'order', 'order', 'Sắp thứ tự dọn phòng trả', f'Phòng {no} vừa trả. Bấm các việc theo đúng thứ tự trong sổ buồng phòng.',
              _opts(r, hc.HK_ORDER)),
        _step('housekeeping', 'linen', 'choice', 'Thay ga, áo gối', f'Phòng {no}: {hc.BEDS[bed]}.', _opts(r, hc.LINEN)),
        _step('housekeeping', 'bath', 'choice', 'Vệ sinh phòng tắm', 'Khăn ướt vứt trên sàn, gương mờ hơi nước, bồn cầu chưa xả.', _opts(r, hc.BATH)),
        _step('housekeeping', 'amenity', 'choice', 'Bổ sung tiện nghi', f'{hc.BEDS[bed]} · sức chứa {cap} khách. Mỗi khách một bộ.', _opts(r, hc.AMENITY)),
        _step('housekeeping', 'minibar', 'number', 'Kiểm minibar, ghi tiền khách đã dùng', f'{mini}.', unit='xu'),
        _step('housekeeping', 'lost', 'choice', 'Kiểm đồ khách để quên', f'Kiểm gầm giường, ngăn kéo, sau cửa: {lost[1]}.', _opts(r, hc.LOST_OPTIONS)),
        _step('housekeeping', 'report', 'choice', 'Báo lễ tân', issue[1] or 'Mọi thiết bị trong phòng hoạt động bình thường.', _opts(r, hc.REPORT)),
    ]
    key = {'housekeeping.order': order, 'housekeeping.linen': hc.LINEN_OF[bed], 'housekeeping.bath': 'top',
           'housekeeping.amenity': str(cap), 'housekeeping.minibar': bill, 'housekeeping.lost': lost[2],
           'housekeeping.report': 'maint' if issue[0] else 'ready'}
    needs = dict(room=no, bed=bed, capacity=cap, minibar=[dict(id=k, label=label, price=price, start=start[k], left=left[k]) for k, label, price in hc.MINIBAR],
                 found=lost[1], issue=issue[1], steps=steps)
    return needs, key, f'Dọn phòng {no} vừa trả', f'Phòng {no} vừa trả. Cô Tư dặn: làm đủ bước, đúng thứ tự, phòng sạch mới báo lễ tân.', 2


def _laundry(r, day, slot):
    load = 'linen' if (day + slot) % 2 else 'towel'
    title, types, program = hc.LOADS[load]
    rooms = r.sample(hc.ROOMS, 3)
    lo = dict(sheet=1, case=2, towel=2, mat=1)
    hi = dict(sheet=2, case=4, towel=4, mat=2)
    slip = {room[0]: {k: r.randint(lo[k], hi[k]) for k, _ in types} for room in rooms}
    bag = deepcopy(slip)
    if r.random() < 0.6:
        no, (k, _) = r.choice([x[0] for x in rooms]), r.choice(types)
        bag[no][k] = max(0, bag[no][k] + r.choice((-1, 1)))
    total = {k: sum(bag[no][k] for no in bag) for k, _ in types}
    slip_total = {k: sum(slip[no][k] for no in slip) for k, _ in types}
    diff = sum(total.values()) - sum(slip_total.values())
    verdict = 'match' if diff == 0 else 'short' if diff < 0 else 'over'
    items = []
    pool = [(no, k, label) for no in bag for k, label in types if bag[no][k] > 0]
    picks = r.sample(pool, min(6, len(pool)))
    stains = [r.choice(hc.STAINS) for _ in picks]
    if not any(s[2] for s in stains):
        stains[0] = hc.STAINS[0]
    if all(s[2] for s in stains):
        stains[-1] = hc.STAINS[4]
    for i, ((no, k, label), stain) in enumerate(zip(picks, stains)):
        items.append(dict(id=f'i{i + 1}', label=f'{label} phòng {no}: {stain[1]}', stained=stain[2]))
    rows = '; '.join(f'phòng {no}: ' + ', '.join(f'{bag[no][k]} {label.lower()}' for k, label in types) for no in bag)
    slips = '; '.join(f'phòng {no}: ' + ', '.join(f'{slip[no][k]} {label.lower()}' for k, label in types) for no in slip)
    steps = [
        _step('laundry', 'tally', 'counts', 'Đếm thực tế từng loại', f'Trong túi: {rows}. Ghi tổng số đếm được, không chép phiếu.',
              fields=[dict(id=k, label=label) for k, label in types]),
        _step('laundry', 'slip', 'choice', 'Đối chiếu với phiếu giao', f'Phiếu buồng phòng ghi: {slips}.',
              _opts(r, [('match', 'Khớp phiếu'), ('short', 'Thiếu so với phiếu: ghi chênh lệch, báo buồng phòng'),
                        ('over', 'Dư so với phiếu: ghi chênh lệch, báo buồng phòng'), ('fix', 'Sửa phiếu cho khớp, không ghi chú')])),
        _step('laundry', 'stain', 'multi', 'Tách đồ cần xử lý vết bẩn trước', 'Chọn mọi món có vết bẩn (đồ chỉ nhàu hoặc hơi ẩm thì giặt thường).',
              [dict(id=x['id'], label=x['label']) for x in items]),
        _step('laundry', 'program', 'choice', 'Chọn chương trình giặt', f'{title}: {", ".join(label.lower() for _, label in types)}.', _opts(r, hc.PROGRAMS)),
    ]
    key = {'laundry.tally': total, 'laundry.slip': verdict, 'laundry.stain': sorted(x['id'] for x in items if x['stained']),
           'laundry.program': program}
    needs = dict(load=load, load_title=title, types=[dict(id=k, label=label) for k, label in types],
                 rooms=[dict(no=no, slip=slip[no], bag=bag[no]) for no in bag], items=[dict(id=x['id'], label=x['label']) for x in items], steps=steps)
    return needs, key, title + ' từ ba phòng', f'{title} từ ba phòng vừa xuống. Đếm thực tế, tách đồ bẩn, chọn đúng chương trình.', 2


def _breakfast(r, day, slot):
    rooms = [x[0] for x in r.sample(hc.ROOMS, 4)]
    note = r.choice(('peanut', 'peanut_adult', 'seafood', 'veg'))
    tour = rooms[3]
    plan = {}
    safe = dict(peanut=('pho', 'banhmi', 'haisan'), peanut_adult=('pho', 'banhmi', 'haisan', 'chay'),
                seafood=('pho', 'banhmi', 'xoi', 'chay'), veg=('chay',))
    # the conflict room: one guest whose pre-order breaks the note
    label, bad, swap = hc.NOTES[note]
    guests = []
    if note == 'peanut':
        guests = [dict(who='Người lớn', dish=r.choice(safe['peanut'])), dict(who='Bé 5 tuổi', dish=bad)]
    else:
        guests = [dict(who='Người lớn', dish=bad)] + ([dict(who='Người lớn', dish=r.choice(('pho', 'banhmi', 'chay')) if note != 'veg' else 'chay')] if r.random() < 0.5 else [])
    plan[rooms[0]] = dict(notes=[note], guests=guests)
    # a second allergy room with a safe order (gets a card, no swap); always one when the conflict is not an allergy
    extra = 'seafood' if note == 'veg' else r.choice(('seafood', 'peanut_adult', None))
    if extra:
        plan[rooms[1]] = dict(notes=[extra], guests=[dict(who='Người lớn', dish=r.choice(safe[extra])) for _ in range(r.randint(1, 2))])
    else:
        plan[rooms[1]] = dict(notes=[], guests=[dict(who='Người lớn', dish=r.choice(('pho', 'banhmi', 'haisan', 'xoi'))) for _ in range(r.randint(1, 2))])
    kid = r.random() < 0.5
    g2 = [dict(who='Người lớn', dish=r.choice(('pho', 'banhmi', 'haisan', 'xoi'))) for _ in range(r.randint(1, 2))]
    if kid:
        g2.append(dict(who='Bé 4 tuổi', dish='chao'))
    plan[rooms[2]] = dict(notes=[], guests=g2)
    boxes = r.randint(1, 2)
    plan[tour] = dict(notes=['tour'], guests=[dict(who='Người lớn', dish=r.choice(('pho', 'banhmi'))) for _ in range(boxes)])
    kitchen = {k: 0 for k, _ in hc.DISHES}
    for no in rooms[:3]:
        for g in plan[no]['guests']:
            dish = swap if (no == rooms[0] and g['dish'] == bad) else g['dish']
            kitchen[dish] += 1
    cards = sorted(no for no in rooms[:3] if any(n in ('peanut', 'peanut_adult', 'seafood') for n in plan[no]['notes']))
    dish_name = dict(hc.DISHES)
    order = list(rooms)
    r.shuffle(order)
    listing = []
    for no in order:
        p = plan[no]
        notes = ['Đi tour sớm 5:30' if n == 'tour' else hc.NOTES[n][0] for n in p['notes']]
        listing.append(dict(no=no, notes=notes, guests=[dict(who=g['who'], dish=g['dish'], label=dish_name[g['dish']]) for g in p['guests']]))
    swap_opts = [('chao', 'Đổi sang cháo gà suất nhỏ'), ('banhmi', 'Đổi sang bánh mì ốp la'), ('pho', 'Đổi sang phở bò'),
                 ('chay', 'Đổi sang bún chay'), ('keep', 'Giữ nguyên món, dặn ăn ít thôi')]
    steps = [
        _step('breakfast', 'swap', 'choice', 'Sửa món trái lưu ý', f'Phòng {rooms[0]}: {label.lower()}, nhưng phiếu chọn {dish_name[bad].lower()}.', _opts(r, swap_opts)),
        _step('breakfast', 'boxes', 'number', 'Đóng hộp ăn sáng mang đi', f'Phòng {tour}: {boxes} khách đi tour sớm 5:30.', unit='hộp'),
        _step('breakfast', 'kitchen', 'counts', 'Báo bếp số suất ăn tại nhà hàng', 'Mỗi khách ăn tại nhà hàng một suất, đã sửa món trái lưu ý; khách đi tour không tính.',
              fields=[dict(id=k, label=v) for k, v in hc.DISHES]),
        _step('breakfast', 'cards', 'multi', 'Đặt thẻ dị ứng lên bàn', 'Chọn các phòng ăn tại nhà hàng có người dị ứng (ăn chay không phải dị ứng).',
              [dict(id=no, label=f'Phòng {no}') for no in sorted(rooms[:3])]),
    ]
    key = {'breakfast.swap': swap, 'breakfast.boxes': boxes, 'breakfast.kitchen': kitchen, 'breakfast.cards': cards}
    needs = dict(rooms=listing, steps=steps)
    npc = 6 if note == 'peanut' else 0
    return needs, key, 'Danh sách bữa sáng ngày mai', 'Danh sách bữa sáng ngày mai đây. Sửa món trái lưu ý, đóng hộp cho khách đi tour, báo bếp đủ suất mà không dư.', npc


def _repair(r, day, slot):
    fid = sorted(hc.FAULTS)[r.randrange(len(hc.FAULTS))]
    symptom, variants, causes, fixes = hc.FAULTS[fid]
    clues, safety, cause, fix, status = r.choice(variants)
    room = r.choice(hc.ROOMS)[0]
    steps = [
        _step('repair', 'safety', 'choice', 'Việc an toàn đầu tiên', f'Phòng {room} báo: {symptom.lower()}. {clues}', _opts(r, hc.SAFETY)),
        _step('repair', 'cause', 'choice', 'Đọc dấu hiệu, chọn nguyên nhân', clues, _opts(r, causes)),
        _step('repair', 'fix', 'choice', 'Sửa hay gọi nhà thầu', 'Việc của tổ bảo trì thì làm; việc quá tay (gas lạnh, bo mạch, tháo bồn, dây điện, đồ của tòa nhà) thì gọi nhà thầu.',
              _opts(r, fixes)),
        _step('repair', 'status', 'choice', 'Báo tình trạng phòng', 'Báo lễ tân để họ xếp khách cho đúng.', _opts(r, hc.STATUS_AFTER)),
    ]
    key = {'repair.safety': safety, 'repair.cause': cause, 'repair.fix': fix, 'repair.status': status}
    needs = dict(room=room, fault=fid, symptom=symptom, clues=clues, steps=steps)
    return needs, key, f'Phòng {room}: {symptom.lower()}', f'Phòng {room} báo {symptom.lower()}. Anh Bảo dặn: an toàn trước, đọc dấu hiệu rồi mới sửa.', 1


def decor_brief(day: int, slot: int, theme: str) -> tuple[dict, list, dict]:
    """The decoration brief of (day, slot) for `theme`: (brief with its steps, steps, answer key). Pure."""
    r = kit.rng(ID, 'decor', day, slot, theme)
    title, emoji, where = hc.THEMES[theme]
    fits = [i for i in hc.ITEMS if theme in i[3]]
    limits = [k for k, (_, cat) in hc.LIMITS.items() if k == 'none' or any(i[4] == cat for i in fits)]
    limit = limits[r.randrange(len(limits))]
    good = [i for i in fits if i[4] != hc.LIMITS[limit][1]]
    cost = sum(i[2] for i in good)
    top = max(i[2] for i in good)
    tight = len(good) > 2 and sum(1 for i in good if i[2] == top) == 1 and r.random() < 0.4
    if tight:   # over budget: the rule drops the single priciest fitting item
        budget = cost - top + r.randint(0, min(3, top - 1))
        good = [i for i in good if i[2] != top]
        cost -= top
    else:
        budget = cost + r.randint(0, 6)
    off = [i for i in hc.ITEMS if theme not in i[3]]
    shown = fits + r.sample(off, 3)
    r.shuffle(shown)
    room = r.choice(hc.ROOMS)[0] if where == 'room' else None
    place = where
    ask = (f'Khách phòng {room} đặt “{title.lower()}”' if room else f'Chị Hằng giao trang trí “{title.lower()}”') + f', ngân sách {budget} xu.'
    steps = [
        _step('decor', 'items', 'multi', 'Chọn đồ trang trí', f'{ask} {hc.LIMITS[limit][0]}',
              [dict(id=i[0], label=f'{i[1]} · {i[2]} xu') for i in shown]),
        _step('decor', 'cost', 'number', 'Cộng tiền đồ đã chọn', f'Ngân sách {budget} xu. Ghi tổng tiền các món đã chọn.', unit='xu'),
        _step('decor', 'place', 'choice', 'Bày ở đâu', 'Đặt đồ trang trí đúng chỗ khách đặt, an toàn cho mọi người.', _opts(r, hc.PLACES)),
    ]
    key = {'decor.items': sorted(i[0] for i in good), 'decor.cost': cost, 'decor.place': place}
    brief = dict(theme=theme, title=title, emoji=emoji, where=where, room=room, budget=budget, limit=hc.LIMITS[limit][0],
                 ask=ask, items=[dict(id=i[0], label=i[1], price=i[2]) for i in shown], steps=steps)
    return brief, steps, key


def _decor(r, day, slot):
    theme = hc.YEAR_ROUND[(day + slot) % len(hc.YEAR_ROUND)]
    brief, _, key = decor_brief(day, slot, theme)
    title = hc.THEMES[theme][0]
    return brief, key, f'Trang trí: {title.lower()}', 'Có yêu cầu trang trí. Chọn đúng đồ hợp dịp, theo lưu ý của khách, trong ngân sách.', 0


BUILD = dict(checkin=_checkin, housekeeping=_housekeeping, laundry=_laundry, breakfast=_breakfast, repair=_repair, decor=_decor)


def kind_of(day: int, slot: int) -> str:
    """The post of (day, slot): the shift rotates through the six posts."""
    return KINDS[(day - 1 + slot) % len(KINDS)]


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = kind_of(day, slot)
    needs, key, title, opening, npc = BUILD[kind](kit.rng(ID, day, slot), day, slot)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, gen=GEN, kind=kind, needs=needs, _key=key,
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work', season='none')


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _active(t: dict) -> tuple[dict, list, dict]:
    """(brief, steps, key) in force: a decoration task taken in season follows the season's brief."""
    if t.get('kind') == 'decor' and t.get('season') in hc.SEASONS:
        return decor_brief(t['day'], _slot(t), t['season'])
    return t['needs'], t['needs']['steps'], t['_key']


def _quality(wrong: int) -> int:
    return max(40, 100 - 12 * wrong)


def _bonus(t: dict) -> int:
    bonus = max(3, round(hc.BONUS[t['kind']] * t['quality'] / 100))
    if t.get('season') in hc.SEASONS:
        bonus = round(bonus * hc.SEASON_BONUS)
    return bonus


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), stats=dict(jobs=0, good=0, active_days=0, bonus=0, seasonal=0, posts={k: 0 for k in KINDS}),
                last_active_day=0, desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


# ---------------------------------------------------------------- actions
def _value(st: dict, value):
    typ = st['type']
    if typ == 'choice':
        return kit.one_of(value, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(value, 0, 10000)
    if typ in ('order', 'multi'):
        ids = [o['id'] for o in st['options']]
        got = kit.id_list(value, ids, len(ids))
        if typ == 'order':
            kit.need(len(got) == len(ids), 'Xếp đủ mọi việc theo thứ tự nhé.')
            return list(got)
        return sorted(got)
    fields = [f['id'] for f in st['fields']]
    kit.need(isinstance(value, dict) and set(value) == set(fields), 'Ghi đủ số cho từng loại nhé.')
    return {k: kit.integer(value[k], 0, 200) for k in fields}


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('ht_intro', 'ht_step', 'ht_desk'), 'Thao tác khách sạn không hợp lệ.')
    d = _data(c)
    if name == 'ht_intro':
        d['intro'] = True
        return dict(message='Chị Hằng đưa bảng phân ca: hôm nay bạn đi đủ các vị trí. Vào việc thôi!')
    desk = d['desk']
    if name == 'ht_desk':
        return kit.desk_choose(s, c, ID, desk, hc.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở quầy, quyết xong rồi làm tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu việc trước khi làm nhé.')
    _, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    if not _same(value, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        again = 'Đếm lại từng món nhé.' if st['id'] == 'laundry.tally' else 'Đọc lại phiếu và sổ quy trình rồi làm lại bước này.'
        message = f'Chưa đúng: {st["title"].lower()}. {again}'
        t['lines'] = (t['lines'] + [message])[-24:]
        result = dict(message=message, correct=False)
        _after(s, c, d, result)
        return result
    t['work'][st['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-24:]
    if t['at'] < len(steps):
        result = dict(message='Đúng rồi. Tiếp: ' + steps[t['at']]['title'].lower() + '.', correct=True)
        _after(s, c, d, result)
        return result
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= 90
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    if good:
        d['stats']['posts'][t['kind']] += 1
    if t.get('season') in hc.SEASONS:
        d['stats']['seasonal'] += 1
    post = hc.POSTS[t['kind']]
    kit.complete(s, c, t, bonus, f'Xong việc {post[0].lower()}: {post[2].lower()}, chất lượng {t["quality"]}%.')
    extra = ' Thưởng mùa lễ ×1.5.' if t.get('season') in hc.SEASONS else ''
    result = dict(message=f'Xong việc {post[0].lower()}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.{extra}', correct=good, celebrate=good)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, hc.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(hc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A task taken in season carries it (decided once, here, by the real Vietnam date)."""
    if t.get('career') == ID and t.get('status') == 'new' and t.get('at') == 0:
        t['season'] = season_now()


def _extra_guest(s: dict, c: dict) -> None:
    """In season the day opens with one more guest, within the engine's own limits."""
    e = kit.eng()
    try:
        from ..promotion import managing
        if managing(s, c, ID):
            return
    except Exception:  # noqa: BLE001 - a manager-shift check never blocks the day
        pass
    active = sum(t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks'])
    slot = e._next_slot(c)
    if active >= e.MORE_ACTIVE or slot >= e.MORE_DAY:
        return
    t = make_task(c['day'], slot, c['turn'])
    c['tasks'].append(t)
    on_task(s, c, t)
    if not c.get('active_task'):
        c['active_task'] = t['id']


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    season = season_now()
    if season != 'none' and c.get('open'):
        _extra_guest(s, c)
    kit.desk_start(s, c, ID, d['desk'], hc.DESK, None, c['life'].get('mode') == 'festival' or season != 'none')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], hc.DESK)
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    lines = [f'Sông Mây: {today["jobs"]} việc xong, {today["good"]} việc đạt từ 90%. Thưởng chất lượng: {today["bonus"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Ngày có việc đạt từ 90% mới ghi vào hành trình nghề.')


def known_request(c: dict, t: dict) -> str:
    post = hc.POSTS[t['kind']]
    return f'{post[1]} {post[0]}: {t["opening"]}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết vị trí hôm nay và yêu cầu của khách.'
    _, steps, _ = _active(t)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Việc đã xong; nhận việc tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Chất lượng phục vụ', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    else:
        brief, _, _ = _active(t)
        v['needs'] = deepcopy(brief)
    post = hc.POSTS[t['kind']]
    v['post'] = dict(id=t['kind'], label=post[0], emoji=post[1], work=post[2])
    v['season_info'] = season_view(t.get('season', 'none'))
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    posts = sum(1 for k in KINDS if stats['posts'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and posts >= m['posts']) for m in hc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, posts=posts)
    d['desk'] = kit.desk_public(d['desk'], hc.DESK, ID, c)
    d['season'] = season_view()
    return d


def content() -> dict:
    return dict(
        notebook=hc.NOTEBOOK,
        posts=[dict(id=k, label=v[0], emoji=v[1], work=v[2]) for k, v in hc.POSTS.items()],
        beds=hc.BEDS, views=hc.VIEWS, spots=hc.SPOTS, status=hc.STATUS,
        seasons=[dict(id=k, label=v[0], emoji=v[1], note=v[2]) for k, v in hc.SEASONS.items()],
        intro=dict(title='Một ca ở Khách sạn Sông Mây',
                   lead='Khách sạn bốn tầng bên sông. Mỗi ca bạn luân phiên lễ tân, buồng phòng, giặt là, bữa sáng, bảo trì và trang trí. '
                        'Bạn nhận lương ca theo hợp đồng và thưởng chất lượng nhỏ; mùa lễ khách đông hơn, thưởng ×1.5.',
                   work=[['🛎️', 'Nhận khách, chọn phòng, giao thẻ'], ['🧹', 'Dọn phòng, giặt chăn gối, sắp bữa sáng'], ['🔧', 'Sửa trong phòng, trang trí theo dịp']],
                   meet=[['🙂', 'Chị Hằng trưởng ca lễ tân'], ['🧰', 'Anh Bảo tổ bảo trì'], ['🧺', 'Cô Tư trưởng buồng phòng']],
                   stars=[['✓', 'Đọc kỹ phiếu, chọn đúng phòng sạch'], ['✓', 'Đếm thực tế, an toàn trước khi sửa']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu khách sạn bị thay đổi: ' + k)
    kit.need(t.get('season') in SEASON_IDS, 'Mùa lễ của phiếu không hợp lệ.')
    _, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu khách sạn sai.')
    kit.need(at == 0 or t['known'], 'Chưa đọc phiếu việc.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    kit.need(all(_same(work[sid], key[sid]) for sid in ids[:at]), 'Kết quả bước khách sạn sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi khách sạn sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi khách sạn sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(t.get('quality') == _quality(wrong), 'Điểm chất lượng khách sạn không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (_bonus(t) if at == len(steps) else 0), 'Tiền thưởng khách sạn không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= 24 and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký khách sạn sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Phiếu khách sạn chưa xong mà đã hoàn tất.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ khách sạn sai.')
    kit.need(type(d['intro']) is bool, 'Giới thiệu khách sạn sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    kit.need(isinstance(d['today'], dict) and set(d['today']) == set(base['today']), 'Số liệu khách sạn sai.')
    for v in d['today'].values():
        kit.integer(v, 0, 10**9)
    kit.integer(d['today']['counted'], 0, 1)
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu khách sạn sai.')
    for k, v in st.items():
        if k != 'posts':
            kit.integer(v, 0, 10**9)
    kit.need(isinstance(st['posts'], dict) and set(st['posts']) == set(KINDS), 'Số liệu vị trí khách sạn sai.')
    for v in st['posts'].values():
        kit.integer(v, 0, 10**9)
    for bucket in (d['today'], st):
        kit.need(bucket['good'] <= bucket['jobs'], 'Số việc đạt chuẩn sai.')
    kit.need(sum(st['posts'].values()) == st['good'] and st['seasonal'] <= st['jobs'] and st['active_days'] <= st['good'],
             'Tiến trình nghề khách sạn sai.')
    kit.desk_validate(d['desk'], hc.DESK)


SPEC = dict(
    id=ID, prefix='ht_', category='service', people=PEOPLE,
    meta=dict(short='Khách sạn', place='Khách sạn Sông Mây', tagline='Phòng sạch, thẻ đúng, khách ngủ ngon.', icon='bell',
              color='#7a5a9e', light='#f1eaf8', weather='Gió sông thổi qua sảnh', work='Phiếu việc', station='Quầy lễ tân & các tầng phòng',
              greeting='Bảng phân ca treo cạnh quầy: hôm nay bạn đi đủ các vị trí. Đọc phiếu kỹ, làm đúng thứ tự.',
              caption='Bốn tầng phòng, một ca luân phiên', map_label='KHÁCH SẠN SÔNG MÂY'),
    staff=[('Chị Hằng', 'desk', 'Trưởng ca lễ tân, nhớ mặt khách quen.', 84, 90), ('Cô Tư', 'rooms', 'Trưởng buồng phòng, gấp ga vuông như thước.', 80, 92)],
    roles={'desk': 'Lễ tân', 'rooms': 'Buồng phòng'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🛎️', 'Một ca ở Sông Mây', [('Lễ tân', 'Phiếu đúng, phòng sạch'), ('Buồng phòng', 'Đúng thứ tự'), ('Giặt là', 'Đếm thực tế'),
                                          ('Bảo trì', 'An toàn trước')],
              ['Đọc phiếu việc', 'Làm từng bước', 'Sửa bước sai tại chỗ', 'Báo lại cho ca sau']),
    stories=[('Chiếc chuông quầy lễ tân', ('Chiếc chuông đồng trên quầy đã mòn nút bấm.', 'Bạn lau chuông, ghi giờ ca vào sổ bàn giao.',
                                           'Chị Hằng cười: “Chuông kêu đúng lúc là khách biết có người chờ mình.”'))],
    review_asides=['Nhận phòng nhanh, phòng sạch thơm.', 'Lễ tân dặn giờ ăn sáng rõ ràng.', 'Báo hỏng là có người lên sửa ngay.'], situations=[],
    more_line='Thêm một phiếu việc vừa được giao.', open_line='Chị Hằng đã mở quầy; bảng phòng và sổ quy trình đặt cạnh chuông.',
    guide='Mỗi ca luân phiên: lễ tân (phiếu, giấy tờ, phòng, thẻ, giờ ăn sáng) → buồng phòng → giặt là → bữa sáng → bảo trì → trang trí. '
          'Làm từng bước theo phiếu; sai bước thì sửa ngay, thưởng giảm theo chất lượng. Mùa Valentine, Tết, Giáng sinh khách đông hơn, thưởng ×1.5.',
    employment=dict(postings=[dict(id='hotel-songmay', org='Khách sạn Sông Mây', kind='company', title='Nhân viên khách sạn (luân phiên)',
                                   salary=(52, 66), probation_days=3, wants=['careful', 'communication', 'patience'],
                                   perks=['Chị Hằng kèm những ca đầu', 'Thưởng chất lượng nhỏ, mùa lễ ×1.5', 'Lương ca theo hợp đồng'],
                                   culture='Phòng sạch mới giao, đồ khách là của khách, việc quá tay thì gọi thợ.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
