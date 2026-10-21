"""📱 Studio Hẻm Xanh: a content creator (KOL) taking brand deals, one deal at a time (owner 21/10 "nghề mới thì làm đi,
làm KOL này kia luôn"; players #471, #472).

A deal is one brand's brief (a product, a mood, a format) with one or two awkward brand demands (kol_content.DEMANDS:
drop the ad label, fake a three-month review, bought views, a hit song nobody licensed, a cure claim, a fake discount…).
It is a list of server-graded steps (game/careers/stepkit.py), worked one at a time: read the brief and name the format
→ settle the demands → the opening line → [the run sheet's order, early days] → behind the camera (light, framing, a
ruined take) → [the number of takes] → the music from the studio's free library (CC0) or the livestream's product count
→ [the edit's order] → [when to post] → a comment or a message (a scam brand, a hater, a fan's question) → the numbers
for the brand (engagement or conversion %) → [what goes in the report] → the report to the right contract. A wrong answer
stays open to redo and costs quality; an honest-ad step answered wrong weighs double in the reviews. The fee (net × quality)
is paid when the report goes in; there are no parts and no stock. Between deals the studio has its surprises
(kit.desk, kol_content.DESK), some of which come back days later (marks).
"""
from __future__ import annotations

from copy import deepcopy

from . import kit
from . import kol_content as C
from . import stepkit as sk

ID = 'kol'
CERT_ID = 'kol_basics'    # certificate_content.GROUPS (hire=False): its perk is 1 xu more on each deal's fee
PREFIX = 'ko_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('ko_step',)
FREE = ('ko_intro',)
NO_TICK = ('ko_intro', 'ko_desk')
LINES = 24
HONEST = ('brand', 'binh_luan')   # step jobs that are honest-ad matters: a redo weighs double in the review
ORDER_TITLE = dict(video='Xếp kịch bản video', live='Xếp trình tự buổi live', event='Xếp việc quay sự kiện', ward='Xếp việc làm video của phường')


# ---------------------------------------------------------------- building a deal (pure: day, slot)
def _n(v: int) -> str:
    """12000 → '12.000' (Vietnamese thousands)."""
    return f'{v:,}'.replace(',', '.')


def _pick(r, rows, plan: str, deal: str) -> tuple:
    """One (text, right, wrongs) row of a pool whose 4th field limits it to some plans or deals."""
    return r.choice([x[:3] for x in rows if x[3] is None or plan in x[3] or deal in x[3]])


def _music(r, mood: str) -> tuple:
    other = r.choice([m for m in C.TRACKS if m != mood])
    rows = [('right', f'“{C.TRACKS[mood]}” · {mood} · thư viện nhạc miễn phí bản quyền'),
            ('other', f'“{C.TRACKS[other]}” · {other} · thư viện nhạc miễn phí bản quyền')]
    rows += [(f'w{i}', w) for i, w in enumerate(C.MUSIC_TRAPS)]
    opts, ids = sk.lettered(r, rows)
    return sk.step('dung', 'nhac', 'choice', 'Chọn nhạc nền', f'Brief muốn không khí {mood}. Chọn nhạc nền nào?', opts), ids['right']


def _report(r, plan: str) -> tuple:
    if plan == 'live':
        views, pct = r.choice((800, 1000, 1200, 1500, 2000)), r.randint(2, 8)
        return (sk.step('bao_cao', 'ty_le', 'number', 'Tính tỉ lệ chốt đơn',
                        f'Buổi live: {_n(views)} lượt xem, chốt {views * pct // 100} đơn. Tỉ lệ chốt đơn = số đơn ÷ lượt xem × 100. '
                        'Bao nhiêu phần trăm?', unit='%'), pct)
    views, pct = r.choice((4000, 5000, 8000, 10000, 12000, 20000)), r.randint(4, 12)
    total = views * pct // 100
    cmts, shares = total // 5, total // 10
    likes = total - cmts - shares
    return (sk.step('bao_cao', 'ty_le', 'number', 'Tính tỉ lệ tương tác',
                    f'Sau 48 giờ: {_n(views)} lượt xem, {_n(likes)} lượt thích, {_n(cmts)} bình luận, {_n(shares)} chia sẻ. '
                    'Tỉ lệ tương tác = (thích + bình luận + chia sẻ) ÷ lượt xem × 100. Bao nhiêu phần trăm?', unit='%'), pct)


def _deal_steps(r, deal: str, D: dict, level: int) -> list:
    """[(step, answer)] of the deal's own hands-on work, from the hook to the numbers."""
    plan = D['plan']
    out = []
    goal, hook, wrongs = C.HOOKS[deal]
    out.append(sk.scenario(r, 'kich_ban', 'hook', 'Chọn câu mở đầu', (f'Thông điệp brief: {goal}. Câu nào cho ba giây đầu?', hook, wrongs)))
    if plan != 'video' and level <= 1:   # a video's order is the edit's instead (below); later the studio knows it by heart
        out.append(sk.ordered(r, 'kich_ban', 'thu_tu', ORDER_TITLE[plan], 'Bấm lần lượt theo đúng sổ tay của studio.', C.STEPS[plan]))
    out.append(sk.scenario(r, 'quay', 'canh', 'Xử lý lúc quay', _pick(r, C.SHOOT, plan, deal)))
    if plan == 'live':
        total, qa, per = r.choice((60, 90)), r.choice((12, 15, 20)), r.choice((3, 4, 5))
        qa += (total - qa) % per    # the minutes left divide evenly
        out.append((sk.step('live', 'so_mon', 'number', 'Lên kịch bản món',
                            f'Lên sóng {total} phút, chừa {qa} phút trả lời câu hỏi, mỗi món giới thiệu {per} phút. Giới thiệu được bao nhiêu món?',
                            unit='món'), (total - qa) // per))
    else:
        if level == 1 and plan == 'video':
            per, n = r.choice((10, 12, 15)), r.choice((4, 5, 6))
            out.append((sk.step('quay', 'so_canh', 'number', 'Tính số cảnh cần quay',
                                f'Video dài {per * n} giây, mỗi cảnh quay tối đa {per} giây. Cần quay ít nhất bao nhiêu cảnh?', unit='cảnh'), n))
        out.append(_music(r, D['mood']))
        if level == 2 and plan == 'video':
            out.append(sk.ordered(r, 'dung', 'thu_tu', 'Dựng video đúng thứ tự', 'Bấm lần lượt các việc dựng.', C.STEPS['dung']))
    if level <= 2:   # from day 40 the report's contents take its place
        text, right, wrongs = r.choice(C.AUDIENCE)
        out.append(sk.scenario(r, 'dang', 'gio', 'Chọn giờ lên sóng' if plan == 'live' else 'Chọn giờ đăng',
                               (f'{text} Đăng lúc nào?' if plan != 'live' else f'{text} Lên sóng lúc nào?', right, wrongs)))
    out.append(sk.scenario(r, 'binh_luan', 'tra_loi', 'Trả lời bình luận, tin nhắn', _pick(r, C.COMMENTS, plan, deal)))
    out.append(_report(r, plan))
    if level >= 3:
        out.append(sk.picks(r, 'bao_cao', 'gui_gi', 'Soạn báo cáo cho nhãn hàng', 'Báo cáo gửi nhãn hàng gồm những gì?', C.REPORT_GOOD, C.REPORT_BAD))
    return out


def deal(day: int, slot: int) -> dict:
    """The brand deal of (day, slot): {steps, key, net, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    pool = [k for k in C.DEAL_ORDER if C.DEALS[k]['day'] <= day]
    name = r.choice(pool)
    D = C.DEALS[name]
    brand = D['brand'] if isinstance(D['brand'], int) else r.choice(D['brand'])
    product, twin = (D['product'], D['twin']) if D['product'] else C.LIVE_PRODUCTS[brand]
    who = C.PEOPLE[brand][0]
    say, see = r.choice(D['say']), r.choice(D['see'])
    pairs = []
    others = r.sample([k for k in C.DEAL_ORDER if k != name], 3)
    opts, ids = sk.lettered(r, [(k, C.DEALS[k]['name']) for k in [name] + others])
    pairs.append((sk.step('brief', 'dang', 'choice', 'Đọc brief, chốt dạng nội dung', f'{who}: “{say}” {see}', opts), ids[name]))
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or name in x[4] or D['plan'] in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, x in enumerate(demands):
        pairs.append(sk.scenario(r, 'brand', f'd{i + 1}', 'Nhãn hàng dặn điều oái oăm', x[1:4]))
    pairs += _deal_steps(r, name, D, level)
    code = f'HX-{day:03d}{slot:02d}'
    near = [(code, product), (code, twin), (f'HX-{day:03d}{(slot + 1) % 100:02d}', product)]
    opts, ids = sk.lettered(r, [(f'p{i}', f'Hợp đồng {c} · {who} · {p}') for i, (c, p) in enumerate(near)])
    pairs.append((sk.step('gui', 'hop_dong', 'choice', 'Gửi báo cáo đúng hợp đồng',
                          f'{who} nhắn: “Gửi báo cáo theo hợp đồng {code}, {product} nha.” Hộp thư có ba hợp đồng giống nhau. Gửi vào đâu?', opts),
                  ids['p0']))
    steps, key = sk.pairs_to_steps(pairs)
    net = D['net'] + 2 * len(demands) + level
    return dict(steps=steps, key=key, deal=name, deal_name=D['name'], emoji=D['emoji'], brand=who, product=product, code=code,
                npc=brand, opening=f'{who} gửi brief: “{say}”', net=net, demands=len(demands))


def make_task(day: int, slot: int, serial: int) -> dict:
    dl = deal(day, slot)
    needs = {k: v for k, v in dl.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, dl['npc'], f'{dl["brand"]} · {dl["product"]}', dl['opening'],
                         gen=GEN, kind='deal', needs=needs, _key=dl['key'], at=0, work={}, errors=[], wrong=0,
                         quality=100, paid=0, lines=[], stage='work')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, earned=0), desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _severity(step_id: str) -> int:
    """A redone honest-ad step (a brand demand, a comment) is a trust matter for the review."""
    return 2 if step_id.split('.')[0] in HONEST else 1


def _net(t: dict) -> int:
    return max(5, t['needs']['net'] * t['quality'] // 100)


def has_cert(s: dict) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('ko_intro', 'ko_step', 'ko_desk'), 'Thao tác ở studio không hợp lệ.')
    d = _data(c)
    if name == 'ko_intro':
        d['intro'] = True
        return dict(message='Chị Ngân đưa chiếc đèn tròn: “Người xem tin mình là vốn lớn nhất. Nói thật trước, quay đẹp sau nghe em.”')
    desk = d['desk']
    if name == 'ko_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở studio cần quyết, quyết xong rồi làm tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc brief của nhãn hàng trước đã.')
    correct, message, finished = sk.work(t, p, _quality, 'Chị Ngân', LINES, _severity)
    if not finished:
        result = dict(message=message, correct=correct)
        _after(s, c, d, result)
        return result
    n = t['needs']
    net = _net(t)
    t['paid'] = net
    good = t['quality'] >= 90
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['earned'] += net
    extra = 1 if has_cert(s) else 0
    kit.complete(s, c, t, net + extra, f'Gửi báo cáo {n["deal_name"].lower()} cho {n["brand"]}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Báo cáo đã tới đúng hợp đồng {n["code"]}. Cát-xê {net + extra} xu, chất lượng {t["quality"]}%.'
                          + (' 🎓 Nhãn hàng trả thêm 1 xu nhờ chứng chỉ.' if extra else ''),
                  correct=good, celebrate=good)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, C.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(C.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], C.DESK, None, c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], C.DESK)
    if today['day'] == c['day'] and today['good'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    lines = [f'Studio Hẻm Xanh: bạn làm {today["jobs"]} hợp đồng, {today["good"]} hợp đồng đạt từ 90%, cát-xê {today["earned"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Nhãn hàng còn dặn thêm điều oái oăm, chốt cho thật thà trước khi quay nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc brief của nhãn hàng.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Đã gửi báo cáo; nhận hợp đồng tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    honest = any(e.split('.')[0] in HONEST for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Quảng cáo trung thực', score=3 if honest else 5, note='Ghi rõ quảng cáo, nói thật, trả lời người xem đàng hoàng.'),
                          dict(key='safe', label='Báo cáo đúng số thật', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['at'] == 0:   # the first step names it: not before it is answered
        for k in ('deal', 'deal_name', 'emoji'):
            v['needs'].pop(k, None)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= C.MASTER[0] and st['active_days'] >= C.MASTER[1]
    d['expert'] = st['good'] >= C.EXPERT[0] and st['active_days'] >= C.EXPERT[1]
    d['desk'] = kit.desk_public(d['desk'], C.DESK, ID, c)
    return d


def content() -> dict:
    return dict(
        rules=C.RULES,
        deals=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.DEALS.items()],
        intro=dict(title='Một ngày ở Studio Hẻm Xanh',
                   lead='Bạn làm nhà sáng tạo nội dung, nhận hợp đồng quảng cáo của các nhãn hàng trong phố. Đọc brief, chốt cách làm, '
                        'nói thật với người xem rồi mới quay, dựng, đăng và báo cáo số liệu. Cát-xê theo từng hợp đồng, giảm theo chất lượng.',
                   work=[['📝', 'Đọc brief, chọn câu mở đầu'], ['🎥', 'Quay: ánh sáng, khung dọc, quay lại lượt hỏng'],
                         ['🎵', 'Dựng: nhạc miễn phí bản quyền'], ['📊', 'Đăng đúng giờ, trả lời bình luận, báo cáo số thật']],
                   meet=[['🎙️', 'Chị Ngân chủ studio'], ['🎬', 'Bin quay phim'], ['🍢', 'Chị Hồng tiệm bánh tráng']],
                   stars=[['🏷️', 'Ghi rõ quảng cáo, không đánh giá khống'], ['🌀', 'Nhãn hàng oái oăm: nói thật, giữ người xem']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _net, LINES, 'hợp đồng quảng cáo')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ studio sai.')
    kit.need(type(d['intro']) is bool, 'Sổ studio sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê studio sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số hợp đồng đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Nhà sáng tạo nội dung', place=C.PLACE, tagline='Nói thật trước, quay đẹp sau.', icon='camera',
              color='#7b4fc9', light='#efe7fb', weather='Đèn tròn, tiếng bấm máy và mùi cà phê sữa', work='Hợp đồng quảng cáo',
              station='Góc quay và bàn dựng',
              greeting='Đọc brief, chốt cách làm, nói thật với người xem rồi mới bấm quay.',
              caption='Người xem tin là vốn lớn nhất', map_label='STUDIO HẺM XANH'),
    staff=[('Bin', 'camera', 'Quay phim, dựng phim, giữ thẻ nhớ và pin.', 72, 80)], roles={'camera': 'Quay phim'},
    tip=1, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('📱', 'Sổ tay Studio Hẻm Xanh', [('Nhãn', 'Ghi rõ quảng cáo'), ('Quay', 'Khung dọc, đủ sáng'), ('Nhạc', 'Miễn phí bản quyền'),
                                            ('Số liệu', 'Báo số thật')],
              ['Đọc brief, chốt dạng nội dung', 'Chốt với nhãn hàng', 'Quay, dựng theo sổ tay', 'Đăng, trả lời, báo cáo']),
    stories=[('Chiếc đèn tròn đầu tiên', ('Chị Ngân đưa chiếc đèn tròn đã tróc sơn: “Cái đèn đầu tiên của chị, mua bằng cát-xê đầu tiên.”',
                                          'Bạn kéo đèn chếch sang một bên, mặt sáng lên mà không bóng nhẫy.',
                                          'Chị Ngân cười: “Đèn soi mặt mình, chữ quảng cáo soi lòng mình. Đừng tắt cái nào.”'))],
    review_asides=['Video ghi rõ quảng cáo mà vẫn thấy thật.', 'Hỏi gì cũng được trả lời đàng hoàng.', 'Nhạc nền dễ chịu, phụ đề rõ ràng.'],
    situations=[],
    more_line='Thêm một nhãn hàng vừa gửi brief.', open_line='Chị Ngân bật đèn tròn; máy quay, micro cài áo và sổ tay studio đã sẵn.',
    guide='Đọc brief, chốt dạng nội dung → chốt với nhãn hàng điều oái oăm → câu mở đầu, kịch bản → quay, nhạc, dựng theo sổ tay → '
          'đăng đúng giờ, trả lời bình luận → báo cáo số thật đúng hợp đồng. Sai thì làm lại bước đó, cát-xê giảm theo chất lượng.',
)
