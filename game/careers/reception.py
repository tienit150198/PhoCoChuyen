"""🛎️ Lễ tân Khách sạn Hoa Sứ: the front desk of a six-room hotel, a salaried job with its own hiring trial.

Six kinds of work rotate through the shift (ROTA): Nhận khách (read what the guest says, put each party in a room
that fits on the room board, hand the right key from the hook board, load the luggage cart, write the handover),
Trả phòng (the key back, the bill, the luggage hold), Điều phối dọn phòng (which room first, checking a room the
overloaded housekeeper calls done), Lịch dịch vụ (wake-up calls, breakfast trays and taxis on tomorrow's timeline),
Phàn nàn (hear the real issue, verify, compensate by the policy, log it) and Đồ thất lạc (walk the guest's route back
from where the thing was last seen, match the lost-and-found log, check the owner). Every step is graded on the
server; a wrong step stays open to fix and lowers the quality (and the small bonus). The room and luggage steps are
graded by rule (any assignment that respects capacity, needs, status, adjacency and the cart's rules passes).

🧪 Ca thử việc: a newly started desk clerk first works three trial check-ins (a normal guest, an early guest whose
room is not clean, a group with two needs at once). A trial job carries `trial` (set once by on_task, like the
hotel's season), its brief is a pure function of (day, slot, trial) and it passes when capacity, the needs and the
handover were right the first time. A failed part says what to practise and comes again the next day; passed parts
are kept (data['trial']).

🎭 The awkward desk situations (reception_content.DESK) are kit desk scripts with lasting consequences: marks,
relations with the shift lead, the credit-stealing colleague, the new hire, the housekeeper and the regular guest
(data['rel']), what the choices cost the hotel (house) and keepsakes kept in the Sổ nghề (data['keeps']).

A job about a passing guest (a check-in, a check-out, a complaint, a lost thing) carries that guest in needs['guest']
(name, gender, a drawn face code; guest_of): the card, the 2D scene and the feed review show them, the job is filed
under the generic Khách lưu trú NPC, and the lines they say fit their voice and their party (reception_content.says).

After the second promotion the clerk picks a branch (chăm sóc khách, điều hành, sự kiện, tự kinh doanh): the jobs of
that branch pay ×1.25 (×1.1 for every job when going self-employed, with a door to the homestay career). A task
carries the branch it was taken under (`branch`, set by on_task), so its bonus stays checkable.
"""
from __future__ import annotations

from copy import deepcopy
import json

from . import kit
from . import reception_content as rc
from .. import consequences as cq

ID = 'reception'
GEN = 1
PEOPLE = rc.PEOPLE
KINDS = rc.KINDS
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('rc_step',)
FREE = ('rc_intro', 'rc_branch')
NO_TICK = ('rc_intro', 'rc_desk', 'rc_branch')
TYPES = ('choice', 'number', 'order', 'multi', 'assign', 'times')
RULE_STEPS = ('arrival.rooms', 'arrival.cart', 'arrival.keys')
BROKE_CODES = ('cap', 'need', 'near', 'dirty', 'busy', 'same', 'note', 'heard', 'shelf', 'full')
WRONG_COST, QUALITY_FLOOR = 6, 60


# ---------------------------------------------------------------- small helpers
def _opts(r, rows, shuffle=True):
    out = [dict(id=k, label=v) for k, v in rows]
    if shuffle:
        r.shuffle(out)
    return out


def _step(kind, name, typ, title, evidence, **more):
    st = dict(id=f'{kind}.{name}', type=typ, title=title, evidence=evidence)
    st.update({k: v for k, v in more.items() if v is not None})
    return st


def hhmm(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _fits(room: dict, tag: str) -> bool:
    test = rc.TAGS[tag][1]
    return True if test is None else bool(test(room))


def _near(a: str, b: str) -> bool:
    return (a, b) in rc.NEAR or (b, a) in rc.NEAR


# ---------------------------------------------------------------- the guest of a job
_FACE_HAIR = dict(male=('ngan', 'dinh', 'lech', 'dung', 'hoi'), female=('bob', 'dai', 'bui', 'duoi', 'song', 'tet', 'bui_thap'))
_FACE_ORDER = ('skin', 'shape', 'age', 'hair', 'hc', 'expr', 'glasses', 'head', 'hwc', 'beard', 'freckles', 'extra', 'bg', 'shirt')


def guest_face(name: str, gender: str, age: str = 'lon') -> str:
    """A drawn face code for a guest (the chat avatar's 'f1' code, public/js/v4/face-code.js): the same name always
    has the same face, a woman's hair for a woman."""
    r = kit.rng(ID, 'face', name)
    f = dict(skin=r.choice(('s1', 's2', 's3', 's4', 's5')), shape=r.choice(('tron', 'oval', 'vuong', 'tim')), age=age,
             hair=r.choice(_FACE_HAIR['female' if gender == 'female' else 'male']),
             hc=('xam' if age == 'gia' else r.choice(('den', 'den', 'nau', 'mat_ong'))), expr=r.choice(('cuoi', 'toe', 'diu', 'ngac')),
             glasses=r.choice(('0', '0', '0', 'tron', 'vuong')), head='0', hwc='do',
             beard=(r.choice(('0', '0', 'ria', 'lun')) if gender == 'male' else '0'), freckles='0', extra='0',
             bg=r.choice(('kem', 'hong', 'dao', 'vang', 'mint', 'xanh', 'lavender')),
             shirt=r.choice(('navy', 'nau', 'mint', 'trang', 'do', 'vang', 'lavender')))
    return '.'.join(['f1'] + [f[k] for k in _FACE_ORDER] + ['f' if gender == 'female' else 'm', 'ao_quen', '0', 'pk_khong', '0'])


def guest_of(name: str, gender: str | None = None, age: str = 'lon') -> dict:
    """The person a job is about when it is not one of the desk's people: name, gender, face (task needs['guest'];
    the card, the 2D scene and the review show them, not the NPC the job is filed under)."""
    gender = gender or rc.GUEST_GENDER.get(name, 'female')
    return dict(name=name, gender=gender, fc=guest_face(name, gender, age))


def _call(gender: str) -> str:
    """How the desk calls a guest (anh / chị)."""
    return 'chị' if gender == 'female' else 'anh'


# ---------------------------------------------------------------- Nhận khách (arrival)
def _card(r, cid, room, people, tags, name, items, asks):
    gender = rc.GUEST_GENDER.get(name, 'female')
    said = [r.choice(rc.says(t, gender, people)) for t in tags]   # the guest's own voice and party size
    if r.random() < 0.7:
        said.insert(r.randrange(len(said) + 1), r.choice(rc.chatter(gender)))
    return dict(id=cid, name=name, people=people, tags=sorted(tags), said=said, items=items, asks=asks, room=room)


def _luggage(r, n):
    """n pieces of luggage that fit the cart (≤3 heavy, ≤3 fragile, ≤2 tall, ≤8 in all)."""
    for _ in range(40):
        pick = r.sample(rc.LUGGAGE, n)
        kinds = [k for _, _, k in pick]
        if kinds.count('heavy') <= 3 and kinds.count('fragile') <= 3 and kinds.count('tall') <= 2:
            return [x[0] for x in pick]
    return ['balo', 'tui', 'vali'][:n]


def _arrival(r, day, slot, variant=None):
    """A party (or a group of two) at the desk. variant: None (a normal shift: a group now and then), 'normal',
    'early' (the only fitting rooms are not cleaned yet: hold one, the guest waits), 'group' (two rooms side by side)."""
    tier = kit.tier(day)
    group = variant == 'group' or (variant is None and r.random() < (0.2 if tier == 0 else 0.35))
    regular = variant is None and not group and r.random() < 0.12
    names = r.sample(rc.GUESTS, 2)
    cards = []
    if group:
        a, b = r.choice(rc.NEAR)
        if r.random() < 0.5:
            a, b = b, a
        for i, no in enumerate((a, b)):
            room = rc.ROOM[no]
            own = [t for t in rc.TAG_IDS if t != 'near' and _fits(room, t)]
            tags = r.sample(own, 1) + ['near']
            people = r.randint(1, room['cap'])
            cards.append(dict(no=no, people=people, tags=tags, name=names[i]))
    else:
        if regular:
            room = rc.ROOM['102']
            tags, people, name = ['quiet', 'ground'], 1, 'Ông Tư Bến'
        else:
            room = r.choice(rc.ROOMS)
            own = [t for t in rc.TAG_IDS if t != 'near' and _fits(room, t)]
            k = 1 if tier == 0 or variant == 'normal' else r.choice((1, 2)) if tier < 3 else r.choice((1, 2, 3))
            tags = r.sample(own, min(k, len(own)))
            people = room['cap'] if r.random() < 0.4 else r.randint(1, room['cap'])
            name = names[0]
        cards.append(dict(no=room['no'], people=people, tags=tags, name=name))
    targets = {c['no'] for c in cards}
    board = []
    for room in rc.ROOMS:
        no = room['no']
        if no in targets:
            status = 'dirty' if variant == 'early' else 'clean'
        else:
            tempting = any(all(_fits(room, t) for t in c['tags'] if t != 'near') and room['cap'] >= c['people'] for c in cards)
            if variant == 'early' and tempting:
                status = 'busy'
            elif tempting and r.random() < 0.75:
                status = r.choice(('dirty', 'busy'))
            else:
                status = r.choice(('clean', 'clean', 'dirty', 'busy'))
        board.append(dict(no=no, status=status))
    # luggage and the jobs left for the next shift
    n_items = r.randint(3, 4) if group else r.randint(2, 4)
    items = _luggage(r, n_items)
    asks_pool = [a[0] for a in rc.ASKS]
    r.shuffle(asks_pool)
    out_cards, notes, true_ids = [], [], []
    for i, c in enumerate(cards):
        cid = f'g{i + 1}'
        mine = items[i::len(cards)]
        asks = [asks_pool.pop() for _ in range(r.randint(1, 2) if i == 0 else r.randint(0, 1))]
        card = _card(r, cid, c['no'], c['people'], c['tags'], c['name'], mine, asks)
        for a in asks:
            card['said'].append(rc.ASK_INDEX[a][1])
            nid = f'{a}-{cid}'
            notes.append((nid, rc.ASK_INDEX[a][2].format(name=c['name'])))
            true_ids.append(nid)
        out_cards.append(card)
    if variant == 'early':
        nid = 'early-g1'
        notes.append((nid, f'Cô Lài dọn trước phòng đã xếp cho khách {cards[0]["name"]}, xong gọi khách'))
        true_ids.append(nid)
    for did, line in r.sample(rc.DONE_LINES, 2):
        notes.append((f'{did}-g1', line.format(name=cards[0]['name'])))
    who = ' và '.join(f'{c["name"]} ({c["people"]} người{", đi cùng" if i else ""})' for i, c in enumerate(cards))
    heard = ' '.join(f'“{x}”' for c in out_cards for x in c['said'])
    steps = [
        _step('arrival', 'need', 'multi', 'Hiểu khách cần gì', f'{who} nói: {heard} Chọn mọi yêu cầu khách vừa nói (không chọn điều khách không nói).',
              options=_opts(r, [(t, rc.TAGS[t][0]) for t in rc.TAG_IDS])),
        _step('arrival', 'rooms', 'assign', 'Xếp phòng trên bảng phòng',
              ('Phòng chưa dọn cũng được nếu cô Lài dọn trước; phòng có khách thì không.' if variant == 'early' else
               'Kéo hoặc chạm thẻ khách rồi chạm phòng. Chỉ phòng sạch, trống, đủ người, đủ mọi yêu cầu.'),
              cards=[dict(id=c['id'], label=f'{c["name"]} · {c["people"]} người') for c in out_cards],
              targets=[dict(id=b['no'], label=f'Phòng {b["no"]}') for b in board], unique=True),
    ]
    if variant == 'early':
        steps.append(_step('arrival', 'early', 'choice', 'Khách tới sớm 4 tiếng',
                           f'Bây giờ là 10:00, giờ nhận phòng 14:00. Phòng xếp cho {cards[0]["name"]} chưa dọn, cô Lài đang ở tầng 2.',
                           options=_opts(r, rc.EARLY_OPTIONS)))
    steps += [
        _step('arrival', 'keys', 'multi', 'Lấy đúng chìa trên bảng móc',
              'Mỗi phòng vừa xếp một chìa đúng số, móc xanh. Móc đỏ, móc xám, chìa nhà xe không phải chìa phòng.',
              options=_opts(r, [(f'k{room["no"]}', f'🔑 {room["no"]} · móc xanh') for room in rc.ROOMS] + r.sample(rc.KEY_DECOYS, 3))),
        _step('arrival', 'cart', 'assign', 'Xếp hành lý lên xe đẩy',
              'Đồ nặng tầng dưới, đồ dễ vỡ tầng trên, đồ dài hoặc đồ treo ở khung dựng. Tầng dưới, tầng trên mỗi tầng 3 món; khung 2 món.',
              cards=[dict(id=k, label=rc.LUGGAGE_INDEX[k][0]) for k in items],
              targets=[dict(id=k, label=label) for k, label, _ in rc.SHELVES], unique=False),
        _step('arrival', 'note', 'multi', 'Ghi sổ giao ca',
              'Chọn những việc CÒN DỞ cho ca sau. Việc đã xong ở quầy thì không ghi.', options=_opts(r, notes)),
    ]
    cart = {k: rc.SHELF_OF.get(rc.LUGGAGE_INDEX[k][1], 'top') for k in items}
    plain = [k for k in items if rc.LUGGAGE_INDEX[k][1] == 'plain']
    for k in plain:   # a plain piece goes where there is room
        used = {s: sum(1 for x in cart if cart[x] == s and x != k) for s in rc.SHELF_CAP}
        cart[k] = next(s for s in ('top', 'bottom', 'frame') if used[s] < rc.SHELF_CAP[s])
    key = {'arrival.need': sorted({t for c in cards for t in c['tags']}),
           'arrival.rooms': {c['id']: c['room'] for c in out_cards},
           'arrival.keys': sorted(f'k{c["room"]}' for c in out_cards),
           'arrival.cart': cart,
           'arrival.note': sorted(true_ids)}
    if variant == 'early':
        key['arrival.early'] = 'hold'
    for c in out_cards:
        c.pop('room')
    # The guest at the desk is the first card's person (Ông Tư Bến is one of the desk's people: his own portrait).
    guest = None if regular else guest_of(cards[0]['name'])
    needs = dict(variant=variant or ('group' if group else 'normal'), cards=out_cards, board=board, items=items, regular=regular, steps=steps,
                 guest=guest)
    npc = 4 if regular else rc.GUEST_NPC
    title = 'Đoàn khách tới quầy' if group else f'Khách tới quầy: {cards[0]["name"]}'
    first = out_cards[0]['said'][0] if out_cards[0]['said'] else ''
    opening = f'{who} tới quầy: “{first}”' if first else f'{who} tới quầy.'
    return needs, key, title, opening[:900], npc


def rooms_problems(needs: dict, value: dict) -> list[tuple[str, str]]:
    """What is wrong with a room assignment: [(code, words)], empty when it fits (any fitting assignment passes)."""
    status = {b['no']: b['status'] for b in needs['board']}
    early = needs.get('variant') == 'early'
    out = []
    rooms = list(value.values())
    if len(set(rooms)) != len(rooms):
        out.append(('same', 'Hai nhóm không ở chung một phòng: mỗi nhóm một phòng.'))
    for card in needs['cards']:
        no = value.get(card['id'])
        room = rc.ROOM.get(no)
        if room is None:
            continue
        st = status.get(no)
        if st == 'busy':
            out.append(('busy', f'Phòng {no} đang có khách.'))
        elif st == 'dirty' and not early:
            out.append(('dirty', f'Phòng {no} chưa dọn: chỉ giao phòng sạch.'))
        if room['cap'] < card['people']:
            out.append(('cap', f'Phòng {no} chỉ cho {room["cap"]} người, {card["name"]} có {card["people"]} người.'))
        for t in card['tags']:
            if t != 'near' and not _fits(room, t):
                out.append(('need', f'{card["name"]} cần “{rc.TAGS[t][0].lower()}”, phòng {no} không có.'))
    linked = [c for c in needs['cards'] if 'near' in c['tags']]
    for i in range(len(linked) - 1):
        a, b = value.get(linked[i]['id']), value.get(linked[i + 1]['id'])
        if a and b and a != b and not _near(a, b):
            out.append(('near', f'Phòng {a} và {b} không sát vách nhau.'))
    return out


SHELF_NAME = {k: label for k, label, _ in rc.SHELVES}


def cart_problems(needs: dict, value: dict) -> list[tuple[str, str]]:
    out = []
    count = {s: 0 for s in rc.SHELF_CAP}
    for item, shelf in value.items():
        count[shelf] += 1
        label, kind = rc.LUGGAGE_INDEX[item]
        must = rc.SHELF_OF.get(kind)
        if must and shelf != must:
            out.append(('shelf', f'{label} phải để ở {SHELF_NAME[must].lower()}.'))
    for shelf, n in count.items():
        if n > rc.SHELF_CAP[shelf]:
            out.append(('full', f'{SHELF_NAME[shelf]} chỉ chứa {rc.SHELF_CAP[shelf]} món.'))
    return out


# ---------------------------------------------------------------- Trả phòng (checkout)
def _checkout(r, day, slot):
    room = r.choice(rc.ROOMS)
    no, price = room['no'], room['price']
    nights = r.randint(1, 3)
    used = {k: r.randint(0, 2) for k, _, _ in rc.MINIBAR}
    mini = sum(used[k] * p for k, _, p in rc.MINIBAR)
    late = r.random() < 0.3
    late_fee = price * rc.LATE_FEE // 100 if late else 0
    total = nights * price + mini + late_fee
    deposit = r.choice([d for d in (0, 20, 30, 50) if d <= total])
    bill = total - deposit
    back = r.choice(rc.KEY_BACK)
    name = r.choice(rc.GUESTS)
    guest = guest_of(name)
    minilist = ', '.join(f'{label} {used[k]} ({"miễn phí" if p == 0 else f"{p} xu"})' for k, label, p in rc.MINIBAR if used[k])
    steps = [
        _step('checkout', 'key', 'choice', 'Nhận lại chìa', back[1].format(no=no), options=_opts(r, rc.KEY_OPTIONS)),
        _step('checkout', 'bill', 'number', 'Tính tiền trả phòng',
              f'Phòng {no} giá {price} xu/đêm, ở {nights} đêm. Minibar: {minilist or "không dùng gì"}. '
              f'{"Trả phòng 15:30 (sau 14:00)." if late else "Trả phòng 11:00."} Đã cọc {deposit} xu.', unit='xu'),
        _step('checkout', 'hold', 'choice', 'Khách gửi vali tới chiều', f'{name} gửi lại vali và túi xách tới 16:00 rồi mới ra bến.',
              options=_opts(r, rc.HOLD_OPTIONS)),
    ]
    key = {'checkout.key': back[2], 'checkout.bill': bill, 'checkout.hold': 'tag'}
    needs = dict(room=no, name=name, nights=nights, price=price, deposit=deposit, late=late, steps=steps, guest=guest)
    return needs, key, f'Trả phòng {no}', f'{name} trả phòng {no}. “Nhanh giùm nha em, xe tới rồi.”', rc.GUEST_NPC


# ---------------------------------------------------------------- Điều phối dọn phòng (rooms)
def _rooms(r, day, slot):
    rooms = r.sample(rc.ROOMS, 4)
    pool = [n for n in rc.HK_NOTES if n[0] not in ('lobby', 'none')]
    notes = r.sample(pool, 2)
    notes.append(rc.HK_NOTES[0] if r.random() < 0.6 else r.choice([n for n in pool if n not in notes]))
    notes.append(rc.HK_NOTES[-1] if r.random() < 0.5 else r.choice([n for n in pool if n not in notes]))
    r.shuffle(notes)
    plan = [dict(no=room['no'], note=n[0], label=n[1], at=n[2]) for room, n in zip(rooms, notes)]
    order = [p['no'] for p in sorted(plan, key=lambda p: p['at'])]
    rep = r.choice(rc.LAI_REPORT)
    check_no = order[0]
    steps = [
        _step('rooms', 'order', 'order', 'Sắp thứ tự dọn phòng',
              'Bốn phòng chưa dọn, cô Lài làm từng phòng một. ' + '; '.join(f'Phòng {p["no"]}: {p["label"].lower()}' for p in plan) + '.',
              options=[dict(id=p['no'], label=f'Phòng {p["no"]} · {p["label"]}') for p in plan]),
        _step('rooms', 'check', 'choice', 'Cô Lài báo xong phòng', f'Cô Lài báo phòng {check_no} xong. {rep[1]}', options=_opts(r, rc.LAI_OPTIONS)),
        _step('rooms', 'help', 'choice', 'Một mình cô Lài sáu phòng',
              'Còn ba phòng nữa mà cô Lài làm một mình. Na đang rảnh ở quầy, Khoa chiều mới vào ca.', options=_opts(r, rc.HELP_OPTIONS)),
    ]
    key = {'rooms.order': order, 'rooms.check': rep[2], 'rooms.help': 'na'}
    needs = dict(plan=plan, report=rep[0], steps=steps)
    return needs, key, 'Lịch dọn phòng sáng nay', 'Chị Quyên đưa bảng: “Bốn phòng chưa dọn, cô Lài một mình. Em xếp giùm chị phòng nào dọn trước.”', 0


# ---------------------------------------------------------------- Lịch dịch vụ (services)
def _services(r, day, slot):
    rooms = [x['no'] for x in r.sample(rc.ROOMS, 4)]
    grid = list(range(rc.SLOT_FROM, rc.SLOT_TO + 1, rc.SLOT_STEP))
    wake = r.choice([m for m in grid if m <= 7 * 60])
    trays = r.randint(1, 2)
    air = r.choice([m for m in grid if 5 * 60 + 15 <= m <= 7 * 60 + 30])
    travel = r.choice((30, 45, 60))
    flight = air + 90 + travel
    r.random()          # (kept: the draws after it stay as they were)
    has_bus = True      # the clash step is about two car trips: there is always a bus trip besides the airport one
    reqs = [dict(id='wake', room=rooms[0], text=f'Phòng {rooms[0]} nhờ gọi báo thức lúc {hhmm(wake)}.'),
            dict(id='tray', room=rooms[0], text=f'Phòng {rooms[0]} muốn {trays} khay ăn sáng mang lên phòng ngay sau báo thức.'),
            dict(id='air', room=rooms[1], text=f'Phòng {rooms[1]} bay chuyến {hhmm(flight)}, ra sân bay mất {travel} phút.')]
    key_plan = dict(wake=wake, tray=wake + 15, air=air)
    clash = 'none'
    fee = rc.FEES['tray'] * trays + rc.FEES['air']
    if has_bus:
        near = r.random() < 0.7
        bus = r.choice([m for m in grid if abs(m - air) < 80 and m != air] if near else [m for m in grid if abs(m - air) >= 80])
        btravel = r.choice((15, 30, 45))
        reqs.append(dict(id='bus', room=rooms[2], text=f'Phòng {rooms[2]} đi xe khách {hhmm(bus + 15 + btravel)} ở bến Mây, đi đường {btravel} phút.'))
        key_plan['bus'] = bus
        clash = 'second' if abs(bus - air) < 80 else 'none'
        fee += 20 if clash == 'second' else rc.FEES['bus']
    if r.random() < 0.5:
        w2 = r.choice([m for m in grid if m <= 8 * 60])
        reqs.append(dict(id='wake2', room=rooms[3], text=f'Phòng {rooms[3]} nhờ gọi báo thức lúc {hhmm(w2)}.'))
        key_plan['wake2'] = w2
    steps = [
        _step('services', 'plan', 'times', 'Xếp giờ trên lịch sáng mai',
              ' '.join(x['text'] for x in reqs) + ' Đặt mỗi việc vào đúng giờ theo quy định của quầy.',
              fields=[dict(id=x['id'], label=f'{rc.SERVICE_NAMES[x["id"]]} · phòng {x["room"]}') for x in reqs],
              low=rc.SLOT_FROM, high=rc.SLOT_TO, every=rc.SLOT_STEP),
        _step('services', 'clash', 'choice', 'Xe của anh Phát',
              'Anh Phát chỉ có một xe, một chuyến sân bay đi về mất 80 phút. Xem lại hai chuyến xe trên lịch.', options=_opts(r, rc.CLASH_OPTIONS)),
        _step('services', 'fee', 'number', 'Cộng phí dịch vụ vào hóa đơn',
              f'Báo thức miễn phí; khay ăn sáng {rc.FEES["tray"]} xu một khay; xe sân bay {rc.FEES["air"]} xu; xe bến xe {rc.FEES["bus"]} xu '
              '(gọi hãng Sông Mây thì 20 xu). Cộng tất cả phí của sáng mai.', unit='xu'),
    ]
    key = {'services.plan': key_plan, 'services.clash': clash, 'services.fee': fee}
    needs = dict(requests=reqs, steps=steps)
    return needs, key, 'Lịch dịch vụ sáng mai', 'Na đưa xấp giấy nhớ: “Khách nhờ đủ thứ cho sáng mai nè, anh chị xếp giùm em lên lịch.”', 2


# ---------------------------------------------------------------- Phàn nàn (complaint)
def _complaint(r, day, slot):
    cid = sorted(rc.COMPLAINTS)[r.randrange(len(rc.COMPLAINTS))]
    issue, rant, verify, (yes, no), pct, unit = rc.COMPLAINTS[cid]
    fault = r.random() < 0.65
    r.choice(rc.RATES)  # (kept: the draws after it stay as they were)
    room = r.choice(rc.ROOMS)['no']
    rate = rc.ROOM[room]['price']   # the compensation is a share of this room's own night
    comp = (8 if cid == 'charge' else rate * pct // 100) if fault else 0
    others = [rc.COMPLAINTS[k][0] for k in sorted(rc.COMPLAINTS) if k != cid]
    hear = [(cid, issue)] + [(f'x{i}', t) for i, t in enumerate(r.sample(others, 2))] + [('stairs', 'Cầu thang bộ xấu')]
    steps = [
        _step('complaint', 'hear', 'choice', 'Nghe ra điều thật sự sai', f'Khách phòng {room}: “{rant}” Điều khách cần khách sạn sửa là gì?',
              options=_opts(r, hear)),
        _step('complaint', 'verify', 'choice', 'Kiểm lại cho chắc', 'Trước khi hứa gì, kiểm đúng chỗ.', options=_opts(r, rc.VERIFY_OPTIONS)),
        _step('complaint', 'result', 'choice', 'Kết quả kiểm', yes if fault else no, options=_opts(r, rc.RESULT_OPTIONS)),
        _step('complaint', 'comp', 'number', 'Bù theo chính sách',
              f'Phòng {room} giá {rate} xu/đêm. Chính sách: ồn 10%, nước nóng 20%, khăn 10%, wifi 10% một đêm (lẻ thì bỏ phần lẻ); '
              f'minibar tính sai thì trả lại đúng số đã tính (2 lon × 4 xu); không phải lỗi khách sạn thì 0.', unit='xu'),
        _step('complaint', 'log', 'choice', 'Ghi lại', f'Việc cần báo: {unit.lower()}.', options=_opts(r, rc.LOG_OPTIONS)),
    ]
    key = {'complaint.hear': cid, 'complaint.verify': verify, 'complaint.result': 'fault' if fault else 'nofault',
           'complaint.comp': comp, 'complaint.log': 'log'}
    guest = guest_of(r.choice(rc.GUESTS))
    needs = dict(room=room, issue=cid, rate=rate, steps=steps, guest=guest)
    return needs, key, f'Phòng {room} xuống quầy phàn nàn', f'{guest["name"]}, khách phòng {room}, đập tay lên quầy: “{rant}”', rc.GUEST_NPC


# ---------------------------------------------------------------- Đồ thất lạc (lost)
def _lost(r, day, slot):
    item = sorted(rc.LOST)[r.randrange(len(rc.LOST))]
    name, colours, hidden, visible = rc.LOST[item]
    colour = r.choice(colours)
    route = r.sample(rc.PLACES, 4)
    start = 7 * 60 + 30
    times = [start + 20 * i for i in range(4)]
    k = r.randrange(3)
    search = sorted(p[0] for p in route[k:])
    before = route[0] if k > 0 else None
    entries = [dict(id='e1', text=f'{name} {colour} · nhặt ở {route[-1][1].lower()} lúc {hhmm(times[-1] + 15)}', ok=True)]
    entries.append(dict(id='e2', text=f'{name} {r.choice([c for c in colours if c != colour])} · nhặt ở {route[k][1].lower()} lúc {hhmm(times[k] + 10)}', ok=False))
    old_place = before[1].lower() if before else 'sảnh'
    entries.append(dict(id='e3', text=f'{name} {colour} · nhặt ở {old_place} lúc {hhmm(17 * 60 + 20 * k)} hôm qua', ok=False))
    r.shuffle(entries)
    walk = '; '.join(f'{hhmm(t)} {p[1].lower()}' for p, t in zip(route, times))
    owners = [(oid, label.format(hidden=hidden, visible=visible)) for oid, label in rc.OWNER_OPTIONS]
    steps = [
        _step('lost', 'where', 'multi', 'Lần theo đường khách đi',
              f'Sáng nay khách đi: {walk}. Ảnh chụp lúc {hhmm(times[k])} ở {route[k][1].lower()} còn thấy {name.lower()}. Chọn mọi chỗ cần tìm.',
              options=_opts(r, rc.PLACES)),
        _step('lost', 'match', 'choice', 'Đối chiếu sổ đồ thất lạc', f'Khách mất {name.lower()} {colour}. Sổ đồ thất lạc có ba dòng giống nhau.',
              options=[dict(id=e['id'], label=e['text']) for e in entries]),
        _step('lost', 'owner', 'choice', 'Trả đồ cho đúng người', 'Một người khác cũng ghé quầy hỏi đồ y như vậy.', options=_opts(r, owners)),
    ]
    key = {'lost.where': search, 'lost.match': next(e['id'] for e in entries if e['ok']), 'lost.owner': 'hidden'}
    if item == 'gau':   # Bé Su's own teddy: the child asks (one of the desk's people, her own portrait)
        guest = None
        opening = f'Bé Su mếu máo: “Cô chú ơi, {name.lower()} {colour} của con đâu mất rồi, sáng còn chụp hình với nó mà!”'
    else:
        guest = guest_of(r.choice(rc.GUESTS))
        opening = f'{guest["name"]}: “Em ơi, {name.lower()} {colour} của {_call(guest["gender"])} đâu mất rồi, sáng còn chụp hình với nó mà!”'
    needs = dict(item=item, name=name, colour=colour, route=[dict(id=p[0], label=p[1], at=hhmm(t)) for p, t in zip(route, times)], seen=k, steps=steps,
                 guest=guest)
    return needs, key, f'Khách tìm {name.lower()}', opening, 7 if item == 'gau' else rc.GUEST_NPC


BUILD = dict(arrival=_arrival, checkout=_checkout, rooms=_rooms, services=_services, complaint=_complaint, lost=_lost)


def kind_of(day: int, slot: int) -> str:
    return rc.ROTA[(day - 1 + slot) % len(rc.ROTA)]


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = kind_of(day, slot)
    needs, key, title, opening, npc = BUILD[kind](kit.rng(ID, day, slot), day, slot)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, gen=GEN, kind=kind, needs=needs, _key=key,
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work',
                         trial='none', branch='none', broke=[])


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def trial_brief(day: int, slot: int, trial: str) -> tuple[dict, list, dict]:
    """The trial check-in of (day, slot) for one trial part: (brief, steps, key). Pure."""
    needs, key, title, opening, npc = _arrival(kit.rng(ID, 'trial', day, slot, trial), day, slot, trial)
    needs = dict(needs, title=title, opening=opening, npc=kit.npc_id(ID, npc))
    return needs, needs['steps'], key


def _active(t: dict) -> tuple[dict, list, dict]:
    if t.get('trial') in rc.TRIALS:
        return trial_brief(t['day'], _slot(t), t['trial'])
    return t['needs'], t['needs']['steps'], t['_key']


def active_kind(t: dict) -> str:
    return 'arrival' if t.get('trial') in rc.TRIALS else t['kind']


def _quality(wrong: int) -> int:
    return max(QUALITY_FLOOR, 100 - WRONG_COST * wrong)


def _bonus(t: dict) -> int:
    kind = active_kind(t)
    bonus = max(3, round(rc.BONUS[kind] * t['quality'] / 100))
    b = t.get('branch', 'none')
    if b in rc.BRANCHES and kind in rc.BRANCHES[b][4]:
        bonus = round(bonus * rc.BRANCH_RATE[b])
    return bonus


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0, house=0)


def _trial0() -> dict:
    return dict(normal=0, early=0, group=0, done=0, fails=0, last=[])


def initial() -> dict:
    return dict(intro=False, today=_today(0),
                stats=dict(jobs=0, good=0, active_days=0, bonus=0, house=0, kinds={k: 0 for k in KINDS}),
                last_active_day=0, desk=kit.desk_initial(), rel={k: rc.REL_START for k in rc.CAST}, keeps=[],
                trial=_trial0(), branch='none', branch_day=0)


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def trial_left(d: dict) -> list[str]:
    tr = d['trial']
    return [] if tr['done'] else [k for k in rc.TRIAL_IDS if not tr[k]]


def _rel(d: dict, who: str, delta: int) -> None:
    d['rel'][who] = max(rc.REL_MIN, min(rc.REL_MAX, d['rel'][who] + int(delta)))


def _hook(s: dict, c: dict, key: str, v):
    """The desk scripts' own effects: rel, house, keep."""
    d = _data(c)
    if key == 'rel':
        moved = []
        for who, delta in v.items():
            if who in d['rel'] and delta:
                _rel(d, who, delta)
                moved.append(f'{rc.CAST_NAME[who]} {"quý bạn hơn" if delta > 0 else "hơi phật lòng"}')
        return ('(' + ', '.join(moved) + '.)') if moved else None
    if key == 'house':
        n = max(0, int(v))
        d['today']['house'] += n
        d['stats']['house'] += n
        return f'(Khách sạn tốn {n} xu.)' if n else None
    if key == 'keep':
        if v in rc.KEEPS and v not in d['keeps']:
            d['keeps'] = (d['keeps'] + [v])[-rc.KEEP_MAX:]
            return f'📒 Đã cất “{rc.KEEPS[v][1]}” vào Sổ nghề.'
    return None


def _rel_ok(d: dict, x: dict) -> bool:
    return (all(d['rel'].get(k, 0) >= n for k, n in (x.get('rel_min') or {}).items())
            and all(d['rel'].get(k, 100) <= n for k, n in (x.get('rel_max') or {}).items()))


def _scripts(d: dict) -> list:
    """The desk scripts that can fire now: the relation gates on top of the kit's marks."""
    return [x for x in rc.DESK if _rel_ok(d, x)]


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
            kit.need(len(got) == len(ids), 'Xếp đủ mọi phòng theo thứ tự nhé.')
            return list(got)
        return sorted(got)
    if typ == 'assign':
        cards = [x['id'] for x in st['cards']]
        targets = {x['id'] for x in st['targets']}
        kit.need(isinstance(value, dict) and set(value) == set(cards), 'Xếp đủ từng thẻ vào một chỗ nhé.')
        for k in cards:
            kit.need(isinstance(value[k], str) and value[k] in targets, 'Chỗ xếp không có trên bảng.')
        return {k: value[k] for k in sorted(cards)}
    fields = [f['id'] for f in st['fields']]
    kit.need(isinstance(value, dict) and set(value) == set(fields), 'Đặt giờ cho từng việc nhé.')
    out = {}
    for k in fields:
        m = kit.integer(value[k], st['low'], st['high'])
        kit.need((m - st['low']) % st['every'] == 0, 'Giờ trên lịch đi theo từng 15 phút.')
        out[k] = m
    return out


def _expected_keys(t: dict) -> list:
    rooms = t['work'].get('arrival.rooms') or {}
    return sorted(f'k{no}' for no in rooms.values())


def _check(t: dict, brief: dict, key: dict, st: dict, value) -> list[tuple[str, str]]:
    """[] when the value is right; else [(code, words)] (codes for the trial and the help line)."""
    sid = st['id']
    if sid == 'arrival.rooms':
        return rooms_problems(brief, value)
    if sid == 'arrival.cart':
        return cart_problems(brief, value)
    if sid == 'arrival.keys':
        want = _expected_keys(t)
        if value == want:
            return []
        wrong = [x for x in value if x not in want]
        miss = [x for x in want if x not in value]
        words = []
        if wrong:
            words.append('Có chìa không đúng phòng vừa xếp.')
        if miss:
            words.append(f'Còn thiếu {len(miss)} chìa.')
        return [('key', ' '.join(words))]
    if _same(value, key[sid]):
        return []
    code = 'note' if sid == 'arrival.note' else 'heard' if sid == 'arrival.need' else 'x'
    return [(code, '')]


HOW = {
    'checkout.bill': 'Số đêm × giá + minibar + phụ thu trả trễ (50% một đêm nếu sau 14:00) − tiền cọc.',
    'services.fee': 'Cộng phí từng việc trên lịch: khay × 8, xe sân bay 30, xe bến xe 15 (hãng Sông Mây 20), báo thức 0.',
    'services.plan': 'Khay = báo thức + 15 phút; xe sân bay = giờ bay − 1 tiếng 30 − đi đường; xe bến xe = giờ xe chạy − 15 phút − đi đường.',
    'complaint.comp': 'Lỗi có thật: giá một đêm × phần trăm của chính sách; minibar tính sai: trả lại số đã tính; không lỗi: 0.',
    'rooms.order': 'Khách đang chờ ở sảnh trước, rồi theo giờ khách tới, phòng chưa có khách sau cùng.',
    'lost.where': 'Tìm từ chỗ ảnh còn thấy đồ trở đi theo đường khách đi; chỗ trước đó thì đồ vẫn còn trên tay khách.',
    'arrival.need': 'Mỗi câu khách nói về chỗ ngủ là một yêu cầu; câu hỏi han, khen chê, nhờ vả việc khác thì không phải.',
    'arrival.note': 'Chỉ việc khách nhờ mà chưa làm (báo thức, gối, cọc, xe, két, bánh…) và việc dặn buồng phòng; việc đã xong ở quầy thì không.',
}


def _answer(t: dict, st: dict, key: dict) -> str:
    sid = st['id']
    if sid == 'arrival.rooms':
        names = {c['id']: c['label'] for c in st['cards']}
        return '; '.join(f'{names[k]} → phòng {v}' for k, v in key[sid].items())
    if sid == 'arrival.cart':
        return '; '.join(f'{rc.LUGGAGE_INDEX[k][0]} → {SHELF_NAME[v].split(" (")[0].lower()}' for k, v in key[sid].items())
    if sid == 'arrival.keys':
        return ', '.join(f'chìa {x[1:]}' for x in _expected_keys(t))
    if st['type'] == 'times':
        names = {f['id']: f['label'] for f in st['fields']}
        return '; '.join(f'{names[k]} {hhmm(v)}' for k, v in key[sid].items())
    return kit.answer_text(st, key[sid])


def _help(t: dict, st: dict, key: dict, problems: list) -> str:
    sid = st['id']
    if kit.tries_on_step(t.get('lines')) + 1 >= kit.REVEAL_AFTER:
        return f'Chị Quyên chỉ: {_answer(t, st, key).rstrip(".")}.'
    words = ' '.join(w for _, w in problems if w)
    return (words + ' ' if words else '') + HOW.get(sid, 'Đọc lại lời khách và sổ quy trình rồi làm lại bước này.')


def _trial_code(code: str) -> str | None:
    return dict(cap='cap', need='need', near='need', dirty='need', busy='need', same='cap', heard='need', note='note').get(code)


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('rc_intro', 'rc_step', 'rc_desk', 'rc_branch'), 'Thao tác lễ tân không hợp lệ.')
    d = _data(c)
    if name == 'rc_intro':
        d['intro'] = True
        left = trial_left(d)
        line = 'Chị Quyên: “Ba ca thử việc trước nha: một khách thường, một khách tới sớm, một nhóm hai yêu cầu.”' if left else \
            'Chị Quyên đưa sổ giao ca: “Vào ca thôi em.”'
        return dict(message=line)
    if name == 'rc_branch':
        return _branch(s, c, d, p)
    desk = d['desk']
    if name == 'rc_desk':
        return kit.desk_choose(s, c, ID, desk, rc.DESK, p.get('option'), _hook)
    kit.desk_block(desk, 'Có chuyện ở quầy, quyết xong rồi làm tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu việc trước khi làm nhé.')
    brief, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    problems = _check(t, brief, key, st, value)
    if problems:
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        for code, _ in problems:
            if code in BROKE_CODES and code not in t['broke']:
                t['broke'].append(code)
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        message = f'Chưa đúng: {st["title"].lower()}. {_help(t, st, key, problems)}'
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
    return _finish(s, c, d, t)


def _finish(s: dict, c: dict, d: dict, t: dict) -> dict:
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= 90
    kind = active_kind(t)
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    if good:
        d['stats']['kinds'][kind] += 1
    post = rc.POSTS[kind]
    extra = ''
    if t.get('trial') in rc.TRIALS:
        extra = ' ' + _trial_done(s, c, d, t)
    kit.complete(s, c, t, bonus, f'Xong việc {post[0].lower()}: chất lượng {t["quality"]}%.')
    _guest_review(c, t)
    result = dict(message=f'Xong việc {post[0].lower()}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.{extra}'.strip(), correct=good, celebrate=good)
    _after(s, c, d, result)
    return result


def _guest_review(c: dict, t: dict) -> None:
    """A job about a passing guest: the review on the feed is signed by that guest (not by the NPC the job is filed
    under), and a passer-by does not come back tomorrow as that NPC (the engine's return note is dropped)."""
    g = _active(t)[0].get('guest')
    if not (isinstance(g, dict) and g.get('name')):
        return
    for post in c['feed']:
        if post.get('source') == t['id'] and post.get('kind') == 'review':
            post['author'] = g['name']
    c['pending'] = [x for x in c['pending'] if not (x.get('kind') == 'return_note' and x.get('ref') == t['id'])]


def trial_misses(t: dict) -> list[str]:
    """The trial's parts this job missed: 'cap', 'need', 'note' (first-time rule, read from the task's own record)."""
    out = []
    for code in t.get('broke') or []:
        part = _trial_code(code)
        if part and part not in out:
            out.append(part)
    if 'arrival.need' in t.get('errors', []) and 'need' not in out:
        out.append('need')
    if 'arrival.note' in t.get('errors', []) and 'note' not in out:
        out.append('note')
    return [x for x in ('cap', 'need', 'note') if x in out]


def _trial_done(s: dict, c: dict, d: dict, t: dict) -> str:
    tr = d['trial']
    part = t['trial']
    miss = trial_misses(t)
    if not miss:
        tr[part] = c['day']
        tr['last'] = []
        left = trial_left(d)
        if not left:
            tr['done'] = c['day']
            _rel(d, 'quyen', 6)
            kit.log(s, c, 'job', '🎉 Qua ca thử việc lễ tân Hoa Sứ.')
            return 'Chị Quyên ký sổ: “Qua thử việc rồi đó. Từ mai em đứng quầy chính.” 🎉'
        names = ', '.join(rc.TRIALS[k][0].lower() for k in left)
        return f'Đạt phần “{rc.TRIALS[part][0].lower()}”, giữ kết quả. Còn: {names}.'
    tr['fails'] += 1
    tr['last'] = miss
    keep = [rc.TRIALS[k][0].lower() for k in rc.TRIAL_IDS if tr[k]]
    practise = ' '.join(rc.PRACTICE[m] for m in miss)
    kept = f' Giữ phần đã đạt: {", ".join(keep)}.' if keep else ''
    return f'Phần “{rc.TRIALS[part][0].lower()}” chưa đạt, mai làm lại. Luyện thêm: {practise}{kept}'


def _branch(s: dict, c: dict, d: dict, p: dict) -> dict:
    from .. import promotion
    b = p.get('branch')
    kit.need(b in rc.BRANCHES, 'Hướng đi không có trong danh sách.')
    kit.need(promotion.rank(s, c, ID) >= rc.BRANCH_FROM, f'Lên bậc {rc.BRANCH_FROM} ở Thăng tiến rồi mới chọn hướng đi nhé.')
    kit.need(b != d['branch'], 'Bạn đang đi hướng này rồi.')
    kit.need(d['branch'] == 'none' or c['day'] - d['branch_day'] >= 7, 'Đổi hướng đi được sau 7 ngày làm việc.')
    d['branch'], d['branch_day'] = b, c['day']
    emoji, label, title, note, _ = rc.BRANCHES[b]
    kit.log(s, c, 'job', f'{emoji} Chọn hướng {label.lower()}: {title}.')
    return dict(message=f'{emoji} Hướng {label.lower()}: {title}. {note}', celebrate=True)


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, _scripts(d), None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(rc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new job carries its trial part (while the trial is not passed) and the branch it was taken under."""
    if t.get('career') != ID or t.get('status') != 'new' or t.get('at') != 0:
        return
    d = _data(c)
    left = trial_left(d)
    taken = {x.get('trial') for x in c['tasks'] if x.get('career') == ID and x is not t and x['status'] not in ('completed', 'referred', 'cancelled')}
    part = next((k for k in left if k not in taken), None)
    t['trial'] = part or 'none'
    t['branch'] = d['branch'] if not left else 'none'


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], _scripts(d), None, c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], rc.DESK, _hook)
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    lines = [f'Hoa Sứ: {today["jobs"]} việc xong, {today["good"]} việc đạt từ 90%. Thưởng: {today["bonus"]} xu.']
    if today['house']:
        lines.append(f'Các quyết định ở quầy hôm nay tốn của khách sạn {today["house"]} xu.')
        if today['house'] > 50:
            _rel(d, 'quyen', -3)
            lines.append('Chị Quyên nhắc: “Quỹ khách sạn không phải để dập lửa kiểu đó hoài nha em.”')
    left = trial_left(d)
    if left:
        lines.append('🧪 Ca thử việc còn: ' + ', '.join(rc.TRIALS[k][0].lower() for k in left) + '.')
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Ngày có việc đạt từ 90% mới ghi vào hành trình nghề.')


def known_request(c: dict, t: dict) -> str:
    post = rc.POSTS[active_kind(t)]
    if t.get('trial') in rc.TRIALS:
        brief, _, _ = _active(t)
        return f'🧪 Ca thử việc · {rc.TRIALS[t["trial"]][0]}: {brief["opening"]}'
    return f'{post[1]} {post[0]}: {t["opening"]}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết khách cần gì.'
    _, steps, _ = _active(t)
    if t['at'] >= len(steps):
        return 'Việc đã xong; nhận việc tiếp theo.'
    return HOW.get(steps[t['at']]['id']) or steps[t['at']]['evidence']


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Chăm khách', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    kind = active_kind(t)
    if not t['known']:
        v['needs'] = None
    else:
        brief, _, _ = _active(t)
        v['needs'] = deepcopy(brief)
        if kind == 'arrival':
            heard = 'arrival.need' in t['work']
            for card in v['needs']['cards']:
                if not heard:
                    card['tags'] = []      # what the guest needs is the first step: read it from what they say
            v['needs']['rooms'] = [dict(r, beds_label=rc.BEDS[r['beds']]) for r in rc.ROOMS]
    if t.get('trial') in rc.TRIALS:   # a trial check-in shows its own guest (the stored job keeps its slot's facts)
        brief, _, _ = _active(t)
        v['title'], v['opening'], v['npc'] = brief['title'], brief['opening'], brief['npc']
    g = _active(t)[0].get('guest')
    v['guest'] = deepcopy(g) if isinstance(g, dict) else None
    if v['needs']:
        for k in ('issue', 'seen'):   # the complaint's real issue and where the lost thing was last seen are step answers
            v['needs'].pop(k, None)
    post = rc.POSTS[kind]
    v['post'] = dict(id=kind, label=post[0], emoji=post[1], work=post[2])
    v['trial_info'] = dict(id=t['trial'], title=rc.TRIALS[t['trial']][0], note=rc.TRIALS[t['trial']][1]) if t.get('trial') in rc.TRIALS else None
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    kinds = sum(1 for k in KINDS if stats['kinds'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and kinds >= m['kinds']) for m in rc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, kinds=kinds)
    d['desk'] = kit.desk_public(d['desk'], rc.DESK, ID, c)
    d['cast'] = [dict(id=k, name=rc.CAST_NAME[k], role=rc.CAST_ROLE[k], rel=d['rel'][k], npc=kit.npc_id(ID, rc.CAST_NPC[k])) for k in rc.CAST]
    d['keepsakes'] = [dict(id=k, emoji=rc.KEEPS[k][0], name=rc.KEEPS[k][1], desc=rc.KEEPS[k][2]) for k in d['keeps'] if k in rc.KEEPS]
    tr = d['trial']
    d['trial_view'] = dict(done=tr['done'], parts=[dict(id=k, title=rc.TRIALS[k][0], note=rc.TRIALS[k][1], passed=bool(tr[k])) for k in rc.TRIAL_IDS],
                           practise=[rc.PRACTICE[m] for m in tr['last']])
    b = d['branch']
    d['branch_view'] = dict(id=b, can_change_day=(d['branch_day'] + 7) if b != 'none' else 0,
                            info=(dict(emoji=rc.BRANCHES[b][0], label=rc.BRANCHES[b][1], title=rc.BRANCHES[b][2], note=rc.BRANCHES[b][3]) if b in rc.BRANCHES else None))
    return d


def content() -> dict:
    return dict(
        notebook=rc.NOTEBOOK,
        posts=[dict(id=k, label=v[0], emoji=v[1], work=v[2]) for k, v in rc.POSTS.items()],
        rooms=[dict(r, beds_label=rc.BEDS[r['beds']]) for r in rc.ROOMS], near=[list(x) for x in rc.NEAR],
        tags={k: v[0] for k, v in rc.TAGS.items()}, status=rc.STATUS, shelves=[dict(id=k, label=l, cap=n) for k, l, n in rc.SHELVES],
        branches=[dict(id=k, emoji=v[0], label=v[1], title=v[2], note=v[3]) for k, v in rc.BRANCHES.items()], branch_from=rc.BRANCH_FROM,
        trials=[dict(id=k, title=v[0], note=v[1]) for k, v in rc.TRIALS.items()],
        intro=dict(title='Một ca ở quầy lễ tân Hoa Sứ',
                   lead='Khách sạn nhỏ sáu phòng trên phố Hoa Sứ. Bạn đứng quầy: nhận khách, xếp phòng, giao chìa, lo hành lý, xếp lịch dọn phòng và dịch vụ, '
                        'nghe phàn nàn, tìm đồ thất lạc, trả phòng. Ba ca đầu là ca thử việc với chị Quyên.',
                   work=[['🛎️', 'Hiểu khách, xếp phòng, giao chìa'], ['🧳', 'Xe hành lý, lịch dọn phòng, lịch dịch vụ'], ['😤', 'Phàn nàn, đồ thất lạc, trả phòng']],
                   meet=[['📒', 'Chị Quyên trưởng ca'], ['😏', 'Khoa ca chiều, hay nhận công'], ['🐈', 'Mèo Bơ, không phải quản lý']],
                   stars=[['✓', 'Đọc kỹ lời khách: mỗi câu là một yêu cầu'], ['✓', 'Đủ người, đủ yêu cầu, phòng sạch mới giao'],
                          ['✓', 'Sổ giao ca chỉ ghi việc còn dở']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu lễ tân bị thay đổi: ' + k)
    kit.need(t.get('trial') in ('none',) + rc.TRIAL_IDS, 'Ca thử việc của phiếu không hợp lệ.')
    kit.need(t.get('branch') in rc.BRANCH_IDS, 'Hướng đi của phiếu không hợp lệ.')
    brief, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu lễ tân sai.')
    kit.need(at == 0 or t['known'], 'Chưa đọc phiếu việc.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    probe = dict(t, work={})
    for st in steps[:at]:
        value = work[st['id']]
        kit.need(_value(st, value) == value and not _check(probe, brief, key, st, value), 'Kết quả bước lễ tân sai.')
        probe['work'][st['id']] = value
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi lễ tân sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi lễ tân sai.')
    broke = t.get('broke')
    kit.need(isinstance(broke, list) and len(broke) == len(set(broke)) and set(broke) <= set(BROKE_CODES), 'Lỗi xếp phòng sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(not broke or errors, 'Lỗi xếp phòng sai.')
    kit.need(t.get('quality') == _quality(wrong), 'Điểm chất lượng lễ tân không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (_bonus(t) if at == len(steps) else 0), 'Tiền thưởng lễ tân không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= 24 and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký lễ tân sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Phiếu lễ tân chưa xong mà đã hoàn tất.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ lễ tân sai.')
    kit.need(type(d['intro']) is bool, 'Giới thiệu lễ tân sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    kit.integer(d['branch_day'], 0, 10**7)
    kit.need(d['branch'] in rc.BRANCH_IDS, 'Hướng đi lễ tân sai.')
    kit.need(isinstance(d['today'], dict) and set(d['today']) == set(base['today']), 'Số liệu lễ tân sai.')
    for v in d['today'].values():
        kit.integer(v, 0, 10**9)
    kit.integer(d['today']['counted'], 0, 1)
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu lễ tân sai.')
    for k, v in st.items():
        if k != 'kinds':
            kit.integer(v, 0, 10**9)
    kit.need(isinstance(st['kinds'], dict) and set(st['kinds']) == set(KINDS), 'Số liệu việc lễ tân sai.')
    for v in st['kinds'].values():
        kit.integer(v, 0, 10**9)
    for bucket in (d['today'], st):
        kit.need(bucket['good'] <= bucket['jobs'], 'Số việc đạt chuẩn sai.')
    kit.need(sum(st['kinds'].values()) == st['good'] and st['active_days'] <= st['good'] and d['today']['house'] <= st['house'],
             'Tiến trình nghề lễ tân sai.')
    kit.need(isinstance(d['rel'], dict) and set(d['rel']) == set(rc.CAST), 'Quan hệ đồng nghiệp sai.')
    for v in d['rel'].values():
        kit.integer(v, rc.REL_MIN, rc.REL_MAX)
    kit.need(isinstance(d['keeps'], list) and len(d['keeps']) <= rc.KEEP_MAX and len(set(d['keeps'])) == len(d['keeps'])
             and all(k in rc.KEEPS for k in d['keeps']), 'Sổ nghề lễ tân sai.')
    tr = d['trial']
    kit.need(isinstance(tr, dict) and set(tr) == set(_trial0()), 'Ca thử việc sai.')
    for k in rc.TRIAL_IDS + ('done', 'fails'):
        kit.integer(tr[k], 0, 10**7)
    kit.need(isinstance(tr['last'], list) and len(tr['last']) <= 3 and set(tr['last']) <= set(rc.PRACTICE), 'Ca thử việc sai.')
    kit.need(not tr['done'] or all(tr[k] for k in rc.TRIAL_IDS), 'Ca thử việc chưa đủ phần mà đã qua.')
    kit.desk_validate(d['desk'], rc.DESK)


SPEC = dict(
    id=ID, prefix='rc_', category='service', people=PEOPLE,
    meta=dict(short='Lễ tân', place='Khách sạn Hoa Sứ', tagline='Đúng phòng, đúng chìa, khách về còn nhớ.', icon='lock',
              color='#b0546f', light='#fbecef', weather='Hoa sứ rụng trước cửa sảnh', work='Phiếu việc', station='Quầy lễ tân & bảng phòng',
              greeting='Chị Quyên đặt sổ giao ca lên quầy: “Đọc lời khách cho kỹ, sổ ghi cho rõ.”',
              caption='Sáu phòng, một quầy, trăm chuyện', map_label='KHÁCH SẠN HOA SỨ'),
    staff=[('Chị Quyên', 'desk', 'Trưởng ca lễ tân, nhớ hết từng dòng sổ giao ca.', 86, 88), ('Cô Lài', 'rooms', 'Buồng phòng, một mình lo sáu phòng.', 78, 90)],
    roles={'desk': 'Lễ tân', 'rooms': 'Buồng phòng'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🛎️', 'Một ca ở quầy Hoa Sứ', [('Nhận khách', 'Đúng phòng, đúng chìa'), ('Dọn phòng', 'Phòng nào trước'),
                                              ('Dịch vụ', 'Đúng giờ'), ('Phàn nàn', 'Kiểm rồi mới bù')],
              ['Đọc lời khách', 'Xếp phòng trên bảng', 'Giao chìa, xếp hành lý', 'Ghi sổ giao ca']),
    stories=[('Bảng móc chìa', ('Bảng móc chìa gỗ sau quầy có mười móc, ba cái không phải chìa phòng.', 'Bạn đếm lại chìa, ghi giờ ca vào sổ.',
                                'Chị Quyên gõ nhẹ vào móc đỏ: “Cái này là kho khăn. Nhớ chưa?”'))],
    review_asides=['Lễ tân nghe một lần là nhớ hết mình cần gì.', 'Phòng đúng ý, chìa đúng số, hành lý lên tận nơi.', 'Phàn nàn là có người kiểm liền, bù đàng hoàng.'],
    situations=[],
    more_line='Thêm một phiếu việc vừa tới quầy.', open_line='Chị Quyên mở quầy; bảng phòng, bảng móc chìa và sổ giao ca đã sẵn.',
    guide='Ca lễ tân: nhận khách (hiểu nhu cầu → xếp phòng → giao chìa → xếp hành lý → ghi sổ giao ca), trả phòng, điều phối dọn phòng, lịch dịch vụ sáng mai, '
          'phàn nàn và đồ thất lạc. Ba ca đầu là ca thử việc. Sai bước thì sửa ngay, thưởng giảm theo chất lượng.',
    employment=dict(
        postings=[dict(id='rc-hoasu', org='Khách sạn Hoa Sứ', kind='company', title='Nhân viên lễ tân', salary=(50, 64), probation_days=3,
                       wants=['communication', 'careful', 'calm'], boss='chị Quyên', stages=['cv', 'interview', 'trial'],
                       trial_title='ca thử việc ở quầy',
                       perks=['Chị Quyên kèm ca thử việc', 'Thưởng nhỏ mỗi việc', 'Lương ca theo hợp đồng'],
                       culture='Khách sạn nhỏ: lời khách nói là yêu cầu, sổ giao ca là luật, mèo Bơ không phải quản lý.',
                       questions=['rc_iv_listen', 'mistake'], trial=['rc_tr_normal', 'rc_tr_early', 'rc_tr_group'], reference=False)],
        questions={
            'rc_iv_listen': dict(text='Khách nói một tràng dài, vừa than vừa kể. Bạn làm gì đầu tiên?', options=[
                dict(id='listen', label='Nghe hết, ghi lại từng yêu cầu, nhắc lại cho khách xác nhận', score=3, note='Chị Quyên gật: “Nghe ra yêu cầu là nửa việc rồi.”'),
                dict(id='fast', label='Cắt ngang, đưa luôn phòng trống đầu tiên', score=0, note='Chị Quyên nhíu mày.'),
                dict(id='boss', label='Gọi trưởng ca ra nghe giùm', score=1, note='Được, nhưng quầy là chỗ của bạn.')]),
            'rc_tr_normal': dict(text='Ca thử việc 1: khách một mình, ngủ nông, mang vali to. Bảng còn 101 (sạch, ồn, có hốc vali), 202 (sạch, yên, không hốc vali), 203 (chưa dọn).', options=[
                dict(id='ask', label='Hỏi khách điều nào quan trọng hơn, đề xuất 101 kèm nút bịt tai hoặc 202 kèm cất vali ở kho', score=3, note='Chị Quyên: “Không có phòng hoàn hảo thì cho khách chọn rõ ràng.”'),
                dict(id='dirty', label='Giao 203 luôn, dọn sau', score=0, note='Chị Quyên dừng lại: “Phòng chưa dọn là chưa giao.”', fatal=True),
                dict(id='first', label='Đưa 101 vì gần quầy', score=1, note='Khách ngủ không yên.')]),
            'rc_tr_early': dict(text='Ca thử việc 2: khách tới 10 giờ, nhận phòng 14 giờ, phòng còn chưa dọn.', options=[
                dict(id='hold', label='Giữ hành lý, mời trà, nhờ buồng phòng dọn phòng đó trước, hẹn giờ gọi khách', score=3, note='Chị Quyên ghi điểm: “Khách chờ mà vẫn thấy được lo.”'),
                dict(id='out', label='Bảo khách đi chơi, 14 giờ quay lại', score=1, note='Đúng giờ, nhưng khách kéo vali đi khắp phố.'),
                dict(id='fee', label='Thu phụ thu nhận phòng sớm rồi mới tính', score=0, note='Phòng còn chưa dọn mà đã thu tiền.')]),
            'rc_tr_group': dict(text='Ca thử việc 3: một nhà hai phòng, bà ngoại cần tầng trệt, hai phòng phải sát vách, còn nhờ gọi báo thức 5:30.', options=[
                dict(id='both', label='Xếp hai phòng tầng trệt sát vách, ghi báo thức 5:30 vào sổ giao ca', score=3, note='Chị Quyên: “Đủ cả hai yêu cầu, ca sau khỏi hỏi.”'),
                dict(id='one', label='Xếp đúng tầng trệt, quên ghi báo thức', score=1, note='Sáng ra không ai gọi bà ngoại dậy.'),
                dict(id='far', label='Hai phòng hai tầng cho nhanh', score=0, note='Bà ngoại phải leo cầu thang tìm con.')]),
        }),
)
