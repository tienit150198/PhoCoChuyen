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
GEN = 2
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


DECOR_RULE = 'Chọn TẤT CẢ món hợp dịp {title}, bỏ món khách dặn tránh; tổng tiền vượt ngân sách thì bỏ món đắt nhất.'


def decor_rule(brief: dict) -> str:
    """The rule of the decoration step in one line (feedback #404: a budget-fitting combo is not the answer)."""
    return DECOR_RULE.format(title=str(brief.get('title') or '').lower())


def decor_hint(brief: dict, chosen: list, good: list) -> str:
    """What is wrong with a decoration pick, without giving the list away (feedback #404): the chosen items that
    do not fit the occasion (and which occasion they are for), the items the guest asked to avoid, the priciest
    item over budget, and how many fitting items are still missing. Not part of the task: generation is unchanged."""
    items = {i[0]: i for i in hc.ITEMS}
    theme, title = brief.get('theme'), str(brief.get('title') or '').lower()
    cat = next((c for text, c in hc.LIMITS.values() if text == brief.get('limit')), '')
    picked = [items[i] for i in chosen if i in items]
    unfit = [i for i in picked if theme not in i[3]]
    avoid = [i for i in picked if theme in i[3] and cat and i[4] == cat]
    extra = [i for i in picked if theme in i[3] and i not in avoid and i[0] not in good]
    missing = sum(1 for i in good if i not in chosen)
    out = []
    if unfit:
        def other(i):
            return ', '.join(hc.THEMES[x][0].lower() for x in i[3] if x in hc.THEMES)
        out.append(f'Có món không hợp dịp {title}: ' + ', '.join(f'{i[1]} (dành cho {other(i)})' for i in unfit) + '.')
    if avoid:
        out.append('Có món khách dặn tránh: ' + ', '.join(i[1] for i in avoid) + '.')
    if extra:
        out.append(f'Tổng tiền vượt ngân sách {brief.get("budget")} xu: bỏ món đắt nhất trong các món hợp dịp.')
    if missing:
        out.append(f'Còn thiếu {missing} món hợp dịp {title}.')
    return ' '.join(out)[:400]


def _decor(r, day, slot):
    theme = hc.YEAR_ROUND[(day + slot) % len(hc.YEAR_ROUND)]
    brief, _, key = decor_brief(day, slot, theme)
    title = hc.THEMES[theme][0]
    return brief, key, f'Trang trí: {title.lower()}', 'Có yêu cầu trang trí. Chọn đúng đồ hợp dịp, theo lưu ý của khách, trong ngân sách.', 0


BUILD = dict(checkin=_checkin, housekeeping=_housekeeping, laundry=_laundry, breakfast=_breakfast, repair=_repair, decor=_decor)


# ---------------------------------------------------------------- generator 2 (22/10, feedback #466): a big hotel, you are staff
def _clock(m: int) -> str:
    return f'{m // 60}:{m % 60:02d}'


def _board_rows(r, keep: dict, pool: tuple) -> list:
    """The sixteen rooms with the housekeeping supervisor's statuses; `keep` fixes some of them."""
    return [dict(no=room[0], floor=int(room[0][0]), bed=room[1], view=room[2], spot=room[3], access=room[4],
                 status=keep.get(room[0]) or r.choice(pool)) for room in hc.ROOMS]


def _rush(r, day, slot):
    """Lễ tân at rush hour: four guests at once. Hand the VIP and the agency's group leader to the colleague the duty
    sheet names, serve the others by the time they must be done, give the arriving guest a room the supervisor has
    signed off ("Sạch · đã kiểm") and the right key cards, and take a complaint through the protocol."""
    req_id, req_text, test = hc.REQUESTS[r.randrange(len(hc.REQUESTS))]
    match = [room for room in hc.ROOMS if test(room)]
    target = r.choice(match)
    traps = ['vc', 'cleaning', 'vd', 'ooo', 'oc']
    r.shuffle(traps)
    keep = {target[0]: 'vci'}
    keep.update({room[0]: status for room, status in zip([x for x in match if x is not target], traps)})
    board = _board_rows(r, keep, ('oc', 'oc', 'oc', 'vd', 'vc', 'cleaning', 'vci'))
    hand = r.sample(('vip', 'grp'), r.choice((1, 1, 2)))
    kinds = ['arr'] + hand + r.sample(('out', 'walk', 'info', 'cmp'), 3 - len(hand))
    r.shuffle(kinds)
    now = 10 * 60 + 5 * r.randint(0, 6)
    mins = r.sample((5, 10, 15, 20, 25, 30, 40, 45, 50), 4)
    rows = [dict(id=f'q{i + 1}', kind=k, who=who, at=m) for i, (k, who, m) in enumerate(zip(kinds, r.sample(hc.QUEUE_NAMES, 4), mins))]
    queue = [dict(id=q['id'], kind=q['kind'], who=q['who'], emoji=hc.QUEUE[q['kind']][0], need=hc.QUEUE[q['kind']][1], by=_clock(now + q['at']))
             for q in rows]
    label = {q['id']: f'{q["emoji"]} {q["who"]} · {q["need"]} · xong trước {q["by"]}' for q in queue}
    mine = sorted((q for q in rows if not hc.QUEUE[q['kind']][2]), key=lambda q: q['at'])
    shown = list(mine)
    r.shuffle(shown)
    arr = next(q for q in rows if q['kind'] == 'arr')
    guests = 4 if req_id in ('family', 'river_family') else 2 if req_id in ('access', 'lift_double') else r.choice((1, 2))
    cards = min(2, guests)
    no = target[0]
    alt = no[::-1] if no[0] != no[2] else no[0] + '0' + str(5 - int(no[2]))
    steps = [
        _step('rush', 'handoff', 'multi', 'Chuyển khách cho đồng đội',
              f'Bốn khách cùng tới quầy lúc {_clock(now)}. Sổ phân công: VIP → quản lý trực; trưởng đoàn đại lý → quầy đoàn. Chọn những khách chuyển đi ngay.',
              [dict(id=q['id'], label=label[q['id']]) for q in queue]),
        _step('rush', 'order', 'order', 'Xếp thứ tự phục vụ tại quầy', 'Những khách còn lại: ai có giờ cần xong sớm hơn thì làm trước.',
              [dict(id=q['id'], label=label[q['id']]) for q in shown]),
        _step('rush', 'room', 'choice', 'Xếp phòng cho khách nhận phòng',
              f'{arr["who"]} ({guests} khách) đặt: {req_text} Chỉ giao phòng “{hc.STATUS2["vci"]}”.',
              [dict(id=b['no'], label=f'Phòng {b["no"]}') for b in board]),
        _step('rush', 'cards', 'choice', 'Cài thẻ từ', f'{arr["who"]}: {guests} khách. Mỗi khách một thẻ, tối đa 2 thẻ một phòng.',
              _opts(r, [(f'{no}-1', f'Thẻ phòng {no} · 1 thẻ'), (f'{no}-2', f'Thẻ phòng {no} · 2 thẻ'), (f'{alt}-{cards}', f'Thẻ phòng {alt} · {cards} thẻ')])),
    ]
    key = {'rush.handoff': sorted(q['id'] for q in rows if hc.QUEUE[q['kind']][2]), 'rush.order': [q['id'] for q in mine],
           'rush.room': no, 'rush.cards': f'{no}-{cards}'}
    cmp = next((q for q in rows if q['kind'] == 'cmp'), None)
    if cmp:
        steps.append(_step('rush', 'calm', 'order', 'Xử lý phàn nàn theo quy trình',
                           f'{cmp["who"]}: “Phòng ồn quá, đêm qua tôi không ngủ được.” Làm đúng thứ tự trong sổ quy trình xử lý phàn nàn.', _opts(r, hc.CALM)))
        key['rush.calm'] = [k for k, _ in hc.CALM]
    needs = dict(now=_clock(now), queue=queue, board=board, request=req_text, arrival=arr['who'], guests=guests, steps=steps)
    return (needs, key, 'Quầy giờ cao điểm: bốn khách cùng lúc',
            'Bốn khách cùng tới quầy. Chị Hằng: “Chuyển đúng người cho đồng đội, ai gấp làm trước, chỉ giao phòng đã kiểm.”', 0)


def _roomboard(r, day, slot):
    """Buồng phòng as the floor supervisor: which dirty rooms go first (today's arrivals), lock a broken room, split
    the rest between the two housekeepers by floor, inspect a room just cleaned, tell the desk how many sell now."""
    rooms = list(hc.ROOMS)
    arrive = r.sample(rooms, 3)
    fault = r.choice([x for x in rooms if x not in arrive])
    check = r.choice([x for x in rooms if x not in arrive and x is not fault])
    first = r.sample(arrive, r.choice((2, 2, 3)))
    keep = {x[0]: 'vd' if x in first else r.choice(('vci', 'cleaning')) for x in arrive}
    keep.update({fault[0]: 'vd', check[0]: 'vc'})
    board = _board_rows(r, keep, ('oc', 'oc', 'oc', 'vd', 'vd', 'vci', 'cleaning'))
    etas = r.sample((12 * 60, 13 * 60, 14 * 60, 15 * 60 + 30, 17 * 60, 19 * 60), 3)
    vip = r.randrange(3)
    names = r.sample(hc.QUEUE_NAMES, 3)
    arrivals = sorted((dict(name=names[i], room=x[0], eta=etas[i], vip=i == vip) for i, x in enumerate(arrive)), key=lambda a: a['eta'])
    arrivals = [dict(a, eta=_clock(a['eta'])) for a in arrivals]
    text, verdict = r.choice(hc.FINDINGS)
    side = 'low' if int(check[0][0]) <= 2 else 'high'
    issue = r.choice(hc.BOARD_FAULTS)
    dirty = [b['no'] for b in board if b['status'] == 'vd']
    split = {k: sum(1 for no in dirty if no != fault[0] and (int(no[0]) <= 2) == (k == 'low')) for k in hc.TEAM}
    sell = sum(1 for b in board if b['status'] == 'vci' and b['no'] not in {x[0] for x in arrive}) + (verdict == 'pass')
    who = hc.TEAM[side][0]
    steps = [
        _step('housekeeping', 'first', 'multi', 'Phòng phải dọn trước',
              'Đối chiếu danh sách khách đến hôm nay: phòng bẩn đã gán cho khách đến thì dọn trước.',
              [dict(id=no, label=f'Phòng {no} · {hc.STATUS2["vd"]}') for no in sorted(dirty)]),
        _step('housekeeping', 'ooo', 'choice', 'Phòng báo hỏng', f'Phòng {fault[0]} (bẩn, vừa trả) báo: {issue.lower()}.', _opts(r, hc.OOO_OPTIONS)),
        _step('housekeeping', 'split', 'counts', 'Chia phòng bẩn cho tổ',
              'Giao hết phòng bẩn theo tầng phụ trách, trừ phòng hỏng. Ghi số phòng mỗi người.',
              fields=[dict(id=k, label=f'{n} · {f}') for k, (n, f) in hc.TEAM.items()]),
        _step('housekeeping', 'inspect', 'choice', 'Kiểm phòng vừa dọn', f'{who} báo phòng {check[0]} dọn xong. Bạn kiểm: {text}',
              _opts(r, hc.INSPECT_OPTIONS)),
        _step('housekeeping', 'sell', 'number', 'Báo lễ tân số phòng bán được ngay',
              'Phòng trống “Sạch · đã kiểm”, chưa gán cho khách đến; tính cả phòng vừa kiểm nếu đạt.', unit='phòng'),
    ]
    key = {'housekeeping.first': sorted(x[0] for x in first), 'housekeeping.ooo': 'ooo', 'housekeeping.split': split,
           'housekeeping.inspect': verdict, 'housekeeping.sell': sell}
    needs = dict(board=board, arrivals=arrivals, team=[dict(id=k, who=n, floors=f) for k, (n, f) in hc.TEAM.items()],
                 fault=dict(room=fault[0], text=issue), check=dict(room=check[0], by=who, finding=text), steps=steps)
    return needs, key, 'Bảng phòng ca sáng: chia việc cho tổ buồng', 'Cô Tư giao bạn trực bảng phòng: phòng nào dọn trước, chia việc cho tổ, kiểm phòng, báo lễ tân.', 2


BUILD2 = dict(checkin=_rush, housekeeping=_roomboard)


def kind_of(day: int, slot: int) -> str:
    """The post of (day, slot): the shift rotates through the six posts."""
    return KINDS[(day - 1 + slot) % len(KINDS)]


def make_task(day: int, slot: int, serial: int) -> dict:
    """Generator 2 (22/10): the front desk at rush hour and the room board; a task made before it (kit legacy serial
    band, heal_save) is rebuilt by generator 1 exactly as it was made."""
    kind = kind_of(day, slot)
    gen = 1 if kit.legacy(serial) else GEN
    build = BUILD2.get(kind) if gen >= 2 else None
    if build:
        needs, key, title, opening, npc = build(kit.rng(ID, 'g2', day, slot), day, slot)
    else:
        needs, key, title, opening, npc = BUILD[kind](kit.rng(ID, day, slot), day, slot)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, gen=gen, kind=kind, needs=needs, _key=key,
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work', season='none')


def heal_save(s: dict, c: dict) -> None:
    """migrate_state: tasks made by generator 1 move into the kit legacy serial band, so make_task rebuilds them as they
    were made (generator 2 changes what the desk and the rooms post give for a day and slot)."""
    for t in c.get('tasks') if isinstance(c.get('tasks'), list) else ():
        if (isinstance(t, dict) and t.get('career') == ID and t.get('gen') == 1 and type(t.get('created_turn')) is int
                and 0 <= t['created_turn'] < kit.LEGACY_TURN):
            t['created_turn'] += kit.LEGACY_TURN


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _active(t: dict) -> tuple[dict, list, dict]:
    """(brief, steps, key) in force: a decoration task taken in season follows the season's brief."""
    if t.get('kind') == 'decor' and t.get('season') in hc.SEASONS:
        return decor_brief(t['day'], _slot(t), t['season'])
    return t['needs'], t['needs']['steps'], t['_key']


WRONG_COST, QUALITY_FLOOR = 6, 60   # quality lost per redone step (17/10: was 12, floor 40; owner "dễ chơi hơn")


def _quality(wrong: int) -> int:
    return max(QUALITY_FLOOR, 100 - WRONG_COST * wrong)


def _quality_ok(t: dict, wrong: int) -> bool:
    """The quality of `wrong` slips: the current rule, or the one before 17/10 (a task slipped then and not since)."""
    return t.get('quality') in (_quality(wrong), max(40, 100 - 12 * wrong))


# The way to work out a number step, said on its first slip (17/10: "dễ chơi hơn"); the second slip shows the answer.
HOW = {
    'housekeeping.split': 'Đếm mọi phòng “Bẩn” trên bảng theo tầng (tầng 1–2, tầng 3–4), bỏ phòng hỏng ra.',
    'housekeeping.sell': 'Đếm phòng “Sạch · đã kiểm” trên bảng không gán cho khách đến (phòng vừa kiểm đạt đã lên bảng).',
    'housekeeping.minibar': 'Mỗi món: (số lúc đầu − số còn lại) × giá, rồi cộng các món lại. Món miễn phí không tính tiền.',
    'breakfast.boxes': 'Mỗi khách đi tour sớm một hộp.',
    'breakfast.kitchen': 'Đếm từng món của các phòng ăn tại nhà hàng (món trái lưu ý tính theo món đã đổi); phòng đi tour không tính.',
}


def _bonus(t: dict) -> int:
    bonus = max(3, round(hc.BONUS[t['kind']] * t['quality'] / 100))
    if t.get('season') in hc.SEASONS:
        bonus = round(bonus * hc.SEASON_BONUS)
    return bonus + (hc.FAST_BONUS if t.get('fast') is True else 0)


def _speed(t: dict) -> None:
    """A generator-2 job done with no slip within its procedure time is "Nhanh" (decided once, at the last step)."""
    if t.get('gen', 1) >= 2 and isinstance(t.get('t0'), (int, float)):
        t['fast'] = t['wrong'] == 0 and kit.now() - t['t0'] <= hc.TARGET[t['kind']]


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
    brief, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    if t.get('gen', 1) >= 2 and 't0' not in t:
        t['t0'] = round(kit.now(), 3)   # the procedure clock starts at the first step tried
    if not _same(value, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        again = ('Đếm lại từng món nhé.' if st['id'] == 'laundry.tally' else 'Xem lại bảng phòng và sổ quy trình rồi làm lại bước này.'
                 if st['id'].startswith(('rush.', 'housekeeping.')) and t.get('gen', 1) >= 2 else 'Đọc lại phiếu và sổ quy trình rồi làm lại bước này.')
        if st['id'] == 'decor.items':
            again = decor_hint(brief, value, key[st['id']]) or again
        elif st['id'] == 'decor.cost':
            again = f'Cộng giá các món đã chọn ở bước trước ({len(t["work"].get("decor.items", []))} món) rồi ghi tổng.'
        who = 'Cô Tư' if t['kind'] in ('housekeeping', 'laundry') else 'Anh Bảo' if t['kind'] == 'repair' else 'Chị Hằng'
        message = f'Chưa đúng: {st["title"].lower()}. {kit.step_help(t, st, key[st["id"]], HOW.get(st["id"], ""), again, who)}'
        t['lines'] = (t['lines'] + [message[:480]])[-24:]
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
    _speed(t)
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
    post = _post(t)
    kit.complete(s, c, t, bonus, f'Xong việc {post[0].lower()}: {post[2].lower()}, chất lượng {t["quality"]}%.')
    extra = ' Thưởng mùa lễ ×1.5.' if t.get('season') in hc.SEASONS else ''
    if t.get('fast') is True:
        extra += f' ⏱️ Nhanh, đúng quy trình: +{hc.FAST_BONUS} xu.'
    elif t.get('fast') is False and t['wrong'] == 0:
        extra += f' ⏱️ Quá thời gian chuẩn ({hc.TARGET[t["kind"]]} giây).'
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


def briefing(day: int) -> str:
    """The manager's word at the start of the shift (a pure function of the day): a big hotel's numbers."""
    r = kit.rng(ID, 'brief', day)
    occ, arr, vip, grp = r.choice((72, 78, 84, 88, 91, 95)), r.randint(9, 18), r.randint(1, 3), r.randint(0, 2)
    if grp:
        return f'📋 Giao ban: công suất {occ}%, {arr} lượt khách đến, {vip} khách VIP, {grp} đoàn đại lý. Trưởng ca: Chị Hằng, quản lý trực: Anh Khôi.'
    return f'📋 Giao ban: công suất {occ}%, {arr} lượt khách đến, {vip} khách VIP. Trưởng ca: Chị Hằng, quản lý trực: Anh Khôi.'


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    season = season_now()
    kit.log(s, c, ID, briefing(c['day']))
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


def _post(t: dict) -> tuple:
    """(label, emoji, work) of the task's post; generator 2 changed what the desk and the rooms post do."""
    post = hc.POSTS[t['kind']]
    return (post[0], post[1], hc.WORK2[t['kind']]) if t.get('gen', 1) >= 2 and t['kind'] in hc.WORK2 else post


def known_request(c: dict, t: dict) -> str:
    post = _post(t)
    return f'{post[1]} {post[0]}: {t["opening"]}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết vị trí hôm nay và yêu cầu của khách.'
    brief, steps, _ = _active(t)
    if t['at'] < len(steps) and steps[t['at']]['id'] == 'decor.items':
        return decor_rule(brief)   # the brief is on screen; the helper says the rule (#404)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Việc đã xong; nhận việc tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    rows = [dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
            dict(key='care', label='Chất lượng phục vụ', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')]
    if t.get('fast') in (True, False):
        rows.append(dict(key='speed', label='Tốc độ', score=5 if t['fast'] else 3,
                         note=f'Trong thời gian chuẩn ({hc.TARGET[t["kind"]]} giây).' if t['fast'] else f'Quá thời gian chuẩn ({hc.TARGET[t["kind"]]} giây) hoặc có bước làm lại.'))
    return dict(criteria=rows)


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    else:
        brief, _, _ = _active(t)
        v['needs'] = deepcopy(brief)
        if t['kind'] == 'decor':
            v['needs']['rule'] = decor_rule(brief)   # shown on the screen only: not part of the task (#404)
    post = _post(t)
    v['post'] = dict(id=t['kind'], label=post[0], emoji=post[1], work=post[2])
    v['season_info'] = season_view(t.get('season', 'none'))
    v['target'] = hc.TARGET[t['kind']] if t.get('gen', 1) >= 2 else None   # the procedure time in seconds (generator 2)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    posts = sum(1 for k in KINDS if stats['posts'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and posts >= m['posts']) for m in hc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, posts=posts)
    d['desk'] = kit.desk_public(d['desk'], hc.DESK, ID, c)
    d['season'] = season_view()
    d['briefing'] = briefing(c['day'])
    return d


def content() -> dict:
    return dict(
        notebook=hc.NOTEBOOK[:1] + hc.NOTEBOOK2 + hc.NOTEBOOK[1:],
        posts=[dict(id=k, label=v[0], emoji=v[1], work=v[2]) for k, v in hc.POSTS.items()],
        beds=hc.BEDS, views=hc.VIEWS, spots=hc.SPOTS, status=hc.STATUS, status2=hc.STATUS2,
        seasons=[dict(id=k, label=v[0], emoji=v[1], note=v[2]) for k, v in hc.SEASONS.items()],
        intro=dict(title='Một ca ở Khách sạn Sông Mây',
                   lead='Khách sạn bốn tầng, mười sáu phòng bên sông; bạn là nhân viên ca. Mỗi ca luân phiên các vị trí theo bảng phân công; '
                        'chấm theo đúng quy trình và tốc độ. Lương ca theo hợp đồng, thưởng nhỏ từng việc; thăng tiến lên trưởng ca, quản lý.',
                   work=[['🛎️', 'Quầy giờ cao điểm: nhiều khách cùng lúc, chuyển đúng người'], ['📋', 'Bảng phòng: chia việc cho tổ buồng, kiểm phòng'],
                         ['🔧', 'Giặt là, bữa sáng, bảo trì, trang trí theo phiếu']],
                   meet=[['🙂', 'Chị Hằng trưởng ca lễ tân'], ['🧑‍💼', 'Anh Khôi quản lý trực'], ['🧺', 'Cô Tư trưởng buồng phòng']],
                   stars=[['✓', 'Chỉ giao phòng “Sạch · đã kiểm”'], ['⏱️', 'Đúng quy trình trong thời gian chuẩn là “Nhanh”'],
                          ['✓', 'Trang trí: chọn tất cả món hợp dịp (không phải một combo vừa tiền), bỏ món khách dặn tránh']]))


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
    kit.need(_quality_ok(t, wrong), 'Điểm chất lượng khách sạn không khớp.')
    if 't0' in t:   # generator 2: the procedure clock (seconds since the epoch) and its verdict at the last step
        kit.need(t.get('gen', 1) >= 2 and isinstance(t['t0'], (int, float)) and not isinstance(t['t0'], bool) and 0 <= t['t0'] < 10**11,
                 'Đồng hồ quy trình khách sạn sai.')
    if 'fast' in t:
        kit.need(type(t['fast']) is bool and 't0' in t and at == len(steps) and (wrong == 0 or not t['fast']), 'Tốc độ khách sạn sai.')
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
    meta=dict(short='Nhân viên khách sạn', place='Khách sạn Sông Mây', tagline='Làm ca ở khách sạn lớn: đông khách, đúng quy trình, nhanh tay.',
              icon='bell', color='#7a5a9e', light='#f1eaf8', weather='Gió sông thổi qua sảnh', work='Phiếu việc', station='Quầy lễ tân & bảng phòng',
              greeting='Giao ban xong, bảng phân ca treo cạnh quầy. Hôm nay đông khách: làm đúng quy trình, nhanh tay mà không vội.',
              caption='Mười sáu phòng, một ca làm thuê theo quy trình', map_label='KHÁCH SẠN SÔNG MÂY'),
    staff=[('Chị Hằng', 'desk', 'Trưởng ca lễ tân, nhớ mặt khách quen.', 84, 90), ('Cô Tư', 'rooms', 'Trưởng buồng phòng, gấp ga vuông như thước.', 80, 92)],
    roles={'desk': 'Lễ tân', 'rooms': 'Buồng phòng'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🛎️', 'Một ca ở Sông Mây', [('Lễ tân', 'Phiếu đúng, phòng sạch'), ('Buồng phòng', 'Đúng thứ tự'), ('Giặt là', 'Đếm thực tế'),
                                          ('Bảo trì', 'An toàn trước')],
              ['Đọc phiếu việc', 'Làm từng bước', 'Sửa bước sai tại chỗ', 'Báo lại cho ca sau']),
    stories=[('Chiếc chuông quầy lễ tân', ('Chiếc chuông đồng trên quầy đã mòn nút bấm.', 'Bạn lau chuông, ghi giờ ca vào sổ bàn giao.',
                                           'Chị Hằng cười: “Chuông kêu đúng lúc là khách biết có người chờ mình.”'))],
    review_asides=['Nhận phòng nhanh, phòng sạch thơm.', 'Lễ tân dặn giờ ăn sáng rõ ràng.', 'Báo hỏng là có người lên sửa ngay.'], situations=[],
    more_line='Thêm một phiếu việc vừa được giao.', open_line='Chị Hằng đã mở quầy; bảng phòng và sổ quy trình đặt cạnh chuông.',
    guide='Mỗi ca luân phiên: quầy giờ cao điểm (chuyển khách cho đồng đội, ai gấp làm trước, phòng đã kiểm, thẻ từ) → bảng phòng (dọn trước, '
          'khóa phòng hỏng, chia tổ, kiểm phòng) → giặt là → bữa sáng → bảo trì → trang trí. Sai bước thì sửa ngay, thưởng giảm; '
          'đúng hết trong thời gian chuẩn được thêm 1 xu. Mùa Valentine, Tết, Giáng sinh khách đông hơn, thưởng ×1.5.',
    employment=dict(postings=[dict(id='hotel-songmay', org='Khách sạn Sông Mây', kind='company', title='Nhân viên khách sạn (luân phiên)',
                                   salary=(52, 66), probation_days=3, wants=['careful', 'communication', 'patience'],
                                   perks=['Chị Hằng kèm những ca đầu', 'Thưởng chất lượng nhỏ, mùa lễ ×1.5', 'Lương ca theo hợp đồng'],
                                   culture='Phòng sạch mới giao, đồ khách là của khách, việc quá tay thì gọi thợ.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
