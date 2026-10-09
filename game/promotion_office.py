"""🏢 Phòng điều hành: the executive steps of a long ladder (game/promotion.py, F#193).

A pilot from Phó Giám đốc Khối khai thác bay (step 5) and a teacher at Hiệu trưởng (step 5) run a small
department beside their own working day. Three things happen in the office, all of them the player's own taps:

* 🗓️ Điều phối: today's slots (the pilot: the day's rotations, a hard one needs a captain; at Phó Tổng Giám đốc
  also the cabin, dispatch and ramp duties; the principal: cover lessons, exam rooms, the gifted class…). Tap a
  slot, tap a person. Somebody who worked three days running must rest (the legal duty limit), a suspended
  person stays home. What the player leaves empty the assistant fills at the close, worse, and with no bonus;
  a slot nobody may take is cancelled.
* 👥 Nhân sự: talk, praise, remind, warn, hold a review, suspend, promote, demote, raise or cut a pay grade. Each
  person keeps a hidden trait (proud, lazy, eager, steady, fragile, veteran): the same decision lands very
  differently. A private talk reveals it. A decision with a reason (an open fault, earned merit) helps; one
  without hurts the person and the room. Someone pushed too far hands in their notice and a newcomer starts.
* 📥 Việc cần quyết: one or two awkward demands a day (a VIP who wants the plane held, the commercial office
  wanting a crew past its hours, a parent with an envelope…). Giving in is never rewarded. Left undecided, the
  last (worst) option happens at the close.

The close (end_day) turns all of it into the department's figures: on-time rate, complaints, morale and the
salary bill against the budget, and pays a small 🏢 bonus when the player ran the board themselves.

State: journey['promo'][career]['office'] (optional; older builds keep the record's extra keys and ignore them).
Everything random is rolled from (seed, career, day, …).
"""
from __future__ import annotations

import random

TRAITS = ('proud', 'lazy', 'eager', 'steady', 'fragile', 'veteran')
TRAIT_HINT = {
    'proud': 'Tự trọng cao: góp ý riêng thì nghe, bị nói nặng là tự ái.',
    'lazy': 'Hay “lươn”: khen suông là lờn, nhắc đúng lỗi thì sửa nhanh.',
    'eager': 'Cầu tiến: mê được thăng chức, bị giáng chức là muốn nghỉ.',
    'steady': 'Chăm, ít nói: ít phản ứng, làm quá sức thì âm thầm đuối.',
    'fragile': 'Nhạy cảm: bị phê bình là buồn lâu, được hỏi han là lên tinh thần.',
    'veteran': 'Kỳ cựu: tay nghề chắc, ghét bị nhắc khi mình không sai.',
}
MULT = {'proud': (1.0, 1.6), 'lazy': (1.0, .6), 'eager': (1.3, 1.2), 'steady': (.8, .6), 'fragile': (1.2, 1.7), 'veteran': (.8, 1.3)}
REACT = {   # (pleased, stung, hurt)
    'proud': ('{n} gật đầu, ngẩng cao hơn hẳn.', '{n} mím môi, không nói gì.', '{n} đỏ mặt, bỏ ra ngoài một lúc lâu.'),
    'lazy': ('{n} cười tươi: “Dạ, em biết mà!”', '{n} gãi đầu: “Dạ dạ, em sửa liền.”', '{n} lầm bầm: “Có gì đâu mà căng…”'),
    'eager': ('{n} sáng mắt: “Em sẽ không làm sếp thất vọng!”', '{n} hơi chùng xuống nhưng xin góp ý thêm.', '{n} hỏi thẳng: “Vậy em còn tương lai ở đây không?”'),
    'steady': ('{n} gật nhẹ, quay lại làm việc.', '{n} “Dạ.” rồi im lặng.', '{n} im lặng, ánh mắt mệt mỏi.'),
    'fragile': ('{n} rưng rưng: “Cảm ơn sếp đã hỏi.”', '{n} cúi mặt, giọng run run.', '{n} khóc ở phòng nghỉ, cả nhóm xì xào.'),
    'veteran': ('{n} cười: “Lâu rồi mới có sếp hiểu chuyện.”', '{n} nhíu mày: “Tôi làm nghề này hai mươi năm rồi đấy.”', '{n} nói to: “Cứ thế này thì ai làm nổi!”'),
}

# ------------------------------------------------------------------------------------- personnel decisions
BASIC = ('talk', 'praise', 'remind', 'warn', 'review')
FULL = BASIC + ('suspend', 'promote', 'demote', 'raise', 'cut')
ACTS = {
    'talk': dict(icon='💬', label='Nói chuyện riêng'),
    'praise': dict(icon='👏', label='Khen trước nhóm'),
    'remind': dict(icon='⚠️', label='Nhắc nhở'),
    'warn': dict(icon='🟠', label='Cảnh cáo'),
    'review': dict(icon='📝', label='Kiểm điểm'),
    'suspend': dict(icon='🔴', label='Kỷ luật: đình chỉ'),
    'promote': dict(icon='⬆️', label='Thăng chức'),
    'demote': dict(icon='⬇️', label='Giáng chức'),
    'raise': dict(icon='💰', label='Tăng bậc lương'),
    'cut': dict(icon='📉', label='Hạ bậc lương'),
    # Org ladders (game/org.py): khiển trách and điều động between the unit's teams. No pilot or teacher power has them.
    'reprimand': dict(icon='🟡', label='Khiển trách'),
    'move': dict(icon='🔀', label='Điều động'),
}
# (target mood with a reason, without; the room's mood without a reason; complaints without a reason)
FX = {
    'talk': (6, 6, 0, 0),
    'praise': (8, 4, -3, 0),
    'remind': (-4, -10, -2, 0),
    'warn': (-8, -14, -4, 0),
    'review': (-10, -18, -5, 0),
    'suspend': (-16, -25, -6, 2),
    'promote': (18, 10, -6, 0),
    'demote': (-22, -30, -8, 1),
    'raise': (12, 8, -4, 0),
    'cut': (-12, -20, -6, 1),
    'reprimand': (-6, -12, -3, 0),
    'move': (4, -12, -3, 0),
}
MARK_LABEL = ('', 'Đã nhắc nhở', 'Đã cảnh cáo', 'Đã kiểm điểm')
QUIT_AT = 8           # mood at or below which a person hands in their notice
DUTY_MAX = 3          # days in a row; then a day of rest (the legal limit)
TIRED_AT = 2          # days in a row already worked: 50% 🥱 at day_roll, −12 to each slot's chance in close (−15 more when 🥱)
HARD_LEGS = 2         # the pilot's day: at most this many of the 4 legs need a captain (fewer when fewer captains are free)
CAPTAINS_MIN = 2      # F#223: the pilot office never opens a day with fewer captains than this
GOOD_SCORE = 60   # a day's office score that counts as a good office day (the step's 'office' requirement)
PAY_MAX = 7
STAFF_MAX = 12
LOG_MAX = 6

# ------------------------------------------------------------------------------------- careers
OFFICE = {
    'pilot': dict(
        name='Phòng điều hành bay', unit='chặng', plan='Điều phối chuyến bay',
        kpi=('Đúng giờ', 'Phàn nàn', 'Tinh thần', 'Quỹ lương'),
        roles={
            'pl': dict(label='Phi công', ladder=('Cơ phó cấp thấp', 'Cơ phó cao cấp', 'Cơ trưởng', 'Cơ trưởng Huấn luyện'), pay=40),
            'fa': dict(label='Tiếp viên', ladder=('Tiếp viên', 'Tiếp viên phó', 'Tiếp viên trưởng'), pay=26),
            'op': dict(label='Điều phái', ladder=('Điều phái viên', 'Điều phái chính', 'Trưởng ca điều phái'), pay=24),
            'en': dict(label='Kỹ thuật', ladder=('Thợ máy', 'Thợ máy chính', 'Kỹ sư trưởng ca'), pay=28),
        },
        roster=(('Anh Quân', 'pl', 3, 5, 88, 70), ('Chị Hạnh', 'pl', 2, 4, 78, 66), ('Anh Bảo', 'pl', 2, 3, 70, 60),
                ('Anh Tín', 'pl', 1, 2, 62, 72), ('Bạn Khoa', 'pl', 0, 1, 48, 74), ('Bạn Vy', 'pl', 0, 1, 55, 68)),
        extra=(('Chị Mai', 'fa', 2, 4, 80, 70), ('Bạn Ly', 'fa', 0, 1, 50, 72), ('Anh Phát', 'op', 1, 3, 68, 64),
               ('Chị Diệp', 'op', 0, 1, 52, 70), ('Chú Sơn', 'en', 2, 4, 82, 60), ('Anh Đạt', 'en', 1, 2, 64, 66)),
        all_from=7,   # Phó Tổng Giám đốc: every member of staff in the airline, not only the pilots
        hires=('Bạn Minh', 'Bạn Phong', 'Bạn Nhi', 'Bạn Hưng', 'Bạn Trâm', 'Bạn Lâm'),
        # F#223: a captain who quits is replaced by a captain (transferred from another base), and the base never runs
        # with fewer than CAPTAINS_MIN captains (day_roll tops it up); the hard legs follow the captains free today.
        keep_lv=2, cap_hires=('Anh Hòa', 'Chị Thu', 'Anh Định', 'Chị Quyên', 'Anh Khang', 'Chị Ngọc'),
        issues=dict(late='⏰ Báo danh trễ', slip='📋 Bỏ sót một dòng checklist', rude='😤 Khách phàn nàn thái độ', tired='🥱 Mệt, xin đổi ca'),
        powers={5: BASIC + ('promote',), 6: FULL, 7: FULL}, acts={5: 4, 6: 5, 7: 6}, cap={5: 30, 6: 40, 7: 50}, inbox={5: 1, 6: 2, 7: 2},
        cancel='hủy vì thiếu tổ bay', rest='Đã làm 3 ngày liền: theo quy định giờ bay phải nghỉ hôm nay.',
    ),
    'teacher': dict(
        name='Phòng hiệu trưởng', unit='việc', plan='Phân công trong ngày',
        kpi=('Việc đạt', 'Phụ huynh phàn nàn', 'Tinh thần', 'Quỹ lương'),
        roles={'gv': dict(label='Giáo viên', ladder=('Giáo viên', 'GV giỏi cấp trường', 'Tổ phó chuyên môn', 'Tổ trưởng chuyên môn'), pay=22)},
        roster=(('Cô Hoa', 'gv', 3, 5, 85, 68), ('Thầy Nam', 'gv', 2, 4, 74, 62), ('Cô Lan', 'gv', 1, 3, 66, 70),
                ('Cô Thảo', 'gv', 1, 2, 60, 74), ('Thầy Duy', 'gv', 0, 1, 50, 72), ('Cô Ngân', 'gv', 0, 1, 45, 76)),
        extra=(), all_from=99,
        hires=('Cô Yến', 'Thầy Khải', 'Cô My', 'Thầy Tú', 'Cô Diệu', 'Thầy Hiếu'),
        issues=dict(late='⏰ Lên lớp trễ', slip='📒 Thiếu giáo án', rude='😤 Phụ huynh phản ánh nặng lời với học sinh', tired='🥱 Quá tải, xin bớt việc'),
        powers={5: FULL}, acts={5: 5}, cap={5: 30}, inbox={5: 2},
        cancel='bỏ trống, phụ huynh phàn nàn', rest='Đã gánh việc 3 ngày liền: cho nghỉ một hôm đã.',
    ),
}
# 👮 Org ladders (game/org.py, org_content.ORGS[...]['office']): keyed by the org, not the career. Levels are the post's
# office level (org_content posts' olv): 1 Tổ trưởng, 2 Đội 113, 3 Ban chỉ huy CA phường / Phòng PC06, 4 Trợ lý BGĐ
# (kiểm tra điều lệnh, game/org.py inspect), 5 Phó Giám đốc. NPC subordinates only: a player never acts on a player.
CAND_LADDER = ('Hạ sĩ', 'Trung sĩ', 'Thượng sĩ', 'Thiếu úy', 'Trung úy', 'Thượng úy', 'Đại úy')
OFFICE['cand'] = dict(
    name='Phòng chỉ huy', unit='việc', plan='Phân công',
    kpi=('Tin báo đúng hạn', 'Phản ánh của dân', 'Tinh thần', 'Quỹ lương'),
    roles={'tt': dict(label='Tuần tra', ladder=CAND_LADDER, pay=24), 'tb': dict(label='Trực ban', ladder=CAND_LADDER, pay=22)},
    roster=(('Hạ sĩ Lâm Tùng', 'tt', 0, 1, 52, 70), ('Trung sĩ Vy Hạnh', 'tb', 1, 2, 64, 72), ('Thượng sĩ Bảo An', 'tt', 2, 3, 70, 66),
            ('Thiếu úy Kim Ngọc', 'tb', 3, 3, 76, 68), ('Hạ sĩ Ninh Khôi', 'tt', 0, 1, 48, 74), ('Trung úy Phó Đức', 'tt', 4, 4, 80, 62),
            ('Trung sĩ Cù Mai', 'tb', 1, 2, 58, 70), ('Thượng úy Lã Sơn', 'tt', 5, 5, 84, 60), ('Thiếu úy Hồ Nhung', 'tb', 3, 3, 68, 72),
            ('Đại úy Viên Quang', 'tt', 6, 5, 88, 58), ('Hạ sĩ Đinh Thơ', 'tb', 0, 1, 50, 76), ('Thượng sĩ Khúc Hải', 'tt', 2, 2, 62, 68)),
    extra=(), all_from=99,
    grow={1: 4, 2: 6, 3: 8, 4: 8, 5: 12},
    hires=('Hạ sĩ Tạ Minh', 'Hạ sĩ Lý Nga', 'Hạ sĩ Ông Tín', 'Hạ sĩ Hứa Vân', 'Hạ sĩ Từ Lộc', 'Hạ sĩ Âu Thy'),
    issues=dict(late='⏰ Giao ban trễ', slip='📒 Ghi sổ trực ban sót việc', rude='😤 Dân phản ánh thái độ', tired='🥱 Trực đêm liền, xin nghỉ',
                bribe='💵 Có tin nhận phong bì'),
    more_faults=('bribe',), integrity=True,
    slots=(('🚶 Tuần tra Chợ Mây – bến xe buýt', 'Ca sáng', 'tt', 0), ('🚶 Tuần tra cổng trường – Hẻm 7', 'Giờ tan trường', 'tt', 0),
           ('🌙 Tuần tra đêm bờ kênh', 'Sau 22:00', 'tt', 2), ('☎️ Trực ban 113', 'Cả ngày', 'tb', 0), ('📒 Bàn tiếp dân', 'Giờ hành chính', 'tb', 0),
           ('🗂️ Đối chiếu sổ cư trú', 'Buổi chiều', 'tb', 1), ('🔎 Kiểm tra cơ sở kinh doanh có điều kiện', 'Có quyết định kiểm tra', 'tt', 3),
           ('🎤 Nói chuyện chống lừa đảo ở tổ dân phố', 'Tối', 'tb', 1)),
    powers={1: ('talk', 'praise', 'remind'),
            2: ('talk', 'praise', 'remind', 'review', 'promote', 'demote', 'move'),
            3: ('talk', 'praise', 'remind', 'reprimand', 'warn', 'review', 'suspend', 'promote', 'demote', 'move', 'raise', 'cut'),
            4: ('talk', 'remind'),
            5: ('talk', 'praise', 'remind', 'reprimand', 'warn', 'review', 'suspend', 'promote', 'demote', 'move', 'raise', 'cut')},
    acts={1: 3, 2: 4, 3: 5, 4: 3, 5: 6}, cap={1: 20, 2: 26, 3: 32, 4: 26, 5: 40}, inbox={1: 1, 2: 1, 3: 2, 4: 1, 5: 2},
    cancel='bỏ trống, tin báo phải chờ', rest='Đã trực 3 ngày liền: theo quy định phải nghỉ hôm nay.',
)
FAULT = ('late', 'slip', 'rude')
SEVERE = ('slip', 'rude')
ISSUES = FAULT + ('tired',)


def _faults(o: dict) -> tuple:
    return FAULT + o.get('more_faults', ())


def _issues(o: dict) -> tuple:
    return ISSUES + o.get('more_faults', ())

# The day's slots. need: the lowest step on the person's own ladder; role: whose job it is.
TEACHER_SLOTS = (('🏫 Dạy thay lớp {c}', 0), ('📝 Coi kiểm tra khối {k}', 0), ('🏆 Bồi dưỡng học sinh giỏi', 1),
                 ('🚸 Trực cổng giờ tan trường', 0), ('📚 Dự giờ, góp ý giáo viên mới', 2), ('🎨 Câu lạc bộ vẽ cuối chiều', 0))
AIR_EXTRA_SLOTS = (('🧑‍✈️ Tổ tiếp viên chặng đảo', 'fa', 1), ('📡 Trực điều phái', 'op', 0), ('🔧 Trực kỹ thuật sân đỗ', 'en', 1))


def _rng(*parts) -> random.Random:
    return random.Random('|'.join(map(str, parts)))


def available(career: str, rank: int) -> bool:
    o = OFFICE.get(career)
    return bool(o) and rank >= min(o['powers'])


def _level(o: dict, rank: int) -> int:
    return max(k for k in o['powers'] if k <= rank)


def _captains_free(off: dict) -> int:
    """The pilot office's captains who may fly today: a captain's rank, not suspended, not on the legal rest day."""
    need = OFFICE['pilot']['keep_lv']
    return sum(1 for st in off['staff'] if st['r'] == 'pl' and st['lv'] >= need and not st['off'] and st['duty'] < DUTY_MAX)


def _slots(career: str, day: int, seed: int, n: int, off: dict | None = None) -> list[dict]:
    if career == 'pilot':
        from .careers import airline as air
        r = _rng('of-hard', seed, day)
        # F#223: a leg needs a captain only while one is free for it (min(2, captains free today)); else it is flown
        # by whoever is free instead of being cancelled every day.
        h = HARD_LEGS if off is None else min(HARD_LEGS, _captains_free(off))
        hard = set(r.sample(range(4), 2)[:h])
        out = []
        for k in range(4):
            leg = air.leg(day, k * 2)
            out.append(dict(t=f'✈️ {leg["code"]} · {leg["to"]} {leg["emoji"]}', sub=f'Cất cánh {leg["dep"]}', role='pl',
                            need=2 if k in hard else 0))
        for t, role, need in AIR_EXTRA_SLOTS[:max(0, n - 4)]:
            out.append(dict(t=t, sub='Cả ngày', role=role, need=need))
        return out
    o = OFFICE[career]
    if o.get('slots'):   # an org office: its own slots, by the person's grade on the role's ladder
        r = _rng('of-slots', seed, career, day)
        return [dict(t=t, sub=sub, role=role, need=need) for t, sub, role, need in r.sample(o['slots'], n)]
    r = _rng('of-slots', seed, career, day)
    picks = r.sample(TEACHER_SLOTS, n)
    return [dict(t=t.format(c=r.choice('12345') + r.choice('ABC'), k=r.choice('12345')), sub='Trong giờ học', role='gv', need=need)
            for t, need in picks]


def _cost(o: dict, st: dict) -> int:
    return o['roles'][st['r']]['pay'] + 12 * st['lv'] + 8 * (st['pay'] - 1)


def _person(o: dict, sid: str, row: tuple, trait: str, seed: int = 0) -> dict:
    name, role, lv, pay, sk, mood = row
    st = dict(id=sid, n=name, r=role, lv=lv, pay=pay, mood=mood, sk=sk, tr=trait, seen=False, mk=0, iss=None, off=0, duty=0, cl=0)
    if o.get('integrity'):   # hidden: 0 takes envelopes … 3 spotless (org offices only)
        st['ig'] = _rng('of-ig', seed, sid, name).choice((0, 1, 2, 2, 3, 3, 3))
    return st


def _grow(o: dict, level: int) -> int:
    g = o.get('grow')
    return max([v for k, v in g.items() if k <= level] or [min(g.values())]) if g else len(o['roster'])


def new_office(career: str, seed: int, day: int, level: int = 0) -> dict:
    o = OFFICE[career]
    traits = list(TRAITS)
    _rng('of-traits', seed, career).shuffle(traits)
    rows = o['roster'][:_grow(o, level)] if o.get('grow') else o['roster']
    staff = [_person(o, f's{i + 1}', row, traits[i % len(traits)], seed) for i, row in enumerate(rows)]
    return dict(v=1, day=0, staff=staff, plan=[], inbox=[], left=0, acted=[], me=False, xc=0, all=False, hires=0,
                budget=round(sum(_cost(o, st) for st in staff) * 1.1), kpi=dict(ontime=80, compl=0, good=0, days=0), log=[])


def _add_everyone(career: str, off: dict, seed: int) -> None:
    o = OFFICE[career]
    traits = list(TRAITS)
    _rng('of-traits-all', seed, career).shuffle(traits)
    rows = [_person(o, f'x{i + 1}', row, traits[i % len(traits)]) for i, row in enumerate(o['extra'])]
    off['staff'] = (off['staff'] + rows)[:STAFF_MAX]
    off['budget'] += round(sum(_cost(o, st) for st in rows) * 1.1)
    off['all'] = True


def _log(off: dict, line: str) -> None:
    off['log'] = (off['log'] + [line[:140]])[-LOG_MAX:]


def _clamp(n: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, round(n)))


def _mood(st: dict, delta: float) -> int:
    """Apply a mood change through the person's hidden trait; returns the change actually made."""
    pos, neg = MULT[st['tr']]
    d = round(delta * (pos if delta > 0 else neg))
    before = st['mood']
    st['mood'] = _clamp(before + d)
    return st['mood'] - before


def _room(off: dict, delta: float, but: dict | None = None) -> None:
    for st in off['staff']:
        if st is not but:
            _mood(st, delta)


# ------------------------------------------------------------------------------------- inbox (việc cần quyết)
def _x(xid, emoji, title, text, pick, *options):
    return dict(id=xid, emoji=emoji, title=title, text=text, pick=pick,
                options=[dict(id=chr(97 + i), label=lab, good=good, out=out, fx=fx) for i, (lab, good, out, fx) in enumerate(options)])


INBOX = {
    'pilot': [
        _x('p_extra', '🧾', 'Phòng thương mại ép thêm chuyến', 'Đoàn khách VIP muốn thêm một chuyến tối nay. Tổ của {a} đã chạm giới hạn giờ bay.', 'tired',
           ('Từ chối, giải thích quy định giờ bay; mời đoàn đi chuyến sáng mai', True, 'Đoàn VIP càu nhàu nhưng tổ bay nể sếp.', dict(mood=4, compl=1)),
           ('Hỏi {a} có “tình nguyện” bay không', False, '{a} gật vì ngại. Bay mệt, chuyến sau trễ dây chuyền.', dict(a=-12, ontime=-8, mood=-4)),
           ('Cứ xếp bay, quy định để sau', False, 'Phòng an toàn lập biên bản. Cả đội mất niềm tin.', dict(mood=-10, ontime=-10, compl=2))),
        _x('p_vip', '📞', 'Sếp lớn đòi giữ máy bay', 'Một vị “sếp lớn” kẹt xe, gọi điện đòi giữ chuyến sáng thêm 25 phút.', 'any',
           ('Không giữ, đổi vé chuyến sau miễn phí cho ông ấy', True, 'Ông ấy bực, 64 khách còn lại bay đúng giờ.', dict(compl=1)),
           ('Giữ máy bay chờ', False, 'Cả tàu trễ 25 phút, khách đăng bài chê.', dict(ontime=-10, compl=3)),
           ('Giữ 10 phút “cho có”', False, 'Vẫn trễ mà ông ấy vẫn lỡ chuyến.', dict(ontime=-5, compl=2))),
        _x('p_swap', '💒', 'Xin đổi lịch đi đám cưới', '{a} xin đổi lịch bay cuối tuần để dự đám cưới em gái, đã tìm được người đổi.', 'any',
           ('Duyệt, ghi rõ lịch đổi vào bảng', True, '{a} cảm ơn rối rít.', dict(a=12)),
           ('Từ chối: lịch đã chốt là chốt', False, '{a} buồn hẳn, cả nhóm thấy sếp cứng nhắc.', dict(a=-14, mood=-2)),
           ('Bảo {a} tự lo, đừng làm phiền', False, '{a} thấy mình bị bỏ rơi.', dict(a=-16, mood=-3))),
        _x('p_union', '✊', 'Công đoàn đòi phụ cấp bay đêm', 'Đại diện công đoàn xin tăng phụ cấp bay đêm cho cả đội ngay tuần này.', 'any',
           ('Mời họp, đưa số liệu quỹ lương, hẹn xét theo kết quả quý', True, 'Cuộc họp căng nhưng ai cũng thấy được lắng nghe.', dict(mood=4)),
           ('Hứa tăng ngay cho êm', False, 'Cả đội vui một hôm, quỹ lương vỡ kế hoạch.', dict(mood=5, cost=120)),
           ('Từ chối, không tiếp', False, 'Công đoàn gửi đơn lên Tổng Giám đốc.', dict(mood=-10, compl=2))),
        _x('p_report', '📄', 'Báo cáo an toàn tự nguyện', '{a} tự nộp báo cáo: suýt lấn vạch dừng vì mệt sau ba chặng liền.', 'any',
           ('Cảm ơn, không phạt, cho nghỉ một ngày, đưa thành bài học chung', True, 'Cả đội thấy nói thật là an toàn.', dict(a=10, mood=5, clear=True, rest=True)),
           ('Kỷ luật vì “làm xấu hình ảnh hãng”', False, 'Từ nay chẳng ai dám báo lỗi nữa.', dict(a=-25, mood=-12, ontime=-4)),
           ('Cất báo cáo vào ngăn kéo', False, 'Lỗi cũ lặp lại ở chặng sau.', dict(mood=-5, ontime=-5))),
        _x('p_gift', '🎁', '“Quà cảm ơn” của đại lý vé', 'Một đại lý vé gửi phong bì “cảm ơn”, mong được ưu tiên giờ cất cánh đẹp.', 'any',
           ('Trả lại, ghi vào sổ minh bạch', True, 'Phòng điều phái nể sếp ra mặt.', dict(mood=3)),
           ('Nhận rồi tính sau', False, 'Chuyện lộ ra, cả phòng xì xào.', dict(mood=-8, compl=2)),
           ('Nhận, chia cho phòng điều phái', False, 'Thanh tra vào cuộc. Mất uy tín.', dict(mood=-10, compl=3))),
        _x('p_seat', '💺', 'Khách khiếu nại tổ bay', 'Một khách khiếu nại {a} “lạnh lùng” vì không cho ngồi hàng ghế thoát hiểm khi đi cùng em bé.', 'any',
           ('Xem lại: {a} làm đúng quy định. Trả lời khách lịch sự, bảo vệ {a}', True, '{a} thấy được sếp chống lưng.', dict(a=10, compl=-1)),
           ('Bắt {a} xin lỗi khách cho xong', False, '{a} ấm ức, cả tổ thấy đúng mà vẫn bị phạt.', dict(a=-15, mood=-5)),
           ('Tặng voucher cho khách, không hỏi {a}', False, 'Khách vui, quỹ hụt, {a} chẳng biết mình đúng hay sai.', dict(cost=40, compl=-1, a=-4))),
        _x('p_rookies', '👶', 'Hai cơ phó mới cùng một chặng', 'Lịch mai ghép {a} với một cơ phó mới khác trên chặng đảo mùa giông.', 'new',
           ('Đổi để chặng có người dày kinh nghiệm kèm', True, 'Chặng đảo bay êm, {a} học được nhiều.', dict(ontime=4, a=4)),
           ('Giữ nguyên, ai cũng phải tự lớn', False, 'Hai bạn trẻ lúng túng, chặng trễ 20 phút.', dict(ontime=-6, a=-6)),
           ('Hủy chặng cho chắc', False, 'An toàn, nhưng 60 khách phải đổi chuyến.', dict(compl=3))),
        _x('p_fuel', '⛽', 'Phòng tài chính muốn bớt dầu', 'Phòng tài chính đề nghị bớt dầu dự phòng xuống dưới mức để tiết kiệm.', 'any',
           ('Không: dầu dự phòng là luật. Tìm chỗ tiết kiệm khác', True, 'Đội bay yên tâm, tài chính đành tìm khoản khác.', dict(mood=3)),
           ('Đồng ý thử một tuần', False, 'Cơ trưởng phản đối, vài chặng phải chuyển hướng.', dict(mood=-8, ontime=-6)),
           ('Để từng cơ trưởng tự quyết', False, 'Mỗi người một kiểu, điều phái rối.', dict(mood=-3, ontime=-3))),
    ],
    'teacher': [
        _x('t_grade', '✉️', 'Phụ huynh xin “nâng điểm”', 'Phụ huynh lớp 5 xin nâng điểm cho con để vào lớp chọn, kèm một phong bì. Con học lớp {a}.', 'any',
           ('Từ chối phong bì, hướng dẫn phúc khảo đúng quy trình', True, 'Phụ huynh không vui, giáo viên thấy được bảo vệ.', dict(compl=1, mood=4)),
           ('Nhận, bảo {a} nâng điểm', False, '{a} bị đặt vào thế khó. Cả trường xì xào.', dict(a=-15, mood=-10, compl=3)),
           ('Hứa “để xem” cho êm', False, 'Phụ huynh quay lại hỏi mãi.', dict(compl=2))),
        _x('t_leave', '🤒', 'Xin nghỉ đúng tuần thi', '{a} xin nghỉ ba ngày đúng tuần thi vì con nhỏ ốm.', 'any',
           ('Duyệt, sắp xếp người dạy thay', True, '{a} cảm ơn, tổ chia nhau gánh giúp.', dict(a=15, mood=-1, rest=True)),
           ('Không duyệt: tuần thi quan trọng hơn', False, '{a} đi dạy mà đầu óc ở nhà.', dict(a=-20, ontime=-4)),
           ('Duyệt nhưng trừ thi đua', False, '{a} thấy bị phạt vì con ốm.', dict(a=-6))),
        _x('t_fight', '🥊', 'Học sinh xô xát', 'Hai học sinh lớp {a} chủ nhiệm xô xát giờ ra chơi, phụ huynh hai bên đòi gặp hiệu trưởng ngay.', 'any',
           ('Gặp riêng từng bên, nghe {a} báo cáo, lập biên bản', True, 'Hai nhà bắt tay, {a} thấy được tin.', dict(compl=-1, a=5)),
           ('Đổ lỗi {a} không trông lớp', False, '{a} tủi thân, phụ huynh càng làm to.', dict(a=-15, mood=-5, compl=1)),
           ('Hẹn tuần sau', False, 'Phụ huynh đăng lên nhóm phụ huynh.', dict(compl=2))),
        _x('t_fund', '💸', 'Thu tiền “xã hội hóa”', 'Ban đại diện phụ huynh muốn thu bắt buộc mỗi em 500 nghìn lắp máy lạnh.', 'any',
           ('Chỉ vận động tự nguyện, công khai sổ sách', True, 'Ai góp thì góp, không ai bị ép.', dict(mood=2)),
           ('Đồng ý thu bắt buộc', False, 'Phụ huynh khó khăn phản ánh lên phòng giáo dục.', dict(compl=3)),
           ('Để ban phụ huynh tự lo', False, 'Thu sai quy định, trường vẫn chịu tiếng.', dict(compl=2))),
        _x('t_inspect', '📁', 'Đoàn kiểm tra sáng mai', 'Phòng giáo dục báo đoàn kiểm tra hồ sơ chuyên môn sáng mai.', 'any',
           ('Nhờ tổ trưởng rà hồ sơ trong giờ, không bắt thức đêm', True, 'Hồ sơ gọn, thầy cô vẫn ngủ đủ.', dict(ontime=3)),
           ('Bắt cả trường ở lại làm tới khuya', False, 'Hồ sơ đẹp, sáng mai ai cũng phờ phạc.', dict(mood=-10, ontime=2)),
           ('Kệ, có sao nói vậy', False, 'Đoàn ghi nhiều thiếu sót.', dict(ontime=-5, mood=-2))),
        _x('t_tutor', '🏠', 'Phụ huynh nhờ dạy thêm', 'Phụ huynh nhờ {a} dạy thêm tại nhà cho chính học sinh {a} chủ nhiệm, “trả hậu”.', 'any',
           ('Nhắc quy định, mở lớp phụ đạo miễn phí ở trường', True, 'Phụ huynh hiểu, lớp phụ đạo đông vui.', dict(a=2, mood=2)),
           ('Cho phép ngầm', False, 'Phụ huynh khác biết chuyện, phản ánh “ép học thêm”.', dict(compl=3, mood=-4)),
           ('Mặc {a} tự quyết', False, '{a} lúng túng giữa tiền và quy định.', dict(a=-6, compl=1))),
        _x('t_new', '😢', 'Giáo viên mới bị lớp “bắt nạt”', '{a} mới về trường, bị lớp 4B trêu chọc, khóc ở phòng giáo viên.', 'new',
           ('Nhờ tổ trưởng dự giờ, kèm cặp {a} cả tuần', True, '{a} vững dần, lớp 4B ngoan hơn.', dict(a=15, sk=5)),
           ('Bảo {a} “phải tự cứng lên”', False, '{a} càng run, lớp càng loạn.', dict(a=-12, ontime=-3)),
           ('Đổi lớp cho {a} ngay', False, 'Lớp 4B nghĩ trêu là thắng.', dict(a=4, mood=-5))),
        _x('t_post', '📱', 'Bài chê trường trên mạng', 'Một phụ huynh đăng bài chê trường lên nhóm Facebook khu phố, vài trăm lượt chia sẻ.', 'any',
           ('Liên hệ, mời lên trao đổi, sửa phần đúng', True, 'Phụ huynh gỡ bài, viết thêm lời cảm ơn.', dict(compl=-1)),
           ('Đăng bài đáp trả gay gắt', False, 'Drama to hơn, báo khu phố vào cuộc.', dict(compl=3)),
           ('Đòi phụ huynh xóa bài, dọa “mời công an”', False, 'Phụ huynh đăng tiếp ảnh chụp tin nhắn.', dict(compl=3, mood=-3))),
    ],
}
# 👮 The police commander's awkward demands (org office 'cand'). Giving in is never rewarded; criticism is never a fault.
INBOX['cand'] = [
    _x('c_quota', '📊', 'Chỉ tiêu biên bản', 'Cấp trên nhắn: “Tháng này tổ của {a} thiếu biên bản, làm cho đủ số nhé.”', 'any',
       ('Báo cáo số thật, kèm lý do: nhắc nhở nhiều, vi phạm giảm', True, 'Số liệu thật được ghi nhận, tổ yên tâm làm đúng.', dict(mood=4)),
       ('Bảo {a} lập thêm biên bản cho đủ', False, '{a} phải “tìm lỗi” của dân, phản ánh dồn về phường.', dict(a=-12, compl=3)),
       ('Im lặng, chờ tháng sau', False, 'Cuối tháng vẫn bị hỏi, cả tổ lo.', dict(mood=-4))),
    _x('c_mate', '🤝', '“Anh em mình cả”', 'Một tổ trưởng nhắn riêng: “Anh em mình cả, đợt kiểm tra tới phần tổ em nương tay nhé.”', 'any',
       ('Trả lời rõ: kiểm tra như mọi tổ', True, 'Tổ trưởng hơi ngượng, nhưng cả đơn vị nể.', dict(mood=3)),
       ('Hứa nương tay', False, 'Chuyện lộ ra, các tổ khác thấy bất công.', dict(mood=-8, compl=1)),
       ('Không trả lời, để đó', False, 'Tổ trưởng tưởng là đồng ý.', dict(mood=-3))),
    _x('c_fruit', '🧺', 'Giỏ trái cây lên phòng', 'Vợ của {a} mang giỏ trái cây lên phòng, “cảm ơn chỉ huy đã quan tâm”.', 'any',
       ('Cảm ơn, từ chối khéo, mời chị về', True, 'Chị hiểu, {a} cũng nhẹ người.', dict(a=2)),
       ('Nhận cho chị vui', False, 'Cả đơn vị xì xào chuyện “quà cáp”.', dict(mood=-8, compl=1)),
       ('Nhận, chia cho cả phòng', False, 'Vẫn là nhận. Đoàn kiểm tra hỏi tới.', dict(mood=-6, compl=2))),
    _x('c_report', '⏰', 'Báo cáo trước 7 giờ sáng', 'Lãnh đạo cần báo cáo tình hình an ninh trật tự trước 7 giờ sáng mai.', 'any',
       ('Giao {a} tổng hợp trong giờ, mình duyệt tối nay', True, 'Báo cáo gọn, đúng hạn, không ai thức trắng.', dict(ontime=4)),
       ('Bắt cả tổ trực ban ở lại làm tới khuya', False, 'Báo cáo đẹp, sáng mai ai cũng phờ phạc.', dict(mood=-10, ontime=2)),
       ('Gửi số liệu tháng trước cho kịp', False, 'Số liệu cũ bị phát hiện, mất uy tín.', dict(ontime=-6, compl=1))),
    _x('c_critic', '📱', 'Bài chê phường trên mạng', 'Một người dân đăng bài chê phường tiếp dân chậm. {a} đề nghị “mời lên làm việc”.', 'any',
       ('Không mời: góp ý không phải vi phạm. Xem phần đúng để sửa', True, 'Bàn tiếp dân thêm số thứ tự, bài viết được sửa thành lời khen.', dict(compl=-1)),
       ('Mời lên phường cho “biết điều”', False, 'Giấy mời không căn cứ. Chuyện lên báo.', dict(compl=3, mood=-4)),
       ('Nhắn người đó gỡ bài', False, 'Ảnh chụp tin nhắn lan khắp nhóm khu phố.', dict(compl=2))),
    _x('c_night', '🌙', 'Tuần tra đêm thứ ba liền', '{a} xin đổi ca: đã tuần tra đêm ba hôm liền.', 'tired',
       ('Xếp người khác, cho {a} nghỉ bù', True, '{a} cảm ơn, ca sau tỉnh táo hẳn.', dict(a=12, rest=True, clear=True)),
       ('Bảo cố thêm một đêm', False, '{a} gật gù trên xe, suýt bỏ sót một tin báo.', dict(a=-14, ontime=-6)),
       ('Cho nghỉ nhưng trừ thi đua', False, '{a} thấy bị phạt vì mệt.', dict(a=-6, rest=True))),
    _x('c_cam', '📹', 'Camera ghi hình tắt', 'Camera ghi hình của {a} tắt giữa lúc xử lý một vụ va chạm.', 'any',
       ('Lập biên bản sự việc, kiểm tra lại toàn bộ thiết bị', True, 'Lỗi pin được thay, tổ yên tâm làm đúng.', dict(ontime=2, mood=2)),
       ('Bỏ qua, chắc hết pin', False, 'Người dân khiếu nại, không có hình đối chứng.', dict(compl=2)),
       ('Dặn mọi người đừng nói ra', False, 'Chuyện lộ ra, mất niềm tin.', dict(compl=3, mood=-6))),
    _x('c_karaoke', '🎤', 'Quán karaoke gửi “quà”', 'Chủ quán karaoke gửi phong bì cho {a}, mong “bỏ qua” giờ đóng cửa.', 'any',
       ('Lập biên bản hành vi đưa hối lộ, khen {a} đã báo', True, 'Quán đóng cửa đúng giờ, {a} được khen trước đơn vị.', dict(a=8, mood=3)),
       ('Bảo {a} trả lại, không lập biên bản', False, 'Quán thử lại với tổ khác.', dict(compl=1)),
       ('Để {a} tự xử lý', False, '{a} lúng túng, tin đồn lan ra.', dict(a=-6, compl=2))),
]
INBOX_INDEX = {c: {x['id']: x for x in rows} for c, rows in INBOX.items()}


def _target(off: dict, rule: str, r: random.Random, role: str) -> int | None:
    pool = [i for i, st in enumerate(off['staff']) if st['r'] == role]
    if not pool:
        return None
    if rule == 'tired':
        return max(pool, key=lambda i: (off['staff'][i]['duty'], -i))
    if rule == 'new':
        return min(pool, key=lambda i: (off['staff'][i]['lv'], i))
    return r.choice(pool)


# ------------------------------------------------------------------------------------- the day
def day_roll(career: str, off: dict, seed: int, day: int, rank: int) -> None:
    """start_day: today's slots, inbox and new problems; the decisions of the day are fresh."""
    o = OFFICE[career]
    if rank >= o['all_from'] and not off['all'] and o['extra']:
        _add_everyone(career, off, seed)
    lvl = _level(o, rank)
    if o.get('grow'):   # an org office grows with the post: the next people of the roster join
        traits = list(TRAITS)
        _rng('of-traits', seed, career).shuffle(traits)
        have = {st['id'] for st in off['staff']}
        for i, row in enumerate(o['roster'][:_grow(o, lvl)]):
            if len(off['staff']) >= min(STAFF_MAX, _grow(o, lvl)):
                break
            if f's{i + 1}' not in have:
                st = _person(o, f's{i + 1}', row, traits[i % len(traits)], seed)
                off['staff'].append(st)
                off['budget'] = min(10**5, off['budget'] + round(_cost(o, st) * 1.1))
    if o.get('keep_lv') is not None:
        _top_up(career, off)
    off['day'] = day
    n = 4 + (len(AIR_EXTRA_SLOTS) if off['all'] and career == 'pilot' else 0)
    off['plan'] = [None] * n
    off['left'] = o['acts'][lvl]
    off['acted'] = []
    off['me'] = False
    off['xc'] = 0
    for st in off['staff']:
        if st['iss'] or st['off']:
            continue
        r = _rng('of-iss', seed, career, day, st['id'])
        if st['duty'] >= TIRED_AT and r.random() < .5:
            st['iss'] = 'tired'
            continue
        chance = .1 + (.15 if st['mood'] < 40 else 0) + (.12 if st['tr'] == 'lazy' else 0)
        if r.random() < chance:
            st['iss'] = r.choice(FAULT)
            if st.get('ig') == 0 and r.random() < .5:   # an org office: someone who takes envelopes, sooner or later
                st['iss'] = 'bribe'
    r = _rng('of-inbox', seed, career, day)
    main = next(iter(o['roles']))
    picks = r.sample(INBOX[career], o['inbox'][lvl])
    off['inbox'] = [dict(id=x['id'], a=_target(off, x['pick'], r, main), pick=None) for x in picks]


def _top_up(career: str, off: dict) -> None:
    """F#223: an office left with fewer than CAPTAINS_MIN captains (older builds hired every newcomer at step 0) gets its
    most experienced first officers moved up by the airline before the day opens. Runs on every day_roll, so offices saved
    by those builds are repaired on their next day; a full office is never touched."""
    o = OFFICE[career]
    main, need = next(iter(o['roles'])), o['keep_lv']
    ladder = o['roles'][main]['ladder']
    while sum(1 for st in off['staff'] if st['r'] == main and st['lv'] >= need) < CAPTAINS_MIN:
        pool = [st for st in off['staff'] if st['r'] == main and st['lv'] < need]
        if not pool:
            return
        st = max(pool, key=lambda x: (x['lv'], x['sk'], -off['staff'].index(x)))
        before = _cost(o, st)
        st['lv'] = need
        off['budget'] = min(10**5, off['budget'] + round((_cost(o, st) - before) * 1.1))
        _log(off, f'🧑‍✈️ Hãng nâng {st["n"]} lên {ladder[need]}: đội bay cần ít nhất {CAPTAINS_MIN} {ladder[need].lower()}.')


def _settle(career: str, off: dict, seed: int) -> None:
    """After a decision that changes who may fly (a promotion, a suspension, a rest day, a newcomer): drop the plan's
    picks that no longer fit today's slots, so the board never shows a pick the rules refuse."""
    o = OFFICE[career]
    if o.get('keep_lv') is None:
        return   # the teacher's and the org offices' slots never change within a day
    slots = _slots(career, off['day'], seed, len(off['plan']), off)
    off['plan'] = [w if w is None or _can_plan(o, off, slots[k], w) is None else None for k, w in enumerate(off['plan'])]


def ready(off: dict | None, c: dict) -> bool:
    return bool(off) and off['day'] == c.get('day') and bool(c.get('open'))


def _can_plan(o: dict, off: dict, slot: dict, i: int) -> str | None:
    st = off['staff'][i]
    if st['r'] != slot['role']:
        return f'{st["n"]} không làm việc này ({o["roles"][slot["role"]]["label"]}).'
    if st['off']:
        return f'{st["n"]} đang bị đình chỉ, không xếp được.'
    if st['duty'] >= DUTY_MAX:
        return f'{st["n"]}: {o["rest"]}'
    if st['lv'] < slot['need']:
        return f'Việc này cần từ {o["roles"][slot["role"]]["ladder"][slot["need"]]} trở lên.'
    return None


def _just(act: str, st: dict, o: dict | None = None) -> bool:
    fault = st['iss'] in (_faults(o) if o else FAULT)
    severe = SEVERE + (o.get('more_faults', ()) if o else ())
    if st['iss'] == 'bribe' and act in ('praise', 'promote', 'raise'):
        return False   # praise for a member who takes envelopes is never just
    return {
        'talk': True,
        'praise': st['iss'] is None and st['sk'] >= 60,
        'remind': fault,
        'warn': fault and (st['mk'] >= 1 or st['iss'] in severe),
        'review': fault and st['mk'] >= 2,
        'suspend': st['iss'] in severe and (st['mk'] >= 2 or st['iss'] == 'bribe'),
        'promote': st['iss'] is None and st['mk'] == 0 and st['sk'] >= 70,
        'demote': st['mk'] >= 2 or st['sk'] < 40,
        'raise': st['mk'] == 0 and st['sk'] >= 65 and st['iss'] not in FAULT,
        'cut': st['mk'] >= 2,
        'reprimand': fault,
        'move': st['iss'] in ('tired', 'rude') or st['sk'] < 50,
    }[act]


def _hire(career: str, off: dict, i: int, seed: int) -> str:
    o = OFFICE[career]
    old = off['staff'][i]
    off['hires'] = min(10**6, off['hires'] + 1)
    r = _rng('of-hire', seed, career, off['hires'])
    keep = o.get('keep_lv')
    if keep is not None and old['r'] == next(iter(o['roles'])) and old['lv'] >= keep:
        # F#223: a captain leaves, a captain comes (transferred from another base), at the same step.
        name = o['cap_hires'][(off['hires'] - 1) % len(o['cap_hires'])]
        off['staff'][i] = dict(id=f'n{off["hires"]}', n=name, r=old['r'], lv=old['lv'], pay=1, mood=62, sk=r.randint(64, 76),
                               tr=r.choice(TRAITS), seen=False, mk=0, iss=None, off=0, duty=0, cl=0)
    else:
        name = o['hires'][(off['hires'] - 1) % len(o['hires'])]
        off['staff'][i] = dict(id=f'n{off["hires"]}', n=name, r=old['r'], lv=0, pay=1, mood=62, sk=r.randint(42, 58), tr=r.choice(TRAITS),
                               seen=False, mk=0, iss=None, off=0, duty=0, cl=0)
    if o.get('integrity'):
        off['staff'][i]['ig'] = r.choice((1, 2, 3))
    off['plan'] = [None if w == i else w for w in off['plan']]
    for x in off['inbox']:
        if x['a'] == i and x['pick'] is None:
            x['a'] = None   # the item now speaks of "một bạn"; the newcomer is not blamed for it
    return name


def _quit(career: str, off: dict, i: int, seed: int) -> str:
    st = off['staff'][i]
    name = _hire(career, off, i, seed)
    off['kpi']['compl'] = min(999, off['kpi']['compl'] + 1)
    _room(off, -4)
    new = off['staff'][i]
    if new['lv']:
        return f' 📨 {st["n"]} nộp đơn nghỉ việc. {name} ({OFFICE[career]["roles"][new["r"]]["ladder"][new["lv"]]}, điều từ căn cứ khác) vào thay.'
    return f' 📨 {st["n"]} nộp đơn nghỉ việc. {name} vào thay, còn non tay.'


def _hr(career: str, off: dict, rank: int, i: int, act: str, seed: int, need) -> dict:
    o = OFFICE[career]
    need(act in o['powers'][_level(o, rank)], 'Bậc của bạn chưa có quyền này.')
    need(off['left'] > 0, 'Hết lượt quyết nhân sự hôm nay. Mai tính tiếp.')
    st = off['staff'][i]
    need(st['id'] not in off['acted'], f'Hôm nay đã quyết chuyện của {st["n"]} rồi.')
    ladder = o['roles'][st['r']]['ladder']
    if act == 'move':
        need(len(o['roles']) > 1, 'Không có tổ nào khác để điều động.')
    if act == 'promote':
        need(st['lv'] < len(ladder) - 1, f'{st["n"]} đã ở bậc cao nhất của vị trí này.')
    if act == 'demote':
        need(st['lv'] > 0, f'{st["n"]} đang ở bậc thấp nhất.')
    if act == 'raise':
        need(st['pay'] < PAY_MAX, f'{st["n"]} đã ở bậc lương cao nhất.')
    if act == 'cut':
        need(st['pay'] > 1, f'{st["n"]} đang ở bậc lương thấp nhất.')
    just = _just(act, st, o)
    good, bad, room, compl = FX[act]
    delta = good if just else bad
    tr = st['tr']
    extra = ''
    if act == 'talk':
        delta += 6 if tr in ('proud', 'fragile') else 0
        st['seen'] = True
        extra = ' 📝 ' + TRAIT_HINT[tr]
        if st['iss'] == 'tired':
            extra += ' Bạn ấy cần một ngày nghỉ hơn là bị nhắc.'
    if tr == 'proud' and act in ('warn', 'review', 'suspend', 'demote'):
        delta -= 8
    if tr == 'veteran' and act in ('remind', 'warn') and not just:
        delta -= 8
    if tr == 'eager' and act == 'promote':
        delta += 10
    moved = _mood(st, delta)
    if not just and room:
        _room(off, room, st)
    if just and act == 'promote':
        _room(off, 2, st)
    off['kpi']['compl'] = min(999, off['kpi']['compl'] + (0 if just else compl))
    # What the decision changes on paper.
    if act in ('remind', 'reprimand', 'warn', 'review', 'suspend') and just and not (st['iss'] == 'bribe' and act in ('remind', 'reprimand')):
        st['iss'] = None
        st['cl'] = 0
    if act in ('remind', 'reprimand', 'warn', 'review', 'suspend'):
        st['mk'] = max(st['mk'], {'remind': 1, 'reprimand': 2, 'warn': 2, 'review': 3, 'suspend': 3}[act])
    if act == 'move':
        others = [r_ for r_ in o['roles'] if r_ != st['r']]
        st['r'] = others[0]
        st['lv'] = min(st['lv'], len(o['roles'][st['r']]['ladder']) - 1)
        off['plan'] = [None if w == i else w for w in off['plan']]
        if st['iss'] == 'tired' and just:
            st['iss'] = None
    if act == 'suspend':
        st['off'] = 2
        off['plan'] = [None if w == i else w for w in off['plan']]
    if tr == 'lazy':
        if act in ('remind', 'warn', 'review') and just:
            st['sk'] = _clamp(st['sk'] + 6)
        if act in ('praise', 'raise') and not just:
            st['sk'] = _clamp(st['sk'] - 6)
    if act == 'review' and just and tr != 'lazy':
        st['sk'] = _clamp(st['sk'] + 3)
    if act == 'promote':
        st['lv'] += 1
        if tr == 'eager' and just:
            st['sk'] = _clamp(st['sk'] + 4)
    if act == 'demote':
        st['lv'] -= 1
    if act == 'raise':
        st['pay'] += 1
    if act == 'cut':
        st['pay'] -= 1
    off['left'] -= 1
    off['acted'].append(st['id'])
    a = ACTS[act]
    lines = REACT[tr]
    face = lines[0] if moved >= 0 else lines[1] if moved > -15 else lines[2]
    msg = f'{a["icon"]} {a["label"]} · {st["n"]}. {face.format(n=st["n"])}'
    if act != 'talk' and not just:
        msg += ' (Không có lý do rõ ràng: cả phòng để ý.)'
    _log(off, f'{a["icon"]} {st["n"]}: {a["label"].lower()}' + ('' if just else ' (thiếu lý do)'))
    if st['mood'] <= QUIT_AT or (tr == 'eager' and act == 'demote' and st['mood'] < 40):
        msg += _quit(career, off, i, seed)
    return dict(message=msg + extra, just=just)


def _fx(off: dict, fx: dict, i: int | None) -> None:
    k = off['kpi']
    if fx.get('mood'):
        _room(off, fx['mood'])
    if i is not None:
        st = off['staff'][i]
        if fx.get('a'):
            _mood(st, fx['a'])
        if fx.get('sk'):
            st['sk'] = _clamp(st['sk'] + fx['sk'])
        if fx.get('clear') and st['iss'] == 'tired':
            st['iss'] = None
        if fx.get('rest'):
            st['duty'] = DUTY_MAX   # today off the board, rested by tomorrow
            off['plan'] = [None if w == i else w for w in off['plan']]
    k['ontime'] = _clamp(k['ontime'] + fx.get('ontime', 0))
    k['compl'] = max(0, min(999, k['compl'] + fx.get('compl', 0)))
    off['xc'] = min(10**4, off['xc'] + fx.get('cost', 0))


def _fill(text: str, off: dict, i: int | None) -> str:
    return text.replace('{a}', off['staff'][i]['n'] if i is not None else 'một bạn')


def action(career: str, off: dict, rank: int, c: dict, name: str, p: dict, seed: int, need) -> dict:
    need(ready(off, c), 'Phòng điều hành làm việc trong ca. Mở ca trước nhé.', 'office_closed')
    o = OFFICE[career]
    staff = off['staff']
    if name == 'pm_of_plan':
        slot_i = p.get('slot')
        need(type(slot_i) is int and 0 <= slot_i < len(off['plan']), 'Việc không hợp lệ.')
        mate = p.get('mate')
        if mate is None:
            off['plan'][slot_i] = None
            return dict(message='Đã bỏ phân công.')
        need(type(mate) is int and 0 <= mate < len(staff), 'Người không hợp lệ.')
        slot = _slots(career, off['day'], seed, len(off['plan']), off)[slot_i]
        why = _can_plan(o, off, slot, mate)
        need(why is None, why or '')
        need(mate not in off['plan'] or off['plan'][slot_i] == mate, f'{staff[mate]["n"]} đã có việc hôm nay.')
        off['plan'][slot_i] = mate
        off['me'] = True
        st = staff[mate]
        warn = ' (đang có chuyện chưa xử lý)' if st['iss'] else ''
        return dict(message=f'🗓️ {st["n"]} nhận: {slot["t"]}{warn}.')
    if name == 'pm_of_hr':
        i = p.get('mate')
        need(type(i) is int and 0 <= i < len(staff), 'Người không hợp lệ.')
        act = p.get('act')
        need(act in ACTS, 'Quyết định không hợp lệ.')
        r = _hr(career, off, rank, i, act, seed, need)
        _settle(career, off, seed)
        return r
    if name == 'pm_of_inbox':
        k = p.get('item')
        need(type(k) is int and 0 <= k < len(off['inbox']) and off['inbox'][k]['pick'] is None, 'Việc này đã quyết rồi.')
        item = off['inbox'][k]
        x = INBOX_INDEX[career][item['id']]
        opt = next((y for y in x['options'] if y['id'] == p.get('option')), None)
        need(opt, 'Lựa chọn không hợp lệ.')
        item['pick'] = opt['id']
        _fx(off, opt['fx'], item['a'])
        _settle(career, off, seed)
        _log(off, f'{x["emoji"]} {x["title"]}: ' + ('✓' if opt['good'] else '✗'))
        return dict(message=f'{x["emoji"]} {_fill(opt["out"], off, item["a"])}', celebrate=bool(opt['good']))
    need(False, 'Thao tác phòng điều hành không hợp lệ.')
    return {}


def close(career: str, off: dict, rank: int, seed: int, day: int, earned: bool = True) -> dict:
    """end_day: undecided items take their last option, the assistant fills empty slots, the figures move and the bonus is
    worked out (the caller pays it)."""
    o = OFFICE[career]
    k = off['kpi']
    compl = 0
    for item in off['inbox']:
        if item['pick'] is None:
            x = INBOX_INDEX[career][item['id']]
            item['pick'] = x['options'][-1]['id']
            before = k['compl']
            _fx(off, x['options'][-1]['fx'], item['a'])
            compl += k['compl'] - before
            k['compl'] = before
    slots = _slots(career, off['day'], seed, len(off['plan']), off)
    plan = list(off['plan'])
    auto = set()
    for si, slot in enumerate(slots):   # the assistant: the most skilled person still free and allowed
        if plan[si] is None:
            free = [i for i in range(len(off['staff'])) if i not in plan and _can_plan(o, off, slot, i) is None]
            if free:
                plan[si] = max(free, key=lambda i: (off['staff'][i]['sk'], -i))
                auto.add(si)
    ok = 0
    lines = []
    for si, slot in enumerate(slots):
        who = plan[si]
        if who is None:
            compl += 2
            lines.append(f'❌ {slot["t"]}: {o["cancel"]}.')
            continue
        st = off['staff'][who]
        chance = 40 + .45 * st['sk'] + .3 * (st['mood'] - 50) + 4 * st['lv'] - (15 if st['iss'] else 0) \
            - (12 if st['duty'] >= TIRED_AT else 0) - (10 if si in auto else 0)
        r = _rng('of-run', seed, career, day, si, st['id'])
        if r.randrange(100) < _clamp(chance, 10, 97):
            ok += 1
        elif r.random() < .6:
            compl += 1
    compl += sum(1 for st in off['staff'] if st['iss'] in ('rude', 'bribe'))
    today = round(100 * ok / len(slots)) if slots else 0
    morale = round(sum(st['mood'] for st in off['staff']) / len(off['staff']))
    cost = sum(_cost(o, st) for st in off['staff'] if not st['off']) + off['xc']
    over = max(0, 100 * (cost - off['budget']) // off['budget'])
    score = _clamp(.5 * today + .3 * morale + 20 - 6 * compl - 2 * over)
    worked = off['me']
    lvl = _level(o, rank)
    # earned: a task done today, on a day the real-time allowance covers (game/promotion.py _office_close, 09/10 audit)
    bonus = round(o['cap'][lvl] * score / 100) if worked and earned else 0
    k['ontime'] = _clamp(.6 * k['ontime'] + .4 * today)
    k['compl'] = min(999, round(k['compl'] * .6) + compl)
    k['days'] = min(10**6, k['days'] + 1)
    if worked and score >= GOOD_SCORE:
        k['good'] = min(10**6, k['good'] + 1)
    busy = {w for w in plan if w is not None}
    rota = rota_line(career, off, plan)   # before today's duty is counted: the days that cost today
    for i, st in enumerate(off['staff']):
        if i in busy:
            st['duty'] = min(9, st['duty'] + 1)
            if st['duty'] >= DUTY_MAX:
                _mood(st, -6 - (4 if st['tr'] == 'steady' else 0))
        else:
            st['duty'] = 0
            _mood(st, 3)
            if st['iss'] == 'tired':
                st['iss'] = None
        if st['off']:
            st['off'] -= 1
        if st['iss'] is None:
            st['cl'] = min(99, st['cl'] + 1)
            if st['cl'] >= 5 and st['mk']:
                st['mk'] -= 1
                st['cl'] = 0
        else:
            st['cl'] = 0
        st['mood'] = _clamp(st['mood'] + (2 if st['mood'] < 60 else -1 if st['mood'] > 75 else 0))
    if not worked:
        _room(off, -2)
    off['me'] = False
    head = (f'🏢 {o["name"]}: {o["kpi"][0].lower()} {today}% · {compl} phàn nàn · tinh thần {morale}'
            + (f' · quỹ lương vượt {over}%' if over else ''))
    if not worked:
        head += ' · trợ lý xếp tạm, không có thưởng'
    good = worked and score >= GOOD_SCORE
    _log(off, f'Ngày {day}: {today}% · {compl} phàn nàn · điểm {score}' + (' ✓' if good else '') + (f' · +{bonus} xu' if bonus else ''))
    return dict(lines=[head, score_line(o, score, today, morale, compl, over, worked)] + ([rota] if rota else []) + lines[:2], bonus=bonus, score=score,
                ontime=today, compl=compl, worked=worked, good=good)


def rota_line(career: str, off: dict, plan: list) -> str:
    """F#212: the hidden cost of not rotating. Who worked today after TIRED_AT+ days in a row, said in the day's summary."""
    seen, rows = set(), []
    for w in plan:
        if w is None or w in seen:
            continue
        seen.add(w)
        st = off['staff'][w]
        if st['duty'] >= TIRED_AT:
            rows.append(f'{st["n"]} ({st["duty"]} ngày liền' + (', đang 🥱 mệt' if st['iss'] == 'tired' else '') + ')')
    if not rows:
        return ''
    verb = 'bay' if career == 'pilot' else 'làm'
    more = f' và {len(rows) - 3} người nữa' if len(rows) > 3 else ''
    return (f'🥱 Xoay ca: {", ".join(rows[:3])}{more} đã {verb} liền từ hôm trước nên dễ trễ hơn hẳn. '
            f'Xếp người khác, cho nghỉ 1 ngày là hết mệt.')


def score_line(o: dict, score: int, today: int, morale: int, compl: int, over: int, worked: bool) -> str:
    """The close's score, part by part (F#206: how an office day counts), and whether it counted."""
    parts = f'{o["kpi"][0].lower()} {round(.5 * today)} + tinh thần {round(.3 * morale)} + 20'
    if compl:
        parts += f' − phàn nàn {6 * compl}'
    if over:
        parts += f' − vượt quỹ {2 * over}'
    if not worked:
        verdict = 'chưa tính: hôm nay bạn chưa tự xếp việc nào ở 🗓️ Điều phối'
    elif score >= GOOD_SCORE:
        verdict = '✓ tính 1 ngày điều hành tốt'
    else:
        verdict = f'chưa tính: cần từ {GOOD_SCORE} điểm'
    return f'📊 Điểm điều hành {score}/100 ({parts}) → {verdict}.'


# ------------------------------------------------------------------------------------- the client's view
def _bar(off: dict, slot: dict) -> dict:
    """Who of the slot's role may not take it today, and why (off: suspended, rest: duty limit, lv: step too low)."""
    out = {}
    for i, st in enumerate(off['staff']):
        if st['r'] == slot['role']:
            code = 'off' if st['off'] else 'rest' if st['duty'] >= DUTY_MAX else 'lv' if st['lv'] < slot['need'] else None
            if code:
                out[str(i)] = code
    return out


def public(career: str, off: dict, rank: int, c: dict, seed: int) -> dict:
    o = OFFICE[career]
    lvl = _level(o, rank)
    live = ready(off, c)
    slots = _slots(career, off['day'], seed, len(off['plan']), off) if live else []
    staff = []
    for i, st in enumerate(off['staff']):
        role = o['roles'][st['r']]
        staff.append(dict(i=i, n=st['n'], t=role['ladder'][st['lv']], r=st['r'], role=role['label'], mood=st['mood'], sk=st['sk'],
                          pay=st['pay'], mk=MARK_LABEL[st['mk']], iss=o['issues'][st['iss']] if st['iss'] else None,
                          off=st['off'] > 0, duty=st['duty'], rest=st['duty'] >= DUTY_MAX, hint=TRAIT_HINT[st['tr']] if st['seen'] else None,
                          acted=st['id'] in off['acted'], top=st['lv'] >= len(role['ladder']) - 1, low=st['lv'] == 0))
    inbox = []
    for k, item in enumerate(off['inbox'] if live else ()):
        if item['pick'] is None:
            x = INBOX_INDEX[career][item['id']]
            opts = [dict(id=y['id'], label=_fill(y['label'], off, item['a'])) for y in x['options']]
            _rng('of-opts', x['id'], off['day']).shuffle(opts)   # the right answer is not always on top
            inbox.append(dict(i=k, emoji=x['emoji'], title=x['title'], text=_fill(x['text'], off, item['a']), options=opts))
    kpi = off['kpi']
    cost = sum(_cost(o, st) for st in off['staff'] if not st['off']) + off['xc']
    return dict(name=o['name'], plan_name=o['plan'], unit=o['unit'], labels=list(o['kpi']), live=live,
                kpi=dict(ontime=kpi['ontime'], compl=kpi['compl'], morale=round(sum(st['mood'] for st in off['staff']) / len(off['staff'])),
                         cost=cost, budget=off['budget'], good=kpi['good']),
                left=off['left'] if live else 0, acts=[dict(id=a, icon=ACTS[a]['icon'], label=ACTS[a]['label']) for a in o['powers'][lvl]],
                staff=staff, slots=[dict(i=i, t=s['t'], sub=s['sub'], role=s['role'],
                                         need=o['roles'][s['role']]['ladder'][s['need']] if s['need'] else None, who=off['plan'][i],
                                         bar=_bar(off, s))
                                    for i, s in enumerate(slots)],
                inbox=inbox, log=off['log'][-4:], cap=o['cap'][lvl], duty_max=DUTY_MAX, tired_at=TIRED_AT,
                me=bool(off['me']) and live, good_score=GOOD_SCORE)


# ------------------------------------------------------------------------------------- validation
OFFICE_KEYS = frozenset(('v', 'day', 'staff', 'plan', 'inbox', 'left', 'acted', 'me', 'xc', 'all', 'hires', 'budget', 'kpi', 'log'))
STAFF_KEYS = frozenset(('id', 'n', 'r', 'lv', 'pay', 'mood', 'sk', 'tr', 'seen', 'mk', 'iss', 'off', 'duty', 'cl'))


def validate(career: str, off, need, integer, txt, bad: str) -> None:
    o = OFFICE.get(career)
    need(o is not None and isinstance(off, dict) and set(off) == OFFICE_KEYS and off['v'] == 1, bad, 'invalid_save')
    integer(off['day'], 0, 10**9)
    staff = off['staff']
    need(isinstance(staff, list) and 1 <= len(staff) <= STAFF_MAX, bad)
    ids = set()
    for st in staff:
        keys = STAFF_KEYS | ({'ig'} if o.get('integrity') else set())
        need(isinstance(st, dict) and set(st) == keys and st['r'] in o['roles'] and st['tr'] in TRAITS, bad)
        if o.get('integrity'):
            integer(st['ig'], 0, 3)
        txt(st['id'], 12)
        txt(st['n'], 24)
        ids.add(st['id'])
        integer(st['lv'], 0, len(o['roles'][st['r']]['ladder']) - 1)
        integer(st['pay'], 1, PAY_MAX)
        integer(st['mood'], 0, 100)
        integer(st['sk'], 0, 100)
        integer(st['mk'], 0, len(MARK_LABEL) - 1)
        integer(st['off'], 0, 2)
        integer(st['duty'], 0, 9)
        integer(st['cl'], 0, 99)
        need(type(st['seen']) is bool and st['iss'] in (None, *_issues(o)), bad)
    need(len(ids) == len(staff), bad)
    plan = off['plan']
    need(isinstance(plan, list) and len(plan) <= 4 + len(AIR_EXTRA_SLOTS), bad)
    for w in plan:
        need(w is None or type(w) is int and 0 <= w < len(staff), bad)
    used = [w for w in plan if w is not None]
    need(len(used) == len(set(used)), bad)
    inbox = off['inbox']
    need(isinstance(inbox, list) and len(inbox) <= 2, bad)
    for item in inbox:
        need(isinstance(item, dict) and set(item) == {'id', 'a', 'pick'} and item['id'] in INBOX_INDEX[career], bad)
        need(item['a'] is None or type(item['a']) is int and 0 <= item['a'] < len(staff), bad)
        need(item['pick'] is None or item['pick'] in [y['id'] for y in INBOX_INDEX[career][item['id']]['options']], bad)
    integer(off['left'], 0, max(o['acts'].values()))
    need(isinstance(off['acted'], list) and len(off['acted']) <= STAFF_MAX and all(isinstance(x, str) and len(x) <= 12 for x in off['acted']), bad)
    need(type(off['me']) is bool and type(off['all']) is bool, bad)
    integer(off['xc'], 0, 10**4)
    integer(off['hires'], 0, 10**6)
    integer(off['budget'], 1, 10**5)
    k = off['kpi']
    need(isinstance(k, dict) and set(k) == {'ontime', 'compl', 'good', 'days'}, bad)
    integer(k['ontime'], 0, 100)
    integer(k['compl'], 0, 999)
    integer(k['good'], 0, 10**6)
    integer(k['days'], 0, 10**6)
    need(isinstance(off['log'], list) and len(off['log']) <= LOG_MAX, bad)
    for line in off['log']:
        txt(line, 140)
