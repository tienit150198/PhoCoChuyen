"""🔬 Viện nghiên cứu Sông Mây: a salaried research shift on one of three tracks chosen at the start of a shift.

🌱 Giống cây (lai tạo, khảo nghiệm ngoài đồng, ngân hàng hạt giống), 🍳 Công thức món (chuẩn hóa công thức, hội đồng
nếm thử, giá vốn và nhãn), 🛠️ Sáng chế (làm mẫu thử, thử độ bền, hồ sơ sáng chế). A lab shift opens with the safety
checklist (blouse, kính, găng, tủ hút, sổ) and closes with putting the samples away and switching every heater off; the
director's surprise safety walk checks the opening on some days. Leaving without the closing check risks spoilt samples
that night: a bounded compensation from the wallet.

The owner's standing rule (many "oái oăm" demands): rats in the seed store, a ruined trial plot, a biased taster, a
colleague who takes the credit, and from COUNCIL_DAY a council step at the end of every job (GS. Bảo wants the low
numbers gone, the sponsor wants "đột phá thế giới"…); plus the desk surprises of research_content.DESK (thí nghiệm nổ,
mẫu bị chuột ăn, hội đồng khó tính, nhà tài trợ đòi kết quả sớm, đồng nghiệp nhận vơ công, cúp điện…).

Every task step is graded on the server; a wrong step stays open to fix in place and lowers the quality (and so the
small bonus). Pay is the employment contract's salary at closing. A job's content is a pure function of (day, slot,
track), like the banquet's, so the stored task stays as made and a save validates on any date.

Player-to-player research orders (seed batches, recipes, gadgets) are game/research_lab.py: the HTTP side of the
service market, not this engine plugin (nothing of them is in the career record).
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from . import kit
from . import research_content as rc
from .. import consequences as cq

ID = 'research'
GEN = 1
PEOPLE = rc.PEOPLE
TRACKS = tuple(rc.TRACKS)
JOB_IDS = tuple(rc.JOBS)
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('rs_step', 'rs_shift')
FREE = ('rs_intro', 'rs_track')
NO_TICK = ('rs_intro', 'rs_track', 'rs_desk')
TYPES = ('choice', 'number', 'order', 'multi')
LINES = 24


# ---------------------------------------------------------------- task building
def _opts(r, rows, shuffle=True):
    out = [dict(id=k, label=v) for k, v in rows]
    if shuffle:
        r.shuffle(out)
    return out


def _step(job, name, typ, title, evidence, options=None, unit='', sheet=None):
    """`sheet`: the lines of data the step works on, shown under its words (the field book, the score sheet, the recipe
    card, the blueprint's parts): each line its own text, so the English pack translates it as the option it repeats."""
    st = dict(id=f'{job}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if unit:
        st['unit'] = unit
    if sheet:
        st['sheet'] = list(sheet)
    return st


def _council(r, job, day, steps, key):
    """From COUNCIL_DAY the job ends in front of the council with one of its demands."""
    if day < rc.COUNCIL_DAY:
        return
    ask, right = r.choice(rc.COUNCIL_ASKS)
    wrongs = r.sample(rc.COUNCIL_WRONG, 3)
    steps.append(_step(job, 'council', 'choice', 'Bảo vệ trước hội đồng', ask,
                       _opts(r, [('right', right)] + [(f'w{i}', w) for i, w in enumerate(wrongs)])))
    key[f'{job}.council'] = 'right'


def _cross(r, day, slot):
    cid, crop, unit = r.choice(rc.CROPS)
    traits = r.sample(rc.TRAITS, 5)
    target = traits[:2]
    lines = []
    for i, (tid, label) in enumerate(traits):
        lines.append((f'sm{r.randint(10, 99)}{i}', f'Dòng SM-{r.randint(10, 99)}{i}: {crop}, {label}', tid))
    r.shuffle(lines)
    need = r.randint(4, 20) * 10
    germ = r.choice(rc.GERM)
    seeds = math.ceil(need * 100 / germ)
    why = f'{rc.TARGET_WHY[target[0][0]]}, lại {rc.TARGET_WHY[target[1][0]]}'
    steps = [
        _step('cross', 'parents', 'multi', 'Chọn hai dòng bố mẹ',
              f'Cần giống {crop} vừa {target[0][1]} vừa {target[1][1]} vì {why}. Chọn đúng hai dòng mang hai đặc tính đó.',
              [dict(id=a, label=b) for a, b, _ in lines]),
        _step('cross', 'seeds', 'number', 'Tính số hạt cần gieo',
              f'Cần {need} cây con cho khảo nghiệm. Hạt lai nảy mầm khoảng {germ}%. Gieo bao nhiêu hạt (làm tròn lên)?', unit='hạt'),
        _step('cross', 'tag', 'choice', 'Ghi nhãn khay gieo', 'Bé Su đưa bút dạ: “Ghi gì lên khay hả anh chị?”', _opts(r, rc.TAGS)),
        _step('cross', 'control', 'choice', 'Bố trí khay đối chứng', 'Ông Hưng muốn thấy giống mới “ăn đứt” giống cũ trong ảnh chụp.',
              _opts(r, rc.CONTROL)),
    ]
    key = {'cross.parents': sorted(a for a, _, t in lines if t in (target[0][0], target[1][0])), 'cross.seeds': seeds,
           'cross.tag': 'full', 'cross.control': 'control'}
    _council(r, 'cross', day, steps, key)
    brief = dict(crop=crop, target=[t[1] for t in target], need=need, germ=germ, steps=steps)
    return brief, key, f'Lai giống {crop}: {target[0][1]}, {target[1][1]}', \
        f'Cô Diệu Linh giao: lai tạo giống {crop} vừa {target[0][1]} vừa {target[1][1]}. Ghi đủ, có đối chứng.', rc.DIRECTOR


def _field(r, day, slot):
    cid, crop, unit = r.choice(rc.CROPS)
    n = r.choice((4, 5))
    good = [r.randint(48, 72) for _ in range(n - 1)]
    rest = sum(good) % (n - 1)
    good[-1] -= rest   # the mean of the kept plots is a whole number
    mean = sum(good) // (n - 1)
    passed = r.random() < 0.5
    control = math.floor(mean * 100 / 115) if passed else math.ceil(mean * 100 / 104)
    passed = mean * 100 >= control * 110
    spoil, why = r.choice(rc.PLOT_SPOIL)
    bad_at = r.randrange(n)
    plots, bad_id = [], ''
    gi = 0
    for i in range(n):
        pid = f'o{i + 1}'
        if i == bad_at:
            plots.append(dict(id=pid, label=f'Ô {i + 1}: {r.randint(8, 25)} kg · {why}'))
            bad_id = pid
        else:
            plots.append(dict(id=pid, label=f'Ô {i + 1}: {good[gi]} kg'))
            gi += 1
    steps = [
        _step('field', 'exclude', 'choice', 'Loại ô hỏng ngoài thí nghiệm',
              f'Sổ ruộng của bác Tư: giống {crop} mới trồng {n} ô bằng nhau. Ô nào phải bỏ ra khỏi kết quả?', plots),
        _step('field', 'mean', 'number', 'Tính năng suất trung bình',
              'Sổ ruộng của bác Tư ở dưới. Bỏ ô hỏng ra, cộng các ô còn lại rồi chia cho số ô còn lại.', unit='kg',
              sheet=[p['label'] for p in plots]),
        _step('field', 'verdict', 'choice', 'Kết luận so với đối chứng',
              f'Ô đối chứng giống cũ đạt {control} kg. Giống mới đạt khi trung bình từ 110% đối chứng trở lên.', _opts(r, rc.VERDICT)),
    ]
    key = {'field.exclude': bad_id, 'field.mean': mean, 'field.verdict': 'pass' if passed else 'fail'}
    if day >= rc.RATS_DAY and r.random() < 0.5:
        steps.insert(1, _step('field', 'rats', 'choice', 'Xử lý túi mẫu bị chuột gặm',
                              'Sáng nay kho mẫu có hai túi hạt lấy từ ruộng bị chuột gặm thủng. Chiều phải gửi mẫu cho hội đồng.', _opts(r, rc.RATS)))
        key['field.rats'] = 'log'
    _council(r, 'field', day, steps, key)
    brief = dict(crop=crop, plots=n, control=control, steps=steps)
    return brief, key, f'Khảo nghiệm {crop} ở ruộng bác Tư', \
        f'Bác Tư gửi sổ ruộng vụ này. Tính năng suất giống {crop} mới, loại ô hỏng, so với đối chứng.', 6


def _bank(r, day, slot):
    cid, crop, unit = r.choice(rc.CROPS)
    rate = r.choice((1, 2, 3))
    target = r.choice((8, 9, 10, 11, 12))
    hours = r.randint(2, 6)
    now = target + rate * hours
    tried = r.choice((50, 100))
    grew = r.randint(int(tried * .6), tried)
    germ = grew * 100 // tried
    steps = [
        _step('bank', 'order', 'order', 'Sắp quy trình cất giống', 'Bấm các việc theo đúng thứ tự trong sổ ngân hàng hạt giống.', _opts(r, rc.BANK_STEPS)),
        _step('bank', 'hours', 'number', 'Tính giờ sấy',
              f'Hạt {crop} đang ẩm {now}%, độ ẩm chuẩn để cất là {target}%. Máy sấy rút được {rate}% mỗi giờ.', unit='giờ'),
        _step('bank', 'germ', 'number', 'Ghi tỷ lệ nảy mầm',
              f'Ươm thử {tried} hạt, đếm được {grew} cây mọc. Tỷ lệ nảy mầm bao nhiêu phần trăm?', unit='%'),
        _step('bank', 'store', 'choice', 'Chọn chỗ cất', 'Túi hạt đã dán nhãn xong.', _opts(r, rc.STORE)),
    ]
    key = {'bank.order': [k for k, _ in rc.BANK_STEPS], 'bank.hours': hours, 'bank.germ': germ, 'bank.store': 'cold'}
    _council(r, 'bank', day, steps, key)
    brief = dict(crop=crop, steps=steps)
    return brief, key, f'Cất giống {crop} vào ngân hàng hạt', \
        f'Chị Nhàn nhờ: lô hạt {crop} vừa thu, sấy, thử nảy mầm rồi cất kho đúng quy trình.', 2


def _scale(r, day, slot):
    did, name, main, grams, order = r.choice(rc.DISHES)
    servings = r.choice(rc.SERVINGS)
    steps = [
        _step('scale', 'grams', 'number', f'Tính lượng {main}', f'Công thức gốc {name.lower()}: {grams} g {main} cho 4 suất. Bếp ăn đặt {servings} suất.', unit='g'),
        _step('scale', 'variable', 'choice', 'Thiết kế lần thử', 'Lần trước khách chê hơi ngọt. Lần thử này đổi gì?', _opts(r, rc.VARIABLE)),
        _step('scale', 'order', 'order', f'Làm {name.lower()} đúng thứ tự',
              'Bấm từng công đoạn theo thứ tự của thẻ công thức (thứ tự nào đúng thẻ cũng được).', _opts(r, order), sheet=[rc.DISH_CARD[did]]),
        _step('scale', 'log', 'choice', 'Ghi sổ thí nghiệm', 'Mẻ thứ hai hơi khét đáy nồi.', _opts(r, rc.LABBOOK)),
    ]
    key = {'scale.grams': grams * servings // 4, 'scale.variable': 'one', 'scale.order': [k for k, _ in order], 'scale.log': 'all'}
    _council(r, 'scale', day, steps, key)
    brief = dict(dish=name, servings=servings, steps=steps)
    return brief, key, f'Chuẩn hóa {name.lower()} cho {servings} suất', \
        f'Bếp ăn trường Sông Mây đặt công thức {name.lower()} cho {servings} suất. Chuẩn từng gam, ghi từng lần.', rc.DIRECTOR


def _taste(r, day, slot):
    did, name, *_ = r.choice(rc.DISHES)
    codes = r.sample(range(100, 1000), 3)
    who = r.sample(rc.TASTERS, 5)
    biased_at = r.randrange(5)
    why, _ = r.choice(rc.BIASED)
    while True:
        scores = [[r.randint(3, 9) for _ in range(3)] for _ in range(5)]
        totals = [sum(row[v] for i, row in enumerate(scores) if i != biased_at) for v in range(3)]
        if totals.count(max(totals)) == 1:
            break
    best = totals.index(max(totals))
    table = [dict(id=f't{i}', label=f'{who[i]}' + (f' ({why.lower()})' if i == biased_at else '') + ' chấm: ' +
                  ' · '.join(f'{codes[v]}: {scores[i][v]}' for v in range(3))) for i in range(5)]
    sheet = [row['label'] for row in table]
    steps = [
        _step('taste', 'code', 'choice', 'Mã hóa mẫu', f'Ba công thức {name.lower()} sắp đưa ra hội đồng nếm.', _opts(r, rc.CODING)),
        _step('taste', 'exclude', 'choice', 'Bỏ điểm người nếm không khách quan', 'Phiếu điểm (thang 1–9). Điểm của ai không được tính?', table),
        _step('taste', 'total', 'number', 'Tính tổng điểm mẫu thắng', 'Cộng điểm của bốn người còn lại cho mẫu có tổng cao nhất.', unit='điểm',
              sheet=sheet),
        _step('taste', 'best', 'choice', 'Chọn mẫu thắng', 'Mẫu nào thắng sau khi bỏ điểm không khách quan?',
              [dict(id=f'm{codes[v]}', label=f'Mẫu số {codes[v]}') for v in range(3)], sheet=sheet),
    ]
    key = {'taste.code': 'blind', 'taste.exclude': f't{biased_at}', 'taste.total': totals[best], 'taste.best': f'm{codes[best]}'}
    _council(r, 'taste', day, steps, key)
    brief = dict(dish=name, codes=codes, steps=steps)
    return brief, key, f'Hội đồng nếm {name.lower()}', \
        f'Chiều nay hội đồng nếm ba công thức {name.lower()}. Mã hóa mẫu, bỏ điểm thiếu khách quan, chọn mẫu thắng.', 1


def _cost(r, day, slot):
    did, name, *_ = r.choice(rc.DISHES)
    servings = r.choice((10, 20, 25, 40, 50))
    unit = r.randint(3, 12)
    pool = rc.DISH_INGREDIENTS[did]   # what this dish is made of: its core, and two of the rest
    rows = pool[:rc.DISH_CORE] + r.sample(pool[rc.DISH_CORE:], 5 - rc.DISH_CORE)
    parts = [r.randint(1, 4) for _ in rows]
    total = unit * servings
    weights = sum(parts)
    amounts = [total * p // weights for p in parts]
    amounts[0] += total - sum(amounts)
    margin = r.choice((30, 40, 50))
    floor_price = math.ceil(unit * (100 + margin) / 100)
    prices = sorted({floor_price - r.randint(1, 2), floor_price, floor_price + r.randint(2, 4), floor_price + r.randint(5, 9)})
    price = min(p for p in prices if p * 100 >= unit * (100 + margin))
    allergens = sorted({tag for (_, tag) in rows if tag})
    steps = [
        _step('cost', 'unit', 'number', 'Tính giá vốn mỗi suất',
              f'Mẻ {servings} suất {name.lower()}: ' + ' · '.join(f'{n.lower()} hết {a} xu' for (n, _), a in zip(rows, amounts)) + '.', unit='xu'),
        _step('cost', 'price', 'choice', 'Chọn giá bán', f'Quán muốn lời ít nhất {margin}% trên giá vốn. Chọn mức thấp nhất mà vẫn đạt.',
              [dict(id=f'p{p}', label=f'{p} xu một suất') for p in prices]),
        _step('cost', 'allergen', 'multi', 'Ghi chất gây dị ứng lên nhãn', 'Thành phần: ' + ' · '.join(n.lower() for n, _ in rows) + '. Chọn mọi chất gây dị ứng có trong món (không có thì để trống).',
              [dict(id=k, label=v) for k, v in rc.ALLERGENS.items()]),
        _step('cost', 'claim', 'choice', 'Duyệt câu chữ trên nhãn', 'Ông Hưng muốn nhãn “bán chạy hơn”.', _opts(r, rc.CLAIMS)),
    ]
    key = {'cost.unit': unit, 'cost.price': f'p{price}', 'cost.allergen': allergens, 'cost.claim': 'true'}
    _council(r, 'cost', day, steps, key)
    brief = dict(dish=name, servings=servings, margin=margin, steps=steps)
    return brief, key, f'Giá vốn và nhãn {name.lower()}', \
        f'Quán cơm đầu hẻm đặt viện tính giá vốn và làm nhãn cho món {name.lower()}.', rc.SPONSOR


def _proto(r, day, slot):
    gid, name, parts, what = r.choice(rc.GADGETS)
    others = [k for k in rc.PARTS if k not in parts]
    shown = list(parts) + r.sample(others, 3)
    r.shuffle(shown)
    volts, drop, ma = r.choice(rc.OHM)
    ohm = (volts - drop) * 1000 // ma
    steps = [
        _step('proto', 'parts', 'multi', 'Lấy đủ linh kiện',
              f'Bản vẽ “{name}” ({what}) ghi đủ linh kiện ở dưới. Lấy đủ, không lấy thừa món nào trên khay.', sheet=[rc.PARTS[x] for x in parts],
              options=[dict(id=x, label=rc.PARTS[x]) for x in shown]),
        _step('proto', 'battery', 'choice', 'Chọn nguồn pin', 'Kho còn mấy loại pin.', _opts(r, rc.BATTERY)),
        _step('proto', 'ohm', 'number', 'Tính điện trở cho đèn báo',
              f'Nguồn {volts} V, đèn LED báo sụt {drop} V, cần dòng {ma} mA. Điện trở bao nhiêu ôm?', unit='Ω'),
        _step('proto', 'test', 'order', 'Sắp thứ tự chạy thử an toàn', 'Bấm từng bước thử theo sổ an toàn của bàn sáng chế.', _opts(r, rc.TEST_ORDER)),
    ]
    key = {'proto.parts': sorted(parts), 'proto.battery': 'safe', 'proto.ohm': ohm, 'proto.test': [k for k, _ in rc.TEST_ORDER]}
    _council(r, 'proto', day, steps, key)
    brief = dict(gadget=name, steps=steps)
    return brief, key, f'Mẫu thử: {name.lower()}', \
        f'Bàn sáng chế nhận làm mẫu thử “{name}”. Đủ linh kiện, đúng pin, thử an toàn từng bước.', 2


def _drop(r, day, slot):
    gid, name, *_ = r.choice(rc.GADGETS)
    n = 10
    need = r.choice((80, 100, 120, 150))
    vals = [r.choice((need - 40, need - 20, need + 10, need + 30, need + 50, need + 70)) for _ in range(n)]
    if all(v >= need for v in vals):
        vals[r.randrange(n)] = need - 20
    fails = sorted(f's{i + 1}' for i, v in enumerate(vals) if v < need)
    steps = [
        _step('drop', 'fail', 'multi', 'Chọn mẫu hỏng',
              f'Yêu cầu: “{name}” chịu được rơi từ {need} cm. Kết quả thả rơi mười mẫu, chọn mọi mẫu không đạt.',
              [dict(id=f's{i + 1}', label=f'Mẫu {i + 1}: nứt ở {v} cm' if v < need + 60 else f'Mẫu {i + 1}: nguyên vẹn tới {v} cm') for i, v in enumerate(vals)]),
        _step('drop', 'rate', 'number', 'Tính tỷ lệ hỏng', 'Số mẫu hỏng nhân 100 chia cho số mẫu.', unit='%'),
        _step('drop', 'decide', 'choice', 'Quyết định sau thử nghiệm', 'Anh Quý gợi ý: “Bỏ mấy mẫu hỏng đi cho báo cáo gọn.”', _opts(r, rc.DROP_VERDICT)),
    ]
    key = {'drop.fail': fails, 'drop.rate': len(fails) * 100 // n, 'drop.decide': 'fix'}
    _council(r, 'drop', day, steps, key)
    brief = dict(gadget=name, need=need, steps=steps)
    return brief, key, f'Thử độ bền {name.lower()}', f'Lô mười mẫu “{name}” vừa qua bàn thả rơi. Ghi đúng, quyết định đúng.', 2


def _patent(r, day, slot):
    gid, name, *_ = r.choice(rc.GADGETS)
    feats = r.sample(rc.FEATURES, 3)
    new = feats[2]
    claims = r.randint(6, 18)
    fee = rc.FEE_BASE + max(0, claims - rc.FEE_FREE) * rc.FEE_PER
    steps = [
        _step('patent', 'novel', 'choice', 'Tìm điểm mới',
              f'“{name}” của viện: {feats[0][1]}, {feats[1][1]}, {feats[2][1]}. Tra cứu: thiết bị A đã có tính năng “{feats[0][1]}”; thiết bị B đã có “{feats[1][1]}”. Điểm nào là mới?',
              _opts(r, [(k, label[0].upper() + label[1:]) for k, label in feats])),
        _step('patent', 'fee', 'number', 'Tính phí nộp đơn',
              f'Đơn có {claims} điểm yêu cầu bảo hộ. Phí {rc.FEE_BASE} xu, cộng {rc.FEE_PER} xu cho mỗi điểm vượt quá {rc.FEE_FREE}.', unit='xu'),
        _step('patent', 'book', 'choice', 'Chuẩn bị bằng chứng', 'Hội đồng sáng chế đòi bằng chứng ngày làm ra.', _opts(r, rc.NOTEBOOK_OPT)),
        _step('patent', 'credit', 'choice', 'Ghi tên tác giả', 'Anh Quý muốn đứng tên tác giả chính dù chỉ góp ý một lần lúc uống trà.', _opts(r, rc.CREDIT)),
    ]
    key = {'patent.novel': new[0], 'patent.fee': fee, 'patent.book': 'signed', 'patent.credit': 'true'}
    _council(r, 'patent', day, steps, key)
    brief = dict(gadget=name, steps=steps)
    return brief, key, f'Hồ sơ sáng chế {name.lower()}', f'Cô Diệu Linh: nộp hồ sơ sáng chế “{name}” trong tuần. Đúng điểm mới, đúng phí, đúng tác giả.', rc.DIRECTOR


BUILD = dict(cross=_cross, field=_field, bank=_bank, scale=_scale, taste=_taste, cost=_cost, proto=_proto, drop=_drop, patent=_patent)


def job_of(day: int, slot: int, track: str) -> str:
    """The job of (day, slot) on `track`: each track rotates through its own jobs."""
    jobs = rc.TRACK_JOBS[track]
    return jobs[(day - 1 + slot) % len(jobs)]


def brief(day: int, slot: int, track: str) -> tuple:
    """(brief with its steps, steps, answer key, title, opening, npc index, job) of (day, slot) on `track`. Pure."""
    job = job_of(day, slot, track)
    b, key, title, opening, npc = BUILD[job](kit.rng(ID, job, day, slot), day, slot)
    return b, b['steps'], key, title, opening, npc, job


def make_task(day: int, slot: int, serial: int) -> dict:
    """The stored slip is the same for every track (the track is chosen when the shift starts): its brief is built on read."""
    return kit.base_task(ID, day, slot, serial, rc.DIRECTOR, 'Phiếu việc của viện', 'Cô Diệu Linh đưa phiếu việc của ca.',
                         gen=GEN, kind='shift', needs={}, _key={}, track='seed',
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work')


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _track(t: dict) -> str:
    return t.get('track') if t.get('track') in TRACKS else 'seed'


def _active(t: dict) -> tuple:
    b, steps, key, *_ = brief(t['day'], _slot(t), _track(t))
    return b, steps, key


def _job(t: dict) -> str:
    return job_of(t['day'], _slot(t), _track(t))


def _quality(wrong: int) -> int:
    return max(rc.QUALITY_FLOOR, 100 - rc.WRONG_COST * wrong)


# The way to work out a number step, said on its first slip; the second slip shows the answer.
HOW = {
    'cross.seeds': 'Lấy số cây con nhân 100 rồi chia tỷ lệ nảy mầm, có lẻ thì làm tròn lên.',
    'field.mean': 'Bỏ ô hỏng ra, cộng các ô còn lại rồi chia cho số ô còn lại.',
    'bank.hours': 'Lấy độ ẩm hiện tại trừ độ ẩm chuẩn, chia cho số phần trăm máy rút được mỗi giờ.',
    'bank.germ': 'Số cây mọc nhân 100, chia cho số hạt ươm thử.',
    'scale.grams': 'Lấy lượng cho 4 suất nhân số suất, chia 4.',
    'taste.total': 'Bỏ hàng điểm của người không khách quan, cộng điểm của mẫu cao nhất ở bốn hàng còn lại.',
    'cost.unit': 'Cộng tiền mọi nguyên liệu, chia cho số suất.',
    'proto.ohm': 'Lấy điện áp nguồn trừ điện áp đèn, chia cho dòng điện tính bằng ampe (20 mA = 0,02 A).',
    'drop.rate': 'Đếm số mẫu hỏng, nhân 100, chia cho 10 mẫu.',
    'patent.fee': f'Phí {rc.FEE_BASE} xu, cộng {rc.FEE_PER} xu cho mỗi điểm vượt quá {rc.FEE_FREE} (không vượt thì không cộng).',
}


def _bonus(t: dict) -> int:
    return max(3, round(rc.BONUS[_job(t)] * t['quality'] / 100))


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _dish_of(order: list) -> str | None:
    return next((d[0] for d in rc.DISHES if [k for k, _ in d[4]] == list(order)), None)


def correct(st: dict, value, right) -> bool:
    """Is `value` a right answer of step `st` (`right`: the key's answer)? A recipe's order step takes every order that
    keeps its card (rc.DISH_AFTER); every other step has one answer."""
    if st['id'] == 'scale.order' and isinstance(value, list) and isinstance(right, list):
        did = _dish_of(right)
        if did and sorted(value) == sorted(right) and len(set(value)) == len(value):
            at = {k: i for i, k in enumerate(value)}
            return all(at[b] < at[a] for a, before in rc.DISH_AFTER[did].items() for b in before)
    return _same(value, right)


# ---------------------------------------------------------------- shift checklists (pure by day)
def shift_steps(day: int, part: str) -> tuple:
    """The lab's opening ('open') or closing ('close') checklist of `day`: (steps, key). Pure."""
    r = kit.rng(ID, 'shift', part, day)
    if part == 'open':
        steps = [_step('open', 'safety', 'order', 'An toàn đầu ca', 'Bấm các việc theo đúng thứ tự dán ở cửa phòng thí nghiệm. Viện trưởng có thể đi kiểm tra bất chợt.',
                       _opts(r, rc.OPEN_STEPS))]
        return steps, {'open.safety': [k for k, _ in rc.OPEN_STEPS]}
    rows = []
    for eid, label, on, off in rc.EQUIPMENT:
        state = r.choice((on, off))
        rows.append((eid, f'{label}: {state[0]}', state[1]))
    if not any(x[2] for x in rows):
        i = r.randrange(6)   # at least one heater is left on tonight
        eid, label, on, _ = rc.EQUIPMENT[i]
        rows[i] = (eid, f'{label}: {on[0]}', True)
    steps = [_step('close', 'clean', 'order', 'Dọn phòng cuối ca', 'Bấm các việc dọn theo đúng thứ tự trong sổ phòng thí nghiệm.', _opts(r, rc.CLOSE_ORDER)),
             _step('close', 'power', 'multi', 'Tắt thiết bị', 'Chọn mọi thiết bị phải tắt trước khi về. Tủ ấm ươm mầm và tủ lạnh mẫu luôn để chạy.',
                   [dict(id=a, label=lbl) for a, lbl, _ in rows])]
    return steps, {'close.clean': [k for k, _ in rc.CLOSE_ORDER], 'close.power': sorted(a for a, _, need in rows if need)}


def safety_day(day: int) -> bool:
    return day >= 2 and kit.rng(ID, 'safety', day).random() < rc.SAFETY_CHANCE


def night_fine(c: dict) -> int:
    """The compensation spoilt samples cost (before the wallet cap): NIGHT_PCT of the contract salary, NIGHT_MIN..NIGHT_CAP."""
    salary = (c.get('job') or {}).get('salary') if isinstance(c.get('job'), dict) else None
    salary = salary if type(salary) is int and salary > 0 else 54
    return max(rc.NIGHT_MIN, min(rc.NIGHT_CAP, round(salary * rc.NIGHT_PCT / 100)))


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0, lab=0, ljobs=0, open_at=0, close_at=0, slips=0, safety=0, night=0)


def initial() -> dict:
    return dict(intro=False, track='seed', today=_today(0), last_active_day=0,
                stats=dict(jobs=0, good=0, active_days=0, bonus=0, safety_pass=0, safety_fail=0, nights=0, fined=0,
                           tracks={k: 0 for k in TRACKS}),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _open_done(today: dict) -> bool:
    return today['open_at'] >= len(shift_steps(today['day'], 'open')[0])


def _close_done(today: dict) -> bool:
    return today['close_at'] >= len(shift_steps(today['day'], 'close')[0])


# ---------------------------------------------------------------- actions
def _value(st: dict, value):
    typ = st['type']
    if typ == 'choice':
        return kit.one_of(value, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(value, 0, 100000)
    ids = [o['id'] for o in st['options']]
    got = kit.id_list(value, ids, len(ids))
    if typ == 'order':
        kit.need(len(got) == len(ids), 'Xếp đủ mọi việc theo thứ tự nhé.')
        return list(got)
    return sorted(got)


def _restamp(c: dict, track: str) -> int:
    """Today's unread slips follow the track just chosen; a slip already read keeps its own."""
    n = 0
    for t in c['tasks']:
        if t.get('career') == ID and t.get('status') == 'new' and not t.get('known') and t.get('at') == 0 and t.get('track') != track:
            t['track'] = track
            n += 1
    return n


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('rs_intro', 'rs_track', 'rs_step', 'rs_shift', 'rs_desk'), 'Thao tác ở viện không hợp lệ.')
    d = _data(c)
    if name == 'rs_intro':
        d['intro'] = True
        return dict(message='Chị Nhàn đưa áo blouse: chọn hướng nghiên cứu cho ca này rồi bắt đầu nhé!')
    if name == 'rs_track':
        track = kit.one_of(p.get('track'), TRACKS, 'Hướng nghiên cứu không hợp lệ.')
        d['track'] = track
        n = _restamp(c, track)
        label = rc.TRACKS[track][0]
        return dict(message=f'Ca này bạn làm hướng {label.lower()}.' + (f' {n} phiếu chưa đọc chuyển theo hướng mới.' if n and c.get('open') else ''))
    desk = d['desk']
    if name == 'rs_desk':
        return kit.desk_choose(s, c, ID, desk, rc.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện cần quyết ở viện, quyết xong rồi làm tiếp nhé.')
    if name == 'rs_shift':
        return _shift(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu việc trước khi làm nhé.')
    _, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    today = d['today']
    kit.need(not _close_done(today), 'Phòng thí nghiệm đã dọn và tắt điện cho ca này. Việc còn lại để ca sau làm tiếp nhé.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    today['lab'] = 1
    if not correct(st, value, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        again = 'Tính lại cho kỹ nhé.' if st['type'] == 'number' else 'Đọc lại phiếu và sổ của viện rồi làm lại bước này.'
        who = 'GS. Bảo' if st['id'].endswith('.council') else 'Chị Nhàn'
        message = f'Chưa đúng: {st["title"].lower()}. {kit.step_help(t, st, key[st["id"]], HOW.get(st["id"], ""), again, who)}'
        t['lines'] = (t['lines'] + [message[:480]])[-LINES:]
        result = dict(message=message, correct=False)
        _after(s, c, d, result)
        return result
    t['work'][st['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-LINES:]
    if t['at'] < len(steps):
        result = dict(message='Đúng rồi. Tiếp: ' + steps[t['at']]['title'].lower() + '.', correct=True)
        _after(s, c, d, result)
        return result
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= 90
    track = _track(t)
    for bucket in (today, d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    if good:
        d['stats']['tracks'][track] += 1
    job = rc.JOBS[_job(t)]
    kit.complete(s, c, t, bonus, f'Xong việc {job[0].lower()}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Xong: {job[0].lower()}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.', correct=good, celebrate=good)
    today['ljobs'] += 1
    _safety(s, c, d, t, result)
    _after(s, c, d, result)
    return result


def _shift(s: dict, c: dict, d: dict, p: dict) -> dict:
    """One step of the lab's opening or closing checklist."""
    today = d['today']
    part = kit.one_of(p.get('part'), ('open', 'close'), 'Chọn việc đầu ca hay cuối ca nhé.')
    steps, key = shift_steps(today['day'], part)
    field = part + '_at'
    at = today[field]
    kit.need(at < len(steps), 'Việc đầu ca đã xong.' if part == 'open' else 'Phòng thí nghiệm đã dọn và tắt điện xong.')
    if part == 'close':
        busy = [t for t in c['tasks'] if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled')
                and t.get('at', 0) > 0]
        kit.need(not busy, 'Còn việc đang làm dở, xong việc rồi mới dọn phòng nhé.')
    st = steps[at]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở nhé.')
    value = _value(st, p.get('value'))
    today['lab'] = 1
    if not _same(value, key[st['id']]):
        today['slips'] = min(today['slips'] + 1, 999)
        return dict(message=f'Chưa đúng: {st["title"].lower()}. Xem lại sổ phòng thí nghiệm rồi làm lại nhé.', correct=False)
    today[field] = at + 1
    if today[field] < len(steps):
        return dict(message='Đúng rồi. Tiếp: ' + steps[today[field]]['title'].lower() + '.', correct=True)
    if part == 'open':
        return dict(message='🥽 Áo blouse, kính, găng, tủ hút đã chạy, sổ đã ghi giờ. Vào ca thôi!', correct=True)
    return dict(message='🔌 Mẫu đã cất, tủ hóa chất đã khóa, thiết bị đã tắt. Yên tâm về nhé!', correct=True, celebrate=True)


def _safety(s: dict, c: dict, d: dict, t: dict, result: dict) -> None:
    """🦺 On a safety-walk day the director comes by after the first finished job."""
    today = d['today']
    if today['safety'] or today['ljobs'] != 1 or not safety_day(c['day']):
        return
    ok = _open_done(today)
    today['safety'] = 1 if ok else 2
    npc = kit.npc_id(ID, rc.DIRECTOR)
    if ok:
        d['stats']['safety_pass'] += 1
        c['xp'] += 6
        line = '🦺 Cô Diệu Linh đi kiểm tra an toàn: áo blouse, kính, găng đủ, tủ hút chạy, sổ ghi giờ. Đạt!'
        kit.log(s, c, 'surprise', line, npc, t['id'])
    else:
        d['stats']['safety_fail'] += 1
        line = '🦺 Cô Diệu Linh đi kiểm tra an toàn: chưa đeo kính, chưa bật tủ hút. Bị ghi nhắc nhở vào sổ.'
        kit.log(s, c, 'surprise', line, npc, t['id'])
        kit.review(s, c, npc, 2, 'Làm thí nghiệm mà chưa đeo kính, chưa bật tủ hút. Đã nhắc nhở.', t['id'])
    result['message'] = f'{result.get("message", "")} {line}'.strip()
    result['safety'] = 'pass' if ok else 'fail'


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, rc.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(rc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new slip takes the track chosen for the shift."""
    if t.get('career') == ID and t.get('status') == 'new' and t.get('at') == 0:
        d = _data(c)
        t['track'] = d['track'] if d['track'] in TRACKS else 'seed'


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], rc.DESK, None, c['life'].get('mode') == 'festival')


def _night(s: dict, c: dict, d: dict) -> str | None:
    """🌙 Lab work today and no closing check: spoilt samples on NIGHT_CHANCE of such nights; the compensation leaves the wallet."""
    today = d['today']
    if not today['lab'] or _close_done(today) or today['night']:
        return None
    seed = int((s.get('journey') or {}).get('seed') or 0) if isinstance(s.get('journey'), dict) else 0
    if kit.rng(ID, 'night', seed, c['day']).random() >= rc.NIGHT_CHANCE:
        return '⚠️ Ca hôm nay chưa tắt thiết bị, may mà đêm nay không sao. Lần sau nhớ kiểm cuối ca nhé.'
    fine = night_fine(c)
    j = s.get('journey') if isinstance(s.get('journey'), dict) else None
    if j and j.get('story'):
        paid = max(0, min(fine, int(j['wallet'])))
        if paid:
            from .. import journey as jr
            jr._wallet(j, -paid, 'life', '🌙 Đền mẫu hỏng ở Viện nghiên cứu Sông Mây')
    else:
        paid = max(0, min(fine, int(c['money'])))
        if paid:
            kit.money(s, c, -paid, 'Đền mẫu hỏng qua đêm', f'night-{c["day"]}', 'event_cost')
    today['night'] = max(1, paid)
    d['stats']['nights'] += 1
    d['stats']['fined'] += paid
    kit.review(s, c, kit.npc_id(ID, 2), 2, 'Cuối ca quên tắt máy sấy và bếp từ, sáng ra cả khay mẫu hỏng.', f'night-{c["day"]}')
    return (f'🌙 Đêm qua máy chạy suốt vì cuối ca chưa tắt, một khay mẫu hỏng. Tiền đền {paid} xu đã trừ vào ví.'
            if paid else '🌙 Đêm qua máy chạy suốt vì cuối ca chưa tắt, một khay mẫu hỏng. Ví đang trống nên chưa trừ đồng nào.')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], rc.DESK)
    lines = [f'Viện Sông Mây: {today["jobs"]} việc xong, {today["good"]} việc đạt từ 90%. Thưởng chất lượng: {today["bonus"]} xu.']
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    if today['lab']:
        lines.append(('🥽 Đầu ca đã mặc đồ bảo hộ, bật tủ hút.' if _open_done(today) else '🥽 Ca hôm nay chưa làm an toàn đầu ca.')
                     + (' 🔌 Cuối ca đã cất mẫu, tắt thiết bị.' if _close_done(today) else ''))
    night = _night(s, c, d)
    if night:
        lines.append(night)
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Ngày có việc đạt từ 90% mới ghi vào hành trình nghề.')


def known_request(c: dict, t: dict) -> str:
    b, _, _, title, opening, _, job = brief(t['day'], _slot(t), _track(t))
    j = rc.JOBS[job]
    return f'{j[0]}: {opening}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết việc của ca và yêu cầu của viện.'
    _, steps, _ = _active(t)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Việc đã xong; nhận việc tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Trung thực với số liệu', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    b, _, _, title, opening, npc, job = brief(t['day'], _slot(t), _track(t))
    v['title'] = title
    v['opening'] = opening
    v['needs'] = deepcopy(b) if t['known'] else None
    j = rc.JOBS[job]
    tr = rc.TRACKS[_track(t)]
    v['job'] = dict(id=job, label=j[0], emoji=j[1])
    v['track_info'] = dict(id=_track(t), label=tr[0], emoji=tr[1])
    v['client_npc'] = kit.npc_id(ID, npc)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    tracks = sum(1 for k in TRACKS if stats['tracks'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and tracks >= m['tracks']) for m in rc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, tracks=tracks)
    d['desk'] = kit.desk_public(d['desk'], rc.DESK, ID, c)
    today = d['today'] if d['today']['day'] == c['day'] else _today(c['day'])
    shift = {}
    for part in ('open', 'close'):
        steps, _ = shift_steps(c['day'], part)
        at = today[part + '_at']
        shift[part] = dict(at=at, total=len(steps), done=at >= len(steps), step=deepcopy(steps[at]) if at < len(steps) else None)
    shift.update(lab=bool(today['lab']), safety=('', 'pass', 'fail')[today['safety']], night=today['night'])
    d['shift'] = shift
    d['night_fine'] = night_fine(c)
    return d


def content() -> dict:
    return dict(
        notebook=rc.NOTEBOOK,
        tracks=[dict(id=k, label=v[0], emoji=v[1], work=v[2]) for k, v in rc.TRACKS.items()],
        jobs=[dict(id=k, label=v[0], emoji=v[1], track=v[2]) for k, v in rc.JOBS.items()],
        night=dict(chance=round(rc.NIGHT_CHANCE * 100), pct=rc.NIGHT_PCT, min=rc.NIGHT_MIN, cap=rc.NIGHT_CAP),
        council_day=rc.COUNCIL_DAY,
        intro=dict(title='Một ca ở Viện nghiên cứu Sông Mây',
                   lead='Viện nhỏ bên bờ sông Mây: ruộng thử của bác Tư, một bếp thử và một bàn sáng chế. Đầu ca bạn chọn hướng nghiên cứu. '
                        'Lương ca theo hợp đồng, thưởng chất lượng nhỏ; người chơi khác còn đặt viện làm giống, công thức, đồ sáng chế.',
                   work=[['🌱', 'Giống cây: lai tạo, khảo nghiệm, ngân hàng hạt giống'], ['🍳', 'Công thức món: chuẩn hóa, hội đồng nếm, giá vốn và nhãn'],
                         ['🛠️', 'Sáng chế: mẫu thử, thử độ bền, hồ sơ sáng chế']],
                   meet=[['👩‍🔬', 'Cô Diệu Linh viện trưởng'], ['🧪', 'Chị Nhàn kỹ thuật viên'], ['🧐', 'GS. Bảo hội đồng khoa học'], ['🦹', 'Anh Quý hay nhận vơ công']],
                   stars=[['🥽', 'Đầu ca mặc blouse, đeo kính, găng, bật tủ hút'],
                          ['🔌', f'Cuối ca cất mẫu, tắt thiết bị: quên là có thể hỏng mẫu, đền {rc.NIGHT_PCT}% lương ca (tối đa {rc.NIGHT_CAP} xu) từ ví'],
                          ['🧐', f'Từ ngày {rc.COUNCIL_DAY}: việc nào cũng qua hội đồng, giữ số liệu thật']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu của viện bị thay đổi: ' + k)
    kit.need(t.get('track') in TRACKS, 'Hướng nghiên cứu của phiếu không hợp lệ.')
    _, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu của viện sai.')
    kit.need(at == 0 or t['known'], 'Chưa đọc phiếu việc.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    kit.need(all(correct(steps[i], work[sid], key[sid]) for i, sid in enumerate(ids[:at])), 'Kết quả bước nghiên cứu sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi của viện sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi của viện sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(t.get('quality') == _quality(wrong), 'Điểm chất lượng của viện không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (_bonus(t) if at == len(steps) else 0), 'Tiền thưởng của viện không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký của viện sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Phiếu của viện chưa xong mà đã hoàn tất.')
    kit.need(at == 0 or t.get('status') != 'new', 'Phiếu của viện sai trạng thái.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ của viện sai.')
    kit.need(type(d['intro']) is bool, 'Sổ của viện sai.')
    kit.need(d['track'] in TRACKS, 'Hướng nghiên cứu trong ca sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    today = d['today']
    kit.need(isinstance(today, dict) and set(today) == set(base['today']), 'Số liệu của viện sai.')
    for v in today.values():
        kit.integer(v, 0, 10**9)
    for k in ('counted', 'lab'):
        kit.integer(today[k], 0, 1)
    kit.integer(today['safety'], 0, 2)
    kit.integer(today['night'], 0, rc.NIGHT_CAP)
    kit.integer(today['slips'], 0, 999)
    kit.integer(today['open_at'], 0, len(shift_steps(today['day'], 'open')[0]))
    kit.integer(today['close_at'], 0, len(shift_steps(today['day'], 'close')[0]))
    kit.need(today['good'] <= today['jobs'] and today['ljobs'] <= today['jobs'], 'Số việc đạt chuẩn sai.')
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu của viện sai.')
    for k, v in st.items():
        if k != 'tracks':
            kit.integer(v, 0, 10**9)
    kit.need(isinstance(st['tracks'], dict) and set(st['tracks']) == set(TRACKS), 'Số liệu hướng nghiên cứu sai.')
    for v in st['tracks'].values():
        kit.integer(v, 0, 10**9)
    kit.need(st['good'] <= st['jobs'] and sum(st['tracks'].values()) == st['good'] and st['active_days'] <= st['good'],
             'Tiến trình nghề ở viện sai.')
    kit.need(st['fined'] <= st['nights'] * rc.NIGHT_CAP, 'Tiền đền mẫu hỏng sai.')
    kit.desk_validate(d['desk'], rc.DESK)


SPEC = dict(
    id=ID, prefix='rs_', category='office', people=PEOPLE,
    meta=dict(short='Viện nghiên cứu', place='Viện nghiên cứu Sông Mây', tagline='Số liệu thật, kết quả thật.', icon='flask',
              color='#2f6f73', light='#e4f2f1', weather='Mùi đất ẩm từ ruộng thử và mùi bánh từ bếp thử', work='Phiếu việc',
              station='Phòng thí nghiệm, bếp thử & bàn sáng chế',
              greeting='Cô Diệu Linh treo bảng phân việc: chọn giống cây, công thức món hay sáng chế. Đầu ca mặc đồ bảo hộ, cuối ca tắt thiết bị.',
              caption='Một ruộng thử, một bếp thử, một bàn sáng chế', map_label='VIỆN NGHIÊN CỨU SÔNG MÂY'),
    staff=[('Chị Nhàn', 'lab', 'Kỹ thuật viên, thuộc vị trí từng lọ hóa chất.', 84, 90), ('Bé Su', 'intern', 'Thực tập sinh nhanh tay, hay dán nhãn bằng bút dạ.', 72, 80)],
    roles={'lab': 'Kỹ thuật viên', 'intern': 'Thực tập sinh'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🔬', 'Một ca ở Viện Sông Mây', [('Giống cây', 'Có đối chứng'), ('Công thức', 'Mỗi lần đổi một thứ'), ('Sáng chế', 'Thử an toàn từng bước'),
                                              ('Hội đồng', 'Giữ số liệu thật')],
              ['Chọn hướng nghiên cứu', 'An toàn đầu ca', 'Làm từng bước theo phiếu', 'Cất mẫu, tắt thiết bị cuối ca']),
    stories=[('Cuốn sổ thí nghiệm đầu tiên', ('Chị Nhàn đưa bạn cuốn sổ bìa xanh, trang đầu đã đánh số.', 'Bạn ghi ngày, ghi giờ, ký tên dưới dòng đầu tiên.',
                                               'Chị Nhàn cười: “Ở viện này, cái gì không có trong sổ là chưa từng xảy ra.”'))],
    review_asides=['Số liệu rõ ràng, có đối chứng.', 'Ghi sổ đầy đủ, kể cả lần hỏng.', 'Kết luận đúng mức, không phóng đại.'], situations=[],
    more_line='Cô Diệu Linh vừa giao thêm một phiếu việc.', open_line='Viện đã mở cửa; bảng phân việc, sổ phòng thí nghiệm và ruộng thử chờ sẵn.',
    guide='Đầu ca chọn hướng: Giống cây, Công thức món hay Sáng chế. Mặc đồ bảo hộ, bật tủ hút đầu ca; cất mẫu, tắt thiết bị cuối ca. '
          'Làm từng bước theo phiếu; sai bước thì sửa ngay, thưởng giảm theo chất lượng. Từ ngày 4, việc nào cũng qua hội đồng.',
    employment=dict(postings=[dict(id='research-songmay', org='Viện nghiên cứu Sông Mây', kind='company', title='Nghiên cứu viên tập sự (giống cây, công thức, sáng chế)',
                                   salary=(54, 70), probation_days=3, wants=['careful', 'learning', 'patience'],
                                   perks=['Chị Nhàn kèm những ca đầu', 'Thưởng chất lượng nhỏ theo từng việc', 'Nhận đơn nghiên cứu của người chơi khác'],
                                   culture='Số liệu thật, sổ ghi đủ, kết luận đúng mức. Hội đồng khó tính nhưng công bằng.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
